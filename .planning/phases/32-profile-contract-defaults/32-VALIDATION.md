---
phase: 32
slug: profile-contract-defaults
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
completed: 2026-04-29
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 available locally |
| **Config file** | none — tests run directly via pytest |
| **Quick run command** | Task-specific focused pytest command from the active plan, usually one test file such as `pytest tests/test_profile.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | <30 seconds for task-specific focused tests, full suite varies |

---

## Sampling Rate

- **After every task commit:** Run the task-specific focused pytest command from the plan, usually one file such as `pytest tests/test_profile.py -q`, `pytest tests/test_mapping.py -q`, or `pytest tests/test_doctor.py -q`
- **After every plan wave:** Run `pytest tests/test_profile.py tests/test_mapping.py tests/test_doctor.py tests/test_export.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green, accounting for the two historical baseline failures already deferred in `.planning/PROJECT.md`
- **Max feedback latency:** 30 seconds for focused feedback

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | TAX-01/TAX-02 | T-32-01 | Default note paths stay inside `Atlas/Sources/Graphify/` | unit | `pytest tests/test_profile.py tests/test_export.py -q` | yes | green |
| 32-01-02 | 01 | 1 | TAX-04 | T-32-02 | Unsupported taxonomy keys and unsafe folders fail validation | unit/CLI | `pytest tests/test_profile.py -q` | yes | green |
| 32-02-01 | 02 | 1 | CLUST-01/CLUST-04 | T-32-03 | `mapping.min_community_size` controls threshold; `mapping.moc_threshold` is invalid | unit | `pytest tests/test_profile.py tests/test_mapping.py -q` | yes | green |
| 32-03-01 | 03 | 2 | COMM-03 | T-32-04 | Deprecated community overview usage emits actionable migration guidance | unit/CLI | `pytest tests/test_profile.py tests/test_doctor.py -q` | yes | green |
| 32-04-01 | 04 | 2 | TAX-03 | T-32-05 | Valid `taxonomy:` overrides defaults and wins over `folder_mapping` | unit | `pytest tests/test_profile.py tests/test_mapping.py -q` | yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `tests/test_profile.py` — update defaults assertions; add taxonomy schema errors, `mapping.min_community_size`, `mapping.moc_threshold` invalidation, and community overview warnings.
- [x] `tests/test_mapping.py` — update helper profiles and MOC threshold tests to `mapping.min_community_size`; add `_Unclassified` naming/path tests.
- [x] `tests/test_doctor.py` — add shared preflight warning/error surfacing and `_FIX_HINTS` coverage for taxonomy/legacy-key issues.
- [x] `tests/test_export.py` — add no-profile `to_obsidian(..., dry_run=True)` target-path assertions for `Atlas/Sources/Graphify/...`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | N/A | All phase behaviors have automated verification paths | N/A |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing test references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Nyquist-compliant after 12/12 verification truths passed.
