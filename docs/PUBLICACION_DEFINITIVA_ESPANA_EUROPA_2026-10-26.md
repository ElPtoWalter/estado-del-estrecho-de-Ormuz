# Versión definitiva para autorización separada de publicación — PR #24

El titular aprobó el conjunto exacto del candidato `21123ca1a6737aa3809359946ae3d7224e67c74f`: artículos ES/EN, datos, CSV, ocho gráficos, fuentes y conclusiones, con firma institucional **Estrecho Ormuz**. La [referencia real de aprobación](https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/24#pullrequestreview-5649321245) acepta la discrepancia Enagás como documental y no resuelta, junto con la atribución limitada de hechos numéricos y representaciones propias. No permite nuevas cifras, reescrituras de hechos, permisos generales de reutilización o una afirmación de autorización jurídica externa.

La cabecera de la decisión indica 25/10/2026; GitHub registra la evidencia el 26/10/2026 a las 08:38:42 UTC. Se conservan ambas referencias con su significado. La web dice que la aprobación quedó **registrada** el 26/10/2026; no inventa una hora de revisión personal. No se registra nombre de revisor, nuevas comprobaciones estadísticas o revisión jurídica independiente.

Solo se autoriza preparar esta versión. Merge, despliegue, publicidad, solicitud de revisión AdSense y publicación de datos personales siguen sin autorizarse. La PR continúa en borrador. Se incorpora la sincronización del titular `6811fedf8551fe0da29ebbfd76443dc4f6f03c45`, que contiene main `e96145faadd8d164e5a8236da487345a9f13ddb1` y sus actualizaciones automáticas. Si main avanza, debe integrarse y repetirse CI antes de presentar otro commit para publicar.

## Selección pública exacta

| Ruta | Política |
|---|---|
| `/espana-europa-ormuz-dos-porcentajes.html` | Artículo ES indexable, firma Estrecho Ormuz |
| `/en-spain-europe-hormuz-two-percentages.html` | Artículo EN indexable, firma Estrecho Ormuz |
| `/metodo-espana-europa-20261025.html` | Metodología ES accesible con `noindex,follow` |
| `/en-spain-europe-method-20261025.html` | Metodología EN accesible con `noindex,follow` |
| `/assets/research/spain-europe-20261025/source-inputs.csv` | Seis entradas con unidades, período, URL y localizador, intactas |
| `/assets/research/spain-europe-20261025/calculations.csv` | Ocho resultados Decimal y fórmulas explicadas, intactos |
| Ocho SVG y `spain-editorial.css` en el mismo directorio | Figuras ES/EN, móvil/escritorio, y diseño aprobados, intactos |

Hay canonical propios, hreflang ES/EN/x-default recíprocos y enlaces de idioma correctos. Solo los dos artículos se añaden al sitemap: 60 → 62 URLs en la construcción comprobada. Las metodologías quedan fuera. La navegación entrante se integra en portada, análisis y hemeroteca ES/EN. Los enlaces originales a Enagás, Eurostat, AIE y los dos análisis publicados se conservan.

## Únicos cambios sobre el contenido aprobado

El cuerpo completo comprendido entre `<article>` y `</article>` permanece idéntico, sin cambiar una palabra, cifra, tabla, fuente, enlace, conclusión o interpretación. Los dos CSV, los ocho SVG y la CSS conservan sus bytes originales. No se recalculan versiones nuevas ni se actualizan silenciosamente las fuentes fechadas en el candidato.

La presentación cambia la firma prevista por la institucional, incorpora el metadato de autor y sustituye los avisos de borrador por una declaración de asistencia de IA y alcance histórico. Se añade la referencia pública a la fecha real de registro de aprobación. Se aplica indexación a los artículos y se conserva noindex en las metodologías.

En los métodos solo se actualiza el estado editorial y la presentación de la aceptación limitada de reutilización. La revisión ya no aparece pendiente de decisión del titular. Se mantiene expresamente que esa aceptación no acredita permiso específico de Enagás ni revisión jurídica independiente. La explicación de la discrepancia, todas las fórmulas y los límites anteriores a la sección de derechos permanecen idénticos. No se afirma una causa de la diferencia, una conciliación de SL-ATR o comprobaciones nuevas atribuidas al titular.

No se incluyen operaciones internas de GitHub en el texto que leerá el público. El expediente y la separación de permisos quedan en esta documentación interna.

## Registro y construcción segura

El manifest original conserva `human_editorial_approval: null`, como fotografía del estado previo a decisión. Su SHA-256 normalizado a LF es `40eb03ae1fc277a1d5bca6dcf1ab7cb946eca4da9d23ce11d83767f0dfd06f4d`. No se resella el candidato para simular una aprobación anterior.

`docs/spain-release-20261026.json` documenta por separado la decisión real y sus límites. Cuatro registros de `editorial-reviews.json` vinculan los HTML a esa única decisión sobre el conjunto aprobado, con huellas originales y referencia exacta. No se añaden campos de revisor, `facts_checked`, `rights_checked` o `reviewed_at`. Las decisiones de los dos análisis anteriores permanecen intactas.

`spain_release.py` comprueba manifest, generadores originales, las quince huellas y la aprobación antes de seleccionar recursos. El constructor genera `_site` mediante transformación condicionada y después audita bytes finales, cuerpo intacto, indexación, enlaces, canonical, hreflang, sitemap, límites jurídicos y publicidad. Una aprobación parcial, ajena a la ruta, basada en otra revisión o sobre bytes alterados bloquea la construcción. Las tres publicaciones tienen controles independientes.

Las cuatro páginas bloquean anuncios incluso si posteriormente se autorizasen en otro lugar. Los permisos globales de monetización siguen apagados. No se confirma una cuenta AdSense por su ID ni se publica información personal. JSON internos, generadores Python, configuración y expedientes no se copian a Pages.

El artefacto de CI del sitio normal contiene la selección definitiva comprobada; no ejecuta un despliegue. La antigua orden `spain_editorial.py --build-preview` se conserva solo como registro del procedimiento previo a aprobación, y se retira del flujo actual de CI. La orden `--check` sigue comprobando aquel candidato original.

## Validación de esta preparación

- Construcción final: 249 archivos, con quince recursos nuevos. Solo cambian siete archivos previos del artefacto: seis páginas de navegación y sitemap. Los demás 227 archivos previos conservan sus huellas LF, incluidos los recursos de las dos publicaciones anteriores.
- Sitemap: 62 URLs, con los dos artículos y sin los métodos. Enlaces, privacidad y anuncios: cero errores. El validador de fuente mantiene diez avisos existentes sobre duplicados de evidencias, widgets y el archivo de verificación de propiedad; no corresponden a estas páginas.
- Local: 456 pruebas Python (455 correctas y una omisión opcional de vídeo), 20 mantenimiento y 23 JavaScript correctas. Se compilan 103 archivos Python. Las diez regresiones nuevas comprueban aprobación exacta, fechas, rutas, cuerpo y descargas idénticos, cautela legal, noindex y anuncios, navegación y comprobación remota futura.
- 36 comprobaciones HTTP: quince recursos finales locales 200 con bytes esperados, diez rutas privadas 404, siete fuentes oficiales 200 y cuatro enlaces a análisis publicados 200. Los PDF y XLSX oficiales consultados mantienen las huellas binarias documentadas en el candidato aprobado; no se afirma una nueva revisión jurídica o humana por comprobar su entrega.
- 33 fuentes originales del candidato permanecen intactas, excluida únicamente la nota histórica añadida al README. Diez archivos protegidos de datos, automatización y monetización coinciden con main. Las nueve entradas anteriores del registro editorial no cambian.
- Cuatro páginas a 320/390/1280 px: doce casos sin desbordamiento horizontal, dos descargas claras por página, encabezados, tablas con regiones de teclado, alternativas textuales, byline institucional y estados de indexación correctos. Ocho vistas de gráficos inspeccionadas. Esto no se presenta como certificación completa WCAG o prueba de lector de pantalla.

```text
python -m unittest discover -v
python -m unittest discover -s tests -v
node --test test_public_ui.cjs test_own_projects.cjs
python spain_editorial.py --check
python spain_release.py --check
python build_public_site.py
python check_public_links.py _site
python adsense_checks.py --root _site
python validate_site.py
```

`drafts/spain-europe-20261025/release-build-audit.json` conserva huellas de recursos finales y artefacto completo; es evidencia local excluida de Pages. El workflow queda preparado para ejecutar `remote_smoke_test.py --history-release --energy-release --spain-release` después de un despliegue futuro autorizado. Esa comprobación futura de producción no se ha realizado ahora. El commit definitivo, enlace a CI y pruebas descargables se entregan en el informe final de esta conversación.
