---
phase: 08-obsidian-round-trip-awareness
plan: "03"
subsystem: cli-export-merge
tags: [force-flag, manifest-threading, dry-run-enhancements, format-merge-plan, source-column, preamble]
dependency_graph:
  requires: [08-01, 08-02]
  provides: [force-cli-flag, manifest-threading-to-obsidian, format-merge-plan-round-trip]
  affects: [graphify/export.py, graphify/__main__.py, graphify/merge.py, tests/test_merge.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, manifest-path-derived-from-vault-parent, source-annotation-default-omitted]
key_files:
  created: []
  modified:
    - graphify/export.py
    - graphify/__main__.py
    - graphify/merge.py
    - tests/test_merge.py
decisions:
  - "manifest_path derived as vault_dir.parent / vault-manifest.json — vault dir is graphify-out/obsidian, manifest lives in graphify-out/ alongside graph.json"
  - "D-11 source annotation omitted for default source='graphify' — keeps v1.0 dry-run output clean with no manifest in play"
  - "D-12 preamble only shown when user_modified > 0 or any non-default source — backward compatible with v1.0 plans"
  - "--force + --dry-run combination shows what force WOULD do (compute_merge_plan receives force=True) — intuitive behavior per plan spec"
  - "_format_action_suffix extended with parts list pattern instead of early-return chain — allows source annotation before action-specific suffix"
metrics:
  duration: ~4min
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_modified: 4
  tests_added: 7
---

# Phase 8 Plan 03: CLI --force Flag, Manifest Threading, and Dry-Run Enhancements Summary

**One-liner:** --force flag wired CLI-to-export-to-merge; manifest loaded and saved through full to_obsidian pipeline; format_merge_plan extended with D-11 source annotations and D-12 user-modified preamble.

## What Was Built

### Task 1: Thread manifest and force through to_obsidian and CLI

**`graphify/export.py` — `to_obsidian()` extended:**

- New `force: bool = False` parameter added to signature
- `_load_manifest` and `_save_manifest` imported inside the function (function-local imports pattern, consistent with other merge imports)
- Manifest loaded at start: `manifest_path = vault_dir.parent / "vault-manifest.json"` — sits alongside `graph.json` in `graphify-out/`
- `compute_merge_plan` call updated: now passes `manifest=manifest, force=force`
- `apply_merge_plan` call updated: now passes `manifest_path=manifest_path, old_manifest=manifest`

**`graphify/__main__.py` — `--obsidian` argument parsing extended:**

- `force = False` initialized alongside `dry_run = False`
- `elif args[i] == "--force": force = True; i += 1` added before the unknown-option branch
- `to_obsidian(...)` call updated with `force=force`
- Help text documents `--force` with description of behavior

### Task 2: format_merge_plan Source column and summary preamble (TDD)

**`graphify/merge.py` — `format_merge_plan` extended (D-12):**

- Preamble inserted between the `=====` separator and the six-line summary block
- Preamble counts: `user_modified_count` (sum of `a.user_modified`), `graphify_only_count` (UPDATE/REPLACE/SKIP_PRESERVE without `user_modified`), `new_count` (`CREATE` from summary)
- Preamble only emitted when `user_modified_count > 0` OR any action has non-default source — v1.0 plans (no manifest, no user-modified) produce identical output to before

**`graphify/merge.py` — `_format_action_suffix` extended (D-11):**

- Refactored from early-return chain to `parts: list[str]` accumulator pattern
- Source annotation prepended: `[user]` for `source="user"`, `[both]` for `source="both"`, nothing for `source="graphify"` (default)
- SKIP_PRESERVE with `user_modified=True` adds `(user-modified)` suffix
- All existing suffixes (UPDATE field/block counts, SKIP_CONFLICT kind, ORPHAN reason) preserved

## Tests Added

`TestFormatMergePlanRoundTrip` (7 tests):
- `test_format_preamble_with_user_modified` — 2 user-modified + 1 graphify + 1 CREATE → correct preamble counts
- `test_format_preamble_absent_when_no_user_mods` — default source="graphify" only → no preamble
- `test_format_source_user_annotation` — SKIP_PRESERVE source="user" → `[user]` in output
- `test_format_source_both_annotation` — UPDATE source="both" → `[both]` in output
- `test_format_source_graphify_no_annotation` — UPDATE source="graphify" → no `[graphify]` in output
- `test_format_user_modified_skip_preserve_suffix` — SKIP_PRESERVE user_modified=True → `(user-modified)` in output
- `test_format_backward_compat_empty_plan` — empty plan → no preamble, no annotations, standard header present

**Total tests after plan:** 143 in `test_merge.py` (7 new, 136 existing — all still green); 985 passing across full suite.

## Commits

- `3159936` — feat(08-03): thread manifest/force through to_obsidian and add --force CLI flag
- `f77a876` — test(08-03): add failing TestFormatMergePlanRoundTrip tests for D-11/D-12
- `cdd4e25` — feat(08-03): format_merge_plan Source column (D-11) and summary preamble (D-12)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Surface Scan

- `manifest_path` is computed as `vault_dir.parent / "vault-manifest.json"` — always resolves to a path one level above the vault directory (typically `graphify-out/`). No path traversal vector: `vault_dir` is resolved from `Path(output_dir).resolve()` which is caller-controlled but not user-supplied input at the library boundary.
- T-08-09 (Tampering — manifest_path computation) is mitigated: manifest path never escapes the graphify-out sidecar directory. No `_validate_target` needed since the manifest is not a vault note file.

## Self-Check: PASSED

- `graphify/export.py` contains `force: bool = False` in to_obsidian signature
- `graphify/export.py` contains `manifest = _load_manifest(manifest_path)`
- `graphify/export.py` contains `manifest=manifest` and `force=force` in compute_merge_plan call
- `graphify/export.py` contains `manifest_path=manifest_path` and `old_manifest=manifest` in apply_merge_plan call
- `graphify/__main__.py` contains `elif args[i] == "--force":`
- `graphify/__main__.py` contains `force=force` in to_obsidian call
- `graphify/__main__.py` help output contains `--force`
- `graphify/merge.py` contains `user_modified_count = sum(`
- `graphify/merge.py` contains `notes user-modified (will be preserved)`
- `graphify/merge.py` _format_action_suffix contains `action.source == "user"`, `[user]`, `[both]`, `(user-modified)`
- `tests/test_merge.py` contains `class TestFormatMergePlanRoundTrip:`
- Commits `3159936`, `f77a876`, `cdd4e25` — present
- `pytest tests/test_merge.py -q` — 143 passed
- `pytest tests/ -q` — 985 passed
