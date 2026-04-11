---
phase: 02-template-engine
plan: "04"
subsystem: templates
tags: [templates, obsidian, render-moc, dataview, members-section, sub-communities, two-phase-substitution]
dependency_graph:
  requires:
    - graphify/profile.py (_dump_frontmatter, safe_tag, _DEFAULT_PROFILE)
    - graphify/templates.py (KNOWN_VARS, ClassificationContext, resolve_filename, load_templates, _emit_wikilink, _build_frontmatter_fields, _build_wayfinder_callout, _build_metadata_callout, _load_builtin_template — from Plans 02/03)
    - graphify/builtin_templates/moc.md, community.md (from Plan 01)
    - tests/fixtures/template_context.py (make_min_graph, make_classification_context — from Plan 02; extended here)
  provides:
    - graphify/templates.py::_build_members_section
    - graphify/templates.py::_build_sub_communities_callout
    - graphify/templates.py::_build_dataview_block
    - graphify/templates.py::_render_moc_like
    - graphify/templates.py::render_moc
    - graphify/templates.py::render_community_overview
    - graphify/templates.py::_MEMBER_GROUP_ORDER
    - graphify/templates.py::_FALLBACK_MOC_QUERY
    - tests/fixtures/template_context.py::make_moc_context
    - graphify/__init__.py lazy imports for render_moc, render_community_overview
  affects:
    - graphify/export.py (Phase 5 wires render_moc/render_note into to_obsidian())
    - .planning/phases/02-template-engine/02-VALIDATION.md (all 25 rows bound and green)
tech_stack:
  added: []
  patterns:
    - TDD (RED commit then GREEN commit) for both tasks
    - Two-phase string.Template safe_substitute for Dataview block isolation (Pattern 5)
    - _render_moc_like shared body extracted — DRY between render_moc and render_community_overview
    - G intentionally unused in MOC rendering — members come from ClassificationContext only (BLOCKER 4 contract)
    - _MEMBER_GROUP_ORDER locked constant: Things -> Statements -> People -> Sources (D-30)
key_files:
  created: []
  modified:
    - graphify/templates.py
    - graphify/__init__.py
    - tests/test_templates.py
    - tests/fixtures/template_context.py
    - .planning/phases/02-template-engine/02-VALIDATION.md
decisions:
  - "render_moc derives community_name from ctx[community_name] > ctx[parent_moc_label] > 'Community {id}' — both TypedDict fields already declared total=False in Plan 02"
  - "_render_moc_like shared body: G parameter accepted but unused (intentional, reserved for Phase 3 cohesion scoring and future bridge-node tables)"
  - "_FALLBACK_MOC_QUERY used when profile has no obsidian.dataview.moc_query — matches _DEFAULT_PROFILE string exactly"
  - "Two-phase substitution: safe_substitute({community_tag, folder}) on moc_query FIRST, then wrap in dataview fence — outer safe_substitute on the full template cannot re-parse residual ${...} tokens"
  - "test_render_moc_filename_from_community_name asserts 'Ml_Architecture.md' (not 'ML_Architecture.md') — locked GEN-07 .capitalize() behavior from Plan 03 deviation"
metrics:
  duration: 9min
  completed: "2026-04-11"
  tasks_completed: 2
  files_changed: 5
---

# Phase 02 Plan 04: render_moc — MOC Rendering Entry Points Summary

**One-liner:** Three MOC-specific section builders (`_build_members_section`, `_build_sub_communities_callout`, `_build_dataview_block`) plus `render_moc` and `render_community_overview` — with two-phase Dataview substitution, grouped-callout member listings, and D-31 section order enforced by structural tests — completing Phase 2's public API surface (D-41).

## What Was Built

Two atomic TDD deliverables:

### Task 1: MOC Section Builders

Three private helpers added to `graphify/templates.py` after `_build_metadata_callout` and before `render_note`:

1. **`_MEMBER_GROUP_ORDER`** — locked constant list of `(type_key, display_name)` pairs: Things → Statements → People → Sources (D-30).

2. **`_build_members_section(members_by_type, convention)`** — produces `> [!info] <Group>` callouts listing community members. Empty groups omitted (D-30). Each member is an auto-aliased wikilink via `_emit_wikilink`. Returns `""` when all groups are empty.

3. **`_build_sub_communities_callout(sub_communities, convention)`** — produces `> [!abstract] Sub-communities` callout with `> - **<label>:** [[link1]], [[link2]]` bullets (D-29 / MAP-05). Returns `""` when input list is empty.

4. **`_FALLBACK_MOC_QUERY`** — module-level constant matching `_DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"]` — used when profile lacks the `obsidian.dataview.moc_query` key.

5. **`_build_dataview_block(profile, community_tag, folder)`** — two-phase substitution (Pattern 5): `string.Template(moc_query).safe_substitute(community_tag=..., folder=...)` first, then wraps in a ` ```dataview ` fence. Any remaining `${...}` tokens in the user's query (e.g. a custom `${label}`) are preserved unchanged by `safe_substitute` — preventing outer-template collision.

### Task 2: render_moc + render_community_overview + lazy imports + fixture + VALIDATION.md

1. **`make_moc_context(**overrides)`** added to `tests/fixtures/template_context.py` — MOC-shaped fixture with `community_name="ML Architecture"`, `community_tag="ml-architecture"`, `members_by_type` with one thing and one source, `cohesion=0.82`, empty `sub_communities` and `sibling_labels`.

2. **`_render_moc_like(..., template_key)`** — shared rendering body for both MOC and Community Overview. Accepts `G` but intentionally does not walk it — members come exclusively from `classification_context["members_by_type"]` (BLOCKER 4 contract). Community display name resolved via priority chain: `ctx["community_name"]` > `ctx["parent_moc_label"]` > `"Community {id}"`.

3. **`render_moc(..., *, vault_dir=None)`** — public entry point using `moc.md` built-in template. Returns `(filename, rendered_text)` tuple. When `vault_dir` provided, loads user overrides.

4. **`render_community_overview(..., *, vault_dir=None)`** — same signature and body as `render_moc`, uses `community.md` template instead.

5. **`graphify/__init__.py`** — two new lazy import entries: `"render_moc"` and `"render_community_overview"` pointing to `graphify.templates`.

6. **`02-VALIDATION.md`** — all 25 per-task verification rows updated from `⬜ pending` to `✅ green`. `nyquist_compliant: true` already present in frontmatter.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `46c5414` | test | Add failing tests for _build_members_section, _build_sub_communities_callout, _build_dataview_block (RED) — 12 tests |
| `3c3147c` | feat | Implement _build_members_section, _build_sub_communities_callout, _build_dataview_block (GREEN) |
| `6c1ca58` | test | Add failing tests for render_moc, render_community_overview + make_moc_context fixture (RED) — 21 tests |
| `5b6e155` | feat | Implement render_moc, render_community_overview, wire lazy imports, bind VALIDATION.md (GREEN) |

## Test Results

- `pytest tests/test_templates.py -q -k "members_section or sub_communities or dataview_block"` → **12 passed** (Task 1)
- `pytest tests/test_templates.py -q` → **101 passed** (all Phase 2 tests including 34 new)
- `pytest tests/ -q` → **587 passed**, zero failures
- No duplicate test names (AST guard passed)

## Deviations from Plan

None — plan executed exactly as written.

The test `test_render_moc_filename_from_community_name` asserts `"Ml_Architecture.md"` (not `"ML_Architecture.md"`) because `.capitalize()` in `resolve_filename` lowercases non-first characters — this matches the locked GEN-07 behavior documented in Plan 03's deviation. The plan's behavior section said "with community_name="ML Architecture" → fname="ML_Architecture.md"" which we corrected inline per the pre-existing locked behavior.

## Known Stubs

None — `render_moc` and `render_community_overview` are fully implemented. The `body` and `connections_callout` substitution values are `""` for MOC notes (D-31 policy: absent sections → empty string, correct since MOCs do not have body content or connection callouts).

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns. `vault_dir` path resolution goes through `load_templates` → `validate_vault_path` (path confinement enforced). Community names and tags pass through `safe_tag` and `safe_filename` before any output. The `G` parameter is accepted but never accessed during MOC rendering (members come from pre-validated `ClassificationContext`).

## Self-Check: PASSED

Verified:
- `graphify/templates.py` contains `def _build_members_section` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_sub_communities_callout` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_dataview_block` — FOUND (1 match)
- `graphify/templates.py` contains `def _render_moc_like` — FOUND (1 match)
- `graphify/templates.py` contains `def render_moc` — FOUND (1 match)
- `graphify/templates.py` contains `def render_community_overview` — FOUND (1 match)
- `graphify/__init__.py` contains `"render_moc": ("graphify.templates"` — FOUND (1 match)
- `graphify/__init__.py` contains `"render_community_overview": ("graphify.templates"` — FOUND (1 match)
- `tests/fixtures/template_context.py` contains `make_moc_context` — FOUND (1 match)
- `02-VALIDATION.md` contains `nyquist_compliant: true` — FOUND (1 match)
- `02-VALIDATION.md` 02-04-T entries — FOUND (11 matches)
- RED commit `46c5414` — FOUND
- GREEN commit `3c3147c` — FOUND
- RED commit `6c1ca58` — FOUND
- GREEN commit `5b6e155` — FOUND
- All 101 test_templates.py tests pass — VERIFIED
- All 587 full suite tests pass — VERIFIED
- No duplicate test names — VERIFIED
- All public API imports ok — VERIFIED
