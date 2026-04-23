---
name: graphify-moc
description: Generate a proposed MOC (Map of Content) note for a graphify community, rendered via the active Obsidian vault profile (built-in fallback applies when no .graphify/profile.yaml is present).
argument-hint: <community_id>
disable-model-invocation: true
target: obsidian
---

Arguments: $ARGUMENTS

Parse `$ARGUMENTS` as an integer `community_id`. If it is not a non-negative integer, render:
> `$ARGUMENTS` is not a valid community id. Pass an integer (e.g. `/graphify-moc 0`).
and stop.

Call the graphify MCP tool `get_community` with:
- `community_id`: <parsed int>

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke `/graphify-moc`.
and stop.

**If `status` is `community_not_found`:** render:
> Community `<community_id>` is not in the current graph. Check `graphify-out/GRAPH_REPORT.md` for valid community IDs.
and stop.

**If `status` is `ok`:** proceed.

Call the graphify MCP tool `load_profile` with:
- `vault_path`: <current Obsidian vault root>

The loader returns the active profile (user `.graphify/profile.yaml` deep-merged over the built-in default). Use:
- `profile.obsidian.frontmatter_template` for the note's YAML frontmatter fields (tags, type, created)
- `profile.folder_mapping.moc` as the `suggested_folder`
- `profile.obsidian.dataview.moc_query` as the Dataview block to embed

Render a MOC note body in Markdown with these sections:

1. A YAML frontmatter block populated from `profile.obsidian.frontmatter_template` with `type: moc` and `community_id: <id>`.
2. `# <Community title>` — use the community's dominant label from `meta.top_labels[0]` if present, else `Community <community_id>`.
3. `## Members` — bulleted wikilinks of the community's nodes (`[[<label>]]`), one per line, capped at the first 25 nodes.
4. `## Cohesion` — one line with `cohesion_score: <float>` from `meta.cohesion`.
5. `## Dataview` — embed the `profile.obsidian.dataview.moc_query` block verbatim.
6. `## Related Communities` — bulleted wikilinks to other MOCs (names `MOC - <community_id>`) for communities that share cross-edges (from `meta.related_communities`).

Call the graphify MCP tool `propose_vault_note` with:
- `title`: `MOC - <Community title>`
- `body_markdown`: <rendered body above>
- `suggested_folder`: `profile.folder_mapping.moc`
- `note_type`: `"moc"`
- `rationale`: `"Phase 14 /graphify-moc output for community <community_id>"`

Tell the user the proposal ID returned by `propose_vault_note` and instruct them to run `graphify approve <id>` to commit the MOC to their vault — do NOT write to the vault yourself.
