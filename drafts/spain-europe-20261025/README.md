# Tercer análisis original: España, Europa y Ormuz

> Archivo histórico del estado previo a aprobación. El titular aprobó después el candidato exacto `21123ca1`; los originales y su manifest se conservan intactos. La versión pública definitiva y el alcance de la decisión se documentan en [PUBLICACION_DEFINITIVA_ESPANA_EUROPA_2026-10-26.md](../../docs/PUBLICACION_DEFINITIVA_ESPANA_EUROPA_2026-10-26.md). Los estados pendientes y comandos de previsualización siguientes describen aquel borrador histórico, no la selección definitiva.

Edición para revisión editorial, preparada el 25/10/2026 sobre main `63aba657f3cb269d0a686eec4b43dd5621c65fa9`, que ya contiene las publicaciones de las PR #22 y #23. Firma institucional **prevista**: Estrecho Ormuz. Preparación con asistencia de IA. No hay aprobación editorial humana, autorización de publicación o permiso de publicidad para esta edición.

## Auditoría y aportación

Se conservan intactos los cuatro archivos anteriores indicados en el encargo: `espana-europa-exposicion.html`, `spain-europe-exposure.html`, `spain-eu-context.csv` y `spain-reconciliation.csv`, dentro de `drafts/adsense-20261024/`. Sus huellas están en `source-verification.json`. Sus cifras de referencia y la advertencia de denominadores incompatibles eran útiles. La edición nueva amplía la comprobación, sustituye una comparación gráfica que podía invitar a equiparar magnitudes y desarrolla el relato sobre origen, ruta y mercado.

El hallazgo nuevo está en el Excel oficial de Operación física enlazado en la página 80 del propio informe Enagás. La hoja «Pág. 25» identifica 2025 en E4, Qatar en B12 y una fracción literal `0.01718890770907905` en E12. Su caché de gráfico contiene el mismo valor. Es aproximadamente 1,718891 %, muy próximo al cociente de mapa y total. No se utiliza una columna histórica de otro año.

## Dictamen de la discrepancia

| Lectura | Valor | Localizador |
|---|---:|---|
| Total físico | 372.498 GWh | Enagás PDF, p. impresa 23 |
| Catar en el mapa | 6.403 GWh | Enagás PDF, p. impresa 24 |
| Cuota del gráfico | 1,735 % | Enagás PDF, p. impresa 25; barra verde 2025 |
| Cociente propio mapa/total | 1,718935403680… % | 6403 / 372498 × 100 |
| Excel oficial en porcentaje | 1,718890770907905 % | Pág. 25!E12 × 100 |

**Discrepancia documental no resuelta.** Las dos últimas lecturas coinciden a tres decimales, pero no explican la cuota de 1,735 % del PDF. No se obtiene una conciliación específica de SL-ATR ni una explicación del emisor, y no se ha contactado con Enagás. La nota general de provisionalidad del informe no demuestra la causa. No se adjudica a redondeos, revisiones, diferencias de base o erratas.

La diferencia entre gráfico y cociente es de 0,0160645963… puntos porcentuales. La comprobación inversa da 6.462,8403 GWh, 59,8403 GWh más que el mapa. Son resultados aritméticos hipotéticos, no volúmenes observados, cargamentos adicionales o energía perdida. No se elige una cifra oficial definitiva.

La aportación visual adicional usa el mismo numerador de 6.403 GWh con dos denominadores físicos españoles: total 372.498 GWh, aproximadamente 1,719 %, y GNL 248.084 GWh, aproximadamente 2,581 %. No incluye la cuota europea en el gráfico ni crea un indicador de riesgo relativo.

## Fuentes, unidades y derechos

| Fuente | Período, unidad y ámbito | Uso y límites de derechos |
|---|---|---|
| Enagás PDF y Excel oficial enlazado | 2025; GWh y cuota de aprovisionamientos físicos españoles | Aviso legal, apartado 7: no se acredita licencia abierta general. Cita limitada de hechos numéricos con atribución, obra gráfica y cálculos propios. Pendiente valorar la base de reutilización antes de publicar. No se redistribuyen PDF/Excel, mapas, gráficos, fotos o logos. |
| Eurostat, noticia 25/03/2026 y anexo | 2025; valor de importaciones extracomunitarias de GNL de la UE, CN 27111100 | Datos estadísticos reutilizables con atribución y condiciones; excepciones de terceros. Adaptaciones propias y no responsabilidad de Eurostat indicadas. No se copia la fotografía. |
| AIE, ficha Ormuz fechada febrero 2026 | Contexto geográfico y transmisión de mercado | Referencia enlazada y paráfrasis limitada. Sin copiar cifras Kpler, gráficos o bases; no se afirma una licencia general. |
| Observatorio | Cocientes, residuales, matriz y explicación originales | Propuestos para revisión, con asistencia de IA; sin aprobación humana ni revisión jurídica independiente acreditadas. |

Eurostat `VISUAL 2!A1:A2, D4:E9` confirma 8,855309243451158 %, redondeado a 8,9 %, **por valor monetario**, no volumen, consumo o toda la energía. Su anexo también contiene cuotas por masa neta; no se afirma que falten todos los datos físicos. Masa neta y GWh requieren armonización y conversiones justificadas. No se usan los totales de otros bloques del libro para reconstruir silenciosamente la cuota seleccionada.

Las siete URLs oficiales devuelven 200 en la consulta documentada. Se contrastan seis entradas y los metadatos seleccionados del PDF/Excel. La inspección visual del PDF es asistida por IA y se limita a las páginas pertinentes, no certifica todo el informe. Los originales descargados y sus renders quedan fuera del repositorio y de Pages; el expediente conserva solo huellas, localizadores y comprobaciones seleccionadas.

## Entrega y reproducción

Cuatro HTML: artículos ES/EN y método ES/EN. Dos CSV seleccionados: seis entradas con fuentes/localizadores y ocho resultados con unidades, fórmulas y límites. Ocho SVG originales: dos figuras, dos idiomas y variantes móvil/escritorio. El manifest sella quince recursos junto con generadores, textos, datos y evidencias. Las tres lecturas de Enagás ocupan filas separadas; no se desplazan sus valores horizontales. La escala ampliada queda visible y no representa intervalos de incertidumbre.

```text
python spain_data.py
python spain_data.py --verify-downloads RUTA_A_ORIGINALES_DESCARGADOS
python spain_editorial.py --check
python build_public_site.py
python spain_editorial.py --build-preview
python check_public_links.py drafts/spain-europe-20261025/preview
python adsense_checks.py --root drafts/spain-europe-20261025/preview
python -m unittest discover -v
python -m unittest discover -s tests -v
node --test test_public_ui.cjs test_own_projects.cjs
```

La comprobación opcional de originales usa pypdf y openpyxl solo para lectura; CI no requiere descargar documentos ni esos paquetes. Los resultados se calculan con Decimal sin redondeo intermedio, y el CSV conserva ocho decimales aritméticos sin aumentar la precisión de origen. `render_charts.py` utiliza Matplotlib 3.11.2 y NumPy 2.5.4; Arial, con DejaVu Sans y sans-serif de respaldo. Otro motor o fuente puede cambiar los bytes y exige revisar la nueva versión. Hay pruebas de contenido activo SVG, inyección CSV, denominadores, conversión de fracción, exclusión y ausencia de aprobación heredada.

`--write` prepara expresamente una nueva versión sellada de borrador; `--check` nunca resella. `--build-preview` superpone los recursos sobre una **copia local**, comprueba privacidad/enlaces y demuestra que `_site` no cambia. Los quince recursos nuevos siguen ausentes del artefacto normal de Pages. Sus cuatro HTML tienen noindex,follow y quedan fuera de sitemap/RSS. Canonical y hreflang están preparados sin hacerlos indexables. Solo dos rutas CSV completas se admiten para esta previsualización; no se abre una carpeta de CSV o archivos internos.

CI construye y comprueba la previsualización en su espacio temporal, sin subirla como artefacto adicional. La previsualización entregada es local. Los controles de las dos publicaciones previas siguen activos y sus recursos no cambian. No se toca monitor, clasificación, datos operativos, registros de aprobación, anuncios o datos legales privados.

## Revisión pendiente

El titular debe revisar el texto completo de ambos idiomas, el dictamen de discrepancia, el uso de los dos denominadores españoles, gráficos, traducción, conclusiones y la base de reutilización de cifras Enagás. La decisión deberá identificar un commit exacto. Esta preparación técnica no registra esa aprobación ni autoriza merge, despliegue o solicitud de revisión AdSense.
