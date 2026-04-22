---
phase: quick-260422-jdj
plan: 01
subsystem: capability-manifest
tags: [bugfix, path-collision, incremental-detect, phase-13]
requires: []
provides: [capability.json-writer-path, manifest-collision-regression-test]
affects: [graphify/capability.py, graphify/export.py, graphify/skill.md, graphify/skill-codex.md, tests/test_capability.py]
tech-stack:
  added: []
  patterns: [atomic-write-.tmp-os.replace, tdd-red-green]
key-files:
  created: []
  modified:
    - graphify/capability.py
    - graphify/export.py
    - graphify/skill.md
    - graphify/skill-codex.md
    - tests/test_capability.py
decisions:
  - "Rename capability writer target to graphify-out/capability.json (detect owns manifest.json)"
  - "Add dedicated regression test so a future re-collision fails CI immediately"
metrics:
  duration: ~5min
  completed: 2026-04-22
requirements: [BUGFIX-MANIFEST-COLLISION]
---

# Quick Task 260422-jdj: Fix manifest.json Path Collision Summary

**One-liner:** Rename Phase 13 capability manifest from `graphify-out/manifest.json` to `graphify-out/capability.json` so it stops clobbering `detect.py`'s incremental mtime manifest at the same path.

## Files Changed

| File | Change |
|------|--------|
| `graphify/capability.py` | `write_manifest_atomic` now targets `out_dir / "capability.json"`; docstrings on `write_manifest_atomic` and `write_runtime_manifest` updated; atomic `.tmp` + `os.replace` semantics preserved. |
| `graphify/export.py` | Error message in `to_json`'s `write_runtime_manifest` guard now references `graphify-out/capability.json`. |
| `graphify/skill.md` | Frontmatter `capability_manifest:` value changed to `graphify-out/capability.json` (line 5). |
| `graphify/skill-codex.md` | Same frontmatter change (line 5). |
| `tests/test_capability.py` | Renamed `test_pipeline_writes_manifest_json` → `test_pipeline_writes_capability_json`; asserts `capability.json` exists AND `manifest.json` does NOT exist (negative regression). Added `test_capability_writer_basename_is_not_manifest_json` as a dedicated regression guard on the writer's target basename. |

## detect.py Invariant — Confirmed Untouched

`graphify/detect.py:19` still reads exactly:
```python
_MANIFEST_PATH = "graphify-out/manifest.json"
```
No modifications. The incremental mtime manifest owner and path are preserved exactly as-is, so users with existing on-disk `graphify-out/manifest.json` files continue to get correct skip-unchanged-files behavior.

## Grep Confirmation

```
$ grep -rn "manifest.json" graphify/ tests/ | grep -v vault-manifest | grep -v file-manifest | grep -v capability_manifest.schema.json
graphify/capability.py:230:    Renamed from manifest.json in quick-260422-jdj to eliminate the path
graphify/capability.py:232:    graphify-out/manifest.json. Atomic write semantics (``.tmp`` + os.replace)
graphify/detect.py:19:_MANIFEST_PATH = "graphify-out/manifest.json"
tests/test_capability.py:61:    to graphify-out/manifest.json, colliding with detect.py's incremental mtime
tests/test_capability.py:63:    the detect incremental manifest remains at manifest.json.
tests/test_capability.py:75:    # Negative assertion: the capability writer MUST NOT clobber manifest.json
tests/test_capability.py:77:    assert not (tmp_path / "manifest.json").exists()
tests/test_capability.py:80:def test_capability_writer_basename_is_not_manifest_json(tmp_path: Path) -> None:
tests/test_capability.py:81:    """Regression (quick-260422-jdj): capability writer MUST NOT target 'manifest.json'
tests/test_capability.py:82:    (collides with detect incremental manifest at graphify-out/manifest.json)."""
tests/test_capability.py:85:    assert target.name != "manifest.json"
tests/test_capability.py:86:    assert not (tmp_path / "manifest.json").exists()
tests/test_merge.py:1527:        manifest_path = tmp_path / "nonexistent-manifest.json"
```

Classification of remaining hits:
- **`graphify/detect.py:19`** — the single legitimate live reference (detect owns `manifest.json`); unchanged by this fix.
- **`graphify/capability.py` lines 230,232** — docstring narrative describing the rename (cosmetic; not live paths).
- **`tests/test_capability.py` lines 61,63,75,77,80,81,82,85,86** — regression test text / negative assertions that `manifest.json` must NOT exist after capability writer runs.
- **`tests/test_merge.py:1527`** — unrelated Phase 8 merge test referencing `nonexistent-manifest.json` (different context, out of scope).

No stray capability-related `manifest.json` references remain.

## Test Results

```
$ pytest tests/test_capability.py -q
....................                                                     [100%]
20 passed in 0.61s

$ pytest tests/ -q
... 1370 passed, 2 warnings in 45.67s
```

Both the renamed `test_pipeline_writes_capability_json` and the new `test_capability_writer_basename_is_not_manifest_json` regression guard pass. No regressions anywhere else (full 1370-test suite green, including detect, export, and skill-parsing tests).

## Commits

- `f7c415f` — `test(quick-260422-jdj): add failing regression tests for capability.json rename` (TDD RED gate)
- `9a52fa7` — `fix(quick-260422-jdj): rename capability manifest to capability.json to unblock detect incremental` (TDD GREEN gate)

## Deviations from Plan

None beyond trivial naming: the plan referenced `_write_manifest` / `_build_and_write_manifest` as the function names, but the actual code uses `write_manifest_atomic` / `write_runtime_manifest`. The intent (rename the target path from `manifest.json` to `capability.json`) was applied to the real function names. All other plan actions executed verbatim.

## Critical Invariants — Confirmed

- `detect.py` line 19 `_MANIFEST_PATH = "graphify-out/manifest.json"` — untouched.
- `graphify/merge.py` `vault-manifest.json` — not touched (not in changed files).
- Atomic write semantics in `capability.py` (`.tmp` + `os.replace`) — preserved exactly.

## Self-Check: PASSED

- Files created/modified exist on disk: confirmed via `git log --name-only 9a52fa7`.
- Commit hashes `f7c415f` and `9a52fa7` present in `git log --oneline`.
- Regression test `test_capability_writer_basename_is_not_manifest_json` asserts divergence and will fail if the paths ever re-collide.
