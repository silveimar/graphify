---
phase: 260427-rc7-fix-detect-self-ingestion
plan: 01
subsystem: detect
tags: [bugfix, detect, ingestion, obsidian]
requires: []
provides:
  - default-ignore-graphify-out-subtree
affects:
  - graphify/detect.py
  - tests/test_detect.py
tech-stack:
  added: []
  patterns:
    - default-prune-on-os-walk-via-_is_noise_dir
key-files:
  created: []
  modified:
    - graphify/detect.py
    - tests/test_detect.py
decisions:
  - Add _SELF_OUTPUT_DIRS module constant + extend _is_noise_dir rather than touching detect() body, so existing graphify-out/memory/ allow-list (a separate scan_paths root) is preserved without code changes
  - Cover the underscore variant graphify_out/ defensively in the same set
metrics:
  duration: ~5min
  completed: 2026-04-27
---

# Phase 260427-rc7 Plan 01: Fix detect() Self-Ingestion Summary

Two-line patch to `_is_noise_dir` plus a new `_SELF_OUTPUT_DIRS` constant prevents `detect()` from re-ingesting graphify's own `graphify-out/` exports as fresh document inputs, eliminating the nested `graphify-out/obsidian/graphify-out/...` loop seen on repeat `--obsidian` runs.

## What Changed

**`graphify/detect.py`**
- New module-level constant immediately after `_SKIP_DIRS`:
  ```python
  _SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}
  ```
- `_is_noise_dir(part)` now also returns `True` when `part in _SELF_OUTPUT_DIRS`.
- No other lines touched. `.graphifyignore` handling, the per-file `converted_dir` skip, and the `memory_dir` allow-list block (`scan_paths.append(memory_dir)`) are all unchanged.

Because `_is_noise_dir` is invoked inside the `dirnames[:] = [...]` pruning step in `detect()`, `os.walk` never descends into `graphify-out/` from the top-level scan root. The `graphify-out/memory/` allow-list still works because it is walked via a separate `scan_paths` root — `os.walk(memory_dir)` starts inside the dir, so pruning its parent has no effect.

**`tests/test_detect.py`** — four new regression tests (all pass after fix):
1. `test_detect_skips_graphify_out_subtree` — top-level `graphify-out/obsidian/foo.md` not returned.
2. `test_detect_skips_graphify_out_at_any_depth` — `sub/graphify-out/...` pruned at any depth, while `sub/keeper.md` remains.
3. `test_detect_still_includes_graphify_out_memory` — confirms the existing `graphify-out/memory/recall.md` allow-list still works alongside the new exclusion.
4. `test_detect_skips_graphify_out_underscore_variant` — defensive coverage for the `graphify_out/` underscore variant.

Tests use `tmp_path` only and follow the existing pure-unit-test conventions.

## TDD Gate Compliance

- RED: `test(quick-260427-rc7): add failing tests for detect graphify-out self-ingestion` — commit `6584eff`. Confirmed all 4 new tests failed before any implementation.
- GREEN: `fix(quick-260427-rc7): prune graphify-out/ in detect() to stop self-ingestion` — commit `59d8b2f`. All 32 tests in `test_detect.py` pass; full suite `pytest tests/ -q` = `1597 passed, 1 xfailed`.
- REFACTOR: not needed (2-line addition).

## Verification

```
pytest tests/test_detect.py -q  → 32 passed
pytest tests/ -q                → 1597 passed, 1 xfailed
```

`graphify-out/memory/` allow-list verified by `test_detect_still_includes_graphify_out_memory`: `recall.md` is returned, `obsidian/note.md` next door is excluded.

## Deviations from Plan

None — plan executed exactly as written. One minor test refinement during the RED gate: tightened the substring assertions in two tests so they would not false-fail on pytest tmp_path names that contain `graphify_out` (e.g. `test_detect_skips_graphify_out2`) by anchoring on `/graphify-out/` and specific filenames (`note.md`, `some.md`, `foo.md`). This was caught and fixed before committing the RED gate, so the committed tests are clean.

## Follow-ups

- Per the original todo's "Cleanup" note: the user's actual vault may still contain an orphaned nested `graphify-out/obsidian/graphify-out/...` tree from prior runs. That requires a manual `rm -rf` once on the user's side; this fix only prevents the loop from recurring.
- The `converted_dir` per-file prefix skip in `detect()` (line ~377) is now redundant with the new dir prune, but harmless. Cleanup is out of scope.

## Self-Check: PASSED

- FOUND: `graphify/detect.py` contains `_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}` and `_is_noise_dir` references it.
- FOUND: `tests/test_detect.py` contains all four new test functions.
- FOUND: commit `6584eff` (test) and `59d8b2f` (fix) in `git log`.
- VERIFIED: `pytest tests/test_detect.py -q` → 32 passed; `pytest tests/ -q` → 1597 passed.
