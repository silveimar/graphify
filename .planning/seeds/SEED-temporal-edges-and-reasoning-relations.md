---
name: SEED-temporal-edges-and-reasoning-relations
description: Add temporal validity (`valid_from`, `valid_until`, `decay_weight`) to graphify edges AND introduce reasoning-relation edge types (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) for document/concept nodes — borrowed from OB1's typed-reasoning-edges schema
status: dormant
trigger_when: Next graph-schema milestone — OR a UAT surfaces stale-INFERRED-edge confusion across runs — OR ADR/paper ingest becomes a primary use case
planted_date: 2026-05-07
---

# SEED: temporal edges + reasoning relations

Bundled because both touch the edge schema in `validate.py` + `extract.py` + `build.py`. Doing them together is one migration; doing them separately is two.

## Part A: Temporal edge validity

Borrow from `OB1/schemas/typed-reasoning-edges/schema.sql`:

| Column | Type | Purpose |
|---|---|---|
| `valid_from` | timestamp | When the edge first observed |
| `valid_until` | timestamp \| null | When superseded/invalidated; null = currently valid |
| `decay_weight` | float [0,1] | Edge weight decays with age; tunable per-relation |

### Why graphify needs this

Today INFERRED edges from a v1 run on an old corpus stack with INFERRED edges from today's run on the current corpus. There's no way to age the old ones out without dropping the cache. Temporal columns let `cache.py` mark edges from a prior run as `valid_until=now` rather than deleting them, preserving history.

### Open questions

- Per-relation decay rates? (structural edges shouldn't decay; INFERRED semantic edges should.)
- Should `analyze.py` weight edges by `decay_weight` when computing god nodes / surprising connections?
- Export format implications — Neo4j Cypher, GraphML, vis.js HTML.

## Part B: Reasoning-relation edge types

Borrow from `OB1/schemas/typed-reasoning-edges`:

| Relation | Meaning | Source side |
|---|---|---|
| `supports` | A provides evidence for B | doc → doc / concept → concept |
| `contradicts` | A contradicts B | same |
| `supersedes` | A replaces/obsoletes B | ADR → ADR |
| `evolved_into` | A is the predecessor of B | concept → concept |
| `depends_on` | A requires B (semantic, not structural import) | concept → concept |

### Why graphify needs this

Graphify's current `relation` taxonomy is purely structural (`calls`, `imports`, `contains`, `defines_*`) plus the catch-all `semantically_similar_to`. When ingesting ADRs, papers, RFCs, design docs, the actually interesting relations are reasoning ones. Without them, the LLM extractor flattens "this ADR supersedes ADR-0042" into `semantically_similar_to`, which is wrong.

### Implementation surface

- `validate.py` — extend confidence taxonomy / relation whitelist.
- `extract.py` — semantic extraction prompts learn to emit reasoning relations on document nodes.
- `analyze.py` — surface contradictions and supersession chains as a new analysis category.
- `report.py` + `wiki.py` — render reasoning chains.

## Companion

- `.planning/notes/ob1-comparison-2026-05-07.md` — P1 items #2 and #3
- `.planning/seeds/SEED-ob1-recipe-repo-graphify.md` — adjacent integration work
