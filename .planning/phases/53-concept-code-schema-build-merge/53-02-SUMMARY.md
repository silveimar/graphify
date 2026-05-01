---
phase: 53-concept-code-schema-build-merge
plan: 02
subsystem: validate
tags: [schema, validate, concept-code, tdd-green]
requires: [53-01]
provides: [evidence-rule, new-concept-code-relations]
affects: [graphify/validate.py]
tech-stack:
  added: []
  patterns: ["frozenset-vocabulary", "per-edge-conditional-validation"]
key-files:
  created: []
  modified:
    - graphify/validate.py
decisions:
  - "D-53.07/08: EXTRACTED on new relation requires evidence ∈ KNOWN_EVIDENCE_VALUES"
  - "D-53.07/08: INFERRED on new relation requires confidence_score ∈ [0.0, 1.0] (NaN-safe via float() + bounds compare)"
  - "D-53.09: AMBIGUOUS permitted without evidence/score on new relations"
  - "D-53.10: `implements` rule unchanged from Phase 46 (no evidence required for EXTRACTED)"
metrics:
  completed: 2026-04-30
---

# Phase 53 Plan 02: Concept↔code schema (validate.py) Summary

Extended `graphify/validate.py` with the four new concept↔code relations
(`documents`, `tests`, `realizes`, `instantiates`) and a per-edge evidence/score
validation branch. Phase 46 `implements` semantics remain unchanged.

## What was added

### Constants (Task 1, commit `d16d389`)
- `KNOWN_EDGE_RELATIONS` extended with `documents`, `tests`, `realizes`, `instantiates`
  (4 entries inserted after `implemented_by`).
- New module-level frozenset `NEW_CONCEPT_CODE_RELATIONS = {documents, tests,
  realizes, instantiates}` — the trigger set for the new evidence rule.
- New module-level frozenset `KNOWN_EVIDENCE_VALUES = {annotation, jsdoc,
  docstring, test_docstring, inheritance}` — the whitelist for the `evidence`
  field.

### Validation branch (Task 2, commit `ec65e3d`)
Inserted in the per-edge loop of `validate_extraction`, immediately after the
`confidence`-enum check, BEFORE source/target node-id existence checks.

For `relation in NEW_CONCEPT_CODE_RELATIONS`:
- `confidence == "EXTRACTED"`:
  - missing/empty/non-string `evidence` → error "requires non-empty 'evidence' field"
  - `evidence` not in `KNOWN_EVIDENCE_VALUES` → error "has unknown evidence ..."
- `confidence == "INFERRED"`:
  - `confidence_score` missing, non-numeric, NaN, or outside `[0.0, 1.0]` → error
    "requires 'confidence_score' in [0.0, 1.0]"
  - NaN-safe: `float('nan')` fails `0.0 <= score <= 1.0` comparison.
- `confidence == "AMBIGUOUS"`: permitted without evidence/score (D-53.09).

`implements` is intentionally NOT in `NEW_CONCEPT_CODE_RELATIONS`, so its
EXTRACTED-without-evidence behaviour stays Phase-46-compatible (D-53.10).

## Files changed

| File | Change |
|------|--------|
| `graphify/validate.py` | +54 lines (4 relations, 2 frozensets, 1 validation branch) |

## Test status

Run via `pytest tests/test_concept_code_edges.py tests/test_validate.py tests/test_concept_code_mcp.py`:

| Suite | Result |
|-------|--------|
| **Schema-rule tests (Plan 01 contracts)** | **7/7 GREEN** |
| `test_new_relations_validate_clean_with_inferred_score` | PASS |
| `test_extracted_new_relation_without_evidence_rejected` | PASS |
| `test_extracted_new_relation_unknown_evidence_rejected` | PASS |
| `test_extracted_new_relation_with_valid_evidence_accepted` | PASS |
| `test_ambiguous_new_relation_no_evidence_accepted` | PASS |
| `test_inferred_new_relation_missing_score_rejected` | PASS |
| `test_implements_unchanged_extracted_no_evidence_accepted` | PASS |
| **Phase 46 backward-compat tests** | **3/3 GREEN** |
| `test_implemented_by_normalizes_to_implements_orient_code_to_concept` | PASS |
| `test_duplicate_implements_merges_source_files` | PASS |
| `test_graph_json_round_trip_implements` | PASS |
| **Other already-passing in suite** | 3/3 PASS (warn_stderr, max_score-trivial, documents-no-orient-trivial) |
| **Build-merge tests (Wave 3)** | **5 RED (intentional)** |
| `test_round_trip_list_equality_across_reruns` | FAIL (Wave 3) |
| `test_mergeable_duplicates_canonical_source_files` | FAIL (Wave 3) |
| `test_canonical_sort_across_all_relations` | FAIL (Wave 3) |
| `test_direction_normalize_realizes_reverse` | FAIL (Wave 3) |
| `test_direction_normalize_all_concept_code_relations` | FAIL (Wave 3) |
| `tests/test_validate.py` | **16/16 PASS** (no regressions) |
| `tests/test_concept_code_mcp.py` | **1/1 PASS** (no regressions) |

Totals: 13 passed, 5 failed in `test_concept_code_edges.py`. The 5 failures are
build-layer tests deferred to Plan 53-03 (Wave 3); validate.py changes are
correct.

Note: The plan predicted 7 build-merge tests RED, but 2 of them
(`test_mergeable_duplicates_max_confidence_score`, `test_documents_relation_no_orient_when_neither_endpoint_code`)
coincidentally pass against current build code. Wave 3 will exercise them more
rigorously alongside the 5 still-RED tests.

## Commits made

| Commit | Task | Description |
|--------|------|-------------|
| `d16d389` | Task 1 | extend KNOWN_EDGE_RELATIONS + add NEW_CONCEPT_CODE_RELATIONS / KNOWN_EVIDENCE_VALUES |
| `ec65e3d` | Task 2 | add evidence/confidence_score validation branch in validate_extraction |

## Deviations from Plan

None. Plan executed exactly as written.

## Self-Check: PASSED

- `graphify/validate.py`: FOUND, contains all 4 new relations + both frozensets + validation branch.
- Commit `d16d389`: FOUND in `git log`.
- Commit `ec65e3d`: FOUND in `git log`.
- 7/7 schema-rule tests pass; 16/16 test_validate.py pass; 1/1 test_concept_code_mcp.py pass.
- Phase 46 backward-compat: 3/3 pass (`implemented_by` normalize, duplicate `implements` merge, graph json round-trip).

## EXECUTION COMPLETE
