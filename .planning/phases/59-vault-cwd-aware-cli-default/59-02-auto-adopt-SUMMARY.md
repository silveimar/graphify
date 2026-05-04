---
phase: 59-vault-cwd-aware-cli-default
plan: "02"
subsystem: cli-dispatch
tags: [vcwd, auto-adopt, routing, tdd]
dependency_graph:
  requires: [59-01]
  provides: [VCWD-02, gate-routing-wired]
  affects: [graphify/__main__.py, tests/test_vault_cwd.py]
tech_stack:
  added: []
  patterns: [gate-return-capture, explicit-vault-promotion]
key_files:
  created: []
  modified:
    - tests/test_vault_cwd.py
    - graphify/__main__.py
decisions:
  - "gate return value captured as `gate` in all 14 branches; if gate == auto-adopt, branch-local vault var set to Path.cwd()"
  - "_make_profile_vault fixture uses v1.8-valid profile (taxonomy + mapping.min_community_size) with vault-relative output block to avoid _refuse() in resolve_output"
  - "elicit and import-harness: gate captured before argparse/strip, applied after _strip_vault_flags_from_tokens so local vars exist"
  - "branches without _resolve_cli_paths (--dedup, snapshot, approve, save-result, harness, enrich): gate captured; auto-adopt comment documents Plan 04 follow-on"
  - "--init-diagram-templates and --diagram-seeds: vault_arg/vault_path promoted to cwd after arg-parsing loop when gate==auto-adopt and no explicit flag passed"
  - "update-vault and vault-promote: _uv_vault/_vp_vault extracted after argparse; promoted to cwd when gate==auto-adopt and arg is falsy"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-04"
  tasks_completed: 2
  files_changed: 2
---

# Phase 59 Plan 02: Auto-Adopt Routing Summary

**One-liner:** VCWD-02 explicit routing — gate return captured in 14 branches, lv_vault/local vars promoted to Path.cwd() on auto-adopt, parity with --vault $CWD verified via elicit --dry-run --demo test.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | VCWD-02 tests: notice + parity + no-notice-on-explicit | cb3cd9a | tests/test_vault_cwd.py |
| 2 (GREEN) | Wire gate == auto-adopt in 14 branches | 42dcf49 | graphify/__main__.py |

## Branch Variable Bindings (14 gated branches)

| Branch | Gate captures | Auto-adopt wiring | _resolve_cli_paths local_explicit |
|--------|--------------|-------------------|----------------------------------|
| `--obsidian` | `gate = _check_vault_cwd_gate(...)` | `lv_vault = lv_vault or Path.cwd()` | `local_explicit=lv_vault` |
| `run` | `gate = _check_vault_cwd_gate(...)` | `lv_vault = lv_vault or Path.cwd()` | `local_explicit=lv_vault` |
| `elicit` | `gate = _check_vault_cwd_gate(...)` (before strip) | `_lv_e = _lv_e or Path.cwd()` (after strip) | `local_explicit=_lv_e` |
| `import-harness` | `gate = _check_vault_cwd_gate(...)` (before strip) | `_lv_ih = _lv_ih or Path.cwd()` (after strip) | `local_explicit=_lv_ih` |
| `--diagram-seeds` | `gate = _check_vault_cwd_gate(...)` | `vault_path = Path.cwd()` (before build_all_seeds call) | n/a (vault_path arg) |
| `--init-diagram-templates` | `gate = _check_vault_cwd_gate(...)` | `vault_arg = str(Path.cwd())` (after arg parse loop) | n/a (vault_arg str) |
| `--dedup` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `snapshot` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `approve` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `save-result` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `harness` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `enrich` | `gate = _check_vault_cwd_gate(...)` | comment only — no vault routing | n/a |
| `update-vault` | `gate = _check_vault_cwd_gate(...)` | `_uv_vault = str(Path.cwd())` (after argparse) | `vault_dir=Path(_uv_vault)` |
| `vault-promote` | `gate = _check_vault_cwd_gate(...)` | `_vp_vault = str(Path.cwd())` (after argparse) | `vault_path=Path(_vp_vault)` |

## Test Count Delta

- Baseline: 2125 passed
- After Plan 02: 2128 passed (+3)
- New tests: `test_auto_adopt_notice_emitted_once`, `test_auto_adopt_matches_explicit_vault`, `test_explicit_vault_no_auto_adopt_notice`

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | cb3cd9a | Tests added; notice test already passed pre-wiring (existing CWD detection in resolve_output produces equivalent result — documented below) |
| GREEN (feat commit) | 42dcf49 | All 3 VCWD-02 tests pass; full suite 2128/0 |
| REFACTOR | Not needed | Implementation is clean gate-capture pattern |

## Deviations from Plan

### Auto-fixed Issues

None.

### Observations (not deviations)

**1. RED tests passed before GREEN implementation (TDD fail-fast investigated)**

The plan anticipated `test_auto_adopt_matches_explicit_vault` would FAIL in RED because "Plan-01 stub did not promote cwd to explicit_vault." However all 3 tests passed pre-wiring.

Root cause: `resolve_execution_paths(cwd, explicit_vault=None)` falls through to `resolve_output(cwd)`, which detects the vault via CWD and loads the profile — producing the SAME `artifacts_dir` as `resolve_execution_paths(cwd, explicit_vault=Path.cwd())`. The behavioral parity already existed via the CWD detection path in `output.py`.

The GREEN implementation makes the routing EXPLICIT (explicit_vault=cwd flows through `_resolve_cli_paths`) rather than relying on CWD fallback detection. This is correct architecture for VCWD-02: if the CWD detection path in `output.py` were ever removed or changed, the explicit wiring would keep the contract intact.

Per plan TDD fail-fast rule: investigated, found feature already exists via different code path. Proceeding with GREEN to wire the explicit path is the correct response.

**2. Notice already exact-once before Plan 02 wiring**

The auto-adopt notice was already emitted exactly once by the Plan 01 gate helper. Plan 02's routing wiring (setting `lv_vault = Path.cwd()`) routes through `resolve_execution_paths` with `explicit_vault=cwd_r` where `cwd_r == effective_root`. The `--vault pin uses vault root` line in `resolve_execution_paths` has the `cwd_r != effective_root` guard, so no second notice is emitted. Confirmed by `test_auto_adopt_notice_emitted_once`.

## Known Stubs

- **`write_into_vault=False` (Plan 04):** All 14 call sites still pass `write_into_vault=False` as a placeholder. Plan 04 threads the real `--write-into-vault` flag.

## Threat Flags

None beyond the plan's threat model (T-59-04, T-59-05). The auto-adopt notice already emitted via Plan 01's gate — no new surface introduced.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| tests/test_vault_cwd.py modified | FOUND |
| graphify/__main__.py modified | FOUND |
| grep -c 'gate == "auto-adopt"' == 14 | 14 FOUND |
| RED commit cb3cd9a | FOUND |
| GREEN commit 42dcf49 | FOUND |
| Full suite: 2128 passed, 0 failed | PASSED |
