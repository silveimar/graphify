---
phase: 35-templates-export-plumbing-dry-run-migration-visibility
plan: 03
subsystem: export
tags: [migration, cli, obsidian, dry-run, repo-identity, tdd]

requires:
  - phase: 35-templates-export-plumbing-dry-run-migration-visibility
    provides: Migration preview foundation and repo identity metadata from Plans 01-02
provides:
  - Preview-first `graphify update-vault --input work-vault/raw --vault ls-vault` command
  - Raw-corpus-to-vault migration orchestration helper
  - Apply-by-plan-id validation before vault writes
  - Repo identity drift classification as `SKIP_CONFLICT`
affects: [phase-35, phase-36, migration-cli, obsidian-export]

tech-stack:
  added: []
  patterns: [preview-first-cli, classified-merge-plan-apply, content-digest-plan-gate]

key-files:
  created:
    - .planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-03-SUMMARY.md
  modified:
    - tests/test_main_flags.py
    - tests/test_migration.py
    - graphify/migration.py
    - graphify/__main__.py
    - graphify/export.py

key-decisions:
  - "update-vault previews by default and only applies with a reviewed plan id."
  - "Apply uses a validated classified MergePlan and apply_merge_plan(), not a fresh unclassified dry_run=False export."
  - "Existing concrete repo identity drift becomes a review-only repo_identity_drift SKIP_CONFLICT."

patterns-established:
  - "Migration CLI path: parse command flags in __main__.py, delegate orchestration to graphify.migration."
  - "Dry-run render context can be returned explicitly for validated apply without changing default to_obsidian() behavior."

requirements-completed: [COMM-02, REPO-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-06]

duration: 9min
completed: 2026-04-29
---

# Phase 35 Plan 03: update-vault CLI Summary

**Preview-first raw corpus to Obsidian vault updates with reviewed plan-id apply gates and repo-drift conflict visibility**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-29T05:48:24Z
- **Completed:** 2026-04-29T05:57:43Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added Wave 0 tests for `graphify update-vault` preview defaults, `--apply --plan-id` gating, help text, stale-plan rejection, and repo identity drift conflicts.
- Added `run_update_vault()` orchestration that resolves input/vault paths, runs the raw corpus pipeline, renders a dry-run merge plan, writes migration artifacts, and rejects mismatched apply requests before vault writes.
- Wired the `update-vault` CLI branch with required `--input` and `--vault` flags, preview output, `--repo-identity`, `--router`, `--verbose`, and guarded apply semantics.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 update-vault CLI and drift tests** - `067dc65` (`test`)
2. **Task 2: Add update-vault orchestration helper** - `2c9a1be` (`feat`)
3. **Task 3: Wire update-vault CLI and apply-by-plan-id gate** - `1450bfa` (`feat`)

## Files Created/Modified

- `tests/test_main_flags.py` - CLI subprocess coverage for preview default, apply gate, and help command shape.
- `tests/test_migration.py` - Helper-level coverage for stale plan rejection and repo identity drift conflict classification.
- `graphify/migration.py` - update-vault orchestration, repo-drift classification, reviewed-action filtering, and validated apply handoff.
- `graphify/__main__.py` - `update-vault` argparse branch and top-level help entry.
- `graphify/export.py` - Optional render-context return for dry-run exports so migration apply can reuse the current rendered notes safely.

## Decisions Made

- `update-vault` delegates all workflow logic to `graphify.migration.run_update_vault()` so CLI parsing stays thin and testable.
- Valid apply reconstructs a `MergePlan` only from reviewed CREATE, UPDATE, and REPLACE rows, leaving `SKIP_CONFLICT`, `SKIP_PRESERVE`, and `ORPHAN` review-only.
- `to_obsidian()` default behavior remains unchanged; the migration path opts into render-context return only during dry-run preparation.

## Verification

- `pytest tests/test_main_flags.py::test_update_vault_preview_default_runs_pipeline tests/test_main_flags.py::test_update_vault_apply_without_plan_id_exits_two tests/test_main_flags.py::test_update_vault_help_lists_command_shape tests/test_migration.py::test_update_vault_rejects_stale_plan_id tests/test_migration.py::test_repo_identity_drift_becomes_skip_conflict -q` -> 5 passed, 2 dependency warnings.
- `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q` -> 199 passed, 2 dependency warnings.
- Acceptance grep checks passed for the required test names, CLI branch and arguments, migration helper anchors, `filter_applicable_actions`, `apply_merge_plan`, and absence of `dry_run=False` in `graphify/migration.py`.

## TDD Gate Compliance

- RED gate: `067dc65` added failing tests before the `update-vault` command, `run_update_vault()`, and repo-drift classification existed.
- GREEN gate: `2c9a1be` implemented the migration helper and repo-drift classification.
- GREEN gate: `1450bfa` implemented the CLI branch and apply-by-plan-id gate.
- REFACTOR gate: Not needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Repository ignore rules hid files under `graphify/`, so source files were staged explicitly with `git add -f`, consistent with earlier Phase 35 plans.
- The git hook prints ImageMagick `import` usage before rebuilding the Graphify graph, but the hook completes and commits succeed.

## Known Stubs

None. Stub scan hits were existing string defaults, empty test fixtures, argparse defaults, or UI placeholder text in the HTML visualization, not runtime stubs introduced by this plan.

## Threat Flags

None. The new CLI filesystem surface, plan-id lookup, stale-plan validation, repo identity drift, user-modified preservation, and legacy non-deletion behavior are all covered by the plan threat model.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 35 now has all three plans implemented. Phase 36 can document the real migration workflow and align skill/docs around the new preview/apply command.

## Self-Check: PASSED

- Found required summary file: `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-03-SUMMARY.md`.
- Found task commits in git history: `067dc65`, `2c9a1be`, and `1450bfa`.

---
*Phase: 35-templates-export-plumbing-dry-run-migration-visibility*
*Completed: 2026-04-29*
