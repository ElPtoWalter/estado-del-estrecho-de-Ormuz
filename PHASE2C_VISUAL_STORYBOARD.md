# Fase 2C — Storyboard, mapas y gráficos

Estado: infraestructura interna terminada para piloto manual. Sin voz, montaje ni publicación.

## Flujo

```text
video-package validado + guion validado
  → VISUAL_RULESET_V1
  → storyboard 1.0.0
  → SVG originales generados localmente
  → manifiesto visual 1.0.0
  → validación técnica, factual y de derechos
  → preview temporal
  → revisión humana obligatoria
```

## Componentes

- `phase2_visual/schema.py`: versiones, carga de reglas, serialización, hashes e identidades.
- `phase2_visual/storyboard.py`: resolución segura de intenciones y línea de tiempo determinista.
- `phase2_visual/render.py`: plantillas SVG originales, verticales y sin red.
- `phase2_visual/validator.py`: validación cerrada del storyboard, manifiesto, archivos, SVG y derechos.
- `visual-rules.json`: formato, duración mínima, política de derechos y temas por sitio.
- `pilot_phase2c_visual.py`: piloto local aislado sobre una entrada real o fixture histórica real.
- `.github/workflows/pilot-phase2c-visual.yml`: ejecución exclusivamente manual y sin secretos.

El núcleo, el contrato y las pruebas comunes deben permanecer iguales en Ormuz y Gibraltar. Solo cambian el nombre del sitio y del artefacto en cada workflow.

## Decisiones de seguridad

La fase no consume la salida pausada de ElevenLabs. Utiliza el guion local validado de Fase 2A y puede ejecutarse sin coste. `presenter` nunca crea un avatar: se convierte en una tarjeta de estado. `map` crea un esquema editorial rotulado como no navegable. No se aceptan fotografías, vídeos, logotipos, tipografías o mapas descargados.

Las escenas conservan las mismas referencias factuales del guion. El validador reconstruye el storyboard esperado y rechaza cualquier desviación aunque se recalculen sus hashes. Los SVG no pueden contener `image`, `script`, `foreignObject`, enlaces o recursos embebidos externos.

## Artefactos del piloto

El piloto escribe fuera del repositorio:

- `video-package.json`;
- `script.json`;
- `storyboard.json`;
- `visual-manifest.json`;
- `validation.json`;
- `storyboard.md`;
- `assets/*.svg`.

No hace commit, push, despliegue ni publicación. La preview declara fixture, procedencia, tiempos, intención solicitada, plantilla resuelta, trazabilidad, derechos y resultados de validación.

## Ejecución local

```bash
python -m unittest -v test_visual_storyboard.py test_visual_render.py test_visual_validator.py test_phase2c_pilot.py
python pilot_phase2c_visual.py --site ormuz --output-dir /ruta/temporal/phase2c-visual
python pilot_phase2c_visual.py --site gibraltar --output-dir /ruta/temporal/phase2c-visual
```

Cada repositorio ejecuta únicamente su sitio. Si no existe candidato actual elegible, reutiliza el selector seguro de Fase 2A y marca la fixture histórica de forma explícita.

## Límites y siguiente fase

Fase 2C no genera un vídeo reproducible: entrega planos estáticos y tiempos. La futura fase de montaje deberá incorporar voz aprobada o una pista temporal explícita, animación, sincronización, zonas seguras, subtítulos, QA audiovisual y revisión de derechos. Nada de esta fase autoriza FFmpeg productivo, avatares, metraje generativo, redes sociales o publicación.
