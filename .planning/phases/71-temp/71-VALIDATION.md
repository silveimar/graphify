---
phase: 71
slug: temp
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-07
---

# Phase 71 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 71-RESEARCH.md "Validation Architecture" section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — see `pyproject.toml`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_temporal.py tests/test_validate.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds full / ~3 seconds quick |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite command above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 71-01-T1 | 71-01 | 1 | TEMP-02 | T-71-01, T-71-03 | yaml.safe_load only; ImportError/FileNotFoundError → in-code defaults; GRAPHIFY_RUN_TS test-only override | unit | `pytest tests/test_temporal.py -x -q` | YES (created in this task) | planned |
| 71-01-T2 | 71-01 | 1 | TEMP-01 | T-71-05 | Read-tolerant validator; write-strict rejects missing valid_from / out-of-range decay_weight with exact strings (Pitfall 2) | unit | `pytest tests/test_validate.py tests/test_temporal.py -x -q` | YES (fixtures + tests created) | planned |
| 71-02-T1 | 71-02 | 2 | TEMP-01, TEMP-02 | T-71-06, T-71-07, T-71-08, T-71-09 | setdefault preserves pre-stamped fields; run_now computed once per build (Pitfall 3); AMBIGUOUS decays like INFERRED | unit | `pytest tests/test_build.py tests/test_temporal.py tests/test_validate.py -x -q` | YES (test_build.py extended) | planned |
| 71-03-T1 | 71-03 | 2 | TEMP-03 | T-71-10, T-71-11, T-71-12 | data.get("valid_until") is not None filter at 4 sites; god_nodes uses edge_subgraph view; legacy edges (no key) treated as current | unit | `pytest tests/test_analyze.py -x -q` | YES (test_analyze.py extended) | planned |
| 71-04-T1 | 71-04 | 3 | TEMP-03 | T-71-13, T-71-14, T-71-16 | Supersession stamps INFERRED-only missing tuples (D-4); global rule prevents supersession when same tuple in another file (D-5); history retained (D-6); shared ResolvedOutput path with __main__.py:1962 (Pitfall 1) | unit | `pytest tests/test_build.py -x -q` | YES (test_build.py extended) | planned |
| 71-04-T2 | 71-04 | 3 | TEMP-03 | T-71-18 | _merge_edge_fields preserves earliest valid_from and valid_until=None when any input is current (Pitfall 5) | unit | `pytest tests/test_build.py::test_merge_mixed_temporal_status -x -q` | YES (test_build.py extended) | planned |
| 71-04-T3 | 71-04 | 3 | TEMP-03 | T-71-17 | to_json round-trips temporal fields; to_graphml sanitizes valid_until=None (Pitfall 4); to_cypher quotes ISO and renders null; to_obsidian unchanged | integration | `pytest tests/test_export.py -x -q` | YES (test_export.py extended) | planned |
| 71-05-T1 | 71-05 | 3 | TEMP-04 | — | report.py emits "## Temporal Health" with currently-valid count, superseded count, % superseded (D-10 minimal counts-only) | unit | `pytest tests/test_report.py -x -q` | YES (test_report.py extended) | planned |
| 71-05-T2 | 71-05 | 3 | TEMP-04 | T-71-15 | wiki.py renders "## Historical relations" when non-empty (D-11); omits heading when empty; html.escape + 64-char cap on valid_until | unit | `pytest tests/test_wiki.py -x -q` | YES (test_wiki.py extended) | planned |

*Wave 0 fixtures (legacy graph.json without temporal columns; modern graph.json with temporal columns) gate Wave 1+ — created by 71-01-T2.*

---

## Wave 0 Requirements

- [x] `tests/test_temporal.py` — new test module for valid_from / valid_until field semantics, schema_version 2.0 round-trip (created by 71-01-T1)
- [x] `tests/fixtures/graph_legacy_v113.json` — frozen pre-temporal graph for backward-compat read tests (created by 71-01-T2)
- [x] `tests/fixtures/graph_temporal_v20.json` — temporal-stamped graph for write/read round-trip (created by 71-01-T2)
- [x] `tests/conftest.py` — add `pinned_run_ts` fixture (env-var `GRAPHIFY_RUN_TS` override) for deterministic temporal stamping (created by 71-01-T1)
- [x] Extend `tests/test_validate.py` — assert `validate_extraction_for_read` accepts legacy edges and `validate_extraction_for_write` requires `valid_from` (extended by 71-01-T2)

---

## Manual-Only Verifications

*(None.)* The earlier row claiming `to_obsidian` renders edge temporal frontmatter has been removed: `to_obsidian` writes node frontmatter only, and temporal data lives in wiki.py community articles per 71-05 (covered by automated `tests/test_wiki.py`).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
