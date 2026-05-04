---
phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e
plan: 02
requirement: EXIT-CODE-CONST-01
status: complete
green_commit: 87e7f6b
red_commit: a8ceb7d
---

# Phase 62 Plan 02: Exit-Code Constants Summary

One-liner: Replaced magic exit-code literals (`1`/`2`) at four vault-error call sites with named constants `EXIT_VAULT_REFUSAL` and `EXIT_VAULT_GATE` exported from `graphify.output`. Wire values unchanged; behavior preserved.

## Constants Defined

| Constant | Value | Semantics |
|----------|-------|-----------|
| `EXIT_VAULT_REFUSAL` | `1` | Vault-policy refusals (no profile, write-into-vault guard, missing vault root) |
| `EXIT_VAULT_GATE` | `2` | VCWD-03 CWD-gate refusal (cwd is vault, no profile, no override) |

Both constants live in `graphify/output.py` (lines 80-81), above `_emit_vault_error`.

## Call Sites Updated

| # | File | Line | Site | Before | After |
|---|------|------|------|--------|-------|
| 1 | `graphify/output.py` | 109 | `_ensure_vault_root` (path-not-dir) | implicit default | `code=EXIT_VAULT_REFUSAL` |
| 2 | `graphify/output.py` | 115 | `_ensure_vault_root` (not-a-vault) | implicit default | `code=EXIT_VAULT_REFUSAL` |
| 3 | `graphify/__main__.py` | 1560 | `_check_vault_cwd_gate` (VCWD-03) | `code=2` | `code=EXIT_VAULT_GATE` |
| 4 | `graphify/__main__.py` | 2909 | import-harness vault-write guard (HARN-FMT-01) | implicit default | `code=EXIT_VAULT_REFUSAL` |

Additional changes:
- `_emit_vault_error` default changed from `code: int = 1` → `code: int = EXIT_VAULT_REFUSAL` and docstring extended with named-constant policy note.
- `_check_vault_cwd_gate` docstring (lines 1525, 1529): `SystemExit(2)` → `SystemExit(EXIT_VAULT_GATE)` (two replacements).

## Commits

| Gate | SHA | Message |
|------|-----|---------|
| RED | `a8ceb7d` | `test(62-02): RED — add EXIT_VAULT_REFUSAL/EXIT_VAULT_GATE constant-existence test` |
| GREEN | `87e7f6b` | `refactor(62-02): name vault-error exit codes via EXIT_VAULT_REFUSAL/EXIT_VAULT_GATE` |

**GREEN commit SHA for plan 62-04 traceability: `87e7f6b`**

## Test Results

- `tests/test_output.py::test_emit_vault_error_exit_code_constants` — PASSED (new)
- `tests/test_vault_cwd.py` — PASSED (regression guard, unmodified, VCWD-03 still exits 2)
- `tests/test_harness_import.py` — PASSED (regression guard, unmodified, HARN-FMT-01 still exits 1)
- Full suite: 2139 passed, 1 xfailed, 2 failed.

### Pre-existing failures (NOT caused by this plan)

1. `tests/test_migration.py::test_preview_expands_risky_action_rows` — pre-existing tech debt from a dirty `graphify/migration.py` working-tree state (documented in execution prompt).
2. `tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd` — owned by plan 62-03 (E2E-AUTO-ADOPT-01); requires argparse `--vault` default-from-cwd which is not yet implemented. Not in scope for 62-02.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `graphify/output.py` defines `EXIT_VAULT_REFUSAL` and `EXIT_VAULT_GATE`: confirmed via grep.
- `code=2` no longer appears in `graphify/__main__.py` production code: confirmed.
- RED commit `a8ceb7d` and GREEN commit `87e7f6b` exist in git log: confirmed.
- Regression guards (`test_vault_cwd.py`, `test_harness_import.py`) byte-identical and passing: confirmed.
