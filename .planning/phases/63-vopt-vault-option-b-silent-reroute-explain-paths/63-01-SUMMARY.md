---
phase: 63
plan: "01"
subsystem: vault-output-resolver
tags: [vault, path-resolution, cli, breadcrumb, tdd]
requirements_closed: [VOPT-01, VOPT-02]
dependency_graph:
  requires: []
  provides:
    - "ResolvedSource literal value 'option-b'"
    - "graphify.output.emit_option_b_breadcrumb (idempotent process-once)"
    - "graphify.output._emit_vault_info advisory breadcrumb helper"
    - "_check_vault_cwd_gate cli_path_override parameter"
  affects:
    - "graphify run / --obsidian / doctor / elicit / import-harness output paths from a no-profile vault CWD"
tech_stack:
  added: []
  patterns:
    - "Once-per-process sentinel (D-02 single-emission breadcrumb)"
    - "Pre-argparse token scan (_has_path_override_in_tokens) to hoist routing decisions before subcommand argparse"
    - "Strict-trigger override parameter (obsidian_dir_override) instead of try/except SystemExit"
key_files:
  created: []
  modified:
    - graphify/output.py
    - graphify/__main__.py
    - graphify/doctor.py
    - tests/test_output_path_matrix.py
    - tests/test_vault_cwd.py
    - tests/test_output.py
    - tests/test_main_flags.py
decisions:
  - "Emit Option B breadcrumb at the gate (not just resolver) so subcommands that exit before resolve_output (update-vault, enrich, etc.) still surface the info: / hint: lines; once-per-process sentinel prevents resolver from double-emitting."
  - "Pre-parse argv scan via _has_path_override_in_tokens — gate decides Option B routing before each subcommand's argparse runs, so D-02 strict-trigger (--output / --obsidian-dir) suppression works uniformly across all 14 gated branches."
  - "Doctor's _classify_vault_cwd flips 'refuse' → 'option-b' to maintain doctor↔runtime parity contract."
metrics:
  duration_minutes: 28
  completed: "2026-05-06"
  tasks_completed: "2/2 (Task 1 RED in commit 3e3503c, Task 2 GREEN in commit f11a0e6)"
---

# Phase 63 Plan 01: Option B Silent Vault Reroute — Resolver + Gate + CLI Forwarding

Implements VOPT-01 (silent reroute) and VOPT-02 (single-emission two-line breadcrumb) using a TDD RED → GREEN cycle.

## What changed

When CWD is an Obsidian vault that lacks `.graphify/profile.yaml` AND neither `--output` nor `--obsidian-dir` was passed, graphify silently reroutes outputs to `<vault>/.graphify-out/` (notes_dir = `<vault>/.graphify-out/obsidian`, artifacts_dir = `<vault>/.graphify-out`) and emits exactly one two-line `[graphify] info: vault CWD without .graphify/profile.yaml — Option B reroute active` / `  hint: outputs → <vault>/.graphify-out/` breadcrumb on stderr. The legacy VAULT-08 `vault detected at` line is suppressed on this branch. `_check_vault_cwd_gate` no longer pre-empts the resolver with EXIT_VAULT_GATE; it now returns "option-b" (or "n/a" when caller passes a path override) and emits the breadcrumb at the gate so subcommands that exit early still surface it.

## Commits

| Task | Commit  | Subject                                                                                                                                              |
| ---- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | 3e3503c | test(63-01): RED — failing tests for Option B reroute, breadcrumb, gate harmonization, run-subcommand --output suppression                            |
| 2    | f11a0e6 | feat(63-01): GREEN — Option B silent reroute resolver + VCWD-03 gate harmonization + CLI --output forwarding audit (VOPT-01, VOPT-02)                |

## CLI subcommands audited (B2)

Every `_check_vault_cwd_gate(...)` call site now passes `cli_path_override=_has_path_override_in_tokens(<tokens>)`. Audited branches (14 total):

| Branch                         | Token source     |
| ------------------------------ | ---------------- |
| `--obsidian`                   | `args`           |
| `--diagram-seeds`              | `sys.argv[2:]`   |
| `--init-diagram-templates`     | `sys.argv[2:]`   |
| `--dedup`                      | `sys.argv[2:]`   |
| `snapshot`                     | `sys.argv[2:]`   |
| `approve`                      | `sys.argv[2:]`   |
| `save-result`                  | `sys.argv[2:]`   |
| `elicit`                       | `sys.argv[2:]`   |
| `harness`                      | `sys.argv[2:]`   |
| `import-harness`               | `sys.argv[2:]`   |
| `run`                          | `rest`           |
| `enrich`                       | `sys.argv[2:]`   |
| `update-vault`                 | `sys.argv[2:]`   |
| `vault-promote`                | `sys.argv[2:]`   |

B3 grep equality: `grep -c 'cli_path_override=' graphify/__main__.py == 14` and `grep -c '_check_vault_cwd_gate(' graphify/__main__.py == 15` (= 14 call sites + 1 def line).

## Verification

- `pytest tests/test_output_path_matrix.py tests/test_vault_cwd.py -q` → **35 passed** (incl. 7 new `test_option_b_*` and B2 integration)
- `pytest tests/test_output.py tests/test_routing_audit.py -q` → **38 passed**
- `pytest tests/ -q --ignore=tests/test_migration.py` → **2242 passed, 1 xfailed**
- `python -m graphify --help` shows precedence line including `option-b (vault)`
- B3 grep equality holds: 14 == 15 - 1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test breakage from intentional behavior change] Updated three pre-existing tests**

- **Found during:** Task 2 GREEN, after running broader test suite.
- **Issue:**
  - `tests/test_output.py::test_resolve_output_vault_no_profile_refuses` directly asserted the legacy refuse path that Phase 63 replaces with Option B reroute.
  - `tests/test_main_flags.py::test_run_in_vault_no_profile_refuses` asserted exit ≠ 0 plus the legacy refusal text — both no longer fire post-Option-B.
  - `tests/test_vault_cwd.py::test_write_into_vault_suppresses_refusal` and `::test_global_write_into_vault_suppresses_refusal` previously relied on `_refuse(...)` exiting before `run` parsed `--help`. With Option B replacing that refusal, `run` now treats `--help` as a missing path and exits 2, tripping `assert returncode != 2` for an unrelated reason.
- **Fix:**
  - `test_resolve_output_vault_no_profile_refuses`: assert Option B silent reroute by default; assert refuse only when `obsidian_dir_override=True`.
  - `test_run_in_vault_no_profile_refuses`: assert no legacy refusal text and presence of "Option B reroute active" breadcrumb.
  - The two `--write-into-vault` tests: pass an existing corpus path (`vault/doc.md`) instead of `--help`, so the no-VCWD-03-refusal contract is locked without colliding with run's path-not-found exit.
- **Files modified:** tests/test_output.py, tests/test_main_flags.py, tests/test_vault_cwd.py
- **Commit:** f11a0e6

**2. [Rule 2 - Missing critical functionality] Added once-per-process sentinel for Option B breadcrumb**

- **Found during:** Task 2 GREEN, when the new B1 test `test_gate_runs_for_each_gated_cmd` discovered subcommands that exit before reaching `resolve_output()` never emitted the info breadcrumb.
- **Issue:** Plan called for resolver-side emission only, but ~10 of the 14 gated subcommands either argparse-error or print help and exit before the resolver runs (so users never saw the breadcrumb).
- **Fix:** Added `emit_option_b_breadcrumb(vault_cwd)` in `graphify/output.py` guarded by `_OPTION_B_BREADCRUMB_EMITTED` module flag. Gate emits when returning "option-b". Resolver also calls `emit_option_b_breadcrumb(...)` — the sentinel makes the second call a no-op so `run` / `--obsidian` (which hit both gate and resolver) still emit exactly two non-empty stderr lines.
- **Test support:** `_reset_option_b_breadcrumb_for_tests()` plus an autouse fixture in `tests/test_output_path_matrix.py` reset the sentinel between unit tests.
- **Files modified:** graphify/output.py, graphify/__main__.py, tests/test_output_path_matrix.py
- **Commit:** f11a0e6

**3. [Rule 2 - Missing critical functionality] Updated graphify.doctor classifier + renderer**

- **Found during:** Task 2 GREEN; `tests/test_vault_cwd.py::test_doctor_three_outcomes` and `test_doctor_runtime_parity` (flipped in RED commit) require doctor to predict `option-b` and parity with runtime.
- **Issue:** `_classify_vault_cwd` returned "refuse" for vault+no-profile; `format_report` rendered `[vault-cwd] refuse — ...`. Both broke parity with the new runtime gate.
- **Fix:** `_classify_vault_cwd` now returns `"option-b"`. `format_report` renders `[vault-cwd] option-b — vault at <cwd>, no .graphify/profile.yaml; outputs → <vault>/.graphify-out/`.
- **Files modified:** graphify/doctor.py
- **Commit:** f11a0e6

## Authentication gates

None.

## Known Stubs

None — all changes wire real behavior.

## Threat Flags

None — Phase 63 changes affect existing trust boundaries (already covered by the threat register in 63-01-PLAN.md). No new network endpoints, auth paths, or schema changes introduced.

## TDD Gate Compliance

- RED commit `3e3503c`: subject `test(63-01): RED — ...` ✓
- GREEN commit `f11a0e6`: subject `feat(63-01): GREEN — ...` ✓
- No REFACTOR commit (none required).

## Pre-existing failures (excluded from Phase 63 verdict)

- `tests/test_migration.py::test_preview_expands_risky_action_rows` — pre-existing failure unrelated to Phase 63 (memory 5920). Not touched.

## Self-Check: PASSED

- Created files: none (this plan modified existing files only).
- Modified files verified present:
  - graphify/output.py (FOUND)
  - graphify/__main__.py (FOUND)
  - graphify/doctor.py (FOUND)
  - tests/test_output_path_matrix.py (FOUND)
  - tests/test_vault_cwd.py (FOUND)
  - tests/test_output.py (FOUND)
  - tests/test_main_flags.py (FOUND)
- Commits verified in git log: 3e3503c (RED) FOUND, f11a0e6 (GREEN) FOUND.
