#!/usr/bin/env python3
"""Validate links and browser assets against the actual public artifact."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
    def handle_starttag(self, tag, attrs):
        if tag not in {"a", "link", "script", "img", "iframe", "source"}:
            return
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.refs.append(value)

def check(root):
    root = Path(root).resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        return [f"Missing public artifact or homepage: {root}"]
    errors = []
    for page in root.rglob("*.html"):
        parser = References()
        parser.feed(page.read_text(encoding="utf-8"))
        for ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            target = root / path.lstrip("/") if path.startswith("/") else page.parent / path
            if path.endswith("/"):
                target = target / "index.html"
            target = target.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{page.relative_to(root)}: missing public target {ref}")
    return errors

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "_site"
    failures = check(folder)
    for failure in failures:
        print(failure)
    print(f"Public links: {len(failures)} error(s).")
    raise SystemExit(bool(failures))
