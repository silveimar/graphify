---
phase: 02-template-engine
plan: "03"
subsystem: templates
tags: [templates, obsidian, render-note, frontmatter, wikilinks, callouts]
dependency_graph:
  requires:
    - graphify/profile.py (_dump_frontmatter, safe_frontmatter_value, safe_filename, validate_vault_path)
    - graphify/templates.py (KNOWN_VARS, ClassificationContext, resolve_filename, load_templates, _load_builtin_template — from Plan 02)
    - graphify/builtin_templates/*.md (six template files from Plan 01)
    - tests/fixtures/template_context.py (make_min_graph, make_classification_context — from Plan 02)
  provides:
    - graphify/templates.py::render_note (public entry point for non-MOC notes)
    - graphify/templates.py::_emit_wikilink (auto-aliased wikilink emitter)
    - graphify/templates.py::_build_frontmatter_fields (ordered D-24 frontmatter dict builder)
    - graphify/templates.py::_build_wayfinder_callout (Up/Map callout with atlas_root)
    - graphify/templates.py::_build_connections_callout (outgoing edge list callout)
    - graphify/templates.py::_build_metadata_callout (source/community callout)
    - graphify/__init__.py lazy import for render_note
  affects:
    - graphify/export.py (Plan 04 reuses section builders for render_moc)
tech_stack:
  added: []
  patterns:
    - TDD (RED commit then GREEN commit) for all section builders and render_note
    - duck-typed graph access (G[node], G.nodes[id], G.edges(id, data=True)) — no nx import in templates.py
    - string.Template.safe_substitute for placeholder rendering (unknown vars left in place)
    - keyword-only vault_dir=None extension to locked D-41 signature (non-breaking)
key_files:
  created: []
  modified:
    - graphify/templates.py
    - graphify/__init__.py
    - tests/test_templates.py
decisions:
  - "Test expectations for resolve_filename use resolve_filename() directly rather than hardcoding expected filenames — avoids fragility when .capitalize() lowercases multi-capital acronyms like 'ML' → 'Ml'"
  - "vault_dir is keyword-only with None default — preserves backward-compat D-41 locked signature while enabling GEN-03 user override path (non-breaking addition)"
  - "community_name in render_note is derived from ctx.get('parent_moc_label') — Phase 3 will set community_name directly when available"
metrics:
  duration: 5min
  completed: "2026-04-11"
  tasks_completed: 2
  files_changed: 3
---

# Phase 02 Plan 03: render_note — Section Builders and Non-MOC Rendering Summary

**One-liner:** Five private section builders (`_emit_wikilink`, `_build_frontmatter_fields`, `_build_wayfinder_callout`, `_build_connections_callout`, `_build_metadata_callout`) plus public `render_note()` producing GEN-01/02/06-compliant markdown for all four non-MOC note types, wired into `graphify.__init__` lazy imports and tested with 35 new tests.

## What Was Built

Two atomic TDD deliverables:

### Task 1: Section Builders

Five private helpers added to `graphify/templates.py` after `load_templates`:

1. **`_emit_wikilink(label, convention)`** — produces `[[filename|label]]` auto-aliased wikilinks. The filename is derived via `resolve_filename` (single source of truth for D-19 coupling). Display always uses the original human label.

2. **`_build_frontmatter_fields(...)`** — builds an ordered dict following D-24 field order (`up → related → collections → created → tags → type → file_type → source_file → source_location → community → cohesion`). Empty lists are skipped (locked policy). `cohesion` only emitted for `moc`/`community` note types. Returns a plain dict passed to `_dump_frontmatter()`.

3. **`_build_wayfinder_callout(note_type, parent_moc_label, profile, convention)`** — produces `> [!note] Wayfinder` callout. For `moc`/`community` types, both Up and Map link to `atlas_root` (D-35). For non-MOC with a parent, Up links to the parent MOC. Orphans fall back to Atlas.

4. **`_build_connections_callout(G, node_id, convention)`** — iterates `G.edges(node_id, data=True)`, emits `> - [[target|label]] — relation [CONFIDENCE]` per edge. Returns empty string for isolated nodes (D-18 absent-section policy). Uses duck-typed graph access — no `import networkx` needed.

5. **`_build_metadata_callout(...)`** — produces `> [!abstract] Metadata` callout with `source_file`, `source_location` (if present), and `community`.

### Task 2: render_note + lazy import

**`render_note(node_id, G, profile, note_type, classification_context, *, vault_dir=None)`** — public entry point:
- Validates `note_type` in `(thing, statement, person, source)` and `node_id in G`, both raising `ValueError` on failure
- Extracts node attrs (`label`, `file_type`, `source_file`, `source_location`) and context (`parent_moc_label`, `community_tag`, `sibling_labels`)
- Builds all five sections and passes them to `string.Template.safe_substitute`
- When `vault_dir` is provided, calls `load_templates(vault_dir)` for user overrides (GEN-03); otherwise loads all built-ins directly without any file I/O
- Returns `(filename_with_ext, rendered_text)` tuple

`graphify/__init__.py` updated with `"render_note": ("graphify.templates", "render_note")` lazy entry.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `dd13b8b` | test | Add failing tests for section builders and render_note (RED) — 35 tests |
| `b38c4bb` | feat | Implement section builders and render_note (GREEN) |
| `f59863f` | feat | Wire render_note into lazy import map |

## Test Results

- `pytest tests/test_templates.py -q` → **67 passed** (32 Plan 02 + 35 new)
- `pytest tests/test_templates.py -q -k "build_ or emit_wikilink"` → **15 passed**
- `pytest tests/test_templates.py -q -k "render_note"` → **20 passed**
- `pytest tests/ -q` → **546 passed**, 2 pre-existing failures in `test_detect.py` and `test_extract.py` (present on base commit, not caused by this plan)
- No duplicate test names (AST guard passed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test expectations hardcoded `ML_Architecture` but resolve_filename produces `Ml_Architecture`**
- **Found during:** Task 1 GREEN phase (test_build_wayfinder_callout_thing_links_to_parent_moc_and_atlas, test_render_note_frontmatter_up_is_list_with_parent_moc, test_render_note_contains_wayfinder_callout)
- **Issue:** `.capitalize()` in `resolve_filename` lowercases non-first characters in each word — "ML" becomes "Ml". The plan's example expected `[[ML_Architecture|ML Architecture]]` but the actual output is `[[Ml_Architecture|ML Architecture]]`.
- **Fix:** Updated 3 test assertions to derive expected filename via `resolve_filename()` dynamically rather than hardcoding, making tests robust to the locked GEN-07 behavior.
- **Files modified:** `tests/test_templates.py`
- **Commit:** `b38c4bb` (test fixes bundled with GREEN)

## Known Stubs

None — `render_note` is fully implemented and produces complete markdown output for all four non-MOC note types. The `body` section renders as empty string (D-18 policy: absent sections → empty string), which is correct since body content comes from Phase 3 classification, not from Plan 03.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns. `vault_dir` path resolution goes through `load_templates` → `validate_vault_path` (path confinement enforced). Node labels pass through `safe_filename` and `safe_frontmatter_value` before any output.

## Self-Check: PASSED

Verified:
- `graphify/templates.py` contains `def _emit_wikilink` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_frontmatter_fields` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_wayfinder_callout` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_connections_callout` — FOUND (1 match)
- `graphify/templates.py` contains `def _build_metadata_callout` — FOUND (1 match)
- `graphify/templates.py` contains `def render_note` — FOUND (1 match)
- `graphify/templates.py` contains `import datetime` — FOUND (1 match)
- `graphify/__init__.py` contains `"render_note": ("graphify.templates"` — FOUND (1 match)
- RED commit `dd13b8b` — FOUND
- GREEN commit `b38c4bb` — FOUND
- Lazy import commit `f59863f` — FOUND
- All 67 tests pass — VERIFIED
- No regressions beyond 2 pre-existing failures — VERIFIED
