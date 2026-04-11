# Ideaverse Integration — Configurable Vault Adapter

## What This Is

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

## Core Value

Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

## Requirements

### Validated

- [x] Markdown templates with placeholders for note generation per note type (MOC, Dot/Thing, Dot/Statement, Dot/Person, Source, Community Overview) _(Validated in Phase 2: Template Engine)_
- [x] Proper Ideaverse frontmatter generation: `up:`, `related:`, `collections:`, `created:`, `tags:` with wikilink format _(Validated in Phase 2: Template Engine)_
- [x] Wikilink generation respecting vault naming conventions _(Validated in Phase 2: Template Engine)_
- [x] Wayfinder generation in notes (configurable) _(Validated in Phase 2: Template Engine)_
- [x] Dataview query embedding in MOC notes (configurable) _(Validated in Phase 2: Template Engine)_

### Active

- [ ] `.graphify/` vault-side profile system with `profile.yaml` + `templates/` directory
- [ ] Default built-in profile producing Ideaverse ACE-compatible output (Atlas/Maps, Atlas/Dots, Atlas/Sources)
- [ ] Profile YAML schema: folder mapping, mapping rules, merge behavior, naming conventions, Obsidian config
- [ ] Mapping rules support both graph topology (god node, community hub, leaf node) and node content/attributes (`file_type`, `type`, custom attributes)
- [ ] Vault profile takes precedence over default; graceful fallback when no profile exists
- [x] Merge/update strategy for existing notes — update by default, preserve user-specified frontmatter fields, skip or replace as configured _(Validated in Phase 4: Merge Engine)_
- [x] Community-to-MOC mapping: communities above configurable member threshold become MOCs in the configured Maps folder with Dataview queries _(Validated in Phase 3: Mapping Engine)_
- [x] God-node-to-Dot mapping: high-degree abstraction nodes become Dots (Things) with connections as body content _(Validated in Phase 3: Mapping Engine)_
- [x] Source-file-to-Source mapping: origin files become Source notes in configured Sources folder _(Validated in Phase 3: Mapping Engine)_
- [x] Replaces current `to_obsidian()` in `export.py` while maintaining backward compatibility (no profile = similar output to current) _(Validated in Phase 5: Integration & CLI — confirmed by live dry-run against fixture graph and 872 passing tests)_

### Out of Scope

- Designing or generating the vault framework itself (ACE, Sefirot, Guitton, LSA, or fused framework) — separate project
- Wiki article generation (`wiki.py`) — existing separate system, not part of this integration
- Calendar and Efforts population — graphify produces knowledge (Atlas-equivalent), not time/action data
- Obsidian plugin development — output is standard markdown + frontmatter
- Real-time sync or watch mode integration — this is a batch injection operation
- Neo4j or other export formats — this is Obsidian-specific
- `.obsidian/graph.json` community color generation (OBS-01, OBS-02) — de-scoped in D-74; `to_obsidian()` no longer manages graph.json directly. The `safe_tag()` invariant that produced the `community/<slug>` form is preserved and anchored by a regression test, but single-file graph.json read-merge-write lives outside the library-level entry point in v1.0

## Context

- graphify already has a working `to_obsidian()` function in `export.py` (lines 440-679) that produces flat vaults with community tags, basic wikilinks, and a single Dataview query per community. This is the baseline to evolve.
- The target use case is the owner's fused Obsidian framework (Ideaverse ACE + Sefirot + Guitton + LSA Research), being designed in a separate project. graphify must be ready to receive that profile when it's defined.
- Ideaverse Pro 2.5 uses rich YAML frontmatter (`up:`, `related:`, `collections:`, `rank:`, `mapState:`, `tags:`), hierarchical folder structure (Atlas/Dots/{Things,Statements,People,Quotes,Questions}, Atlas/Maps/, Atlas/Sources/{Books,Movies,...}), MOCs with Dataview queries, wayfinders for navigation, and garden/architect maturity tags.
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
| Vault-side `.graphify/` profile over CLI flags | Vault owns its framework definition; portable, versionable, framework-agnostic | — Pending |
| YAML for profile, Markdown for templates | YAML is declarative and familiar; MD templates are native to Obsidian users | — Pending |
| Dual mapping (topology + content attributes) | Some note types are determined by graph position (god node → Thing), others by content (file_type: person → Person) | — Pending |
| Default = Ideaverse ACE structure | Most popular Obsidian framework; sensible fallback; validates the system works | — Pending |
| Update-by-default merge strategy | Users expect injected content to refresh, not duplicate; preserving user-edited fields prevents data loss | Validated in Phase 4 — `merge.py` ships `compute_merge_plan`/`apply_merge_plan`; D-67 sentinel blocks + D-64 field policies + D-72 orphan-preservation locked in |
| Simple placeholder templating (no Jinja2) | Avoids new dependency; templates stay readable as plain markdown; sufficient for frontmatter + body generation | Validated in Phase 2 — `string.Template.safe_substitute` works for KNOWN_VARS + two-phase Dataview wrap |
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

- **Phase 1 (Foundation)** — ✅ Complete. `graphify/profile.py` delivers profile loading, validation, safe-filename/tag helpers, and security primitives.
- **Phase 2 (Template Engine)** — ✅ Complete. `graphify/templates.py` renders MOC, Community, Thing, Statement, Person, and Source notes via `string.Template` + 6 built-in `.md` templates shipped in the wheel. `render_note()` and `render_moc()` are the public entry points.
- **Phase 3 (Mapping Engine)** — ✅ Complete. `ClassificationContext` drives topology + attribute classification.
- **Phase 4 (Merge Engine)** — ✅ Complete. `graphify/merge.py` delivers `compute_merge_plan` (pure) and `apply_merge_plan` (atomic writes, content-hash skip, ORPHAN-preservation). 818 project tests passing, 28/28 must-haves verified.
- **Phase 5 (Integration & CLI)** — Next. Wires the merge engine into the `--obsidian` CLI path with `--dry-run` support.

---
*Last updated: 2026-04-11 after Phase 4 completion*
