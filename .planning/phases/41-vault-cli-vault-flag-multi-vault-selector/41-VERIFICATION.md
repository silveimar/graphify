# Phase 41 — Verification

**Phase:** 41-vault-cli-vault-flag-multi-vault-selector  
**Requirements:** VCLI-01 — VCLI-06 (`.planning/REQUIREMENTS.md`)

## Goal

Explicit vault selection (`--vault`, env, list file), doctor/dry-run alignment with resolved output, scripting docs, and **`tmp_path`** tests — per plans **`41-01` … `41-04`** and **`41-PATTERNS.md`**.

## Requirement coverage

| REQ-ID | Summary | Evidence |
|--------|---------|----------|
| **VCLI-01** | `--vault <path>` precedence | `graphify/output.py` resolution; **`tests/test_vault_cli.py`**; **`41-01-SUMMARY.md`**, **`41-02-SUMMARY.md`** |
| **VCLI-02** | Multi-vault selector (env / list / TTY) | Same test module + **`graphify/__main__.py`** flag stripping; **`41-02-SUMMARY.md`** |
| **VCLI-03** | Doctor reflects pinned vault consistently | **Phase 42** closure: **`graphify/doctor.py`** preflight uses profile root when vault pinned — see **`.planning/phases/42-doctor-preflight-pinned-vault-parity/42-VERIFICATION.md`** and **`42-03-SUMMARY.md`** (not Phase 41 code alone). |
| **VCLI-04** | Dry-run / preview aligned with v1.7–v1.8 | Doctor + dry-run tests in **`tests/test_vault_cli.py`** / doctor tests; **`41-03-SUMMARY.md`** |
| **VCLI-05** | Unit tests for precedence edge cases | **`tests/test_vault_cli.py`** (`tmp_path` only) |
| **VCLI-06** | README / `--help` for scripters | **`README.md`** vault subsection; **`41-04-SUMMARY.md`**; top-level **`graphify --help`** vault lines |

## Nyquist / VALIDATION

- **`41-VALIDATION.md`** holds extended validation notes — referenced here as primary Nyquist artifact for this phase.

## Automated verification

```bash
pytest tests/test_vault_cli.py -q
pytest tests/test_doctor.py -q
pytest tests/ -q
```

(Adjust `test_doctor.py` name if the repo uses a different module — grep `doctor` under `tests/` if imports fail.)

## Status

**passed** for Phase **41**-scoped delivery; **VCLI-03** end-to-end satisfaction is **jointly** evidenced by **Phase 41** + **Phase 42** verification artifacts.
