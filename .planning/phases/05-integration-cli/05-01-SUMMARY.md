---
phase: 05-integration-cli
plan: "01"
subsystem: merge
tags: [format, dry-run, split, helpers, D-76, MRG-03]
dependency_graph:
  requires: [graphify/merge.py (existing MergePlan/MergeAction/MergeResult dataclasses), graphify/profile.py (_dump_frontmatter)]
  provides: [format_merge_plan(plan) -> str, split_rendered_note(text) -> (dict, str)]
  affects: [Phase 05 Plans 02-05 (skill, export.py, integration tests)]
tech_stack:
  added: []
  patterns: [TDD red-green, pure functions, no I/O]
key_files:
  created: []
  modified:
    - graphify/merge.py
    - tests/test_merge.py
decisions:
  - "_dump_frontmatter returns no trailing newline — round-trip test uses newline separator before body (documents real render_note assembly pattern)"
  - "format_merge_plan total count = len(plan.actions) only (plan.orphans not double-counted since ORPHAN MergeActions live in plan.actions per _VALID_ACTIONS)"
  - "split_rendered_note empty-dict return for _parse_frontmatter({}) empty-dict case — {} is falsy-but-valid, handled correctly by None-check"
metrics:
  duration: "2m 23s"
  completed: "2026-04-11T20:40:59Z"
  tasks_completed: 3
  files_modified: 2
---

# Phase 05 Plan 01: format_merge_plan and split_rendered_note Helpers Summary

**One-liner:** Two pure public helpers added to merge.py — `format_merge_plan` for D-76 dry-run output and `split_rendered_note` as a stable public inverse of the private frontmatter reader pair.

## What Was Built

### format_merge_plan(plan: MergePlan) -> str

Added to `graphify/merge.py` immediately after `apply_merge_plan`. Produces the grouped human-readable dry-run output specified in CONTEXT.md D-76:

- Header: `Merge Plan — N actions` + `========================` separator
- Six-line summary block with all action keys (CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN) in locked order, counts right-aligned, zero counts shown
- Per-group sections only for non-empty action kinds, each listing one line per file sorted lexicographically by `str(path)` for determinism
- UPDATE rows append `(N fields, M blocks)`, SKIP_CONFLICT rows append `[conflict_kind]`, ORPHAN rows append `(reason)`

Supporting constant `_ACTION_DISPLAY_ORDER: tuple[str, ...]` added near `_VALID_ACTIONS` to lock presentation order module-wide.

Supporting private helper `_format_action_suffix(action: MergeAction) -> str` handles the per-action-type suffix logic.

### split_rendered_note(rendered_text: str) -> tuple[dict[str, Any], str]

Added as a thin public wrapper over the existing private `_parse_frontmatter` + `_find_body_start` pair. Provides a stable cross-module contract so Plan 05-03 (export.py refactor) can call it without importing private helpers across modules.

Behavior contract:
- Happy path: returns `(frontmatter_dict, body_without_fence)`
- No frontmatter fence: returns `({}, rendered_text)`
- Malformed/unclosed frontmatter: returns `({}, rendered_text)`
- Empty string: returns `({}, "")`
- Never raises, never mutates input

### Test Coverage

9 `format_merge_plan` tests + 6 `split_rendered_note` tests added to `tests/test_merge.py`. All 110 tests in the file pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Round-trip test concatenation corrected**
- **Found during:** Task 3 GREEN phase — `test_split_rendered_note_roundtrip_with_dump_frontmatter` failed
- **Issue:** The plan's prescribed test used `_dump_frontmatter(original) + "body\n"` which produces `"---\n...\n---body\n"` — the closing fence and body are on the same line since `_dump_frontmatter` emits no trailing newline. `_parse_frontmatter` correctly returns `None` for this malformed input.
- **Fix:** Changed to `_dump_frontmatter(original) + "\nbody\n"` — a newline separator is required before the body, which mirrors how `render_note` assembles the full document in practice. Added clarifying comment.
- **Files modified:** `tests/test_merge.py`
- **Commit:** a5886cb

## MergeResult.failed Note

Per the plan objective: `MergeResult.failed: list[tuple[Path, str]]` (the "failures" field from CONTEXT.md Claude's Discretion) already existed from Phase 4. No changes were made to the `MergeResult` dataclass.

## Known Stubs

None — both helpers are fully implemented with real logic, no placeholders.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Both new functions are pure in-memory transformers. `format_merge_plan` embeds `MergeAction.path` (Path-typed, sanitized upstream by `validate_vault_path`) and enum-valued action/conflict_kind fields. `split_rendered_note` delegates to the existing `_parse_frontmatter` which uses a hand-rolled parser (no yaml.safe_load, no new injection surface). No threat flags.

## Self-Check: PASSED

- graphify/merge.py: FOUND
- tests/test_merge.py: FOUND
- 05-01-SUMMARY.md: FOUND
- commit a5886cb: FOUND
- 110 tests passing: CONFIRMED
