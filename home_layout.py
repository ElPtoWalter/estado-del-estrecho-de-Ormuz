"""A compact reading order for ES/EN home pages; assessment and articles are untouched."""
from pathlib import Path
import re
from seo_surface import Regions

STYLE = r"""
.home-v4 .home-recent,.home-v4 .home-assessment-details{border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.02);margin:1.25rem 0;padding:0 1.1rem}
.home-v4 .home-recent>summary,.home-v4 .home-assessment-details>summary{cursor:pointer;min-height:48px;padding:1rem 0;font-weight:750;line-height:1.5;color:var(--text)}
.home-v4 summary:focus-visible,.home-v4 a:focus-visible,.home-v4 button:focus-visible{outline:3px solid #82d6e4;outline-offset:4px}
.home-v4 .home-recent .split-section{margin-top:.5rem}.home-v4 .home-recent .section-index{display:none}
.home-v4 .home-assessment-details .opintel-v7{margin:0 0 1rem;padding:1rem}
.home-v4 .home-assessment-details .opintel-head p{max-width:68ch}
.home-v4 .status-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));text-align:left}
.home-v4 .status-facts>div{padding:1rem;min-width:0}.home-v4 .status-facts strong{font-size:1rem!important;line-height:1.5}
.home-v4 .observatory-dimensions{margin:1rem 0;padding:1rem;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.025)}
.home-v4 .status-hero .observatory-dimensions{display:none}
.home-v4 .journal-home-v8{margin:1.5rem 0}
.home-v4 .seo-research{margin-top:1.5rem}
.home-v4 .home-analysis-v11 .analysis-card{min-width:0}
@media(max-width:760px){
 .home-v4 .status-facts{grid-template-columns:1fr 1fr;gap:.5rem}
 .home-v4 .status-facts>div:first-child{grid-column:1/-1}
 .home-v4 .status-facts>div{padding:.8rem;border:1px solid var(--line);border-radius:10px}
 .home-v4 .observatory-dimensions{gap:.8rem;padding:.9rem}
 .home-v4 .home-assessment-details,.home-v4 .home-recent{padding:0 .8rem}
 .home-v4 .hero-v4 h1{font-size:clamp(1.75rem,7vw,2.4rem);line-height:1.12}
 .home-v4 .evidence-grid{gap:.7rem}.home-v4 .evidence-card{padding:1rem}
 .home-v4 .journal-home-v8 h2{font-size:1.9rem;line-height:1.12}
 .home-v4 .content-section{margin-top:1.4rem}
}
"""


def transform(document, name):
    if name not in {"index.html", "en.html"} or "data-home-layout" in document:
        return document
    es = name == "index.html"
    scope = re.search(r'<p class="seo-scope-note" data-seo-scope>.*?</p>',document,re.S)
    if scope:
        title = "Sin recuento AIS propio · límites del monitor" if es else "No in-house AIS count · monitor limits"
        document = document[:scope.start()] + '<details class="home-scope"><summary>'+title+'</summary>'+scope[0]+'</details>' + document[scope.end():]
    # Extract balanced existing sections; nested content and fragment anchors survive.
    regions = Regions(document).nodes
    recent = next(((a,b) for a,b,tag,attrs in regions if tag=="section"
                   and "split-section" in attrs.get("class","").split()
                   and 'id="recentHistory"' in document[a:b]), None)
    if recent:
        a,b = recent
        content = document[a:b]
        document = document[:a] + document[b:]
        title = "Cambios recientes del monitor V7" if es else "Recent V7 monitor changes"
        block = '<details class="home-recent" data-home-recent><summary>' + title + '</summary>' + content + '</details>'
        document = document.replace('<div class="evidence-section">',block+'<div class="evidence-section">',1)
    # One visible verdict and four dimensions; the complete explanation remains reachable.
    pattern = re.compile(r'(<!-- OPERATIONAL_INTELLIGENCE_V7_START -->.*?<!-- OPERATIONAL_INTELLIGENCE_V7_END -->)',re.S)
    summary = "Desglose y evidencias del diagnóstico V7" if es else "V7 assessment breakdown and evidence"
    document = pattern.sub(lambda m:'<details class="home-assessment-details" data-home-assessment><summary>'+summary+'</summary>'+m[1]+'</details>',document,count=1)
    # Put confidence/verification before dimensions, keeping their original text.
    dimensions = re.search(r'<dl class="observatory-dimensions">.*?</dl>',document,re.S)
    if dimensions:
        block = dimensions[0]
        document = document[:dimensions.start()]+document[dimensions.end():]
        # The freshness note follows the facts; insert the four dimensions immediately before it.
        marker = '<p class="observatory-freshness'
        document = document.replace(marker,block+marker,1)
    # Place the dated daily before research, without changing either content.
    journal = re.search(r'<!-- JOURNAL_V8_HOME_START -->.*?<!-- JOURNAL_V8_HOME_END -->',document,re.S)
    if journal:
        block = journal[0]
        document = document[:journal.start()]+document[journal.end():]
        research = next(((a,b) for a,b,tag,attrs in Regions(document).nodes if "data-seo-research" in attrs),None)
        if research:
            pos=research[0]
            document=document[:pos]+block+document[pos:]
        else:
            raise ValueError("Missing research insertion point")
    document = document.replace("</head>",'<style data-home-layout>'+STYLE+'</style></head>',1)
    return document


def publish(root):
    for name in ("index.html","en.html"):
        path=Path(root)/name
        path.write_text(transform(path.read_text(encoding="utf-8"),name),encoding="utf-8",newline="\n")
