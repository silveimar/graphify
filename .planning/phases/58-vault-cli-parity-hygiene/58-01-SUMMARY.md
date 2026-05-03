---
phase: 58-vault-cli-parity-hygiene
plan: "01"
subsystem: output-resolution
tags: [tdd, vaux-01, parity-helper, vault-cli]
dependency_graph:
  requires: []
  provides: [resolve_vault_for_parity]
  affects: [graphify/output.py, tests/test_vault_parity.py]
tech_stack:
  added: []
  patterns: [stderr-capture-via-redirect_stderr, delegate-never-duplicate]
key_files:
  created:
    - tests/test_vault_parity.py
  modified:
    - graphify/output.py
decisions:
  - "resolve_vault_for_parity delegates to resolve_execution_paths exclusively — no duplicated resolution logic (anti-pattern #2)"
  - "warnings dimension captures only resolve_execution_paths stderr, not _merge_vault_pins (Q1 split — circular import prevention)"
  - "profile load wrapped in try/except per T-58-01 — helper never crashes on malformed YAML"
metrics:
  duration: "329s"
  completed: "2026-05-03T23:26:11Z"
  tasks_completed: 2
  files_modified: 2
requirements: [VAUX-01]
---

# Phase 58 Plan 01: VAUX-01 Structured Parity Helper Summary

**One-liner:** TDD-implemented `resolve_vault_for_parity()` in `graphify/output.py` returns a structured dict (vault_path, source, profile_path, profile_mode, warnings) by delegating to `resolve_execution_paths()` and capturing stderr, locked by 5 field-level parity tests against `run_doctor()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED — failing parity tests | 67fe947 | tests/test_vault_parity.py (created) |
| 2 | GREEN — implement resolve_vault_for_parity | 45ce2de | graphify/output.py (modified) |

## What Was Built

`resolve_vault_for_parity(cwd, *, explicit_vault, env_vault, vault_list_file) -> dict`

- Captures stderr from `resolve_execution_paths()` via `contextlib.redirect_stderr(io.StringIO())`.
- Returns `{"vault_path", "source", "profile_path", "profile_mode", "warnings"}`.
- Attempts `load_profile()` to extract `output.mode` when a profile.yaml exists; wrapped in `try/except` so YAML import failure or malformed profile returns `profile_mode=None` (T-58-01 mitigation).
- Re-raises `SystemExit` from inner resolution (non-swallowing).
- `warnings` list contains only lines from `resolve_execution_paths()` stderr — NOT `_merge_vault_pins` overrides (Q1 split per circular-import constraint).

`tests/test_vault_parity.py` covers:
1. `test_parity_helper_returns_dict_with_four_dimensions` — dict shape and field values for explicit-vault scenario.
2. `test_parity_vault_cli_matches_doctor` — parity dict vault_path/source matches `run_doctor()` resolution.
3. `test_parity_env_var_resolution` — env_vault argument yields vault-env source label.
4. `test_parity_no_vault_returns_none` — no vault yields vault_path=None, source=default.
5. `test_parity_helper_does_not_duplicate_resolution` — parity dict equals direct `resolve_execution_paths()` call.

## TDD Gate Compliance

- RED gate: `test(58-01)` commit 67fe947 — all 5 tests fail with `ImportError` on `resolve_vault_for_parity`.
- GREEN gate: `feat(58-01)` commit 45ce2de — all 5 tests pass; full suite 2099 passed + 1 xfailed.
- REFACTOR: not needed — implementation is minimal and non-duplicating.

## Deviations from Plan

None — plan executed exactly as written.

The comment line `# Test helpers (replicated from tests/test_doctor.py — D-08 forbids cross-import)` in `test_vault_parity.py` contains "test_doctor.py" as documentation text. The acceptance criterion `grep -c "from tests.test_doctor"` checks for import statements; no actual `from tests.test_doctor` import exists.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary surfaces beyond what was in the plan's threat model.

## Self-Check: PASSED

- `tests/test_vault_parity.py` exists and contains 5 test functions.
- `graphify/output.py` contains `def resolve_vault_for_parity`.
- Commits 67fe947 and 45ce2de verified in git log.
- Full test suite: 2099 passed, 1 xfailed, 0 failures.
