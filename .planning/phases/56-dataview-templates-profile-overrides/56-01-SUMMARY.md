---
phase: 56
plan: 01
subsystem: profile-composition
tags: [provenance, profile-merge, CFG-02, foundation]
requires: []
provides:
  - "provenance: dict[str, list[Path]] shape across PreflightResult, ResolvedProfile, _deep_merge_with_provenance, _resolve_profile_chain, validate_profile_preflight"
  - "merge-order invariant: paths list ordered extends-parents → includes → own"
  - "current-writer convention: paths[-1]"
affects:
  - graphify/profile.py
  - graphify/__main__.py
  - tests/test_profile.py
  - tests/test_profile_composition.py
tech-stack:
  added: []
  patterns:
    - "setdefault([]).append(...) accumulator instead of scalar overwrite"
    - "current-writer = paths[-1] (last entry wins)"
key-files:
  created: []
  modified:
    - graphify/profile.py
    - graphify/__main__.py
    - tests/test_profile.py
    - tests/test_profile_composition.py
decisions:
  - "Provenance leaf is dict[str, list[Path]] — single-writer leaves are still lists of length 1, never bare Path. Consumers always see list shape (no isinstance branching)."
  - "Merge order = list order: extends-parents first, includes next, own last. paths[-1] is always the winning writer."
  - "CLI rendering (graphify validate-profile) shows paths[-1] for the 'field ← file.yaml' line — preserves current visible output."
metrics:
  duration: "~12 min"
  completed: 2026-05-02
---

# Phase 56 Plan 01: Provenance List-Shape Foundation — Summary

One-liner: Switched `provenance` from `dict[str, Path]` (last-writer-wins scalar) to `dict[str, list[Path]]` (full contributor history per leaf), unblocking Plan 02's CFG-02 §4 cross-chain collision detector.

## What Was Built

A pure data-shape change that thread `dict[str, list[Path]]` through every site that produces or consumes the provenance map in `graphify/profile.py`, plus a single reader update in `graphify/__main__.py` to keep CLI output identical.

### Five Edit Sites in `graphify/profile.py`

1. **`PreflightResult.provenance`** (line 35) — `dict[str, Path] = {}` → `dict[str, list[Path]] = {}` (NamedTuple default; mutable default acceptable here per existing pattern).
2. **`ResolvedProfile.provenance`** (line 56) — type annotation only; NamedTuple has no defaults.
3. **`_deep_merge_with_provenance` signature** (line 251) — parameter type updated.
4. **`_deep_merge_with_provenance` body** (line 274) — `provenance[dotted] = source_path` → `provenance.setdefault(dotted, []).append(source_path)`. The single-line behavioral change.
5. **Initialization sites** (lines 392 and 1479) — both local `provenance: dict[str, Path] = {}` initializers updated.

### Reader Updates

- **`graphify/__main__.py`** validate-profile output (lines 1523–1532): now reads `paths = result.provenance[dotted]; src = paths[-1]` so the `field ← file.yaml` line continues to print the winning source. Preserves the visible CLI contract.
- **`tests/test_profile_composition.py::test_provenance_records_dotted_keys`**: amended to assert `list[Path]` shape and use `paths[-1]` for current-writer assertions.

### New Tests in `tests/test_profile.py`

1. **`test_dataview_queries_provenance_in_validate_profile_output`** (amended): in addition to the existing CLI-output assertions, now also calls `_resolve_profile_chain` directly to assert `provenance["dataview_queries.moc"]` is a single-element `list[Path]` pointing at `profile.yaml`.
2. **`test_provenance_accumulates_across_extends_chain`** (new): 4-file extends/includes chain (`seed.yaml` → `grandparent.yaml` → `parent.yaml` → `profile.yaml`) all writing `dataview_queries.code`. Asserts `len(sources) == 3` and order = `[grandparent.yaml, parent.yaml, profile.yaml]`. The `seed.yaml` is required so `dataview_queries` exists as a dict before `grandparent`'s write — this triggers per-leaf recursion in every subsequent merge step (see merge-order note below).
3. **`test_provenance_single_source_remains_single_element`** (new): 3-file chain proves a leaf written by only one source still surfaces as a length-1 list, never a bare `Path`.

## Merge-Order Invariant

The `paths` list is ordered by merge call sequence in `_resolve_profile_chain` (`graphify/profile.py:464–491`):

1. **extends-parents first** — parent (and recursively grandparent) merges feed into `composed` before any other source.
2. **includes next** — left-to-right in declaration order.
3. **own last** — current file's data is applied LAST, so it always wins.

Therefore: **`paths[-1]` is the winning source** for any leaf. This is the contract Plan 02 will rely on when building the cross-chain collision detector (any leaf with `len(paths) > 1` is a candidate for collision reporting).

### Recursion Caveat (documented for Plan 02)

Per-leaf provenance is recorded only when `_deep_merge_with_provenance` *recurses* into a sub-dict — i.e., when both sides of a merge are dicts at the parent key. If a parent key is introduced for the first time by some merge call, that whole sub-dict is recorded as one leaf (`provenance[parent_key]`), not per-child. Plan 02's collision detector will need to iterate `provenance` for `dataview_queries.<note_type>` keys *and* check `provenance.get("dataview_queries")` whole-leaf entries to enumerate all contributors fairly. (Out of scope for Plan 01.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test alignment] `test_provenance_accumulates_across_extends_chain` chain depth**
- **Found during:** Task 2 (GREEN run)
- **Issue:** Plan literal text said "3-deep extends chain" producing 3 contributors, but per-leaf recursion only fires when `dataview_queries` already exists as a dict in `composed`. With grandparent being the first to introduce `dataview_queries`, its write is recorded as the whole-dict leaf (`provenance["dataview_queries"]`), not as `dataview_queries.code` — yielding only 2 (parent + child) per-leaf entries.
- **Fix:** Added a 4th file `seed.yaml` (pulled in via grandparent's `includes`) that pre-establishes `dataview_queries` as a dict. Now grandparent's `code` write recurses → recorded → 3 contributors as the spec intended.
- **Files modified:** tests/test_profile.py
- **Commit:** 369ffbc

**2. [Rule 1 - Test alignment] `test_provenance_single_source_remains_single_element` chain depth**
- **Found during:** Task 1 (RED run)
- **Issue:** Same recursion caveat — single-file profile records the WHOLE `dataview_queries` dict as one leaf, so `provenance["dataview_queries.thing"]` never exists.
- **Fix:** Switched to a 3-file chain (`grand.yaml` → `mid.yaml` → `profile.yaml`) where `mid.yaml` is the single writer of `community` (recursion is triggered because grandparent already established `dataview_queries` as a dict).
- **Files modified:** tests/test_profile.py
- **Commit:** cbd6999 (RED)

**3. [Rule 1 - Bug] CLI consumer in `__main__.py:1527` would crash on list shape**
- **Found during:** Task 2 audit
- **Issue:** `print(f"  {dotted:40s} ← {_rel(src)}")` would print `[PosixPath(...)]` instead of a single path; `_rel` would either error or print the list repr.
- **Fix:** Read `paths[-1]` per the merge-order invariant — preserves identical visible CLI output ("current writer" semantics). Documented inline.
- **Files modified:** graphify/__main__.py
- **Commit:** 369ffbc

**4. [Rule 1 - Bug] Reader regression in `tests/test_profile_composition.py::test_provenance_records_dotted_keys`**
- **Found during:** Full-suite verify after Task 2
- **Issue:** Test asserted `str(src_thing).endswith("bases/fusion.yaml")` against a list, so it failed.
- **Fix:** Updated to assert `list[Path]` shape and index `[-1]` per the new contract.
- **Files modified:** tests/test_profile_composition.py
- **Commit:** 369ffbc

## Verification

- `pytest tests/test_profile.py -q` → 100% green (all provenance tests pass).
- `pytest tests/ -q` → **2036 passed, 1 xfailed** (no regressions).
- `grep -c "dict\[str, list\[Path\]\]" graphify/profile.py` → 5 (≥ 4 required).
- `grep -c "provenance.setdefault(dotted, \[\]).append(source_path)" graphify/profile.py` → 1.
- `grep -c "provenance\[dotted\] = source_path" graphify/profile.py` → 0 (old scalar writer removed).

## Commits

- `cbd6999` — `test(56-01): RED — provenance list-shape tests`
- `369ffbc` — `feat(56-01): GREEN — provenance dict[str, list[Path]] for cross-chain collision detection`

## TDD Gate Compliance

RED commit (`cbd6999` — `test(56-01)`) precedes GREEN commit (`369ffbc` — `feat(56-01)`). No REFACTOR commit needed (production change is a single-line behavioral substitution; no follow-up cleanup). Gate sequence verified.

## Self-Check: PASSED

- `graphify/profile.py` — modified (5 edit sites verified by grep).
- `graphify/__main__.py` — modified (line 1527 reader updated).
- `tests/test_profile.py` — modified (3 tests assert list shape).
- `tests/test_profile_composition.py` — modified (1 test updated for list shape).
- Commits `cbd6999` and `369ffbc` present in `git log`.
