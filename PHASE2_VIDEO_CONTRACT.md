# Contrato de datos de vídeo — Fase 2

Versión del contrato: `1.0.0`  
Estado: aprobado como interfaz futura; implementación fuera de alcance de la Fase 1.

## 1. Objetivo y límites

Este documento define el único paquete de datos que una futura cadena audiovisual podrá consumir. El paquete debe derivarse exclusivamente del modelo factual y del estado operativo ya validados en la Fase 1. No autoriza ni implementa generación de guiones, voz, avatar, mapas, vídeo, publicación social, credenciales, compras, suscripciones ni llamadas a servicios externos.

La recomendación de vídeo es una salida determinista del sistema editorial, no una decisión autónoma de un modelo generativo. Un modelo podrá redactar en la Fase 2 únicamente a partir de los campos permitidos y su resultado deberá volver a validarse contra este paquete.

## 2. Invariantes editoriales

1. Solo entran en `verified_facts` hechos con estado `VERIFIED_PRIMARY` o `VERIFIED_MULTISOURCE`.
2. Las declaraciones se conservan en `statements`, siempre atribuidas, y nunca se presentan como hechos verificados por repetición.
3. Todo hecho referencia `event_id`, `source_ids`, hora de observación y estado de verificación.
4. El estado operativo procede del campo canónico de cada sitio; ningún consumidor puede recalcularlo desde titulares.
5. Las incertidumbres, lagunas y contradicciones se conservan. No pueden omitirse para hacer el vídeo más concluyente.
6. Los textos de artículos, prompts, secretos, datos privados y cuerpos completos de fuentes quedan excluidos.
7. Cada recurso visual necesita estado de derechos, crédito y usos permitidos explícitos.
8. Un paquete con fuentes vencidas, salud degradada o derechos ambiguos no puede recomendar publicación automática.
9. La selección, prioridad, deduplicación y recomendación son reproducibles con las mismas entradas.
10. La revisión humana nunca puede ser rebajada por un modelo generativo.

## 3. Sobre JSON normativo

```json
{
  "schema_version": "1.0.0",
  "package_id": "video-package:<site>:<edition_date>:<content_hash>",
  "site": "ormuz|gibraltar",
  "language_set": ["es", "en"],
  "generated_at": "2026-09-29T10:00:00Z",
  "edition_date": "2026-09-29",
  "content_kind": "event|daily_summary",
  "event_id": "event-id-or-null",
  "importance": 0,
  "video_recommended": false,
  "video_recommendation": {
    "rule_id": "VIDEO_RULESET_V1",
    "reason_codes": [],
    "decided_by": "deterministic_rules",
    "human_review_required": true
  },
  "video_type": "breaking|daily_summary|explainer|null",
  "headlines": {
    "es": "",
    "en": ""
  },
  "verified_facts": [
    {
      "fact_id": "fact-id",
      "text_es": "",
      "text_en": "",
      "event_id": "event-id",
      "verification_status": "VERIFIED_PRIMARY|VERIFIED_MULTISOURCE",
      "source_ids": ["source-id"],
      "observed_at": "2026-09-29T09:30:00Z"
    }
  ],
  "statements": [
    {
      "statement_id": "statement-id",
      "text_es": "",
      "text_en": "",
      "speaker": "",
      "source_ids": ["source-id"],
      "attributed": true,
      "not_verified_as_fact": true
    }
  ],
  "sources": [
    {
      "source_id": "source-id",
      "canonical_name": "",
      "url": "https://example.invalid/item",
      "published_at": "2026-09-29T09:00:00Z",
      "tier": "primary|official|trusted_media|secondary",
      "official": false,
      "rights_status": "link_and_factual_reference_only"
    }
  ],
  "operational_context": {
    "state": "canonical-site-state",
    "confidence": "high|medium|low",
    "dimensions": {},
    "as_of": "2026-09-29T09:30:00Z",
    "health": "healthy|degraded|stale"
  },
  "what_changed": [],
  "what_we_know": [],
  "what_we_dont_know": [],
  "watch_next_24h": [],
  "visual_assets": [
    {
      "asset_id": "asset-id",
      "type": "map|chart|photo|video|logo",
      "uri": "",
      "rights_status": "cleared|restricted|unknown",
      "credit": "",
      "allowed_uses": [],
      "sha256": ""
    }
  ],
  "content_hash": "sha256-of-canonical-payload"
}
```

Los campos indicados son obligatorios, aunque admitan `null` o listas vacías. Se serializan con claves ordenadas, UTF-8 y fechas ISO 8601 en UTC. `content_hash` se calcula sobre el objeto canónico sin el propio campo `content_hash`.

## 4. Reglas deterministas de recomendación

La Fase 2 deberá versionar el conjunto exacto de umbrales. Como mínimo:

- `video_recommended` es `false` si no existe cambio material verificado, si la importancia no alcanza el umbral, si hay conflicto no resuelto, si la salud es `stale`, si faltan derechos o si la evidencia solo contiene declaraciones.
- Un evento podrá aspirar a `breaking` únicamente con impacto operativo material, importancia alta, verificación suficiente, fuentes sanas y revisión humana obligatoria.
- `explainer` se reserva a cambios verificados que necesitan contexto; no se usa para especulación.
- `daily_summary` se produce como máximo una vez por sitio y fecha, y solo cuando haya material verificado nuevo.
- La ausencia de novedades produce `video_recommended: false`; nunca se rellena con contenido de archivo presentado como actual.
- Los motivos se guardan como códigos estables en `reason_codes`. Gemini u otro modelo no puede alterar la decisión ni sus motivos.

La revisión humana es obligatoria para contenido de última hora, riesgo para personas, violencia o material gráfico, disputas, restricciones legales, derechos ambiguos y cualquier estado de confianza baja.

## 5. Paquete de resumen diario

Un `daily_summary` incluye la fotografía operativa canónica, eventos verificados de la edición, cambios desde la edición anterior, hechos conocidos, incógnitas y señales a vigilar durante las próximas 24 horas. No incorpora una conclusión que no exista en el producto editorial validado ni mezcla fechas para aparentar actualidad.

## 6. Validación, idempotencia y errores

Antes de aceptarse, el consumidor validará esquema, tipos, enumeraciones, referencias internas, URLs, fechas, permisos, salud y correspondencia literal o semántica de cada afirmación con sus hechos. Los identificadores desconocidos, campos adicionales, hechos sin fuente, derechos `unknown`, hashes incorrectos o fechas futuras invalidan el paquete.

`package_id` y `content_hash` hacen la operación idempotente. Un consumidor debe rechazar duplicados y no volver a publicar el mismo contenido. Las correcciones generan un nuevo hash, conservan trazabilidad al paquete sustituido y requieren una nueva validación. Los errores se devuelven como códigos estructurados; nunca se corrigen silenciosamente con invenciones.

## 7. Flujo futuro previsto

El flujo permitido para una implementación posterior será: paquete factual validado → guion → validador factual local → voz/avatar/mapas → control audiovisual y de derechos → aprobación humana cuando corresponda → publicación. Cada salida deberá conservar `package_id`, `content_hash`, fuentes y versión de reglas.

Queda expresamente fuera de la Fase 1 integrar o llamar a ElevenLabs, PixVerse, Kling, YouTube, TikTok, Instagram o servicios equivalentes; almacenar sus credenciales; activar facturación; o publicar vídeos. Cualquier incorporación futura exige una decisión separada, pruebas aisladas sin publicación y controles de coste.

## 8. Evolución del contrato

Los cambios compatibles incrementan la versión menor y solo podrán añadir campos opcionales. Eliminar o reinterpretar campos, cambiar enumeraciones o relajar garantías exige versión mayor. Los consumidores declaran las versiones que aceptan y rechazan cualquier versión desconocida. Las migraciones deben mantener pruebas de contrato idénticas en Ormuz y Gibraltar.
