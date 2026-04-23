---
phase: 08-obsidian-round-trip-awareness
fixed_at: 2026-04-12T23:45:00Z
review_path: .planning/phases/08-obsidian-round-trip-awareness/08-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 8: Code Review Fix Report

**Fixed at:** 2026-04-12T23:45:00Z
**Source review:** .planning/phases/08-obsidian-round-trip-awareness/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: _restore_user_blocks re-matches just-inserted markers when multiple blocks present

**Files modified:** `graphify/merge.py`
**Commit:** c8b7ef2
**Applied fix:** Added `search_from` offset variable that advances past each replaced region after insertion. The `_USER_SENTINEL_START_RE.search(result, search_from)` call now starts searching after the previously inserted block, preventing re-matching of markers within just-inserted user content. This is a logic fix that requires human verification.

### WR-01: Unused import of _save_manifest in export.py

**Files modified:** `graphify/export.py`
**Commit:** 1ccf983
**Applied fix:** Removed `_save_manifest` from the import list in the `to_obsidian` function. The manifest saving is handled internally by `apply_merge_plan`, so the import was dead code.

### WR-02: _has_user_sentinel_blocks lightweight check does not verify ordering

**Files modified:** `graphify/merge.py`
**Commit:** 3024c42
**Applied fix:** Replaced the simple boolean `and` check with positional comparison: now searches for both START and END markers individually, then verifies `start_match.start() < end_match.start()` to reject inverted marker order. Updated docstring to reflect the new ordering guarantee.

---

_Fixed: 2026-04-12T23:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
