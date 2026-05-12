---
title: OB1 (Open Brain) ↔ graphify gap analysis
date: 2026-05-07
context: /gsd-explore comparison of `companion-util_repos/OB1/` against current graphify implementation
---

# OB1 ↔ graphify gap analysis

## Framing

OB1 is **storage-side** infrastructure: Supabase + pgvector + async workers + a wide capture-recipe ecosystem. Graphify is **structure-side**: tree-sitter + Leiden + filesystem JSON. They sit at opposite ends of a knowledge pipeline. The cleanest integration is **graphify produces, OB1 stores**, not "merge the two."

OB1's most architecturally interesting moves — temporal edge decay, typed reasoning relations, content-fingerprint dedup, async extraction queue — are *graph-schema upgrades* graphify could absorb without touching its design philosophy. OB1's *retrieval* moves (pgvector, embeddings) deliberately don't fit graphify's "no embeddings, topology-only" stance.

## What OB1 has that graphify doesn't

| Capability | OB1 location | Graphify state |
|---|---|---|
| Temporal edge validity (`valid_from`, `valid_until`, `decay_weight`) | `schemas/typed-reasoning-edges` | Missing — INFERRED edges from old runs stack with new |
| Reasoning relations (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) | same | Missing — graphify has only structural relations |
| Content-fingerprint dedup (SHA-256 of normalized content + unique index) | `recipes/content-fingerprint-dedup` | File-hash cache only; no node-level dedup across sources |
| Async extraction queue w/ retry + error tracking | `schemas/entity-extraction` | Inline extraction; no queue/retry |
| Live retrieval (read-side) skill | `recipes/live-retrieval` | Build-time only; no in-conversation surfacing |
| Compiled-views orchestrator (extraction → typed-edges → wiki, one wrapper) | `recipes/wiki-compiler` | Has `wiki.py` but no scheduled compile loop |
| Schema-aware routing (one input → multiple typed tables) | `recipes/schema-aware-routing` | All inputs land in one graph |
| Sensitivity tiers + source-type gating | `schemas/enhanced-thoughts`, `recipes/source-filtering` | `.graphifyignore` + simple secret heuristic |
| Capture breadth (ChatGPT/Gmail/Slack/X/IG/Perplexity/Grok exports) | `recipes/*-import` | URL + arxiv + tweet only |
| Shared/scoped MCP w/ RLS | `primitives/shared-mcp`, `primitives/rls` | Single-user local stdio MCP |
| Local Ollama embeddings | `recipes/local-ollama-embeddings` | Intentionally absent |
| Repo learning loop (research → lessons → captured takeaways) | `recipes/repo-learning-coach` | Produces graph artifact; no feedback loop |

## What graphify has that OB1 doesn't

- Deterministic AST extraction across 16+ languages — OB1 has nothing code-aware
- Leiden community detection w/ cohesion scoring
- God-node + surprising-connection + knowledge-gap analysis
- Multi-format export (HTML/SVG/GraphML/Obsidian/Neo4j Cypher)
- Confidence taxonomy (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`) with score

## Prioritized recommendations

### P1 — high leverage, low/med effort

1. **Ship `recipes/repo-graphify` for OB1** (Direction 1). Package graphify as an OB1 recipe writing nodes/edges into OB1's `graph_nodes`/`graph_edges` (per ob-graph schema) or `entities`/`edges` (per entity-extraction schema), preserving community labels in metadata. Natural integration point: graphify is structure-extraction, OB1 lacks any code-aware extractor. Seeded: `SEED-ob1-recipe-repo-graphify.md`.
2. **Temporal validity columns on graphify edges** (Direction 2). `valid_from`, `valid_until`, `decay_weight`. Solves stale-INFERRED-edge problem from previous runs. Pairs with existing `cache.py` rerun model. Seeded with #3 in `SEED-temporal-edges-and-reasoning-relations.md`.
3. **Reasoning-relation edge types** (Direction 3). `supports`, `contradicts`, `supersedes` for document/concept nodes. Closes expressivity gap when ingesting ADRs, papers, design docs. Mostly schema + classifier-prompt addition.

### P2 — medium leverage

4. **Content-fingerprint dedup at node level** (Direction 2). SHA-256 of normalized label/description so the same concept across PDF + tweet + repo doc collapses. Extends `_make_id()`. Needs measurement first — see research question.
5. **Align `serve.py` MCP tool surface with ob-graph's 10 tools** (Direction 1). `get_neighbors`, `multi_hop`, `shortest_path`, etc. Lets OB1 users point existing prompts at graphify-built graphs.
6. **Live-retrieval skill for graphify** (Direction 3). Watches active conversation, surfaces graph neighbors from `graphify-out/`. Turns build artifact into runtime context.

### P3 — defer / decisions to flag

7. **Async extraction queue** — only when scale demands.
8. **Multi-layer routing** (structural + concept + reasoning graphs as separate layers) — aligns with prior CCONF/CFED phase notes.
9. **Embeddings / Ollama / pgvector** — **explicit non-recommendation**. `cluster.py` is intentionally embedding-free (Leiden on topology). Don't drift without a decision.
10. **Postgres backend** — **explicit non-recommendation**. Filesystem JSON + Neo4j optional matches graphify's "any-input → artifact" CLI shape. OB1's Supabase coupling is wrong for graphify.
11. **Capture-source breadth** (Slack/Gmail imports) — mission-creep unless graphify pivots toward personal-knowledge.
12. **RLS / shared MCP** — only relevant if graphify becomes multi-tenant.

## Hard non-goals (decisions, not omissions)

- No embeddings in clustering (preserve Leiden topology-only design)
- No Postgres/Supabase as primary store (preserve filesystem-artifact CLI shape)
- No personal-knowledge capture loop (graphify is a structure tool, not a memory tool)
