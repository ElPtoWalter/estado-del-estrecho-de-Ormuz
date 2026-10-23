# Auditoría posterior al despliegue · 23/10/2026

Versión pública comprobada: `e22cff5b15474bef3d1b1096940e024ba085d099`. La PR #19 ya está fusionada; no se vuelve a fusionar ni se inicia otro despliegue. [Pages](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/40016394962) y su CI terminaron correctamente.

## Verificado en producción

| Superficie | Resultado |
|---|---|
| Páginas ES/EN | 170 URLs HTML responden 200; canonical y noindex coinciden con la versión publicada. Se incluyen los archivos especiales de verificación y 404. |
| Monitor | Mismo estado, dimensiones, confianza y hora de comprobación en ambos idiomas. Es una instantánea fechada; no se modifica su clasificación. |
| Radar ES/EN | No hay iframe ni script del proveedor antes de pulsar. Tras pulsar, MyShipTracking muestra mapa, barcos y controles. No se certifica cobertura AIS ni se usa el mapa para cambiar el estado. |
| Archivo de evidencias | Filtro inglés: 60 resultados → búsqueda sin coincidencias: 0 → restablecer: 60. Funciona sin solicitar JSON interno. |
| Diario y hemeroteca | Contenido y fechas conservados, aviso de automatización, canonical histórico y noindex. La edición existente no ha sido sustituida por el piloto. |
| RSS | 30 entradas ES y 30 EN, todas a páginas históricas existentes; sus destinos conservan noindex y ausencia de anuncios. |
| Enlaces | 192 destinos internos accesibles. Se detectan fallos de destino semántico y anclas descritos abajo. |
| AdSense | Cero cargadores en el HTML revisado; sin cargador propio en los scripts observados del navegador. Las cuatro opciones siguen en false. La promoción propia etiquetada es independiente. |
| Archivos internos | 330 rutas comprobadas sin respuesta pública accesible, incluidos JSON, Python, workflows, documentos técnicos, .env y .git. No se guardan sus cuerpos en las evidencias. |
| SEO técnico | Sitemap público con 74 URLs y destinos válidos; robots permite rastrear. Esto no demuestra indexación real en Google. |

## Problemas y propuesta de corrección

La comprobación HTTP por sí sola no detectaba **138 selectores ES/EN que abrían otra página**, en lugar de su traducción. En archivos históricos esto perdía la fecha de la edición. Además, tres enlaces ingleses apuntaban a `en.html#estado-actual`, pero el identificador real es `current-status`. La portada inglesa ofrecía una API que la superficie pública no publica.

La rama independiente `codex/postdeploy-audit-20261023` repara los selectores usando el alternate declarado, conserva la fecha y el cuerpo de cada artículo, corrige las tres anclas y sustituye aquella mención a API por fuentes. También repara dos rutas UKMTO/JMIC que devuelven 404: el índice de productos y la URL del mismo boletín histórico de mayo, sin sustituirlo por otro documento. El comprobador de enlaces ahora detecta los dos tipos de regresión interna, además de destinos ausentes y RSS inválido.

La propuesta pasa 370 pruebas Python de raíz (18 omitidas por dependencias opcionales de montaje), 20 de mantenimiento y 23 JavaScript. Compilación y enlaces del artefacto: cero errores. Validación de fuente: cero errores y 10 avisos conocidos, relativos a evidencias duplicadas, verificación Google y widgets. El nuevo comprobador detecta 141 errores antes de la corrección y ninguno después.

**La corrección no está desplegada:** se entrega en una PR sin fusionar. `status.json`, `operational-intelligence.json` y `monetization.json` conservan sus hashes; no se cambian reglas, datos ni clasificación del monitor. No se solicita otra generación Gemini. El piloto con claves se limita a cambios de sus archivos editoriales, evitando que una PR de navegación o documentación consuma cuota; el CI sin claves se conserva.

## Pendiente o no acreditado

Se comprobaron 526 URLs externas por HTTP: 517 accesibles, dos 404 corregidos en la propuesta y siete que requieren revisión manual. Estas siete son dos CNBC con timeout, dos enlaces de compartir en X y una página UNCTAD con 403, un documento EIA con 503 y un PDF Enagás con error de conexión. Un bloqueo o timeout no acredita un enlace roto. No se certifican el contenido íntegro ni las redirecciones JavaScript de Google News o paywalls. La verificación de mapas es de esta sesión, no una garantía de disponibilidad futura. No se midieron Core Web Vitals de usuarios reales, clics, impresiones, indexación efectiva, RPM ni ingresos.

Rutas oficiales comprobadas para las dos correcciones: [productos JMIC](https://www.ukmto.org/partner-products/jmic-products) y [Update 040, 1 de marzo–3 de mayo de 2026](https://www.ukmto.org/-/media/ukmto/products/update-040-jmic-advisory-note-03-may.pdf). Se corrigen únicamente enlaces, sin incorporar el contenido del boletín al motor operativo.

AdSense requiere revisar la cuenta, motivo exacto de rechazo, titularidad y consentimiento. Search Console permite decidir qué contenidos priorizar a partir de datos reales. El [plan específico](PLAN_ADSENSE_SEO_2026-10-23.md) distingue los pasos públicos de los que requieren acceso del propietario.
