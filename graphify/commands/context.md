---
name: context
description: Load a full graph-backed summary of the current knowledge graph — active god nodes, top communities, and recent changes.
argument-hint:
disable-model-invocation: true
---

Call the graphify MCP tool `graph_summary` with:
- `top_n`: 10
- `budget`: 500

The response is a hybrid envelope: a human-readable text body, then the line `---GRAPHIFY-META---`, then a JSON metadata block.

Parse `meta.status`. Handle these cases:

**If `status` is `no_graph`:** render verbatim, do not embellish:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `ok`:** render as a thinking-partner summary:
1. Open with a one-line frame: "Your knowledge graph has N nodes across M communities."
2. Call out the top 3 god nodes — what they are, why they are central.
3. Name the top 3 communities by size — one-line theme per community from the sample labels.
4. Summarize the most recent delta: "Since your last run, A nodes joined, B departed, C edges formed." Use `meta.delta`.
5. Close with one thinking-partner question pointing to a next step: if delta is non-empty, suggest `/emerge`; if god nodes are unexpected, suggest `/trace <node>`; if the graph is stable, suggest `/drift` to see what is changing.

Keep the response under 500 tokens. Do not echo raw JSON. Do not restate the tool's full output verbatim — synthesize.
