# PR #26 — indexación, identificación y preparación AdSense

Auditoría del 28/10/2026 sobre main `97ff0f0a` y la entrega HTTP observada. Las PR #22–#25 están fusionadas y sus publicaciones se conservan. Este documento prepara decisiones; no autoriza merge, despliegue, publicidad, publicación de datos personales o solicitudes a Google. `ready_for_resubmission=false`.

## Cuatro evidencias distintas de sitemap e indexación

| Capa | Comprobación | Alcance y límite |
|---|---|---|
| `sitemap.xml` del repositorio | **112 URLs**; huella y listado en `preflight-20261028/sitemap-audit.json` | Inventario fuente/intermedio de las automatizaciones. No es el archivo que se sube directamente a Pages. |
| `_site/sitemap.xml` generado | **62 URLs**; construido después de políticas editoriales y selección de publicaciones | Elegibilidad técnica de esta construcción; no confirma inclusión en Google. |
| `https://estrechoormuz.com/sitemap.xml` | **HTTP 200, 62 URLs**; su conjunto de URLs coincide con `_site` | Evidencia pública fechada, con cabeceras y huella propias. No se deduce de GitHub. |
| Metadatos históricos del conector Search Console | **60 URLs enviadas** | La respuesta consultada conserva fecha de última descarga en julio de 2026. No es un recuento actual de URLs indexadas ni prueba de que Google no haya rastreado después. No se publica la exportación privada. |

La diferencia fuente/construcción es explícita: 56 URLs solo están en el fuente —36 ediciones fechadas, dos índices del diario y 18 páginas con otras políticas—; seis artículos originales solo aparecen en el sitemap público generado, pues se seleccionan de sus paquetes sellados al construir. No se elimina una página por esta diferencia ni se copia el sitemap fuente sobre la salida pública. Las dos listas y sus huellas quedan en la evidencia reproducible.

Las seis versiones ES/EN responden 200, tienen canonical propios, hreflang recíprocos y `index,follow`; robots.txt permite su rastreo y están en ambos sitemaps públicos comprobados. Esto no informa de la canonical elegida por Google o de su indexación actual. Las metodologías y el archivo congelado siguen accesibles con noindex según la política previa.

`preflight-20261028/url-inspection-template.csv` contiene seis filas técnicas y casillas de cuenta vacías. **Copiarlo a un entorno privado antes de incorporar resultados de cuenta.** Registrar Page Indexing, veredicto de URL Inspection, canonical elegida por Google, último rastreo y fecha de consulta, conservando allí la evidencia original. No introducir nombres de personas o exportaciones de cuenta en esta plantilla pública. No se han enviado URLs, sitemap o solicitudes de indexación.

## Ediciones del diario: revisión sin decisión automática

El inventario `preflight-20261028/diary-audit.csv` revisa individualmente las **36 versiones ES/EN incluidas en el sitemap fuente**. En las 36, el origen conserva `index` y la construcción/HTTP aplican `noindex`; ninguna está en el sitemap desplegado. Es una divergencia heredada, no una nueva exclusión de esta PR.

La extracción encuentra **34 párrafos compartidos entre ediciones**. Un párrafo de 48 palabras aparece en 18 ediciones españolas; su equivalente inglés de 45 palabras aparece en 18. Hay bloques que reiteran estado, seguridad y límites, además de noticias que sí cambian. No se encuentran cuerpos completos idénticos; la huella con fechas/números enmascarados tampoco los convierte en duplicados. Ese enmascaramiento es solo una ayuda de revisión y puede ocultar cambios de hechos.

La extensión observada, 597–1.047 palabras, no mide valor independiente ni constituye un mínimo AdSense. Los textos mezclan diagnóstico repetido, síntesis de fuentes y secciones de continuidad. La revisión editorial debe determinar qué aporta cada fecha además de titulares/plantilla, si identifica fuentes fechadas y si evita presentar una conclusión del monitor como observación completa de tráfico. No se declara que Google haya rechazado estas URLs concretas.

No se detecta contradicción formal entre la fecha visible, la ruta y las fechas schema convertidas a Madrid en estas 36 páginas. Una fecha UTC del día anterior puede corresponder al mismo día local; no se corrige como error. Esto no es una comprobación factual completa de toda la narrativa ni permite presentar un parte antiguo como situación actual. La afirmación de «primera línea base» localizada corresponde a la misma fecha en sus dos traducciones, no a varias jornadas. Los riesgos y límites quedan separados de los hallazgos demostrados.

**Decisión pendiente del titular:** conservar, mejorar o reconsiderar individualmente la elegibilidad de las ediciones tras lectura editorial y resultados reales de cuenta. No se cambia robots, canonical, sitemap fuente, diario o motor. No se crean exclusiones para aparentar mayor calidad.

## Correo: recepción y envío no son lo mismo

Recepción de `contacto@estrechoormuz.com`: **confirmada por declaración del titular del 28/10/2026**. La auditoría no ha enviado un mensaje ni ha hecho una prueba independiente. El registro está en `publisher-preparation.json`; no contiene dirección privada de destino.

Enviar respuestas con la identidad del dominio sigue **sin comprobarse**. La declaración no verifica otros alias. No se infiere capacidad SMTP, envío autenticado o respuesta efectiva de la existencia de MX, reenvío, SPF o DKIM. No se cambia DNS, contrata un proveedor o envía correo. Las propuestas ES/EN de aviso legal, privacidad y contacto corrigen el antiguo «recepción sin verificar» y quedan pendientes de revisión pública en esta PR.

## Matriz de comprobaciones y decisiones

| Elemento | Comprobado | Cuenta externa pendiente | Decisión del titular pendiente | Asesoramiento legal pendiente |
|---|---|---|---|---|
| Tres investigaciones, seis artículos | HTTP, metadatos y paquetes sellados; aprobaciones reales anteriores conservadas | Indexación, canonical elegida y rastreo | Ninguna nueva edición de los originales autorizada aquí | No se declara autorización jurídica externa de fuentes/licencias |
| PR #25 y navegación | Las cuatro páginas desplegadas contienen su sección de investigaciones y títulos esperados | Evolución SEO y datos posteriores suficientes | Fusión/publicación de esta PR, si procede | — |
| Diario histórico | 36 filas, políticas y repetición documentadas | Page Indexing/Inspection por URL | Revisión de valor por edición; no decisión automática | Derechos de terceros si se plantea otra reutilización |
| Correo entrante | Declaración del titular, separada de prueba técnica | Proveedor y operación de respuesta, si requiere cuenta | Validar identidad de envío y otros alias; ningún envío autorizado ahora | Canal efectivo y tratamiento de comunicaciones |
| Identificación de persona física | Naturaleza declarada; plantillas sin datos reales | — | Completar de forma privada y decidir un procedimiento seguro antes de cualquier publicación | Aplicación LSSI y dirección admisible; NIF, datos exigibles y condiciones |
| Privacidad | Borradores ES/EN revisados contra fuentes oficiales; siguen pendientes | Roles, contratos, retención y transferencias de proveedores | Confirmar tratamientos y políticas finales | Bases jurídicas, información y obligaciones aplicables |
| ads.txt | HTTP 200, texto e ID coherentes con fuente y construcción | Estado actual del archivo en AdSense, avisos y autorización de cuenta | Ninguna activación o revisión autorizada | — |
| CMP y anuncios | Sin cargadores activos; permisos en false | CMP y configuración real aún no verificadas | Elección y autorización futura, sin instalación ahora | Consentimiento, proveedores y datos/tecnologías reales |
| Reenvío y datos personales | Ningún destino privado ni identidad real incorporados | — | Prohibida su publicación en este encargo | Resolver obligaciones sin inventar domicilios o exenciones |

## Preparación AdSense actualizada

El reporte `adsense-readiness-report.json` y los informes antiguos enlazan este estado. Sus recuentos, dependencias y propuestas del 24/10 se conservan como historial, no como situación actual. Las tres investigaciones están publicadas y la PR #25 se verifica por HTTP; no siguen pendientes como seis borradores sin aprobación. Se mantienen los límites de esas aprobaciones: no se inventa una revisión humana adicional ni un permiso jurídico externo.

La cuenta AdSense no se ha consultado directamente. «Requiere su atención / contenido de poco valor / ads.txt no se encuentra» y la evaluación del 12/09/2026 son información histórica comunicada por el titular. La entrega HTTP actual de ads.txt no confirma que el estado interno de Google haya cambiado. Ni el ID público ni un archivo válido acreditan cuenta autorizada.

Permanecen `ready_for_resubmission=false`, `enabled=false`, `account_ready=false`, `cmp_verified=false` y `publisher_identity_complete=false`. El generador histórico deja de imprimir que el sitio está listo para revisión cuando devuelve false. No se ejecuta su instalador ni se aplica una nueva política editorial.

## CMP y consentimiento antes de cualquier activación

Google exige CMP certificada e integrada con IAB TCF para anuncios personalizados en EEE/Reino Unido y Suiza. Su documentación distingue otras modalidades; no se afirma que «no personalizado» elimine consentimiento o todas las obligaciones. La certificación evalúa criterios técnicos de Google y no acredita por sí sola cumplimiento legal completo. [Requisitos y lista vigente](https://support.google.com/adsense/answer/13554116?hl=es).

El plan del proyecto exige comprobar una CMP apropiada antes de activar publicidad. Elegir proveedor/versión certificada, territorios y partners; documentar finalidades y almacenamiento; probar rechazo/aceptación/retirada, señales y registros de consentimiento, bloqueo previo cuando sea exigible y ausencia de reactivaciones indebidas. Consent Mode o un enlace que intenta abrir ajustes no sustituyen una CMP verificada. Nada se instala o carga en esta PR. [Política de Google](https://www.google.com/about/company/user-consent-policy/).

La AEPD exige opciones de aceptar y rechazar simultáneas, al mismo nivel y con igual visibilidad para las cookies que requieran consentimiento. Revisar también mapas bajo demanda, preferencias y cualquier medición según su funcionamiento real, sin describir como activos futuros servicios. [AEPD](https://www.aepd.es/preguntas-frecuentes/17-internet-y-redes-sociales/FAQ-1707-importancia-de-las-cookies-en-la-proteccion-de-datos).

Checklist jurídico: [IDENTIFICACION_Y_PRIVACIDAD_2026-10-28.md](IDENTIFICACION_Y_PRIVACIDAD_2026-10-28.md). Pruebas, commit, CI y artefacto exacto se entregan en el informe final; no se asume que estos documentos completan las dependencias externas.

## Verificación local del candidato

479 pruebas Python de raíz (478 satisfactorias, una opcional omitida), 20 de mantenimiento y 23 JavaScript sin fallos; 125 archivos Python compilados. Construcción, enlaces, privacidad y ausencia de cargadores publicitarios pasan. Los tres controles de integridad de investigaciones pasan: sus 46 recursos públicos sellados se conservan. De los 255 archivos de salida, solo cambian las seis páginas legales/contacto por la actualización limitada del correo; los otros 249 son idénticos a la construcción de main con saltos de línea normalizados.

El validador general de fuentes devuelve cero errores y diez avisos heredados: tres evidencias compartidas entre listas activas/archivo, dos widgets sin h1 y siete metadatos ausentes en la página de verificación de Google. No son diez fallos nuevos ni se ocultan como un resultado sin avisos. Este encargo no cambia esas superficies o las evidencias operativas. La CI remota y su artefacto se referenciarán en la PR, vinculados al commit exacto; no se declara que su aprobación técnica cierre las dependencias legales o de cuenta.
