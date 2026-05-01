---
phase: 50
slug: v1-10-gap-baselines-verification
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (stdlib assertions) |
| **Config file** | none dedicated |
| **Quick run command** | `pytest tests/test_detect.py tests/test_extract.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~CI-dependent (full suite per CLAUDE.md on Python 3.10 / 3.12) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_detect.py tests/test_extract.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Before ticking HYG-01..03 in REQUIREMENTS.md:** Full `pytest tests/ -q` with transcript in `45-VERIFICATION.md`

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 1 | HYG-01..03 | — | N/A (docs/traceability) | unit | `pytest tests/test_detect.py::test_detect_skips_dotfiles tests/test_extract.py::test_collect_files_from_dir tests/test_extract.py::test_collect_files_skips_nested_graphify_out -q` | ✅ | ✅ green |
| 50-01-02 | 01 | 1 | HYG-01..03 | — | N/A | unit + full | `pytest tests/ -q` then grep HYG ticks in REQUIREMENTS.md | ✅ | ✅ green |
| 50-01-03 | 01 | 1 | HYG-01..03 | — | N/A | grep | ROADMAP / VALIDATION / SUMMARY file checks per plan | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing infrastructure covers all phase requirements (`tests/test_detect.py`, `tests/test_extract.py`, `tests/fixtures/phase45-mini-vault/`).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Optional CLI doctor preview | HYG-01 (dot_graphify track) | Operator discretion | `graphify doctor --dot-graphify-track` on `tests/fixtures/phase45-mini-vault/` if stakeholders require |

*If none required: state N/A in `45-VERIFICATION.md`.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Full suite green before REQUIREMENTS ticks
- [x] `nyquist_compliant: true` set in frontmatter when Phase 50 executes

**Approval:** approved 2026-05-01
