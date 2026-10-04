"""Local factual and structural validators for packages and scripts."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from .rules import load_rules
from .schema import (
    ASSET_TYPES,
    CONFIDENCE_VALUES,
    HEALTH_VALUES,
    PACKAGE_KEYS,
    PACKAGE_SCHEMA_VERSION,
    SCENE_KEYS,
    SCRIPT_KEYS,
    SCRIPT_SCHEMA_VERSION,
    VALIDATOR_VERSION,
    VERIFIED_STATUSES,
    VIDEO_TYPES,
    VISUAL_INTENTS,
    package_content_hash,
    package_id,
    parse_utc,
    script_id,
)


_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?%?(?![\w])")
_DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"\d{1,2}\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|"
    r"july|august|september|october|november|december)\s+(?:de\s+)?\d{4})\b",
    re.I,
)
_URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.I)
_HTML_RE = re.compile(r"<\s*/?\s*[a-z][^>]*>|javascript\s*:", re.I)
_INJECTION_RE = re.compile(
    r"\b(?:ignore (?:all |the |any )?(?:previous |prior )?instructions|"
    r"ignora (?:todas? )?(?:las )?instrucciones|system prompt|developer message|"
    r"reveal (?:the )?(?:secret|key|prompt)|disclose (?:secrets?|credentials?)|"
    r"muestra (?:la )?(?:clave|contraseña|prompt))\b",
    re.I,
)
_SENSATIONAL_RE = re.compile(
    r"(?:¡|\b)(?:crisis hist[oó]rica|cat[aá]strofe total|caos absoluto|fin del mundo|"
    r"world[- ]?ending|historic catastrophe|absolute chaos|you won'?t believe|"
    r"no te lo vas a creer|impactante revelaci[oó]n)(?:!|\b)",
    re.I,
)
_ATTRIBUTION_RE = re.compile(
    r"\b(?:seg[uú]n|afirma|afirm[oó]|dice|dijo|declara|declar[oó]|advierte|"
    r"according to|says?|said|states?|stated|warns?|warned|claims?|claimed)\b",
    re.I,
)
_WORD_RE = re.compile(r"\b[\wáéíóúüñ'-]+\b", re.I)
_ENTITY_RE = re.compile(
    r"\b(?:[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ&.'’-]{2,}|[A-Z]{2,})"
    r"(?:\s+(?:(?:de|del|la|el|of|the|and|&|al)\s+)?"
    r"(?:[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ&.'’-]{1,}|[A-Z]{2,})){0,5}\b"
)
_GENERIC_ENTITIES = {
    "ahora", "así", "breaking", "cada", "confianza", "contexto", "daily summary",
    "durante", "el estado", "en resumen", "estas", "este", "estos", "explainer",
    "esta", "esto", "frente", "fuentes", "hoy", "la situación", "lo confirmado",
    "local", "mañana", "mapa", "mientras", "nuestro", "para", "por ahora",
    "seguimos", "straitwatch", "vigilaremos", "fase uno", "phase one",
}
_CONTRADICTION_PAIRS = (
    (("daños menores", "minor damage", "damaged"), ("destruido", "destroyed", "total loss")),
    (("abierto", "open", "operativo", "operational"), ("cerrado", "closed", "closure")),
    (("aument", "increase", "rise"), ("redu", "decrease", "fall")),
    (("sin confirmar", "unconfirmed", "unknown"), ("confirmado", "confirmed", "certain")),
)


def _report(kind: str, identity: str, errors: Iterable[str], **extra: Any) -> dict[str, Any]:
    ordered = list(dict.fromkeys(errors))
    return {
        "validator_version": VALIDATOR_VERSION,
        f"{kind}_id": identity,
        "validation_status": "PASS" if not ordered else "FAIL",
        "validation_errors": ordered,
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        **extra,
    }


def _is_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _future(value: Any, now: datetime, tolerance: timedelta) -> bool:
    try:
        return parse_utc(value) > now + tolerance
    except (TypeError, ValueError):
        return True


def validate_package(
    package: Any,
    *,
    now: datetime | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(package, dict):
        return _report("package", "", ["PACKAGE_SCHEMA"])
    identity = str(package.get("package_id") or "")
    if set(package) != PACKAGE_KEYS or package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        errors.append("PACKAGE_SCHEMA")
    config = rules or load_rules()
    moment = now or datetime.now(timezone.utc)
    tolerance = timedelta(seconds=int(config["freshness"]["future_tolerance_seconds"]))

    digest = str(package.get("content_hash") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != package_content_hash(package):
        errors.append("CONTENT_HASH_MISMATCH")
    try:
        expected_id = package_id(str(package.get("site")), str(package.get("edition_date")), digest)
    except (TypeError, ValueError):
        expected_id = ""
    if identity != expected_id:
        errors.append("PACKAGE_ID_MISMATCH")

    if package.get("language_set") != ["es", "en"]:
        errors.append("LANGUAGE_SET")
    if package.get("content_kind") not in {"event", "daily_summary"}:
        errors.append("CONTENT_KIND")
    if package.get("content_kind") == "event" and not package.get("event_id"):
        errors.append("EVENT_ID")
    if package.get("content_kind") == "daily_summary" and package.get("event_id") is not None:
        errors.append("EVENT_ID")
    if not isinstance(package.get("importance"), int) or isinstance(package.get("importance"), bool) or not 0 <= package.get("importance", -1) <= 100:
        errors.append("IMPORTANCE")
    for key in ("generated_at",):
        if _future(package.get(key), moment, tolerance):
            errors.append("FUTURE_DATE")
    try:
        if datetime.fromisoformat(str(package.get("edition_date"))).date().isoformat() != package.get("edition_date"):
            errors.append("EDITION_DATE")
    except (TypeError, ValueError):
        errors.append("EDITION_DATE")

    recommendation = package.get("video_recommendation")
    if not isinstance(recommendation, dict) or set(recommendation) != {
        "rule_id", "reason_codes", "decided_by", "human_review_required"
    }:
        errors.append("VIDEO_RECOMMENDATION_SCHEMA")
    else:
        if recommendation.get("rule_id") != config["rule_id"] or recommendation.get("decided_by") != "deterministic_rules":
            errors.append("VIDEO_RECOMMENDATION_RULE")
        if recommendation.get("human_review_required") is not True:
            errors.append("HUMAN_REVIEW_REQUIRED")
        if not isinstance(recommendation.get("reason_codes"), list) or not all(isinstance(item, str) and item for item in recommendation.get("reason_codes", [])):
            errors.append("REASON_CODES")
    recommended = package.get("video_recommended")
    if not isinstance(recommended, bool):
        errors.append("VIDEO_RECOMMENDED")
    if recommended and package.get("video_type") not in VIDEO_TYPES:
        errors.append("VIDEO_TYPE")
    if not recommended and package.get("video_type") is not None:
        errors.append("VIDEO_TYPE")

    headlines = package.get("headlines")
    if not isinstance(headlines, dict) or set(headlines) != {"es", "en"} or not all(isinstance(headlines.get(lang), str) and headlines.get(lang).strip() for lang in ("es", "en")):
        errors.append("HEADLINES")

    source_rows = package.get("sources") if isinstance(package.get("sources"), list) else []
    source_ids: set[str] = set()
    for source in source_rows:
        if not isinstance(source, dict) or set(source) != {
            "source_id", "canonical_name", "url", "published_at", "tier", "official", "rights_status"
        }:
            errors.append("SOURCE_SCHEMA")
            continue
        source_id_value = str(source.get("source_id") or "")
        if not source_id_value or source_id_value in source_ids:
            errors.append("SOURCE_ID")
        source_ids.add(source_id_value)
        if not source.get("canonical_name") or not _is_url(source.get("url")):
            errors.append("SOURCE_TRACEABILITY")
        if source.get("tier") not in {"primary", "official", "trusted_media", "secondary"}:
            errors.append("SOURCE_TIER")
        if source.get("rights_status") != "link_and_factual_reference_only":
            errors.append("SOURCE_RIGHTS")
        if _future(source.get("published_at"), moment, tolerance):
            errors.append("FUTURE_DATE")
        if re.search(r"(?:api[_-]?key|token|secret|password)=", str(source.get("url") or ""), re.I):
            errors.append("SECRET_IN_URL")

    facts = package.get("verified_facts") if isinstance(package.get("verified_facts"), list) else []
    fact_ids: set[str] = set()
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {
            "fact_id", "text_es", "text_en", "event_id", "verification_status", "source_ids", "observed_at"
        }:
            errors.append("FACT_SCHEMA")
            continue
        fact_id_value = str(fact.get("fact_id") or "")
        if not fact_id_value or fact_id_value in fact_ids:
            errors.append("FACT_ID")
        fact_ids.add(fact_id_value)
        if fact.get("verification_status") not in VERIFIED_STATUSES:
            errors.append("FACT_VERIFICATION")
        if not fact.get("event_id") or not fact.get("text_es") or not isinstance(fact.get("text_en"), str):
            errors.append("FACT_CONTENT")
        refs = fact.get("source_ids") if isinstance(fact.get("source_ids"), list) else []
        if not refs or any(ref not in source_ids for ref in refs):
            errors.append("FACT_SOURCE")
        if _future(fact.get("observed_at"), moment, tolerance):
            errors.append("FUTURE_DATE")
        if any(key in fact for key in ("body", "description", "article", "content")):
            errors.append("ARTICLE_BODY_FORBIDDEN")

    statements = package.get("statements") if isinstance(package.get("statements"), list) else []
    statement_ids: set[str] = set()
    for statement in statements:
        if not isinstance(statement, dict) or set(statement) != {
            "statement_id", "text_es", "text_en", "speaker", "source_ids",
            "attributed", "not_verified_as_fact",
        }:
            errors.append("STATEMENT_SCHEMA")
            continue
        statement_id_value = str(statement.get("statement_id") or "")
        if not statement_id_value or statement_id_value in statement_ids:
            errors.append("STATEMENT_ID")
        statement_ids.add(statement_id_value)
        if not statement.get("speaker") or not statement.get("text_es"):
            errors.append("STATEMENT_ATTRIBUTION")
        if statement.get("attributed") is not True or statement.get("not_verified_as_fact") is not True:
            errors.append("STATEMENT_ATTRIBUTION")
        refs = statement.get("source_ids") if isinstance(statement.get("source_ids"), list) else []
        if not refs or any(ref not in source_ids for ref in refs):
            errors.append("STATEMENT_SOURCE")

    context = package.get("operational_context")
    if not isinstance(context, dict) or set(context) != {"state", "confidence", "dimensions", "as_of", "health"}:
        errors.append("OPERATIONAL_CONTEXT_SCHEMA")
    else:
        if not context.get("state") or context.get("confidence") not in CONFIDENCE_VALUES or not isinstance(context.get("dimensions"), dict):
            errors.append("OPERATIONAL_CONTEXT")
        if context.get("health") not in HEALTH_VALUES:
            errors.append("OPERATIONAL_HEALTH")
        if _future(context.get("as_of"), moment, tolerance):
            errors.append("FUTURE_DATE")

    for key in ("what_changed", "what_we_know", "what_we_dont_know", "watch_next_24h"):
        if not isinstance(package.get(key), list) or not all(isinstance(item, str) for item in package.get(key, [])):
            errors.append("EDITORIAL_LISTS")
    assets = package.get("visual_assets")
    if not isinstance(assets, list):
        errors.append("VISUAL_ASSETS")
    else:
        for asset in assets:
            if not isinstance(asset, dict) or set(asset) != {
                "asset_id", "type", "uri", "rights_status", "credit", "allowed_uses", "sha256"
            }:
                errors.append("VISUAL_ASSET_SCHEMA")
                continue
            if asset.get("type") not in ASSET_TYPES or asset.get("rights_status") not in {"cleared", "restricted"}:
                errors.append("VISUAL_ASSET_RIGHTS")
            if not asset.get("credit") or not asset.get("allowed_uses") or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256") or "")):
                errors.append("VISUAL_ASSET_RIGHTS")

    if recommended and not facts:
        errors.append("RECOMMENDED_WITHOUT_FACTS")
    return _report(
        "package", identity, errors,
        package_schema_version=PACKAGE_SCHEMA_VERSION,
        content_hash=str(package.get("content_hash") or ""),
        rule_version=str((recommendation or {}).get("rule_id") or ""),
    )


def _text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _text_values(child)


def _numbers(text: str) -> set[str]:
    return {item.replace(",", ".").casefold() for item in _NUMBER_RE.findall(text)}


def _dates(text: str) -> set[str]:
    return {item.casefold() for item in _DATE_RE.findall(text)}


def _entities(text: str) -> set[str]:
    result: set[str] = set()
    # Work sentence by sentence so a period cannot accidentally join two
    # unrelated capitalised fragments into a synthetic entity.
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for match in _ENTITY_RE.finditer(sentence):
            raw = re.sub(r"\s+", " ", match.group(0)).strip()
            value = raw.casefold()
            if value in _GENERIC_ENTITIES:
                continue
            # A lone title-cased word at the start of a sentence is normally
            # grammar, not an entity.  Acronyms and multi-word names remain.
            if match.start() == 0 and " " not in raw and not raw.isupper():
                continue
            result.add(value)
    return result


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _contradicts(voiceover: str, evidence: str) -> bool:
    voice = voiceover.casefold()
    source = evidence.casefold()
    for left, right in _CONTRADICTION_PAIRS:
        source_left = any(token in source for token in left)
        source_right = any(token in source for token in right)
        voice_left = any(token in voice for token in left)
        voice_right = any(token in voice for token in right)
        if (source_left and voice_right and not source_right) or (source_right and voice_left and not source_left):
            return True
    return False


def validate_script(
    package: dict[str, Any],
    script: Any,
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(script, dict):
        return _report("script", "", ["SCRIPT_SCHEMA"])
    # Explicit version dispatch: old fixtures/cached voice jobs remain 1.0.
    # Background context is only accepted by the separately typed 1.1 contract.
    if script.get("schema_version") == "1.1.0":
        from .editorial import validate_clear_script
        return validate_clear_script(package, script, rules=rules or load_rules())
    identity = str(script.get("script_id") or "")
    config = rules or load_rules()
    if set(script) != SCRIPT_KEYS or script.get("schema_version") != SCRIPT_SCHEMA_VERSION:
        errors.append("SCRIPT_SCHEMA")
    if script.get("package_id") != package.get("package_id"):
        errors.append("PACKAGE_ID_MISMATCH")
    if script.get("package_content_hash") != package.get("content_hash"):
        errors.append("CONTENT_HASH_MISMATCH")
    if script.get("video_type") != package.get("video_type") or script.get("video_type") not in VIDEO_TYPES:
        errors.append("VIDEO_TYPE")
    if script.get("language") not in package.get("language_set", []):
        errors.append("LANGUAGE")
    if script.get("generated_by") not in {"gemini", "openrouter-free", "rules"}:
        errors.append("GENERATED_BY")
    if identity != script_id(script):
        errors.append("SCRIPT_ID_MISMATCH")

    scenes = script.get("scenes") if isinstance(script.get("scenes"), list) else []
    if not scenes:
        errors.append("SCENES")
    fact_map = {str(item.get("fact_id")): item for item in package.get("verified_facts", []) if isinstance(item, dict)}
    statement_map = {str(item.get("statement_id")): item for item in package.get("statements", []) if isinstance(item, dict)}
    source_ids = {str(item.get("source_id")) for item in package.get("sources", []) if isinstance(item, dict)}
    seen_scene_ids: set[str] = set()
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or set(scene) != SCENE_KEYS:
            errors.append("SCENE_SCHEMA")
            continue
        expected_scene_id = f"scene-{index:02d}"
        if scene.get("scene_id") != expected_scene_id or scene.get("scene_id") in seen_scene_ids:
            errors.append("SCENE_ID")
        seen_scene_ids.add(str(scene.get("scene_id")))
        voiceover = str(scene.get("voiceover") or "").strip()
        if not voiceover:
            errors.append("SCENE_VOICEOVER")
        fact_refs = scene.get("fact_ids") if isinstance(scene.get("fact_ids"), list) else []
        statement_refs = scene.get("statement_ids") if isinstance(scene.get("statement_ids"), list) else []
        source_refs = scene.get("source_ids") if isinstance(scene.get("source_ids"), list) else []
        if any(ref not in fact_map for ref in fact_refs):
            errors.append("UNKNOWN_FACT_ID")
        if any(ref not in statement_map for ref in statement_refs):
            errors.append("UNKNOWN_STATEMENT_ID")
        if any(ref not in source_ids for ref in source_refs):
            errors.append("UNKNOWN_SOURCE_ID")
        if voiceover and not fact_refs and not statement_refs:
            errors.append("UNTRACED_FACTUAL_CLAIM")
        evidence_rows = [fact_map[ref] for ref in fact_refs if ref in fact_map] + [statement_map[ref] for ref in statement_refs if ref in statement_map]
        expected_sources = {item for row in evidence_rows for item in row.get("source_ids", [])}
        if evidence_rows and (not source_refs or not set(source_refs).issubset(expected_sources)):
            errors.append("SCENE_SOURCE_TRACE")
        if statement_refs:
            speakers = [str(statement_map[ref].get("speaker") or "") for ref in statement_refs if ref in statement_map]
            if not _ATTRIBUTION_RE.search(voiceover) and not any(speaker and speaker.casefold() in voiceover.casefold() for speaker in speakers):
                errors.append("STATEMENT_AS_FACT")
        evidence_text = " ".join(" ".join(_text_values(row)) for row in evidence_rows)
        if evidence_rows and _contradicts(voiceover, evidence_text):
            errors.append("SEMANTIC_CONTRADICTION")
        if scene.get("visual_intent") not in VISUAL_INTENTS:
            errors.append("VISUAL_INTENT")
        if not isinstance(scene.get("on_screen_text"), str):
            errors.append("ON_SCREEN_TEXT")

    prose = ". ".join([
        str(script.get("headline") or ""), str(script.get("hook") or ""),
        *(str(scene.get("voiceover") or "") for scene in scenes if isinstance(scene, dict)),
        *(str(scene.get("on_screen_text") or "") for scene in scenes if isinstance(scene, dict)),
        str(script.get("outro") or ""),
    ])
    package_text_values = list(_text_values(package))
    package_corpus = ". ".join(package_text_values)
    package_corpus += " " + str((package.get("operational_context") or {}).get("state") or "").replace("_", " ")
    if _numbers(prose) - _numbers(package_corpus):
        errors.append("NEW_NUMBER")
    if _dates(prose) - _dates(package_corpus):
        errors.append("NEW_DATE")
    allowed_entities: set[str] = set()
    for value in package_text_values:
        allowed_entities.update(_entities("reference: " + value))
    allowed_entities.update(_entities("reference: " + str((package.get("operational_context") or {}).get("state") or "").replace("_", " ")))
    if _entities(prose) - allowed_entities:
        errors.append("NEW_ENTITY")
    package_urls = set(_URL_RE.findall(package_corpus))
    if set(_URL_RE.findall(prose)) - package_urls:
        errors.append("NEW_URL")
    if _HTML_RE.search(prose):
        errors.append("HTML_FORBIDDEN")
    if _INJECTION_RE.search(prose):
        errors.append("PROMPT_INJECTION")
    if _SENSATIONAL_RE.search(prose):
        errors.append("SENSATIONALISM")

    state = str((package.get("operational_context") or {}).get("state") or "").casefold()
    confidence = str((package.get("operational_context") or {}).get("confidence") or "").casefold()
    lowered = prose.casefold()
    if "closed" not in state and "cerr" not in state and re.search(r"\b(?:est[aá] cerrado|cierre confirmado|is closed|confirmed closure)\b", lowered):
        errors.append("OPERATIONAL_STATE_ALTERED")
    if "open" not in state and "abiert" not in state and re.search(r"\b(?:normalidad total|fully open|completely normal)\b", lowered):
        errors.append("OPERATIONAL_STATE_ALTERED")
    confidence_mentions = {
        "high": ("confianza alta", "high confidence"),
        "medium": ("confianza media", "medium confidence"),
        "low": ("confianza baja", "low confidence"),
    }
    for level, phrases in confidence_mentions.items():
        if level != confidence and any(phrase in lowered for phrase in phrases):
            errors.append("CONFIDENCE_ALTERED")
    if package.get("what_we_dont_know") and re.search(r"\b(?:sin ninguna duda|con certeza absoluta|definitely confirmed|certain beyond doubt)\b", lowered):
        errors.append("UNCERTAINTY_REMOVED")

    spoken = " ".join([
        str(script.get("hook") or ""),
        *(str(scene.get("voiceover") or "") for scene in scenes if isinstance(scene, dict)),
        str(script.get("outro") or ""),
    ])
    words = _word_count(spoken)
    duration = config["duration"].get(str(script.get("video_type")), {})
    if script.get("target_seconds") != duration.get("target_seconds"):
        errors.append("TARGET_DURATION")
    if script.get("estimated_words") != words:
        errors.append("ESTIMATED_WORDS")
    if words < int(duration.get("minimum_words", 0)) or words > int(duration.get("maximum_words", 10**9)):
        errors.append("WORD_COUNT")

    return _report(
        "script", identity, errors,
        script_schema_version=SCRIPT_SCHEMA_VERSION,
        package_id=str(package.get("package_id") or ""),
        content_hash=str(package.get("content_hash") or ""),
        generated_by=str(script.get("generated_by") or ""),
        fact_ids=sorted({ref for scene in scenes if isinstance(scene, dict) for ref in scene.get("fact_ids", [])}),
        statement_ids=sorted({ref for scene in scenes if isinstance(scene, dict) for ref in scene.get("statement_ids", [])}),
        source_ids=sorted({ref for scene in scenes if isinstance(scene, dict) for ref in scene.get("source_ids", [])}),
        estimated_words=words,
    )
