"""Publication rules shared by human readers and crawlers; no cloaking."""
import re


def set_noindex(document):
    document = re.sub(r'<meta\b(?=[^>]*\bname=["\x27]robots["\x27])[^>]*>', "", document, flags=re.I)
    return re.sub(r"</head>", '<meta name="robots" content="noindex,follow"></head>', document, count=1, flags=re.I)


def without_ads(document):
    if 'name="publisher-ads"' not in document:
        document = re.sub(r"</head>", '<meta name="publisher-ads" content="disabled"></head>', document, count=1, flags=re.I)
    document = re.sub(r"<!-- ADSENSE[^>]*START -->.*?<!-- ADSENSE[^>]*END -->", "", document, flags=re.I | re.S)
    document = re.sub(r'<script\b[^>]*src=["\x27][^"\x27]*(?:pagead2\.googlesyndication\.com|googletagservices\.com)[^"\x27]*["\x27][^>]*>.*?</script>', "", document, flags=re.I | re.S)
    document = re.sub(r'<ins\b[^>]*class=["\x27][^"\x27]*adsbygoogle[^"\x27]*["\x27][^>]*>.*?</ins>', "", document, flags=re.I | re.S)
    return re.sub(r"<script\b[^>]*>\s*(?:\(adsbygoogle|window\.adsbygoogle).*?</script>", "", document, flags=re.I | re.S)


def apply_policy(document, path):
    path = str(path)
    name = path.rsplit("/", 1)[-1]
    digest = (path.startswith(("diario/", "diary/", "briefs/", "newsletter/"))
              or name in {"diario.html", "en-diary.html", "parte-diario.html", "en-daily-brief.html"}
              or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", name)))
    utility = name in {"404.html", "contacto.html", "en-contact.html", "privacidad.html", "en-privacy.html",
                       "cookies.html", "en-cookies.html", "aviso-legal.html", "en-legal.html",
                       "historial.html", "en-history.html", "evidencias.html", "en-evidence.html",
                       "alertas.html", "en-alerts.html", "embed.html", "en-embed.html",
                       "widget.html", "en-widget.html", "publicidad.html", "publicidad-y-patrocinios.html",
                       "media-kit.html", "en-media-kit.html"}
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
    if digest or utility or re.search(r'<meta\b[^>]*noindex', document, re.I):
        document = without_ads(document)
    return document
