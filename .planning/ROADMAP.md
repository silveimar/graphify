# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- 📋 **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9–12 (incl. 9.1, 9.2) (planned)
- 📋 **v1.3 Agent Discoverability & Obsidian Workflows** — Phases 13–18 (planned)

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

### 📋 v1.2 Intelligent Analysis & Cross-File Extraction

**Theme:** Upgrade graphify's analysis from mechanical graph metrics to LLM-assisted multi-perspective interpretation, and prepare the extraction pipeline for the longer-context-window era.

**Origin:** LLM Council patterns (Karpathy, Verbalized Sampling), TurboQuant compression implications, AI Engineer London "understanding your codebase" insight, SPAR-Kit structured argumentation, Smolcluster heterogeneous distribution. See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

**Phases:**

- [x] Phase 9: Multi-Perspective Graph Analysis with Autoreason Tournament — Add configurable analysis "lenses" (security, architecture, complexity, onboarding). **Adopt autoreason's tournament protocol** instead of a simple council: (1) each lens independently analyzes the graph producing an incumbent analysis (A), (2) an adversarial agent generates a competing revision (B) that challenges the incumbent's findings, (3) a synthesis agent produces a merged interpretation (AB), (4) fresh blind judges score A/B/AB via Borda count with no shared context. **"No finding" competes as a first-class option** — prevents the analysis from hallucinating problems in clean graphs. The knowledge graph itself serves as the "shared cognitive map" that all perspectives reason over — graphify's unique advantage. Reuses existing API integration from `extract.py`. _(Informed by: NousResearch/autoreason tournament-based self-refinement, karpathy/llm-council, synthanai/spar-kit ABSTRACT step)_ (completed 2026-04-14)
  **Plans:** 3 plans
  - [x] 09-01-PLAN.md — Python utility functions (render_analysis_context + render_analysis) with TDD
  - [x] 09-02-PLAN.md — Tournament orchestration in skill.md
  - [x] 09-03-PLAN.md — Human verification of tournament output quality
- [ ] Phase 9.1: Query Telemetry & Usage-Weighted Edges — Track which MCP queries traverse which edges (query telemetry), maintain traversal counters per edge, and run a post-query pass that strengthens high-traffic paths and decays unused ones. After N traversals of A->B->C, propose a direct A->C derived edge with INFERRED confidence. Surface "hot paths" and "cold zones" in GRAPH_REPORT.md. Prerequisite for making multi-perspective analysis usage-aware. _(Informed by: topoteretes/cognee memify() RL-inspired graph self-improvement, rohitg00/agentmemory tiered consolidation)_
  **Plans:** 3 plans
  - [x] 09.1-01-PLAN.md — Telemetry sidecar, traversal recording, weight formula, decay, derived edges (serve.py)
  - [x] 09.1-02-PLAN.md — Usage Patterns report section with hot/cold paths (report.py)
  - [ ] 09.1-03-PLAN.md — Integration wiring: decay on rebuild + telemetry passed to generate() (skill.md)
- [ ] Phase 9.2: Progressive Graph Retrieval — Token-aware 3-layer MCP responses: Layer 1 returns compact summaries (node IDs + labels + community, ~50 tokens), Layer 2 returns edge details and neighbors on drill-down (~200 tokens per node), Layer 3 returns full subgraph with all attributes only on explicit request. Add `budget` parameter to `graph_query` for context-window-aware retrieval. Prevents context blowout at 500+ node graphs. _(Informed by: thedotmack/claude-mem progressive disclosure, rohitg00/agentmemory triple-stream retrieval)_
- [ ] Phase 10: Cross-File Semantic Extraction — When context window allows, send clusters of related files (same directory, import-connected) as a batch for extraction. Captures cross-file relationships the current file-by-file approach misses. Requires cluster detection before extraction.
- [ ] Phase 11: Narrative Mode — Generate a "codebase walkthrough" document that reads like a guided tour for someone new to the codebase. Builds on `wiki.py` module but structured for onboarding, not reference.
- [ ] Phase 12: Heterogeneous Extraction Routing — Route files to different models by complexity and type. Simple/boilerplate files go to fast/cheap models; complex logic files go to powerful models. Detect file complexity via AST metrics (cyclomatic complexity, nesting depth, import count) before extraction. Support parallel extraction across multiple API endpoints. _(Informed by: YuvrajSingh-mist/smolcluster elastic parallelism with capability-aware workload distribution)_

---

### 📋 v1.3 Agent Discoverability & Obsidian Workflows

**Theme:** Make graphify discoverable to agents that don't already know it exists, package graphify-aware thinking commands for Obsidian vault users, and enable continuous background graph improvement.

**Origin:** Agent-readiness stress test framework, Obsidian-Claude Codebook (12 commands pattern), Honcho async derivers, Letta sleep-time compute, SPAR-Kit graph-as-cognitive-map. See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

**Phases:**

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
| 9.1 Query Telemetry & Usage-Weighted Edges | v1.2 | 0/3 | Planned | — |
| 9.2 Progressive Graph Retrieval | v1.2 | 0/? | Planned | — |
| 10. Cross-File Semantic Extraction | v1.2 | 0/? | Planned | — |
| 11. Narrative Mode | v1.2 | 0/? | Planned | — |
| 12. Heterogeneous Extraction Routing | v1.2 | 0/? | Planned | — |
| 13. Agent Capability Manifest | v1.3 | 0/? | Planned | — |
| 14. Obsidian Thinking Commands | v1.3 | 0/? | Planned | — |
| 15. Async Background Enrichment | v1.3 | 0/? | Planned | — |
| 16. Graph Argumentation Mode | v1.3 | 0/? | Planned | — |
| 17. Conversational Graph Chat | v1.3 | 0/? | Planned | — |
| 18. Focus-Aware Graph Context | v1.3 | 0/? | Planned | — |

---
*Last updated: 2026-04-13 — v1.1 milestone archived. v1.2-v1.3 milestones preserved from prior exploration sessions.*
