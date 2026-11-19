"""Stage only declared generator outputs. A stale checkout fails without overwriting main."""
import argparse
import subprocess
from pathlib import Path, PurePosixPath

COMMON = {"daily-brief.json", "daily-brief-archive.json", "daily-brief-feed.xml", "daily-brief-feed-en.xml",
          "social-drafts.json", "feed.xml", "index.html", "en.html", "sitemap.xml", "robots.txt", "health.json"}
MONITOR = COMMON | {"status.json", "history.json", "events.json", "operational-intelligence.json",
                    "operational-intelligence-history.json", "historial.html", "en-history.html",
                    "evidencias.html", "en-evidence.html", "notification-outbox.json"}
JOURNAL = COMMON | {"diario.html", "en-diary.html", "events.json", "journal-latest.json", "journal-archive.json", "journal-check.json",
                    "journal-state.json", "journal-health.json", "journal-social-draft.json", "diario-feed.xml", "diary-feed.xml"}


def allowed(path, mode):
    parts = PurePosixPath(path).parts
    if path in (MONITOR if mode == "monitor" else JOURNAL):
        return True
    if len(parts) == 2 and parts[0] in {"briefs", "briefs-en", "diario", "diary", "journal-data"}:
        import re
        return bool(re.fullmatch(r"(?:\d{4}-\d{2}-\d{2}|index)\.(?:html|json)", parts[1]))
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["monitor", "journal"])
    args = parser.parse_args()
    run = lambda *cmd: subprocess.check_output(cmd, text=True).strip()
    paths = set(run("git", "diff", "--name-only").splitlines())
    paths.update(run("git", "ls-files", "--others", "--exclude-standard").splitlines())
    paths.discard("")
    unexpected = sorted(p for p in paths if not allowed(p, args.mode))
    if unexpected:
        raise SystemExit("Unexpected generated paths; nothing staged: " + ", ".join(unexpected))
    if paths:
        subprocess.run(["git", "add", "--", *sorted(paths)], check=True)
    print(f"Declared outputs staged: {len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
