---
phase: 05-integration-cli
plan: "04"
subsystem: tests
tags: [integration-tests, migration, MRG-03, MRG-05, FIX-01, FIX-02, FIX-03, OBS-01, OBS-02, D-74]
dependency_graph:
  requires:
    - 05-03 (refactored to_obsidian with MergeResult/MergePlan return types)
    - 05-01 (split_rendered_note, MergeResult/MergePlan dataclasses)
    - graphify/profile.py (safe_tag, _DEFAULT_PROFILE)
  provides:
    - tests/test_integration.py (9-test Phase 5 pipeline coverage suite)
    - OBS-01/OBS-02 regression anchor in tests/test_profile.py
  affects:
    - tests/test_export.py (5 obsolete functions removed)
    - tests/test_pipeline.py (Step 9 updated to MergeResult assertion)
tech_stack:
  added: []
  patterns:
    - pytest tmp_path fixture for filesystem isolation
    - Sparse summary dict assertion (sum of values > 0, not key presence)
    - Idempotent re-run assertion via skipped_identical count
key_files:
  created:
    - tests/test_integration.py
  modified:
    - tests/test_export.py
    - tests/test_pipeline.py
    - tests/test_profile.py
decisions:
  - "MergeResult.plan.summary is sparse (zero-count keys omitted) — assertions use .get(key, 0) or sum(values) not key membership"
  - "test_pipeline_incremental_update uses sum(summary.values()) > 0 to cover both first-run CREATE and re-run UPDATE scenarios"
  - "to_canvas removed from test_export.py imports alongside to_obsidian (was imported but unused)"
metrics:
  duration: "6m"
  completed: "2026-04-11T21:05:00Z"
  tasks_completed: 3
  files_modified: 4
---

# Phase 05 Plan 04: Test Migration — to_obsidian Pipeline Coverage Summary

**One-liner:** Migrated 5 legacy flat-vault tests from test_export.py into a new 9-test test_integration.py asserting on MergeResult/MergePlan shapes and Atlas/-prefixed paths; updated test_pipeline.py Step 9 to the new return type; added OBS-01/OBS-02 safe_tag regression anchor to test_profile.py.

## What Was Built

### tests/test_integration.py (new, 225 lines)

Full Phase 5 pipeline integration test suite replacing the deleted `test_to_obsidian_*` functions. Tests use `tmp_path` pytest fixture (no `tempfile.TemporaryDirectory`), `_minimal_graph()` helper producing a 4-node 2-community graph, and `_make_graph()` for custom topologies.

**9 tests:**

| Test | Invariant | Requirement |
|------|-----------|-------------|
| `test_to_obsidian_default_profile_returns_merge_result` | Returns `MergeResult`, plan has CREATE > 0 | MRG-05 |
| `test_to_obsidian_default_profile_writes_atlas_layout` | Atlas/Dots/Things or Atlas/Maps directory exists | MRG-05, D-74 |
| `test_to_obsidian_dry_run_returns_plan` | Returns `MergePlan`, summary has CREATE > 0 | MRG-03 |
| `test_to_obsidian_dry_run_writes_zero_md_files` | No .md files written on dry_run | MRG-03 |
| `test_fix01_frontmatter_special_chars_quoted` | source_file with colon is double-quoted | FIX-01 |
| `test_fix02_dedup_deterministic_across_runs` | Two runs produce identical relative file paths | FIX-02 |
| `test_fix03_community_tag_sanitization` | community/ tag slugs contain no / + or spaces | FIX-03 |
| `test_merge_result_shape_after_normal_run` | All summary keys are valid; total_actions > 0 | MRG-05 |
| `test_re_run_is_idempotent` | Second run has skipped_identical > 0 | Phase 4 content-hash skip |

### tests/test_export.py (pruned)

Deleted 5 functions and the `_make_small_graph` helper:
- `test_to_obsidian_frontmatter_special_chars` (FIX-01, migrated)
- `test_to_obsidian_dedup_deterministic` (FIX-02, migrated)
- `test_to_obsidian_tag_sanitization` (FIX-03, migrated)
- `test_graph_json_tag_syntax` (OBS-01, coverage via safe_tag tests)
- `test_graph_json_preserves_user_settings` (OBS-02, coverage via safe_tag tests)

Removed orphaned imports: `to_obsidian`, `to_canvas` from the import line.

### tests/test_pipeline.py (updated)

Step 9 (Obsidian export) replaced:
- **Before:** `n_notes = to_obsidian(...)` + `assert n_notes > 0` + `assert graph.json exists` + `vault.glob("*.md")`
- **After:** `result = to_obsidian(...)` + `isinstance(result, MergeResult)` + `sum(summary.values()) > 0` + `vault.rglob("*.md")`

The `rglob` (recursive) replaces `glob` to match Atlas/-shaped subdirectory layout. The graph.json assertion is removed with an explanatory comment pointing to the safe_tag tests.

### tests/test_profile.py (regression anchor added)

One new test `test_obs01_obs02_safe_tag_regression_anchor` inserted after `test_safe_tag_slashes_and_plus`. Contains docstring explaining Phase 5 D-74 decision, with explicit OBS-01/OBS-02 search anchors. Asserts the `tag:community/<slug>` literal form that graph.json used to emit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MergeResult.plan.summary is a sparse dict**
- **Found during:** Task 1, first test run — `test_merge_result_shape_after_normal_run` failed with `AssertionError: Missing UPDATE in summary: {'CREATE': 6}`
- **Issue:** The plan's prescribed assertion `assert key in result.plan.summary` assumed all 6 keys are always present. The actual implementation only includes keys with non-zero counts.
- **Fix:** Changed to validate the key set is a subset of valid keys (no unexpected keys) + `sum(values) > 0` instead of per-key presence check.
- **Files modified:** tests/test_integration.py
- **Commit:** 4485725

**2. [Rule 1 - Bug] test_pipeline_incremental_update: CREATE assertion fails on re-run**
- **Found during:** Task 2, running tests/test_pipeline.py — `test_pipeline_incremental_update` calls `run_pipeline` twice on the same `tmp_path`, so the second call finds existing files and produces UPDATE not CREATE.
- **Issue:** Plan prescribed `assert result.plan.summary.get("CREATE", 0) > 0` which is always false on the second run.
- **Fix:** Changed to `sum(result.plan.summary.values()) > 0` — accepts both CREATE (first run) and UPDATE (re-run).
- **Files modified:** tests/test_pipeline.py
- **Commit:** 0ac925a

## Known Stubs

None — all tests are fully implemented with real assertions against actual pipeline output.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Test files only — no production code modified. No threat flags.

## Self-Check: PASSED

- tests/test_integration.py: FOUND (225 lines)
- tests/test_export.py: `def test_to_obsidian_frontmatter_special_chars` ABSENT — CONFIRMED
- tests/test_export.py: `def test_graph_json_tag_syntax` ABSENT — CONFIRMED
- tests/test_pipeline.py: `isinstance(result, MergeResult)` PRESENT — CONFIRMED
- tests/test_pipeline.py: `n_notes = to_obsidian` ABSENT — CONFIRMED
- tests/test_profile.py: `def test_obs01_obs02_safe_tag_regression_anchor` PRESENT — CONFIRMED
- commit 4485725: FOUND
- commit 0ac925a: FOUND
- commit 0c5a0e4: FOUND
- 862 tests passing: CONFIRMED
