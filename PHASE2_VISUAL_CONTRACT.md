# Contrato visual — Fase 2C

Versión: `1.0.0`

Estado: piloto manual de storyboard y gráficos originales. No produce ni publica vídeo.

## 1. Entrada autorizada

La Fase 2C consume exclusivamente un `video-package` válido de Fase 2A y un guion estructurado que haya superado el validador factual local. No consulta Internet, no reabre la selección editorial, no recalcula el estado operativo y no añade hechos.

La identidad completa de ambos artefactos —`package_id`, `content_hash` y `script_id`— queda incorporada al storyboard. Cualquier cambio anterior obliga a generar una identidad visual nueva.

## 2. Salida

El piloto produce:

- un storyboard sellado y determinista;
- una línea de tiempo completa en formato vertical `9:16`, `1080×1920`, `30 fps`;
- un SVG original por escena;
- un manifiesto con hashes, tamaño, dimensiones, trazabilidad y derechos;
- una validación cerrada y una preview legible.

No produce voz, avatar, fotografía, metraje, animación, montaje, vídeo final ni publicación.

## 3. Trazabilidad

Cada escena visual conserva el `scene_id` del guion y sus `fact_ids`, `statement_ids` y `source_ids`. Las referencias deben coincidir exactamente; no se aceptan referencias añadidas, eliminadas o reordenadas. La línea de tiempo empieza en cero, no tiene huecos ni solapes y termina exactamente en la duración objetivo del guion.

El texto visible procede del `on_screen_text` ya validado o de etiquetas editoriales locales cerradas. Las tarjetas de estado consumen el estado y la confianza del paquete; no los infieren.

## 4. Resolución segura de intenciones

Las intenciones de Fase 2A se convierten de forma determinista:

| Intención | Plantilla local |
|---|---|
| `presenter` | `status-card`; nunca se crea una persona o avatar. |
| `map` | `schematic-map`, rotulado como no apto para navegación. |
| `chart` | `metric-card` solo si el texto validado contiene cifras; en otro caso `text-card`. |
| `timeline` | `timeline`. |
| `source-card` | `source-card`. |
| `status-card` | `status-card`. |
| `text-card` | `text-card`. |

No existe fallback generativo ni selección autónoma de recursos.

## 5. Derechos

`VISUAL_RULESET_V1` permite únicamente `generated_original_only`. Todos los SVG se crean con código local del proyecto, sin imágenes, fuentes, mapas o bibliotecas remotas. El manifiesto declara:

- `rights_status: cleared`;
- crédito `StraitWatch · gráfico original generado localmente`;
- `allowed_uses: [internal_preview]`;
- `network_used: false`;
- `external_assets_used: false`.

La validación rechaza archivos ausentes o modificados, hashes incorrectos, rutas que salgan del artefacto, elementos SVG capaces de cargar contenido externo y cualquier ampliación de usos.

## 6. Seguridad editorial

La revisión humana es obligatoria y `publication_allowed` permanece en `false` en storyboard y manifiesto. Un `PASS` confirma integridad técnica y trazabilidad, no exactitud cartográfica, calidad audiovisual ni autorización de publicación.

Los mapas son esquemas editoriales, no cartografía y nunca pueden utilizarse para navegación. No se representa como real ningún suceso mediante metraje recreado.

## 7. Coste y red

La fase utiliza solo Python estándar, no requiere secretos, no activa facturación y no llama a servicios externos. El workflow es manual, tiene `contents: read` y guarda únicamente artefactos temporales durante catorce días.

## 8. Evolución

Cambiar formatos, derechos, plantillas, resolución de intenciones o permitir activos externos exige una nueva versión del contrato y pruebas de regresión. Incorporar voz, avatar, montaje, publicación o servicios comerciales requiere autorización separada.
