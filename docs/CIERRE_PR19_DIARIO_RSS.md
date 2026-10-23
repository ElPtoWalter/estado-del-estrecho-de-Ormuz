# PR #19 · revisión del diario, RSS y publicidad

23 de octubre de 2026. Continuación de la auditoría inicial, conservada como registro histórico. No se ha fusionado ninguna PR ni se ha desplegado esta rama.

## Cambios editoriales

El primer borrador repetía el diagnóstico y sus límites en la entradilla, el desarrollo, las tarjetas y la conclusión. Además, un nombre de medio válido no demostraba que la frase describiera realmente su titular. La revisión elimina el anclaje al texto completo del fallback y asigna una función distinta a cada campo: ángulo informativo, referencias fechadas, estado documentado, noticias concretas, contexto y comprobaciones pendientes. Las tarjetas que volvían a explicar lo mismo se retiran de las próximas ediciones.

El diario conserva el estado canónico y los identificadores de eventos y fuentes. El paquete de redacción conserva metadatos de verificación de los eventos, pero deja fuera sus titulares y fechas históricas: las noticias de esta edición proceden de la selección fechada. El piloto incluye ahora las evidencias recientes del monitor y compara las referencias con las ya vistas, igual que el flujo de producción. No se convierte un titular o una declaración en confirmación independiente.

La selección para la redacción principal exige prioridad de fuente 3 o superior según el registro existente; las referencias de menor prioridad se conservan como contexto enlazado. Es una selección editorial, sin cambios de umbrales ni clasificación del monitor. Un vertido se clasifica como asunto marítimo, sin confundirlo con una noticia sobre precios solo porque empiece por «Oil».

La validación mantiene los controles previos y añade procedencia de cifras y fechas por sección, detalles concretos del titular citado, identificación del declarante en las declaraciones detectadas y atribución de noticias de mercados en titular y entradilla. Las equivalencias geográficas se activan solo cuando el mismo lugar está presente, incluida la abreviatura US; no se desarrollan organismos desconocidos por conocimiento del modelo. «Buque cisterna» y “tanker” describen el mismo término suministrado. Estas comprobaciones léxicas no constituyen una prueba semántica exhaustiva.

La entradilla recibe una noticia propia; el desarrollo debe utilizar las otras referencias de ese tema. El editor elige el ángulo de titular respaldado y el esquema lo limita por idioma. En el caso de máximos del petróleo, la opción requiere una referencia nueva, publicada ese día, con la afirmación literal y el medio identificado; en su ausencia se utiliza continuidad operativa. No se fabrica una novedad para satisfacer el estilo. La cronología de publicación y el alcance de verificación se generan como metadatos fiables: el modelo no puede declarar que comprobó avisos o sucesos que solo aparecen en titulares.

El control de estilo detecta también una frase corta repetida dentro de otra más larga. Una única revisión opcional de Gemini corrige esos problemas con el mismo paquete y vuelve a pasar la validación original; conserva los idiomas que ya pasan. Hay como máximo dos llamadas a Gemini por edición, sin tercer intento ni OpenRouter en esa revisión. Usa la integración existente; no se ha contratado otro servicio y estas llamadas consumen su cuota. La extensión corta es un aviso orientativo, no una medida suficiente de profundidad; el umbral factual mínimo no se ha rebajado.

Las restricciones de longitud se comunican en el esquema y sus descripciones y siguen verificándose localmente. Google indica que los límites de longitud de cadenas pueden ignorarse en el servidor; el esquema no sustituye a la validación. [Documentación de salida estructurada](https://ai.google.dev/gemini-api/docs/structured-output).

El fallback permanece disponible. Si se rechaza un fragmento, solo se conserva una sustitución que supera la validación completa bilingüe. El piloto guarda su paquete y su instantánea para poder revalidarlos y reconstruir la vista sin leer datos posteriores ni volver a llamar al modelo. La generación inicial para diagnóstico se distingue de la edición aceptada y nunca se usa para renderizar el diario.

## Contexto primario y derechos

`editorial-context.json` incorpora dos paráfrasis factuales de una publicación EIA del 16/06/2025: el flujo de petróleo de 2024 (unos 20 millones de barriles diarios, aproximadamente el 20% del consumo de líquidos petrolíferos) y una estimación de junio de 2025 sobre rutas alternativas por oleoducto (unos 2,6 millones de barriles diarios). Cada registro lleva URL primaria, período propio, fecha de comprobación, limitación de uso y huella del contenido revisado. Un cambio del texto invalida esa huella. Si falta el contexto o no supera los controles, se omite; no se completa con conocimiento del modelo. La estimación de rutas alternativas no acredita capacidad libre disponible en octubre de 2026.

La EIA permite reutilizar sus productos propios con atribución y fecha, y pide identificar las traducciones. Se citan la fuente y la paráfrasis de Estrecho Ormuz; no se reproducen fotos, logotipos ni el dataset de Vortexa. Los datos históricos no se presentan como mediciones actuales ni como pérdidas de suministro. [Fuente primaria](https://www.eia.gov/todayinenergy/detail.php?id=65504), [condiciones de reutilización](https://www.eia.gov/about/copyrights_reuse.php).

Para ampliar el contexto: incorporar avisos operativos primarios con emisor, URL, fecha del documento y del hecho, ámbito, limitaciones y condiciones de reutilización comprobadas; mantener las declaraciones oficiales como declaraciones cuando no exista contraste. Para datos económicos, conservar período, unidad y metodología. No se ha implantado un raspado indiscriminado de artículos, elusión de paywalls ni reproducción de textos completos de prensa. No se añaden servicios de pago. La revisión de esta ficha por el asistente no acredita revisión humana de cada diario.

## Hemeroteca y RSS

Los feeds ES/EN exigen `/diario/AAAA-MM-DD.html` o `/diary/AAAA-MM-DD.html` y comprueban que el archivo exista. Una instantánea JSON sin HTML histórico se excluye; si falta una traducción, no entra en el feed de ese idioma. Se mantienen identificadores por fecha e idioma para evitar duplicaciones en lectores existentes.

La comprobación del artefacto público valida también esos destinos, `noindex` y ausencia de anuncios en las páginas históricas. Las URLs absolutas del propio dominio se comprueban como enlaces internos. Los HTML históricos y la edición ya publicada se conservan; la muestra de prueba no los reemplaza. La nueva redacción se aplicará en las próximas generaciones autorizadas.

## Qué falta para activar AdSense

Las cuatro opciones de `monetization.json` siguen en `false`:

| Opción | Evidencia externa necesaria antes de cambiarla |
|---|---|
| `account_ready` | Entrar en AdSense, comprobar el dominio y su estado **Ready**, obtener el motivo exacto del rechazo anterior y verificar que no queden restricciones o acciones pendientes aplicables. El informe local, ads.txt y la meta de verificación no prueban aprobación. |
| `publisher_identity_complete` | Aportar y publicar los datos reales del responsable que correspondan, verificar el canal de contacto y revisar la coherencia de aviso legal, privacidad y cookies con el tratamiento y los proveedores efectivos. No se inventan identidades ni domicilios. |
| `cmp_verified` | Elegir/configurar el mensaje y la CMP apropiados; para anuncios personalizados en EEE, Reino Unido y Suiza, verificar CMP certificada y TCF según Google. Probar en móvil/escritorio y las regiones pertinentes: primera visita, aceptación, rechazo y retirada; conservar evidencia de comportamiento y solicitudes reales. La certificación no acredita por sí sola cumplimiento legal completo. |
| `enabled` | Solo después de las tres verificaciones anteriores, revisar ubicaciones elegibles y autorizar expresamente la activación. El cambio debe revisarse y desplegarse de forma separada. |

Los partes automáticos, incluida la hemeroteca, permanecen sin anuncios y sin indexación aunque se active la opción global en el futuro. La promoción propia etiquetada en páginas elegibles es independiente. Se conservan ads.txt y la verificación de propiedad. [Estado del sitio en AdSense](https://support.google.com/adsense/answer/12131223), [requisitos de consentimiento de Google](https://support.google.com/adsense/answer/13554116).

**Diferencia con producción:** la lectura pública del 23/10 sigue encontrando el cargador `adsbygoogle.js` en ambas portadas, mientras el diario público no lo carga. La rama construida tiene cero cargadores. No se ha cambiado producción: retirar allí el script requiere un despliegue autorizado. La aprobación técnica de la PR no debe describirse como publicidad ya apagada en la web existente.

## Sincronización y PR #18

Se incorpora `main` hasta `7e2f06cd1b19dd842b634b22ed0826135e72d50e`, actualización automática de las 18:39 UTC, y se conservan sus datos y páginas. Se ha vuelto a comprobar el diff de la PR #18: sus dos ventanas de recuperación, a las 12:25 y 16:25 UTC, están presentes con idempotencia por fecha; sus instrucciones útiles de estilo, atribución y transparencia quedan incorporadas y ampliadas. Ni la #18 ni la #19 se han fusionado o cerrado.

## Resultados del cierre

La entrega adjunta el resultado real del piloto, su evaluación editorial separada, los logs técnicos y el estado final de GitHub. La aprobación de controles automáticos no se interpreta como originalidad periodística, revisión humana ni aprobación de AdSense.

El [piloto real #58](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/actions/runs/40014302607), de las 19:49:03 UTC, usa `gemini-3.5-flash-lite` y el paquete `0315e09ae34b4e19f75f19b15d3af1732ce781aa19c9af57eb019632e3185557`. Pasan sus nueve controles técnicos con el validador 9. La edición tiene 323 palabras ES y 273 EN según el contador del piloto, sin repeticiones detectadas ni bloqueos de estilo; EN conserva un aviso orientativo de extensión. Hubo dos llamadas y la segunda propuesta no se adoptó. La versión final evita esa llamada extra cuando solo existe el aviso de extensión.

**La revisión editorial detectó un matiz que esos nueve controles no detectaban:** «record high in October» se convirtió en «récord mensual en octubre». No debe interpretarse como equivalencia acreditada. La entrega sustituye únicamente «récord mensual» por «récord» y registra original, cambio y motivo. Es corrección del asistente, no revisión humana. El validador 10 añade una guarda contra ese período comparativo no suministrado: rechaza el texto original y acepta la edición corregida con el mismo paquete. El fallback parcial EN conserva la paráfrasis EIA revisada, después de rechazar una denominación compuesta no admitida. No se ha suavizado ese control para conservar más prosa del modelo.

El piloto en vivo corresponde al validador 9; el cierre revalida localmente con el 10. No se presenta esa revalidación como otra ejecución remota. Se retiró el disparador temporal por push de la rama de desarrollo, evitando más consumo de cuota. Una revisión automática rechazó volver a habilitarlo; el cierre utiliza el piloto ya obtenido y las comprobaciones locales.

Pruebas de cierre: 364 pruebas Python de raíz (18 omisiones por dependencias opcionales de montaje), 20 de mantenimiento y 23 JavaScript; compilación y enlaces del artefacto sin errores. La validación de fuente conserva 10 avisos conocidos: seis evidencias duplicadas entre listas, el archivo de verificación Google y los widgets. No se ocultan ni se presentan como fallos nuevos de redacción.

La recomendación es **fusionable como parte automático, no indexable y con anuncios desactivados**, sujeto a la autorización del propietario. No se recomienda promover este material a original periodístico revisado ni activar publicidad. La muestra es más específica y aporta dos referencias primarias históricas; sigue limitada por el acceso a titulares y no equivale a reporteo independiente. La fusión y el despliegue siguen pendientes.
