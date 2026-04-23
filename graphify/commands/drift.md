---
name: drift
description: Surface nodes whose community, centrality, or edge density has trended consistently across recent snapshots.
argument-hint:
disable-model-invocation: true
target: both
---

Call the graphify MCP tool `drift_nodes` with:
- `top_n`: 10
- `max_snapshots`: 10
- `budget`: 500

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `insufficient_history`:** render:
> Only N snapshot(s) found (need ≥2). Run `/graphify` more times to build history — drift patterns emerge across multiple sessions.
> (Substitute N from `meta.snapshots_available`.)

**If `status` is `ok`:** render as thinking-partner narrative, not a table:
- Name the 3 most drifting nodes. What communities have they crossed? Growing or shrinking in centrality?
- Is the drift directional (consistently moving toward/away from a theme)?
- End with ONE pressing question: "You've been circling [X] — want to look at [Y]?" where X is the top drifter and Y is either its current community or a suggested `/trace`.

Keep the response under 500 tokens.
