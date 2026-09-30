# Fase 2A — Video Intelligence

Estado: infraestructura interna terminada para piloto. No publica ni produce vídeo.

## Alcance

Fase 2A convierte artefactos ya validados de Fase 1 en una recomendación audiovisual reproducible, un paquete factual cerrado y un guion trazable. No recalcula la actualidad ni el estado operativo. Tampoco descarga imágenes, genera voz o vídeo, monta piezas, modifica la web pública ni llama a redes sociales.

La cadena implementada es:

```text
eventos + estado + health + comparación de Fase 1
  -> VIDEO_RULESET_V1
  -> video-package 2.0.0
  -> Gemini gratuito / OpenRouter gratuito / reglas locales
  -> validador factual local
  -> preview y artefactos temporales
  -> revisión humana obligatoria
```

## Componentes

- `phase2_video/schema.py`: versiones, enumeraciones, serialización canónica, hashes y adaptador de estados de verificación.
- `phase2_video/rules.py`: decisión determinista y códigos de motivo.
- `phase2_video/package.py`: adaptadores de Ormuz y Gibraltar y construcción del paquete cerrado.
- `phase2_video/script.py`: guion por escenas, Gemini, OpenRouter gratuito y fallback local.
- `phase2_video/validator.py`: validación estructural, factual, semántica y de seguridad.
- `video-rules.json`: umbrales, duración, frescura, visuales permitidos y bloqueos.
- `pilot_phase2a_video.py`: piloto aislado, sin publicación.
- `.github/workflows/pilot-phase2a-video.yml`: ejecución exclusivamente manual.

El núcleo y sus pruebas comunes deben conservarse byte a byte iguales en los dos repositorios. Solo cambian la selección de datos históricos del piloto y el nombre del sitio en su workflow.

## Contratos y versiones

- paquete: `2.0.0`;
- guion: `1.0.0`;
- reglas: `VIDEO_RULESET_V1`;
- validador: `1.0.0`.

Durante la implementación se detectó una circularidad en el contrato 1.0.0: `package_id` contenía `content_hash`, pero el hash incluía a su vez `package_id`. La versión mayor 2.0.0, aprobada expresamente, calcula SHA-256 sobre el JSON canónico excluyendo los dos campos derivados, `content_hash` y `package_id`; después construye el identificador con el hash resultante. El resto de garantías editoriales permanece intacto.

El esquema del guion conserva `package_id`, `package_content_hash`, tipo, idioma, duración, proveedor y escenas. Cada escena incluye voz, texto en pantalla, intención visual y referencias a hechos, declaraciones y fuentes.

## Adaptación desde Fase 1

El mapping está centralizado y probado:

| Fase 1 | Fase 2A | Efecto |
|---|---|---|
| `CONFIRMED_PRIMARY` | `VERIFIED_PRIMARY` | Puede entrar en `verified_facts`. |
| `CONFIRMED_MULTI_SOURCE` | `VERIFIED_MULTISOURCE` | Puede entrar en `verified_facts`. |
| `DECLARATION_ONLY` | sin hecho verificado | Se conserva solo como declaración atribuida. |
| `SINGLE_SOURCE` | sin hecho verificado | Bloquea la recomendación automática. |
| `UNCONFIRMED` | sin hecho verificado | Bloquea la recomendación automática. |
| `CONFLICTING` | sin hecho verificado | Bloquea por conflicto no resuelto. |

Ormuz consume `events.json`, `operational-intelligence.json`, `health.json` y `daily-brief.json`. Gibraltar consume `events.json`, `observatory.json`, `health.json` y `since_yesterday` dentro del observatorio. Ningún adaptador vuelve a inferir estado o confianza.

## Decisión audiovisual

Los umbrales iniciales están versionados en `video-rules.json`:

- 0–54: no hay vídeo;
- 55–64: solo `daily_summary`, con material diario verificado;
- 65–84: `explainer`;
- 85–100: candidato `breaking`, si además es nuevo y material, tiene impacto operativo o información excepcional, verificación suficiente, salud aceptable y trazabilidad completa.

La puntuación nunca basta por sí sola. Son bloqueos duros la evidencia insuficiente, las declaraciones sin hechos, fuente única, evento no confirmado o conflictivo, fuentes o contexto obsoletos, ausencia de cambio material, duplicidad, antigüedad presentada como novedad, referencias incompletas, fechas futuras, paquete inválido o hash incorrecto.

La salida incluye códigos estables como `PRIMARY_VERIFICATION`, `MULTISOURCE_VERIFICATION`, `MATERIAL_OPERATIONAL_CHANGE`, `HIGH_IMPORTANCE`, `DAILY_MATERIAL_UPDATE`, `BELOW_VIDEO_THRESHOLD` o `UNRESOLVED_CONFLICT`. `human_review_required` es siempre `true`.

## Paquete factual

`build_video_package` selecciona únicamente eventos elegibles, separa hechos y declaraciones, conserva IDs y tiempos, limita cada hecho a titulares o resúmenes de Fase 1 y no incorpora cuerpos de artículos. Las fuentes usadas por un hecho deben proceder de evidencia factual, avisos oficiales o señales operativas; una fuente usada solo por una declaración no refuerza el hecho.

`visual_assets` queda vacío en Fase 2A. Esto significa que todavía no se han seleccionado activos; no concede derechos sobre imágenes de Internet.

El mismo input, fecha de generación incluida, produce la misma decisión, JSON canónico, hash e identificador. Una corrección produce otro hash. Un consumidor debe rechazar duplicados.

## Generación del guion y fallback

Gemini recibe exclusivamente el paquete cerrado y una plantilla estructural local. La clave se envía en cabecera, nunca en la URL. Solo se admiten modelos Gemini expresamente permitidos. El modelo no puede cambiar el tipo, la importancia, el estado, la confianza, el hash o la decisión.

El orden de ejecución es:

1. Gemini, si existe `GEMINI_API_KEY`;
2. OpenRouter, solo con `openrouter/free` o un modelo terminado en `:free`, si ya existe `OPENROUTER_API_KEY`;
3. reglas locales deterministas.

Errores 429, timeouts, JSON inválido o un guion remoto rechazado activan el siguiente fallback. No existe dependencia de pago ni activación de facturación. El guion local usa etiquetas legibles para estado y confianza, conserva la incertidumbre y respeta los intervalos de palabras configurados.

## Validación

El validador vuelve a comprobar paquete y guion sin usar otro modelo. Rechaza, entre otros casos:

- esquema, versión, identidad, hash o referencias inválidas;
- números, fechas, URLs, personas, organismos o lugares nuevos;
- HTML, prompt injection o instrucciones de sistema;
- lenguaje sensacionalista no respaldado;
- una declaración convertida en hecho;
- cambio de estado operativo o confianza;
- contradicciones locales conocidas y certeza añadida sobre una incógnita;
- escenas sin trazabilidad o fuentes no asociadas;
- duración fuera del intervalo.

Las fuentes se tratan siempre como datos no confiables. Un titular que intente dar instrucciones invalida la recomendación factual; nunca se ejecuta ni se copia como prompt operativo.

## Observabilidad y seguridad

Paquete, guion y validaciones conservan versión de reglas, esquemas y validador, `package_id`, hash, evento, fuentes, hechos, declaraciones, proveedor, fallback, estado, errores y tiempo de generación. Los artefactos se auditan antes de escribirse para impedir que incluyan claves o patrones de secreto.

El workflow tiene permisos `contents: read`, se inicia solo con `workflow_dispatch`, no contiene pasos de commit, push, despliegue o publicación y escribe en el directorio temporal del runner. El piloto produce exactamente:

- `video-package.json`;
- `script-local.json`;
- `script-gemini.json`;
- `validation-local.json`;
- `validation-gemini.json`;
- `preview.md`.

La preview identifica claramente una fixture histórica, compara local y remoto, muestra proveedor, duración, escenas, respaldo, incógnitas, información nueva detectada y resultado del validador. Siempre declara `Publicación: NO` y revisión humana obligatoria.

## Ejecución local

Debe elegirse un directorio de salida fuera del repositorio:

```bash
python -m unittest -v test_video_rules.py test_video_package.py test_video_script.py test_video_validator.py test_phase2a_pilot.py
python pilot_phase2a_video.py --site ormuz --output-dir /ruta/temporal/phase2a-video
python pilot_phase2a_video.py --site gibraltar --output-dir /ruta/temporal/phase2a-video
```

Cada repositorio ejecuta únicamente su sitio. Si no hay un evento actual elegible, el piloto selecciona una fixture basada en un evento real del archivo y la marca `historical_fixture = true`; nunca la presenta como actualidad.

## Límites y siguiente fase

Fase 2A termina en guiones validados y artefactos temporales. No añade menús, reproductores, feeds, SEO o contenido a producción. No integra voz, clonación, avatares, mapas renderizados, generación de vídeo, FFmpeg productivo ni redes sociales.

La siguiente subfase es Fase 2B — Voz. Requiere una autorización separada y deberá mantener paquete cerrado, validación factual, revisión humana, control de derechos y límites explícitos de coste. Nada de Fase 2A autoriza a comenzar esa subfase.
