# Fase 2B · Voz

## Resultado implementado

La Fase 2B incorpora una síntesis local reproducible sobre la salida validada de Fase 2A:

`video-package` validado → guion validado → `voice-package` → eSpeak NG local → WAV + manifiesto → validación técnica → escucha humana.

No se modifica la Fase 1 ni la decisión audiovisual. La voz no recibe artículos, claves, acceso a Internet ni capacidad editorial.

## Piloto seguro

El workflow `Piloto manual · Fase 2B Voz` solo puede iniciarse manualmente. Usa permisos `contents: read`, instala eSpeak NG desde los repositorios de Ubuntu, ejecuta las pruebas y guarda durante 14 días exactamente ocho artefactos temporales. No hace commit, despliegue ni publicación.

El piloto selecciona un candidato real actual de Fase 2A o, si no existe, una fixture histórica real claramente etiquetada. Genera el guion local determinista, no llama a Gemini ni a OpenRouter y no necesita secretos.

## Criterio de salida

Un piloto técnico es verde cuando:

1. paquete de vídeo y guion pasan los validadores de Fase 2A;
2. el paquete de voz pasa su contrato;
3. eSpeak NG genera un WAV no vacío y con señal;
4. hash, formato, duración y enlaces del manifiesto pasan;
5. los únicos artefactos son los ocho permitidos.

Todavía queda una acción humana no automatizable: escuchar `audio-local.wav` y decidir si pronunciación, pausas y ritmo son aceptables. `PASS` técnico no equivale a autorización de publicación.
