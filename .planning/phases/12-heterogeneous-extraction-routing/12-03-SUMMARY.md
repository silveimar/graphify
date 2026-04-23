---
phase: 12-heterogeneous-extraction-routing
plan: "03"
subsystem: extract
tags: [ThreadPoolExecutor, ROUTE-03, ROUTE-07, batch]

requires:
  - phase: 12-01
    provides: Router API
  - phase: 12-02
    provides: model_id in cache keys
provides:
  - extract(paths, router=...) with optional parallel fan-out
  - Semaphore + 429 Event stampede control
  - max_tier_route for cluster batch tiering (CONTEXT D-01)
affects: [batch, skill, pipeline]

tech-stack:
  added: []
  patterns: ["router=None preserves single-thread deterministic order"]

key-files:
  created: ["tests/test_extract_router.py"]
  modified: ["graphify/extract.py", "graphify/batch.py"]

key-decisions:
  - "No ThreadPoolExecutor when router is None (behavior match pre-12)"

requirements-completed: [ROUTE-03, ROUTE-07]

duration: —
completed: 2026-04-17
---

# Phase 12 — Plan 03 Summary

**Optional `router` on `extract()` drives per-file resolution, parallel workers when router set, and ROUTE-07 concurrency primitives; `max_tier_route` picks cluster tier by deterministic order.**

## Self-Check: PASSED

`pytest tests/test_extract_router.py tests/test_extract.py -q`; full suite `1257 passed`.
