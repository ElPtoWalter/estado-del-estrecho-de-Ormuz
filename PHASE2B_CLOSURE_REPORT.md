# PHASE2B_CLOSURE_REPORT · StraitWatch Gemini Voice

## Actualización · 2 octubre 2026

**Identidad vocal castellana aprobada por el usuario y adoptada en ambos
borradores.** `es-es-advisor-2` / `straitwatch_es_v2` es el nuevo valor ES por
defecto; Charon queda como alternativa explícita, no automática. Arquitectura
3.1.0, 54 pruebas comunes. EN no cambia. La audición aprobada de Gibraltar se
conserva intacta, con su perfil experimental y su job original; no se regenera
ni se cambia su metadata histórica PENDING. Véase `PHASE2B_CASTILIAN_APPROVAL.md`.

Esta aprobación es de voz/acento, no un permiso de merge, publicación o inicio
de vídeo. No hay nuevo piloto regional de Ormuz: los resultados que siguen son
el registro histórico de los primeros pilotos Charon, no del nuevo perfil.
Cada audio futuro mantiene revisión humana PENDING; ASR sigue NOT_RUN.

## Informe histórico original · 1 octubre 2026

Fecha: 1 octubre 2026, UTC. Resultado: **IMPLEMENTACIÓN Y PILOTOS TÉCNICOS COMPLETOS; APROBACIÓN AUDITIVA PENDIENTE**.

No se ha fusionado ningún PR, publicado audio o modificado las webs. No se inicia
otra fase audiovisual. Se detiene el trabajo para que el usuario escuche ambos
candidatos. PASS técnico NO significa aprobación artística, editorial o ASR.

## Resultado comprobable

| Comprobación | Ormuz | Gibraltar |
| --- | --- | --- |
| Proveedor / modelo | Gemini / gemini-3.8-flash-tts | Gemini / gemini-3.8-flash-tts |
| Voz / perfil compartido | Charon / straitwatch_es_v1 | Charon / straitwatch_es_v1 |
| Idioma solicitado | es-ES | es-ES |
| WAV nativo | PCM16 mono, 24000 Hz | PCM16 mono, 24000 Hz |
| Objetivo del guion | 60 s | 35 s |
| Duración real | 56.36 s | 37.2 s |
| Desviación | -6,07% | +6,29% |
| Tamaño master | 2711348 bytes | 1791668 bytes |
| Clipping severo / silencio total | NO / NO | NO / NO |
| Validación remota y local independiente | PASS / PASS | PASS / PASS |
| Guion / paquete alterados para TTS | NO / NO | NO / NO |
| Revisión de acento, cifras y pronunciación | PENDIENTE | PENDIENTE |
| ASR / validación de transcripción acústica | NOT_RUN | NOT_RUN |
| Publicación / aprobación humana | DISABLED / PENDING | DISABLED / PENDING |

La señal es no vacía, presenta amplitud razonable y duración dentro de ±20%.
No se ha hecho resampling, normalización, speed-up o corte. Los masters son
los bytes originales de la API. Las características subjetivas (voz adulta
masculina, acento peninsular, naturalidad, credibilidad) deben confirmarse
escuchando: no se consideran probadas por la configuración o el PASS.

## Arquitectura entregada

- Núcleo común `phase2_voice/`: configuración/identidad, entradas, pronunciación,
  Gemini REST, WAV, metadatos, validación, artefactos temporales, caché y fixtures.
- Contrato de arquitectura 3.0.0; voice-input y metadatos 1.0.0. Sustituye el
  borrador proveedor-específico 2.0.0 nunca integrado.
- Fase 2A revalidada en cada frontera; su paquete 2.0.0 y guion 1.0.0 se
  consumen intactos. No se confía en un campo PASS suministrado por el cliente.
- `voice-pronunciation.json`: STRAITWATCH_PRONUNCIATION_V1, ningún override
  no escuchado, términos solicitados registrados para revisión.
- `phase2b-pilot-fixtures.json`: dos pilotos 2A históricos REALES congelados,
  paquetes, guiones y commits de procedencia. No se presentan como noticias actuales.
- `pilot_phase2b_voice.py`, workflow manual `pilot-phase2b-voice.yml`,
  CI sin API, 49 tests comunes y documentación `PHASE2B_VOICE.md`.
- Un request completo por guion; hook, escenas y outro conservados en orden,
  con referencias a hechos/declaraciones/fuentes. Estimaciones temporales
  proporcionales; NO se representan como alineación acústica.
- Identidad determinista del job; bytes TTS no deterministas. WAV de caché solo
  reutilizable tras revalidación completa, sin nuevas llamadas innecesarias.
- Resultados temporales fuera de repositorios, sin WAVs/pesos/cachés commiteados.

No se han cambiado funciones, reglas, estados o decisiones de producción de
Fase 1, 2A o 2C. Dos harnesses históricos de Ormuz se hicieron reproducibles
con datos reales congelados, manteniendo sus validadores y aserciones.

## Configuración y límites

`GEMINI_API_KEY`: secreto existente en ambos repositorios; no se extrajo su valor.

`GEMINI_TTS_MODEL`: gemini-3.8-flash-tts, selección explícita. Whitelist:
gemini-3.8-flash-tts y gemini-3.8-flash-lite-tts. No se cambia de modelo al fallar.

`GEMINI_TTS_VOICE_ES` / `GEMINI_TTS_VOICE_EN`: Charon por defecto; catálogo
cerrado de voces predefinidas. No voces custom, diseño o clonación. EN preparado
estructuralmente, sin piloto ni aprobación inglesa.

`GEMINI_MODEL` no se reutiliza. La locución se instruye por metadatos separados
del texto. Interactions API, `store=false`, clave en cabecera, sin herramientas,
sin redirects, timeout 120 s, texto máximo 6000 caracteres y límites de tamaño.
Solo workflow_dispatch para síntesis; sin push o ejecución recurrente.

## Pilotos, commits y PRs

| Elemento | Ormuz | Gibraltar |
| --- | --- | --- |
| PR Gemini sin merge, borrador | [#14](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/14) | [#18](https://github.com/ElPtoWalter/Gibraltar-Watch/pull/18) |
| Rama de implementación | phase2b-gemini-tts | phase2b-gemini-tts |
| SHA de implementación probado por CI | 6ab4bdf2cf5a7aafb15acd656e7c83fcc69fea1d | d2f7add271cba23b96b3bd6dcbea279505245293 |
| SHA de piloto temporal | 24aa639062bc542a6c4b298650c278858021c055 | 987938ba2ecdcf68792a02b39fae4e7383895ae9 |
| Ejecución real PASS | [36924840711](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36924840711) | [36924841040](https://github.com/ElPtoWalter/Gibraltar-Watch/actions/runs/36924841040) |
| CI de regresiones PASS | [36924839066](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36924839066) | [36924839585](https://github.com/ElPtoWalter/Gibraltar-Watch/actions/runs/36924839585) |
| Otra CI de Fase 1 PASS | [36924839123](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36924839123) | [36924839587](https://github.com/ElPtoWalter/Gibraltar-Watch/actions/runs/36924839587) |

El commit posterior solo incorpora este informe; su SHA exacto se obtiene del PR,
evitando una autorreferencia imposible dentro del propio documento.

Bases auditadas: Ormuz 14fefea665ff02a88f41b337494abd69f4f91ee2 y Gibraltar
6a3c8cc8605c821eb0da260f2f5dd7ba7729b26b. Durante el trabajo el workflow habitual
de Ormuz avanzó main a aee78aaa21b30edad8db4d53ec2bc53c2af7b38d, modificando
solo registros/superficie pública. Se preservó ese avance: la rama Gemini parte
de ese main, sin sobrescribir sus datos. Este trabajo no produjo ese despliegue.

Para dispatch antes de merge se utilizó únicamente una rama temporal
`phase2b-gemini-pilot-20261001` y el camino de workflow ya registrado de 2A.
La copia de ese workflow no está modificada en el PR final. No hubo síntesis
por push. Después de descargar y verificar ambos masters, las ramas temporales
se retiran; los commits, runs, artefactos y ramas de implementación se conservan.

## Identidades y masters

Ormuz:
- Paquete: `video-package:ormuz:2026-09-21:c62123682b8782326e7bf81dd49aa5fada7220933a8e36a6419891f2ac78b8e0`.
- Guion: `video-script:6dddb8b7362bdd2530a3bb8e35f330e8d038b3c3ca734561ca00c441acb86588`.
- Job: `voice-job:89ddbdf72c4bd40a5a885cc091785c2b7fa1b58708b5bac60a32972f9edf10c1`.
- WAV SHA256: `2435a4738c769c94866d9b7b5e57377e77e440b27e4e8571d4e1f88606cc0aa4`.
- Fixture: 21 septiembre 2026, events + archivo operativo, snapshot conservadora.
- RMS: -18.7847 dBFS; pico 0.858948; clipping 0.

Gibraltar:
- Paquete: `video-package:gibraltar:2026-08-15:373719d6c596966392fa0cdd50afe86720aca9c0f5be4020124fe87c4ebfb97b`.
- Guion: `video-script:840caadad38667fb6436d68ccc7267c094b88156f81c0a52e7cbd37052da7a29`.
- Job: `voice-job:1c635f46969d68532abb249f5b43ee5b3db9420a27423d3e56154567339fd388`.
- WAV SHA256: `5ccdc3524a0855b52c6b93c0e8997df43014eb6270361c1968d1d169bfb2abe0`.
- Fixture: observatorio 15 agosto 2026, parte OPE oficial del 14 agosto.
- RMS: -19.9727 dBFS; pico 0.84021; clipping 0.

Los dos artefactos descargados contienen: voice-input.json, audio-gemini.wav,
audio-metadata.json, validation-report.json, preview.md, video-package.json y
script.json. Los paquetes/guiones descargados coinciden íntegramente con las
fixtures validadas originales. Se repitió la validación local independiente
sobre los archivos descargados, comprobando también hashes e integridad RIFF.

## Pruebas y problemas detectados

- 49 pruebas específicas de voz PASS en ambos proyectos, sin red real ni consumo
  de cuota: input inválido, IDs/hashes, orden inmutable, pronunciación separada,
  modelos/voces, errores HTTP, timeout/red, corrupción, tamaños, señales,
  duración, silencio, clipping, metadatos, secretos, caché, directorios y workflow.
- Ormuz: 258 pruebas Python PASS; 3 pruebas Node PASS.
- Gibraltar: 287 pruebas Python PASS; 20 pruebas Node PASS. Su CI Fase 1 adicional
  también valida construcción y seguridad pública sin publicarla.
- Windows: las ACL privadas de mkdtemp eran incompatibles con el token restringido.
  Los tests propios usan directorios aislados con mkdir y limpieza de destino
  verificado. Pruebas locales finales y Linux CI PASS.
- Ormuz: la rotación de events.json hacía desaparecer un evento requerido por
  dos pruebas históricas preexistentes 2A/2C. Corregido únicamente el suministro
  de fixture real de sus harnesses; criterios editoriales y código de producción
  intactos. El fallo inicial está registrado en runs 36924012215 / 36924012169.
- Ambos pilotos iniciales fallaron ANTES de cualquier request TTS porque la
  comprobación estática del workflow 2A veía la copia temporal 2B. Se mantiene
  dicha comprobación en la suite completa final; el manual 2B prueba directamente
  sus contratos. Runs fallidos iniciales: 36924067856 / 36924071489.
- El primer CI 2B de Gibraltar apuntaba al fichero Node de Ormuz, inexistente
  en Gibraltar. Se corrigió a test_own_projects.cjs y pasaron sus 20 pruebas.
- Ningún fallo dio lugar a corte, speed-up, reescritura factual, menor confianza
  artificial, nueva clave, modelo premium o activación de billing.

## Seguridad, coste y fallback

No hay SDK, variables requeridas, voice IDs o llamadas ElevenLabs. Los PR
experimentales Ormuz #12 y Gibraltar #16 se cerraron sin merge; los workflows
únicos 371316228 / 371316298 se deshabilitaron. Se conservaron ramas antiguas
y secretos, sin borrar trabajo del usuario.

Los errores HTTP solo salen como códigos sanitizados; no se registran cuerpos,
cabeceras, credenciales o excepciones crudas. Los artefactos textuales se escanean.
WAV/JSON/ficheros y rutas de caché se validan antes de reutilizarse.

Gemini 3.8 Flash TTS tiene free tier documentado en los [precios oficiales](https://ai.google.dev/gemini-api/docs/pricing).
Los dos requests de síntesis funcionaron con las claves existentes. Este trabajo
no activó ni modificó billing o recursos comerciales. **No se ha verificado el
tier de la cuenta ni medido su importe facturado**; no afirmar coste cero real
sin revisar AI Studio. No hay recurrencia ni upgrades/reintentos automáticos.

Fallback local: interfaz disponible, motor físico APLAZADO y claramente
no operativo. Kokoro (82M, pesos Apache 2.0) y Piper (motor GPL-3.0, licencias
de cada voz por revisar) analizados; faltan audición es-ES masculina, fijar
modelo/licencia/checksum y caché externa. No se descargaron modelos grandes
para este encargo ni se sustituyó Gemini silenciosamente. Esta parte aplazada
está permitida por el alcance, no se oculta como un fallback funcionando.

## Estado de cierre y pendientes

Entregado: pilotos Gemini válidos en los dos sitios, masters escuchables,
contratos, metadatos, reportes, fixtures reales, tests, workflow manual, núcleo
compartido y documentación. Sin integración en main ni publicación.

Pendiente por decisión humana: escuchar ambos WAVs, contrastar cifras y texto,
acento, nombres/siglas, naturalidad y escoger o rechazar la voz. Pronunciación,
calidad editorial acústica y eventual EN no aprobados. Fallback local físico
aplazado; ASR opcional no implementada; revisar cuota/tier antes de recurrencia.

**Parar aquí. No fusionar, publicar ni continuar integración audiovisual hasta
que el usuario apruebe la escucha y dé una nueva instrucción.**
