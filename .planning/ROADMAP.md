# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- ✅ **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9, 9.1 (+ 9.1.1 gap closure) (shipped 2026-04-15)
- ✅ **v1.3 Intelligent Analysis Continuation** — Phases 9.2, 10, 11 (shipped 2026-04-17)
- 🚧 **v1.4 Agent Discoverability & Obsidian Workflows** — Phases 12–18 (7 phases; SEED-002 bundled under Phase 13)

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

<details>
<summary>✅ v1.3 Intelligent Analysis Continuation (Phases 9.2, 10, 11) — SHIPPED 2026-04-17</summary>

**Theme:** Make graphify viable for real production use on multi-source codebases — agents can query without blowing their token budget, extraction produces dramatically better graphs via entity deduplication, and humans get an interactive thinking partner via Obsidian slash commands. Priority order locked a → b → c during 2026-04-16 exploration: Phase 9.2 first (agent viability), Phase 10 second (graph quality), Phase 11 third (human UX).

**Origin:** Priority lock and scope decisions captured in `.planning/notes/april-2026-v1.3-priorities.md`. Research anchors: Your-GPUs-Just-Got-6x, Make-Knowledge-Graphs-Fast, Pied-Piper-Was-a-Documentary (cardinality estimation + bidirectional search signals for 9.2); Build-Agents-That-Never-Forget, Everything-Is-Connected, Cognee dedup patterns (entity fragmentation signals for 10); Obsidian-Claude-Codebook, Your-Harness-Your-Memory, memory-harness (static-to-interactive slash command pivot for 11). Phase 12 (Heterogeneous Extraction Routing) explicitly deferred to v1.4 — see Out of Scope in REQUIREMENTS.md.

**Phases:**

- [x] Phase 9.2: Progressive Graph Retrieval (3/3 plans, completed 2026-04-17)
- [x] Phase 10: Cross-File Semantic Extraction with Entity Deduplication (9/9 plans, completed 2026-04-17)
- [x] Phase 11: Narrative Mode as Interactive Slash Commands (7/7 plans, completed 2026-04-17)

**Totals:** 3 phases, 19 plans, 14/15 requirements satisfied (TOKEN-04 Bloom filter stretch deferred per D-09).

**Archives:**
- Full phase detail: `.planning/milestones/v1.3-ROADMAP.md`
- Requirements: `.planning/milestones/v1.3-REQUIREMENTS.md`

</details>

### 🚧 v1.4 Agent Discoverability & Obsidian Workflows

**Theme:** Turn graphify from a tool you run into a tool that agents find, trust, compose with, and improve in the background. Agent discoverability via MCP capability manifest + harness-memory export (SEED-002), Obsidian workflow depth via vault-scoped thinking commands, and graph quality over time via heterogeneous routing, async enrichment, focus-aware zoom, grounded chat, and SPAR-Kit graph-argumentation. Phase 12 (Heterogeneous Extraction Routing) pulled forward from v1.3 deferral.

**Origin:** 4-dimension research synthesized 2026-04-17 (`.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS,SUMMARY}.md`). 86 atomic REQ-IDs across 7 phases committed 2026-04-17 (19488ef). User locked P1 + P2 as the full v1.4 scope — no stretch deferrals beyond documented v1.4.x carve-outs (`.planning/REQUIREMENTS.md`). Research anchors: Obsidian-Claude Codebook (12 commands pattern), Honcho async derivers, Letta sleep-time compute, SPAR-Kit POPULATE→ABSTRACT→RUMBLE→KNIT protocol, MCP Spec 2025-11-25 servers-registry format.

**Milestone-level invariants carried forward from v1.0–v1.3 that every v1.4 phase MUST preserve:**

- **D-02 MCP envelope** — every new MCP tool emits `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with status codes. Applies to Phase 13 manifest, Phase 16 `argue_topic`, Phase 17 `chat`, Phase 18 `get_focus_context`.
- **D-16 alias redirect** — every new handler threads IDs through `_resolve_alias` so dedup-merged aliases stay transparent to agent callsites. Applies to Phases 15, 16, 17, 18.
- **D-18 compose don't plumb** — new MCP tools compose existing `analyze.py` / `delta.py` / `snapshot.py` primitives; new analysis algorithms earn their own module (Phase 15 `enrich.py`, Phase 16 `argue.py`, Phase 18 `serve.py` handler). No new pure plumbing modules.
- **`graph.json` read-only** — all new state lives in atomic `.tmp` + `os.replace` sidecars (`routing.json`, `manifest.json`, `enrichment.json`, `GRAPH_ARGUMENT.md`, `harness/*.md`). Grep-CI guard: only `build.py` + `__main__.py` may call `_write_graph_json`.
- **`peer_id="anonymous"` default** — never derived from `os.environ`, `socket.gethostname()`, or `platform.node()`.
- **`security.py` gate** — all new file I/O routes through `validate_graph_path(base=...)`; all label renders go through `sanitize_label` / `sanitize_label_md`; `yaml.safe_load` only.
- **Snapshot double-nesting regression guard (Pitfall 20 / v1.3 CR-01)** — Phase 18 codifies this by renaming `snapshot.py::root` → `project_root` with a sentinel dataclass asserting `not path.name == "graphify-out"`. Phases 12, 15, 17 inherit this guard automatically.

**Phases:**

- [x] Phase 12: Heterogeneous Extraction Routing — Per-file complexity classifier (AST metrics) routes extraction to cheap/mid/expensive model classes with parallel fan-out, cost ceiling enforcement, model-isolated cache keys, and a `routing.json` sidecar audit trail. (6/6 plans, completed 2026-04-17)
- [x] Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export) — Static `server.json` + runtime `manifest.json` with MCP `capability_describe` tool, CLI `graphify capability`, introspection-driven generation (never hand-maintained), manifest-hash drift detection, and bundled SEED-002 `graphify harness export` producing SOUL/HEARTBEAT/USER triplet for Claude harness. Shipped 2026-04-17 (4/4 plans, 18/18 REQ-IDs).
- [ ] Phase 14: Obsidian Thinking Commands — Vault-scoped `/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind` slash commands (plus P2 `/graphify-bridge`, `/graphify-voice`, `/graphify-drift-notes`) with `target: obsidian|code|both` frontmatter filtering, mandatory `propose_vault_note + approve` trust boundary, and a Plan 00 refactor migrating `_uninstall_commands()` from hardcoded whitelist to directory-scan.
- [ ] Phase 15: Async Background Enrichment — Four-pass background enricher (description, patterns, community summaries, staleness) writing overlay-only `enrichment.json`; event-driven via `watch.py` post-rebuild hook; `fcntl.flock`-coordinated with foreground `/graphify`; snapshot-pinned at process start for determinism.
- [ ] Phase 16: Graph Argumentation Mode — `graphify/argue.py` substrate populates a SPAR-Kit-style `ArgumentPackage` from a graph subgraph; `skill.md` orchestrates the LLM debate (Phase 9 blind-label harness reused); mandatory `{claim, cites: [node_id]}` schema rejects fabricated node IDs; round cap 6; `dissent`/`inconclusive` valid outputs; `GRAPH_ARGUMENT.md` advisory-only artifact.
- [ ] Phase 17: Conversational Graph Chat — Two-stage structurally-enforced `chat(query, session_id)` MCP tool (Stage 1 tool-call only, Stage 2 compose from results only); every claim cited to `{node_id, label, source_file}`; empty results return templated fuzzy suggestions; session-scoped history; `/graphify-ask` slash command.
- [x] Phase 18: Focus-Aware Graph Context — `get_focus_context(focus_hint)` MCP tool returns BFS ego-graph + community summary for a structured focus hint (`file_path`, optional `function_name`/`line`/`neighborhood_depth`/`include_community`); pull-model (no filesystem watcher); codifies v1.3 CR-01 snapshot-root fix; silently ignores spoofed paths. ✅ 2026-04-20

**Deferred to v1.4.x (not v1.4 scope):**

- **SEED-002 inverse-import** (CLAUDE.md → graph) — requires quarantine + prompt-injection defenses; v1.4 is export-only (OQ-4).
- **SEED-002 multi-harness schemas** (codex.yaml, letta.yaml, honcho.yaml, AGENTS.md) — prove canonical pattern on `claude.yaml` first (OQ-5).

**Deferred to v1.5+:**

- **SEED-001 Tacit-to-Explicit Elicitation Engine** — revisit if onboarding/discovery becomes the milestone theme.

## Phase Details

### Phase 12: Heterogeneous Extraction Routing
**Goal**: User can route an extraction run across multiple model classes so cheap files get cheap models and complex files get expensive ones, with full cost visibility and cache isolation per model choice.
**Depends on**: Nothing new (builds on v1.0–v1.3 `extract.py` + `cache.py`). HARD-gates `cache.py::file_hash()` key format for all downstream phases.
**Requirements**: ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05, ROUTE-06, ROUTE-07, ROUTE-08 [P2], ROUTE-09 [P2], ROUTE-10 [P2] — 10 REQ-IDs.
**Success Criteria** (what must be TRUE):
  1. User runs `graphify run --router` on a mixed codebase and a `graphify-out/routing.json` sidecar records a per-file `{class, model, endpoint, tokens_used, ms}` decision trail.
  2. User edits `graphify/routing_models.yaml` to retarget a complexity class to a different model and the next extraction honors the new mapping without any code change.
  3. Re-running extraction with a different model for the same file produces a distinct cache entry — no cross-contamination between routing decisions (model_id participates in the cache key).
  4. User sets `GRAPHIFY_COST_CEILING` and extraction aborts with a clear pre-flight cost-overrun message before any expensive LLM call fires.
  5. A pathological concurrency test (8 workers, 10 provider-429 responses) completes without thundering-herd retries — the central semaphore and global 429 `threading.Event` enforce polite backoff.
**Plans**: 6/6 complete (12-01 routing + YAML, 12-02 cache keys, 12-03 extract + batch tier helper, 12-04 routing audit, 12-05 P2 cost/canary/vision, 12-06 CLI + skill). Summaries under `.planning/phases/12-heterogeneous-extraction-routing/12-*-SUMMARY.md`.

### Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export)
**Goal**: Agents that don't already know graphify exists can discover it via MCP registries, describe its surface before calling it, and export graphify's state into any supported agent harness without lock-in.
**Depends on**: Nothing new for Wave A. Wave B depends on all of Phases 14, 15, 16, 17, 18 having landed (final manifest regeneration captures the full MCP surface).
**Requirements**: MANIFEST-01, MANIFEST-02, MANIFEST-03, MANIFEST-04, MANIFEST-05, MANIFEST-06, MANIFEST-07, MANIFEST-08, MANIFEST-09 [P2], MANIFEST-10 [P2], HARNESS-01, HARNESS-02, HARNESS-03, HARNESS-04, HARNESS-05, HARNESS-06, HARNESS-07 [P2], HARNESS-08 [P2] — 18 REQ-IDs.
**Bundled**: SEED-002 Harness Memory Export (HARNESS-01..08, claude.yaml-only in v1.4).
**Success Criteria** (what must be TRUE):
  1. User runs `graphify capability --stdout` and receives an MCP-compliant `server.json` document validated against JSON Schema draft 2020-12 without errors.
  2. An external MCP agent connects to graphify, calls `capability_describe`, and receives a merged static+live manifest including graph stats, alias map size, sidecar freshness, and enrichment snapshot id.
  3. Every MCP response envelope's `meta` includes a manifest content-hash; an agent can detect drift between what was advertised at connect time and what the live server is responding.
  4. Developer adds a new MCP tool to `serve.py::list_tools()` and the next manifest regeneration picks it up automatically — CI `graphify capability --validate` fails if the manifest drifts from the live registry (no hand-maintenance possible).
  5. User runs `graphify harness export --target claude` and receives `graphify-out/harness/claude-{SOUL,HEARTBEAT,USER}.md` rendered from `graph.json` + `annotations.jsonl` + `agent-edges.json` + `telemetry.json` with annotations excluded by default (allow-list enforced).

**Execution waves** (single Phase 13 entry, not decimal-phase split):

- **Wave A (plumbing — 3rd in build order):** Manifest generator + `graphify capability` CLI + runtime `capability_describe` MCP tool. Describes the surface present at this point (Phases 12 + 18 landed). Establishes the introspection pattern that Phases 14/15/16/17 auto-register into.
- **Wave B (final regeneration — 8th in build order):** Manifest regenerates with all 14–18 tools present. SEED-002 `graphify harness export` bundles here — both waves advertise graphify externally, and Wave B captures the full SEED-002 + manifest surface together.

**Plans**: 4/4 complete. 13-01 (MANIFEST-01..08 manifest generator + CLI + MCP tool + drift gate), 13-02 (MANIFEST-09..10 CI gate + examples), 13-03 (HARNESS-01..06 harness export core — SOUL/HEARTBEAT/USER), 13-04 (HARNESS-07..08 secret scanner + round-trip fidelity). Summaries under `.planning/phases/13-agent-capability-manifest/13-*-SUMMARY.md`.

### Phase 14: Obsidian Thinking Commands
**Goal**: Obsidian vault users invoke graphify-aware slash commands directly inside their vault to navigate, query, and expand their graphify-enriched notes, with every write routed through the v1.1 `propose_vault_note + approve` trust boundary.
**Depends on**: HARD-depends on Phase 18 (commands consume `get_focus_context`) + Plan 00 commands-whitelist refactor. Soft-depends on Phase 17 (for `/graphify-voice` P2).
**Requirements**: OBSCMD-01, OBSCMD-02, OBSCMD-03, OBSCMD-04, OBSCMD-05, OBSCMD-06, OBSCMD-07, OBSCMD-08, OBSCMD-09 [P2], OBSCMD-10 [P2], OBSCMD-11 [P2], OBSCMD-12 [P2] — 12 REQ-IDs.
**Cross-phase rule**: **Plan 00 refactor required before any new command ships.** Migrate `_uninstall_commands()` in `__main__.py:153` from hardcoded filename whitelist to directory-scan (reads `graphify/commands/*.md` at runtime). Existing Phase-11 commands remain installed; refactor is transparent to end users.
**Success Criteria** (what must be TRUE):
  1. User runs `/graphify-moc <community_id>` inside an Obsidian vault and receives a proposed MOC note rendered via the vault's profile template — pending user `graphify approve` before any vault file is touched.
  2. User invokes `/graphify-related` from a vault note and sees graph-connected notes scoped to that note's `source_file` neighborhood (community + 1-hop neighbors).
  3. User runs `/graphify-orphan` and receives a list of nodes with zero community membership or `staleness=GHOST`, sourced from existing telemetry + community metadata.
  4. User runs `/graphify-wayfind` and receives a breadcrumb path from the vault MOC to the current note using the existing `connect_topics` shortest-path machinery.
  5. Installer filters commands by frontmatter `target: obsidian|code|both` — a `--no-obsidian-commands` flag suppresses vault-only commands on code-only platforms; `/graphify-*` prefix convention prevents collision with user-authored commands.
**Plans**: TBD (planner will refine; 4–6 plans expected — Plan 00 = whitelist refactor, Plan 01 = frontmatter filter + installer, Plan 02+ = command implementations).

### Phase 15: Async Background Enrichment
**Goal**: Graphify runs four derivation passes in the background after each rebuild, enriching node descriptions, detecting emerging cross-snapshot patterns, generating per-community summaries, and refreshing staleness — writing only an overlay sidecar, never mutating `graph.json`.
**Depends on**: Nothing hard. Soft-depends on Phase 12 `routing.json` (description pass skip-list for files already extracted by expensive model).
**Requirements**: ENRICH-01, ENRICH-02, ENRICH-03, ENRICH-04, ENRICH-05, ENRICH-06, ENRICH-07, ENRICH-08, ENRICH-09, ENRICH-10 [P2], ENRICH-11 [P2], ENRICH-12 [P2] — 12 REQ-IDs.
**Cross-phase rule**: `graph.json` is **never mutated** by this phase (v1.1 D-invariant preserved; Pitfall 3 critical mitigation). Enrichment writes ONLY `graphify-out/enrichment.json` with atomic `.tmp` + `os.replace`. A single `fcntl.flock` on `.enrichment.lock` coordinates with foreground `/graphify` — foreground always wins, enrichment SIGTERM-aborts cleanly without corrupting partial writes.
**Success Criteria** (what must be TRUE):
  1. User runs `graphify enrich` on an existing graph and all four passes complete within their `--budget TOKENS` cap; `graphify-out/enrichment.json` contains derived content keyed by canonical node_id.
  2. User triggers foreground `/graphify` while enrichment is running — enrichment releases its lock and aborts cleanly without corrupting `enrichment.json` or any other sidecar.
  3. User opens MCP `get_node` on an enriched node and sees the overlay description merged into the response — `serve.py::_load_enrichment_overlay(out_dir)` reads post-load without mutating `graph.json`.
  4. User invokes `graphify enrich --dry-run` and receives a per-pass cost preview (estimated tokens, per-node budget breakdown) without any LLM calls firing.
  5. A grep-CI test asserts only `build.py` and `__main__.py` call `_write_graph_json` — enrichment writes are structurally prevented from touching the pipeline artifact.
**Plans**: 6 plans in 4 waves.
- [x] 15-01-PLAN.md — Module scaffold: `enrich.py` + `graphify enrich` CLI + fcntl.flock lifecycle + snapshot pinning + SIGTERM handler (Wave 1; ENRICH-01, 04, 05, 07)
- [ ] 15-02-PLAN.md — Three LLM passes (description, patterns, community) + priority-drain budget + alias redirect + routing skip-list + atomic per-pass commit (Wave 2; ENRICH-02, 03, 11, 12)
- [ ] 15-03-PLAN.md — Staleness pass (compute-only) + D-07 resume-by-default + D-05 schema versioning guard (Wave 2; ENRICH-02, 03, 05)
- [ ] 15-04-PLAN.md — `serve.py::_load_enrichment_overlay` merge-on-read + `_reload_if_stale` enrichment.json mtime watcher + alias-on-read (Wave 3; ENRICH-08, 09, 12)
- [ ] 15-05-PLAN.md — Foreground-lock acquisition in `__main__.py` `run` + opt-in `--enrich` flag + atexit cleanup in `watch.py` (Wave 3; ENRICH-06, 07)
- [ ] 15-06-PLAN.md — `--dry-run` D-02 envelope + grep-CI `_write_graph_json` whitelist (SC-5) + graph.json byte-equality invariant (SC-1, SC-3) + lifecycle integration tests (SC-2) (Wave 4; ENRICH-03, 10)

### Phase 16: Graph Argumentation Mode
**Goal**: User poses a decision-shaped question about the codebase and graphify orchestrates a structurally-enforced multi-perspective debate grounded in the knowledge graph, producing a cited advisory transcript with no fabricated nodes.
**Depends on**: Soft-depends on Phase 17 citation packet format (shared schema). Reuses Phase 9 blind-label harness as-is.
**Requirements**: ARGUE-01, ARGUE-02, ARGUE-03, ARGUE-04, ARGUE-05, ARGUE-06, ARGUE-07, ARGUE-08, ARGUE-09, ARGUE-10, ARGUE-11 [P2], ARGUE-12 [P2], ARGUE-13 [P2] — 13 REQ-IDs.
**Cross-phase rule**: **Phase 16 MUST NOT invoke Phase 17 `chat` tool** (Pitfall 18 recursion + non-determinism guard). Manifest declares `composable_from: []` for `argue_topic`. Debate uses lower-level deterministic primitives (`graph_context(node_id)`, `get_community`) only. LLM orchestration lives in `skill.md` (D-73 honored); `argue.py` substrate contains zero LLM calls — parallels Phase 9 autoreason tournament structure.
**Success Criteria** (what must be TRUE):
  1. User runs `/graphify-argue <question>` and receives `graphify-out/GRAPH_ARGUMENT.md` with every persona claim cited to an existing `node_id` from the graph.
  2. A persona invents a node that doesn't exist in the graph — the mandatory `{claim, cites: [node_id]}` validator flags it as `[FABRICATED]` and the orchestrator re-prompts without accepting the turn.
  3. Debate runs end-to-end with `dissent` or `inconclusive` as valid final outcomes (no consensus-forcing); round cap = 6 is never exceeded; temperature ≤ 0.4 is enforced.
  4. A regression test replays the Phase 9 blind-label bias suite against Phase 16 — blind A/B labels, stripped persona phrases, rotating judge identity all verified intact.
  5. `GRAPH_ARGUMENT.md` is advisory-only — the file exists under `graphify-out/` and never triggers any code change or graph mutation.
**Plans**: TBD (planner will refine; 4–6 plans expected, including `argue.py` substrate + `ArgumentPackage`, `argue_topic` MCP tool, skill-side debate orchestration with blind harness, `/graphify-argue` command, citation validator).

### Phase 17: Conversational Graph Chat
**Goal**: User asks a natural-language question about the codebase and receives a graph-grounded narrative answer where every claim traces back to a real node — no fabricated entities, no hallucinated connections.
**Depends on**: Soft-depends on Phase 18 (`focus_hint` in args) + Phase 15 (enrichment overlay used as citation source).
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, CHAT-10 [P2], CHAT-11 [P2], CHAT-12 [P2] — 12 REQ-IDs.
**Success Criteria** (what must be TRUE):
  1. User runs `/graphify-ask "what connects module X to module Y?"` and receives a narrative answer paired with `meta.citations: [{node_id, label, source_file}]` resolving every claim to a real graph node.
  2. A post-process grep over the narrative text finds no node IDs or labels that aren't in the citation list — uncited phrases are rejected before the response leaves `_run_chat`.
  3. User asks about an entity not in the graph and receives templated fuzzy suggestions ("did you mean X, Y?") — the handler never fabricates a plausible-but-nonexistent node name.
  4. A two-stage architectural test asserts `serve.py` makes zero LLM calls — Stage 1 emits only tool-call sequences, Stage 2 composes from tool results only; narrative rendering is the skill or calling agent's responsibility.
  5. D-16 alias redirect is threaded through every citation — a node merged into an alias during dedup resolves to its canonical ID in chat output without breaking the user's prior callsite.
**Plans**: TBD (planner will refine; 4–5 plans expected, including `chat` MCP tool + two-stage pipeline, citation validator + fuzzy suggestion templates, session history scoping, `/graphify-ask` command, alias-redirect threading).

### Phase 18: Focus-Aware Graph Context
**Goal**: An agent reports what the user is currently focused on (a file path, optionally a function or line) and graphify returns a scoped subgraph — neighbors, community, and citations — so downstream tools can reason about the local neighborhood without loading the full graph.
**Depends on**: Nothing new (first v1.4 phase alongside Phase 12; no code overlap with Phase 12 — `serve.py` only).
**Requirements**: FOCUS-01, FOCUS-02, FOCUS-03, FOCUS-04, FOCUS-05, FOCUS-06, FOCUS-07, FOCUS-08 [P2], FOCUS-09 [P2] — 9 REQ-IDs.
**Cross-phase rule**: **Codifies v1.3 CR-01 snapshot-path double-nesting regression** (Pitfall 20). Renames `snapshot.py::root` → `project_root` with a sentinel dataclass asserting `not path.name == "graphify-out"` at construction. Phases 12, 15, 17 inherit this guard — any downstream reader that reintroduces double-nesting trips the sentinel at runtime. A nested-dir integration fixture replaces the tmp_path-only test coverage that allowed CR-01 to ship undetected.
**Success Criteria** (what must be TRUE):
  1. Agent calls `get_focus_context({"file_path": "...", "neighborhood_depth": 2, "include_community": true})` and receives a BFS ego-graph + community summary in the D-02 envelope with full citations.
  2. Agent spoofs `focus_hint.file_path = "/etc/passwd"` — the handler silently ignores the request (no filesystem-structure leak, no error echo) via `security.py::validate_graph_path(path, base=project_root)`.
  3. `source_file` as `str | list[str]` (v1.3 schema) resolves correctly — a node with multiple source files returns matching node_ids without crashing the focus resolver.
  4. A regression test constructs `Snapshot(project_root=Path("graphify-out"))` and the sentinel raises before any path operation — the renamed field + assertion prevents Phase 12/15/17 from reintroducing CR-01. ✅ **VERIFIED 2026-04-20** via Plan 18-04 — inline `Path(project_root).name == "graphify-out"` guard wired into all 4 production snapshot helpers (`snapshots_dir`, `list_snapshots`, `save_snapshot`, `auto_snapshot_and_delta`); 4 production-callsite tests in `tests/test_snapshot.py` confirm rejection; structural SC4 check in 18-04-SUMMARY.md runs all 4 helpers against `graphify-out/` and each raises `ValueError`.
  5. Focus is pull-model via MCP arg — no filesystem watcher thread exists; `nx.ego_graph` is reused (no new traversal algorithms) per D-18 compose-don't-plumb.
**Plans**: 3 plans (locked 2026-04-20 per CONTEXT.md D-13).
- [x] 18-01-PLAN.md — Focus Resolver: `_resolve_focus_seeds` + `_multi_seed_ego` (FOCUS-02, FOCUS-06) — ✅ 2026-04-20 (commits 529e4e9 + cb04973)
- [x] 18-02-PLAN.md — MCP Tool + Snapshot Sentinel: `get_focus_context` + `ProjectRoot` + `root`→`project_root` rename + nested-dir fixture (FOCUS-01, FOCUS-03, FOCUS-04, FOCUS-05, FOCUS-07) — ✅ 2026-04-20 (commits 6c63501 + 39a8236 + 1d0169c + b058d37 + 4da9efb)
- [x] 18-03-PLAN.md — P2 Debounce + Freshness: 500ms debounce cache + `reported_at` freshness with Py 3.10 Z-suffix shim (FOCUS-08 [P2], FOCUS-09 [P2]) — ✅ 2026-04-20 (commits 2309a57 + 0f06629)
- [x] 18-04-PLAN.md — Gap closure: CR-01 sentinel wiring + WR-02/03/04 cleanups (SC4 PARTIAL → VERIFIED; inline `Path(project_root).name == "graphify-out"` guard in 4 snapshot helpers; dead `alias_map` param removed from `_run_get_focus_context_core`; WR-03 dispatcher-exercising test + WR-04 D-08 strict-depth invariants) — ✅ 2026-04-20 (commits 81d904a + 28b0f34 + edf793a + docs commit)

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
| 9.2 Progressive Graph Retrieval | v1.3 | 3/3 | Complete | 2026-04-17 |
| 10. Cross-File Semantic Extraction with Entity Deduplication | v1.3 | 9/9 | Complete   | 2026-04-17 |
| 11. Narrative Mode as Interactive Slash Commands | v1.3 | 7/7 | Complete   | 2026-04-17 |
| 12. Heterogeneous Extraction Routing | v1.4 | 6/6 | Complete | 2026-04-17 |
| 13. Agent Capability Manifest (+ SEED-002 Harness Export) | v1.4 | 4/4 | Complete | 2026-04-17 |
| 14. Obsidian Thinking Commands | v1.4 | 0/TBD | Planned | — |
| 15. Async Background Enrichment | v1.4 | 1/6 | In Progress|  |
| 16. Graph Argumentation Mode | v1.4 | 0/TBD | Planned | — |
| 17. Conversational Graph Chat | v1.4 | 0/TBD | Planned | — |
| 18. Focus-Aware Graph Context | v1.4 | 4/4 | Complete | 2026-04-20 |

---
*Last updated: 2026-04-20 — Phase 18 ✅ COMPLETE. Verifier re-run post gap closure flipped status `gaps_found → passed`: 5/5 SCs VERIFIED (including SC4 via inline `Path(project_root).name == "graphify-out"` guard in all 4 snapshot helpers), 9/9 FOCUS REQ-IDs satisfied, 1329 tests passing, code review 0 critical / 0 warning / 3 info (cosmetic). v1.4 progress: 3/7 phases complete (12 + 13 + 18). Build order: 12 ✅ → 13 ✅ → 18 ✅ → 15 (next candidate) → 17 → 16 → 14 → final manifest regen.*
