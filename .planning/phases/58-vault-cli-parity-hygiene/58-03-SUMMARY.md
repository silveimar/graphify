---
phase: 58-vault-cli-parity-hygiene
plan: 03
subsystem: testing
tags: [regression-lock, self-ingestion, _SELF_OUTPUT_DIRS, corpus_prune, detect]

# Dependency graph
requires:
  - phase: quick/260427-rc7-fix-detect-self-ingestion
    provides: "HYG-01 fix shipped in commit 59d8b2f — _SELF_OUTPUT_DIRS constant with both spellings"
provides:
  - "Named regression-lock test guarding both corpus_prune._SELF_OUTPUT_DIRS and detect._SELF_OUTPUT_DIRS against drift or dropped spellings"
affects: [58-vault-cli-parity-hygiene]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Constant-membership assertion pattern for mirrored module constants"]

key-files:
  created: []
  modified: [tests/test_detect.py]

key-decisions:
  - "Use local imports inside the test (matches existing late-import pattern in test_detect.py)"
  - "Assert equality of both copies to catch future divergence between mirrored constants"
  - "Cite quick-task SUMMARY path and commit hash in docstring for traceability"

patterns-established:
  - "Regression-lock pattern: import constant from both modules, assert membership + equality in one test"

requirements-completed: [HYG-01]

# Metrics
duration: 3min
completed: 2026-05-03
---

# Phase 58 Plan 03: HYG-01 Regression-Lock Test Summary

**Named constant-membership regression guard asserting both "graphify-out" and "graphify_out" spellings exist in `_SELF_OUTPUT_DIRS` across both `corpus_prune.py` and `detect.py`**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-03T23:29:00Z
- **Completed:** 2026-05-03T23:32:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Appended `test_self_ingestion_dirs_constant_excludes_both_spellings` to `tests/test_detect.py`
- Test imports `_SELF_OUTPUT_DIRS` from both `graphify.corpus_prune` and `graphify.detect`
- Asserts both `"graphify-out"` and `"graphify_out"` are present, and the two copies are equal
- Docstring cites the quick-task SUMMARY and commit hash `59d8b2f` for future traceability

## Task Commits

Each task was committed atomically:

1. **Task 1: append HYG-01 regression-lock test** - `74ce7ef` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_detect.py` - Appended 19-line regression-lock test function (lines 805-823)

## Decisions Made
- Local imports used inside the test body — matches the existing late-import pattern in `test_detect.py` and avoids any top-level import side effects
- No new fixtures created (per D-08 — pure constant assertion, no `_make_vault` needed)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HYG-01 regression-lock is in place; future refactors of `_is_noise_dir` or the `_SELF_OUTPUT_DIRS` constant will fail loudly
- Verifier writes HYG-01 closure citation in `58-VERIFICATION.md` (responsibility of verifier per D-10/D-11)

---
*Phase: 58-vault-cli-parity-hygiene*
*Completed: 2026-05-03*
