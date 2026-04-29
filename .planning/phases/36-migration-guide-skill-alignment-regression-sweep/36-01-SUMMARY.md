---
phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 01
subsystem: migration
tags: [obsidian, migration, archive, cli, pytest]

requires:
  - phase: 35-templates-export-plumbing-dry-run-migration-visibility
    provides: reviewed update-vault preview/apply flow and legacy ORPHAN surfacing
provides:
  - reviewed migration apply archives legacy notes by default
  - plan-scoped archive metadata for rollback evidence
  - helper-level and CLI-level tmp_path archive regression coverage
affects: [migration-guide, skill-alignment, security-validation]

tech-stack:
  added: []
  patterns:
    - migration-specific archive helper after successful merge apply
    - vault source validation plus archive-root destination confinement

key-files:
  created:
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-01-SUMMARY.md
  modified:
    - graphify/migration.py
    - graphify/__main__.py
    - tests/test_migration.py
    - tests/test_main_flags.py

key-decisions:
  - "Archive movement stays migration-specific in graphify/migration.py; the generic merge engine continues to skip ORPHAN rows."
  - "Reviewed apply archives legacy notes only after apply_merge_plan reports zero failures."
  - "Rollback evidence is exposed through archived_legacy_notes metadata and CLI wording under graphify-out/migrations/archive/."

patterns-established:
  - "Archive preflight: validate all source and destination paths before moving any legacy file."
  - "Apply result formatting: attach archive metadata to the reviewed preview so CLI output and artifacts share wording."

requirements-completed: [MIG-05, VER-01, VER-03]

duration: 13min
completed: 2026-04-29
---

# Phase 36 Plan 01: Archive-By-Default Migration Apply Summary

**Reviewed `update-vault --apply --plan-id` now archives legacy Obsidian notes under plan-scoped `graphify-out/migrations/archive/` paths with rollback metadata and helper/CLI regression coverage.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-29T07:19:22Z
- **Completed:** 2026-04-29T07:32:04Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `archive_legacy_notes()` with source validation through `validate_vault_path()`, destination confinement under `migrations/archive/{plan_id}/`, duplicate preflight checks, and metadata containing source, archive, relative path, and reason.
- Wired reviewed apply to archive only after `apply_merge_plan()` succeeds with no failures; failed writes now return empty archive metadata and leave legacy notes in place.
- Added helper-level and CLI-level `tmp_path` coverage proving preview does not move legacy notes, apply archives by default, contents are preserved, and CLI output includes `Archived legacy notes` plus `graphify-out/migrations/archive/`.

## Task Commits

1. **Task 1 RED: Add archive helper tests** - `d42a5b4` (test)
2. **Task 1 GREEN: Implement archive helper** - `2bbfc66` (feat)
3. **Task 2 RED: Add apply archive tests** - `442c031` (test)
4. **Task 2 GREEN: Wire archive into reviewed apply** - `014b330` (feat)
5. **Task 3: Add CLI archive regression** - `a1ef763` (test)

## Files Created/Modified

- `graphify/migration.py` - Added archive helper, archive display formatting, and post-apply archive orchestration.
- `graphify/__main__.py` - Added help evidence that reviewed apply outputs archived legacy note paths.
- `tests/test_migration.py` - Added helper-level archive movement, path confinement, failed-apply, and apply metadata tests.
- `tests/test_main_flags.py` - Added CLI subprocess regression for preview/apply archive-by-default behavior.
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-01-SUMMARY.md` - Captures execution outcome and verification evidence.

## Decisions Made

- Archive remains outside `merge.py` so generic merge semantics still never write, move, or delete `ORPHAN` rows.
- Archive destination display uses `graphify-out/migrations/archive/{plan_id}/{relative_path}` so user-facing output is stable even when tests run under temporary absolute directories.
- Failed merge writes are treated as a hard archive stop: callers receive the failed merge result and `archived_legacy_notes: []`.

## Deviations from Plan

### Auto-fixed Issues

None - no Rule 1-3 auto-fixes were required.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** Plan scope was preserved.

## TDD Gate Compliance

- Task 1 RED failed as expected before `archive_legacy_notes()` existed, then GREEN passed after implementation.
- Task 2 RED failed as expected on missing `archived_legacy_notes` metadata, then GREEN passed after apply wiring.
- Task 3's CLI regression passed immediately because Task 2 had already wired archive evidence through the actual CLI formatter. The test was committed as Task 3 coverage, but there is no failing RED commit for that task.

## Issues Encountered

- The git hook prints ImageMagick `import` help before graph rebuilds; commits still completed successfully with normal hooks.
- `git add graphify/...` reports the ignored `graphify` path, but the tracked files were staged and committed correctly.

## Known Stubs

None. Stub-pattern scan only found existing empty-list/default idioms unrelated to user-facing placeholder behavior.

## Threat Flags

None. The new archive file-movement surface was already covered by the plan threat model and mitigated with reviewed-plan validation, source confinement, archive-root confinement, and failed-apply gating.

## Verification

- `pytest tests/test_migration.py -q` - 13 passed, 2 warnings
- `pytest tests/test_main_flags.py -q` - 23 passed
- `pytest tests/test_migration.py tests/test_main_flags.py -q` - 36 passed, 2 warnings
- `pytest tests/ -q` - 1877 passed, 1 xfailed, 8 warnings

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 36-02 to document the migration guide and reuse the exact CLI wording: `Archived legacy notes` and `graphify-out/migrations/archive/`.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-01-SUMMARY.md`.
- Task commits exist: `d42a5b4`, `2bbfc66`, `442c031`, `014b330`, `a1ef763`.
- Focused and full verification commands passed.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*
