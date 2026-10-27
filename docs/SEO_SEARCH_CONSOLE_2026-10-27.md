# SEO con datos reales — candidato en borrador, 27/10/2026

## Datos autorizados y alcance temporal

Esta documentación pública solo reproduce los agregados facilitados por el titular y cocientes calculados a partir de ellos. Las exportaciones autenticadas, consultas, países, dispositivos, posiciones por página y comparaciones detalladas quedan fuera del checkout público. El conector Windsor.ai se utiliza exclusivamente en lectura para la propiedad de Ormuz.

| Período / página | Clics | Impresiones | CTR |
|---|---:|---:|---:|
| 01/08–23/10/2026, sitio | 444 | 10.266 | 4,32 % |
| Portada española, mismo período | 416 | 5.872 | 7,08 % calculado |
| Portada inglesa, mismo período | 8 | 1.951 | 0,41 % calculado |
| Guía inglesa de flujos energéticos, mismo período | 0 | 1.416 | 0 % |
| Últimos 28 días del encargo | 302 | 5.635 | 5,36 % |

Posición media global facilitada: 6,07. No es la posición de cada URL ni una explicación suficiente de su CTR. Los datos se han contrastado con el conector. Su fecha de corte precede la publicación completa de las tres investigaciones: no constituyen un resultado posterior de estas publicaciones o de esta PR.

La guía con 1.416 impresiones es `/en-how-much-energy-crosses-strait-of-hormuz.html`, distinta de la investigación reciente `/en-hormuz-closure-passage-flows.html`. No se trasladan sus métricas a esta última ni se reescribe ninguna de las dos.

## Hallazgos y cambios acotados

1. Las descripciones y metadatos sociales de portada prometían «tráfico AIS» / «AIS traffic» sin describir sus límites. Se sustituyen por la evaluación más reciente, hora, confianza y fuentes, aclarando que el observatorio no produce un recuento completo de buques ni mediciones AIS propias. Los títulos y H1 de cada idioma responden a la intención de consultar el estado. El estado operativo, sus evidencias, fecha y cálculo no se editan.
2. Las investigaciones estaban enlazadas en tres bloques al final. En la medición local inicial a 390 px, el primer enlace empezaba a 13.700 px en ES y 13.376 px en EN. Se consolidan en una sección después del indicador, con acceso directo desde el encabezado. En los índices de análisis se colocan inmediatamente después de su introducción. Las guías útiles existentes se conservan.
3. Canonical propios, hreflang ES/EN/x-default coherentes y selector de idioma entre los índices equivalentes. Se corrige el x-default del índice español, que apuntaba a la portada. No se cambian las anotaciones o textos de los artículos aprobados.
4. `seo_surface.py` se aplica al construir después de seleccionar las tres publicaciones selladas. Solo transforma `index.html`, `en.html`, `analisis.html` y `en-analysis.html`; las actualizaciones automáticas de datos de main siguen entrando. La transformación es idempotente y bloquea una selección sin los tres enlaces aprobados.
5. No se añaden scripts, fuentes remotas, imágenes, peticiones externas, etiquetas de analítica o cargadores publicitarios. Las tarjetas adaptan su rejilla a móvil y tienen enlaces enfocados por teclado. El pequeño estilo queda limitado a estas cuatro páginas.

## Lectura prudente del CTR inglés

La consulta privada por URL confirma que la posición inglesa difiere de la global y de la española. La muestra visible de consultas de portada encaja principalmente con la intención de conocer la situación actual; la de la guía energética incluye búsquedas informativas. Las tablas de consultas no cubren todas las impresiones, especialmente en la guía. No puede deducirse de ellas una causa exhaustiva del CTR cero, ni atribuirlo a «contenido de poco valor» o a una penalización.

La propuesta mejora la promesa de la portada y la distribución interna. No promete una mejora de ranking ni un volumen de clics. La posición, la mezcla de países/dispositivos, los competidores, el formato de la SERP y la demanda pueden cambiar los resultados. Google puede generar títulos y fragmentos diferentes de los propuestos. [Títulos](https://developers.google.com/search/docs/appearance/title-link), [fragmentos](https://developers.google.com/search/docs/appearance/snippet).

El HTML auditado es el actual, del 27/10/2026. No se dispone de un registro histórico de los fragmentos que Google mostró entre agosto y el 23 de octubre; no se afirma que la descripción actual fuese la mostrada entonces ni que causara aquel CTR.

## Seguimiento reproducible y privado

`search_console_report.py` funciona sin red ni credenciales. Rechaza entradas y salidas dentro del checkout, no sobrescribe informes y no publica nada. Las pruebas usan únicamente datos sintéticos. No se incluyen exportaciones privadas en Git, en la documentación pública o en Pages.

Configuración de extracción: propiedad `sc-domain:estrechoormuz.com`; búsqueda web; datos finalizados (`include_fresh_data=false`); sin filtros de consulta para totales diarios. Las fechas de Search Console se interpretan en `America/Los_Angeles`, no como días horarios de Madrid. Registrar fecha de extracción, campos, filtros y huellas SHA-256 de cada exportación privada. [Referencia de la API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).

Comparación histórica reproducida: **29/08–25/09 frente a 26/09–23/10/2026**, dos ventanas inclusivas, contiguas y de 28 días, con los mismos días de la semana. Hay extracciones independientes por página para ambas ventanas. Los resultados detallados se conservan en el informe privado, no aquí.

```text
python search_console_report.py --daily PRIVATE/daily.json --pages PRIVATE/pages.json --queries PRIVATE/english_queries.json --previous-pages PRIVATE/pages_previous.json --current-pages PRIVATE/pages_current.json --provenance PRIVATE/provenance.json --end 2026-10-23 --days 28 --output PRIVATE/comparison.json
```

`PRIVATE` debe ser una carpeta privada fuera de este repositorio. Formato de entradas: lista de filas JSON o respuesta Windsor `{status: "done", data: [...]}`. Totales diarios: `date,clicks,impressions,position`; páginas: `page,clicks,impressions,position`; consultas: dimensiones explícitas del manifiesto. La procedencia exige propiedad, tipo web, datos finalizados, zona de fecha y ventanas exactas de las exportaciones por página.

CTR = suma de clics / suma de impresiones. Variación de CTR en puntos porcentuales; variación de clics e impresiones respecto al denominador anterior. La posición se recompone con peso de impresiones y es aproximada por el redondeo de filas. No se promedian CTR diarios ni posiciones sin ponderar. Un día o página ausente no se convierte en cero; se bloquea la comparación incompleta. No se suman los totales por día, página y consulta entre sí. [Límites y privacidad de Search Console](https://developers.google.com/search/blog/2022/10/performance-data-deep-dive).

Tras un despliegue autorizado, registrar su fecha real y el rastreo observado; no inventar una fecha de efecto. Comparar ventanas completas de 28 días antes y después, con intervalo de propagación identificado. Separar el lanzamiento de artículos del cambio de portada. Repetir por URL, dispositivo, país y conjuntos de consultas comparables, manteniendo el mismo nivel de agregación. Revisar también los cambios de posición y composición; una comparación observacional no demuestra causalidad.

## Hipótesis comprobables

| Hipótesis | Observación y criterio de seguimiento | Qué impediría atribuir el resultado |
|---|---|---|
| Una promesa precisa de la portada inglesa facilita el clic pertinente | CTR por URL y consultas de estado, en ventanas equivalentes, desglosadas por dispositivo/país; registrar título realmente mostrado y fecha de rastreo | Cambio de posición o mezcla de consultas, noticias extraordinarias o fragmento reescrito por Google |
| La navegación temprana facilita encontrar las investigaciones | Posición visual y salto por teclado comprobados; prueba de tarea «abrir una investigación y su método»; futuras métricas internas solo con autorización | Search Console no mide clics internos ni lectura completada; no presentar CTR orgánico como conversión de la tarjeta |
| Los enlaces internos ayudan al descubrimiento de las seis versiones | Inspección de URL y evolución de impresiones de cada investigación después de su fecha real de publicación | Impresiones antiguas de las guías no corresponden a los artículos nuevos; impresiones no acreditan indexación actual de todo el sitio |
| La mejora móvil mantiene el coste de carga acotado | Sin desbordamientos ni recursos de terceros nuevos; presupuesto de bytes y scripts antes/después; contrastar con mediciones móviles posteriores | Sin medición de campo/laboratorio válida no se afirma mejora de LCP, INP, CLS o puntuación Lighthouse |

## Sitemap e indexación

La construcción mantiene las 62 URLs elegibles existentes. `seo_surface.py --root _site` examina canonical, noindex y reciprocidad de idiomas, tanto en el ámbito modificado como en el resto de páginas del artefacto. No se retiran URLs ni se cambian políticas de noindex para mejorar artificialmente indicadores.

**62 URLs en el sitemap no son 62 páginas indexadas.** La información disponible en el conector de sitemaps no sustituye el informe de indexación ni la inspección de URL; no se usa su campo obsoleto `indexed`. Comprobar después en Search Console: estado de indexación, canonical elegida por Google, último rastreo y exclusiones para portadas y seis artículos. No se envía sitemap ni se solicita indexación o revisión a Google desde esta preparación. [Alcance de los sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview), [requisitos sin garantía de indexación](https://developers.google.com/search/docs/essentials/technical).

## Validación y límites

Se conservan el motor y los datos operativos, las 46 piezas de los tres conjuntos sellados, sus decisiones editoriales, permisos de monetización y datos personales. Las comprobaciones contrastan esos recursos con la construcción base y con sus manifest. La diferencia pública se limita a las cuatro páginas y al sitemap generado.

Se comprueban Python, JavaScript, compilación, enlaces, privacidad, idioma, canonical/hreflang, construcción y artefacto exacto de CI. Las previsualizaciones y mediciones antes/después se entregan fuera del repositorio. No son una certificación completa de accesibilidad.

La consulta móvil a la API oficial de PageSpeed respondió HTTP 429. No hay una puntuación Lighthouse ni datos de campo Core Web Vitals disponibles en esta comprobación; quedan pendientes de una consulta válida. La navegación móvil y el coste estático sí son verificables localmente, sin atribuirles mejoras de rendimiento no medidas.

Esta PR permanece en borrador. No autoriza merge, despliegue, publicidad, publicación de datos privados o solicitudes de revisión a Google.
