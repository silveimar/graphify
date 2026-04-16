# Ideaverse Integration — Configurable Vault Adapter

## What This Is

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

## Core Value

Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

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

### Active

v1.2 is shipped. No active requirements until `/gsd-new-milestone v1.3` instantiates the next milestone (v1.3 Intelligent Analysis Continuation — phases 9.2, 10, 11, 12 are queued in ROADMAP.md). Run `/gsd-complete-milestone v1.2` to archive the current requirements block into `.planning/milestones/v1.2-REQUIREMENTS.md`.

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

**Shipped v1.2** (2026-04-15) — Intelligent analysis & cross-file extraction (narrow scope). 2 phases, 6 plans, 7/7 derived requirements satisfied (registered post-hoc in `.planning/REQUIREMENTS.md` during Phase 9.1.1), ~1,108 tests. See `.planning/phases/09-*` and `.planning/phases/09.1-*`.

**Codebase:** Python 3.10/3.12; `graphify/` + `tests/` with 108 new test additions during v1.2 scope.

**Next milestone:** v1.3 Intelligent Analysis Continuation (queued — phases 9.2, 10, 11, 12). Run `/gsd-complete-milestone v1.2` to archive the current requirements catalog, then `/gsd-new-milestone v1.3` when ready to plan the next block.

---
*Last updated: 2026-04-15 after v1.2 milestone + Phase 9.1.1 lifecycle cleanup reconciliation*
