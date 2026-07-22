#!/usr/bin/env python3
"""Auditor integral previo a publicación para estrechoormuz.com.

Los errores bloquean el commit. Los avisos se conservan en un informe JSON y
solo bloquean con --strict. El validador está diseñado para ser útil sin romper
la web por diferencias estilísticas menores.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from maintenance_common import (
    BASE_URL,
    HOST,
    VALID_CONFIDENCE,
    VALID_OPERATIONAL,
    VALID_STATUS,
    atomic_write_json,
    evidence_key,
    iter_evidence,
    load_json,
    load_publishers,
    normalized_key,
    normalized_space,
    parse_iso,
    publisher_from_title,
    utc_now,
)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"
ATOM_NS = "http://www.w3.org/2005/Atom"
EXCLUDED_DIRS = {".git", ".github", "node_modules", "tests", "test", "vendor", "tmp"}
PUBLIC_EXCLUDED = {"404.html", "panel-x.html", "offline.html", "preview.html", "test.html"}
BAD_SELECTOR = ".status-hero.is-loading .status-dot,status-hero.is-loading .status-word"
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:TELEGRAM_BOT_TOKEN|CLOUDFLARE_API_TOKEN)\s*[=:]\s*[\"'][^\"']{12,}", re.I),
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def warn(self, text: str) -> None:
        self.warnings.append(text)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.lang = ""
        self.title_count = 0
        self.description_count = 0
        self.viewport_count = 0
        self.charset_count = 0
        self.canonicals: list[str] = []
        self.robots = ""
        self.h1_count = 0
        self.ids: list[str] = []
        self.refs: list[str] = []
        self.alternates: dict[str, str] = {}
        self.meta_outside_head: list[str] = []
        self.blank_without_rel = 0
        self.images_without_alt = 0
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._json_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "head":
            self.in_head = True
        elif tag == "html":
            self.lang = data.get("lang", "").strip().lower()
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "title":
            self.title_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = data.get("name", "").lower()
            if not self.in_head:
                self.meta_outside_head.append(name or data.get("charset", "meta"))
            if data.get("charset"):
                self.charset_count += 1
            if name == "description":
                self.description_count += 1
            elif name == "viewport":
                self.viewport_count += 1
            elif name in {"robots", "googlebot"}:
                self.robots += " " + data.get("content", "").lower()
        elif tag == "link":
            rel = {part.lower() for part in data.get("rel", "").split()}
            href = data.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonicals.append(href)
            if "alternate" in rel and href and data.get("hreflang"):
                self.alternates[data["hreflang"].strip().lower()] = href
        elif tag == "a":
            if data.get("target", "").lower() == "_blank":
                rel = {part.lower() for part in data.get("rel", "").split()}
                if "noopener" not in rel:
                    self.blank_without_rel += 1
        elif tag == "img" and "alt" not in data:
            self.images_without_alt += 1
        if tag in {"a", "link", "script", "img", "iframe", "source", "video", "audio"}:
            ref = data.get("href") or data.get("src")
            if ref:
                self.refs.append(ref)
        if tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "head":
            self.in_head = False
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_chunks).strip())
            self._in_json_ld = False
            self._json_chunks = []


def public_html_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if path.name.casefold() in PUBLIC_EXCLUDED:
            continue
        result.append(path)
    return result


def local_target(root: Path, source: Path, ref: str) -> Path | None:
    if ref.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#")):
        return None
    clean = ref.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return None
    if clean.startswith("/"):
        candidate = root / clean.lstrip("/")
    else:
        candidate = source.parent / clean
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate.resolve()


def validate_status(root: Path, report: Report) -> dict[str, Any] | None:
    path = root / "status.json"
    payload = load_json(path)
    if not isinstance(payload, dict):
        report.error("status.json falta o no contiene un objeto JSON válido.")
        return None
    required_types = {
        "status": str,
        "operational_status": str,
        "confidence": str,
        "checked_at": str,
        "last_change_at": str,
        "verification_ok": bool,
        "stale": bool,
    }
    for key, expected in required_types.items():
        if key not in payload:
            report.error(f"status.json no contiene {key}.")
        elif not isinstance(payload[key], expected):
            report.error(f"status.json: {key} debe ser {expected.__name__}.")
    if payload.get("status") not in VALID_STATUS:
        report.error(f"status no permitido: {payload.get('status')!r}.")
    if payload.get("operational_status") not in VALID_OPERATIONAL:
        report.error(f"operational_status no permitido: {payload.get('operational_status')!r}.")
    if payload.get("confidence") not in VALID_CONFIDENCE:
        report.error(f"confidence no permitida: {payload.get('confidence')!r}.")

    checked = parse_iso(payload.get("checked_at"))
    changed = parse_iso(payload.get("last_change_at"))
    now = utc_now()
    if checked is None:
        report.error("checked_at no es una fecha ISO válida.")
    elif checked > now + timedelta(hours=2):
        report.error("checked_at está más de dos horas en el futuro.")
    if changed is None:
        report.error("last_change_at no es una fecha ISO válida.")
    if checked and changed and changed > checked:
        report.error("last_change_at es posterior a checked_at.")
    if payload.get("verification_ok") is False:
        report.warn("status.json declara verification_ok=false.")
    if payload.get("stale") is True:
        report.warn("status.json declara stale=true.")
    if payload.get("editorial_review_required") is True:
        report.warn("Existe una transición candidata retenida para revisión editorial.")

    aliases = load_publishers(root / "source_aliases.json")
    keys: list[str] = []
    evidence_count = 0
    for item in iter_evidence(payload):
        evidence_count += 1
        title = normalized_space(item.get("title"))
        source = normalized_space(item.get("source_name"))
        if not title or not source:
            report.warn("Hay una evidencia sin título o fuente.")
        key = evidence_key(item)
        if key:
            keys.append(key)
        for date_key in ("published_at", "observed_at"):
            value = item.get(date_key)
            if value and parse_iso(value) is None:
                report.warn(f"Evidencia con {date_key} inválido: {title[:70]}.")
        suffix = publisher_from_title(title, aliases)
        if suffix and normalized_key(source) != normalized_key(suffix.name):
            report.warn(f"Atribución sospechosa: {source} frente al sufijo {suffix.name}: {title[:90]}.")
        if bool(item.get("official")):
            current = aliases.get(normalized_key(source))
            if current is None or not current.official:
                report.error(f"official=true en una fuente no oficial: {source}.")
        signal = normalized_key(item.get("signal")).upper()
        if signal in {"OPEN_OPERATIONAL", "CLOSED_OPERATIONAL"} and "?" in title:
            report.warn(f"Señal operativa basada en un titular interrogativo: {title[:100]}.")
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        report.warn(f"Hay {len(duplicates)} evidencias duplicadas entre listas activas/archivo.")
    report.info["evidence_count"] = evidence_count
    return payload


def history_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("history", "items", "entries", "changes"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


def validate_history(root: Path, report: Report) -> None:
    path = root / "history.json"
    if not path.exists():
        report.error("Falta history.json.")
        return
    payload = load_json(path)
    if not isinstance(payload, (list, dict)):
        report.error("history.json debe contener una lista u objeto.")
        return
    items = history_items(payload)
    dates: list[Any] = []
    for item in items:
        value = next((item.get(key) for key in ("at", "changed_at", "timestamp", "date", "last_change_at") if item.get(key)), None)
        if value:
            parsed = parse_iso(value)
            if parsed is None:
                report.warn(f"history.json contiene una fecha inválida: {value!r}.")
            else:
                dates.append(parsed)
    if dates and any(value > utc_now() + timedelta(hours=2) for value in dates):
        report.error("history.json contiene cambios fechados en el futuro.")
    report.info["history_entries"] = len(items)


def validate_feed(root: Path, report: Report) -> None:
    path = root / "feed.xml"
    if not path.exists():
        report.error("Falta feed.xml.")
        return
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        report.error(f"feed.xml no es XML válido: {exc}.")
        return
    ids: list[str] = []
    entries = tree.getroot().findall(f".//{{{ATOM_NS}}}entry")
    for entry in entries:
        node = entry.find(f"{{{ATOM_NS}}}id")
        if node is not None and node.text:
            ids.append(node.text.strip())
    if len(ids) != len(set(ids)):
        report.error("feed.xml contiene IDs de entrada duplicados.")
    report.info["feed_entries"] = len(entries)


def url_to_local(root: Path, url: str) -> Path:
    parsed = urlparse(url)
    rel = parsed.path.lstrip("/")
    if not rel:
        rel = "index.html"
    elif parsed.path.endswith("/"):
        rel += "index.html"
    return root / rel


def validate_sitemap(root: Path, report: Report, parsed_pages: dict[Path, PageParser]) -> None:
    path = root / "sitemap.xml"
    if not path.exists():
        report.error("Falta sitemap.xml.")
        return
    if path.stat().st_size > 50 * 1024 * 1024:
        report.error("sitemap.xml supera 50 MB.")
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        report.error(f"sitemap.xml no es XML válido: {exc}.")
        return
    root_node = tree.getroot()
    if root_node.tag != f"{{{SITEMAP_NS}}}urlset":
        report.error("sitemap.xml no usa urlset con el namespace oficial.")
        return
    nodes = root_node.findall(f"{{{SITEMAP_NS}}}url")
    if not nodes:
        report.error("sitemap.xml no contiene URLs.")
    if len(nodes) > 50000:
        report.error("sitemap.xml supera 50.000 URLs.")
    seen: set[str] = set()
    alternate_graph: dict[str, dict[str, str]] = {}
    for node in nodes:
        loc_node = node.find(f"{{{SITEMAP_NS}}}loc")
        loc = normalized_space(loc_node.text if loc_node is not None else "")
        if not loc:
            report.error("Entrada del sitemap sin loc.")
            continue
        if loc in seen:
            report.error(f"URL duplicada en sitemap: {loc}.")
        seen.add(loc)
        parsed = urlparse(loc)
        if parsed.scheme != "https" or parsed.netloc.casefold() != HOST:
            report.error(f"URL no canónica en sitemap: {loc}.")
        local = url_to_local(root, loc)
        if not local.exists():
            report.error(f"El sitemap apunta a un archivo inexistente: {local.relative_to(root)}.")
        page = parsed_pages.get(local.resolve())
        if page:
            if "noindex" in page.robots:
                report.error(f"Página noindex incluida en sitemap: {loc}.")
            if page.canonicals:
                canonical = urljoin(BASE_URL, page.canonicals[0]).split("#", 1)[0]
                if canonical != loc:
                    report.error(f"Canonical y sitemap no coinciden: {loc} frente a {canonical}.")
        lastmod = node.find(f"{{{SITEMAP_NS}}}lastmod")
        if lastmod is not None and lastmod.text:
            try:
                from datetime import date

                parsed_date = date.fromisoformat(lastmod.text.strip())
                if parsed_date > utc_now().date() + timedelta(days=1):
                    report.error(f"lastmod futuro en {loc}.")
            except ValueError:
                report.error(f"lastmod inválido en {loc}: {lastmod.text!r}.")
        langs: dict[str, str] = {}
        for alt in node.findall(f"{{{XHTML_NS}}}link"):
            lang = normalized_key(alt.attrib.get("hreflang"))
            href = normalized_space(alt.attrib.get("href"))
            if alt.attrib.get("rel") != "alternate" or not lang or not href:
                report.error(f"xhtml:link incompleto en {loc}.")
                continue
            if lang in langs:
                report.error(f"hreflang {lang} duplicado en {loc}.")
            langs[lang] = href
            target = urlparse(href)
            if target.scheme != "https" or target.netloc.casefold() != HOST:
                report.error(f"hreflang fuera del dominio en {loc}: {href}.")
        alternate_graph[loc] = langs
    for loc, langs in alternate_graph.items():
        for lang, href in langs.items():
            if lang == "x-default" or href not in alternate_graph:
                continue
            reverse_values = set(alternate_graph[href].values())
            if loc not in reverse_values:
                report.warn(f"hreflang no recíproco entre {loc} y {href}.")
    report.info["sitemap_urls"] = len(seen)


def validate_html(root: Path, report: Report) -> dict[Path, PageParser]:
    parsed: dict[Path, PageParser] = {}
    files = public_html_files(root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        parser = PageParser()
        try:
            parser.feed(text)
        except Exception as exc:
            report.error(f"{rel}: HTML no analizable: {exc}.")
            continue
        parsed[path.resolve()] = parser
        if parser.title_count != 1:
            report.warn(f"{rel}: contiene {parser.title_count} etiquetas title.")
        if parser.description_count != 1:
            report.warn(f"{rel}: contiene {parser.description_count} meta descriptions.")
        if parser.viewport_count != 1:
            report.warn(f"{rel}: contiene {parser.viewport_count} meta viewport.")
        if parser.charset_count != 1:
            report.warn(f"{rel}: contiene {parser.charset_count} meta charset.")
        if len(parser.canonicals) != 1:
            report.warn(f"{rel}: contiene {len(parser.canonicals)} enlaces canonical.")
        if not parser.lang:
            report.warn(f"{rel}: falta lang en html.")
        if parser.h1_count != 1:
            report.warn(f"{rel}: contiene {parser.h1_count} encabezados h1.")
        if parser.meta_outside_head:
            report.error(f"{rel}: hay meta fuera de head: {', '.join(parser.meta_outside_head[:8])}.")
        duplicates = [value for value, count in Counter(parser.ids).items() if count > 1]
        if duplicates:
            report.error(f"{rel}: IDs duplicados: {', '.join(duplicates[:8])}.")
        if parser.blank_without_rel:
            report.warn(f"{rel}: {parser.blank_without_rel} enlaces _blank sin noopener.")
        if parser.images_without_alt:
            report.warn(f"{rel}: {parser.images_without_alt} imágenes sin atributo alt.")
        if BAD_SELECTOR in text:
            report.error(f"{rel}: contiene el selector CSS defectuoso conocido.")
        if re.search(r"http://(?:www\.)?estrechoormuz\.com", text, re.I):
            report.error(f"{rel}: contiene URLs HTTP del propio dominio.")
        for block in parser.json_ld:
            if not block:
                continue
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                report.warn(f"{rel}: JSON-LD inválido: {exc.msg}.")
        missing: set[str] = set()
        for ref in parser.refs:
            target = local_target(root, path, ref)
            if target is not None and not target.exists():
                missing.add(ref)
        for ref in sorted(missing)[:12]:
            report.warn(f"{rel}: referencia local no encontrada: {ref}.")
    report.info["html_pages"] = len(files)
    return parsed


def validate_robots(root: Path, report: Report) -> None:
    path = root / "robots.txt"
    if not path.exists():
        report.error("Falta robots.txt.")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if f"Sitemap: {BASE_URL}sitemap.xml" not in text:
        report.warn("robots.txt no declara el sitemap canónico.")
    if re.search(r"(?im)^\s*Disallow:\s*/\s*$", text):
        report.error("robots.txt bloquea todo el sitio con Disallow: /.")


def validate_security(root: Path, report: Report) -> None:
    for forbidden in (".env", "id_rsa", "id_ed25519"):
        if (root / forbidden).exists():
            report.error(f"Archivo sensible presente en el sitio público: {forbidden}.")
    extensions = {".py", ".yml", ".yaml", ".json", ".html", ".js", ".css", ".txt", ".xml", ".md"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in extensions:
            continue
        rel = path.relative_to(root)
        if any(part in {".git", "node_modules"} for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                report.error(f"Posible secreto expuesto en {rel.as_posix()}.")
                break


def validate_optional_json(root: Path, report: Report) -> None:
    for name in ("daily-brief.json", "social-drafts.json", "config.json", "sources.json", "health.json"):
        path = root / name
        if not path.exists():
            continue
        if load_json(path, default=None) is None:
            report.error(f"{name} no es JSON válido.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = Report()

    validate_status(root, report)
    validate_history(root, report)
    validate_feed(root, report)
    pages = validate_html(root, report)
    validate_sitemap(root, report, pages)
    validate_robots(root, report)
    validate_optional_json(root, report)
    validate_security(root, report)

    # Deduplicación estable para que el log no repita el mismo defecto.
    report.errors = list(dict.fromkeys(report.errors))
    report.warnings = list(dict.fromkeys(report.warnings))
    for item in report.errors:
        print(f"ERROR: {item}")
    for item in report.warnings:
        print(f"AVISO: {item}")
    print(f"Resultado: {len(report.errors)} errores, {len(report.warnings)} avisos.")

    payload = {
        "version": 2,
        "valid": not report.errors and not (args.strict and report.warnings),
        "errors": report.errors,
        "warnings": report.warnings,
        "metrics": report.info,
    }
    if args.report:
        atomic_write_json(args.report, payload)
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
