# Tres borradores originales · 24/10/2026

Preparados con asistencia de IA. **Sin revisión humana acreditada, sin publicación ni anuncios.** Son tres trabajos y sus versiones inglesas; no seis investigaciones independientes. El directorio `drafts/` queda excluido del artefacto público, sitemap y feeds, y cada HTML lleva noindex y una advertencia visible.

| Trabajo | Español | English | Aportación |
|---|---|---|---|
| Historia del monitor | [Qué cuentan realmente los historiales](evolucion-historica.html) | [What the archives actually count](historical-evolution.html) | Dos modelos separados; 54 decisiones antiguas y 49 V7; comparación de ventanas consecutivas de 21 días, 11 frente a 10 registros. No calcula horas de cierre o barcos. |
| Cierre y energía | [Declarar, verificar y medir](cierre-paso-y-flujos.html) | [Closure, passage and flows](closure-passage-and-flows.html) | Matriz de pruebas; índice propio sobre estimaciones trimestrales EIA. Petróleo −77,3% y GNL −92,4% entre 2025T4 y 2026T2; no son cifras actuales ni mediciones del monitor. |
| España y Europa | [El denominador cambia el diagnóstico](espana-europa-exposicion.html) | [The denominator changes the diagnosis](spain-europe-exposure.html) | Dos bases y unidades explícitas: aprovisionamiento español frente al valor de importaciones extracomunitarias de GNL de la UE. No se dividen para inventar un índice de vulnerabilidad. |

[Expediente para revisión final](REVISION_FINAL.md): incluye localizadores, cálculo reproducible, discrepancia de Enagás y unidad de comercio en valor confirmada en el anexo de Eurostat.

## Datos, gráficos y derechos

`monitor-observations.csv` y `monitor-summary.json` congelan el conjunto del proyecto y las huellas de sus fuentes. `energy-context.csv` recoge seis trimestres de estimaciones publicadas por EIA, suplemento de 12/08/2026, tabla 4. `spain-eu-context.csv` conserva proveedor, año, denominadores y la base monetaria de Eurostat. spain-reconciliation.csv conserva el total, volumen por origen, cuota publicada y la discrepancia no reconciliada de Enagás. `sources.json` identifica localizadores, derechos conocidos y pendientes.

Las tres visualizaciones tienen versiones ES/EN, etiquetas y tablas o cifras accesibles en el texto. Son diseños propios creados con Matplotlib sobre los CSV. No se copian fotografías, logotipos o gráficos de terceros ni se redistribuye AIS comercial. La política EIA permite reutilizar sus productos públicos con atribución; no se extiende a los datos comerciales subyacentes ni a imágenes de terceros. Eurostat permite reutilización con reconocimiento y señalando las adaptaciones; sus conclusiones no se atribuyen al organismo. Enagás no se trata como una fuente con licencia abierta: solo se citan cifras puntuales y se mantiene pendiente la comprobación humana de derechos antes de autorizar el artículo. Los datos de 2025 pueden ser provisionales o revisados.

Para reproducir los gráficos: instalar `requirements.txt` en un entorno de trabajo y ejecutar `python render_charts.py` desde este directorio. No requiere una API, cuenta o servicio de pago. Las gráficas leen únicamente los CSV congelados. No volver a ejecutar `original_research.py` sobre datos nuevos y conservar una aprobación anterior: cambiaría el objeto revisado.

## Revisión necesaria antes de publicar

1. Contrastar fuentes primarias, tablas, períodos, unidades y cálculos. Para historia, distinguir el archivo retenido de un registro completo de ejecuciones y de tráfico físico.
2. Revisar redacción, conclusiones y alcance. La diferencia de recuentos entre ventanas no prueba una tendencia marítima.
3. Comprobar derechos y atribución de cada conjunto y visualización. No aprobar automáticamente el campo de derechos por existir un enlace.
4. Preparar las rutas públicas y los enlaces definitivos en una rama. Una aprobación sobre el HTML privado no autoriza una versión pública diferente.
5. Una persona real debe aprobar esa versión final, con nombre, fecha, fuentes, comprobaciones y contribución original en `editorial-reviews.json`. La política existente verifica el SHA-256 exacto; una edición material invalida la aprobación. No se ha creado ningún registro ficticio.
6. Construir y comprobar la versión pública y obtener autorización de publicación. Los anuncios seguirán apagados. Aprobar un artículo no equivale a aprobar AdSense ni autoriza solicitar revisión de la cuenta.

La revisión técnica de este trabajo no se presenta como revisión editorial humana.
