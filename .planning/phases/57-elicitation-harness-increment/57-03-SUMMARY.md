---
phase: 57-elicitation-harness-increment
plan: 03
subsystem: cli, mcp, harness-import
tags: [HARN-02, security, tdd, regression-lock]
requires:
  - graphify/__main__.py:import-harness
  - graphify/output.py:is_obsidian_vault
  - graphify/serve.py:_tool_import_harness
provides:
  - "--allow-vault-write CLI flag on graphify import-harness"
  - "vault-rooted-output refusal guard (HARN-02 #1)"
  - "AST allowlist regression test (HARN-02 #2)"
  - "MCP empty-path refusal regression lock (HARN-02 #3)"
affects:
  - tests/test_harness_import.py
  - tests/test_mcp_harness_io.py
  - graphify/__main__.py
tech-stack:
  added: []
  patterns:
    - argparse store_true flag mirroring --strict
    - sys.exit(2) refusal with [graphify] stderr prefix
    - subprocess + monkeypatch.chdir CLI smoke test
    - ast.walk Name/Attribute scan for call-site allowlist
    - source-substring assertion to avoid closure-construction overhead
key-files:
  created: []
  modified:
    - tests/test_harness_import.py
    - tests/test_mcp_harness_io.py
    - graphify/__main__.py
decisions:
  - "Vault-output guard belongs CLI-side, not in harness_import.py library (Pitfall 1, RESEARCH.md)."
  - "Test 2 places src inside vault so artifacts_root validation passes — exercises the guard, not source-path validation."
  - "AST allowlist uses subset (`<=`) so the definition site (harness_import.py) is permitted; new files trigger failure."
  - "MCP test uses source-substring assertion (Pitfall 4) — closure-bound handler not cheaply invocable in unit tests."
metrics:
  duration: ~10 min
  completed: 2026-05-03
  tasks: 3
  commits: 4
  tests_added: 4
  tests_passing: 2090
---

# Phase 57 Plan 03: HARN-02 Off-by-Default Vault-Write Guard Summary

Implemented `--allow-vault-write` argparse flag on `graphify import-harness` with vault-rooted-output refusal guard, plus regression-lock tests for all three HARN-02 guarantees (vault refusal CLI, AST auto-invocation allowlist, MCP explicit-path).

## Tasks Completed

### Task 1: TDD RED → GREEN — vault-output refusal CLI guard

**RED commit** `427f729` — `test(57-03): add failing HARN-02 vault-output guard tests`
- Added `test_import_refuses_vault_rooted_output`: subprocess invocation of `import-harness ... --output <vault>` must exit non-zero with `vault` and `--allow-vault-write` substrings in stderr.
- Added `test_import_accepts_vault_with_explicit_flag`: same invocation with `--allow-vault-write` exits 0 and writes `harness_import.json` under the vault.
- Both tests failed as expected: refusal substring not in stderr / unrecognized argparse argument.

**GREEN commit** `32a384a` — `feat(57-03): refuse vault-rooted import-harness output unless --allow-vault-write`
- Added `--allow-vault-write` argparse flag in `graphify/__main__.py` after `--strict`.
- Inserted guard immediately after `_resolve_cli_paths` returns and before `artifacts.mkdir`:
  ```python
  from graphify.output import is_obsidian_vault
  if not opts.allow_vault_write and is_obsidian_vault(artifacts):
      print(f"[graphify] refusing to write harness import under vault root {artifacts}; "
            "pass --allow-vault-write to override", file=sys.stderr)
      sys.exit(2)
  ```
- Test 2 src placement adjusted to live inside the vault so `validate_graph_path` accepts it (the test exercises the guard, not source-path validation).
- `python -m graphify import-harness --help` now advertises `--allow-vault-write`.

**REFACTOR**: skipped — addition is two surgical edits matching existing `--strict` pattern.

### Task 2: AST auto-invocation allowlist guard test (HARN-02 #2)

**Commit** `b57974a` — `test(57-03): add HARN-02 AST allowlist guard for import_harness call sites`
- Added `test_no_auto_invocation_of_import_harness`: walks `graphify/**/*.py` AST, collects every file referencing `import_harness_path` or `import_harness_bytes` via `ast.Name` or `ast.Attribute`, and asserts the set is `<=` `{__main__.py, serve.py, harness_import.py}`.
- Pre-test sanity confirmed exactly those three files reference the functions today.
- Subset comparison ensures the definition site is allowed; failure includes the violating set for fast diagnosis.

### Task 3: MCP empty-path refusal regression lock (HARN-02 #3)

**Commit** `90640c8` — `test(57-03): lock MCP import_harness empty-path refusal (HARN-02 guarantee 3)`
- Added `test_mcp_import_harness_refuses_empty_path` to `tests/test_mcp_harness_io.py`.
- Source-substring assertions on `graphify/serve.py`:
  - `(arguments or {}).get("path") or ""` (defensive read)
  - `validate_graph_path(Path(raw_path), base=_out_dir)` (rejects empty)
  - `"status": "error"` (structured error response)
- Mirrors the existing `test_serve_handlers_reference_library_functions` pattern; avoids closure construction (Pitfall 4).

## Verification

```
pytest tests/test_harness_import.py tests/test_mcp_harness_io.py -q  →  14 passed
pytest tests/ -q                                                      →  2090 passed, 1 xfailed
python -m graphify import-harness --help | grep -- '--allow-vault-write'  →  flag advertised
```

Acceptance criteria from plan:

- [x] `grep -c '"--allow-vault-write"' graphify/__main__.py` ≥ 1 (1)
- [x] `grep -c "is_obsidian_vault(artifacts)" graphify/__main__.py` == 1
- [x] `grep -c "refusing to write harness import under vault root" graphify/__main__.py` == 1
- [x] `grep -c "sys.exit(2)" graphify/__main__.py` ≥ 3 (25 — well above lower bound)
- [x] `grep -c "def test_import_refuses_vault_rooted_output" tests/test_harness_import.py` == 1
- [x] `grep -c "def test_import_accepts_vault_with_explicit_flag" tests/test_harness_import.py` == 1
- [x] `grep -c "def test_no_auto_invocation_of_import_harness" tests/test_harness_import.py` == 1
- [x] `grep -c "def test_mcp_import_harness_refuses_empty_path" tests/test_mcp_harness_io.py` == 1
- [x] All four new tests pass.
- [x] Two atomic git commits exist for Task 1 (RED `test:` + GREEN `feat:`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_import_accepts_vault_with_explicit_flag src placement**
- **Found during:** Task 1 GREEN
- **Issue:** Plan specified `src = tmp_path / "harness_memory.v1.json"` (outside vault). With `--output <vault>`, `import_harness_path` validates the source via `validate_graph_path(src, base=artifacts_root=vault)` — src outside vault → rejection regardless of the new guard.
- **Fix:** Placed `src = vault / "harness_memory.v1.json"` so the source lives inside `artifacts_root`. The test now exercises the guard exclusively, not source-path validation.
- **Files modified:** `tests/test_harness_import.py`
- **Commit:** `32a384a` (rolled into GREEN commit since the change is what enables GREEN)

## TDD Gate Compliance

- RED gate: `427f729` (`test(57-03): add failing HARN-02 vault-output guard tests`)
- GREEN gate: `32a384a` (`feat(57-03): refuse vault-rooted import-harness output unless --allow-vault-write`)
- REFACTOR gate: skipped (no refactor needed — two surgical edits matching existing patterns).

## HARN-02 Closure

All three HARN-02 guarantees are now testably locked:

| Guarantee | Lock |
|-----------|------|
| #1 vault refusal off by default | `test_import_refuses_vault_rooted_output` + `test_import_accepts_vault_with_explicit_flag` (CLI flag + guard) |
| #2 no auto-invocation | `test_no_auto_invocation_of_import_harness` (AST allowlist) |
| #3 MCP explicit path required | `test_mcp_import_harness_refuses_empty_path` (source-substring lock) |

## Self-Check

- FOUND: `.planning/phases/57-elicitation-harness-increment/57-03-SUMMARY.md` (this file, just written)
- FOUND commit `427f729` (RED)
- FOUND commit `32a384a` (GREEN feat)
- FOUND commit `b57974a` (AST allowlist)
- FOUND commit `90640c8` (MCP regression lock)

## Self-Check: PASSED
