# Preparación de monetización: dependencias y autorizaciones

> **Estado posterior — 28/10/2026:** las tres investigaciones ES/EN están publicadas (PR #22–#24) y la entrega de la PR #25 se ha verificado por HTTP. La recepción de `contacto@estrechoormuz.com` está confirmada por declaración del titular; el envío con identidad del dominio sigue sin comprobarse. Hay acceso a rendimiento y metadatos históricos de Search Console y una instantánea global de Page Indexing aportada por el titular el 28/10/2026 (61 indexadas, 62 sin indexar); el estado individual de las seis investigaciones y URL Inspection siguen pendientes. Los recuentos, dependencias y propuestas fechados en este documento son historial. Prevalece [la auditoría actual](PREFLIGHT_ADSENSE_2026-10-28.md); no acredita aprobación AdSense ni cumplimiento legal completo.

24/10/2026. Trabajo en las ramas de PR #20 y #21. Ambas se mantienen en borrador, abiertas y sin fusionar en main. No se despliega desde esta tarea ni se activa publicidad o solicita revisión de AdSense. PR #19 ya estaba fusionada; PR #18 permanece independiente.

## Integración

PR #20 incorpora main 6b89924d sin conflictos de contenido; conserva las actualizaciones automáticas. Incluye CI de construcción y enlaces. [Comprobaciones específicas](PR20_SINCRONIZACION_2026-10-24.md).

PR #21 incorpora la rama actualizada de #20. Los conflictos fueron los dos workflows: en el CI se conservó la construcción, enlaces y ads.txt; en el piloto Gemini se mantuvo el filtro de los cinco archivos editoriales, equivalente entre ambas ramas. No se ejecuta el piloto real ni se consumen APIs en esta tarea. Las correcciones de idioma, anclas y feeds se comprueban en el artefacto combinado. Integrar ramas no equivale a autorizar la fusión de una PR en main.

## Validación actual y límites externos

PR #20: 354 pruebas Python aprobadas y 18 opcionales omitidas; 20 de mantenimiento y 23 JavaScript aprobadas. CI 40092093606 aprobado sobre 81f43479, incluyendo construcción y enlaces.

PR #21 combinada: 385 pruebas Python, 367 aprobadas y 18 opcionales omitidas; 20 de mantenimiento y 23 JavaScript aprobadas. Compilación, construcción, enlaces y ads.txt local sin errores. Fuente: cero errores y diez avisos conocidos. Auditoría adicional: 170 HTML, 56 URLs en sitemap, 113 HTML noindex y una página mínima de verificación; canonical/hreflang recíprocos, JSON-LD y recursos comprobados. Se retiran alternates falsos de la 404, que apuntaban a una portada como si fuese traducción. Ningún archivo interno, borrador legal, marcador pendiente o cargador publicitario aparece en el artefacto. Los datos, motor y configuración de monetización coinciden con main. Las seis versiones originales cargan sus gráficos, sin scripts ni desbordamiento observado en navegador.

RSS: 50 destinos con ancla de historial; 30 ediciones históricas por idioma; feed auxiliar vacío mientras no haya HTML fechado. ads.txt se vuelve a comprobar por HTTP real, redirecciones, robots y TLS: formato e ID coherentes; no acredita estado de cuenta. No se demuestra acceso desde IPs reales de Google.

**Límite externo:** las dos rutas UKMTO corregidas devuelven actualmente HTTP 403 de Cloudflare desde este entorno (24/10/2026, 12:36 UTC). Se conservan los destinos oficiales identificados y comprobados previamente, pero no se afirma accesibilidad actual universal ni se sortea el bloqueo. Hace falta comprobación manual de ambos enlaces. Los siete bloqueos/errores externos documentados en la auditoría anterior tampoco se convierten en enlaces aprobados por pasar el comprobador interno. Esta limitación no es un fallo de anclas o recursos del artefacto.

## Indexación y originales

Se revisan [las 32 URLs individualmente](REVISION_32_URLS_2026-10-24.md), comparando 74 URLs del artefacto de #20 con las 42 de la propuesta anterior. Se restauran 14 útiles: diez de documentación/herramienta y cuatro guías de contexto. La propuesta queda en 56 URLs; 18 conservan noindex con fundamento y condición de revisión. **Todas las decisiones SEO son provisionales sin Search Console.** No se elimina ni redirige ninguna página y no se presume tráfico cero. Los recursos documentales siguen sin anuncios aunque sean indexables.

[Expediente de los tres originales ES/EN](../drafts/adsense-20261024/REVISION_FINAL.md): fuentes, localizadores, CSV, fórmulas, seis gráficos y huellas de versión. Se corrige la unidad de Eurostat —valor comercial, no volumen físico— y se expone una discrepancia entre las presentaciones de Enagás sin inventar su causa. Conserva períodos históricos; no son mediciones AIS propias ni situación actual. La validación técnica no constituye aprobación editorial o de derechos. editorial-reviews.json sigue vacío.

## Datos legales, contacto y AdSense

No se han recibido ni publicado nombre legal, NIF, domicilio privado, teléfono o destino del reenvío. Las plantillas contienen marcadores y están excluidas de Pages; el repositorio es público, por lo que cualquier dato real se completará fuera de Git. No se atribuyen revisión jurídica ni identidad completa a esas plantillas.

[Opciones de correo y pruebas pendientes](CORREO_OPCIONES_2026-10-24.md). No se han enviado correos ni configurado servicios. La confirmación del ID por el propietario y el HTTP de ads.txt se distinguen del acceso a AdSense. account_ready, cmp_verified, publisher_identity_complete y enabled permanecen en false. También se corrigen las frases comerciales ES/EN que aún afirmaban una CMP activa o revisión de cuenta confirmada.

## Decisiones que requieren autorización expresa

| Decisión concreta | Resultado preparado para revisar | Qué no autoriza por sí sola |
|---|---|---|
| Fusionar PR #20 y permitir el despliegue asociado, si procede | Navegación, RSS y enlaces; rama sincronizada y pruebas repetidas. | Fusionar #21, publicar originales o activar anuncios. |
| Fusionar PR #21 y permitir el despliegue asociado, si procede | Integración de #20, controles técnicos, 32 decisiones SEO provisionales y transparencia. Recomendación de orden: #20 primero y #21 después. | Publicar los borradores, revelar datos privados, solicitar AdSense o encender publicidad. #21 incluye técnicamente los cambios de #20; no debe usarse para saltarse esa aprobación. |
| Aprobar cada original, con su traducción y derechos | Seis HTML y manifest de huellas; elección editorial explícita de publicar la discrepancia de Enagás o esperar reconciliación. | Aprobar otro original, otra versión o cualquier anuncio. La firma y fecha deben ser reales y autorizadas; no se registran aquí. |
| Publicar las versiones finales de los originales | Definir rutas, enlazado, canonical/hreflang y revisar los HTML públicos exactos antes de la aprobación final. | Convertir automáticamente los borradores actuales en páginas indexables. |
| Publicar datos legales concretos | Determinar campos exigibles, dirección válida y datos exactos que el titular autoriza, fuera del repositorio hasta esa decisión. | Publicar copia del DNI/NIE, dirección privada de reenvío, teléfono o capturas de cuenta. |
| Configurar correo o contratar un proveedor, si fuese necesario | Recepción confirmada por declaración del titular el 28/10/2026; envío con identidad del dominio y operación de respuesta pendientes. | Enviar mensajes a terceros, cambiar todos los registros DNS o incurrir en costes sin alcance y autorización. |
| Solicitar revisión de AdSense, en una fase posterior | Comprobar cuenta, rastreo de ads.txt, contenido aprobado y publicado, identidad y requisitos de Google. | Activar anuncios. No se recomienda solicitarla todavía. |
| Activar publicidad, en una fase posterior | Cuenta, CMP/consentimiento, identidad y ubicaciones verificadas y autorización expresa. | Interpretar el ID configurado o una puntuación local como aprobación de Google. |

Para revisar SEO con evidencia externa, hace falta acceso o exportaciones de Search Console: rendimiento por URL/consulta, indexación e inspección de páginas relevantes, con fechas y canonical. Las comprobaciones técnicas de rama y la ausencia de datos de cuenta deben figurar separadas en la entrega; no se atribuyen cambios orgánicos que aún no se han medido.
