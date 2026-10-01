# StraitWatch · Fase 2B Gemini Voice

Contrato de arquitectura **3.0.0**. Artefactos `voice-input` y metadatos **1.0.0**.
Sustituye el contrato experimental 2.0.0, nunca integrado, ligado a ElevenLabs.
No modifica Fase 1, Fase 2A, Fase 2C existente, decisiones operativas, datos públicos
ni páginas web. No produce vídeo ni publica audio. Revisión humana obligatoria.

## Auditoría inicial · 1 octubre 2026

- Los dos repositorios disponen del secreto `GEMINI_API_KEY`. No se conoce ni
  descarga su valor desde GitHub. No existen variables TTS configuradas inicialmente.
- `main` de Ormuz: `14fefea665ff02a88f41b337494abd69f4f91ee2`.
- `main` de Gibraltar: `6a3c8cc8605c821eb0da260f2f5dd7ba7729b26b`.
- Paquete 2A 2.0.0, guion 1.0.0 y validadores 1.0.0 son compatibles. Se ejecutan
  de nuevo localmente; no se acepta un campo PASS proporcionado por el cliente.
- Los PR antiguos Ormuz #12 / Gibraltar #16 (`phase2b-voice`) son borradores sin
  integrar. Sus pilotos anteriores no obtuvieron voz remota (errores de acceso y
  facturación). Se retiran de esta arquitectura, sin borrar secretos o trabajo.
- Configuración TTS independiente de `GEMINI_MODEL`, que pertenece al editor.

## Proveedor, modelo y política de coste

Proveedor único remoto: Gemini. REST Interactions API, una petición síncrona,
`store=false`, clave solo en cabecera, sin herramientas ni redirecciones.

| Variable | Valor por defecto | Validación |
| --- | --- | --- |
| `GEMINI_API_KEY` | secreto existente | obligatorio para síntesis, nunca en artefactos |
| `GEMINI_TTS_MODEL` | `gemini-3.8-flash-tts` | solo este y `gemini-3.8-flash-lite-tts` |
| `GEMINI_TTS_VOICE_ES` | `Charon` | catálogo cerrado de voces predefinidas |
| `GEMINI_TTS_VOICE_EN` | `Charon` | misma lista; estructura EN, no audicionada |

Modelo seleccionado explícitamente por calidad. Google documenta nivel gratuito
para ambos modelos, verificado el 1 octubre 2026. La clave no permite demostrar
el nivel de facturación de la cuenta: **no se afirma coste real cero sin evidencia**.
Este sistema no activa billing, no pide tarjetas, no crea recursos comerciales y
no migra a un modelo de pago ni reintenta automáticamente. Si la cuenta ya tiene
billing, su tarifa configurada puede aplicarse: revisar AI Studio antes de uso
recurrente. El piloto es manual y acotado a una petición por job, 6000 caracteres,
120 s de timeout, 30 MiB de respuesta máxima y 20 MiB de WAV. No hay SDK extra.

Modelos antiguos 2.5 TTS no se reutilizan: la documentación actual recomienda
3.8 y restringe 2.5 para proyectos nuevos. Cambiar de modelo exige configuración
explícita, dentro de la whitelist, y cambia la identidad del job.

Fuentes oficiales consultadas:

- [TTS y formato de petición](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Modelo 3.8 Flash TTS](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts)
- [Precios y free tier](https://ai.google.dev/gemini-api/docs/pricing)
- [Deprecaciones](https://ai.google.dev/gemini-api/docs/deprecations)
- [Retención y store=false](https://ai.google.dev/gemini-api/docs/interactions-overview)

## Voz editorial común

`straitwatch_es_v1`: intención de voz adulta masculina, español peninsular,
profesional, neutral, sobria, natural, autoridad moderada y ritmo controlado.
Se utiliza Charon predefinida, descrita por Google como informativa. La identidad
percibida, el acento y la calidad requieren escucha: **no se garantiza que el
prompt consiga todos los atributos**. No se diseña, clona ni imita a una persona.
Ormuz y Gibraltar comparten exactamente configuración, módulos y pruebas.

Las instrucciones están en `speech_metadata.style`, NO en el texto pronunciado.
Se especifica un ritmo orientativo según palabras y objetivo, sin cortar,
reescribir ni acelerar el audio después. Si el resultado supera ±20% del
objetivo, se conserva como candidato rechazado `DURATION_MISMATCH`.

## Entrada inmutable y pronunciación

`voice-input.json` contiene identidad del paquete, hash del paquete, identidad y
hash completo del guion, idioma, tipo, objetivo, configuración y su hash,
versión/hash del diccionario, segmentos y texto completo. Orden: hook, voz de
cada escena, outro. Cada segmento conserva `scene_id`, hechos, declaraciones y
fuentes; hook/outro heredan la unión de referencias del guion, no inventan hechos.
No se pronuncian los identificadores, URLs o instrucciones. Si están en el texto
editorial se rechaza la entrada; no se silencian cambiando el original.

`voice-pronunciation.json` inicia sin sustituciones: ningún deletreo fonético
experimental se da por probado. Contiene todos los términos solicitados para
revisión. Overrides futuros requieren idioma, término, texto hablado,
`human_reviewed=true` y nota. Solo modifican `text_for_tts`; el texto editorial
original sigue intacto, con registro de cada sustitución, sin cascadas. No se
admiten números ni markup de proveedor en overrides. La aprobación debe venir
de una escucha humana, no de un PASS técnico.

El hash del job incluye el guion, paquete, configuración, pronunciación y texto
final. Identidad determinista; **bytes de audio no deterministas**. Repetir el
mismo job reutiliza el WAV únicamente tras revalidar entrada, hash, metadatos y
señal. Un caché corrupto o un job fallido no desencadena nuevas llamadas.

## WAV, metadatos y validación

Salida: `voice-input.json`, `audio-gemini.wav`, `audio-metadata.json`,
`validation-report.json`, `preview.md`, más copias de paquete y guion para auditar.
Gemini 3.8 devuelve WAV nativo; se escribe sin envolverlo otra vez. El adaptador
también sabe envolver PCM16 little-endian inequívoco a 24 kHz; otros formatos se
rechazan. Sin MP3 obligatorio, resampling, filtros, normalización o speed-up.

Validaciones: archivo mínimo 48044 bytes, RIFF/WAVE y tamaño íntegro, PCM16 mono,
24/48 kHz, frames completos, duración ±20%, RMS, pico, fracción de silencio,
clipping total y rachas saturadas. Silencio total/casi total y clipping severo
rechazados. Metadatos vinculados a todos los IDs, hashes, modelo, voz, perfil,
idioma, formato, duración y fecha UTC. Campos desconocidos rechazados.

Mapa de segmentos **estructural con tiempos estimados proporcionalmente a
palabras**, no alineación acústica ni ASR. El audio se genera completo en una
petición para minimizar deriva de voz. Validación de transcripción: NOT_RUN.
No se afirma que las cifras y nombres hayan sido pronunciados exactamente:
eso requiere revisión humana o una futura comprobación ASR independiente.

`PASS` significa solo técnicamente válido. `human_review_status=PENDING`,
pronunciación PENDING y publicación DISABLED siempre. Nunca se publica ni se
continúa a vídeo automáticamente.

## Errores y seguridad

400 BAD_REQUEST; 401 AUTHENTICATION_FAILED; 403 ACCESS_DENIED; 404
MODEL_UNAVAILABLE; 429 QUOTA_EXHAUSTED; 500 PROVIDER_ERROR; 503
PROVIDER_UNAVAILABLE; timeout PROVIDER_TIMEOUT; error de red
PROVIDER_NETWORK_ERROR. Respuesta vacía, JSON corrupto, audio ambiguo/corrupto,
redirección o exceso de tamaño fallan cerradamente. Ningún cuerpo o mensaje HTTP,
cabecera, clave, URL con clave o traceback del proveedor sale a logs/artefactos.
Se escanean artefactos textuales antes de escribirlos. Pruebas usan solo mocks;
no consumen cuota. No hay dependencias, variables ni llamadas ElevenLabs.

## Fallback local: decisión explícita

Interfaz `LocalVoiceEngine` implementada; motor físico **aplazado**, no se
presenta como disponible. Gemini fallido NO sustituye silenciosamente la voz.

- [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M): pesos Apache 2.0,
  82 millones de parámetros, soporte multilingüe incluido español, CPU viable
  como candidato. Dependencias Torch/G2P/espeak y pesos de cientos de MB aumentan
  arranque y caché; la calidad y acento es-ES masculino no están aprobados.
- [Piper](https://github.com/OHF-Voice/piper1-gpl): motor GPL-3.0, voces ONNX
  es_ES disponibles, CPU y caché razonables. Cada voz tiene su licencia/model
  card; la licencia del motor no garantiza la de los pesos. Revisión de
  distribución y licencia de la voz concreta pendiente.

Elegir solo tras audicionar una voz y fijar licencia, versión y checksums.
Si se activa, usar un directorio externo y caché persistente; jamás descargar
modelos grandes en cada ejecución o commitear pesos, WAVs o cachés.

## Piloto manual, aislamiento y uso

Workflow `pilot-phase2b-voice.yml`: **solo workflow_dispatch**, contents:read,
sin push, schedule, publicación, permisos de escritura o integración en main.
Artefactos temporales por 14 días, caché por job solo de WAV + metadatos PASS.
Reutiliza la selección real de Fase 2A, incluidos históricos claramente rotulados.
No convierte fixturas históricas en noticias actuales. Genera el guion local
2A validado, sin nueva llamada de IA editorial. También acepta guion 2A existente.

GitHub no permite registrar un workflow nuevo por dispatch hasta que existe en
la rama predeterminada. Para verificar sin merge se usa una rama temporal con
el workflow manual ya registrado `pilot-phase2a-video.yml` que ejecuta este mismo
piloto 2B. Solo cambia esa copia en esa rama temporal; no se modifica el workflow
2A en el PR final ni en main. Ninguna síntesis se activa con push. La rama
temporal se retira después; las ejecuciones y artefactos quedan auditables.

```powershell
python -m unittest -v test_phase2b_voice.py
python pilot_phase2b_voice.py --site ormuz --output-dir C:\ruta\fuera-del-repo\voz --prepare-only
python pilot_phase2b_voice.py --site ormuz --output-dir C:\ruta\fuera-del-repo\voz --package C:\ruta\video-package.json --script C:\ruta\script.json
```

La carpeta debe estar fuera del repositorio. No se sobrescribe otro job ni un
directorio con ficheros ajenos; exclusión local por lock. Reintentar un fallo
requiere una nueva carpeta deliberada; no ocurre automáticamente. Con clave
ausente puede comprobarse preparación y pruebas pero no crear voz ficticia.

## Puerta de salida

Un piloto Gemini PASS en cada estrecho, un WAV audible de cada uno, informes y
PRs sin merge. Después **parar para aprobación auditiva del usuario**. No iniciar
automatización recurrente, publicar o modificar Fase 2C con este encargo.
