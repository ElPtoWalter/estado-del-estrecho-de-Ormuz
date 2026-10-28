# Plan AdSense y tráfico orgánico

> **Estado posterior — 28/10/2026:** las tres investigaciones ES/EN están publicadas (PR #22–#24) y la entrega de la PR #25 se ha verificado por HTTP. La recepción de `contacto@estrechoormuz.com` está confirmada por declaración del titular; el envío con identidad del dominio sigue sin comprobarse. Hay acceso a rendimiento y metadatos históricos de Search Console y una instantánea global de Page Indexing aportada por el titular el 28/10/2026 (61 indexadas, 62 sin indexar); el estado individual de las seis investigaciones y URL Inspection siguen pendientes. Los recuentos, dependencias y propuestas fechados en este documento son historial. Prevalece [la auditoría actual](PREFLIGHT_ADSENSE_2026-10-28.md); no acredita aprobación AdSense ni cumplimiento legal completo.

23/10/2026. Propuesta operativa, sin activación publicitaria ni promesa de aprobación o visitas. Las prioridades de búsquedas son hipótesis hasta disponer de Search Console.

## Punto de partida verificado

La superficie pública funciona, tiene sitemap y versiones ES/EN; los partes automáticos están excluidos de indexación y publicidad. Hay 74 URLs en el sitemap, que no equivalen a 74 URLs indexadas. AdSense está apagado; ads.txt y la meta de propiedad son públicos, pero no prueban que la cuenta o el dominio estén aprobados. No se dispone de datos privados de tráfico ni ingresos.

Google distingue la verificación de propiedad —posible mediante código, ads.txt o meta— de la revisión del sitio y su estado **Ready**. Por tanto, no es necesario activar el cargador publicitario para demostrar aprobación local; se usará el método de verificación que ofrezca la cuenta, manteniendo los anuncios apagados. [Gestión de sitios](https://support.google.com/adsense/answer/12131223), [estados de aprobación](https://support.google.com/adsense/answer/12170222).

## AdSense: pasos y criterios de salida

| Orden | Acción concreta | Acceso o aportación necesaria | Criterio de salida |
|---|---|---|---|
| 1 | Registrar estado de `estrechoormuz.com`, motivo literal del rechazo, fecha, tareas pendientes y restricciones del Centro de políticas. | Cuenta AdSense del propietario, mediante sesión autorizada o exportación/capturas. | Diagnóstico específico de Google documentado; no inferido del HTML. |
| 2 | Contrastar el publisher ID de la cuenta con ads.txt y meta; comprobar propiedad y el estado de ads.txt dentro de AdSense. | Lectura pública posible; pertenencia y estado Authorized requieren la cuenta. | Identificadores coherentes y propiedad confirmada. Authorized no se interpreta como Ready. |
| 3 | Completar identidad real del responsable, contacto comprobado y coherencia entre aviso legal, privacidad, cookies y proveedores efectivos. | Datos auténticos del propietario y revisión de los requisitos aplicables. | Páginas ES/EN completas y coherentes. No inventar personas, credenciales o revisión humana. |
| 4 | Revisar la utilidad y autoría del contenido indexable. Priorizar tres recursos propios de la tabla siguiente, con fuentes, cálculos reproducibles, fecha y revisión editorial identificada. | Trabajo editorial; aprobación de un revisor humano cuando se declare tal revisión. | Cada recurso aporta algo comprobable más allá de reescribir titulares. Los borradores y partes siguen noindex y sin anuncios. |
| 5 | Preparar una CMP adecuada antes de cualquier activación futura; comprobar aceptación, rechazo y retirada, móvil/escritorio y regiones pertinentes. | Configuración de mensajes/CMP y pruebas autorizadas. | Evidencia de comportamiento real. Para anuncios personalizados en EEE, Reino Unido y Suiza: CMP certificada e integración TCF según Google. |
| 6 | Solicitar revisión una vez corregido el motivo de rechazo y completadas las tareas de cuenta. | Acción del propietario en AdSense. | Google comunica Ready y no hay restricciones aplicables pendientes. No eliminar y volver a añadir el sitio como rutina. |
| 7 | Valorar activación por separado, solo en páginas elegibles. | Nueva autorización expresa del propietario. | Cuenta, identidad, consentimiento y ubicaciones revisados; los cuatro controles permanecen false hasta entonces. |

Google pide contenido propio y relevante y una navegación útil; aumentar el número de páginas no sustituye ese valor. No se utiliza una supuesta cifra mínima de visitas o artículos como criterio de aprobación. [Preparar páginas para AdSense](https://support.google.com/adsense/answer/7299563). La certificación de una CMP no acredita por sí sola cumplimiento legal completo. [Requisitos de consentimiento](https://support.google.com/adsense/answer/13554116).

## Captación orgánica: cuatro semanas de trabajo

**Semana 1: corregir navegación y medir.** Revisar y, con autorización, desplegar la PR independiente de esta auditoría. En Search Console: confirmar propiedad del dominio, sitemap, indexación, canonical elegido, acciones manuales y seguridad. Exportar rendimiento de los últimos tres meses y comparar los últimos 28 días con los 28 anteriores, por URL, consulta, país y dispositivo. Separar consultas de marca y actualidad de las explicativas. No usar un `site:` como recuento completo de indexación. [Métricas de Search Console](https://support.google.com/webmasters/answer/7576553?hl=es).

**Semanas 2 y 3: reforzar tres páginas existentes, después adaptar sus versiones inglesas.** Es una meta de trabajo, no un requisito de Google ni un compromiso de nuevas publicaciones automáticas.

| Necesidad del lector / hipótesis de consulta | Página que se revisará | Aportación prevista |
|---|---|---|
| Cuánto petróleo pasa por Ormuz | `trafico-normal-estrecho-ormuz-cifras.html` y su versión EN | Tabla con período, unidad, fuente primaria y cálculo; diferenciar referencia histórica de flujo actual. Revisar derechos de cada gráfico. |
| Rutas alternativas y capacidad real | `rutas-alternativas-cierre-estrecho-ormuz-capacidad.html` y EN | Comparación por ruta que distinga capacidad nominal, utilizable y estimación fechada; explicar qué no puede deducirse. |
| Cómo afecta Ormuz a España y Europa | `como-afecta-ormuz-espana-europa.html` y EN | Fuentes primarias de importación, período y metodología; separar datos observados de escenarios. No prometer un precio futuro de combustibles. |

Enlazar esos recursos desde los apartados pertinentes de portada, análisis y metodología, con etiquetas descriptivas. Adaptar el inglés para su lector y conservar hreflang recíproco. La portada atiende la consulta de estado actual con hora, confianza y límites; los diarios automáticos no se convierten en páginas SEO por volumen. Google recomienda ayudar al lector, explicar quién y cómo produce el contenido y evitar generación masiva sin valor añadido. [Contenido útil](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [versiones localizadas](https://developers.google.com/search/docs/specialty/international/localized-versions), [política de contenido a escala](https://developers.google.com/search/docs/essentials/spam-policies#scaled-content).

**Semana 4: decidir con resultados.** Priorizar URLs con impresiones y margen de mejora; corregir títulos o descripciones que no respondan a la intención observada. Comparar clics, impresiones, CTR y posición por consulta/URL, sin atribuir a SEO un pico causado por noticias de Ormuz. Revisar Core Web Vitals de campo y hacer una medición móvil/escritorio antes de decidir cambios de rendimiento. Repetir la lectura semanal y evaluar una tendencia de 6–8 semanas, sin garantizar crecimiento. [Guía SEO de Google](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

## Qué puede hacerse ahora y qué necesita cuentas

Sin cuentas: corregir enlaces, revisar estructura, contenido, procedencia, metadatos, sitemap y rastreabilidad; comprobar públicamente robots, ads.txt y ausencia de cargadores. Esto ya tiene evidencias en la auditoría.

Con Search Console: acreditar indexación real, canonical seleccionado, consultas, clics, impresiones, CTR, problemas de experiencia y enlaces detectados. Con AdSense: acreditar rechazo, propiedad, Authorized/Ready, restricciones, consentimiento configurado e ingresos. Analítica, si existe y se autoriza su lectura, permitirá añadir sesiones orgánicas y comportamiento; no es necesario instalar otra herramienta para empezar con Search Console.

Pendientes iniciales del propietario: acceso de lectura o exportaciones de esas dos cuentas, identidad real y motivo exacto del rechazo. No se necesitan contraseñas en el chat. Hasta obtenerlos, no se afirma cuánto tráfico hay, cuánto puede ingresar el sitio ni que Google vaya a aprobarlo.
