---
phase: 6
slug: graph-delta-analysis-staleness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_snapshot.py tests/test_delta.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_snapshot.py tests/test_delta.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | DELTA-03 | — | N/A | unit | `pytest tests/test_snapshot.py -q` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | DELTA-02 | — | N/A | unit | `pytest tests/test_snapshot.py -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | DELTA-01 | — | N/A | unit | `pytest tests/test_delta.py -q` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | DELTA-05 | — | N/A | unit | `pytest tests/test_delta.py -q` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | DELTA-06 | — | N/A | unit | `pytest tests/test_delta.py -q` | ❌ W0 | ⬜ pending |
| 06-02-04 | 02 | 1 | DELTA-08 | — | N/A | unit | `pytest tests/test_delta.py -q` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | DELTA-04 | — | N/A | unit | `pytest tests/test_delta.py -q` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | DELTA-07 | — | N/A | unit | `pytest tests/test_snapshot.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_snapshot.py` — stubs for DELTA-02, DELTA-03, DELTA-07
- [ ] `tests/test_delta.py` — stubs for DELTA-01, DELTA-04, DELTA-05, DELTA-06, DELTA-08

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
