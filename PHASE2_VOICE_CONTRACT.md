# Contrato de voz — Fase 2B

Versión del contrato: `1.0.0`
Estado: piloto local, sin publicación.

## 1. Finalidad y límites

La etapa de voz transforma exclusivamente un guion de Fase 2A ya validado en audio. No decide hechos, estado operativo, importancia, recomendación audiovisual ni redacción. No consulta Internet, no altera el texto, no clona voces, no usa un proveedor de pago y no publica.

La entrada obligatoria es la pareja exacta `video-package` + `script`. Si cualquiera falla su validador de Fase 2A, no se construye el paquete de voz.

## 2. Sobre normativo del paquete

```json
{
  "schema_version": "1.0.0",
  "voice_package_id": "voice-package:<site>:<language>:<content_hash>",
  "video_package_id": "video-package:...",
  "video_content_hash": "sha256",
  "script_id": "video-script:...",
  "script_schema_version": "1.0.0",
  "site": "ormuz|gibraltar",
  "language": "es|en",
  "video_type": "breaking|explainer|daily_summary",
  "generated_at": "UTC ISO 8601",
  "voice_profile": {
    "engine": "espeak-ng",
    "voice": "es|en-gb",
    "speed_wpm": 150,
    "pitch": 50,
    "word_gap_ms": 0,
    "amplitude": 100,
    "deterministic_mode": true,
    "cloning": false,
    "network_required": false,
    "license": "GPL-3.0-or-later"
  },
  "narration": {
    "text": "texto exacto enviado al sintetizador",
    "text_sha256": "sha256",
    "segments": []
  },
  "audio_constraints": {
    "format": "wav",
    "channels": 1,
    "sample_width_bits": 16,
    "min_sample_rate_hz": 16000,
    "max_sample_rate_hz": 48000,
    "minimum_duration_seconds": 20,
    "maximum_duration_seconds": 150
  },
  "human_review_required": true,
  "publication_allowed": false,
  "content_hash": "sha256"
}
```

Cada segmento conserva su `segment_id`, texto, hash y referencias `fact_ids`, `statement_ids` y `source_ids`. El orden es `hook` → escenas → `outro`. Cambiar, reordenar, añadir u omitir texto invalida el paquete.

`content_hash` se calcula sobre JSON canónico UTF-8, con claves ordenadas, excluyendo solo los campos derivados `content_hash` y `voice_package_id`. El identificador se construye después a partir de ese hash.

## 3. Síntesis y manifiesto

`VOICE_RULESET_V1` admite únicamente eSpeak NG local con argumentos fijos. El texto se entrega por entrada estándar y la salida es WAV PCM mono de 16 bits. No existe fallback silencioso: si el ejecutable no está disponible o falla, el piloto falla explícitamente.

El manifiesto registra motor, versión exacta del motor, voz, identificadores de entrada, hash del texto, hash y tamaño del WAV, duración, frecuencia, canales, profundidad, hora de renderizado y los invariantes `network_used: false` y `cloning_used: false`.

## 4. Validación y revisión humana

El validador comprueba:

- identidad y hashes de todos los eslabones;
- texto y orden exactos del guion;
- trazabilidad de cada escena;
- perfil local permitido;
- formato, canales, profundidad, frecuencia y duración;
- existencia, tamaño, hash e información técnica del WAV;
- presencia de señal no nula;
- ausencia de red, clonación y permiso de publicación.

Estas comprobaciones no demuestran por sí solas que cada palabra se oiga correctamente. Pronunciación, ritmo, naturalidad y correspondencia audible completa exigen escucha humana. La aprobación humana sigue siendo obligatoria incluso cuando ambos validadores devuelven `PASS`.

## 5. Evolución

Los cambios compatibles aumentan versión menor y añaden campos opcionales. Relajar la revisión humana, permitir publicación, red, clonación o proveedores distintos exige contrato mayor, autorización separada y nuevas pruebas. Ormuz y Gibraltar deben conservar el mismo contrato y el mismo núcleo.
