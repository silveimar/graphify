---
phase: 28-self-ingestion-hardening
plan: "02"
subsystem: detect
tags: [vault-adapter, detect, tdd, nesting-guard, exclude-globs, pipeline]
dependency_graph:
  requires:
    - phases/28-self-ingestion-hardening/28-01-SUMMARY.md
  provides:
    - _is_nested_output() predicate in detect.py
    - detect() resolved kwarg with nesting guard + exclude_globs application
    - pipeline.run_corpus() resolved kwarg threading to detect()
  affects:
    - graphify/detect.py
    - graphify/pipeline.py
    - tests/test_detect.py
tech_stack:
  added: []
  patterns:
    - TYPE_CHECKING guard for circular-import-safe forward references
    - frozenset resolved_basenames computed once before walk
    - dirnames[:] accumulator pattern for single-line D-20 warning
    - all_ignore_patterns = graphifyignore + exclude_globs (VAULT-11 D-16)
key_files:
  created: []
  modified:
    - graphify/detect.py
    - graphify/pipeline.py
    - tests/test_detect.py
decisions:
  - "D-18: nesting guard matches notes_dir.name + artifacts_dir.name basenames at any scan depth"
  - "D-19: nesting detection is warn-and-skip, never fatal (no raise SystemExit)"
  - "D-20: single summary WARNING line aggregates all nested paths; deepest reported"
  - "D-21: resolved=None activates universal scope — _SELF_OUTPUT_DIRS still caught by _is_noise_dir"
  - "D-15/D-16: exclude_globs always applied via _is_ignored(); --output destination does not suppress them"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
requirements: [VAULT-11, VAULT-12]
---

# Phase 28 Plan 02: VAULT-12 Nesting Guard + VAULT-11 detect-side exclude_globs Summary

detect.py becomes ResolvedOutput-aware: `_is_nested_output()` predicate prunes renamed-output directories at any scan depth, emitting exactly one `[graphify] WARNING` summary; `exclude_globs` from resolved are merged with `.graphifyignore` patterns and applied uniformly per file; `pipeline.run_corpus()` threads `resolved` through to `detect()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED tests for nesting guard, summary warning, and exclude_globs (Wave 0) | 9dfe028 | tests/test_detect.py |
| 2 | Add _is_nested_output predicate, extend detect() with resolved kwarg, summary warning, exclude_globs application | 6cec764 | graphify/detect.py |
| 3 | Thread resolved through pipeline.py:run_corpus() | aedd3e7 | graphify/pipeline.py |

## What Was Built

**graphify/detect.py** — Added `import sys` + `TYPE_CHECKING` guard importing `ResolvedOutput`. New `_is_nested_output(part, resolved_basenames)` predicate returns True for `_SELF_OUTPUT_DIRS` members or any member of the `resolved_basenames` frozenset. `detect()` gains keyword-only `resolved: "ResolvedOutput | None" = None`. Before the walk: computes `resolved_basenames` (frozenset of notes_dir.name + artifacts_dir.name minus `_SELF_OUTPUT_DIRS`), merges `exclude_globs` into `all_ignore_patterns`, initializes `nested_paths = []`. Inside the walk: `dirnames[:]` filter refactored to an explicit loop accumulating `nested_paths` for `_is_nested_output` matches. Per-file `_is_ignored` call upgraded to `all_ignore_patterns`. After the walk: emits single `[graphify] WARNING: skipped N nested output path(s) (deepest: ...)` to stderr if `nested_paths` is non-empty.

**graphify/pipeline.py** — `TYPE_CHECKING` guard added; `run_corpus()` extended with `resolved: "ResolvedOutput | None" = None`; internal `detect(target)` call updated to `detect(target, resolved=resolved)`.

**tests/test_detect.py** — 8 new tests: 2 for `nesting_guard_resolved` (notes_dir and artifacts_dir basename pruning), 2 for `nesting_guard_summary` (one warning per run + no warning when clean), 3 for `exclude_globs` (prune files, cli-flag source, empty tuple no-op). All tests were RED at Task 1 commit (TypeError on unknown kwarg) and GREEN after Task 2.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 9dfe028 | 8 tests failing with TypeError — correct RED state |
| GREEN (feat) | 6cec764, aedd3e7 | All 8 target tests pass + full suite green |
| REFACTOR | n/a | No refactor needed |

## Verification

- `pytest tests/test_detect.py -q -k "nesting_guard_resolved or nesting_guard_summary or exclude_globs or skips_graphify_out"` — 9 passed
- `pytest tests/ -q` — 1664 passed, 1 xfailed, 8 warnings (full regression clean; +8 tests vs 28-01 baseline 1657 → rounding: one baseline test counted differently)
- `grep -n "_is_nested_output" graphify/detect.py` — definition + 1 call inside dirnames loop
- `grep -c "WARNING: skipped" graphify/detect.py` == 1 (single aggregated warning)
- `grep -v '^#' graphify/detect.py | grep -c "raise SystemExit"` == 0 (D-19 warn-and-skip enforced)

## Deviations from Plan

None — plan executed exactly as written. The `_is_noise_dir` function was not modified (as required by D-21); `_SELF_OUTPUT_DIRS` paths continue to be caught by `_is_noise_dir` and are NOT counted in `nested_paths` (they are silently pruned as noise, which preserves the existing warning-free behavior for default output dirs).

## Known Stubs

None — `resolved` kwarg threading is complete through detect() and pipeline.run_corpus(). The `__main__.py` wire-up to pass a real `ResolvedOutput` to `run_corpus()` is deferred to Plan 28-03 (manifest layer), which is the documented plan boundary.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced. The nesting guard mitigates T-28-05 (adversarial nested directory flood) via D-20 single aggregated warning. T-28-07 (fatal raise blocking recovery) is mitigated — `raise SystemExit` is absent from detect.py (confirmed via grep). T-28-06 (empty basename) is handled safely: `frozenset({""}) - _SELF_OUTPUT_DIRS` is `{""}` which never matches a real directory basename.

## Self-Check: PASSED

- `graphify/detect.py` exists and contains `def _is_nested_output` — FOUND
- `graphify/detect.py` exists and contains `resolved: "ResolvedOutput | None" = None` — FOUND
- `graphify/detect.py` exists and contains `WARNING: skipped` — FOUND
- `graphify/pipeline.py` exists and contains `detect(target, resolved=resolved)` — FOUND
- `tests/test_detect.py` exists and contains `nesting_guard_resolved` — FOUND
- Commits 9dfe028, 6cec764, aedd3e7 — FOUND
