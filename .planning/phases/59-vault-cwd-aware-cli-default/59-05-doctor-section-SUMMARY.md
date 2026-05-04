---
phase: 59-vault-cwd-aware-cli-default
plan: "05"
subsystem: doctor-diagnostics
tags: [vcwd, doctor, parity, tdd]
dependency_graph:
  requires: [59-01, 59-02, 59-03, 59-04]
  provides: [VCWD-05]
  affects: [graphify/doctor.py, graphify/__main__.py, tests/test_vault_cwd.py, tests/test_doctor.py]
tech_stack:
  added: []
  patterns: [pure-classifier, parity-contract, dataclass-threading]
key_files:
  created: []
  modified:
    - graphify/doctor.py
    - graphify/__main__.py
    - tests/test_vault_cwd.py
    - tests/test_doctor.py
decisions:
  - "_classify_vault_cwd is a pure read-only function in doctor.py importing is_obsidian_vault from output.py — same import the gate uses — structural parity not test-coincidence"
  - "has_explicit_route field added to DoctorReport and threaded from __main__.py doctor branch via _had_pin boolean"
  - "test_env_pin and test_vault_list use _make_profile_vault (full valid profile) to avoid SystemExit propagation when _had_pin=True causes doctor to raise on resolution failure"
  - "test_format_report_graphify_prefix updated to allow [vault-cwd] prefix alongside [graphify] prefix (VCWD-05 design contract)"
metrics:
  duration: 622s
  completed: "2026-05-04T18:10:57Z"
  tasks_completed: 3
  files_changed: 4
---

# Phase 59 Plan 05: Doctor [vault-cwd] Section + Parity Contract Summary

**One-liner:** Pure read-only `_classify_vault_cwd` classifier in doctor.py shares `is_obsidian_vault` + profile-exists predicates with the runtime gate, emitting `[vault-cwd] auto-adopt / refuse / n/a` unconditionally in `format_report()`.

## What Was Built

### `_classify_vault_cwd(cwd, *, has_explicit_route) -> str` (doctor.py line 517)

Pure classifier with identical predicate ordering to `_check_vault_cwd_gate`:
1. `is_obsidian_vault(cwd)` — if False → `"n/a"`
2. `has_explicit_route` — if True → `"n/a"` (explicit routing bypasses gate)
3. `.graphify/profile.yaml` exists — if True → `"auto-adopt"`
4. else → `"refuse"`

`write_into_vault` is intentionally omitted — the doctor describes the *default* outcome (what the gate does without overrides), not the overridden outcome.

### `DoctorReport.has_explicit_route: bool = False` (doctor.py line 161)

New field threaded from `__main__.py` doctor branch:
```python
report.has_explicit_route = _had_pin  # _had_pin already computed from --vault/env/--vault-list
```

### `format_report()` — new `[vault-cwd]` section (doctor.py line 609)

Appended after `[Recommended Fixes]`, before any future `[Version Sync]` section:

```
[graphify] === Vault-CWD Default ===
[vault-cwd] auto-adopt — vault at <cwd>, profile: .graphify/profile.yaml
[vault-cwd] refuse — vault at <cwd>, no .graphify/profile.yaml (override: --write-into-vault)
[vault-cwd] n/a — <cwd> is not an Obsidian vault
```

## Tests Added (5 new rows)

| Test | Outcome Covered |
|------|----------------|
| `test_doctor_vault_cwd_section_always_shown` | n/a — non-vault CWD still emits section |
| `test_doctor_three_outcomes` | all three outcomes reachable via subprocess |
| `test_doctor_runtime_parity` | parity contract: doctor refuse ↔ runtime exit 2 |
| `test_env_pin_disables_gate` | GRAPHIFY_VAULT env pin → gate n/a + doctor n/a |
| `test_vault_list_disables_gate` | --vault-list → gate n/a (runtime side) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_format_report_graphify_prefix assertion too strict**
- **Found during:** Task 2 (GREEN)
- **Issue:** Existing test asserted ALL doctor output lines start with `[graphify]`. The new `[vault-cwd]` lines use a different prefix by design (Decision 5).
- **Fix:** Updated assertion to allow `line.startswith("[graphify] ") or line.startswith("[vault-cwd]")`.
- **Files modified:** `tests/test_doctor.py`
- **Commit:** 5eb2c17

**2. [Rule 1 - Bug] test_env_pin and test_vault_list used _make_partial_vault for pin_target**
- **Found during:** Task 2 (GREEN) — 3/5 tests passed, 2 failed
- **Issue:** `_make_partial_vault(with_profile=True)` creates a minimal profile lacking `output:` block. When `_had_pin=True`, doctor propagates the SystemExit from resolution failure before `format_report()` is reached. Test produced empty stdout so `_doctor_section_lines()` found nothing.
- **Fix:** Changed `pin_target` in both cross-cutting tests to use `_make_profile_vault()` which writes a fully valid profile that resolves successfully.
- **Files modified:** `tests/test_vault_cwd.py`
- **Commit:** 5eb2c17

## TDD Gate Compliance

- RED gate: `ddd15fc` — `test(59-05): RED — ...`
- GREEN gate: `5eb2c17` — `feat(59-05): GREEN — ...`
- REFACTOR: No additional code changes required after GREEN — parity ordering and docstrings were correct in GREEN commit.

## Structural Parity Contract

The classifier and gate share `is_obsidian_vault` from `graphify/output.py` via import (not copy). Profile-exists check uses identical `(cwd / ".graphify" / "profile.yaml").is_file()`. Predicate ordering is documented in `_classify_vault_cwd` docstring with explicit mapping to VCWD-01..04 and T-59-12 threat entry.

## Test Count

- Baseline before Plan 05: 2135
- After Plan 05: 2139 passed, 1 xfailed
- Delta: +4 net new tests in collection (5 added in test_vault_cwd.py; doctor.py regression fix is in-place edit)

## Self-Check: PASSED

Files exist:
- graphify/doctor.py — `_classify_vault_cwd` at line 517, section at line 609
- tests/test_vault_cwd.py — 5 new tests at end of file
- tests/test_doctor.py — prefix assertion updated line ~321

Commits exist:
- ddd15fc — RED commit
- 5eb2c17 — GREEN commit (includes REFACTOR content)
