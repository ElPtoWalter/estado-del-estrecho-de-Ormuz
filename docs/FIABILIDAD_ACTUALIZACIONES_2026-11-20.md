# Fiabilidad del cron y vigilancia independiente

Estado: preparación para revisión. No se ha creado ni activado un servicio externo,
una GitHub App, credenciales o un canal de avisos. No se ha fusionado esta rama.
Base del primer candidato: `9644fb064bff502765457dde4f3eeae478724442`.
La revisión final sincronizó primero con `86a529ca17b0539035749bafefa773c5d2e866e6`
y después con `ee2f44d1c4350bce907e544c4f4c0a39dfb2cc30`.
Los recuentos siguientes conservan su ventana histórica; no son una consulta del
estado actual ni prueba de la cadencia posterior. El cierre y las correcciones
del candidato `ea05260b` están en [CIERRE_PR31_2026-11-20.md](CIERRE_PR31_2026-11-20.md).

## Diagnóstico comprobado

Ventana UTC: **12/11/2026 23:58 a 19/11/2026 23:58**, exactamente siete días.
Consulta REST realizada el 19/11 a las 23:58:17–18 UTC. Se recuperaron las últimas
100 ejecuciones del actualizador, cubriendo holgadamente la ventana; el watchdog
devolvió un historial vacío. Las respuestas detalladas permanecen fuera del repo.

| Workflow | Estado API | Cron UTC | Franjas previstas elegibles | Ejecuciones `schedule` observadas | Diferencia de recuentos |
|---|---|---|---:|---:|---:|
| `update-status.yml` (ID 311661179) | active | `37 * * * *` | 168 | 24 | 144 |
| `watch-publication.yml` (ID 424369501) | active | `13,43 * * * *` | 4 | 0 | 4 |

El watchdog existe en la rama por defecto desde la fusión `ec5926d0`, el 19/11 a
las **21:57 UTC**. Sus cuatro franjas son 22:13, 22:43, 23:13 y 23:43. No se le
atribuyen siete días de funcionamiento anteriores a su incorporación a main.

| Fecha UTC | Franjas del actualizador | Ejecuciones programadas |
|---|---:|---:|
| 13/11 | 24 | 4 |
| 14/11 | 24 | 4 |
| 15/11 | 24 | 4 |
| 16/11 | 24 | 3 |
| 17/11 | 24 | 3 |
| 18/11 | 24 | 3 |
| 19/11 | 24 | 3 |

Las 24 ejecuciones programadas terminaron correctamente: 0 fallidas, 0 canceladas,
0 pendientes. Hubo además una manual correcta, excluida de esos 24. El mayor
intervalo entre creaciones de ejecuciones fue **10,5539 h** (10 h 33 min 14 s).
Las 144 franjas aparentemente no representadas son una diferencia de recuentos,
no 144 eventos cuya omisión haya certificado GitHub.

**Retrasos:** la API no proporciona el `scheduled_for` original. Respecto de la
franja :37 inmediatamente anterior, 3 creaciones están a ≤5 min, 21 a >5 min y
10 de esas 21 a >30 min. Es un indicador ambiguo: puede asignar a otra hora un
lanzamiento muy retrasado. El número de retrasos reales y su duración exacta no
están establecidos. No se presenta ese indicador como latencia real del cron.

Dos muestras con jobs comprobados distinguen la cola del runner de la generación
del evento: [programada 44613411677](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/44613411677)
creada 20:54:33, job iniciado 20:54:37; [manual 44624378701](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/44624378701)
creada 22:00:27, job iniciado 22:00:31. **4 s de cola en ambas muestras**, sin
extrapolarlo al resto. Sus jobs terminaron en 53 s y 88 s respectivamente.

El estado `active` y `actions/permissions` (`enabled=true`, `allowed_actions=all`)
descartan una desactivación general visible en el momento de consulta. El cron
:37 está en main y se conserva en su historial. La concurrencia actual no cancela
el job activo; en la ventana no hay ejecuciones programadas canceladas visibles.
Las escrituras y publicaciones manuales y del diario han funcionado. Ninguna de
estas evidencias prueba que el planificador esté entregando eventos cada hora.

## Hechos, hipótesis y pendientes

| Cuestión | Resultado / límite |
|---|---|
| Cron y rama | Sintaxis válida, minuto alejado del inicio de hora, main, workflows activos |
| Inactividad de 60 días | Incompatible con la actividad reciente y el estado activo observado |
| Concurrencia | Grupo compartido con diario/recibos; protege escrituras. GitHub conserva como máximo una ejecución pendiente por grupo y puede sustituirla; no ofrece una cola durable de todas las franjas |
| Permisos de ejecución/escritura | Actions habilitado y manual correcta; no evidencia de un fallo `contents:write` |
| Retraso/supresión del planificador | Hipótesis compatible con el historial. GitHub documenta que puede retrasar o descartar eventos bajo carga; no prueba esta causa concreta |
| Cuotas, facturación o restricciones del actor | No comprobadas en la cuenta. Requieren acceso del titular y, si procede, soporte de GitHub con los IDs y la ventana |
| Estado global GitHub | API pública consultada: Actions y Pages operativos, sin incidentes abiertos; el documento llevaba actualización 19/11 21:09 UTC. No certifica la entrega del cron de este repo |
| Fuente externa GDELT | Se observó 429 en la recuperación anterior; el pipeline completó con otras fuentes. No es evidencia de una cuota de Actions |
| Watchdog | Activación administrativa comprobada; ninguna ejecución real observada a la hora de corte. No se fuerza un dispatch ni se declara periodicidad recuperada |

Fuentes: [limitaciones de schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[concurrencia](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[estado público](https://www.githubstatus.com/api/v2/summary.json).

Reproducción local, con entrada detallada privada y sin credenciales:

```sh
python workflow_cadence.py /PRIVATE/monitor-actions-private.json --end 2026-11-19T23:58:00Z --minutes 37
python workflow_cadence.py /PRIVATE/watchdog-actions-private.json --end 2026-11-19T23:58:00Z --minutes 13 43 --eligible-from 2026-11-19T21:57:00Z
```

Esquema de entrada: `total_count`, `runs[]` con `event`, `created_at`, `conclusion`.
El script rechaza una primera página que no cubra los siete días. Para siguientes
auditorías recoger todas las páginas necesarias; nunca convertir ausencia de
paginación en ausencia de ejecuciones. Mantener el detalle fuera del repositorio.

## Cambios preparados

1. `external-watch/`: Worker independiente de GitHub, coordinado por un Durable
   Object SQLite. Cron de 15 min (`7,22,37,52` UTC), desactivado por configuración.
   Consulta `publication-health.xml`, seis HTML y otra vez el XML, sin JSON interno.
2. Verificación V7 >3 h => incidencia. El diario usa su propio heartbeat de 36 h;
   una edición antigua es solo advertencia editorial. Un `not_due` válido no es
   fallo del diario ni renovación de V7. Las pruebas ejecutan los generadores
   reales sobre temporales y conservan exactamente status, V7 y health.
3. Avisos técnicos privados opcionales: dos fallos separados ≥14 min; con cadencia
   de 15 min prevista, detección inicial hasta 15 min después del umbral y aviso
   aproximadamente hasta 30 min después. Esto es un diseño, **no un SLA medido**.
   Destino HTTPS autorizado, bearer secreto, clave de idempotencia por incidente,
   acuse JSON con el ID correcto y consulta GET de recibo tras respuesta ambigua;
   un envío ambiguo no se repite a ciegas. No se envían notificaciones públicas
   ni avisos automáticos de recuperación. La resolución queda en el estado.
4. Recuperación opcional mediante GitHub App y `workflow_dispatch` fijo a main.
   Desde 75 min sin verificación V7, contrato válido y publicación coherente.
   Si el contrato es inaccesible/incoherente se avisa; no se hace un dispatch ciego.
5. Lease persistente de 10 min contra solapamientos externos. Si existe un job de
   actualización, diario o Pages activo, espera. Un run correcto puede ser un
   no-op: no se usa su fecha como prueba de actualización. Registra el intento
   **antes** del POST y correlaciona el UUID con el
   `run-name`. HTTP 204 no equivale a ejecución, verificación ni publicación.
6. Solo un run terminal comprobado admite reintento: ≥90 min entre intentos,
   máximo tres para la misma verificación. Falta de confirmación, historial
   truncado o respuesta ambigua => espera/revisión; nunca reenvío ciego.
7. `recovery_preflight.py`: dentro del bloqueo compartido y tras checkout del main
   actual, compara V7 y un recibo específico del monitor. Solo coalesce un trigger
   antiguo si otro run posterior de ese workflow ya validó el mismo V7 hace <50 min.
   Un trigger nativo nuevo se ejecuta; `health.json` nunca decide su omisión. La
   recuperación externa puede omitir una comprobación que un monitor validado
   ya cubrió; una ejecución manual explícita sin inputs conserva su función.
8. Se retira `publication_needed.py` y su gate: seis HTML y un manifiesto no
   prueban la integridad de todo el sitio. Pages reconstruye en push, dispatch y
   workflow_run elegibles, incluso para reparar otros recursos del mismo commit.
9. La salud incluye los errores de recuperación y recibos de aviso pendientes.
   Un lease vencido impide nuevos efectos del writer antiguo. El recibo privado
   del actualizador enlaza run, UUID, evaluación y commit persistido, sin renovar
   artificialmente verified_at ni entrar en Pages.

## Límites y seguridad real

Implementados en código y probados localmente: límites de respuesta/tiempo, TLS,
sin redirecciones, secretos fuera del código, token App corto y revocado,
destino fijo, bloqueo persistente, controles de frescura, reintentos limitados,
prueba XML/HTML y estado autenticado de solo lectura `/health`. Este endpoint
devuelve 503 si su último chequeo tiene >45 min; necesita un observador adicional
para alertar de una caída del propio monitor externo. No se afirma autovigilancia
infalible ni disponibilidad de Cloudflare/GitHub garantizada.

**Pendientes de autorización y comprobación real:** cuenta y despliegue Cloudflare,
GitHub App/instalación/secretos, receptor de incidentes, monitorización del propio
servicio, cuotas y facturación, cadencia de cron, recuperación y entrega efectiva.
El segundo disparador evita depender del cron de GitHub, pero **sí depende de la
API y runners de GitHub para ejecutar el motor**. Si GitHub entero falla solo
puede detectar y avisar. No hay migración a repositorio privado completada.

Los datos operativos, históricos, investigaciones aprobadas, políticas de
indexación, DNS, alojamiento, identidad legal y permisos publicitarios no se
modifican. El código externo y documentos no entran en el allowlist de Pages.

Ver [activación, costes y reversión](ACTIVACION_VIGILANCIA_EXTERNA.md).

## Validación de la propuesta

- Pruebas Python de guardas, reloj, generadores reales sobre temporales,
  deduplicación, evidencia cuantitativa y exclusión de código externo del builder.
- Pruebas Node sin credenciales reales: contrato/HTML, fuentes obsoletas, diario,
  lease persistente, autenticación de estado, firma RSA efímera, alcance de la App,
  concurrencia con diario/Pages, aceptación ambigua, reintentos y avisos privados.
- Wrangler 4.165.0: bundle local `deploy --dry-run`, sin iniciar sesión ni publicar.
  Runtime local: evento scheduled desactivado HTTP 200; `/health` sin configurar
  HTTP 404; POST a `/recover` HTTP 404. El helper de prueba quedó cerrado.
- Construcción Pages, privacidad, enlaces, sitemap y regresión de las tres parejas
  de investigaciones: **285 archivos**, **46 recursos aprobados idénticos**,
  sitemap fuente **112** y construido **62**. Esto no afirma páginas indexadas.
- HTTP real: XML inicial/final y seis HTML devolvieron 200 y coincidieron en V7 y
  commit `9644fb06`; verificación `22:01:44Z`, diario comprobado `23:07:32Z` sin
  renovar V7. El código nuevo no se ha publicado ni ejecutado con una App real.

Los resultados de CI se vinculan al commit de la PR. La comprobación inicial en
Windows encontró cuatro bloqueos de sandbox en fixtures Git temporales; se
repitieron solo esos cuatro con **GIT_ALLOW_PROTOCOL=file**, impidiendo alcanzar
remotos HTTPS/SSH, y pasaron. No se relajaron pruebas ni se hizo push a main.
