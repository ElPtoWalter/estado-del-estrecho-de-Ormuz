#!/usr/bin/env python3
"""Install Operational Intelligence V7 without replacing the legacy engine."""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "operational_v7_payload.zip"
INSTALL_V11 = ROOT / "install_v11.py"
WIDGET_JS = ROOT / "widget.js"
SOCIAL_JS = ROOT / "social-studio.js"
DAILY = ROOT / "generate_daily_brief.py"
REPORT = ROOT / "operational-v7-readiness.json"
MARKER = "OPERATIONAL_INTELLIGENCE_V7_HOOK"


class InstallError(RuntimeError):
    pass


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def stable_write(path: Path, content: str) -> None:
    previous = read(path) if path.exists() else None
    if previous != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(args), cwd=ROOT, text=True, check=False)
    if check and result.returncode != 0:
        raise InstallError(f"{' '.join(args)} failed with exit code {result.returncode}")
    return result


def extract_payload() -> list[str]:
    if not PAYLOAD.exists():
        raise InstallError("operational_v7_payload.zip is missing")
    names: list[str] = []
    with zipfile.ZipFile(PAYLOAD) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            rel = Path(info.filename)
            if rel.is_absolute() or ".." in rel.parts:
                raise InstallError(f"Unsafe payload entry: {info.filename}")
            target = ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            names.append(rel.as_posix())
    return names


def patch_installer(source: str) -> str:
    if MARKER in source:
        return source
    main_pos = source.find("def main()")
    if main_pos < 0:
        main_pos = source.find("def main(")
    if main_pos < 0:
        raise InstallError("install_v11.py has no main()")
    needle = "    update_sitemap()\n"
    pos = source.find(needle, main_pos)
    if pos < 0:
        raise InstallError("Could not find update_sitemap() hook point in install_v11.py")
    hook = '''    # OPERATIONAL_INTELLIGENCE_V7_HOOK\n    try:\n        import operational_intelligence_v7\n        operational_intelligence_v7.run(ROOT)\n    except Exception as exc:\n        print(f"AVISO: Operational Intelligence V7 no aplicado: {exc}")\n\n'''
    updated = source[:pos] + hook + source[pos:]
    compile(updated, str(INSTALL_V11), "exec")
    return updated


def patch_home_assets(path: Path) -> None:
    if not path.exists():
        return
    text = read(path)
    if "/operational-v7.css" not in text:
        text = re.sub(
            r"</head>",
            '<link href="/operational-v7.css" rel="stylesheet"/>\n</head>',
            text,
            count=1,
            flags=re.I,
        )
    if "/operational-v7.js" not in text:
        text = re.sub(
            r"</head>",
            '<script defer src="/operational-v7.js"></script>\n</head>',
            text,
            count=1,
            flags=re.I,
        )
    stable_write(path, text)


def patch_widget(source: str) -> str:
    if "OPERATIONAL_INTELLIGENCE_V7_WIDGET" in source:
        return source
    old = '''      const status = data.status || 'INCIERTO';\n      const operational = lang === 'en' ? data.operational_label_en : data.operational_label_es;\n      $('[data-state]').textContent = operational || labels[status === 'ABIERTO' ? 'open' : status === 'CERRADO' ? 'closed' : 'uncertain'];\n      $('[data-state]').classList.add(status === 'ABIERTO' ? 'g4-status-open' : status === 'CERRADO' ? 'g4-status-closed' : 'g4-status-uncertain');\n      $('[data-summary]').textContent = lang === 'en' ? data.summary_en : data.summary_es;\n      $('[data-confidence]').textContent = data.confidence || '—';\n      const date = data.checked_at ? new Date(data.checked_at) : null;\n'''
    new = '''      // OPERATIONAL_INTELLIGENCE_V7_WIDGET\n      const oi = data.operational_intelligence;\n      const status = oi && oi.state ? (oi.family === 'OPEN' ? 'ABIERTO' : oi.family === 'CLOSED' ? 'CERRADO' : 'INCIERTO') : (data.status || 'INCIERTO');\n      const operational = oi && oi.state ? (lang === 'en' ? oi.label_en : oi.label_es) : (lang === 'en' ? data.operational_label_en : data.operational_label_es);\n      $('[data-state]').textContent = operational || labels[status === 'ABIERTO' ? 'open' : status === 'CERRADO' ? 'closed' : 'uncertain'];\n      $('[data-state]').classList.add(status === 'ABIERTO' ? 'g4-status-open' : status === 'CERRADO' ? 'g4-status-closed' : 'g4-status-uncertain');\n      $('[data-summary]').textContent = oi && oi.state ? (lang === 'en' ? oi.summary_en : oi.summary_es) : (lang === 'en' ? data.summary_en : data.summary_es);\n      $('[data-confidence]').textContent = (oi && oi.state ? oi.confidence : data.confidence) || '—';\n      const effectiveCheckedAt = oi && oi.state ? (oi.generated_at || data.checked_at) : data.checked_at;\n      const date = effectiveCheckedAt ? new Date(effectiveCheckedAt) : null;\n'''
    if old not in source:
        raise InstallError("widget.js no longer matches the expected Growth V4 structure")
    return source.replace(old, new, 1)


def patch_social(source: str) -> str:
    if "OPERATIONAL_INTELLIGENCE_V7_SOCIAL" in source:
        return source
    old = "  fetch('/status.json?studio='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{statusData=d;render();});"
    new = """  fetch('/status.json?studio='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{\n    // OPERATIONAL_INTELLIGENCE_V7_SOCIAL\n    const oi=d.operational_intelligence;\n    if(oi&&oi.state){\n      d.status=oi.family==='OPEN'?'ABIERTO':oi.family==='CLOSED'?'CERRADO':'INCIERTO';\n      d.operational_label_es=oi.label_es;d.operational_label_en=oi.label_en;\n      d.summary_es=oi.summary_es;d.summary_en=oi.summary_en;\n      d.confidence=oi.confidence;d.checked_at=oi.generated_at||d.checked_at;\n    }\n    statusData=d;render();\n  });"""
    if old not in source:
        raise InstallError("social-studio.js no longer matches the expected Growth V4 structure")
    return source.replace(old, new, 1)


DAILY_HELPER = r'''def apply_operational_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    """Use V7 public assessment for the human-facing daily brief only."""
    if not isinstance(data, dict):
        return data
    oi = data.get("operational_intelligence")
    if not isinstance(oi, dict) or not oi.get("state"):
        return data
    output = dict(data)
    family = oi.get("family")
    output["status"] = "ABIERTO" if family == "OPEN" else "CERRADO" if family == "CLOSED" else "INCIERTO"
    state = str(oi.get("state") or "")
    output["operational_status"] = (
        "OPEN_NORMAL" if state == "OPEN_NORMAL"
        else "OPEN_RESTRICTED" if family == "OPEN"
        else "CLOSED_CONFIRMED" if family == "CLOSED"
        else "HIGH_RISK_UNCONFIRMED"
    )
    output["operational_label_es"] = oi.get("label_es") or output.get("operational_label_es")
    output["operational_label_en"] = oi.get("label_en") or output.get("operational_label_en")
    output["summary_es"] = oi.get("summary_es") or output.get("summary_es")
    output["summary_en"] = oi.get("summary_en") or output.get("summary_en")
    output["confidence"] = oi.get("confidence") or output.get("confidence")
    output["checked_at"] = oi.get("generated_at") or output.get("checked_at")
    return output
'''


def patch_daily(source: str) -> str:
    if "def apply_operational_intelligence(" not in source:
        anchor = "def main() -> int:"
        pos = source.find(anchor)
        if pos < 0:
            raise InstallError("generate_daily_brief.py has no main()")
        source = source[:pos] + DAILY_HELPER + "\n" + source[pos:]
    pattern = re.compile(r'(\n\s*status\s*=\s*load_json\("status\.json",\{\}\)\s*\n)')
    match = pattern.search(source)
    if not match:
        raise InstallError("Could not locate status load in generate_daily_brief.py")
    if "status=apply_operational_intelligence(status)" not in source and "status = apply_operational_intelligence(status)" not in source:
        indent_match = re.match(r'\n(\s*)status', match.group(1))
        indent = indent_match.group(1) if indent_match else "    "
        source = source[:match.end()] + f"{indent}status=apply_operational_intelligence(status)\n" + source[match.end():]
    compile(source, str(DAILY), "exec")
    return source


def patch_llms() -> None:
    path = ROOT / "llms.txt"
    if not path.exists():
        return
    text = read(path)
    marker = "## Operational Intelligence V7"
    if marker not in text:
        text = text.rstrip() + "\n\n" + marker + "\n"
        text += "- Metodología operativa: https://estrechoormuz.com/metodo-inteligencia-operativa.html\n"
        text += "- Operational method: https://estrechoormuz.com/en-operational-intelligence-method.html\n"
        text += "- Live operational intelligence JSON: https://estrechoormuz.com/operational-intelligence.json\n"
        stable_write(path, text)


def run_initial_assessment() -> dict[str, Any]:
    run(sys.executable, "-m", "unittest", "-v", "test_operational_intelligence_v7.py")
    run(sys.executable, "operational_intelligence_v7.py", "--root", ".", "--offline")
    return json.loads((ROOT / "operational-intelligence.json").read_text(encoding="utf-8"))


def rebuild_sitemap() -> None:
    builder = ROOT / "build_sitemap.py"
    if builder.exists():
        run(sys.executable, "build_sitemap.py", "--root", ".")


def validate_repo() -> list[str]:
    warnings: list[str] = []
    validator = ROOT / "validate_site.py"
    if validator.exists():
        result = subprocess.run([sys.executable, "validate_site.py", "--root", "."], cwd=ROOT, text=True, check=False)
        if result.returncode != 0:
            raise InstallError("validate_site.py rejected the patched repository")
    for filename in ("index.html", "en.html"):
        text = read(ROOT / filename)
        if text.count("/operational-v7.js") != 1:
            raise InstallError(f"{filename}: operational-v7.js must appear exactly once")
        if text.count("/operational-v7.css") != 1:
            raise InstallError(f"{filename}: operational-v7.css must appear exactly once")
        if text.count("OPERATIONAL_INTELLIGENCE_V7_START") != 1:
            raise InstallError(f"{filename}: V7 block missing or duplicated")
    return warnings


def apply() -> None:
    required = [INSTALL_V11, WIDGET_JS, SOCIAL_JS, DAILY]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise InstallError("Missing required repository files: " + ", ".join(missing))

    extracted = extract_payload()
    stable_write(INSTALL_V11, patch_installer(read(INSTALL_V11)))
    patch_home_assets(ROOT / "index.html")
    patch_home_assets(ROOT / "en.html")
    stable_write(WIDGET_JS, patch_widget(read(WIDGET_JS)))
    stable_write(SOCIAL_JS, patch_social(read(SOCIAL_JS)))
    stable_write(DAILY, patch_daily(read(DAILY)))
    patch_llms()

    assessment = run_initial_assessment()
    rebuild_sitemap()
    warnings = validate_repo()

    ready = assessment.get("state") in {
        "OPEN_NORMAL", "OPEN_RESTRICTED", "OPEN_SEVERELY_RESTRICTED",
        "EFFECTIVELY_CLOSED", "CLOSED_CONFIRMED", "UNVERIFIED",
    }
    report = {
        "version": 7,
        "ready": bool(ready),
        "initial_assessment": {
            "state": assessment.get("state"),
            "label_es": assessment.get("label_es"),
            "label_en": assessment.get("label_en"),
            "confidence": assessment.get("confidence"),
            "dimensions": assessment.get("dimensions"),
            "source_counts": assessment.get("source_counts"),
        },
        "legacy_engine_replaced": False,
        "legacy_engine_preserved": True,
        "patched": [
            "install_v11.py", "widget.js", "social-studio.js",
            "generate_daily_brief.py", "index.html", "en.html", "llms.txt",
        ],
        "payload_files": extracted,
        "warnings": warnings,
    }
    stable_write(REPORT, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Operational Intelligence V7 installed successfully.")
    print(json.dumps(report["initial_assessment"], ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Run with --apply to install Operational Intelligence V7.")
        return 0
    try:
        apply()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
