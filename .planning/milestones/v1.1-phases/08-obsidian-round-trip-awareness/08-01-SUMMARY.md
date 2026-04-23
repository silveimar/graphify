---
phase: 08-obsidian-round-trip-awareness
plan: "01"
subsystem: merge-engine
tags: [vault-manifest, user-modified-detection, content-hash, merge-engine]
dependency_graph:
  requires: []
  provides: [vault-manifest-io, user-modified-detection, MergeAction-source-fields]
  affects: [graphify/merge.py, tests/test_merge.py]
tech_stack:
  added: []
  patterns: [atomic-write-via-os-replace, content-only-sha256, manifest-keyed-by-relative-path]
key_files:
  created: []
  modified:
    - graphify/merge.py
    - tests/test_merge.py
decisions:
  - "D-04 implemented: _content_hash() uses content-only SHA256 (no path) — avoids macOS symlink hash mismatch that cache.file_hash() would cause"
  - "D-05 implemented: _save_manifest() uses tmp + os.replace atomic write; OSError unlinks tmp before re-raise"
  - "D-06 implemented: manifest entries include content_hash, last_merged, target_path, node_id, note_type, community_id, has_user_blocks"
  - "D-07 implemented: user-modified notes (hash mismatch) receive SKIP_PRESERVE with user_modified=True, source='user'"
  - "D-10 implemented: force=True bypasses user-modified detection — notes processed normally"
  - "MergeAction extended with backward-compatible fields: user_modified=False, has_user_blocks=False, source='graphify'"
  - "Multiple USER_START/END blocks per note supported (D-03, Claude's discretion) — sentinel parser deferred to Plan 02"
metrics:
  duration: ~17min
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_modified: 2
  tests_added: 14
---

# Phase 8 Plan 01: Vault Manifest Write and User-Modified Detection Summary

**One-liner:** Vault-manifest.json atomic write after apply_merge_plan with content-only SHA256 hashing; compute_merge_plan routes hash-mismatch notes to SKIP_PRESERVE with user_modified=True and force override.

## What Was Built

### Task 1: Manifest I/O helpers + MergeAction extension + apply_merge_plan manifest write

Four new private functions in `graphify/merge.py`:

- `_content_hash(path)` — SHA256 of raw file bytes only, no path mixed in. Critical distinction from `cache.file_hash()` which includes the resolved path and would cause hash mismatches across symlink differences (macOS `/private/tmp` vs `/tmp`).
- `_load_manifest(manifest_path)` — returns `{}` on missing or corrupt; prints stderr warning for corrupt; never aborts the pipeline.
- `_save_manifest(manifest_path, manifest)` — atomic write via `tmp + os.replace`; creates parent dirs; unlinks tmp on OSError before re-raise.
- `_build_manifest_from_result(result, rendered_notes, vault_dir, old_manifest)` — builds new manifest from MergeResult: records succeeded + skipped_identical paths with all D-06 fields, retains old entries for SKIP_PRESERVE notes, removes entries for paths that no longer exist on disk.

`MergeAction` dataclass extended with three backward-compatible fields (all have defaults so all existing construction calls remain valid):
- `user_modified: bool = False`
- `has_user_blocks: bool = False`
- `source: str = "graphify"`

`apply_merge_plan` extended with `manifest_path: Path | None = None` and `old_manifest: dict[str, dict] | None = None` keyword params. After all writes complete, if `manifest_path` is not None, builds and saves the manifest atomically.

### Task 2: User-modified detection in compute_merge_plan

`compute_merge_plan` extended with `manifest: dict[str, dict] | None = None` and `force: bool = False` keyword params.

In the per-note loop, after the CREATE branch and before reading the existing file, injects user-modified detection:
- Only runs when `manifest` is provided and `force` is False
- Computes `_content_hash(target_path)` and compares against manifest entry's `content_hash`
- Hash mismatch → `SKIP_PRESERVE` with `user_modified=True`, `has_user_blocks` from manifest entry, `source="user"`
- Hash match with `has_user_blocks=True` in manifest → `source="both"` on the resulting UPDATE action
- Missing manifest, empty manifest, or entry without `content_hash` → v1.0 behavior (normal strategy dispatch)

## Tests Added

`TestVaultManifest` (8 tests):
- `test_save_load_roundtrip` — round-trip all D-06 fields through save/load
- `test_load_missing_returns_empty` — graceful degradation
- `test_load_corrupt_returns_empty` — stderr warning + empty return
- `test_save_atomic_no_partial` — monkeypatched json.dumps failure leaves no .json or .json.tmp
- `test_content_hash_content_only` — same content at different paths → same hash
- `test_merge_action_new_fields_backward_compat` — defaults verified
- `test_apply_writes_manifest` — apply_merge_plan with manifest_path writes vault-manifest.json with all D-06 fields
- `test_apply_skip_preserve_retains_old_entry` — SKIP_PRESERVE notes retain their old manifest entry

`TestUserModifiedDetection` (6 tests):
- `test_user_modified_gets_skip_preserve` — hash mismatch → SKIP_PRESERVE, user_modified=True, source="user"
- `test_hash_match_proceeds_normally` — hash match → normal UPDATE, user_modified=False
- `test_missing_manifest_normal_behavior` — manifest=None → v1.0 behavior
- `test_corrupt_entry_no_content_hash` — entry without content_hash → processed normally
- `test_force_overrides_user_modified` — force=True bypasses detection
- `test_source_both_when_has_user_blocks` — matching hash + has_user_blocks=True → source="both"

**Total tests after plan:** 124 passing (14 new, 110 existing — all still green).

## Commits

- `ed87e4c` — feat(08-01): vault manifest I/O helpers + MergeAction extension + apply_merge_plan manifest write
- `190118e` — feat(08-01): user-modified detection in compute_merge_plan

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

**`graphify/merge.py:995` — `has_user_blocks: False` placeholder in `_build_manifest_from_result`**

```python
"has_user_blocks": False,  # Will be set to True in Plan 02 when sentinel parser lands
```

- **Location:** `graphify/merge.py`, `_build_manifest_from_result`, line ~995
- **Reason:** Intentional per plan spec. The user sentinel block parser (`_parse_user_sentinel_blocks`) is Plan 02's scope. Plan 01 records the field in the manifest schema (D-06) but always writes `False` until Plan 02 implements the parser.
- **Impact:** `has_user_blocks` in manifest will always be `False` after this plan. Plan 02 will update `_build_manifest_from_result` to call the parser and set the correct value.
- **Resolves in:** Plan 02 (sentinel blocks)

## Self-Check: PASSED

- `graphify/merge.py` — modified and contains `def _content_hash`, `def _load_manifest`, `def _save_manifest`, `def _build_manifest_from_result`, `manifest_path: Path | None = None` in apply_merge_plan, `manifest: dict[str, dict] | None = None` in compute_merge_plan
- `tests/test_merge.py` — modified and contains `class TestVaultManifest` and `class TestUserModifiedDetection`
- Commit `ed87e4c` — present
- Commit `190118e` — present
- `pytest tests/test_merge.py -q` — 124 passed
