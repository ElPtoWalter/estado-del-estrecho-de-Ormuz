# Revisión de sincronización y publicación — PR #30

Esta revisión incorpora main 78fe4b79e1faac2b8b1abe37b5cd199d74dfe876, incluida la edición del Diario del 19/11. Si main vuelve a avanzar, debe repetirse la sincronización y la CI del nuevo SHA. No se ha autorizado una fusión ni un despliegue.

## Conservación de producción

La incorporación no regenera la edición periodística aprobada: sus HTML ES/EN, archivos fechados, JSON, feeds, índices y avances de portada se comparan con main. Tampoco se recalcula la clasificación. Solo se refrescan el parte y RSS derivados del V7 existente. La fecha de generación de un documento no sustituye la hora real de verificación; si V7 está anticuado, debe seguir figurando como tal.

## Avisos y carreras

- El grupo de publicación serializa todo el workflow, incluidos comprobación y avisos, sin cancelar al emisor activo cuando llega un despliegue posterior. GitHub puede sustituir una ejecución pendiente por otra: se anuncian los últimos cambios visibles, no todos los estados intermedios.
- El job de avisos sigue compartiendo el grupo de escritura con los dos actualizadores. No se cambian permisos ni se habilita la variable de envío.
- Antes de cada canal y de cada reintento se comprueba por HTTP el commit construido, V7 y seis páginas reales. Se vuelve a leer el manifiesto después de los HTML para detectar un despliegue que cambie durante las lecturas.
- La CLI de entrega también comprueba el HEAD remoto. Si main avanzó respecto al checkout, no envía. Solo acepta descendientes del commit construido que modifiquen exclusivamente recibos: se examina cada commit intermedio para detectar cambios de publicación aunque se hayan revertido después.
- Los commits que contienen solo recibos no disparan otro despliegue por push. Los recibos por canal evitan repetir entregas ya reconocidas; se guardan localmente tras cada intento y en artefacto separado incluso si falla su push. No se usa force push. Un avance externo durante el push puede impedir persistirlos; ese fallo debe recuperarse antes de reintentar una entrega ambigua.
- Las pruebas usan transportes simulados y repositorios Git locales. No se ha comprobado recepción real ni se promete exactamente una entrega. La serialización coordina estos workflows, no un despliegue externo ajeno a ellos o una cancelación manual del administrador.

## Watchdog: procesos y ediciones son relojes distintos

V7 y el parte mantienen su límite técnico de 3 h. La antigüedad de una edición periodística superior a 36 h produce una advertencia editorial, no prueba un fallo de ejecución.

El generador registra journal-check.json solo cuando realmente se ejecuta, con resultado published, edition_already_exists o not_due. Una ejecución omitida por idempotencia no cambia fechas, texto ni fuentes de la edición existente. El constructor publica únicamente los campos mínimos de ese control en XML; el JSON interno queda excluido.

El watchdog distingue control reciente, control ausente/desconocido y control antiguo o inválido (36 h). Un control antiguo sí es un problema técnico; una fecha de edición reciente no lo oculta. La ausencia de control en versiones anteriores se declara desconocida, sin inventar una ejecución a partir de la fecha de la edición. No haber publicado una edición nueva no se interpreta por sí solo como falta de actualización del monitor.

## Seguridad: estado exacto

| Medida | Estado |
|---|---|
| Allowlist de archivos públicos, exclusión de JSON/Python/workflows, bloqueo de symlinks y ocultos no autorizados | Implementada en el candidato; pendiente de publicar |
| TAR de Pages contrastado por nombres/bytes y security.txt autorizado | Implementado en CI; no es todavía un nuevo despliegue |
| Actions oficiales fijadas a SHA y controles de trazabilidad | Implementados en el candidato |
| Avisos tras prueba HTTP y guardia del HEAD remoto | Implementados y probados con simulación; envío real desactivado |
| Watchdog separado del actualizador dentro de GitHub | Implementado en la rama; pendiente de publicar/configurar recepción |
| Watchdog en segundo proveedor | Propuesta; no instalado |
| Desarrollo en repositorio privado y publicación mínima separada | Prototipo local con hashes; separación real NO realizada. El repositorio actual sigue público |
| CSP, nosniff y otras cabeceras mediante proxy compatible | Propuesta; sin cambios de DNS/hosting ni cabeceras activadas |
| Ausencia absoluta de secretos o vulnerabilidades | No certificada; el escaneo previo solo cubre patrones y referencias especificados |
| AdSense, CMP y nuevas captaciones | Desactivados/no instalados; requieren verificaciones y autorización separadas |

## Publicación y reversión

Antes de autorizar se comprueba el HEAD remoto inmediato, los cuatro checks del SHA exacto, el artefacto descargado y los recursos sellados. Una fusión autorizada en main dispararía el despliegue existente. El SHA construido tras la fusión puede diferir del head de la PR: los controles remotos deben compararse con el primero.

La copia de reversión debe corresponder al último despliegue exitoso que incluya la edición del 19/11, no al antiguo main 08429e73. Se conserva localmente con SHA256 antes de cualquier publicación. Una reversión solo visual conserva P0/P1; una reversión integral requiere autorización y recuperaría también los defectos conocidos del artefacto previo. Los datos e históricos nuevos nunca se restauran desde un commit viejo ni se fuerza main.
