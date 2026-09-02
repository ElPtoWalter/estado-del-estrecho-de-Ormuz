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
        ("Puertos, comercio y geopolítica entre dos continentes." if other == "gibraltar" else "Tráfico, petróleo y claves del corredor del Golfo.")
        if es else
        ("Ports, trade and geopolitics between two continents." if other == "gibraltar" else "Shipping, oil and context for the Gulf corridor.")
    )
    label = "Publicidad propia · Otros proyectos" if es else "House promotion · Other projects"
    dv_copy = "Vuestras fotos y juegos, en una web privada." if es else "Your photos and games, in a private website."
    dv_cta = "Entrar en DespedidaVerse" if es else "Explore DespedidaVerse"
    other_cta = "Visitar el observatorio" if es else "Visit the observatory"
    disclosure = "Publicidad propia" if es else "House promotion"
    domain = "estrechogibraltar.com" if other == "gibraltar" else "estrechoormuz.com"
    topics = (("Tráfico y puertos", "Economía y rutas", "Geopolítica") if other == "gibraltar" else
              ("Tráfico marítimo", "Energía y rutas", "Fuentes y análisis")) if es else (
              ("Shipping and ports", "Economy and routes", "Geopolitics") if other == "gibraltar" else
              ("Maritime traffic", "Energy and routes", "Sources and analysis"))
    topic_rows = "".join(f'<span><b>0{n}</b>{topic}</span>' for n, topic in enumerate(topics, 1))
    return f'''<aside id="otros-proyectos" class="own-projects own-projects--{site}" data-own-projects aria-labelledby="own-projects-title">
<h2 id="own-projects-title" class="own-projects__label">{label}</h2>
<div class="own-projects__grid">
<a class="own-projects__card own-projects__card--verse" href="https://despedidaverse.com/" rel="sponsored">
<span class="own-projects__disclosure">{disclosure}<span aria-hidden="true">↗</span></span>
<div class="own-projects__window own-projects__window--verse">
<span class="own-projects__address">despedidaverse.com</span>
<img class="own-projects__logo" src="/own-projects-dv-logo.webp" alt="DespedidaVerse Studio" width="1600" height="400" decoding="async">
<strong class="own-projects__headline">{"Una despedida." if es else "One celebration."}<em>{"Todo un universo." if es else "A whole universe."}</em></strong>
<p class="own-projects__copy">{dv_copy}</p>
<span class="own-projects__preview"><img src="/own-projects-dv-preview.webp" alt="" width="958" height="759" decoding="async"></span>
<span class="own-projects__caption">{"Ejemplo real · Antonverse" if es else "Real example · Antonverse"}</span>
</div>
<span class="own-projects__cta">{dv_cta}<span aria-hidden="true"> →</span>{'<small lang="en">Spanish-language site</small>' if not es else ""}</span>
</a>
<a class="own-projects__card own-projects__card--strait own-projects__card--{other}" href="{escape(url, quote=True)}" rel="sponsored">
<span class="own-projects__disclosure">{disclosure}<span aria-hidden="true">↗</span></span>
<div class="own-projects__window own-projects__window--strait">
<span class="own-projects__address">{domain}</span>
<span class="own-projects__eyebrow">{"OBSERVATORIO INDEPENDIENTE" if es else "INDEPENDENT OBSERVATORY"}</span>
<strong class="own-projects__brand">{name}</strong>
<p class="own-projects__copy">{description}</p>
<span class="own-projects__topics">{topic_rows}</span>
<span class="own-projects__caption">{"El otro paso. Otra perspectiva." if es else "Another passage. Another perspective."}</span>
</div>
<span class="own-projects__cta">{other_cta}<span aria-hidden="true"> →</span></span>
</a>
</div></aside>'''


class PromotionPlacement(HTMLParser):
    """Find a complete introductory block; never split paragraphs or headings."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    IGNORED = {"script", "style", "nav", "aside", "form", "template", "noscript"}

    def __init__(self, document):
        super().__init__()
        self.document = document
        self.lines = [0]
        for line in document.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.stack = []
        self.blocks = []
        self.paragraphs = []

    def source_position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        parents = [frame["tag"] for frame in self.stack]
        inside = "main" in parents and not self.IGNORED.intersection(parents)
        if tag == "h1":
            for frame in self.stack:
                frame["heading"] = True
        self.stack.append({"tag": tag, "attrs": dict(attrs), "start": self.source_position(),
                           "inside": inside, "parent": parents[-1] if parents else "",
                           "words": 0, "heading": False})

    def handle_startendtag(self, tag, attrs):
        return

    def handle_data(self, data):
        if self.IGNORED.intersection(frame["tag"] for frame in self.stack):
            return
        words = len(re.findall(r"[^\W_]+", data))
        for frame in self.stack:
            frame["words"] += words

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack)-1, -1, -1) if self.stack[i]["tag"] == tag), None)
        if index is None:
            return
        frame = self.stack[index]
        del self.stack[index:]
        if not frame["inside"]:
            return
        frame["end"] = self.document.find(">", self.source_position()) + 1
        if tag in {"section", "header"} and frame["parent"] in {"main", "article"}:
            if frame["words"] >= 8 and (tag == "section" or frame["heading"]):
                self.blocks.append(frame)
        elif tag == "p" and frame["words"] >= 12 and frame["parent"] in {"main", "article"}:
            self.paragraphs.append(frame)


def mobile_position(document, path, site, fallback):
    placement = PromotionPlacement(document)
    placement.feed(document)
    blocks = sorted(placement.blocks, key=lambda frame: frame["start"])
    if path in HOME_PAGES:
        for frame in blocks:
            attrs = frame["attrs"]
            if (site == "ormuz" and attrs.get("id") in {"estado-actual", "current-status"}) or (
                    site == "gibraltar" and "gwc-status" in attrs.get("class", "").split()):
                return frame["end"]
    if blocks:
        return blocks[0]["end"]
    if placement.paragraphs:
        return min(placement.paragraphs, key=lambda frame: frame["start"])["end"]
    return fallback


def add_promotions(document, path, site):
    if "data-own-projects" in document or not eligible(document, path, site):
        return document
    main_end = list(re.finditer(r"</main\s*>", document, re.I))
    if not main_end or not re.search(r"</head\s*>", document, re.I):
        return document
    facts = PageFacts()
    facts.feed(document)
    end = main_end[-1].start()
    early = mobile_position(document, path, site, end)
    # One pair, already near the start without JavaScript. Desktop restores its
    # original end position; CSS alone continues to provide the wide side rails.
    start_marker = '<span id="projects-mobile-position" class="own-projects-anchor" hidden></span>'
    end_marker = '<span id="projects-desktop-position" class="own-projects-anchor" hidden></span>'
    block = start_marker + render_promotions(site, facts.lang) + "\n"
    document = document[:early] + block + document[early:end] + end_marker + document[end:]
    assets = ('<link rel="stylesheet" href="/own-projects.css?v=20260902-3">\n'
              '<script defer src="/own-projects.js?v=20260902-3"></script>\n</head>')
    return re.sub(r"</head\s*>", assets, document, count=1, flags=re.I)
