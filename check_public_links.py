#!/usr/bin/env python3
"""Validate links and browser assets against the actual public artifact."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import sys
import re
import xml.etree.ElementTree as ET

class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = set()
        self.lang = ''
        self.alternates = {}
        self.anchors = []
        self.active_anchor = None
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'):
            self.ids.add(values['id'])
        if tag == 'a' and values.get('name'):
            self.ids.add(values['name'])
        if tag == 'html':
            self.lang = values.get('lang', '').split('-')[0].lower()
        if tag == 'link' and values.get('rel') == 'alternate' and values.get('hreflang'):
            self.alternates[values['hreflang']] = values.get('href', '')
        if tag == 'a' and values.get('href'):
            self.active_anchor = {'href': values['href'], 'class': values.get('class', ''), 'text': ''}
            self.anchors.append(self.active_anchor)
        if tag not in {"a", "link", "script", "img", "iframe", "source"}:
            return
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.refs.append(value)

    def handle_data(self, data):
        if self.active_anchor is not None:
            self.active_anchor['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self.active_anchor = None


def document_key(url):
    parts = urlsplit(url)
    path = parts.path or '/'
    if path == '/index.html':
        path = '/'
    return parts.hostname, path

def check(root):
    root = Path(root).resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        return [f"Missing public artifact or homepage: {root}"]
    errors = []
    parsers = {}
    for page in root.rglob('*.html'):
        parser = References()
        parser.feed(page.read_text(encoding="utf-8"))
        parsers[page] = parser
    for page, parser in parsers.items():
        for ref in parser.refs:
            url = urlsplit(ref)
            if (url.scheme and url.scheme not in {'http', 'https'}) or (url.netloc and url.hostname != 'estrechoormuz.com') or not (url.path or url.fragment):
                continue
            path = unquote(url.path) if url.path else ('/' if url.netloc else '')
            target = (root / path.lstrip("/") if path.startswith("/") else page.parent / path) if path else page
            if path.endswith("/"):
                target = target / "index.html"
            target = target.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{page.relative_to(root)}: missing public target {ref}")
                continue
            fragment = unquote(url.fragment).split(':~:text=', 1)[0]
            if fragment and target in parsers and fragment not in parsers[target].ids:
                errors.append(f'{page.relative_to(root)}: missing public fragment {ref}')
        other = 'en' if parser.lang == 'es' else 'es'
        alternate = parser.alternates.get(other)
        if alternate:
            base = 'https://estrechoormuz.com/' + page.relative_to(root).as_posix()
            for anchor in parser.anchors:
                switch = ('language-link' in anchor['class'].split()
                          or (urlsplit(urljoin(base, anchor['href'])).hostname == 'estrechoormuz.com'
                              and anchor['text'].strip().casefold() in ({'en', 'english'} if other == 'en' else {'es', 'español'})))
                if switch and document_key(urljoin(base, anchor['href'])) != document_key(alternate):
                    errors.append(f'{page.relative_to(root)}: language switch does not match its alternate: {anchor["href"]}')
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
