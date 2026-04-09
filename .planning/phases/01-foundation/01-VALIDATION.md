---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_profile.py tests/test_export.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profile.py tests/test_export.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | PROF-01 | — | N/A | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | PROF-02 | — | N/A | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | PROF-03 | — | N/A | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | PROF-04 | — | N/A | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | PROF-06 | — | N/A | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 1 | MRG-04 | T-01-01 | Path traversal rejected | unit | `pytest tests/test_profile.py -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | FIX-01 | — | YAML injection prevented | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | FIX-02 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 2 | FIX-03 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 2 | FIX-04 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-05 | 02 | 2 | FIX-05 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-06 | 02 | 2 | OBS-01 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 01-02-07 | 02 | 2 | OBS-02 | — | N/A | unit | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profile.py` — stubs for PROF-01, PROF-02, PROF-03, PROF-04, PROF-06, MRG-04
- [ ] `tests/test_export.py` — add stubs for FIX-01 through FIX-05, OBS-01, OBS-02

*Existing test infrastructure (pytest, pyproject.toml) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
