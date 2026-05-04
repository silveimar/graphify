---
phase: 59-vault-cwd-aware-cli-default
plan: 04
subsystem: cli-dispatch
tags: [vcwd, vault-cwd, flag-plumbing, tdd]
dependency_graph:
  requires: [59-01, 59-02, 59-03]
  provides: [VCWD-04]
  affects: [graphify/__main__.py, tests/test_vault_cwd.py]
tech_stack:
  added: []
  patterns: [boolean-flag-strip, global-pop-mirror, sys.argv-mutation]
key_files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_vault_cwd.py
decisions:
  - Boolean flag parsed via token-strip (not argparse) for symmetry with --vault pattern
  - sys.argv[2:] mutated in-place for branches without pre-gate strip so subsequent parsing is clean
  - g_write_into_vault ORed with lv_write_into_vault at gate call — whichever branch is taken, flag is honored
  - allow-vault-write (Phase 57 harness) kept orthogonal — both coexist independently
metrics:
  duration_seconds: 648
  completed_date: 2026-05-04
  tasks_completed: 2
  files_modified: 2
---

# Phase 59 Plan 04: write-into-vault flag SUMMARY

## One-liner

`--write-into-vault` boolean flag wired globally and per-command via token-strip helpers mirroring `--vault` plumbing; threads into all 14 gated dispatch branches suppressing VCWD-03 refusal only.

## What Was Built

Two new helpers and complete threading through the dispatch ladder:

- `_pop_global_write_into_vault(argv)` at `graphify/__main__.py:1420` — strips leading `--write-into-vault` from argv before subcommand; mirrors `_strip_leading_vault_global_argv` shape
- `_strip_write_into_vault_from_tokens(tokens)` at `graphify/__main__.py:1460` — strips per-command `--write-into-vault` from a token list; mirrors `_strip_vault_flags_from_tokens` shape
- `sys.argv, g_write_into_vault = _pop_global_write_into_vault(sys.argv)` at `graphify/__main__.py:1567` — wired in `main()` after global vault pop

## 14 Branch Insertion Points

| Branch | Strip line | Gate write_into_vault line | Method |
|--------|-----------|--------------------------|--------|
| `--obsidian` | 1817 | 1824 | `_strip_write_into_vault_from_tokens(args)` (args already stripped of vault flags) |
| `--diagram-seeds` | 1959 | 1966 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `--init-diagram-templates` | 2020 | 2027 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `--dedup` | 2076 | 2083 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `snapshot` | 2216 | 2223 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `approve` | 2345 | 2352 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `save-result` | 2629 | 2636 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `elicit` | 2674 | 2681 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place (pre-strips before post-gate `_e_cli` strip) |
| `harness` | 2772 | 2779 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `import-harness` | 2843 | 2850 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place (pre-strips before post-gate `_ih_cli` strip) |
| `run` (pipeline) | 2945 | 2952 | `_strip_write_into_vault_from_tokens(rest)` (rest already stripped of vault flags) |
| `enrich` | 3050 | 3057 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `update-vault` | 3281 | 3288 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |
| `vault-promote` | 3339 | 3346 | `_strip_write_into_vault_from_tokens(sys.argv[2:])` in-place |

## Semantic Guarantees Preserved

- **Profile wins over flag**: `_check_vault_cwd_gate` checks `has_profile` BEFORE `write_into_vault` — VCWD-02 auto-adopt fires even with `--write-into-vault` set.
- **Explicit route wins silently**: `has_explicit_route` check is BEFORE `write_into_vault` — when `--vault` is present, gate returns `"n/a"` immediately; `write_into_vault` is never consulted; no warning emitted.
- **Suppresses VCWD-03 only**: `write_into_vault=True` causes gate to return `"n/a"` (skips refusal) after profile check fails.

## Coexistence with --allow-vault-write (Phase 57 PITFALL-4)

`--allow-vault-write` at `graphify/__main__.py:2843` (harness `import-harness` argparse) is ORTHOGONAL. Both flags coexist:
- `--write-into-vault` → affects `_check_vault_cwd_gate` (VCWD-03 refusal)  
- `--allow-vault-write` → affects `is_obsidian_vault(artifacts)` check AFTER gate dispatch

`grep -c "allow-vault-write" graphify/__main__.py` = 2 (unchanged).

## Test Results

- 4 VCWD-04 tests added (`test_write_into_vault_suppresses_refusal`, `test_global_write_into_vault_suppresses_refusal`, `test_write_into_vault_silent_precedence`, `test_write_into_vault_yields_to_profile`)
- All 4 pass
- Full suite: 2134 passed, 1 xfailed (baseline 2130 + 4)
- Phase 41 regression (`tests/test_vault_cli.py`): 3/3 passed

## Commits

| Hash | Message |
|------|---------|
| 68b6a9e | test(59-04): RED — VCWD-04 --write-into-vault global+per-command, silent precedence |
| a4ab3c2 | feat(59-04): GREEN — VCWD-04 --write-into-vault global+per-command, suppresses refusal only |

## Deviations from Plan

None — plan executed exactly as written. The `sys.argv[2:]` in-place mutation approach for branches without a pre-gate token strip was the natural implementation of the plan's Step 4 template adapted for those branch types.

## TDD Gate Compliance

- RED gate: commit `68b6a9e` with prefix `test(59-04):` — 4 failing tests
- GREEN gate: commit `a4ab3c2` with prefix `feat(59-04):` — 4 passing tests

## Self-Check: PASSED

- `graphify/__main__.py`: exists, contains `_pop_global_write_into_vault` (line 1420) and `_strip_write_into_vault_from_tokens` (line 1460)
- `tests/test_vault_cwd.py`: exists, contains all 4 VCWD-04 test functions
- Commits `68b6a9e` and `a4ab3c2`: verified in git log
- `write_into_vault=False` occurrences: 0 (all replaced)
- `_strip_write_into_vault_from_tokens` call sites: 15 (def + 14 branches)
