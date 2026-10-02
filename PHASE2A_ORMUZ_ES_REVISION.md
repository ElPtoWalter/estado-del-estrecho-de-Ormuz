# Ormuz · Revisión editorial española autorizada · 2 octubre 2026

El usuario autorizó corregir el titular inglés en Fase 2A, revalidar y regenerar
solo Ormuz. No autoriza merge, publicación o continuación audiovisual.

## Alcance exacto

Fuente preservada: `Iran and US trade threats after Houthi attacks escalate regional conflict - reuters.com`.

Representación española: **Irán y Estados Unidos intercambian amenazas tras
ataques hutíes que agravan el conflicto regional**.

La revisión es determinista y explícita para esta única instantánea histórica;
no es un traductor genérico, no hace llamadas editoriales de IA ni de red. La
etiqueta de dominio deja de formar parte de la prosa ES, pero se conserva en
la evidencia original EN y las URLs de Reuters y Bloomberg siguen intactas.
Los actores, amenazas, ataques y escalada del conflicto proceden del mismo
titular; no se añaden cifras, hechos, fechas, atribuciones o mayor certeza.
No se realiza una nueva verificación de noticias: se conserva la del paquete.

Se modifica únicamente `headlines.es`, `verified_facts[0].text_es` y
`what_we_know[0]`. Fact/event/source IDs, enlaces, texto EN, verificación, estado,
confianza, fechas históricas, dimensiones, incertidumbres y vigilancia permanecen
intactos. Después se sellan un paquete y un guion nuevos; no se sobrescriben
los originales. El guion solo cambia el titular, la locución y texto en pantalla
de escena 1, además de sus campos derivados de identidad y recuento de palabras.

## Identidades y validación

- Paquete original: `video-package:ormuz:2026-09-21:c62123682b8782326e7bf81dd49aa5fada7220933a8e36a6419891f2ac78b8e0`.
- Guion original: `video-script:6dddb8b7362bdd2530a3bb8e35f330e8d038b3c3ca734561ca00c441acb86588`.
- Paquete revisado: `video-package:ormuz:2026-09-21:eb23116f7bbf6244708e70f41728d6a878474b294c42bb10297995c4ef72e614`.
- Guion revisado: `video-script:9b814b8cecc48da259c6a5523ac1518d8090c9f04e690987c2465449e2ae2c32`.
- Job nuevo: `voice-job:88c6fae29409ec984bf7da1420564fdf93b574b635f4c90d5fc71c16d67ed05d`.
- Fact ID preservado: `fact-a0b4364f38881c5f`; mismo hecho, nueva prosa ES.

Paquete y guion originales y revisados pasan los validadores 2A sin modificar
esquemas, reglas o validadores. Una pareja nueva/vieja mezclada falla. Las
pruebas comprueban que solo cambian los campos autorizados y que otro paquete,
incluso válido, no puede acceder a esta corrección acotada.

## Flujo del piloto

`prepare_phase2a_ormuz_es.py` carga la fixture original, verifica sus IDs/hash,
aplica la revisión y escribe la pareja validada fuera del repo. Rechaza carpetas
existentes o interiores al repo. La procedencia y auditoría quedan en el
`fixture.editorial_revision` del reporte, conservado por el piloto de voz.

El workflow manual de Ormuz prepara primero esos artefactos 2A y luego los
entrega a `pilot_phase2b_voice.py` con `--package`, `--script` y metadatos de
procedencia. TTS consume ese guion íntegro sin traducciones, limpiezas ni cambios.
El núcleo compartido `phase2_voice/`, el perfil aprobado y los archivos de
Gibraltar no se modifican. No se repite ninguna síntesis de Gibraltar.

9 pruebas específicas de revisión editorial, más las 54 de voz y los contratos
2A. Síntesis solo manual: una petición para el nuevo job, sin retries, billing,
model fallback, cortes o aceleración. Los masters anteriores quedan intactos.
Histórico del 21 septiembre: no se presenta como actualidad. PASS es técnico;
escucha de la nueva pieza PENDING y transcripción acústica/ASR NOT_RUN.

## Resultado del piloto revisado

[Ejecución manual PASS](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36980491324),
commit temporal `97ce68e62b3385d810c23ed00b8deb37564a5c14`, base de implementación
`3c13bc16566340d6a1a34830eb67304df67881b7`. Validación local independiente del
artefacto descargado también PASS; nuevo paquete, guion, entrada y procedencia
coinciden exactamente con la revisión 2A y el job preparado.

WAV nativo PCM16 mono 24 kHz: 52,04 s frente a 60 s (-13,27%), 2503988 bytes,
1248960 frames, RMS -21,405 dBFS, clipping 0. Master SHA256:
`0f65d86951e4f855ad5f2a032fa2d582268b9bf18d7be5b5a34356892cf6d259`.
Una única petición Gemini; cache_hit false. No se conoce el tier de la cuenta
ni se afirma coste facturado cero. Los cuatro masters anteriores se preservan.

113 pruebas locales de revisión/voz/contratos 2A PASS. La CI completa Linux
de la base de código también pasa:
[regresiones 2B](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36980413578),
[Fase 1](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/36980413479).
La revisión auditiva humana sigue pendiente: no se afirma coincidencia de
transcripción acústica sin ASR o escucha. No merge ni publicación.
