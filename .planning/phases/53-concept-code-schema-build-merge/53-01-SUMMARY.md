---
phase: 53-concept-code-schema-build-merge
plan: 01
subsystem: validate+build (concept↔code edges)
tags: [tdd, red, schema, build-merge]
type: tdd
wave: 1
requires: []
provides:
  - "Round-trip fixture (tests/fixtures/concept_code/round_trip.json)"
  - "Failing tests codifying CGRAPH-01 (validate.py schema rules) — RED"
  - "Failing tests codifying CGRAPH-02 (build.py merge determinism) — RED"
affects: [graphify/validate.py, graphify/build.py]
tech-stack:
  added: []
  patterns: ["pytest", "deterministic JSON fixture", "id-prefix→file_type test convention"]
key-files:
  created:
    - tests/fixtures/concept_code/round_trip.json
  modified:
    - tests/test_concept_code_edges.py
decisions: []
metrics:
  duration: ~5 minutes
  completed: 2026-04-30
---

# Phase 53 Plan 01: Concept↔code schema & build merge — RED tests Summary

Locked the CGRAPH-01 / CGRAPH-02 acceptance contract in test code via 14 new test functions and a deterministic 6-node/8-edge fixture, before any schema or merge code change is written. 8 of 14 newly added tests fail RED on `main` (the assertions that demand new behavior); the other 6 are accept-case oracles that hold trivially today and act as anti-regression guards. Phase 46 backward-compat tests remain green.

## What Was Created

### Fixture
- `tests/fixtures/concept_code/round_trip.json` — 6 nodes, 8 edges; covers all 5 concept↔code relations (`implements`, `documents`, `tests`, `realizes`, `instantiates`) + a `contains` structural edge + a mergeable duplicate `(k_klass, c_concept, implements)` pair (EXTRACTED@other.py + INFERRED@k.py) + a reverse-direction `realizes` edge (`c_concept2 → k_klass`) + an opposite-direction AMBIGUOUS `implements` edge.

### New tests appended to `tests/test_concept_code_edges.py`

Helper:
- `_minimal_nodes_for(...)` — id-prefix → file_type convention helper (W3).

Schema tests (Task 2, CGRAPH-01) — 7 functions:
- `test_new_relations_validate_clean_with_inferred_score`
- `test_extracted_new_relation_without_evidence_rejected` ← RED on main
- `test_extracted_new_relation_unknown_evidence_rejected` ← RED on main
- `test_extracted_new_relation_with_valid_evidence_accepted`
- `test_ambiguous_new_relation_no_evidence_accepted`
- `test_inferred_new_relation_missing_score_rejected` ← RED on main
- `test_implements_unchanged_extracted_no_evidence_accepted` (D-53.10 backward compat)

Build/merge tests (Task 3, CGRAPH-02) — 7 functions:
- `test_round_trip_list_equality_across_reruns` ← RED on main
- `test_mergeable_duplicates_canonical_source_files` ← RED on main
- `test_mergeable_duplicates_max_confidence_score`
- `test_canonical_sort_across_all_relations` ← RED on main
- `test_direction_normalize_realizes_reverse` ← RED on main
- `test_direction_normalize_all_concept_code_relations` ← RED on main
- `test_documents_relation_no_orient_when_neither_endpoint_code`

Total new tests: 14 (7 + 7). Total RED on main: 8.

## RED Confirmation

`pytest tests/test_concept_code_edges.py 2>&1 | tail`:

```
FAILED tests/test_concept_code_edges.py::test_extracted_new_relation_without_evidence_rejected
FAILED tests/test_concept_code_edges.py::test_extracted_new_relation_unknown_evidence_rejected
FAILED tests/test_concept_code_edges.py::test_inferred_new_relation_missing_score_rejected
FAILED tests/test_concept_code_edges.py::test_round_trip_list_equality_across_reruns
FAILED tests/test_concept_code_edges.py::test_mergeable_duplicates_canonical_source_files
FAILED tests/test_concept_code_edges.py::test_canonical_sort_across_all_relations
FAILED tests/test_concept_code_edges.py::test_direction_normalize_realizes_reverse
FAILED tests/test_concept_code_edges.py::test_direction_normalize_all_concept_code_relations
=================== 8 failed, 10 passed, 2 warnings in 7.01s ===================
```

Sample failure messages (excerpts confirming the assertions exercise the right gap):
- `test_extracted_new_relation_without_evidence_rejected`: `Expected evidence-required error, got: []` — current `validate_extraction` does not enforce the evidence rule yet.
- `test_mergeable_duplicates_canonical_source_files`: `source_file parts not lex-sorted: ['other.py', 'k.py', 'design.md']` — current `_merge_edge_fields` concatenates in iteration order.
- `test_direction_normalize_realizes_reverse`: `Expected k_klass → c_concept2, got _src=c_concept2 _tgt=k_klass` — current `_normalize_concept_code_edges` orients only `implements`.

The remaining 6 new tests (4 schema accept-cases + 2 build accept-cases) pass on main because the current code is permissive on those paths; they exist as anti-regression guards once GREEN-phase plans (53-02 / 53-03) tighten validation and merge logic.

## Phase 46 Backward-Compat (Precondition)

`pytest tests/test_concept_code_edges.py -k "implemented_by_normalizes_to_implements_orient_code_to_concept or duplicate_implements_merges_source_files or graph_json_round_trip_implements"`:

```
================= 3 passed, 15 deselected, 2 warnings in 7.53s =================
```

All 3 Phase 46 tests still pass — fixture and new tests do not perturb existing `implements` semantics.

## Files Changed

| File | Change |
|------|--------|
| tests/fixtures/concept_code/round_trip.json | Created (20 lines, 6 nodes / 8 edges) |
| tests/test_concept_code_edges.py | Appended 1 helper + 14 test functions (~216 new lines) |

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | b2bb78c | tests(53-01): add round-trip fixture corpus for concept-code edges |
| 2 | 61647e5 | tests(53-01): add failing schema tests for CGRAPH-01 |
| 3 | 4af2d59 | tests(53-01): add failing build/merge tests for CGRAPH-02 |

## Deviations from Plan

None. Plan executed exactly as written. Fixture content matches the plan verbatim; test functions appended unchanged. The hooked auto-build (graphify watch) ran after each commit per project convention; no deviations from RED/GREEN expectations.

## Observations for Wave 2/3

- 4 of 7 schema tests already pass on main only because `validate_extraction` is permissive (accepts unknown evidence labels and clean INFERRED records by silence). Wave 2 must keep these passing while making the 3 RED tests green.
- 2 of 7 build/merge tests already pass on main: `test_mergeable_duplicates_max_confidence_score` (because `_merge_edge_fields` does take max() for confidence_score on existing duplicates) and `test_documents_relation_no_orient_when_neither_endpoint_code` (vacuously true since current `_normalize_concept_code_edges` ignores `documents` entirely). Wave 3's orient extension must preserve the no-op when neither endpoint is `code`.
- Stderr noise during runs: graphify emits "unknown edge relation" warnings for `documents`, `tests`, `realizes`, `instantiates` — Wave 2 must add these to `KNOWN_EDGE_RELATIONS` (per plan's interface notes) and the warnings will disappear; existing `test_unknown_edge_relation_warns_stderr` is unaffected since it uses a synthetic relation name.

## Self-Check: PASSED

- [x] tests/fixtures/concept_code/round_trip.json exists (6 nodes, 8 edges, 5 concept↔code relations + contains).
- [x] Commit b2bb78c found in `git log`.
- [x] Commit 61647e5 found in `git log`.
- [x] Commit 4af2d59 found in `git log`.
- [x] All 14 new test function names present in tests/test_concept_code_edges.py via grep.
- [x] 8 RED failures confirmed via pytest run.
- [x] 3 Phase 46 precondition tests pass.

## EXECUTION COMPLETE
