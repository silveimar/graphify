---
phase: 67
plan: 05
subsystem: drift-report
tags: [cdrift, report, cli, drift-section, snapshot-lifecycle]
requires:
  - graphify/drift.py (compute_edge_drift, write_drift_snapshot from Plan 01)
  - graphify/report.py (Federation section template from Phase 66)
provides:
  - graphify/report.py::generate(... drift_summary=...) — Drift section renderer
  - graphify/__main__.py::_run_drift_pipeline — CLI orchestration helper (compute-before / write-after)
  - tests/test_drift.py — CDRIFT-02 rename E2E anchor
affects:
  - graphify/watch.py::_rebuild_code (now invokes _run_drift_pipeline around report.generate)
  - GRAPH_REPORT.md (new "## Drift" section after "## Federation" when a prior snapshot exists)
tech-stack:
  added: []
  patterns:
    - kwarg-on-generate() shape mirroring federation_manifest (D-06)
    - omit-on-None section policy (D-09)
    - compute-BEFORE-report / write-AFTER-report split via _run_drift_pipeline(when=...)
key-files:
  created: []
  modified:
    - graphify/report.py
    - graphify/__main__.py
    - graphify/watch.py
    - tests/test_report.py
    - tests/test_drift.py
decisions:
  - D-06: Drift section sits AFTER Federation section
  - D-07: 4-row class table + per-class top-10 listing; _DRIFT_TOP_N = 10 hardcoded
  - D-08: empty-graph-with-snapshot still renders 0/0/0/0 table + "no drift edges to classify" note
  - D-09: drift_summary=None ⇒ section omitted entirely (no header, no table)
  - Snapshot lifecycle ordering: compute_edge_drift → report.generate(drift_summary=...) → write_drift_snapshot
metrics:
  duration: ~7 min
  tasks: 2
  files: 5
  tests_added: 6
  completed: 2026-05-06
---

# Phase 67 Plan 05: Drift Section + CLI Orchestration + CDRIFT-02 Rename E2E Summary

Wires the Drift section into `GRAPH_REPORT.md` directly after the Federation block, threads `drift.compute_edge_drift` / `drift.write_drift_snapshot` around `report.generate(...)` via a `_run_drift_pipeline(when=...)` helper, and proves CDRIFT-02 (membership-preserving community renames classify as `community-renamed`, never `orphaned`) end-to-end.

## What Shipped

### `graphify/report.py`
- `generate(...)` gains optional `drift_summary: dict | None = None` kwarg (next after `federation_manifest`).
- New section emitted right after the Federation block:
  - 4-row class table (`stable` / `community-renamed` / `community-resharded` / `orphaned`).
  - Per-non-stable-class subsections show up to `_DRIFT_TOP_N = 10` edges as `` `src` → `dst`  (relation) ``.
  - Empty `edges` list ⇒ `_No drift edges to classify._` note (D-08).
  - `drift_summary is None` ⇒ no `## Drift` heading at all (D-09).

Example 4-row table emitted by the renderer:

```markdown
## Drift
| Class | Edges |
|---|---|
| stable | 3 |
| community-renamed | 1 |
| community-resharded | 2 |
| orphaned | 1 |
```

### `graphify/__main__.py`
- New helper `_run_drift_pipeline(G, communities, *, project_root, when, cap=10)`:
  - `when="before-report"` → `drift.compute_edge_drift(...)` → returns `drift_summary` (or `None`).
  - `when="after-report"` → `drift.write_drift_snapshot(..., cap=10)` (FIFO retention per D-02).
  - Snapshots persist under `graphify-out/snapshots/` (D-01); zero references to `cache/snapshots/` in non-comment code.
- Ordering invariant: compute happens BEFORE `report.generate(...)`, write happens AFTER, so the snapshot of *this* run cannot influence the report it accompanies.

### `graphify/watch.py`
- `_rebuild_code` now calls `_run_drift_pipeline(when="before-report")` to obtain the `drift_summary`, threads it into `report.generate(..., drift_summary=...)`, then calls `_run_drift_pipeline(when="after-report")` to persist the new snapshot. This is the actual Python orchestration site that calls `report.generate(...)`.

### `tests/test_report.py` (5 new tests, RED→GREEN)
- `test_drift_section_omitted_when_summary_is_none` (D-09)
- `test_drift_section_renders_summary_table` (D-07 4-row exact strings)
- `test_drift_section_empty_graph_with_snapshot` (D-08)
- `test_drift_section_per_class_top_10` (D-07 N=10)
- `test_drift_section_placement_after_federation` (D-06 ordering)

### `tests/test_drift.py` (1 new test — CDRIFT-02 anchor)
- `test_rename_yields_community_renamed_not_orphaned`: builds 2-community graph with 2 `implements` edges, snapshots, then changes only the integer cids (membership identical), recomputes drift, and asserts `community-renamed >= 1` AND `orphaned == 0`.

## Commits

| Gate  | Hash      | Message |
|-------|-----------|---------|
| RED   | `f3944bc` | `test(67-05): add failing tests for Drift section in GRAPH_REPORT.md` |
| GREEN | `a7d507d` | `feat(67-05): render Drift section in GRAPH_REPORT.md after Federation` |
| FEAT  | `a593e98` | `feat(67-05): wire drift compute and snapshot into graphify run pipeline; add CDRIFT-02 rename E2E test` |

## Verification

- `pytest tests/test_drift.py tests/test_report.py -q` → **63 passed**.
- `pytest tests/ -q` → **2389 passed, 1 xfailed, 2 failed (both pre-existing on main)**:
  - `tests/test_migration.py::test_preview_expands_risky_action_rows` — flagged in 67-01 SUMMARY.
  - `tests/test_capability.py::test_validate_cli_zero` — confirmed pre-existing via `git stash` test run on the prior tip; unrelated to drift wiring (it validates `server.json`).
- All Task-1 grep gates pass:
  - `grep -c "## Drift" graphify/report.py` = 2 (≥1 required)
  - `grep -c "drift_summary" graphify/report.py` = 5 (≥2 required)
  - `grep -c "_DRIFT_TOP_N = 10" graphify/report.py` = 1
  - `grep -o '"stable"\|"community-renamed"\|"community-resharded"\|"orphaned"' graphify/report.py | wc -l` = 7 (≥4 required)
- All Task-2 grep gates pass:
  - `grep -c "compute_edge_drift" graphify/__main__.py` = 3
  - `grep -c "write_drift_snapshot" graphify/__main__.py` = 2
  - `grep -c "drift_summary" graphify/__main__.py` = 3
  - First `compute_edge_drift` line (51) precedes first `write_drift_snapshot` line (54) ✓
  - `grep -v '^#' graphify/__main__.py | grep -c "cache/snapshots"` = 0 (D-01 path enforced)
  - `cap=10` literal present in `_run_drift_pipeline` and at the watch.py call site

## Deviations from Plan

### [Rule 3 — blocking] Orchestration site is `watch.py`, not `__main__.py::run` directly

**Found during:** Task 2.
**Issue:** The plan's Task-2 instructions say "locate the call to `report.generate(...)` in `graphify/__main__.py::run`". However, `__main__.py::run` only invokes `graphify.pipeline.run_corpus`, which is an extract-only stage — it never calls `report.generate(...)`. The actual Python orchestration that calls `cluster() → report.generate()` lives in `graphify/watch.py::_rebuild_code` (skill files invoke `report.generate` externally).
**Fix:** Added the canonical drift-orchestration helper `_run_drift_pipeline(when=...)` in `graphify/__main__.py` (satisfying the plan's "CLI orchestration in `__main__.py`" intent and all grep-based acceptance gates), and wired `watch._rebuild_code` to call it before/after `report.generate(...)`. This preserves the compute-before / write-after invariant where it actually matters.
**Files modified:** `graphify/__main__.py` (helper added), `graphify/watch.py` (call sites added).
**Commit:** `a593e98`.

## TDD Gate Compliance

- RED commit (`test(67-05): ...` — `f3944bc`) lands before GREEN (`feat(67-05): ...` — `a7d507d`).
- RED gate confirmed: `pytest tests/test_report.py -q` exited non-zero with `TypeError: generate() got an unexpected keyword argument 'drift_summary'` on the RED commit.
- GREEN gate confirmed: `pytest tests/test_report.py -q` → 50 passed after GREEN.

## Self-Check: PASSED

- `graphify/report.py` modified ✓ (Drift section renderer present).
- `graphify/__main__.py` modified ✓ (`_run_drift_pipeline` helper present).
- `graphify/watch.py` modified ✓ (drift wiring around report.generate present).
- `tests/test_report.py` modified ✓ (5 new Drift tests).
- `tests/test_drift.py` modified ✓ (CDRIFT-02 rename test present).
- Commits `f3944bc`, `a7d507d`, `a593e98` all present in `git log --oneline --all`.
