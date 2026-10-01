#!/usr/bin/env python3
"""Manual Phase 2B pilot; real Phase 2A material, Gemini TTS, no publication."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from phase2_voice.fixtures import load_pilot_fixture
from phase2_voice.pipeline import run_voice_job
from phase2_voice.schema import VoiceError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=("ormuz", "gibraltar"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--fixture-metadata", type=Path, help="Previous prepared validation report; preserves historical labelling.")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix=f"straitwatch-{args.site}-phase2b-"))
    try:
        if bool(args.package) != bool(args.script):
            raise VoiceError("PACKAGE_AND_SCRIPT_REQUIRED_TOGETHER")
        if args.package:
            package = json.loads(args.package.read_text(encoding="utf-8"))
            script = json.loads(args.script.read_text(encoding="utf-8"))
            fixture = {"historical_fixture": "NOT_DECLARED", "fixture_source": "provided Phase 2A package and script"}
            if args.fixture_metadata:
                fixture = json.loads(args.fixture_metadata.read_text(encoding="utf-8"))["fixture"]
        else:
            # Real validated Phase 2A pilots frozen before the live event store
            # rotates. No rewritten script, invented fixture or editorial call.
            package, script, fixture = load_pilot_fixture(args.site)
        if package.get("site") != args.site:
            raise VoiceError("SITE_MISMATCH")
        report = run_voice_job(package, script, output, repo_root=args.root, fixture=fixture, prepare_only=args.prepare_only)
    except VoiceError as exc:
        print(json.dumps({"validation_status": "FAIL", "validation_errors": [exc.code]}))
        return 1
    except Exception:
        print(json.dumps({"validation_status": "FAIL", "validation_errors": ["PILOT_INPUT_OR_INTERNAL_ERROR"]}))
        return 1
    print(json.dumps({key: report[key] for key in ("voice_job_id", "validation_status", "validation_errors", "cache_hit")}, sort_keys=True))
    return 0 if report["validation_status"] in ("PASS", "READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
