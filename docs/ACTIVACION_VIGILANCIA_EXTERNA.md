# Activación pendiente de autorización

No ejecutar estos pasos de producción durante la preparación de la PR. Separar
la aprobación del código de cada activación. Todos los flags de la plantilla
`external-watch/wrangler.toml` están en `false` y los IDs están vacíos.

## 1. Vigilancia de solo lectura

- El titular elige y autoriza una cuenta Cloudflare, plan y retención. No requiere
  modificar DNS ni el alojamiento actual: usar un subdominio `workers.dev` nuevo.
- Verificar el CLI oficial; esta preparación utilizó **Wrangler 4.165.0**,
  `sha512-c4CX82CieBfWTQPOnrsbQI/h0pYYj+heF32LKC/+EIyUh1rASVoDGKW6i3aogi/aKPloSLZLOTVAQ+UH36mqyA==`
  según el registro npm oficial. Fijar versión y revisar antes de instalar.
- Guardar fuera de Git una copia de la configuración. No escribir credenciales
  en TOML, documentación, argumentos, logs ni artefactos de CI.
- Crear un secreto aleatorio de al menos 32 caracteres `READ_STATUS_TOKEN` mediante
  `wrangler secret put READ_STATUS_TOKEN` (entrada interactiva protegida).
- Solo tras autorización, habilitar `CHECKS_ENABLED=true`; mantener los otros dos
  flags `false`. Desplegar el Worker y su único Durable Object SQLite con el CLI.
  La migración `v1` crea almacenamiento del monitor; no toca datos del observatorio.
- Verificar `/health` con bearer en un cliente privado: 401 sin token, 200 con
  informe fresco correcto, 503 ante fuente obsoleta/fallo o >45 min sin chequeo.
  No poner el token en la URL. Métodos/rutas distintos no activan nada.
- Observar **48 horas** y después **siete días** de timestamps reales, intervalos,
  errores y límites. La propagación de Cron Triggers puede tardar hasta 15 min.
  No declarar la cadencia operativa antes de esa evidencia. Autorizar por separado
  un comprobador adicional de `/health` si se desea alertar de una caída del Worker.

## 2. Canal de incidencias técnicas privado

Autorizar antes el receptor concreto, destinatarios, coste y tratamiento de datos.
No usar la lista pública de cambios marítimos. Configurar `ALERT_HOST` con el host
exacto permitido y secretos `ALERT_WEBHOOK_URL`, `ALERT_WEBHOOK_TOKEN` (≥32 caracteres).
El receptor debe aceptar JSON con `id`, `type`, `checked_at`, `errors`, `verified_at`
y deduplicar `Idempotency-Key`. Solo salen estados públicos y códigos técnicos,
sin noticias internas, identidades o credenciales.

Activar `ALERTS_ENABLED=true` únicamente con autorización. Probar primero con una
fuente ficticia en un entorno local de pruebas, después una incidencia técnica
controlada expresamente autorizada. Comprobar recepción real. No se envía un aviso
de prueba a destinatarios reales durante esta PR. Un timeout o rechazo del POST
queda registrado y exige comprobar la recepción antes de actuar; no se reintenta
automáticamente la misma incidencia. Sin un canal probado no hay alertas garantizadas.

## 3. Segunda vía de activación del motor

Crear una GitHub App dedicada e instalarla **solo** en
`ElPtoWalter/estado-del-estrecho-de-Ormuz` (ID `1298193500`). Permiso de repositorio
**Actions: read and write** y Metadata de lectura implícita; sin Contents,
Administration, miembros, webhooks ni permisos de organización. Confirmar los IDs
en GitHub y en el servicio antes de activar. No usar un PAT personal amplio.

Actions:write es el permiso mínimo que GitHub ofrece para dispatch; no se puede
limitar por permiso a un único workflow. La aplicación técnicamente tiene acceso
a más acciones del repo; la restricción a `update-status.yml`/main se impone en
el código. Es un riesgo residual a aceptar, con claves rotables y revocables.

La clave debe ser RSA PKCS#8, almacenada como secreto `GITHUB_APP_PRIVATE_KEY`.
Si GitHub entrega PKCS#1, convertir **localmente en entorno privado** con OpenSSL
`pkcs8 -topk8 -nocrypt`, sin pasar la clave en argumentos ni subir los archivos.
Configurar `GITHUB_APP_ID` y `GITHUB_INSTALLATION_ID`; comprobar el repositorio
instalado. JWT RS256 (iat -60 s, exp +540 s), instalación solo para ese ID con
`actions:write`, token ≤65 min validado y revocado al acabar. No conservar tokens.

Solo después de fusionar y comprobar el preflight en main, y con autorización
distinta, activar `RECOVERY_ENABLED=true`. La primera prueba real debe dejar
evidencia correlacionada de UUID → run → commit → Pages → XML/HTML público.
Si otro writer terminó primero, el preflight debe omitir la recuperación sin
modificar datos ni renovar verificación. Medir este comportamiento realmente.

Un 204 ambiguo no se vuelve a enviar. Un run terminal observado permite hasta
tres intentos por verificación y espera ≥90 min. Tras el límite o pérdida de
confirmación: revisar el UUID en Actions, la publicación y los logs; una ejecución
manual explícita del actualizador permite recuperar el proceso. No borrar el
estado del coordinador para forzar un reenvío mientras pueda existir un run activo.
Un nuevo verified_at real inicia otro ciclo; no modificarlo manualmente.

## Costes estimados (consulta 20/11/2026)

Cada 15 min: **96 comprobaciones/día**, aproximadamente **2.880/30 días**; ocho GET
públicos por comprobación = **768 GET/día**. Estado acotado a lease, último informe,
incidente y último intento: no almacena un histórico creciente. Los intentos App
solo se solicitan cuando la recuperación está activada y procede/reconcilia.

Estimación **0 USD/mes dentro del plan Free**, condicionada a límites, tráfico,
CPU y disponibilidad real de la cuenta. Workers Free: 100.000 peticiones/día y
10 ms CPU por invocación; Durable Objects SQLite Free: 100.000 peticiones/día,
13.000 GB-s/día, 5 millones de filas leídas/día, 100.000 escritas/día y 5 GB.
La firma RSA y consultas se ejecutan dentro del DO, no en la ruta exterior ligera.
Falta medir CPU/duración/cuotas reales tras la autorización; un free tier agotado
puede fallar. No es un compromiso de coste ni un SLA.

Workers Paid empieza en **5 USD/mes por cuenta**, más excesos y posibles cargos
de otros productos. El receptor de avisos puede tener su propio coste. El consumo
de Actions, especialmente si cambia la visibilidad/plan, requiere verificar la
cuenta del titular. Establecer límites de gasto y revisar la factura; no contratar
ni activar facturación automáticamente.

Fuentes oficiales: [Workers](https://developers.cloudflare.com/workers/platform/pricing/),
[Durable Objects](https://developers.cloudflare.com/durable-objects/platform/pricing/),
[Cron](https://developers.cloudflare.com/workers/configuration/cron-triggers/),
[JWT App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app),
[token de instalación](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app),
[dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

## Reversión

Antes de activar, la reversión consiste en cerrar/revertir esta PR: no hay servicio
externo creado. Después de una futura activación autorizada:

1. Desactivar primero `RECOVERY_ENABLED` y `ALERTS_ENABLED`; después
   `CHECKS_ENABLED` y los Cron Triggers del Worker. Comprobar que no quedan jobs
   aceptados/pendientes en Actions; desactivar no cancela un POST ya aceptado.
2. Revocar instalación/clave de la App y secretos del receptor según el alcance.
   Guardar los recibos/UUID privados para resolver intentos ambiguos antes de
   eliminar el almacenamiento. No borrar documentos/históricos del observatorio.
3. Si se revierte código, hacerlo con una nueva PR limitada a estos módulos,
   docs y cambios de workflows. Mantener PR #30 y todas las nuevas actualizaciones
   de producción; nunca resetear main ni restaurar JSON operativos antiguos.
4. El cron nativo y el dispatch manual anteriores siguen disponibles. Restaurar
   sus pasos sin modificar el motor, clasificaciones, Pages, DNS ni publicidad.
