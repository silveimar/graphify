---
phase: 06-graph-delta-analysis-staleness
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - graphify/__init__.py
  - graphify/__main__.py
  - graphify/delta.py
  - graphify/extract.py
  - graphify/snapshot.py
  - tests/test_delta.py
  - tests/test_snapshot.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the new snapshot persistence, graph delta computation, staleness classification, and CLI wiring for phase 6. The core logic in `delta.py` and `snapshot.py` is clean, well-structured, and follows project conventions. Provenance metadata injection in `extract.py` is minimal and correct. The CLI arg parsing in `__main__.py` has a few edge-case gaps. No security vulnerabilities found -- snapshot name sanitization is properly implemented and path handling is reasonable.

## Warnings

### WR-01: --from without --to (or vice versa) silently ignored

**File:** `graphify/__main__.py:943-957`
**Issue:** When the user provides `--from` without `--to` (or `--to` without `--from`), the code falls through to the normal snapshot-save path without any warning. The user likely intended a delta comparison and would not realize their flag was ignored.
**Fix:**
```python
# After the arg-parsing loop, before the --from/--to block:
if bool(from_path) != bool(to_path):
    print("error: --from and --to must be specified together", file=sys.stderr)
    sys.exit(2)
```

### WR-02: --cap accepts zero or negative values, which deletes all snapshots

**File:** `graphify/__main__.py:925-928`
**Issue:** `cap = int(args[i + 1])` accepts any integer. If `--cap 0` or `--cap -1` is passed, the FIFO prune in `save_snapshot` will execute `snaps[:-0]` (which is `snaps[:]` -- deletes everything including the just-saved snapshot) or `snaps[:--1]` (deletes all but the last). With `cap=0`, `snaps[:-0]` evaluates to the full list, so every snapshot including the one just saved gets deleted.
**Fix:**
```python
# In __main__.py arg parsing:
cap = int(args[i + 1])
if cap < 1:
    print("error: --cap must be at least 1", file=sys.stderr)
    sys.exit(2)
```
Also add a guard in `save_snapshot` itself:
```python
# In snapshot.py save_snapshot, before FIFO prune:
if cap < 1:
    cap = 1
```

### WR-03: --delta output path is relative to cwd, not to graph root

**File:** `graphify/__main__.py:1005`
**Issue:** When `--delta` is used (without `--from`/`--to`), the delta file is written to `Path("graphify-out/GRAPH_DELTA.md")` relative to the current working directory. However, `list_snapshots()` on line 997 is also called with no arguments, defaulting to `Path(".")`. This works when cwd is the project root, but if the user runs the command from a different directory while pointing `--graph` to an absolute path, the snapshot listing and delta output could end up in the wrong location. The `--from`/`--to` path on line 951 has the same issue.
**Fix:** Derive the output root from the resolved graph path's parent:
```python
root = gp.parent.parent  # graphify-out/graph.json -> project root
# Use root for list_snapshots(root) and output path
```

### WR-04: Floating-point mtime comparison may produce false FRESH results

**File:** `graphify/delta.py:86`
**Issue:** `current_mtime == stored_mtime` compares floats for exact equality. On some filesystems, mtime precision varies (e.g., ext3 has 1-second granularity, while APFS has nanosecond). When a snapshot is loaded from JSON and the mtime was serialized/deserialized, floating-point representation differences could cause a modified file to appear unchanged, or an unchanged file to appear modified. In the false-FRESH case: if the mtime float loses precision during JSON round-trip, a modified file could retain the same (truncated) mtime, causing the fast gate to incorrectly return FRESH without checking the hash.
**Fix:** This is mitigated by the fact that when mtime differs, the code falls through to hash comparison. The risk is limited to the narrow case where mtime precision loss makes a changed file appear unchanged. Consider using a small epsilon or always falling through to hash when the mtime was loaded from a serialized source:
```python
# Conservative: only trust mtime gate when types match exactly
if stored_mtime is not None and isinstance(stored_mtime, float) and current_mtime == stored_mtime:
    return "FRESH"
```

## Info

### IN-01: Unused import in test file

**File:** `tests/test_delta.py:4`
**Issue:** `import json` is imported but only used by `_write_graph_json`, which also imports `json_graph` from networkx. The `json` import is used on line 242 (`json.dumps`), so it is actually used. However, `import subprocess` (line 5) and `import time` (line 7) are only used by the CLI integration tests at the bottom. This is fine but worth noting for maintainability.
**Fix:** No action needed -- the imports are used. This is informational only.

### IN-02: `auto_snapshot_and_delta` always returns a delta_path (never None)

**File:** `graphify/snapshot.py:83-118`
**Issue:** The return type annotation is `tuple[Path, Path | None]`, suggesting `delta_path` can be `None`. However, the implementation always writes `GRAPH_DELTA.md` (either with delta content or a "First run" sentinel) and returns the path. The `None` case in the return type never occurs.
**Fix:** Update the return type to `tuple[Path, Path]` for accuracy, or document why `None` is kept (e.g., future use where delta generation might be skipped).

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
