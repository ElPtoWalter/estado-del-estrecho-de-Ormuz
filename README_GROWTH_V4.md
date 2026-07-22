# Ormuz Growth V4

Paquete de crecimiento y distribución que no modifica el motor editorial.

## Incluye

- Widget responsive ES/EN, oscuro/claro y completo/compacto.
- Página para configurar y copiar el iframe.
- Estudio social que genera una tarjeta PNG 1200×630 y texto para X/LinkedIn desde `status.json`.
- Tres análisis originales en español e inglés:
  - abierto frente a caída del tráfico;
  - control del estrecho y derecho de paso;
  - seguro marítimo y primas de guerra.
- Integración visual en portadas, páginas de análisis y media kit.
- Enlaces UTM, fuentes primarias y generación automática del sitemap.

## Instalación en GitHub

1. Sube a la raíz:
   - `install_growth_v4.py`
   - `growth_v4_payload.zip`
   - `README_GROWTH_V4.md`
2. Crea `.github/workflows/install-growth-v4.yml` con el archivo incluido. También se entrega `PARA_COPIAR_install-growth-v4.yml`.
3. Confirma los archivos en `main`.
4. Abre **Actions → Instalar Ormuz Growth V4 → Run workflow**.
5. La acción instala, valida, guarda y lanza después el workflow normal de Ormuz.

El instalador es idempotente: puede ejecutarse otra vez sin duplicar bloques.
