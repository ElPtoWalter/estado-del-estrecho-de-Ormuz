"""Conservative headline handling. No article-body or live-traffic claims."""
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Lexical translations of a supplied headline, not additional reporting.
# The first matching concrete subject is a minimum grounding check, not NLI.
HEADLINE_ANCHORS = (
    (r'\boil spill\b', ('vertido', 'derrame', 'oil spill')),
    (r'\bengine rooms?\b', ('sala de máquinas', 'salas de máquinas', 'motores', 'engine room')),
    (r'\bBrent\b', ('Brent',)),
    (r'\bimports?\b', ('importaciones', 'imports')),
    (r'\bceasefire\b', ('alto el fuego', 'tregua', 'ceasefire')),
    (r'\bblockade\b', ('bloqueo', 'blockade')),
    (r'\btankers?\b', ('petrolero', 'petroleros', 'tanker', 'tankers')),
    (r'\bships?\b|\bvessels?\b', ('buque', 'buques', 'barco', 'barcos', 'ship', 'ships', 'vessel', 'vessels')),
)


def headline_grounding(title):
    anchors = next((list(names) for pattern, names in HEADLINE_ANCHORS if re.search(pattern, title, re.I)), [])
    declaration = bool(re.search(r'\bIran(?:\x27s [\w ]+)? (?:says|warns|claims|urges)\b', title, re.I))
    return {'anchors': anchors, 'iran_declaration': declaration}


def primary_context(root, edition_date):
    """Reviewed, dated factual paraphrases; never scrape or trust arbitrary URLs."""
    try:
        data = json.loads((root / 'editorial-context.json').read_text(encoding='utf-8'))
        reviewed = date.fromisoformat(data['reviewed_at'])
        if reviewed > edition_date:
            return []
    except (OSError, ValueError, KeyError, TypeError):
        return []
    output = []
    for item in data.get('items', []):
        if not isinstance(item, dict):
            continue
        try:
            published = date.fromisoformat(item['published_at'])
            period = int(item['reference_period'])
            if published > reviewed or period > published.year:
                continue
        except (KeyError, ValueError, TypeError):
            continue
        if (item.get('kind') != 'historical_context' or item.get('rights') != 'US-government-authored-text'
                or item.get('source') != 'EIA'
                or item.get('url') != 'https://www.eia.gov/todayinenergy/detail.php?id=65504'
                or item.get('rights_url') != 'https://www.eia.gov/about/copyrights_reuse.php'):
            continue
        if not all(isinstance(item.get(key), str) and 20 <= len(item[key]) <= 600
                   for key in ('fact_es', 'fact_en', 'limit_es', 'limit_en')):
            continue
        content = {key: value for key, value in item.items() if key != 'review_sha256'}
        digest = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        if item.get('review_sha256') != digest:
            continue
        output.append({**item, 'reviewed_at': data['reviewed_at']})
    return output[:3]


def classify_headline(title):
    if re.search(r'\boil spill\b|\bvertido\b|\bderrame\b', title, re.I):
        return 'maritime'
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
    relevant = [item for item in items if item.topic == topic and not item.analytical and item.tier >= 3][:2]
    if not relevant:
        return "Sin titulares seleccionados en este ámbito; no se añade una conclusión nueva." if lang == "es" else "No selected headlines in this area; no new conclusion is added."
    sources = ", ".join(dict.fromkeys(item.source for item in relevant))
    prefix = (f"Referencias de esta sección: {sources}. " if lang == "es" else f"References in this section: {sources}. ")
    return prefix + reading(topic, lang)
