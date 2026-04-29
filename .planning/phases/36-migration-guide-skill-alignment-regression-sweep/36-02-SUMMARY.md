---
phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 02
subsystem: documentation
tags: [obsidian, migration, cli, docs, pytest]

requires:
  - phase: 35-templates-export-plumbing-dry-run-migration-visibility
    provides: preview-first update-vault flow, reviewed apply, and archive evidence
  - phase: 36-migration-guide-skill-alignment-regression-sweep
    provides: archive-by-default apply wording from Plan 36-01
provides:
  - generic-first v1.8 Obsidian migration guide
  - README guidance distinguishing direct export from reviewed update-vault migration
  - CLI help contract for backup-before-apply and archive location
affects: [migration-guide, skill-alignment, release-docs]

tech-stack:
  added: []
  patterns:
    - docs contract tests reading repo-root Markdown directly
    - argparse RawDescriptionHelpFormatter epilog for multi-line safety guidance

key-files:
  created:
    - MIGRATION_V1_8.md
    - tests/test_docs.py
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md
  modified:
    - README.md
    - graphify/__main__.py
    - tests/test_main_flags.py

key-decisions:
  - "The v1.8 guide is generic-first: --input is any raw corpus and --vault is the target Obsidian vault, with work-vault/raw -> ls-vault as the canonical example."
  - "README presents --obsidian as lower-level direct export and update-vault as the reviewed existing-vault migration/update workflow."
  - "CLI help repeats backup-before-apply, reviewed --apply --plan-id, archive path, and non-destructive legacy-note wording."

patterns-established:
  - "Docs drift tests assert exact safety phrases and section ordering rather than snapshotting full Markdown files."
  - "User-facing migration docs put backup before any apply command and rollback immediately after apply/archive."

requirements-completed: [MIG-05, VER-02]

duration: 7min
completed: 2026-04-29
---

# Phase 36 Plan 02: Migration Guide and Command Docs Summary

**Generic-first v1.8 migration guide with README and CLI help aligned around preview-first `update-vault`, reviewed apply, archive evidence, and rollback.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-29T07:36:05Z
- **Completed:** 2026-04-29T07:43:41Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `MIGRATION_V1_8.md`, covering raw-corpus-to-target-vault semantics, validation, dry-run preview, plan review, backup as a hard prerequisite, reviewed apply/archive, immediate rollback, rerun, and cleanup review.
- Added `tests/test_docs.py` to enforce required migration guide phrases, backup/apply/rollback ordering, README guide linkage, and the English-only docs contract for this plan.
- Updated `README.md` and `graphify update-vault --help` so both distinguish lower-level `--obsidian` export from reviewed `update-vault` migration and mention `graphify-out/migrations/archive/`.

## Task Commits

1. **Task 1 RED: Add migration guide docs contract** - `90ecce3` (test)
2. **Task 1 GREEN: Add v1.8 migration guide** - `afc8ac1` (feat)
3. **Task 1 refinement: Tighten migration guide wording/order** - `2992437` (feat)
4. **Task 2 RED: Add README and CLI help docs contracts** - `dfd0ef5` (test)
5. **Task 2 GREEN: Align README and CLI help** - `ca24880` (feat)

## Files Created/Modified

- `MIGRATION_V1_8.md` - Generic-first v1.8 migration guide with canonical `work-vault/raw` to `ls-vault` example.
- `README.md` - English Obsidian adapter docs now describe direct export and reviewed existing-vault update/migration as separate surfaces.
- `graphify/__main__.py` - Top-level and `update-vault --help` text now include reviewed apply, backup, and archive wording.
- `tests/test_docs.py` - Docs contract tests for guide phrases, ordering, README linkage, and localized README scope.
- `tests/test_main_flags.py` - CLI help contract now checks backup, `--apply --plan-id`, and archive path wording.

## Decisions Made

- Keep the migration guide in the repository root as `MIGRATION_V1_8.md` so README can link to it directly and users can find it beside other top-level guides.
- Keep localized READMEs unchanged per D-08; the tests explicitly scope this contract to English docs.
- Use exact phrase tests for safety-critical wording, including `Back up the target vault before apply`, `Review the migration plan before apply`, and `Rollback immediately after apply/archive if needed`.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** Plan scope was preserved.

## TDD Gate Compliance

- Task 1 RED failed as expected because `MIGRATION_V1_8.md` did not exist yet; GREEN passed after adding the guide.
- Task 2 RED failed as expected because README and CLI help lacked the required v1.8 wording; GREEN passed after updating both surfaces.
- An additional guide refinement commit (`2992437`) was created after the initial guide commit to tighten section wording and ordering while preserving the Task 1 behavior.

## Issues Encountered

- The git hook prints ImageMagick `import` help before graph rebuilds; commits still completed successfully with normal hooks.
- `git add graphify/...` reports the ignored `graphify` path, so tracked changes under `graphify/` were staged explicitly with `git add -f graphify/__main__.py`.
- A transient `.git/index.lock` appeared after the first commit retry. No active Git process was found, and the lock cleared before the retry; no manual lock deletion was needed.

## Known Stubs

None. Stub-pattern scan found no TODO/FIXME/placeholder or UI-empty-data patterns in the files created or modified by this plan.

## Threat Flags

None. This plan changed documentation and CLI help only; no new endpoint, auth path, schema, network, or filesystem trust boundary was introduced beyond the documented migration behavior covered by the plan threat model.

## Verification

- `pytest tests/test_docs.py -q` - 3 passed after Task 1 GREEN
- `pytest tests/test_docs.py tests/test_main_flags.py::test_update_vault_help_lists_command_shape -q` - 5 passed
- `pytest tests/ -q` - 1881 passed, 1 xfailed, 8 warnings

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 36-03 to align packaged platform skill variants with the same v1.8 wording and drift tests.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md`.
- Created/modified files exist: `MIGRATION_V1_8.md`, `tests/test_docs.py`, `README.md`, `graphify/__main__.py`, and `tests/test_main_flags.py`.
- Task commits exist in `git log --oneline --all`: `90ecce3`, `afc8ac1`, `2992437`, `dfd0ef5`, `ca24880`.
- Focused and full verification commands passed.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*
