---
phase: 58-vault-cli-parity-hygiene
verified: 2026-05-03T23:55:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
gaps: []
---

# Phase 58: Vault CLI Parity & Hygiene Verification Report

**Phase Goal:** Ensure `--vault` / discovery behavior matches `graphify doctor` reporting, vault-related CLI failures produce actionable messages, and the v1.10-close registry/hygiene item (HYG-01) is resolved with in-planning evidence.
**Verified:** 2026-05-03T23:55:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `resolve_vault_for_parity()` returns a dict with `vault_path`, `source`, `profile_path`, `profile_mode`, `warnings` | VERIFIED | Function defined at `graphify/output.py:215`; 5 VAUX-01 tests in `tests/test_vault_parity.py` all pass |
| 2 | Parity helper agrees with `run_doctor()` on resolved vault_path and source label across resolution scenarios | VERIFIED | `test_parity_vault_cli_matches_doctor` passes; helper delegates exclusively to `resolve_execution_paths()` |
| 3 | All vault CLI failures emit `[graphify] error: <msg>` + `  hint: <fix>` two-line stderr format with non-zero exit | VERIFIED | `_emit_vault_error()` at `output.py:80`; 3 D-07 call sites migrated; subprocess tests 6-8 pass |
| 4 | Existing `_refuse()` callers remain unchanged; `_merge_vault_pins` override warning text preserved (D-09) | VERIFIED | `__main__.py` not touched in any phase-58 commit; `test_global_local_override_warning_preserved` passes |
| 5 | HYG-01 regression-lock test asserts both spellings in `_SELF_OUTPUT_DIRS` (both copies) with provenance citation | VERIFIED | `test_self_ingestion_dirs_constant_excludes_both_spellings` in `tests/test_detect.py:807`; cites commit `59d8b2f` |

**Score:** 5/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/output.py` | `resolve_vault_for_parity()` function | VERIFIED | Defined at line 215; delegates to `resolve_execution_paths()` |
| `graphify/output.py` | `_emit_vault_error(msg, hint, *, code=1)` function | VERIFIED | Defined at line 80; `raise _emit_vault_error` at lines 95 and 100 (2 sites); hint print at line 166 |
| `tests/test_vault_parity.py` | 10 tests (5 VAUX-01 + 5 VAUX-02) | VERIFIED | All 10 tests present and passing |
| `tests/test_detect.py` | HYG-01 regression-lock test appended | VERIFIED | `test_self_ingestion_dirs_constant_excludes_both_spellings` at line 807 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `output.py:resolve_vault_for_parity` | `output.py:resolve_execution_paths` | direct call inside `contextlib.redirect_stderr` block | WIRED | Confirmed at output.py:230-240 |
| `output.py:_ensure_vault_root` (not-a-dir branch) | `output.py:_emit_vault_error` | `raise _emit_vault_error(...)` | WIRED | Line 95 |
| `output.py:_ensure_vault_root` (no-.obsidian branch) | `output.py:_emit_vault_error` | `raise _emit_vault_error(...)` | WIRED | Line 100 |
| `output.py:_pick_vault_from_list_file` (ambiguous branch) | hint print + `raise SystemExit(2)` | `print("  hint: ...")` before existing `raise SystemExit(2)` | WIRED | Line 166 |
| `tests/test_vault_parity.py` | `graphify.doctor.run_doctor` | `run_doctor(..., resolved_output=...)` | WIRED | Confirmed in test_parity_vault_cli_matches_doctor |
| `tests/test_detect.py:test_self_ingestion_dirs_constant_excludes_both_spellings` | `graphify.corpus_prune._SELF_OUTPUT_DIRS` | local import inside test | WIRED | Lines 818-819 |
| `tests/test_detect.py:test_self_ingestion_dirs_constant_excludes_both_spellings` | `graphify.detect._SELF_OUTPUT_DIRS` | local import inside test | WIRED | Lines 818-819 |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 10 parity tests pass | `pytest tests/test_vault_parity.py -v` | 10 passed | PASS |
| HYG-01 regression-lock test passes | `pytest tests/test_detect.py::test_self_ingestion_dirs_constant_excludes_both_spellings -v` | 1 passed | PASS |
| Full suite — no regressions | `pytest tests/ -q` | 2105 passed, 1 xfailed | PASS |
| test_vault_cli + test_doctor — no precedence change | `pytest tests/test_vault_cli.py tests/test_doctor.py -q` | 23 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VAUX-01 | 58-01 | Structured parity helper asserting `--vault` CLI resolution == `run_doctor()` view | SATISFIED | `resolve_vault_for_parity()` exists; 5 passing tests |
| VAUX-02 | 58-02 | Vault CLI failures emit two-line actionable error format with non-zero exit | SATISFIED | `_emit_vault_error()` at 3 D-07 sites; 5 passing subprocess tests |
| HYG-01 | 58-03 | Self-ingestion fix regression-locked with named constant-membership test | SATISFIED | See HYG-01 Evidence Narrative below |

---

## TDD Gate Compliance

| Plan | RED Commit | GREEN Commit | Order |
|------|------------|--------------|-------|
| 58-01 (VAUX-01) | `67fe947` — add failing parity tests | `45ce2de` — implement resolve_vault_for_parity() | RED before GREEN confirmed |
| 58-02 (VAUX-02) | `06c2c3c` — add failing VAUX-02 subprocess tests | `2864dbb` — add _emit_vault_error() + migrate 3 D-07 sites | RED before GREEN confirmed |

---

## D-09 Scope Check (No Precedence Behavior Change)

`graphify/__main__.py` was NOT modified in any phase-58 commit. The most recent `__main__.py` change predates phase 58 (`32a384a` from phase 57). The `_merge_vault_pins` function body (lines 1288-1310) is unchanged and continues to emit `[graphify] command --vault / --vault-list overrides global pin` to stderr. This is independently locked by `test_global_local_override_warning_preserved` passing.

---

## Q2 Scope Check (No `_emit_vault_error` Scope Creep)

`git grep '_emit_vault_error'` within `graphify/` returns exactly 4 hits:
- Line 80: function definition (`def _emit_vault_error`)
- Line 84: docstring mention (not a call)
- Line 95: `raise _emit_vault_error(...)` — `_ensure_vault_root` not-a-directory branch
- Line 100: `raise _emit_vault_error(...)` — `_ensure_vault_root` no-.obsidian branch

The third D-07 site (`_pick_vault_from_list_file`) uses a direct `print("  hint: ...")` (line 166) before the existing `raise SystemExit(2)` as specified by the plan, so no additional `raise _emit_vault_error` call was needed there. Total `raise _emit_vault_error` sites = 2, matching the plan acceptance criteria. No creep into `__main__.py` or any other module.

---

## HYG-01 Evidence Narrative

**Requirement:** Lock the v1.10-close hygiene item — `detect()` must never self-ingest `graphify-out/` output trees.

**Original fix (already shipped):**
- Quick task `260427-rc7-fix-detect-self-ingestion` shipped on 2026-04-27
- Commit `59d8b2f` — `fix(quick-260427-rc7): prune graphify-out/ in detect() to stop self-ingestion`
- Added `_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}` constant to `graphify/detect.py` and extended `_is_noise_dir()` to return `True` for both spellings
- The same constant was mirrored in `graphify/corpus_prune.py`
- Evidence: `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md`

**Phase 58 regression-lock (Plan 03):**
- Commit `74ce7ef` — `test(58-03): add HYG-01 regression-lock test for _SELF_OUTPUT_DIRS`
- Test function: `test_self_ingestion_dirs_constant_excludes_both_spellings` in `tests/test_detect.py:807`
- The test imports `_SELF_OUTPUT_DIRS` from BOTH `graphify.corpus_prune` AND `graphify.detect` (using local aliases `_CORPUS_SELF` and `_DETECT_SELF`)
- Assertions:
  1. `"graphify-out" in _CORPUS_SELF` — hyphen spelling present
  2. `"graphify_out" in _CORPUS_SELF` — underscore spelling present
  3. `_CORPUS_SELF == _DETECT_SELF` — both copies remain in sync; any future divergence is caught immediately
- Test docstring cites `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md` and commit `59d8b2f` for full traceability
- Test passes as of this verification run

**HYG-01 closure status: CLOSED.** The behavioral fix was shipped in 260427-rc7 (commit `59d8b2f`). Phase 58 adds a permanent, named constant-membership guard that will catch any future regression regardless of refactors to `_is_noise_dir`.

---

## Anti-Patterns Found

No blockers or warnings. The phase-58 changes are minimal and surgical:
- `_emit_vault_error` interpolates user-supplied path into `msg` (T-58-04 accepted — echoed to user's own stderr)
- No `TODO`/`FIXME`/placeholder patterns in any modified file
- No hardcoded empty returns in wired code paths
- `_refuse()` body unchanged; no existing call site migrated beyond the three D-07 sites

---

## Human Verification Required

None. All must-haves are fully verifiable programmatically. The full test suite passes (2105 tests, 0 failures).

---

## Gaps Summary

No gaps. All 5 must-haves verified against codebase evidence:

1. `resolve_vault_for_parity()` exists, has the correct 5-key return shape, delegates exclusively to `resolve_execution_paths()`, and is tested by 5 passing VAUX-01 tests.
2. `_emit_vault_error()` exists, produces the two-line `[graphify] error:` + `  hint:` format, is used at exactly the 3 D-07 call sites, and is tested by 5 passing VAUX-02 subprocess tests.
3. HYG-01 is locked by a named regression-lock test citing original commit `59d8b2f` and the quick-task SUMMARY path.
4. D-09 is preserved: `__main__.py` untouched in all phase-58 commits.
5. Q2 scope respected: `_emit_vault_error` appears in `output.py` only (4 hits = 1 def + 1 docstring mention + 2 raise sites).

---

_Verified: 2026-05-03T23:55:00Z_
_Verifier: Claude (gsd-verifier)_
