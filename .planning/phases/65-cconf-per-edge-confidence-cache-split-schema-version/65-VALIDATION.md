---
phase: 65
slug: cconf-per-edge-confidence-cache-split-schema-version
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-06
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (project: graphify, see `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `pytest tests/test_validate.py tests/test_export.py tests/test_confidence_cache.py tests/test_extract_confidence.py tests/test_skill_prompt_drift.py tests/test_report_calibration.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30s quick, ~120s full |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (quick), 120s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 65-01-T1 | 01 | 1 | CCONF-05 | — | RED — failing tests assert split + schema_version round-trip + legacy fixture read | unit (RED) | `! pytest tests/test_validate.py::test_legacy_v1_12_passes_read tests/test_validate.py::test_write_requires_schema_version tests/test_validate.py::test_write_accepts_with_schema_version tests/test_export.py::test_to_json_emits_schema_version tests/test_export.py::test_to_json_round_trips_g_graph_attr -x -q` | ✅ W0 | ⬜ pending |
| 65-01-T2 | 01 | 1 | CCONF-05 | — | GREEN — `validate_extraction_for_read/_for_write` split, `schema_version` emitted in `to_json`, frozen v1.12 fixture passes read | unit (GREEN) | `pytest tests/test_validate.py tests/test_export.py -x -q` | ✅ W0 | ⬜ pending |
| 65-02-T1 | 02 | 2 | CCONF-01, CCONF-02, CCONF-03 | — | RED — failing tests assert non-uniform confidence, sanitized evidence, separate cache namespace, drift gate across 7 skill files | unit (RED) | `! pytest tests/test_confidence_cache.py tests/test_extract_confidence.py tests/test_skill_prompt_drift.py -x -q` | ✅ W0 | ⬜ pending |
| 65-02-T2 | 02 | 2 | CCONF-01, CCONF-02, CCONF-03 | — | GREEN — `cache.confidence_*` helpers, scored emission at extract.py:596/1211–1231/2252, evidence ≤280 chars via `security.sanitize_label`, prompt_version `1.13.0` in all 7 skill files | unit (GREEN) | `pytest tests/test_confidence_cache.py tests/test_extract_confidence.py tests/test_skill_prompt_drift.py tests/test_extract.py tests/test_cache.py tests/test_validate.py -x -q` | ✅ W0 | ⬜ pending |
| 65-03-T1 | 03 | 3 | CCONF-04 | — | RED — failing tests assert calibration histogram + 3 flag rules + skewed-corpus detection | unit (RED) | `! pytest tests/test_report_calibration.py -x -q` | ✅ W0 | ⬜ pending |
| 65-03-T2 | 03 | 3 | CCONF-04 | — | GREEN — GRAPH_REPORT.md gains `## Confidence Calibration Self-Check` section with 10-bin histogram + mode-collapse / refusal / no-negatives flags + n<10 skip note | unit (GREEN) | `pytest tests/test_report_calibration.py tests/test_validate.py tests/test_export.py tests/test_extract.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing pytest infrastructure covers all phase requirements. Per-plan RED tasks self-create their own test files:

- Plan 01 Task 1 creates: `tests/test_validate.py` extensions (read/write split tests), `tests/test_export.py` extensions (schema_version round-trip), `tests/fixtures/legacy_v1_12_graph.json` (frozen real v1.12 capture per D-65.09)
- Plan 02 Task 1 creates: `tests/test_confidence_cache.py`, `tests/test_extract_confidence.py`, `tests/test_skill_prompt_drift.py`
- Plan 03 Task 1 creates: `tests/test_report_calibration.py`, `tests/fixtures/skewed_confidence_corpus.json` (synthetic skewed-distribution fixture per D-65.13)

No new framework install required.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (RED tasks self-bootstrap test files)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (quick) / < 120s (full)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-06
