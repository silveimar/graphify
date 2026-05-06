---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 09
subsystem: cli/reverse-sync-hook
tags: [bugfix, gap-closure, tdd, vrsync, vprof]
requires: [70-05]
provides: [auto_on_run_uses_raw_target]
affects: [graphify/__main__.py:run-cmd]
tech_stack:
  added: []
  patterns: [tdd-red-green]
key_files:
  created:
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-09-auto-on-run-input-dir-SUMMARY.md
  modified:
    - graphify/__main__.py
    - tests/test_auto_on_run.py
decisions:
  - "Use raw_target (pre-D-07) for the auto_on_run hook's input_dir_override; D-07 still rewrites the pipeline target."
metrics:
  duration_minutes: 5
  tasks_completed: 2
  completed_date: 2026-05-05
requirements: [VRSYNC-01, VPROF-03]
---

# Phase 70 Plan 09: Auto-on-run Input Dir Fix Summary

One-liner: Auto-on-run reverse-sync hook in `graphify run` now passes the user's raw input path (pre-D-07) as `input_dir_override`, restoring vault-only file augmentation when cwd != input dir (UAT Test 5).

## Tasks

| # | Name              | Type | Commit  |
|---|-------------------|------|---------|
| 1 | RED tests         | test | df434c8 |
| 2 | GREEN one-line fix| fix  | aa86035 |

## Changes

### graphify/__main__.py

In the `run` command's `auto_on_run` hook (~line 3010), replaced
`input_dir_override=target,` with
`input_dir_override=Path(raw_target).resolve(),`. The pipeline `target`
continues to be D-07-rewritten to CWD when the vault auto-adopts a
profile; only the reverse-sync hook now bypasses the rewrite. The
second hook site at line 3419 (update-vault cmd) was untouched — it
already uses `Path(opts.input)`.

### tests/test_auto_on_run.py

Added two tests:

- `test_auto_on_run_uses_raw_target_for_input_dir_override` —
  monkeypatches `run_reverse_sync`, runs from cwd=tmp_path with
  `--vault` and an explicit input dir, asserts the captured
  `input_dir_override` equals the user input dir (not cwd).
- `test_auto_on_run_copies_vault_only_file_to_user_input_dir` —
  UAT-5 reproduction: vault-only `People/Bob.md`, `auto_on_run: true`,
  `mode: always_copy`, cwd=parent of vault. Asserts Bob.md ends up in
  the user's input dir.

## Verification

- `pytest tests/test_auto_on_run.py tests/test_reverse_sync.py -q` → 43 passed
- `pytest tests/ -q` → 2241 passed, 1 pre-existing unrelated failure
  (`tests/test_migration.py::test_preview_expands_risky_action_rows`,
  confirmed reproducible with this plan's changes stashed)
- Grep invariants:
  - `input_dir_override=Path(raw_target).resolve()` → 1 match
  - `input_dir_override=target,` → 0 matches
  - `input_dir_override=Path(opts.input)` → 2 matches (untouched)

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED commit: `df434c8 test(70-09): add RED tests …`
- GREEN commit: `aa86035 fix(70-09): auto_on_run hook uses raw_target …`
- No REFACTOR step needed (one-line change).

## Self-Check: PASSED

- FOUND: graphify/__main__.py (line 3012 verified via grep)
- FOUND: tests/test_auto_on_run.py
- FOUND: commit df434c8
- FOUND: commit aa86035
