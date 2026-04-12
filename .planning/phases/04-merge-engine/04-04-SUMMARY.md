---
phase: 04-merge-engine
plan: 04
subsystem: merge
tags: [merge, compute-merge-plan, pure-function, fixtures, tdd, phase-4]

# Dependency graph
requires:
  - phase: 04-03
    provides: "merge.py primitive layer: _parse_frontmatter, _parse_sentinel_blocks, _resolve_field_policy, _apply_field_policy, MergeAction/MergePlan/MergeResult"
  - phase: 01-foundation
    provides: "profile.py validate_vault_path + _dump_frontmatter + safe_frontmatter_value"
provides:
  - "graphify/merge.py: compute_merge_plan public function (D-70)"
  - "graphify/merge.py: RenderedNote TypedDict — input contract for Phase 5"
  - "graphify/merge.py: _CANONICAL_KEY_ORDER — D-24 slot-insertion reference"
  - "graphify/merge.py: _merge_frontmatter / _insert_with_canonical_neighbor — D-66 order preservation"
  - "graphify/merge.py: _merge_body_blocks — D-68 refresh-in-place semantics"
  - "graphify/merge.py: _has_fingerprint / _find_body_start / _validate_target — per-file decision helpers"
  - "tests/fixtures/vaults/: 7 representative vault states (empty + 6 populated)"
affects:
  - 04-05-apply-merge-plan    # consumes MergePlan output
  - 04-06-dry-run             # calls compute_merge_plan for --dry-run display
  - 05-integration            # Phase 5 CLI wires to_obsidian -> compute_merge_plan

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure read-only orchestration: compute_merge_plan reads vault files but never writes (D-70)"
    - "Dual-signal fingerprint check (D-62): graphify_managed:true OR non-empty sentinel blocks"
    - "D-66 field-order preservation: existing keys keep positions; new keys slot after canonical neighbor"
    - "D-68 deleted-block respect: absent blocks skipped, never re-inserted"
    - "Strategy dispatch table: update (per-field diff) / skip (SKIP_PRESERVE) / replace (REPLACE)"
    - "Path confinement via validate_vault_path on every target before any file I/O"

key-files:
  created:
    - tests/fixtures/vaults/empty/.gitkeep
    - tests/fixtures/vaults/pristine_graphify/Atlas/Dots/Things/Transformer.md
    - tests/fixtures/vaults/user_extended/Atlas/Dots/Things/Transformer.md
    - tests/fixtures/vaults/fingerprint_stripped/Atlas/Dots/Things/Transformer.md
    - tests/fixtures/vaults/malformed_sentinel/Atlas/Dots/Things/Transformer.md
    - tests/fixtures/vaults/preserve_fields_edited/Atlas/Dots/Things/Transformer.md
    - tests/fixtures/vaults/unmanaged_collision/Atlas/Dots/Things/Transformer.md
  modified:
    - graphify/merge.py
    - tests/test_merge.py

key-decisions:
  - "_CANONICAL_KEY_ORDER mirrors _build_frontmatter_fields emission order in templates.py — single source of truth for D-24 slot placement"
  - "RenderedNote TypedDict defined in merge.py (not templates.py) — Phase 5 is the real caller, merge.py owns the contract today per the plan"
  - "unmanaged_collision fixture has no graphify-specific words — acceptance criterion requires grep for 'graphify' to FAIL"
  - "preserve_fields_edited inserts rank+mapState between created and type — positions match user edit scenario (not after graphify_managed)"

patterns-established:
  - "Fixture copy pattern: _copy_vault_fixture(name, tmp_path) always copies to tmp_path to prevent test mutation of checked-in fixtures"
  - "Idempotent render helper: _rendered_note_matching_pristine parses the pristine fixture's own content to guarantee zero changed_fields on UPDATE"
  - "Strategy-as-profile-key: merge_strategy dispatched from profile.merge.strategy with 'update' fallback"

requirements-completed: [MRG-01, MRG-06, MRG-07]

# Metrics
duration: ~4min
completed: 2026-04-11
---

# Phase 4 Plan 04: compute_merge_plan Summary

**compute_merge_plan delivers the pure read-only decision core of Phase 4: a single function that consumes a vault directory, rendered notes, and a profile and emits a MergePlan with CREATE/UPDATE/SKIP_CONFLICT/SKIP_PRESERVE/REPLACE/ORPHAN actions — no file writes, strategy dispatch, D-66 field-order preservation, and D-68 deleted-block respect, backed by 7 real vault fixtures and 17 integration tests.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-11T16:58:34Z
- **Completed:** 2026-04-11T17:02:14Z
- **Tasks:** 3 (all TDD)
- **Files created:** 7 vault fixtures + 0 (merge.py and test_merge.py existed from Plan 03)
- **Files modified:** 2 (`graphify/merge.py`, `tests/test_merge.py`)
- **Lines added to merge.py:** 342 (388 → 730 total)
- **Tests added:** 17 (46 from Plan 03 + 17 new = 63 total passing)

## Accomplishments

### Vault Fixture Corpus (Task 1)

7 representative vault states checked into `tests/fixtures/vaults/`:

| Fixture | Role | Fingerprint State |
|---------|------|------------------|
| `empty/` | Zero existing files — all renders become CREATE | N/A |
| `pristine_graphify/` | Both fingerprint signals present, byte-exact _dump_frontmatter output | graphify_managed:true + 3 sentinel blocks |
| `user_extended/` | Extra `user/research` tag + `collections: [[Research Log]]` | Fingerprinted — union semantics tested |
| `fingerprint_stripped/` | graphify_managed removed + all sentinel comments removed | None → SKIP_CONFLICT/unmanaged_file |
| `malformed_sentinel/` | graphify:wayfinder:end deleted, graphify_managed kept | graphify_managed:true but sentinel raises _MalformedSentinel → SKIP_CONFLICT/malformed_sentinel |
| `preserve_fields_edited/` | rank:7 + mapState added by user | Fingerprinted — preserve policy tested |
| `unmanaged_collision/` | Plain user markdown, no frontmatter, no sentinels | None → SKIP_CONFLICT/unmanaged_file |

### compute_merge_plan Dispatch Table (Task 2)

| Condition | Action | Notes |
|-----------|--------|-------|
| target_path does not exist | CREATE | New file, path is absolute inside vault_dir |
| target_path exists, parseFrontmatter returns None | SKIP_CONFLICT/malformed_frontmatter | Never self-heal |
| target_path exists, _parse_sentinel_blocks raises | SKIP_CONFLICT/malformed_sentinel | D-69 |
| target_path exists, no fingerprint | SKIP_CONFLICT/unmanaged_file | D-63 — even with strategy=replace |
| Fingerprinted + strategy=skip | SKIP_PRESERVE | D-63 |
| Fingerprinted + strategy=replace | REPLACE | D-63 still protects unmanaged |
| Fingerprinted + strategy=update | UPDATE | changed_fields + changed_blocks computed |
| UPDATE with zero changes | UPDATE reason="idempotent re-render" | Distinguishable from substantive updates |
| node_id in skipped_node_ids | (no action) | D-68 skip contract |
| previously_managed_paths not in render | ORPHAN | D-72 — never deletes |
| target_path escapes vault_dir | SKIP_CONFLICT/unmanaged_file | T-04-14/T-04-15 path confinement |

### _CANONICAL_KEY_ORDER

```python
["up", "related", "collections", "created", "tags", "type",
 "file_type", "source_file", "source_location", "community",
 "cohesion", "graphify_managed"]
```

Mirrors `_build_frontmatter_fields` emission order in `templates.py` (D-24). Used by `_insert_with_canonical_neighbor` to slot new keys in the right position when existing files gain new graphify fields on UPDATE.

### Integration Tests (Task 3) — 17 tests covering all must_haves

| Test | Must-have | Coverage |
|------|-----------|---------|
| test_compute_empty_vault_empty_render | — | empty plan baseline |
| test_compute_create_action_for_new_path | — | CREATE path |
| test_compute_update_idempotent_pristine | — | UPDATE reason="idempotent re-render" |
| test_compute_update_changed_source_file | — | UPDATE changed_fields=["source_file"] |
| test_compute_update_unions_user_extended_tags | — | union semantics verified |
| test_compute_skip_conflict_fingerprint_stripped | — | SKIP_CONFLICT/unmanaged_file |
| test_compute_skip_conflict_malformed_sentinel | — | SKIP_CONFLICT/malformed_sentinel |
| test_compute_skip_conflict_unmanaged_collision | — | SKIP_CONFLICT/unmanaged_file |
| test_compute_preserve_rank_survives_update | **M1** | rank/mapState not in changed_fields |
| test_compute_strategy_skip_is_noop_for_existing | **M2** | SKIP_PRESERVE |
| test_compute_strategy_replace_overwrites_fingerprinted | **M3** | REPLACE |
| test_compute_strategy_replace_still_skips_unmanaged | **M3** | D-63 survives replace |
| test_compute_orphan_detection_via_previously_managed_paths | — | ORPHAN + plan.orphans |
| test_compute_skipped_node_id_produces_no_action | — | skipped_node_ids |
| test_compute_is_pure_no_mtime_change | — | purity assertion |
| test_compute_field_order_preserved_after_merge | **M4** | cohesion after community |
| test_compute_action_paths_are_absolute_and_inside_vault | — | path confinement |

## Task Commits

1. **Task 1 (fixtures):** `52c8cd2` — `feat(04-04): create vault fixture corpus for compute_merge_plan tests`
2. **Task 2+3 RED:** `cc65566` — `test(04-04): add failing tests for compute_merge_plan (Tasks 2+3 RED)` — 17 failing
3. **Task 2+3 GREEN:** `f87643e` — `feat(04-04): implement compute_merge_plan + merge/diff helpers (Tasks 2+3 GREEN)` — 63 passing

## Files Modified

- `graphify/merge.py` (730 lines, +342 from Plan 03's 388)
- `tests/test_merge.py` (613 lines, +300 from Plan 03's 313)

## Decisions Made

- **_CANONICAL_KEY_ORDER in merge.py, not imported from templates.py.** Module isolation per CONTEXT.md Claude's Discretion — merge.py must not depend on templates.py. The list is duplicated intentionally and documented to stay in sync.
- **RenderedNote TypedDict defined in merge.py.** Phase 5 is the real caller; merge.py owns the input contract today. When Phase 5 is built it imports RenderedNote from merge.
- **unmanaged_collision fixture avoids the word "graphify".** Acceptance criterion verifies `grep -q "graphify"` FAILS — even "before running graphify" would break it.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — compute_merge_plan is purely algorithmic, no UI rendering, no data flows through empty placeholders.

## Threat Model Coverage

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-04-14 | Mitigated | `_validate_target` calls `validate_vault_path`; path escape → SKIP_CONFLICT. Tested in `test_compute_action_paths_are_absolute_and_inside_vault`. |
| T-04-15 | Mitigated | `validate_vault_path` uses `.resolve()` which follows symlinks; escape → ValueError → SKIP_CONFLICT. |
| T-04-16 | Accepted | `read_text()` loads full file. Vault files are user-controlled; size caps are Phase 5 concern. |
| T-04-17 | Mitigated | reason strings contain only control info ("no fingerprint", "malformed sentinel: {short exc}"), never file contents. |
| T-04-18 | Transferred | TOCTOU is apply_merge_plan (Plan 05) responsibility — `.tmp + os.replace` pattern documented there. |
| T-04-19 | Mitigated | 7 fixtures reviewed before commit; no adversarial content. |

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. compute_merge_plan is purely in-memory computation over user-controlled vault files.

## Self-Check: PASSED
