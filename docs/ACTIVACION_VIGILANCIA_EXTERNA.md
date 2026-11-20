# Operación por fases — pendiente de autorización

Guía preparada el 20/11/2026. **No se ha creado cuenta, App, instalación, secreto,
servicio Cloudflare, receptor o envío real.** La PR sigue en borrador. La fusión
del código y las activaciones B, C y D requieren decisiones separadas del titular.
Los comandos de producción siguientes son instrucciones futuras, no tareas ejecutadas.

## Preparación local, sin cuenta

Usar Node LTS compatible y PowerShell 7. Desde la raíz del repositorio, guardar
herramientas, configuración y evidencias en un directorio privado fuera del checkout:

```powershell
$opsDir = Join-Path $env:LOCALAPPDATA 'OrmuzWatch'
New-Item -ItemType Directory -Force -Path $opsDir | Out-Null
npm install --prefix "$opsDir/tools" --ignore-scripts wrangler@4.165.0
$cli = Join-Path $opsDir 'tools/node_modules/wrangler/bin/wrangler.js'
node $cli --version
$repoDir = (Get-Location).Path
$entry = (Join-Path $repoDir 'external-watch/cloudflare-entry.mjs').Replace('\','/')
$config = Join-Path $opsDir 'wrangler.toml'
$text = Get-Content 'external-watch/wrangler.toml' -Raw
$text = $text.Replace('main = "cloudflare-entry.mjs"', ('main = "' + $entry + '"'))
Set-Content -LiteralPath $config -Value $text -Encoding utf8NoBOM
$env:WRANGLER_SEND_METRICS = 'false'
node $cli deploy --dry-run --config $config --outdir "$opsDir/bundle"
```

Wrangler 4.165.0 se contrastó con npm oficial:
`sha512-c4CX82CieBfWTQPOnrsbQI/h0pYYj+heF32LKC/+EIyUh1rASVoDGKW6i3aogi/aKPloSLZLOTVAQ+UH36mqyA==`.
Contrastar siempre `npm view wrangler@4.165.0 dist.integrity` con el paquete recibido.
No desactivar TLS. No poner claves en argumentos, logs, Git ni artefactos de CI.

La plantilla conserva todos los flags en false, SQLite (`new_sqlite_classes`),
un solo DO y cron UTC `7,22,37,52 * * * *`. No define rutas sobre el dominio.

## B — Primera activación, exclusivamente lectura

1. **Obtener autorización expresa B.** Elegir la cuenta Cloudflare del titular.
   Si todavía no existe, su creación requiere la misma autorización; no crear
   una cuenta en nombre del titular por inferencia. Verificar en su panel que el
   plan es Workers Free y que admite Durable Objects SQLite. Si no, detenerse;
   no contratar Paid ni añadir facturación automáticamente.
2. Ejecutar `node $cli login` y `node $cli whoami` con el titular. En caso de
   varias cuentas, elegir explícitamente la autorizada. Guardar su `account_id`
   solo en la copia privada TOML, como clave superior antes de `[triggers]`.
3. Revisar la copia: `workers_dev=true`, sin `routes`, sin `zone_id`, sin secrets,
   IDs App vacíos y los tres flags false. Autorizar la creación del Worker
   `ormuz-independent-watch` en `workers.dev` y su DO SQLite. Desplegar inicialmente
   inactivo con `node $cli deploy --config $config`. No modificar DNS ni Pages.
4. Generar 32 bytes aleatorios en un gestor de contraseñas y guardar el secreto
   `READ_STATUS_TOKEN` con `node $cli secret put READ_STATUS_TOKEN --config $config`.
   Usar la entrada del CLI, sin imprimir ni pasar el valor como argumento.
5. Cambiar **solo** `CHECKS_ENABLED = "true"` en la copia privada. Mantener
   `ALERTS_ENABLED = "false"`, `RECOVERY_ENABLED = "false"`,
   `RECOVERY_GATE_EVIDENCE_SHA256 = ""` e IDs App vacíos. Repetir dry-run y revisar
   los bindings. Solo entonces ejecutar `node $cli deploy --config $config`.
6. Guardar URL `https://ormuz-independent-watch.<SUBDOMINIO_AUTORIZADO>.workers.dev`,
   ID/fecha de versión desplegada, commit fuente y migración. El subdominio exacto
   lo devuelve Cloudflare; no inventarlo. Cron puede tardar hasta 15 min en propagarse.
7. Probar `/health`: sin bearer devuelve 401 si el secreto está configurado; con
   token correcto devuelve JSON y 200 o 503. **503 con `v7_stale` prueba detección,
   no indisponibilidad del endpoint**. Sin secreto configurado devuelve 404.
   POST `/recover` y rutas distintas devuelven 404. No hay trigger HTTP público.
8. Observar 48 horas y después siete días. Mantener C y D desactivados durante B.

Lectura privada de ejemplo; ejecutar solo tras B. El token se introduce oculto y
no va en la URL ni en el informe:

```powershell
$watchUrl = Read-Host 'URL workers.dev autorizada, sin /health'
$readToken = Read-Host 'Token de lectura' -MaskInput
$timer = [Diagnostics.Stopwatch]::StartNew()
$response = Invoke-WebRequest -Uri ($watchUrl.TrimEnd('/')+'/health') -MaximumRedirection 0 -TimeoutSec 20 -SkipHttpErrorCheck -Headers @{Authorization=('Bearer '+$readToken)}
$timer.Stop()
$sample = @{observed_at=(Get-Date).ToUniversalTime().ToString('o');http=[int]$response.StatusCode;response_ms=$timer.ElapsedMilliseconds;health=($response.Content|ConvertFrom-Json)}
$sample | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $opsDir 'health-private.json')
Remove-Variable readToken
```

El titular puede repetir la lectura cada 15 min durante la ventana autorizada en
su entorno privado. Si automatiza la captura local, registrar también los fallos
del propio capturador; su ausencia no prueba que Cloudflare omitiera un cron.
No registrar headers/bearer ni subir capturas o exportaciones a GitHub.

### Medición real y criterios de aceptación B

| Evidencia privada | Dónde / cálculo | Criterio antes de avanzar |
|---|---|---|
| Franjas y ejecuciones | Cron UTC, timestamps `checked_at`, eventos del proveedor | Contar previstas, observadas, huecos y retrasos; excluir propagación inicial de forma explícita |
| Endpoint accesible | Capturas HTTP autenticadas desde fuera de GitHub | Distinguir JSON válido 200/503 de timeout/TLS/5xx sin contrato; registrar intervalo del observador |
| Salud del sitio | `report.errors`, verified_at y V7 publicado | Los datos antiguos deben producir 503; el diario no debe renovarlos |
| Tiempo transcurrido | `metrics.elapsed_ms`, probe/recovery/alert ms y Wall Time del proveedor | p50/p95/máximo, sin confundirlo con CPU |
| CPU Worker | Workers & Pages → Worker → Metrics → CPU Time per execution | Medir p50/p95/máximo y errores de recursos; límite Free documentado 10 ms, no dar suficiencia por supuesta |
| DO y almacenamiento | Durable Objects → namespace → Metrics + uso de cuenta | Peticiones, errores, duración/GB-s, filas leídas/escritas, almacenamiento y límites compartidos |
| CPU del DO | Métrica/log de proveedor si está disponible en la cuenta | Si no se expone, marcar no medido; no sustituirlo por Wall Time ni CPU del Worker exterior |
| Estado persistente | `completed_checks`, `phase_b_observation`, reinicio controlado | Conservación tras reinicio; lease se recupera y un owner antiguo no puede enviar |

El código deja `cpu_time_ms=null` deliberadamente: falta la medición del proveedor.
El gate D exige ≥96 observaciones B válidas, ≥23 h 45 min entre primera y última y
ningún hueco >30 min en esa secuencia. Un hueco mayor reinicia la secuencia B.
Esto es un mínimo técnico; **no sustituye** las 48 h/siete días, cuotas, recepción,
revisión humana ni autorización. Un JSON válido de V7 antiguo cuenta como un
chequeo de vigilancia realizado, conservando su error y sin fingir frescura.

## C — Receptor privado de incidencias, autorización nueva

Elegir antes el proveedor y los destinatarios, coste, retención y tratamiento de
datos. Ningún receptor ha sido creado. No reutilizar suscriptores ni canales de
notificaciones marítimas. Configurar `ALERT_HOST` exacto y secretos separados:
`ALERT_WEBHOOK_URL`, `ALERT_WEBHOOK_TOKEN` (≥32 caracteres).

Contrato obligatorio del receptor, verificable antes de habilitar envíos:

- HTTPS, bearer validado, sin redirecciones. Token erróneo => 401/403.
- POST JSON `{id,type,checked_at,errors,verified_at}` y `Idempotency-Key=id`.
  Registrar atómicamente el ID antes de enrutar el aviso y deduplicarlo durablemente.
- Responder 200/202 con JSON **`{"id":"<MISMO_UUID>","accepted":true}`** solo tras
  aceptar durablemente el incidente. Un 204, HTML, ID distinto o 2xx vacío no confirma.
- GET al mismo endpoint con `?incident_id=<UUID>` y el mismo bearer debe devolver
  ese acuse si está registrado; 404 si no consta. No listar otros incidentes.
- Un acuse del receptor acredita aceptación técnica, no lectura humana ni entrega
  final de email/mensajería. Comprobar además el canal final en una prueba autorizada.

Tras C autorizada, probar en un Worker de ensayo separado con una incidencia
sintética, nunca alterando V7/Pages. Usar el receptor privado autorizado; confirmar
acuse y entrega final. Ensayar caída, rechazo, respuesta perdida y reinicio del
receptor. La consulta GET debe reconciliar un POST aceptado sin respuesta; si no
hay acuse, la incidencia sigue sin confirmar, `/health` devuelve 503 y **no se
repite el POST a ciegas**. No borrar el estado para forzar reenvíos.

Solo tras comprobar el contrato y con permiso C habilitar `ALERTS_ENABLED=true`
en el Worker vigilante. Mantener D false. Dos comprobaciones fallidas separadas
≥14 min confirman el episodio. El episodio conserva su ID aunque cambien sus
códigos de error. La recuperación de la fuente no oculta una entrega sin confirmar.

## D — GitHub App y recuperación, autorización distinta

Configuración exacta propuesta (no creada ni instalada):

| Campo | Valor |
|---|---|
| Nombre | Elegir uno disponible para esta instalación; no se declara registrado |
| Homepage | `https://estrechoormuz.com` |
| Webhook | Desactivado |
| Callback / OAuth / usuario | Sin callback; sin flujo OAuth de usuario ni permisos de usuario |
| Repository permissions | Actions **Read and write**; Metadata **Read-only** implícito; todos los demás No access |
| Organization permissions / eventos | Ninguno |
| Instalación | Solo cuenta/repositorio autorizado: `ElPtoWalter/estado-del-estrecho-de-Ormuz`, ID `1298193500` |
| Branch / workflow en código | Exclusivamente `main` / `update-status.yml` |
| Credenciales | ID App, ID instalación y RSA PKCS#8; nunca client secret/PAT personal amplio |

Actions:write permite más operaciones dentro de ese repo; GitHub no lo limita a
un único workflow. El destino se restringe en código. Aceptar este riesgo residual,
prever rotación/revocación y no instalar la App en todos los repositorios.

Si la clave de GitHub es PKCS#1, convertirla localmente con OpenSSL
`pkcs8 -topk8 -nocrypt`; archivo de entrada/salida exclusivamente privado. Guardar
`GITHUB_APP_PRIVATE_KEY` como secreto de Cloudflare y los dos IDs en la copia
privada. JWT RS256: iat -60 s, exp +540 s; token de instalación solo ese repository_id,
solo Actions write, Metadata read y **caducidad máxima 60 min**. Se revoca siempre;
si falla la revocación, la salud falla y exige intervención.

Antes de cualquier dispatch real, y con autorización para probar credenciales:
cargar los tres valores en variables privadas de un proceso, establecer
`APP_AUTH_PROBE_AUTHORIZED=true` y ejecutar:

```sh
node external-watch/check-app.mjs
```

El probe pide un token, comprueba repo/alcance, lee Actions y lo revoca. **Nunca
hace dispatch.** Sin autorización explícita en su variable no hace peticiones.
Guardar la salida privada y la confirmación real de revocación; limpiar el entorno.
No ejecutar este probe con credenciales reales durante la preparación de la PR.

### Gate previo a D

Exigir evidencia real, privada y revisada por el titular de: B y métricas/cuotas,
autenticación y revocación App, C y entrega final, duplicados, límites, reversión y
una prueba controlada de trazabilidad. La primera prueba de dispatch necesita su
propia autorización y entorno/ventana acordados; no activar un cron recuperador
sin haberla realizado.

Para ese ensayo único, mantener `RECOVERY_ENABLED=false` en Cloudflare. El CLI
`external-watch/exercise-recovery.mjs` no crea servicios ni periodicidad. Solo con
permiso explícito de ensayo, cargar en el proceso los tres valores App, fijar
`RECOVERY_SINGLE_TEST_AUTHORIZED=true`, `RECOVERY_EXPECTED_VERIFIED_AT` exactamente
al contrato público y `RECOVERY_TEST_RECEIPT` a un archivo nuevo con ruta absoluta
en `$opsDir`. Ejecutar `node external-watch/exercise-recovery.mjs` una sola vez.
Comprueba XML/HTML y elegibilidad ≥75 min, comprueba writers, guarda el intento con
UUID antes del POST, envía un dispatch a main y revoca el token. Un archivo ya
existente impide repetir el POST; no cambiarlo/borrarlo para reintentar un resultado
incierto. Un error puede ocurrir después de la aceptación: reconciliar primero
UUID y Actions. Sin el flag de autorización el CLI no hace peticiones.

Este ensayo externo comprueba la App y la publicación real, pero no prueba por sí
solo el cron autónomo de Cloudflare. Después de D se debe observar también la
primera recuperación real originada por el Worker, con su cadena completa.

Preparar fuera de Git un acta que referencia versiones, métricas, IDs reales de
pruebas y decisiones; calcular SHA-256 de ese archivo. Solo tras aprobación D,
poner ese hash real en `RECOVERY_GATE_EVIDENCE_SHA256` de la copia privada y
`RECOVERY_ENABLED=true`. No inventar acta ni hash para superar el gate. El código
comprueba hash configurado, receptor activado, token de lectura y observación B;
**no puede certificar por sí mismo la autenticidad del acta del titular**.

## Pruebas de extremo a extremo y reversión

Usar la [matriz de ensayo y condiciones de parada](CIERRE_PR31_2026-11-20.md).
Tras una prueba D expresamente autorizada, seguir UUID → run_name → run_id →
recibo/resumen y artefacto `monitor-run-<run_id>-<attempt>` → `written_commit` → Pages →
source_commit/assessment_id/verified_at publicados y seis HTML. Si main avanzó
después, comprobar la ascendencia y el artefacto exacto de cada despliegue; no
inferir causalidad por una verificación nueva. Un run correcto sin nuevo V7 es
una incidencia explícita, no recuperación demostrada.

Los artefactos de un repositorio público no constituyen una bóveda privada. El
recibo de run solo tiene metadatos técnicos; credenciales, actas, métricas de
cuenta, pruebas de entrega y exportaciones permanecen fuera de Git y de Actions.

Revertir o pausar al superar cuotas, perder autenticación/recibos, observar
duplicados, una clasificación no justificada o discrepancias entre run y publicación:

1. D false primero; C false si hay riesgo de envío. B puede continuar en lectura.
   Si el propio monitor falla, CHECKS false y retirar Cron Triggers, verificando
   propagación. Ningún flag cancela un dispatch que ya aceptó GitHub.
2. Revisar jobs activos/pendientes y los UUID. Revocar instalación/clave y secretos
   comprometidos; conservar recibos antes de eliminarlos. No borrar datos para
   provocar reenvíos ni resetear main.
3. Si hace falta revertir código, nueva PR limitada a esta solución. Conservar
   PR #30 y todas las nuevas actualizaciones. Recuperación manual del actualizador
   y reconstrucción manual de Pages siguen disponibles mediante autorización.
4. Tras corregir, repetir la fase afectada y volver a solicitar su activación.

## Costes y fuentes (20/11/2026)

Diseño de 15 min: 96 ticks/día y 768 GET públicos/día, más consultas autenticadas
de estado. DO conserva contadores y estado acotado; no un histórico creciente.
**Free es una hipótesis de coste, no suficiencia validada.** Comparar consumo real
de toda la cuenta con Workers Free (100.000 peticiones/día, CPU 10 ms) y DO SQLite
Free (100.000 peticiones/día, 13.000 GB-s/día, 5 millones de filas leídas/día,
100.000 escritas/día, 5 GB). Agotar una cuota puede interrumpir vigilancia.
Paid parte de 5 USD/mes por cuenta más excesos; no se ha contratado. El receptor
puede cobrar aparte. Medir de nuevo tras C y D: sus peticiones y firma RSA no
están representadas por las métricas de B.

Fuentes oficiales: [Workers y precio](https://developers.cloudflare.com/workers/platform/pricing/),
[DO y precio](https://developers.cloudflare.com/durable-objects/platform/pricing/),
[métricas Worker](https://developers.cloudflare.com/workers/observability/metrics-and-analytics/),
[métricas DO](https://developers.cloudflare.com/durable-objects/observability/metrics-and-analytics/),
[cron](https://developers.cloudflare.com/workers/configuration/cron-triggers/),
[token App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).
