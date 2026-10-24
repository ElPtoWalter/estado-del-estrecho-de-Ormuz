# Historiales de Ormuz: nueva versión editorial independiente

Rama desde main 9d6b0cf5, después de las fusiones de #20 y #21 realizadas fuera de esta tarea. Se prepara una nueva PR editorial; no se vuelven a fusionar las anteriores ni se despliega esta edición.

[Artículo completo ES](../drafts/historiales-20261024/historiales-monitor-ormuz.html) · [Complete English article](../drafts/historiales-20261024/en-monitor-archives-hormuz.html) · [Datos, reproducción y plan](../drafts/historiales-20261024/README.md).

## Enfoque y conservación de los datos

Una lectura periodística de qué conserva el monitor, no una reconstrucción del tránsito marítimo. Se distinguen decisiones del sistema, mediciones de actividad y cambios de método. La nueva versión añade la confianza V7 comprobada: 47 MEDIA y 2 ALTA. Los dos registros ALTA, del 07/08 y 02/09, están fuera de las ventanas comparadas y no contradicen sus recuentos exclusivamente MEDIA.

CSV y resumen de entrada originales intactos; ni nuevas filas ni cambios de clasificación. Fuentes enlazadas a commits completos: 373545ee para los dos archivos históricos y 9d6b0cf5 para el CSV. Peticiones HTTP del 24/10/2026 a las 14:00 UTC: los tres archivos responden 200 y sus huellas normalizadas coinciden. El CSV se contrastó fila por fila con los dos JSON congelados usando sus claves originales; no se añaden mediciones AIS.

54 decisiones anteriores y 49 V7, analizadas por separado; 51 INCIERTO y 3 ABIERTO en el primer modelo, 49 OPEN_SEVERELY_RESTRICTED en V7. Ventanas de 21 días UTC: 11 registros en 8 días y 10 en 7 días. No se extrapolan barcos, variación del tráfico, duración de cierres, fallos de servicio, riesgo ni precisión. Confianza es una etiqueta del modelo, no una probabilidad calibrada.

## Visualización y reproducción

Dos gráficos por idioma y versiones móviles de confianza: seis SVG propios, sin fuentes de pago ni imágenes ajenas. La cronología incluye un símbolo por fila en paneles separados y agrupa por día UTC para evitar puntos ocultos. plot-records.csv conserva fecha exacta y posición de apilado de los 103 símbolos. Los gráficos no unen puntos, interpolan días ni convierten altura en intensidad marítima.

La comprobación se hace sobre los centros dibujados en los SVG, no solo las fechas: 54 y 49 centros únicos; separación mínima 8,55849 unidades SVG, superior al límite conservador de 8 para el diámetro de los marcadores. Los gráficos anchos mantienen tamaño mínimo y desplazamiento; el de confianza usa una composición móvil sin desplazamiento. Se incorporan formas, texto alternativo, leyendas, tablas, fuentes y períodos visibles. Las fuentes SVG incluyen alternativas sans-serif para navegadores sin DejaVu Sans.

reproduce.py verifica los derivados sin red y rechaza un cambio del CSV congelado. render_charts.py solo lee ese conjunto y genera los gráficos, con versión de Matplotlib declarada. No se modifica el motor, el archivo vivo ni otras investigaciones.

## Estado editorial y publicación

Se registra de forma limitada que el propietario comunicó haber comprobado recuentos y ventanas. La nueva redacción ES/EN, gráficos, derechos y publicación siguen pendientes; no se crea una aprobación humana, nombre o fecha ficticios. editorial-reviews.json y las cuatro opciones de monetización permanecen intactos.

Los dos HTML tienen canonical, hreflang es/en/x-default recíprocos para las rutas previstas, además de noindex, original-draft y publisher-ads disabled. El directorio completo se excluye de Pages, sitemap y feeds incluso si se fusiona la PR. No se habilita un publicador ni se relajan filtros de seguridad. Una publicación posterior exige preparar el candidato público exacto con sus destinos de recursos, comprobarlo y obtener autorización expresa y una revisión real de esa versión.

El CI incluye el directorio y sus pruebas y verifica los CSV derivados. La revisión técnica no se presenta como revisión editorial humana ni como aprobación de AdSense.

## Verificación de la entrega

Pruebas locales: 394 casos Python (376 correctos y 18 opcionales omitidos), 20 de mantenimiento y 23 JavaScript correctos. Los nueve casos nuevos cubren datos congelados, ventanas UTC, confianza, SVG, fuentes, metadatos, exclusión de la publicación y ausencia de aprobación ficticia. Compilación, reproducción, build público, enlaces y controles de publicidad correctos; validación de fuentes sin errores, con diez avisos preexistentes.

Revisión en navegador de ambos idiomas a 320, 390 y 1280 píxeles: imágenes cargadas, cuerpo sin desbordamiento horizontal, confianza legible sin desplazamiento móvil y cronología desplazable por teclado. El artefacto público conserva 170 HTML y 56 URLs en sitemap, sin incluir esta nueva edición ni sus recursos. La comparación de archivos protegidos confirma que motor, historiales, clasificación, monetización y registro de revisiones no cambian.
