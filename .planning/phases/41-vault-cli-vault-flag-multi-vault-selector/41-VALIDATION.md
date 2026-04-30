---
phase: 41
slug: vault-cli-vault-flag-multi-vault-selector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (matches CI) |
| **Config file** | none — existing repo convention |
| **Quick run command** | `pytest tests/test_output.py tests/test_vault_cli.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60–120 seconds full suite |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run `pytest tests/test_output.py tests/test_vault_cli.py -q`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | VCLI-01..02 | T-41-* | Path confinement on vault args | unit | `pytest tests/test_output.py -q` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Extend `tests/test_output.py` or add `tests/test_vault_cli.py` — precedence matrix stubs for VCLI-01/05
- [ ] Existing `tests/conftest.py` — reuse `tmp_path` patterns

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive multi-vault prompt | VCLI-02 | Requires TTY | Smoke: run under script/expect locally |

*If none: "All phase behaviors have automated verification except optional TTY smoke."*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity maintained
- [ ] `nyquist_compliant: true` set when waves complete

**Approval:** pending
