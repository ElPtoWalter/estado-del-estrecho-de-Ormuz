# PR #20: sincronización y comprobación

Actualizada sobre main `6b89924d4d3b768400256b85727219e91ede7b87`. Git pudo incorporar sus actualizaciones automáticas sin conflictos de contenido. No se fusiona esta PR en main ni se despliega desde esta tarea.

Se conservan la reparación de selectores ES/EN mediante los alternates, los destinos del historial y del RSS, las dos rutas UKMTO y la eliminación de la referencia a una API no publicada. El CI ejecuta ahora construcción y enlaces y cubre cambios en el generador del feed y las pruebas de navegación.

Validación local: 372 pruebas Python, 354 aprobadas y 18 opcionales omitidas; otras 20 de mantenimiento y 23 JavaScript aprobadas. Construcción y comprobador de enlaces: cero errores. El intento de mantenimiento con el TEMP predeterminado de Windows produjo errores de permisos; se repitió usando una carpeta temporal del workspace y las 20 pruebas pasaron. No se modifica el clasificador para corregir ese problema del entorno.

Artefacto: 74 URLs en sitemap; 50 entradas del RSS del monitor con ancla existente; 30 ediciones por idioma con URL fechada; cero entradas del feed auxiliar mientras no existan sus HTML históricos. Las pruebas comprueban conservación del cuerpo y la fecha al cambiar idioma, anclas antiguas y actuales, enlaces externos intactos y rechazo de destinos inválidos. Los archivos históricos permanecen noindex y sin publicidad.

Los JSON automáticos, reglas operativas y configuración de monetización se conservan como en main. Las cuatro opciones de AdSense siguen en false. La comprobación del despliegue público realizada en la auditoría original sigue fechada en ese informe; esta validación de rama no afirma que las correcciones ya estén publicadas.

Autorización pendiente: fusión de la PR y el despliegue que proceda tras ella. #19 ya estaba fusionada y no se vuelve a fusionar. #18 permanece independiente. La integración de estos cambios en #21 no equivale a fusionar #20 en main.
