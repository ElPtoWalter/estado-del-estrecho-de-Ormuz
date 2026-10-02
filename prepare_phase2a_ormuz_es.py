"""One explicitly authorized Phase 2A editorial revision; never a TTS rewrite."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

from phase2_video.schema import package_content_hash, package_id, script_id
from phase2_video.validator import validate_package, validate_script
from phase2_voice.fixtures import load_pilot_fixture
from phase2_voice.pipeline import audit_output

ROOT = Path(__file__).resolve().parent
SOURCE_PACKAGE_ID = "video-package:ormuz:2026-09-21:c62123682b8782326e7bf81dd49aa5fada7220933a8e36a6419891f2ac78b8e0"
SOURCE_SCRIPT_ID = "video-script:6dddb8b7362bdd2530a3bb8e35f330e8d038b3c3ca734561ca00c441acb86588"
SOURCE_TITLE = "Iran and US trade threats after Houthi attacks escalate regional conflict - reuters.com"
TITLE_ES = "Irán y Estados Unidos intercambian amenazas tras ataques hutíes que agravan el conflicto regional"
FACT_ID = "fact-a0b4364f38881c5f"
WORD_RE = re.compile(r"\b[\wáéíóúüñ'-]+\b", re.I)


def revise_editorial_input(package: dict, script: dict) -> tuple[dict, dict, dict]:
    """Preserve source evidence; mint new package/script identities for ES prose."""
    if validate_package(package)["validation_status"] != "PASS" or validate_script(package, script)["validation_status"] != "PASS":
        raise ValueError("INVALID_EDITORIAL_SOURCE")
    if package["package_id"] != SOURCE_PACKAGE_ID or script["script_id"] != SOURCE_SCRIPT_ID:
        raise ValueError("UNAUTHORIZED_EDITORIAL_SOURCE")
    fact = package["verified_facts"][0]
    first = script["scenes"][0]
    if (
        fact["fact_id"] != FACT_ID or fact["text_es"] != SOURCE_TITLE
        or fact["text_en"] != SOURCE_TITLE or package["headlines"]["es"] != SOURCE_TITLE
        or package["what_we_know"] != [SOURCE_TITLE] or script["headline"] != SOURCE_TITLE
        or first["voiceover"] != "El principal hecho verificado de esta actualización es: " + SOURCE_TITLE
        or first["on_screen_text"] != SOURCE_TITLE
    ):
        raise ValueError("EDITORIAL_SOURCE_CONTENT_MISMATCH")

    revised_package, revised_script = copy.deepcopy(package), copy.deepcopy(script)
    # This is the ES rendering of the SAME fact, not a new verification.
    # Raw EN title, fact/event/source IDs, URLs, verification, dates, operational
    # state and uncertainty all remain untouched. The original fixture is kept.
    revised_package["headlines"]["es"] = TITLE_ES
    revised_package["verified_facts"][0]["text_es"] = TITLE_ES
    revised_package["what_we_know"][0] = TITLE_ES
    revised_package["content_hash"] = package_content_hash(revised_package)
    revised_package["package_id"] = package_id("ormuz", package["edition_date"], revised_package["content_hash"])
    revised_script["package_id"] = revised_package["package_id"]
    revised_script["package_content_hash"] = revised_package["content_hash"]
    revised_script["headline"] = TITLE_ES
    revised_script["scenes"][0]["voiceover"] = "El principal hecho verificado de esta actualización es: " + TITLE_ES
    revised_script["scenes"][0]["on_screen_text"] = TITLE_ES
    spoken = " ".join([revised_script["hook"], *(row["voiceover"] for row in revised_script["scenes"]), revised_script["outro"]])
    revised_script["estimated_words"] = len(WORD_RE.findall(spoken))
    revised_script["script_id"] = script_id(revised_script)
    if validate_package(revised_package)["validation_status"] != "PASS" or validate_script(revised_package, revised_script)["validation_status"] != "PASS":
        raise ValueError("INVALID_EDITORIAL_REVISION")
    audit = {
        "revision_id": "ormuz-es-20261002-v1", "layer": "phase2a", "language": "es",
        "authorized_action": "User authorized correcting the English headline in Phase 2A, revalidating and regenerating only Ormuz on 2026-10-02.",
        "translation_method": "explicit_deterministic_editorial_revision_no_model_call",
        "human_review_status": "PENDING", "source_package_id": package["package_id"],
        "source_script_id": script["script_id"], "revised_package_id": revised_package["package_id"],
        "revised_script_id": revised_script["script_id"], "fact_id": FACT_ID,
        "original_title": SOURCE_TITLE, "title_es": TITLE_ES,
        "changed_package_paths": ["headlines.es", "verified_facts[0].text_es", "what_we_know[0]", "content_hash", "package_id"],
        "changed_script_paths": ["headline", "scenes[0].voiceover", "scenes[0].on_screen_text", "package_id", "package_content_hash", "estimated_words", "script_id"],
        "original_en_evidence_preserved": True, "operational_context_unchanged": True,
        "source_traceability_unchanged": True, "upstream_validation": "PASS",
    }
    return revised_package, revised_script, audit


def prepare_revision(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir == ROOT or output_dir.is_relative_to(ROOT):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    if output_dir.exists():
        raise ValueError("EDITORIAL_OUTPUT_ALREADY_EXISTS")
    package, script, provenance = load_pilot_fixture("ormuz")
    package, script, revision = revise_editorial_input(package, script)
    fixture = {**provenance, "editorial_revision": revision}
    report = {
        "validation_status": "PASS", "human_review_status": "PENDING", "publication": "DISABLED",
        "package_validation": validate_package(package), "script_validation": validate_script(package, script),
        "fixture": fixture,
    }
    artifacts = {"video-package.json": package, "script.json": script, "validation-report.json": report}
    serialized = {name: json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n" for name, value in artifacts.items()}
    for value in serialized.values():
        audit_output(value)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, text in serialized.items():
        (output_dir / name).write_text(text, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = prepare_revision(args.output_dir)
    except ValueError as exc:
        print(json.dumps({"validation_status": "FAIL", "validation_errors": [str(exc)]}))
        return 1
    except Exception:
        print(json.dumps({"validation_status": "FAIL", "validation_errors": ["EDITORIAL_INPUT_OR_INTERNAL_ERROR"]}))
        return 1
    print(json.dumps({"validation_status": report["validation_status"], "revision_id": report["fixture"]["editorial_revision"]["revision_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
