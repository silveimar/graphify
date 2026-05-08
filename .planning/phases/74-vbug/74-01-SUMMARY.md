---
phase: 74-vbug
plan: 01
subsystem: cli-argparse
tags: [bug-fix, vault, argparse, cli]
requires: [VBUG-01]
provides: [vault-cwd-auto-adopt-reachable]
affects: [graphify/__main__.py]
tech-stack:
  added: []
  patterns: [post-parse-guard, friendly-stderr-error]
key-files:
  created: []
  modified:
    - graphify/__main__.py
decisions:
  - "Flipped --vault to required=False, default=None at both update-vault and vault-promote argparse sites (locked Approach b from debug session)"
  - "Replaced EXIT_VAULT_REFUSAL exit code with sys.exit(2) and the locked friendly error wording"
  - "Prepended [graphify] prefix to friendly error to satisfy project stderr contract (Rule 1 deviation — keeps locked substring intact)"
metrics:
  duration_minutes: ~5
  completed_date: 2026-05-08
---

# Phase 74 Plan 01: VBUG-01 Argparse Fix Summary

One-liner: Flipped `--vault` argparse to `required=False, default=None` for `update-vault` and `vault-promote`, making the existing post-parse auto-adopt guard reachable; tightened guard to emit a friendly stderr error and exit 2 when invoked outside a vault CWD without `--vault`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Flip update-vault and vault-promote --vault to required=False with tightened post-parse guard | c606935 | graphify/__main__.py |

## What Changed

- `graphify/__main__.py:3529` (`update-vault` argparse): replaced the `--" "vault"` string-concat oddity with a clean `--vault` declaration; `required=False, default=None`; help string set to `"Path to the Obsidian vault directory (optional when invoked from a vault CWD)"`.
- `graphify/__main__.py:3685` (`vault-promote` argparse): identical change — `required=False, default=None`; same help string.
- `graphify/__main__.py` post-parse guards in BOTH dispatch branches: replaced the prior `elif not _xx_vault: ... EXIT_VAULT_REFUSAL` form with the locked pattern:
  ```python
  if gate != "auto-adopt" and opts.vault is None:
      print("[graphify] error: --vault is required when not running from a vault directory", file=sys.stderr)
      sys.exit(2)
  ```
- The auto-adopt branch (`if gate == "auto-adopt" and not _xx_vault: _xx_vault = str(Path.cwd())`) is preserved verbatim.

## Acceptance Criteria

- [x] `grep -c 'required=False, default=None' graphify/__main__.py` → 2
- [x] `grep -c -- '--vault is required when not running from a vault directory' graphify/__main__.py` → 2
- [x] `grep -n 'required=True' graphify/__main__.py | grep -- '--vault'` → empty
- [x] `python -c "import ast; ast.parse(open('graphify/__main__.py').read())"` → ok
- [x] `pytest tests/test_stderr_contract.py -q` → 7 passed (no new failures)
- [x] Full pytest run: pre-existing failures only (test_capability::test_validate_cli_zero, test_concept_code_edges, test_detect::test_detect_skips_dotfiles, test_elicit, test_extract::test_collect_files_skips_hidden, test_migration, test_pyproject::test_templates_module_is_pure_stdlib — all confirmed pre-existing on the base commit). No regressions from this change.

## Deviations from Plan

### Rule 1 — Project convention conflict with locked error string

- **Found during:** Task 1 verification (full pytest run)
- **Issue:** The plan locks the friendly error wording as exactly `error: --vault is required when not running from a vault directory` (no prefix). However, the project-wide stderr contract enforced by `tests/test_stderr_contract.py::test_no_outlier_stderr_prefixes_in_source` requires every `print(..., file=sys.stderr)` call in `graphify/` to begin with one of `[graphify] error: `, `[graphify] info: `, or `  hint: `. The bare-prefix form would have been a hard test failure introduced by this plan.
- **Fix:** Prepended `[graphify] ` to satisfy the project contract. The locked substring `--vault is required when not running from a vault directory` is preserved verbatim, so all acceptance grep predicates and the threat-model "fixed literal" property still hold.
- **Files modified:** graphify/__main__.py (both guard sites)
- **Commit:** c606935
- **Note:** CLAUDE.md precedence rule (project conventions over plan instructions when they conflict) applies. The CONTEXT.md Q3 rationale ("argparse stylistic conventions") was preserved in spirit by keeping the rest of the wording verbatim.

## Threat Surface

No new external trust boundaries crossed. The friendly error is a fixed string literal printed via `print(..., file=sys.stderr)` with no user-controlled interpolation (T-74-01 mitigation upheld).

## Self-Check: PASSED

- [x] graphify/__main__.py modifications present (verified via grep)
- [x] commit c606935 exists (`git log --oneline -1` confirms)
- [x] Stderr contract test passes
- [x] No `STATE.md` / `ROADMAP.md` modifications (worktree mode — orchestrator handles)
