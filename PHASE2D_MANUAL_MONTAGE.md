# Integración manual del montaje — Fase 2D, contrato 1.0.0

Esta capa integra los pilotos internos de Ormuz y Gibraltar. No cambia Fase 2A,
los jobs/metadatos de voz 2B ni el storyboard 2C. Mantiene todos sus validadores
y sus objetivos temporales. El montaje ajusta solo su propia línea temporal
a la duración real del WAV, sin cortar, acelerar o volver a sintetizar voz.

## Alcance autorizado

El usuario aprobó los pilotos y autorizó un proceso manual repetible en ambos
proyectos. Prefirió aplazar el pulido visual y la sincronización fina.
No hay autorización de merge, publicación, distribución social, avatar,
generación recurrente o activación de facturación.

Código y pruebas comunes idénticos en ambos repositorios:
`phase2_montage.py`, `test_phase2d_montage.py`, `requirements-montage.txt`.
Solo cambian los valores de sitio, run y artefacto en los workflows.

## Entrada explícita, sin proveedor

Se consume una carpeta con cinco archivos 2B existentes:
`video-package.json`, `script.json`, `voice-input.json`,
`audio-metadata.json`, `audio-gemini.wav`.
Se exige el SHA256 esperado del WAV como confirmación independiente.
No se buscan noticias nuevas ni se selecciona otra pieza automáticamente.

Se revalidan contrato factual 2A, job/configuración 2B, métricas, hashes y estado
PENDING/NOT_RUN. Solo voz castellana es-es-advisor-2 y perfiles v2 o audición
original. La audición aprobada conserva su perfil experimental; no se reetiqueta.

Sin audio o ante corrupción, identidad mezclada, configuración no admitida,
hash incorrecto o herramientas ausentes: FAIL cerrado. Nunca genera ni regenera
voz, nunca pide una clave Gemini/ElevenLabs y nunca cambia a otro proveedor.

## Montaje y salida

Ejecución manual en Linux/GitHub Actions con FFmpeg, ffprobe, librsvg y Pillow.
Las bibliotecas/herramientas se instalan al preparar el runner; el motor de
montaje no usa red ni descarga medios o fuentes. Usa tipografía ya instalada
en el sistema, rasterizada; no distribuye el archivo de fuente.

Formato: MP4 H.264/AAC, 1080×1920, 30 fps. Copia AAC con pérdida para entrega;
máster PCM original preservado byte a byte en `source/`. No efectos ni cambios
de velocidad. Duración mínima que cubra el WAV, con redondeo menor a un fotograma.

La salida aislada, fuera del checkout y sin sobrescribir contenido previo,
incluye MP4, SRT, storyboard y manifiesto originales 2C, composición con identidad
sellada, fuentes de entrada intactas, SVG/PNG derivados, QA visual del MP4,
ffprobe, validación, manifiesto de hashes y preview Markdown.

La caché de vídeo se acepta solo con el plan esperado idéntico, hashes íntegros,
contratos 2C válidos y comprobación de pista de audio/fotogramas. Ante fallo no
se sobrescribe ni se llama a TTS. El audio fuente se comprueba otra vez al final.

## Límites editoriales

Siempre `historical_fixture: true`, fecha UTC visible de la instantánea,
`allowed_uses: [internal_preview]`, `publication_allowed: false`,
`human_review_required: true`, `human_review_status: PENDING`,
`transcript_validation: NOT_RUN`. No representa noticias actuales.

Los subtítulos contienen exactamente el texto editorial, con referencias
por segmento y escena. Su sincronización es estimada por proporción y pausas,
no ASR ni alineación palabra a palabra. Debe revisarse antes de publicar.
Los esquemas no son cartografía ni aptos para navegación. No se incorporan
hechos nuevos y la incertidumbre no se presenta como hecho confirmado.

PASS técnico no equivale a revisión artística, aprobación de transcripción
o autorización de publicar. No se alteran los metadatos de aprobaciones antiguas.

## Ejecución

```bash
python -m pip install -r requirements-montage.txt
python -m unittest -v test_phase2d_montage.py
python phase2_montage.py --site ormuz --input-dir /tmp/voz-existente --output-dir /tmp/preview-nueva --expected-audio-sha256 HASH_REAL_DEL_WAV
```

Para Gibraltar, cambiar únicamente `--site gibraltar` y las carpetas/hash de
su propia pieza. Se necesitan FFmpeg, ffprobe, rsvg-convert y una fuente Sans
compatible del sistema. Windows local continúa bloqueado por el sandbox en la
sesión de trabajo actual; no se declara probada allí esta integración.

## Workflows y borradores

`pilot-phase2d-montage.yml` solo tiene workflow_dispatch. Inputs explícitos:
run de voz existente del mismo repo, nombre exacto del artefacto y SHA256 del WAV.
Token mínimo contents:read/actions:read, sin secretos TTS, sin schedule,
sin commit/push/deploy, sin publicar. Entrega artefactos internos durante 14 días.

`phase2d-montage-ci.yml` es una comprobación de PR, no una redacción automática:
ejecuta regresiones sin API, pruebas de caché con tono sintético (no voz humana)
y montaje de un WAV ya existente para probar la integración. No llama a TTS.

Los workflows nuevos quedan propuestos en una rama dependiente de los PR de
voz, todavía en borrador. El botón manual en main requiere que sus dependencias
y esta integración se revisen y fusionen: no se fusiona nada automáticamente.

Audios de comprobación, sin síntesis nueva:
- Ormuz: run 36980491324, artefacto phase2b-gemini-ormuz-5,
  WAV `0f65d86951e4f855ad5f2a032fa2d582268b9bf18d7be5b5a34356892cf6d259`.
- Gibraltar: run 36934873991, artefacto castilian-audition-4,
  WAV `31edeb5ec69fe81b7851906bfdc7a37c6cf304e2015fd578fdd582f20a7cca4c`.

Estos artefactos expiran el 16 y el 15 de octubre de 2026 respectivamente.
Los másteres locales anteriores no se borran. Si un artefacto remoto caduca,
hay que proporcionar otra copia íntegra existente; no se regenera voz como fallback.

Herramientas: [Pillow](https://pypi.org/project/pillow/),
[FFmpeg](https://ffmpeg.org/), [librsvg](https://gitlab.gnome.org/GNOME/librsvg),
[artefactos de Actions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).
