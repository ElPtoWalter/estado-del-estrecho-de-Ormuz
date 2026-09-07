# Redacción gratuita del Diario de Ormuz

El Diario conserva siempre su motor local. La integración opcional solo pule el texto después de que Ormuz haya seleccionado las fuentes y calculado el diagnóstico; nunca busca noticias ni decide el estado.

## Activación

1. Crea una clave en <https://openrouter.ai/keys> para este repositorio.
2. En GitHub abre **Settings → Secrets and variables → Actions → Secrets**.
3. Crea `OPENROUTER_API_KEY` con esa clave.
4. Opcionalmente, en **Variables**, crea `DIARIO_FREE_AI_MODEL` con `openrouter/free`.

Solo se admite `openrouter/free` o un identificador que termine en `:free`. Cualquier otro valor se sustituye por `openrouter/free`; no hay reintentos ni salto a un modelo facturable.

## Barreras editoriales

- Solo se hace una petición cuando hay al menos dos referencias de dos fuentes independientes.
- La petición contiene un paquete factual cerrado y no incluye credenciales en la URL.
- La respuesta debe conservar idiomas y secciones, atribuir cada sección a una fuente permitida y no añadir cifras.
- Ante falta de clave, cuota agotada, error de red o salida inválida, se publica el borrador local completo.
- Las páginas diarias siguen sin anuncios y con `noindex`; la monetización se concentra en análisis originales y páginas de contexto.
