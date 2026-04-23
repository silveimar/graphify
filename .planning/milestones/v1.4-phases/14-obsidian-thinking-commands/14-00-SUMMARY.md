---
phase: 14-obsidian-thinking-commands
plan: 00
subsystem: installer
tags: [installer, cli, refactor, tdd]
requires: []
provides:
  - directory-scan-uninstall
  - whitelist-drift-fix
affects:
  - graphify/__main__.py
  - tests/test_install.py
tech-stack:
  added: []
  patterns:
    - "sorted(src_dir.glob('*.md')) symmetric scan for install + uninstall"
    - "Path.unlink(missing_ok=True) for idempotent removal"
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_install.py
decisions:
  - "Resolve src_dir internally in _uninstall_commands from cfg['commands_src_dir'] rather than threading it through the caller — preserves existing public call signature (`_uninstall_commands(cfg)`)."
  - "Only remove names that originate in graphify/commands/ source tree; never rglob or wildcard-delete dst_dir — protects user-authored adjacent command files (TM-14-00-01)."
metrics:
  duration_seconds: 144
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-04-22
requirements_completed:
  - OBSCMD-01
threat_mitigations:
  - TM-14-02
---

# Phase 14 Plan 00: _uninstall_commands Directory-Scan Refactor Summary

**One-liner:** Replaced `_uninstall_commands` hardcoded 7-name whitelist with `sorted(src_dir.glob("*.md"))` directory-scan symmetric with `_install_commands`, eliminating whitelist-drift (TM-14-02) and unblocking Phase 14's new command additions.

## What Shipped

- **`graphify/__main__.py`** (`_uninstall_commands`, lines 157-182): hardcoded tuple `("context.md", "trace.md", "connect.md", "drift.md", "emerge.md", "ghost.md", "challenge.md")` replaced with a directory-scan over `Path(__file__).parent / cfg["commands_src_dir"]`. Uses `target.unlink(missing_ok=True)` for idempotency. Guards added for absent `commands_enabled`, missing `dst_dir`, and missing `src_dir`.
- **`tests/test_install.py`** (appended): two new unit tests — `test_uninstall_directory_scan` (proves `ask.md` and `argue.md`, which were outside the legacy whitelist, are now removed) and `test_uninstall_idempotent` (proves double-uninstall never raises).

## Commits

| Task | Type     | Hash      | Message |
| ---- | -------- | --------- | ------- |
| 1    | test     | `23d4bb4` | `test(14-00): add failing directory-scan + idempotency tests for uninstall` |
| 2    | refactor | `6bbda52` | `refactor(14-00): _uninstall_commands directory-scan (OBSCMD-01)` |

## Verification

- `pytest tests/test_install.py::test_uninstall_directory_scan tests/test_install.py::test_uninstall_idempotent -q` → **2 passed**
- `pytest tests/test_install.py -q` → **47 passed** (no regressions)
- `pytest tests/ -q` → **1412 passed, 2 warnings** (full suite green)
- `grep -n 'for name in ("context.md"' graphify/__main__.py` → **no match** (hardcoded tuple removed)
- `grep -n "src_dir.glob" graphify/__main__.py` → **2 matches** (line 150 install, line 177 uninstall — symmetric)

## Success Criteria

- [x] `_uninstall_commands` uses `sorted(src_dir.glob("*.md"))`
- [x] `test_uninstall_directory_scan` passes
- [x] `test_uninstall_idempotent` passes
- [x] Full `pytest tests/ -q` suite green (1412 passed)
- [x] Hardcoded 7-name tuple removed from `graphify/__main__.py`

## Threat Mitigations

- **TM-14-02 (Whitelist drift):** Mitigated. Single source of truth is now `graphify/commands/*.md`. Any command file added to the source tree is automatically uninstalled — no parallel list to update.
- **T-14-00-01 (rm -rf dst_dir risk):** Mitigated. Only files whose names come from `src_dir.glob("*.md")` are removed; adjacent user-authored commands in `dst_dir` are preserved.
- **T-14-00-02 (Repeated uninstall DoS):** Accepted and trivially satisfied — `unlink(missing_ok=True)` + `dst_dir.exists()` guard.

## Deviations from Plan

None — plan executed exactly as written. The `test_uninstall_idempotent` test technically passed on first run (against the old whitelist code) because the old implementation's `.exists()` guard already provided idempotency; the genuinely failing RED signal came from `test_uninstall_directory_scan` (which caught `ask.md` / `argue.md` leftovers). This matches the plan's stated RED requirement: "at least one of the two tests FAIL." Both now pass after the GREEN refactor.

## TDD Gate Compliance

- RED gate: `test(14-00): ...` commit `23d4bb4` ✓
- GREEN gate: `refactor(14-00): ...` commit `6bbda52` ✓
- REFACTOR gate: not needed (refactor commit served dual GREEN+cleanup role per plan; no additional cleanup required).

## Self-Check: PASSED

- FOUND: `graphify/__main__.py` (modified)
- FOUND: `tests/test_install.py` (modified)
- FOUND: commit `23d4bb4` in `git log`
- FOUND: commit `6bbda52` in `git log`
- FOUND: `.planning/phases/14-obsidian-thinking-commands/14-00-SUMMARY.md`
