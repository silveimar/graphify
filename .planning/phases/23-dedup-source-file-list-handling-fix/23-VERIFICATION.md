---
phase: 23-dedup-source-file-list-handling-fix
verified: 2026-04-27T19:02:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 23: Dedup `source_file` List-Handling Fix — Verification Report

**Phase Goal:** `graphify --dedup --dedup-cross-type` no longer crashes on extractions whose edges already carry `list[str]` `source_file` values; merged shape stays compatible with `export.py` consumers.

**Verified:** 2026-04-27 14:02 CST
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | `graphify --dedup --dedup-cross-type` completes on a fixture with `list[str]` `source_file` edges, no `TypeError: unhashable type: 'list'` | VERIFIED | `pytest tests/test_dedup.py::test_cross_type_merges_list_shaped_source_file` PASSED. Test fixture at `tests/test_dedup.py:411-440` deliberately seeds `source_file: ["a.py", "x.py"]` on an edge and invokes `dedup(..., cross_type=True)`. No exception raised. |
| SC2 | After dedup, edge with ≥2 contributors has `source_file = sorted(unique union)`; edge with 1 contributor preserves scalar | VERIFIED | Test 1 asserts `merged[0]["source_file"] == ["a.py", "b.md", "x.py"]` (sorted unique union of list `["a.py","x.py"]` and scalar `"b.md"`). Patched code at `graphify/dedup.py:493-510` implements exact 3-branch contract (`sorted(sf_set)` if >1 / `next(iter(sf_set))` if 1 / `""` if 0). |
| SC3 | `pytest tests/test_dedup.py -q` includes regression case on cross-type list-shaped fixture and is green | VERIFIED | `pytest tests/test_dedup.py -q` → `24 passed in 3.04s`. Two new tests added at lines 411 and 441. |
| SC4 | `export.py` consumers (HTML, JSON, GraphML, Obsidian) handle merged `source_file` shape without raising | VERIFIED (by design — D-06) | Locked decision D-06 explicitly excludes export-consumer smoke tests as redundant. RESEARCH.md confirms all consumers route `source_file` through `_iter_sources`/`_fmt_source_file`. Output shape contract preserved verbatim per D-04, so no consumer-visible shape change vs. pre-bug behavior. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/dedup.py` | +11/-1 patch: import + flatten-then-fold replacing buggy set comprehension | VERIFIED | Diff confirms exactly +11/-1: line 35 adds `from graphify.analyze import _iter_sources`; lines 493-510 replace `{e["source_file"] for e in group ...}` with `for e in group: sf_set.update(_iter_sources(...))` plus 3-branch shape contract. |
| `tests/test_dedup.py` | +65/-0 patch: 2 new test functions | VERIFIED | `test_cross_type_merges_list_shaped_source_file` at line 411 (DEDUP-03 spec); `test_dedup_is_idempotent_on_source_file_shape` at line 441 (idempotency). Both PASS. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `dedup.py:_merge_extraction` (edge-merge) | `analyze._iter_sources` | top-of-file import (line 35) | WIRED | Import present and called inside the merge loop (`sf_set.update(_iter_sources(e.get("source_file")))`). |
| Test 1 fixture (list-shaped) | `dedup(..., cross_type=True, embed_threshold=0.85)` | `_forced_merge_encoder` | WIRED | Test invokes the public `dedup()` API with cross-type enabled — no mocking of internals. Test passes. |

### Locked Decision Compliance (D-01..D-07)

| Decision | Requirement | Status | Evidence |
|----------|-------------|--------|----------|
| D-01 | Reuse `_iter_sources`, no new `_sf_flatten` helper | VERIFIED | `grep -nF "_sf_flatten"` → 0 matches in `dedup.py` and `test_dedup.py`. Import of `_iter_sources` present at line 35. |
| D-02 | Node block at lines 445-459 untouched | VERIFIED | Diff `a517c8d..HEAD` on `dedup.py` shows ONLY two hunks: import block (line 35) and edge-merge site (lines ~491-510). Node block at 445-459 byte-identical (still uses v1.3 IN-06 set-fold pattern). |
| D-03 | Flatten-then-set construction at patch site | VERIFIED | Patch at lines 498-500 does exactly: `sf_set: set[str] = set()` then `for e in group: sf_set.update(_iter_sources(e.get("source_file")))`. |
| D-04 | 3-branch shape contract preserved (sorted list / scalar / `""`) | VERIFIED | Lines 503-509 implement 3 branches: `if len(sf_set) > 1: sorted(sf_set)`, `elif sf_set: next(iter(sf_set))`, `else: ""`. Matches DEDUP-02 wording verbatim. |
| D-05 | Two new test functions in `test_dedup.py` | VERIFIED | Both functions present and named per plan: `test_cross_type_merges_list_shaped_source_file` (line 411) and `test_dedup_is_idempotent_on_source_file_shape` (line 441). |
| D-06 | NO export-consumer smoke tests added | VERIFIED | Diff on `tests/` confined to `test_dedup.py`. No new `to_obsidian` / `to_html` / `to_json` integration tests added. |
| D-07 | NO mixed scalar+list fixtures added (beyond Test 1's implicit mix) | VERIFIED | Test 1 has implicit mix (one edge `list`, one edge `scalar`) per plan allowance; no separate "mixed within same group" fixture introduced. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEDUP-01 | 23-01-PLAN | No `TypeError: unhashable type: 'list'` on list-form `source_file` edges | SATISFIED | Test 1 PASSES; pre-fix RED step in SUMMARY documents the exact `TypeError` was reproduced and is now gone. |
| DEDUP-02 | 23-01-PLAN | Merged `source_file` = sorted unique union (≥2) or scalar (==1) | SATISFIED | Test 1 asserts sorted union output `["a.py","b.md","x.py"]`. Code lines 503-509 implement contract. |
| DEDUP-03 | 23-01-PLAN | Regression test in `tests/test_dedup.py` exercises cross-type path on `list[str]` fixture | SATISFIED | `test_cross_type_merges_list_shaped_source_file` (line 411) does exactly this. |

No orphaned requirements — all 3 phase REQ-IDs accounted for in 23-01-PLAN.

### Anti-Patterns Found

None. Files modified (`graphify/dedup.py`, `tests/test_dedup.py`) scanned for stub patterns (`TODO`, `FIXME`, empty returns, console-only handlers) — no matches. The patch site has an inline comment block referencing Issue #4 / DEDUP-01 / DEDUP-02 (intentional documentation, not a stub marker).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| DEDUP-03 spec test green | `pytest tests/test_dedup.py::test_cross_type_merges_list_shaped_source_file -q` | 1 passed in ~2s | PASS |
| Idempotency test green | `pytest tests/test_dedup.py::test_dedup_is_idempotent_on_source_file_shape -q` | 1 passed | PASS |
| Full dedup file green (no regressions) | `pytest tests/test_dedup.py -q` | 24 passed in 3.04s | PASS |
| Buggy comprehension absent | `grep -nF '{e["source_file"] for e in group' graphify/dedup.py` | 0 matches | PASS |
| `_iter_sources` import present | `grep -n "from graphify.analyze import _iter_sources" graphify/dedup.py` | 1 match (line 35) | PASS |
| Node block untouched | `sed -n '440,465p' graphify/dedup.py` | Confirms v1.3 IN-06 `isinstance` set-fold pattern still present | PASS |
| Diff scope confined | `git diff a517c8d..HEAD -- graphify/dedup.py` | Exactly 2 hunks: import + edge-merge site | PASS |

### Executor Deviations Review

| Deviation | Assessment |
|-----------|------------|
| Test 2 (idempotency) passed RED instead of failing | NON-BLOCKING. SUMMARY documents that the second-pass fixture short-circuits at `dedup.py:483` (`len(group) == 1`), so the buggy line is never reached on re-pass for this fixture. The test still locks the idempotency contract (no crash, shape preserved) and passes GREEN. Acceptable per plan intent. |
| Worktree branch reset to `main` HEAD | NON-BLOCKING. Pure environment fix — no source change. The original worktree base predated phase 23 plan files; reset was required to access the targets. |
| `deferred-items.md` with 2 pre-existing test failures | NON-BLOCKING. SUMMARY confirms `git stash` round-trip showed both failures pre-exist on `main` and are unrelated to dedup. Out of scope per phase boundary. |

## Gaps Summary

None. All 4 ROADMAP success criteria met, all 3 DEDUP requirements satisfied, all 7 locked decisions (D-01..D-07) honored, the patched code lands at exactly the right surface (edge-merge site + import; node block byte-identical), and both regression tests pass green alongside the full dedup test file.

The phase achieves its goal: `graphify --dedup --dedup-cross-type` now correctly handles list-shaped `source_file` edges without crashing, while preserving the downstream-consumer-compatible shape contract.

---

_Verified: 2026-04-27T19:02:00Z_
_Verifier: Claude (gsd-verifier)_
