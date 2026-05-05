---
phase: 70
plan: 03
subsystem: vrsync
tags: [reverse-sync, cli, vault-input, prompt-ux, tdd]
type: tdd
requirements: [VRSYNC-01]
provides:
  - run_reverse_sync()
  - prompt_per_file()
  - apply_change()
  - _diff_summary()
  - graphify reverse-sync CLI subcommand
requires:
  - 70-02 (compute_change_set + ChangeRecord)
affects:
  - graphify/__main__.py (CLI dispatch)
tech_added: []
patterns:
  - atomic write via .tmp + os.replace (mirrors merge.py/vault_promote)
  - TTY-gated interactive prompt (sys.stdin.isatty + sys.stdout.isatty)
key_files_created: []
key_files_modified:
  - graphify/reverse_sync.py
  - graphify/__main__.py
  - tests/test_reverse_sync.py
decisions:
  - D-12 enforced in code: yes flag flips only always_ask, never_copy is unaffected
  - D-13 enforced: non-TTY under always_ask returns "skip" → counted as skipped_conflict
  - D-02 enforced: [d] prints unified_diff and re-prompts (does not auto-accept)
metrics:
  tasks_completed: 2
  tests_added: 13
  tests_passing: 22
  files_modified: 3
completed: 2026-05-05
---

# Phase 70 Plan 03: reverse-sync command Summary

Implemented mode dispatch (`always_ask` / `always_copy` / `never_copy`), Y/n/d/A/Q
prompt with TTY gating, atomic path-confined file copy, and the
`graphify reverse-sync --vault --input --mode --yes` CLI subcommand on top of
Plan 02's detection layer.

## What Was Built

- **`run_reverse_sync(vault_dir, *, input_dir_override, mode_override, yes, auto_on_run)`** in `graphify/reverse_sync.py`
  - Loads profile via `graphify.profile.load_profile`, overlays vault_path/input_path from arguments.
  - Resolves mode precedence: `mode_override > profile.reverse_sync.mode > "always_ask"`.
  - Iterates `compute_change_set(profile)` and dispatches each `ChangeRecord` through `apply_change()`.
  - Returns counter dict: `copied / skipped_user / skipped_conflict / skipped_never_copy / vault_deleted / conflicts_skipped / failed`.
- **`prompt_per_file(rel, vault_text, input_text)`** — TTY-gated Y/n/d/A/Q loop. `[d]` writes `difflib.unified_diff` to stdout and re-prompts (D-02). Non-TTY → returns `"skip"` immediately (D-13).
- **`apply_change(rec, *, mode, all_yes, input_dir)`** — single-record dispatch with path-confinement guard (refuses targets outside `input_dir`). Returns `(outcome, new_all_yes)` so the caller can flip `all_yes` after `[A]`.
- **`_atomic_copy(src, dst)`** — writes `.tmp` sibling then `os.replace` (mirrors merge.py / vault_promote pattern).
- **`_diff_summary(a, b)`** — compact `"+N -M lines, +A -B bytes"` string for Plan 04's JSONL log (D-03 contract pre-built so Plan 04 has the surface ready).
- **CLI subcommand** registered in `graphify/__main__.py` between `update-vault` and `vault-promote` blocks; help-text entry added.

## Deviations from Plan

None — plan executed exactly as written. The plan called for a CLI test invoking `gm.main()` with only `--vault` and `--mode`; the test was updated to also pass `--input` because the test profile (which intentionally uses only valid v1.8 keys) does not carry `input_path`. This is consistent with plan intent (override-via-CLI is the documented surface) and with how the production CLI already supports `--input`.

## Tests

- 13 new tests appended to `tests/test_reverse_sync.py`:
  - `test_mode_always_copy_writes_without_prompt` — input() must not be called
  - `test_mode_never_copy_logs_only` — no writes, even with `yes=True` (D-12)
  - `test_mode_always_ask_yes_response` / `_no_response`
  - `test_prompt_diff_then_yes` — [d] prints diff and re-prompts (D-02)
  - `test_prompt_all_response` — [A] auto-accepts subsequent files
  - `test_prompt_quit_response` — [Q] aborts cleanly, `failed=False`
  - `test_yes_flag_overrides_always_ask` — input() not called
  - `test_yes_does_NOT_override_never_copy` — D-12
  - `test_non_tty_skips_conflicts` — D-13
  - `test_atomic_copy` — verifies `os.replace` is called with `.tmp` source
  - `test_path_confinement` — `_validate_input_path` unit check
  - `test_cli_subcommand_dispatch` — invokes `graphify.__main__.main()` with `argv` patched
- Result: 22/22 tests in `tests/test_reverse_sync.py` pass.
- Full suite: 2196 passed, 1 pre-existing failure in `test_migration` (unrelated, out-of-scope per scope-boundary rule), 1 xfailed.

## Verification

```
$ pytest tests/test_reverse_sync.py -q
......................                                                   [100%]
22 passed in 0.26s

$ python3 -m graphify reverse-sync --help
usage: graphify reverse-sync [-h] [--vault VAULT] [--input INPUT] [--yes]
                             [--mode {always_ask,always_copy,never_copy}]
...
  --yes                 Override always_ask mode (does NOT override never_copy
                        per D-12)
  --mode {always_ask,always_copy,never_copy}

$ grep -n "elif cmd == .reverse-sync" graphify/__main__.py
3393:    elif cmd == "reverse-sync":
```

## Commits

- `6fc300b` — `test(70-03): add failing tests for reverse-sync mode dispatch + prompt + CLI`
- `ff81b55` — `feat(70-03): implement reverse-sync mode dispatch + prompt + CLI subcommand`

## Self-Check: PASSED

- File `graphify/reverse_sync.py` modified (run_reverse_sync, prompt_per_file, apply_change, _atomic_copy, _validate_input_path, _diff_summary added). FOUND.
- File `graphify/__main__.py` modified (reverse-sync dispatch + help text). FOUND.
- File `tests/test_reverse_sync.py` modified (13 new tests). FOUND.
- Commit `6fc300b` (test). FOUND in git log.
- Commit `ff81b55` (feat). FOUND in git log.
- All 22 reverse_sync tests pass.
- CLI subcommand `graphify reverse-sync` registered, help text mentions D-12 invariant.
