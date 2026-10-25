# Segundo análisis original: cierre, paso y flujos

Edición de trabajo del 25/10/2026. Borrador ES/EN sin aprobación editorial humana ni autorización de publicación. Firma institucional prevista: Estrecho Ormuz. Rama independiente basada en main `04792ada6cdd99fb8b044d503bd557344a1d283c`; la PR #22 ya fusionada no se modifica.

## Auditoría del material anterior

Se revisaron `drafts/adsense-20261024/cierre-paso-y-flujos.html`, `closure-passage-and-flows.html`, `energy-context.csv` y sus gráficos. Los doce valores del CSV ya eran correctos y se conservan sin tocar el archivo anterior. Los extremos 2025T4/2026T2 y las dos variaciones también eran correctos. La distinción entre anuncio, tránsito y operación comercial era útil, pero el texto no explotaba toda la serie, la matriz no separaba suficientemente un bloqueo físico total, los enlaces aún apuntaban al primer borrador y faltaba un método público detallado.

Esta edición añade la trayectoria completa de 2025 y 2026, variaciones entre trimestres, sensibilidad al elegir otra base, una matriz de cuatro afirmaciones, fuentes permanentes del primer análisis publicado y ocho SVG propios (dos visualizaciones, dos idiomas, dos tamaños). La revisión visual detectó proximidad entre unidades y fuente en el primer diseño móvil; se amplió el espacio y se añadió comprobación de cajas de texto para títulos/unidades/fuente, además de etiquetas numéricas. Los documentos anteriores quedan conservados para trazabilidad.

## Hechos verificados

- Tres URLs primarias consultadas por HTTP; doce cifras de las dos filas de la tabla 4 y fecha del suplemento comprobadas automáticamente contra la fuente. Evidencia en `source-verification.json`; no se copia la página completa ni sus contactos personales.
- Petróleo 2025T1–2026T2: 20,9; 21,0; 21,3; 21,6; 14,9; 4,9 millones de barriles diarios. GNL: 11,7; 11,0; 10,9; 10,5; 7,4; 0,8 miles de millones de pies cúbicos diarios.
- Cambio 2025T4→2026T2: −77,31481481 % y −92,38095238 %. Cambio 2025T1→2025T4: +3,34928230 % y −10,25641026 %. Cambio 2026T1→2026T2: −67,11409396 % y −89,18918919 %.
- La metodología EIA describe estimación complementaria con rutas/puertos y revisiones frecuentes de los volúmenes de Ormuz de 2026. La cabecera de otra edición del STEO no sustituye la fecha del suplemento.
- La OMI identifica su indicador como tránsitos diarios medios en ambos sentidos para información general. No se extraen sus números o gráficos.

## Interpretaciones propias

La matriz propone el tipo de prueba y el alcance necesario para cada afirmación; no certifica haber reunido esos datos. El contraste de bases muestra que la conclusión de una contracción importante de ambas estimaciones se mantiene, aunque cambien los porcentajes. La parte logística, de seguros y cadenas energéticas plantea qué información investigar después; no aporta costes observados ni pronósticos. No atribuye causalidad a la serie.

## Límites y derechos

Solo seis medias trimestrales y una edición. Sin AIS propio, buques identificados, cifras diarias, incertidumbre cuantificada, fechas de cierre o estimación de precisión. No se suman barriles y pies cúbicos ni se transforma la reducción de flujo en consumo perdido o caída de buques. Las ocho cifras decimales calculadas no aumentan la precisión del dato fuente de un decimal. Los períodos son los trimestres de la EIA; no se inventan marcas horarias UTC.

`sources-and-rights.json` distingue la política general EIA efectivamente consultada de lo pendiente: excepciones para materiales de terceros y revisión final del titular. No se declara una licencia abierta de Vortexa o una autorización jurídica independiente. Se usan doce agregados publicados con atribución y gráficos propios; no posiciones privadas, fotografías, logos ni gráficos ajenos. Las explicaciones ES/EN son del observatorio, con asistencia de IA; no se atribuye a la EIA responsabilidad por su traducción o conclusiones.

## Reproducción y previsualización

```text
python energy_data.py
python energy_editorial.py --check
python build_public_site.py
python energy_editorial.py --build-preview
python check_public_links.py drafts/energy-flows-20261025/preview
```

`--verify-online` de `energy_data.py` vuelve a consultar las fuentes y cambia la evidencia fechada: no se ejecuta automáticamente en CI ni refresca el pasado silenciosamente. Para reconstruir gráficos, ejecutar `render_charts.py` con Matplotlib 3.11.2 y NumPy 2.5.4 (versiones de esta ejecución). Arial se usa cuando está disponible y DejaVu Sans como alternativa; otros motores/fuentes pueden producir un SVG binario diferente y requieren nueva revisión. `--write` prepara y sella una versión explícita; `--check` nunca la resella. El CSV de descarga se genera con aritmética Decimal, sin redondeos intermedios, resultados a ocho decimales y formato neutral con punto decimal.

El manifest sella cuatro HTML, ocho SVG, una CSS y un CSV, junto con generadores, textos, fuentes y auditoría gráfica. La copia local `preview/` tiene navegación completa; el constructor comprueba que `_site` no cambie y que los cuatro documentos sigan ausentes de Pages. Los canonical y hreflang están preparados, pero las páginas siguen noindex y fuera del sitemap y RSS. El registro de revisiones humanas y los datos operativos permanecen intactos. La única excepción nueva de recursos es una ruta CSV completa; otros CSV, JSON y Python siguen bloqueados.

## Revisión editorial y autorizaciones pendientes

El titular debe revisar esta versión ES/EN completa: enfoque, matriz, matices de bloqueo físico/servicio comercial, interpretación económica, gráficos, bases elegidas, traducción, atribución y uso de agregados. La revisión de derechos/atribución final queda pendiente; no se inventa un revisor ni se hereda la aprobación del primer análisis. Solo después de una aprobación real sobre huellas exactas se preparará la selección pública definitiva, con autorización separada para merge y despliegue. Anuncios apagados; no se solicita revisión AdSense.
