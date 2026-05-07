---
phase: 68
slug: audit-b-nyquist-gap-fill-seed-sha-traceability
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-06
---

# Phase 68 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pyproject.toml` (Plan 01 adds `[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest -m audit_v112 -v` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~12s quick / ~50s full |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -m audit_v112 -v` (≤ 12s feedback)
- **After every plan wave:** Run `pytest tests/ -q` (≤ 50s full suite)
- **Before `/gsd-verify-work`:** `python scripts/audit_b_closure.py` exits 0 + full suite green
- **Max feedback latency:** 50 seconds (well under 68s budget)

---

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement | Threat Ref         | Secure Behavior                                                              | Test Type   | Automated Command                                                                                              | File Exists                  | Status     |
|----------|------|------|-------------|--------------------|------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------|------------------------------|------------|
| 68-01-01 | 01   | 1    | AUDIT-01    | T-68-02            | Marker registered; 5 v1.12 tests carry `@pytest.mark.audit_v112`; no warnings | unit        | `python -m pytest --collect-only -m audit_v112 -q` (expect 5)                                                  | ✅ (5 tests + pyproject)     | ⬜ pending |
| 68-01-02 | 01   | 1    | AUDIT-01    | T-68-01, T-68-03   | Closure script enforces drift detection (exit 2), test pass (0), failure (1) | unit + smoke| `python -m pytest tests/test_audit_b_closure.py -v && python scripts/audit_b_closure.py`                       | ❌ W0 (Plan 01 creates)      | ⬜ pending |
| 68-02-01 | 02   | 1    | AUDIT-01    | T-68-05, T-68-06   | All 5 SHAs + test paths cited verbatim from RESEARCH.md; D-02 schema followed | doc-grep    | `grep -c "^## Phase " .planning/milestones/v1.12-VALIDATION.md` (expect 5) + per-SHA grep                      | ❌ W0 (Plan 02 creates)      | ⬜ pending |
| 68-03-01 | 03   | 2    | AUDIT-03    | T-68-08            | SEED bullets v1.13-closure form; AUDIT checkboxes flipped                    | doc-grep    | `grep -q "v1.13.*Phase 63" .planning/PROJECT.md && grep -q "^- \[x\] \*\*AUDIT-01\*\*" .planning/REQUIREMENTS.md` | ✅ (PROJECT/REQUIREMENTS exist) | ⬜ pending |
| 68-03-02 | 03   | 2    | AUDIT-01    | T-68-07            | v1.12 section prepended; closure script exit 0                               | doc + smoke | `grep -q "^## v1.12 Vault Awareness" .planning/MILESTONES.md && python scripts/audit_b_closure.py`             | ✅ (MILESTONES exists)       | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_audit_b_closure.py` — Plan 01 / Task 2 creates (RED before GREEN per TDD)
- [x] `scripts/audit_b_closure.py` — Plan 01 / Task 2 creates
- [x] `pyproject.toml [tool.pytest.ini_options]` — Plan 01 / Task 1 adds; section currently absent

*Existing pytest infrastructure covers all 5 cited v1.12 tests; Wave 0 gaps are limited to the closure-script ecosystem.*

---

## Manual-Only Verifications

| Behavior                                              | Requirement | Why Manual                                       | Test Instructions                                                                  |
|-------------------------------------------------------|-------------|--------------------------------------------------|------------------------------------------------------------------------------------|
| MILESTONES.md voice / narrative quality of v1.12 entry | AUDIT-01    | Style judgment (matches v1.11 voice; not gradeable by automation) | Read `.planning/MILESTONES.md` v1.12 section; confirm tone matches v1.11 entry. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 68s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-06
