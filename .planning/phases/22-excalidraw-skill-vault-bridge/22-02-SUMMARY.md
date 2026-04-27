---
phase: 22
plan: 02
subsystem: excalidraw-skill-vault-bridge
tags: [skill, excalidraw, install, platform-config, packaging]
requires: [22-01 (skill-excalidraw.md authored, install xfails landed)]
provides: [SKILL-01, SKILL-02, SKILL-03]
affects: [graphify/__main__.py, pyproject.toml, tests/test_install.py]
tech-stack:
  added: []
  patterns: [dict-driven-platform-dispatch, package-data-bundling, xfail-flip]
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - pyproject.toml
    - tests/test_install.py
decisions: [D-04, D-05, D-06, D-07]
metrics:
  duration: ~5 min
  completed: 2026-04-27
  tasks_completed: 1
  files_changed: 3
  files_created: 0
---

# Phase 22 Plan 02: Excalidraw Install/Uninstall Wiring Summary

Add `excalidraw` to `_PLATFORM_CONFIG`, ship `skill-excalidraw.md` in the wheel, flip 6 xfail markers — `graphify install excalidraw` now writes `~/.claude/skills/excalidraw-diagram/SKILL.md` and `graphify uninstall excalidraw` removes it (both idempotent, both isolated from existing platforms).

## Files

| File | Status | Change | Role |
|------|--------|--------|------|
| `graphify/__main__.py` | modified | +10 lines | New `excalidraw` entry in `_PLATFORM_CONFIG`, inserted between `antigravity` and `windows` per D-04/D-05 |
| `pyproject.toml` | modified | +1 token | `"skill-excalidraw.md"` appended to `[tool.setuptools.package-data] graphify` list (between `skill-trae.md` and `builtin_templates/*.md`) |
| `tests/test_install.py` | modified | -6 xfail markers | Removed `@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")` from the 6 install/uninstall/idempotency/isolation/platform-config tests |

## `_PLATFORM_CONFIG` Diff

```python
"antigravity": { ... },
+ # D-04/D-05: excalidraw skill platform — claude_md=False (no CLAUDE.md anchor needed)
+ "excalidraw": {
+     "skill_file": "skill-excalidraw.md",
+     "skill_dst": Path(".claude") / "skills" / "excalidraw-diagram" / "SKILL.md",
+     "claude_md": False,
+     "commands_src_dir": "commands",
+     "commands_dst": None,
+     "commands_enabled": False,
+     "supports": ["obsidian", "code"],
+ },
"windows": { ... },
```

## `pyproject.toml` Diff

```diff
-graphify = ["skill.md", ..., "skill-trae.md", "builtin_templates/*.md", ...]
+graphify = ["skill.md", ..., "skill-trae.md", "skill-excalidraw.md", "builtin_templates/*.md", ...]
```

## Handlers NOT Modified — Confirmed

The install handler (`graphify/__main__.py:230–286`) and uninstall handler (`graphify/__main__.py:289–310`) are dict-driven via `cfg = _PLATFORM_CONFIG[platform]`. Adding the new key propagates automatically — exactly the precedent set by `antigravity` (Plan 22-01 RESEARCH Pitfall 6 + D-06).

`git diff --stat HEAD~1 -- graphify/__main__.py` confirms the only change in `__main__.py` is the new dict entry. No handler logic touched.

## Test Count Delta

- Before plan 22-02: 1577 collected, 1566 passed, 7 xfail (1 schema-traversal kept; 6 install wiring deferred).
- After plan 22-02: 1577 collected, 1576 passed, 1 xfail (only the schema-traversal xfail intentionally kept by Plan 22-01 spec). Net: +10 passing, -6 xfail.

`pytest tests/test_install.py -x -q` → 67 passed in 0.22s.
`pytest tests/ -q` → 1576 passed, 1 xfailed in 45.45s.
`pytest tests/test_denylist.py::test_no_lzstring_import_anywhere -x -q` → 1 passed.

## Decisions Honored

- **D-04 (positional surface):** `graphify install excalidraw` / `graphify uninstall excalidraw` — no `--excalidraw` flag introduced. CLI dispatch remains positional through the existing `platform` argument.
- **D-05 (platform shape):** `claude_md=False`, `commands_enabled=False`, `supports=["obsidian", "code"]`.
- **D-06 (dict-driven dispatch):** No handler code modified — adding a `_PLATFORM_CONFIG` key is sufficient. Verified by full suite + the `antigravity` precedent.
- **D-07 (isolation):** `test_install_excalidraw_does_not_touch_claude_skill` passes — installing `excalidraw` leaves `~/.claude/skills/graphify/SKILL.md` from the `claude` install untouched.

## Commits

- `67aaa59` feat(22-02): wire excalidraw platform install/uninstall surface

## mcp_excalidraw / LZ-String Boundary

```
$ grep -rE "import.*mcp_excalidraw|from.*mcp_excalidraw|import.*lzstring|from.*lzstring" graphify/ --include='*.py'
(no matches)
```

The two `mcp_excalidraw` / `lzstring` mentions remain exclusively in `graphify/skill-excalidraw.md` — never imported in graphify Python. `tests/test_denylist.py::test_no_lzstring_import_anywhere` still green.

## Deviations from Plan

None — plan executed exactly as written. Single task, single commit, all acceptance criteria met on first test run.

## Phase 22 End-of-Phase Status

- SKILL-01 (install writes skill): ✅ `test_install_excalidraw`
- SKILL-02 (uninstall removes skill): ✅ `test_uninstall_excalidraw`
- SKILL-03 (both idempotent): ✅ `test_install_excalidraw_idempotent`, `test_uninstall_excalidraw_idempotent`
- SKILL-04, SKILL-05, SKILL-06 (skill body, layout fallback, ordering): ✅ delivered Plan 22-01
- D-07 isolation: ✅ `test_install_excalidraw_does_not_touch_claude_skill`
- Skill in wheel: ✅ `test_excalidraw_skill_in_package`
- Platform-config shape: ✅ `test_platform_config_has_excalidraw`

Phase 22 ready for `/gsd-verify-work`.

## Self-Check: PASSED

- `graphify/__main__.py` modified (commit `67aaa59`): FOUND
- `pyproject.toml` modified (commit `67aaa59`): FOUND
- `tests/test_install.py` modified (commit `67aaa59`): FOUND
- Commit `67aaa59` exists: FOUND
- `_PLATFORM_CONFIG["excalidraw"]` exists with required shape: FOUND (verified via `python -c`)
- `skill-excalidraw.md` in pyproject `package-data`: FOUND
- Full pytest suite green: FOUND (1576 passed, 1 xfail pre-existing)
- LZ-String denylist green: FOUND
