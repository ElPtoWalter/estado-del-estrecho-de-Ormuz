"""Conservative headline handling. No article-body or live-traffic claims."""
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def classify_headline(title):
    # Subject first: an oil-price story about strikes is still a market story.
    if re.search(r"^(?:oil|crude|brent|wti|gas|petróleo|crudo)\b", title, re.I):
        return "energy"
    patterns = (
        ("insurance", r"\b(?:insurance|premium|premiums|freight|seguros?|fletes?)\b|war risk"),
        ("security", r"\b(?:attack\w*|strike[sd]?|struck|missiles?|drones?|explosion\w*|ataques?|bombarde\w*|mines)\b"),
        ("diplomacy", r"\b(?:talks?|negotiat\w*|ceasefire|agreement|diplomac\w*|negoci\w*|acuerdo\w*|tregua)\b"),
        ("maritime", r"\b(?:shipping|ships?|vessels?|tankers?|transit\w*|traffic|cross\w*|ports?|buques?|tráfico|navegación)\b"),
        ("energy", r"\b(?:oil|crude|brent|wti|lng|energy|barrels?|petróleo|gas)\b"),
        ("security", r"\b(?:jmic|ukmto|advisory|navy|escort|security)\b"),
    )
    return next((topic for topic, pattern in patterns if re.search(pattern, title, re.I)), "other")


def identity(url, title, source):
    parsed = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.startswith("utm_") and k not in {"oc", "fbclid", "gclid"}]
    canonical = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urlencode(query), ""))
    raw = canonical or f"{source.casefold()}|{re.sub(r'\W+', ' ', title.casefold()).strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


READING = {
    "es": {
        "security": "La información de seguridad no demuestra por sí sola una interrupción del paso: falta vincular el incidente a una ruta, una hora y una restricción verificable. Un ataque en territorio iraní y un ataque a un buque son hechos distintos.",
        "energy": "Una variación del precio del petróleo mide expectativas de mercado, no buques detenidos. Para atribuirla a una pérdida de suministro harían falta volúmenes exportados y un periodo de comparación; los titulares enlazados no bastan para calcularlos.",
        "diplomacy": "El anuncio de conversaciones o acuerdos no equivale a su aplicación. La comprobación relevante es si existe una medida en vigor con fecha, ámbito y condiciones de paso, y después si el tránsito la refleja.",
        "maritime": "Un cruce individual no permite estimar el volumen total ni declarar normalidad. Hacen falta hora del tránsito, tipo de buque, cobertura de la observación y una base comparable; una caída del número de señales AIS tampoco equivale automáticamente a un cierre.",
        "insurance": "Una noticia sobre seguros o fletes no permite calcular un coste universal. La comparación requiere ruta, tipo de buque, periodo de cobertura y base de la prima. Un encarecimiento comercial no demuestra que el paso físico esté bloqueado.",
        "other": "El titular se conserva como referencia, sin extraer de él una conclusión operativa que no esté documentada.",
    },
    "en": {
        "security": "Security reporting alone does not establish a disruption of passage. The incident must be tied to a route, time and verifiable restriction. An attack on Iranian territory and an attack on a vessel are different events.",
        "energy": "An oil-price move measures market expectations, not stopped vessels. Attributing it to lost supply requires export volumes and a comparison period; the linked headlines are not enough to calculate either.",
        "diplomacy": "Announced talks or agreements are not implementation. The relevant check is an effective measure with a date, scope and passage conditions, followed by evidence of traffic reflecting it.",
        "maritime": "One crossing cannot establish total volume or normality. Transit time, vessel type, observation coverage and a comparable baseline are needed. Fewer AIS signals do not automatically mean closure.",
        "insurance": "Insurance or freight reporting does not establish a universal cost. Comparisons require route, vessel type, coverage period and premium basis. Higher commercial costs do not prove physical blockage.",
        "other": "The headline is retained as a reference without deriving an undocumented operational conclusion.",
    },
}


def reading(topic, lang):
    return READING[lang].get(topic, READING[lang]["other"])


def section_note(topic, items, lang):
    relevant = [item for item in items if item.topic == topic][:2]
    if not relevant:
        return "Sin titulares seleccionados en este ámbito; no se añade una conclusión nueva." if lang == "es" else "No selected headlines in this area; no new conclusion is added."
    sources = ", ".join(dict.fromkeys(item.source for item in relevant))
    prefix = (f"Referencias de esta sección: {sources}. " if lang == "es" else f"References in this section: {sources}. ")
    return prefix + reading(topic, lang)
