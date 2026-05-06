---
phase: 64-audit-a-stderr-format-snapshot-lock-sweep
verified: 2026-05-06T12:45:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 64: AUDIT-A — stderr Format Snapshot Lock & Sweep Verification Report

**Phase Goal:** The `[graphify] error:` + `  hint:` two-line stderr contract is locked by an automated snapshot test BEFORE any reformatting touches the codebase, so the 7 platform skills' regex parsers cannot silently break.
**Verified:** 2026-05-06T12:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | stderr-format snapshot test exists and passes capturing the v1.12 contract | VERIFIED | `tests/test_stderr_contract.py` — 5 tests pass; `tests/fixtures/stderr_contract.txt` contains 3-section golden fixture |
| 2 | One-line outliers migrated with snapshot still passing | VERIFIED | All `__main__.py` bare `hint:` lines (2009, 2127, 2434) are immediately preceded by `[graphify] error:` lines; `harness_export.py:204` is in a two-line block; `test_no_outlier_stderr_prefixes_in_source` passes |
| 3 | `pytest tests/ -q` produces zero unexpected stderr-format diffs | VERIFIED | 1 failed (`test_migration.py::test_preview_expands_risky_action_rows`) — pre-existing, unrelated to Phase 64; 2284 passed |
| 4 | 7 platform skill regex parsers enumerated in a test fixture | VERIFIED | `tests/fixtures/skill_stderr_regexes.yaml` has exactly 7 keys: claude-code, codex, opencode, openclaw, factory-droid, trae, trae-cn |

**Score:** 4/4 truths verified

### Locked Decisions (D-01..D-04)

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01: golden text snapshot at `tests/fixtures/stderr_contract.txt` | VERIFIED | File exists with 3 sections (error+hint, info+hint, Option-B info+hint) |
| D-02: grep-and-migrate-all — `test_no_outlier_stderr_prefixes_in_source` must exist and pass | VERIFIED | Test at line 93 of `test_stderr_contract.py`; passes; whitelists `graphify/output.py` (intentional — it is the emit_* implementation); all other files comply |
| D-03: 7-platform regex fixture at `tests/fixtures/skill_stderr_regexes.yaml` | VERIFIED | 7 entries confirmed: claude-code, codex, opencode, openclaw, factory-droid, trae, trae-cn |
| D-04: `test_strict_prefix_whitelist` exists in `test_stderr_contract.py` | VERIFIED | Test at line 122; passes; validates every non-empty fixture line matches `[graphify] error:`, `[graphify] info:`, `[graphify] hint:`, or `  hint:` |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/fixtures/stderr_contract.txt` | Golden snapshot of stderr contract | VERIFIED | 9 lines, 3 sections matching v1.12 two-line convention |
| `tests/fixtures/skill_stderr_regexes.yaml` | 7-platform regex fixture | VERIFIED | 7 keys present |
| `tests/test_stderr_contract.py` | Snapshot + invariant tests | VERIFIED | 5 tests: 3 snapshot, 1 grep-invariant, 1 strict-whitelist |
| `tests/test_skill_regex_fixture.py` | Platform regex tests | VERIFIED | 3 tests: all_seven_platforms_present, each_regex_compiles, each_regex_matches_locked_contract |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 64 test suite passes | `pytest tests/test_stderr_contract.py tests/test_skill_regex_fixture.py -v` | 8 passed in 0.09s | PASS |
| Full suite — no phase-64 regressions | `pytest tests/ -q` | 1 failed (pre-existing test_migration.py), 2284 passed | PASS |
| Fixture has exactly 7 platform keys | `python -c "import yaml; d=yaml.safe_load(...); print(len(d))"` | `7 ['claude-code', 'codex', 'factory-droid', 'openclaw', 'opencode', 'trae', 'trae-cn']` | PASS |

### Anti-Patterns Found

None. All identified outlier `hint:` lines in `__main__.py` (lines 2009, 2127, 2434) and `harness_export.py` (line 204) are structurally compliant — each is immediately preceded by a `[graphify] error:` line, forming valid two-line blocks. The grep invariant test correctly catches single-line violations; multi-line prints of the same structure are inherently compliant.

### Note on `graphify/output.py` Whitelist

`output.py` is whitelisted in `test_no_outlier_stderr_prefixes_in_source` because it contains the raw `print(f"[graphify] {msg}", file=sys.stderr)` implementation behind `emit_error()` / `emit_info()` / `emit_hint()`. This is the correct design — the whitelist is intentional and documented in the test docstring.

### Note on `trae-cn` Platform

`graphify/skill-trae-cn.md` is absent from the repo; the `trae-cn` fixture entry uses a permissive default regex. This is acknowledged as an acceptable deviation per the verification context brief. The test passes and the platform is enumerated.

### Human Verification Required

None required. All success criteria and locked decisions are verifiable programmatically and all pass.

---

_Verified: 2026-05-06T12:45:00Z_
_Verifier: Claude (gsd-verifier)_
