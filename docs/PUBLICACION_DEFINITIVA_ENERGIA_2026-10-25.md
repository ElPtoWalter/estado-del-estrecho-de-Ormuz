# Versión definitiva para autorización separada de publicación — PR #23

El titular aprobó expresamente el contenido del candidato `e40b057eb86ab1a9d4b5fec0d5b55fa1f40d6cd4`: artículos ES/EN, gráficos, CSV, fuentes y conclusiones. La [revisión de GitHub](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/23#pullrequestreview-5642834731), registrada el 25/10/2026 a las 10:58:02 UTC, recoge esa decisión y la firma institucional **Estrecho Ormuz**. La hora corresponde al registro de la evidencia; no se presenta como hora de una comprobación personal.

La aprobación editorial permite preparar esta selección pública. No autoriza merge, despliegue, publicidad o publicación de datos personales. La PR se mantiene en borrador hasta una autorización posterior, como pide la revisión. No se inventan identidades, nuevas revisiones personales, certificaciones jurídicas o permisos de terceros. No se confirma la cuenta AdSense a partir del identificador configurado.

## Selección exacta

| Ruta | Política |
|---|---|
| `/ormuz-cierre-paso-flujos.html` | Artículo ES indexable, firma Estrecho Ormuz |
| `/en-hormuz-closure-passage-flows.html` | Artículo EN indexable, firma Estrecho Ormuz |
| `/metodo-flujos-energia-20261025.html` | Método ES accesible con `noindex,follow` |
| `/en-energy-flow-method-20261025.html` | Método EN accesible con `noindex,follow` |
| `/assets/research/energy-flows-20261025/energy-series.csv` | Un CSV reproducible común a ambos idiomas |
| Ocho SVG y `energy-editorial.css` en el mismo directorio | Recursos aprobados sin cambios |

Los artículos tienen canonical propio y hreflang ES, EN y x-default recíprocos. Las metodologías tienen sus propios canonical y pares hreflang; quedan fuera del sitemap. Solo se incorporan los dos artículos al sitemap. Hay enlaces de entrada desde portada, análisis y hemeroteca en cada idioma; se conservan navegación, fuentes y referencias al primer análisis publicado.

Las cuatro páginas mantienen publicidad desactivada incluso si se autorizasen anuncios en otras secciones. Los permisos globales de `monetization.json` siguen en falso. Las páginas públicas no incluyen el expediente de aprobación, identificadores personales, scripts Python, configuraciones o JSON internos.

## Cambios autorizados

En el cuerpo de cada artículo se realizan únicamente los dos ajustes de la revisión:

1. La pregunta inicial existente enlaza a la guía publicada del mismo idioma sobre apertura y tráfico reducido. No se cambia su texto.
2. Se eliminan los dos enlaces CSV redundantes de las leyendas de las figuras. La fila final de descargas conserva una descarga CSV clara por idioma. Cada metodología conserva también un acceso único al mismo CSV.

La transición de presentación añade firma y metadato institucional, conserva la asistencia de IA, sustituye el estado de borrador por la aprobación real y aplica la selección de indexación. No atribuye al titular nuevas verificaciones ni una certificación de derechos de terceros. En la metodología se actualiza solo el estado editorial; permanecen las cautelas sobre Vortexa, atribución y ausencia de autorización jurídica independiente.

Las doce cifras EIA, unidades, seis períodos, fórmulas, cálculos, tablas, conclusiones y fuentes del artículo aprobado no cambian. Una prueba compara todas las palabras del cuerpo antes y después, descontando exclusivamente las dos etiquetas de descarga eliminadas. Los ocho SVG, el CSV y la CSS conservan sus bytes originales.

## Integridad y procedimiento

El candidato original y sus generadores permanecen intactos. Su manifest normalizado a LF tiene SHA-256 `530538a57a1d94ca00268996c4938c63885d974fc50ace7e990d54d8a6a6a77d`. `docs/energy-release-20261025.json` registra separadamente la evidencia real, su alcance, las catorce huellas originales y los permisos que siguen sin otorgarse. `editorial-reviews.json` vincula los cuatro HTML a esa única decisión sobre el conjunto aprobado, sin campos de revisor, comprobaciones jurídicas o verificaciones adicionales.

`energy_release.py` verifica el sello original y el registro antes de transformar las páginas. `build_public_site.py` crea la selección en `_site`, actualiza los enlaces de entrada y comprueba todas las huellas, canonical, hreflang, indexación, sitemap, privacidad y enlaces. La ausencia de una aprobación exacta o cualquier modificación del candidato bloquea la construcción. Los recursos técnicos originales no se copian a Pages. El primer análisis de la PR #22 conserva sus huellas y controles independientes.

```text
python -m unittest discover -v
python -m unittest discover -s tests -v
node --test test_public_ui.cjs test_own_projects.cjs
python energy_editorial.py --check
python energy_release.py --check
python build_public_site.py
python check_public_links.py _site
python adsense_checks.py --root _site
python validate_site.py
```

El informe local `drafts/energy-flows-20261025/release-build-audit.json` contiene las huellas de la selección y del artefacto completo. CI conserva el artefacto comprobado durante siete días mediante `upload-artifact`; esa operación no publica en GitHub Pages. La previsualización antigua `energy_editorial.py --build-preview` corresponde exclusivamente al estado previo a la aprobación y ya no forma parte del flujo definitivo de CI.

La evidencia JSON se sube como un artefacto de auditoría separado: no se incorpora al ZIP del sitio ni al directorio que consume GitHub Pages. La copia del sitio conserva también sus archivos públicos ocultos seleccionados, como `.well-known/security.txt`.

El workflow de despliegue queda preparado para ejecutar `remote_smoke_test.py --history-release --energy-release` solo después de una futura publicación autorizada. Verificará por HTTP las huellas de los catorce recursos de esta edición y la selección del sitemap, además del primer análisis. No se ha ejecutado ese despliegue durante esta preparación. La comprobación real de la nueva edición en producción queda pendiente de autorización y publicación.

## Verificación local de esta preparación

- 436 pruebas Python: 435 correctas y una omitida por ausencia de herramientas opcionales de render de vídeo, ajena a esta edición. Las diez regresiones nuevas cubren el sello, el alcance de la aprobación, las dos modificaciones, las rutas, los anuncios y la futura comprobación remota.
- 20 pruebas de mantenimiento y 23 pruebas JavaScript correctas. Compilación de 95 archivos Python correcta.
- Construcción y enlaces públicos sin errores. Artefacto de 234 archivos; sitemap de 60 URLs, con los dos artículos y sin las dos metodologías. Auditoría de privacidad y anuncios correcta.
- 31 comprobaciones HTTP: catorce recursos de esta edición con 200 y huellas correctas, diez rutas internas con 404 y siete enlaces externos/publicados con 200. Se vuelven a contrastar las doce cifras EIA y la fecha del suplemento, conservando intacto el expediente original.
- 32 archivos fuente sellados del candidato aprobado sin cambios; diez archivos protegidos del monitor, automatización y monetización iguales a `main`. La decisión y los recursos del primer análisis siguen intactos.
- Las cuatro páginas se comprueban a 320, 390 y 1280 px: sin desbordamiento horizontal, una descarga CSV por página, gráficos correctos para cada tamaño, alternativas textuales y regiones de tablas accesibles. Se inspeccionan las ocho vistas de gráficos ES/EN en móvil y escritorio. Las coincidencias de la base 100 conservan sus coordenadas y símbolos diferenciados.
- El validador del sitio fuente termina sin errores y con diez avisos existentes: seis evidencias duplicadas, dos páginas widget sin h1 y metadatos deliberadamente mínimos del archivo de verificación de propiedad. No son fallos de las cuatro páginas nuevas.

## Límites que permanecen

Los datos describen seis estimaciones trimestrales EIA, 2025T1–2026T2, del suplemento de 12/08/2026. No describen el tráfico actual, no son mediciones AIS propias y no acreditan días de cierre, recuentos de buques o causalidad. Las bases, unidades y precisión de la fuente permanecen visibles. La aprobación editorial no equivale a una licencia abierta de todos los materiales de terceros.

La autorización pendiente es sobre el commit definitivo y, por separado, su merge y publicación. AdSense y cualquier solicitud de revisión comercial siguen fuera de ese permiso.
