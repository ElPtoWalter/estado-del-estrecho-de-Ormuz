#!/usr/bin/env python3
"""Instalador idempotente Ormuz Growth V4.

Extrae los activos del paquete, integra el widget, el estudio social y tres
análisis bilingües sin modificar el motor editorial ni los workflows normales.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "growth_v4_payload.zip"
CSS_LINK = '<link href="/growth-v4.css" rel="stylesheet"/>'
HOME_START = '<!-- ORMUZ_GROWTH_V4_HOME_START -->'
HOME_END = '<!-- ORMUZ_GROWTH_V4_HOME_END -->'
CARDS_START = '<!-- ORMUZ_GROWTH_V4_CARDS_START -->'
CARDS_END = '<!-- ORMUZ_GROWTH_V4_CARDS_END -->'

NEW_HTML = [
    "widget.html", "en-widget.html", "embed.html", "en-embed.html",
    "social-studio.html",
    "puede-estar-abierto-ormuz-aunque-caiga-trafico.html",
    "en-can-hormuz-be-open-while-traffic-collapses.html",
    "quien-controla-estrecho-ormuz-derecho-paso.html",
    "en-who-controls-strait-of-hormuz-transit-passage.html",
    "seguros-maritimos-primas-guerra-ormuz.html",
    "en-marine-insurance-war-risk-premiums-hormuz.html",
]

class InstallError(RuntimeError):
    pass


def stable_write(path: Path, text: str) -> None:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def remove_marked(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end), "", text, flags=re.S)


def ensure_css(text: str) -> str:
    if "growth-v4.css" in text:
        return text
    if "</head>" not in text:
        raise InstallError("HTML sin </head> al intentar enlazar Growth V4")
    return text.replace("</head>", CSS_LINK + "\n</head>", 1)


def insert_before_main_end(text: str, block: str) -> str:
    if "</main>" not in text:
        raise InstallError("HTML sin </main>")
    return text.replace("</main>", block + "\n</main>", 1)


def patch_home(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = ensure_css(remove_marked(text, HOME_START, HOME_END))
    # Prefer the FAQ boundary; fall back to sponsorship or the end of main.
    patterns = [
        r'<section\b(?=[^>]*aria-labelledby=["\']faq-title["\'])',
        r'<section\b(?=[^>]*class=["\'][^"\']*sponsor-band)',
    ]
    inserted = False
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            text = text[:match.start()] + block + "\n" + text[match.start():]
            inserted = True
            break
    if not inserted:
        text = insert_before_main_end(text, block)
    stable_write(path, text)


def patch_analysis(path: Path, cards: str, english: bool) -> None:
    text = path.read_text(encoding="utf-8")
    text = ensure_css(remove_marked(text, CARDS_START, CARDS_END))
    if english:
        text = re.sub(r"\b7\s+analyses\s+published\b", "10 analyses published", text, count=1, flags=re.I)
        last_url = "/en-how-hormuz-affects-spain-europe.html"
    else:
        text = re.sub(r"\b7\s+análisis\s+publicados\b", "10 análisis publicados", text, count=1, flags=re.I)
        last_url = "/como-afecta-ormuz-espana-europa.html"
    pattern = re.compile(
        r'(<a\b[^>]*href=["\']' + re.escape(last_url) + r'["\'][^>]*>.*?</a>)',
        re.I | re.S,
    )
    if not pattern.search(text):
        raise InstallError(f"No se encontró la última tarjeta conocida en {path.name}")
    text = pattern.sub(lambda m: m.group(1) + cards, text, count=1)
    stable_write(path, text)


def patch_media_kit(path: Path, english: bool) -> None:
    if not path.exists():
        return
    marker_a = '<!-- ORMUZ_GROWTH_V4_MEDIA_START -->'
    marker_b = '<!-- ORMUZ_GROWTH_V4_MEDIA_END -->'
    text = ensure_css(remove_marked(path.read_text(encoding="utf-8"), marker_a, marker_b))
    if english:
        block = marker_a + '''<section class="content-section g4-growth-band"><div class="g4-growth-copy"><span class="section-kicker">Live syndication</span><h2>Embed the status with visible attribution</h2><p>Publishers can use the responsive widget or create a current social card without copying an unverified screenshot.</p><div class="g4-actions"><a class="button primary" href="/en-embed.html">Configure widget</a><a class="button" href="/social-studio.html?lang=en">Create social card</a></div></div><div class="g4-growth-preview"><iframe src="/en-widget.html?lang=en&theme=dark&compact=0" title="Live Hormuz status" style="width:100%;height:260px;border:0"></iframe></div></section>''' + marker_b
    else:
        block = marker_a + '''<section class="content-section g4-growth-band"><div class="g4-growth-copy"><span class="section-kicker">Distribución en directo</span><h2>Inserta el estado con atribución visible</h2><p>Medios y blogs pueden usar el widget responsive o crear una tarjeta actual sin copiar una captura descontextualizada.</p><div class="g4-actions"><a class="button primary" href="/embed.html">Configurar widget</a><a class="button" href="/social-studio.html">Crear tarjeta social</a></div></div><div class="g4-growth-preview"><iframe src="/widget.html?lang=es&theme=dark&compact=0" title="Estado en directo de Ormuz" style="width:100%;height:260px;border:0"></iframe></div></section>''' + marker_b
    stable_write(path, insert_before_main_end(text, block))


def patch_llms() -> None:
    path = ROOT / "llms.txt"
    if not path.exists():
        return
    start = "## Growth V4 · distribución y nuevos análisis"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\n?## Growth V4 · distribución y nuevos análisis.*\Z", "", text, flags=re.S)
    block = '''

## Growth V4 · distribución y nuevos análisis
- Widget ES: https://estrechoormuz.com/widget.html
- Widget EN: https://estrechoormuz.com/en-widget.html
- Guía para insertar: https://estrechoormuz.com/embed.html
- Estudio social: https://estrechoormuz.com/social-studio.html
- Abierto frente a caída del tráfico: https://estrechoormuz.com/puede-estar-abierto-ormuz-aunque-caiga-trafico.html
- Control y derecho de paso: https://estrechoormuz.com/quien-controla-estrecho-ormuz-derecho-paso.html
- Seguros y riesgo de guerra: https://estrechoormuz.com/seguros-maritimos-primas-guerra-ormuz.html
'''
    stable_write(path, text.rstrip() + block)


def extract_payload() -> Path:
    if not PAYLOAD.exists():
        raise InstallError("Falta growth_v4_payload.zip junto al instalador")
    temp = Path(tempfile.mkdtemp(prefix="ormuz-growth-v4-"))
    with zipfile.ZipFile(PAYLOAD) as archive:
        for member in archive.infolist():
            destination = (temp / member.filename).resolve()
            if not str(destination).startswith(str(temp.resolve())):
                raise InstallError("Ruta insegura dentro del payload")
        archive.extractall(temp)
    return temp


def install_files(temp: Path) -> None:
    for path in temp.rglob("*"):
        if not path.is_file() or "_snippets" in path.parts:
            continue
        rel = path.relative_to(temp)
        stable_write(ROOT / rel, path.read_text(encoding="utf-8"))


def validate() -> None:
    required = [
        ROOT / "growth-v4.css", ROOT / "widget.js", ROOT / "embed.js",
        ROOT / "social-studio.js", *[ROOT / name for name in NEW_HTML],
    ]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise InstallError("Faltan archivos tras instalar: " + ", ".join(missing))
    for name in ("index.html", "en.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        if text.count(HOME_START) != 1 or text.count("growth-v4.css") != 1:
            raise InstallError(f"Integración de portada incompleta en {name}")
    for name in ("analisis.html", "en-analysis.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        if text.count(CARDS_START) != 1 or text.count("growth-v4.css") != 1:
            raise InstallError(f"Integración de análisis incompleta en {name}")
    # Basic HTML checks for the new static pages.
    for name in NEW_HTML:
        text = (ROOT / name).read_text(encoding="utf-8")
        if "<!DOCTYPE html>" not in text or "</html>" not in text:
            raise InstallError(f"Documento HTML incompleto: {name}")


def run_optional_tools() -> None:
    commands = []
    if (ROOT / "build_sitemap.py").exists():
        commands.append([sys.executable, "build_sitemap.py", "--root", "."])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            raise InstallError("Falló: " + " ".join(command))


def apply() -> None:
    for name in ("index.html", "en.html", "analisis.html", "en-analysis.html"):
        if not (ROOT / name).exists():
            raise InstallError(f"No existe {name} en la raíz")
    temp = extract_payload()
    try:
        install_files(temp)
        home_es = (temp / "_snippets/home_es.html").read_text(encoding="utf-8")
        home_en = (temp / "_snippets/home_en.html").read_text(encoding="utf-8")
        cards_es = (temp / "_snippets/cards_es.html").read_text(encoding="utf-8")
        cards_en = (temp / "_snippets/cards_en.html").read_text(encoding="utf-8")
        patch_home(ROOT / "index.html", home_es)
        patch_home(ROOT / "en.html", home_en)
        patch_analysis(ROOT / "analisis.html", cards_es, False)
        patch_analysis(ROOT / "en-analysis.html", cards_en, True)
        patch_media_kit(ROOT / "media-kit.html", False)
        patch_media_kit(ROOT / "en-media-kit.html", True)
        patch_llms()
        validate()
        run_optional_tools()
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    print("ORMUZ GROWTH V4 instalado: widget, estudio social y 3 análisis bilingües.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Ejecuta con --apply para instalar Growth V4.")
        return 0
    try:
        apply()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
