# Correo profesional: opciones y comprobaciones

24/10/2026. El propietario prefiere contacto@estrechoormuz.com. La evidencia DNS en [EMAIL_DNS_2026-10-24.json](EMAIL_DNS_2026-10-24.json) muestra MX de Cloudflare y SPF; la consulta de DMARC devuelve NXDOMAIN. No se ha accedido a Cloudflare, al buzón de destino o a la cuenta del emisor: no se declara que el correo funcione. No se ha enviado ningún mensaje ni cambiado DNS.

| Opción | Qué permite | Qué falta y qué debe autorizar el propietario |
|---|---|---|
| Reenvío con Cloudflare Email Routing al buzón actual | Recibir en una dirección del dominio sin mostrar el destino privado en la web. Es la primera opción a comprobar por los MX existentes. | Confirmar regla contacto Active con destino verificado y acción de entrega, no Drop; probar recepción desde otra cuenta. No acredita capacidad de responder como contacto@. |
| Reenvío más proveedor de envío/alias autenticado ya disponible | Recibir por la ruta actual y responder desde el dominio si el proveedor realmente admite ese remitente. | Comprobar soporte, permisos del remitente, SPF/DKIM y alineación DMARC de los mensajes reales. No basta cambiar el campo From; no se confirma que la cuenta actual lo admita. |
| Buzón completo de un proveedor de correo | Entrada, almacenamiento y salida con identidad del dominio. | Elegir proveedor, plan/coste, condiciones, tratamiento de datos y migración de MX. No se recomienda una compra concreta ni se contrata nada sin conocer necesidades y autorización. |
| Cloudflare Email Sending | Servicio de envío transaccional; su documentación actual ofrece envío a destinatarios arbitrarios con Workers Paid. | No confundirlo con el reenvío ni con un buzón de atención humana. No se contrata ni se usa para mensajes comerciales o pruebas sin autorización. |

La documentación actual distingue reenvío y envío; las condiciones de un plan no se infieren de los registros DNS. [Cloudflare Email Service](https://developers.cloudflare.com/email-service/), [reglas y destinos](https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/).

## Secuencia mínima para cerrar la recepción y respuesta

1. Verificar con acceso autorizado la regla y el destino privado. No copiar al repositorio su dirección, capturas o datos de cuenta. El proyecto debe atender también las correcciones: comprobar correcciones@ o elegir un único canal realmente probado.
2. El propietario envía una prueba desde una cuenta distinta del destino, con identificador único y sin datos personales innecesarios. Comprobar bandeja, spam y registro de entrega. [Procedimiento del proveedor](https://developers.cloudflare.com/email-service/get-started/route-emails/).
3. Responder por la opción elegida y verificar recepción, remitente visible, Reply-To y SPF/DKIM/DMARC del mensaje efectivo. Registrar únicamente fecha y resultado. Un 250 SMTP, MX o SPF aislado no acredita la entrega final ni respuesta.
4. Revisar DMARC con todos los emisores identificados; no imponer reject sin probar alineación. La ausencia observada no prueba por sí sola fallo de recepción. Repetir tras cambios y establecer atención al canal de derechos.

Autorizar configuración de cuenta/DNS o contratación es una decisión distinta de autorizar envío de un mensaje de prueba. En esta tarea solo se ha comprobado información pública y preparado opciones. Se conserva el ID de editor confirmado por el propietario como declaración del propietario; ningún dato de correo o ads.txt confirma el estado interno de AdSense.
