"""Check ads.txt delivery and publisher consistency, never account approval."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import ssl
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

BASE = 'https://estrechoormuz.com'


class PublisherMeta(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.accounts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', '').lower() == 'google-adsense-account':
            self.accounts.append(attrs.get('content', ''))


def publisher_id(root: Path) -> str:
    accounts = PublisherMeta((root / 'index.html').read_text(encoding='utf-8')).accounts
    if len(accounts) != 1 or not re.fullmatch(r'ca-pub-\d{16}', accounts[0]):
        raise ValueError('Expected one valid publisher meta in index.html')
    return accounts[0].removeprefix('ca-')


def validate_ads_txt(raw: bytes, expected: str) -> list[str]:
    errors = []
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return ['ads.txt is not UTF-8']
    if '<' in text or '\ufeff' in text or any(ord(c) < 32 and c not in '\r\n\t' for c in text):
        errors.append('ads.txt contains HTML, BOM or control characters')
    records = [[field.strip() for field in line.split('#', 1)[0].split(',')]
               for line in text.splitlines() if line.split('#', 1)[0].strip()]
    google = [row for row in records if row[0].lower() == 'google.com']
    if google != [['google.com', expected, 'DIRECT', 'f08c47fec0942fa0']]:
        errors.append('Expected exactly one Google DIRECT record matching the configured publisher')
    return errors


def check_artifact(root: Path) -> list[str]:
    try:
        expected = publisher_id(root)
        errors = validate_ads_txt((root / 'ads.txt').read_bytes(), expected)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    for path in root.rglob('*.html'):
        accounts = PublisherMeta(path.read_text(encoding='utf-8')).accounts
        if any(account != 'ca-' + expected for account in accounts):
            errors.append(f'{path.relative_to(root)}: inconsistent publisher meta')
    return errors


def fetch(url, agent='Ormuz-ads-txt-audit/1.0'):
    chain = []

    class Redirects(HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, new_url):
            chain.append({'url': request.full_url, 'status': code, 'location': new_url})
            return super().redirect_request(request, response, code, message, headers, new_url)

    try:
        request = Request(url, headers={'User-Agent': agent, 'Cache-Control': 'no-cache'})
        try:
            response = build_opener(Redirects()).open(request, timeout=20)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read(512 * 1024)
            headers = {key.lower(): value for key, value in response.headers.items()}
            row = {'url': url, 'agent_header': agent, 'redirects': chain, 'status': response.status,
                   'final_url': response.geturl(), 'content_type': headers.get('content-type'),
                   'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                   'delivery_headers': {key: headers[key] for key in ('server', 'cf-ray', 'cf-cache-status',
                       'age', 'last-modified', 'cache-control', 'x-github-request-id', 'x-cache', 'location') if key in headers}}
            return row, raw
    except Exception as exc:
        return {'url': url, 'agent_header': agent, 'redirects': chain, 'status': None,
                'error': f'{type(exc).__name__}: {exc}'}, b''


def audit_network(root: Path):
    expected = publisher_id(root)
    urls = [f'{scheme}://{host}/ads.txt' for host in ('estrechoormuz.com', 'www.estrechoormuz.com')
            for scheme in ('https', 'http')]
    requests = [(url, 'Ormuz-ads-txt-audit/1.0') for url in urls]
    requests += [(BASE + '/ads.txt', agent) for agent in ('Mediapartners-Google', 'Google-adstxt')]
    requests += [(BASE + '/ads.txt?audit=' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'), 'Ormuz-ads-txt-audit/1.0')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda args: fetch(*args), requests))
    rows = []
    for row, raw in responses:
        row['format_errors'] = validate_ads_txt(raw, expected) if row['status'] == 200 else ['Not HTTP 200']
        row['matches_built_artifact'] = raw == (root / 'ads.txt').read_bytes()
        rows.append(row)
    robots_row, raw = fetch(BASE + '/robots.txt')
    parser = RobotFileParser(BASE + '/robots.txt')
    parser.parse(raw.decode('utf-8', errors='replace').splitlines())
    robots_row['ads_txt_allowed'] = {agent: parser.can_fetch(agent, BASE + '/ads.txt')
                                     for agent in ('*', 'Mediapartners-Google', 'Google-adstxt', 'Googlebot')}
    robots_row['text'] = raw.decode('utf-8', errors='replace')
    home_row, raw = fetch(BASE + '/')
    home_row['publisher_meta'] = PublisherMeta(raw.decode('utf-8', errors='replace')).accounts
    tls = {}
    for host in ('estrechoormuz.com', 'www.estrechoormuz.com'):
        try:
            with socket.create_connection((host, 443), timeout=15) as stream:
                with ssl.create_default_context().wrap_socket(stream, server_hostname=host) as secure:
                    cert = secure.getpeercert()
                    tls[host] = {'verified': True, 'version': secure.version(), 'expires': cert.get('notAfter'),
                                 'issuer': cert.get('issuer'), 'subject_alt_names': cert.get('subjectAltName')}
        except Exception as exc:
            tls[host] = {'verified': False, 'error': f'{type(exc).__name__}: {exc}'}
    dns_row, raw = fetch('https://dns.google/resolve?name=estrechoormuz.com&type=NS')
    try:
        dns = json.loads(raw).get('Answer', [])
    except (ValueError, TypeError):
        dns = []
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'configured_publisher_id': expected,
            'artifact_ads_txt_sha256': hashlib.sha256((root / 'ads.txt').read_bytes()).hexdigest(),
            'requests': rows, 'robots': robots_row, 'homepage': home_row, 'tls': tls,
            'public_dns_nameservers': dns, 'dns_http_status': dns_row.get('status'),
            'account_status': 'not_accessed',
            'limits': ['User-agent strings are simulated; these are not requests from verified Google IPs.',
                       'Cloudflare rules, crawl logs and account publisher ownership require account access.',
                       'Public delivery and correct format do not prove AdSense Authorized or Ready.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).parent / '_site')
    parser.add_argument('--audit-network', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    errors = check_artifact(args.root)
    if args.audit_network:
        result = audit_network(args.root)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        for row in result['requests']:
            errors.extend(f"{row['url']}: {error}" for error in row['format_errors'])
            if row.get('status') == 200 and 'text/plain' not in row.get('content_type', '').lower():
                errors.append(f"{row['url']}: not text/plain")
        if result['robots'].get('status') != 200 or not all(result['robots']['ads_txt_allowed'].values()):
            errors.append('robots.txt could not be verified as allowing ads.txt')
        if not all(row['verified'] for row in result['tls'].values()):
            errors.append('HTTPS certificate verification failed')
        if result['homepage'].get('status') != 200 or result['homepage']['publisher_meta'] != ['ca-' + result['configured_publisher_id']]:
            errors.append('Public homepage publisher meta does not match the configured account')
    for error in errors:
        print('ERROR:', error)
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
