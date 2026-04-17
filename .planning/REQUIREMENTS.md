# Requirements: graphify — Milestone v1.3 Intelligent Analysis Continuation

**Defined:** 2026-04-16
**Core Value:** Make graphify viable for real production use on multi-source codebases — agents can query it without blowing their token budget, it produces dramatically better graphs via entity deduplication, and humans get an interactive thinking partner via Obsidian slash commands.

**Priority order (locked during 2026-04-16 exploration):** (a) Phase 9.2 → (b) Phase 10 → (c) Phase 11. See `.planning/notes/april-2026-v1.3-priorities.md`.

## v1.3 Requirements

Requirements grouped by priority category. Each maps to exactly one roadmap phase. `[stretch]` tagged items are scope reductions if capacity tightens — roadmapper and plan-phase decide.

### Agent Token Economy (Priority a → Phase 9.2)

- [x] **TOKEN-01**: Agent can call MCP `graph_query` with a `budget=N` token parameter that returns a 3-layer progressive response (Layer 1: compact summaries ~50 tokens/node; Layer 2: edge details + neighbors on drill-down ~200 tokens/node; Layer 3: full subgraph with all attributes only on explicit request)
- [x] **TOKEN-02**: Agent sees an estimated result cardinality (node count, edge count, approximate token size) before a multi-hop graph query executes, with the option to abort when the estimate exceeds the supplied budget
- [x] **TOKEN-03**: Multi-hop graph queries (depth ≥ 3) use bidirectional search from both endpoints and meet in the middle, avoiding exponential path explosion on densely connected graphs
- [ ] **TOKEN-04** *[stretch]*: Sparse-predicate joins are skipped via Bloom filter probes, and 2–3-hop transitive closures are served from a materialized cache computed during idle rebuild windows

### Graph Quality on Multi-Source Inputs (Priority b → Phase 10)

- [x] **GRAPH-01**: Graphify extracts import-connected or co-located file clusters as a single batch unit (one LLM call per cluster, not per file) so cross-file relationships are captured during extraction rather than inferred later
- [x] **GRAPH-02**: A new `graphify/dedup.py` module merges fuzzy-matched (string-similarity ≥ threshold) and embedding-similar (cosine ≥ threshold) entities into a single canonical node after extraction, eliminating the 5–50× entity fragmentation that currently occurs on multi-source corpora
- [x] **GRAPH-03**: When duplicate nodes merge, inbound edges are re-routed to the canonical node, edge weights are aggregated (sum for `weight`, max for `confidence_score`), and the chosen canonical label follows a deterministic tie-breaker (longest / most-connected / most-recent)
- [x] **GRAPH-04** *[stretch]*: Entity references align across source types — the `auth` function in `auth.py`, the "authentication" concept in `docs.md`, and the `AuthService` class referenced in `tests/` resolve to one canonical node via cross-source ontology alignment rules

### Human Thinking Partner via Slash Commands (Priority c → Phase 11)

All commands ship as `.claude/commands/*.md` skill files that invoke the graphify MCP server. They are thin wrappers — no new `graphify/` module required unless an MCP query is missing.

- [x] **SLASH-01**: User can run `/context` to load a full graph-backed life-state summary (active god nodes, top communities, recent deltas) from the currently-loaded graph
- [ ] **SLASH-02**: User can run `/trace <entity>` to see how a specific entity / concept has evolved across graph snapshots (first-seen, modifications, current community, staleness history)
- [x] **SLASH-03**: User can run `/connect <topic-a> <topic-b>` to find the shortest surprising bridge paths between two topics in the graph (uses surprising-connections analysis)
- [ ] **SLASH-04**: User can run `/drift` to surface emerging patterns across sessions / runs — nodes whose community membership, centrality, or edge density has trended in a consistent direction
- [ ] **SLASH-05**: User can run `/emerge` to surface newly-formed clusters that weren't present in the previous snapshot (uses v1.1 delta machinery)
- [ ] **SLASH-06** *[stretch]*: User can run `/ghost` to answer as they would, grounded in voice / style extracted from the user's own graph contributions (may land in a sibling skill if scope exceeds graphify proper)
- [ ] **SLASH-07** *[stretch]*: User can run `/challenge <belief>` to pressure-test a stated belief against graph evidence — surface supporting vs contradicting edges (may land in a sibling skill)

## Deferred (v1.4+)

Carried forward from v1.0/v1.1/v1.2 scope; still valid but not this milestone's priority.

### Template Engine Extensions

- **TMPL-01**: Conditional template sections (`{{#if_god_node}}...{{/if}}` guards)
- **TMPL-02**: Loop blocks for connections in templates (`{{#connections}}...{{/connections}}`)
- **TMPL-03**: Custom Dataview query templates per note type in profile

### Profile Composition

- **CFG-02**: Profile includes/extends mechanism (compose profiles from fragments)
- **CFG-03**: Per-community template overrides

### Obsidian Plugin Integration

- **OBS-01/02**: `.obsidian/graph.json` management as plugin-side integration (if user demand emerges)

## Out of Scope

Explicitly excluded from v1.3 to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Phase 12 Heterogeneous Extraction Routing | Deferred to v1.4. Useful but secondary to the agent-viability (9.2) + graph-quality (10) + human-UX (11) triad. Pull forward only if token costs of running powerful models against simple boilerplate become the dominant v1.3 UAT complaint. |
| SEED-001 Tacit-to-Explicit Elicitation Engine | Trigger conditions do not match v1.3 (onboarding / discovery milestones). Planted in `.planning/seeds/SEED-001-*.md`. |
| SEED-002 Harness Memory Export | Trigger conditions do not match v1.3 (multi-harness lock-in friction). Planted in `.planning/seeds/SEED-002-*.md`. May pair with v1.4 Phase 13 Agent Capability Manifest. |
| Multi-model council extraction | Violates "no new required deps" project constraint; requires external API keys beyond the single-vendor Claude API pattern. |
| Vision-model routing | Was part of the original Phase 12 expansion. Deferred alongside Phase 12. |
| `GRAPH_TOUR.md` static artifact | Original Phase 11 output reshaped into interactive slash commands (SLASH-01..07). Static narrative is inert; slash commands turn the graph into a live thinking partner. |

## Traceability

Which phases cover which requirements. Filled by roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOKEN-01 | Phase 9.2 | Complete |
| TOKEN-02 | Phase 9.2 | Complete |
| TOKEN-03 | Phase 9.2 | Complete |
| TOKEN-04 | Phase 9.2 | Pending |
| GRAPH-01 | Phase 10 | Complete |
| GRAPH-02 | Phase 10 | Complete |
| GRAPH-03 | Phase 10 | Complete |
| GRAPH-04 | Phase 10 | Complete |
| SLASH-01 | Phase 11 | Complete |
| SLASH-02 | Phase 11 | Pending |
| SLASH-03 | Phase 11 | Complete |
| SLASH-04 | Phase 11 | Pending |
| SLASH-05 | Phase 11 | Pending |
| SLASH-06 | Phase 11 | Pending |
| SLASH-07 | Phase 11 | Pending |

**Coverage:**
- v1.3 requirements: 15 total (11 core, 4 stretch)
- Mapped to phases: 15 (all pre-mapped; roadmapper verifies and locks)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 during /gsd-new-milestone v1.3*
