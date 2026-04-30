# Phase 42 — Technical research

**Phase:** 42 doctor-preflight-pinned-vault-parity  
**Question:** What must change so doctor profile preflight matches the pinned vault when CWD ≠ vault?

## Findings

### Current behavior (`graphify/doctor.py`)

- `run_doctor()` computes `profile_home` from `resolved_output.vault_path` when Phase 41 pins apply (`resolved_output` set); otherwise `profile_home = cwd_resolved`.
- Profile artifacts are located at `profile_home / ".graphify" / "profile.yaml"` and `.../templates`.
- When either exists, the code calls **`validate_profile_preflight(cwd_resolved)`** — wrong tree when `profile_home != cwd_resolved`.
- `validate_profile_preflight(vault_dir)` (`graphify/profile.py`) expects the **vault root** whose `.graphify/` directory should be validated.

### Root cause

Mismatch between the directory used to **decide** whether to run preflight (`profile_home`) and the directory passed into **`validate_profile_preflight`** (`cwd_resolved`).

### Recommended fix

- Replace **`validate_profile_preflight(cwd_resolved)`** with **`validate_profile_preflight(profile_home)`** inside the same guard (`profile_yaml.exists()` or `templates_dir.exists()`).
- No API change to `validate_profile_preflight` (D-36 remains satisfied — signature unchanged).
- When no pin, `profile_home == cwd_resolved` → behavior identical to today.

### Verification approach

- Unit test: **`cwd`** is a plain directory **without** `.graphify/`; **`resolved_output.vault_path`** points at a vault whose `profile.yaml` is invalid. Before fix, preflight targets CWD and returns empty validation errors for missing `.graphify/`; after fix, errors must reflect the pinned vault’s profile.
- Regression: `pytest tests/test_doctor.py -q` plus targeted new test.

## Validation Architecture

Nyquist dimension mapping for this phase:

| Dimension | Approach |
|-----------|----------|
| Functional correctness | Unit test pinned-vault vs CWD divergence |
| Regression | Full `tests/test_doctor.py` + full suite |
| Security / paths | No new paths opened — still validates existing vault roots only |

---

## RESEARCH COMPLETE
