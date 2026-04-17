---
phase: 10-cross-file-semantic-extraction
plan: "07"
subsystem: obsidian-export
tags: [obsidian, aliases, dedup, frontmatter, D-15, T-10-05]
dependency_graph:
  requires:
    - 10-cross-file-semantic-extraction/03  # dedup.py + dedup_report.json schema
    - 10-cross-file-semantic-extraction/04  # --obsidian CLI handler baseline
  provides:
    - Obsidian aliases: frontmatter from merged_from (D-15)
    - _hydrate_merged_from() helper in export.py
    - --obsidian-dedup CLI flag
  affects:
    - graphify/templates.py
    - graphify/export.py
    - graphify/__main__.py
tech_stack:
  added: []
  patterns:
    - YAML list frontmatter emission via _dump_frontmatter (existing serializer)
    - Wikilink alias sanitization via _sanitize_wikilink_alias (existing helper)
    - G.nodes mutation before rendering for dedup hydration
key_files:
  created: []
  modified:
    - graphify/templates.py
    - graphify/export.py
    - graphify/__main__.py
    - tests/test_templates.py
    - tests/test_export.py
decisions:
  - "Aliases injected into frontmatter_fields dict after _build_frontmatter_fields returns, before _dump_frontmatter call — cleanest insertion point that avoids touching _build_frontmatter_fields signature"
  - "_hydrate_merged_from is a module-level helper (not nested) following the project's extract-to-named-helper pattern"
  - "Candidate lookup tries output_dir.parent first (typical graphify-out/obsidian layout), then fallbacks — silently returns when missing, never raises"
metrics:
  duration: "7 minutes"
  completed: "2026-04-17"
  tasks_completed: 2
  files_modified: 5
---

# Phase 10 Plan 07: Obsidian Aliases + --obsidian-dedup Wiring Summary

Wired dedup provenance (D-15) through to the Obsidian vault adapter: canonical nodes now emit eliminated IDs as Obsidian `aliases:` frontmatter entries so existing user wikilinks resolve after dedup.

## What Was Built

### Frontmatter serializer — how aliases: is emitted

`render_note()` in `graphify/templates.py` assembles a `frontmatter_fields` dict via `_build_frontmatter_fields()`, then calls `_dump_frontmatter(frontmatter_fields)`. The aliases injection happens between those two calls:

```python
merged_from_ids = node.get("merged_from") or []
if merged_from_ids:
    aliases_list = sorted({
        _sanitize_wikilink_alias(str(mid))
        for mid in merged_from_ids
        if isinstance(mid, str) and mid
    })
    aliases_list = [a for a in aliases_list if a.strip()]
    if aliases_list:
        frontmatter_fields["aliases"] = aliases_list
```

`_dump_frontmatter` emits lists as YAML block sequences (`key:\n  - item`). The `aliases:` key only appears when `merged_from` is non-empty — nodes without it are byte-identical to pre-Phase-10 output.

### _hydrate_merged_from placement in export.py

`_hydrate_merged_from(G, output_dir)` is defined at module level between the `generate_html` alias and the `to_obsidian` function (line ~453). It:
1. Searches for `dedup_report.json` in `output_dir.parent`, `output_dir/../..`, then `graphify-out/` relative to cwd
2. Reads `merges[]` array, extracts `eliminated[].id` per canonical_id
3. Merges into any existing `merged_from` on the node (union + sort)
4. Silently returns on missing/corrupt report — never raises

### CLI flag propagation chain

```
argv["--obsidian-dedup"]
  → obsidian_dedup = True  (in __main__.py --obsidian handler, line ~1049)
  → to_obsidian(..., obsidian_dedup=obsidian_dedup)  (line ~1102)
  → if obsidian_dedup: _hydrate_merged_from(G, out)  (export.py line ~560)
  → G.nodes[canonical_id]["merged_from"] = [...]  (mutation in place)
  → render_note() reads merged_from → emits aliases: frontmatter
```

### Sanitization coverage

All alias strings pass through `_sanitize_wikilink_alias` (defined at `templates.py:283`). It strips:
- `]` and `|` — break wikilink syntax `[[alias|display]]`
- `\n`, `\r` — split callout lines
- C0 control chars + NEL + line/paragraph separators

This is the same helper used by `_emit_wikilink()` for connection display aliases — already well-tested by existing wikilink tests.

### Backward compat confirmation

- Nodes without `merged_from`: `frontmatter_fields["aliases"]` is never set — output unchanged
- `to_obsidian()` without `obsidian_dedup`: defaults to `False`, `_hydrate_merged_from` never called
- All 156 `test_templates.py` tests pass; all 15 `test_export.py` tests pass

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (templates) | 4680f6c | 3 failing tests committed before implementation |
| GREEN (templates) | f4c46e3 | 14 alias tests pass, 156 total |
| RED (export) | 54c27ce | 1 failing test committed before implementation |
| GREEN (export+CLI) | a00ecba | 2 export tests pass, 1140 total (excl. pre-existing delta failures) |

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing failures in `tests/test_delta.py` (3 tests): confirmed present before this plan's changes via `git stash` verification. Out of scope per CLAUDE.md scope boundary rule.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. The `_hydrate_merged_from` function reads a graphify-generated sidecar file (same trust level as graph.json). Type checks on every field read per T-10-05 mitigation.

## Self-Check: PASSED

- `graphify/templates.py` — modified (aliases injection at line ~648)
- `graphify/export.py` — modified (_hydrate_merged_from at line ~453, obsidian_dedup param at ~517)
- `graphify/__main__.py` — modified (obsidian_dedup flag at ~1033/1049/1102, help at ~946)
- `tests/test_templates.py` — modified (4 new tests at end of file)
- `tests/test_export.py` — modified (2 new tests at end of file)
- Commit 4680f6c: test RED templates
- Commit f4c46e3: feat GREEN templates
- Commit 54c27ce: test RED export
- Commit a00ecba: feat GREEN export+CLI
