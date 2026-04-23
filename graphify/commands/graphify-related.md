---
name: graphify-related
description: Show graph-connected notes (community peers + 1-hop neighbors) for the given vault note, scoped to that note's source_file.
argument-hint: <note-path>
disable-model-invocation: true
target: obsidian
---

Arguments: $ARGUMENTS

Treat `$ARGUMENTS` as a path to an Obsidian note (absolute, vault-relative, or home-relative).

Read the note file at `$ARGUMENTS`. Parse its YAML frontmatter block (lines between the first two `---` markers). Extract the `source_file` field — the path of the real project file this note summarises.

If the note has no YAML frontmatter, or no `source_file` field, render:
> The note at `$ARGUMENTS` has no `source_file:` frontmatter field. `/graphify-related` needs this field to look up the note's position in the graph. Add `source_file: <path-in-project>` to the note's frontmatter and retry.
and stop.

Call the graphify MCP tool `get_focus_context` with:
- `focus_hint`: `{"file_path": "<source_file value>"}`
- `neighborhood_depth`: 2
- `include_community`: true

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke `/graphify-related`.
and stop.

**If `status` is `no_context`:** render verbatim (TM-14-03 explicit-silence mitigation for the `no_context` branch):
> The `source_file` path `<source_file value>` does not resolve to any node in the graph (status: `no_context`). Possible causes:
> - The path is outside the project root snapshot (Phase 18 CR-01 guard).
> - The file was added after the last `/graphify` run — rebuild the graph.
> - The note's frontmatter points at a path that doesn't exist on disk.
and stop.

**If `status` is `ok`:** render the `text_body` verbatim. It already contains:
1. `## Community peers` — other nodes in the same community as `source_file`.
2. `## 1-hop neighbors` — direct graph neighbors outside the community.
3. `## Citations` — `{node_id, label, source_file}` per reference.

Do NOT re-summarize or paraphrase. Do NOT write to the vault — this command is read-only.
