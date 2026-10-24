# Versión definitiva para autorizar merge y despliegue — PR #22

El titular ha aprobado expresamente en la conversación el candidato exacto `c01c7d968d5dfeab2decaf0f3395181caf8f733f` y la firma institucional **Estrecho Ormuz**. La [última revisión de GitHub](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/22#pullrequestreview-5639358356), registrada el 24/10/2026 a las 18:11:21 UTC, transmite esa decisión. Esta hora es la del registro de la evidencia, no una hora inventada de revisión personal.

Se registra aprobación editorial del titular sobre los artículos ES/EN, tablas, gráficos y fuentes del candidato. No se afirma una certificación periodística externa, una revisión jurídica independiente, nuevas comprobaciones personales, ni una identidad de revisor distinta de la información autorizada. El registro interno no tiene campos `reviewer`, `facts_checked`, `rights_checked` o `reviewed_at` que puedan atribuir verificaciones adicionales. La web muestra exclusivamente la firma institucional, la fecha de aprobación editorial y la asistencia de IA.

## Selección pública definitiva

| Ruta | Política |
|---|---|
| `/historiales-monitor-ormuz.html` | Artículo ES, indexable, firma Estrecho Ormuz |
| `/en-monitor-archives-hormuz.html` | Artículo EN, indexable, firma Estrecho Ormuz |
| `/metodo-historiales-monitor-20261024.html` | Metodología ES, accesible con noindex,follow |
| `/en-monitor-archive-method-20261024.html` | Metodología EN, accesible con noindex,follow |
| `/archivo-monitor-20261024.html` | Archivo tabular con 103 filas, accesible con noindex,follow |
| `/assets/research/monitor-history-20261024/{records,models,confidence,windows,plot}.csv` | Cinco descargas seleccionadas, sin cambios |
| Seis SVG y una CSS en el mismo directorio | Gráficos y diseño del candidato aprobado, sin cambios |

Las cinco páginas quedan permanentemente excluidas de publicidad, incluso si posteriormente se autorizasen anuncios en otras páginas. `monetization.json` conserva todos sus permisos en falso. El identificador configurado de AdSense no se presenta como confirmación de cuenta.

Los artículos mantienen exactamente los datos y conclusiones prudentes: 54 registros anteriores (51 INCIERTO / 3 ABIERTO), 49 V7 (47 MEDIA / 2 ALTA), ventanas UTC de 21 días con 11 registros en 8 días y 10 en 7. No se deducen barcos, caídas del tráfico, horas de cierre ni precisión. No se cambian la clasificación del monitor o sus datos vivos.

## Aprobación verificable y transformación limitada

- El candidato y su manifest originales permanecen intactos, incluido su estado histórico de no autorización. Su SHA-256 normalizado a LF, contrastado con el commit aprobado, es `be55e16a51551f9015eecc0bf21025602933477d2a6cb2fce17d9679fe916d54`.
- [Registro de alcance del titular](history-release-20261024.json): referencia de evidencia, commit aprobado, fecha, firma, límites y huellas de los 17 recursos. Merge, despliegue, anuncios y publicación de datos personales permanecen sin autorización.
- `editorial-reviews.json`: cinco entradas vinculadas a las huellas exactas de los HTML del candidato, como una sola decisión editorial sobre el conjunto. No se inventan cinco revisiones personales independientes.
- `history_release.py` comprueba todo el conjunto y la decisión antes de incorporarlo al build normal. Un recurso o permiso cambiado bloquea la construcción. No existe una excepción general para publicar carpetas de borradores.
- La transformación retira los avisos de candidato/pendiente, conserva la transparencia de IA, añade firma y metadato de autor institucional y aplica la política SEO solicitada. El texto factual, tablas, métodos, datos y SVG permanecen intactos.
- El build añade enlaces desde inicio, análisis e historial en ambos idiomas. Los artículos mantienen enlaces relacionados, fuentes permanentes y alternancia con su metodología. Canonical y hreflang es/en/x-default son recíprocos. El sitemap construido contiene **58 URLs**, dos más que antes; los tres recursos noindex no entran.

Los registros y manifests internos, JSON de configuración, scripts y borradores quedan fuera de `_site`. El enlace de GitHub que acredita la autorización se conserva en la documentación interna, sin exponer la cuenta como autor o revisor en las páginas.

## Verificación reproducible

```text
python -m unittest discover -v
python -m unittest discover -s tests -v
node --test test_public_ui.cjs test_own_projects.cjs
python drafts/historiales-20261024/reproduce.py --check
python history_public_candidate.py --check
python history_release.py --check
python build_public_site.py
python check_public_links.py _site
python adsense_checks.py --root _site
python validate_site.py
```

`release-build-audit.json`, generado fuera de `_site`, identifica las huellas del conjunto renderizado, las seis páginas con navegación y el artefacto completo. Las huellas fuente y HTML renderizado difieren por las transformaciones declaradas; los cinco CSV y seis SVG conservan las mismas huellas. `history_public_candidate.py --build` sigue permitiendo consultar una copia histórica noindex; no es la previsualización definitiva. La versión que se debe autorizar ahora es la construcción normal `_site`.

Resultado local: **417 pruebas Python ejecutadas, 416 correctas y una omitida** por falta de herramientas locales de codificación de vídeo; **20 pruebas de mantenimiento y 23 JavaScript correctas**. Compilados 89 archivos Python. Las advertencias de clasificación impresas por las pruebas pertenecen a sus datos ficticios; no modifican el monitor del proyecto. Reproducción, construcción, privacidad, permisos editoriales y enlaces pasan. Validación general: cero errores y diez avisos preexistentes relativos a duplicados de evidencias, widgets y la página de verificación de Google.

Revisión en navegador de las cinco páginas a 320, 390 y 1280 px: 15 casos sin desbordamientos horizontales del cuerpo, imágenes cargadas, alternativas presentes, captions de tablas y enlace para saltar al contenido. Firma visible solo en los artículos, dos indexables y tres noindex. Los gráficos conservan 103 símbolos separados, sin solapamiento según el análisis de coordenadas original. Esta revisión práctica no se presenta como certificación de accesibilidad completa.

El workflow de despliegue queda preparado para comprobar por HTTP los 17 recursos y su sitemap con `remote_smoke_test.py --history-release` después de una publicación futura. No se ejecuta ese despliegue ahora. La comprobación posterior real de la nueva edición en producción permanece pendiente.

## Acción pendiente del titular

Autorizar expresamente el **commit final de esta PR** para merge y posterior despliegue. La PR se prepara para revisión/fusión, sin fusionarla, desplegarla, activar publicidad ni solicitar revisión de AdSense. Cualquier cambio posterior en hechos, recursos o versión requiere una nueva comprobación de integridad y no hereda automáticamente esta aprobación.
