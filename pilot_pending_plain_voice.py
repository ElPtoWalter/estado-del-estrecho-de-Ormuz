"""One bounded native-voice candidate from the published 1.1 script contract.

Historical test, not live news. Credentials remain in the runner environment;
no billing activation, fallback, retries, publication or final human approval.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--observed-free-at")
    args = parser.parse_args()
    root, output = args.repo.resolve(), args.output.resolve()
    if output == root or output.is_relative_to(root) or output.exists():
        raise ValueError("NEW_EXTERNAL_OUTPUT_REQUIRED")
    sys.path.insert(0, str(root))
    from phase2_voice.fixtures import load_pilot_fixture
    from phase2_video.script import generate_script
    from phase2_video.validator import validate_package, validate_script
    from prepare_phase2a_ormuz_es import revise_editorial_input
    from phase2_voice.schema import load_pronunciation, VoiceError
    from phase2_voice.pipeline import run_voice_job, write_json
    package, legacy, fixture = load_pilot_fixture("ormuz")
    package, _, _ = revise_editorial_input(package, legacy)
    script, trace = generate_script(package, gemini_key="", openrouter_key="")
    if (validate_package(package)["validation_status"] != "PASS" or
            validate_script(package, script)["validation_status"] != "PASS" or
            script["schema_version"] != "1.1.0" or
            script["script_id"] != "video-script:89e3a19b8c5668d3272fc0d7784fc6f5896cb3425699be7cfdb69014b9a8958d"):
        raise ValueError("PUBLISHED_SCRIPT_CHANGED")
    rules = load_pronunciation()
    rules["version"] = "STRAITWATCH_HUTIES_USER_RULE_20261004"
    rules["review_terms"] = sorted(set(rules["review_terms"]) | {"utíes"})
    rules["overrides"] = [{
        "language": "es", "term": "hutíes", "spoken": "utíes", "human_reviewed": True,
        "review_note": "El usuario rechazó jutíes y pidió utíes, con h muda, el 04/10/2026. Regla fonética revisada por el usuario; audio candidato NO aprobado.",
    }]
    # The immutable editorial script and all on-screen text retain hutíes.
    fixture = {**fixture, "historical_fixture": True,
               "fixture_source": "Validated historical Ormuz package; newly generated Spanish script 1.1, not current news"}
    billing = {"provider": "gemini", "project": "gen-lang-client-0254781554",
               "observed_tier": "free", "billing_changed": False,
               "pricing_source": "https://ai.google.dev/gemini-api/docs/pricing",
               "account_tier_verified": False, "generation_requests": 0,
               "automatic_retry": False, "audio_human_review": "PENDING", "publication_allowed": False}
    if args.generate:
        if not args.observed_free_at:
            raise ValueError("FRESH_FREE_OBSERVATION_REQUIRED")
        observed = datetime.fromisoformat(args.observed_free_at.replace("Z", "+00:00"))
        if not 0 <= (datetime.now(timezone.utc) - observed).total_seconds() <= 1200:
            raise ValueError("FREE_OBSERVATION_EXPIRED")
        # Bind the key to the exact existing free-tier project seen in the UI.
        # Never output the credential, including on mismatch or provider failure.
        if not os.getenv("GEMINI_API_KEY", "").endswith("Vdrg"):
            raise ValueError("WRONG_EXISTING_FREE_PROJECT_KEY")
        billing.update(observed_at_utc=args.observed_free_at, account_tier_verified=True,
                       generation_requests=1)
    report = run_voice_job(package, script, output, repo_root=root, pronunciation=rules,
                           fixture=fixture, prepare_only=not args.generate)
    write_json(output / "pronunciation-rules.json", rules)
    write_json(output / "manual-generation-audit.json", {**billing, "script_generation": trace,
               "human_rejected_previous_audio": True, "previous_audio_reused": False,
               "editorial_text_changed": False, "phonetic_override_only": True,
               "technical_status": report["validation_status"]})
    print(json.dumps({"technical_status": report["validation_status"], "historical_fixture": True,
                      "generation_requests": billing["generation_requests"],
                      "publication_allowed": False, "audio_human_review": "PENDING"}))
    return 0 if report["validation_status"] in {"READY", "PASS"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        code = getattr(exc, "code", "") or (str(exc) if isinstance(exc, ValueError) else "")
        code = code if re.fullmatch(r"[A-Z0-9_]+", code) else "SANITIZED_PILOT_FAILURE"
        print(json.dumps({"technical_status": "FAIL", "error": code, "automatic_retry": False}))
        raise SystemExit(1)

