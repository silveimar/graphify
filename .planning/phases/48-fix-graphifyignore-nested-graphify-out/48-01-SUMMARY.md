---
phase: 48-fix-graphifyignore-nested-graphify-out
plan: "01"
subsystem: diagnostics
requirements-completed:
  - HYG-04
completed: 2026-04-30
---

# Phase 48 Plan 01 — Summary

**Outcome:** `self_ingest_graphifyignore_hint_redundant()` in `graphify/doctor.py` suppresses the WOULD_SELF_INGEST `.graphifyignore` fix when `_is_ignored` already excludes probe paths under resolved destinations; `_build_recommended_fixes` threads `cwd` + `resolved`.

## Accomplishments

- Shared pattern list: `_load_graphifyignore(cwd)` + `resolved.exclude_globs`, matching `detect` / `collect_files`.
- Regression: `test_hyg04_graphifyignore_suppresses_redundant_self_ingest_hint` (uses `graphify-out/**` pattern compatible with `fnmatch` semantics).

## Verification

- `pytest tests/test_doctor.py -q -k hyg04`
- `pytest tests/test_doctor.py tests/test_output.py -q`
