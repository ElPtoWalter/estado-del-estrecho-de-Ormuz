"""First-party cross-promotion. Static links; no ad network, cookies or tracking."""
from html import escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re

HOME_PAGES = {"index.html", "en.html"}
MIN_ARTICLE_WORDS = 350
ARTICLE_PAGES = {
    "ormuz": set("""
        alternativas-exportadores-golfo-capacidad-real.html auditoria-casos-reales-verificacion-ormuz.html
        como-afecta-ormuz-espana-europa.html como-afectaria-cierre-ormuz-petroleo-gas-economia.html
        como-comprobar-trafico-maritimo-operativo-ormuz.html datos-propios-monitor-ormuz.html
        guia-fuentes-maritimas-verificar-ormuz.html paises-dependen-mas-estrecho-ormuz.html
        por-que-qatar-no-puede-desviar-gnl-ormuz.html puede-estar-abierto-ormuz-aunque-caiga-trafico.html
        que-significa-cierre-estrecho-ormuz.html quien-controla-estrecho-ormuz-derecho-paso.html
        rutas-alternativas-cierre-estrecho-ormuz-capacidad.html seguros-maritimos-primas-guerra-ormuz.html
        senales-normalizacion-trafico-ormuz.html trafico-normal-estrecho-ormuz-cifras.html
        importancia.html en-importance.html
        en-alternative-routes-strait-of-hormuz-closure-capacity.html en-audit-real-hormuz-verification-errors.html
        en-can-hormuz-be-open-while-traffic-collapses.html en-countries-most-dependent-on-strait-of-hormuz.html
        en-gulf-exporters-hormuz-bypass-capacity.html en-how-hormuz-affects-spain-europe.html
        en-how-hormuz-closure-affects-oil-gas-economy.html en-how-much-energy-crosses-strait-of-hormuz.html
        en-how-to-verify-operational-maritime-traffic-hormuz.html en-marine-insurance-war-risk-premiums-hormuz.html
        en-maritime-sources-guide-verify-hormuz.html en-monitor-original-data-report.html
        en-signals-confirm-hormuz-traffic-normalisation.html en-what-does-closing-strait-of-hormuz-mean.html
        en-who-controls-strait-of-hormuz-transit-passage.html en-why-qatar-cannot-reroute-lng-around-hormuz.html
    """.split()),
    "gibraltar": set("""
        auditoria-datos-ope.html como-funciona-intercambio-agua-gibraltar.html
        impacto-cierre-gibraltar-comercio-europa-africa.html importancia.html
        por-que-45-mm-no-significa-cierre-gibraltar.html que-significaria-cierre-estrecho-gibraltar.html
        quien-controla-estrecho.html servicios-buques-estrecho-gibraltar.html
        ceuta-melilla.html escenarios.html espana-marruecos.html futuro.html geologia.html tunel.html
        en-ceuta-melilla.html en-scenarios.html en-spain-morocco.html en-future.html en-geology.html en-tunnel.html
        en-how-water-exchange-works-strait-of-gibraltar.html en-impact-gibraltar-closure-trade-europe-africa.html
        en-importance.html en-ship-services-strait-gibraltar.html en-what-would-closure-strait-of-gibraltar-mean.html
        en-who-controls-strait.html en-why-4-5-mm-does-not-mean-gibraltar-is-closing.html
    """.split()),
}


class PageFacts(HTMLParser):
    """Read paragraph text, excluding scripts, menus and non-editorial material."""
    def __init__(self):
        super().__init__()
        self.lang = "es"
        self.noindex = False
        self.redirect = False
        self.disabled_ads = False
        self.main = 0
        self.paragraph = 0
        self.ignored = 0
        self.words = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "es").split("-")[0].lower()
        if tag == "meta":
            name = attrs.get("name", "").lower()
            value = attrs.get("content", "").lower()
            self.noindex |= name in {"robots", "googlebot"} and "noindex" in value
            self.disabled_ads |= name == "publisher-ads" and value == "disabled"
            self.redirect |= attrs.get("http-equiv", "").lower() == "refresh"
        if tag == "main":
            self.main += 1
        if tag == "p":
            self.paragraph += 1
        if tag in {"script", "style", "nav", "footer", "aside", "form", "template", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag == "main":
            self.main = max(0, self.main - 1)
        if tag == "p":
            self.paragraph = max(0, self.paragraph - 1)
        if tag in {"script", "style", "nav", "footer", "aside", "form", "template", "noscript"}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if self.main and self.paragraph and not self.ignored:
            self.words.extend(re.findall(r"[^\W_]+", data))


def eligible(document, path, site):
    if site not in ARTICLE_PAGES:
        raise ValueError("Unknown site")
    path = str(PurePosixPath(path))
    if "/" in path or path not in HOME_PAGES | ARTICLE_PAGES[site]:
        return False
    facts = PageFacts()
    facts.feed(document)
    if facts.noindex or facts.redirect or facts.disabled_ads:
        return False
    return path in HOME_PAGES or len(facts.words) >= MIN_ARTICLE_WORDS


def render_promotions(site, lang):
    es = lang != "en"
    other = "gibraltar" if site == "ormuz" else "ormuz"
    name = ("Estrecho de Gibraltar" if other == "gibraltar" else "Estrecho de Ormuz") if es else ("Strait of Gibraltar" if other == "gibraltar" else "Strait of Hormuz")
    url = ("https://estrechogibraltar.com/" if other == "gibraltar" else "https://estrechoormuz.com/") + ("" if es else "en.html")
    description = (
        ("Tráfico marítimo, puertos y contexto entre el Atlántico y el Mediterráneo." if other == "gibraltar" else "Tráfico marítimo, energía y claves para entender el corredor del Golfo.")
        if es else
        ("Shipping, ports and context between the Atlantic and the Mediterranean." if other == "gibraltar" else "Shipping, energy and context for understanding the Gulf corridor.")
    )
    label = "Publicidad propia · Otros proyectos" if es else "House promotion · Other projects"
    dv_copy = "Una web privada para vuestra despedida, con fotos, mensajes y juegos a medida. Se abre desde un QR, sin instalar apps." if es else "A private website for your stag or hen party, with photos, messages and personalised games. Open it with a QR code, no app needed."
    dv_cta = "Descubrir DespedidaVerse" if es else "Explore DespedidaVerse"
    other_cta = "Visitar el observatorio" if es else "Visit the observatory"
    return f'''<aside id="otros-proyectos" class="own-projects own-projects--{site}" data-own-projects aria-labelledby="own-projects-title">
<h2 id="own-projects-title" class="own-projects__label">{label}</h2>
<div class="own-projects__grid">
<a class="own-projects__card own-projects__card--verse" href="https://despedidaverse.com/" rel="sponsored">
<span class="own-projects__eyebrow">{"EXPERIENCIAS PARA DESPEDIDAS" if es else "PERSONALISED PARTY EXPERIENCES"}</span>
<strong class="own-projects__brand">DespedidaVerse</strong>
<p class="own-projects__copy">{dv_copy}</p>
<span class="own-projects__cta">{dv_cta}<span aria-hidden="true"> →</span>{" · Spanish-language site" if not es else ""}</span>
</a>
<a class="own-projects__card own-projects__card--strait" href="{escape(url, quote=True)}" rel="sponsored">
<span class="own-projects__eyebrow">{"OTRO ESTRECHO, MÁS CONTEXTO" if es else "ANOTHER STRAIT, MORE CONTEXT"}</span>
<strong class="own-projects__brand">{name}</strong>
<p class="own-projects__copy">{description}</p>
<span class="own-projects__cta">{other_cta}<span aria-hidden="true"> →</span></span>
</a>
</div></aside>'''


def add_promotions(document, path, site):
    if "data-own-projects" in document or not eligible(document, path, site):
        return document
    main_end = list(re.finditer(r"</main\s*>", document, re.I))
    if not main_end or not re.search(r"</head\s*>", document, re.I):
        return document
    facts = PageFacts()
    facts.feed(document)
    position = main_end[-1].start()
    document = document[:position] + render_promotions(site, facts.lang) + "\n" + document[position:]
    return re.sub(r"</head\s*>", '<link rel="stylesheet" href="/own-projects.css?v=20260902-1">\n</head>', document, count=1, flags=re.I)
