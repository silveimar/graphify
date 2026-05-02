---
phase: 55
plan: "01"
subsystem: templates
tags: [tdd, red-gate, block-context, predicate-scaffold]
dependency_graph:
  requires: []
  provides: [BlockContext-6-fields, red-tests-if-note-type, red-tests-if-flag, red-tests-predicate-flags]
  affects: [graphify/templates.py, tests/test_templates.py, tests/test_profile.py]
tech_stack:
  added: []
  patterns: [frozen-dataclass-defaults, tdd-red-gate]
key_files:
  created: []
  modified:
    - graphify/templates.py
    - tests/test_templates.py
    - tests/test_profile.py
decisions:
  - "Frozen dataclass with default fields (Python 3.10+) makes BlockContext extension backward-compatible at all ~30+ existing call sites"
  - "RED tests for omit-cases (note_type mismatch, flag absent) correctly pass because current engine already evaluates unknown predicates as false — this is expected and documented"
  - "Added test_if_note_type_all_six_types_evaluated_independently to provide 1 extra RED test covering all 6 type branches in a single test, ensuring >=7 RED tests"
  - "Added test_if_flag_truthy_rule_with_node_attr and test_if_flag_equality_rule_renders_when_attr_equals_value to reach >=3 RED flag tests"
metrics:
  duration: "330s"
  completed: "2026-05-02"
  tasks: 2
  files: 3
---

# Phase 55 Plan 01: Wave 0 RED Gate — BlockContext Extension + RED Scaffolds

Frozen `BlockContext` extended with two defaulted Phase 55 fields (`note_type`, `flag_predicates`) and RED scaffold tests established for `if_note_type_*`, `if_flag_*`, and `predicate_flags` validation — all with the Phase 31 byte-identical gate held GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend BlockContext with note_type and flag_predicates | 1abad3f | graphify/templates.py |
| 2 | Update byte-identical gate + write RED scaffold tests | 91a3b60 | tests/test_templates.py, tests/test_profile.py |

## Acceptance Gate Results

| Gate | Result | Count |
|------|--------|-------|
| test_block_free_template_renders_byte_identical | GREEN | 1/1 |
| Phase 31 backward-compat tests (nested x2, empty-loop) | GREEN | 3/3 |
| if_note_type_* tests fail RED | RED | 7 failing / 10 collected |
| if_flag_* tests fail RED | RED | 3 failing / 5 collected |
| predicate_flags validation tests fail RED | RED | 8 failing / 8 collected |

## Deviations from Plan

### Auto-adjustments

**1. [Rule 2 - Missing functionality] Added 2 extra if_note_type_* tests to meet >=7 RED count**
- **Found during:** Task 2 acceptance verification
- **Issue:** "Omits when mismatch" and "omits when None" tests passed GREEN (expected — current engine already evaluates unknown predicates as false). Only 6 of 9 `if_note_type_*` tests failed RED. Plan requires >=7.
- **Fix:** Added `test_if_note_type_all_six_types_evaluated_independently` which requires the evaluator and fails RED. Total: 7 failing / 10 collected.
- **Files modified:** tests/test_templates.py

**2. [Rule 2 - Missing functionality] Added 2 extra if_flag_* tests to meet >=3 RED count**
- **Found during:** Task 2 acceptance verification
- **Issue:** "Omits when false" and "unknown name omits" tests passed GREEN (same reason as above). Only 1 of 3 flag tests failed RED.
- **Fix:** Added `test_if_flag_truthy_rule_with_node_attr` and `test_if_flag_equality_rule_renders_when_attr_equals_value`. Total: 3 failing / 5 collected.
- **Files modified:** tests/test_templates.py

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 91a3b60 | PRESENT |
| GREEN | Deferred to 55-02 / 55-03 | N/A — this plan is the RED gate |

This plan intentionally establishes RED state only. GREEN landing is Plans 55-02 (evaluator) and 55-03 (validator).

## Known Stubs

None. The new `note_type` and `flag_predicates` fields in `BlockContext` default to `None` and `{}` respectively. No stub values flow to rendered output — the fields are used only by predicate evaluation logic which is intentionally deferred to 55-02/55-03.

## Threat Flags

None. Changes are dataclass field additions (no new network endpoints, auth paths, or schema changes at trust boundaries). Threat mitigations T-55-INJ and T-55-NAME-COLLISION are staged as RED tests (`test_predicate_flags_catalog_collision_rejected`) and will be verified GREEN in 55-03.

## Self-Check: PASSED

- `graphify/templates.py` modified: FOUND
- `tests/test_templates.py` modified: FOUND
- `tests/test_profile.py` modified: FOUND
- Commit 1abad3f: FOUND
- Commit 91a3b60: FOUND
- `dataclasses.fields(BlockContext)` == 6: VERIFIED
- Backward-compat 4/4 GREEN: VERIFIED
- RED counts: if_note_type 7/10, if_flag 3/5, predicate_flags 8/8: VERIFIED
