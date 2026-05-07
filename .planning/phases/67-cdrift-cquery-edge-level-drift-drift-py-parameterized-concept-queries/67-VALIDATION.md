---
phase: 67
slug: cdrift-cquery-edge-level-drift-drift-py-parameterized-concept-queries
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-06
---

# Phase 67 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sources: 67-RESEARCH.md `## Validation Architecture` section + Phase 66 test patterns.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_drift.py tests/test_concept_code_hops.py tests/test_report.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30s quick / ~60s full |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green (1 pre-existing `test_migration.py` failure unrelated to Phase 67 may remain — see STATE.md)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Filled in by `gsd-planner` once PLAN.md tasks exist. One row per task with `<automated>` verify command or Wave 0 dependency.

| Plan-Task | Requirement | Automated Verify |
|-----------|-------------|------------------|
| 67-01 Task 1 (RED Jaccard+classify) | CDRIFT-01, CDRIFT-02 | `pytest tests/test_drift.py -q` (must FAIL — RED gate) |
| 67-01 Task 2 (GREEN drift.py impl) | CDRIFT-01, CDRIFT-02, CDRIFT-04 | `pytest tests/test_drift.py -q` |
| 67-02 Task 1 (RED CQUERY validators) | CQUERY-01 | `pytest tests/test_concept_code_hops.py -q` (must FAIL) |
| 67-02 Task 2 (GREEN validators+predicate) | CQUERY-01 | `pytest tests/test_concept_code_hops.py tests/test_serve.py -q` |
| 67-03 Task 1 (frozen v1.12 fixture) | CQUERY-02 | `python -c "import json; json.load(open('tests/fixtures/cquery_v1_12/graph.json')); json.load(open('tests/fixtures/cquery_v1_12/golden_concept_code_hops.json'))"` |
| 67-04 Task 1 (BFS+MCP threading) | CQUERY-01 | `pytest tests/test_concept_code_hops.py tests/test_serve.py -q` |
| 67-04 Task 2 (byte-identity oracle) | CQUERY-02 | `pytest tests/test_concept_code_hops.py::test_v1_12_byte_identity -xvs` |
| 67-05 Task 1 (Drift renderer in report.py) | CDRIFT-03 | `pytest tests/test_report.py -q` |
| 67-05 Task 2 (CLI wire + CDRIFT-02 E2E) | CDRIFT-01..04 | `pytest tests/test_drift.py tests/test_report.py -q` |

Sampling continuity: every plan has at least one automated verify; no Wave 0 MISSING references; no 3 consecutive tasks without automated verify; feedback latency < 30s on the quick command.


| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD     | TBD  | TBD  | TBD         | TBD        | TBD             | TBD       | TBD               | TBD         | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_drift.py` — new file; stubs for CDRIFT-01..04 (Jaccard math, classify_edges, write_snapshot, evict)
- [ ] `tests/test_concept_code_hops.py` (or extension of `tests/test_serve.py`) — stubs for CQUERY-01..02 (filter combinatorics + byte-identity golden)
- [ ] `tests/fixtures/legacy_v1_12_graph.json` — already committed (researcher confirmed); verify it includes Phase 65 cache_version + schema_version fields, otherwise regenerate
- [ ] `tests/fixtures/legacy_v1_12_concept_code_hops_golden.json` — new committed golden output for the all-None CQUERY call (CQUERY-02)
- [ ] No new framework install required — pytest already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drift section visually renders sensibly in real-world `graphify run` against a deliberately-mutated repo | CDRIFT-03 | Subjective audit-friendliness check beyond table-shape assertion | (1) Run graphify on a sample repo. (2) Rename a community in source, re-run. (3) Inspect `GRAPH_REPORT.md` Drift section — confirm renamed edges appear under `community-renamed`, not `orphaned`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-06 by gsd-planner
