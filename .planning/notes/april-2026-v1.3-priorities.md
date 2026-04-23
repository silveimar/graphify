---
title: "v1.3 Priorities — April 2026 Gap Analysis + North Star Decision"
date: 2026-04-16
context: Exploration session during /gsd-new-milestone v1.3 kickoff. Re-read all 18 docs in input_docs/April/ and reconciled against staged v1.3 roadmap. Captures both the analytical findings and the user's explicit a→b→c priority ordering.
---

# v1.3 Priorities — April 2026 Gap Analysis + North Star Decision

## User's Priority Ordering (North Star)

Explicitly stated during exploration on 2026-04-16:

1. **(a)** Agents can query graphify without blowing their token budget → **Phase 9.2** (Progressive Graph Retrieval, expanded scope)
2. **(b)** Graphify produces a dramatically better graph on real multi-source codebases → **Phase 10** (Cross-File Semantic Extraction, with entity deduplication)
3. **(c)** Humans get a thinking partner via Obsidian slash commands → **Phase 11** (Narrative Mode, reshaped as interactive slash commands)

**Phase 12** (Heterogeneous Extraction Routing) dropped out of the top 3 — **defer to v1.4**.

**Novel ideas** (Tacit-to-Explicit Elicitation Engine, Harness Memory Export, Multi-Model Council) not selected for v1.3. Captured as seeds for future milestones.

## April Docs → Staged Phase Re-Scoping

The 18 April docs don't contradict the staged v1.3 roadmap — they deepen scope in 3 of the 4 phases. Bottom line: **reshape, don't replace**.

### Phase 9.2 — Progressive Graph Retrieval (EXPAND)

**Current scope (staged):** Token-aware 3-layer MCP responses: Layer 1 compact summaries, Layer 2 edge details on drill-down, Layer 3 full subgraph on request. Add `budget` parameter to `graph_query`.

**What April docs signal** (Your-GPUs-Just-Got-6x, Make-Knowledge-Graphs-Fast, Pied-Piper-Was-a-Documentary):
- Cardinality estimation (predict result size *before* executing — stops the blast before it hits the wire)
- Bidirectional search (tame the 50^6 explosion on multi-hop paths)
- Bloom filters to skip joins on sparse predicates
- Materialized transitive closures (cache 2-hop / 3-hop paths computed during idle time)
- Leapfrog triejoin for worst-case-optimal multi-hop joins on triple-indexed stores

**Why this matters for v1.3:** Token economy is now the dominant constraint. Without these, agents will reject graphify for cost reasons and roll their own (or pick Cognee). This is *the* viability lever.

**Caveat:** Not all of those techniques need to land in 9.2. Cardinality estimation + bidirectional search is the minimum; Bloom filters + materialized transitive closures are "nice to have if time permits." Leapfrog triejoin is deep research territory — flag it but don't promise it.

### Phase 10 — Cross-File Semantic Extraction (EMPHASIZE ENTITY DEDUP)

**Current scope (staged):** Batch import-connected or co-located files as extraction units to capture cross-file relationships.

**What April docs signal** (Build-Agents-That-Never-Forget, Everything-Is-Connected, Cognee patterns):
- Batch ingestion alone isn't enough — without **entity deduplication**, you get fragmented graphs where the same entity is represented 5–50 ways
- Cognee's approach: fuzzy matching + embedding-based dedup + merge conflict resolution → node consolidation, inbound edge aggregation
- Automatic ontology alignment across source types (function called `auth` in `auth.py` = "authentication" concept in `docs.md` = "AuthService" class mentioned in `tests/`)

**Why this matters for v1.3:** Graph quality is currently "okay" — nodes cluster reasonably but cross-source entity collisions are common. Agents querying these graphs hit multiple node IDs for the same concept and lose the thread. Dedup is the jump from "okay" to "production-ready."

**Implementation note:** Probably wants a new `graphify/dedup.py` module + a merge step after extraction, not a modification to `extract.py` itself.

### Phase 11 — Narrative Mode (CONVERT TO SLASH COMMANDS)

**Current scope (staged):** Generate a `GRAPH_TOUR.md` — codebase walkthrough reading like a guided tour. Builds on `wiki.py` but structured for onboarding.

**What April docs signal** (Obsidian-Claude-Codebook, Your-Harness-Your-Memory, memory-harness):
- Static narratives are inert. The live pattern is **interactive slash commands** that query the graph:
  - `/context` — load full life state from the graph
  - `/trace` — track idea/entity evolution over time
  - `/connect` — find unexpected bridges between topics (already adjacent to graphify's "surprising connections")
  - `/ghost` — answer as the user would (voice/style extraction)
  - `/challenge` — pressure-test beliefs using the graph as evidence
  - `/drift` — find emerging patterns across sessions/runs
  - `/emerge` — surface new clusters that weren't there last run

**Why this matters for v1.3:** `GRAPH_TOUR.md` is a one-shot artifact; slash commands turn the graph into a thinking partner. Plus, this leverages the v1.1 delta machinery (snapshot / staleness / agent-edges) that otherwise sits unused in the user-facing workflow.

**Delivery:** As `.claude/commands/*.md` skill files that consume the graphify MCP server. Not a new module in `graphify/`.

**Trade-off to flag:** This is as much a Claude-Code-ecosystem feature as a graphify feature. Some commands (`/ghost`, `/challenge`) may land in a sibling skill rather than graphify proper.

### Phase 12 — Heterogeneous Extraction Routing (DEFER TO v1.4)

**Why deferred:** Outside the top-3 priority. Useful but secondary to the agent-viability (9.2) + graph-quality (10) + human-UX (11) triad. Folding this into v1.4 keeps v1.3 tight at 3 phases.

**When we bring it back:** If token costs of running Opus against simple boilerplate become the dominant complaint in v1.3 UAT, pull Phase 12 forward. Otherwise v1.4.

## Ideas Captured as Seeds (Not v1.3)

- **SEED-001** — Tacit-to-Explicit Elicitation Engine (see `.planning/seeds/tacit-knowledge-elicitation-engine.md`)
- **SEED-002** — Harness Memory Export (see `.planning/seeds/harness-memory-export.md`)

## Candidate v1.3 Requirement Categories (Draft)

Seed for the `/gsd-new-milestone` requirements-scoping step:

### Agent Token Economy (Phase 9.2)
- Token-aware 3-layer MCP responses with `budget` parameter
- Cardinality estimation before query execution
- Bidirectional search for multi-hop queries
- (Stretch) Bloom filter skip + materialized transitive closure cache

### Graph Quality on Multi-Source Inputs (Phase 10)
- Batch extraction for import-connected / co-located file clusters
- Fuzzy + embedding-based entity deduplication
- Node consolidation with inbound edge aggregation
- Cross-source ontology alignment (code ↔ docs ↔ papers)

### Human Thinking Partner (Phase 11)
- Slash command suite: `/context`, `/trace`, `/connect`, `/drift`, `/emerge` at minimum
- Optional: `/ghost`, `/challenge` (may land in sibling skill)
- MCP-backed — each command is a thin wrapper over existing graphify queries

## What v1.3 Is NOT (Explicit Out-of-Scope)

- Phase 12 Heterogeneous Routing (deferred to v1.4)
- Elicitation Engine (SEED-001 — trigger conditions not met)
- Harness Memory Export (SEED-002 — trigger conditions not met)
- Multi-model council extraction (violates "no new required deps" constraint; requires external API keys)
- Vision-model routing (was part of proposed Phase 12 expansion — deferred)

## Source Material

- `input_docs/April/` — 18 markdown files, all read during 2026-04-16 exploration
- Prior analyses: `.planning/notes/april-research-gap-analysis.md`, `.planning/notes/repo-gap-analysis.md`
- Staged roadmap: `.planning/ROADMAP.md` (v1.3 section)

---
*Captured during /gsd-explore session on 2026-04-16, consumed by /gsd-new-milestone v1.3.*
