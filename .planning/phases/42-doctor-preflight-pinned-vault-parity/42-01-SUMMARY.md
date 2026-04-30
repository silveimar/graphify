# Phase 42 Plan 01 — Summary

## Delivered

- **`graphify/doctor.py`**: Profile validation block calls **`validate_profile_preflight(profile_home)`** instead of **`cwd_resolved`**, so when Phase 41 pins supply **`resolved_output`**, preflight inspects the same vault tree as **`profile_home / ".graphify/profile.yaml"`** (**VCLI-03**).
- **`tests/test_doctor.py`**: **`test_run_doctor_preflight_uses_pinned_vault_not_cwd`** — invalid profile under pinned vault + bare **`cwd_elsewhere`** without `.graphify/` must surface **`profile_validation_errors`** (regression for masked-CWD bug).

## Verification

```bash
rg -n 'validate_profile_preflight\(profile_home\)' graphify/doctor.py
pytest tests/test_doctor.py::test_run_doctor_preflight_uses_pinned_vault_not_cwd -q
pytest tests/test_doctor.py -q
```

## Notes

When **`resolved_output`** is unset, **`profile_home == cwd_resolved`** — behavior unchanged from pre-fix runs.
