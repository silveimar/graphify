---
phase: 32-profile-contract-defaults
plan: 04
subsystem: doctor-diagnostics
tags: [v1.8, doctor, profile-preflight, validation, obsidian]

# Dependency graph
requires:
  - phase: 32-profile-contract-defaults
    provides: v1.8 taxonomy defaults, mapping.min_community_size validation, and community overview preflight warnings
provides:
  - Doctor diagnostics routed through validate_profile_preflight()
  - Warning-level profile findings in DoctorReport and formatted output
  - v1.8 fix hints for taxonomy, mapping.min_community_size, mapping.moc_threshold, and MOC-only output
affects: [graphify-doctor, validate-profile-cli, phase-35, phase-36, vault-profile-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: [shared-preflight-diagnostics, warning-nonfatal-doctor-output, tdd-red-green]

key-files:
  created:
    - .planning/phases/32-profile-contract-defaults/32-04-SUMMARY.md
  modified:
    - graphify/doctor.py
    - tests/test_doctor.py

key-decisions:
  - "Doctor now treats validate_profile_preflight() as the single source for profile validation errors and warnings."
  - "Warning-level preflight findings render in doctor output and recommended fixes without making is_misconfigured() true."
  - "Output resolution is skipped after fatal preflight errors to avoid duplicate fallback diagnostics from reloading an invalid profile."

patterns-established:
  - "Doctor reports should consume shared preflight results instead of revalidating merged profiles locally."
  - "Doctor fix hints can be generated from both preflight errors and warnings while preserving one fix line per issue type."

requirements-completed: [TAX-04, COMM-03, CLUST-04]

# Metrics
duration: 6min
completed: 2026-04-29
---

# Phase 32 Plan 04: Doctor Shared Preflight Summary

**Doctor diagnostics now surface the same v1.8 profile preflight errors and warnings as direct profile validation, with warning-only community overview guidance kept nonfatal.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T00:29:06Z
- **Completed:** 2026-04-29T00:34:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added TDD coverage for taxonomy errors, `mapping.moc_threshold` errors, warning-level `community.md` deprecation output, and fix hints in `tests/test_doctor.py`.
- Refactored `graphify/doctor.py` to call `validate_profile_preflight()` when a vault has `.graphify/profile.yaml` or `.graphify/templates/`.
- Added `profile_validation_warnings` to `DoctorReport`, rendered warnings as `[graphify] warning:`, and kept warnings out of `is_misconfigured()`.
- Extended doctor fix hints for taxonomy, `mapping.min_community_size`, legacy `mapping.moc_threshold`, and MOC-only output migration guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add doctor tests for shared v1.8 preflight findings** - `fbd1bb8` (test)
2. **Task 2: Refactor doctor to consume validate_profile_preflight** - `48a71b4` (feat)
3. **Rule 1 fix: Avoid duplicate doctor profile errors** - `122bd04` (fix)

## Files Created/Modified

- `tests/test_doctor.py` - Adds v1.8 doctor/preflight regression tests and updates the valid profile fixture to the required v1.8 contract.
- `graphify/doctor.py` - Routes profile diagnostics through shared preflight, stores warnings, renders warning output, and adds targeted fix hints.
- `.planning/phases/32-profile-contract-defaults/32-04-SUMMARY.md` - Records execution outcome and verification evidence.

## Decisions Made

- Used `validate_profile_preflight()` directly in doctor rather than `load_profile()` plus `validate_profile()` so doctor and `--validate-profile` share the same v1.8 diagnostic source.
- Kept preflight warnings advisory: they render in the Profile Validation section and can produce fixes, but only errors make the doctor report misconfigured.
- Skipped output resolution when fatal preflight errors already exist, preventing secondary fallback messages from obscuring the shared preflight finding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Suppressed duplicate invalid-profile diagnostics**
- **Found during:** Plan-level CLI smoke test
- **Issue:** After preflight reported `mapping.moc_threshold`, doctor still called output resolution, which reloaded the invalid profile and emitted duplicate/fallback errors.
- **Fix:** Skip output resolution when `profile_validation_errors` is already non-empty.
- **Files modified:** `graphify/doctor.py`
- **Verification:** `pytest tests/test_profile.py tests/test_doctor.py -q` and temporary-vault `python -m graphify doctor` smoke test.
- **Committed in:** `122bd04`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** The fix kept doctor diagnostics aligned with the shared preflight source and did not expand scope.

## Issues Encountered

- `git add graphify/doctor.py` printed the repo's existing ignore-rule warning for the tracked package directory; staged diffs were checked and committed from the index.
- The repo post-commit graphify hook rebuilt the graph after commits and printed ImageMagick `import` help before completing. Generated graph output remained ignored and was not staged.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Stub scan found only existing empty/default initializers in diagnostic containers and local lists/dicts; no runtime UI/data stubs were introduced.

## Verification

- RED gate: `pytest tests/test_doctor.py -q` failed before implementation with 3 expected doctor/preflight contract failures.
- GREEN verification: `pytest tests/test_profile.py tests/test_doctor.py -q` passed with `198 passed, 1 xfailed`.
- Final plan verification: `pytest tests/test_profile.py tests/test_doctor.py -q` passed with `198 passed, 1 xfailed`.
- CLI smoke test: temporary vault with `mapping.moc_threshold: 3` made `python -m graphify doctor` print a `mapping.moc_threshold` error and exit non-zero.
- Editor diagnostics: no linter errors for `graphify/doctor.py` or `tests/test_doctor.py`.

## TDD Gate Compliance

- RED commit present: `fbd1bb8`
- GREEN commit present after RED: `48a71b4`
- Refactor commit: not needed

## Threat Flags

None. No network endpoints, auth paths, schema changes, or new trust boundaries were introduced beyond the plan's doctor/preflight diagnostic surface.

## Self-Check: PASSED

- Found `.planning/phases/32-profile-contract-defaults/32-04-SUMMARY.md`.
- Found `graphify/doctor.py`.
- Found `tests/test_doctor.py`.
- Found task commit `fbd1bb8`.
- Found task commit `48a71b4`.
- Found auto-fix commit `122bd04`.

## Next Phase Readiness

Phase 32 now has consistent profile validation across `--validate-profile` and `graphify doctor`. Later migration/export phases can rely on doctor warnings to guide users away from community overview output without blocking warning-only vaults.

---
*Phase: 32-profile-contract-defaults*
*Completed: 2026-04-29*
