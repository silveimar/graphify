---
phase: 72-reas
plan: 03
subsystem: build
tags: [reasoning, supersedes, temporal, build-pipeline]
requires: [72-01]
provides: [_resolve_reasoning_targets, _stamp_supersession_outbound]
affects: [graphify/build.py, tests/test_build.py]
tech-stack:
  added: []
  patterns: [two-pass-resolution, idempotent-stamp, in-place-mutation]
key-files:
  created: []
  modified:
    - graphify/build.py
    - tests/test_build.py
decisions:
  - D-04 substring fallback uses lex-sorted candidates for determinism
  - D-07 newer→older orientation: target of supersedes edge is the SUPERSEDED node
  - D-09 idempotency via `if e.get("valid_until") is None` guard preserves prior stamps
  - D-10 outbound stamp never creates new edges — pure attribute mutation
  - Resolver runs BEFORE _normalize_concept_code_edges so canonical sort sees resolved targets
  - Outbound stamp runs AFTER stamp_supersessions (Phase 71) so triggers stay disjoint
metrics:
  duration: ~15m
  completed: 2026-05-07
  tests_added: 9
  tests_passing: 90 (test_build.py + test_validate.py + test_temporal.py)
---

# Phase 72 Plan 03: REAS — build.py reasoning resolver + supersedes outbound stamp Summary

build.py now resolves raw reasoning-edge target strings via id→label-ci→deterministic-substring fallback (dropping unresolved with stderr warning), and auto-stamps `valid_until=run_now` on every outbound edge of a superseded node so Phase 72 wiki/Obsidian rendering can surface historical relations.

## What Shipped

Two new module-level helpers in `graphify/build.py`:

1. **`_resolve_reasoning_targets(nodes, edges) → list[dict]`** (D-04). Pure function. Walks reasoning edges (relation ∈ `REASONING_RELATIONS`); for each, resolves `target` against:
   - (a) exact node id match → no-op,
   - (b) case-insensitive label match → rewrite to that node's id,
   - (c) deterministic substring match (lex-sorted candidates) → rewrite,
   - (d) drop with stderr `[graphify] dangling reasoning edge ... -relation-> 'tgt': no matching node, dropping`.

   Wired into `build_from_json` immediately after the edge-list copy and **before** `_normalize_concept_code_edges`, so canonical sort sees resolved targets.

2. **`_stamp_supersession_outbound(edges, run_now) → None`** (D-07/D-08/D-09/D-10). In-place mutator. Computes `superseded_ids = {e.target for e in edges if e.relation == "supersedes"}`, then for each non-supersedes edge whose `source` is in that set, stamps `valid_until=run_now` only when `valid_until` is currently `None`. Wired into `build_from_json` immediately after the existing `stamp_supersessions(...)` call.

9 new tests in `tests/test_build.py`:
- Resolver: `test_resolve_label_to_id`, `test_resolve_drops_unresolved`, `test_resolve_noop_for_non_reasoning`, `test_resolve_substring_deterministic`.
- Outbound stamp: `test_supersedes_outbound_stamp`, `test_supersedes_stamp_idempotent`, `test_supersedes_no_new_edges`, `test_supersedes_preserves_existing_valid_until`, `test_supersedes_no_supersedes_no_op`.

## Verification

- `pytest tests/test_build.py -x -q` → 40 passed.
- `pytest tests/test_build.py tests/test_validate.py tests/test_temporal.py -x -q` → 90 passed (no Phase 71 regressions).
- Acceptance grep checks:
  - `grep -c "_resolve_reasoning_targets" graphify/build.py` → 2 (def + call site).
  - `grep -c "_stamp_supersession_outbound" graphify/build.py` → 2.
  - `grep -q "dangling reasoning edge"` → match.
  - `grep -q 'str(e\["target"\])'` → match (orientation correct).
  - Call site ordering: resolver line 363 < normalize line 366; outbound stamp line 403 > stamp_supersessions line 395.

## Deviations from Plan

None — plan executed exactly as written. Both helpers, both wirings, and all 9 tests landed verbatim per `<action>` blocks. TDD RED→GREEN sequence: failing tests committed first (3ad35b9), implementation committed second (3b3b7d8). REFACTOR pass not needed — code shape matches RESEARCH §Pattern 3/4 exactly.

## Commits

| Hash    | Message                                                                          |
| ------- | -------------------------------------------------------------------------------- |
| 3ad35b9 | test(72-03): add failing tests for reasoning resolver and supersedes outbound stamp |
| 3b3b7d8 | feat(72-03): add reasoning-target resolver and supersedes outbound stamp         |

## Threat Flags

None. The `<threat_model>` mitigations T-72-06 (substring lex-min), T-72-07 (orientation), T-72-08 (cycle = single-pass O(E)), T-72-09 (idempotency guard) are all enforced by the implementation and covered by tests `test_resolve_substring_deterministic`, `test_supersedes_outbound_stamp`, and `test_supersedes_preserves_existing_valid_until`.

## Self-Check: PASSED

- FOUND: graphify/build.py (helpers + wirings present)
- FOUND: tests/test_build.py (9 new tests)
- FOUND commit: 3ad35b9 (test)
- FOUND commit: 3b3b7d8 (feat)
- All acceptance criteria from plan met.

## TDD Gate Compliance

- RED gate commit: 3ad35b9 (`test(72-03): ...`) ✓
- GREEN gate commit: 3b3b7d8 (`feat(72-03): ...`) ✓
- REFACTOR gate: not required (code matched target shape on first pass).
