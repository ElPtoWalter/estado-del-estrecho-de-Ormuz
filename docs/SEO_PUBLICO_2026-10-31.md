# Correcciones de enlaces y superficie pública — 31/10/2026

Cambios sobre main `e5654294a81a02ee8579d9c3659ec2be695fb400`, con las PR #22–#26 y sus actualizaciones operativas posteriores. Preparación para revisión humana: sin merge, despliegue, solicitudes a Google o activación publicitaria.

## Correcciones implementadas

- Ocho páginas aún anunciaban un buzón de correcciones cuya recepción no está confirmada. Sus enlaces y etiquetas visibles pasan a `contacto@estrechoormuz.com`, conservando los asuntos. Incluye política editorial ES/EN y las guías anteriores de economía, rutas y verificación AIS. No se envía correo, cambia DNS o afirma capacidad de responder con identidad del dominio.
- Ocho enlaces contextuales en cuatro guías ES/EN conectan explicaciones ya relacionadas: apertura con derecho de paso y consecuencias económicas; impacto económico con rutas alternativas y seguros. Se enlazan palabras existentes, sin añadir cifras, alterar conclusiones, títulos, fechas o metadatos. La utilidad es facilitar la lectura entre conceptos, no garantizar indexación. Los índices de análisis ya enlazaban las guías.
- El comprobador de enlaces detecta la reaparición del alias no verificado. Las pruebas cubren destinatarios ajenos y enlaces a la versión de idioma correcta.
- README distingue el contrato interno `status.json` de la superficie pública segura.

Las capturas, estados individuales, fechas de rastreo y exportaciones de cuenta no se incorporan a GitHub. El diagnóstico detallado y el plan para el titular se entregan fuera del repositorio.

## Casos sin modificación

### JSON interno del monitor

La petición pública a `/status.json` devuelve **404**, no 200. El fichero fuente existe y contiene JSON válido para sus consumidores internos. El flujo de publicación excluye expresamente `_site/status.json`; las páginas y widgets públicos reciben la edición renderizada en HTML y no necesitan descargar ese archivo. Los scripts originales que lo consumen no se publican como consumidores públicos.

No se declara resuelto por existir en Git ni se expone el JSON para obtener un 200. Se preservan archivo, esquema, consumidores, automatizaciones y reglas de privacidad. Suprimir esta barrera sería un cambio de contrato público y seguridad que no forma parte de esta corrección SEO.

### Ruta antigua de alternativas

`/analysis/alternative-routes` devuelve 404. No se encuentran enlaces internos o referencias vigentes en el sitemap publicado que la anuncien. El artículo español actual responde 200 en `/rutas-alternativas-cierre-estrecho-ormuz-capacidad.html` y está correctamente enlazado.

Se conserva el 404 actual. El despliegue es un artefacto estático construido por Python, no una compilación Jekyll. No se añaden `_redirects`, `.htaccess`, PHP, carpetas arbitrarias o redirecciones JavaScript que pretendan ser una respuesta HTTP 301. Si el titular quiere conservar esa ruta antigua, una regla HTTP exacta hacia el artículo equivalente requiere una capa de alojamiento que realmente la aplique y una comprobación posterior del estado y Location. No se configura infraestructura externa ni se cambia DNS en este encargo.

[GitHub Pages es alojamiento estático](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). [Google distingue redirecciones HTTP de meta refresh y JavaScript](https://developers.google.com/search/docs/crawling-indexing/301-redirects).

### Páginas auxiliares

Se conserva la verificación de propiedad sin alterar su contenido. Los widgets siguen noindex y fuera del sitemap. El estudio social sigue excluido de Pages. El feed continúa siendo Atom XML, no una página HTML. Las páginas de inserción ES/EN conservan su elegibilidad: ofrecen instrucciones, vista previa y código de inserción utilizable, sin solicitar su indexación como prioridad. No se cambia la política del diario.

## Alcance de las comprobaciones

La auditoría separa sitemap fuente, salida `_site`, HTTP público y evidencia de cuenta. Una respuesta 200 o una canonical propia no confirma indexación. Las pruebas en vivo comunicadas por el titular tampoco equivalen a inclusión en el índice. [Inspección de URL](https://support.google.com/webmasters/answer/9012289?hl=es).

La construcción incluye la misma selección de publicaciones. Los tres paquetes de investigaciones ES/EN y sus 46 recursos permanecen sellados. Los hashes completos de artefacto, recursos, motor, fuentes, históricos, datos operativos y permisos se comparan con main. La nueva CI y su artefacto exacto se adjuntan en la PR; no se reutiliza la conclusión de una entrega anterior.

Todos los controles de AdSense y `ready_for_resubmission` permanecen en false. Ninguna identidad privada, dato de cuenta o aprobación editorial ficticia se añade a esta rama.
