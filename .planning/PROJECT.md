# Ideaverse Integration — Configurable Vault Adapter

## What This Is

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

## Core Value

Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

## Requirements

### Validated (v1.0 — Ideaverse Integration milestone)

- [x] `.graphify/` vault-side profile system with `profile.yaml` + `templates/` directory _(v1.0, Phase 1: Foundation)_
- [x] Default built-in profile producing Ideaverse ACE-compatible output (Atlas/Maps, Atlas/Dots, Atlas/Sources) _(v1.0, Phase 1)_
- [x] Profile YAML schema: folder_mapping, mapping_rules, merge behavior, naming conventions, Obsidian config — plus topology section _(v1.0, Phase 1)_
- [x] Vault profile takes precedence over default; graceful fallback when no profile exists _(v1.0, Phase 1)_
- [x] Path-traversal guard on every profile-derived file path (`validate_vault_path`) _(v1.0, Phase 1)_
- [x] Safety helpers: `safe_filename` (NFC normalization, 200-char cap), `safe_tag` (slug/digit-prefix/plus-sign handling), `safe_frontmatter_value` (YAML injection neutralization) _(v1.0, Phase 1)_
- [x] FIX-01..05 pre-existing bug fixes: YAML frontmatter injection, nondeterministic filename dedup, shallow tag sanitization, NFC normalization, filename length cap _(v1.0, Phase 1)_
- [x] Markdown templates with placeholders for note generation per note type (MOC, Dot/Thing, Dot/Statement, Dot/Person, Source, Community Overview) _(v1.0, Phase 2: Template Engine)_
- [x] Proper Ideaverse frontmatter generation: `up:`, `related:`, `collections:`, `created:`, `tags:` with wikilink format _(v1.0, Phase 2)_
- [x] Wikilink generation respecting vault naming conventions _(v1.0, Phase 2)_
- [x] Wayfinder generation in notes (configurable) _(v1.0, Phase 2)_
- [x] Dataview query embedding in MOC notes via two-phase `string.Template.safe_substitute` (no Jinja2) _(v1.0, Phase 2)_
- [x] User template overrides in `.graphify/templates/` with built-in fallback _(v1.0, Phase 2)_
- [x] Configurable filename conventions (title_case, kebab-case, preserve) _(v1.0, Phase 2)_
- [x] Mapping rules support both graph topology (god node, community hub, leaf node) and node content/attributes (`file_type`, `type`, custom attributes) _(v1.0, Phase 3: Mapping Engine)_
- [x] Dual evaluation: attribute rules take precedence, then topology rules, then default _(v1.0, Phase 3)_
- [x] Community-to-MOC mapping: communities above configurable member threshold become MOCs in the configured Maps folder with Dataview queries _(v1.0, Phase 3)_
- [x] God-node-to-Dot mapping: high-degree abstraction nodes become Dots (Things) with connections as body content _(v1.0, Phase 3)_
- [x] Source-file-to-Source mapping: origin files become Source notes in configured Sources folder (with file-type sub-folder routing) _(v1.0, Phase 3)_
- [x] Community-to-MOC threshold configurable (default 3); below-threshold communities collapse into sub-community callouts in parent MOC _(v1.0, Phase 3)_
- [x] Merge/update strategy for existing notes — update by default, preserve user-specified frontmatter fields, skip or replace as configured _(v1.0, Phase 4: Merge Engine)_
- [x] `preserve_fields` list in profile specifies frontmatter fields graphify never overwrites (default: `rank`, `mapState`, `tags`) _(v1.0, Phase 4)_
- [x] Frontmatter field-ordering preserved on update to minimize git diff noise _(v1.0, Phase 4)_
- [x] Configurable merge strategy per profile: `update` (default), `skip`, `replace` _(v1.0, Phase 4)_
- [x] `compute_merge_plan` + `apply_merge_plan` with CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN action types; content-hash skip for idempotent re-runs _(v1.0, Phase 4)_
- [x] Replaces current `to_obsidian()` in `export.py` while maintaining backward compatibility (no profile = Atlas/Dots/Things layout identical to prior output) _(v1.0, Phase 5: Integration & CLI)_
- [x] `graphify --obsidian --dry-run` previews all changes without writing any files _(v1.0, Phase 5)_
- [x] `graphify --validate-profile <vault-path>` runs a four-layer preflight (schema → templates → dead-rules → path-safety) and exits with appropriate status _(v1.0, Phase 5)_

### Active (v1.1 — Context Persistence & Agent Memory)

- [x] Graph snapshot persistence in `graphify-out/snapshots/` for run-over-run comparison _(v1.1, Phase 6: Graph Delta Analysis & Staleness)_
- [x] `GRAPH_DELTA.md` output showing new/removed nodes, community migration, connectivity changes _(v1.1, Phase 6)_
- [x] Per-node staleness metadata (`extracted_at`, `source_hash`, `source_mtime`) with three-state classification (FRESH/STALE/GHOST) _(v1.1, Phase 6)_
- [x] Summary+archive delta pattern (summary for agent context, full diff for search) _(v1.1, Phase 6)_
- [x] MCP mutation tools: annotate nodes, add edges, flag importance, tag with context _(v1.1, Phase 7: MCP Write-Back & Peer Modeling)_
- [x] Peer identity tracking on annotations (agent name, session ID, timestamp) _(v1.1, Phase 7)_
- [x] Session-scoped graph views via MCP _(v1.1, Phase 7)_
- [x] `propose_vault_note` MCP tool with human approval before write _(v1.1, Phase 7)_
- [x] Annotations persist in `graphify-out/annotations.jsonl` across re-runs _(v1.1, Phase 7)_
- [ ] Obsidian round-trip: detect user-modified notes on `--obsidian` re-run
- [ ] Preserve user-authored content blocks during merge (extend v1.0 merge engine)

### Deferred (v1.2+ — template engine extensions from v1.0)

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

## Current Milestone: v1.1 Context Persistence & Agent Memory

**Goal:** Make graphify a persistent, evolving context layer — not just a one-shot graph builder. Enables agents to read AND write to the knowledge graph across sessions, and gives users visibility into how their codebase/corpus changes over time.

**Target features:**
- Graph delta analysis with per-node staleness metadata and snapshot persistence
- MCP write-back with peer modeling, session-scoped views, and `propose_vault_note` tool
- Obsidian round-trip awareness preserving user-authored content on re-run

**Informed by:** Gap analysis against 12 articles + 7 repositories. See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

## Current State

**Milestone v1.0 — Ideaverse Integration — Configurable Vault Adapter: ✅ SHIPPED 2026-04-11**

All five v1.0 phases delivered and verified. The configurable vault adapter is the production `to_obsidian()` code path; there is no separate opt-in flag. 5 phases, 22 plans, 31/31 requirements, 872 tests passing. See `.planning/milestones/` for full archives.

**Milestone v1.1 — Context Persistence & Agent Memory: ○ DEFINING REQUIREMENTS**

Phases 6–8 scoped. Requirements being defined.

---
*Last updated: 2026-04-13 — Phase 6 (Graph Delta Analysis & Staleness) complete*
