---
phase: 69
plan: "02"
subsystem: vault_promote
tags: [profile-driven, folder-routing, tdd, regression-fix]
dependency_graph:
  requires: [69-01]
  provides: [_resolve_folder_prefix, _BUCKET_TO_PROFILE_KEY, profile-driven folder routing]
  affects: [graphify/vault_promote.py, tests/test_vault_promote.py]
tech_stack:
  added: []
  patterns: [profile-driven routing via _DEFAULT_PROFILE fallback, D-04 unknown-type stderr breadcrumb]
key_files:
  modified:
    - graphify/vault_promote.py
    - tests/test_vault_promote.py
decisions:
  - "_BUCKET_TO_PROFILE_KEY maps plural bucket keys (things/questions/maps/people/quotes/statements/sources) to singular profile keys per D-01"
  - "_resolve_folder_prefix lookup order: merged_profile graphify_folder_mapping -> _DEFAULT_PROFILE fallback -> D-04 Atlas/Sources/Graphify/<Type>/ with stderr INFO"
  - "3 existing tests updated to reference new Atlas/Sources/Graphify/ subtree (Rule 1 auto-fix: tests encoded old literal paths)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-05"
requirements: [VPROF-02]
---

# Phase 69 Plan 02: Profile-Driven Folder Resolution Summary

Replaced hardcoded `_FOLDER_PATH_PREFIX` dict and per-record `"folder": "Atlas/..."` literals in `vault_promote.py` with profile-driven resolution via `_resolve_folder_prefix(bucket_key, merged_profile)`. Community MOC notes now land at `Atlas/Sources/Graphify/Maps/` (not `Atlas/Maps/`) when using the default profile.

## What Was Built

### Removed Symbols

| Symbol | Location | Lines (approx) | Reason |
|--------|----------|-----------------|--------|
| `_FOLDER_PATH_PREFIX` | `vault_promote.py` | 872-880 | Replaced by `_resolve_folder_prefix()` |
| 7 `"folder": "Atlas/..."` literals | `classify_nodes()` | 206, 219, 231, 249, 267, 283, 299 | Replaced by `_resolve_folder_prefix()` calls |

### Added Symbols

**`_BUCKET_TO_PROFILE_KEY`** (module-level dict, `vault_promote.py`)

| Plural bucket key | Singular profile key |
|-------------------|---------------------|
| `things` | `thing` |
| `questions` | `question` |
| `maps` | `map` |
| `people` | `person` |
| `quotes` | `quote` |
| `statements` | `statement` |
| `sources` | `source` |

**`_resolve_folder_prefix(bucket_key: str, merged_profile: dict) -> str`**

Lookup order:
1. `merged_profile["graphify_folder_mapping"][profile_key]` — user override
2. `_DEFAULT_PROFILE["graphify_folder_mapping"][profile_key]` — built-in default
3. D-04 fallback: `Atlas/Sources/Graphify/<BucketKey.capitalize()>` with stderr `[graphify] profile: unknown record type` INFO line

### `promote()` changes

- `promoted_counts` initialized from `_BUCKET_TO_PROFILE_KEY` (was `_FOLDER_PATH_PREFIX`)
- `prefix = _resolve_folder_prefix(bucket_key, merged_profile)` (was `_FOLDER_PATH_PREFIX[bucket_key]`)

### `classify_nodes()` changes

All 7 bucket record types now call `_resolve_folder_prefix(<bucket_plural>, profile)` for the `folder` field. The `profile` parameter was already threaded through; no signature change needed.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | dcb9f39 | test(69-02): add failing tests — all 4 failed as expected |
| GREEN (feat) | 0588f1f | feat(69-02): profile-driven folder resolution — all 4 pass |

## Test Count

- 4 new tests in `tests/test_vault_promote.py`:
  - `test_profile_folder_routing` — custom mapping overrides default
  - `test_unknown_type_fallback` — D-04 fallback path + stderr breadcrumb
  - `test_end_to_end_all_seven_folders` — updated; asserts `Atlas/Sources/Graphify/<Type>/` paths
  - `test_no_hardcoded_atlas_literals` — negative grep for `_FOLDER_PATH_PREFIX`, `"Atlas/Maps"`, `"Atlas/Dots/"`
- Full `tests/test_vault_promote.py`: 32 passed (no regressions)
- `tests/test_migration.py::test_preview_expands_risky_action_rows` — pre-existing failure, unrelated to this plan (confirmed via git stash)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED test `test_profile_folder_routing` needed `source_file` on nodes**
- **Found during:** Task 1 → Task 2 (test debugging)
- **Issue:** Test nodes lacked `source_file` attribute with file extension; `_is_concept_node()` returned True for them, so `god_nodes()` excluded them, producing empty `things` bucket.
- **Fix:** Added `"source_file": "ideas.md"` to nodes and peers in the test fixture.
- **Files modified:** `tests/test_vault_promote.py`

**2. [Rule 1 - Bug] 3 existing tests used old hardcoded Atlas paths**
- **Found during:** Task 2 full suite run
- **Issue:** `test_vault01_cli_does_not_overwrite_foreign`, `test_multi_run_preserves_foreign_file`, `test_multi_run_preserves_user_edit` all referenced `Atlas/Maps` or `Atlas/Dots/Things` paths that no longer exist under the new profile-driven routing.
- **Fix:** Updated path references to `Atlas/Sources/Graphify/Maps` and `Atlas/Sources/Graphify/Things`.
- **Files modified:** `tests/test_vault_promote.py`

## Known Stubs

None — all 7 bucket types route to real profile-driven paths; no placeholder or hardcoded fallback stubs remain in production code paths.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. File writes still go through existing `write_note()` path with manifest guard.

## Self-Check: PASSED

- `graphify/vault_promote.py` — modified and committed at 0588f1f
- `tests/test_vault_promote.py` — modified and committed at dcb9f39 (RED), 0588f1f (GREEN)
- `grep -c "_FOLDER_PATH_PREFIX" graphify/vault_promote.py` = 0
- `grep -c "def _resolve_folder_prefix" graphify/vault_promote.py` = 1
- `grep -c "_BUCKET_TO_PROFILE_KEY" graphify/vault_promote.py` = 3
- `grep -c "Atlas/Sources/Graphify" tests/test_vault_promote.py` = 13
- `pytest tests/test_vault_promote.py -q` = 32 passed
