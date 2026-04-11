---
phase: 04-merge-engine
plan: 02
subsystem: profile
tags: [profile, merge-config, validation, field-policies, phase-4]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "_DEFAULT_PROFILE + validate_profile accumulator pattern + _VALID_MERGE_STRATEGIES"
  - phase: 02-template-engine
    provides: "created: frontmatter field (D-27) set once at first CREATE"
provides:
  - "_DEFAULT_PROFILE.merge extended to {strategy, preserve_fields[+created], field_policies{}}"
  - "_VALID_FIELD_POLICY_MODES constant = frozenset({replace, union, preserve})"
  - "validate_profile coverage of merge.field_policies (non-dict, non-string key, invalid mode)"
affects:
  - 04-03-merge-module  # Plan 03 deep-merges _DEFAULT_FIELD_POLICIES with profile.merge.field_policies
  - 04-merge-engine     # All subsequent merge plans rely on the preserve_fields + field_policies shape
  - 05-integration      # CLI --validate-profile surfaces these errors to users

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mode-vocabulary constant co-located with _VALID_MERGE_STRATEGIES (mirrors existing pattern)"
    - "Accumulator-style validation (list[str], never raises) extended branch-by-branch"
    - "Deep-merge-friendly defaults: empty {} means 'no overrides, downstream table wins'"

key-files:
  created: []
  modified:
    - graphify/profile.py
    - tests/test_profile.py

key-decisions:
  - "field_policies default is an empty dict — Plan 03's built-in _DEFAULT_FIELD_POLICIES table wins unchanged until users opt in"
  - "Non-string field_policies keys skip further validation (continue) to avoid double-reporting on one bad entry"
  - "preserve_fields order is locked: ['rank', 'mapState', 'tags', 'created'] — 'created' appended, existing order preserved"
  - "_VALID_FIELD_POLICY_MODES is a frozenset (immutable, hashable) placed adjacent to _VALID_MERGE_STRATEGIES"

patterns-established:
  - "Policy-table-as-profile-override: downstream modules own a default policy dict; profile.merge.{section} deep-merges overrides"
  - "Validation error messages include the exact sorted(_VALID_*) set for user-actionable feedback"

requirements-completed: [MRG-02, MRG-07]

# Metrics
duration: 15min
completed: 2026-04-11
---

# Phase 4 Plan 02: Merge Config Contract Summary

**Profile merge section ships the Phase 4 contract: `created` preserved across UPDATE runs, optional `field_policies` override surface, and validator branches that reject non-dict / non-string-key / invalid-mode entries.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-11T12:38:00Z (approximate)
- **Completed:** 2026-04-11T12:53:23Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 2 (`graphify/profile.py`, `tests/test_profile.py`)
- **Tests added:** 13 (6 for _DEFAULT_PROFILE shape + 7 for validator branches)
- **Tests passing:** 102 / 102 in `tests/test_profile.py`

## Accomplishments

- `_DEFAULT_PROFILE.merge.preserve_fields` extended from `["rank", "mapState", "tags"]` to `["rank", "mapState", "tags", "created"]` — satisfies D-27 + D-65 so that `created:` frontmatter set once at first CREATE is never overwritten on UPDATE
- `_DEFAULT_PROFILE.merge.field_policies` added as an empty-dict default — downstream Plan 03's `_DEFAULT_FIELD_POLICIES` table wins until users opt in via `profile.merge.field_policies: {<field>: <mode>}`
- `_VALID_FIELD_POLICY_MODES: frozenset[str] = frozenset({"replace", "union", "preserve"})` constant declared adjacent to `_VALID_MERGE_STRATEGIES`, documenting the Phase 4 D-64 per-key policy vocabulary
- `validate_profile` gained three new error branches inside the `merge` block:
  1. `'merge.field_policies' must be a mapping (dict) of field-name -> policy-mode`
  2. `merge.field_policies key {k!r} must be a string (got {type})`
  3. `merge.field_policies.{key} has invalid mode {v!r} — valid modes are: {sorted}`
- All three existing merge strategies (`update`, `skip`, `replace`) continue to validate (regression test added)

## Task Commits

Each task followed RED → GREEN TDD:

1. **Task 1 (RED) + Task 2 (RED): failing tests** — `4874bfb` (`test(04-02): add failing tests for merge.field_policies defaults and validation`)
2. **Task 1 (GREEN): extend _DEFAULT_PROFILE.merge + add _VALID_FIELD_POLICY_MODES** — `6fa0833` (`feat(04-02): extend _DEFAULT_PROFILE.merge with created + field_policies`)
3. **Task 2 (GREEN): validate merge.field_policies in validate_profile** — `ffd4bae` (`feat(04-02): validate merge.field_policies in validate_profile`)

_Note: TDD RED was combined across both tasks in a single commit because Tasks 1 and 2 share the same test file and the test batch is self-consistent — Task 1 tests started failing immediately, Task 2 tests started passing once Task 1 landed (empty field_policies + valid strategies already returned `[]`), and the remaining 3 failures drove Task 2 GREEN._

## Files Created/Modified

- `graphify/profile.py` — modified:
  - New constant `_VALID_FIELD_POLICY_MODES` (frozenset) after `_VALID_MERGE_STRATEGIES` (L49)
  - `_DEFAULT_PROFILE["merge"]` extended with `"created"` appended to `preserve_fields` and a new `"field_policies": {}` key
  - `validate_profile` gained a `field_policies` validation block inside the existing `merge` branch (non-dict guard, non-string-key guard, invalid-mode guard, accumulator pattern preserved)
- `tests/test_profile.py` — modified:
  - 13 new tests under two section banners: "_DEFAULT_PROFILE.merge extension + _VALID_FIELD_POLICY_MODES" and "merge.field_policies validation"
  - Coverage: existence + exact order of new preserve_fields, empty field_policies default, constant value, `load_profile` regression (no-profile vault), deep-merge override path, all six validator branches, all three merge strategies

## Decisions Made

- **Combined RED commit for Tasks 1 + 2.** Both tasks modify the same test file and the 13 tests are self-consistent; splitting the RED commit would have left tests/test_profile.py in a partially-populated intermediate state. Green commits are still split per task for clear commit history.
- **field_policies key type guard uses `continue`.** When a non-string key is found, we emit the type error and skip the mode check for that entry. Rationale: reporting both "key is not a string" and "mode is invalid" for the same bad entry would be noisy and the root cause is the key, not the value.
- **No semantic validation of `fp_key` against a whitelist.** Users can name any frontmatter key — `priority`, `author`, user-defined fields. Validation is intentionally scoped to the type + mode-set membership, per plan guardrails.

## Deviations from Plan

None — plan executed exactly as written. The `action` blocks in the plan were followed verbatim; test wording matches the `<behavior>` specifications.

## Issues Encountered

- None during Task 1 + Task 2 execution.
- Two pre-existing unrelated test failures surfaced when running the full suite:
  - `tests/test_detect.py::test_detect_skips_dotfiles`
  - `tests/test_extract.py::test_collect_files_from_dir`
  - Both fail on `HEAD` before any 04-02 changes (verified via `git stash && pytest -q`). Out-of-scope per the SCOPE BOUNDARY rule; logged to `.planning/phases/04-merge-engine/deferred-items.md`.

## Deferred Issues

Pre-existing failures in `test_detect.py` and `test_extract.py` — see `.planning/phases/04-merge-engine/deferred-items.md`.

## Threat Model Coverage

Mitigated during this plan:

- **T-04-05 (Elevation of Privilege — unknown mode silently reinterpreted)** — `validate_profile` rejects invalid modes with actionable errors. `load_profile` falls back to defaults on validation errors (existing L120-124 behavior), so a malformed `field_policies` cannot degrade merge to an unknown mode at runtime.
- **T-04-06 (Information Disclosure — non-string key crashes downstream dispatcher)** — `validate_profile` rejects non-string keys before the profile is returned to callers. Plan 03's dispatcher will never see a non-string key under this validation regime.

Accepted (documented only):

- **T-04-04 (Tampering — user-friendly field_policies override of graphify-owned key)** — Trust model per plan: user-local config equivalent to CLI flags. Documented in Plan 03's policy dispatcher.
- **T-04-07 (Denial of Service — enormous field_policies dict)** — No cap in v1. Dispatch in Plan 03 is O(1) hash lookup per key.

## Next Phase / Plan Readiness

- **Plan 04-03 (merge module)** can now import `_DEFAULT_PROFILE["merge"]["field_policies"]` and deep-merge its own `_DEFAULT_FIELD_POLICIES` table against it. The expected shape is guaranteed by `validate_profile` at load time.
- **Plan 04-05 / 04-06 (apply + report)** can rely on `created` being in the default preserve list — no need to special-case `created` at the dispatcher level.
- No blockers introduced. No downstream contracts changed beyond the explicit additions.

## Self-Check: PASSED

Verification commands run and their outputs:

- `pytest tests/test_profile.py -q` → `102 passed`
- `pytest tests/test_profile.py -k field_polic -q` → `10 passed, 92 deselected`
- `pytest tests/test_profile.py -k all_three_merge_strategies -q` → `1 passed, 101 deselected`
- `python -c "from graphify.profile import _DEFAULT_PROFILE, _VALID_FIELD_POLICY_MODES; assert _DEFAULT_PROFILE['merge']['preserve_fields'] == ['rank', 'mapState', 'tags', 'created']; assert _DEFAULT_PROFILE['merge']['field_policies'] == {}; assert _VALID_FIELD_POLICY_MODES == frozenset({'replace', 'union', 'preserve'}); assert _DEFAULT_PROFILE['merge']['preserve_fields'].index('created') == 3; print('OK')"` → `OK`
- Commit hashes verified in `git log --oneline`:
  - `4874bfb` FOUND (RED tests)
  - `6fa0833` FOUND (Task 1 GREEN)
  - `ffd4bae` FOUND (Task 2 GREEN)
- Files verified present:
  - `graphify/profile.py` FOUND
  - `tests/test_profile.py` FOUND

---
*Phase: 04-merge-engine*
*Plan: 02*
*Completed: 2026-04-11*
