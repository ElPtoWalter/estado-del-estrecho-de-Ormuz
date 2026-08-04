#!/usr/bin/env python3
"""Prepare Estrecho Ormuz for a second AdSense review."""
from __future__ import annotations

import argparse
import ast
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / "install_v11.py"
PRERENDER = ROOT / "adsense_prerender.py"
REPORT = ROOT / "adsense-readiness-report.json"

CLIENT = "ca-pub-1713078636060241"
PUBLISHER = "pub-1713078636060241"

MONETIZABLE_EXACT = {
    "index.html",
    "en.html",
    "analisis.html",
    "en-analysis.html",
    "parte-diario.html",
    "en-daily-brief.html",
    "importancia.html",
    "en-importance.html",
    "metodologia.html",
    "en-methodology.html",
    "fuentes.html",
    "en-sources.html",
    "sobre.html",
    "en-about.html",
}

NOINDEX_UTILITY = {
    "404.html",
    "widget.html",
    "en-widget.html",
    "social-studio.html",
    "en-social-studio.html",
}

EXCLUDED_FROM_ADS = {
    "404.html",
    "alertas.html",
    "en-alerts.html",
    "aviso-legal.html",
    "en-legal.html",
    "privacidad.html",
    "en-privacy.html",
    "cookies.html",
    "en-cookies.html",
    "contacto.html",
    "en-contact.html",
    "publicidad.html",
    "en-advertising.html",
    "media-kit.html",
    "en-media-kit.html",
    "historial.html",
    "en-history.html",
    "evidencias.html",
    "en-evidence.html",
    "embed.html",
    "en-embed.html",
    "widget.html",
    "en-widget.html",
    "social-studio.html",
    "en-social-studio.html",
}

ADSENSE_BLOCK_RE = re.compile(
    r'\s*<!-- ADSENSE_V11_3_START -->.*?<!-- ADSENSE_V11_3_END -->\s*',
    re.I | re.S,
)
ADSENSE_SCRIPT_RE = re.compile(
    r'\s*<script\b[^>]*src=["\'][^"\']*pagead2\.googlesyndication\.com/'
    r'pagead/js/adsbygoogle\.js[^"\']*["\'][^>]*>\s*</script>\s*',
    re.I | re.S,
)
ADSENSE_META_RE = re.compile(
    r'\s*<meta\b[^>]*name=["\']google-adsense-account["\'][^>]*>\s*',
    re.I | re.S,
)

ADSENSE_SCRIPT = f"""<!-- ADSENSE_V11_3_START -->
<script async
  src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={CLIENT}"
  crossorigin="anonymous"></script>
<!-- ADSENSE_V11_3_END -->"""


class PatchError(RuntimeError):
    pass


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    previous = read(path) if path.exists() else None
    if previous != content:
        path.write_text(content, encoding="utf-8")


def strip_adsense(document: str) -> str:
    document = ADSENSE_BLOCK_RE.sub("\n", document)
    document = ADSENSE_SCRIPT_RE.sub("\n", document)
    document = ADSENSE_META_RE.sub("\n", document)
    return document


def has_article_schema(document: str) -> bool:
    return bool(
        re.search(
            r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>'
            r'.*?"@type"\s*:\s*"(?:Article|NewsArticle|AnalysisNewsArticle)"',
            document,
            re.I | re.S,
        )
    )


def monetizable(filename: str, document: str) -> bool:
    if filename in EXCLUDED_FROM_ADS:
        return False
    return filename in MONETIZABLE_EXACT or has_article_schema(document)


def add_adsense(document: str) -> str:
    meta = f'<meta name="google-adsense-account" content="{CLIENT}">'
    additions = meta + "\n" + ADSENSE_SCRIPT
    if not re.search(r"</head>", document, re.I):
        return document
    return re.sub(
        r"</head>",
        additions + "\n</head>",
        document,
        count=1,
        flags=re.I,
    )


def manage_adsense(filename: str, document: str) -> str:
    document = strip_adsense(document)
    if monetizable(filename, document):
        document = add_adsense(document)
    return document


def set_robots(document: str, value: str) -> str:
    meta = f'<meta name="robots" content="{value}">'
    pattern = re.compile(
        r'<meta\b[^>]*name=["\']robots["\'][^>]*>',
        re.I,
    )
    if pattern.search(document):
        return pattern.sub(meta, document, count=1)
    if re.search(r"</head>", document, re.I):
        return re.sub(
            r"</head>",
            meta + "\n</head>",
            document,
            count=1,
            flags=re.I,
        )
    return document


def add_transparency(document: str, english: bool) -> str:
    marker = "ADSENSE_READINESS_TRANSPARENCY"
    if marker in document or "</main>" not in document:
        return document

    if english:
        block = """<!-- ADSENSE_READINESS_TRANSPARENCY -->
<section class="content-section prose-card" id="editorial-responsibility">
  <span class="section-kicker">Editorial responsibility</span>
  <h2>Independent project operated from Spain</h2>
  <p>Estrecho Ormuz is an independent editorial and technical project. It is not affiliated with a government, military organisation, shipping company or energy company.</p>
  <p>Automated systems collect public signals, but the methodology, thresholds, corrections and publication criteria are documented and remain under human editorial responsibility. Documented corrections can be sent through the contact page.</p>
  <p>Advertising, if enabled, is clearly separated from the monitor's classifications and cannot influence status, evidence selection or conclusions.</p>
</section>
"""
    else:
        block = """<!-- ADSENSE_READINESS_TRANSPARENCY -->
<section class="content-section prose-card" id="responsabilidad-editorial">
  <span class="section-kicker">Responsabilidad editorial</span>
  <h2>Proyecto independiente operado desde España</h2>
  <p>Estrecho Ormuz es un proyecto editorial y técnico independiente. No está afiliado a ningún gobierno, organización militar, naviera ni empresa energética.</p>
  <p>Los sistemas automatizados recopilan señales públicas, pero la metodología, los umbrales, las correcciones y los criterios de publicación están documentados y permanecen bajo responsabilidad editorial humana. Las correcciones documentadas pueden enviarse desde la página de contacto.</p>
  <p>La publicidad, si se activa, se mantiene claramente separada de las clasificaciones del monitor y no puede influir en el estado, la selección de evidencias ni las conclusiones.</p>
</section>
"""
    return document.replace("</main>", block + "</main>", 1)


def replace_top_level_function(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    if len(matches) != 1:
        raise PatchError(f"Expected one function {name}, found {len(matches)}.")
    node = matches[0]
    if node.end_lineno is None:
        raise PatchError(f"Could not locate end of {name}.")
    lines = source.splitlines(keepends=True)
    return "".join(
        lines[: node.lineno - 1]
        + [replacement.rstrip() + "\n\n"]
        + lines[node.end_lineno :]
    )


INSTALLER_FUNCTION = r"""def ensure_adsense_code(text: str, filename: str = "") -> str:
    # ADSENSE_READINESS_V5:
    # Keep ads only on editorial/content-rich pages. Tools, legal pages,
    # archives and utility screens do not load Google ads.
    monetizable_exact = {
        "index.html", "en.html",
        "analisis.html", "en-analysis.html",
        "parte-diario.html", "en-daily-brief.html",
        "importancia.html", "en-importance.html",
        "metodologia.html", "en-methodology.html",
        "fuentes.html", "en-sources.html",
        "sobre.html", "en-about.html",
    }
    excluded = {
        "404.html",
        "alertas.html", "en-alerts.html",
        "aviso-legal.html", "en-legal.html",
        "privacidad.html", "en-privacy.html",
        "cookies.html", "en-cookies.html",
        "contacto.html", "en-contact.html",
        "publicidad.html", "en-advertising.html",
        "media-kit.html", "en-media-kit.html",
        "historial.html", "en-history.html",
        "evidencias.html", "en-evidence.html",
        "embed.html", "en-embed.html",
        "widget.html", "en-widget.html",
        "social-studio.html", "en-social-studio.html",
    }

    text = re.sub(
        r'\s*<!-- ADSENSE_V11_3_START -->.*?<!-- ADSENSE_V11_3_END -->\s*',
        "\n",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'\s*<script\b[^>]*src=["\'][^"\']*pagead2\.googlesyndication\.com/'
        r'pagead/js/adsbygoogle\.js[^"\']*["\'][^>]*>\s*</script>\s*',
        "\n",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'\s*<meta\b[^>]*name=["\']google-adsense-account["\'][^>]*>\s*',
        "\n",
        text,
        flags=re.I | re.S,
    )

    article_schema = bool(
        re.search(
            r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>'
            r'.*?"@type"\s*:\s*"(?:Article|NewsArticle|AnalysisNewsArticle)"',
            text,
            re.I | re.S,
        )
    )
    allowed = filename not in excluded and (
        filename in monetizable_exact or article_schema
    )
    if not allowed:
        return text

    meta = f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}">'
    additions = meta + "\n" + ADSENSE_SCRIPT
    if re.search(r'</head>', text, re.I):
        return re.sub(
            r'</head>',
            additions + "\n</head>",
            text,
            count=1,
            flags=re.I,
        )
    return text
"""


def patch_installer(source: str) -> str:
    if "ADSENSE_READINESS_V5" not in source:
        source = replace_top_level_function(
            source,
            "ensure_adsense_code",
            INSTALLER_FUNCTION,
        )

    source = source.replace(
        "text = ensure_adsense_code(text)",
        "text = ensure_adsense_code(text, path.name)",
    )

    hook = """    try:
        from adsense_prerender import prerender_all
        prerender_all(ROOT)
    except Exception as exc:
        print(f"AVISO: prerender AdSense no aplicado: {exc}")
"""
    if "from adsense_prerender import prerender_all" not in source:
        anchor = "    update_sitemap()\n"
        if anchor not in source:
            raise PatchError("Could not find installer hook point.")
        source = source.replace(anchor, hook + anchor, 1)

    compile(source, str(INSTALLER), "exec")
    return source


def remove_noindex_urls_from_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return
    document = read(path)
    for filename in sorted(NOINDEX_UTILITY):
        document = re.sub(
            rf'\s*<url>\s*<loc>https://estrechoormuz\.com/{re.escape(filename)}</loc>'
            r'.*?</url>\s*',
            "\n",
            document,
            flags=re.I | re.S,
        )
    write(path, document)


def word_count(document: str) -> int:
    visible = re.sub(r"<script\b.*?</script>", " ", document, flags=re.I | re.S)
    visible = re.sub(r"<style\b.*?</style>", " ", visible, flags=re.I | re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    visible = html.unescape(visible)
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", visible))


def apply_html_policy() -> dict[str, Any]:
    monetized: list[str] = []
    ad_free: list[str] = []
    noindex: list[str] = []
    warnings: list[str] = []

    for path in sorted(ROOT.glob("*.html")):
        document = read(path)
        document = manage_adsense(path.name, document)

        if path.name in NOINDEX_UTILITY:
            document = set_robots(document, "noindex,nofollow,noarchive")
            noindex.append(path.name)

        if path.name == "sobre.html":
            document = add_transparency(document, False)
        elif path.name == "en-about.html":
            document = add_transparency(document, True)

        write(path, document)

        if "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" in document:
            monetized.append(path.name)
            if word_count(document) < 250:
                warnings.append(
                    f"{path.name}: monetized page has fewer than 250 visible words"
                )
        else:
            ad_free.append(path.name)

    return {
        "monetized_pages": monetized,
        "ad_free_pages": ad_free,
        "noindex_utility_pages": noindex,
        "warnings": warnings,
    }


def run_prerender() -> None:
    subprocess.run(
        [sys.executable, str(PRERENDER)],
        cwd=ROOT,
        check=True,
    )


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings = list(policy["warnings"])

    for path in ROOT.glob("*.html"):
        document = read(path)
        count = document.count(
            "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
        )
        if count > 1:
            errors.append(f"{path.name}: duplicate AdSense loader")
        if path.name in EXCLUDED_FROM_ADS and count:
            errors.append(f"{path.name}: excluded page still loads AdSense")
        if path.name in NOINDEX_UTILITY and not re.search(
            r'<meta\b[^>]*name=["\']robots["\'][^>]*noindex',
            document,
            re.I,
        ):
            errors.append(f"{path.name}: utility page is not noindex")

    for filename in ("index.html", "en.html"):
        path = ROOT / filename
        if not path.exists():
            errors.append(f"{filename}: missing")
            continue
        document = read(path)
        for token in (
            "CONSULTANDO…",
            "CHECKING…",
            "Cargando evidencias verificadas",
            "Loading verified evidence",
        ):
            if token in document:
                errors.append(
                    f"{filename}: raw HTML still contains loading placeholder {token!r}"
                )

    for filename in ("parte-diario.html", "en-daily-brief.html"):
        path = ROOT / filename
        if not path.exists():
            errors.append(f"{filename}: missing")
            continue
        document = read(path)
        loading_tag = re.search(
            r'<[^>]*id=["\']briefLoading["\'][^>]*>',
            document,
            re.I,
        )
        if loading_tag and "hidden" not in loading_tag.group(0):
            errors.append(f"{filename}: loading notice remains visible")
        if re.search(
            r'id=["\']briefStatusPill["\'][^>]*>\s*—\s*<',
            document,
            re.I,
        ):
            errors.append(f"{filename}: status is still a placeholder")

    ads_txt = ROOT / "ads.txt"
    required = (
        f"google.com, {PUBLISHER}, DIRECT, f08c47fec0942fa0"
    )
    if not ads_txt.exists() or required not in read(ads_txt):
        errors.append(
            "ads.txt does not contain the required Google publisher line"
        )

    result = {
        **policy,
        "warnings": warnings,
        "errors": errors,
        "ready_for_resubmission": not errors,
    }
    write(
        REPORT,
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    )
    if errors:
        raise PatchError(
            "Readiness validation failed: " + " | ".join(errors)
        )
    return result


def apply() -> None:
    if not INSTALLER.exists():
        raise PatchError("install_v11.py is missing")
    if not PRERENDER.exists():
        raise PatchError("adsense_prerender.py is missing")

    write(INSTALLER, patch_installer(read(INSTALLER)))
    policy = apply_html_policy()
    remove_noindex_urls_from_sitemap()
    run_prerender()

    policy = apply_html_policy()
    result = validate(policy)

    print("ADSENSE READINESS V5 COMPLETED")
    print(f"Monetized pages: {len(result['monetized_pages'])}")
    print(f"Ad-free pages: {len(result['ad_free_pages'])}")
    print(f"Noindex utilities: {len(result['noindex_utility_pages'])}")
    print("The site is technically ready for a new review.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Run with --apply to patch the repository.")
        return 0
    try:
        apply()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
