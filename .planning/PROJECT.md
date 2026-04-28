# Ideaverse Integration — Configurable Vault Adapter

## What This Is

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

## Core Value

Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

## Current Milestone: (between milestones — v1.7 shipped 2026-04-28; v1.8 unscoped)

**Last shipped (v1.7) — Vault Adapter UX & Template Polish:** Make graphify safe and ergonomic to run from inside an Obsidian vault. Profile-driven output placement, vault-CWD detection with auto-adopt (SEED-vault-root-aware-cli Option C), hardened self-ingestion defenses, `graphify doctor` onboarding + dry-run preview, profile composition (`extends:`/`includes:` with cycle detection + per-key provenance), and the long-deferred template engine extensions (`{{#if_*}}` conditionals, `{{#connections}}` loops, per-note-type Dataview queries). Audit verdict: **passed** (13/13 requirements, 5/5 Nyquist, 1801 tests).

**Deferred to later milestones:**
- v1.8 candidate: Onboarding & Tacit-to-Explicit Elicitation Engine (SEED-001)
- v1.9 candidate: Multi-harness memory export + prompt-injection defenses (SEED-002)
- 2 pre-existing baseline test failures — separate `/gsd-debug` session

---

## Prior Milestones

**Prior milestone (v1.7) shipped 2026-04-28:** Phases 27–31 (5 phases, 14 plans). Vault detection + profile-driven output routing (VAULT-08/09/10), self-ingestion hardening with output-manifest cross-run recovery (VAULT-11/12/13), `graphify doctor` + `--dry-run` (VAULT-14/15), profile composition with `extends:`/`includes:` + cycle detection + per-community templates (CFG-02/03), template engine extensions with `{{#if_*}}`/`{{#connections}}` blocks + per-note-type `dataview_queries` (TMPL-01/02/03). 13/13 requirements, 5/5 Nyquist ratified, 1801 tests passing. Full detail archived to `.planning/milestones/v1.7-*`.

**Prior milestone (v1.6) shipped 2026-04-27:** Phases 23–26 (4 phases, 5 plans). Dedup `source_file` list-crash fix, atomic manifest read-merge-write across 5 writers + AUDIT.md, mandatory dual-artifact persistence baked into all 9 platform skill variants, single-file `CONFIGURING_V1_5.md` walkthrough. 15/15 requirements. Full detail archived to `.planning/milestones/v1.6-*`.

**Prior milestone (v1.5) shipped 2026-04-27:** Phases 19–22 (4 phases, 11 plans). Vault Promotion Script (Layer B), Diagram Seed Engine, Profile Extension & Template Bootstrap, Excalidraw Skill & Vault Bridge. 34/34 requirements. Full detail archived to `.planning/milestones/v1.5-*`.

**Prior milestone (v1.4) shipped 2026-04-22:** Phases 12–18 (7 phases, 32 plans). Heterogeneous Extraction Routing, Agent Capability Manifest + SEED-002 Harness Export, Async Background Enrichment, Focus-Aware Graph Context, Conversational Graph Chat, Graph Argumentation Mode, Obsidian Thinking Commands. 86/86 requirements. Full detail archived to `.planning/milestones/v1.4-*`.

**Seed carryover into v1.7 backlog:**
- SEED-001 (Tacit-to-Explicit Elicitation Engine) — dormant. Trigger: onboarding/discovery becomes a milestone theme.
- SEED-002 (Harness Memory Export) — dormant. claude.yaml shipped in v1.4; multi-harness expansion (codex/letta/honcho/AGENTS.md) + inverse-import deferred pending prompt-injection defenses.

**Carryover tech debt:**
- 2 baseline test failures (`tests/test_detect.py::test_detect_skips_dotfiles`, `tests/test_extract.py::test_collect_files_from_dir`) — pre-existing on base 24810ec; deferred to v1.7 `/gsd-debug` session.

## Requirements

### Validated

**v1.0 — Ideaverse Integration:**
- ✓ `.graphify/` vault-side profile system with `profile.yaml` + `templates/` directory — v1.0
- ✓ Default built-in profile producing Ideaverse ACE-compatible output — v1.0
- ✓ Profile YAML schema with folder_mapping, mapping_rules, merge behavior, naming, topology — v1.0
- ✓ Vault profile precedence with graceful fallback — v1.0
- ✓ Path-traversal guard (`validate_vault_path`) — v1.0
- ✓ Safety helpers: `safe_filename`, `safe_tag`, `safe_frontmatter_value` — v1.0
- ✓ FIX-01..05 pre-existing bug fixes — v1.0
- ✓ 6 built-in Markdown templates (MOC, Thing, Statement, Person, Source, Community Overview) — v1.0
- ✓ Ideaverse frontmatter generation with wikilinks — v1.0
- ✓ Wayfinder generation, Dataview query embedding, user template overrides — v1.0
- ✓ Configurable filename conventions (title_case, kebab-case, preserve) — v1.0
- ✓ Dual mapping (topology + content attributes) with first-match-wins precedence — v1.0
- ✓ Community-to-MOC, god-node-to-Dot, source-file-to-Source mapping — v1.0
- ✓ Merge engine with CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN actions — v1.0
- ✓ `preserve_fields`, field-ordering preservation, configurable merge strategy — v1.0
- ✓ Refactored `to_obsidian()` with backward compatibility — v1.0
- ✓ `graphify --obsidian --dry-run` and `graphify --validate-profile` CLI flags — v1.0

**v1.1 — Context Persistence & Agent Memory:**
- ✓ Graph snapshot persistence in `graphify-out/snapshots/` with FIFO retention — v1.1
- ✓ `GRAPH_DELTA.md` with summary+archive pattern (added/removed nodes, community migration, connectivity changes) — v1.1
- ✓ Per-node staleness metadata (FRESH/STALE/GHOST) with `extracted_at`, `source_hash`, `source_mtime` — v1.1
- ✓ MCP mutation tools: `annotate_node`, `flag_node`, `add_edge` with JSONL sidecar persistence — v1.1
- ✓ Peer identity tracking (`peer_id`, `session_id`, `timestamp`) on all annotations — v1.1
- ✓ Session-scoped graph views via MCP — v1.1
- ✓ `propose_vault_note` MCP tool with `graphify approve` CLI for human-in-the-loop — v1.1
- ✓ Obsidian round-trip: content-hash manifest detects user-modified notes on re-run — v1.1
- ✓ User sentinel blocks (`GRAPHIFY_USER_START/END`) — inviolable preservation zones — v1.1
- ✓ `--force` flag, dry-run source annotations, merge plan audit trail — v1.1
- ✓ MCP `get_node` provenance (staleness classification) and `get_agent_edges` query tool — v1.1

**v1.2 — Intelligent Analysis & Cross-File Extraction:** *(Shipped 2026-04-15, narrow scope: phases 9 + 9.1)*
- ✓ Configurable analysis lenses (security, architecture, complexity, onboarding) with autoreason tournament A/B/AB/Borda — v1.2-REQ-09-A
- ✓ "No finding" competes as first-class Borda option (Clean verdict) — v1.2-REQ-09-B
- ✓ Tournament output in `GRAPH_ANALYSIS.md` separate from `GRAPH_REPORT.md` (D-80) — v1.2-REQ-09-C
- ✓ Per-edge traversal counters via MCP query telemetry (`serve.py`) — v1.2-REQ-09.1-A
- ✓ Hot-path strengthening and unused-path decay (`_edge_weight` + `_decay_telemetry`) — v1.2-REQ-09.1-B
- ✓ 2-hop A→C derived edges with INFERRED confidence via `_check_derived_edges` — v1.2-REQ-09.1-C
- ✓ Hot/cold paths surfaced in `GRAPH_REPORT.md` "## Usage Patterns" section — v1.2-REQ-09.1-D

**v1.3 — Intelligent Analysis Continuation:** *(Shipped 2026-04-17, phases 9.2 + 10 + 11)*
- ✓ Token-aware 3-layer MCP `graph_query` with `budget` parameter and cardinality estimation — TOKEN-01, TOKEN-02
- ✓ Bidirectional BFS for depth ≥ 3 with 3-state status return (`ok` / `frontiers_disjoint` / `budget_exhausted`) — TOKEN-03
- ✓ Import-connected file clustering with token-budget soft cap + topological ordering — GRAPH-01
- ✓ Post-extraction entity deduplication via fuzzy (`difflib`) + embedding (`sentence-transformers`) — GRAPH-02
- ✓ Canonical merge with edge re-routing, weight aggregation (sum/max), EXTRACTED>INFERRED>AMBIGUOUS precedence — GRAPH-03
- ✓ Cross-source ontology alignment (stretch: same entity across `.py` + `.md` + `tests/` resolves to one canonical node) — GRAPH-04
- ✓ `/context` slash command — graph_summary MCP tool returns god nodes + top communities + recent deltas — SLASH-01
- ✓ `/trace <entity>` slash command — entity_trace walks snapshot chain with memory discipline — SLASH-02
- ✓ `/connect <topic-a> <topic-b>` slash command — shortest path + globally surprising bridges as distinct sections — SLASH-03
- ✓ `/drift` slash command — drift_nodes trend vectors (community / degree / edge-density) across last N snapshots — SLASH-04
- ✓ `/emerge` slash command — newly_formed_clusters via v1.1 delta machinery — SLASH-05
- ✓ `/ghost` slash command (stretch, annotation-grounded with anti-impersonation guard) — SLASH-06
- ✓ `/challenge <belief>` slash command (stretch, anti-fabrication guard + supporting/contradicting sections) — SLASH-07

**v1.4 — Agent Discoverability & Obsidian Workflows:** *(Shipped 2026-04-22, phases 12 + 13 + 14 + 15 + 16 + 17 + 18 + 18.1 + 18.2; 72/86 P1+P2 REQ-IDs, 14 P2 carve-outs deferred)*
- ✓ Per-file AST-complexity-classified extraction routing (cheap/mid/expensive model tiers) with parallel fan-out, `GRAPHIFY_COST_CEILING` pre-flight guard, model-isolated cache keys, `routing.json` sidecar audit — ROUTE-01..07
- ✓ Introspection-driven MCP capability manifest (`server.json` + live `manifest.json`, drift detection via `meta.manifest_content_hash`, CI validation) — MANIFEST-01..08
- ✓ SEED-002 harness memory export — `graphify harness export --target claude` produces SOUL/HEARTBEAT/USER with byte-equal round-trip fidelity — HARNESS-01..06
- ✓ Vault-scoped Obsidian thinking commands (`/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind`) with `target:` filtering + `propose_vault_note + approve` trust boundary + directory-scan command registration — OBSCMD-00..08
- ✓ Async background enrichment — four-pass overlay-only `enrichment.json`, `fcntl.flock`-coordinated with foreground runs, snapshot-pinned, atomic `.tmp` + `os.replace` commits — ENRICH-01..12
- ✓ SPAR-Kit graph argumentation — `argue_topic` MCP tool, 4-lens × 6-round cap, blind-label shuffle, Jaccard early-stop, `{claim, cites: [node_id]}` schema rejecting fabricated IDs, `dissent`/`inconclusive` valid outputs — ARGUE-01..10
- ✓ Two-stage structurally-enforced conversational chat — `chat(query, session_id)` Stage 1 tool-call only / Stage 2 compose-from-results with `{node_id, label, source_file}` citations, recursion guard, `/graphify-ask` command — CHAT-01..09
- ✓ Focus-aware graph context — `get_focus_context(focus_hint)` BFS ego-graph + community summary, pull-model, codifies v1.3 CR-01 via `snapshot.py::root` → `project_root` rename — FOCUS-01..09

**v1.5 — Diagram Intelligence & Excalidraw Bridge:** *(Shipped 2026-04-27, phases 19 + 20 + 21 + 22; 34/34 requirements)*
- ✓ Vault Promotion Script (Layer B) — `graphify vault-promote` CLI writes 7-folder Ideaverse-Pro 2.5 notes (Atlas/Dots/{Things,Statements,People,Quotes,Questions}, Atlas/Maps, Atlas/Sources) with full frontmatter, atomic SHA-256 manifest, append-first import-log, D-13 overwrite-self-skip-foreign policy, and 3-layer taxonomy merge — VAULT-01..07
- ✓ Diagram Seed Engine — `possible_diagram_seed` auto-tagging (god nodes + cross-community surprises), `detect_user_seeds()` reader for `gen-diagram-seed[/type]` vault tag contract, `graphify/seed.py` 13-step `build_all_seeds` orchestrator with 6-predicate D-05 layout heuristic, >60%-Jaccard single-pass dedup, max-20 cap, deterministic sha256 element IDs, atomic-write + manifest-last lifecycle, `graphify --diagram-seeds` CLI, and MANIFEST-05 atomic MCP pair `list_diagram_seeds` + `get_diagram_seed` (closure-local `_resolve_alias` per D-16, `_SEED_ID_RE` traversal defense) — SEED-01..11
- ✓ Profile Extension & Template Bootstrap — `profile.yaml` `diagram_types:` schema with 6 built-in defaults (architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph), D-06 gating + D-07 tiebreak, `graphify --init-diagram-templates [--force]` writes `.excalidraw.md` stubs with hardcoded `compress: false` (one-way door enforced via lzstring-import denylist), TMPL-06 vault-write denylist test — PROF-01..04, TMPL-01..06
- ✓ Excalidraw Skill & Vault Bridge — deployable `excalidraw-diagram` skill orchestrates seeds → Excalidraw → vault pipeline with pure-Python `graphify/excalidraw.py` fallback (`write_diagram`, `layout_for`, `SCENE_JSON_SKELETON`), `graphify install excalidraw` unified dispatcher, `_PLATFORM_CONFIG` 12-key entry — SKILL-01..06
- ✓ End-to-end flow verified: `vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → skill invocation. All 7 cross-phase wires confirmed by `gsd-integration-checker`. Nyquist compliance: all 4 phases formally signed off.

**v1.6 — Hardening & Onboarding:** *(Shipped 2026-04-27, phases 23 + 24 + 25 + 26; 15/15 requirements)*
- ✓ Dedup `source_file` list-handling fix — `dedup.py` edge-merge delegates list-shape handling to `analyze._iter_sources`; cross-type regression test green (Issue #4) — DEDUP-01..03
- ✓ Manifest writer hardening — `RoutingAudit.flush` + `write_manifest_atomic` perform read-merge-write keyed by row identity (path/tool name) before atomic `.tmp` + `os.replace`; subpath isolation regression tests assert sibling rows preserved; AUDIT.md enumerates all 5 on-disk writers with PATCHED/LOCKED/DEFERRED dispositions — MANIFEST-09..12
- ✓ Mandatory dual-artifact persistence — sentinel "Mandatory response persistence" block emitted byte-equal across all 9 platform skill variants (`skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-openclaw.md`, `skill-droid.md`, `skill-trae.md`, `skill-trae-cn.md`, copilot/antigravity); 12 parametrized tests over `_PLATFORM_CONFIG` enforce drift-lock — SKILLMEM-01..04
- ✓ v1.5 configuration walkthrough — single-file `CONFIGURING_V1_5.md` (414 lines) covers `vault-promote → --diagram-seeds → --init-diagram-templates → install excalidraw → /excalidraw-diagram` end-to-end with annotated `.graphify/profile.yaml` (6 built-ins + custom `decision-tree`) and verbatim MCP `list_diagram_seeds` / `get_diagram_seed` / `_resolve_alias` quotes; README cross-link added — DOCS-01..04

### Active

**v1.7 — (unscoped):** *(scope TBD; re-scope via `/gsd-new-milestone`)*

### Deferred (v1.3+ — template engine extensions from v1.0)

- [ ] Conditional template sections (`{{#if_god_node}}...{{/if}}` guards) — TMPL-01
- [ ] Loop blocks for connections in templates (`{{#connections}}...{{/connections}}`) — TMPL-02
- [ ] Custom Dataview query templates per note type in profile — TMPL-03
- [ ] Profile includes/extends mechanism (compose profiles from fragments) — CFG-02
- [ ] Per-community template overrides (specific communities get custom templates) — CFG-03
- [ ] `.obsidian/graph.json` management (revisit OBS-01/02 as plugin-side integration) — if user demand emerges

### Out of Scope

- Designing or generating the vault framework itself (ACE, Sefirot, Guitton, LSA, or fused framework) — separate project
- Wiki article generation (`wiki.py`) — existing separate system, not part of this integration
- Calendar and Efforts population — graphify produces knowledge (Atlas-equivalent), not time/action data
- Obsidian plugin development — output is standard markdown + frontmatter
- Real-time sync or watch mode integration — this is a batch injection operation
- Neo4j or other export formats — this is Obsidian-specific
- `.obsidian/graph.json` community color generation (OBS-01, OBS-02) — de-scoped in D-74; `to_obsidian()` no longer manages graph.json directly. The `safe_tag()` invariant that produced the `community/<slug>` form is preserved and anchored by a regression test, but single-file graph.json read-merge-write lives outside the library-level entry point in v1.0

## Context

### v1.0 shipped (2026-04-11)

- **Delivered:** Configurable Obsidian vault adapter. Five new/rewritten modules (`profile.py`, `templates.py`, `mapping.py`, `merge.py`, refactored `export.py`), two new CLI entry points (`graphify --obsidian [--dry-run]`, `graphify --validate-profile`), and a fully refactored `to_obsidian()` pipeline that reads a vault-side `.graphify/profile.yaml` + templates and produces notes with correct frontmatter, wikilinks, folder placement, and merge semantics. Backward compatible when no vault profile exists (default `_DEFAULT_PROFILE` emits Ideaverse ACE Atlas/ layout).
- **Codebase state:** 11,620 LOC across 24 Python modules under `graphify/`; 10,500 LOC across 33 test files under `tests/`; 872 tests passing.
- **Shipped in:** 5 phases, 22 plans, ~172 commits over 2 days (2026-04-09 → 2026-04-11), fully verified with goal-backward VERIFICATION.md for each phase plus milestone audit (31/31 in-scope requirements satisfied, 2 de-scoped via D-74).
- **Tech stack additions:** PyYAML as optional `obsidian` extra (guarded regression test in `tests/test_pyproject.py`).

### v1.1 Phase 7 complete (2026-04-13)

- **Delivered:** MCP write-back and peer modeling. Extended `serve.py` with 5 new MCP tools (annotate_node, flag_node, add_edge, propose_vault_note, get_annotations), JSONL/JSON sidecar persistence, peer/session identity tracking, mtime-based graph reload, and startup compaction. Added `graphify approve` CLI subcommand for human-in-the-loop proposal review. graph.json never mutated by any tool.
- **Test count:** 952 passing (57 new across `test_serve.py` and `test_approve.py`).
- **Shipped in:** 3 plans across 3 waves, 11 commits.

### v1.1 Phase 8 complete (2026-04-13)

- **Delivered:** Obsidian round-trip awareness. Content-hash manifest (`vault-manifest.json`) tracks what graphify wrote per note. On re-run, user-modified notes receive SKIP_PRESERVE — user content never overwritten. User sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) provide explicit preservation zones that survive even REPLACE strategy and `--force` mode. `--force` flag bypasses whole-note user-modified detection while respecting sentinel blocks. Dry-run output enhanced with source annotations (`[user]`/`[both]`) and summary preamble.
- **Test count:** 985 passing (33 new across 5 test classes in `test_merge.py`).
- **Shipped in:** 3 plans across 3 waves, 9 feature commits.

### v1.2 shipped (2026-04-15)

- **Delivered:** Intelligent analysis and usage-weighted graph self-improvement. Phase 09 added the autoreason tournament (`render_analysis_context` in `analyze.py:456`, `render_analysis` in `report.py:185`, full A/B/AB/Borda tournament orchestration in `skill.md:1324-1546` writing to `GRAPH_ANALYSIS.md` — separate from `GRAPH_REPORT.md` per D-80). Phase 09.1 added query telemetry (`_record_traversal`, `_save_telemetry`, `_edge_weight`, `_decay_telemetry` in `serve.py`), 2-hop derived shortcut edges with INFERRED confidence (`_check_derived_edges` writes to `agent-edges.json`), and hot/cold path surfacing (`_compute_hot_cold` in `report.py:16`, "## Usage Patterns" section at `report.py:219`). Skill pipeline wired to pass `usage_data=` to all 3 `generate()` call sites and run `_decay_telemetry` at both full-rebuild points.
- **Test count:** ~1,108 passing (108 new across `test_serve.py` + `test_report.py`).
- **Shipped in:** 2 phases, 6 plans, ~20 feature commits over 2 days (2026-04-14 → 2026-04-15). Formal goal-backward verification recorded in `09-VERIFICATION.md` (11/12, 1 human_needed resolved via `09-HUMAN-UAT.md` 3/3) and `09.1-VERIFICATION.md` (13/13, generated via Phase 9.1.1 Plan 01 from existing UAT/VALIDATION/SECURITY evidence). 14/14 security threats closed (ASVS L1).
- **Narrow-scope reconciliation:** Milestone v1.2 originally listed 6 phases (9, 9.1, 9.2, 10, 11, 12) in the ROADMAP. During the `/gsd-audit-milestone` review on 2026-04-16 the operator locked v1.2 at phases 9 + 9.1. Phases 9.2, 10, 11, 12 moved to a new milestone v1.3 "Intelligent Analysis Continuation"; the original v1.3 (Agent Discoverability) renamed to v1.4. Reconciliation executed by Phase 9.1.1 lifecycle cleanup.

### Enduring background (carries across milestones)

- The target use case is the owner's fused Obsidian framework (Ideaverse ACE + Sefirot + Guitton + LSA Research), being designed in a separate project. graphify must be ready to receive that profile when it's defined — v1.0 delivers the adapter; the framework itself arrives later.
- Ideaverse Pro 2.5 uses rich YAML frontmatter (`up:`, `related:`, `collections:`, `rank:`, `mapState:`, `tags:`), hierarchical folder structure (Atlas/Dots/{Things,Statements,People,Quotes,Questions}, Atlas/Maps/, Atlas/Sources/{Books,Movies,...}), MOCs with Dataview queries, wayfinders for navigation, and garden/architect maturity tags. v1.0's built-in default profile emits this shape.
- The `.graphify/` directory pattern follows established conventions (`.editorconfig`, `.obsidian/`) — vault-owned, versioned with the vault, framework-agnostic.
- Graph data available for mapping: node attributes (label, file_type, source_file, source_location, community), edge attributes (relation, confidence, source_file, weight), community data (members, cohesion, labels), analysis data (god nodes, surprising connections, bridge nodes).

## Constraints

- **Python 3.10+**: Must work on CI targets (Python 3.10 and 3.12)
- **No new required dependencies**: Profile parsing uses stdlib (`yaml` via PyYAML already optional, `json` stdlib). Template rendering uses simple string substitution, not Jinja2.
- **Backward compatible**: Running `graphify --obsidian` without a profile in the target vault must produce output similar to current behavior
- **Existing test patterns**: Pure unit tests, no network calls, no filesystem side effects outside `tmp_path`
- **Security**: All file paths confined to output directory per `security.py` patterns. Template placeholders must be sanitized (no injection via node labels).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vault-side `.graphify/` profile over CLI flags | Vault owns its framework definition; portable, versionable, framework-agnostic | ✓ Validated in v1.0 — `profile.py::load_profile` discovers `.graphify/profile.yaml` per vault, CLI flags stay minimal (`--validate-profile`, `--obsidian [--dry-run]`) |
| YAML for profile, Markdown for templates | YAML is declarative and familiar; MD templates are native to Obsidian users | ✓ Validated in v1.0 — PyYAML as optional `obsidian` extra; `.graphify/templates/*.md` supplies overrides for 6 built-in note types |
| Dual mapping (topology + content attributes) | Some note types are determined by graph position (god node → Thing), others by content (file_type: person → Person) | ✓ Validated in v1.0 Phase 3 — `mapping.py::classify` implements attribute > topology > default precedence, first-match-wins; 5/5 must-haves verified |
| Default = Ideaverse ACE structure | Most popular Obsidian framework; sensible fallback; validates the system works | ✓ Validated in v1.0 — `_DEFAULT_PROFILE` emits `Atlas/Maps/`, `Atlas/Dots/Things/`, etc.; MRG-05 (backward compat) PASS |
| Update-by-default merge strategy | Users expect injected content to refresh, not duplicate; preserving user-edited fields prevents data loss | ✓ Validated in v1.0 Phase 4 — `merge.py` ships `compute_merge_plan`/`apply_merge_plan`; D-67 sentinel blocks + D-64 field policies + D-72 orphan-preservation locked in |
| Simple placeholder templating (no Jinja2) | Avoids new dependency; templates stay readable as plain markdown; sufficient for frontmatter + body generation | ✓ Validated in v1.0 Phase 2 — `string.Template.safe_substitute` works for KNOWN_VARS + two-phase Dataview wrap; zero Jinja2 dependency |
| **D-73**: CLI is utilities-only; the skill is the pipeline driver | `graphify --obsidian` and `graphify --validate-profile` exist as direct utility entry points, but the full pipeline (detect → extract → build → cluster → analyze → report → export) runs via the skill, not via a single CLI verb. Avoids rebuilding agent orchestration in Python. | ✓ Validated in v1.0 Phase 5 — `__main__.py` exposes two new flags for direct utility access; `skill.md` drives the full pipeline with embedded Python blocks. Known limitation: `dry_run = False` in skill.md:547 is a placeholder the agent flips when `--dry-run` is parsed. |
| **D-74**: De-scope `.obsidian/graph.json` generation from `to_obsidian()` | Phase 5 integration refactor consolidated `to_obsidian()` around the merge engine and profile-driven mapping. Writing `.obsidian/graph.json` directly from the library entry point couples vault-config-file management with note generation, which conflicts with the "library is a pipeline, skill is the driver" shape from D-73. The `safe_tag()` helper that produced `community/<slug>` labels remains in `profile.py` and is used by note frontmatter tags + Dataview queries; a regression test in `test_profile.py::test_obs01_obs02_safe_tag_regression_anchor` locks the slugification invariant. | ✓ Accepted in v1.0 Phase 5 refactor — moves OBS-01 and OBS-02 to Out of Scope for v1.0. ⚠️ Revisit if a future release needs plugin-side `.obsidian/graph.json` management, at which point the feature likely lives behind a flag or in a separate module, not in `to_obsidian()`. |

**Phase-level decisions (D-01..D-72):** Archived alongside each phase in `.planning/milestones/v1.0-phases/*-CONTEXT.md` (if phases are archived) or preserved in the live phase directories. They cover implementation-level choices (sentinel block shapes, field-policy precedence, NFC normalization placement, dry-run return-type, etc.) and are referenced by the milestone audit report in `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.
| **D-73**: CLI is utilities-only; the skill is the pipeline driver | `graphify --obsidian` and `graphify --validate-profile` exist as direct utility entry points, but the full pipeline (detect → extract → build → cluster → analyze → report → export) runs via the skill, not via a single CLI verb. Avoids rebuilding agent orchestration in Python. | Validated in Phase 5 — `__main__.py` exposes two new flags for direct utility access; `skill.md` drives the full pipeline with embedded Python blocks. Known limitation: `dry_run = False` in skill.md:547 is a placeholder the agent flips when `--dry-run` is parsed. |
| **D-74**: De-scope `.obsidian/graph.json` generation from `to_obsidian()` | Phase 5 integration refactor consolidated `to_obsidian()` around the merge engine and profile-driven mapping. Writing `.obsidian/graph.json` directly from the library entry point couples vault-config-file management with note generation, which conflicts with the "library is a pipeline, skill is the driver" shape from D-73. The `safe_tag()` helper that produced `community/<slug>` labels remains in `profile.py` and is used by note frontmatter tags + Dataview queries; a regression test in `test_profile.py::test_obs01_obs02_safe_tag_regression_anchor` locks the slugification invariant. | Accepted in Phase 5 refactor — moves OBS-01 and OBS-02 to Out of Scope for v1.0. Revisit if a future release needs plugin-side `.obsidian/graph.json` management, at which point the feature likely lives behind a flag or in a separate module, not in `to_obsidian()`. |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Current State

**Shipped v1.0** (2026-04-11) — Configurable Obsidian vault adapter. 5 phases, 22 plans, 31/31 requirements, 872 tests. See `.planning/milestones/v1.0-*`.

**Shipped v1.1** (2026-04-13) — Context persistence and agent memory. 5 phases, 12 plans, 25/25 requirements, 1,000 tests. See `.planning/milestones/v1.1-*`.

**Shipped v1.2** (2026-04-15) — Intelligent analysis & cross-file extraction (narrow scope, + Phase 9.1.1 retroactive lifecycle cleanup). 3 phases, 9 plans, 10/10 requirements satisfied, milestone audit passed (5/5 integration links WIRED, 3/3 E2E flows COMPLETE). See `.planning/milestones/v1.2-*`.

**Shipped v1.3** (2026-04-17) — Intelligent analysis continuation. 3 phases (9.2, 10, 11), 19 plans, 14/15 requirements satisfied (TOKEN-04 Bloom filter stretch deferred per D-09). Progressive Graph Retrieval (token-aware 3-layer MCP `query_graph` + bidirectional BFS), Cross-File Semantic Extraction with Entity Deduplication (import-cluster batching + fuzzy/embedding entity merge with alias redirect), Narrative Mode as Interactive Slash Commands (7 `.claude/commands/*.md` files + 5 new MCP tools). 2 production-breaking bugs caught by post-execution code review and auto-fixed before shipping. See `.planning/milestones/v1.3-*`.

**Shipped v1.4** (2026-04-22) — Agent Discoverability & Obsidian Workflows. 7 phases (12–18), 32 plans, 86/86 requirements (72/86 P1+P2; 14 P2 carve-outs deferred). Heterogeneous Extraction Routing, MCP capability manifest + harness memory export, vault-scoped Obsidian commands, async enrichment, SPAR-Kit argumentation, conversational graph chat, focus-aware graph context. See `.planning/milestones/v1.4-*`.

**Shipped v1.5** (2026-04-27) — Diagram Intelligence & Excalidraw Bridge. 4 phases (19–22), 11 plans, 34/34 requirements. Vault-promotion CLI writing 7-folder Ideaverse Pro 2.5 notes; diagram seed engine with auto-tagging + MCP `list_diagram_seeds`/`get_diagram_seed` pair; profile `diagram_types:` schema with 6 built-in defaults + `--init-diagram-templates` Excalidraw stubs (compress=false one-way door); deployable `excalidraw-diagram` skill orchestrating seeds → Excalidraw → vault with pure-Python fallback. End-to-end flow verified across 7 cross-phase wires. Nyquist compliance: all 4 phases signed off. See `.planning/milestones/v1.5-*`.

**Shipped v1.6** (2026-04-27) — Hardening & Onboarding. 4 phases (23–26), 5 plans, 15/15 requirements. Dedup `--dedup-cross-type` no longer crashes on list-form `source_file` (Issue #4); 5 on-disk manifest writers patched to atomic read-merge-write by row identity preventing subpath sibling-row erasure; mandatory dual-artifact response-persistence sentinel baked byte-equal into all 9 platform skill variants with parametrized drift-lock; single-file `CONFIGURING_V1_5.md` walkthrough lets a new user run the v1.5 pipeline end-to-end from docs alone. All 4 phases Nyquist-compliant. Status `tech_debt` (no blockers; 2 pre-existing baseline test failures deferred to v1.7). See `.planning/milestones/v1.6-*`.

**Codebase at v1.6 close:** Python 3.10/3.12. v1.6 added +3,159 / −65 LOC across 27 files (16 commits, single-day milestone 2026-04-27). Full test suite still green at 1,524+ passing (excluding 2 pre-existing baseline failures inherited from base 24810ec).

## Next Milestone Goals

v1.7 scoped 2026-04-27 as **Vault Adapter UX & Template Polish** (see Current Milestone above).

Backlog beyond v1.7:
- v1.8 candidate: Onboarding & Tacit-to-Explicit (SEED-001 trigger conditions met when discovery becomes a primary theme)
- v1.9 candidate: Multi-harness memory expansion + prompt-injection defenses (SEED-002 follow-on)
- 2 pre-existing baseline test failures (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`) — separate `/gsd-debug` session

---
*Last updated: 2026-04-27 — v1.7 Vault Adapter UX & Template Polish scoped*
