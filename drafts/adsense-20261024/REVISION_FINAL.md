# Tres análisis: expediente para revisión editorial final

24/10/2026. Asistencia de IA; comprobación técnica y contraste preparatorio de fuentes. **Ninguna aprobación humana registrada.** Los seis HTML y sus recursos están fuera de Pages, sitemap y feeds. El repositorio es público; aquí no se incorporan datos personales del titular o del revisor sin autorización.

## 1. Qué cuentan realmente los historiales

[Leer ES](evolucion-historica.html) · [Read EN](historical-evolution.html) · [Datos CSV](monitor-observations.csv) · [Resumen y huellas](monitor-summary.json) · [Gráfico ES](history-es.svg) · [Chart EN](history-en.svg).

- **Aportación:** lectura propia de decisiones retenidas, dos modelos separados y comparación de ventanas de igual duración. No es una serie AIS ni un indicador nuevo.
- **Fuente y corte:** history.json y operational-intelligence-history.json en el commit 373545ee; huellas normalizadas CRLF→LF en el resumen. Motor anterior: 54 filas, 12/07–18/10/2026; V7: 49, 07/08–21/10/2026. Se conservan sin refrescarlos con la última consulta de la web.
- **Cálculos:** conteos por modelo/estado. Ventanas UTC [10/09, 01/10) y [01/10, 22/10), 21 días cada una: 11 registros en 8 días frente a 10 en 7 días. El intervalo es inclusivo al inicio y exclusivo al final. No se interpola ni se supone cero actividad en días sin fila.
- **Gráficos:** dos paneles de puntos, uno por motor; fecha UTC, sin líneas entre observaciones. Los 49 registros V7 tienen la misma etiqueta, no 49 verificaciones independientes de barcos.
- **Límites:** retención y frecuencia irregular; definiciones distintas; ningún ratio numérico de tráfico en las 49 filas. No permite horas de cierre, exactitud, riesgo de viaje, volúmenes o tendencia física. No fusionar ambos modelos.
- **Decisión editorial:** comprobar si el enfoque, título, traducción y límites son suficientemente claros para publicarlo como análisis histórico. No atribuir revisión o validación humana a los datos por haber reproducido los cálculos.

## 2. Declarar, verificar y medir

[Leer ES](cierre-paso-y-flujos.html) · [Read EN](closure-passage-and-flows.html) · [Datos CSV](energy-context.csv) · [Gráfico ES](energy-es.svg) · [Chart EN](energy-en.svg).

- **Aportación:** matriz propia de evidencia que separa anuncio, paso físico y operación comercial; comparación histórica de dos productos sin sustituir la clasificación del monitor.
- **Fuente exacta:** [EIA, Global Energy Security Data, tabla 4](https://www.eia.gov/outlooks/steo/report/energysecurity/article.php), suplemento de **12/08/2026**; no confundir con la fecha de cabecera del STEO que cambia mensualmente. Se volvieron a contrastar las doce cifras de la tabla con los seis trimestres del CSV.
- **Unidades:** petróleo total —crudo, condensados y productos— en millones de barriles/día; GNL en miles de millones de pies cúbicos/día. Son estimaciones publicadas por EIA basadas en seguimiento de terceros, no posiciones AIS propias ni una descarga de su base comercial.
- **Cálculos:** índice = dato / dato de 2025T4 × 100. Cambio = (dato 2026T2 / dato 2025T4 − 1) × 100. Petróleo 21,6→4,9: −77,3148%, redondeado −77,3%; GNL 10,5→0,8: −92,3810%, redondeado −92,4%. No se suman ambas unidades.
- **Gráficos:** transformaciones propias, ambas series como índices sobre su referencia; los datos absolutos permanecen en CSV y texto. Un índice común no significa equivalencia energética.
- **Límites:** promedios históricos y revisables, no situación de octubre, ni prueba causal de una decisión política, ni volumen perdido frente a un escenario contrafactual. Un cruce confirmado no demuestra normalización comercial.
- **Derechos y decisión:** revisar atribución y alcance de [reutilización EIA](https://www.eia.gov/about/copyrights_reuse.php). Solo se usan estimaciones publicadas y diseño propio; no fotos, logotipos ni base comercial subyacente. Aprobar enfoque, redacción y traducción sobre la versión exacta.

## 3. España y Europa: el denominador cambia el diagnóstico

[Leer ES](espana-europa-exposicion.html) · [Read EN](spain-europe-exposure.html) · [Cuotas CSV](spain-eu-context.csv) · [Reconciliación CSV](spain-reconciliation.csv) · [Gráfico ES](exposure-es.svg) · [Chart EN](exposure-en.svg).

- **Aportación:** contraste de bases, unidades y perímetros. Ahora distingue explícitamente aprovisionamiento físico español de **valor monetario** de importaciones extracomunitarias europeas de GNL. No es una comparación de vulnerabilidad.
- **Enagás:** [informe 2025](https://www.enagas.es/content/dam/enagas/es/ficheros/sala-de-comunicacion/publicaciones/informe-sistema-gasista/informe-sistema-gasista-espa%C3%B1ol-2025.pdf), páginas impresas 23–25 (índices PDF 22–24). Inspección visual de las tres páginas: total 372.498 GWh, mapa Catar 6.403 GWh y barra verde 2025 Catar 1,735%.
- **Discrepancia identificada:** 6.403 / 372.498 × 100 = 1,7189354%, frente al 1,735% del gráfico. Total × cuota publicada = 6.462,8403 GWh, diferencia 59,8403 GWh. **No se explica la diferencia como redondeo ni se escoge una cifra armonizada sin evidencia**. Se retiró la anterior inferencia de 6,46 TWh como aproximación al suministro catarí y se muestran ambas presentaciones con su límite. 6.403 GWh / 1.000 = 6,403 TWh es solo conversión del valor del mapa.
- **Eurostat:** [noticia 25/03/2026](https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20260325-3) y [anexo XLSX](https://ec.europa.eu/eurostat/documents/d/products-eurostat-news/imports-energy-products-2025), hoja `VISUAL 2`: A2 define cuota del comercio **en valor**, D9 identifica Qatar y E9 = 8,855309243451158%, redondeado 8,9%. No es cuota en toneladas, GWh ni volumen físico.
- **Gráficos:** dos barras propias sobre 100 con bases rotuladas; conservan las cuotas publicadas, no una serie física armonizada. La discrepancia española se explica en el texto. España pertenece a la UE; los ámbitos tampoco son independientes.
- **Límites:** no inferir 8,9 / 1,735 como multiplicador de riesgo; no estimar energía no servida, pérdidas, factura o exposición actual de 2026. Para comparar físicamente hace falta una base homogénea actualizada y reconciliada.
- **Decisiones pendientes:** el editor debe decidir si publicar esta lectura metodológica con la discrepancia claramente expuesta o esperar su reconciliación. La comprobación de derechos de Enagás sigue pendiente; no se afirma licencia abierta. [Eurostat permite reutilización con atribución y condiciones](https://ec.europa.eu/eurostat/help/copyright-notice); no se usa su fotografía ni se le atribuyen conclusiones propias.

## Reproducción y aprobación

`python review_calculations.py` reproduce los resultados desde los CSV sin red ni claves. `python render_charts.py` reproduce los seis SVG con las dependencias declaradas; las etiquetas no mezclan valor y volumen. [Fuentes y localizadores](sources.json).

[Manifest de revisión](review-manifest.json) identifica las huellas de los seis HTML, insumos y gráficos para saber qué versión se revisa. No es editorial-reviews.json y no lo autoriza: mantiene aprobación pendiente y persona/fecha nulas. Cambiar un texto, gráfico o dato exige revisar la nueva huella.

Autorizaciones distintas: (1) aprobación editorial factual, de redacción, fuentes, derechos y traducción de cada análisis; (2) elección de rutas públicas y revisión de su versión definitiva; (3) autorización de publicación/despliegue. La futura aprobación debe referirse a la versión pública exacta, después de resolver sus enlaces y metadatos. No se inventará un revisor ni se trasladará una aprobación entre versiones. La aprobación del artículo no activa publicidad ni autoriza una solicitud de revisión de AdSense.
