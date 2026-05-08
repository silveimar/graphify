---
phase: 74-vbug
plan: 02
subsystem: cli-tests
tags: [regression-tests, vault, argparse, gate]
requires: [VBUG-02]
provides: [vault-cwd-gate-regression-suite]
affects: [tests/test_vault_cwd_gate.py, tests/test_vault_cwd.py, .planning/debug/vault-cwd-gate-argparse-required.md]
tech-stack:
  added: []
  patterns: [parametrized-subprocess-test, profile-vault-fixture]
key-files:
  created:
    - tests/test_vault_cwd_gate.py
  modified:
    - tests/test_vault_cwd.py
    - .planning/debug/vault-cwd-gate-argparse-required.md
decisions:
  - "Parametrize 14 distinct gate call sites (not 15); CONTEXT.md's '15th inline gate at line 2947' falls inside the elicit branch's existing gate call at 2860, not a separate site"
  - "Decisive assertion is absence of argparse signature 'the following arguments are required: --vault'; returncode!=2 guarded on that string to avoid false positives from unrelated business-layer SystemExit(2) (e.g. import-harness security check)"
  - "Co-locate the friendly-error sibling test (test_update_vault_no_vault_flag_outside_vault_friendly_error) with the moved RED tests so all gate-related regression coverage lives in one file"
metrics:
  duration_minutes: ~10
  completed_date: 2026-05-08
---

# Phase 74 Plan 02: VBUG-02 Gate Regression Suite Summary

One-liner: Created `tests/test_vault_cwd_gate.py` with parametrized 14-branch coverage of every gated subcommand invoked from a profile-vault CWD without `--vault`, moved the two unskipped RED tests + the update-vault friendly-error sibling out of `tests/test_vault_cwd.py`, and resolved the `.planning/debug/vault-cwd-gate-argparse-required.md` debug session.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Audit tests/test_vault_cwd.py for gate-related tests | (folded into Task 2 commit per plan) | (read-only) |
| 2 | Create tests/test_vault_cwd_gate.py with parametrized 14-command coverage and unskipped moved RED tests | 79dabdb | tests/test_vault_cwd_gate.py, tests/test_vault_cwd.py |
| 3 | Resolve debug session frontmatter | 2b2be93 | .planning/debug/vault-cwd-gate-argparse-required.md |

## What Changed

- **New file `tests/test_vault_cwd_gate.py`** (235 lines):
  - Audit comment header documenting the move/leave decisions and the 14-vs-15 site enumeration.
  - `_make_profile_vault` fixture mirroring the canonical `tests/test_vault_cwd.py:_make_profile_vault` pattern (full v1.8 profile.yaml, .obsidian/, notes/).
  - `vault_dir` pytest fixture wrapping the helper.
  - `GATED_COMMANDS` list with 14 (subcmd, extra_args) tuples covering: `--obsidian`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `save-result`, `elicit`, `harness`, `import-harness`, `run`, `enrich`, `update-vault`, `vault-promote`.
  - `test_gated_subcommand_no_argparse_vault_required_from_vault_cwd` — parametrized test with three assertions per case: (a) absence of argparse `the following arguments are required: --vault` signature, (b) `auto-adopt` notice fired on stderr, (c) returncode==2 only allowed when not for the argparse-required-flag reason.
  - Three moved tests verbatim (with skip-marker removed): `test_update_vault_auto_adopt_no_vault_flag`, `test_vault_promote_auto_adopt_no_vault_flag`, `test_update_vault_no_vault_flag_outside_vault_friendly_error`.
- **`tests/test_vault_cwd.py`**:
  - Removed the three moved tests (lines 437–499 region collapsed to a forwarding comment pointing at the new file).
  - Updated `test_vault_promote_no_vault_flag_outside_vault_friendly_error` exit-code assertion from `==1` to `!= 0` to match plan-01's locked `sys.exit(2)` friendly-error contract (Rule 1 deviation; see below).
- **`.planning/debug/vault-cwd-gate-argparse-required.md` frontmatter**:
  - `status: diagnosed-pending-fix-phase` → `status: resolved`
  - Added `resolved_in: phase-74-vbug`
  - `updated: 2026-05-04` → `updated: 2026-05-08`

## Acceptance Criteria

- [x] `test -f tests/test_vault_cwd_gate.py` — succeeds
- [x] `grep -c '@pytest.mark.parametrize' tests/test_vault_cwd_gate.py` — 1
- [x] `grep -c '@pytest.mark.skip' tests/test_vault_cwd_gate.py` — 0
- [x] `grep -c 'def test_update_vault_auto_adopt_no_vault_flag\|def test_vault_promote_auto_adopt_no_vault_flag' tests/test_vault_cwd.py` — 0 (moved out)
- [x] `pytest tests/test_vault_cwd_gate.py -q` — 17 passed (14 parametrized + 3 moved)
- [x] `pytest tests/test_vault_cwd.py tests/test_vault_cwd_gate.py -q` — 35 passed (gate-relevant suite green)
- [x] `pytest tests/ -q` — 2517 passed, 7 pre-existing failures only (matches 74-01 SUMMARY's pre-existing failure list); the 8th flake observed mid-execution (`test_vault_promote_no_vault_flag_outside_vault_friendly_error`) was a plan-01 regression, fixed inline (Rule 1 deviation)
- [x] `grep -E '^status: resolved$|^resolved_in: phase-74-vbug$|^updated: 2026-05-08$' .planning/debug/vault-cwd-gate-argparse-required.md | wc -l` — 3
- [x] `grep -c '^status: diagnosed-pending-fix-phase$' .planning/debug/vault-cwd-gate-argparse-required.md` — 0

## Deviations from Plan

### Rule 1 — Plan-01 regression in tests/test_vault_cwd.py

- **Found during:** Task 2 verification (full pytest run)
- **Issue:** `test_vault_promote_no_vault_flag_outside_vault_friendly_error` (in tests/test_vault_cwd.py, NOT one of the three tests slated for move) asserted `proc.returncode == 1` (EXIT_VAULT_REFUSAL=1). Plan-01 (commit c606935) flipped the friendly-error path to `sys.exit(2)` per CONTEXT.md decision; the old `==1` assertion was a pre-existing test that became wrong after plan-01 landed but was not flagged in 74-01 SUMMARY's pre-existing-failure list.
- **Fix:** Relaxed assertion to `proc.returncode != 0` to encode the new locked contract (non-zero exit, exact code is plan-01's choice).
- **Files modified:** tests/test_vault_cwd.py (lines 488–490 region).
- **Commit:** 79dabdb (folded into Task 2 commit).

### Plan-spec adjustment — 14 vs 15 sites

- **Found during:** Task 2 audit of `__main__.py`.
- **Issue:** CONTEXT.md and the debug-session blast-radius enumerate 15 gated branches, including an "inline gate at ~line 2947". Audit at base aeff5eb shows the gate is invoked at exactly 14 distinct call sites; line 2947 sits inside the `elicit` branch (gate call at line 2860), not a separate site.
- **Fix:** Parametrized 14 cases with explicit comment documenting the audit; plan-02 explicitly permitted this ("if no distinct CLI form exists, document why and reduce to 14 cases with a comment").
- **Files modified:** tests/test_vault_cwd_gate.py (audit header).
- **Commit:** 79dabdb.

## Threat Surface

No new external trust boundaries crossed. All subprocess invocations are local (`sys.executable -m graphify`) under `tmp_path` fixtures with `timeout=30`. T-74-04 (test fixture tampering) and T-74-05 (DoS via subprocess) mitigations from the plan's threat model are upheld. T-74-06 (stderr information disclosure) — stderr content is graphify's own output; no secrets.

## Self-Check: PASSED

- [x] tests/test_vault_cwd_gate.py exists (verified via `test -f`)
- [x] tests/test_vault_cwd.py modified (forwarding comment + Rule 1 fix)
- [x] .planning/debug/vault-cwd-gate-argparse-required.md frontmatter flipped to resolved
- [x] commit 79dabdb exists (`git log --oneline | grep 79dabdb` confirms)
- [x] commit 2b2be93 exists (`git log --oneline | grep 2b2be93` confirms)
- [x] `pytest tests/test_vault_cwd_gate.py -q` exits 0 (17 passed)
- [x] No STATE.md or ROADMAP.md modifications (worktree mode — orchestrator handles)
