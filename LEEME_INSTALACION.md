# Estrecho Ormuz — actualización V4 seria

## Qué contiene
- Nueva portada ES/EN orientada a credibilidad, SEO y futura monetización.
- Panel de verificación conectado a `status.json`.
- Historial, metodología, importancia, alertas, fuentes y páginas de confianza ES/EN.
- Política editorial, publicidad/patrocinios, privacidad, cookies, aviso legal y contacto.
- Dominio canónico corregido a `https://estrechoormuz.com/`.
- `robots.txt`, `sitemap.xml`, manifest, favicon, tarjeta social y `llms.txt`.
- JavaScript sin frameworks compatible con el esquema actual de `status.json` y `history.json`.

## Instalación en GitHub
1. Haz una copia/descarga del repositorio actual.
2. En el repositorio `estado-del-estrecho-de-Ormuz`, abre **Add file → Upload files**.
3. Arrastra el contenido de esta carpeta (no la carpeta exterior).
4. Acepta reemplazar los archivos con el mismo nombre y confirma el commit.
5. Espera a que termine GitHub Pages y el workflow automático.
6. Comprueba `/`, `/en.html`, `/status.json`, `/historial.html` y `/sitemap.xml`.

## Archivos que NO se incluyen deliberadamente
No se incluyen `status.json`, `history.json`, `feed.xml`, scripts Python ni workflows. Así no se sobrescribe el estado vivo ni el motor automático.

## Antes de monetizar
1. Configura Cloudflare Email Routing para `contacto@estrechoormuz.com`.
2. Completa el aviso legal con los datos identificativos/fiscales del titular antes de activar anuncios o patrocinios remunerados.
3. Cuando tengas un identificador de AdSense, crea `ads.txt`; no se ha inventado ninguno.
4. Si activas publicidad o analítica no esencial en el EEE, instala una CMP y actualiza privacidad/cookies.
5. Registra la propiedad de dominio en Google Search Console y envía `/sitemap.xml`.

## Compatibilidad con el motor
Se conservan los marcadores `STATUS_SNAPSHOT_START/END` y `HISTORY_SNAPSHOT_START/END`, además de los IDs usados por el frontend. El CSS conserva las clases históricas para que las instantáneas generadas por el updater sigan renderizando.
