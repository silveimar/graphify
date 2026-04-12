# Milestones

## v1.0 Ideaverse Integration — Configurable Vault Adapter (Shipped: 2026-04-11)

**Delivered:** Configurable output adapter that injects graphify knowledge graphs into any Obsidian vault framework via a declarative `.graphify/profile.yaml`. Replaces the monolithic `to_obsidian()` with a four-component pipeline (profile → mapping → templates → merge) and wires it behind two new CLI entry points. Backward-compatible when no vault profile exists (default profile emits Ideaverse ACE Atlas/ layout).

**Phases completed:** 5 phases, 22 plans, ~172 commits
**Timeline:** 2026-04-09 → 2026-04-11 (2 days)
**Codebase delta:** 11,620 LOC across 24 Python modules (`graphify/`) + 10,500 LOC across 33 test files (`tests/`)
**Test suite:** 872 passing (up from pre-milestone baseline)
**Requirements:** 31/33 satisfied (2 de-scoped via D-74 — see Out of Scope in archived requirements)

### Key Accomplishments

1. **Configurable vault profile system** (Phase 1: Foundation) — `.graphify/profile.yaml` discovery, deep-merge over built-in defaults, schema validation with actionable errors, path-traversal guard (`validate_vault_path`). Standalone `profile.py` module with no `export.py` coupling (D-16). Ships `_DEFAULT_PROFILE` constant producing Ideaverse ACE Atlas/ layout.

2. **Safety helpers + pre-existing bug fixes** (Phase 1 Plan 2) — `safe_filename` with NFC normalization (FIX-04) and 200-char length cap (FIX-05), `safe_tag` handling slashes / plus signs / digit-at-start (FIX-03), `safe_frontmatter_value` neutralizing YAML injection (FIX-01), and deterministic filename deduplication sorted on `(source_file, label)` (FIX-02). PyYAML added as optional `obsidian` extra.

3. **Template engine with placeholder substitution** (Phase 2: Template Engine) — `graphify/templates.py` delivers 6 built-in note types (MOC, Thing, Statement, Person, Source, Community Overview) via `string.Template.safe_substitute` with KNOWN_VARS + two-phase Dataview wrap. User template overrides in `.graphify/templates/` with built-in fallback on error. Wayfinder navigation callouts. Configurable filename conventions.

4. **Mapping engine with dual-evaluation classification** (Phase 3: Mapping Engine) — `graphify/mapping.py` classifies every graph node into exactly one note type via first-match-wins precedence: attribute rules (`compile_rules` + `_match_when`) override topology fallbacks (god nodes → Things, communities above threshold → MOCs, source files → Sources, default → Statements). Configurable community-to-MOC threshold; below-threshold communities collapse into sub-community callouts. Source-file extension routing.

5. **Merge engine with field-level policies** (Phase 4: Merge Engine) — `graphify/merge.py` delivers a pure `compute_merge_plan` (CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN actions) and atomic `apply_merge_plan` (`.tmp` + fsync + `os.replace`). 14-key built-in field-policy table (D-64), hand-rolled YAML frontmatter reader as strict inverse of `_dump_frontmatter`, D-67 sentinel block protection for graphify-owned body regions, content-hash skip for idempotent re-runs, D-72 orphan preservation. Four configurable merge strategies (`update` / `skip` / `replace`). 28/28 must-haves verified.

6. **Integration & CLI** (Phase 5: Integration & CLI) — Refactored `to_obsidian()` in `graphify/export.py` orchestrates the four-module pipeline behind a single entry point. `graphify --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run]` and `graphify --validate-profile <vault-path>` land in `__main__.py:691-740`. `validate_profile_preflight` runs a four-layer preflight (schema → templates → dead-rules → path-safety). `format_merge_plan` + `split_rendered_note` public helpers support dry-run formatting. All 9 skill platform variants updated with the new pipeline patterns.

### Architectural Decisions Locked

- **D-73** — CLI is utilities-only; the skill is the pipeline driver. `graphify --obsidian` and `graphify --validate-profile` exist as direct utility entry points, but the full detect→extract→build→cluster→analyze→report→export pipeline runs via the skill (`graphify/skill.md`), not via a single CLI verb. Avoids rebuilding agent orchestration in Python.
- **D-74** — De-scope `.obsidian/graph.json` generation from `to_obsidian()` — the library entry point is a notes pipeline, not a vault-config-file manager. OBS-01 and OBS-02 moved to Out of Scope. The underlying `safe_tag()` invariant (slug form `community/<slug>`) remains and is anchored by `tests/test_profile.py::test_obs01_obs02_safe_tag_regression_anchor`.

Other locked decisions (D-01..D-72) are recorded in the archived phase contexts and in `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.

### Verification

- All 5 phases have passing VERIFICATION.md artifacts (Phase 01 was retroactive to close the audit's evidence gap — commit `ffdb076`)
- 12/12 cross-phase integration key-links WIRED (verified by `gsd-integration-checker`)
- 5/5 primary user flows traced end-to-end (2 of them additionally live-verified against a 3-node graph fixture)
- Milestone audit run #2: `status: passed` — see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

### Known Gaps / Deferred

- **OBS-01, OBS-02** — `.obsidian/graph.json` read-merge-write management. Deliberately de-scoped via D-74. Revisit if a future release needs plugin-side graph.json management.
- **SUMMARY.md frontmatter schema drift** — Phases 2/3/5 used inconsistent field names (`requirements-completed`, `requirements`, `requirements_closed`) or omitted the field. Non-blocking; future housekeeping.
- **Nyquist validation artifacts** — Only Phase 1 has `VALIDATION.md`. Phases 2-5 shipped without Nyquist coverage. Advisory only per workflow config.

### Archives

- `.planning/milestones/v1.0-ROADMAP.md` — full phase detail (success criteria, plan descriptions, requirements mapping)
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 33 v1 requirements with traceability table + Out of Scope for D-74 items
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — audit runs 1 and 2, integration trace, 3-source cross-reference

---
