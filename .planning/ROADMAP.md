# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- 📋 **v1.1 Context Persistence & Agent Memory** — Phases 6–8 (planned)
- 📋 **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9–12 (planned)
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

### 📋 v1.1 Context Persistence & Agent Memory

**Theme:** Make graphify a persistent, evolving context layer — not just a one-shot graph builder. Enables agents to read AND write to the knowledge graph across sessions, and gives users visibility into how their codebase/corpus changes over time.

**Origin:** Gap analysis against April 2026 research corpus + 6 external repositories (llm-council, spar-kit, smolcluster, context-constitution, honcho, cpr). See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

**Phases:**

- [x] Phase 6: Graph Delta Analysis & Staleness — Compare current run against previous run; surface added/removed/changed nodes, community migration, and connectivity changes. Output `GRAPH_DELTA.md` using CPR summary+archive pattern. Persist graph snapshots in `graphify-out/snapshots/` with automatic FIFO retention. Attach per-node staleness metadata (`extracted_at`, `source_hash`, staleness state) so agents can judge how much to trust each graph claim. _(Informed by: letta-ai/context-constitution staleness-as-first-class principle, EliaAlberti/cpr summary+archive pattern)_
- [x] Phase 7: MCP Write-Back with Peer Modeling — Extend MCP server with mutation tools: `annotate_node`, `add_edge`, `flag_node` with crash-safe JSONL append persistence. Add peer identity tracking (peer_id, session_id, timestamp) and session-scoped graph views. Add `propose_vault_note` tool that stages proposals for human approval before any vault write. `graph.json` is never mutated by agent tools. _(Informed by: plastic-labs/honcho peer-centric entity model, letta-ai/letta-obsidian `propose_obsidian_note` approval pattern)_ (completed 2026-04-13)
- [x] Phase 8: Obsidian Round-Trip Awareness — On `--obsidian` re-run, detect user-modified notes via content-hash manifest and preserve user-authored content blocks during merge. Extend v1.0 merge engine with `PARTIAL_UPDATE` action and user-space sentinel blocks. `--dry-run` reports which notes have user modifications. User content always wins — graphify never overwrites content between user sentinel markers. (completed 2026-04-13)
- [ ] Phase 8.1: Approve & Pipeline Wiring — Thread vault manifest through `graphify approve` path so approved proposals respect user-modified detection and manifest updates. Wire `auto_snapshot_and_delta` into skill.md pipeline so snapshots and deltas generate automatically on every `/graphify` run. _(Gap closure: INT-01 high, INT-02 medium from v1.1 audit)_
- [ ] Phase 8.2: MCP Query Enhancements — Extend MCP `get_node` to surface provenance fields (`extracted_at`, `source_hash`, staleness state). Add `get_agent_edges` query tool so agents can retrieve edges they previously created via `add_edge`. _(Gap closure: INT-03 low, INT-04 low from v1.1 audit)_

**Carried forward from v1.0 v2 scope** (may be folded into phases above or addressed separately):

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

- [ ] Phase 9: Multi-Perspective Graph Analysis with Structured Protocol — Add configurable analysis "lenses" (security, architecture, complexity, onboarding). **Adopt a 3-stage council protocol**: (1) each lens independently analyzes the graph, (2) anonymous peer review identifies blind spots and contradictions across lens outputs, (3) synthesis produces a unified report highlighting convergences, tensions, and the single most important insight per lens. The knowledge graph itself serves as the "shared cognitive map" (SPAR-Kit's ABSTRACT step) that all perspectives reason over — a unique advantage no other tool has. Reuses existing API integration from `extract.py`. _(Informed by: karpathy/llm-council 3-stage pipeline, synthanai/spar-kit NOOL→TRANSMIT protocol and ABSTRACT step)_
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

## Phase Details

### Phase 6: Graph Delta Analysis & Staleness
**Goal**: Users can see how their knowledge graph changed between runs and know how fresh each node is
**Depends on**: Phase 5 (v1.0 pipeline output format)
**Requirements**: DELTA-01, DELTA-02, DELTA-03, DELTA-04, DELTA-05, DELTA-06, DELTA-07, DELTA-08
**Success Criteria** (what must be TRUE):
  1. After two pipeline runs, user can open `GRAPH_DELTA.md` and see exactly which nodes were added, removed, or changed communities since the previous run
  2. User can read a concise delta summary (agent-context-sized) and separately reference a full machine-readable archive without the summary being bloated
  3. Every graph node carries `extracted_at`, `source_hash`, and a staleness state (FRESH / STALE / GHOST) so user or agent can judge data freshness without re-running extraction
  4. Running `graphify snapshot` saves a named snapshot without requiring a full pipeline re-run, and the `graphify-out/snapshots/` directory never exceeds the configured retention limit
  5. Per-node connectivity delta (degree change, new/lost edge counts) is visible in the delta output, not just node-level presence/absence
**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md — Snapshot module (save/load/prune/list) + provenance metadata injection in extract.py
- [x] 06-02-PLAN.md — Delta computation (set-arithmetic diff, staleness classification, GRAPH_DELTA.md rendering)
- [x] 06-03-PLAN.md — CLI wiring (graphify snapshot command, auto-snapshot+auto-delta pipeline helper)

### Phase 7: MCP Write-Back with Peer Modeling
**Goal**: Agents can annotate, flag, and propose notes on the knowledge graph across sessions, with full provenance and a human-in-the-loop for vault writes
**Depends on**: Phase 6 (snapshot format validated; staleness metadata available to annotation tools)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08, MCP-09, MCP-10
**Success Criteria** (what must be TRUE):
  1. An agent can annotate a node, flag its importance, and add an inferred edge via MCP tools, and those annotations survive a server restart and a full pipeline re-run without being erased
  2. Every annotation record identifies who wrote it (peer_id, session_id, timestamp); default peer_id is "anonymous" and never derives from environment variables or machine identity
  3. Agent can call `propose_vault_note` to stage a proposed note; the note lands in `graphify-out/proposals/` and the vault is untouched until the user runs `graphify approve` to review and accept/reject
  4. Agent can query annotations filtered by peer, session, or time range, and retrieve only annotations relevant to a specific session context
  5. `graph.json` (pipeline ground truth) is never modified by any MCP mutation tool; all agent state lives in `annotations.jsonl` and `agent-edges.json` sidecars
**Plans:** 3/3 plans complete

Plans:
- [x] 07-01-PLAN.md — Sidecar persistence + mutation tools (annotate_node, flag_node, add_edge) + query tool (get_annotations) + mtime reload
- [x] 07-02-PLAN.md — propose_vault_note tool with proposal staging to graphify-out/proposals/
- [x] 07-03-PLAN.md — graphify approve CLI subcommand (list/approve/reject/batch)

### Phase 8: Obsidian Round-Trip Awareness
**Goal**: Users can freely edit graphify-injected vault notes between runs without losing their changes on the next `--obsidian` re-run
**Depends on**: Phase 7 (proposal approval flow established; merge engine well-tested)
**Requirements**: TRIP-01, TRIP-02, TRIP-03, TRIP-04, TRIP-05, TRIP-06, TRIP-07
**Success Criteria** (what must be TRUE):
  1. After a user edits a graphify-injected note and re-runs `--obsidian`, graphify detects the modification and applies `UPDATE_PRESERVE_USER_BLOCKS` instead of a blind overwrite
  2. Content the user places between `<!-- GRAPHIFY_USER_START -->` and `<!-- GRAPHIFY_USER_END -->` sentinel markers is never overwritten by any merge action, even `replace` strategy
  3. Running `--obsidian --dry-run` shows which notes have user modifications and what merge action would be applied to each, before any file is touched
  4. `vault-manifest.json` is written atomically after each successful merge and records content hashes for all graphify-managed notes, enabling accurate change detection on the next run
  5. Merge plan output includes per-note modification source (graphify-generated, user-modified, or both) so the user has an audit trail of what changed and why
**Plans:** 3/3 plans complete

Plans:
- [x] 08-01-PLAN.md — Vault manifest I/O helpers, MergeAction extension, user-modified detection in compute/apply_merge_plan
- [x] 08-02-PLAN.md — User sentinel block parsing and preservation in _synthesize_file_text
- [x] 08-03-PLAN.md — CLI --force flag, manifest/force threading through to_obsidian, format_merge_plan dry-run enhancements

### Phase 8.1: Approve & Pipeline Wiring
**Goal**: The `graphify approve` path respects vault manifest (user-modified detection + manifest update), and the skill pipeline automatically generates snapshots and deltas on every run
**Depends on**: Phase 8 (manifest I/O and auto_snapshot_and_delta implementations)
**Requirements**: TRIP-01, TRIP-02, TRIP-03, TRIP-06, MCP-07, DELTA-01, DELTA-02
**Gap Closure**: INT-01 (approve manifest threading), INT-02 (skill auto-snapshot), FLOW-01, FLOW-02
**Success Criteria** (what must be TRUE):
  1. Running `graphify approve <id> --vault <path>` on a vault with user-modified notes triggers SKIP_PRESERVE for those notes (same behavior as `--obsidian` re-run)
  2. After `graphify approve` writes a note, `vault-manifest.json` is updated with the new content hash
  3. Running `/graphify` (skill invocation) on a corpus that has been graphified before produces `GRAPH_DELTA.md` and saves a snapshot to `graphify-out/snapshots/` without requiring a separate `graphify snapshot` command
**Plans:** 2 plans

Plans:
- [x] 08.1-01-PLAN.md — Approve manifest threading, --force flag, SKIP_PRESERVE warning, proposal deletion
- [x] 08.1-02-PLAN.md — Wire auto_snapshot_and_delta into skill.md pipeline (full + cluster-only paths)

### Phase 8.2: MCP Query Enhancements
**Goal**: Agents can query node staleness state and retrieve agent-created edges through the MCP server
**Depends on**: Phase 8.1 (not strictly, but logical ordering)
**Requirements**: DELTA-04, MCP-08
**Gap Closure**: INT-03 (provenance in get_node), INT-04 (agent-edges query)
**Success Criteria** (what must be TRUE):
  1. Calling MCP `get_node` returns `extracted_at`, `source_hash`, and a staleness classification (FRESH/STALE/GHOST) alongside existing fields
  2. A new MCP tool `get_agent_edges` returns edges from `agent-edges.json`, filterable by peer_id and session_id
**Plans:** 2 plans

Plans:
- [x] 08.1-01-PLAN.md — Approve manifest threading, --force flag, SKIP_PRESERVE warning, proposal deletion
- [x] 08.1-02-PLAN.md — Wire auto_snapshot_and_delta into skill.md pipeline (full + cluster-only paths)

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
| 8.1 Approve & Pipeline Wiring | v1.1 | 0/2 | Planned | — |
| 8.2 MCP Query Enhancements | v1.1 | 0/? | Planned | — |
| 9. Multi-Perspective Analysis (Council Protocol) | v1.2 | 0/? | Planned | — |
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
*Last updated: 2026-04-12 — Gap closure phases 8.1-8.2 added from v1.1 milestone audit. Phase 6 status corrected to Complete. v1.2-v1.3 milestones preserved from prior exploration sessions.*
