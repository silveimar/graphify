---
phase: 05-integration-cli
plan: "03"
subsystem: export
tags: [orchestration, to_obsidian, dry-run, pipeline, MRG-03, MRG-05, D-74, D-75]
dependency_graph:
  requires:
    - 05-01 (split_rendered_note public helper)
    - 05-02 (validate_profile_preflight — not called here, but wave context)
    - graphify/profile.py (load_profile)
    - graphify/mapping.py (classify)
    - graphify/templates.py (render_note, render_moc, render_community_overview)
    - graphify/merge.py (compute_merge_plan, apply_merge_plan, RenderedNote, split_rendered_note)
  provides:
    - refactored to_obsidian() with profile= and dry_run= keyword-only params
    - MergeResult | MergePlan union return type
  affects:
    - graphify/export.py
    - tests/test_export.py (intentionally broken; fixed in Plan 04)
    - tests/test_pipeline.py (intentionally broken; fixed in Plan 04)
tech_stack:
  added: []
  patterns:
    - Function-local imports (heavy deps deferred until call time)
    - thin orchestration over pure pipeline stages
    - public helper contract (split_rendered_note) instead of private cross-module coupling
key_files:
  created: []
  modified:
    - graphify/export.py
decisions:
  - "D-74: always run new pipeline — no if-profile-is-None branching inside body; profile None is resolved as first line via load_profile(out)"
  - "D-75 signature adopted verbatim: positional G/communities/output_dir, keyword-only profile/community_labels/cohesion/dry_run"
  - "split_rendered_note (Plan 01 public helper) is the ONLY merge.py internal consumed by export.py — private _parse_frontmatter/_find_body_start never imported"
  - "community_labels injected into per_community ctx via setdefault('community_name', label) — non-destructive, profile-independent"
  - "Per-node MOC-typed classification (note_type in moc/community) is skipped defensively to prevent double-rendering"
  - "render_community_overview fallback imported lazily inside per-community loop for note_type != moc"
  - "test_export.py::test_to_obsidian_* and test_pipeline.py::test_pipeline_end_to_end intentionally broken pending Plan 04 migration"
metrics:
  duration: "4m"
  completed: "2026-04-11T20:49:50Z"
  tasks_completed: 1
  files_modified: 1
---

# Phase 05 Plan 03: to_obsidian() Orchestration Refactor Summary

**One-liner:** Legacy 255-line flat-vault body deleted; replaced with ~120-line pipeline orchestration wiring load_profile → classify → render_note/render_moc → compute_merge_plan → apply_merge_plan, adding `profile=` and `dry_run=` keyword-only parameters per D-75.

## What Was Built

### Refactored to_obsidian() in graphify/export.py

The entire legacy body of `to_obsidian()` (L444–698 in the original 1012-line file) was deleted and replaced with a thin orchestration that runs the four Phase 1–4 modules in sequence.

**New signature (D-75 verbatim):**

```python
def to_obsidian(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    *,
    profile: dict | None = None,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    dry_run: bool = False,
) -> "MergeResult | MergePlan":
```

**Pipeline orchestration:**

1. Function-local imports of all four module helpers (defers heavy deps until call time)
2. `out.mkdir(parents=True, exist_ok=True)` — ensures output directory exists
3. `profile = load_profile(out)` if `profile is None` — D-74 compliant (no branching inside body)
4. `mapping_result = classify(G, communities, profile, cohesion=cohesion)` — Phase 3 classification
5. `community_labels` injected into `per_community` ctx via `setdefault("community_name", label)`
6. Per-node render loop: calls `render_note()` for each non-skipped, non-MOC node; builds `RenderedNote` via `split_rendered_note()`
7. Per-community render loop: calls `render_moc()` (or `render_community_overview()` for non-moc note_type); builds `RenderedNote` with synthetic id `_moc_{cid}`
8. `plan = compute_merge_plan(out, rendered_notes, profile, skipped_node_ids=skipped)`
9. `if dry_run: return plan` — returns `MergePlan` without any filesystem writes
10. `return apply_merge_plan(plan, out, rendered_notes, profile)` — returns `MergeResult`

**Line count:** export.py shrinks from 1012 to 876 lines (136 net lines removed despite adding new implementation).

### Key Architectural Decisions Applied

**split_rendered_note as stable public contract:**
`render_note()` and `render_moc()` return `(filename, rendered_text)` where `rendered_text` has YAML frontmatter embedded. `RenderedNote` requires `frontmatter_fields: dict` and `body: str` separately. Plan 01 added `split_rendered_note()` as a public wrapper over merge.py's private `_parse_frontmatter` + `_find_body_start` pair. This export.py refactor imports only `split_rendered_note` — never the private helpers — so any future merge.py internal refactor cannot break the cross-module contract.

**Removed from export.py entirely:**
- `_dominant_confidence()` nested helper (was inside legacy body)
- `_FTYPE_TAG` local dict (was inside legacy body)
- All `_COMMUNITY_` filename prefix logic (flat-vault artifact)
- The 200-line community note construction block

**Preserved (still used by to_html, to_canvas, etc.):**
- `from collections import Counter` (module-level)
- `from graphify.analyze import _node_community_map` (module-level)
- `COMMUNITY_COLORS` constant (used by to_html, to_canvas)
- `json` import (used by to_json, to_canvas)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — implementation is fully wired. The function correctly calls all four pipeline stages.

## Intentionally Broken Tests

Per Plan 04's mandate (D-74a):
- `tests/test_export.py::test_to_obsidian_*` — all `to_obsidian` tests assert on legacy flat output shape (root-level .md files, int return value). These are obsolete after the signature change and body deletion. Plan 04 migrates them to `tests/test_integration.py` asserting against `MergeResult.summary` counts and Atlas/-prefixed paths.
- `tests/test_pipeline.py::test_pipeline_end_to_end` — asserts on int return; Plan 04 updates to assert on `MergeResult` shape.

These test failures are expected, documented, and resolved in Plan 04.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. All path construction routes through `compute_merge_plan → validate_vault_path` (Phase 4 security gate) before any write. `to_obsidian` itself never writes files directly — only `apply_merge_plan` does, and it re-validates every action path (defense in depth per T-05-09). No threat flags.

## Self-Check: PASSED

- graphify/export.py: FOUND (876 lines, < original 1012)
- Contains `def to_obsidian(`: CONFIRMED
- Contains `dry_run: bool = False,`: CONFIRMED
- Contains `profile: dict | None = None,`: CONFIRMED
- Contains `from graphify.merge import` (indented, inside body): CONFIRMED
- Contains `split_rendered_note`: CONFIRMED (3 occurrences)
- Contains `compute_merge_plan(`: CONFIRMED
- Contains `apply_merge_plan(`: CONFIRMED
- Contains `classify(G, communities, profile`: CONFIRMED
- Does NOT contain `_parse_frontmatter`: CONFIRMED (0 matches)
- Does NOT contain `_find_body_start`: CONFIRMED (0 matches)
- Does NOT contain `def _split_rendered_text`: CONFIRMED
- Does NOT contain `_dominant_confidence`: CONFIRMED (0 matches)
- Does NOT contain `_FTYPE_TAG = {`: CONFIRMED (0 matches)
- Does NOT contain `_COMMUNITY_` inside to_obsidian body: CONFIRMED (0 matches anywhere in file)
- commit fc3bd3d: FOUND
- `python -c "from graphify import export; print(export.to_obsidian.__doc__[:60])"`: PASSED
- Signature check (profile + dry_run keyword-only): PASSED
