---
phase: 04-merge-engine
plan: 06
subsystem: merge
tags: [merge, tests, coverage, must-haves, phase-4, tdd]

# Dependency graph
requires:
  - phase: 04-05
    provides: "apply_merge_plan + atomic writes + MergeResult — exercised end-to-end in every M* test"
  - phase: 04-04
    provides: "compute_merge_plan pure function — exercised end-to-end in every M* test"
  - phase: 04-03
    provides: "merge.py primitives: _parse_frontmatter, _parse_sentinel_blocks, MergeAction/MergePlan/MergeResult"
provides:
  - "tests/test_merge.py: TestPhase4MustHaves section — 11 end-to-end tests covering M1..M10 + T-04-01"
  - "tests/test_merge.py: phase-4 must_have traceability comment block (M1..M10 → requirement IDs)"
  - "Phase 4 audit evidence: every ROADMAP success criterion has a dedicated named test"
affects:
  - 05-integration  # Phase 5 can wire to_obsidian with confidence — all must_haves have green tests

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "End-to-end TDD: tests cover compute + apply round-trip against real vault fixture copies in tmp_path"
    - "Traceability matrix comment block: M1..M10 → requirement IDs greppable for future maintainers"
    - "Content-hash skip idempotence assertion: mtime unchanged on second apply run"
    - "D-68 deletion contract: stripped sentinel block not re-inserted even when rendered note includes it"
    - "T-04-01 security assertion: malicious label in wikilink alias does not break sentinel pairing"

key-files:
  created: []
  modified:
    - tests/test_merge.py

key-decisions:
  - "Traceability block added as comment (not runnable assertion) for M1..M10 greppability"
  - "M7 test asserts conflict_kind field only — compute_merge_plan does not emit stderr warnings (future enhancement)"
  - "Verification script regex discrepancy: plan spec used ^def test_ (misses class methods); actual count is 85 total test functions vs plan's >=50 threshold — threshold is satisfied"

patterns-established:
  - "_copy_vault_fixture(name, tmp_path) + _rendered_note_matching_pristine(vault) helpers reused across all must_have tests"
  - "Every M* test asserts action type before calling apply — ensures compute result is deterministic"
  - "M4 locked assertion: exactly 1 line differs in git-diff-style comparison after minimal UPDATE"

requirements-completed: [MRG-01, MRG-02, MRG-06, MRG-07]

# Metrics
duration: ~2min
completed: 2026-04-11
---

# Phase 4 Plan 06: TestPhase4MustHaves Summary

**Auditable end-to-end test suite for Phase 4: 11 new must_have tests (M1..M10 + T-04-01 security assertion) added to `tests/test_merge.py`, each named after its must_have ID, covering every ROADMAP success criterion and all four edge case design decisions (D-63, D-68, D-69, D-72). Full test suite of 85 tests passes green with zero regressions across 818 tests project-wide.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-11T17:10:51Z
- **Completed:** 2026-04-11T17:13:03Z
- **Tasks:** 3 (Tasks 1+2 TDD; Task 3 regression sweep)
- **Files modified:** 1 (`tests/test_merge.py`)
- **Lines added:** 309 (845 → 1154 total)
- **Tests added:** 11 (74 from Plans 03-05 + 11 new = 85 total passing)

## Accomplishments

### TestPhase4MustHaves — M1..M4 (success criteria end-to-end)

| Test | Coverage | Assertion |
|------|----------|-----------|
| `test_preserve_rank_survives_update` | M1, MRG-01, success-1 | rank==7 and mapState survives UPDATE |
| `test_strategy_skip_is_noop` | M2, MRG-07, success-2 | SKIP_PRESERVE leaves file byte-identical |
| `test_strategy_replace_overwrites_preserve_fields` | M3, MRG-07, success-3 | REPLACE drops rank/mapState |
| `test_field_order_preserved_minimal_diff` | M4, MRG-06, success-4 | key order preserved + exactly 1 line diff |

M4 includes the locked minimal-diff assertion: `diff_count == 1` ensures graphify updates produce minimal git noise (only the changed field's line differs).

### TestPhase4MustHaves — M5..M10 + T-04-01 (edge cases + purity + cheapness)

| Test | Coverage | Assertion |
|------|----------|-----------|
| `test_sentinel_round_trip_deleted_block_not_reinserted` | M5, D-68 | Deleted connections block not re-inserted |
| `test_unmanaged_file_skip_conflict` | M6, D-63 | fingerprint_stripped → SKIP_CONFLICT/unmanaged_file, bytes unchanged |
| `test_malformed_sentinel_skip_warn` | M7, D-69 | malformed_sentinel → SKIP_CONFLICT/malformed_sentinel, bytes unchanged |
| `test_orphan_never_deleted_under_replace` | M8, D-72 | replace strategy never deletes orphan files |
| `test_compute_merge_plan_is_pure` | M9 | mtime unchanged + no .tmp files after compute-only |
| `test_apply_merge_plan_content_hash_skip` | M10 | Second apply: skipped_identical contains target, mtime unchanged |
| `test_malicious_label_does_not_break_sentinel_pairing` | T-04-01 | Malicious wikilink alias does not corrupt sentinel parsing |

### Traceability Matrix

```
# M1  test_preserve_rank_survives_update                         → MRG-01, success-1
# M2  test_strategy_skip_is_noop                                 → MRG-07, success-2
# M3  test_strategy_replace_overwrites_preserve_fields           → MRG-07, success-3
# M4  test_field_order_preserved_minimal_diff                    → MRG-06, success-4
# M5  test_sentinel_round_trip_deleted_block_not_reinserted      → D-68
# M6  test_unmanaged_file_skip_conflict                          → D-63
# M7  test_malformed_sentinel_skip_warn                          → D-69
# M8  test_orphan_never_deleted_under_replace                    → D-72
# M9  test_compute_merge_plan_is_pure                            → Plan 04 purity
# M10 test_apply_merge_plan_content_hash_skip                    → re-run cheapness
```

### Regression Sweep Results

- `pytest tests/test_merge.py` — 85 passed (0 failed)
- `pytest tests/test_merge.py tests/test_profile.py tests/test_templates.py` — 339 passed
- `pytest tests/` — 818 passed (0 failed, 0 errors)

## Task Commits

1. **Task 1 GREEN:** `c0feb56` — `feat(04-06): add TestPhase4MustHaves M1..M4 end-to-end tests`
2. **Task 2 GREEN:** `adc3857` — `feat(04-06): add TestPhase4MustHaves M5..M10 + T-04-01 security assertion`

## Files Modified

- `tests/test_merge.py` (1154 lines, +309 from Plan 05's 845)

## Decisions Made

- **Traceability comment block, not runnable assertion.** M1..M10 → requirement ID mapping is a comment for greppability. Runtime assertion of all 10 names is handled by the plan's automated verification script.
- **M7 test asserts conflict_kind only (no stderr check).** `compute_merge_plan` does not emit stderr warnings — it surfaces the conflict via `MergeAction.reason` and `conflict_kind`. A future enhancement could add explicit `print(..., file=sys.stderr)` for operator visibility, but it is not required for the test to pass.
- **Verification script regex clarification.** The plan's automated verification script used `^def test_` (top-level only), yielding 39. The actual test count is 85 (`grep -c "def test_"`), exceeding the >=50 threshold. The regex discrepancy is a spec issue in the plan, not a production code bug.

## Deviations from Plan

None — all 11 test functions implemented verbatim from the plan's `<action>` code blocks. Test names match the `<behavior>` spec exactly. M5..M10 + T-04-01 all pass on first run.

## Known Stubs

None — all tests exercise real implementations end-to-end with vault fixture copies in tmp_path. No mocked production code, no placeholder assertions.

## Threat Model Coverage

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-04-27 | Mitigated | All tests use `_copy_vault_fixture` → `shutil.copytree` into `tmp_path`. No test opens a path directly under `tests/fixtures/` for writing. |
| T-04-28 | Accepted | Tests use synthetic fixtures only. No production data in test output. |
| T-04-29 | Mitigated | `test_malicious_label_does_not_break_sentinel_pairing` is present and passes. T-04-01 sentinel security contract is verified. |

## Threat Flags

None — plan adds tests only; no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED
