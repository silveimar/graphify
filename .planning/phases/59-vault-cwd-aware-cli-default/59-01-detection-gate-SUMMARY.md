---
phase: 59-vault-cwd-aware-cli-default
plan: "01"
subsystem: cli-dispatch
tags: [vcwd, vault-detection, cli-gate, tdd]
dependency_graph:
  requires: []
  provides: [_check_vault_cwd_gate, test_vault_cwd.py, VCWD-01]
  affects: [graphify/__main__.py, tests/test_vault_cwd.py]
tech_stack:
  added: []
  patterns: [single-gate-helper, dispatch-time-insertion, before-argparse-insertion]
key_files:
  created:
    - tests/test_vault_cwd.py
  modified:
    - graphify/__main__.py
decisions:
  - "_check_vault_cwd_gate inserted BEFORE argparse.parse_args() in all argparse-using branches so --help still triggers gate refusal from profile-less vault CWD"
  - "is_obsidian_vault(Path.cwd().resolve()) used as detection primitive per CONTEXT D-01 — no duplication"
  - "Pre-existing is_obsidian_vault check at __main__.py:2849 checks artifacts output path (not CWD) — orthogonal to VCWD gate, left untouched"
metrics:
  duration: "~13 minutes"
  completed: "2026-05-04"
  tasks_completed: 3
  files_changed: 2
---

# Phase 59 Plan 01: Detection Gate Summary

**One-liner:** Single `_check_vault_cwd_gate` helper + 14 dispatch call sites gates all output-producing CLI commands when running from a profile-less Obsidian vault CWD (exits 2 with two-line error).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Wave 0: Create tests/test_vault_cwd.py | 9ae740d | tests/test_vault_cwd.py |
| 1 (RED) | RED — tests fail on unmodified codebase | (no separate commit — RED confirmed against Task 0) | — |
| 2 (GREEN) | GREEN — implement gate, wire 14 branches | 32a9b48 | graphify/__main__.py |

## Dispatch Branches Modified (14 call sites)

| Command | Branch Type | Line (post-edit) | Insertion Point |
|---------|-------------|------------------|-----------------|
| `--obsidian` | `if cmd ==` | 1787 | After `_strip_vault_flags_from_tokens` |
| `--diagram-seeds` | `if cmd ==` | 1926 | Top of branch (no strip helper) |
| `--init-diagram-templates` | `if cmd ==` | 1984 | Top of branch (no strip helper) |
| `--dedup` | `if cmd ==` | 2037 | Top of branch (no strip helper) |
| `snapshot` | `if cmd ==` | 2175 | Top of branch |
| `approve` | `if cmd ==` | 2302 | Top of branch |
| `save-result` | `elif cmd ==` | 2584 | Before `import argparse` |
| `elicit` | `elif cmd ==` | 2627 | Before `import argparse` |
| `harness` | `elif cmd ==` | 2722 | Before usage-check / argparse |
| `import-harness` | `elif cmd ==` | 2791 | Before `import argparse` |
| `run` | `elif cmd ==` | 2890 | After `_strip_vault_flags_from_tokens` (captures lv_vault/lv_vlist) |
| `enrich` | `elif cmd ==` | 2992 | Before `import argparse` |
| `update-vault` | `elif cmd ==` | 3221 | Before `import argparse` |
| `vault-promote` | `elif cmd ==` | 3275 | Before `import argparse` |

## Helper Signature

```python
def _check_vault_cwd_gate(
    cmd: str,
    *,
    has_explicit_route: bool,
    write_into_vault: bool,
) -> str:
    """Returns 'n/a', 'auto-adopt', or raises SystemExit(2)."""
```

Located at: `graphify/__main__.py:1490`

## Test Count Delta

- Baseline: 2123 passed
- After Plan 01: 2125 passed (+2)
- New tests: `test_gate_runs_for_each_gated_cmd`, `test_gate_skipped_for_readonly_cmds`

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 9ae740d (chore — Wave 0 combined) | Tests exist and fail on unmodified code — RED state confirmed |
| GREEN (feat commit) | 32a9b48 | Both Plan-01 tests pass; full suite 2125/0 |
| REFACTOR | Not needed | Implementation is clean single-helper pattern |

Note: RED was committed as part of the Wave 0 `chore(59-01)` commit (Task 0) since the test file creation and RED confirmation are the same artifact. The tests are demonstrably failing against the unmodified baseline (confirmed by RED verification run).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Observations (not deviations)

**1. `run` branch pre-existing vault detection in `output.py`**

The `run` branch calls `_resolve_cli_paths()` which internally calls `resolve_output()` in `output.py`. That function already contained CWD vault detection using `_refuse()` (single-line, exit code 1). The new `_check_vault_cwd_gate` is inserted BEFORE `_resolve_cli_paths()` in the `run` branch, so the gate fires first (exit 2, two-line format). The old detection in `output.py` is now unreachable for profile-less vault CWD when coming through `run` — it only fires if somehow the CWD is not a vault but the resolved path is. No code was removed; precedence is achieved by gate placement.

**2. `import-harness` pre-existing `is_obsidian_vault` check at line 2849**

This check examines `artifacts` (the resolved output directory), not `Path.cwd()`. It is orthogonal to the VCWD gate and was left untouched. It guards against writing harness output INTO a vault directory (output path check), while VCWD-01 guards against running from a vault CWD without explicit routing.

## Known Stubs

**Auto-adopt routing (Plan 02):** The gate returns `"auto-adopt"` and emits the notice but does NOT yet wire the routing side (i.e., does not set `explicit_vault = Path.cwd()`). Plan 02 wires that. This is intentional per the plan structure — Plan 01 stubs the auto-adopt routing.

**`write_into_vault=False` (Plan 04):** All 14 call sites pass `write_into_vault=False` as a placeholder. Plan 04 threads the `--write-into-vault` flag.

## Threat Flags

None beyond those in the plan's threat model (T-59-01 through T-59-03). The gate emits `cwd` in the auto-adopt notice line — this is benign (user trusts their own CWD). The refusal message also interpolates `cwd`; Plan 03 sanitizes it via `security.py`.

## Follow-up Work for Downstream Plans

- **Plan 02 (auto-adopt):** Wire `gate == "auto-adopt"` to set `lv_vault = Path.cwd()` in each of the 14 branches. Replace `write_into_vault=False` placeholder with branch-local logic.
- **Plan 03 (refusal):** Sanitize `<cwd>` in the refusal message via `security.py` before interpolation.
- **Plan 04 (write-into-vault):** Thread `--write-into-vault` global + per-command flag; replace `write_into_vault=False` with the resolved flag value.
- **Plan 05 (doctor):** Add `[vault-cwd]` section to `graphify/doctor.py` using `_classify_vault_cwd()` classifier.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| tests/test_vault_cwd.py exists | FOUND |
| graphify/__main__.py exists | FOUND |
| _check_vault_cwd_gate in __main__.py | FOUND |
| _make_partial_vault in test_vault_cwd.py | FOUND |
| Wave 0 commit 9ae740d | FOUND |
| GREEN commit 32a9b48 | FOUND |
| Full suite: 2125 passed, 0 failed | PASSED |
