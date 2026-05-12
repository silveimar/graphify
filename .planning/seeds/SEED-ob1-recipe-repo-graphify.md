---
name: SEED-ob1-recipe-repo-graphify
description: Package graphify as an OB1 (Open Brain) `recipes/repo-graphify` recipe so any OB1 user can run graphify against a corpus and write nodes/edges into their Supabase graph tables
status: dormant
trigger_when: v1.14 (or later) milestone scoping starts — OR external interest from OB1 community surfaces — OR graphify ships an MCP tool surface aligned with ob-graph (P2 #5 in ob1-comparison-2026-05-07.md)
planted_date: 2026-05-07
---

# SEED: graphify-as-OB1-recipe (`recipes/repo-graphify`)

## Why

OB1 has zero code-aware extraction. Its entity-extraction worker reads `thoughts.content` with an LLM; it doesn't parse ASTs. Graphify is exactly that missing layer. Shipping graphify as an OB1 recipe gives OB1 users a code-structure layer for free, and gives graphify external distribution + a real persistent-store integration target.

## Sketch

Recipe shape (mirrors existing OB1 recipes like `obsidian-vault-import`, `ob-graph`):

```
recipes/repo-graphify/
  README.md
  metadata.json
  graphify-to-ob1.py    # thin adapter
  schema.sql            # optional: alignment notes for ob-graph or entity-extraction
```

Adapter responsibilities:
1. Run graphify against a corpus path (`graphify run --corpus <path>` or library call).
2. Read produced `graphify-out/graph.json` (nodes, edges, community labels, confidence).
3. Map graphify nodes → OB1 `graph_nodes` (or `entities`); graphify edges → `graph_edges` (or `edges`).
4. Preserve graphify community + confidence + source_file in target `metadata` jsonb.
5. Idempotent insert via OB1's content-fingerprint dedup.

## Open questions (resolve at activation)

- Target `ob-graph` schema (manual graph) or `entity-extraction` schema (extracted entities)? Probably both, gated by flag.
- How to represent graphify's structural relations (`calls`, `imports`, `contains`) in OB1's relation taxonomy — extend or map?
- Embed graphify CLI as Python dependency, or shell out? Shelling out keeps graphify's optional-dep matrix from polluting OB1 users.
- Should community labels become OB1 `topics` / tags?

## Dependencies

- Likely lighter once graphify ships **P2 #5**: align `serve.py` MCP tool surface with ob-graph's 10 tools. Same data shape on both sides.
- Independent of P1 #2 (temporal edges) and P1 #3 (reasoning relations), but those make the recipe more valuable.

## Companion artifacts

- `.planning/notes/ob1-comparison-2026-05-07.md` — full gap analysis
- `.planning/seeds/SEED-temporal-edges-and-reasoning-relations.md` — adjacent schema work
