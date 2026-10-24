# Historiales de Ormuz: nueva versión editorial ES/EN

Preparada el 24/10/2026. Borrador con asistencia de IA, sin autorización de publicación ni anuncios. El propietario ha confirmado los recuentos y ventanas; esa comprobación limitada no se convierte en aprobación humana de esta nueva edición.

- [Artículo completo en español](historiales-monitor-ormuz.html).
- [Complete English article](en-monitor-archives-hormuz.html).
- [Plan de publicación bloqueado](publication-plan.json), con canonical/hreflang previstos y condiciones de una futura versión pública.
- [Manifest de esta versión](review-manifest.json), con huellas de los textos, datos, gráficos y código, sin revisor ni fecha de aprobación inventados.

## Qué se conserva y qué cambia

El CSV original y el resumen de entrada se copian sin modificar desde la entrega anterior. Se mantienen los 54 registros del motor anterior, los 49 V7 y las ventanas UTC de 21 días. La distribución completa de confianza V7 es **47 MEDIA y 2 ALTA**; las dos ALTA son de 07/08 y 02/09/2026 y no pertenecen a las ventanas 10–30/09 y 01–21/10. Ambas ventanas siguen siendo exclusivamente MEDIA.

La nueva redacción distingue decisiones publicadas de observaciones marítimas. La cronología agrupa por día UTC y apila para evitar que una fila tape otra; no interpola y no elimina registros. Las horas exactas siguen en el CSV. La altura del apilado no indica tráfico, riesgo o duración. Los modelos permanecen en paneles separados.

Los gráficos tienen fuentes, períodos, unidades, etiquetas de texto, formas además de color, datos tabulados y textos alternativos. La cronología y las tablas anchas se desplazan dentro de su contenedor en lugar de encoger las fechas y los puntos; el gráfico de confianza tiene una composición móvil sin desplazamiento. El cuerpo de la página no debe desbordarse horizontalmente. El CSV de posiciones hace reproducible el apilado.

## Archivos y reproducción

| Archivo | Función |
|---|---|
| [monitor-observations.csv](monitor-observations.csv) | Las 103 filas originales; los modelos se analizan por separado. |
| [source-summary.json](source-summary.json) | Resumen congelado original, sin modificar. |
| [sources.json](sources.json) | Enlaces permanentes a commits, períodos y huellas verificadas por HTTP. |
| [analysis-summary.json](analysis-summary.json) | Conteos, confianza, ventanas, campos ausentes y máximos diarios derivados. |
| [model-summary.csv](model-summary.csv) | Tabla de los dos archivos. |
| [v7-confidence.csv](v7-confidence.csv) | 47 MEDIA y 2 ALTA con período visible. |
| [comparison-windows.csv](comparison-windows.csv) | Límites inclusivos/exclusivos UTC y recuentos. |
| [plot-records.csv](plot-records.csv) | Un símbolo por registro con hora exacta, día y posición de apilado. |
| [chart-audit.json](chart-audit.json) | Número de marcadores, centros únicos y separación mínima medida en los SVG. |

Desde este directorio: `python reproduce.py --check` comprueba los derivados sin red ni dependencias externas. `python reproduce.py --write` solo regenera las tablas derivadas; rechaza un CSV de entrada cuya huella no sea la congelada. Para los gráficos: instalar [requirements.txt](requirements.txt) en un entorno local y ejecutar `python render_charts.py`. No requiere AIS, claves o servicios de pago. `--png-output RUTA` añade copias PNG para revisión local.

## Publicación posterior

Esta carpeta queda fuera del build público incluso si se fusiona la PR editorial. Ambos HTML conservan noindex, contenido original en borrador y publicidad desactivada. Los canonical/hreflang son identidades previstas, no una afirmación de que las rutas existan o estén indexadas. La navegación entre idiomas de la previsualización usa los dos archivos locales.

Antes de publicar habrá que preparar y validar el candidato público exacto, incluidos destinos de recursos y fuentes, respetando la selección de archivos públicos y la protección del código/JSON interno. El plan identifica ese paso; esta PR no añade un publicador ni relaja la seguridad para anticiparlo. No basta con quitar noindex o copiar HTML a la raíz. Cualquier cambio del candidato requiere comprobar su nueva huella antes de una aprobación real y autorizada. editorial-reviews.json y monetization.json permanecen intactos.

El repositorio es público: las fuentes enlazadas contienen metadatos del proyecto ya públicos. No se añaden datos personales, posiciones AIS ni contenido íntegro de medios.
