---
phase: 08-obsidian-round-trip-awareness
reviewed: 2026-04-13T04:28:50Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - graphify/__main__.py
  - graphify/export.py
  - graphify/merge.py
  - tests/test_merge.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-04-13T04:28:50Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 8 adds round-trip awareness to the Obsidian vault merge pipeline: manifest I/O for tracking file hashes, user-modified detection via hash comparison, user sentinel block parsing/preservation, `--force` flag threading from CLI through `to_obsidian` into `compute_merge_plan`, and `format_merge_plan` enhancements for source annotations and a round-trip preamble.

The implementation is well-structured with thorough test coverage (the test file alone covers manifest I/O, user-modified detection, force override, user sentinel parsing, extraction/restoration, and format_merge_plan annotations). The core merge engine logic is sound and the defensive patterns (fail-loud on malformed input, graceful degradation on missing manifest) are well-executed.

One critical bug was found in user sentinel block restoration when multiple blocks are present. Two warnings and two informational items are also noted.

## Critical Issues

### CR-01: _restore_user_blocks re-matches just-inserted markers when multiple blocks present

**File:** `graphify/merge.py:371-390`
**Issue:** When `_restore_user_blocks` replaces existing USER_START/END pairs in `new_text`, it searches for the next START marker from the beginning of `result` on each iteration (line 378). After replacing the first template placeholder with a captured user block (which itself contains `<!-- GRAPHIFY_USER_START -->` and `<!-- GRAPHIFY_USER_END -->` markers), the next iteration's `_USER_SENTINEL_START_RE.search(result)` will re-match the START marker of the block that was just inserted rather than advancing to the next template placeholder. This causes the second user block to overwrite the first one's content, losing the first user block entirely.

This affects the case where a template contains 2+ empty USER_START/END placeholder pairs and the existing file had 2+ user blocks to preserve.
**Fix:**
Track a search offset to advance past the previously replaced region:
```python
if has_markers:
    result = new_text
    search_from = 0
    for block in user_blocks:
        start_match = _USER_SENTINEL_START_RE.search(result, search_from)
        if start_match is None:
            result = _append_user_block(result, block)
            continue
        end_match = _USER_SENTINEL_END_RE.search(result, start_match.end())
        if end_match is None:
            result = _append_user_block(result, block)
            continue
        result = result[:start_match.start()] + block + result[end_match.end():]
        search_from = start_match.start() + len(block)
    return result
```

## Warnings

### WR-01: Unused import of _save_manifest in export.py

**File:** `graphify/export.py:485`
**Issue:** `_save_manifest` is imported from `graphify.merge` but never used in `export.py`. The manifest saving is correctly handled inside `apply_merge_plan` (which calls `_save_manifest` internally), so the import in `export.py` is dead code. While this does not cause a runtime error, it creates a misleading dependency signal and could confuse future maintainers into thinking `export.py` manages manifest writes directly.
**Fix:**
Remove the unused import:
```python
from graphify.merge import (
    compute_merge_plan,
    apply_merge_plan,
    RenderedNote,
    split_rendered_note,
    _load_manifest,
)
```

### WR-02: _has_user_sentinel_blocks lightweight check does not verify ordering

**File:** `graphify/merge.py:321-329`
**Issue:** The docstring for `_has_user_sentinel_blocks` explicitly acknowledges that "false positives from inverted order are acceptable for the manifest boolean." However, an inverted file like `<!-- GRAPHIFY_USER_END --> ... <!-- GRAPHIFY_USER_START -->` would cause `has_user_blocks=True` in the manifest. On the next run, `compute_merge_plan` would set `source="both"` for that note (line 1003-1004), and `format_merge_plan` would display `[both]` annotation. This is misleading -- the note does not actually have valid user blocks, it has malformed sentinels. The `_parse_user_sentinel_blocks` function would correctly return `[]` for this case (orphan END is silently skipped, then START without END triggers the warning), but the manifest records a false positive.
**Fix:**
Use the full parser for the manifest boolean, or at minimum check that START appears before END:
```python
def _has_user_sentinel_blocks(body: str) -> bool:
    start_match = _USER_SENTINEL_START_RE.search(body)
    end_match = _USER_SENTINEL_END_RE.search(body)
    if not start_match or not end_match:
        return False
    return start_match.start() < end_match.start()
```

## Info

### IN-01: Frontmatter scalar regex rejects hyphenated keys

**File:** `graphify/merge.py:145`
**Issue:** `_FM_SCALAR_RE` uses `[A-Za-z_][A-Za-z0-9_]*` for key names, which does not match hyphenated keys like `date-created` or `my-custom-field`. While graphify's own emitted frontmatter uses underscore-style keys exclusively (per the codebase conventions), a user who adds hyphenated keys to a graphify-managed note would cause `_parse_frontmatter` to return `None` (malformed), which triggers `SKIP_CONFLICT` with `conflict_kind="malformed_frontmatter"`. The user would lose merge updates on that note with no obvious cause. This is documented implicitly ("hand-rolled reader" is the inverse of `_dump_frontmatter` which only emits underscore keys), but users editing notes in Obsidian may not be aware of this constraint.
**Fix:** Consider extending the regex to accept hyphens: `[A-Za-z_][A-Za-z0-9_-]*`. Alternatively, document this limitation in the CONTEXT.md or a user-facing warning.

### IN-02: Mid-level import of TypedDict at line 580

**File:** `graphify/merge.py:580`
**Issue:** `from typing import TypedDict` appears at line 580, well below the top-of-file imports (lines 1-18). While this works at runtime, it breaks the convention established by CLAUDE.md ("Imports at top: stdlib, then third-party, then local"). The `TypedDict` import should be grouped with the other `typing` imports at the top of the file.
**Fix:** Move `from typing import TypedDict` to the top imports block alongside the existing `from typing import Any, Literal` on line 9.

---

_Reviewed: 2026-04-13T04:28:50Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
