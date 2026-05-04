---
phase: 60
slug: milestone-level-e2e-integration-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 60 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` (existing pytest config) |
| **Quick run command** | `pytest tests/test_e2e_integration.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds for the new file; ~3 min full suite |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_e2e_integration.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds (E2E file alone)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 1 | E2E-01 | — | N/A (test infra; no prod path changed) | integration (subprocess) | `pytest tests/test_e2e_integration.py::test_e2e_compose_override_ladder -q` | ❌ W0 | ⬜ pending |
| 60-02-01 | 02 | 1 | E2E-02 | — | N/A (test infra; no prod path changed) | integration (subprocess) | `pytest tests/test_e2e_integration.py::test_e2e_elicit_then_update_vault -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_e2e_integration.py` — new file with locally-defined `_graphify` helper, `_write_vault` helper, and the two TDD RED-stage tests (one per requirement)

*Existing pytest framework, fixtures, and CI matrix cover everything else.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
