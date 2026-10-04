"""Sourced plain-language ES scripts; no news lookup, model or audio calls.

The factual package stays closed. Background definitions are a separate,
versioned allowlist and can NEVER serve as evidence for a news claim.
Legacy 1.0 scripts and voice-cache identities are deliberately unchanged.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

from .schema import SCRIPT_KEYS, SCENE_KEYS, script_id

CLEAR_SCRIPT_VERSION = "1.1.0"
EDITORIAL_VERSION = "plain-es-v1"
CLEAR_SCRIPT_KEYS = SCRIPT_KEYS | {"editorial_context"}
CLEAR_SCENE_KEYS = SCENE_KEYS | {"evidence_kind", "context_ids", "package_fields"}
WORD_RE = re.compile(r"\b[\wáéíóúüñ'-]+\b", re.I)
INTERNAL_RE = re.compile(
    r"\b(?:estado operativo canónico|fase uno|fase 1|sobre completo|instantánea|"
    r"paquete|snapshot|reglas deterministas|sistema factual|selección audiovisual|"
    r"RISK_RESTRICTION|OPEN_[A-Z_]+|CONFIRMED_[A-Z_]+)\b", re.I
)
CLERICAL_RE = re.compile(
    r"\b(?:archivo|instantánea|snapshot|paquete|incorpor[oó]|edición|evidencia|evidence|"
    r"file|added|edition)\b", re.I
)
ACRONYM_RE = re.compile(r"\b[A-Z]{2,8}\b")
QUANTITY_RE = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s+(pasajeros?|vehículos?|rotaciones?|buques?|barcos?|tránsitos?|personas?)\b", re.I)
STATES = {
    "OPEN_SEVERELY_RESTRICTED": "abierto con tránsito muy restringido",
    "OPEN_RESTRICTED": "abierto con tránsito restringido",
    "OPEN": "abierto",
    "NORMAL": "normalidad operativa",
    "NORMAL_OPERATIONS": "normalidad operativa",
    "CLOSED": "cerrado",
    "UNCERTAIN": "situación incierta",
    "REINFORCED_WATCH": "vigilancia reforzada",
}
CONFIDENCE = {"high": "alta", "medium": "media", "low": "baja"}
HOOK = "Estas son las claves verificadas y lo que todavía no sabemos."
OUTRO = "Seguimos atentos a nuevas confirmaciones."
# Paraphrased definitions, not copied articles. Scope is background only.
GLOSSARY = {
    "ope": {
        "context_id": "context:ope:es:v1",
        "term": "OPE",
        "definition": "La Operación Paso del Estrecho organiza los desplazamientos de verano entre Europa y el norte de África.",
        "source_name": "Protección Civil",
        "source_url": "https://www.proteccioncivil.es/coordinacion/campanas/operaci%C3%B3n-paso-del-estrecho",
        "checked_on": "2026-10-03",
        "scope": "background_only",
    },
    "huties": {
        "context_id": "context:huties:es:v1",
        "term": "hutíes",
        "definition": "Los hutíes son un grupo armado de Yemen.",
        "source_name": "Naciones Unidas",
        "source_url": "https://www.ungeneva.org/es/news-media/news/2025/10/111947/los-huties-detienen-20-empleados-de-la-onu-en-yemen",
        "checked_on": "2026-10-03",
        "scope": "background_only",
    },
}
ROLE_FIELDS = {
    "state": ["operational_context.state", "operational_context.confidence"],
    "uncertainty": ["what_we_dont_know", "operational_context.health"],
    "watch": ["watch_next_24h"],
    "change": ["what_changed"],
}


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def spoken(script: dict) -> str:
    return " ".join([str(script.get("hook") or ""),
                     *(str(row.get("voiceover") or "") for row in script.get("scenes", []) if isinstance(row, dict)),
                     str(script.get("outro") or "")])


def target_seconds(word_count: int, config: dict, video_type: str) -> int:
    # Duration follows real content; never pad news with implementation details.
    rate = config["duration"]["words_per_minute"]
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise ValueError("invalid-speaking-rate")
    return max(15, math.ceil(word_count * 60 / rate))


def normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def clear_factual_excerpt(text: Any) -> str:
    # Select understandable quantities, never guess what "rotations" measures.
    # Original evidence and all its metrics remain in the factual package.
    return re.sub(r",\s*(\d+\s+vehículos)\s+y\s+\d+\s+rotaciones\b",
                  r" y \1", normalize(text), flags=re.I)


def contexts_for(package: dict) -> list[dict]:
    # Only terms actually present in verified Spanish evidence trigger context.
    evidence = " ".join(str(row.get("text_es") or "") for row in package.get("verified_facts", []))
    keys = []
    if re.search(r"\bOPE\b", evidence):
        keys.append("ope")
    if re.search(r"\bhut[ií]es\b", evidence, re.I):
        keys.append("huties")
    return [copy.deepcopy(GLOSSARY[key]) for key in keys]


def editorial_context(package: dict) -> dict:
    return {
        "version": EDITORIAL_VERSION,
        "background": contexts_for(package),
        "human_review_required": True,
        "publication_allowed": False,
    }


def derived_text(package: dict, role: str) -> tuple[str, str]:
    if role == "state":
        context = package["operational_context"]
        state = STATES.get(str(context["state"]).upper())
        if not state:
            raise ValueError("unmapped-operational-state")
        if state.startswith("abierto") or state == "cerrado":
            opening = f"El estrecho está {state}."
        elif state == "situación incierta":
            opening = "La situación del estrecho es incierta."
        else:
            opening = f"El estrecho presenta {state}."
        voice = f"{opening} La evaluación tiene confianza {CONFIDENCE[context['confidence']]}."
        if context["confidence"] != "high":
            voice += " La información disponible no permite darlo por seguro."
        return voice, state
    if role == "uncertainty":
        rows = package.get("what_we_dont_know") or []
        first = normalize(rows[0]) if rows else ""
        if re.search(r"instantánea.*(?:sobre completo|salud de fuentes)", first, re.I):
            text = "Faltan datos sobre la fiabilidad de las fuentes de ese momento."
            return text, text
        if re.search(r"instantánea.*(?:nivel|confianza)", first, re.I):
            text = "No se conservó una valoración completa de la fiabilidad de los datos."
            clear = [normalize(row) for row in rows[1:] if normalize(row) and not INTERNAL_RE.search(str(row))]
            return text + (" " + clear[0] if clear else ""), "Falta información para valorar los datos"
        clear = [normalize(row) for row in rows if normalize(row) and not INTERNAL_RE.search(str(row))]
        if clear:
            text = clear[0]
            return text, text
        if rows or package["operational_context"]["health"] != "healthy":
            return "Falta información para completar la evaluación. Mantenemos esa incertidumbre.", "Falta información"
        raise ValueError("no-uncertainty")
    if role == "watch":
        rows = [normalize(row) for row in package.get("watch_next_24h", [])
                if normalize(row) and not INTERNAL_RE.search(str(row))]
        if not rows:
            raise ValueError("no-watch")
        return "Seguiremos atentos a: " + rows[0], rows[0]
    if role == "change":
        # Conservative: clerical updates and unsupported yesterday comparisons
        # are omitted, not converted into an operational change.
        facts = {normalize(row["text_es"]) for row in package.get("verified_facts", [])}
        rows = [normalize(row) for row in package.get("what_changed", [])
                if normalize(row) in facts and not CLERICAL_RE.search(str(row))]
        if not rows:
            raise ValueError("no-evidenced-change")
        return rows[0], rows[0]
    raise ValueError("unsupported-editorial-role")


def generate_clear_script(package: dict, *, rules: dict) -> dict:
    scenes = []

    def add(voice: str, screen: str, role: str, visual: str, *,
            facts=None, statements=None, sources=None, contexts=None, fields=None) -> None:
        scenes.append({
            "scene_id": f"scene-{len(scenes) + 1:02d}",
            "voiceover": normalize(voice), "on_screen_text": normalize(screen),
            "fact_ids": list(facts or []), "statement_ids": list(statements or []),
            "source_ids": list(sources or []), "visual_intent": visual,
            "evidence_kind": role, "context_ids": list(contexts or []),
            "package_fields": list(fields or []),
        })

    # Each fact gets only its own evidence. Do not truncate a fact mid-sentence.
    for fact in package["verified_facts"][:2]:
        text = clear_factual_excerpt(fact["text_es"])
        add(text, text, "news", "source-card",
            facts=[fact["fact_id"]], sources=fact["source_ids"])
    context = editorial_context(package)
    for row in context["background"]:
        add(row["definition"], row["definition"], "background", "text-card",
            contexts=[row["context_id"]])
    voice, screen = derived_text(package, "state")
    add(voice, screen, "state", "status-card", fields=ROLE_FIELDS["state"])
    for role, visual in (("uncertainty", "text-card"), ("watch", "map")):
        if role == "watch" and package["video_type"] == "breaking":
            continue
        try:
            voice, screen = derived_text(package, role)
        except ValueError:
            continue
        add(voice, screen, role, visual, fields=ROLE_FIELDS[role])
    # No "changed since yesterday" claim unless the closed package supports it.
    # Optional attributed statements remain explicitly separate from facts.
    for statement in package.get("statements", [])[:1]:
        text = normalize(statement["text_es"])
        voice = f"Según {statement['speaker']}: {text} Es una declaración, no un hecho verificado."
        add(voice, text, "attributed", "source-card",
            statements=[statement["statement_id"]], sources=statement["source_ids"])
    script = {
        "schema_version": CLEAR_SCRIPT_VERSION, "script_id": "",
        "package_id": package["package_id"], "package_content_hash": package["content_hash"],
        "language": "es", "video_type": package["video_type"], "target_seconds": 0,
        "estimated_words": 0, "headline": clear_factual_excerpt(package["headlines"]["es"]),
        "hook": HOOK, "scenes": scenes, "outro": OUTRO, "generated_by": "rules",
        "editorial_context": context,
    }
    script["estimated_words"] = words(spoken(script))
    script["target_seconds"] = target_seconds(script["estimated_words"], rules, script["video_type"])
    script["script_id"] = script_id(script)
    return script


def validate_clear_script(package: dict, script: dict, *, rules: dict) -> dict:
    # Import here so the legacy validator can dispatch without an import cycle.
    from .validator import (validate_package, _report, _text_values, _numbers, _dates,
                            _entities, _contradicts, _HTML_RE, _INJECTION_RE,
                            _SENSATIONAL_RE, _ATTRIBUTION_RE, _URL_RE)
    errors = []
    if validate_package(package, rules=rules)["validation_status"] != "PASS":
        errors.append("INVALID_VIDEO_PACKAGE")
    if not package.get("video_recommended"):
        errors.append("VIDEO_NOT_RECOMMENDED")
    if set(script) != CLEAR_SCRIPT_KEYS or script.get("language") != "es":
        errors.append("SCRIPT_SCHEMA")
    if script.get("package_id") != package.get("package_id"):
        errors.append("PACKAGE_ID_MISMATCH")
    if script.get("package_content_hash") != package.get("content_hash"):
        errors.append("CONTENT_HASH_MISMATCH")
    if script.get("script_id") != script_id(script):
        errors.append("SCRIPT_ID_MISMATCH")
    if script.get("video_type") != package.get("video_type"):
        errors.append("VIDEO_TYPE")
    if script.get("generated_by") not in {"rules", "gemini", "openrouter-free"}:
        errors.append("GENERATED_BY")
    expected_context = editorial_context(package)
    if script.get("editorial_context") != expected_context:
        errors.append("EDITORIAL_CONTEXT_ALTERED")
    # The model cannot use context sources as new news evidence or add concepts
    # to the hook/title/outro where no per-claim evidence exists.
    if (script.get("headline") != clear_factual_excerpt(package["headlines"]["es"])
            or script.get("hook") != HOOK or script.get("outro") != OUTRO):
        errors.append("EDITORIAL_FRAMING_ALTERED")
    fact_map = {row["fact_id"]: row for row in package["verified_facts"]}
    statement_map = {row["statement_id"]: row for row in package["statements"]}
    context_map = {row["context_id"]: row for row in expected_context["background"]}
    seen_background, seen_roles, seen_facts = set(), set(), set()
    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("SCENES")
        scenes = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or set(scene) != CLEAR_SCENE_KEYS:
            errors.append("SCENE_SCHEMA")
            continue
        if scene.get("scene_id") != f"scene-{index:02d}":
            errors.append("SCENE_ID")
        refs_ok = all(isinstance(scene[key], list) and all(isinstance(ref, str) for ref in scene[key])
                      for key in ("fact_ids", "statement_ids", "source_ids", "context_ids", "package_fields"))
        if not refs_ok:
            errors.append("SCENE_TRACEABILITY")
            continue
        voice = scene.get("voiceover")
        screen = scene.get("on_screen_text")
        if not isinstance(voice, str) or not voice.strip() or not isinstance(screen, str) or not screen.strip():
            errors.append("SCENE_TEXT")
            continue
        if scene["visual_intent"] not in {"source-card", "status-card", "text-card", "timeline", "map", "chart", "presenter"}:
            errors.append("VISUAL_INTENT")
        role = scene["evidence_kind"]
        if role in {"news", "attributed"}:
            facts = scene["fact_ids"]
            statements = scene["statement_ids"]
            if any(ref not in fact_map for ref in facts):
                errors.append("UNKNOWN_FACT_ID")
            if any(ref not in statement_map for ref in statements):
                errors.append("UNKNOWN_STATEMENT_ID")
            if ((role == "news" and (not facts or statements))
                    or (role == "attributed" and (not statements or facts))
                    or scene["context_ids"] or scene["package_fields"]):
                errors.append("UNTRACED_FACTUAL_CLAIM")
            rows = [fact_map[ref] for ref in facts if ref in fact_map] + [statement_map[ref] for ref in statements if ref in statement_map]
            seen_facts.update(facts)
            expected_sources = {ref for row in rows for ref in row["source_ids"]}
            if set(scene["source_ids"]) != expected_sources or not expected_sources:
                errors.append("SCENE_SOURCE_TRACE")
            if any(ref not in {row["source_id"] for row in package["sources"]} for ref in scene["source_ids"]):
                errors.append("UNKNOWN_SOURCE_ID")
            evidence = " ".join(" ".join(_text_values(row)) for row in rows)
            prose = voice + ". " + screen
            if _numbers(prose) - _numbers(evidence):
                errors.append("NEW_NUMBER")
            evidence_quantities = {(number, unit.casefold()) for number, unit in QUANTITY_RE.findall(evidence)}
            if {(number, unit.casefold()) for number, unit in QUANTITY_RE.findall(prose)} - evidence_quantities:
                errors.append("QUANTITY_UNIT_ALTERED")
            if _dates(prose) - _dates(evidence):
                errors.append("NEW_DATE")
            allowed_entities = set()
            for row in rows:
                for value in _text_values(row):
                    allowed_entities.update(_entities("reference: " + value))
            if _entities(prose) - allowed_entities:
                errors.append("NEW_ENTITY")
            if set(_URL_RE.findall(prose)) - set(_URL_RE.findall(evidence)):
                errors.append("NEW_URL")
            if rows and _contradicts(voice, evidence):
                errors.append("SEMANTIC_CONTRADICTION")
            if statements and not _ATTRIBUTION_RE.search(voice):
                errors.append("STATEMENT_AS_FACT")
            if role == "attributed" and "no un hecho verificado" not in voice:
                errors.append("STATEMENT_AS_FACT")
        elif role == "background":
            refs = scene["context_ids"]
            row = context_map.get(refs[0]) if len(refs) == 1 else None
            if (row is None or voice != row["definition"] or screen != row["definition"]
                    or scene["fact_ids"] or scene["statement_ids"] or scene["source_ids"] or scene["package_fields"]):
                errors.append("BACKGROUND_TRACE")
            seen_background.update(refs)
        elif role in ROLE_FIELDS:
            seen_roles.add(role)
            try:
                expected_voice, expected_screen = derived_text(package, role)
            except ValueError:
                expected_voice, expected_screen = "", ""
            if (voice != expected_voice or screen != expected_screen
                    or scene["package_fields"] != ROLE_FIELDS[role]
                    or scene["fact_ids"] or scene["statement_ids"] or scene["source_ids"] or scene["context_ids"]):
                errors.append("CANONICAL_CONTEXT_ALTERED")
        else:
            errors.append("EVIDENCE_KIND")
        combined = voice + ". " + screen
        if INTERNAL_RE.search(combined):
            errors.append("INTERNAL_JARGON")
        if any(words(sentence) > 30 for sentence in re.split(r"(?<=[.!?])\s+", voice)):
            errors.append("LONG_SENTENCE")
        if _HTML_RE.search(combined):
            errors.append("HTML_FORBIDDEN")
        if _INJECTION_RE.search(combined):
            errors.append("PROMPT_INJECTION")
        if _SENSATIONAL_RE.search(combined):
            errors.append("SENSATIONALISM")
        # Unknown acronyms are not silently read aloud. Obtain a sourced
        # definition or rewrite upstream under human review first.
        defined = {"OPE"} if "context:ope:es:v1" in context_map else set()
        if set(ACRONYM_RE.findall(voice)) - defined:
            errors.append("UNEXPLAINED_ACRONYM")
        if re.search(r"\brotaciones\b", voice, re.I):
            errors.append("UNEXPLAINED_TECHNICAL_TERM")
        confidence = package["operational_context"]["confidence"]
        for level, label in CONFIDENCE.items():
            if level != confidence and re.search(r"\bconfianza(?:\s+\w+){0,5}\s+" + label + r"\b", voice, re.I):
                errors.append("CONFIDENCE_ALTERED")
        if re.search(r"sin ninguna duda|con certeza absoluta|definitivamente confirmado", voice, re.I):
            errors.append("UNCERTAINTY_REMOVED")
        if ("closed" not in package["operational_context"]["state"].casefold()
                and re.search(r"est[aá] cerrado|cierre confirmado", voice, re.I)):
            errors.append("OPERATIONAL_STATE_ALTERED")
    if not seen_facts:
        errors.append("UNTRACED_FACTUAL_CLAIM")
    if seen_background != set(context_map):
        errors.append("MISSING_BACKGROUND_DEFINITION")
    if "state" not in seen_roles:
        errors.append("MISSING_OPERATIONAL_CONTEXT")
    if (package["what_we_dont_know"] or package["operational_context"]["health"] != "healthy") and "uncertainty" not in seen_roles:
        errors.append("UNCERTAINTY_REMOVED")
    count = words(spoken(script))
    framing = ". ".join(str(script.get(key) or "") for key in ("headline", "hook", "outro"))
    if _HTML_RE.search(framing) or _INJECTION_RE.search(framing) or _SENSATIONAL_RE.search(framing):
        errors.append("UNSAFE_EDITORIAL_FRAMING")
    video_type = str(script.get("video_type"))
    maximum = rules["duration"].get(video_type, {}).get("maximum_words", 0)
    if count < 30 or count > maximum:
        errors.append("WORD_COUNT")
    if script.get("estimated_words") != count:
        errors.append("ESTIMATED_WORDS")
    if script.get("target_seconds") != target_seconds(count, rules, video_type):
        errors.append("TARGET_DURATION")
    return _report("script", str(script.get("script_id") or ""), errors,
                   validator_version="1.1.0",
                   script_schema_version=CLEAR_SCRIPT_VERSION,
                   package_id=package.get("package_id"), content_hash=package.get("content_hash"),
                   generated_by=script.get("generated_by"), estimated_words=count,
                   human_review_required=True, publication_allowed=False)

