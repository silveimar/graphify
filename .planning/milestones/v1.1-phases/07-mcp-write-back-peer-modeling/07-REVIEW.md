---
phase: 07-mcp-write-back-peer-modeling
reviewed: 2026-04-13T02:49:25Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - graphify/serve.py
  - tests/test_serve.py
  - tests/test_approve.py
  - graphify/__main__.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-13T02:49:25Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 07 adds MCP write-back capabilities (annotate, flag, add_edge, propose_vault_note) and a CLI approve subcommand. The code is well-structured with good patterns: atomic file writes via os.replace, input sanitization via sanitize_label, sidecar-only persistence (never mutating graph.json), and clean separation between record constructors and persistence. Tests are thorough.

Key concerns: a path traversal vulnerability in the approve flow via unsanitized record_id used in file paths, a race condition between approve status write and the merge engine, and session_id not being sanitized while other string fields are.

## Critical Issues

### CR-01: Path Traversal via record_id in _reject_proposal and _approve_and_write_proposal

**File:** `graphify/__main__.py:752`
**Issue:** Both `_reject_proposal` and `_approve_and_write_proposal` construct file paths using `record_id` directly from CLI input (`target_id = args[i]` at line 1181) without any validation. A malicious record_id like `../../etc/something` would construct a path outside the proposals directory. While `_save_proposal` in serve.py uses a UUID-generated record_id (safe), the CLI approve path accepts arbitrary user input as record_id and uses it to build `proposals_dir / f"{record_id}.json"`.

The path.exists() check at line 753/799 prevents writing to non-existent paths, but if an attacker can place a file at a traversed path, they could get it read and rewritten. More practically, this violates the security model where all paths should be confined.
**Fix:**
```python
def _reject_proposal(proposals_dir: Path, record_id: str) -> dict:
    # Validate record_id is a simple filename (UUID format)
    path = (proposals_dir / f"{record_id}.json").resolve()
    if not str(path).startswith(str(proposals_dir.resolve())):
        raise ValueError(f"Invalid proposal ID: {record_id}")
    if not path.exists():
        raise FileNotFoundError(f"Proposal not found: {record_id}")
    ...
```

Apply the same confinement check in `_approve_and_write_proposal` at line 798.

## Warnings

### WR-01: session_id Not Sanitized in Record Constructors

**File:** `graphify/serve.py:85`
**Issue:** In `_make_annotate_record`, `_make_flag_record`, and `_make_edge_record`, every string field is passed through `sanitize_label()` except `session_id`. While session_id is currently generated server-side as a UUID (line 339), the record constructors are public functions that could be called with arbitrary session_id values. This inconsistency could lead to control characters in the JSONL output if the functions are reused.
**Fix:**
```python
"session_id": sanitize_label(session_id),
```

Apply to all three record constructors (lines 85, 100, 114) and `_make_proposal_record` (line 139).

### WR-02: Approve Writes Status Before Confirming Merge Success

**File:** `graphify/__main__.py:826-834`
**Issue:** In `_approve_and_write_proposal`, the merge engine is called (lines 826-827), and then the proposal status is set to "approved" (line 830). If `apply_merge_plan` partially succeeds (writes some files but throws on others), the proposal is never marked as approved, which is the safe direction. However, the inverse is not guarded: if the status write itself fails after the merge has already written files to the vault, the proposal stays "pending" while vault files exist. A re-run would attempt to write again. This is a minor consistency issue since the merge engine likely handles idempotent writes, but it should be documented or addressed.
**Fix:** Add a comment documenting this is intentional (merge engine handles re-writes idempotently), or wrap in a try that logs a warning if the status update fails after a successful merge.

### WR-03: _compact_annotations Produces File Without Trailing Newline When Empty

**File:** `graphify/serve.py:46`
**Issue:** The expression `("\n" if deduped else "")` means an empty deduped list writes an empty file. However, the `"\n".join(...)` for a non-empty list produces records separated by newlines but the trailing newline is only added by the ternary. For a single record, this produces `{json}\n` which is correct. But the join for multiple records produces `{json1}\n{json2}\n` -- this is correct JSONL. No actual bug, but the logic is subtle and could break if the join separator changes. Consider using a simpler pattern.
**Fix:**
```python
tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in deduped), encoding="utf-8")
```

This is clearer: each record always gets its own trailing newline, and an empty list produces an empty string.

## Info

### IN-01: Unused Variable `safe` in _load_graph

**File:** `graphify/serve.py:199`
**Issue:** The variable `safe = resolved` on line 199 is assigned but serves no purpose -- `data` is read from `safe.read_text()` on line 200, but `safe` is just an alias for `resolved`. This appears to be a leftover from a removed path-confinement check.
**Fix:** Replace `safe` with `resolved` directly:
```python
data = json.loads(resolved.read_text(encoding="utf-8"))
```

### IN-02: Inline Import of `os` in _reject_proposal

**File:** `graphify/__main__.py:755`
**Issue:** `import os as _os` is done inside `_reject_proposal` and `_approve_and_write_proposal`. The module already imports `sys` and other stdlib modules at the top level. This inline import pattern is unusual for `os` which is a lightweight stdlib module.
**Fix:** Add `import os` to the top-level imports of `__main__.py` and remove the inline imports at lines 755 and 797.

---

_Reviewed: 2026-04-13T02:49:25Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
