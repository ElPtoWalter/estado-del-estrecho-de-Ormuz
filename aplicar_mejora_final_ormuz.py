#!/usr/bin/env python3
# Mejora final V3 del motor editorial de Estrecho Ormuz.
from __future__ import annotations

import argparse
import ast
import json
import py_compile
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MARKER = "ORMUZ_V3_FINAL_GUARD"
ROOT = Path(__file__).resolve().parent

FILES = {
    "engine": ROOT / "update_status.py",
    "guard": ROOT / "evidence_guard.py",
    "aliases": ROOT / "source_aliases.json",
    "workflow": ROOT / ".github" / "workflows" / "update-status.yml",
    "tests": ROOT / "tests" / "test_final_guard.py",
}

SOURCE_PROFILE = '''    SourceProfile(
        "national_security_journal",
        "National Security Journal",
        2,
        2.1,
        ("nationalsecurityjournal.org",),
        ("national security journal",),
    ),
'''

SOURCE_PROFILE_FUNCTION = r'''def source_profile(
    source_name: str = "",
    source_url: str = "",
    article_url: str = "",
) -> SourceProfile | None:
    # ORMUZ_V3_FINAL_GUARD: evita que "ona" coincida dentro de "national".
    for url in (source_url, article_url):
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if not host:
            continue
        for profile in SOURCE_PROFILES:
            if any(host == domain or host.endswith("." + domain) for domain in profile.domains):
                return profile

    normalized = normalized_key(source_name)
    if not normalized:
        return None

    for alias, profile in PROFILE_BY_ALIAS.items():
        if normalized_key(alias) == normalized:
            return profile

    padded = f" {normalized} "
    aliases = sorted(
        PROFILE_BY_ALIAS.items(),
        key=lambda pair: len(normalized_key(pair[0])),
        reverse=True,
    )
    for alias, profile in aliases:
        alias_key = normalized_key(alias)
        if alias_key and f" {alias_key} " in padded:
            return profile
    return None
'''

CLASSIFY_FUNCTIONS = r'''ANALYTICAL_HEADLINE_RE = re.compile(
    r"(?:\?|\bwhy\b|\bhow\b|\bwhat\b|\bwhether\b|"
    r"\bkeeps?\s+insisting\b|\binsists?\b|\bclaims?\b|\bargues?\b|"
    r"\bopinion\b|\banalysis\b|\bexplainer\b|"
    r"\bopen\b.{0,55}\bbut\b|\bclosed\b.{0,55}\bbut\b)",
    re.I,
)


def headline_is_non_operational(title: str) -> bool:
    cleaned = normalize_text(title)
    if not cleaned:
        return False
    if ANALYTICAL_HEADLINE_RE.search(cleaned):
        return True
    return bool(
        re.match(
            r"^(?:why|how|what|when|where|who|which|can|could|would|will|"
            r"is|are|was|were|do|does|did|should|may|might)\b",
            cleaned,
            re.I,
        )
    )


def classify_text(title: str, description: str = "") -> set[str]:
    # ORMUZ_V3_FINAL_GUARD: preguntas/análisis no confirman apertura o cierre.
    title_text = normalize_text(title)
    description_text = normalize_text(description)
    combined = normalize_text(f"{title_text}. {description_text}").lower()
    operational_text = description_text.lower() if headline_is_non_operational(title_text) else combined

    signals: set[str] = set()
    hypothetical = any(re.search(pattern, combined) for pattern in HYPOTHETICAL_PATTERNS)

    if operational_text and any(re.search(pattern, operational_text) for pattern in OPEN_PATTERNS):
        signals.add("OPEN_OPERATIONAL")
    if operational_text and any(re.search(pattern, operational_text) for pattern in CLOSED_OPERATIONAL_PATTERNS):
        signals.add("CLOSED_OPERATIONAL")
    if any(re.search(pattern, combined) for pattern in DECLARATION_PATTERNS) and not hypothetical:
        signals.add("CLOSURE_DECLARED")
    if any(re.search(pattern, combined) for pattern in RISK_PATTERNS) or re.search(
        r"\b(?:traffic|transits?|shipping)\s+(?:has\s+)?(?:collapsed|fallen|dropped|declined|slowed)\b|"
        r"\b(?:ships?|vessels?|tankers?)\s+(?:are\s+)?(?:waiting|holding|diverted|rerouted|avoiding)\b|"
        r"\bwar[- ]risk\s+(?:premium|premiums|insurance|rates?)\b",
        combined,
        re.I,
    ):
        signals.add("RISK_RESTRICTION")

    if "CLOSURE_DECLARED" in signals and "CLOSED_OPERATIONAL" in signals:
        strong_operational_terms = (
            "closed to shipping", "traffic halted", "traffic stopped",
            "no vessels", "no safe transit", "passage blocked", "impassable",
        )
        if not any(term in operational_text for term in strong_operational_terms):
            signals.discard("CLOSED_OPERATIONAL")
    return signals
'''

CARRY_FUNCTIONS = r'''def expected_confirmation_signal(status: str) -> str | None:
    return {"ABIERTO": "OPEN_OPERATIONAL", "CERRADO": "CLOSED_OPERATIONAL"}.get(status)


def confirmation_matches_status(confirmation: dict[str, Any] | None, status: str) -> bool:
    if not isinstance(confirmation, dict):
        return False
    expected = expected_confirmation_signal(status)
    if not expected:
        return False
    stored_status = confirmation.get("status")
    if stored_status and stored_status != status:
        return False
    title = normalize_text(str(confirmation.get("title") or ""))
    description = normalize_text(str(confirmation.get("description") or ""))
    if not title and not description:
        return False
    stored_signal = normalize_text(str(confirmation.get("signal") or "")).upper()
    signals = {stored_signal} if stored_signal else classify_text(title, description)
    if expected not in signals:
        return False
    if headline_is_non_operational(title) and not description:
        return False
    profile = source_profile(
        source_name=str(confirmation.get("source_name") or ""),
        source_url=str(confirmation.get("source_url") or ""),
        article_url=str(confirmation.get("source_url") or ""),
    )
    if profile is None:
        return False
    if bool(confirmation.get("official")) and not profile.official:
        return False
    return True


def confirmation_supports_status(
    confirmation: dict[str, Any] | None,
    status: str,
    now: datetime,
    carry_hours: int,
) -> bool:
    if not confirmation_matches_status(confirmation, status):
        return False
    assert isinstance(confirmation, dict)
    at = parse_datetime(confirmation.get("at"))
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    if at <= minimum or at > now + timedelta(hours=2):
        return False
    return now - at <= timedelta(hours=carry_hours)


def previous_is_carryable(previous: dict[str, Any], now: datetime, carry_hours: int) -> bool:
    # ORMUZ_V3_FINAL_GUARD: solo se arrastra una confirmación operativa real.
    if previous.get("engine_version") != ENGINE_VERSION:
        return False
    status = str(previous.get("status") or "")
    if status not in {"ABIERTO", "CERRADO"}:
        return False
    return confirmation_supports_status(previous.get("last_valid_confirmation"), status, now, carry_hours)
'''

FINALIZE_FUNCTION = r'''def finalize_payload(
    *,
    previous: dict[str, Any],
    now: datetime,
    status: str,
    operational: str,
    confidence: str,
    summary_es: str,
    summary_en: str,
    evidence: list[dict[str, Any]],
    verification_ok: bool,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    # ORMUZ_V3_FINAL_GUARD: una señal de riesgo nunca sustituye la última confirmación válida.
    if status not in VALID_STATUS:
        status = "INCIERTO"
    if operational not in VALID_OPERATIONAL:
        operational = "NO_RECENT_CONFIRMATION"
    if confidence not in VALID_CONFIDENCE:
        confidence = "BAJA"

    now_iso = iso_z(now)
    meaningful_changed = previous.get("status") != status or previous.get("operational_status") != operational
    last_change_at = now_iso if meaningful_changed else previous.get("last_change_at", now_iso)

    prior = previous.get("last_valid_confirmation") if isinstance(previous.get("last_valid_confirmation"), dict) else None
    last_valid = prior
    expected = expected_confirmation_signal(status)
    matching = [
        item for item in evidence
        if expected
        and str(item.get("signal") or "").upper() == expected
        and not headline_is_non_operational(str(item.get("title") or ""))
    ]

    if status in {"ABIERTO", "CERRADO"} and matching:
        main = sorted(
            matching,
            key=lambda item: (float(item.get("score", 0.0)), parse_datetime(item.get("published_at"))),
            reverse=True,
        )[0]
        last_valid = {
            "status": status,
            "signal": expected,
            "at": main.get("published_at") or now_iso,
            "source_name": main.get("source_name"),
            "source_id": main.get("source_id"),
            "source_url": main.get("source_url"),
            "title": main.get("title"),
            "description": main.get("description", ""),
            "tier": main.get("tier"),
            "official": bool(main.get("official", False)),
        }
    elif status in {"ABIERTO", "CERRADO"}:
        if not confirmation_matches_status(prior, status):
            last_valid = None
    elif isinstance(prior, dict):
        prior_status = str(prior.get("status") or "")
        if not confirmation_matches_status(prior, prior_status):
            last_valid = None

    last_success_at = now_iso if verification_ok else previous.get("last_success_at")
    stale = not verification_ok
    if last_success_at:
        stale = stale or now - parse_datetime(last_success_at) > timedelta(hours=4)

    return {
        "engine_version": ENGINE_VERSION,
        "status": status,
        "operational_status": operational,
        "operational_label_es": OPERATIONAL_LABELS[operational][0],
        "operational_label_en": OPERATIONAL_LABELS[operational][1],
        "confidence": confidence,
        "checked_at": now_iso,
        "last_success_at": last_success_at,
        "last_change_at": last_change_at,
        "verification_ok": verification_ok,
        "stale": stale,
        "summary_es": summary_es,
        "summary_en": summary_en,
        "last_valid_confirmation": last_valid,
        "evidence": clean_public_evidence(evidence),
        "diagnostics": diagnostics,
    }
'''

GUARD_DIRECT_FUNCTIONS = r'''GUARD_ANALYTICAL_RE = re.compile(
    r"(?:\bkeeps?\s+insisting\b|\binsists?\b|\bclaims?\b|\bargues?\b|"
    r"\bopinion\b|\banalysis\b|\bexplainer\b|"
    r"\bopen\b.{0,55}\bbut\b|\bclosed\b.{0,55}\bbut\b)",
    re.I,
)


def direct_evidence(item: dict[str, Any], desired_status: str, checked_at: Any) -> tuple[bool, str]:
    title = normalized_space(item.get("title"))
    if not title:
        return False, "sin título"
    if QUESTIONABLE_RE.search(title) or GUARD_ANALYTICAL_RE.search(title):
        return False, "titular hipotético, interrogativo, analítico o controvertido"
    if not recent_enough(item, checked_at):
        return False, "evidencia demasiado antigua o sin fecha fiable"
    signal = normalized_key(item.get("signal")).upper()
    if desired_status == "ABIERTO":
        if signal != "OPEN_OPERATIONAL":
            return False, "señal distinta de OPEN_OPERATIONAL"
        if not OPEN_EXPLICIT_RE.search(title):
            return False, "el texto no confirma tránsito operativo"
    elif desired_status == "CERRADO":
        if signal != "CLOSED_OPERATIONAL":
            return False, "señal distinta de CLOSED_OPERATIONAL"
        if not CLOSED_EXPLICIT_RE.search(title):
            return False, "el texto no confirma cierre operativo"
    else:
        return True, "estado conservador"
    try:
        tier = int(item.get("tier", 0))
    except (TypeError, ValueError):
        tier = 0
    if tier < 3:
        return False, "fuente por debajo del umbral de reputación"
    return True, "evidencia operativa explícita"
'''

GUARD_MAIN = r'''def downgrade_to_uncertain(current: dict[str, Any], reasons: list[str]) -> None:
    signals = {normalized_key(item.get("signal")).upper() for item in iter_evidence(current)}
    if "CLOSURE_DECLARED" in signals:
        operational = "CLOSURE_DECLARED_UNCONFIRMED"
        summary_es = "Existe una declaración de cierre, pero no una confirmación operativa suficiente."
        summary_en = "A closure has been declared, but there is no sufficient operational confirmation."
    elif "RISK_RESTRICTION" in signals:
        operational = "HIGH_RISK_UNCONFIRMED"
        summary_es = "Las fuentes describen riesgo o restricciones, pero no permiten confirmar de forma fiable si el paso está abierto o cerrado."
        summary_en = "Sources describe risk or restrictions, but do not reliably confirm whether the passage is open or closed."
    else:
        operational = "NO_RECENT_CONFIRMATION"
        summary_es = "No se ha encontrado una confirmación operativa reciente y suficientemente sólida."
        summary_en = "No sufficiently strong and recent operational confirmation has been found."
    labels = {
        "CLOSURE_DECLARED_UNCONFIRMED": ("Cierre declarado, no confirmado", "Closure declared, not operationally confirmed"),
        "HIGH_RISK_UNCONFIRMED": ("Riesgo elevado, estado no confirmado", "High risk, status unconfirmed"),
        "NO_RECENT_CONFIRMATION": ("Sin confirmación reciente", "No recent confirmation"),
    }
    current["status"] = "INCIERTO"
    current["operational_status"] = operational
    current["operational_label_es"], current["operational_label_en"] = labels[operational]
    current["confidence"] = "BAJA"
    current["summary_es"] = summary_es
    current["summary_en"] = summary_en
    current["last_change_at"] = iso_z(utc_now())
    current["last_valid_confirmation"] = None
    current["editorial_review_required"] = True


def copy_previous_public_state(current: dict[str, Any], previous: dict[str, Any]) -> None:
    for key in (
        "status", "operational_status", "operational_label_es", "operational_label_en",
        "confidence", "summary_es", "summary_en", "last_change_at",
        "last_valid_confirmation", "evidence",
    ):
        if key in previous:
            current[key] = previous[key]


def main() -> int:
    # ORMUZ_V3_FINAL_GUARD: ABIERTO/CERRADO se revalida en cada ciclo.
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, default=Path("status.json"))
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=Path("editorial-review.json"))
    parser.add_argument("--aliases", type=Path, default=Path("source_aliases.json"))
    parser.add_argument("--change-file", type=Path)
    parser.add_argument("--rollback-unsafe", action="store_true", default=True)
    parser.add_argument("--fail-unsafe", action="store_true")
    parser.add_argument("--no-restore-generated", action="store_true")
    args = parser.parse_args()

    current = load_json(args.status, {})
    previous = load_json(args.previous, {})
    if not isinstance(current, dict) or not isinstance(previous, dict):
        print("ERROR: status actual o anterior no es un objeto JSON válido.")
        return 2
    for key, allowed in (("status", VALID_STATUS), ("operational_status", VALID_OPERATIONAL), ("confidence", VALID_CONFIDENCE)):
        if current.get(key) not in allowed:
            print(f"ERROR: {key} contiene un valor no permitido: {current.get(key)!r}")
            return 2

    notes = normalize_sources(current, args.aliases)
    changed_state = status_tuple(current) != status_tuple(previous)
    desired = str(current.get("status"))
    supported, supporting, reasons = support_transition(current, desired)
    needs_review = desired in {"ABIERTO", "CERRADO"} and not supported

    if needs_review:
        candidate = {
            "status": current.get("status"),
            "operational_status": current.get("operational_status"),
            "confidence": current.get("confidence"),
            "last_change_at": current.get("last_change_at"),
        }
        candidate_evidence = list(iter_evidence(current))[:8]
        previous_status = str(previous.get("status") or "")
        previous_supported, _, previous_reasons = support_transition(previous, previous_status)
        can_restore_previous = changed_state and previous_status in VALID_STATUS and previous_supported
        restored: list[str] = []
        if can_restore_previous and not args.fail_unsafe:
            if not args.no_restore_generated:
                restored = restore_stateful_files(args.status.resolve().parent)
            copy_previous_public_state(current, previous)
            decision = "BLOCKED_AND_ROLLED_BACK"
            message = "AVISO: transición no respaldada; se restauró una clasificación anterior respaldada."
        else:
            downgrade_to_uncertain(current, reasons)
            decision = "DOWNGRADED_TO_UNCERTAIN"
            message = "AVISO: la clasificación vigente no tiene respaldo operativo suficiente; se rebajó a INCIERTO."

        current["editorial_review_required"] = True
        current["candidate_classification"] = candidate
        diagnostics = current.setdefault("diagnostics", {})
        if not isinstance(diagnostics, dict):
            diagnostics = {}
            current["diagnostics"] = diagnostics
        diagnostics["editorial_guard"] = {
            "blocked": True,
            "decision": decision,
            "checked_at": iso_z(utc_now()),
            "reasons": reasons[:8],
            "previous_reasons": previous_reasons[:5],
            "restored_files": restored,
        }
        report = {
            "version": 3,
            "generated_at": iso_z(utc_now()),
            "decision": decision,
            "candidate": candidate,
            "published_classification": {
                "status": current.get("status"),
                "operational_status": current.get("operational_status"),
                "confidence": current.get("confidence"),
            },
            "reasons": reasons[:20],
            "previous_reasons": previous_reasons[:10],
            "source_normalizations": notes[:30],
            "supporting_evidence": supporting[:6],
            "candidate_evidence": candidate_evidence,
        }
        atomic_write_json(args.review, report)
        atomic_write_json(args.status, current, compact=False)
        if args.change_file and args.change_file.exists():
            args.change_file.unlink(missing_ok=True)
        print(message)
        for reason in reasons[:8]:
            print(f" - {reason}")
        write_github_output(True, len(notes))
        return 1 if args.fail_unsafe else 0

    current.pop("editorial_review_required", None)
    current.pop("candidate_classification", None)
    diagnostics = current.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics.pop("editorial_guard", None)
    atomic_write_json(args.status, current, compact=False)
    if args.review.exists():
        args.review.unlink(missing_ok=True)
    write_github_output(False, len(notes))
    if notes:
        print(f"Fuentes normalizadas de forma conservadora: {len(notes)}")
    if changed_state:
        print(f"Transición {status_tuple(previous)} → {status_tuple(current)} respaldada editorialmente.")
    elif desired in {"ABIERTO", "CERRADO"}:
        print("Clasificación vigente revalidada con evidencia operativa suficiente.")
    else:
        print("Estado conservador revisado.")
    return 0
'''

TEST_FILE = r'''from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import evidence_guard
import update_status


class FinalEditorialGuardTests(unittest.TestCase):
    def test_ona_does_not_match_inside_national(self) -> None:
        self.assertIsNone(update_status.source_profile("National Desk"))
        profile = update_status.source_profile("Oman News Agency")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.source_id, "oman_news")

    def test_national_security_journal_is_non_official(self) -> None:
        profile = update_status.source_profile("National Security Journal")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.source_id, "national_security_journal")
        self.assertFalse(profile.official)
        self.assertEqual(profile.tier, 2)

    def test_analytical_open_headline_is_not_operational_proof(self) -> None:
        title = "CENTCOM Keeps Insisting the Strait of Hormuz Is Open — but Shipping Traffic Has Collapsed"
        signals = update_status.classify_text(title)
        self.assertNotIn("OPEN_OPERATIONAL", signals)
        self.assertIn("RISK_RESTRICTION", signals)

    def test_question_is_not_operational_proof(self) -> None:
        signals = update_status.classify_text("Why Can't Donald Trump Keep the Strait of Hormuz Open?")
        self.assertNotIn("OPEN_OPERATIONAL", signals)

    def test_factual_description_can_confirm_transit(self) -> None:
        signals = update_status.classify_text(
            "Is the Strait of Hormuz open?",
            "UKMTO reports commercial shipping continues through the Strait of Hormuz.",
        )
        self.assertIn("OPEN_OPERATIONAL", signals)

    def test_risk_item_never_becomes_last_valid_confirmation(self) -> None:
        now = update_status.utc_now()
        risk = {
            "signal": "RISK_RESTRICTION", "title": "U.S. forces complete another night of strikes",
            "description": "", "source_name": "U.S. CENTCOM", "source_id": "centcom",
            "source_url": "https://centcom.mil/example", "published_at": update_status.iso_z(now),
            "tier": 5, "official": True, "score": 5.0,
        }
        payload = update_status.finalize_payload(
            previous={}, now=now, status="ABIERTO", operational="OPEN_RESTRICTED",
            confidence="BAJA", summary_es="x", summary_en="x", evidence=[risk],
            verification_ok=True, diagnostics={},
        )
        self.assertIsNone(payload["last_valid_confirmation"])

    def test_invalid_previous_confirmation_is_not_carried(self) -> None:
        now = update_status.utc_now()
        previous = {
            "engine_version": update_status.ENGINE_VERSION, "status": "ABIERTO",
            "last_valid_confirmation": {
                "status": "ABIERTO", "at": update_status.iso_z(now - timedelta(hours=1)),
                "source_name": "U.S. CENTCOM", "source_url": "https://centcom.mil/example",
                "title": "U.S. forces complete another night of strikes",
            },
        }
        self.assertFalse(update_status.previous_is_carryable(previous, now, 18))

    def test_guard_downgrades_unchanged_unsupported_open_state(self) -> None:
        now = update_status.iso_z(update_status.utc_now())
        payload = {
            "engine_version": 3, "status": "ABIERTO", "operational_status": "OPEN_RESTRICTED",
            "confidence": "ALTA", "checked_at": now, "last_change_at": now,
            "verification_ok": True,
            "evidence": [{
                "signal": "RISK_RESTRICTION", "title": "Shipping traffic has collapsed amid attacks",
                "source_name": "Reuters", "source_url": "https://reuters.com/example",
                "published_at": now, "tier": 4, "official": False,
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status, previous, review, aliases = [root / name for name in ("status.json", "previous.json", "review.json", "aliases.json")]
            status.write_text(json.dumps(payload), encoding="utf-8")
            previous.write_text(json.dumps(payload), encoding="utf-8")
            aliases.write_text(json.dumps({"version": 2, "official_publishers": {}, "publishers": {}}), encoding="utf-8")
            argv = ["evidence_guard.py", "--status", str(status), "--previous", str(previous), "--review", str(review), "--aliases", str(aliases), "--no-restore-generated"]
            with patch.object(sys, "argv", argv), patch.dict(os.environ, {}, clear=False):
                result = evidence_guard.main()
            self.assertEqual(result, 0)
            updated = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual(updated["status"], "INCIERTO")
            self.assertEqual(updated["operational_status"], "HIGH_RISK_UNCONFIRMED")
            self.assertIsNone(updated["last_valid_confirmation"])
            self.assertTrue(review.exists())


if __name__ == "__main__":
    unittest.main()
'''


class PatchError(RuntimeError):
    pass


def ensure_files() -> None:
    missing = [str(path.relative_to(ROOT)) for key, path in FILES.items() if key != "tests" and not path.exists()]
    if missing:
        raise PatchError("Faltan archivos necesarios: " + ", ".join(missing))
    engine = FILES["engine"].read_text(encoding="utf-8")
    guard = FILES["guard"].read_text(encoding="utf-8")
    if len(engine.splitlines()) < 1300 or "ENGINE_VERSION = 3" not in engine:
        raise PatchError("update_status.py no parece ser el motor completo V3.")
    if len(guard.splitlines()) < 250 or "def support_transition(" not in guard:
        raise PatchError("evidence_guard.py no parece ser la versión de mantenimiento V2.")


def replace_top_level_function(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    if len(matches) != 1:
        raise PatchError(f"Se esperaba una función {name!r}; se encontraron {len(matches)}.")
    node = matches[0]
    if node.end_lineno is None:
        raise PatchError(f"No se pudo delimitar la función {name!r}.")
    lines = source.splitlines(keepends=True)
    return "".join(lines[:node.lineno - 1] + [replacement.rstrip() + "\n\n"] + lines[node.end_lineno:])


def insert_source_profile(source: str) -> str:
    if '"national_security_journal"' in source:
        return source
    start = source.find("SOURCE_PROFILES = (")
    end = source.find("\n)\n\nPROFILE_BY_ALIAS", start)
    if start < 0 or end < 0:
        raise PatchError("No se pudo localizar SOURCE_PROFILES.")
    return source[:end] + "\n" + SOURCE_PROFILE.rstrip() + source[end:]


def patch_engine(source: str) -> str:
    if MARKER in source:
        return source
    source = insert_source_profile(source)
    source = replace_top_level_function(source, "source_profile", SOURCE_PROFILE_FUNCTION)
    source = replace_top_level_function(source, "classify_text", CLASSIFY_FUNCTIONS)
    source = replace_top_level_function(source, "previous_is_carryable", CARRY_FUNCTIONS)
    source = replace_top_level_function(source, "finalize_payload", FINALIZE_FUNCTION)
    ast.parse(source)
    compile(source, str(FILES["engine"]), "exec")
    for token in (MARKER, '"national_security_journal"', "def confirmation_supports_status("):
        if token not in source:
            raise PatchError(f"Validación del motor incompleta: falta {token!r}.")
    return source


def patch_guard(source: str) -> str:
    if MARKER in source:
        return source
    source = replace_top_level_function(source, "direct_evidence", GUARD_DIRECT_FUNCTIONS)
    source = replace_top_level_function(source, "main", GUARD_MAIN)
    ast.parse(source)
    compile(source, str(FILES["guard"]), "exec")
    for token in (MARKER, "def downgrade_to_uncertain(", "Clasificación vigente revalidada"):
        if token not in source:
            raise PatchError(f"Validación del cortafuegos incompleta: falta {token!r}.")
    return source


def patch_aliases(text: str) -> str:
    data = json.loads(text)
    publishers = data.setdefault("publishers", {})
    if not isinstance(publishers, dict):
        raise PatchError("El campo publishers no es un objeto.")
    entry = {"name": "National Security Journal", "tier": 2}
    publishers["national security journal"] = entry
    publishers["nationalsecurityjournal.org"] = entry
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def patch_workflow(text: str) -> str:
    if "tests/test_final_guard.py" not in text:
        old = "for test_file in test_decision_engine.py test_v11.py tests/test_maintenance.py; do"
        new = "for test_file in test_decision_engine.py test_v11.py tests/test_maintenance.py tests/test_final_guard.py; do"
        if old not in text:
            raise PatchError("No se encontró la lista de pruebas del workflow.")
        text = text.replace(old, new, 1)
    step_name = "Reconstruir portadas tras el cortafuegos editorial"
    if step_name not in text:
        anchor = "      - name: Instalar mejoras de interfaz existentes\n"
        if anchor not in text:
            raise PatchError("No se encontró el punto de inserción del workflow.")
        step = '''      - name: Reconstruir portadas tras el cortafuegos editorial
        run: |
          if [ -f postprocess_evidence.py ]; then
            python postprocess_evidence.py
          else
            echo "postprocess_evidence.py no existe; se omite."
          fi

'''
        text = text.replace(anchor, step + anchor, 1)
    return text


def create_backup(paths: Iterable[Path]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = ROOT.parent / f"respaldo_ormuz_antes_v3_{timestamp}.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            if path.exists():
                archive.write(path, arcname=str(path.relative_to(ROOT)))
    return destination


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".v3tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def run_tests() -> None:
    for file in (FILES["engine"], FILES["guard"], ROOT / "maintenance_common.py", FILES["tests"]):
        py_compile.compile(str(file), doraise=True)
    command = [sys.executable, "-m", "unittest", "-v", "test_decision_engine.py", "tests/test_maintenance.py", "tests/test_final_guard.py"]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise PatchError("Las pruebas no han terminado correctamente.")


def apply() -> None:
    ensure_files()
    original = {key: path.read_text(encoding="utf-8") for key, path in FILES.items() if path.exists()}
    backup = create_backup(path for key, path in FILES.items() if key != "tests")
    try:
        atomic_write(FILES["engine"], patch_engine(original["engine"]))
        atomic_write(FILES["guard"], patch_guard(original["guard"]))
        atomic_write(FILES["aliases"], patch_aliases(original["aliases"]))
        atomic_write(FILES["workflow"], patch_workflow(original["workflow"]))
        atomic_write(FILES["tests"], TEST_FILE)
        run_tests()
    except Exception:
        for key, content in original.items():
            atomic_write(FILES[key], content)
        if "tests" not in original and FILES["tests"].exists():
            FILES["tests"].unlink()
        raise
    print("\nMEJORA FINAL V3 APLICADA CORRECTAMENTE")
    print(f"Respaldo creado fuera del repositorio: {backup}")
    for key in ("engine", "guard", "aliases", "workflow", "tests"):
        print(f" - {FILES[key].relative_to(ROOT)}")
    print("\nSiguiente paso: ejecutar Actions > Actualizar estado de Ormuz > Run workflow.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ensure_files()
    if not args.apply:
        print("Repositorio compatible. Ejecuta con --apply para modificarlo.")
        return 0
    try:
        apply()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
