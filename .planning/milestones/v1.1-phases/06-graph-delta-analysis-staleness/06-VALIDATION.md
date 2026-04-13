---
phase: 6
slug: graph-delta-analysis-staleness
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
updated: 2026-04-12
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
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_snapshot.py tests/test_delta.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Coverage | Automated Command | Status |
|---------|------|------|-------------|---------------|-------------------|--------|
| 06-01-01 | 01 | 1 | DELTA-03 | `test_extract_python_provenance_fields`, `test_provenance_source_hash_matches_file_hash`, `test_provenance_extracted_at_is_iso8601` | `pytest tests/test_snapshot.py -q` | ✅ green |
| 06-01-02 | 01 | 1 | DELTA-02 | `test_save_snapshot_creates_json_file`, `test_fifo_prune_removes_oldest`, `test_auto_snapshot_and_delta_*` | `pytest tests/test_snapshot.py -q` | ✅ green |
| 06-02-01 | 02 | 1 | DELTA-01 | `test_identical_graphs_empty_delta`, `test_added_node`, `test_removed_node`, `test_added_edge`, `test_removed_edge` | `pytest tests/test_delta.py -q` | ✅ green |
| 06-02-02 | 02 | 1 | DELTA-05 | `test_render_delta_md_with_changes`, `test_render_delta_md_empty`, `test_render_delta_md_first_run` | `pytest tests/test_delta.py -q` | ✅ green |
| 06-02-03 | 02 | 1 | DELTA-06 | `test_community_migration`, `test_render_delta_md_with_changes` | `pytest tests/test_delta.py -q` | ✅ green |
| 06-02-04 | 02 | 1 | DELTA-08 | `test_connectivity_change`, `test_render_delta_md_connectivity` | `pytest tests/test_delta.py -q` | ✅ green |
| 06-03-01 | 03 | 2 | DELTA-04 | `test_classify_staleness_fresh`, `test_classify_staleness_stale`, `test_classify_staleness_ghost`, `test_classify_staleness_no_provenance` | `pytest tests/test_delta.py -q` | ✅ green |
| 06-03-02 | 03 | 2 | DELTA-07 | `test_cli_snapshot_help`, `test_cli_snapshot_saves_file`, `test_cli_snapshot_with_name`, `test_cli_snapshot_from_to` | `pytest tests/test_delta.py -q` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test File Summary

| Test File | Test Count | Requirements Covered |
|-----------|-----------|---------------------|
| `tests/test_snapshot.py` | 19 | DELTA-02, DELTA-03, DELTA-07 |
| `tests/test_delta.py` | 21 | DELTA-01, DELTA-04, DELTA-05, DELTA-06, DELTA-07, DELTA-08 |
| **Total** | **40** | **All 8 DELTA requirements** |

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Requirements audited | 8 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Tests total | 40 |
| Tests passing | 40 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-04-12
