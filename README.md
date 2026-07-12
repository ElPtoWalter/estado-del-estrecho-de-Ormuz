# Estado del estrecho de Ormuz

Web estática para GitHub Pages con actualización automática mediante GitHub Actions.

## Instalación

1. Sube **todo el contenido** de esta carpeta a la raíz del repositorio, incluida la carpeta oculta `.github`.
2. En GitHub abre **Settings → Pages**.
3. En **Build and deployment**, selecciona **Deploy from a branch**, rama `main` y carpeta `/ (root)`.
4. Abre la pestaña **Actions**, entra en “Actualizar estado de Ormuz” y pulsa **Run workflow** para hacer la primera comprobación.

Después, GitHub ejecutará la comprobación cada hora. Los horarios programados de GitHub Actions pueden sufrir pequeños retrasos.

## Funcionamiento

- `update_status.py` consulta titulares recientes en GDELT.
- Solo acepta señales explícitas procedentes de una lista limitada de dominios.
- Actualiza `status.json`, que es leído por `index.html`.
- Ante falta de pruebas o contradicciones muestra `INCIERTO`.

## Forzar un estado manualmente

En `config.json`, cambia:

```json
"manual_override": null
```

por `"ABIERTO"`, `"CERRADO"` o `"INCIERTO"`. Para recuperar la automatización, vuelve a poner `null`.

## Advertencia

Es un indicador automatizado basado en noticias, no una fuente oficial de navegación marítima ni una garantía en tiempo real.
