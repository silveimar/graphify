---
phase: 02-template-engine
plan: "01"
subsystem: profile
tags: [packaging, templates, yaml, frontmatter, obsidian]
dependency_graph:
  requires: []
  provides:
    - graphify/builtin_templates/*.md (six template files, wheel-shipped)
    - graphify/profile._dump_frontmatter (YAML frontmatter emitter)
    - graphify/profile._DEFAULT_PROFILE.obsidian.atlas_root
    - graphify/profile._DEFAULT_PROFILE.obsidian.dataview.moc_query
  affects:
    - graphify/export.py (downstream plans use these templates and helpers)
tech_stack:
  added: []
  patterns:
    - importlib.resources for package-data file loading
    - Hand-rolled type-dispatched YAML emitter (no PyYAML dependency for writing)
    - TDD (RED commit then GREEN commit) for _dump_frontmatter
key_files:
  created:
    - graphify/builtin_templates/moc.md
    - graphify/builtin_templates/community.md
    - graphify/builtin_templates/thing.md
    - graphify/builtin_templates/statement.md
    - graphify/builtin_templates/person.md
    - graphify/builtin_templates/source.md
  modified:
    - pyproject.toml
    - graphify/profile.py
    - tests/test_pyproject.py
    - tests/test_profile.py
decisions:
  - "_dump_frontmatter checks bool before int because isinstance(True, int) is True in Python — getting this wrong renders True as 1 in YAML"
  - "sub_communities_callout added to KNOWN_VARS as dedicated variable for below-threshold community rendering (D-29, Claude's Discretion)"
  - "validate_profile passes new obsidian.* keys through without error — obsidian is an opaque dict at top level, subkeys not inspected"
metrics:
  duration: 3min
  completed: "2026-04-11"
  tasks_completed: 3
  files_changed: 9
---

# Phase 02 Plan 01: Scaffolding — Templates, Package-Data, Frontmatter Helper Summary

**One-liner:** Wheel-shipped built-in templates (six `.md` files), extended `_DEFAULT_PROFILE` with `obsidian.atlas_root`/`dataview.moc_query`, and type-dispatched `_dump_frontmatter()` YAML emitter guarded by 14 new tests.

## What Was Built

This plan lands the foundational scaffolding that every downstream Phase 2 task depends on. Three atomic deliverables:

1. **Package-data wiring** — `builtin_templates/*.md` added to `[tool.setuptools.package-data]` so the six template files survive wheel installs without `FileNotFoundError`. A test in `test_pyproject.py` guards against future removal.

2. **Six built-in `.md` template files** under `graphify/builtin_templates/`:
   - `moc.md` and `community.md`: MOC/Community Overview scaffold — `${frontmatter}`, `${label}`, `${wayfinder_callout}`, `${members_section}`, `${sub_communities_callout}`, `${dataview_block}`, `${metadata_callout}`
   - `thing.md`, `statement.md`, `person.md`, `source.md`: uniform non-MOC scaffold — `${frontmatter}`, `${label}`, `${wayfinder_callout}`, `${body}`, `${connections_callout}`, `${metadata_callout}`
   - All placeholders confined to the locked `KNOWN_VARS` set; loadable via `importlib.resources`

3. **`profile.py` extensions:**
   - `import datetime` added (alphabetical order)
   - `_DEFAULT_PROFILE["obsidian"]` extended with `atlas_root: "Atlas"` and `dataview.moc_query` (the default Dataview query with `${community_tag}` placeholder)
   - `_dump_frontmatter(fields: dict) -> str` helper added — type-dispatched emitter producing Obsidian-compatible YAML with `---` delimiters, block-form lists, unquoted dates/floats/ints/bools

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `903ed0b` | chore | Add builtin_templates/*.md to package-data + guard test |
| `af1fc8a` | feat | Six built-in .md template files under graphify/builtin_templates/ |
| `9878759` | test | Failing tests for _dump_frontmatter + obsidian defaults (RED) |
| `4061ca5` | feat | _dump_frontmatter helper + obsidian defaults to profile.py (GREEN) |

## Test Results

- `pytest tests/test_profile.py tests/test_pyproject.py -q` → **56 passed**
- 14 new tests for `_dump_frontmatter` (all passing)
- 3 new tests in `test_pyproject.py` (all passing)
- Zero Phase 1 regressions

## Deviations from Plan

None — plan executed exactly as written.

The `sub_communities_callout` placeholder name was chosen per plan instructions (Claude's Discretion, D-29), and the name is confirmed here for downstream reference.

## Known Stubs

None — all six template files are complete `string.Template` texts with real placeholder structure. No hardcoded empty values or placeholder text.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. File writes are confined to the `graphify/builtin_templates/` package directory (static files, not runtime output).

## Self-Check: PASSED

Verified:
- `graphify/builtin_templates/moc.md` — FOUND
- `graphify/builtin_templates/community.md` — FOUND
- `graphify/builtin_templates/thing.md` — FOUND
- `graphify/builtin_templates/statement.md` — FOUND
- `graphify/builtin_templates/person.md` — FOUND
- `graphify/builtin_templates/source.md` — FOUND
- `graphify/profile._dump_frontmatter` — FOUND (commit 4061ca5)
- `pyproject.toml builtin_templates/*.md` — FOUND (commit 903ed0b)
