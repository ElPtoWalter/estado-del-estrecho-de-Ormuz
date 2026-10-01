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
La audición regional de Ormuz se generó después de la elección de voz, con
los pilotos anteriores conservados; su revisión auditiva específica sigue
PENDING. No se traslada automáticamente la aprobación de Gibraltar a esta pieza.

Charon / `straitwatch_es_v1` sigue disponible únicamente por selección explícita.
EN mantiene Charon / `straitwatch_en_v1`, sin aprobación de voz inglesa.
La adopción del perfil no requirió nuevas llamadas TTS. El piloto posterior
de Ormuz usa una única petición, sin nuevas dependencias, secretos, activación
de billing, fallback de modelo o publicación automática.

## Piloto regional posterior · Ormuz · 2 octubre 2026

- [Ejecución manual PASS](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36937022300).
- Commit temporal: `457ff4b685265d59023b435eba9f92510aea4c54`; base de
  implementación `90b00143fde040790117a0f0a4c02292b954852e`.
- Voz/modelo/perfil: `es-es-advisor-2`, `gemini-3.8-flash-tts`, `straitwatch_es_v2`.
- WAV nativo PCM16 mono 24 kHz; duración 51,28 s, objetivo 60 s (-14,53%).
  2467508 bytes; 1230720 frames; fracción clipped 0; RMS -20,0981 dBFS.
- SHA256: `0568cdcd649e8137559ee34984a9ea73efac999726e0a1d1c948b998d49d3b08`.
- Job: `voice-job:4b2491593af81328dcbd9073fd9cc444268b37fd865ee0273507eece64bbaf7a`.
- Guion: `video-script:6dddb8b7362bdd2530a3bb8e35f330e8d038b3c3ca734561ca00c441acb86588`.
- Paquete: `video-package:ormuz:2026-09-21:c62123682b8782326e7bf81dd49aa5fada7220933a8e36a6419891f2ac78b8e0`.

Validación remota y local independiente PASS; paquete, guion y entrada coinciden
exactamente con la fixture real y el job preparado. Histórico del 21 septiembre,
no noticia actual. Conserva un titular en inglés y su sufijo de fuente del guion
2A; no se traduce, elimina o reescribe desde TTS. Esa mezcla requiere revisión
editorial antes de producción; cualquier corrección pertenece a Fase 2A y exige
revalidación del nuevo guion. PASS técnico no certifica pronunciación o contenido.

Los tres masters previos mantienen sus hashes. El audio nuevo queda fuera del
repo; no se repite la audición de Gibraltar. Tras descargar y verificar, se
retira solo la rama temporal de este piloto, conservando commits, run, artefactos
y borradores. Revisión humana PENDING, ASR NOT_RUN, publicación DISABLED.

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
