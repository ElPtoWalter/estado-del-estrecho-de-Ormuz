# Seguridad, separación y trazabilidad

Propuesta dependiente de la reparación P0. No cambia clasificación, datos operativos, DNS, visibilidad de repositorios, alojamiento, legales o anuncios.

## Comprobaciones y correcciones

- HTTP público inicial: status, history, daily-brief, config, operational-intelligence y health JSON; Python; .git/config; .env; workflows; revisiones y bandeja de avisos: 404 en las rutas comprobadas. No es un rastreo exhaustivo de todas las posibles rutas.
- Se analizaron todos los objetos alcanzables por las referencias Git descargadas: 22.546 blobs, de los que 22.536 eran texto, aproximadamente 1,028 GB sin comprimir. No coincidieron los patrones específicos de tokens GitHub, Google, Telegram, AWS o claves privadas PEM. No se reproducen valores y este análisis no demuestra ausencia absoluta de secretos; no cubre credenciales fuera de patrones ni secretos incrustados en binarios.
- Se fija por SHA completo cada acción oficial ya utilizada en los 25 workflows, conservando su versión. Las referencias se resolvieron el 19/11 con git ls-remote contra los repositorios oficiales. Inventario: actions-pins-20261119.json. Una actualización futura requiere revisar y cambiar esos SHA.
- Python de producción usa biblioteca estándar. Las dependencias opcionales gráficas/vídeo están fijadas por versión, pero no se certifica ausencia de vulnerabilidades ni bloqueo completo por hash. No se instala ni activa el módulo de vídeo.
- La construcción permite ahora únicamente los JS, CSS y XML declarados. Un nuevo archivo con esas extensiones no se publica accidentalmente por aparecer en la raíz.
- El configurador de inserción limita idioma y tema a valores conocidos; el código copiable usa textContent.
- Se mantienen mapas externos bajo acción del lector. No se añade analítica, CMP ni formulario de captación.
- Se contrastó el TAR del último despliegue con la construcción: upload-pages-artifact v5 excluía por defecto .well-known/security.txt. Se habilita su inclusión tras una lista exacta de ocultos autorizados; cualquier otro oculto o enlace simbólico bloquea la auditoría. La CI comprueba los nombres y bytes del TAR de Pages sin desplegar. El contacto ya existe en la fuente y no se modifica.

## Trazabilidad editorial

editorial_evidence_audit.py produce un diagnóstico interno reproducible: relevancia directa o contextual, fecha de publicación, fecha del hecho explícita o desconocida, procedencia primaria/secundaria, duplicados, conflictos ya registrados y ausencia de documentación completa para mediciones de volumen.

Una búsqueda RSS que menciona Ormuz no prueba que cada resultado trate sobre su operatividad. La evaluación inspeccionada incluye una noticia de Yemen cuya relación operativa no queda establecida en el título. Se marca para revisión, sin borrar el registro ni cambiar la clasificación histórica o vigente.

La puerta de publicación rechaza ALTA si los contadores del motor no ofrecen el apoyo mínimo: apertura con dos fuentes de paso o una primaria; cierre con dos fuentes de cierre. Es un control estructural sobre datos del motor, no una verificación independiente de esos contadores ni autorización humana. La revisión contextual sigue siendo necesaria.

Las fechas de publicación no se convierten en fechas de acontecimientos. Un cruce no acredita volumen; sin recuento, referencia y período documentados no se etiqueta una medición como reproducible. Una rectificación debe añadirse con su fuente y fecha; no se reescribe la evidencia original ni se registra una revisión humana ficticia.

## Cabeceras e infraestructura

La respuesta inspeccionada fue de GitHub.com, con HSTS. No se observaron CSP, X-Content-Type-Options ni X-Frame-Options en esa respuesta. No se infiere una cuenta Cloudflare activa a partir del dominio.

GitHub Pages no aplica un archivo _headers. Propuesta para un proxy o alojamiento compatible, pendiente de autorización y ensayo:

- X-Content-Type-Options: nosniff.
- Referrer-Policy: strict-origin-when-cross-origin.
- Permissions-Policy: camera=(), microphone=(), geolocation=().
- CSP inicialmente Report-Only por cabecera HTTP, sin colector externo de informes hasta autorizar el tratamiento de esos datos. Inventariar hashes de los scripts inline y permitir los dominios efectivos del mapa bajo acción del lector; no usar una política ficticiamente estricta con unsafe-inline general como conclusión de auditoría.
- frame-ancestors 'self' para las páginas ordinarias. Excepción deliberada para widget.html y en-widget.html, que deben poder insertarse en otros sitios. No aplicar X-Frame-Options: DENY globalmente.

Report-Only y frame-ancestors no funcionan mediante meta HTML. No se añade una cabecera que Pages ignoraría ni se cambia DNS.

Referencias: [GitHub Actions, uso seguro](https://docs.github.com/en/actions/reference/security/secure-use), [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP), [frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).

## Desarrollo privado y publicación mínima

Opción preparada: repositorio privado para motores, historiales de trabajo y construcción; repositorio público separado que contiene solamente public/ con el artefacto auditado y un workflow de Pages sin motor. prepare_public_handoff.py genera ese esqueleto local, exige destino nuevo y verifica integridad/enlaces antes de copiar. La comparación de hashes prueba la preservación del artefacto, no un despliegue real.

GitHub Pages admite repositorios públicos en GitHub Free; para servir directamente desde uno privado se requiere un plan compatible. Por eso el destino mínimo público conserva una vía viable sin cambiar el plan de Pages. La transferencia automática entre repositorios necesitaría GitHub App o credencial de alcance mínimo, configurada por el titular; GITHUB_TOKEN no concede por sí solo escritura en otro repositorio.

No se cambia la visibilidad del repositorio actual. El código ya publicado puede conservarse en clones e historial; la separación futura no lo vuelve secreto retroactivamente. El frontend necesario seguirá siendo público.

Costes: Pages público puede mantenerse en el plan gratuito aplicable; dominio, proveedor de vigilancia y consumo privado de Actions son partidas separadas. No se conoce el plan ni la factura del titular. El coste de construcción privada se debe calcular con los minutos medidos, el resto de sus repositorios, retención de artefactos y la tarifa de cuenta vigente; no se ofrece una factura o precio mensual ficticio. No se ha contratado ningún servicio.

Referencias: [Disponibilidad de Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [límites de Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

La documentación de [facturación de Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions) mantiene gratuitos los runners estándar en repositorios públicos y distingue el cómputo privado y almacenamiento. No se puede atribuir la falta de ciclos al agotamiento de minutos sin comprobar la cuenta. La página de [límites](https://docs.github.com/en/actions/reference/limits) tampoco demuestra que esta cuenta haya alcanzado alguno.

## Aplicación y reversión

Revisar esta PR después de P0 y repetir CI contra el main vigente. Tras autorización, publicar con el mismo constructor; comprobar que el inventario público conserva investigaciones y recursos. Para revertir, usar un commit inverso de esta PR conservando los registros operativos nuevos. No desactivar exclusiones del artefacto para resolver una incidencia. La separación de repositorios y las cabeceras requieren una autorización distinta.
