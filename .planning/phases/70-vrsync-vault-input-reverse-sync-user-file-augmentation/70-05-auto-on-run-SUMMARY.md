---
phase: 70
plan: 05
subsystem: vrsync
tags: [reverse-sync, auto-on-run, hook, integration]
type: execute
requirements: [VRSYNC-01]
provides:
  - auto_on_run hook in `graphify run`
  - auto_on_run hook in `graphify update-vault`
  - D-11 warn-and-continue error handling at hook sites
  - D-11 stderr summary when conflicts_skipped > 0
requires:
  - 70-03 (run_reverse_sync entry point + auto_on_run kwarg)
  - 70-04 (JSONL log path / conflicts_skipped in result dict)
affects:
  - graphify/__main__.py
tech_added: []
patterns:
  - Local-import-inside-if guards keep lazy-load convention
  - Try/except wrapper at the hook site (D-11 warn-and-continue)
key_files_created:
  - tests/test_auto_on_run.py
key_files_modified:
  - graphify/__main__.py
decisions:
  - D-11 enforced at both hook sites: any exception from run_reverse_sync
    is caught, warning emitted to stderr, parent command continues
  - Hook placed AFTER target/vault path resolution (so input_dir_override is known)
  - Hook gated on `profile.reverse_sync.auto_on_run` truthy AND
    (for run cmd) `resolved.vault_path is not None`
  - Pitfall 5 actively verified by test_no_recursion (reverse-sync does not
    re-invoke run — log line count == change count, not 2× change count)
metrics:
  tasks_completed: 2
  tests_added: 6
  tests_passing: 121
  files_modified: 2
completed: 2026-05-05
---

# Phase 70 Plan 05: auto_on_run Hook Summary

Wired the `auto_on_run` hook into the two parent commands (`graphify run` and
`graphify update-vault`). When `profile.reverse_sync.auto_on_run` is truthy,
the hook fires AFTER profile/vault/target resolution and BEFORE the main
pipeline call. Failures and skipped conflicts warn-and-continue per D-11,
satisfying Success Criterion 4 without ever blocking the parent command.

## What Was Built

- **Hook in `cmd == "run"`** (`graphify/__main__.py`): inserted right after
  the `target.exists()` guard and before `_foreground_acquire_enrichment_lock`.
  Calls `run_reverse_sync(resolved.vault_path, input_dir_override=target,
  auto_on_run=True)` and prints the D-11 conflict-skipped hint to stderr if
  `conflicts_skipped > 0`. Exceptions caught and logged as
  `[graphify] reverse-sync: skipped due to error: <exc>`.
- **Hook in `cmd == "update-vault"`**: inserted after `format_migration_preview`
  / `run_update_vault` import and before the `run_update_vault` call. Loads
  the profile via `load_profile(_uv_vault)` to read the `reverse_sync` block,
  then calls `run_reverse_sync(_uv_vault, input_dir_override=opts.input,
  auto_on_run=True)` with the same D-11 wrapping.
- **Local imports** (`from graphify.reverse_sync import run_reverse_sync`)
  live inside the if-block to preserve the lazy-load convention from
  `__init__.py`.

## Deviations from Plan

None substantive. Two implementation refinements worth recording:

1. **Hook placement** — the plan suggested "immediately after profile load",
   but `target` (the corpus path used as `input_dir_override`) is computed
   ~10 lines later in the run block. Hook moved AFTER target resolution so
   the reverse-sync call sees the right input. No semantic change; profile
   has already loaded by then.
2. **input_dir_override propagation** — `run_reverse_sync` reads
   `profile["input_path"]` from the loaded profile, but built-in profiles
   don't set that key. The hook explicitly passes `input_dir_override=target`
   (run) / `Path(opts.input)` (update-vault) so reverse-sync mirrors into the
   actual user-specified corpus rather than failing with KeyError. The
   override path was already supported by Plan 03's signature.

## Tests

6 new integration tests in `tests/test_auto_on_run.py`:

- `test_run_with_auto_on_run_true_fires_hook` — vault with new file, profile
  auto_on_run=true; after `main()`, file mirrored into input + log line written
- `test_run_with_auto_on_run_false_skips_hook` — auto_on_run=false (default):
  no log file, no mirror
- `test_update_vault_with_auto_on_run_true_fires_hook` — same proof for the
  `update-vault` cmd block
- `test_auto_on_run_failure_warn_continue` — `run_reverse_sync` monkey-patched
  to raise; assert no exception bubbles, stderr captures
  `[graphify] reverse-sync: skipped due to error`, pipeline still ran
- `test_auto_on_run_conflicts_skipped_summary` — `run_reverse_sync` returns
  `conflicts_skipped=3`; stderr matches the D-11 wording
  `reverse-sync: 3 conflicts skipped — run 'graphify reverse-sync' to resolve`
- `test_no_recursion` — 2 changes → exactly 2 log entries (Pitfall 5 guard)

`run_corpus` and `run_update_vault` are stubbed via `monkeypatch.setattr`
so tests don't drive the heavy pipeline; the hook fires before the stub.

## Verification

```
$ pytest tests/test_auto_on_run.py -q
......
6 passed

$ pytest tests/test_auto_on_run.py tests/test_commands.py tests/test_reverse_sync.py \
        tests/test_cli_run.py tests/test_main_cli.py tests/test_main_flags.py -q
121 passed in 51.46s

$ grep -c "auto_on_run" graphify/__main__.py
6   # 2 hook sites (gate check + call) + comments

$ grep -c "reverse-sync: .* conflicts skipped" graphify/__main__.py
2   # one D-11 message per command block
```

## Commits

- `9dcddc5` — `test(70-05): add failing tests for auto_on_run hook`
- `13a8cb3` — `feat(70-05): wire auto_on_run hook into run and update-vault`

## Self-Check: PASSED

- `tests/test_auto_on_run.py` — FOUND (282 lines, 6 tests)
- `graphify/__main__.py` — modified at both hook sites; FOUND
- Commit `9dcddc5` (RED) — FOUND in git log
- Commit `13a8cb3` (GREEN) — FOUND in git log
- All 6 auto_on_run tests pass; 121 regression tests pass
- D-11 wording verified verbatim by `test_auto_on_run_conflicts_skipped_summary`
- Pitfall 5 invariant verified by `test_no_recursion`
