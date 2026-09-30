# Fase 2B · Voz con ElevenLabs

## Resultado

La cadena queda así:

`video-package` validado → guion validado → `voice-package` sellado → ElevenLabs → WAV + manifiesto → validación técnica → escucha humana.

ElevenLabs sustituye a eSpeak como sintetizador del piloto. Se usa `eleven_multilingual_v2` en español, salida PCM a 24 kHz y una voz elegida mediante variable de repositorio. No se ha habilitado clonación ni publicación.

## Configuración necesaria en cada repositorio

1. Crear una clave de ElevenLabs restringida a Text to Speech y con límite de créditos.
2. Guardarla como secreto de Actions `ELEVENLABS_API_KEY`.
3. Guardar el identificador de la voz española como secreto de Actions `ELEVENLABS_VOICE_ID_ES`.
4. Abrir `Piloto manual · Fase 2B Voz`, marcar la confirmación de consumo y ejecutar.

La clave no debe guardarse en archivos, variables normales, incidencias, artefactos ni mensajes.

## Seguridad operativa

El workflow es exclusivamente manual y de solo lectura. Las pruebas usan audio PCM simulado y no llaman a ElevenLabs. Solo el paso de piloto recibe el secreto.

Si faltan configuración, créditos, conectividad o una respuesta PCM válida, la ejecución falla sin crear un audio falso. Los artefactos se conservan 14 días y siguen limitados a los ocho archivos aprobados.

## Criterio de salida

Un piloto es técnicamente válido cuando:

1. las entradas de Fase 2A son válidas;
2. el paquete de voz conserva texto, orden y trazabilidad;
3. ElevenLabs devuelve PCM válido;
4. el WAV cumple formato, duración, señal y hashes;
5. ningún secreto aparece en las salidas;
6. los únicos artefactos son los ocho permitidos.

Después debe escucharse `audio-elevenlabs.wav`. El `PASS` técnico no equivale a autorización de publicación.
