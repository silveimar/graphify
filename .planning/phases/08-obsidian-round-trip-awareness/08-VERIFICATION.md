---
phase: 08-obsidian-round-trip-awareness
verified: 2026-04-13T18:45:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Edit a graphify-injected note in Obsidian, re-run --obsidian, verify note is preserved"
    expected: "User-modified note receives SKIP_PRESERVE action; file content unchanged"
    why_human: "Requires actual vault, file editing, and CLI execution to validate end-to-end"
  - test: "Add <!-- GRAPHIFY_USER_START -->user notes<!-- GRAPHIFY_USER_END --> to a note, re-run --obsidian --force"
    expected: "User sentinel content survives even with --force; graphify sections refresh"
    why_human: "Requires real file manipulation and visual inspection of sentinel preservation"
  - test: "Run --obsidian --dry-run on a vault with modified notes"
    expected: "Dry-run output shows preamble with user-modified counts and [user]/[both] source annotations"
    why_human: "Requires running CLI with a real vault to verify formatted output readability"
---

# Phase 8: Obsidian Round-Trip Awareness Verification Report

**Phase Goal:** Users can freely edit graphify-injected vault notes between runs without losing their changes on the next --obsidian re-run
**Verified:** 2026-04-13T18:45:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After user edits a note and re-runs --obsidian, graphify detects modification and preserves it instead of blind overwrite | VERIFIED | `compute_merge_plan` at line 921 checks `manifest and not force`, compares `_content_hash(target_path)` against manifest entry, assigns `SKIP_PRESERVE` with `user_modified=True` on hash mismatch (line 927-935). Note: roadmap says `UPDATE_PRESERVE_USER_BLOCKS` but D-07 decided `SKIP_PRESERVE` is the correct action -- entire note left untouched. User sentinel blocks (D-08) provide granular preservation for --force mode. |
| 2 | Content between GRAPHIFY_USER_START and GRAPHIFY_USER_END sentinels is never overwritten, even with replace strategy | VERIFIED | `_synthesize_file_text` calls `_extract_user_blocks(existing_text)` at line 1206 for REPLACE and line 1228 for UPDATE, then `_restore_user_blocks` re-inserts content. `_parse_user_sentinel_blocks` supports multiple pairs. Malformed sentinels warn to stderr and return []. TestUserSentinelPreservation (6 tests) confirms. |
| 3 | --dry-run shows which notes have user modifications and what merge action would be applied | VERIFIED | `format_merge_plan` adds D-12 preamble (line 1382-1392) with user_modified/graphify-only/new counts. `_format_action_suffix` adds `[user]`/`[both]` source annotations (lines 1438-1441) and `(user-modified)` suffix (line 1451). TestFormatMergePlanRoundTrip (7 tests) confirms. |
| 4 | vault-manifest.json is written atomically after each successful merge with content hashes | VERIFIED | `_save_manifest` uses tmp + `os.replace` atomic pattern (line 1093). `_build_manifest_from_result` records all D-06 fields: content_hash, last_merged, target_path, node_id, note_type, community_id, has_user_blocks (lines 1131-1139). `apply_merge_plan` calls `_save_manifest` when `manifest_path` is not None (line 1353). TestVaultManifest (8 tests) confirms. |
| 5 | Merge plan output includes per-note modification source (graphify/user/both) for audit trail | VERIFIED | MergeAction has `source` field (line 102) defaulting to "graphify". User-modified notes get `source="user"` (line 933). Notes with user blocks but matching hash get `source="both"`. `_format_action_suffix` renders `[user]`/`[both]` annotations in dry-run output. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/merge.py` | _load_manifest, _save_manifest, _content_hash, _build_manifest, user sentinel functions, MergeAction fields, compute_merge_plan manifest+force, apply_merge_plan manifest_path | VERIFIED | All functions present: _content_hash (L1054), _load_manifest (L1064), _save_manifest (L1083), _build_manifest_from_result (L1099), _parse_user_sentinel_blocks (L273), _extract_user_blocks (L332), _restore_user_blocks (L353), _has_user_sentinel_blocks (L321). MergeAction has user_modified, has_user_blocks, source fields (L100-102). |
| `tests/test_merge.py` | TestVaultManifest, TestUserModifiedDetection, TestUserSentinelParser, TestUserSentinelPreservation, TestFormatMergePlanRoundTrip | VERIFIED | All 5 test classes present at lines 1505, 1656, 1757, 1844, 2013. 33 phase-specific tests all pass. Full suite: 143 tests pass. |
| `graphify/export.py` | to_obsidian with force and manifest_path parameters | VERIFIED | force param in signature (L458). manifest loaded via _load_manifest (L505). compute_merge_plan receives manifest= and force= (L604-605). apply_merge_plan receives manifest_path= and old_manifest= (L611-612). |
| `graphify/__main__.py` | --force flag parsing | VERIFIED | force=False initialized (L976), --force parsed (L990-991), force=force passed to to_obsidian (L1042), help text present (L898). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| apply_merge_plan | _save_manifest | call at end when manifest_path set | WIRED | Line 1353: `_save_manifest(manifest_path, new_manifest)` |
| compute_merge_plan | _content_hash | hash comparison in user-modified detection | WIRED | Line 925: `current_hash = _content_hash(target_path)` |
| _synthesize_file_text | _extract_user_blocks | extracts user blocks before rewrite | WIRED | Lines 1206 (REPLACE) and 1228 (UPDATE) |
| _build_manifest_from_result | _has_user_sentinel_blocks | sets has_user_blocks in manifest | WIRED | Line 1138: `_has_user_sentinel_blocks(path.read_text(...))` |
| __main__.py | to_obsidian | force= keyword argument | WIRED | Line 1042: `force=force` |
| to_obsidian | compute_merge_plan | manifest= and force= | WIRED | Lines 604-605 |
| to_obsidian | apply_merge_plan | manifest_path= and old_manifest= | WIRED | Lines 611-612 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| merge.py::compute_merge_plan | manifest dict | _load_manifest -> JSON file | Yes - reads vault-manifest.json from disk | FLOWING |
| merge.py::_build_manifest_from_result | content_hash | _content_hash -> file bytes | Yes - SHA256 of actual file content | FLOWING |
| merge.py::_synthesize_file_text | user_blocks | _extract_user_blocks -> file text | Yes - parses real file content for sentinels | FLOWING |
| export.py::to_obsidian | manifest | _load_manifest(manifest_path) | Yes - loads from graphify-out/vault-manifest.json | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 8 tests pass | `pytest tests/test_merge.py -q -k "TestVaultManifest or TestUserModifiedDetection or TestUserSentinelParser or TestUserSentinelPreservation or TestFormatMergePlanRoundTrip"` | 33 passed | PASS |
| Full merge test suite | `pytest tests/test_merge.py -q` | 143 passed | PASS |
| MergeAction backward compat | `python -c "from graphify.merge import MergeAction; ..."` | user_modified=False, source="graphify" | PASS |
| --force in CLI help | `python -m graphify --help \| grep force` | "--force" found | PASS |
| to_obsidian has force param | `python -c "import inspect; ..."` | force in signature | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TRIP-01 | 08-01 | apply_merge_plan writes vault-manifest.json with content hash per note | SATISFIED | _save_manifest called from apply_merge_plan (L1353); _build_manifest_from_result records content_hash (L1132); TestVaultManifest confirms |
| TRIP-02 | 08-01 | On re-run, graphify detects user-modified notes via hash comparison | SATISFIED | compute_merge_plan checks manifest hash vs _content_hash (L921-935); TestUserModifiedDetection confirms |
| TRIP-03 | 08-01 | User-modified notes receive preservation action | SATISFIED | SKIP_PRESERVE with user_modified=True assigned on hash mismatch (L927-934). Note: REQUIREMENTS.md says UPDATE_PRESERVE_USER_BLOCKS but D-07 decided SKIP_PRESERVE (entire note untouched). User sentinel blocks provide granular preservation. Intent satisfied. |
| TRIP-04 | 08-02 | User sentinel blocks provide explicit preservation zones | SATISFIED | _USER_SENTINEL_START_RE/_END_RE defined (L269-270); _parse_user_sentinel_blocks, _extract_user_blocks, _restore_user_blocks implemented; TestUserSentinelParser + TestUserSentinelPreservation confirm |
| TRIP-05 | 08-03 | --dry-run shows user modification status per note | SATISFIED | format_merge_plan preamble (L1382-1392) and _format_action_suffix source annotations (L1438-1451); TestFormatMergePlanRoundTrip confirms |
| TRIP-06 | 08-02 | User content always wins -- sentinel blocks never overwritten | SATISFIED | _synthesize_file_text extracts+restores user blocks for both REPLACE (L1206) and UPDATE (L1228); even --force preserves sentinels (D-08) |
| TRIP-07 | 08-03 | Per-note modification source in merge plan output | SATISFIED | MergeAction.source field (L102); [user]/[both] annotations in _format_action_suffix (L1438-1441); preamble counts (L1382-1392) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TODOs, FIXMEs, placeholders, or stubs found | - | - |

No anti-patterns detected. Plan 01's known stub (`has_user_blocks: False`) was resolved in Plan 02 per the summary.

### Human Verification Required

### 1. End-to-End User-Modified Note Preservation

**Test:** Edit a graphify-injected note in an Obsidian vault (change some text), then re-run `graphify --obsidian`.
**Expected:** The modified note is detected (SKIP_PRESERVE action), file content unchanged. The new vault-manifest.json should contain the note's original hash (not the modified hash).
**Why human:** Requires actual vault creation, file editing between runs, and CLI execution to validate the full round-trip.

### 2. User Sentinel Block Preservation with --force

**Test:** Add `<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->` blocks with personal notes to a graphify-managed vault note. Run `graphify --obsidian --force`.
**Expected:** Graphify-managed sections refresh with new data, but content between sentinel markers is preserved verbatim.
**Why human:** Requires real file manipulation, --force execution, and visual inspection that sentinel content survived while graphify sections updated.

### 3. Dry-Run Output Readability

**Test:** Run `graphify --obsidian --dry-run` on a vault where some notes have been user-modified.
**Expected:** Output shows a preamble line like "2 notes user-modified (will be preserved), 5 notes graphify-only (will update), 1 new notes (will create)" and per-note lines with `[user]` or `[both]` annotations.
**Why human:** Requires running CLI with a real vault to verify the formatted output is readable and counts are accurate.

### Gaps Summary

No automated gaps found. All 5 roadmap success criteria are verified at the code level. All 7 TRIP requirements are satisfied. All artifacts exist, are substantive, are wired, and have data flowing through them. 143 merge tests pass including 33 phase-specific tests.

The only notable deviation is that roadmap SC1 and TRIP-03 reference `UPDATE_PRESERVE_USER_BLOCKS` as an action name, but the implementation uses `SKIP_PRESERVE` with `user_modified=True`. This was an explicit design decision (D-07) documented in the phase context: "the entire note is left untouched. User content always wins." The sentinel block mechanism (D-08) provides granular preservation for --force mode. The intent of the requirement is fully satisfied.

3 items require human verification to confirm end-to-end behavior in a real vault environment.

---

_Verified: 2026-04-13T18:45:00Z_
_Verifier: Claude (gsd-verifier)_
