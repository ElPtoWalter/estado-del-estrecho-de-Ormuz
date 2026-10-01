"""Frozen real Phase 2A pilot material, not today's newsroom state."""

import json
from pathlib import Path

from .input import validate_upstream
from .schema import VoiceError

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "phase2b-pilot-fixtures.json"


def load_pilot_fixture(site: str) -> tuple[dict, dict, dict]:
    try:
        store = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        if store["schema_version"] != "1.0.0":
            raise VoiceError("INVALID_REAL_FIXTURE")
        row = store["fixtures"][site]
        package, script, metadata = row["package"], row["script"], row["provenance"]
        if package["site"] != site or metadata["historical_fixture"] is not True:
            raise VoiceError("INVALID_REAL_FIXTURE")
        validate_upstream(package, script)
        return package, script, metadata
    except (OSError, KeyError, ValueError, TypeError):
        raise VoiceError("INVALID_REAL_FIXTURE") from None
