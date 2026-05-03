---
phase: 58-vault-cli-parity-hygiene
plan: "02"
subsystem: vault-cli
tags: [vaux-02, error-format, tdd, output-py]
dependency_graph:
  requires: [58-01]
  provides: [_emit_vault_error, VAUX-02-tests]
  affects: [graphify/output.py, tests/test_vault_parity.py]
tech_stack:
  added: []
  patterns: [two-line-error-format, raise-SystemExit-convention, subprocess-cli-test]
key_files:
  created: []
  modified:
    - graphify/output.py
    - tests/test_vault_parity.py
decisions:
  - D-09 preserved: _merge_vault_pins warning text in __main__.py untouched
  - Q2 scoped: _emit_vault_error used at exactly 3 D-07 call sites; all other _refuse() callers unchanged
  - Ambiguous-list uses print(hint) before existing raise SystemExit(2) — exit code 2 preserved per D-06
metrics:
  duration: "377s"
  completed: "2026-05-03T23:41:33Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 58 Plan 02: VAUX-02 Actionable Error Format Summary

Two-line `[graphify] error: <msg> / hint: <fix>` stderr format for vault CLI failures via `_emit_vault_error()` companion to `_refuse()`, with 5 VAUX-02 subprocess tests locking three D-07 failure categories plus D-09 override-warning preservation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing VAUX-02 subprocess tests | 06c2c3c | tests/test_vault_parity.py |
| 2 (GREEN) | Add _emit_vault_error() + migrate 3 D-07 sites | 2864dbb | graphify/output.py, tests/test_vault_parity.py |

## What Was Built

### `_emit_vault_error()` in `graphify/output.py`

Added immediately after `_refuse()` (line ~80). Emits two lines to stderr and returns `SystemExit(code)`. Callers do `raise _emit_vault_error(msg, hint)` — same convention as `_refuse()`.

```python
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```

### 3 D-07 Call Sites Migrated

1. `_ensure_vault_root()` — not-a-directory branch: `raise _emit_vault_error(...)` with hint about path being a directory.
2. `_ensure_vault_root()` — no `.obsidian/` marker: `raise _emit_vault_error(...)` with hint mentioning `.obsidian/`.
3. `_pick_vault_from_list_file()` — ambiguous multi-root non-TTY: added `print("  hint: ...")` before the existing `raise SystemExit(2)`. Exit code 2 preserved (D-06).

### 5 VAUX-02 Tests in `tests/test_vault_parity.py`

| Test | Scenario | Key Assertions |
|------|----------|----------------|
| `test_unknown_vault_nonexistent_path_error` | --vault /no-such-dir | returncode != 0, `[graphify] error:` in stderr, `  hint:` in stderr |
| `test_unknown_vault_no_obsidian_marker_error` | --vault dir-without-.obsidian | returncode != 0, both error lines, `.obsidian` in stderr |
| `test_ambiguous_vault_list_exit2` | vault-list with 2 vaults + non-TTY | returncode == 2, `  hint:` in stderr |
| `test_global_local_override_warning_preserved` | global + per-command --vault | `[graphify] command --vault / --vault-list overrides global pin` in stderr |
| `test_dry_run_mismatch_uses_parity_helper` | CLI doctor + parity helper | vault_path agreement, vault path in doctor stdout |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_ambiguous_vault_list_exit2 — parent directory not created**
- **Found during:** Task 2 GREEN verification
- **Issue:** `_make_vault(tmp_path / "a")` failed with FileNotFoundError because `_make_vault` creates `parent/vault` and `tmp_path/a` did not exist yet.
- **Fix:** Added `sub_a.mkdir()` and `sub_b.mkdir()` before calling `_make_vault`.
- **Files modified:** tests/test_vault_parity.py

**2. [Rule 1 - Bug] test_global_local_override_warning_preserved — spurious exit code assertion**
- **Found during:** Task 2 GREEN verification
- **Issue:** Test asserted `returncode == 0` but doctor exits 1 when it finds recommended fixes (self-ingestion of `graphify-out/`). The D-09 check only requires the warning text be present in stderr.
- **Fix:** Removed `assert r.returncode == 0` — left only the warning text assertion.
- **Files modified:** tests/test_vault_parity.py

**3. [Rule 1 - Bug] test_dry_run_mismatch_uses_parity_helper — spurious exit code assertion**
- **Found during:** Task 2 GREEN verification
- **Issue:** Same as above — doctor exits 1 in tmp_path context. Test purpose is vault_path parity between CLI and helper.
- **Fix:** Removed `assert r.returncode == 0, r.stderr` — kept parity assertions (vault_path equality, vault path in stdout).
- **Files modified:** tests/test_vault_parity.py

## TDD Gate Compliance

- RED gate commit: `06c2c3c` — `test(58-02): add failing VAUX-02 subprocess tests (RED gate)`
- GREEN gate commit: `2864dbb` — `feat(58-02): add _emit_vault_error() and migrate 3 D-07 call sites (GREEN gate)`
- RED before GREEN: confirmed (git log order)
- Tests 1-3 failed before GREEN implementation (error format mismatch confirmed in RED run output)

## Known Stubs

None. All three D-07 failure paths emit real error+hint text. No hardcoded placeholders.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. `_emit_vault_error()` interpolates user-supplied path into the `msg` parameter printed to stderr — consistent with T-58-04 disposition (user's own path echoed to user's own stderr).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| graphify/output.py exists | FOUND |
| tests/test_vault_parity.py exists | FOUND |
| RED commit 06c2c3c exists | FOUND |
| GREEN commit 2864dbb exists | FOUND |
| `_emit_vault_error` defined once in output.py | 1 (confirmed) |
| `_emit_vault_error` not in __main__.py (Q2) | 0 references (confirmed) |
