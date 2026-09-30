# Contrato de voz — Fase 2B

Versión del contrato: `2.0.0`
Estado: piloto manual con ElevenLabs, sin publicación.

## 1. Finalidad y límites

La etapa transforma exclusivamente un guion validado de Fase 2A en audio. No decide hechos, estado operativo, importancia ni redacción. El texto enviado al proveedor coincide exactamente con el texto sellado en `voice-package`.

La integración autorizada usa la API de ElevenLabs. Requiere red y consume créditos, pero no clona voces, no publica y no dispone de permisos de escritura en el repositorio. Cualquier fallo de credencial, cuota, red, formato o validación detiene el piloto; no existe fallback silencioso.

## 2. Perfil permitido

`VOICE_RULESET_V2` admite estos parámetros cerrados:

```json
{
  "engine": "elevenlabs",
  "voice": "<voice_id resuelto>",
  "model_id": "eleven_multilingual_v2",
  "output_format": "pcm_24000",
  "sample_rate_hz": 24000,
  "stability": 0.55,
  "similarity_boost": 0.75,
  "style": 0.0,
  "use_speaker_boost": true,
  "deterministic_mode": false,
  "cloning": false,
  "network_required": true,
  "license": "ElevenLabs paid commercial terms"
}
```

El identificador de voz se toma de `ELEVENLABS_VOICE_ID_ES` o `ELEVENLABS_VOICE_ID_EN`. Se incorpora al paquete y a su hash para impedir que una voz cambie sin alterar la identidad del candidato.

La credencial `ELEVENLABS_API_KEY` se lee únicamente en tiempo de ejecución. Nunca forma parte del paquete, manifiesto, vista previa, artefactos ni mensajes de error.

## 3. Síntesis y trazabilidad

La petición se envía a `POST /v1/text-to-speech/:voice_id` con `output_format=pcm_24000`. El cuerpo contiene solo el texto sellado, el modelo y los ajustes de voz autorizados. La respuesta PCM se encapsula localmente como WAV mono de 16 bits a 24 kHz.

El manifiesto registra:

- identificadores y hashes de entrada;
- proveedor, versión de API, modelo, voz y formato;
- hash, tamaño, duración y propiedades técnicas del WAV;
- `network_used: true` y `cloning_used: false`;
- hora UTC de renderizado.

No se serializan cabeceras, credenciales ni el cuerpo de error del proveedor.

## 4. Controles de coste y secretos

El workflow solo admite `workflow_dispatch`, tiene `contents: read` y exige marcar `confirm_paid_synthesis`. Antes de llamar a la API comprueba que existan:

- secreto: `ELEVENLABS_API_KEY`;
- secreto: `ELEVENLABS_VOICE_ID_ES`.

La clave debe restringirse a Text to Speech y tener un límite de créditos en ElevenLabs. Las pruebas unitarias usan un proveedor simulado y no consumen red ni créditos.

## 5. Validación y revisión humana

Los validadores comprueban identidad, texto, orden, trazabilidad, perfil, modelo, voz, formato, duración, señal y hashes. También verifican que la red se declaró y utilizó, que la clonación permanece desactivada y que la publicación sigue bloqueada.

La salida técnica `PASS` no autoriza publicar. Pronunciación, acento, pausas, naturalidad y correspondencia audible completa requieren escucha humana del archivo `audio-elevenlabs.wav`.

## 6. Evolución

Cambiar modelo, voz, parámetros, formato, proveedor, clonación, publicación o ejecución automática exige actualizar contrato y pruebas. Ormuz y Gibraltar deben conservar el mismo núcleo y el mismo contrato.
