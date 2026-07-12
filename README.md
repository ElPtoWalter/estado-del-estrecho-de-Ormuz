# Estado del estrecho de Ormuz

Web estática para GitHub Pages con actualización automática y configuración SEO básica.

## Archivos añadidos para buscadores

- `robots.txt`: permite el rastreo y anuncia el sitemap.
- `sitemap.xml`: indica la URL principal a Google y Bing.
- Etiqueta canónica, título y descripción optimizados en `index.html`.
- Open Graph y Twitter Cards para que el enlace se comparta con una imagen profesional.
- Datos estructurados Schema.org.
- Estado actual escrito también directamente en el HTML, además de `status.json`, para que pueda leerse aunque JavaScript tarde en renderizarse.

## Instalación o actualización

1. Sube **todo el contenido** de esta carpeta a la raíz del repositorio.
2. Al subir por la web de GitHub, comprueba especialmente que existan:
   - `.github/workflows/update-status.yml`
   - `robots.txt`
   - `sitemap.xml`
   - `social-card.png`
3. Sustituye los archivos existentes cuando GitHub lo indique.
4. Ejecuta una vez **Actions → Actualizar estado de Ormuz → Run workflow**.
5. Actualiza la página con `Ctrl + F5` cuando termine.

## Google Search Console

Usa una propiedad de prefijo de URL con esta dirección exacta:

`https://elptowalter.github.io/estado-del-estrecho-de-Ormuz/`

Después:

1. Verifica la propiedad con el método que indique Google.
2. En **Sitemaps**, envía `sitemap.xml`.
3. En **Inspección de URLs**, pega la página principal y solicita su indexación.

## Funcionamiento

- `update_status.py` consulta GDELT y Google News RSS.
- Solo acepta señales explícitas procedentes de fuentes seleccionadas.
- Actualiza `status.json` y la copia visible en `index.html`.
- Ante falta de pruebas o contradicciones muestra `INCIERTO`.
- Si fallan temporalmente todas las conexiones, conserva el último estado publicado.

## Forzar un estado manualmente

En `config.json`, cambia:

```json
"manual_override": null
```

por `"ABIERTO"`, `"CERRADO"` o `"INCIERTO"`. Para recuperar la automatización, vuelve a poner `null`.

## Advertencia

Es un indicador automatizado basado en noticias, no una fuente oficial de navegación marítima ni una garantía en tiempo real.
