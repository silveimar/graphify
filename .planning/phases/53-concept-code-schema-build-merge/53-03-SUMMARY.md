---
phase: 53-concept-code-schema-build-merge
plan: 03
subsystem: build
tags: [build, merge, canonical, deterministic, concept-code, tdd-green]
requires: [53-01, 53-02]
provides: ["Deterministic edge merge", "Canonical (source,target,relation) sort", "Code→concept orientation for all 5 relations"]
affects: [graphify/build.py]
tech-stack:
  added: []
  patterns: ["sorted(set()) dedup join", "lex-min source_location", "max() confidence_score", "node insertion ordered by edge sources for NetworkX iteration determinism"]
key-files:
  created: []
  modified:
    - graphify/build.py
decisions: [D-53.02, D-53.05, D-53.06, D-53.10]
metrics:
  duration: ~5min
  tasks: 2
  completed: 2026-04-30
---

# Phase 53 Plan 03: Concept↔code build/merge canonicalization Summary

GREEN-build phase for CGRAPH-02: rewrote `_merge_edge_fields` for deterministic merge, extended code→concept orientation to all 5 concept↔code relations, and added a final canonical sort across all edges with NetworkX-iteration-aware node insertion.

## What Was Changed

### Task 1: `_merge_edge_fields` canonical determinism (D-53.05)
Rewrote the merge function in `graphify/build.py` to enforce deterministic field merging across re-runs:
- **`source_file`**: split on `;`, dedupe via `set`, lex-sort, rejoin with `"; "`. Accepts `list[str]` for forward compatibility.
- **`source_location`**: lex-min of non-empty values (was: concatenation).
- **`confidence`**: highest tier wins via `_CONF_RANK` (EXTRACTED > INFERRED > AMBIGUOUS); base wins on tie.
- **`confidence_score`**: `max()` of present numeric values across both edges.
- **`weight`**: sum (Phase 46 contract preserved).
- **`evidence`** and other base fields: inherited via `dict(base)` (base-wins, silent drop of non-base evidence per W5).

### Task 2: Orientation extension + canonical sort (D-53.02, D-53.06)
- Added module-level `CONCEPT_CODE_RELATIONS` constant: `("implements", "documents", "tests", "realizes", "instantiates")`.
- Extended `orient(...)` block in `_normalize_concept_code_edges` to apply to all 5 relations (was: `implements` only).
- **Opposite-direction collapse (`impl_buckets`) intentionally remains scoped to `implements` only** — the four new relations have no `*_by` synonym; widening would silently merge user-distinct edges (per RESEARCH §"Extend orientation").
- Appended final `edges.sort(key=lambda e: (source, target, relation))` at the end of `_normalize_concept_code_edges`, applied across ALL edges (concept↔code AND structural).
- **W2 acceptance fix**: reordered node insertion in `build_from_json` so NetworkX undirected edge iteration matches the canonical sort. Strategy: insert edge sources first (in canonical-sorted edge order), then edge targets not yet seen, then isolated nodes. This guarantees `(source, target)` tuple yielding aligns with insertion order because NetworkX iterates edges per-node in node-insertion order.

## Test Status

| Suite | Result |
|-------|--------|
| `tests/test_concept_code_edges.py` | **18/18 GREEN** (5 RED → GREEN; 13 backward-compat preserved) |
| `tests/test_concept_code_mcp.py` | GREEN |
| `tests/test_validate.py` | GREEN |
| `tests/test_build.py` | GREEN |
| `tests/test_excalidraw_layout.py` | GREEN |
| `pytest tests/ -q` (full) | **1979 passed, 1 xfailed, 0 failed** in 70.36s |

### Plan-01 tests now GREEN (formerly RED)
- `test_round_trip_list_equality_across_reruns` (W2 — NetworkX iteration matches canonical sort)
- `test_mergeable_duplicates_canonical_source_files`
- `test_mergeable_duplicates_max_confidence_score`
- `test_canonical_sort_across_all_relations`
- `test_direction_normalize_realizes_reverse`
- `test_direction_normalize_all_concept_code_relations`
- `test_documents_relation_no_orient_when_neither_endpoint_code`

### Phase 46 backward-compat (still GREEN)
- `test_implemented_by_normalizes_to_implements_orient_code_to_concept`
- `test_duplicate_implements_merges_source_files`
- `test_graph_json_round_trip_implements`

## Files Changed

- `graphify/build.py` — 2 commits, +96/-11 lines net.

## Commits

| Hash    | Message |
|---------|---------|
| `d051387` | `feat(53-03): rewrite _merge_edge_fields for canonical determinism` |
| `45c18b1` | `feat(53-03): extend orientation to 5 relations + canonical sort` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Node insertion order required for W2 acceptance**
- **Found during:** Task 2 verification
- **Issue:** `edges.sort` alone was insufficient to satisfy `test_round_trip_list_equality_across_reruns` and `test_canonical_sort_across_all_relations`. NetworkX undirected `Graph.edges()` iterates edges per-node in node-insertion order, so the iteration order does not follow edge-list order even when the underlying edge list is canonically sorted.
- **Fix:** Reordered node addition in `build_from_json` to insert edge sources first (in canonical-sorted edge order), then edge targets not yet seen, then isolated nodes. The plan acceptance criteria explicitly anticipated this need: "the implementation must be revised (e.g., feed pre-sorted edges into `add_edges_from` rather than relying on dict iteration order)."
- **Files modified:** `graphify/build.py` (`build_from_json` node-insertion block)
- **Commit:** `45c18b1`
- **Verification:** All 1979 tests pass; no regressions.

## Decisions Made

- **D-53.02 (orient all 5)**: Implemented as planned. `CONCEPT_CODE_RELATIONS` tuple defines canonical set.
- **D-53.05 (canonical merge)**: Implemented exactly per plan sketch.
- **D-53.06 (final sort)**: Implemented at end of `_normalize_concept_code_edges`. Augmented with node-insertion reordering in `build_from_json` to satisfy W2 acceptance.
- **D-53.10 (`implements` rules unchanged)**: Verified — Phase 46 tests pass unchanged. Rewrite changes HOW fields merge, not the relation contract.

## Self-Check: PASSED

- Files modified verified present (`graphify/build.py`).
- Both commits verified in `git log` (`d051387`, `45c18b1`).
- Acceptance grep counts all met:
  - `_split_sf` → 2 occurrences
  - `sorted(set(` → 1 occurrence
  - `if scores:` → 1 occurrence
  - `CONCEPT_CODE_RELATIONS` → 2 occurrences
  - `edges.sort` → 1 occurrence
  - `implemented_by` → 2 occurrences (existing handling preserved)

## EXECUTION COMPLETE
