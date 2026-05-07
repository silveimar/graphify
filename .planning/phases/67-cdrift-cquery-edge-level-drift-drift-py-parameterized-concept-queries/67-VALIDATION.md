---
phase: 67
slug: cdrift-cquery-edge-level-drift-drift-py-parameterized-concept-queries
status: draft
nyquist_compliant: false
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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
