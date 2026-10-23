"""Publication rules shared by human readers and crawlers; no cloaking."""
import re
import hashlib
import html
from datetime import datetime, timezone
from urllib.parse import urlsplit


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
    if original_draft and not digest:
        if reviewed_original:
            document = re.sub(r'<meta\b(?=[^>]*\bname=["\x27]robots["\x27])[^>]*>', "", document, flags=re.I)
            document = re.sub(r'</head>', '<meta name="robots" content="index,follow,max-image-preview:large"></head>', document, count=1, flags=re.I)
            es = not re.search(r'<html\b[^>]*lang=["\x27]en', document, re.I)
            label = ("Análisis original · revisión editorial" if review['kind'] == 'original_analysis' else "Artículo revisado y autorizado") if es else ("Original analysis · editorial review" if review['kind'] == 'original_analysis' else "Reviewed and authorized article")
            note = f'<aside data-original-review role="note">{label}: {html.escape(review["reviewer"])} · {html.escape(review["reviewed_at"])}</aside>'
            document = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + note, document, count=1, flags=re.I)
        else:
            document = set_noindex(document)
    block_all_ads = bool(digest or utility or re.search(r'<meta\b[^>]*noindex', document, re.I))
    if not programmatic_ads or block_all_ads:
        document = without_ads(document, block_house_promotions=block_all_ads)
    return document
