#!/usr/bin/env python3
"""Validate links and browser assets against the actual public artifact."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys
import re
import xml.etree.ElementTree as ET

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
            if (url.scheme and url.scheme not in {'http', 'https'}) or (url.netloc and url.hostname != 'estrechoormuz.com') or not url.path:
                continue
            path = unquote(url.path)
            target = root / path.lstrip("/") if path.startswith("/") else page.parent / path
            if path.endswith("/"):
                target = target / "index.html"
            target = target.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{page.relative_to(root)}: missing public target {ref}")
    atom = {'a': 'http://www.w3.org/2005/Atom'}
    for name, folder in (('diario-feed.xml', 'diario'), ('diary-feed.xml', 'diary')):
        feed = root / name
        if not feed.exists():
            continue
        try:
            entries = ET.parse(feed).findall('a:entry', atom)
        except ET.ParseError:
            errors.append(f'{name}: invalid Atom XML')
            continue
        for entry in entries:
            link = entry.find('a:link', atom)
            href = link.get('href', '') if link is not None else ''
            url = urlsplit(href)
            match = re.fullmatch(rf'/{folder}/(\d{{4}}-\d{{2}}-\d{{2}})\.html', url.path)
            if url.scheme != 'https' or url.netloc != 'estrechoormuz.com' or url.query or url.fragment or not match:
                errors.append(f'{name}: entry requires a dated permalink: {href}')
                continue
            target = root / url.path.lstrip('/')
            if not target.is_file():
                errors.append(f'{name}: missing historical page: {href}')
                continue
            document = target.read_text(encoding='utf-8')
            if not re.search(r'<meta\b(?=[^>]*name=["\x27]robots["\x27])(?=[^>]*content=["\x27][^"\x27]*noindex)', document, re.I):
                errors.append(f'{name}: automatic archive must remain noindex: {href}')
            if re.search(r'adsbygoogle|pagead2\.googlesyndication', document, re.I):
                errors.append(f'{name}: automatic archive contains advertising: {href}')
    return errors

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "_site"
    failures = check(folder)
    for failure in failures:
        print(failure)
    print(f"Public links: {len(failures)} error(s).")
    raise SystemExit(bool(failures))
