---
phase: 55
plan: "03"
subsystem: templates
tags: [tdd, green-gate, if-flag, predicate-flags, profile-validation]
dependency_graph:
  requires: [55-01-SUMMARY.md, 55-02-SUMMARY.md]
  provides: [if-flag-evaluator-GREEN, predicate-flags-validation-GREEN, compile-flag-predicates]
  affects: [graphify/templates.py, graphify/profile.py]
tech_stack:
  added: []
  patterns: [tdd-green-gate, regex-predicate-dispatch, local-import-cycle-avoidance]
key_files:
  created: []
  modified:
    - graphify/templates.py
    - graphify/profile.py
decisions:
  - "_IF_FLAG_RE placed immediately after _IF_NOTE_TYPE_RE for visual grouping of Phase 55 predicate families"
  - "_compile_flag_predicates compiles at render-call time per Q4 — does NOT mutate module-level _PREDICATE_CATALOG"
  - "KeyError propagation in _eval_predicate for unknown flag names leverages existing _expand_blocks defensive elision (D-19) — unknown flags evaluate False at render time"
  - "_validate_predicate_flags uses local import for _PREDICATE_CATALOG to preserve templates↔profile cycle avoidance pattern from profile.py:1430-1435"
  - "predicate_flags added to _VALID_TOP_LEVEL_KEYS so validate_profile does not emit spurious 'unknown key' errors"
  - "validate_template signature extended with known_flag_predicates: frozenset keyword-only arg (default frozenset()) — all existing callers remain valid"
metrics:
  duration: "104s"
  completed: "2026-05-02"
  tasks: 1
  files: 2
---

# Phase 55 Plan 03: GREEN Gate — `if_flag_*` Evaluator + `predicate_flags` Validation

`_IF_FLAG_RE` regex + `_compile_flag_predicates` helper + `_eval_predicate` flag branch + `validate_template` `if_flag_*` guard + `predicate_flags` key in `_VALID_TOP_LEVEL_KEYS` + `_validate_predicate_flags` in `validate_profile`; all 3 RED `if_flag_*` tests and 8 RED `predicate_flags` tests now GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _IF_FLAG_RE + _compile_flag_predicates + _eval_predicate branch + validate_template guard + predicate_flags validation | 80348d3 | graphify/templates.py, graphify/profile.py |

## Acceptance Gate Results

| Gate | Result | Count |
|------|--------|-------|
| if_flag_* tests GREEN | GREEN | 5/5 (3 prev-RED + 2 prev-passing) |
| predicate_flags validation tests GREEN | GREEN | 8/8 |
| test_block_free_template_renders_byte_identical | GREEN | 1/1 |
| if_note_type_* regression check | GREEN | 10/10 (no regression) |
| Phase 31 sentinels (nested x2, empty-loop) | GREEN | 3/3 |
| Full suite new failures | NONE | 0 new failures (16 doc-fence RED = 55-04 scope) |

## Deviations from Plan

None — plan executed exactly as written. All concrete deltas from plan context were applied:
1. `_IF_FLAG_RE` regex constant added after `_IF_NOTE_TYPE_RE`
2. `_compile_flag_predicates` helper added before `_eval_predicate`
3. `_eval_predicate` if_flag branch added (KeyError for unknown names, elision via _expand_blocks D-19)
4. `validate_template` signature extended with `known_flag_predicates: frozenset[str] = frozenset()`
5. `validate_template` if_flag validation branch added
6. Both production `BlockContext` call sites wired with `flag_predicates=_compile_flag_predicates(profile)`
7. `predicate_flags` added to `_VALID_TOP_LEVEL_KEYS` in profile.py
8. `_validate_predicate_flags` helper added before `validate_profile`
9. `_validate_predicate_flags` called from `validate_profile`
10. `known_flag_predicates` passed to `_validate_template` in preflight Layer 2

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 91a3b60 (from 55-01) | PRESENT |
| GREEN (impl commit) | 80348d3 | PRESENT |
| REFACTOR | N/A — no cleanup needed | N/A |

## Known Stubs

None. `flag_predicates` is now compiled and wired at both BlockContext production call sites. No placeholder values flow to rendered output.

## Threat Flags

None. Changes are pure predicate evaluation and validation additions — no new network endpoints, auth paths, file access, or schema changes at trust boundaries. T-55-FLAG-VAL (count cap ≤64) implemented in `_validate_predicate_flags`. T-55-NAME-COLLISION (catalog collision) implemented via catalog_bare check with `if_god_node` → `god_node` stripping.

## Self-Check: PASSED

- `graphify/templates.py` modified: FOUND
- `graphify/profile.py` modified: FOUND
- Commit 80348d3: FOUND
- `_IF_FLAG_RE` present in templates.py: VERIFIED
- `_compile_flag_predicates` present in templates.py: VERIFIED
- `_eval_predicate` flag branch present: VERIFIED
- `validate_template` known_flag_predicates param present: VERIFIED
- `flag_predicates=_compile_flag_predicates(profile)` at both BlockContext sites: VERIFIED
- `predicate_flags` in _VALID_TOP_LEVEL_KEYS: VERIFIED
- `_validate_predicate_flags` in profile.py: VERIFIED
- 5 if_flag_* tests GREEN: VERIFIED (pytest 5 passed)
- 8 predicate_flags tests GREEN: VERIFIED (pytest 8 passed)
- byte-identical gate GREEN: VERIFIED (1 passed)
- if_note_type_* no regression: VERIFIED (10 passed)
- Full suite: 16 doc-fence RED (55-04 scope), 0 new failures: VERIFIED (2018 passed)
