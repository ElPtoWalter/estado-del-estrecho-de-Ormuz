#!/usr/bin/env python3
"""Genera un sitemap XML válido, determinista y compatible con hreflang.

Se ejecuta al final de todos los generadores, de modo que cualquier mutación
previa y defectuosa del sitemap queda reemplazada antes de validar y publicar.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from maintenance_common import BASE_URL, HOST

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"
ET.register_namespace("", SITEMAP_NS)
ET.register_namespace("xhtml", XHTML_NS)

EXCLUDED_FILES = {"404.html", "offline.html", "preview.html", "panel-x.html", "test.html"}
EXCLUDED_DIRS = {".git", ".github", "node_modules", "tests", "test", "drafts", "private", "vendor", "tmp"}
EXCLUDED_PREFIXES = ("draft-", "private-", "admin-", "test-")


@dataclass
class Page:
    path: Path
    relative: Path
    canonical: str | None = None
    robots: str = ""
    lang: str = ""
    alternates: dict[str, str] = field(default_factory=dict)


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical: str | None = None
        self.robots = ""
        self.lang = ""
        self.alternates: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "html":
            self.lang = data.get("lang", "").strip().lower()
        elif tag == "meta" and data.get("name", "").lower() in {"robots", "googlebot"}:
            self.robots += " " + data.get("content", "").lower()
        elif tag == "link":
            rel = {part.lower() for part in data.get("rel", "").split()}
            href = data.get("href", "").strip()
            if not href:
                return
            if "canonical" in rel:
                self.canonical = href
            if "alternate" in rel and data.get("hreflang"):
                self.alternates[data["hreflang"].strip().lower()] = href


def qname(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def same_host(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc.lower() == HOST


def parse_page(root: Path, path: Path) -> Page:
    parser = MetaParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return Page(
        path=path,
        relative=path.relative_to(root),
        canonical=parser.canonical,
        robots=parser.robots,
        lang=parser.lang,
        alternates=parser.alternates,
    )


def canonical_for(page: Page) -> str:
    if page.canonical:
        candidate = urljoin(BASE_URL, page.canonical)
        if same_host(candidate):
            return candidate.split("#", 1)[0]
    relative = page.relative.as_posix()
    if relative == "index.html":
        return BASE_URL
    if relative.endswith("/index.html"):
        return urljoin(BASE_URL, relative[: -len("index.html")])
    return urljoin(BASE_URL, relative)


def discover_pages(root: Path) -> list[Page]:
    pages: list[Page] = []
    for path in sorted(root.rglob("*.html"), key=lambda p: p.as_posix().casefold()):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        name = path.name.casefold()
        if name in EXCLUDED_FILES or name.startswith(EXCLUDED_PREFIXES):
            continue
        page = parse_page(root, path)
        if "noindex" in page.robots:
            continue
        pages.append(page)
    return pages


def git_lastmod(root: Path, page: Page) -> str | None:
    rel = page.relative.as_posix()
    if not (root / ".git").exists():
        return None
    try:
        changed = subprocess.run(
            ["git", "diff", "--quiet", "--", rel],
            cwd=root, check=False, capture_output=True, timeout=10
        ).returncode != 0
        if changed:
            return datetime.now(timezone.utc).date().isoformat()
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", rel],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def lastmod_for(root: Path, page: Page) -> str:
    return git_lastmod(root, page) or datetime.fromtimestamp(
        page.path.stat().st_mtime, tz=timezone.utc
    ).date().isoformat()


def frequency_priority(url: str) -> tuple[str, str]:
    path = urlparse(url).path.casefold()
    if path in {"/", "/en.html"}:
        return "hourly", "1.0"
    if any(token in path for token in ("evidencias", "en-evidence", "parte-diario", "en-daily-brief")):
        return "hourly", "0.90"
    if any(token in path for token in ("historial", "en-history")):
        return "daily", "0.85"
    if any(token in path for token in ("privacidad", "privacy", "cookies", "aviso-legal", "en-legal")):
        return "yearly", "0.30"
    if any(token in path for token in ("contacto", "contact", "publicidad", "advertising", "media-kit")):
        return "monthly", "0.55"
    if path.startswith("/briefs/"):
        return "monthly", "0.55"
    return "monthly", "0.75"


def build_tree(root: Path, pages: list[Page]) -> ET.ElementTree:
    canonical_map: dict[str, Page] = {}
    for page in pages:
        canonical_map.setdefault(canonical_for(page), page)
    urlset = ET.Element(qname(SITEMAP_NS, "urlset"))
    known = set(canonical_map)

    for loc, page in sorted(canonical_map.items()):
        node = ET.SubElement(urlset, qname(SITEMAP_NS, "url"))
        ET.SubElement(node, qname(SITEMAP_NS, "loc")).text = loc
        ET.SubElement(node, qname(SITEMAP_NS, "lastmod")).text = lastmod_for(root, page)
        freq, priority = frequency_priority(loc)
        ET.SubElement(node, qname(SITEMAP_NS, "changefreq")).text = freq
        ET.SubElement(node, qname(SITEMAP_NS, "priority")).text = priority

        alternates: dict[str, str] = {}
        for lang, href in page.alternates.items():
            absolute = urljoin(BASE_URL, href).split("#", 1)[0]
            if same_host(absolute) and (absolute in known or lang == "x-default"):
                alternates[lang] = absolute
        if "x-default" not in alternates:
            if "es" in alternates:
                alternates["x-default"] = alternates["es"]
            elif page.lang.startswith("es"):
                alternates["x-default"] = loc
        for lang, href in sorted(alternates.items(), key=lambda item: (item[0] == "x-default", item[0])):
            ET.SubElement(
                node,
                qname(XHTML_NS, "link"),
                {"rel": "alternate", "hreflang": lang, "href": href},
            )

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    return tree


def validate_tree(tree: ET.ElementTree, root: Path) -> list[str]:
    errors: list[str] = []
    root_node = tree.getroot()
    if root_node.tag != qname(SITEMAP_NS, "urlset"):
        return ["La raíz no es urlset con el namespace oficial."]
    seen: set[str] = set()
    nodes = root_node.findall(qname(SITEMAP_NS, "url"))
    if not nodes:
        errors.append("El sitemap no contiene URLs.")
    if len(nodes) > 50000:
        errors.append("El sitemap supera el límite de 50.000 URLs.")
    for node in nodes:
        loc_node = node.find(qname(SITEMAP_NS, "loc"))
        loc = (loc_node.text or "").strip() if loc_node is not None else ""
        if not loc:
            errors.append("Entrada sin <loc>.")
            continue
        if loc in seen:
            errors.append(f"URL duplicada: {loc}")
        seen.add(loc)
        if not same_host(loc):
            errors.append(f"URL fuera del dominio canónico: {loc}")
        parsed = urlparse(loc)
        rel = parsed.path.lstrip("/") or "index.html"
        if parsed.path.endswith("/") and parsed.path != "/":
            rel = parsed.path.lstrip("/") + "index.html"
        if rel.endswith(".html") and not (root / rel).exists():
            errors.append(f"El sitemap apunta a un HTML inexistente: {rel}")
        langs: set[str] = set()
        for alt in node.findall(qname(XHTML_NS, "link")):
            lang = alt.attrib.get("hreflang", "").strip().lower()
            href = alt.attrib.get("href", "").strip()
            if alt.attrib.get("rel") != "alternate" or not lang or not href:
                errors.append(f"hreflang incompleto en {loc}")
            if lang in langs:
                errors.append(f"hreflang duplicado {lang} en {loc}")
            langs.add(lang)
            if href and not same_host(href):
                errors.append(f"Alternativa fuera del dominio: {href}")
    return errors


def serialize(tree: ET.ElementTree) -> bytes:
    fd, name = tempfile.mkstemp(prefix="sitemap-render-", suffix=".xml")
    os.close(fd)
    temp = Path(name)
    try:
        tree.write(temp, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
        data = temp.read_bytes()
        ET.fromstring(data)
        if len(data) > 50 * 1024 * 1024:
            raise ValueError("El sitemap supera 50 MB sin comprimir.")
        return data
    finally:
        temp.unlink(missing_ok=True)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else None
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def ensure_robots(root: Path) -> None:
    path = root / "robots.txt"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "User-agent: *\nAllow: /\n"
    lines = [line.rstrip() for line in text.splitlines() if not line.lower().startswith("sitemap:")]
    while lines and not lines[-1]:
        lines.pop()
    lines += ["", f"Sitemap: {BASE_URL}sitemap.xml"]
    from maintenance_common import atomic_write_text

    atomic_write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true", help="No escribe; falla si el sitemap generado difiere.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "sitemap.xml"
    pages = discover_pages(root)
    tree = build_tree(root, pages)
    errors = validate_tree(tree, root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    data = serialize(tree)
    if args.check:
        if not output.exists() or output.read_bytes() != data:
            print("ERROR: sitemap.xml está desactualizado respecto de los HTML públicos.")
            return 1
        print(f"Sitemap correcto y actualizado: {len(pages)} páginas descubiertas.")
        return 0
    atomic_write_bytes(output, data)
    ensure_robots(root)
    print(f"Sitemap regenerado de forma segura: {len(tree.getroot())} URLs, {len(data)} bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
