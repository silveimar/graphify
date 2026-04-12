---
phase: 02-template-engine
plan: "02"
subsystem: templates
tags: [templates, obsidian, filename-resolution, template-validation, lazy-import]
dependency_graph:
  requires:
    - graphify/profile.py (safe_filename, safe_frontmatter_value, safe_tag, validate_vault_path, _dump_frontmatter)
    - graphify/builtin_templates/*.md (six template files from Plan 01)
  provides:
    - graphify/templates.py (KNOWN_VARS, ClassificationContext, resolve_filename, validate_template, load_templates)
    - tests/fixtures/template_context.py (make_classification_context, make_min_graph — reused by Plans 03+04)
    - graphify.__init__.py lazy imports for resolve_filename, validate_template, load_templates
  affects:
    - graphify/export.py (Plans 03 and 04 use these contracts to implement render_note/render_moc)
tech_stack:
  added: []
  patterns:
    - string.Template.pattern.finditer for placeholder extraction (validate_template)
    - importlib.resources Traversable API for built-in template loading (no Path() cast pitfall)
    - TypedDict total=False for optional classification context shape (D-42)
    - TDD (RED commit then GREEN commit) for templates.py skeleton
key_files:
  created:
    - graphify/templates.py
    - tests/test_templates.py
    - tests/fixtures/template_context.py
  modified:
    - graphify/__init__.py
decisions:
  - "resolve_filename splits on r'[ \t_]+' for BOTH title_case and kebab-case (LOCKED BEHAVIOR GEN-07) so labels with existing underscores round-trip cleanly in either direction"
  - "ClassificationContext uses total=False (all fields optional) matching D-42 — Phase 3 populates it, Phase 2 consumes it with synthetic test contexts"
  - "validate_template uses string.Template.pattern.finditer directly (class attribute) — no instance needed, handles $$ escapes and ignores Templater <% %> tokens"
  - "load_templates wraps validate_vault_path in try/except ValueError before reading any user file — path confinement per security.py pattern"
  - "render_* functions NOT added to __init__.py lazy map — deferred to Plans 03/04 to prevent ImportError before those modules exist"
metrics:
  duration: 3min
  completed: "2026-04-11"
  tasks_completed: 3
  files_changed: 4
---

# Phase 02 Plan 02: Templates Module Skeleton Summary

**One-liner:** `graphify/templates.py` module with locked `KNOWN_VARS` frozenset, `ClassificationContext` TypedDict, and three fully-tested helpers (`resolve_filename`, `validate_template`, `load_templates`) wired into `__init__.py` lazy imports — contracts Plans 03/04 implement against.

## What Was Built

Three atomic deliverables in TDD order (RED → GREEN for Tasks 1+2, then Task 3):

1. **Shared test fixtures** — `tests/fixtures/template_context.py` exposes `make_classification_context(**overrides)` returning a dict conforming to ClassificationContext shape with defaults, and `make_min_graph()` returning a 3-node/2-edge NetworkX graph. Both helpers are designed for reuse by Plans 03 and 04 without rework.

2. **`graphify/templates.py` module** (179 lines) — standalone, imports only from `graphify.profile`:
   - `KNOWN_VARS: frozenset[str]` — 9 placeholder names including `sub_communities_callout` (confirmed from Plan 01 discretion)
   - `_NOTE_TYPES: frozenset[str]` — 6 note type names for iteration
   - `ClassificationContext(TypedDict, total=False)` — 8 optional fields including `community_name` for Phase 3 display names
   - `resolve_filename(label, convention) -> str` — splits on `r"[ \t_]+"` for both `title_case` and `kebab-case` (LOCKED BEHAVIOR GEN-07), delegates to `safe_filename()` for final sanitization
   - `validate_template(text, required) -> list[str]` — uses `string.Template.pattern.finditer`, ignores `$$` escapes and Templater `<% %>` tokens, returns sorted error list
   - `_REQUIRED_PER_TYPE` — per-type required placeholder policy for `load_templates`
   - `_load_builtin_template(note_type) -> string.Template` — uses `importlib.resources.files().joinpath().read_text()` Traversable API (never casts to `Path()`)
   - `load_templates(vault_dir) -> dict[str, string.Template]` — discovers user overrides at `<vault>/.graphify/templates/<type>.md`, validates, falls back to built-ins with `[graphify] template error:` stderr warning per D-22

3. **`graphify/__init__.py` lazy import wiring** — three entries added: `resolve_filename`, `validate_template`, `load_templates` all pointing to `graphify.templates`. `render_*` functions intentionally deferred to Plans 03/04.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `020db91` | test | Add failing tests for templates.py skeleton (RED) — 30 tests |
| `2e800c9` | feat | Add templates.py with KNOWN_VARS, ClassificationContext, resolve_filename, validate_template, load_templates (GREEN) |
| `ab6f22e` | feat | Wire resolve_filename, validate_template, load_templates into lazy import map |

## Test Results

- `pytest tests/test_templates.py -q` → **32 passed**
- `pytest tests/test_templates.py tests/test_profile.py tests/test_pyproject.py -q` → **88 passed**
- `pytest tests/ -q` → **516 passed**, 2 pre-existing failures in `test_detect.py` and `test_extract.py` (present on base commit, not caused by this plan)
- Edge cases covered: all 8 resolve_filename cases from 02-RESEARCH.md Pattern 4, `$$` dollar escape, Templater tokens, partial user override, path confinement structural assertion

## Deviations from Plan

None — plan executed exactly as written.

The RED commit contains all 30 tests at once (Tasks 1, 2, and 3 tests combined) because the lazy import tests would also fail with ImportError before any implementation. This matches the TDD flow: write all failing tests, then implement to pass them.

## Known Stubs

None — all three public helpers are fully implemented and tested. `ClassificationContext` is a TypedDict contract (intentionally incomplete until Phase 3 populates it at runtime).

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond the profile-confined path resolution already in `validate_vault_path`. User template files are read only from `<vault_dir>/.graphify/templates/` with path confinement enforced before any `read_text()` call.

## Self-Check: PASSED

Verified:
- `graphify/templates.py` — FOUND
- `tests/test_templates.py` — FOUND
- `tests/fixtures/template_context.py` — FOUND
- `graphify/__init__.py` lazy entries — FOUND (commit ab6f22e)
- `resolve_filename` in templates.py — FOUND (commit 2e800c9)
- `validate_template` in templates.py — FOUND (commit 2e800c9)
- `load_templates` in templates.py — FOUND (commit 2e800c9)
- `ClassificationContext` in templates.py — FOUND (commit 2e800c9)
- `KNOWN_VARS` in templates.py — FOUND (commit 2e800c9)
- All 32 tests pass — VERIFIED
- No import from graphify.export — VERIFIED (`grep -c 'from graphify.export' graphify/templates.py` = 0)
