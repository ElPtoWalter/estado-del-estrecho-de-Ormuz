# Candidato público exacto del historial — PR #22

Se ha consultado la [nueva revisión preparatoria de GitHub](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/22#pullrequestreview-5638755073). Consta una valoración técnica asistida favorable, no una revisión personal acreditada del propietario ni una aprobación editorial humana. Se corrige esa atribución indebida en ES/EN, en el generador y en el manifest. No se crea una revisión humana en el registro del sitio.

Rama sincronizada con main `34a70ff7d833299b7e9e484a937b30c0908d751c`, conservando sus actualizaciones automáticas de estado, evidencias, parte, salud, inteligencia operativa y sitemap. Esta sincronización de rama no fusiona la PR ni autoriza un despliegue.

## Candidato y recursos

Los [17 archivos candidatos](../drafts/historiales-20261024/public-candidate/) están separados del borrador técnico inicial y del artefacto de Pages. [Manifest de fuentes exactas](../drafts/historiales-20261024/public-candidate-manifest.json), con SHA-256 normalizado a LF, sin aprobación ni fecha inventadas.

| Ruta pública prevista | Función |
|---|---|
| historiales-monitor-ormuz.html | Artículo completo ES; indexable tras aprobación editorial real |
| en-monitor-archives-hormuz.html | Artículo completo EN; indexable tras aprobación editorial real |
| metodo-historiales-monitor-20261024.html | Método ES accesible, siempre noindex,follow |
| en-monitor-archive-method-20261024.html | Method EN accessible, always noindex,follow |
| archivo-monitor-20261024.html | Instantánea de 103 filas con anclas, siempre noindex,follow |
| assets/research/monitor-history-20261024/records.csv | Mismos seis campos y 103 filas del CSV original; finales de línea LF |
| assets/research/monitor-history-20261024/models.csv | Resumen de los dos modelos, separados |
| assets/research/monitor-history-20261024/confidence.csv | 47 MEDIA y 2 ALTA V7, con período |
| assets/research/monitor-history-20261024/windows.csv | Dos ventanas UTC de 21 días, límites exactos y recuentos |
| assets/research/monitor-history-20261024/plot.csv | Fechas exactas y posiciones de los 103 símbolos |
| assets/research/monitor-history-20261024/history-*.svg | Seis gráficos propios conservados, incluidos móviles |
| assets/research/monitor-history-20261024/history-editorial.css | Identidad visual y navegación responsive |

Las fuentes públicas son páginas HTML estáticas y CSV seleccionados. El método identifica los commits y las huellas exactas de las entradas originales; explica que la instantánea es una proyección de campos, no una copia completa de los archivos técnicos. Las fórmulas, filtros UTC y reglas de apilado permiten repetir el análisis en una hoja de cálculo o herramienta equivalente. El código sigue disponible para auditoría del proyecto, fuera del sitio público; los lectores no reciben enlaces a scripts o configuración.

## Integridad y privacidad

No cambian las cifras, tablas, gráficos ni conclusiones contrastadas. Una prueba compara todo el texto visible desde el título hasta el final de los límites en ambos idiomas. Otras contrastan las cinco descargas y los seis SVG con el conjunto congelado. Se mantienen separados los 54 registros anteriores y los 49 V7; 47 MEDIA y 2 ALTA; ventanas de 11 registros en 8 días y 10 en 7 días.

El constructor incorpora cinco excepciones CSV con ruta completa, además del CSV del monitor que ya se publicaba. Continúa bloqueando los demás CSV, JSON, Python, configuración o recursos privados. La auditoría ahora también rechaza CSV inesperados que aparezcan en un artefacto. El candidato verifica esquemas y huellas de entrada, fórmulas peligrosas en CSV, SVG activos o con referencias externas y enlaces técnicos en HTML. No publica posiciones AIS, textos de medios, datos personales ni un registro de aprobación ficticio.

## Construcción y navegación

```text
python history_public_candidate.py --check
python build_public_site.py
python history_public_candidate.py --build
python check_public_links.py drafts/historiales-20261024/preview
python adsense_checks.py --root drafts/historiales-20261024/preview
```

El primer comando verifica el candidato comprometido y su manifest, sin reescribirlos. `--write` sirve para preparar una nueva versión candidata explícita; cualquier cambio requiere volver a revisar sus huellas. El build normal sigue produciendo `_site` sin esta edición. La herramienta genera una copia local en `drafts/historiales-20261024/preview`, pasa los mismos filtros y auditorías y añade enlaces entrantes desde inicio, análisis e historial ES/EN solo en esa copia. Comprueba que `_site` no se haya modificado. El despliegue Pages permanece sin cambios y únicamente consume `_site`.

Los artículos enlazan al monitor, análisis, historial, métodos, contexto y páginas institucionales de su idioma. Los canonical y hreflang es/en/x-default son recíprocos en artículos y métodos. Los enlaces de fuentes funcionan también en la previsualización local; sus identidades HTTPS canónicas quedan declaradas para la futura revisión exacta.

La propuesta SEO autorizable se incluye en el manifest: **solo los dos artículos** pasan a indexables tras aprobación editorial real; metodología ES/EN y archivo permanecen accesibles con noindex,follow, incluso tras una revisión válida. Las cinco páginas actuales conservan noindex y el sitemap local sigue teniendo 56 URLs. Se valida por separado la proyección de **58 URLs**, con dos añadidas. No se escribe una página indexable ni un permiso ficticio para obtener ese resultado. La proyección queda fuera de la superficie servida y sus cifras se calculan sobre el build sincronizado, no sobre un sitemap antiguo.

La política de publicación comprueba huella del documento, revisor identificado, fecha real, aprobación de hechos/derechos y fuentes. Solo una revisión que supere ese control puede retirar los avisos de candidato y pendiente de aprobación. La valoración técnica de GitHub no satisface el control. No existe un interruptor que la convierta en aprobación. El registro real sigue vacío. Los cinco documentos quedan fuera del inventario publicitario, aunque en el futuro se habiliten anuncios en otras páginas.

El build escribe fuera del artefacto un informe de auditoría con las huellas de todos los archivos renderizados y las seis páginas con integración de navegación. Esa es la versión exacta para previsualizar y autorizar. Se conservan anuncios desactivados y los registros de monetización y revisión intactos.

## Verificaciones y autorización pendiente

La suite añade cuatro regresiones sobre atribución ES/EN, valoración técnica insuficiente, política de dos artículos indexables y tres recursos noindex y publicidad siempre desactivada. Se prueban los estados de aprobación con objetos sintéticos únicamente en memoria; no se guardan revisiones ni HTML aprobados de prueba en la entrega. Las pruebas anteriores de integridad, metadatos, privacidad y navegación se mantienen. Resultado local: 408 pruebas Python (390 correctas y 18 opcionales omitidas), 20 de mantenimiento y 23 JavaScript correctas. Construcción, privacidad y enlaces correctos; tres fuentes HTTP 200 con integridad coincidente, 17 recursos locales 200 y diez pruebas de privacidad 404 deliberadas. Validación general: cero errores y diez avisos preexistentes.

Comprobadas las cinco páginas a 320, 390 y 1280 px: 15 casos sin fallos. Sin desbordamiento horizontal del cuerpo; imágenes cargadas, fuentes legibles, tabla y cronología desplazables en su contenedor, confianza móvil sin desplazamiento. Permanecen los 103 símbolos sin superposición. La verificación de accesibilidad es práctica (semántica, alternativas, contraste y teclado), no una certificación completa.

Pendiente: autorización final del propietario sobre los dos artículos, las tres páginas de soporte, cinco descargas, seis gráficos y su integración de navegación, identificados por los manifests. Esa autorización deberá registrar únicamente al revisor real, la fecha real y la versión exacta que se apruebe. La transición de borrador a publicación (avisos, robots y sitemap) y cualquier despliegue requieren autorización expresa; esta herramienta no permite ejecutarlos ni los deduce de una fusión. Si cambia contenido o datos, hay que presentar una nueva huella.

No se fusiona la PR, no se publica esta edición y no se activa ni se solicita revisión de AdSense.
