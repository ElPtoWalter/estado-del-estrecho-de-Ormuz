# Presentación, SEO y preparación comercial

Propuesta dependiente de P0 y P1. No es una autorización de publicación, de anuncios o de solicitud a Google.

## Cambios demostrables

La portada de referencia repite estado, resumen, confianza y dimensiones en dos bloques. En la medición inicial, la página española mide 15.831 px de alto a 390 px de ancho. La propuesta deja un único veredicto visible, mantiene el desglose V7 desplegable con teclado, coloca los cambios recientes antes de las evidencias y sitúa el diario fechado antes de las tres investigaciones.

El alcance sigue visible como «Sin recuento AIS propio» y puede ampliarse. No se añade una medición marítima, un estado nuevo o una promesa de tiempo real. Se mantienen los enlaces y fragmentos existentes. Los antiguos registros del motor anterior se conservan en el historial bajo su identificación propia.

Lighthouse encontró un enlace sin nombre accesible en el logotipo del pie y un nombre que no incluía todo el texto visible en escritorio. Los logotipos referencian ahora su propio texto mediante aria-labelledby, incluso cuando el texto se oculta visualmente en móvil. Los enlaces que ya tienen una etiqueta personalizada se conservan.

CSS limitado a la portada para compactar tarjetas, dimensiones, fechas y controles. No se modifican los cuerpos, datos, CSV, gráficos ni metodologías de las investigaciones aprobadas.

## Mediciones reproducibles

Herramientas: Lighthouse 13.6.0 y Chrome 158.0.8127.36, Windows; artefactos servidos en localhost. Perfiles predeterminados móvil y desktop, misma máquina, sin activar el mapa externo. Una ejecución por idioma y perfil, con informes JSON completos conservados localmente; las repeticiones intermedias de desarrollo no se presentan como versión final.

| Portada final | Rendimiento móvil | Accesibilidad móvil | Rendimiento escritorio | Accesibilidad escritorio |
|---|---:|---:|---:|---:|
| ES | 98 | 100 | 100 | 100 |
| EN | 98 | 100 | 100 | 100 |

Buenas prácticas y SEO automatizado: 100 en los cuatro ensayos. El resultado no certifica conformidad total WCAG, calidad editorial ni posicionamiento. Los informes finales no detectan los dos fallos de nombre accesible anteriores.

No son Core Web Vitals de usuarios reales ni una estimación de INP. No se confunde TBT de laboratorio con INP. La consulta pública de PageSpeed respondió HTTP 429; no se inventa una evaluación CrUX ni se atribuye el rechazo a una cuota de la cuenta del titular.

### Radar: incidencia adicional confirmada

En una prueba real, el script de MyShipTracking respondió 200, su visor redirigió y el documento final respondió 500. La interfaz anterior anunciaba «Radar AIS cargado» igualmente. Se sustituye esa afirmación por la inserción observable del visor y una alternativa visible de MarineTraffic. El evento load de un iframe externo no acredita su disponibilidad ni cobertura. Un límite de 15 segundos evita dejar indefinidamente esperando un script que no responde; los errores y la falta de iframe permiten reintentar.

Seis pruebas JavaScript cubren carga voluntaria, duplicados, inserción sin afirmar disponibilidad, error, falta de iframe, espera agotada y equivalencia inglesa. El fallo externo no se declara resuelto; no se extraen recuentos AIS ni se modifica la clasificación del monitor.

Referencia: [Web Vitals y diferencia entre campo y laboratorio](https://web.dev/articles/vitals), [Lighthouse oficial](https://github.com/GoogleChrome/lighthouse).

## SEO e indexación

El sitemap fuente conserva 112 URL. El generado en el artefacto y el obtenido por HTTP contienen 62 en esta auditoría. Son tres evidencias distintas; ninguna acredita el número indexado.

Las seis versiones ES/EN de investigaciones conservan canonical, hreflang, indexabilidad autorizada, firma y navegación. Sus metodologías y archivo tabular mantienen noindex. No se modifica la política del diario ni se envían sitemaps o solicitudes de indexación.

La instantánea de Search Console del 28/10/2026 es histórica, no un diagnóstico de hoy. Para seguimiento actual: exportación privada o consulta autorizada de Page Indexing/URL Inspection, con fecha, URL, canonical seleccionado, rastreo y motivo; conservar resultados fuera de Git. Comparar 28 días completos con los 28 anteriores, con iguales filtros, sin atribuir crecimiento a investigaciones publicadas después del período observado.

Hipótesis comprobables: lectura más rápida del estado en móvil; menos repeticiones visibles; acceso conservado al detalle y mayor localización del diario/investigaciones. Verificar con tareas de usuarios o métricas consentidas futuras. No se afirma aumento de CTR, tráfico o ingresos.

## Monetización: límites y pasos

ads.txt respondió HTTP 200 y contiene pub-1713078636060241, igual que la configuración. Esta coincidencia no confirma la aprobación ni el estado de la cuenta AdSense. Los cuatro permisos de monetización siguen en false, y ready_for_resubmission sigue en false.

| Paso | Evidencia o decisión necesaria | Acción actual |
|---|---|---|
| AdSense | Estado vigente en la cuenta, titularidad, dominio y resolución del rechazo | No se accede ni se solicita revisión |
| Identificación legal | Datos reales y domicilio lícito valorados con el titular/profesional | No se publican ni se añaden datos personales a Git |
| Privacidad/cookies | Inventario real de proveedores, bases y conservación, especialmente antes de captación o publicidad | No se instala seguimiento ni se declara cumplimiento completo |
| CMP | Elección y prueba de una CMP certificada, TCF y configuración adecuada al tráfico del EEE/Reino Unido/Suiza | Sin instalación ni scripts publicitarios |
| Correo | Recepción confirmada por declaración del titular; envío con identidad de dominio todavía no probado | Sin mensajes ni cambios DNS |
| Avisos | Canales y recibos reales, con autorización de prueba separada | Solo pruebas simuladas |

La [LSSI, artículo 10](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758#a10) y el [deber de información de la AEPD](https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-de-informacion) requieren resolver la identificación y responsabilidad aplicables. No se sustituye al titular por una organización ficticia ni se inventa un domicilio. La firma institucional de los artículos no resuelve por sí sola esos requisitos.

Google exige contenido propio y políticas cumplidas; una mejora técnica no garantiza aprobación. La CMP certificada tampoco constituye certificación jurídica completa. Referencias: [requisitos AdSense](https://support.google.com/adsense/answer/9724?hl=es), [consentimiento y CMP](https://support.google.com/adsense/answer/13554116?hl=es).

Secuencia comercial propuesta, sin activar nada:

1. Resolver actualización y confianza editorial antes de vender inventario.
2. Patrocinio contextual identificado de una sección o informe, con contrato y separación editorial; sin influencia sobre estados o conclusiones.
3. Espacios de transporte/energía con creatividad revisada y medición mínima autorizada; ninguna cifra de audiencia futura inventada.
4. Newsletter especializada, solo después de decidir proveedor, privacidad, consentimiento y bajas; no se crea formulario.
5. Informes o herramientas premium tras validar demanda y alcance. No vender AIS propio inexistente ni presentar el monitor como asesoramiento de navegación.
6. Publicidad programática únicamente después de cierre legal/CMP/cuenta y autorización expresa. No se solicita revisión de AdSense en esta propuesta.

## Despliegue y reversión

Revisar las comparativas y la CI del commit exacto, después de P0 y P1. Publicar solo con autorización. Tras la publicación autorizada, repetir HTTP, identidad del artefacto, tamaños móviles y recursos sellados. Para revertir la presentación basta revertir esta PR, manteniendo las reparaciones de actualización/seguridad y los históricos nuevos; no restaurar archivos operativos antiguos.
