---
phase: 21-profile-extension-template-bootstrap
plan: 01
subsystem: profile
tags: [profile, diagram_types, recommender, atomicity, d-06, d-07]
requirements: [PROF-01, PROF-02, PROF-03, PROF-04]
dependency_graph:
  requires:
    - graphify/profile.py::_DEFAULT_PROFILE
    - graphify/profile.py::_VALID_TOP_LEVEL_KEYS
    - graphify/profile.py::validate_profile
    - graphify/profile.py::load_profile
    - graphify/seed.py::build_seed
    - graphify/seed.py::_TEMPLATE_MAP
  provides:
    - profile.diagram_types schema (6 built-in entries)
    - diagram_types per-entry validator
    - seed.py recommender honoring profile.diagram_types with D-06 gating + D-07 tiebreak
  affects:
    - Phase 21 Plan 21-02 (--init-diagram-templates reads _DEFAULT_PROFILE.diagram_types)
    - Phase 22 Excalidraw skill (profile-driven template selection)
tech_stack:
  added: []
  patterns:
    - PROF-02 atomic landing (schema + default + validator + first consumer in one commit)
    - D-06 recommender gating (trigger_tags OR trigger_node_types AND min_main_nodes threshold)
    - D-07 tiebreak (stable max on min_main_nodes → declaration-order fallback)
    - try/except wrap around load_profile in seed.py to preserve never-break semantics
    - bool-before-int guard on min_main_nodes validation (mirrors topology.god_node.top_n pattern)
key_files:
  created: []
  modified:
    - graphify/profile.py (diagram_types in _DEFAULT_PROFILE, _VALID_TOP_LEVEL_KEYS, validate_profile entry validator)
    - graphify/seed.py (build_seed recommender reading profile.diagram_types)
    - tests/test_profile.py (+7 tests)
    - tests/test_seed.py (+5 tests)
decisions:
  - Parameter name `trigger` (not `source`) kept on `build_seed` call sites to match the actual signature in seed.py — the plan text read `source='auto'` in one sample; the real signature is `trigger`.
  - Added 2 tests beyond plan minimum — malformed-list rejection (non-list diagram_types) and declaration-order tiebreak — to lock down D-07 completely.
  - `min_main_nodes` validator uses `isinstance(x, bool)` short-circuit before `isinstance(x, int)` check, matching the pattern already used at `topology.god_node.top_n` (booleans subclass int in Python — without this guard `True`/`False` would pass an int check).
  - Recommender wraps `load_profile` in try/except and falls back to `_TEMPLATE_MAP[layout_type]` on any error — never breaks seed build on profile IO/import failure (T-21-05 mitigation).
metrics:
  duration_seconds: ~900
  commits: 1
  tasks_completed: 2
  files_modified: 4
  tests_added: 12
  completed: 2026-04-23
---

# Phase 21 Plan 01: Profile diagram_types Extension — Summary

**One-liner:** Extended `profile.py` schema with a `diagram_types:` section (6 built-in defaults — architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph) and wired `seed.py::build_seed` as the first consumer — all four hunks landed atomically in one commit per PROF-02, with D-06 gating (`min_main_nodes` threshold) and D-07 tiebreak (highest-min wins; declaration-order fallback) both covered by tests.

## Commit

| SHA | Subject |
|-----|---------|
| `0f4acf2` | `feat(21-01): add profile.diagram_types section with 6 builtin defaults + seed recommender (PROF-01/02/03/04)` |

## Files Changed (all in one commit — PROF-02 atomicity)

| File | Change |
|------|--------|
| `graphify/profile.py` | +54/-1 — `diagram_types` added to `_DEFAULT_PROFILE` (6 entries), `_VALID_TOP_LEVEL_KEYS` extended, `validate_profile` gains per-entry validator |
| `graphify/seed.py` | +30/-1 — `build_seed` recommender reading `profile.diagram_types` with D-06/D-07 |
| `tests/test_profile.py` | +63 — 7 tests (atomicity guard, 6 defaults, missing-fields graceful, missing-section OK, malformed rejected, non-list rejected, unknown-key rejected) |
| `tests/test_seed.py` | +108 — 5 tests (recommender profile match, fallback, D-06 min_main_nodes gate, D-07 highest-min wins, D-07 declaration-order tiebreak) |

Total: 253 insertions, 2 deletions.

## PROF-02 Atomicity Confirmation

Verified: `git show --stat 0f4acf2` shows all four files touched in the single commit. The schema change (keys list + default), the validator, and the first consumer (`build_seed`) all land together — no intermediate commit ever exposed a half-wired state where `diagram_types` is in the defaults but not yet validated, or validated but not yet read.

## Tests Added

**`tests/test_profile.py` (7 new):**
- `test_profile_diagram_types_atomicity_guard` — `'diagram_types'` in both `_VALID_TOP_LEVEL_KEYS` and `_DEFAULT_PROFILE`; `validate_profile(_DEFAULT_PROFILE) == []`.
- `test_profile_6_builtin_defaults` — exactly 6 entries with the named set.
- `test_profile_missing_diagram_types_section_ok` — absent section doesn't error.
- `test_profile_diagram_types_missing_fields_graceful` — entry with only `name` passes.
- `test_profile_diagram_types_malformed_rejected` — `{'name': 123}` yields non-empty errors.
- `test_profile_diagram_types_non_list_rejected` — `diagram_types: {}` → "must be a list".
- `test_profile_diagram_types_unknown_key_rejected` — unknown per-entry key → error.

**`tests/test_seed.py` (5 new):**
- `test_seed_recommender_profile_match` — node tagged `workflow` → `suggested_template` ends with `workflow.excalidraw.md`.
- `test_seed_recommender_fallback_to_layout` — no tag match → falls back to `_TEMPLATE_MAP[layout_type]`.
- `test_seed_recommender_gates_on_min_main_nodes` (D-06) — candidate with `min_main_nodes=5` excluded when `len(main_nodes)==4`.
- `test_seed_recommender_tiebreak_highest_min_main_nodes_wins` (D-07) — two matches, higher `min_main_nodes` wins.
- `test_seed_recommender_declaration_order_tiebreak` (D-07) — equal `min_main_nodes` → first-declared wins via stable `max`.

## Test Results

```
pytest tests/test_profile.py tests/test_seed.py -q
  (12 new tests + existing) — all passing

pytest tests/ -q
  1537 passed
```

Full-suite: **1537 passed**, 0 failures, 0 errors.

## Requirements Satisfied

| ID | Description | Evidence |
|----|-------------|----------|
| PROF-01 | Profile schema accepts `diagram_types:` | `_VALID_TOP_LEVEL_KEYS` extended; `test_profile_diagram_types_atomicity_guard` |
| PROF-02 | All four hunks land in ONE commit | Commit `0f4acf2` shows 4 files, 1 commit |
| PROF-03 | 6 built-in defaults merged into user profile | `_DEFAULT_PROFILE['diagram_types']` has 6 entries; `test_profile_6_builtin_defaults` |
| PROF-04 | First consumer (`seed.py::build_seed`) reads profile with fallback | Recommender in `build_seed`; 5 seed tests cover match/fallback/gate/tiebreak |

## Deviations from Plan

**1. [Rule 3 - Signature Match] Used parameter name `trigger` on `build_seed` invocation**
- **Issue:** Plan's sample test code called `build_seed(G, main_id, source='auto')`; the real `build_seed` signature uses `trigger` (not `source`).
- **Fix:** Tests pass `trigger='auto'`. No behavior change; purely matched actual API.

**2. [Rule 2 - Defense-in-depth] Added bool guard before int check for `min_main_nodes`**
- **Issue:** In Python, `True`/`False` are `isinstance(int)` — a user profile with `min_main_nodes: true` would silently pass an int check and become `1` at comparison time.
- **Fix:** `if isinstance(v, bool) or not isinstance(v, int):` — matches the pattern already used at `topology.god_node.top_n` in the same file.

**3. [Scope Expansion — within plan intent] Added 2 extra tests**
- `test_profile_diagram_types_non_list_rejected` — covers the "diagram_types must be a list" branch of the validator, which the plan's behavior-A list mentioned but did not test explicitly.
- `test_seed_recommender_declaration_order_tiebreak` — locks down the "ties fall back to declaration order" half of D-07 that the plan's tiebreak test covered only for the "different `min_main_nodes`" case.

No architectural changes, no new dependencies, no scope deviation. All extras tighten the contract the plan already specified.

## Authentication Gates

None.

## Self-Check: PASSED

- `graphify/profile.py` modifications present and contain `diagram_types` ✓
- `graphify/seed.py` modifications present and contain `diagram_types` ✓
- `tests/test_profile.py` and `tests/test_seed.py` modified ✓
- Commit `0f4acf2` exists in `git log` ✓
- Full pytest suite: 1537 passed ✓
