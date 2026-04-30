---
phase: 42
slug: doctor-preflight-pinned-vault-parity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 42 — Validation Strategy

> Preflight path parity (VCLI-03) — doctor validates the same vault tree used for profile discovery.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — repo standard |
| **Quick run command** | `pytest tests/test_doctor.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~2 minutes full suite |

---

## Sampling Rate

- **After task commit:** `pytest tests/test_doctor.py -q`
- **Before phase close:** `pytest tests/ -q`

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command |
|---------|------|------|-------------|-----------|-------------------|
| 42-01-01 | 01 | 1 | VCLI-03 | unit | `pytest tests/test_doctor.py::test_run_doctor_preflight_uses_pinned_vault_not_cwd -q` |

---

## Wave 0 Requirements

- Existing `tests/test_doctor.py` patterns and `_make_vault` helper cover fixtures.

---

## Manual-Only Verifications

| Behavior | Why Manual | Instructions |
|----------|------------|----------------|
| — | — | None required for this phase |
