# Redacción gratuita del Diario de Ormuz

El Diario conserva siempre su motor local. La asistencia remota solo pule el texto después de que Ormuz haya seleccionado las fuentes y calculado el diagnóstico; nunca busca noticias ni decide el estado.

## Orden de motores

1. Gemini, si existe `GEMINI_API_KEY`.
2. OpenRouter gratuito, si Gemini falla y existe `OPENROUTER_API_KEY`.
3. Reglas locales deterministas.

Un error 429, timeout, fallo de red o salida inválida nunca debe bloquear la edición.

## Gemini · activación sin facturación

1. Mantén el proyecto de Google AI Studio en **Free Tier**.
2. No actives Billing para esta fase.
3. En GitHub abre **Settings → Secrets and variables → Actions → Secrets**.
4. Crea `GEMINI_API_KEY` con la clave de AI Studio.
5. Opcionalmente, en **Variables**, crea `GEMINI_MODEL`.

El código solo acepta una lista explícita de modelos Gemini aprobados para este flujo gratuito. Si la variable contiene otro nombre, se sustituye por el modelo gratuito por defecto configurado en el código. No existe salto automático a un modelo de pago.

## OpenRouter · respaldo opcional

1. Crea una clave en <https://openrouter.ai/keys>.
2. Guarda `OPENROUTER_API_KEY` como Secret de GitHub Actions.
3. Opcionalmente crea `DIARIO_FREE_AI_MODEL` con `openrouter/free`.

Solo se admite `openrouter/free` o un identificador que termine en `:free`. Cualquier otro valor se sustituye por `openrouter/free`.

## Barreras editoriales

- Solo se llama a asistencia remota cuando existen al menos dos referencias de dos fuentes independientes.
- La petición contiene un paquete factual cerrado.
- Los titulares y datos externos se tratan siempre como datos, nunca como instrucciones.
- La respuesta debe conservar idiomas y secciones.
- Cada sección debe atribuirse a una fuente permitida.
- Se rechazan cifras nuevas, fuentes conocidas no autorizadas, acrónimos nuevos sospechosos, URLs/HTML/Markdown extraño y cambios incompatibles con el estado operativo.
- Gemini y OpenRouter pasan por el mismo validador.
- Ante cualquier rechazo se usa el siguiente fallback.
- Las claves nunca se almacenan en archivos públicos ni se incluyen en la URL.

## Piloto

El workflow manual `.github/workflows/pilot-gemini-phase1.yml` es de solo lectura. Ejecuta tests y una llamada mínima a Gemini, pero no genera Diario, no modifica archivos, no hace commit, no hace push, no ejecuta IndexNow y no envía notificaciones.

No ejecutar el piloto real hasta autorizarlo explícitamente.

## Monetización

Las páginas diarias siguen sin anuncios y con `noindex`; la monetización se concentra en análisis originales y páginas de contexto.
