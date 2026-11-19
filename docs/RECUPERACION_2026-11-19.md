# Recuperación del observatorio — 19 de noviembre de 2026

## Evidencia inicial y alcance

Base inspeccionada: `6ea981f69a42cc14a4b851aa3ed3b5c852dedee7`. No se ha desplegado esta propuesta.

| Prioridad | Confirmado | Consecuencia |
|---|---|---|
| P0 | Parte ES/EN público y JSON principal fechados 29/09; V7 fechado 19/11 02:45 UTC | Publicación desfasada; el generador diario ejecutaba el parte, pero no lo incluía en su commit |
| P0 | El actualizador modificaba únicamente la evaluación V7 embebida en ese parte antiguo | Dos fechas y estados incompatibles dentro del mismo documento |
| P0 | Historial público/RSS general derivados del motor heredado; avisos basados en su change-file | Una transición de V7 podía quedar sin aviso |
| P0 | Espera fija de 15 segundos antes de avisar, sin prueba del despliegue | Podía notificarse una versión todavía no publicada |
| P0 | Un arrastre V7 renovaba su propia fecha de referencia | La ventana máxima de 12 horas podía prolongarse sucesivamente |
| P0 | En 7 días hasta 19/11 02:45:30 UTC: 25 ejecuciones del actualizador, hueco máximo 10,55 h | Un cron horario no demuestra actualización horaria efectiva |
| P1 | El último log examinado contiene un 429 de GDELT; otros proveedores permitieron continuar | Dependencia degradada, sin demostrar fallo total ni agotamiento de cuota |
| P1 | Archivos internos comprobados por HTTP: 404; artefacto construido con exclusiones | Protección existente que debe conservarse |

Se recorrieron las 3.171 ejecuciones disponibles de la API, del 12/07 al 19/11: 1.150 del actualizador, 255 del diario y 1.067 del despliegue seguro. Hay 16 fallos históricos del actualizador; ninguno en los últimos 30 días consultados. Los horarios de creación no identifican inequívocamente qué slot de cron fue retrasado u omitido. No se atribuye una causa de cuota o bloqueo sin evidencia de cuenta.

La captura Search Console de 28/10 es histórica. No se conoce el estado de indexación individual actual de las investigaciones por estas comprobaciones HTTP.

## P0 propuesto

- Generación y persistencia explícita del parte completo en ambos workflows, RSS bilingüe y páginas históricas fechadas con noindex, sin anuncios.
- V7 como fuente de la portada, parte, historial actual y RSS. Los antiguos fragmentos del historial siguen accesibles, bajo un bloque que identifica el método anterior.
- Ninguna reescritura de los archivos históricos de origen ni de las investigaciones aprobadas. El diario conserva su evaluación al cierre, no se transforma retrospectivamente en una evaluación actual.
- Identidad estable de cada evaluación; control de coherencia entre el parte y V7.
- Fecha de evaluación separada de la última verificación durante arrastres. El reloj del arrastre no se renueva.
- Contrato público mínimo `publication-health.xml`: campos ya visibles de estado, dimensiones, confianza, fechas y revisión publicada. No contiene evidencias completas, JSON internos, configuraciones ni destinatarios.
- Umbral técnico: 3 horas, equivalente a tres ciclos horarios esperados. La advertencia no cambia la clasificación marítima.
- Bandeja de avisos V7 con transición anterior/nueva y evidencia; recibos por canal y reintentos. No anuncia estados ya superados.
- Envío únicamente después de comprobar por HTTP el commit y la evaluación del artefacto desplegado.
- Separación de vigilancia y actualización: otro workflow lee el contrato público. Un proveedor externo puede ejecutar exactamente el mismo comprobador sin acceso al repositorio.

La entrega real queda supeditada a canales configurados y a la variable `CANONICAL_NOTIFICATIONS_ENABLED=true`, que esta propuesta no activa. Las pruebas usan transportes simulados. Una confirmación HTTP evita duplicados ya reconocidos; un corte de red después de que el proveedor acepte un mensaje puede dejar un resultado ambiguo. No se promete entrega exactamente una vez.

## Despliegue propuesto, únicamente tras autorización

1. Revisar el diff y la CI del SHA exacto; comprobar que main no haya avanzado. Si avanza, sincronizar y repetir integridad/CI.
2. Fusionar solo con autorización expresa del titular. El workflow habitual construye y publica desde main; no ejecutar instaladores históricos.
3. Verificar HTTP ES/EN, los tres feeds del diario/parte y RSS operativo, el contrato público y los recursos sellados. Comparar `source_commit` con el commit construido.
4. Comprobar el siguiente ciclo real y que su parte, archivo y feeds quedan persistidos en Git.
5. Autorizar y configurar por separado la entrega real a Telegram/ntfy y suscribirse a fallos de Actions. No se han enviado pruebas reales.
6. Para cubrir una caída del planificador de GitHub, instalar el comprobador en un segundo proveedor con ejecución cada 30 minutos y salida distinta de cero como alarma. Comando: `python watch_publication.py --report watchdog-report.json`. No necesita tokens para consultar HTTP. El proveedor y destino de avisos requieren configuración del titular.

## Reversión

No restaurar por fuerza main, status ni históricos. Revertir el commit de código aprobado mediante PR, conservando los nuevos registros ya generados. Antes de revertir, desactivar por decisión del titular la variable de entrega si existe un incidente de avisos. Restaurar el anterior workflow de despliegue únicamente con revisión; verificar después que el artefacto sigue excluyendo archivos internos. Mantener el aviso de antigüedad hasta recuperar un ciclo comprobado.

## Pendientes externos

- Motivo exacto de los ciclos no observados, cuotas de cuenta y notificaciones de fallos efectivamente recibidas.
- Entrega real y pertenencia de los canales; no se leen ni publican valores de secretos.
- Vigilancia en otro proveedor para cubrir fallos de todo GitHub.
- Search Console actual; no se solicita indexación ni se envían sitemaps.
- Legal, correo saliente, CMP y AdSense: sin autorizaciones nuevas, anuncios apagados.
