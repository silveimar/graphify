# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- ✅ **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9, 9.1 (+ 9.1.1 gap closure) (shipped 2026-04-15)
- ✅ **v1.3 Intelligent Analysis Continuation** — Phases 9.2, 10, 11 (shipped 2026-04-17)
- ✅ **v1.4 Agent Discoverability & Obsidian Workflows** — Phases 12–18.2 (shipped 2026-04-22)
- 🚧 **v1.5 Diagram Intelligence & Excalidraw Bridge** — Phases 19–22 (4 phases; 32 REQ-IDs)

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

<details>
<summary>✅ v1.4 Agent Discoverability & Obsidian Workflows (Phases 12, 13, 14, 15, 16, 17, 18, 18.1, 18.2) — SHIPPED 2026-04-22</summary>

Agent discoverability via MCP capability manifest + harness-memory export (SEED-002), Obsidian workflow depth via vault-scoped thinking commands, and graph quality over time via heterogeneous routing, async enrichment, focus-aware zoom, grounded chat, and SPAR-Kit graph-argumentation. Phase 12 (Heterogeneous Extraction Routing) pulled forward from v1.3 deferral. Milestone audit passed after Phase 18.1 (Phase 13 verification artifact retrofill) and Phase 18.2 (MANIFEST-06 metadata closure + VALIDATION frontmatter refresh).

**Phases:**

- [x] Phase 12: Heterogeneous Extraction Routing — AST-complexity-classified routing to cheap/mid/expensive model classes with parallel fan-out, cost ceiling, model-isolated cache keys, `routing.json` sidecar. (6/6 plans, completed 2026-04-17)
- [x] Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export) — Static `server.json` + runtime `manifest.json`, MCP `capability_describe`, manifest-hash drift detection, `graphify harness export` producing SOUL/HEARTBEAT/USER triplet. (4/4 plans, 18/18 REQ-IDs, completed 2026-04-17; verification retrofitted via Phase 18.1)
- [x] Phase 14: Obsidian Thinking Commands — Vault-scoped `/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind` slash commands with `target:` frontmatter filtering + `propose_vault_note + approve` trust boundary. (6/6 plans, completed 2026-04-23)
- [x] Phase 15: Async Background Enrichment — Four-pass background enricher writing overlay-only `enrichment.json`; event-driven via `watch.py`; `fcntl.flock`-coordinated; snapshot-pinned for determinism. (6/6 plans, completed 2026-04-22)
- [x] Phase 16: Graph Argumentation Mode — `argue.py` SPAR-Kit-style `ArgumentPackage` + `argue_topic` MCP tool; `{claim, cites: [node_id]}` schema rejecting fabricated IDs; round cap 6; advisory-only `GRAPH_ARGUMENT.md`. (3/3 plans, completed 2026-04-23)
- [x] Phase 17: Conversational Graph Chat — Two-stage structurally-enforced `chat(query, session_id)` MCP tool; every claim cited; templated fuzzy suggestions on empty; `/graphify-ask` slash command. (3/3 plans, completed 2026-04-22)
- [x] Phase 18: Focus-Aware Graph Context — `get_focus_context(focus_hint)` MCP tool returning BFS ego-graph + community summary; codifies v1.3 CR-01 snapshot-root fix via `snapshot.py::root` → `project_root` rename. (4/4 plans, completed 2026-04-20)
- [x] Phase 18.1: v1.4 Gap Closure — Produced retrofitted `13-VERIFICATION.md`, `13-SECURITY.md`, `13-VALIDATION.md` for Phase 13's shipped 18 REQ-IDs. (commits `33f9f84`, `63d2480`, `1eda4be`)
- [x] Phase 18.2: v1.4 Gap Closure — Added `chat` + `get_focus_context` to `capability_tool_meta.yaml` closing MANIFEST-06; refreshed 15/18 VALIDATION frontmatter; audit re-stamped `passed`. (commits `59298c8`, `37aad87`, `012a90b`)

**Totals:** 9 phase directories (7 core + 2 gap closure), 32 plans, 72/86 P1+P2 requirements satisfied, 14 P2 carve-outs intentionally deferred. 155 files changed, +35,754 / −2,481 lines across 165 commits over 2026-04-17 → 2026-04-22.

**Deferred to v1.4.x / v1.5:**
- SEED-002 inverse-import (CLAUDE.md → graph) — requires quarantine + prompt-injection defenses (OQ-4)
- SEED-002 multi-harness schemas (codex.yaml, letta.yaml, honcho.yaml, AGENTS.md) — prove canonical on claude.yaml first (OQ-5)
- SEED-001 Tacit-to-Explicit Elicitation Engine — revisit if onboarding/discovery becomes the theme
- Phase 19 Vault Promotion Script Layer B — moved to v1.5 via scope reconciliation 2026-04-23 (commit `0f6304b`)

**Archives:**
- Full phase detail: `.planning/milestones/v1.4-ROADMAP.md`
- Requirements: `.planning/milestones/v1.4-REQUIREMENTS.md`
- Milestone audit: `.planning/milestones/v1.4-MILESTONE-AUDIT.md`
- Per-phase artifacts: `.planning/milestones/v1.4-phases/`

</details>

## Phase Details

### 🌱 Candidate Phase: ACE-Aligned Vocabulary, Linking & Naming

**Goal:** Replace graphify's hardcoded note-type vocabulary with an ACE-aligned,
profile-driven system. Emit full Ideaverse-compatible frontmatter (backlinks, collections,
rank, confidence tags) and enforce naming conventions across all vault output.

**Scope:**

- `project.yaml` — new `vocabulary:` section (note types, tags taxonomy, `diagrams:` with
  `x/Excalidraw/` folder map and per-template stencil/palette config)
- `profile.py` — parse and validate the `vocabulary:` section; expose typed dicts to all exporters
- `templates.py` — replace hardcoded `_NOTE_TYPES` frozenset with `vocab.note_types.keys()`
  loaded from profile; add `map`, `dot`, `work`, `question` built-in templates
- `mapping.py` — `classify()` driven by profile vocabulary rules; emit `rank` score to frontmatter
- `export.py` — emit full frontmatter: `up`, `related`, `down`, `collections`, `rank`,
  `created`, and confidence tags (`extracted`/`inferred`/`ambiguous`) on all promoted notes;
  all vault filenames use `safe_filename()` → `lowercase-hyphen` slugs with type prefix
- `seeds.py` (new) — generate `-seed.md` files in `x/Excalidraw/seeds/` from promoted Dots
  using `vocab.diagrams` template/stencil/palette config
- `builtin_templates/` — add `map-template.md`, `dot-template.md`, `work-template.md`,
  `question-template.md`; rename existing templates to `lowercase-hyphen-template` convention

**Naming conventions enforced (all output):**
- Tags: `lowercase-hyphen-separated`, no IDs/symbols/numbers
- Master Keys: `PascalCase`, max 4 words
- MD filenames: `lowercase-hyphen-separated` with type prefix
- Wikilinks: always with human-readable alias `[[filename|Human Readable Alias]]`
- Seeds: `name-seed.md` in `x/Excalidraw/seeds/`
- Diagrams: `name.excalidraw.md` in `x/Excalidraw/diagrams/`

**ACE folder targets:**
`Atlas/Maps`, `Atlas/Dots`, `Atlas/Dots/Things`, `Atlas/Dots/Statements`,
`Atlas/Dots/Questions`, `Atlas/Dots/People`, `Atlas/Sources`, `Efforts/Works`,
`x/Excalidraw/{annotations,cropped,diagrams,palettes,templates,seeds,scripts/downloaded,scripts/custom}`

**Design doc:** `.planning/notes/ace-vocabulary-naming-conventions.md`

**Entry point:** Run `/gsd-add-phase` to formally scope and plan this phase.

---

### 🚧 v1.5 Diagram Intelligence & Excalidraw Bridge

**Theme:** Turn graphify's knowledge graph into a diagram generation pipeline. Auto-detect and user-tag seed nodes from the analyzed graph, produce structured diagram seeds with layout heuristics, bootstrap vault Excalidraw templates from a new `diagram_types` profile section, and deploy a SKILL.md that orchestrates the full seeds → mcp_excalidraw → vault flow. No new required Python dependencies.

**Origin:** Scope confirmed 2026-04-22 via `/gsd-new-milestone v1.5`. Research completed 2026-04-22 (`.planning/research/SUMMARY.md`). Phase 19 (Vault Promotion Script Layer B, VAULT-01..05) pulled in from v1.4 scope-reconciliation 2026-04-23. 32 atomic REQ-IDs across 4 phases (VAULT-01..05, SEED-01..11, PROF-01..04, TMPL-01..06, SKILL-01..06).

**Milestone-level invariants carried forward from v1.4:**
- **D-02 MCP envelope** — `list_diagram_seeds` + `get_diagram_seed` emit `text_body + "\n---GRAPHIFY-META---\n" + json(meta)`.
- **D-16 alias threading** — all new MCP tools thread node IDs through `_resolve_alias`.
- **D-18 compose don't plumb** — `seed.py` composes `analyze.py` primitives (`god_nodes`, `detect_user_seeds`) only; no new pure plumbing modules.
- **MANIFEST-05 atomic pair** — `mcp_tool_registry.py` + `serve.py` extensions land in the same plan.
- **`_VALID_TOP_LEVEL_KEYS` atomicity** — `profile.py` update lands with its first `diagram_types` reader.
- **`compress: false` one-way door** — all `.excalidraw.md` stubs use `compress: false` frontmatter; LZ-String is forbidden.
- **Tag write-back trust boundary** — `gen-diagram-seed` tags written via `vault_adapter.py::compute_merge_plan` with `tags: "union"` only; direct frontmatter writes are forbidden.

**Phases:**

- [ ] Phase 19: Vault Promotion Script (Layer B) — `graphify/vault_promote.py` reads `graph.json` + `GRAPH_REPORT.md`, classifies/scores nodes, writes promoted Obsidian markdown notes directly to the user's vault at correct Ideaverse Pro 2.5 destination folders with full frontmatter, wikilinks, and tag taxonomy. Pulled in from v1.4 scope-reconciliation 2026-04-23. (plans TBD)
- [ ] Phase 20: Diagram Seed Engine — `analyze.py` auto-tagging + `detect_user_seeds(G)`; new `seed.py` module with `build_seed` / `build_all_seeds` / layout heuristics / >60% overlap dedup / max_seeds=20 cap; `--diagram-seeds` CLI; `list_diagram_seeds` + `get_diagram_seed` MCP tools. (3 plans)
- [ ] Phase 21: Profile Extension & Template Bootstrap — `profile.yaml` `diagram_types:` section (ATOMIC with first reader); 6 built-in diagram type defaults; `--init-diagram-templates` CLI command writing real `.excalidraw.md` JSON stubs; `gen-diagram-seed` tag write-back via vault adapter. (2 plans)
- [ ] Phase 22: Excalidraw Skill & Vault Bridge — `skill-excalidraw.md` full orchestration (list seeds → get seed → read template → mcp_excalidraw → vault); `graphify install --excalidraw`; pure-Python `.excalidraw.md` fallback path complete before mcp_excalidraw integration. (2 plans)

---

### Phase 19: Vault Promotion Script (Layer B)
**Goal**: A Python script (`graphify/vault_promote.py`) that reads `graphify-out/graph.json` and `GRAPH_REPORT.md`, classifies and scores nodes, then writes promoted Obsidian markdown notes directly into the user's vault at the correct Ideaverse Pro 2.5 destination folders with full frontmatter, wikilinks, and tag taxonomy.
**Depends on**: Phase 12 (graph.json schema stable), Phase 18 (graph.json read patterns established). No `serve.py` changes — pure file I/O.
**Requirements**: VAULT-01, VAULT-02, VAULT-03, VAULT-04, VAULT-05 — 5 REQ-IDs.
**Success Criteria** (what must be TRUE):
  1. Running `graphify vault-promote --vault /path/to/vault --threshold 3` reads `graphify-out/graph.json` and writes notes to correct Ideaverse folders without touching any existing vault file it did not create.
  2. Every promoted note has valid Ideaverse frontmatter: `up`, `related`, `created`, `collections`, `graphifyProject`, `graphifyRun`, `graphifyScore`, `graphifyThreshold`, and at minimum one tag from each of: `garden/*`, `source/*`, `graph/*`.
  3. Node type dispatch is correct: a god-node domain concept lands in `Atlas/Dots/Things/`, a knowledge gap lands in `Atlas/Dots/Questions/`, a cluster becomes `Atlas/Maps/<slug>.md` with `stateMaps: 🟥`.
  4. `related:` links are populated only from EXTRACTED-confidence edges; INFERRED and AMBIGUOUS edges are omitted from wikilinks.
  5. `graphify-out/import-log.md` is written after each run with vault path, run timestamp, promoted-count by type, threshold, and skipped-count.
**Plans**: TBD (not yet planned).

---

### Phase 20: Diagram Seed Engine
**Goal**: graphify auto-detects diagram-worthy nodes from the analyzed graph and exposes structured seeds — both via the filesystem and as MCP tools — so agents can select and consume them in the Excalidraw pipeline.
**Depends on**: Nothing new (extends existing `analyze.py`, `serve.py`, `mcp_tool_registry.py`).
**Requirements**: SEED-01, SEED-02, SEED-03, SEED-04, SEED-05, SEED-06, SEED-07, SEED-08, SEED-09, SEED-10, SEED-11 — 11 REQ-IDs.
**Cross-phase rules**: D-18 hard invariant — `seed.py` calls only `god_nodes()` and `detect_user_seeds()` from `analyze.py`; never reimplements detection. MANIFEST-05 — `mcp_tool_registry.py` + `serve.py` extensions land in the same plan (Plan 20-03). D-02 envelope on both MCP tools. D-16 alias threading on both MCP tools.
**Success Criteria** (what must be TRUE):
  1. User runs `graphify --diagram-seeds` and `graphify-out/seeds/` is populated with one `{node_id}-seed.json` per auto-detected seed (god nodes + cross-community bridges) plus one per vault-tagged `gen-diagram-seed` node; auto seeds are capped at 20 before any file I/O.
  2. User inspects a seed JSON and finds: `main_nodes` (ego-graph radius-1), `supporting_nodes` (radius-2 minus radius-1), `relations` (all edges in subgraph), `suggested_layout_type` (selected by NetworkX heuristic or overridden by `gen-diagram-seed/<type>` tag), `suggested_template`, and `trigger` (`"auto"` or `"user"`).
  3. Two seeds with >60% node overlap are merged into a single union seed (single-pass, sorted by degree descending, no recursive re-merge); element IDs are `sha256(node_id)[:16]` — never label-derived.
  4. Agent calls `list_diagram_seeds` MCP tool and receives a D-02 envelope listing seed summaries (seed_id, main_node_label, suggested_layout_type, trigger, node_count) — alias-resolved via D-16.
  5. Agent calls `get_diagram_seed(seed_id)` and receives the full SeedDict in a D-02 envelope; a non-existent seed_id returns an error status in the envelope without crashing.
**Plans**: 3 plans.
- [ ] 20-01-PLAN.md — `analyze.py` extension: `god_nodes()` + `_cross_community_surprises()` emit `possible_diagram_seed: true` node attribute; new `detect_user_seeds(G)` reads `tags` attribute for `gen-diagram-seed` / `gen-diagram-seed/<type>` patterns, returns `auto_seeds` + `user_seeds` lists with extracted type hints. Tag write-back via `vault_adapter.py::compute_merge_plan` with `tags: "union"` policy. (SEED-02, SEED-03)
- [ ] 20-02-PLAN.md — New `graphify/seed.py` module: `build_seed(G, node_id, trigger, layout_hint=None) → SeedDict`; `build_all_seeds(G, analysis, profile)`; layout heuristic (6 NetworkX predicates: `is_tree`, DAG topo-gens, community count, degree distribution, edge directionality, node file_types); >60% overlap dedup (single-pass, degree-sorted, union merge); `max_seeds=20` cap before file I/O; element IDs `sha256(node_id)[:16]`; deterministic `versionNonce`; file output to `graphify-out/seeds/{node_id}-seed.json`; `graphify --diagram-seeds` CLI flag in `__main__.py`. (SEED-01, SEED-04, SEED-05, SEED-06, SEED-07, SEED-08)
- [ ] 20-03-PLAN.md — MCP exposure (ATOMIC PAIR per MANIFEST-05): `list_diagram_seeds` + `get_diagram_seed` tools in `mcp_tool_registry.py` + `serve.py` (`_tool_list_diagram_seeds`, `_tool_get_diagram_seed`, `_run_list_diagram_seeds_core`, `_run_get_diagram_seed_core`); D-02 envelope on both; D-16 `_resolve_alias` threading on both; `tests/test_serve.py` additions (8+ cases). (SEED-09, SEED-10, SEED-11)
**UI hint**: no

### Phase 21: Profile Extension & Template Bootstrap
**Goal**: `profile.yaml` gains a `diagram_types` section (with graceful fallback to 6 built-in defaults), and `graphify --init-diagram-templates` writes real `.excalidraw.md` JSON stubs to the vault — locking in `compress: false` as the one-way format decision.
**Depends on**: Phase 20 (`seed.py` `build_seed` for template recommender call path; `detect_user_seeds` for tag write-back).
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, TMPL-06 — 10 REQ-IDs.
**Cross-phase rules**: PROF-02 atomicity — `_VALID_TOP_LEVEL_KEYS` (profile.py line 67), `_DEFAULT_PROFILE`, `validate_profile()`, and the first code reading `diagram_types` all land in the same plan (Plan 21-01). `compress: false` one-way door — all stubs use frontmatter `compress: false`; LZ-String (`lzstring` package) is never used. Tag write-back test-time grep denylist — `Path.write_text`, `write_note_directly`, `open('w')` on vault notes are forbidden; only `vault_adapter.py::compute_merge_plan` is allowed.
**Success Criteria** (what must be TRUE):
  1. User adds a `diagram_types:` section to `.graphify/profile.yaml`; graphify validates it without error and uses the declared template paths, trigger conditions, and naming patterns. When `diagram_types:` is absent, graphify falls back to 6 built-in defaults (architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph) without erroring.
  2. Template recommender in `seed.py` resolves in order: profile `diagram_types` match → layout heuristic default → built-in fallback; never throws on a missing profile section.
  3. User runs `graphify --init-diagram-templates` and 6 `.excalidraw.md` stubs appear at vault paths from profile (or `Excalidraw/Templates/` by default). Each stub has `excalidraw-plugin: parsed`, `compress: false`, a `## Text Elements` block, and a `## Drawing` block with raw scene JSON (`type: excalidraw, version: 2, source: graphify`). Running the command twice without `--force` produces no changes.
  4. User runs `graphify --init-diagram-templates --force` and all 6 stubs are overwritten. If `profile.yaml` has a `diagram_types:` section listing only 3 types, only those 3 stubs are written.
  5. A test-time grep denylist asserts no production code in `seed.py`, `export.py`, or `__main__.py` calls `Path.write_text` / `write_note_directly` / `open('w')` directly on vault note paths — all tag write-backs route through `vault_adapter.py::compute_merge_plan`.
**Plans**: 2 plans.
- [ ] 21-01-PLAN.md — ATOMIC profile update: extend `_VALID_TOP_LEVEL_KEYS` + `_DEFAULT_PROFILE` + `validate_profile()` in `profile.py` for `diagram_types:` section (6 built-in defaults: architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph; each entry: `name`, `template_path`, `trigger_node_types`, `trigger_tags`, `min_main_nodes`, `naming_pattern`; all fields gracefully default when absent); template recommender in `seed.py` reads `diagram_types` via `load_profile()`; `tests/test_profile.py` additions (PROF-02 atomicity guard, fallback behavior, missing-field defaults). (PROF-01, PROF-02, PROF-03, PROF-04)
- [ ] 21-02-PLAN.md — `graphify --init-diagram-templates [--force]` CLI command in `__main__.py`: writes 6 `.excalidraw.md` stubs (or only profile-listed types if `diagram_types:` present); frontmatter: `excalidraw-plugin: parsed` + `compress: false`; `## Text Elements` block; `## Drawing` block with raw scene JSON (`{"type":"excalidraw","version":2,"source":"graphify","elements":[...],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}`); font family 5 (Excalifont); idempotent without `--force`; `gen-diagram-seed` tag write-back for auto-detected nodes via `vault_adapter.py::compute_merge_plan`; grep denylist test. (TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, TMPL-06)
**UI hint**: no

### Phase 22: Excalidraw Skill & Vault Bridge
**Goal**: A deployable `excalidraw-diagram` skill orchestrates the full seeds → Excalidraw → vault pipeline, with a pure-Python `.excalidraw.md` fallback path that works without mcp_excalidraw.
**Depends on**: Phase 20 (MCP tools `list_diagram_seeds` + `get_diagram_seed`) + Phase 21 (`.excalidraw.md` stubs + template paths from profile).
**Requirements**: SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06 — 6 REQ-IDs.
**Cross-phase rules**: Pure-Python output path must be complete and tested before mcp_excalidraw integration (SKILL-06 ordering invariant). mcp_excalidraw is never a required Python import — graphify's Python code never imports it. Skill install/uninstall are idempotent.
**Success Criteria** (what must be TRUE):
  1. User runs `graphify install --excalidraw` and `.claude/skills/excalidraw-diagram/SKILL.md` is written (idempotent; running twice is safe). User runs `graphify uninstall --excalidraw` and the file is removed.
  2. An agent invokes the `excalidraw-diagram` skill and it executes the full 7-step pipeline: (1) `list_diagram_seeds` → show user seeds; (2) user selects; (3) `get_diagram_seed` → SeedDict; (4) read matching template from vault; (5) build diagram via mcp_excalidraw using SeedDict nodes/edges + template style; (6) export scene → write to vault at `Excalidraw/Diagrams/{naming_pattern}.excalidraw.md`; (7) report seed_id, node count, template used, vault path written.
  3. mcp_excalidraw is unavailable — the skill falls back to the pure-Python `.excalidraw.md` generation path (SeedDict nodes/edges → scene JSON → stub file written directly) and completes without error.
  4. The skill file includes: a `.mcp.json` snippet for obsidian + excalidraw servers, vault folder layout rules, naming conventions, style-matching rules (Excalifont for node labels, font family 5), and a "do not" guard list (no LZ-String, no label-derived IDs, no direct frontmatter writes).
  5. `_PLATFORM_CONFIG` in `__main__.py` contains an `excalidraw` entry; `graphify install --excalidraw` and `graphify uninstall --excalidraw` are registered paths (idempotent, no side-effects on other platform entries).
**Plans**: 2 plans.
- [ ] 22-01-PLAN.md — `graphify/skill-excalidraw.md`: full 7-step orchestration sequence; `.mcp.json` snippet (obsidian + excalidraw servers); vault conventions (folder layout: `Excalidraw/Templates/`, `Excalidraw/Diagrams/`; naming: `{topic}-{layout_type}.excalidraw.md`); style rules (Excalifont font family 5; `strokeColor: "#1e1e2e"`; `backgroundColor: "transparent"`); guard list (`compress: false` assertion, no label-derived IDs, no direct frontmatter writes, no multi-seed in v1.5); pure-Python `.excalidraw.md` fallback path (complete before mcp_excalidraw section); mcp_excalidraw integration section (optional, guarded by availability check). (SKILL-04, SKILL-05, SKILL-06)
- [ ] 22-02-PLAN.md — Install/uninstall wiring in `__main__.py`: new `excalidraw` entry in `_PLATFORM_CONFIG` with `skill_src: "skill-excalidraw.md"`, `skill_dst: ".claude/skills/excalidraw-diagram/SKILL.md"`; `graphify install --excalidraw` handler (idempotent mkdir + copy); `graphify uninstall --excalidraw` handler (idempotent remove); `skill-excalidraw.md` packaged via `MANIFEST.in` + `pyproject.toml` `package_data`; `tests/test_install.py` additions (install/uninstall/idempotency). (SKILL-01, SKILL-02, SKILL-03)
**UI hint**: no


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
| 14. Obsidian Thinking Commands | v1.4 | 6/6 | Complete   | 2026-04-23 |
| 15. Async Background Enrichment | v1.4 | 6/6 | Complete    | 2026-04-22 |
| 16. Graph Argumentation Mode | v1.4 | 3/3 | Complete   | 2026-04-23 |
| 17. Conversational Graph Chat | v1.4 | 3/3 | Complete   | 2026-04-22 |
| 18. Focus-Aware Graph Context | v1.4 | 4/4 | Complete | 2026-04-20 |
| 18.1 v1.4 Gap Closure — Phase 13 Verification Artifacts | v1.4 | 0/3 | Not started | — |
| 18.2 v1.4 Gap Closure — Manifest Metadata + Tech Debt Cleanup | v1.4 | 0/3 | Not started | — |
| 19. Vault Promotion Script (Layer B) | v1.5 | 0/TBD | Planned | — |
| 20. Diagram Seed Engine | v1.5 | 0/3 | Not started | — |
| 21. Profile Extension & Template Bootstrap | v1.5 | 0/2 | Not started | — |
| 22. Excalidraw Skill & Vault Bridge | v1.5 | 0/2 | Not started | — |

---
*Last updated: 2026-04-23 — Phase 19 (Vault Promotion Script Layer B, VAULT-01..05) moved from v1.4 to v1.5 per scope reconciliation; v1.4 scope corrected to Phases 12–18.2 (86 REQ-IDs); v1.5 now Phases 19–22 (32 REQ-IDs: VAULT-01..05, SEED-01..11, PROF-01..04, TMPL-01..06, SKILL-01..06). v1.5 Diagram Intelligence & Excalidraw Bridge opened 2026-04-22.*
