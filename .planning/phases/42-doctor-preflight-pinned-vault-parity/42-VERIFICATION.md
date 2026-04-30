---
phase: 42-doctor-preflight-pinned-vault-parity
status: passed
verified_at: "2026-04-30"
requirements_checked:
  - VCLI-03
---

# Phase 42 — Verification

## Goal (from ROADMAP)

When **`run_doctor(..., resolved_output=…)`** supplies a pinned vault, **`validate_profile_preflight`** runs against **that** vault root (not shell CWD). **VCLI-03** parity.

## Automated checks

| Check | Command | Result |
|-------|---------|--------|
| Preflight uses `profile_home` | `rg -n 'validate_profile_preflight\(profile_home\)' graphify/doctor.py` | Single match at profile validation block |
| No stray CWD preflight in block | `rg 'validate_profile_preflight\(cwd_resolved\)' graphify/doctor.py` | No matches |
| Regression test | `pytest tests/test_doctor.py::test_run_doctor_preflight_uses_pinned_vault_not_cwd -q` | Pass |
| Doctor module suite | `pytest tests/test_doctor.py -q` | 19 passed |

## Must-haves (from plan frontmatter)

| Truth | Evidence |
|-------|----------|
| `validate_profile_preflight` receives same vault root as `profile_home` when pins apply | `doctor.py` passes **`profile_home`** into **`validate_profile_preflight`** |
| Unit test: CWD without `.graphify` cannot mask invalid pinned vault profile | **`test_run_doctor_preflight_uses_pinned_vault_not_cwd`** asserts non-empty errors |

## Requirement traceability

- **VCLI-03** (`REQUIREMENTS.md`): Doctor reflects resolved vault pin consistently — satisfied by validating **pinned vault’s** `.graphify/` via **`profile_home`**.

## Human verification

None required (read-only preflight path change + unit tests).
