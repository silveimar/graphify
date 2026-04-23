---
phase: 11-narrative-mode-slash-commands
plan: "06"
subsystem: install
tags: [install, packaging, cli, phase-11, commands, platform-config]
dependency_graph:
  requires: [11-04, 11-05]
  provides: [command-file-install-path, package-data-commands]
  affects: [graphify/__main__.py, pyproject.toml]
tech_stack:
  added: []
  patterns: [shutil.copy for command file install, Path.home() patching for test isolation]
key_files:
  created: []
  modified:
    - graphify/__main__.py
    - pyproject.toml
    - tests/test_install.py
    - tests/test_pyproject.py
decisions:
  - "_PLATFORM_CONFIG extended in place — no new data structure needed; three new keys (commands_src_dir, commands_dst, commands_enabled) added to each of the 11 platform dicts"
  - "New top-level uninstall() function added alongside install() — only removes known Phase 11 filenames, not a glob-delete (T-11-06-02 mitigation)"
  - "windows platform commands_enabled=True with same .claude/commands/ destination as claude — plan-checker BLOCKER 3 fix per RESEARCH.md §Install Path Extension"
  - "install() renamed internal content variable from content to _content to avoid shadowing outer scope when reading CLAUDE.md"
metrics:
  duration_seconds: 400
  completed_date: "2026-04-17"
  tasks_completed: 3
  files_modified: 4
---

# Phase 11 Plan 06: Install Path Extension Summary

Ship the 5 Phase 11 command files to users via `graphify install` by extending `_PLATFORM_CONFIG` with commands keys, adding install/uninstall helpers, wiring `--no-commands`, and adding `commands/*.md` to pyproject.toml package-data.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend `_PLATFORM_CONFIG` + add helpers | c00442f | graphify/__main__.py |
| 2 | Add `commands/*.md` to pyproject.toml | 8c94bb2 | pyproject.toml |
| 3 | Extend test_install.py + test_pyproject.py | 0740a75 | tests/test_install.py, tests/test_pyproject.py |

## What Was Built

### `_PLATFORM_CONFIG` extension (graphify/__main__.py)

Three new keys added to each of the 11 platform entries:

- `"commands_src_dir": "commands"` — subdirectory of the graphify package containing command .md files
- `"commands_dst": Path(".claude") / "commands"` or `None` — relative-to-home install destination
- `"commands_enabled": True | False`

**Platforms with `commands_enabled=True`** (plan-checker BLOCKER 3 fix):
- `claude`: `.claude/commands/`
- `windows`: `.claude/commands/` (same as claude — Windows users share Claude Code's native commands convention)

**All other platforms** (`codex`, `opencode`, `aider`, `copilot`, `claw`, `droid`, `trae`, `trae-cn`, `antigravity`): `commands_enabled=False`, `commands_dst=None`.

### `_install_commands` / `_uninstall_commands` helpers

- `_install_commands(cfg, src_dir, *, verbose=True)`: Copies all `*.md` files from `src_dir` to `Path.home() / cfg["commands_dst"]`, creating dirs as needed. No-ops when `commands_enabled=False` or `commands_dst=None`.
- `_uninstall_commands(cfg, *, verbose=True)`: Removes only the specific known Phase 11 filenames (`context.md`, `trace.md`, `connect.md`, `drift.md`, `emerge.md`, `ghost.md`, `challenge.md`) — never a glob-delete (T-11-06-02 mitigation).

### `install()` and `uninstall()` modifications

- `install(platform, no_commands=False)`: Added `no_commands` kwarg. Calls `_install_commands` after skill-file copy unless suppressed.
- `uninstall(platform, no_commands=False)`: New top-level function that removes skill file + version marker then calls `_uninstall_commands` unless suppressed.
- `main()`: Parses `--no-commands` from `sys.argv` before dispatch, removes it, passes `no_commands=True/False` to `install()`.

### pyproject.toml package-data

`"commands/*.md"` appended to `[tool.setuptools.package-data] graphify`. The 5 command files from plan 11-04 now ship with wheel installs.

### Tests added

**tests/test_install.py** (6 new tests):
- `test_install_command_files_claude` — 5 files land in `tmp_path/.claude/commands/`
- `test_install_command_files_windows` — same 5 files, platform=windows (BLOCKER 3 regression guard)
- `test_install_no_commands_flag` — `no_commands=True` skips file copy
- `test_install_idempotent_commands` — double install does not raise
- `test_uninstall_removes_commands` — files gone after uninstall
- `test_install_non_claude_platform_skips_commands` — codex install does not create `.claude/commands/`

**tests/test_pyproject.py** (1 new test):
- `test_package_data_includes_commands` — `commands/*.md` in package-data

## Verification

```
pytest tests/test_install.py tests/test_pyproject.py -q
50 passed in 0.13s

python -m graphify --help   # exits 0, CLI functional
python3 -c "import tomli; tomli.load(open('pyproject.toml','rb'))"   # valid TOML
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Shadowed `content` variable in install()**
- **Found during:** Task 1 implementation
- **Issue:** The plan's code snippet for `install()` read CLAUDE.md into a variable also named `content`, which would shadow the outer file-read `content` variable if any future refactor merged them. The existing code already used `content` as the CLAUDE.md read variable.
- **Fix:** Renamed the inner variable to `_content` in the modified `install()` to avoid any shadowing risk.
- **Files modified:** graphify/__main__.py

**2. [Rule 2 - Missing functionality] Top-level `uninstall()` function**
- **Found during:** Task 1 — the plan says "Modify `uninstall()` similarly" but no top-level `uninstall()` existed in the codebase.
- **Fix:** Added a new `uninstall(platform, no_commands=False)` function alongside `install()`. Tests call `uninstall(platform="claude")` directly so this was required for correctness.
- **Files modified:** graphify/__main__.py

## Known Stubs

None — all command files were created in plan 11-04 and are now fully wired.

## Threat Flags

None — install path confined to `Path.home() / cfg["commands_dst"]` with no user-supplied path component (T-11-06-01 resolved). Uninstall uses explicit filenames not glob-delete (T-11-06-02 resolved).

## Self-Check: PASSED

- graphify/__main__.py: FOUND (c00442f)
- pyproject.toml: FOUND (8c94bb2)
- tests/test_install.py: FOUND (0740a75)
- tests/test_pyproject.py: FOUND (0740a75)
- 50 tests pass
