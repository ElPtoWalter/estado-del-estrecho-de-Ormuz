# StraitWatch · Aprobación de identidad vocal castellana

Fecha de aprobación: 2 octubre 2026. Evidencia humana: el usuario respondió
«me encanta» después de escuchar la audición regional de Gibraltar. Alcance:
elección de esa voz/acento como identidad común de Ormuz y Gibraltar.
No autoriza por sí sola merge, publicación, vídeo o generación recurrente.

## Selección y muestra auditada

- Proveedor / modelo: Gemini / `gemini-3.8-flash-tts`, sin cambios.
- Voz: `es-es-advisor-2`, prebuilt; catálogo es-ES, región ES, masculino,
  Castilian Spanish. Sin clonación ni diseño de voz, ni consulta recurrente.
- Perfil de la muestra: `straitwatch_es_castilian_audition_v1`.
- Perfil compartido adoptado: `straitwatch_es_v2`. Mismo payload de voz y estilo
  que la muestra aprobada, sin instrucciones añadidas al texto editorial.
- [Audición manual PASS](https://github.com/ElPtoWalter/Gibraltar-Watch/actions/runs/36934873991).
- WAV nativo: PCM16 mono 24 kHz; 41 s frente a objetivo 35 s (+17,14%).
- SHA256 del master: `31edeb5ec69fe81b7851906bfdc7a37c6cf304e2015fd578fdd582f20a7cca4c`.
- Job: `voice-job:749ea6cc7af3289ccdafedc81fdca3216ab71616675ea8d875e983a967c79055`.
- Guion: `video-script:840caadad38667fb6436d68ccc7267c094b88156f81c0a52e7cbd37052da7a29`.
- Paquete: `video-package:gibraltar:2026-08-15:373719d6c596966392fa0cdd50afe86720aca9c0f5be4020124fe87c4ebfb97b`.

Guion y paquete históricos reales de Fase 2A, intactos: la muestra no representa
noticias actuales. No se cortó, aceleró, normalizó ni remuestreó el master.
Los artefactos se conservan fuera de los repositorios. No se modifican sus IDs,
hashes o metadatos históricos para aparentar una generación o revisión nueva.

## Límites de la aprobación

La identidad vocal queda aprobada. La revisión de exactitud de cifras y nombres,
transcripción acústica y pronunciación específica de cada pieza es independiente.
Los validadores siguen emitiendo `human_review_status=PENDING` y ASR `NOT_RUN`;
PASS solo certifica validez técnica. Este documento no es un bypass del gate.
No se afirma que exista un nuevo audio regional de Ormuz: se aplica la misma
configuración aprobada a su borrador, con sus pilotos anteriores conservados.

Charon / `straitwatch_es_v1` sigue disponible únicamente por selección explícita.
EN mantiene Charon / `straitwatch_en_v1`, sin aprobación de voz inglesa.
No se añaden llamadas TTS para adoptar el perfil, dependencias, secretos,
activación de billing, fallback de modelo o publicación automática.

## Verificación de la adopción

54 pruebas comunes sin API pasan en cada checkout. Los núcleos Python de ambos
repositorios coinciden byte a byte. La validación independiente con el código
nuevo acepta el master aprobado y los dos masters históricos Charon, sin
modificar sus hashes. Pruebas Node de interfaz: 3 Ormuz y 20 Gibraltar, PASS
local usando `--test-isolation=none` por la restricción de spawn de Windows.

La suite completa local de Windows no se da por aprobada: tests históricos
ajenos a voz encuentran PermissionError en TemporaryDirectory; el runner Node
aislado encuentra EPERM. La regresión completa se ejecuta además en Linux en
la CI de cada PR, sin relajar tests ni permisos del código de producción.
