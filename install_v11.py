


#!/usr/bin/env python3
# Estrecho Ormuz · Instalador V11.3 · AdSense
# Integra el Parte diario y los 7 análisis en las portadas ES/EN.
# Añade el código de Google AdSense a todas las páginas y crea ads.txt.
# Es idempotente: puede ejecutarse cada hora sin duplicar bloques.

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ADSENSE_CLIENT = "ca-pub-1713078636060241"
ADSENSE_PUBLISHER = "pub-1713078636060241"
ADSENSE_SCRIPT = f'''<!-- ADSENSE_V11_3_START -->
<script async
  src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}"
  crossorigin="anonymous"></script>
<!-- ADSENSE_V11_3_END -->'''


NEW_URLS = [
    ("parte-diario.html", "daily", "0.95"),
    ("en-daily-brief.html", "daily", "0.95"),
    ("paises-dependen-mas-estrecho-ormuz.html", "monthly", "0.90"),
    ("en-countries-most-dependent-on-strait-of-hormuz.html", "monthly", "0.90"),
    ("por-que-qatar-no-puede-desviar-gnl-ormuz.html", "monthly", "0.90"),
    ("en-why-qatar-cannot-reroute-lng-around-hormuz.html", "monthly", "0.90"),
    ("como-afecta-ormuz-espana-europa.html", "monthly", "0.90"),
    ("en-how-hormuz-affects-spain-europe.html", "monthly", "0.90"),
    ("media-kit.html", "monthly", "0.55"),
    ("en-media-kit.html", "monthly", "0.55"),
]

ARTICLES_ES = [
    "que-significa-cierre-estrecho-ormuz.html",
    "como-afectaria-cierre-ormuz-petroleo-gas-economia.html",
    "como-comprobar-trafico-maritimo-operativo-ormuz.html",
    "rutas-alternativas-cierre-estrecho-ormuz-capacidad.html",
]

ARTICLES_EN = [
    "en-what-does-closing-strait-of-hormuz-mean.html",
    "en-how-hormuz-closure-affects-oil-gas-economy.html",
    "en-how-to-verify-operational-maritime-traffic-hormuz.html",
    "en-alternative-routes-strait-of-hormuz-closure-capacity.html",
]

CSS_MARKER = "/* HOME_V11_2_START */"
CSS_BLOCK = r'''
/* HOME_V11_2_START */
.home-brief-v11{
  position:relative;
  display:grid;
  grid-template-columns:minmax(0,1.35fr) minmax(260px,.65fr);
  gap:28px;
  align-items:center;
  overflow:hidden;
  padding:clamp(24px,4vw,42px);
  border:1px solid rgba(104,217,255,.24);
  border-radius:26px;
  background:
    radial-gradient(circle at 90% 20%,rgba(104,217,255,.15),transparent 34%),
    linear-gradient(145deg,rgba(13,29,45,.98),rgba(7,17,31,.94));
  box-shadow:0 24px 80px rgba(0,0,0,.22);
}
.home-brief-v11::after{
  content:"";
  position:absolute;
  width:240px;height:240px;
  right:-110px;bottom:-150px;
  border:1px solid rgba(104,217,255,.18);
  border-radius:50%;
  box-shadow:0 0 0 34px rgba(104,217,255,.035),0 0 0 68px rgba(104,217,255,.018);
  pointer-events:none;
}
.home-brief-v11 h2{margin:.35rem 0 .8rem;font-size:clamp(1.75rem,3.5vw,3rem);letter-spacing:-.035em}
.home-brief-v11 p{max-width:760px;color:var(--muted)}
.home-brief-points{display:grid;gap:10px;margin:20px 0 0;padding:0;list-style:none}
.home-brief-points li{display:flex;gap:10px;align-items:flex-start;color:var(--text)}
.home-brief-points li::before{content:"";flex:0 0 8px;width:8px;height:8px;margin-top:.52em;border-radius:50%;background:var(--v11-cyan,#68d9ff);box-shadow:0 0 16px rgba(104,217,255,.75)}
.home-brief-action-v11{position:relative;z-index:1;padding:22px;border:1px solid var(--line);border-radius:20px;background:rgba(4,12,22,.56)}
.home-brief-action-v11 strong{display:block;margin-bottom:8px;font-size:1.12rem}
.home-brief-action-v11 p{margin:0 0 18px;font-size:.92rem}
.home-analysis-v11{display:block}
.home-analysis-grid-v11{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.home-analysis-card-v11{
  display:flex;
  min-height:220px;
  flex-direction:column;
  padding:21px;
  border:1px solid var(--line);
  border-radius:21px;
  background:linear-gradient(145deg,rgba(13,29,45,.90),rgba(7,17,31,.84));
  color:var(--text);
  text-decoration:none;
  transition:transform .18s ease,border-color .18s ease,background .18s ease;
}
.home-analysis-card-v11:hover{transform:translateY(-3px);border-color:rgba(104,217,255,.38);background:linear-gradient(145deg,rgba(16,35,54,.96),rgba(7,17,31,.91))}
.home-analysis-card-v11 .home-analysis-label{color:var(--v11-cyan,#68d9ff);font-size:.73rem;font-weight:850;letter-spacing:.07em;text-transform:uppercase}
.home-analysis-card-v11 h3{margin:.72rem 0 .62rem;font-size:1.12rem;line-height:1.25}
.home-analysis-card-v11 p{margin:0;color:var(--muted);font-size:.9rem}
.home-analysis-card-v11 b{margin-top:auto;padding-top:18px;font-size:.86rem}
.home-analysis-card-v11.is-new{border-color:rgba(104,217,255,.23)}
.home-analysis-card-v11.is-new .home-analysis-label::before{content:"NUEVO · "}
html[lang="en"] .home-analysis-card-v11.is-new .home-analysis-label::before{content:"NEW · "}
.home-analysis-footer-v11{display:flex;justify-content:flex-end;margin-top:18px}
@media (max-width:980px){
  .home-brief-v11{grid-template-columns:1fr}
  .home-analysis-grid-v11{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:650px){
  .home-brief-v11{padding:22px}
  .home-analysis-grid-v11{grid-template-columns:1fr}
  .home-analysis-card-v11{min-height:0}
}
/* HOME_V11_2_END */
'''

BRIEF_ES = r'''<!-- HOME_V11_BRIEF_START -->
<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">
  <div>
    <span class="section-kicker">Parte operativo diario</span>
    <h2 id="daily-brief-title">La situación esencial, actualizada automáticamente</h2>
    <p>Una síntesis del estado verificado, los cambios materiales, las evidencias destacadas y las señales que conviene vigilar, sin convertir cada titular en una alerta.</p>
    <ul class="home-brief-points">
      <li>Estado operativo y nivel de confianza.</li>
      <li>Cambios frente al parte anterior.</li>
      <li>Evidencias seleccionadas y próximas señales.</li>
    </ul>
  </div>
  <aside class="home-brief-action-v11">
    <strong>Actualización automática</strong>
    <p>La página se regenera desde <code>status.json</code> y conserva un archivo diario auditable.</p>
    <a class="button primary" href="/parte-diario.html">Abrir parte diario</a>
  </aside>
</section>
<!-- HOME_V11_BRIEF_END -->'''

BRIEF_EN = r'''<!-- HOME_V11_BRIEF_START -->
<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">
  <div>
    <span class="section-kicker">Daily operational brief</span>
    <h2 id="daily-brief-title">The essential situation, updated automatically</h2>
    <p>A concise view of verified status, material changes, highlighted evidence and the signals worth watching, without turning every headline into an alert.</p>
    <ul class="home-brief-points">
      <li>Operational status and confidence level.</li>
      <li>Changes from the previous brief.</li>
      <li>Selected evidence and next signals.</li>
    </ul>
  </div>
  <aside class="home-brief-action-v11">
    <strong>Automatic update</strong>
    <p>The page is regenerated from <code>status.json</code> and retains an auditable daily archive.</p>
    <a class="button primary" href="/en-daily-brief.html">Open daily brief</a>
  </aside>
</section>
<!-- HOME_V11_BRIEF_END -->'''

ANALYSIS_ES = r'''<!-- HOME_V11_ANALYSIS_START -->
<section aria-labelledby="context-title" class="content-section home-analysis-v11">
  <div class="section-heading section-heading-v4">
    <div><span class="section-index">05</span><div><p class="section-kicker">Análisis y contexto</p><h2 id="context-title">Entender antes de concluir</h2></div></div>
    <a class="text-link" href="/analisis.html">Ver todos los análisis →</a>
  </div>
  <div class="home-analysis-grid-v11">
    <a class="home-analysis-card-v11" href="/que-significa-cierre-estrecho-ormuz.html"><span class="home-analysis-label">Navegación</span><h3>¿Qué significa realmente que el estrecho esté cerrado?</h3><p>Amenaza, restricción, interrupción parcial y cierre efectivo.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11" href="/como-afectaria-cierre-ormuz-petroleo-gas-economia.html"><span class="home-analysis-label">Energía</span><h3>Cómo afectaría al petróleo, al gas y a la economía</h3><p>Flujos físicos, GNL, fletes, inflación y límites de sustitución.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11" href="/como-comprobar-trafico-maritimo-operativo-ormuz.html"><span class="home-analysis-label">AIS</span><h3>Cómo comprobar si existe tráfico marítimo operativo</h3><p>Trayectorias completas, avisos oficiales y límites de cobertura.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11" href="/rutas-alternativas-cierre-estrecho-ormuz-capacidad.html"><span class="home-analysis-label">Infraestructura</span><h3>Qué rutas alternativas existen y cuánta capacidad tienen</h3><p>Oleoductos, puertos, capacidad nominal y caudal utilizable.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/paises-dependen-mas-estrecho-ormuz.html"><span class="home-analysis-label">Dependencia</span><h3>Qué países dependen más del estrecho de Ormuz</h3><p>China, India, Japón, Corea del Sur, Europa y exportadores del Golfo.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/por-que-qatar-no-puede-desviar-gnl-ormuz.html"><span class="home-analysis-label">GNL</span><h3>Por qué Catar no puede desviar fácilmente su GNL</h3><p>Geografía, metaneros, intercambios de cargamentos y límites físicos.</p><b>Leer análisis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/como-afecta-ormuz-espana-europa.html"><span class="home-analysis-label">España y Europa</span><h3>Cómo afectaría una crisis a España y Europa</h3><p>Petróleo, diésel, GNL, electricidad, reservas e inflación.</p><b>Leer análisis →</b></a>
  </div>
</section>
<!-- HOME_V11_ANALYSIS_END -->'''

ANALYSIS_EN = r'''<!-- HOME_V11_ANALYSIS_START -->
<section aria-labelledby="context-title" class="content-section home-analysis-v11">
  <div class="section-heading section-heading-v4">
    <div><span class="section-index">05</span><div><p class="section-kicker">Analysis and context</p><h2 id="context-title">Understand before concluding</h2></div></div>
    <a class="text-link" href="/en-analysis.html">View all analysis →</a>
  </div>
  <div class="home-analysis-grid-v11">
    <a class="home-analysis-card-v11" href="/en-what-does-closing-strait-of-hormuz-mean.html"><span class="home-analysis-label">Navigation</span><h3>What does it really mean for the strait to be closed?</h3><p>Threats, restrictions, partial disruption and effective closure.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11" href="/en-how-hormuz-closure-affects-oil-gas-economy.html"><span class="home-analysis-label">Energy</span><h3>How a closure would affect oil, gas and the economy</h3><p>Physical flows, LNG, freight, inflation and substitution limits.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11" href="/en-how-to-verify-operational-maritime-traffic-hormuz.html"><span class="home-analysis-label">AIS</span><h3>How to verify operational maritime traffic</h3><p>Completed tracks, official notices and coverage limitations.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11" href="/en-alternative-routes-strait-of-hormuz-closure-capacity.html"><span class="home-analysis-label">Infrastructure</span><h3>Which alternative routes exist and how much can they carry?</h3><p>Pipelines, ports, nameplate capacity and usable throughput.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/en-countries-most-dependent-on-strait-of-hormuz.html"><span class="home-analysis-label">Dependence</span><h3>Which countries depend most on the Strait of Hormuz?</h3><p>China, India, Japan, South Korea, Europe and Gulf exporters.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/en-why-qatar-cannot-reroute-lng-around-hormuz.html"><span class="home-analysis-label">LNG</span><h3>Why Qatar cannot easily reroute its LNG</h3><p>Geography, LNG carriers, cargo swaps and physical limits.</p><b>Read analysis →</b></a>
    <a class="home-analysis-card-v11 is-new" href="/en-how-hormuz-affects-spain-europe.html"><span class="home-analysis-label">Spain and Europe</span><h3>How a crisis would affect Spain and Europe</h3><p>Oil, diesel, LNG, electricity, emergency stocks and inflation.</p><b>Read analysis →</b></a>
  </div>
</section>
<!-- HOME_V11_ANALYSIS_END -->'''


def stable_write(path: Path, text: str) -> None:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous != text:
        path.write_text(text, encoding="utf-8")


def is_english(text: str) -> bool:
    return bool(re.search(r'<html\b[^>]*\blang=["\']en(?:-[^"\']+)?["\']', text, re.I))


def remove_panel_links(text: str) -> str:
    patterns = [
        r'\s*<a\b[^>]*href=["\']/panel-x\.html["\'][^>]*>.*?</a>',
        r'\s*<a\b[^>]*href=["\']https://estrechoormuz\.com/panel-x\.html["\'][^>]*>.*?</a>',
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.I | re.S)
    return text


def ensure_adsense_code(text: str) -> str:
    """Añade el código oficial de AdSense una sola vez dentro de <head>."""
    if re.search(r'pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js', text, re.I):
        return text

    meta = f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}">'
    additions = ADSENSE_SCRIPT
    if not re.search(r'<meta\b[^>]*name=["\']google-adsense-account["\']', text, re.I):
        additions = meta + "\n" + additions

    if re.search(r'</head>', text, re.I):
        return re.sub(r'</head>', additions + "\n</head>", text, count=1, flags=re.I)
    return text


def ensure_ads_txt() -> None:
    """Crea o completa ads.txt en la raíz sin borrar otros vendedores existentes."""
    path = ROOT / "ads.txt"
    required = f"google.com, {ADSENSE_PUBLISHER}, DIRECT, f08c47fec0942fa0"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line.rstrip() for line in current.splitlines() if line.strip()]
    if required not in lines:
        lines.append(required)
    stable_write(path, "\n".join(lines).rstrip() + "\n")


def ensure_css_link(text: str) -> str:
    if re.search(r'<link\b[^>]*href=["\']/v11\.css["\']', text, re.I):
        return text
    return text.replace("</head>", '<link href="/v11.css" rel="stylesheet"/>\n</head>', 1)


def patch_main_navigation(text: str, english: bool) -> str:
    target = "/en-daily-brief.html" if english else "/parte-diario.html"
    label = "Daily brief" if english else "Parte diario"
    history = "/en-history.html" if english else "/historial.html"

    pattern = re.compile(
        r'(<nav\b(?=[^>]*\bid=["\']site-nav["\'])[^>]*>)(.*?)(</nav>)',
        re.I | re.S,
    )

    def replace(match: re.Match[str]) -> str:
        inner = match.group(2)
        if re.search(rf'href=["\']{re.escape(target)}["\']', inner, re.I):
            return match.group(0)

        history_link = re.compile(
            rf'(<a\b[^>]*href=["\']{re.escape(history)}["\'][^>]*>.*?</a>)',
            re.I | re.S,
        )
        addition = rf'\1<a href="{target}">{label}</a>'
        if history_link.search(inner):
            inner = history_link.sub(addition, inner, count=1)
        else:
            inner += f'<a href="{target}">{label}</a>'
        return match.group(1) + inner + match.group(3)

    return pattern.sub(replace, text, count=1)


def patch_footer(text: str, english: bool) -> str:
    target = "/en-daily-brief.html" if english else "/parte-diario.html"
    label = "Daily brief" if english else "Parte diario"
    if re.search(rf'<footer\b.*?href=["\']{re.escape(target)}["\']', text, re.I | re.S):
        return text

    footer_start = text.lower().find("<footer")
    if footer_start < 0:
        return text

    head = text[:footer_start]
    footer = text[footer_start:]
    analysis_target = "/en-analysis.html" if english else "/analisis.html"
    link_pattern = re.compile(
        rf'(<a\b[^>]*href=["\']{re.escape(analysis_target)}["\'][^>]*>.*?</a>)',
        re.I | re.S,
    )
    if link_pattern.search(footer):
        footer = link_pattern.sub(rf'\1<a href="{target}">{label}</a>', footer, count=1)
    return head + footer


def remove_old_home_blocks(text: str) -> str:
    text = re.sub(
        r'<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->',
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<!-- HOME_V11_ANALYSIS_START -->.*?<!-- HOME_V11_ANALYSIS_END -->',
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<!-- V11_DAILY_BRIEF_TEASER -->\s*<section\b[^>]*>.*?</section>',
        "",
        text,
        flags=re.I | re.S,
    )
    return text


def replace_old_analysis(text: str, analysis_block: str) -> tuple[str, bool]:
    old = re.compile(
        r'<section\b(?=[^>]*aria-labelledby=["\']context-title["\'])(?=[^>]*class=["\'][^"\']*editorial-row[^"\']*["\'])[^>]*>.*?</section>',
        re.I | re.S,
    )
    if old.search(text):
        return old.sub(analysis_block, text, count=1), True
    return text, False


def patch_home(path: Path, english: bool) -> None:
    text = path.read_text(encoding="utf-8")
    text = remove_panel_links(text)
    text = remove_old_home_blocks(text)

    brief = BRIEF_EN if english else BRIEF_ES
    analysis = ANALYSIS_EN if english else ANALYSIS_ES

    text, replaced = replace_old_analysis(text, brief + "\n" + analysis)
    if not replaced:
        faq = re.search(
            r'<section\b(?=[^>]*aria-labelledby=["\']faq-title["\'])[^>]*>',
            text,
            re.I,
        )
        if faq:
            text = text[: faq.start()] + brief + "\n" + analysis + "\n" + text[faq.start() :]
        else:
            text = text.replace("</main>", brief + "\n" + analysis + "\n</main>", 1)

    stable_write(path, text)


def patch_article(path: Path, english: bool) -> None:
    text = path.read_text(encoding="utf-8")
    if "V11_EDITORIAL_TRANSPARENCY" in text or "</main>" not in text:
        return

    box = r'''<!-- V11_EDITORIAL_TRANSPARENCY -->
<section class="editorial-transparency">
  <span class="section-kicker">Editorial record</span><h2>Traceability and corrections</h2>
  <dl><dt>Author</dt><dd>Estrecho Ormuz Editorial Team</dd><dt>Review</dt><dd>Reviewed when operational evidence or source data materially changes.</dd><dt>Method</dt><dd>Facts, inferences and scenarios are separated. Primary sources are prioritised.</dd><dt>Corrections</dt><dd><a href="/en-contact.html">Send a documented correction</a>.</dd></dl>
  <div class="related-v11"><a href="/en-countries-most-dependent-on-strait-of-hormuz.html">Countries most exposed to Hormuz</a><a href="/en-why-qatar-cannot-reroute-lng-around-hormuz.html">Why Qatari LNG cannot bypass Hormuz</a><a href="/en-how-hormuz-affects-spain-europe.html">Impact on Spain and Europe</a></div>
</section>
''' if english else r'''<!-- V11_EDITORIAL_TRANSPARENCY -->
<section class="editorial-transparency">
  <span class="section-kicker">Ficha editorial</span><h2>Trazabilidad y correcciones</h2>
  <dl><dt>Autoría</dt><dd>Equipo editorial de Estrecho Ormuz</dd><dt>Revisión</dt><dd>Se revisa cuando cambian materialmente las evidencias operativas o los datos fuente.</dd><dt>Método</dt><dd>Se separan hechos, inferencias y escenarios. Se priorizan fuentes primarias.</dd><dt>Correcciones</dt><dd><a href="/contacto.html">Enviar una corrección documentada</a>.</dd></dl>
  <div class="related-v11"><a href="/paises-dependen-mas-estrecho-ormuz.html">Países más expuestos a Ormuz</a><a href="/por-que-qatar-no-puede-desviar-gnl-ormuz.html">Por qué el GNL catarí no puede evitar Ormuz</a><a href="/como-afecta-ormuz-espana-europa.html">Impacto en España y Europa</a></div>
</section>
'''
    stable_write(path, text.replace("</main>", box + "</main>", 1))


def patch_styles() -> None:
    path = ROOT / "v11.css"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    current = re.sub(
        r'/\* HOME_V11_2_START \*/.*?/\* HOME_V11_2_END \*/',
        "",
        current,
        flags=re.S,
    ).rstrip()
    stable_write(path, current + "\n\n" + CSS_BLOCK.strip() + "\n")


def update_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    blocks: list[str] = []
    for rel, freq, priority in NEW_URLS:
        absolute = f"https://estrechoormuz.com/{rel}"
        if absolute in text:
            continue
        blocks.append(
            "  <url>\n"
            f"    <loc>{absolute}</loc>\n"
            "    <lastmod>2026-07-17</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>\n"
        )
    if blocks and "</urlset>" in text:
        stable_write(path, text.replace("</urlset>", "".join(blocks) + "</urlset>", 1))


def update_text_files() -> None:
    robots = ROOT / "robots.txt"
    if robots.exists():
        lines = robots.read_text(encoding="utf-8").splitlines()
        lines = [line for line in lines if line.strip() != "Disallow: /panel-x.html"]
        stable_write(robots, "\n".join(lines).rstrip() + "\n")

    llms = ROOT / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        if "## V11 · partes y nuevos análisis" not in text:
            stable_write(
                llms,
                text.rstrip()
                + "\n\n## V11 · partes y nuevos análisis\n"
                "- Parte diario: https://estrechoormuz.com/parte-diario.html\n"
                "- Daily brief: https://estrechoormuz.com/en-daily-brief.html\n"
                "- Países más dependientes: https://estrechoormuz.com/paises-dependen-mas-estrecho-ormuz.html\n"
                "- GNL de Catar y Ormuz: https://estrechoormuz.com/por-que-qatar-no-puede-desviar-gnl-ormuz.html\n"
                "- España y Europa: https://estrechoormuz.com/como-afecta-ormuz-espana-europa.html\n",
            )


def remove_panel_page() -> None:
    panel = ROOT / "panel-x.html"
    if panel.exists():
        panel.unlink()

    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        text = re.sub(
            r'\s*<url>\s*<loc>https://estrechoormuz\.com/panel-x\.html</loc>.*?</url>',
            "",
            text,
            flags=re.I | re.S,
        )
        stable_write(sitemap, text)


def main() -> int:
    remove_panel_page()
    ensure_ads_txt()
    patch_styles()

    for path in ROOT.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        english = is_english(text)
        text = remove_panel_links(text)
        text = ensure_adsense_code(text)
        text = ensure_css_link(text)
        text = patch_main_navigation(text, english)
        text = patch_footer(text, english)
        stable_write(path, text)

    for name in ("index.html", "en.html"):
        path = ROOT / name
        if path.exists():
            patch_home(path, name == "en.html")

    for name in ARTICLES_ES:
        path = ROOT / name
        if path.exists():
            patch_article(path, False)

    for name in ARTICLES_EN:
        path = ROOT / name
        if path.exists():
            patch_article(path, True)

    update_sitemap()
    update_text_files()
    print("V11.3 instalada: contenido integrado, AdSense añadido a los HTML y ads.txt preparado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
