# Lenguaje claro · integración local

El generador español produce ahora guiones 1.1.0. El paquete factual 2.0.0,
las decisiones de Fase 1 y los umbrales de verificación no cambian.
Los guiones antiguos 1.0.0 y sus identidades de voz siguen siendo válidos;
la generación inglesa conserva su comportamiento anterior.

## Qué cambia

- Frases cortas, sin relleno de arquitectura ni etiquetas internas.
- Duración estimada a partir de las palabras reales, mínimo 15 segundos y
  mínimo 30 palabras; se conservan los máximos por tipo de vídeo.
- Hechos y declaraciones usan solamente sus propias fuentes.
- OPE y hutíes tienen definiciones documentadas en una lista cerrada,
  separada de las noticias. Sus referencias NO verifican el evento.
- Las cifras conservan su unidad. En una lista de pasajeros, vehículos y
  rotaciones se seleccionan las dos primeras; no se adivina qué mide la
  tercera. Una noticia basada solo en rotaciones queda para revisión.
- Estado, confianza, incertidumbre y vigilancia se derivan del paquete;
  la IA no puede reescribirlos ni elevar su certeza.
- Se omiten novedades administrativas y comparaciones sin respaldo.
- Un término sin explicación, un estado desconocido o una frase demasiado
  larga bloquean el guion antes de llamar al proveedor.
- El fallback local se valida de verdad; no se devuelve un PASS ficticio.
- La entrada de voz 1.1 conserva los tipos de evidencia y referencias de contexto.
  «Hutíes» queda señalado para escucha humana, sin cambiar una palabra por
  «judíes» ni alterar el texto editorial con una pronunciación no aprobada.
- Los gráficos distinguen contexto, hechos, declaraciones e incertidumbre.

## Fuentes de contexto

Definiciones parafraseadas verificadas el 03/10/2026:

- [Operación Paso del Estrecho · Protección Civil](https://www.proteccioncivil.es/coordinacion/campanas/operaci%C3%B3n-paso-del-estrecho).
- [Hutíes · Naciones Unidas](https://www.ungeneva.org/es/news-media/news/2025/10/111947/los-huties-detienen-20-empleados-de-la-onu-en-yemen).

Estas páginas se citan como contexto general; no se incorporan sus noticias,
fechas ni cifras al estado del estrecho.

## Límites y activación

Integración para uso interno, con publicación audiovisual desactivada.
No se han habilitado costes, automatizado publicaciones ni generado voz
con este contrato. El guion 1.1 crea una nueva
identidad: nunca reutilizar un audio si su transcripción no coincide exactamente.

La duración por palabras y el storyboard son estimaciones. Los subtítulos finales
deben alinearse con el audio real, como en el render con alineación de palabras
ya probado; no son sincronización fonética por sí mismos.

Los filtros de cifras, entidades y contradicciones son defensas mecánicas,
no una prueba semántica completa. La revisión editorial, escucha, derechos y
QA audiovisual siguen siendo obligatorios. El campo de revisión humana no
puede aprobarse automáticamente.

Los datos actuales congelados del 03/10/2026 no contienen eventos
CONFIRMED_PRIMARY ni CONFIRMED_MULTI_SOURCE en ninguno de los proyectos.
Resultado correcto: no recomendar vídeo, no generar voz y no publicar.
No se sustituyen por noticias antiguas etiquetadas como actualidad.

Antes de usar un resultado: exigir CI verde y aprobar el guion/audio.
Integrar el cambio sobre main no aprueba ni publica una pieza audiovisual.
El léxico se amplía con una referencia
primaria y pruebas nuevas; nunca con definiciones inventadas por el modelo.
