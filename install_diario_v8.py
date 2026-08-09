#!/usr/bin/env python3
"""Instala El Diario de Ormuz V8 sin sustituir el motor operativo existente."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "diario_v8_payload.zip"
GENERATOR = ROOT / "generate_daily_journal.py"
TEST = ROOT / "test_daily_journal_v8.py"
READINESS = ROOT / "diario-v8-readiness.json"
CSS_NAME = "diario-v8.css"


class InstallError(RuntimeError):
    pass


def stable_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous != text:
        path.write_text(text, encoding="utf-8")


def ensure_repo() -> None:
    required = [
        ROOT / "status.json",
        ROOT / "index.html",
        ROOT / "en.html",
        ROOT / "build_sitemap.py",
        ROOT / "validate_site.py",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise InstallError("Faltan archivos base del repositorio: " + ", ".join(missing))
    if not PAYLOAD.exists():
        raise InstallError("Falta diario_v8_payload.zip en la raíz.")


def extract_payload() -> None:
    allowed = {
        "generate_daily_journal.py",
        "diario-v8.css",
        "test_daily_journal_v8.py",
    }
    with zipfile.ZipFile(PAYLOAD) as archive:
        names = set(archive.namelist())
        if not allowed.issubset(names):
            raise InstallError("El payload está incompleto.")
        for name in allowed:
            target = (ROOT / name).resolve()
            if ROOT.resolve() not in target.parents:
                raise InstallError("Ruta insegura en el payload.")
            target.write_bytes(archive.read(name))


def ensure_css_link(text: str) -> str:
    if re.search(r'<link\b[^>]*href=["\']/diario-v8\.css["\']', text, re.I):
        return text
    tag = '<link rel="stylesheet" href="/diario-v8.css"/>'
    return re.sub(r'</head>', tag + "\n</head>", text, count=1, flags=re.I)


def insert_link_after(text: str, href: str, label: str, anchors: tuple[str, ...]) -> str:
    if re.search(rf'href=["\']{re.escape(href)}["\']', text, re.I):
        return text
    for anchor in anchors:
        pattern = re.compile(
            rf'(<a\b[^>]*href=["\']{re.escape(anchor)}["\'][^>]*>.*?</a>)',
            re.I | re.S,
        )
        if pattern.search(text):
            return pattern.sub(lambda m: m.group(1) + f'<a href="{href}">{label}</a>', text, count=1)
    return text


def patch_navigation(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    english = bool(re.search(r'<html\b[^>]*lang=["\']en', text, re.I))
    href = "/en-diary.html" if english else "/diario.html"
    label = "Daily diary" if english else "Diario"
    anchors = ("/en-daily-brief.html", "/en-analysis.html") if english else ("/parte-diario.html", "/analisis.html")

    nav_pattern = re.compile(r'(<nav\b(?=[^>]*id=["\']site-nav["\'])[^>]*>)(.*?)(</nav>)', re.I | re.S)
    match = nav_pattern.search(text)
    if match:
        inner = insert_link_after(match.group(2), href, label, anchors)
        text = text[: match.start()] + match.group(1) + inner + match.group(3) + text[match.end() :]

    footer_pos = text.lower().find("<footer")
    if footer_pos >= 0:
        head, footer = text[:footer_pos], text[footer_pos:]
        footer = insert_link_after(footer, href, label, anchors)
        text = head + footer

    text = ensure_css_link(text)
    stable_write(path, text)


def patch_root_pages() -> None:
    for path in sorted(ROOT.glob("*.html")):
        patch_navigation(path)


def patch_analysis_card(path: Path, english: bool) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "JOURNAL_V8_ANALYSIS_CARD"
    if marker in text:
        return
    if english:
        card = '''<!-- JOURNAL_V8_ANALYSIS_CARD --><a class="home-analysis-card-v11 is-new" href="/en-diary.html"><span class="home-analysis-label">Daily newsroom</span><h3>Hormuz Daily: the situation explained every morning</h3><p>A narrative briefing combining traffic, security, diplomacy, energy and what to watch next.</p><b>Read today’s edition →</b></a>'''
    else:
        card = '''<!-- JOURNAL_V8_ANALYSIS_CARD --><a class="home-analysis-card-v11 is-new" href="/diario.html"><span class="home-analysis-label">Redacción diaria</span><h3>El Diario de Ormuz: la situación explicada cada mañana</h3><p>Una crónica que combina tráfico, seguridad, diplomacia, energía y qué vigilar después.</p><b>Leer edición de hoy →</b></a>'''
    grid_end = re.search(r'</div>\s*</section>', text, re.I)
    if grid_end:
        text = text[:grid_end.start()] + card + text[grid_end.start():]
    else:
        text = text.replace("</main>", f'<section class="content-section">{card}</section></main>', 1)
    stable_write(path, ensure_css_link(text))


def patch_llms() -> None:
    path = ROOT / "llms.txt"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "## V8 · El Diario de Ormuz"
    if marker in text:
        return
    addition = (
        "\n\n## V8 · El Diario de Ormuz\n"
        "- Edición diaria ES: https://estrechoormuz.com/diario.html\n"
        "- Daily edition EN: https://estrechoormuz.com/en-diary.html\n"
        "- Hemeroteca ES: https://estrechoormuz.com/diario/\n"
        "- Archive EN: https://estrechoormuz.com/diary/\n"
        "- Feed: https://estrechoormuz.com/diario-feed.xml\n"
    )
    stable_write(path, text.rstrip() + addition)


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, check=False)
    if result.returncode != 0:
        raise InstallError("Falló: " + " ".join(command))


def validate_installation() -> dict:
    checks = {
        "generator": GENERATOR.exists(),
        "css": (ROOT / CSS_NAME).exists(),
        "live_es": (ROOT / "diario.html").exists(),
        "live_en": (ROOT / "en-diary.html").exists(),
        "archive_es": (ROOT / "diario" / "index.html").exists(),
        "archive_en": (ROOT / "diary" / "index.html").exists(),
        "latest_json": (ROOT / "journal-latest.json").exists(),
        "health_json": (ROOT / "journal-health.json").exists(),
        "feed": (ROOT / "diario-feed.xml").exists(),
        "home_es": "JOURNAL_V8_HOME_START" in (ROOT / "index.html").read_text(encoding="utf-8"),
        "home_en": "JOURNAL_V8_HOME_START" in (ROOT / "en.html").read_text(encoding="utf-8"),
    }
    health = json.loads((ROOT / "journal-health.json").read_text(encoding="utf-8")) if checks["health_json"] else {}
    ready = all(checks.values()) and bool(health.get("ok"))
    result = {
        "version": 8,
        "ready": ready,
        "checks": checks,
        "journal_health": health,
        "design": {
            "live_daily_page": True,
            "material_only_indexable_archive": True,
            "paid_ai_api_required": False,
            "transparent_automation": True,
            "legacy_status_engine_replaced": False,
        },
    }
    stable_write(READINESS, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if not ready:
        raise InstallError("La validación final de Diario V8 no está completa.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Ejecuta con --apply para instalar El Diario de Ormuz V8.")
        return 0
    try:
        ensure_repo()
        extract_payload()
        run([sys.executable, "-m", "py_compile", "generate_daily_journal.py", "test_daily_journal_v8.py"])
        run([sys.executable, "-m", "unittest", "-v", "test_daily_journal_v8.py"])
        patch_root_pages()
        patch_analysis_card(ROOT / "analisis.html", False)
        patch_analysis_card(ROOT / "en-analysis.html", True)
        patch_llms()
        # First edition: network is attempted, but existing monitor evidence is enough to fall back safely.
        run([sys.executable, "generate_daily_journal.py", "--force"])
        # Generator rewrites the home teaser; make sure the root pages retain nav/CSS additions.
        patch_root_pages()
        run([sys.executable, "build_sitemap.py", "--root", "."])
        run([sys.executable, "validate_site.py", "--root", ".", "--report", "diario-v8-validation.json"])
        result = validate_installation()
        print("EL DIARIO DE ORMUZ V8 INSTALADO")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
