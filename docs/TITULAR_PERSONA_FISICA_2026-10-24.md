# Titular persona física: identidad, privacidad y contacto

24/10/2026. Preparación sobre PR #21; no constituye aprobación jurídica ni autorización de despliegue. No se han publicado datos personales, contratado servicios, enviado mensajes o solicitado revisión de AdSense.

## Confirmado y pendiente

El propietario confirma titularidad personal independiente y pub-1713078636060241. Prefiere contacto@estrechoormuz.com y no desea publicar teléfono personal. Nombre legal, NIF, domicilio y autorización de los campos públicos siguen pendientes. La confirmación del ID por el propietario **no es acceso directo a AdSense**, ni acredita Authorized/Ready. Los cuatro controles de monetización siguen en false.

Las [cuatro plantillas ES/EN](../drafts/legal-persona-fisica-20261024/README.md) están excluidas del artefacto web. **GitHub es público**: contienen solo instrucciones, nunca datos reales pendientes de autorización. Completar copias fuera del repositorio; ningún DNI/NIE, domicilio privado, dirección de reenvío ni captura de cuenta debe añadirse a la PR. Las mejoras editoriales y técnicas continúan mientras se resuelven esos campos; no se declara completada la identidad legal.

## Obligaciones aplicables y opciones de privacidad

La LSSI contempla proveedores personas físicas y jurídicas y servicios gratuitos para lectores cuando constituyen actividad económica. Por ello, gestionar la web como particular **no concede una excepción por sí solo** si se financia con publicidad. No se determina aquí una fecha de inicio de actividad o la situación fiscal del titular. Debe comprobarse el alcance actual de la actividad, incluidos posibles patrocinios, afiliación o promoción económica; la ausencia de un cargador AdSense no demuestra ausencia de toda actividad económica. [LSSI: ámbito, artículo 10 y anexo](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758).

| Cuestión | Tratamiento propuesto |
|---|---|
| Identidad | Nombre y apellidos reales del titular cuando resulte exigible; la marca no los sustituye. No se obtiene el nombre legal del usuario de Windows o del perfil de GitHub. |
| NIF | El artículo 10.1.e exige el número de identificación fiscal correspondiente. No se promete ocultarlo, enmascararlo o facilitarlo solo por correo como equivalente al acceso público exigido. No hace falta publicar una imagen del documento. |
| Dirección | El artículo 10.1.a exige residencia o domicilio o, en su defecto, dirección de un establecimiento permanente en España. Evaluar un establecimiento profesional real y admisible si existe, con capacidad efectiva de contacto. No se presupone que una oficina virtual, dirección de gestoría, coworking o apartado postal satisfaga ese requisito por contratarla; debe verificarse su encaje real. No se contrata ninguno ni se inventa dirección. |
| Teléfono | No se añade teléfono personal por defecto. La sentencia C-298/07 admite medios adicionales al correo que permitan contacto rápido, directo y efectivo sin exigir siempre teléfono. Hace falta un canal real y atendido; no se afirma que exista un formulario. Si la actividad cambia a contratación con consumidores, revisar los requisitos adicionales antes de ofrecerla. |
| Datos condicionales | Registro, autorización administrativa, profesión regulada, precios o códigos de conducta solo si corresponden. No se atribuyen sociedad, colegiación ni credenciales. |
| Privacidad | Identidad/contacto del responsable, fines y bases por tratamiento, destinatarios y transferencias, plazos o criterios, derechos y reclamaciones, datos obligatorios y decisiones automatizadas relevantes. Representante, DPD y artículo 14 si proceden. El RGPD no obliga por sí solo a publicar un NIF en toda política; esa exigencia debe distinguirse de LSSI. |

El correo puede ser del dominio y reenviar a un buzón privado sin revelar su dirección en la web. Eso protege el destino de correo, **no sustituye las obligaciones de identificación**. Las obligaciones fiscales/censales y, en su caso, de Seguridad Social requieren valoración separada antes de ingresos; no se afirma exención por ser particular o por no superar una cifra de ingresos. La minimización consiste en publicar lo necesario y autorizado, no en sustituir los datos exigibles por información falsa. [TJUE C-298/07, fallo sobre contacto](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex%3A62007CJ0298), [RGPD, artículos 12–14](https://www.boe.es/doue/2016/119/L00001-00088.pdf), [información por capas de la AEPD](https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-de-informacion).

Las plantillas no asignan a todos los tratamientos una base genérica alternativa ni inventan plazos. Deben confirmarse el rol de GitHub, Cloudflare, el proveedor real del buzón y el mapa, sus condiciones y los mecanismos de transferencia aplicables. Los MX no prueban el proveedor de destino, DPA, DPF o cláusulas contractuales. La generación de noticias no equivale por sí sola a decisiones automatizadas sobre visitantes del artículo 22.

## Comprobación real del correo

[Evidencia DNS](EMAIL_DNS_2026-10-24.json), 24/10/2026 a las 11:29 UTC, consultas DNS-only mediante el resolvedor configurado:

- MX: route1, route2 y route3.mx.cloudflare.net; prioridades observadas 29, 27 y 24.
- SPF: `v=spf1 include:_spf.mx.cloudflare.net ~all`.
- `_dmarc.estrechoormuz.com`: NXDOMAIN en esa consulta. No se infiere un fallo del buzón. Revisar autenticación y política con el proveedor real antes de cambios; no imponer reject sin comprobar alineación y todos los emisores.
- No se conoce la ruta concreta `contacto`, si está activa, el destino verificado ni sus registros de entrega. No se han probado recepción, carpeta spam, respuesta desde el dominio o DKIM del emisor real; no se adivinan selectores.

La documentación de Cloudflare distingue MX de reglas de reenvío y destinos verificados. Por tanto, **DNS configurado no significa buzón confirmado**. La web ya enlaza contacto@ y correcciones@; ninguno se declara operativo basándose solo en esta prueba. La propuesta añade esa limitación en los textos legales, sin afirmar una recepción que no se ha visto. [Reglas y destinos de Cloudflare](https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/).

## Prueba pendiente con acceso a cuentas

1. Cloudflare: comprobar que `contacto@estrechoormuz.com` tiene regla Active con acción de reenvío al destino correcto y verificado, no Drop. Comprobar correcciones@ o dirigir las correcciones a un canal que se pruebe. No publicar el destino privado.
2. Desde una cuenta distinta del destino, enviar un mensaje de prueba con un identificador único y sin datos sensibles. Confirmar recepción en bandeja o spam y actividad de entrega; conservar fecha y resultado, sin copiar contenido privado a GitHub. No se ha enviado ningún mensaje en esta entrega.
3. Responder desde el medio profesional que realmente vaya a usarse. Verificar remitente visible, Reply-To, recepción y SPF/DKIM/DMARC del envío efectivo. El reenvío entrante no demuestra que esté habilitado el envío desde el dominio. No contratar un servicio de pago sin autorización.
4. Registrar la prueba y configurar atención a consultas/derechos. No afirmar un plazo comercial de respuesta que no pueda cumplirse. Repetir tras cambiar la ruta. [Prueba recomendada de recepción de Cloudflare](https://developers.cloudflare.com/email-service/get-started/route-emails/).

## Acciones para cerrar la preparación

Continúan sin datos personales: controles HTTP, ads.txt, build y enlaces; revisión del contenido y derechos; preparación del consentimiento. El propietario ha confirmado el ID, por lo que no se vuelve a pedir esa confirmación. Quedan el estado/rastreo de AdSense dentro de su cuenta, la prueba de correo, los campos legales necesarios y la autorización de su versión final. También siguen pendientes la revisión humana de los originales y las correcciones independientes de navegación/RSS de PR #20.

Antes de publicar los textos legales: resolver marcadores, validar dirección y canal adicional, completar tratamientos reales, revisar ES/EN y autorizar los datos concretos. No trasladar la plantilla sin completar a una página pública. Antes de solicitar revisión: publicar solo los cambios autorizados y comprobar de nuevo el sitio real. Antes de activar publicidad: cuenta, CMP/consentimiento y autorización expresa, sin dar por completado ninguno por esta documentación.
