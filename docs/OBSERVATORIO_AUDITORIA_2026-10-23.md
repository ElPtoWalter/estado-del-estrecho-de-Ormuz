# Estrecho Ormuz — auditoría y versión de desarrollo

> Registro de la entrega inicial. Para el estado vigente del diario, los enlaces permanentes del RSS y el cierre de la PR #19, consultar [la revisión posterior](CIERRE_PR19_DIARIO_RSS.md). Los resultados históricos que siguen no certifican la versión actual.

23 de octubre de 2026. Base inspeccionada: `2b0163a58f169c6708c0a9ee4904abd97107da10`. Repositorio público, 536 archivos versionados al inicio y 24 workflows. Se conserva GitHub Pages, el dominio y el motor operativo. No se han cambiado estados, evidencias ni credenciales por iniciativa de esta auditoría. No se autoriza con este documento una fusión o un despliegue. Al cerrar se incorpora `main` hasta `d55ed5bed4e31377f575ca785809b528ac76e54a`, una publicación automática del diario ocurrida durante el trabajo: se conserva íntegra, se resuelve el único conflicto del feed regenerando ambos idiomas y se repiten pruebas y compilación. La muestra controlada conserva su instantánea anterior y su hash; no se presenta como sustitución de esa publicación.

## A. Diagnóstico priorizado

| Prioridad | Evidencia comprobada | Resolución |
|---|---|---|
| Alta | El informe local decía `ready_for_resubmission: true` sin comprobar la cuenta de AdSense. La portada pública cargaba el anuncio, sin script CMP identificable en el HTML. | El informe distingue comprobaciones locales y aprobación externa. Publicidad programática desactivada por defecto mediante `monetization.json`. No se afirma que la ausencia de un script pruebe por sí sola un incumplimiento de consentimiento. |
| Alta | El aviso legal aplaza los datos completos del titular hasta monetizar. La privacidad identifica solo al proyecto y su correo. | Pendiente aportar los datos reales del responsable y revisar su aplicación al caso. No se han inventado nombre, domicilio ni identificadores. [Referencia: artículo 10 LSSI](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758#a10). |
| Alta | `PRO_LANGUAGE` sustituía menciones de IA y automatización por expresiones editoriales. El piloto real de PR #18 pasaba seguridad conservando el titular genérico y la entradilla original. | Se retiran las sustituciones que ocultaban el proceso. El prompt pide una nueva redacción, no copiar la plantilla. El piloto informa por separado sobre seguridad y semejanza con el borrador. |
| Alta | La caché atribuía un titular de Epping Forest Guardian a The Guardian por compartir «Guardian». CNBC TV18 también heredaba una identidad no declarada. Algunos titulares con «could» o «COMMENTARY» figuraban como factuales. | Identificación exacta de alias o dominio; verificación del editor en los titulares de Google News en caché y uso del dominio de `<source>` en nuevas lecturas. Las identidades ambiguas se excluyen de la selección del diario; hipótesis y comentarios quedan fuera del paquete factual de noticias. No se reescriben los archivos históricos ni la clasificación operativa. |
| Alta | El despliegue admitía ejecución manual desde otras ramas; no filtraba explícitamente la rama y repositorio del workflow precedente. | Guardas de `main` en monitor, diario y despliegue; comprobación del origen de `workflow_run`. No se cambian reglas de infraestructura ni permisos de la cuenta. |
| Media | El 23/10 la portada llamaba «Edición de hoy» al diario de 22/10. El último diario del historial consultado era de la jornada anterior. | «Última edición disponible», fecha preservada y dos ventanas UTC de recuperación. Se mantiene la idempotencia por fecha. Los horarios de GitHub pueden retrasarse o perderse; esto no constituye una garantía de ejecución. |
| Media | `diario-feed.xml` se alimentaba solo de ediciones materiales; no existía feed diario inglés. | Feeds ES/EN con hasta 30 instantáneas diarias, identificadores estables por fecha e idioma y preferencia por la URL histórica cuando existe. Para días sin archivo, el enlace abre la edición vigente; el título y resumen del feed conservan su fecha. |
| Media | El archivo de clave IndexNow devolvía HTTP 404 aunque el código lo usaba. | Excepción explícita para copiar esa clave pública. Se conserva la verificación de Search Console. No se confunden estos identificadores públicos con secretos de API. |
| Media | 24 páginas indexables carecían de la referencia hreflang a su propio idioma. El sitemap compilado asignaba la fecha del día a todas las páginas. | Se completa la autorreferencia cuando existe traducción declarada. El sitemap público reutiliza el generador común, respeta canonical/noindex/hreflang y omite fechas artificiales. Excluye la verificación Google. |
| Media | La portada inicial relegaba el diagnóstico por debajo de una presentación muy alta. | Encabezado compacto, dimensiones junto al estado, acceso al diario/RSS e historial, aviso de instantánea y antigüedad superior a seis horas. Prueba visual a 390 px y en escritorio. |
| Media | El constructor exploraba HTML en cualquier subcarpeta. `_headers` se servía como texto, sin las cabeceras que declaraba. | HTML limitado a raíz y rutas editoriales conocidas; previsualizaciones fuera del repositorio. Se deja de distribuir `_headers`, se conserva contacto de seguridad y se añade política de referencia mediante meta. Las cabeceras HTTP adicionales quedan pendientes de configuración real. |

En la comprobación HTTP pública, portada, inglés, diario, sitemap, robots, ads.txt y verificación Google devolvieron 200; `status.json`, `config.json` y `update_status.py` devolvieron 404. La respuesta de portada incluía HSTS y `Server: GitHub.com`; no incluía CSP, Permissions-Policy, X-Content-Type-Options ni X-Frame-Options. Los registros A consultados apuntaban a GitHub Pages. Esto no permite inspeccionar el panel completo de Cloudflare. El mecanismo `_headers` pertenece a [Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/headers/).

Los datos excluidos de `_site` siguen siendo accesibles en un repositorio público. El análisis por patrones no encontró claves en el texto versionado ni en el historial de texto de las ramas clonadas; no cubre binarios ni sustituye un servicio de detección de secretos. Las Actions usan secretos y no se han mostrado ni extraído sus valores. Los permisos de escritura se concentran en trabajos que guardan contenido o despliegan; los pilotos y CI son de lectura. Persisten instaladores históricos manuales: no forman parte del nuevo flujo ni se han ejecutado.

Un repositorio privado puede servir una web pública con un plan compatible. En GitHub Free, hacerlo privado puede retirar Pages: **no cambiar la visibilidad antes de verificar plan y alojamiento**. Alternativas a valorar con autorización: plan ya disponible que admita Pages privado, o fuente privada y superficie pública separada. No se contrata nada ni se cambia DNS. [Documentación de GitHub](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [cambio de visibilidad](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).

## B. Cambios implementados y mantenimiento

| Archivos | Resultado |
|---|---|
| `free_editorial_ai.py`, `generate_daily_journal.py` | Estilo editorial, objetivo de extensión bilingüe, capacidad de respuesta, titular local basado en el estado, transparencia y feeds diarios. Los validadores factuales permanecen activos. |
| `straitwatch_core.py`, `journal_evidence.py` | Resolución más estricta de la identidad del medio y exclusión de titulares analíticos del resumen factual. Las reglas de clasificación y los datos operativos almacenados se conservan. |
| `pilot_gemini_phase1.py`, su workflow | HTML autónomo de prueba fuera del repositorio; diagnóstico de plantilla separado de los controles de seguridad. |
| `publication_quality.py`, `editorial-reviews.json`, `monetization.json` | Políticas explícitas de anuncios y originales revisados; los partes conservan noindex y ausencia de anuncios. La promoción propia etiquetada sigue permitida en portada y análisis elegibles. |
| `build_public_site.py`, `build_sitemap.py` | Portada, rutas públicas, transparencia, metadatos bilingües, sitemap compartido, clave IndexNow, media kit y enlaces de contexto. |
| `monitor_report.py` y sus dos HTML | Gráfico de distribución del archivo y hreflang. El gráfico cuenta registros del monitor: no representa horas de cierre ni tránsito de buques. CSV y tabla comparten datos. |
| `public-ui.js` | Advertencia de antigüedad sin modificar la clasificación ni consultar APIs internas. |
| Workflows de monitor, diario, despliegue y CI | Guardas de rama, recuperación e inclusión de pruebas de `tests/` y promoción propia. |
| Informe AdSense, generador histórico, pruebas, README y CHANGELOG | Se elimina la equivalencia entre un informe local favorable y aprobación externa; procedimiento consolidado y regresiones cubiertas. |

No se añade un framework, una base de datos ni un proveedor de pago. Las modificaciones se concentran en los generadores que ya se utilizan. No se ejecutan los antiguos instaladores para aplicar estas mejoras.

## C. Diario Gemini y revisión de originales

La cadena sigue siendo fuentes → selección/deduplicación → eventos y contraste → paquete factual → Gemini → validación local → fallback/publicación. Se mantienen contratos bilingües, atribución por sección, controles de cifras, fechas, entidades, certeza y contradicciones operativas. Son barreras conservadoras, no una demostración semántica de cada frase. El modelo no decide el estado. La política de archivo selectivo y noindex no se relaja.

El validador v7 corrige fallos comprobados por pilotos reales: confundía la sintaxis «Según Associated Press»/«informes de Reuters» con nombres nuevos y no reconocía meses escritos a partir de fechas ISO. La atribución se analiza separadamente y sigue exigiendo una fuente autorizada. Las fechas naturales se comparan con fechas completas existentes en el paquete: no basta con que sus números aparezcan por separado. Un léxico geográfico ES/EN solo reconoce la misma localización cuando ya figura en los datos; no autoriza lugares nuevos. Las pruebas cubren fuentes inventadas, siglas, fechas nuevas y cambios de día/mes; el modal inglés «may» se distingue del mes. Un ensayo que añadió una organización ausente del paquete fue rechazado y no se ha autorizado ese nombre.

El módulo compartido mantiene por defecto el rechazo de la propuesta completa. El diario activa una recuperación explícita por fragmentos: parte de un borrador local que debe superar el mismo validador, prueba cada sustitución y vuelve a validar toda la edición bilingüe. Lo rechazado conserva el texto local; si no hay una aportación válida de Gemini o cambia el esquema, se mantiene el fallback completo. Se registra `partial-fallback`, las rutas de los fragmentos sustituidos y la validación final. No realiza llamadas adicionales al modelo. Esto mejora disponibilidad sin incorporar frases rechazadas ni cambiar estados, cifras o atribuciones. La nota pública explica la combinación de IA y reglas locales; el piloto diferencia este resultado de una salida íntegra del modelo.

El piloto real de la PR #18, ejecución `39928446884`, generó una edición bilingüe el 23/10 a las 08:58:39 UTC con `gemini-3.5-flash-lite`. Sus ocho comprobaciones fueron positivas: mismo paquete, versión de validador, eventos, fuentes, estado y salida bilingüe. No publicó nada. Su titular español seguía siendo «Ormuz: tráfico marítimo, evidencia y límites» y la entradilla era idéntica al borrador: **seguridad aprobada, calidad editorial todavía insuficiente**. Se ha conservado una previsualización real; no se presenta como una generación de esta rama.

La nueva prueba registra número de palabras, semejanza de secuencia de palabras y alertas de titular genérico/entradilla sin reescribir. Estos indicadores no miden originalidad periodística ni sustituyen una lectura. El presupuesto de respuesta pasa de 2.600 a 4.096 tokens para reducir el riesgo de truncar ambos idiomas; el prompt apunta a 320–450 palabras por idioma. El nombre del modelo no acredita que la clave pertenezca a un proyecto sin facturación: verificarlo en AI Studio, sin activar facturación. [Cuotas y facturación Gemini](https://ai.google.dev/gemini-api/docs/billing).

La revisión de la salida del primer piloto de esta rama detectó la atribución de Epping Forest Guardian: aunque los controles técnicos pasaban, el paquete heredaba una identidad incorrecta. Se corrigió la selección antes de preparar la muestra final. Esta comprobación ilustra el límite del validador: conservar un paquete no garantiza que su recopilación sea perfecta. El prompt también exige mantener al declarante original («Irán afirma») y no atribuir un hecho conjunto a medios cuyos titulares no lo sostienen. La muestra se entrega como parte automático sin aprobación editorial para convertirse en original indexable.

**Muestra final real:** [ejecución 39943911592](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/39943911592), commit `a13945d59aa1d60f14f0a7c5ffd7a397dbe062c5`, 23/10/2026 a las 11:08:24 UTC, modelo `gemini-3.5-flash-lite`. Nueve de nueve comprobaciones técnicas positivas. Paquete `946a9dd7cc1b9f3911b8d3467b72c47781078eeb8d30ee5c2ac0b2bbded209f4`; mismo estado `OPEN_SEVERELY_RESTRICTED`, eventos y fuentes operativas. Resultado **`partial-fallback`**: se rechazaron los párrafos de tráfico ES/EN y diplomacia EN; se conservaron sus versiones locales y se validó el conjunto. El diagnóstico inicial detectó una entidad no autorizada («guardia revolucionaria islámica»); no se añadió al léxico para hacer pasar la salida. Los archivos entregados contienen el resultado validado, no los párrafos rechazados. La activación temporal por push de la rama de auditoría se retira al cerrar la prueba.

Evaluación editorial de la muestra: 458 palabras ES y 341 EN antes del render; semejanza de secuencia con el borrador 0,643 y 0,724. Titulares basados en el estado, entradilla aún idéntica y varios fragmentos mecánicos: **es un parte disponible y más controlado, no un original periodístico terminado**. Las referencias energéticas a Reuters son demasiado generales frente al titular de importaciones del paquete; el seguimiento de seguridad contiene formulaciones interpretativas que necesitan lectura de las fuentes completas. Por ello no se certifica la exactitud semántica de cada frase ni se habilita indexación/publicidad. La vista elimina una repetición exacta de la entradilla cuando existe; no suprime afirmaciones distintas. Antes de promover una edición a original, concretar cada atribución y aportar análisis propio comprobable. No se ha registrado ninguna aprobación editorial en `editorial-reviews.json`.

La vista final incluye la selección completa de referencias (máximo 40), evitando que el corte previo de diez enlaces oculte una noticia usada en el paquete. Las tarjetas de sección priorizan titulares factuales y excluyen los analíticos; estos siguen identificados como análisis en la lista completa. La vista de prueba se ha reconstruido sobre la instantánea original y se ha comprobado de nuevo su hash, sin otra llamada al modelo.

Para generar y revisar sin publicar:

```sh
python pilot_gemini_phase1.py --output /ruta/fuera-del-repo/informe.json --preview-dir /ruta/fuera-del-repo/preview
```

La clave se configura como secreto de Actions o variable de entorno; nunca en argumentos, HTML o archivos versionados. Si falta, la prueba indica que no puede comprobar Gemini. No se disfraza el fallback como una salida del modelo.

Para un **original nuevo**, crear el HTML con `content-kind=original-draft` y `robots=noindex,follow`. Tras revisar hechos, derechos y aportación propia, añadir en `editorial-reviews.json`, bajo la ruta del HTML, un registro con `kind` (`original_analysis` o `reviewed_article`), `reviewer`, `reviewed_at` con zona horaria, `facts_checked`, `rights_checked`, `approved`, `original_contribution` (al menos 80 caracteres), `sources` (dos URLs HTTPS distintas presentes en el documento) y `sha256` del archivo UTF-8 exacto. La compilación verifica estos campos antes de transformar el HTML. Una edición posterior invalida la revisión. Sin registro válido, conserva noindex. **Una revisión nunca desbloquea un parte automático**. Los originales existentes conservan su política; esta puerta se aplica a borradores nuevos marcados, no certifica retrospectivamente el catálogo.

## D. Crecimiento y medición

La exploración de búsquedas públicas confirma competencia en estado/abierto/cerrado y contexto España/GNL; no aporta volumen, cuota ni posición fiable del proyecto. Priorizar mejoras en páginas existentes, sin crear variantes para cada keyword:

1. Estado actual: portada con tiempos, límites y fuentes; revisar cobertura y CTR en Search Console.
2. Tránsito de petroleros: fortalecer la guía de verificación y el artículo sobre abierto con tráfico reducido, incorporando únicamente series con permiso y metodología.
3. Energía, rutas y Catar: actualizar las comparativas existentes con documentos primarios fechados y cálculos reproducibles.
4. España y Europa: una actualización sustancial del artículo actual con datos de CORES, Enagás, Eurostat y fuentes regulatorias pertinentes; nunca convertir un titular en una cifra de suministro.
5. Fidelización: RSS de cambios y del diario ES/EN, enlaces de contexto y widget fechado. No se implantan cuentas, boletines ni recogida de datos personales.

Se conserva el noindex del contenido automático. Google pide valor para el lector y puede considerar abusiva la generación masiva sin aportación propia. [Google Search: IA y contenido](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content).

No se detectó un beacon de analítica en el HTML público comprobado. No hay acceso a informes de Search Console, AdSense o Cloudflare; no se inventan visitantes, CTR ni ingresos. Propuesta sencilla: Search Console para búsquedas/clics/CTR; Cloudflare Web Analytics para páginas, visitantes, procedencias y rendimiento agregado, tras revisar configuración y transparencia. Cloudflare documenta una opción gratuita sin cambiar DNS ni activar su proxy. [Documentación](https://developers.cloudflare.com/web-analytics/about/).

| Métrica | Fuente y límite |
|---|---|
| Visitantes, páginas y procedencias | Analítica agregada; registrar periodo, definición y cobertura. |
| Búsquedas, clics y CTR | Search Console, por URL/consulta/país, ventanas de 28 y 90 días. |
| Visitas recurrentes | No prometer identificación fiable con analítica sin identificadores persistentes. Si es imprescindible, diseñar una medición consentida antes de implementarla. |
| Suscripciones | RSS no acredita número de personas suscritas; las peticiones pueden incluir lectores, cachés y bots. No equipararlas a usuarios. |
| Ingresos y RPM | Informes reales de AdSense y contratos/facturas de patrocinios. |

Un boletín requeriría responsable identificado, información del tratamiento, finalidad, base jurídica, proveedor/encargo, conservación, baja y consentimiento cuando corresponda. No se presume que toda herramienta «sin cookies» esté exenta por su nombre. [Guía de medición de audiencia de la AEPD](https://www.aepd.es/guias/guia-cookies-analiticas-externas.pdf).

## E. Monetización

Verificado: ads.txt y meta de cuenta presentes; páginas de privacidad/cookies/contacto/política editorial disponibles; anuncios excluidos en partes y utilidades; promoción propia etiquetada. No verificado: titular completo, funcionamiento del correo, motivo exacto del rechazo, estado de cuenta, configuración CMP, consentimiento real por región/dispositivo y calidad editorial global. Google exige contenido útil/original y revisión de cuenta; [preparación del sitio](https://support.google.com/adsense/answer/7299563), [estado Ready](https://support.google.com/adsense/answer/12131223), [CMP certificada para anuncios personalizados en EEE, Reino Unido y Suiza](https://support.google.com/adsense/answer/13554116).

El media kit incorpora una oferta de piloto de cuatro semanas en análisis original, alcance y medición pactados, sin prometer audiencia o cobertura favorable. Logística, navieras, energía, comercio, formación y riesgo son sectores de prospección; no se ha contactado a ninguna empresa. Los patrocinios deben llevar identificación visible y `rel=sponsored` en enlaces comerciales; no compran conclusiones ni acceso a lectores.

Modelo ilustrativo mensual — **supuestos de planificación, no audiencia ni tarifas de mercado verificadas**:

| Escenario hipotético | Páginas vistas | RPM neto de publicidad supuesto | Anuncios | Patrocinios vendidos supuestos | Ingreso total antes de costes e impuestos |
|---|---:|---:|---:|---:|---:|
| Inicial | 5.000 | 1 € | 5 € | 0 | 5 € |
| Desarrollo | 25.000 | 2 € | 50 € | 1 × 100 € | 150 € |
| Consolidación | 100.000 | 4 € | 400 € | 2 × 300 € | 1.000 € |

Fórmula: páginas/1.000 × RPM + patrocinios. Restar dominio, herramientas, producción, comisiones y horas editoriales valoradas a un coste explícito; esos costes reales no están disponibles. El tráfico de partes no monetizables no se suma al inventario publicitario. Medir RPM sobre páginas elegibles, cobertura real y consentimiento. Sin aprobación o inventario servido, el componente AdSense es cero. Vender un patrocinio tampoco está garantizado. Priorizar aportación editorial y patrocinio selectivo; los anuncios programáticos son complementarios.

## F. Validación y límites

La línea base superó 315 pruebas Python (18 de montaje opcional omitidas por dependencias) y 23 JavaScript. El cierre de esta rama añade contratos de publicación, revisión, RSS, metadata y guardas. CI incluye ahora también las 20 pruebas de `tests/`, antes fuera del descubrimiento de raíz. Los resultados finales y logs acompañan la entrega.

Cierre local tras incorporar la actualización de `main`: 344 pruebas descubiertas en raíz (326 superadas, 18 omitidas del montaje opcional), otras 20 Python superadas y 23 JavaScript superadas; cero fallos. Compilación y enlaces internos sin errores. Validador fuente: cero errores y diez avisos; auditoría del HTML público: cero errores y nueve avisos. La diferencia es la comprobación agregada de duplicados activo/archivo, solo presente en la fuente. `_site`: 203 archivos, 169 HTML, 74 páginas indexables, cero huérfanas indexables, cero hreflang bilingües pendientes, cero errores de sitemap, cero cargadores de anuncios y cero JSON internos publicados. No se detectaron patrones de credenciales en el texto examinado. La revalidación offline conserva el hash del piloto y supera cinco comprobaciones adicionales, incluida una inyección sintética de cambio de estado y cifra inventada que se sustituye por fallback antes de validar el conjunto.

Se validan HTML analizable, IDs, JSON-LD, enlaces internos, canonical, hreflang, robots, sitemap y ausencia de internos en `_site`. No equivale a certificación W3C, auditoría WCAG completa ni prueba de cada enlace externo. Las advertencias del HTML de verificación Google y de widgets sin h1 se distinguen de páginas editoriales. La duplicación fuente de seis evidencias entre activo/archivo se conserva por retención y se deduplica en la salida pública.

La inspección visual cubre escritorio y un viewport de 390 px; se ha comprobado apertura del menú. No se dispone de CrUX/Search Console para Core Web Vitals de campo. Los tiempos de una petición HTTP de auditoría no se presentan como LCP, INP o CLS ni como una puntuación Lighthouse. El radar sigue cargando bajo acción del lector. No se añaden solicitudes de analítica.

## G. Autorización para producción

Revisar la PR y la edición de prueba; después autorizar expresamente fusión y despliegue. Al fusionar, `deploy-public.yml` puede publicar automáticamente: ambos pasos deben autorizarse juntos. La PR #18 permanece abierta y sin fusionar; esta rama incorpora sus ideas útiles y amplía las correcciones, por lo que conviene decidir cuál conservar antes de fusionar cualquiera.

La publicación técnica puede mantener anuncios apagados. Activarlos requiere antes verificar titular, cuenta, mensaje CMP y comportamiento real; solo entonces registrar las cuatro comprobaciones en `monetization.json`. Para cambiar visibilidad del repositorio, activar analítica, implantar boletín o modificar Cloudflare se necesita una decisión aparte sobre alcance, datos y costes. No se ha realizado ninguna de esas acciones externas.
