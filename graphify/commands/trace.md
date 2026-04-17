---
name: trace
description: Show how a named entity has evolved across graph snapshots — first-seen, community journey, centrality trend, current status.
argument-hint: <entity-name>
disable-model-invocation: true
---

The entity to trace is: $ARGUMENTS

Call the graphify MCP tool `entity_trace` with:
- `entity`: "$ARGUMENTS"
- `budget`: 500

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `insufficient_history`:** render:
> Only N snapshot(s) found (need ≥2 for a trace). Run `/graphify` more times — snapshots auto-save each run.
> (Substitute N from `meta.snapshots_available`.)

**If `status` is `ambiguous_entity`:** render:
> Multiple entities match '$ARGUMENTS'. Which did you mean?
> [Render each entry from `meta.candidates` as a numbered list: `ID — label (source_file)`.]
> Re-invoke with an exact ID: `/trace <id>`

**If `status` is `entity_not_found`:** render:
> No entity matching '$ARGUMENTS' found in any snapshot. Try a shorter search term or check spelling.

**If `status` is `ok`:** render as a timeline:
1. **First seen**: timestamp from `meta.first_seen` (e.g., "Snapshot 1 of N, 2026-03-01").
2. **Community journey**: per-snapshot (timestamp → community) pairs — highlight changes.
3. **Connectivity trend**: degree per snapshot — growing, shrinking, or stable.
4. **Current status**: whether the entity is present at the tip, and its community there.
5. **If `meta.resolved_from_alias` is present:** mention the alias redirect: "Resolved '$ARGUMENTS' → `<canonical_id>`".

End with one thinking-partner follow-up: if community changed, suggest `/drift`; if entity just appeared, suggest `/emerge`.

Keep the response under 500 tokens.
