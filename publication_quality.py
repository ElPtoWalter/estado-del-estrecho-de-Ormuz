"""Publication rules shared by human readers and crawlers; no cloaking."""
import re
import hashlib
import html
from datetime import datetime, timezone
from urllib.parse import urlsplit


# Individual decisions in docs/REVISION_32_URLS_2026-10-24.md.
# SEO choices are provisional without Search Console; useful resources stay indexable.
INDEXABLE_RESOURCES = {
    "metodologia.html", "en-methodology.html", "fuentes.html", "en-sources.html",
    "historial.html", "en-history.html", "evidencias.html", "en-evidence.html",
    "embed.html", "en-embed.html",
}
EDITORIAL_HOLDS = {
    "como-afecta-ormuz-espana-europa.html", "en-how-hormuz-affects-spain-europe.html",
}
EDITORIAL_NOTES = EDITORIAL_HOLDS | {
    "importancia.html", "en-importance.html",
    "puede-estar-abierto-ormuz-aunque-caiga-trafico.html", "en-can-hormuz-be-open-while-traffic-collapses.html",
}
HISTORY_ARTICLES = frozenset({
    "historiales-monitor-ormuz.html", "en-monitor-archives-hormuz.html",
})
HISTORY_REFERENCES = frozenset({
    "metodo-historiales-monitor-20261024.html", "en-monitor-archive-method-20261024.html",
    "archivo-monitor-20261024.html",
})
HISTORY_NO_ADS = HISTORY_ARTICLES | HISTORY_REFERENCES


def original_review_valid(document, review):
    """A named review authorizes only the exact original draft that was checked."""
    if not isinstance(review, dict) or review.get("kind") not in {"original_analysis", "reviewed_article"}:
        return False
    if not all(review.get(key) is True for key in ("facts_checked", "rights_checked", "approved")):
        return False
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        return False
    if not isinstance(review.get("original_contribution"), str) or len(review["original_contribution"].strip()) < 80:
        return False
    if review.get("sha256") != hashlib.sha256(document.encode("utf-8")).hexdigest():
        return False
    try:
        if not isinstance(review.get("reviewed_at"), str):
            return False
        reviewed_at = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None or reviewed_at > datetime.now(timezone.utc):
            return False
    except (KeyError, ValueError, TypeError):
        return False
    sources = review.get("sources")
    if not isinstance(sources, list) or not all(isinstance(url, str) for url in sources) or len(set(sources)) < 2:
        return False
    try:
        return all(urlsplit(url).scheme == "https" and urlsplit(url).netloc and url in document for url in sources)
    except ValueError:
        return False


def set_noindex(document):
    document = re.sub(r'<meta\b(?=[^>]*\bname=["\x27]robots["\x27])[^>]*>', "", document, flags=re.I)
    return re.sub(r"</head>", '<meta name="robots" content="noindex,follow"></head>', document, count=1, flags=re.I)


def without_ads(document, *, block_house_promotions=True):
    if 'name="publisher-ads"' not in document:
        mode = "disabled" if block_house_promotions else "programmatic-disabled"
        document = re.sub(r"</head>", f'<meta name="publisher-ads" content="{mode}"></head>', document, count=1, flags=re.I)
    document = re.sub(r"<!-- ADSENSE[^>]*START -->.*?<!-- ADSENSE[^>]*END -->", "", document, flags=re.I | re.S)
    document = re.sub(r'<script\b[^>]*src=["\x27][^"\x27]*(?:pagead2\.googlesyndication\.com|googletagservices\.com)[^"\x27]*["\x27][^>]*>.*?</script>', "", document, flags=re.I | re.S)
    document = re.sub(r'<ins\b[^>]*class=["\x27][^"\x27]*adsbygoogle[^"\x27]*["\x27][^>]*>.*?</ins>', "", document, flags=re.I | re.S)
    return re.sub(r"<script\b[^>]*>\s*(?:\(adsbygoogle|window\.adsbygoogle).*?</script>", "", document, flags=re.I | re.S)


def ads_authorized(settings):
    """Account-side checks are explicit owner attestations, never a local approval score."""
    ads = settings.get("adsense", {}) if isinstance(settings, dict) else {}
    if not isinstance(ads, dict):
        return False
    return all(ads.get(key) is True for key in (
        "enabled", "account_ready", "cmp_verified", "publisher_identity_complete",
    ))


def approved_history_notices(document, es):
    """Called only after the exact document's editorial review passes the real gate."""
    neutral = ("Preparación con asistencia de IA · Datos propios · Sin publicidad" if es else
               "Prepared with AI assistance · Original project data · Advertising disabled")
    document = re.sub(r'<p\b[^>]*\bdata-draft-disclosure[^>]*>.*?</p>',
                      lambda m: '<p class="source-note">'+neutral+'</p>', document, flags=re.I | re.S)
    document = re.sub(r'<p\b[^>]*\bdata-editorial-approval-pending[^>]*>.*?</p>', '', document, flags=re.I | re.S)
    document = re.sub(r'<p\b[^>]*\bdata-history-publication-status[^>]*>.*?</p>',
                      lambda m: '<p>ESTRECHO ORMUZ · '+neutral+'</p>', document, flags=re.I | re.S)
    # Resource provenance remains; only its pending-authorization notice changes.
    resource = ("Metadatos de decisiones y gráficos elaborados por el proyecto. Las fuentes, la versión y la atribución se documentan aquí. El archivo excluye posiciones AIS y textos de medios." if es else
                "Decision metadata and charts prepared by the project. Sources, version and attribution are documented here. The archive excludes AIS positions and media article bodies.")
    return re.sub(r'<p\b[^>]*\bdata-resource-publication-pending[^>]*>.*?</p>',
                  lambda m: '<p>'+resource+'</p>', document, flags=re.I | re.S)


def apply_policy(document, path, *, programmatic_ads=False, review=None):
    reviewed_original = original_review_valid(document, review)
    path = str(path).replace("\\", "/")
    name = path.rsplit("/", 1)[-1]
    digest = (path.startswith(("diario/", "diary/", "briefs/", "newsletter/"))
              or name in {"diario.html", "en-diary.html", "parte-diario.html", "en-daily-brief.html"}
              or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", name)))
    utility = name in {"404.html", "contacto.html", "en-contact.html", "privacidad.html", "en-privacy.html",
                       "cookies.html", "en-cookies.html", "aviso-legal.html", "en-legal.html",
                       "historial.html", "en-history.html", "evidencias.html", "en-evidence.html",
                       "alertas.html", "en-alerts.html", "embed.html", "en-embed.html",
                       "widget.html", "en-widget.html", "publicidad.html", "en-advertising.html", "publicidad-y-patrocinios.html",
                       "media-kit.html", "en-media-kit.html", "metodologia.html", "en-methodology.html",
                       "fuentes.html", "en-sources.html"}
    es = not re.search(r'<html\b[^>]*lang=["\x27]en', document, re.I)
    if not reviewed_original:
        # A date stamped by an old generator is not evidence of human review.
        document = document.replace(
            "Revisión documental realizada el 4 de agosto de 2026. Se actualiza si cambian los datos fuente.",
            "Texto fechado el 4 de agosto de 2026; no consta una revisión humana individual acreditada.")
        document = document.replace(
            "Document review completed on 4 August 2026. Updated when source data materially change.",
            "Text dated 4 August 2026; no individual human review is documented.")
    if utility and name not in INDEXABLE_RESOURCES:
        document = set_noindex(document)
    if name in EDITORIAL_HOLDS and not reviewed_original:
        document = set_noindex(document)
    if name in EDITORIAL_NOTES and not reviewed_original:
        note = ("Contexto pendiente de actualización editorial. No describe por sí solo la situación actual "
                "ni acredita una revisión humana individual. Consulta el monitor y las fuentes fechadas." if es else
                "Context awaiting an editorial update. It does not establish current conditions or an individual "
                "human review. Consult the monitor and dated sources.")
        if 'data-editorial-hold' not in document:
            document = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + '<aside data-editorial-hold role="note">' + note + '</aside>', document, count=1, flags=re.I)
    if digest:
        document = set_noindex(document)
        if 'data-editorial-disclosure' not in document:
            es = not re.search(r'<html\b[^>]*lang=["\x27]en', document, re.I)
            note = ("Parte de seguimiento automatizado, no reportaje con verificación humana individual. "
                    "Las ediciones antiguas conservan su contexto y pueden contener criterios ya corregidos. "
                    "Las fechas de los feeds no acreditan por sí solas la fecha de los hechos." if es else
                    "Automated monitoring digest, not individually human-verified reporting. "
                    "Older editions preserve their context and may contain criteria since corrected. "
                    "Feed dates alone do not establish when events occurred.")
            document = re.sub(r"(<main\b[^>]*>)", lambda m: m[1] + '<aside data-editorial-disclosure role="note" style="padding:1rem;border:1px solid #888;margin-bottom:1rem">' + note + '</aside>', document, count=1, flags=re.I)
    original_draft = bool(re.search(r'<meta\b(?=[^>]*name=["\x27]content-kind["\x27])(?=[^>]*content=["\x27]original-draft["\x27])[^>]*>', document, re.I))
    original_draft = original_draft or name in HISTORY_NO_ADS
    if original_draft and not digest:
        if reviewed_original:
            if name in HISTORY_NO_ADS:
                document = approved_history_notices(document, es)
            document = re.sub(r'<meta\b(?=[^>]*\bname=["\x27]robots["\x27])[^>]*>', "", document, flags=re.I)
            document = re.sub(r'</head>', '<meta name="robots" content="index,follow,max-image-preview:large"></head>', document, count=1, flags=re.I)
            es = not re.search(r'<html\b[^>]*lang=["\x27]en', document, re.I)
            label = ("Análisis original · revisión editorial" if review['kind'] == 'original_analysis' else "Artículo revisado y autorizado") if es else ("Original analysis · editorial review" if review['kind'] == 'original_analysis' else "Reviewed and authorized article")
            note = f'<aside data-original-review role="note">{label}: {html.escape(review["reviewer"])} · {html.escape(review["reviewed_at"])}</aside>'
            document = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + note, document, count=1, flags=re.I)
        else:
            document = set_noindex(document)
            if 'data-draft-disclosure' not in document:
                note = ("Borrador de análisis original · pendiente de revisión editorial humana. "
                        "Los cálculos automáticos no certifican los hechos marítimos." if es else
                        "Original analysis draft · pending human editorial review. "
                        "Automated calculations do not certify maritime events.")
                document = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + '<aside data-draft-disclosure role="note">' + note + '</aside>', document, count=1, flags=re.I)
    # A real editorial review never makes these three support resources indexable.
    if name in HISTORY_REFERENCES:
        document = set_noindex(document)
    if name in HISTORY_NO_ADS:
        document = re.sub(r'<meta\b(?=[^>]*\bname=["\x27]publisher-ads["\x27])[^>]*>', '', document, flags=re.I)
    block_all_ads = bool(name in HISTORY_NO_ADS or digest or utility or re.search(r'<meta\b[^>]*noindex', document, re.I))
    if not programmatic_ads or block_all_ads:
        document = without_ads(document, block_house_promotions=block_all_ads)
    return document
