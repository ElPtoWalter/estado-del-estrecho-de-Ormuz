# StraitWatch shared Phase 1 architecture

Both observatories use the same factual and editorial core, while keeping site-specific collectors and operational rules.

## Shared core

- `straitwatch_core.py` owns source identity, article deduplication, event aggregation, verification, importance, factual packets and deterministic hashes.
- `free_editorial_ai.py` owns the optional free editorial-assistant chain: Gemini, OpenRouter free models and local rules.
- Remote models receive the same versioned factual packet and cannot alter the canonical operational state.
- Every remote response is validated against the packet. Invalid, unavailable or exhausted providers fall back without interrupting publication.

## Site adapters

- Collectors map raw source records into the common article contract.
- Operational assessment stays site-specific: Ormuz uses its canonical V7 state; Gibraltar separates maritime, border, bilateral, security, seismic and OPE signals.
- Each repository has its own source registry, public presentation, schedules and retention history.

## Data flow

`collectors -> normalized articles -> deduplication -> events -> verification -> canonical state -> factual packet -> optional assistant -> validator -> Diario/archive/RSS`

Health of sources, pipeline execution, publication integrity and operational assessment are separate dimensions. A stale source can reduce confidence, but never silently rewrite operational reality.

## Invariants

1. Tier 1 records cannot change operational state.
2. Absence of news is not positive operational evidence.
3. Declarations remain declarations.
4. Stable event IDs are reused when corroboration arrives.
5. The factual packet and validator version are recorded with each edition.
6. No AI credential, prompt or private trace is published.
7. The system remains fully operable with local rules and no paid service.
