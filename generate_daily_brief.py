#!/usr/bin/env python3
"""Genera parte diario, archivo, feed y borradores de X desde status.json."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from canonical_publication import assessment_id, age_hours, MAX_AGE_HOURS

ROOT = Path(os.getenv("ORMUZ_ROOT", Path(__file__).resolve().parent))
try:
    MADRID = ZoneInfo("Europe/Madrid")
except Exception:  # Windows environments may not bundle the IANA database.
    MADRID = timezone(timedelta(hours=2), "CEST")
BASE_URL = "https://estrechoormuz.com"
MAX_ARCHIVE_DAYS = 90

def load_json(name: str, default: Any) -> Any:
    path = ROOT / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

def stable_write(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True

def dump_json(path: Path, value: Any) -> bool:
    return stable_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\W+", " ", text.lower()).strip()

def dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output, seen = [], set()
    for item in sorted(items, key=lambda x: x.get("published_at", ""), reverse=True):
        key = item.get("source_url") or normalized(item.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append({
            "signal":item.get("signal",""),"title":item.get("title",""),
            "source_name":item.get("source_name",""),"source_url":item.get("source_url",""),
            "published_at":item.get("published_at",""),"official":bool(item.get("official",False))
        })
    return output[:5]

def display_labels(data: dict[str, Any]) -> tuple[str,str,str,str]:
    state = data.get("status","INCIERTO")
    operational = data.get("operational_status","HIGH_RISK_UNCONFIRMED")
    es_state = {"ABIERTO":"ABIERTO","CERRADO":"CERRADO","INCIERTO":"INCIERTO"}.get(state,"INCIERTO")
    en_state = {"ABIERTO":"OPEN","CERRADO":"CLOSED","INCIERTO":"UNCERTAIN"}.get(state,"UNCERTAIN")
    if state == "ABIERTO" and operational == "OPEN_RESTRICTED":
        es_state,en_state = "ABIERTO CON RESTRICCIONES","OPEN WITH RESTRICTIONS"
    return es_state,en_state,data.get("operational_label_es") or es_state,data.get("operational_label_en") or en_state

def risk_lists(data: dict[str, Any], evidence: list[dict[str, Any]]) -> tuple[list[str],list[str],list[str],list[str]]:
    mapping = {
      "OPEN_NORMAL":("No se observan restricciones suficientes para degradar el estado, aunque la vigilancia continúa.","No restrictions sufficient to degrade the status are observed, although monitoring continues."),
      "OPEN_RESTRICTED":("El tránsito se considera operativo, pero persisten restricciones, incidentes o fricción relevantes.","Transit is considered operational, but relevant restrictions, incidents or friction remain."),
      "CLOSED_CONFIRMED":("Existe evidencia suficiente de una interrupción operativa confirmada.","There is sufficient evidence of a confirmed operational interruption."),
      "CLOSURE_DECLARED_UNCONFIRMED":("Hay declaraciones de cierre, pero falta confirmación operativa independiente.","Closure has been declared, but independent operational confirmation is missing."),
      "HIGH_RISK_UNCONFIRMED":("El riesgo es elevado y no puede confirmarse de forma fiable si el paso está abierto o cerrado.","Risk is high and it cannot be reliably confirmed whether the passage is open or closed."),
      "CONFLICTING_SOURCES":("Las fuentes relevantes ofrecen señales contradictorias.","Relevant sources provide conflicting signals.")
    }
    es,en = mapping.get(data.get("operational_status"),("El estado requiere interpretación prudente.","The status requires cautious interpretation."))
    risks_es,risks_en=[es],[en]
    if data.get("stale"):
        risks_es.append("Los datos están marcados como desactualizados y no deben utilizarse como confirmación operativa.")
        risks_en.append("Data are marked as stale and should not be used as operational confirmation.")
    if not data.get("verification_ok",False):
        risks_es.append("La verificación está degradada porque una o más capas del motor no respondieron correctamente.")
        risks_en.append("Verification is degraded because one or more engine layers did not respond correctly.")
    if evidence:
        risks_es.append(f"El ciclo contiene {len(evidence)} evidencias destacadas; la cantidad no sustituye la independencia ni la calidad.")
        risks_en.append(f"The cycle contains {len(evidence)} highlighted evidence items; quantity does not replace independence or quality.")
    watch_es=["Avisos marítimos oficiales y confirmaciones operativas independientes.","Trayectorias completas de buques y continuidad real de los cruces, no puntos AIS aislados.","Cambios en restricciones, seguros, escoltas, puertos y disponibilidad de tripulaciones."]
    watch_en=["Official maritime notices and independent operational confirmations.","Completed vessel tracks and actual continuity of crossings, not isolated AIS points.","Changes in restrictions, insurance, escorts, ports and crew availability."]
    return risks_es,risks_en,watch_es,watch_en

def material_hash(brief: dict[str, Any]) -> str:
    material = {key:brief[key] for key in ("date","status","operational_status","confidence","verification_ok","stale","summary_es")}
    material["evidence"]=[(x.get("source_url"),x.get("signal"),x.get("title")) for x in brief["evidence"]]
    return hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]

def trim_post(text: str, limit: int=260) -> str:
    text = re.sub(r"[ \t]+"," ",text).strip()
    return text if len(text)<=limit else text[:limit-1].rstrip()+"…"

def build_feed(items: list[dict[str, Any]], updated: str, *, root: Path | None = None) -> str:
    root = ROOT if root is None else Path(root)
    entries=[]
    for item in items:
        day = str(item.get('date', ''))
        try:
            valid_day = date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_day = False
        if not valid_day or not (root / 'briefs' / f'{day}.html').is_file():
            continue
        entries.append(f"""  <entry>
    <title>{html.escape(item.get('operational_label_es','Parte diario'))} · {item.get('date','')}</title>
    <id>{BASE_URL}/parte-diario.html#{item.get('date','')}</id>
    <link href="{BASE_URL}/briefs/{day}.html"/>
    <updated>{item.get('generated_at',updated)}</updated>
    <summary>{html.escape(item.get('summary_es',''))}</summary>
  </entry>""")
        if len(entries) >= 30:
            break
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Parte diario · Estrecho Ormuz</title>
  <id>{BASE_URL}/daily-brief-feed.xml</id>
  <link href="{BASE_URL}/daily-brief-feed.xml" rel="self"/>
  <link href="{BASE_URL}/parte-diario.html"/>
  <updated>{updated}</updated>
{chr(10).join(entries)}
</feed>
"""

def apply_operational_intelligence(data: dict[str, Any]) -> dict[str, Any]:
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
    output["checked_at"] = oi.get("verified_at") or oi.get("generated_at") or output.get("checked_at")
    output["canonical_assessment"] = {key: oi.get(key) for key in ("state", "family", "confidence", "generated_at", "dimensions")}
    output["assessment_id"] = assessment_id(oi)
    output["evidence"] = [{"title": e.get("title"), "source_name": e.get("source"),
                           "source_url": e.get("url"), "published_at": e.get("published_at"),
                           "signal": e.get("kind"), "official": int(e.get("tier") or 0) >= 5}
                          for e in oi.get("evidence", []) if isinstance(e, dict)]
    output["stale"] = bool(data.get("stale")) or (age_hours(output["checked_at"]) or 0) > MAX_AGE_HOURS
    return output

def main() -> int:
    status=load_json("status.json",{})
    status=apply_operational_intelligence(status)
    if not isinstance(status,dict) or not status.get("status"):
        raise SystemExit("status.json no contiene un estado válido.")
    now=datetime.now(timezone.utc)
    local_date=now.astimezone(MADRID).date().isoformat()
    generated_at=now.replace(microsecond=0).isoformat().replace("+00:00","Z")
    archive=load_json("daily-brief-archive.json",[])
    if isinstance(archive,dict): archive=archive.get("items",[])
    if not isinstance(archive,list): archive=[]
    previous=next((item for item in archive if item.get("date")!=local_date),None)
    state_es,state_en,op_es,op_en=display_labels(status)
    evidence=dedupe_evidence(status.get("evidence",[]))
    risks_es,risks_en,watch_es,watch_en=risk_lists(status,evidence)
    current_key=f"{status.get('status')}|{status.get('operational_status')}|{status.get('confidence')}"
    previous_key=f"{previous.get('status')}|{previous.get('operational_status')}|{previous.get('confidence')}" if previous else ""
    if not previous:
        change_es="Primera línea base del parte diario; no implica por sí sola una novedad publicable."
        change_en="First daily-brief baseline; this does not by itself represent a publishable change."
        publish=False
    elif current_key!=previous_key:
        change_es=f"Comparación con el parte fechado el {previous.get('date','—')}: «{previous.get('operational_label_es','—')}» frente a «{op_es}», con sus respectivos niveles de confianza. Estos registros no permiten fechar el cambio marítimo."
        change_en=f"Compared with the brief dated {previous.get('date','—')}: “{previous.get('operational_label_en','—')}” versus “{op_en}”, each with its own confidence level. These records cannot date a maritime change."
        publish=bool(previous.get("date") == (now.astimezone(MADRID).date() - timedelta(days=1)).isoformat())
    else:
        change_es="Sin cambio material en la clasificación desde el parte anterior."
        change_en="No material change in classification since the previous brief."
        publish=False
    confidence_es={"ALTA":"Alta","MEDIA":"Media","BAJA":"Baja"}.get(status.get("confidence"),"Baja")
    confidence_en={"ALTA":"High","MEDIA":"Medium","BAJA":"Low"}.get(status.get("confidence"),"Low")
    brief={
      "schema_version":2,"date":local_date,"generated_at":generated_at,"source_checked_at":status.get("checked_at"),
      "assessment_id":status.get("assessment_id"),"canonical_assessment":status.get("canonical_assessment"),
      "status":status.get("status","INCIERTO"),"status_label_es":state_es,"status_label_en":state_en,
      "operational_status":status.get("operational_status",""),"operational_label_es":op_es,"operational_label_en":op_en,
      "confidence":status.get("confidence","BAJA"),"confidence_label":{"es":confidence_es,"en":confidence_en},
      "verification_ok":bool(status.get("verification_ok",False)),"stale":bool(status.get("stale",False)),
      "summary_es":status.get("summary_es",""),"summary_en":status.get("summary_en",""),
      "change_es":change_es,"change_en":change_en,"risks_es":risks_es,"risks_en":risks_en,
      "watchlist_es":watch_es,"watchlist_en":watch_en,"evidence":evidence,
      "last_valid_confirmation":status.get("last_valid_confirmation"),"publish_recommended":publish
    }
    brief["material_hash"]=material_hash(brief)
    existing=load_json("daily-brief.json",{})
    if isinstance(existing,dict) and existing.get("material_hash")==brief["material_hash"] and existing.get("assessment_id")==brief.get("assessment_id"):
        brief["generated_at"]=existing.get("generated_at",generated_at)
    archive=[item for item in archive if item.get("date")!=local_date]
    archive.insert(0,brief)  # Never discard historical records to repair freshness.
    es_url=f"{BASE_URL}/parte-diario.html?utm_source=x&utm_medium=social&utm_campaign=parte_diario&utm_content=es"
    en_url=f"{BASE_URL}/en-daily-brief.html?utm_source=x&utm_medium=social&utm_campaign=daily_brief&utm_content=en"
    es_text=trim_post(f"PARTE DIARIO — ESTRECHO DE ORMUZ\n\n{op_es}\nConfianza: {confidence_es}.\n\n{brief['summary_es']}")
    en_text=trim_post(f"DAILY BRIEF — STRAIT OF HORMUZ\n\n{op_en}\nConfidence: {confidence_en}.\n\n{brief['summary_en']}")
    social={"generated_at":brief["generated_at"],"publish_recommended":publish,
            "status_es":f"{es_text}\n\n{es_url}","status_en":f"{en_text}\n\n{en_url}",
            "thread_es":f"{es_text}\n\nEvidencias y metodología:\n{es_url}",
            "thread_en":f"{en_text}\n\nEvidence and methodology:\n{en_url}"}
    dump_json(ROOT/"daily-brief.json",brief)
    dump_json(ROOT/"daily-brief-archive.json",archive)
    dump_json(ROOT/"social-drafts.json",social)
    dump_json(ROOT/"briefs"/f"{local_date}.json",brief)
    # Historical feeds link only to an actual dated page. JSON remains internal.
    for lang, folder in (("es", "briefs"), ("en", "briefs-en")):
        stable_write(ROOT/folder/f"{local_date}.html", render_frozen(brief, lang))
    stable_write(ROOT/"daily-brief-feed.xml",build_feed(archive,brief["generated_at"]))
    stable_write(ROOT/"daily-brief-feed-en.xml", build_feed_en(archive, brief["generated_at"]))
    print(f"Parte diario listo: {local_date} · publicar={publish}")
    return 0


def render_frozen(brief, lang):
    es = lang == "es"
    folder, alternate = ("briefs", "briefs-en") if es else ("briefs-en", "briefs")
    day = brief["date"]
    title = ("Parte diario" if es else "Daily brief") + " · " + day
    label = html.escape(brief.get("operational_label_" + lang) or "")
    summary = html.escape(brief.get("summary_" + lang) or "")
    sources = "".join('<li><a href="' + html.escape(x.get("source_url", ""), quote=True) + '" rel="noopener noreferrer">' +
                      html.escape(x.get("title", "")) + "</a> · " + html.escape(x.get("published_at", "")) + "</li>"
                      for x in brief.get("evidence", []) if str(x.get("source_url", "")).startswith("https://"))
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | Estrecho Ormuz</title>
<meta name="robots" content="noindex,follow"><meta name="publisher-ads" content="disabled">
<link rel="canonical" href="{BASE_URL}/{folder}/{day}.html">
<link rel="alternate" hreflang="{lang}" href="{BASE_URL}/{folder}/{day}.html">
<link rel="alternate" hreflang="{'en' if es else 'es'}" href="{BASE_URL}/{alternate}/{day}.html">
<link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/professional-v9.css">
</head><body><header class="site-header"><a href="/{'index.html' if es else 'en.html'}">Estrecho Ormuz</a></header>
<main class="container"><h1>{title}</h1><p>{'Instantánea automatizada, sin revisión humana individual.' if es else 'Automated snapshot; no individual human review.'}</p>
<h2>{label}</h2><p>{summary}</p>
<p>{'Confianza' if es else 'Confidence'}: {html.escape(brief.get("confidence_label", {}).get(lang, ""))}</p>
<p>{'Datos comprobados' if es else 'Source check'}: <time>{html.escape(brief.get("source_checked_at") or "")}</time></p>
<p>{'Documento generado' if es else 'Document generated'}: <time>{html.escape(brief["generated_at"])}</time></p>
<h2>{'Fuentes fechadas' if es else 'Dated sources'}</h2><ul>{sources}</ul>
<p>{'Registro del monitor; no es un recuento de buques ni una medición AIS.' if es else 'Monitor record; neither a vessel count nor an AIS measurement.'}</p>
<a href="/{'parte-diario.html' if es else 'en-daily-brief.html'}">{'Parte actual' if es else 'Latest brief'}</a>
<a href="/{'metodo-inteligencia-operativa.html' if es else 'en-operational-intelligence-method.html'}">{'Metodología' if es else 'Methodology'}</a>
</main></body></html>\n'''


def build_feed_en(items, updated):
    # Only the explicitly generated paired resources qualify for the English feed.
    valid = [x for x in items if (ROOT / "briefs-en" / (str(x.get("date")) + ".html")).is_file()]
    translated = [{**x, "operational_label_es": x.get("operational_label_en"), "summary_es": x.get("summary_en")} for x in valid]
    return (build_feed(translated, updated).replace("/briefs/", "/briefs-en/")
            .replace("daily-brief-feed.xml", "daily-brief-feed-en.xml")
            .replace("parte-diario.html", "en-daily-brief.html")
            .replace("Parte diario ·", "Daily brief ·"))

if __name__=="__main__":
    raise SystemExit(main())
