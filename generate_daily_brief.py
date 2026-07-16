#!/usr/bin/env python3
"""Genera parte diario, archivo, feed y borradores de X desde status.json."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(os.getenv("ORMUZ_ROOT", Path(__file__).resolve().parent))
MADRID = ZoneInfo("Europe/Madrid")
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

def build_feed(items: list[dict[str, Any]], updated: str) -> str:
    entries=[]
    for item in items[:30]:
        entries.append(f"""  <entry>
    <title>{html.escape(item.get('operational_label_es','Parte diario'))} · {item.get('date','')}</title>
    <id>{BASE_URL}/parte-diario.html#{item.get('date','')}</id>
    <link href="{BASE_URL}/parte-diario.html"/>
    <updated>{item.get('generated_at',updated)}</updated>
    <summary>{html.escape(item.get('summary_es',''))}</summary>
  </entry>""")
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

def main() -> int:
    status=load_json("status.json",{})
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
        change_es=f"El indicador cambia de «{previous.get('operational_label_es','—')}» a «{op_es}»."
        change_en=f"The indicator changes from “{previous.get('operational_label_en','—')}” to “{op_en}”."
        publish=True
    else:
        change_es="Sin cambio material en la clasificación desde el parte anterior."
        change_en="No material change in classification since the previous brief."
        publish=False
    confidence_es={"ALTA":"Alta","MEDIA":"Media","BAJA":"Baja"}.get(status.get("confidence"),"Baja")
    confidence_en={"ALTA":"High","MEDIA":"Medium","BAJA":"Low"}.get(status.get("confidence"),"Low")
    brief={
      "schema_version":1,"date":local_date,"generated_at":generated_at,"source_checked_at":status.get("checked_at"),
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
    if isinstance(existing,dict) and existing.get("material_hash")==brief["material_hash"]:
        brief["generated_at"]=existing.get("generated_at",generated_at)
    archive=[item for item in archive if item.get("date")!=local_date]
    archive.insert(0,brief);archive=archive[:MAX_ARCHIVE_DAYS]
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
    stable_write(ROOT/"daily-brief-feed.xml",build_feed(archive,brief["generated_at"]))
    print(f"Parte diario listo: {local_date} · publicar={publish}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
