---
phase: 10-cross-file-semantic-extraction
plan: 01
subsystem: testing
tags: [validate, pyproject, sentence-transformers, fixtures, dedup, conftest, numpy]

# Dependency graph
requires: []
provides:
  - validate.py accepts source_file str|list[str] and optional merged_from list[str] (D-11, D-12)
  - pyproject.toml [dedup] optional extra with sentence-transformers (D-01)
  - tests/conftest.py shared fixtures: fake_encoder, tmp_corpus, dedup_config, multi_file_extraction
  - tests/test_batch.py Wave 0 stub importable by pytest
  - tests/test_dedup.py Wave 0 stub with fixture smoke tests
  - tests/fixtures/multi_file_extraction.json canonical Phase 10 test corpus
affects:
  - 10-02 (batch.py uses cluster_files; test_batch.py stubs filled in)
  - 10-03 (dedup.py uses validate_extraction; test_dedup.py stubs filled in)
  - 10-04 through 10-07 (all plans depend on conftest fixtures and multi_file fixture)

# Tech tracking
tech-stack:
  added:
    - sentence-transformers (optional dep, [dedup] extra)
    - numpy (already present as transitive dep; used explicitly in fake_encoder fixture)
  patterns:
    - TDD RED/GREEN/REFACTOR cycle within a single plan+commit
    - importorskip stubs for not-yet-created modules (test_batch.py, test_dedup.py)
    - Deterministic mock encoder using numpy default_rng with hash-based seed per label
    - tomllib/tomli try/except fallback pattern (reused from test_pyproject.py)

key-files:
  created:
    - tests/conftest.py
    - tests/test_batch.py
    - tests/test_dedup.py
    - tests/fixtures/multi_file_extraction.json
  modified:
    - graphify/validate.py (D-11/D-12 isinstance checks added after file_type block)
    - tests/test_validate.py (5 new tests appended)
    - pyproject.toml ([dedup] extra + sentence-transformers in all)
    - tests/test_pyproject.py (test_dedup_optional_extra_present appended)

key-decisions:
  - "D-11: merged_from optional list[str] field accepted by validate_extraction; bare string rejected"
  - "D-12: source_file accepts str or list[str]; int/other types and lists with non-str elements rejected"
  - "D-01: sentence-transformers declared as [dedup] optional extra following [leiden]/[obsidian] pattern"
  - "fake_encoder uses hash-based seed so same label always yields same L2-normalized 384-dim vector across calls and Python sessions"
  - "REQUIRED_NODE_FIELDS unchanged — source_file still required; D-12 type check runs only when present"

patterns-established:
  - "Wave 0 stub pattern: create test files with importorskip + fixture smoke tests before Wave 1 modules exist"
  - "Multi-file fixture pattern: canonical JSON with duplicate-candidate nodes across 5 files for Phase 10 plans"

requirements-completed: [GRAPH-02, GRAPH-03]

# Metrics
duration: 6min
completed: 2026-04-16
---

# Phase 10 Plan 01: Wave 0 Foundation — Schema Extension + Test Scaffolding Summary

**Extended validate_extraction to accept dedup provenance fields (D-11/D-12), added [dedup] sentence-transformers extra (D-01), and created conftest.py fixtures + stub test files that all 6 downstream Phase 10 plans depend on.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-16T07:08:00Z (approx)
- **Completed:** 2026-04-16T07:14:19Z
- **Tasks:** 3 completed
- **Files modified:** 8 total (4 created, 4 modified)

## Accomplishments
- validate_extraction now accepts D-11 `merged_from: list[str]` and D-12 `source_file: list[str]` without changes to REQUIRED_NODE_FIELDS (back-compat preserved)
- [dedup] optional extra added to pyproject.toml following the [leiden]/[obsidian] precedent; sentence-transformers added to `all` bundle
- Wave 0 test scaffolding in place: conftest.py (4 fixtures), test_batch.py (importorskip stub), test_dedup.py (2 smoke tests + importorskip), multi_file_extraction.json (7 nodes, 6 edges, AuthService duplicate candidates)

## Task Commits

1. **Task 1: Extend validate.py schema (D-11, D-12) + tests** - `7749dac` (test/feat — TDD)
2. **Task 2: Add [dedup] optional extra to pyproject.toml** - `2254d83` (feat)
3. **Task 3: Create shared conftest.py fixtures + test stubs + multi-file fixture** - `9d390bb` (feat)

## Files Created/Modified

- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/validate.py` — D-11/D-12 isinstance checks added inside the node-validation loop after file_type check; D-12 checks `isinstance(sf, (str, list))` then `all(isinstance(s, str) for s in sf)`; D-11 checks `isinstance(mf, list) and all(isinstance(m, str) for m in mf)`
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_validate.py` — 5 tests appended: test_source_file_as_list, test_merged_from_accepted, test_source_file_invalid_type, test_source_file_list_with_non_string, test_merged_from_not_list
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/pyproject.toml` — `dedup = ["sentence-transformers"]` added after `obsidian`; `all` updated to include `"sentence-transformers"`
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_pyproject.py` — test_dedup_optional_extra_present appended; reused existing `_load_pyproject()` helper and tomllib/tomli try/except pattern
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/conftest.py` — **CREATED**: fake_encoder, tmp_corpus, dedup_config, multi_file_extraction fixtures
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_batch.py` — **CREATED**: Wave 0 stub with importorskip for graphify.batch
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_dedup.py` — **CREATED**: Wave 0 stub with importorskip for graphify.dedup + 2 fixture smoke tests
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/fixtures/multi_file_extraction.json` — **CREATED**: 7 nodes (AuthService x2, auth_service, Authentication Service, AuthService test, UserProfile, login_handler, api_router), 6 edges (4 structural + 2 import edges); SHA256: 296e32f571fbf58be4c10c3491ef172ad40346805543a19d7e71c2d951b8dc05; 1704 bytes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed f-string quote mismatch in source_file error message**
- **Found during:** Task 1 GREEN phase
- **Issue:** The error message template used `'source_file' list must contain only strings` (with surrounding single quotes from the f-string), but the test expected the substring `source_file list must contain only strings` (without quotes). Python's `in` substring check failed.
- **Fix:** Removed the surrounding `'...'` quotes from the f-string: `f"...source_file list must contain only strings"` instead of `f"...'source_file' list must contain only strings"`.
- **Files modified:** `graphify/validate.py`
- **Commit:** 7749dac (included in same TDD commit)

## Known Stubs

- `tests/test_batch.py::test_batch_module_importable` — skipped via importorskip until plan 10-02 creates graphify/batch.py
- `tests/test_dedup.py::test_dedup_module_importable` — skipped via importorskip until plan 10-03 creates graphify/dedup.py
- These are intentional Wave 0 scaffolding stubs. Plans 10-02 and 10-03 will fill in the real test bodies.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. validate.py changes are schema-tightening (additive validation). pyproject.toml change is a packaging declaration only. No threat flags.

## Self-Check: PASSED

Files exist:
- FOUND: graphify/validate.py
- FOUND: tests/test_validate.py
- FOUND: pyproject.toml
- FOUND: tests/conftest.py
- FOUND: tests/test_batch.py
- FOUND: tests/test_dedup.py
- FOUND: tests/fixtures/multi_file_extraction.json

Commits exist:
- FOUND: 7749dac (test(10-01): add failing validate tests for D-11/D-12 dedup provenance fields)
- FOUND: 2254d83 (feat(10-01): add [dedup] optional extra to pyproject.toml (D-01))
- FOUND: 9d390bb (feat(10-01): create Phase 10 test scaffolding — conftest fixtures, stubs, multi-file fixture)
