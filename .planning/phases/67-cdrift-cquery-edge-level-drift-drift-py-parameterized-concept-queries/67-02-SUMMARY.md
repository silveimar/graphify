---
phase: 67
plan: 02
subsystem: cquery
tags: [cquery, validation, mcp, tdd]
requires: []
provides:
  - "_validate_relations_filter_arg"
  - "_resolve_confidence_band"
  - "_build_concept_hops_filter"
  - "_CONFIDENCE_BAND_CUTPOINTS"
affects:
  - graphify/serve.py
tech-stack:
  added: []
  patterns:
    - "Sibling-validator pattern (legacy _validate_relations_arg preserved byte-identical)"
    - "Half-open [lo, hi) band ranges for uniform predicate test"
    - "Identity-skip optimization (factory returns None when all gates None)"
key-files:
  created:
    - tests/test_concept_code_hops.py
  modified:
    - graphify/serve.py
decisions:
  - "D-10 cutpoints encoded as half-open ranges; high → (0.8, +inf) so a single `lo <= x < hi` test covers all three bands"
  - "All-None args → factory returns None (not an always-true predicate) so Plan 04 BFS callers can skip predicate eval entirely and preserve v1.12 byte-identity"
  - "typing.Callable imported eagerly (not just under TYPE_CHECKING) so the annotation resolves under any future runtime introspection"
metrics:
  duration: ~4 min
  completed: 2026-05-06
---

# Phase 67 Plan 02: CQUERY Validators + Filter Predicate Factory Summary

TDD-built three pure helpers in `graphify/serve.py` for CQUERY-01: a `[]`-accepting relations validator, a D-10 band resolver, and an AND-semantic edge predicate factory — all sibling to (and not modifying) the legacy `_validate_relations_arg`.

## What Was Built

- **`_validate_relations_filter_arg(value)`** — NEW. Accepts `None`, `[]` (D-12 zero-match), or `list[str]`. Rejects non-list, non-string members.
- **`_resolve_confidence_band(band)`** — NEW. Maps `"high"|"medium"|"low"|None` to half-open `(lo, hi)` per D-10. `"high"` uses `+inf` as the upper bound so the predicate's uniform `lo <= x < hi` test simplifies to `x >= 0.8`.
- **`_build_concept_hops_filter(min_confidence, relations, confidence_band)`** — NEW. Returns `None` when all three args are `None` (D-13 v1.12 byte-identity preservation). Otherwise returns a `Callable[[dict], bool]` applying AND semantics (D-11): min_confidence gate → band gate → relations gate. `relations=[]` → strict zero-match (drops every edge).
- **`_CONFIDENCE_BAND_CUTPOINTS`** — module-level dict, single source of truth for D-10 band edges.

## Test Coverage

`tests/test_concept_code_hops.py` — 23 new tests, all passing:

- 5 tests on `_validate_relations_filter_arg` (incl. `[]` accepted, parametrized non-list rejection)
- 1 test pinning legacy `_validate_relations_arg([])` STILL returns an error (D-12 revised contract)
- 5 tests on `_resolve_confidence_band` (each band's range membership, `None` passthrough, invalid-name rejection)
- 8 tests on `_build_concept_hops_filter` (single-gate, AND-composition, empty-list zero-match, all-None identity, missing-score handling)

## Verification

- `pytest tests/test_concept_code_hops.py -q` → 23 passed
- `pytest tests/test_serve.py -q` → 208 passed (no regression)
- `grep -c "^def _validate_relations_arg" graphify/serve.py` → `1` (legacy preserved, not duplicated)
- `grep -c "^def _validate_relations_filter_arg" graphify/serve.py` → `1`
- Full suite (`pytest tests/ -q --ignore=tests/test_drift.py`): 2365 passed, 1 unrelated pre-existing failure in `tests/test_migration.py::test_preview_expands_risky_action_rows`, 1 xfailed.

## Deferred / Out-of-Scope Issues

- `tests/test_drift.py` fails to import `graphify.drift` — Phase 67 Plan 01 deliverable, not this plan.
- `tests/test_migration.py::test_preview_expands_risky_action_rows` — pre-existing failure, unrelated to serve.py changes.

## Deviations from Plan

None — plan executed exactly as written. Only minor: added `from typing import Callable` to imports so the return-type annotation resolves under runtime introspection (defensive; `from __future__ import annotations` already lazy-evaluates annotations).

## Commits

| Task | Type     | Hash      | Message                                                                   |
| ---- | -------- | --------- | ------------------------------------------------------------------------- |
| 1    | RED      | `ad854d0` | test(67-02): add failing tests for CQUERY validators and filter predicate |
| 2    | GREEN    | `d23f6a9` | feat(67-02): add CQUERY validators and AND-semantic filter predicate      |

## Hand-off to Plan 04

Plan 04 will thread `_build_concept_hops_filter` into `_run_concept_code_hops` BFS at serve.py:2290–2566. The factory's `None`-return-when-all-gates-None contract lets Plan 04 do `if predicate is None: <legacy v1.12 code path>` to guarantee byte-identity for unaffected callers.

## Self-Check: PASSED

- File `tests/test_concept_code_hops.py`: FOUND
- File `graphify/serve.py`: FOUND (modified)
- Commit `ad854d0`: FOUND
- Commit `d23f6a9`: FOUND
- Legacy validator unchanged: VERIFIED (208/208 serve tests green)
- New helpers exported: VERIFIED (23/23 new tests green)
