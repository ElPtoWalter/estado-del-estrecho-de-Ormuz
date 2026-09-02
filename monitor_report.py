"""Reader-facing analysis of the monitor's own recorded decisions, not ship traffic."""
import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone


FIELDS = ("at", "status", "operational_status", "confidence")


def records(root):
    raw = json.loads((root / "history.json").read_text())
    return sorted([{key: str(row.get(key) or "UNKNOWN") for key in FIELDS}
                   for row in raw if isinstance(row, dict)], key=lambda row: row["at"])


def build_reports(root):
    data = records(root)
    with (root / "monitor-records.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(data)
    states = Counter(row["status"] for row in data)
    total = len(data)
    uncertain = states.get("INCIERTO", 0)
    changed = sum(a["status"] != b["status"] for a, b in zip(data, data[1:]))
    same = max(0, total - 1 - changed)
    valid = sum(row["at"] != "UNKNOWN" for row in data)
    status = json.loads((root / "status.json").read_text())
    checked = html.escape(str(status.get("checked_at") or "sin fecha"))
    period = " → ".join(html.escape(row["at"][:10]) for row in (data[0], data[-1])) if data else "—"
    pct = round(100 * uncertain / total, 1) if total else 0
    for lang in ("es", "en"):
        es = lang == "es"
        slug = "datos-propios-monitor-ormuz.html" if es else "en-monitor-original-data-report.html"
        title = "Ormuz: lo que revela el historial y lo que no mide" if es else "Hormuz: what the archive reveals and what it does not measure"
        table = "".join("<tr>" + "".join(f"<td>{html.escape(row[key])}</td>" for key in FIELDS) + "</tr>" for row in reversed(data))
        body = f"""<p>Analizamos <strong>{total} registros</strong> conservados entre {period}. No son observaciones periódicas de buques: son decisiones del monitor. Fecha de consulta del sistema: {checked}. La consulta no cambia la fecha de las observaciones históricas.</p>
<h2>La incertidumbre no es una medida de cierre</h2><p>{uncertain} de las {total} filas figuran como INCIERTO: {pct}%. El cálculo es {uncertain} ÷ {total} × 100, redondeado a una cifra decimal. Ese porcentaje describe el archivo, no el porcentaje de horas de cierre, el riesgo de un viaje ni la proporción de buques afectados.</p>
<h2>Registrar una novedad no siempre cambia el estado</h2><p>Al ordenar las filas por fecha y comparar cada una con la anterior, encontramos {changed} cambios de la etiqueta general y {same} pares que conservan la misma etiqueta. La primera fila no tiene comparación previa. Una nueva fila puede actualizar la categoría operativa o la confianza sin cambiar de abierto a cerrado; por eso no llamamos «cierres» a las entradas del historial.</p>
<p>Esta distinción explica por qué dos contadores aparentemente incompatibles pueden ser correctos: el total de registros cuenta publicaciones; el de transiciones cuenta cambios entre etiquetas. Ninguno prueba que el clasificador haya acertado. Para evaluar aciertos haría falta cotejar cada decisión con evidencia marítima externa fechada.</p>
<h2>Tres errores que el diario ahora evita</h2><ol><li><strong>Geografía no es diplomacia.</strong> Mencionar Irán, Teherán o Washington no basta para clasificar un ataque como negociación. La clasificación requiere palabras que describan el hecho.</li><li><strong>Mercado no es navegación.</strong> Un titular sobre el precio del crudo se trata como señal de mercado incluso si menciona ataques; no se convierte en una estimación de tránsito.</li><li><strong>Recencia no es novedad.</strong> Una actualización de un mismo enlace no crea por sí sola una noticia nueva. Más titulares sin cambio del diagnóstico no abren otra entrada histórica.</li></ol>
<h2>Cómo comprobar el resultado</h2><p><a href="/monitor-records.csv" download>Descargar registros y reproducir los cálculos (CSV)</a>. El archivo contiene únicamente fecha, estado, categoría operativa y confianza; no incorpora información personal ni configuración del sistema. En una hoja de cálculo, cuenta las filas sin la cabecera, filtra la columna de estado por INCIERTO y divide ambos recuentos. Ordena por fecha y compara estados consecutivos para reproducir las transiciones.</p>
<p>Hay {valid} filas con una marca de fecha en el archivo. No se rellenan periodos ausentes. El conjunto puede estar limitado por la retención histórica y por cambios de método: no permite reconstruir por sí solo toda la evolución física del corredor. El CSV y la tabla proceden de la misma instantánea y se regeneran con la publicación del sitio.</p>
<h2>Registro completo utilizado</h2>""" if es else f"""<p>We examine <strong>{total} retained records</strong> from {period}. These are monitor decisions, not periodic vessel observations. System check: {checked}; this does not refresh historical observation dates.</p>
<h2>Uncertainty is not a closure measure</h2><p>{uncertain} of {total} rows are INCIERTO (uncertain): {pct}%, calculated as {uncertain} ÷ {total} × 100 and rounded to one decimal place. This describes the archive, not hours of closure, voyage risk or affected vessels.</p>
<h2>A new record need not change the general state</h2><p>Chronological comparison yields {changed} changes of the general state label and {same} adjacent pairs retaining that label. The first row has no preceding comparison. A record can update an operational category or confidence without changing the general state. Publication counts and state-transition counts measure different things; neither establishes the classifier's accuracy.</p>
<h2>Three corrections to the diary</h2><ol><li>Country names are not evidence of diplomacy: classification requires event terms.</li><li>Oil-price headlines remain market signals even when they mention strikes; they do not measure passage.</li><li>An updated headline at the same URL is not automatically a new story. More headlines without a changed assessment do not create another archive entry.</li></ol>
<h2>Reproduce the calculations</h2><p><a href="/monitor-records.csv" download>Download the exact records (CSV)</a>. Count rows without the header, filter state for INCIERTO and divide the two counts. Sort chronologically and compare adjacent state labels to reproduce transitions. The export contains only date, state, operational category and confidence, not personal information or system configuration.</p>
<p>{valid} rows have a date value. Missing periods are not filled. Retention and methodological changes limit the dataset: it cannot reconstruct physical traffic. Accuracy would require comparison against separately dated maritime evidence. The table and CSV use the same snapshot and are regenerated when the site is published.</p><h2>Complete record used</h2>"""
        schema = json.dumps({"@context": "https://schema.org", "@type": "Dataset", "name": title,
                             "url": f"https://estrechoormuz.com/{slug}",
                             "distribution": {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": "https://estrechoormuz.com/monitor-records.csv"}}, ensure_ascii=False)
        page = f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | Estrecho Ormuz</title><meta name="description" content="{'Análisis reproducible del historial: incertidumbre, transiciones y límites; descarga los registros usados.' if es else 'Reproducible archive analysis: uncertainty, transitions and limitations, with a downloadable dataset.'}"><link rel="canonical" href="https://estrechoormuz.com/{slug}"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/v11.css"><link rel="stylesheet" href="/authority-v6.css"><script type="application/ld+json">{schema}</script></head><body><header class="site-header"><nav class="header-inner"><a href="/">Estrecho Ormuz</a> · <a href="{'/diario.html' if es else '/en-diary.html'}">{'Diario' if es else 'Daily'}</a> · <a href="{'/analisis.html' if es else '/en-analysis.html'}">{'Análisis' if es else 'Analysis'}</a> · <a href="{'/metodologia.html' if es else '/en-methodology.html'}">{'Metodología' if es else 'Methodology'}</a> · <a href="{'/en-monitor-original-data-report.html' if es else '/datos-propios-monitor-ormuz.html'}">{'EN' if es else 'ES'}</a></nav></header><main class="site-main"><header class="a6-hero"><span class="section-kicker">{'ANÁLISIS PROPIO · DATOS REPRODUCIBLES' if es else 'ORIGINAL ANALYSIS · REPRODUCIBLE DATA'}</span><h1>{title}</h1></header><article class="a6-body">{body}<div class="a6-table-wrap"><table class="a6-table"><thead><tr><th>UTC</th><th>{'Estado' if es else 'State'}</th><th>{'Categoría' if es else 'Category'}</th><th>{'Confianza' if es else 'Confidence'}</th></tr></thead><tbody>{table}</tbody></table></div><p>{'Cálculos automáticos sobre el archivo del proyecto; no constituyen una verificación externa del tránsito.' if es else 'Automatic calculations on the project archive; not external verification of transit.'}</p></article></main></body></html>'''
        (root / slug).write_text(page, encoding="utf-8")
