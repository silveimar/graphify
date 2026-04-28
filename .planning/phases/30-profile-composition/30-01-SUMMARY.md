---
phase: 30-profile-composition
plan: 01
subsystem: profile-loader
tags: [cfg-02, profile, composition, extends, includes, validation, security]
dependency_graph:
  requires:
    - graphify/profile.py::_deep_merge
    - graphify/profile.py::PreflightResult
    - graphify/profile.py::validate_profile
    - graphify/profile.py::_DEFAULT_PROFILE
  provides:
    - graphify/profile.py::_resolve_profile_chain
    - graphify/profile.py::_deep_merge_with_provenance
    - graphify/profile.py::ResolvedProfile
    - extended graphify/profile.py::PreflightResult (chain, provenance, community_template_rules)
    - tests/fixtures/profiles/ (Wave 0 fixture vaults)
  affects:
    - graphify/profile.py::load_profile (now routes through resolver)
    - graphify/profile.py::validate_profile_preflight (now routes through resolver)
tech-stack:
  added: []
  patterns:
    - "stack-local cycle detection (descending set + frame_chain list cleared in try/finally)"
    - "post-order chain construction so root-ancestor lands first naturally"
    - "sibling-relative path resolution confined to .graphify/ via Path.resolve + is_relative_to"
    - "graceful fallback: any resolver/validate error → stderr [graphify] profile error: + _DEFAULT_PROFILE"
key-files:
  created:
    - tests/test_profile_composition.py
    - tests/fixtures/profiles/single_file/.graphify/profile.yaml
    - tests/fixtures/profiles/linear_chain/.graphify/profile.yaml
    - tests/fixtures/profiles/linear_chain/.graphify/bases/fusion.yaml
    - tests/fixtures/profiles/linear_chain/.graphify/bases/core.yaml
    - tests/fixtures/profiles/includes_only/.graphify/profile.yaml
    - tests/fixtures/profiles/includes_only/.graphify/mixins/team.yaml
    - tests/fixtures/profiles/includes_only/.graphify/mixins/tags.yaml
    - tests/fixtures/profiles/extends_and_includes/.graphify/profile.yaml
    - tests/fixtures/profiles/extends_and_includes/.graphify/bases/fusion.yaml
    - tests/fixtures/profiles/extends_and_includes/.graphify/mixins/team-tags.yaml
    - tests/fixtures/profiles/cycle_self/.graphify/profile.yaml
    - tests/fixtures/profiles/cycle_indirect/.graphify/a.yaml
    - tests/fixtures/profiles/cycle_indirect/.graphify/b.yaml
    - tests/fixtures/profiles/cycle_indirect/.graphify/c.yaml
    - tests/fixtures/profiles/diamond/.graphify/profile.yaml
    - tests/fixtures/profiles/diamond/.graphify/fusion.yaml
    - tests/fixtures/profiles/diamond/.graphify/c.yaml
    - tests/fixtures/profiles/diamond/.graphify/core.yaml
    - tests/fixtures/profiles/partial_fragment/.graphify/profile.yaml
    - tests/fixtures/profiles/partial_fragment/.graphify/bases/partial.yaml
  modified:
    - graphify/profile.py
    - tests/test_profile.py
decisions:
  - "Stack-local frame_chain (list) ordered companion to descending (set) for cycle-error rendering"
  - "Resolver returns partial composition + errors list; caller decides whether to fall back"
  - "load_profile() prefixes resolver errors verbatim ([graphify] profile error:); preflight prefixes with 'profile.yaml: '"
  - "Existing test_preflight_result_tuple_unpack updated to star-rest unpack — full 4-tuple unpack of an extended NamedTuple is fundamentally incompatible with adding fields"
metrics:
  completed_date: "2026-04-28"
  tasks_total: 2
  tasks_complete: 2
  tests_added: 26
  tests_total_pass: 1721
---

# Phase 30 Plan 01: Profile Composition Resolver Summary

Add `extends:`/`includes:` resolver with cycle detection, depth cap 8, sibling-relative path resolution confined to `.graphify/`, and a provenance-tracking deep-merge variant — wiring `load_profile()` and `validate_profile_preflight()` to route through the resolver. Foundation for CFG-02 (Plans 02 + 03 build on this).

## What Shipped

- **`_resolve_profile_chain(entry_path, vault_dir) -> ResolvedProfile`** — walks single-parent extends + left-to-right includes + own-fields-last, returns `ResolvedProfile(composed, chain, provenance, errors, community_template_rules)`. Errors accumulate; the resolver never raises.
- **`_deep_merge_with_provenance`** — mirrors `_deep_merge` line-for-line, adding dotted-key→source-Path recording at every leaf write. Lists are recorded under the list key (no `[index]` suffix per R7). Preserves the does-not-mutate-base contract via `result = base.copy()` at recursion entry.
- **`ResolvedProfile` NamedTuple** — distinct from `PreflightResult` because the resolver runs before validation and before merge with `_DEFAULT_PROFILE`.
- **`PreflightResult` extended** — three trailing fields with defaults: `chain: list[Path] = []`, `provenance: dict[str, Path] = {}`, `community_template_rules: list[dict] = []`. Star-rest unpacking (`errors, warnings, *_ = result`) still works; the legacy 4-tuple full unpack pattern was updated in `test_profile.py` to use star-rest (the only call-site).
- **`_VALID_TOP_LEVEL_KEYS` extended** with `extends`, `includes`, `community_templates`.
- **`validate_profile()` extended** — type guards for `extends` (str), `includes` (list[str]), and a full `community_templates` validator block (match ∈ {label, id}, pattern type per match, template non-empty + relative + traversal-clean, only known keys allowed).
- **`load_profile()` refactored** — calls the resolver before validation. Any resolver error → `[graphify] profile error: …` to stderr + return `_deep_merge(_DEFAULT_PROFILE, {})`. Validate-then-fallback path preserved.
- **`validate_profile_preflight()` refactored** — routes through the resolver with prefix `profile.yaml: ` on errors. Populates `chain`, `provenance`, `community_template_rules` even on partial-failure so doctor output keeps producing useful context.
- **Cycle error format** — `extends/includes cycle detected: a.yaml → b.yaml → c.yaml → a.yaml` (U+2192 RIGHTWARDS ARROW), rendered root-ancestor-first ending in the duplicate.

## Test Coverage

26 new composition tests (`tests/test_profile_composition.py`) covering the CFG-02 success-criteria #1, #4 and the must-haves from PLAN.md:

- Composition order: extends single-parent, includes left-to-right, extends+includes+own-fields combined, and back-compat (no extends/includes behaves as pre-Phase-30).
- Schema typing: `extends` must be string (D-03), `includes` must be list.
- Cycle detection: direct (`a → a`), indirect (`a → b → c → a`), via includes, and the diamond (A extends B; A includes C; C extends B) NOT flagged.
- Depth cap: depth=8 succeeds, depth=9 rejected with `recursion depth exceeded 8`.
- Path security (T-30-01): absolute path rejected, `../` traversal rejected, symlink-escape rejected (skipif Win32), sibling-relative resolution honored.
- Partial fragments (D-08): a fragment without folder_mapping composes fine; resolver does NOT validate per-fragment.
- Graceful fallback through `load_profile()` for cycle/path-escape/missing-fragment, all logging `[graphify] profile error:` to stderr.
- `ResolvedProfile` shape, provenance dotted-key recording, list-leaf provenance, and `_deep_merge_with_provenance` does-not-mutate-base.

## Verification

- `pytest tests/test_profile_composition.py -q` — **26 passed**
- `pytest tests/test_profile.py -q` — **164 passed** (test_preflight_result_tuple_unpack updated to star-rest unpack pattern)
- `pytest tests/ -q` — **1721 passed, 1 xfailed** (full suite green; the xfailed is pre-existing)
- Cycle-error format runtime check: `extends/includes cycle detected: a.yaml → b.yaml → c.yaml → a.yaml` ✓
- Import smoke: `from graphify.profile import _resolve_profile_chain, _deep_merge_with_provenance, ResolvedProfile, PreflightResult` succeeds; `PreflightResult([], [], 0, 0).chain == []`, `.provenance == {}`, `.community_template_rules == []` ✓
- All Plan 01 acceptance-criteria grep checks pass (`_resolve_profile_chain`, `_deep_merge_with_provenance`, `ResolvedProfile`, `is_relative_to`, `recursion depth exceeded 8`, `cycle detected`, `frame_chain ≥ 2`, `→` arrow present, `fnmatch` import).

## Commits

| Task | Hash      | Message |
|------|-----------|---------|
| 1    | `fe46463` | test(30-01): add Wave 0 profile composition test scaffolding (RED) |
| 2    | `462a421` | feat(30-01): implement profile composition resolver (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy-import resolver symbols at top of test_profile_composition.py**
- **Found during:** Task 1 — pytest collect-only failed with `ImportError: cannot import name '_resolve_profile_chain'`
- **Issue:** The plan's acceptance criteria explicitly require `pytest --collect-only` to exit 0 (parse-clean) AND tests to fail at runtime with `ImportError`/`AttributeError`. A top-level `from graphify.profile import _resolve_profile_chain` makes collection itself fail, contradicting the parse-clean requirement. The plan also forbids `pytest.importorskip` guards.
- **Fix:** Defined module-level shim functions `_resolve_profile_chain` / `_deep_merge_with_provenance` that lazy-import from `graphify.profile` on first call. Collection succeeds (26 tests collected); each test fails with the expected ImportError once it actually invokes the symbol.
- **Files modified:** tests/test_profile_composition.py
- **Commit:** fe46463

**2. [Rule 1 - Bug] Updated test_preflight_result_tuple_unpack_backward_compat for new NamedTuple shape**
- **Found during:** Task 2 — full 4-tuple unpack `e2, w2, rc, tc = result` raised `ValueError: too many values to unpack` after `PreflightResult` gained three trailing fields.
- **Issue:** Adding fields to a NamedTuple breaks any unpack site that asserts the exact arity. The plan REQUIRES adding three new fields (acceptance criterion). The plan's "back-compat preserved via trailing defaults" comment refers to attribute access and star-rest unpacking, NOT exact-arity unpacking.
- **Fix:** Changed the full unpack to `e2, w2, rc, tc, *_ = result` and added attribute-access assertions for the three new fields. The first star-rest assertion (`errors, warnings, *_`) remains unchanged.
- **Files modified:** tests/test_profile.py (1 test)
- **Commit:** 462a421

### Architectural Changes

None — no Rule 4 deviations were necessary.

## Self-Check: PASSED

- File `graphify/profile.py` — FOUND, contains `_resolve_profile_chain`, `_deep_merge_with_provenance`, `ResolvedProfile`, extended `PreflightResult`, extended `_VALID_TOP_LEVEL_KEYS`, extended `validate_profile`, refactored `load_profile`, refactored `validate_profile_preflight`.
- File `tests/test_profile_composition.py` — FOUND (26 tests).
- All 21 fixture YAML files — FOUND under `tests/fixtures/profiles/`.
- Commit `fe46463` — FOUND in git log (Task 1 RED).
- Commit `462a421` — FOUND in git log (Task 2 GREEN).
- `pytest tests/test_profile_composition.py tests/test_profile.py -q` — 190 passed, 1 xfailed.
- `pytest tests/ -q` — 1721 passed, 1 xfailed.

## TDD Gate Compliance

The plan declared `tdd="true"` on both tasks. Gate sequence verified in git log:

1. RED gate — `fe46463 test(30-01): …` (failing tests committed first, no implementation present)
2. GREEN gate — `462a421 feat(30-01): …` (implementation lands, tests turn green)
3. REFACTOR gate — none required (implementation already clean; no refactor commit needed).

Both required TDD gate commits are present and ordered correctly.
