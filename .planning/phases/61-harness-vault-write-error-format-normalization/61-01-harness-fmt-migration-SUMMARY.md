---
phase: 61
plan: 01
subsystem: harness-import / cli-output
tags: [tdd, vault-safety, error-format, refactor]
type: tdd
requires: [_emit_vault_error in graphify/output.py]
provides: [uniform two-line "[graphify] error:" + "  hint:" surface for harness vault-write refusal]
affects: [graphify/__main__.py, tests/test_harness_import.py]
tech-stack:
  added: []
  patterns: [VAUX-02 two-line error format adoption]
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_harness_import.py
decisions:
  - D-02 strict scope: only line 2727 refusal migrated; adjacent ~:2745 print untouched
  - D-03 exit code: defaulted to 1 via _emit_vault_error (was sys.exit(2))
  - D-04 msg verbatim: "Refusing to write harness import under vault root {artifacts}"
  - D-05 hint verbatim: "Pass --allow-vault-write to override."
  - D-07 keep --allow-vault-write assertion in test
  - D-08 strict TDD ordering: RED commit before GREEN commit
metrics:
  duration_minutes: 4
  tasks_completed: 2
  completed_date: 2026-05-04
---

# Phase 61 Plan 01: Harness Vault-Write Error Format Migration Summary

Migrated the harness import vault-write refusal at `graphify/__main__.py:2727` from an
ad-hoc 5-line `print(...) ; sys.exit(2)` to the canonical `_emit_vault_error(msg, hint)`
helper, locking in the uniform `[graphify] error: ... \n  hint: ...` two-line surface
that the rest of the vault subsystem already emits.

## Tasks Completed

| Gate     | Description                                                             | Commit  |
| -------- | ----------------------------------------------------------------------- | ------- |
| RED      | Tighten harness vault-write assertions to lock two-line shape           | 28f27ea |
| GREEN    | Migrate harness vault-write refusal to `_emit_vault_error` two-line fmt | 2413f18 |
| REFACTOR | N/A — `_emit_vault_error` already encapsulates the format               | —       |

## Test Evidence

- **RED**: `pytest tests/test_harness_import.py::test_import_refuses_vault_rooted_output -q`
  failed on `assert "[graphify] error:" in rc.stderr` against the live one-line stderr,
  confirming the new assertions actually exercise the contract before the migration.
- **GREEN**: `pytest tests/test_harness_import.py -q` → `10 passed in 0.55s`.
- **Full suite**: `pytest tests/ -q` → `2123 passed, 1 xfailed in 103.45s`.

## Acceptance Checks

| Check                                                  | Result |
| ------------------------------------------------------ | ------ |
| `raise _emit_vault_error` present at harness site      | PASS   |
| Old `refusing to write harness import` text absent     | PASS   |
| `_emit_vault_error` imported in `__main__.py`          | PASS (2 occurrences: 1 import, 1 raise) |
| Test asserts `[graphify] error:`                       | PASS   |
| Test asserts `hint:`                                   | PASS   |
| Test asserts old text NOT present                      | PASS   |
| Test asserts `--allow-vault-write`                     | PASS   |
| Adjacent `~:2745` print untouched (D-02)               | PASS (verified via diff)   |

## Deviations from Plan

None — plan executed exactly as written. RED, GREEN, REFACTOR (skipped per plan), all
within the scope locked by D-02..D-08.

## Decisions Made

- **Exit code 1** (not the previous 2): per D-03, the test asserts `rc.returncode != 0`,
  so dropping to the helper default is observably safe.
- **Single-line import update**: extended the existing local import to add
  `_emit_vault_error` alongside `is_obsidian_vault`, avoiding a second import line.

## Files Changed

- `graphify/__main__.py` — 4 insertions, 6 deletions (5-line block → 4-line `raise`).
- `tests/test_harness_import.py` — 4 insertions (3 new assertions + comment).

## Self-Check: PASSED

- `[ -f graphify/__main__.py ]` — FOUND
- `[ -f tests/test_harness_import.py ]` — FOUND
- `git log --oneline | grep 28f27ea` — FOUND (RED commit)
- `git log --oneline | grep 2413f18` — FOUND (GREEN commit)
- `! grep -q 'refusing to write harness import' graphify/__main__.py` — PASS (text absent)
- `pytest tests/ -q` — PASS (2123 passed)
