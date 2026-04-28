---
phase: 29-doctor-diagnostics-dry-run-preview
plan: 02
subsystem: detect
tags: [detect, skip-reasons, abi-additive, doctor-prep]
requires:
  - 29-01 (PLAN/RESEARCH/PATTERNS/VALIDATION artifacts)
provides:
  - "detect() returns additive `skipped: dict[str, list[str]]` with 5 stable D-38 buckets"
  - "Single source of truth for skip decisions consumable by Plan 29-03 doctor --dry-run"
affects:
  - graphify/detect.py (instrumented; ABI preserved)
  - tests/test_detect.py (+2 new tests)
tech-stack:
  added: []
  patterns:
    - "Bounded list accumulator with overflow counter (T-29-05 OOM mitigation)"
    - "Additive return-key extension preserving caller ABI"
key-files:
  created: []
  modified:
    - graphify/detect.py
    - tests/test_detect.py
decisions:
  - "Approach A from RESEARCH §C.1: additive return-shape extension (no struct break)"
  - "_SKIP_CAP = 10000 entries per reason bucket; overflow counts tracked separately"
  - "Stable D-38 reason labels: nesting, exclude-glob, manifest, sensitive, noise-dir"
  - "skipped['sensitive'] mirrors existing skipped_sensitive list (zero-cost backcompat)"
metrics:
  duration: ~12 min
  completed: 2026-04-28
---

# Phase 29 Plan 02: detect() Skip-Reason Surfacing Summary

**One-liner:** Added an additive `skipped: dict[str, list[str]]` return key to `graphify/detect.py:detect()` so Plan 29-03's `graphify doctor --dry-run` has a single source of truth for skip decisions, with bounded memory via per-bucket entry caps.

## Tasks Completed

| Task | Name                                                                | Commit  | Files                  |
| ---- | ------------------------------------------------------------------- | ------- | ---------------------- |
| 1    | Add `skipped` return key with bounded accumulation                  | 690e9a3 | `graphify/detect.py`   |
| 2    | Add test_detect_skip_reasons + test_detect_return_shape_backcompat | 29367a0 | `tests/test_detect.py` |

## What Was Built

### `graphify/detect.py` (instrumented)

- **New accumulator (top of `detect()`):**
  - `_SKIP_CAP = 10000` constant (T-29-05 OOM mitigation)
  - `skipped: dict[str, list[str]]` initialized with all 5 D-38 reason keys
  - `skipped_overflow: dict[str, int]` mirroring keys for capped overflow counts
  - Inner helper `_record_skip(reason, rel_path)` enforces the cap

- **Five pruning sites instrumented (each call paired with the existing `continue`):**
  1. Hidden / `_is_noise_dir` directory pruning → `skipped["noise-dir"]`
  2. Directory-level `_is_ignored` (split out from the previous combined branch) → `skipped["exclude-glob"]`
  3. `_is_nested_output` directory pruning → `skipped["nesting"]` (also retains existing `nested_paths.append` so the D-20 stderr WARNING line is unchanged)
  4. File-level `_is_ignored` (.graphifyignore + output.exclude) → `skipped["exclude-glob"]`
  5. File-level `prior_files` manifest skip → `skipped["manifest"]`
  6. File-level `_is_sensitive` → `skipped["sensitive"]` (existing `skipped_sensitive.append` preserved)

- **Return dict gains exactly ONE new key:** `"skipped": skipped`. Every existing key (`files`, `total_files`, `total_words`, `needs_graph`, `warning`, `skipped_sensitive`, `graphifyignore_patterns`) is untouched — ABI preserved.

### `tests/test_detect.py` (+2 tests, +45 lines)

- `test_detect_skip_reasons` — verifies `result["skipped"]` is a dict with all 5 D-38 stable reason keys present, and that `node_modules` is recorded under `noise-dir`.
- `test_detect_return_shape_backcompat` — ABI guard asserting every pre-existing return key remains present.

## Verification Results

- Smoke test (from PLAN `<verify>`): **PASS**
- `pytest tests/test_detect.py::test_detect_skip_reasons tests/test_detect.py::test_detect_return_shape_backcompat -q` → **2 passed**
- Full suite `pytest tests/ -q` → **1674 passed, 1 xfailed, 2 failed**
  - The 2 failing tests (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`) are **pre-existing worktree-path artifacts** — verified by stashing changes and re-running; they fail identically on the unmodified base because the worktree path contains `.claude/`. Out of scope per executor scope-boundary rules. Logged below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Split combined `dir.startswith(".") or _is_noise_dir(d) or _is_ignored(...)` branch into two distinct branches**
- **Found during:** Task 1 implementation (instrumenting the directory pruning loop).
- **Issue:** The original code grouped three different skip causes under one `if` branch with a single `continue`-equivalent (`pruned.add(d)`). To assign each pruning correctly to its D-38 reason bucket (`noise-dir` vs `exclude-glob`), the branch had to be split — otherwise an ignored dir would have been mislabeled as `noise-dir`.
- **Fix:** Promoted the `_is_ignored(dp / d, …)` test into its own `elif` branch placed before `_is_nested_output`. Behavior is identical: any directory that previously got pruned still gets pruned; the only change is the reason attribution. Verified by full test suite (no behavioral regressions).
- **Files modified:** `graphify/detect.py`
- **Commit:** 690e9a3

### Architectural / Optional Items

- **Did NOT include `skipped_overflow` in the return dict.** The PLAN flagged this as "Optional but encouraged ... otherwise drop it (Plan 29-03 doesn't strictly require overflow counts)". Kept it as a local-only accumulator to keep the public ABI surface minimal and the diff review-friendly. Plan 29-03 can compute `would_skip_counts[reason] = len(skipped[reason])` directly. If 29-03 needs overflow telemetry, it's a one-line addition.

## Deferred Issues

| Issue | File | Notes |
|-------|------|-------|
| `test_detect_skips_dotfiles` fails when run from a worktree path containing `.claude/` | `tests/test_detect.py:54` | Pre-existing; affects all tests run from `.claude/worktrees/...`. Not introduced by 29-02. |
| `test_collect_files_from_dir` fails when run from a worktree path containing `.claude/` | `tests/test_extract.py` | Same root cause. Pre-existing. |

Both failures existed at base commit `72bfaaa` before any change in this plan.

## Threat Model Compliance

- **T-29-05 (DoS via skip-list growth):** Mitigated. `_SKIP_CAP = 10000` per bucket; overflow counted in `skipped_overflow` rather than appended. Memory bounded at ~50K paths total even on pathological inputs.
- **T-29-04 (Tampering — new return key surface):** Accepted. No new path validation needed; existing pruning sites already validate (`_is_ignored`, `_is_sensitive`, `_is_nested_output`, `_is_noise_dir`) before the new `_record_skip` call.

## Self-Check: PASSED

- [x] `graphify/detect.py` modified — verified via `git log --stat 690e9a3`
- [x] `tests/test_detect.py` modified — verified via `git log --stat 29367a0`
- [x] Commit `690e9a3` exists — verified via `git log --oneline`
- [x] Commit `29367a0` exists — verified via `git log --oneline`
- [x] `grep -c '"skipped":' graphify/detect.py` → 1 (the return-dict key; dict literal uses unquoted reason keys on separate lines, so this is the canonical count) ✓
- [x] `grep -c '"nesting"' graphify/detect.py` → 2 ✓
- [x] `grep -c '"exclude-glob"' graphify/detect.py` → 3 ✓
- [x] `grep -c '"noise-dir"' graphify/detect.py` → 2 ✓
- [x] `grep -c "_record_skip(" graphify/detect.py` → 7 (1 def + 6 call sites — exceeds the ≥5 minimum) ✓
- [x] `skipped_sensitive` count unchanged (still appended at the existing site) ✓
- [x] Both new tests pass ✓
- [x] No regression in baseline test count (1672 → 1674; +2 new tests, 0 lost) ✓
