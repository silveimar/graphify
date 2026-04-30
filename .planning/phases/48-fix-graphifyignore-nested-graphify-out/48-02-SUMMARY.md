---
phase: 48-fix-graphifyignore-nested-graphify-out
plan: "02"
subsystem: cli-output
requirements-completed:
  - HYG-05
completed: 2026-04-30
---

# Phase 48 Plan 02 — Summary

**Outcome:** `default_graphify_artifacts_dir()` in `graphify/output.py` — for `ResolvedOutput.source == "default"`, artifact dir is `(cwd / resolved.artifacts_dir).resolve()` instead of nesting under an arbitrary corpus `target`. Wired from `graphify/pipeline.run_corpus` and `graphify/__main__.py` enrich-style `run` path.

## Accomplishments

- `CLAUDE.md` pipeline note documents cwd-relative default `graphify-out/` and legacy nested folders (warn-only, no auto-delete).
- Tests: `test_default_graphify_artifacts_dir_*` in `tests/test_output.py`.

## Verification

- `pytest tests/test_output.py -q`
- `pytest tests/ -q`
