---
phase: 65
plan: 03
subsystem: report
tags: [report, calibration, histogram, graphify, cconf]
requires: [65-01, 65-02]
provides:
  - GRAPH_REPORT.md `## Calibration` section
  - 10-bin histogram of INFERRED concept↔code confidence_score
  - mode_collapse, refusal, no_negatives flag rules with named thresholds
  - skewed_distribution.json fixture (D-65.13)
affects:
  - graphify/report.py
tech-stack:
  added: []
  patterns:
    - "private underscore helpers + UPPER_SNAKE constants colocated near use site"
    - "lines.append() rendering pattern (mirrors existing inf_avg block)"
key-files:
  created:
    - tests/test_report_calibration.py
    - tests/fixtures/skewed_distribution.json
  modified:
    - graphify/report.py
decisions:
  - "Used networkx json_graph.node_link_graph for fixture loading (matches plan interface; nx.Graph is undirected, so fixture uses 5 code nodes × 2 concept nodes = 10 unique edges all in [0.80, 0.90) bin)"
  - "Calibration block placed immediately after Summary section (before Community Hubs) — earliest visible signal in report"
  - "No REFACTOR commit needed; helpers landed clean"
metrics:
  duration: ~12 minutes
  completed: 2026-05-06
  tasks: 2
  files: 3
requirements: [CCONF-04]
---

# Phase 65 Plan 03: GRAPH_REPORT.md Calibration Self-Check Summary

GRAPH_REPORT.md now ships a calibration self-check section that surfaces three scoring pathologies — mode collapse, refusal-to-decide, and absence of negatives — over the post-merge `confidence_score` distribution of INFERRED concept↔code edges, gated on n≥10.

## What Shipped

### `graphify/report.py` extensions
- Four module-level threshold constants (D-65.10/11): `_CALIBRATION_MIN_EDGES=10`, `_CALIBRATION_MODE_COLLAPSE_THRESHOLD=0.70`, `_CALIBRATION_REFUSAL_THRESHOLD=0.50`, `_CALIBRATION_NEGATIVE_FLOOR=0.05`.
- `_calibration_histogram(scores) -> list[int]`: 10 bins over [0.0, 1.0]; `int(s*10)` clamped to [0, 9] so 1.0 lands in bin 9.
- `_calibration_flags(bins, scores) -> list[(name, observed, threshold)]`: returns one tuple per fired rule.
- `generate(...)` extended with a `## Calibration` block placed immediately after the Summary section. Renders the histogram (one line per bin with ASCII bar), fired flags, and a post-merge semantics note (Pitfall #5). Skipped with a single `calibration skipped — insufficient INFERRED edges (n=…, need ≥10)` line when n<10.

### Test fixture (D-65.13)
- `tests/fixtures/skewed_distribution.json` — `schema_version: "1.13"`, 5 code nodes × 2 concept nodes = 10 INFERRED `documents` edges, all `confidence_score` in [0.80, 0.90) → 100% mass in bin 8 → fires `mode_collapse` (and `no_negatives` since 0% below 0.5).

### Tests (6 total)
- `test_histogram_bucketing` — bucket math + clamp at 1.0.
- `test_mode_collapse_flag_fires` — loads fixture, asserts `mode_collapse` with observed > 0.70.
- `test_refusal_flag_fires` — synthetic 60% exactly-0.5.
- `test_no_negatives_flag_fires` — synthetic 0% below 0.5.
- `test_histogram_always_rendered` — n=10 well-distributed renders all 10 bin lines.
- `test_min_edge_gate_skips` — n=5 produces "calibration skipped" with `n=5` and no flag-firing language.

## Verification

- `pytest tests/test_report_calibration.py -x -q` → 6 passed.
- `pytest tests/ -q` → 2318 passed, 1 xfailed, 1 failed (the pre-existing `tests/test_migration.py::test_preview_expands_risky_action_rows` documented in `deferred-items.md`; out of scope per plan).
- Phase 64 stderr contract preserved (no new prints from this plan).

## Deviations from Plan

None — plan executed exactly as written. The fixture was authored with 5 code × 2 concept nodes (instead of 2 code + 2 rationale × multi-key) so that `nx.Graph` (simple, undirected) preserves all 10 distinct edges as required by the acceptance test.

## Auth Gates

None.

## Known Stubs

None.

## Commits

| Hash    | Type | Message |
|---------|------|---------|
| 0f59655 | test | RED — failing tests for calibration histogram + 3 flag rules + skewed fixture |
| dda7592 | feat | GREEN — calibration self-check histogram + 3 flag rules (CCONF-04) |

## TDD Gate Compliance

RED → GREEN sequence verified in git log. No REFACTOR commit (helpers landed clean — adding one would be churn).

## Self-Check: PASSED

- `tests/fixtures/skewed_distribution.json` — FOUND
- `tests/test_report_calibration.py` — FOUND
- `graphify/report.py` calibration helpers — FOUND (`_CALIBRATION_*` × 4 constants, `_calibration_histogram`, `_calibration_flags`, `## Calibration` render block)
- Commit 0f59655 — FOUND
- Commit dda7592 — FOUND
