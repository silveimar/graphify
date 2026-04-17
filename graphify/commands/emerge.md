---
name: emerge
description: Surface newly-formed clusters that were not present in the previous graph snapshot.
argument-hint:
disable-model-invocation: true
---

Call the graphify MCP tool `newly_formed_clusters` with:
- `budget`: 500

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `insufficient_history`:** render:
> Only N snapshot(s) found (need ≥2). Run `/graphify` more times — each run auto-saves a snapshot.
> (Substitute N from `meta.snapshots_available`.)

**If `status` is `no_change`:** render:
> No new clusters formed since the last run. The graph structure is stable.

**If `status` is `ok`:** render as thinking-partner narrative:
- For each emerged community: name it by the dominant labels, note size, list 2–3 representative members.
- End with: "These topics were not a cluster before — want to `/trace` any of them to see where they came from?"

Keep the response under 500 tokens.
