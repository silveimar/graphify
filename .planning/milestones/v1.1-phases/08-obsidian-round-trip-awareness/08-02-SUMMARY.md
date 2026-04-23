---
phase: 08-obsidian-round-trip-awareness
plan: "02"
subsystem: merge-engine
tags: [user-sentinel-blocks, merge-engine, d-08, preservation, round-trip]
dependency_graph:
  requires: [08-01]
  provides: [user-sentinel-parser, user-block-extraction, user-block-restoration, has-user-blocks-manifest-field]
  affects: [graphify/merge.py, tests/test_merge.py]
tech_stack:
  added: []
  patterns: [extract-before-rewrite-restore-after, regex-sentinel-pattern, malformed-graceful-degradation]
key_files:
  created: []
  modified:
    - graphify/merge.py
    - tests/test_merge.py
decisions:
  - "D-03 resolved (Claude's Discretion): multiple USER_START/END pairs per note supported — simpler for users and equally simple to implement"
  - "D-08 implemented: user sentinel blocks inviolable even for REPLACE strategy and within UPDATE's graphify-block merge layer"
  - "Malformed sentinels (START without END, nested) warn to stderr and return [] — note treated as having no user blocks (D-02)"
  - "_restore_user_blocks appends blocks at end when new_text has no empty sentinel pairs — survives template structure changes"
  - "apply_merge_plan now reads existing_text for REPLACE as well as UPDATE so _synthesize_file_text can extract user blocks"
  - "has_user_blocks stub (Plan 01) resolved: _build_manifest_from_result now calls _has_user_sentinel_blocks on written file content"
metrics:
  duration: ~3min
  completed_date: "2026-04-13"
  tasks_completed: 1
  files_modified: 2
  tests_added: 12
---

# Phase 8 Plan 02: User Sentinel Parser and Preservation Summary

**One-liner:** User sentinel blocks (`<!-- GRAPHIFY_USER_START/END -->`) parsed, extracted, and restored through REPLACE and UPDATE merge actions; `has_user_blocks` manifest field now correctly computed from file content.

## What Was Built

### Task 1: User sentinel parser, preservation in _synthesize_file_text, and has_user_blocks in manifest

Seven additions/changes to `graphify/merge.py`:

**New regex patterns** (near existing graphify sentinel regexes):
- `_USER_SENTINEL_START_RE` and `_USER_SENTINEL_END_RE` — match `<!-- GRAPHIFY_USER_START/END -->` with whitespace tolerance. Uppercase naming ensures no collision with graphify's lowercase `graphify:name:start/end` patterns.

**`_parse_user_sentinel_blocks(body: str) -> list[tuple[int, int, str]]`**
Scans body lines for START/END marker pairs, returns list of `(start_line_idx, end_line_idx, content_between)` tuples. Multiple pairs supported. Malformed cases (START without END, nested STARTs) print `[graphify] malformed user sentinel: ...` to stderr and return `[]` — the note is treated as having no user blocks (D-02). Empty list = no user blocks.

**`_has_user_sentinel_blocks(body: str) -> bool`**
Lightweight check: both regexes must match. Used by `_build_manifest_from_result` to set the `has_user_blocks` manifest field without running the full parser.

**`_extract_user_blocks(text: str) -> list[str]`**
Calls `_parse_user_sentinel_blocks`, then slices the original text lines to produce full block strings including marker lines. Used before rewriting a file to capture user content.

**`_restore_user_blocks(new_text: str, user_blocks: list[str]) -> str`** + **`_append_user_block`**
If `new_text` contains existing sentinel marker pairs, replaces them in order with captured blocks. If no markers in `new_text`, appends blocks at the end. This ensures user content survives even when the template structure changes between graphify runs.

**`_synthesize_file_text` extended** for D-08:
- REPLACE branch: calls `_extract_user_blocks(existing_text)` then `_restore_user_blocks` after generating new text. User sentinel content survives even when `strategy=replace` or `--force` is used.
- UPDATE branch: same extract+restore layer sits on top of the graphify-sentinel merge (`_merge_body_blocks`). User blocks and graphify blocks are independently managed.

**`apply_merge_plan` extended**: condition changed from `if action.action == "UPDATE"` to `if action.action in ("UPDATE", "REPLACE")` for reading `existing_text`. REPLACE now passes the existing file's text to `_synthesize_file_text` so user blocks can be extracted.

**`_build_manifest_from_result` stub resolved**: `"has_user_blocks": False` placeholder replaced with `_has_user_sentinel_blocks(path.read_text(...))` — correctly reflects actual file state after each merge run.

## Tests Added

`TestUserSentinelParser` (6 tests):
- `test_single_pair` — one START/END pair returns one tuple with correct content
- `test_multiple_pairs` — two pairs returns two tuples, each with correct content
- `test_no_sentinels` — body with no markers returns empty list
- `test_malformed_start_no_end` — START without END returns `[]` and warns to stderr
- `test_nested_start` — two STARTs before END returns `[]` and warns to stderr
- `test_whitespace_tolerance` — extra spaces in marker comment still match

`TestUserSentinelPreservation` (6 tests):
- `test_replace_preserves_user_blocks` — full integration via `_synthesize_file_text` with REPLACE strategy
- `test_update_preserves_user_blocks` — same with UPDATE strategy and changed `source_file`
- `test_create_has_no_user_blocks` — CREATE produces clean output, no spurious markers
- `test_extract_restore_roundtrip` — extract from source text, restore into different text, verify content and markers intact
- `test_has_user_blocks_in_manifest` — `apply_merge_plan` on a file with user sentinels → manifest `has_user_blocks=True`
- `test_no_sentinels_manifest_false` — file without sentinels → `has_user_blocks=False`

**Total tests after plan:** 136 in `test_merge.py` (12 new, 124 existing — all still green); 978 passing across full suite.

## Commits

- `5c14f8f` — feat(08-02): user sentinel parser, extraction, restoration, and manifest has_user_blocks

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the Plan 01 stub (`has_user_blocks: False`) has been resolved in this plan.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All user sentinel content is preserved as-is with no interpretation (T-08-05 mitigated). Malformed sentinels return `[]` gracefully (T-08-06 mitigated). File sizes are bounded by existing graphify limits (T-08-07 accepted).

## Self-Check: PASSED

- `graphify/merge.py` contains `_USER_SENTINEL_START_RE`, `_USER_SENTINEL_END_RE`, `_parse_user_sentinel_blocks`, `_extract_user_blocks`, `_restore_user_blocks`, `_has_user_sentinel_blocks`
- `graphify/merge.py` `_synthesize_file_text` contains `_extract_user_blocks` call for REPLACE action (line 1206)
- `graphify/merge.py` `apply_merge_plan` reads `existing_text` for `("UPDATE", "REPLACE")` (line 1306)
- `graphify/merge.py` `_build_manifest_from_result` calls `_has_user_sentinel_blocks` (line 1138)
- `tests/test_merge.py` contains `class TestUserSentinelParser:` (line 1757)
- `tests/test_merge.py` contains `class TestUserSentinelPreservation:` (line 1844)
- Commit `5c14f8f` — present
- `pytest tests/test_merge.py -q -k "TestUserSentinelParser or TestUserSentinelPreservation"` — 12 passed
- `pytest tests/test_merge.py -q` — 136 passed
- `pytest tests/ -q` — 978 passed
