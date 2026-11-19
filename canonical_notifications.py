"""Durable V7 outbox. Delivery requires a matching, already public release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical_publication import ENGINE, DIMENSIONS, assessment_id, canonical, material_key, read, timestamp
from maintenance_common import atomic_write_json


def enqueue(root, before, after):
    root = Path(root)
    if not before.get("state") or material_key(before) == material_key(after):
        return None
    kind = ("classification" if before.get("state") != after.get("state") else
            "confidence" if before.get("dimensions") == after.get("dimensions") else "dimensions")
    event = {"engine": ENGINE, "kind": kind, "at": after.get("generated_at"),
             "before": before, "after": after, "evidence": after.get("evidence", [])}
    event["id"] = "v7-" + hashlib.sha256((assessment_id(before) + assessment_id(after)).encode()).hexdigest()[:24]
    queue = read(root / "notification-outbox.json", []) or []
    if not any(x.get("id") == event["id"] for x in queue):
        queue.append(event)
        atomic_write_json(root / "notification-outbox.json", queue)
    return event


def fetch_public(url):
    request = urllib.request.Request(url, headers={"User-Agent": "EstrechoOrmuz-ReleaseCheck/1",
                                                "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("Publication endpoint is not HTTP 200")
        return response.read(16000)


def verify_public(body, current, expected_commit):
    doc = ET.fromstring(body)
    if doc.tag != "publication" or doc.get("engine") != ENGINE:
        raise ValueError("Unexpected public contract")
    if not expected_commit or doc.findtext("source_commit") != expected_commit:
        raise ValueError("Deployed commit differs from the built commit")
    if doc.findtext("assessment_id") != assessment_id(current):
        raise ValueError("Deployed V7 assessment differs from the local snapshot")
    if doc.findtext("brief_assessment_id") != assessment_id(current):
        raise ValueError("Published brief is not aligned with V7")
    return doc


def verify_release(fetcher, current, expected_commit):
    doc = verify_public(fetcher("https://estrechoormuz.com/publication-health.xml"), current, expected_commit)
    expected = assessment_id(current)
    # Check the actual HTML too: a fresh health endpoint alone does not prove all cached pages changed.
    for name in ("index.html", "en.html", "parte-diario.html", "en-daily-brief.html", "historial.html", "en-history.html"):
        body = fetcher("https://estrechoormuz.com/" + name)
        text = body.decode("utf-8") if isinstance(body, bytes) else body
        match = re.search(r'<meta\s+name="ormuz-assessment"\s+content="([a-f0-9]+)"', text)
        if not match or match[1] != expected:
            raise ValueError("Public HTML has not reached the canonical assessment: " + name)
    return doc


def configured_channels():
    result = {}
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")
    if token and chat:
        result["telegram"] = ("https://api.telegram.org/bot" + token + "/sendMessage", chat)
    topic = os.getenv("NTFY_TOPIC_URL", "")
    if topic.startswith("https://"):
        result["ntfy"] = (topic, "")
    return result


def send(channel, settings, text):
    if channel == "telegram":
        payload = urllib.parse.urlencode({"chat_id": settings[1], "text": text, "disable_web_page_preview": "true"}).encode()
        request = urllib.request.Request(settings[0], data=payload, method="POST")
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200 or not json.loads(response.read(64000)).get("ok"):
                raise ValueError("Telegram did not acknowledge delivery")
    else:
        request = urllib.request.Request(settings[0], data=text.encode(), method="POST",
                                        headers={"Content-Type": "text/plain; charset=utf-8"})
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200 or not json.loads(response.read(16000)).get("id"):
                raise ValueError("ntfy did not acknowledge delivery")


def deliver(root, expected_commit, *, enabled=False, fetcher=fetch_public, sender=send, sleep=time.sleep):
    root = Path(root)
    queue = read(root / "notification-outbox.json", []) or []
    ledger = read(root / "notification-delivery.json", {}) or {}
    current = canonical(root)
    # No secrets, channel addresses or tokens are ever written to this ledger.
    report = {"enabled": enabled, "queued": len(queue), "channels": [], "errors": []}
    if not enabled:
        return report
    verify_release(fetcher, current, expected_commit)
    channels = configured_channels()
    report["channels"] = sorted(channels)
    if not channels:
        report["errors"].append("No delivery channels configured")
        return report
    matching = [event for event in queue if material_key(event["after"]) == material_key(current)]
    latest_visible = max(matching, key=lambda event: timestamp(event["at"]))["id"] if matching else None
    for event in queue:
        row = ledger.setdefault(event["id"], {"at": event["at"], "channels": {}})
        if event["id"] != latest_visible:
            row["superseded_by"] = assessment_id(current)
            continue  # Coalesce multiple unpublished transitions, including returns to the same state.
        if timestamp(event["at"]) > timestamp(current["generated_at"]):
            raise ValueError("Outbox event is newer than the public assessment")
        after, before = event["after"], event["before"]
        text = (f"Estrecho Ormuz · {after.get('label_es')}\n"
                f"Anterior: {before.get('label_es')}\nConfianza: {after.get('confidence')}\n"
                f"Cambio: {event['kind']} · {event['at']}\n"
                f"{after.get('summary_es', '')}\nID: {event['id']}\nhttps://estrechoormuz.com/")
        for channel, settings in channels.items():
            state = row["channels"].setdefault(channel, {"attempts": 0})
            if state.get("delivered"):
                continue
            # Ambiguous transport outcomes cannot provide exactly-once delivery.
            # Stable IDs and per-channel acknowledgements suppress confirmed duplicates.
            for attempt in range(3):
                state["attempts"] += 1
                try:
                    sender(channel, settings, text)
                    state.update(delivered=True, last_error=None)
                    break
                except Exception as exc:
                    state["last_error"] = type(exc).__name__  # Never log a secret-bearing URL.
                    if attempt < 2:
                        sleep(2 ** attempt)
                finally:
                    atomic_write_json(root / "notification-delivery.json", ledger)
            if not state.get("delivered"):
                report["errors"].append(event["id"] + ":" + channel + ":" + state["last_error"])
    atomic_write_json(root / "notification-delivery.json", ledger)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    report = deliver(args.root, args.commit, enabled=args.send)
    print(json.dumps(report, ensure_ascii=False))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
