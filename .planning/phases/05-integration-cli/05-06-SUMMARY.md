---
phase: 05-integration-cli
plan: "06"
subsystem: cli
tags: [gap-closure, cli, obsidian, profile-validation, phase-5]
dependency_graph:
  requires: [05-01, 05-02, 05-03, 05-04, 05-05]
  provides: [PROF-05-cli, MRG-03-cli]
  affects: [graphify/__main__.py]
tech_stack:
  added: []
  patterns:
    - "function-local imports for heavy deps (consistent with query/save-result/benchmark)"
    - "pre-dispatch flag intercept: if cmd == '--flag': ... sys.exit() before install chain"
    - "community dict reconstruction from node.community attrs (to_json round-trip pattern)"
key_files:
  created:
    - tests/test_main_cli.py
  modified:
    - graphify/__main__.py
decisions:
  - "D-78: thin finished-graph utilities are allowed in __main__.py (pre-dispatch if blocks, not elif in main chain)"
  - "Help text added above 'benchmark' line, matching plan action spec exactly"
  - "Community reconstruction skips None-community nodes (isolates) to avoid phantom community -1"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-11T21:54:27Z"
  tasks_completed: 3
  files_modified: 2
  files_created: 1
  tests_added: 10
  tests_total: 872
requirements_closed: [PROF-05, MRG-03]
---

# Phase 5 Plan 06: Gap Closure — CLI Wiring for --validate-profile and --obsidian Summary

**One-liner:** Added `--validate-profile` and `--obsidian [--dry-run]` top-level CLI flags to `__main__.py` as thin wrappers over `validate_profile_preflight` / `to_obsidian` / `format_merge_plan`, closing the two gaps from 05-VERIFICATION.md.

## Goal Achievement

Both gaps from `05-VERIFICATION.md` are now closed. Evidence from manual spot-checks:

**Gap 1 (PROF-05): `graphify --validate-profile <vault>`**

```
$ python -m graphify --validate-profile /tmp/empty-vault
profile ok — 0 rules, 0 templates validated
exit=0
```

**Gap 2 (MRG-03): `graphify --obsidian --dry-run --graph <fixture.json> --obsidian-dir <tmp>`**

```
$ python -m graphify --obsidian --dry-run --graph /tmp/.../graph.json --obsidian-dir /tmp/.../obsidian
Merge Plan — 3 actions
========================
  CREATE:          3
  UPDATE:          0
  SKIP_PRESERVE:   0
  SKIP_CONFLICT:   0
  REPLACE:         0
  ORPHAN:          0

CREATE (3)
  CREATE  .../obsidian/Atlas/Dots/Things/Attention.md
  CREATE  .../obsidian/Atlas/Dots/Things/Transformer.md
  CREATE  .../obsidian/Atlas/Maps/Uncategorized.md
exit=0
```

Both commands exit with the expected codes and output the required markers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --validate-profile and --obsidian branches to __main__.py | 9cced12 | graphify/__main__.py (+123 lines) |
| 2 | Add tests/test_main_cli.py with subprocess integration tests | 185ef71 | tests/test_main_cli.py (new, +185 lines) |
| 3 | Full-suite regression + verification sweep | (no files changed) | pytest 872 passed |

## Test Results

```
pytest tests/ -q
872 passed in 3.36s
```

- 862 pre-existing tests: all pass (zero regressions)
- 10 new CLI integration tests in `tests/test_main_cli.py`: all pass

## Deviations from Plan

None — plan executed exactly as written. All `<action>` blocks were applied verbatim. The `if cmd == "install":` line (previously `elif`) was correctly converted since the new pre-dispatch blocks both `sys.exit()` before reaching the install chain — no behavioral change to existing commands.

## Known Stubs

None. Both CLI branches are fully wired to production library functions with no placeholder data.

## Threat Flags

No new security surface beyond what the plan's threat model already covers. The `--obsidian` branch follows the identical graph-loading pattern as the existing `query` command (T-05-06-03). Path confinement for vault writes is handled by `to_obsidian` → `apply_merge_plan` → `validate_vault_path` (Phase 1 D-06).

## Self-Check: PASSED

```
[ -f "graphify/__main__.py" ] → FOUND
[ -f "tests/test_main_cli.py" ] → FOUND
git log --oneline | grep "9cced12" → FOUND: feat(05-06): add --validate-profile and --obsidian CLI branches to main()
git log --oneline | grep "185ef71" → FOUND: test(05-06): add CLI integration tests for --validate-profile and --obsidian
pytest tests/ -q → 872 passed (≥ 867 required)
```
