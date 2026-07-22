#!/usr/bin/env python3
"""Reparaciones HTML seguras y repetibles, sin rediseñar la web.

Corrige únicamente defectos mecánicos conocidos: metadatos fuera de head,
duplicados idénticos, target=_blank inseguro, URLs HTTP del propio dominio y
el selector CSS defectuoso detectado en la web.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from maintenance_common import atomic_write_text

EXCLUDED_DIRS = {".git", ".github", "node_modules", "tests", "test", "vendor", "tmp"}
BAD_SELECTOR = ".status-hero.is-loading .status-dot,status-hero.is-loading .status-word"
GOOD_SELECTOR = ".status-hero.is-loading .status-dot,.status-hero.is-loading .status-word"
ADSENSE_RE = re.compile(r'<meta\s+name=["\']google-adsense-account["\'][^>]*>', re.I)
HEAD_RE = re.compile(r"<head\b[^>]*>(.*?)</head\s*>", re.I | re.S)
TARGET_BLANK_RE = re.compile(r"<a\b([^>]*\btarget\s*=\s*([\"'])_blank\2[^>]*)>", re.I)
REL_RE = re.compile(r"\brel\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def dedupe_identical_head_tags(head: str, pattern: re.Pattern[str]) -> str:
    seen: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        normalized = re.sub(r"\s+", " ", match.group(0)).strip().casefold()
        if normalized in seen:
            return ""
        seen.add(normalized)
        return match.group(0)

    return pattern.sub(repl, head)


def secure_blank_anchor(match: re.Match[str]) -> str:
    attrs = match.group(1)
    rel = REL_RE.search(attrs)
    if rel:
        values = {part.casefold() for part in rel.group(2).split()}
        values.update({"noopener", "noreferrer"})
        replacement = f'rel="{" ".join(sorted(values))}"'
        attrs = attrs[: rel.start()] + replacement + attrs[rel.end() :]
    else:
        attrs += ' rel="noopener noreferrer"'
    return f"<a{attrs}>"


def repair_file(path: Path) -> list[str]:
    original = path.read_text(encoding="utf-8", errors="replace")
    text = original
    changes: list[str] = []

    if BAD_SELECTOR in text:
        text = text.replace(BAD_SELECTOR, GOOD_SELECTOR)
        changes.append("selector CSS de carga")

    text2 = re.sub(r"http://(?:www\.)?estrechoormuz\.com", "https://estrechoormuz.com", text, flags=re.I)
    if text2 != text:
        text = text2
        changes.append("URLs internas HTTPS")

    head_match = HEAD_RE.search(text)
    if head_match:
        head = head_match.group(1)
        all_adsense = ADSENSE_RE.findall(text)
        # Elimina todas las ocurrencias y conserva una sola dentro de head.
        if all_adsense:
            chosen_match = ADSENSE_RE.search(text)
            chosen = chosen_match.group(0) if chosen_match else all_adsense[0]
            text_without = ADSENSE_RE.sub("", text)
            fresh = HEAD_RE.search(text_without)
            if fresh:
                new_head = fresh.group(1)
                insertion = "\n  " + chosen
                if chosen.casefold() not in new_head.casefold():
                    new_head = insertion + new_head
                text = text_without[: fresh.start(1)] + new_head + text_without[fresh.end(1) :]
                if len(all_adsense) != 1 or not ADSENSE_RE.search(head):
                    changes.append("meta AdSense dentro de head y sin duplicados")

        fresh = HEAD_RE.search(text)
        if fresh:
            head = fresh.group(1)
            patterns = (
                re.compile(r'<meta\s+charset\s*=\s*["\'][^"\']+["\'][^>]*>', re.I),
                re.compile(r'<meta\s+name\s*=\s*["\']viewport["\'][^>]*>', re.I),
                re.compile(r'<link\s+[^>]*rel\s*=\s*["\'][^"\']*canonical[^"\']*["\'][^>]*>', re.I),
            )
            new_head = head
            for pattern in patterns:
                new_head = dedupe_identical_head_tags(new_head, pattern)
            if new_head != head:
                text = text[: fresh.start(1)] + new_head + text[fresh.end(1) :]
                changes.append("metadatos idénticos duplicados")

    secured = TARGET_BLANK_RE.sub(secure_blank_anchor, text)
    if secured != text:
        text = secured
        changes.append("noopener/noreferrer")

    if text != original:
        atomic_write_text(path, text)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    touched = 0
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        changes = repair_file(path)
        if changes:
            touched += 1
            print(f"{rel.as_posix()}: {', '.join(changes)}")
    print(f"Reparación HTML finalizada: {touched} archivo(s) modificados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
