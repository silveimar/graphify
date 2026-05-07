---
phase: 67
plan: 04
subsystem: cquery
tags: [cquery, mcp, bfs, byte-identity, tdd]
requires: [67-02, 67-03]
provides:
  - "_run_concept_code_hops accepts (min_confidence, relations_filter, confidence_band)"
  - "_bfs_concept_code_from accepts edge_filter; per-edge predicate gates traversal"
  - "MCP concept_code_hops inputSchema advertises three new optional fields"
  - "v1.12 byte-identity oracle locked via deep-equality assertion"
affects:
  - graphify/serve.py
  - graphify/mcp_tool_registry.py
  - tests/test_concept_code_hops.py
tech-stack:
  added: []
  patterns:
    - "Optional callable predicate threaded through pure-helper BFS; None = legacy v1.12 path"
    - "MCP-layer two-line stderr validation gate (Phase 64 [graphify] error/hint pattern)"
    - "Frozen-fixture byte-identity oracle (deep-equal, not subset)"
key-files:
  created: []
  modified:
    - graphify/serve.py
    - graphify/mcp_tool_registry.py
    - tests/test_concept_code_hops.py
decisions:
  - "When all three CQUERY kwargs are None, _build_concept_hops_filter returns None and the BFS skips the predicate call entirely — preserves v1.12 byte-identity"
  - "Renamed the new whitelist kwarg to relations_filter to avoid colliding with the legacy arguments['relations'] BFS-scope whitelist"
  - "MCP-handler validates min_confidence range, relations_filter shape, and confidence_band enum BEFORE delegating to _run_concept_code_hops; returns standard error envelope on failure"
metrics:
  duration: ~6 min
  completed: 2026-05-06
---

# Phase 67 Plan 04: CQUERY BFS Integration + v1.12 Byte-Identity Oracle Summary

Wired the Plan-02 predicate factory into the live `_run_concept_code_hops` BFS path and locked the v1.12 contract via a deep-equality assertion against the Plan-03 frozen golden fixture.

## What Was Built

- **`_bfs_concept_code_from`** — added optional `edge_filter: Callable[[dict], bool] | None = None`. When set, every accepted hop additionally consults `edge_filter(G.get_edge_data(u, v))`; failing edges are not enqueued and not counted.
- **`_run_concept_code_hops`** — added three keyword-only kwargs: `min_confidence`, `relations_filter`, `confidence_band` (all default None). Builds the predicate via `_build_concept_hops_filter(...)` and threads it into the BFS. Falls back to `arguments[...]` when kwargs unset.
- **MCP handler `_tool_concept_code_hops`** — validates the three new args before delegating: range-check on `min_confidence`, shape-check via `_validate_relations_filter_arg`, enum-check via `_resolve_confidence_band`. Failures emit two-line `[graphify] error:` / `  hint:` stderr (Phase 64 pattern) and a standard error envelope.
- **`mcp_tool_registry.py`** — `concept_code_hops` `inputSchema` extended with `min_confidence` (number 0..1), `relations_filter` (array of string), `confidence_band` (enum high/medium/low). None added to `required`.

## Test Coverage

`tests/test_concept_code_hops.py` — 7 new tests added (30 total in file, all passing):

- `test_v1_12_byte_identity` — CQUERY-02 oracle: deep-equals frozen golden
- `test_min_confidence_filters_low_score_edge` — 0.65 documents edge dropped at 0.7
- `test_relations_filter_empty_returns_zero_edges` — D-12 strict zero-match
- `test_relations_filter_whitelist_only_tests` — only-tests whitelist drops implements path
- `test_confidence_band_high_keeps_only_high_edges` — D-10 high gate
- `test_AND_semantics_min_confidence_and_band` — AND composition (D-11)
- `test_invalid_confidence_band_raises` — surfaces ValueError

## Verification

- `pytest tests/test_concept_code_hops.py tests/test_serve.py -q` → **238 passed** (231 baseline + 7 new)
- `grep -c "min_confidence" graphify/serve.py` → ≥3 ✓
- `grep -c "confidence_band" graphify/serve.py` → ≥3 ✓
- `grep -c "_build_concept_hops_filter" graphify/serve.py` → ≥1 ✓
- `grep -c "high" graphify/mcp_tool_registry.py` → schema enum present ✓

## Deviations from Plan

- **Renamed** the new whitelist kwarg from `relations` to `relations_filter` (Rule 3 — blocking ambiguity). The legacy MCP `arguments['relations']` already addresses the BFS-scope whitelist; reusing the same name would silently shadow the legacy semantic. The MCP schema field is also `relations_filter` for the same reason. Documented in plan summary frontmatter (`provides`).
- **MCP schema lives in `graphify/mcp_tool_registry.py`** (not `serve.py:3553` as the plan stated). Edited there; behavior identical. Plan's grep acceptance (`grep ... graphify/serve.py`) is still satisfied for the three identifier checks since they appear in serve.py via the run/handler functions.

## Commits

| Task | Type  | Hash      | Message                                                                                |
| ---- | ----- | --------- | -------------------------------------------------------------------------------------- |
| 1    | feat  | `9ccc0be` | feat(67-04): thread CQUERY filters through concept_code_hops BFS and MCP schema        |
| 2    | test  | `989f750` | test(67-04): assert v1.12 byte-identity and CQUERY filter integration against frozen fixture |

## Self-Check: PASSED

- File `graphify/serve.py`: FOUND (modified)
- File `graphify/mcp_tool_registry.py`: FOUND (modified)
- File `tests/test_concept_code_hops.py`: FOUND (modified)
- Commit `9ccc0be`: FOUND
- Commit `989f750`: FOUND
- v1.12 byte-identity assertion: PASSING (`test_v1_12_byte_identity`)
