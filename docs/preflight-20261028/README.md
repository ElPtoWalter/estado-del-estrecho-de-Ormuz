# Evidencias de indexación — 28/10/2026

- `sitemap-audit.json`: capas fuente/construida/HTTP, metadatos de seis artículos y revisión de las 36 ediciones incluidas en el fuente. No contiene exportaciones privadas de Search Console.
- `diary-audit.csv`: una fila por edición. Fechas schema se convierten a Europe/Madrid; sus flags son ayudas de revisión, sin cambiar indexación o calificar automáticamente valor editorial.
- `url-inspection-template.csv`: plantilla vacía de datos de cuenta para las seis investigaciones. Copiar fuera del repositorio antes de completar Page Indexing/Inspection y referencias de evidencia privada. No interpretar vacíos como resultados positivos o negativos.
- `page-indexing-owner-snapshot.json`: resumen agregado de la captura del titular del 28/10/2026, según la revisión de GitHub enlazada: 61 indexadas, 62 sin indexar y seis motivos que suman 62. Sin captura, identificadores o exportación privada; no se ha consultado API independiente. No es estado vivo ni un veredicto sobre las seis investigaciones o las 62 URL del sitemap.

Reproducción offline desde la construcción correspondiente:

```text
python indexation_audit.py --root . --public-root _site --http PRIVATE/http-observations.json --output PRIVATE/repeated-audit
```

El archivo de observaciones contiene respuestas GET públicas con fecha, estado, cabeceras y cuerpo; se conserva fuera del sitio. Sin `--http`, la capa desplegada y sus resultados son desconocidos: no se sustituyen por la construcción local. El script no usa credenciales, red, correo o APIs de envío. No modifica los sitemaps, HTML o políticas editoriales.

La plantilla existente no se sobrescribe al regenerar la evidencia. Los valores nuevos de cuenta deben mantenerse privados hasta que se acuerde expresamente qué resumen puede publicarse. Las cifras históricas del conector no constituyen un recuento de indexación actual; la nueva instantánea global tampoco determina el estado individual de los artículos. El resumen fechado se valida por sus sumas, sin fijar sus recuentos como constantes del código.
