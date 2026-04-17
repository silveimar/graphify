# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- ✅ **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9, 9.1 (+ 9.1.1 gap closure) (shipped 2026-04-15)
- 🚧 **v1.3 Intelligent Analysis Continuation** — Phases 9.2, 10, 11 (in progress, started 2026-04-16)
- 📋 **v1.4 Agent Discoverability & Obsidian Workflows** — Phases 12, 13–18 (planned)

## Phases

<details>
<summary>✅ v1.0 Ideaverse Integration — Configurable Vault Adapter (Phases 1–5) — SHIPPED 2026-04-11</summary>

Configurable output adapter replacing the monolithic `to_obsidian()` with a four-component vault-driven pipeline: profile loading → template rendering → mapping classification → safe merge → CLI wiring. Reads a `.graphify/profile.yaml` from the target vault, falls back to a built-in Ideaverse ACE default when absent, and supports `graphify --obsidian [--dry-run]` plus `graphify --validate-profile` as direct CLI entry points.

**Phases:**

- [x] Phase 1: Foundation — Profile loader, filename safety utilities, and security primitives; FIX-01..05 bug fixes (2/2 plans, completed 2026-04-11)
- [x] Phase 2: Template Engine — Note rendering via `string.Template` with 6 built-in templates (MOC, Thing, Statement, Person, Source, Community Overview) (4/4 plans, completed 2026-04-11)
- [x] Phase 3: Mapping Engine — Topology + attribute classification of nodes into note types and folder placements (4/4 plans, completed 2026-04-11)
- [x] Phase 4: Merge Engine — Safe frontmatter round-trip with `preserve_fields`, field-order preservation, and configurable merge strategies (6/6 plans, completed 2026-04-11)
- [x] Phase 5: Integration & CLI — Wire all four modules into refactored `to_obsidian()`; add `--dry-run` and `--validate-profile` CLI flags (6/6 plans including 05-06 gap-closure, completed 2026-04-11)

**Totals:** 5 phases, 22 plans, 31/31 in-scope requirements satisfied, 2 requirements de-scoped via D-74 (OBS-01/OBS-02).

**Archives:**
- Full phase detail: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v1.1 Context Persistence & Agent Memory (Phases 6–8.2) — SHIPPED 2026-04-13</summary>

Persistent, evolving context layer — graphify is no longer a one-shot graph builder. Agents can read AND write to the knowledge graph across sessions, users see how their corpus changes over time, and Obsidian vault notes survive round-trip re-runs with user content preservation. 25/25 requirements satisfied.

**Phases:**

- [x] Phase 6: Graph Delta Analysis & Staleness (3/3 plans, completed 2026-04-12)
- [x] Phase 7: MCP Write-Back with Peer Modeling (3/3 plans, completed 2026-04-13)
- [x] Phase 8: Obsidian Round-Trip Awareness (3/3 plans, completed 2026-04-13)
- [x] Phase 8.1: Approve & Pipeline Wiring (2/2 plans, completed 2026-04-13)
- [x] Phase 8.2: MCP Query Enhancements (1/1 plan, completed 2026-04-13)

**Totals:** 5 phases, 12 plans, 25/25 requirements satisfied, ~117 commits over 2 days.

**Archives:**
- Full phase detail: `.planning/milestones/v1.1-ROADMAP.md`
- Requirements: `.planning/milestones/v1.1-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.1-MILESTONE-AUDIT.md`

</details>

**Carried forward from v1.0/v1.1 scope** (deferred to v1.2+):

- Conditional template sections (`{{#if_god_node}}...{{/if}}` guards) — TMPL-01
- Loop blocks for template connections (`{{#connections}}...{{/connections}}`) — TMPL-02
- Custom Dataview query templates per note type in profile — TMPL-03
- Profile includes/extends mechanism (compose profiles from fragments) — CFG-02
- Per-community template overrides — CFG-03

---

<details>
<summary>✅ v1.2 Intelligent Analysis & Cross-File Extraction (Phases 9, 9.1, 9.1.1) — SHIPPED 2026-04-15</summary>

LLM-assisted multi-perspective graph analysis via autoreason tournament (4 lenses × 4 rounds), query telemetry with usage-weighted edges and 2-hop derived edges, and lifecycle cleanup ensuring retroactive audit compliance.

**Phases:**

- [x] Phase 9: Multi-Perspective Graph Analysis (Autoreason Tournament) — 4 lenses (security, architecture, complexity, onboarding) × 4 tournament rounds (A/B/AB/blind-Borda) with "no finding" as first-class option (3/3 plans, completed 2026-04-14)
- [x] Phase 9.1: Query Telemetry & Usage-Weighted Edges — Per-edge MCP traversal counters, hot-path strengthening, decay of unused edges, 2-hop derived edges with INFERRED confidence, hot/cold paths surfaced in GRAPH_REPORT.md (3/3 plans, completed 2026-04-15)
- [x] Phase 9.1.1: Milestone v1.2 Lifecycle Cleanup — Retroactive 09.1-VERIFICATION.md, project-level REQUIREMENTS.md with traceability, narrow-scope reconciliation across ROADMAP/STATE/PROJECT. Planning-only gap closure (3/3 plans, completed 2026-04-15)

**Totals:** 3 phases, 9 plans, 10/10 requirements satisfied, milestone audit: passed.

**Archives:**
- Full phase detail: `.planning/milestones/v1.2-ROADMAP.md`
- Requirements: `.planning/milestones/v1.2-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.2-MILESTONE-AUDIT.md`

</details>

---

### 🚧 v1.3 Intelligent Analysis Continuation

**Theme:** Make graphify viable for real production use on multi-source codebases — agents can query without blowing their token budget, extraction produces dramatically better graphs via entity deduplication, and humans get an interactive thinking partner via Obsidian slash commands. Priority order locked a → b → c during 2026-04-16 exploration: Phase 9.2 first (agent viability), Phase 10 second (graph quality), Phase 11 third (human UX).

**Origin:** Priority lock and scope decisions captured in `.planning/notes/april-2026-v1.3-priorities.md`. Research anchors: Your-GPUs-Just-Got-6x, Make-Knowledge-Graphs-Fast, Pied-Piper-Was-a-Documentary (cardinality estimation + bidirectional search signals for 9.2); Build-Agents-That-Never-Forget, Everything-Is-Connected, Cognee dedup patterns (entity fragmentation signals for 10); Obsidian-Claude-Codebook, Your-Harness-Your-Memory, memory-harness (static-to-interactive slash command pivot for 11). Phase 12 (Heterogeneous Extraction Routing) explicitly deferred to v1.4 — see Out of Scope in REQUIREMENTS.md.

**Phases:**

- [ ] **Phase 9.2: Progressive Graph Retrieval**

  Token-aware graph retrieval that prevents context blowout when agents query 500+ node graphs. Adds a `budget=N` token parameter to MCP `graph_query` that drives a 3-layer progressive response protocol: Layer 1 returns compact summaries (node IDs, labels, community membership, ~50 tokens/node); Layer 2 returns edge details and neighbors on drill-down (~200 tokens/node); Layer 3 returns the full subgraph with all attributes only on explicit request. Cardinality estimation (node count, edge count, approximate token footprint) is returned before multi-hop queries execute, letting the agent abort before the response hits the wire. Multi-hop queries at depth ≥ 3 switch to bidirectional BFS from both endpoints, eliminating the exponential path explosion on densely connected graphs. Stretch: sparse-predicate joins skipped via Bloom filter probes; 2–3-hop transitive closures served from a materialized cache computed during idle rebuild windows.

  **Requirements:** TOKEN-01, TOKEN-02, TOKEN-03, TOKEN-04 _(TOKEN-04 stretch)_

  **Success Criteria** (what must be TRUE):
  1. Agent calls `graph_query(budget=500)` and receives a response whose total token footprint is ≤ 500, structured in Layer 1 compact-summary format, with Layer 2/3 available on follow-up
  2. Before a depth ≥ 2 multi-hop query executes, the MCP response includes a cardinality estimate (node count, edge count, estimated tokens) that the agent can inspect to decide whether to abort
  3. Depth ≥ 3 queries demonstrably use bidirectional BFS (both-endpoint traversal meets in the middle), visible via a new `search_strategy` field in MCP query telemetry or trace logs
  4. _(stretch)_ A Bloom filter probe skip appears in the query execution trace when a sparse-predicate join would return zero results, with a measurable reduction in nodes traversed

  **Informed by:** Your-GPUs-Just-Got-6x, Make-Knowledge-Graphs-Fast, Pied-Piper-Was-a-Documentary, thedotmack/claude-mem progressive disclosure, rohitg00/agentmemory triple-stream retrieval. Full rationale: `.planning/notes/april-2026-v1.3-priorities.md` § Phase 9.2.

  **Plans:** 3 plans

  Plans:
  - [x] 09.2-01-PLAN.md — Foundation helpers: _estimate_tokens_for_layer, _estimate_cardinality, branching-factor cache, continuation_token codec (TOKEN-02 + TOKEN-01 codec half)
  - [x] 09.2-02-PLAN.md — Bidirectional BFS + search_strategy telemetry: _bidirectional_bfs, _synthesize_targets, _record_traversal extension (TOKEN-03)
  - [x] 09.2-03-PLAN.md — Dispatch wiring + query_graph contract: _subgraph_to_text layered renderer, schema extension, D-02 hybrid response (TOKEN-01 + TOKEN-02 + TOKEN-03 end-to-end; TOKEN-04 deferred per D-09)

- [x] **Phase 10: Cross-File Semantic Extraction with Entity Deduplication** (completed 2026-04-17)

  Two-part graph quality upgrade for multi-source corpora. Part A (batch extraction): import-connected or co-located file clusters are sent to the LLM as a single batch unit per cluster rather than one file at a time, capturing cross-file relationships during extraction instead of requiring them to be inferred post-hoc. Part B (entity deduplication): a new `graphify/dedup.py` module runs after extraction, merging fuzzy-matched (string-similarity ≥ configurable threshold) and embedding-similar (cosine ≥ configurable threshold) entity pairs into a single canonical node. When nodes merge, inbound edges are re-routed to the canonical node, edge weights are aggregated (sum for `weight`, max for `confidence_score`), and canonical label selection follows a deterministic tie-breaker (longest / most-connected / most-recent). Stretch: cross-source ontology alignment resolves the same entity referenced as a function in `.py`, a concept in `.md`, and a class in `tests/` to one canonical node.

  **Requirements:** GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04 _(GRAPH-04 stretch)_

  **Success Criteria** (what must be TRUE):
  1. Extractor processes a cluster of import-connected files as one LLM call per cluster (not per file); this is observable in `graphify-out/cache/` telemetry and the extraction trace shows cluster boundaries
  2. `graphify/dedup.py` exists and a post-extraction run on a multi-source corpus merges fuzzy + embedding-similar node pairs, producing a `dedup_report` that lists merged pairs and their chosen canonical label
  3. After dedup, `graph.json` shows inbound edges re-routed to canonical nodes and edge weight fields aggregated — no dangling edges pointing to eliminated duplicate nodes remain
  4. _(stretch)_ Running against a mixed corpus (`auth.py` + `docs.md` + `tests/AuthService`) produces one canonical node that aggregates all three source references, verified by inspecting the canonical node's `source_file` list in `graph.json`

  **Informed by:** Build-Agents-That-Never-Forget, Everything-Is-Connected, Cognee entity dedup patterns, april-research-gap-analysis (entity fragmentation finding). Full rationale: `.planning/notes/april-2026-v1.3-priorities.md` § Phase 10.

  **Plans:** 7 plans

  Plans:
  - [x] 10-01-PLAN.md — Wave 0 scaffolding: [dedup] extra, validate.py schema (D-11/D-12), conftest fixtures, test stubs, multi-file fixture (GRAPH-02/03 foundation)
  - [x] 10-02-PLAN.md — graphify/batch.py: cluster_files() with import-component clustering, top-dir cap, token-budget split, topological order (GRAPH-01)
  - [x] 10-03-PLAN.md — graphify/dedup.py: fuzzy+cosine gates, D-09 canonical selection, D-10 edge aggregation, write_dedup_reports, GRAPH-04 stretch (GRAPH-02/03/04)
  - [x] 10-04-PLAN.md — CLI --dedup command + yaml.safe_load config + skill.md + 8 platform variants (GRAPH-01/02; T-10-04)
  - [x] 10-05-PLAN.md — GRAPH_REPORT.md Entity Dedup section with defense-in-depth sanitization (GRAPH-02; T-10-02)
  - [x] 10-06-PLAN.md — MCP serve.py alias redirect layer with resolved_from_alias meta (GRAPH-03; D-16)
  - [x] 10-07-PLAN.md — Obsidian aliases: frontmatter from merged_from + --obsidian-dedup flag (GRAPH-03; D-15)

- [x] **Phase 11: Narrative Mode as Interactive Slash Commands** (completed 2026-04-17)

  Replaces the original static `GRAPH_TOUR.md` artifact concept with a suite of seven MCP-backed slash commands that turn graphify into a live thinking partner. Each command ships as a `.claude/commands/*.md` skill file — thin wrappers that invoke existing graphify MCP server queries. No new `graphify/` module is required unless an MCP query is missing. Core five commands: `/context` (full graph-backed life-state summary: active god nodes, top communities, recent deltas), `/trace <entity>` (evolution of a named entity across graph snapshots: first-seen, modifications, current community, staleness history), `/connect <topic-a> <topic-b>` (shortest surprising bridge paths between two topics using the existing surprising-connections analysis), `/drift` (emerging patterns across sessions: nodes whose community, centrality, or edge density has trended consistently), `/emerge` (newly-formed clusters not present in the previous snapshot, using v1.1 delta machinery). Stretch commands: `/ghost` (respond in the user's voice/style extracted from their graph contributions) and `/challenge <belief>` (pressure-test a stated belief against graph evidence — supporting vs contradicting edges). Stretch commands may land in a sibling skill if scope exceeds graphify proper.

  **Requirements:** SLASH-01, SLASH-02, SLASH-03, SLASH-04, SLASH-05, SLASH-06, SLASH-07 _(SLASH-06, SLASH-07 stretch)_

  **Success Criteria** (what must be TRUE):
  1. `/context` returns a summary of active god nodes, top communities, and recent graph deltas via MCP — the response is grounded in live graph data, not a static snapshot
  2. `/trace <entity>` returns a snapshot history for a named entity: first-seen timestamp, community membership over time, and current staleness score
  3. `/connect <topic-a> <topic-b>` returns the shortest path between two topics AND a complementary block of globally surprising bridges from `analyze.py`'s surprising-connections analysis — rendered as two distinct sections, with the surprising-bridges block labelled as global to the graph (NOT filtered to the A-B path)
  4. `/drift` returns trending nodes — those whose community membership, centrality, or edge density has moved in a consistent direction across the last N graph runs
  5. `/emerge` returns newly-formed clusters detected by comparing the current graph snapshot to the previous one, using the v1.1 delta machinery
  6. _(stretch)_ `/ghost` and `/challenge` ship as `.claude/commands/*.md` files that invoke the graphify MCP server, with documented fallback behavior when invoked against a vault with no prior graph

  **Informed by:** Obsidian-Claude-Codebook (12 commands pattern), Your-Harness-Your-Memory, memory-harness interactive slash command patterns, letta-ai/letta-obsidian. Full rationale: `.planning/notes/april-2026-v1.3-priorities.md` § Phase 11.

  **Plans:** 7 plans (5 core + 1 discoverability + 1 stretch conditional)
  - [x] 11-01-PLAN.md — MCP tools graph_summary + connect_topics in serve.py (SLASH-01, SLASH-03)
  - [x] 11-02-PLAN.md — MCP tool entity_trace + shared snapshot-chain fixture (SLASH-02)
  - [x] 11-03-PLAN.md — MCP tools drift_nodes + newly_formed_clusters (SLASH-04, SLASH-05)
  - [x] 11-04-PLAN.md — Command prompt files graphify/commands/*.md for core 5 (SLASH-01..05)
  - [x] 11-05-PLAN.md — skill.md + 8 variants Available-slash-commands discoverability section (D-16)
  - [x] 11-06-PLAN.md — __main__.py _PLATFORM_CONFIG + --no-commands + pyproject.toml package-data (D-13, D-14, D-15)
  - [x] 11-07-PLAN.md — CONDITIONAL: /ghost + /challenge command files (SLASH-06, SLASH-07 stretch, D-17)

---

### 📋 v1.4 Agent Discoverability & Obsidian Workflows

**Theme:** Make graphify discoverable to agents that don't already know it exists, package graphify-aware thinking commands for Obsidian vault users, and enable continuous background graph improvement. Phase 12 (Heterogeneous Extraction Routing) pulled forward from v1.3 deferral.

**Origin:** Agent-readiness stress test framework, Obsidian-Claude Codebook (12 commands pattern), Honcho async derivers, Letta sleep-time compute, SPAR-Kit graph-as-cognitive-map. See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

**Phases:**

- [ ] Phase 12: Heterogeneous Extraction Routing — Route files to different models by complexity and type. Simple/boilerplate files go to fast/cheap models; complex logic files go to powerful models. Detect file complexity via AST metrics (cyclomatic complexity, nesting depth, import count) before extraction. Support parallel extraction across multiple API endpoints. _(Informed by: YuvrajSingh-mist/smolcluster elastic parallelism with capability-aware workload distribution)_
- [ ] Phase 13: Agent Capability Manifest — Machine-readable self-description of graphify's MCP server capabilities. Structured format agents can discover, evaluate, and decide to use. Explore emerging standards (MCP registry, schema.org, capability descriptors).
- [ ] Phase 14: Obsidian Thinking Commands — Package graphify-aware slash commands (`/trace`, `/connect`, `/drift`, `/emerge`) that work on graphify-enriched vaults. Leverage the wikilinks and frontmatter injected by v1.0 Ideaverse adapter. Distributed as skill files for Claude Code and other harnesses.
- [ ] Phase 15: Async Background Enrichment — Post-build passes that run without blocking the user: enrich node descriptions from docstrings/comments, detect emerging patterns across runs, update staleness scores, generate per-community natural-language summaries. Modeled on Honcho's async deriver pattern and Letta's sleep-time compute concept. Can be triggered by `graphify watch` or a post-build hook. _(Informed by: plastic-labs/honcho async derivers, letta-ai/context-constitution sleep-time compute)_
- [ ] Phase 16: Graph Argumentation Mode — Use the knowledge graph as a shared cognitive map (SPAR-Kit's ABSTRACT substrate) for structured LLM debates about codebase decisions. User poses a question ("Should we refactor the auth module?"), graphify populates relevant subgraph context, spawns perspective personas that argue over the graph structure, and synthesizes actionable recommendations. Extension of Phase 9's multi-perspective analysis into interactive decision support. _(Informed by: synthanai/spar-kit POPULATE→ABSTRACT→RUMBLE→KNIT protocol)_
- [ ] Phase 17: Conversational Graph Chat — Natural-language querying of the knowledge graph via MCP chat tool or standalone skill. "What connects module X to module Y?" "Explain community 3." "What are the most fragile parts of this codebase?" Translates natural-language questions into graph traversals (BFS/DFS, community lookup, god-node retrieval) and returns narrative answers grounded in graph data. _(Informed by: letta-ai/letta-obsidian chat sidebar for vault querying)_
- [ ] Phase 18: Focus-Aware Graph Context — Track what the user is currently editing/viewing and scope graph queries to that file's neighborhood. MCP tool `get_focus_context(file_path)` returns the node, its edges, its community, and connected nodes. For Obsidian integration: dynamic "Related Knowledge" panel showing graph connections for the active note. _(Informed by: letta-ai/letta-obsidian focus mode memory block pattern)_

**Deferred — revisit if user demand emerges:**

- `.obsidian/graph.json` management (OBS-01/02) as plugin-side integration

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-04-11 |
| 2. Template Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 3. Mapping Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 4. Merge Engine | v1.0 | 6/6 | Complete | 2026-04-11 |
| 5. Integration & CLI | v1.0 | 6/6 | Complete | 2026-04-11 |
| 6. Graph Delta Analysis & Staleness | v1.1 | 3/3 | Complete | 2026-04-12 |
| 7. MCP Write-Back with Peer Modeling | v1.1 | 3/3 | Complete | 2026-04-13 |
| 8. Obsidian Round-Trip Awareness | v1.1 | 3/3 | Complete | 2026-04-13 |
| 8.1 Approve & Pipeline Wiring | v1.1 | 2/2 | Complete | 2026-04-13 |
| 8.2 MCP Query Enhancements | v1.1 | 1/1 | Complete | 2026-04-13 |
| 9. Multi-Perspective Analysis (Autoreason Tournament) | v1.2 | 3/3 | Complete   | 2026-04-14 |
| 9.1 Query Telemetry & Usage-Weighted Edges | v1.2 | 3/3 | Complete | 2026-04-15 |
| 9.1.1 Milestone v1.2 Lifecycle Cleanup | v1.2 | 3/3 | Complete | 2026-04-15 |
| 9.2 Progressive Graph Retrieval | v1.3 | 0/3 | Planned | — |
| 10. Cross-File Semantic Extraction with Entity Deduplication | v1.3 | 9/9 | Complete   | 2026-04-17 |
| 11. Narrative Mode as Interactive Slash Commands | v1.3 | 7/7 | Complete   | 2026-04-17 |
| 12. Heterogeneous Extraction Routing | v1.4 | 0/? | Planned | — |
| 13. Agent Capability Manifest | v1.4 | 0/? | Planned | — |
| 14. Obsidian Thinking Commands | v1.4 | 0/? | Planned | — |
| 15. Async Background Enrichment | v1.4 | 0/? | Planned | — |
| 16. Graph Argumentation Mode | v1.4 | 0/? | Planned | — |
| 17. Conversational Graph Chat | v1.4 | 0/? | Planned | — |
| 18. Focus-Aware Graph Context | v1.4 | 0/? | Planned | — |

---
*Last updated: 2026-04-16 — v1.3 roadmap created. 3 phases (9.2, 10, 11), 15 requirements mapped. Phase 12 moved to v1.4.*
