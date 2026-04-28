---
phase: 23
slug: dedup-source-file-list-handling-fix
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
last_audited: 2026-04-27
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (per pyproject.toml; CI runs Python 3.10 + 3.12) |
| **Config file** | `pyproject.toml` (existing pytest config — no new config needed) |
| **Quick run command** | `pytest tests/test_dedup.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3s for `test_dedup.py`, ~30s for full suite |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dedup.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | DEDUP-01, DEDUP-02 | T-23-01 | edges-merge accepts list-shaped `source_file` without `TypeError`; preserves scalar-when-1, sorted-list-when-≥2 contract | unit | `pytest tests/test_dedup.py -q` | ✅ existing | ✅ green |
| 23-01-02 | 01 | 2 | DEDUP-03 | T-23-01 | regression test asserts no `TypeError` + correct merge shape on pre-merged `list[str]` `source_file` fixture | unit | `pytest tests/test_dedup.py::test_cross_type_merges_list_shaped_source_file -q` | ✅ tests/test_dedup.py:411 | ✅ green |
| 23-01-03 | 01 | 2 | DEDUP-03 | T-23-01 | idempotency: running dedup twice on same extraction is a no-op on shape and raises no exception | unit | `pytest tests/test_dedup.py::test_dedup_is_idempotent_on_source_file_shape -q` | ✅ tests/test_dedup.py:441 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_dedup.py` — two new test functions added (commit `8b7f4dc`, RED step) prior to the dedup.py patch (commit `8c67e1f`, GREEN step). RED→GREEN sequencing observed.

*Existing infrastructure (pytest, test_dedup.py with 408 lines of fixtures and helpers) covers everything else — no new conftest, no new fixtures module needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reproduce GitHub Issue #4 reporter scenario end-to-end via CLI on a real extraction | DEDUP-01 (success criterion 1 in ROADMAP — "completes on a fixture extraction") | Manual sanity check that the unit fixture matches the real CLI invocation surface; pytest case is the formal evidence | `graphify --dedup --dedup-cross-type` against a fixture extraction whose edges already carry `list[str]` `source_file`; assert exit 0 and inspect output graph for shape correctness |

*All formal phase requirements (DEDUP-01, 02, 03) have automated verification via the two new pytest cases.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (≈4s for `test_dedup.py`)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-27 by `/gsd-validate-phase 23`

---

## Validation Audit 2026-04-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Bookkeeping fixes | 3 statuses ⬜→✅, frontmatter draft→validated, sign-off ticked |

All three Per-Task Map entries (23-01-01..03) classify as **COVERED**. The two regression tests (`test_cross_type_merges_list_shaped_source_file`, `test_dedup_is_idempotent_on_source_file_shape`) re-confirmed green at audit time (`pytest ... -q` → `2 passed in 4.09s`). No auditor agent was spawned — the gap was bookkeeping-only (statuses left ⬜ pending after the phase completed).
