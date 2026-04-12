---
phase: 05-integration-cli
plan: "05"
subsystem: public-api
tags: [lazy-imports, skill-surface, PROF-05, MRG-03, MRG-05, D-77a]
dependency_graph:
  requires:
    - 05-01 (format_merge_plan, split_rendered_note, MergePlan/MergeResult)
    - 05-02 (validate_profile_preflight, PreflightResult with rule_count/template_count)
    - 05-03 (to_obsidian with profile= and dry_run= signature)
    - 05-04 (integration tests green)
  provides:
    - graphify/__init__.py (5 new lazy map entries: format_merge_plan, split_rendered_note, validate_profile_preflight, PreflightResult, to_obsidian)
    - graphify/skill.md (Phase 5-aware pipeline with Step 6a validate-profile)
    - graphify/skill-aider.md + 7 other platform variants (same Phase 5 edits)
  affects:
    - All 9 skill files (canonical + 8 platform variants)
tech_stack:
  added: []
  patterns:
    - lazy __getattr__ import map in __init__.py
    - D-77a N/M suffix: result.rule_count / result.template_count from PreflightResult NamedTuple
key_files:
  created: []
  modified:
    - graphify/__init__.py
    - graphify/skill.md
    - graphify/skill-aider.md
    - graphify/skill-claw.md
    - graphify/skill-codex.md
    - graphify/skill-copilot.md
    - graphify/skill-droid.md
    - graphify/skill-opencode.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
decisions:
  - "to_obsidian added to lazy map (Rule 2 auto-fix) — was absent despite being Phase 5 primary entry point"
  - "8 platform variants with hardcoded 'graphify-out/obsidian' retain that hardcoded path; copilot/windows variants with obsidian_dir variable retain that pattern"
metrics:
  duration: "~10m"
  completed: "2026-04-11T21:03:19Z"
  tasks_completed: 4
  files_modified: 10
---

# Phase 05 Plan 05: Public API Surface and Skill Integration Summary

**One-liner:** Registered 5 new public helpers in the lazy import map and updated all 9 skill files (skill.md + 8 platform variants) to invoke the Phase 5 profile-driven to_obsidian pipeline with --dry-run and --validate-profile code paths including the D-77a `profile ok — N rules, M templates validated` literal.

## What Was Built

### graphify/__init__.py (updated)

Added 5 new entries to the `__getattr__` lazy import map:

| Symbol | Module | Group |
|--------|--------|-------|
| `format_merge_plan` | `graphify.merge` | merge exports |
| `split_rendered_note` | `graphify.merge` | merge exports |
| `MergeAction` | already present | — |
| `validate_profile_preflight` | `graphify.profile` | profile exports |
| `PreflightResult` | `graphify.profile` | profile exports |
| `to_obsidian` | `graphify.export` | export exports (Rule 2 fix) |

All 13 symbols from Task 4's verify command now resolve through `graphify.__getattr__`.

### graphify/skill.md (updated)

Two edits applied to the canonical skill:

**Step 6a (new section inserted before Step 6):** Preflight validator invocation block with D-77a literal output:
```
profile ok — {result.rule_count} rules, {result.template_count} templates validated
```
Exits 1 on errors, 0 on warnings-only or clean. Does not touch any file.

**Step 6 (to_obsidian block replaced):** Old `n = to_obsidian(...)` / `print(f'Obsidian vault: {n} notes...')` replaced with:
- `load_profile(obsidian_dir)` to resolve vault profile
- `to_obsidian(..., profile=profile, dry_run=dry_run)` call
- `isinstance(result, MergePlan)` branch printing `format_merge_plan(result)` on dry-run
- Else branch printing CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT counts from `result.plan.summary`

### All 8 Platform Variants (updated)

Same two edits applied to each variant, preserving each variant's shell wrapper style:

| Variant | Shell wrapper | obsidian_dir style |
|---------|--------------|-------------------|
| skill-aider.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-claw.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-codex.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-copilot.md | `$(cat graphify-out/.graphify_python)` | `obsidian_dir` variable |
| skill-droid.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-opencode.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-trae.md | `$(cat .graphify_python)` | hardcoded `'graphify-out/obsidian'` |
| skill-windows.md | `python -c` (PowerShell) | `obsidian_dir` variable |

**Scope discovery:** CONTEXT.md listed 7 variants; actual filesystem had 8 (copilot and windows not in canonical_refs). All 9 files (skill.md + 8 variants) were edited.

## Verification Output

```
# Marker counts across all 9 skill files:
format_merge_plan:          9/9
validate_profile_preflight: 9/9
result.rule_count:          9/9
result.template_count:      9/9
profile ok —:               9/9
n = to_obsidian( (stale):   0  (none remain)

# pytest:
862 passed in 2.73s

# graphify --help: ok

# All 13 lazy imports resolve:
format_merge_plan, split_rendered_note, validate_profile_preflight, PreflightResult,
to_obsidian, load_profile, compute_merge_plan, apply_merge_plan, classify,
render_note, render_moc, MergePlan, MergeResult
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Public Export] to_obsidian absent from __init__.py lazy map**
- **Found during:** Task 4 verify command — `AttributeError: module 'graphify' has no attribute 'to_obsidian'`
- **Issue:** `to_obsidian` was listed in Task 4's verify command but had never been added to the `__getattr__` map, making `graphify.to_obsidian` inaccessible to callers importing through the package.
- **Fix:** Added `"to_obsidian": ("graphify.export", "to_obsidian")` to the export group in the map.
- **Files modified:** `graphify/__init__.py`
- **Commit:** a54dae7

## Known Stubs

None — skill files are documentation/instruction templates. The `dry_run = False` and `obsidian_dir = 'OBSIDIAN_DIR'` lines are intentional placeholders instructing the agent to substitute real values at runtime, consistent with the pre-existing skill file pattern.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Changes are limited to `__init__.py` (lazy import map additions) and skill markdown files (documentation-only, no executable code shipped to production). No threat flags.

## Phase 5 Completion

All five Phase 5 plans are now complete:

| Plan | Deliverable | Requirements |
|------|------------|-------------|
| 05-01 | merge.py: split_rendered_note, format_merge_plan, compute/apply_merge_plan | MRG-01, MRG-02 |
| 05-02 | profile.py: validate_profile_preflight, PreflightResult with rule_count/template_count | PROF-05 |
| 05-03 | export.py: to_obsidian refactored to profile-driven MergeResult/MergePlan return | MRG-03, MRG-05 |
| 05-04 | tests/test_integration.py: 9-test Phase 5 pipeline coverage suite | FIX-01, FIX-02, FIX-03 |
| 05-05 | __init__.py + 9 skill files: public API surface and user-visible pipeline wiring | PROF-05, MRG-03, MRG-05 |

PROF-05, MRG-03, MRG-05 all delivered with both library tests (Plan 04) and skill-surface coverage (Plan 05).

## Self-Check: PASSED

- graphify/__init__.py: `format_merge_plan` FOUND
- graphify/__init__.py: `split_rendered_note` FOUND
- graphify/__init__.py: `validate_profile_preflight` FOUND
- graphify/__init__.py: `PreflightResult` FOUND
- graphify/__init__.py: `to_obsidian` FOUND (Rule 2 fix)
- graphify/skill.md: `Step 6a` FOUND
- graphify/skill.md: `format_merge_plan` FOUND
- graphify/skill.md: `validate_profile_preflight` FOUND
- graphify/skill.md: `result.rule_count` FOUND
- graphify/skill.md: `profile ok —` FOUND
- All 8 variants: 9/9 markers CONFIRMED
- n = to_obsidian( stale pattern: 0 matches CONFIRMED
- commit 44764b3: FOUND
- commit 63ef574: FOUND
- commit 7e1f5b6: FOUND
- commit a54dae7: FOUND
- 862 tests passing: CONFIRMED
