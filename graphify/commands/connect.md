---
name: connect
description: Find the shortest path and surprising bridge paths between two topics in the graph.
argument-hint: <topic-a> <topic-b>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Parse: `topic_a` is the first word or phrase, `topic_b` is the second distinct term. Split on the literal word "and" if present, else split on whitespace.

Call the graphify MCP tool `connect_topics` with:
- `topic_a`: [first topic parsed from $ARGUMENTS]
- `topic_b`: [second topic parsed from $ARGUMENTS]
- `budget`: 500

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `ambiguous_entity`:** list the candidates from `meta.candidates` per endpoint and ask the user to re-invoke with exact IDs.

**If `status` is `entity_not_found`:** list which endpoint was not found (`meta.missing_endpoints`) and suggest trying a shorter term.

**If `status` is `no_path`:** render:
> No path exists between '[topic_a]' and '[topic_b]' in the current graph.
> They may be in disconnected components. Try `/context` to see the top communities.

**If `status` is `ok`:** render TWO DISTINCT SECTIONS. Do NOT merge them. Do NOT present the surprising bridges as "the path between A and B" — they are globally surprising cross-community edges, not an alternative path.

    ## Shortest path (N hops)
    [Render the path from the tool's text_body's "Shortest Path" section — a chain of labels.]

    ## Surprising bridges in the graph
    [Render the tool's "Surprising Bridges" section separately — these are globally surprising edges in the full graph, relevant context but not the path between the two topics.]

End with one thinking-partner question: "Want to `/trace` one of the path nodes?"

Keep the response under 500 tokens.
