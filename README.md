# Estado del estrecho de Ormuz · versión 3

Web estática bilingüe para GitHub Pages con actualización automática, historial, metodología pública, alertas y notificación IndexNow.

## Qué cambia en esta versión

- **Motor de decisión conservador:** una declaración política de cierre ya no basta para publicar `CERRADO`.
- **Estado operativo separado:** abierto normal, abierto con restricciones, cierre operativo confirmado, cierre declarado no confirmado, riesgo elevado o fuentes contradictorias.
- **Nivel de confianza:** alta, media o baja.
- **Última confirmación válida:** se conserva cuando una comprobación de red falla.
- **Evidencias públicas:** fuente, titular, fecha y tipo de señal.
- **Consulta oficial reforzada:** búsqueda web específica de avisos PDF de UKMTO/JMIC, IMO y MARAD, además de GDELT y Google News RSS.
- **Historial:** `history.json`, `historial.html` y `en-history.html`.
- **Versión inglesa completa:** `en.html` y páginas auxiliares.
- **Alertas:** notificaciones mientras la pestaña esté abierta, feed Atom, JSON público y canales opcionales del propietario.
- **IndexNow:** aviso automático a buscadores compatibles cuando cambia el estado.
- **Pruebas automáticas:** el workflow ejecuta nueve casos críticos antes de publicar.

## Instalación sobre el repositorio actual

La dirección configurada es:

`https://elptowalter.github.io/estado-del-estrecho-de-Ormuz/`

### 1. Subir los archivos de la raíz

En GitHub abre **Code → Add file → Upload files** y sube todos los archivos de esta carpeta excepto la carpeta `.github`.

Se sustituirán los archivos existentes y se añadirán las nuevas páginas. No borres:

- `google09e63d26dd2b5de4.html`, porque mantiene verificada la propiedad de Google Search Console.
- El archivo de clave IndexNow `8ee87f80641eba7927c66d271c9380a5.txt`.

### 2. Actualizar el workflow manualmente

Como GitHub web no siempre permite arrastrar carpetas ocultas:

1. Abre `.github/workflows/update-status.yml` en el repositorio.
2. Pulsa el lápiz de edición.
3. Sustituye todo su contenido por el del archivo incluido en esta descarga.
4. Haz **Commit changes**.

### 3. Primera ejecución

1. Abre **Actions → Actualizar estado de Ormuz**.
2. Pulsa **Run workflow → Run workflow**.
3. Comprueba que las pruebas y la actualización terminan en verde.
4. Abre la web y fuerza la recarga con `Ctrl + F5`.

No es necesario volver a configurar GitHub Pages, Google Search Console ni Bing Webmaster Tools.

## Archivos principales

| Archivo | Función |
|---|---|
| `update_status.py` | Consulta fuentes, clasifica señales, decide el estado y actualiza la web. |
| `test_decision_engine.py` | Pruebas contra falsos cierres y contradicciones. |
| `notify_services.py` | IndexNow, Telegram y ntfy después de un cambio significativo. |
| `status.json` | API pública del estado actual. |
| `status.schema.json` | Esquema JSON de la API. |
| `history.json` | Historial de cambios significativos. |
| `feed.xml` | Feed Atom para alertas RSS. |
| `sources.json` | Registro legible por máquinas de las fuentes admitidas. |
| `config.json` | URL base, ventanas de tiempo, override manual e IndexNow. |
| `index.html` / `en.html` | Portadas española e inglesa. |
| `historial.html` / `en-history.html` | Cronologías bilingües. |
| `styles.css` / `app.js` | Diseño, accesibilidad, carga dinámica y avisos del navegador. |

## Lógica de decisión resumida

### `CERRADO`

Solo se publica cuando:

- una fuente marítima oficial confirma una interrupción efectiva; o
- al menos dos fuentes independientes y fiables describen tráfico detenido, paso bloqueado, ausencia de buques o imposibilidad de navegar.

### `ABIERTO`

Requiere evidencia reciente de:

- buques transitando;
- tráfico que continúa o se reanuda;
- una ruta o corredor operativo; o
- reapertura confirmada.

Si además hay minas, ataques, congestión, restricciones o una declaración política de cierre, se muestra **Abierto con restricciones**.

### `INCIERTO`

Se utiliza cuando:

- solo existe una declaración de cierre;
- las fuentes se contradicen;
- hay riesgo elevado sin confirmación operativa; o
- no existe evidencia reciente suficiente.

## Forzar un estado manualmente

`config.json` permite un override sencillo:

```json
"manual_override": {
  "status": "INCIERTO",
  "operational_status": "MANUAL_OVERRIDE",
  "confidence": "ALTA",
  "reason_es": "Revisión manual en curso.",
  "reason_en": "Manual review in progress.",
  "expires_at": "2026-07-13T18:00:00Z"
}
```

Para volver a la automatización:

```json
"manual_override": null
```

También sigue siendo compatible con el formato antiguo: `"manual_override": "ABIERTO"`.

## Alertas opcionales del propietario

El workflow funciona sin secretos. Para recibir un mensaje solo cuando cambie el estado, puedes añadir en **Settings → Secrets and variables → Actions**:

### Telegram

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### ntfy

- `NTFY_TOPIC_URL`

Por ejemplo: `https://ntfy.sh/tu-tema-privado`.

## IndexNow

La clave pública incluida es:

`8ee87f80641eba7927c66d271c9380a5`

Su archivo de verificación está en:

`https://elptowalter.github.io/estado-del-estrecho-de-Ormuz/8ee87f80641eba7927c66d271c9380a5.txt`

Cuando cambia el estado, `notify_services.py` envía las páginas actualizadas al endpoint de IndexNow. Las comprobaciones horarias sin cambios significativos no generan envíos.

## Privacidad

La versión actual no incluye anuncios, cuentas ni analítica propia. Los avisos del navegador utilizan únicamente `localStorage` y requieren que la pestaña permanezca abierta.

## Advertencia

Es una herramienta informativa automatizada. No sustituye avisos oficiales de navegación marítima, instrucciones de las autoridades ni asesoramiento profesional.
