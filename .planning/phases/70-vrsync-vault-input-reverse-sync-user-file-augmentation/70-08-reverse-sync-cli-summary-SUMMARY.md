---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 08
subsystem: reverse_sync
tags: [vrsync, cli, ux, gap-closure, tdd]
gap_closure: true
requirements: [VRSYNC-01]
dependency_graph:
  requires:
    - graphify/reverse_sync.py::run_reverse_sync (Plan 03)
    - graphify/reverse_sync.py::counters dict (Plan 03)
  provides:
    - "run_reverse_sync emits per-file outcome lines + final totals line on stdout"
  affects:
    - operator UX of `graphify reverse-sync` command
tech_stack:
  added: []
  patterns:
    - "stdout summary via plain print() (info channel; warnings still go to stderr)"
key_files:
  created: []
  modified:
    - graphify/reverse_sync.py
    - tests/test_reverse_sync.py
decisions:
  - "Use plain print() (stdout) rather than logging or stderr — these are operator-facing summary lines, not warnings."
  - "No --quiet flag (out of scope; no precedent in cmd_reverse_sync arg parser)."
  - "kind=='skip' (unchanged file) remains silent per D-14 — not a sync event."
  - "outcome=='quit' breaks the loop and emits no per-file line, but the totals line is still printed."
metrics:
  duration_minutes: ~5
  tasks_completed: 2
  completed_date: 2026-05-05
---

# Phase 70 Plan 08: Reverse-Sync CLI Summary

`graphify reverse-sync` now prints a per-file outcome line for every non-skip
record and a final totals line, closing UAT Test 3 (VRSYNC-01).

## What Shipped

- **Per-record stdout line**: For each `outcome` in
  `{copied, skipped_user, skipped_conflict, skipped_never_copy, vault_deleted}`,
  `run_reverse_sync` prints `[graphify] reverse-sync: <outcome> <rel_path>`
  immediately after the apply_change guards (skip/quit) and before the JSONL
  audit append.
- **Final totals line**: After the loop completes (and before `result =
  dict(counters)`), `run_reverse_sync` always prints
  `[graphify] reverse-sync: totals copied=N skipped_user=N skipped_conflict=N
  skipped_never_copy=N vault_deleted=N`.
- **Silence preserved for unchanged files** (`kind=="skip"`): no per-record
  line; only the totals line (showing copied=0) is emitted.
- **Return shape, exit codes, JSONL log format**: unchanged.

## Commits

| Commit  | Type | Message                                                          |
| ------- | ---- | ---------------------------------------------------------------- |
| 00b59c5 | test | test(70-08): add RED tests for reverse-sync stdout summary       |
| 55be6b3 | feat | feat(70-08): emit per-file + totals stdout summary in reverse-sync |

## TDD Gate Compliance

- RED gate (`test(...)`): 00b59c5 — 4 tests added, all failing as expected.
- GREEN gate (`feat(...)`): 55be6b3 — 4 tests pass; full
  `pytest tests/test_reverse_sync.py -q` clean (39 passed).
- REFACTOR gate: not needed — implementation is two small print blocks.

## Tests Added

In `tests/test_reverse_sync.py`:

1. `test_run_reverse_sync_emits_per_file_copied_line` — asserts copied line for
   `People/Alice.md` in `always_copy` mode.
2. `test_run_reverse_sync_emits_totals_line` — asserts the exact totals
   substring with `copied=1`.
3. `test_run_reverse_sync_silent_on_unchanged` — vault and input are identical;
   asserts no per-record `copied` line, totals shows `copied=0`.
4. `test_run_reverse_sync_emits_skipped_never_copy_line` — `never_copy` mode
   emits `[graphify] reverse-sync: skipped_never_copy People/Alice.md`.

A small `_setup_people_dirs(tmp_path)` helper was added (parallels existing
`_setup_dirs` but uses the `People/` user-only folder called out in the plan).

## Verification

- `pytest tests/test_reverse_sync.py -q`: **39 passed**.
- `pytest tests/ -q`: 2241 passed, 1 xfailed, 3 pre-existing failures
  (`test_detect_skips_dotfiles`, `test_collect_files_skips_hidden`,
  `test_preview_expands_risky_action_rows`) confirmed unrelated to this plan
  by re-running with the working tree stashed (same 3 failures on the parent
  commit). See Deferred Issues below.

## Deviations from Plan

None — plan executed exactly as written. The substring assertions, the four
test names, the in-loop print, and the post-loop totals print all match the
plan's `<action>` block verbatim.

## Deferred Issues

These pre-existing failures are out of scope for plan 70-08 and were already
failing on the parent commit (`3f29bde`):

- `tests/test_detect.py::test_detect_skips_dotfiles`
- `tests/test_extract.py::test_collect_files_skips_hidden`
- `tests/test_migration.py::test_preview_expands_risky_action_rows`

(Logged to `.planning/phases/70-.../deferred-items.md` for follow-up.)

## Self-Check: PASSED

- File `graphify/reverse_sync.py`: FOUND (modified)
- File `tests/test_reverse_sync.py`: FOUND (modified)
- Commit `00b59c5` (RED): FOUND in worktree branch
- Commit `55be6b3` (GREEN): FOUND in worktree branch
- `grep -c 'reverse-sync: totals copied=' graphify/reverse_sync.py` == 1
- `grep -c 'def test_run_reverse_sync_emits_per_file_copied_line' tests/test_reverse_sync.py` == 1
- `grep -c 'def test_run_reverse_sync_emits_totals_line' tests/test_reverse_sync.py` == 1
- `grep -c 'def test_run_reverse_sync_silent_on_unchanged' tests/test_reverse_sync.py` == 1
- `grep -c 'def test_run_reverse_sync_emits_skipped_never_copy_line' tests/test_reverse_sync.py` == 1
