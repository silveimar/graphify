---
phase: 12-heterogeneous-extraction-routing
plan: "01"
subsystem: routing
tags: [yaml, radon, complexity, ROUTE-01]

requires: []
provides:
  - graphify/routing.py with Router, classify_file, resolve_model, tier ordering
  - graphify/routing_models.yaml declarative tier → model_id / endpoint
affects: [extract, cache, batch, cli]

tech-stack:
  added: ["PyYAML (optional extra [routing])"]
  patterns: ["code-tier floor ROUTE-06", "vision skip when model absent ROUTE-10"]

key-files:
  created: ["graphify/routing_models.yaml"]
  modified: ["graphify/routing.py", "tests/test_routing.py", "pyproject.toml"]

key-decisions:
  - "Empty model_id uses legacy behavior; vision tier can skip extraction when unconfigured"

patterns-established:
  - "Router: load YAML → classify → resolve with tier floor for code files"

requirements-completed: [ROUTE-01, ROUTE-02, ROUTE-06, ROUTE-10]

duration: —
completed: 2026-04-17
---

# Phase 12 — Plan 01 Summary

**Declarative `routing_models.yaml` plus `Router` / `classify_file` / `resolve_model` with deterministic tier order and ROUTE-06 floor for code paths.**

## Performance

- **Tasks:** 2 (schema + implementation)
- **Verification:** `pytest tests/test_routing.py -q` (included in full suite)

## Accomplishments

- Complexity metrics (radon for Python when available; heuristics otherwise) and YAML-driven tier mapping.
- Code files never resolve below mid/simple tier; image paths use vision tier or explicit skip.

## Files Created/Modified

- `graphify/routing.py` — `Router`, `ResolvedRoute`, `ComplexityMetrics`, concurrency hooks for later plans
- `graphify/routing_models.yaml` — tiers, thresholds, vision/image sections
- `tests/test_routing.py` — tier floor + YAML override tests
- `pyproject.toml` — `[routing]` optional extra

## Self-Check: PASSED

Full project test run: `1257 passed` (2026-04-17).
