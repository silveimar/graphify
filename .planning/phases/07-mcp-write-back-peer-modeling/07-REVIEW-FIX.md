---
phase: 07-mcp-write-back-peer-modeling
fixed_at: 2026-04-12T22:15:00Z
review_path: .planning/phases/07-mcp-write-back-peer-modeling/07-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-04-12T22:15:00Z
**Source review:** .planning/phases/07-mcp-write-back-peer-modeling/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Path Traversal via record_id in _reject_proposal and _approve_and_write_proposal

**Files modified:** `graphify/__main__.py`
**Commit:** 5e76fa5
**Applied fix:** Added `.resolve()` and path confinement check in both `_reject_proposal` and `_approve_and_write_proposal` to ensure the resolved path stays within `proposals_dir`. Raises `ValueError` if record_id attempts directory traversal. Updated docstrings to document the new exception.

### WR-01: session_id Not Sanitized in Record Constructors

**Files modified:** `graphify/serve.py`
**Commit:** 58598b6
**Applied fix:** Wrapped `session_id` with `sanitize_label()` in all four record constructors: `_make_annotate_record`, `_make_flag_record`, `_make_edge_record`, and `_make_proposal_record`. This makes sanitization consistent with all other string fields.

### WR-02: Approve Writes Status Before Confirming Merge Success

**Files modified:** `graphify/__main__.py`
**Commit:** 83427ee
**Applied fix:** Added a comment documenting that the merge engine handles re-writes idempotently, and added a warning message to stderr in the except block so that if the status write fails after a successful merge, the operator gets a clear diagnostic message before the exception propagates.

### WR-03: _compact_annotations Produces File Without Trailing Newline When Empty

**Files modified:** `graphify/serve.py`
**Commit:** 076e011
**Applied fix:** Replaced the `"\n".join(...) + ("\n" if deduped else "")` pattern with the clearer `"".join(json.dumps(r, ensure_ascii=False) + "\n" for r in deduped)` pattern. Each record always gets its own trailing newline, and an empty list naturally produces an empty string.

## Skipped Issues

None -- all in-scope findings were fixed.

---

_Fixed: 2026-04-12T22:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
