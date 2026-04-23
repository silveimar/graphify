---
name: challenge
description: Pressure-test a stated belief against graph evidence — surface supporting vs contradicting edges.
argument-hint: <belief>
disable-model-invocation: true
target: both
---

Belief to pressure-test: $ARGUMENTS

Step 1: Identify concepts in "$ARGUMENTS". Extract the 2–4 most-likely-to-be-nodes noun phrases from the belief.

Step 2: Call the graphify MCP tool `query_graph` with:
- `seed_nodes`: [identified concepts]
- `depth`: 2
- `budget`: 500

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If no seed nodes matched any graph node:** render:
> No nodes in the current graph match the concepts in your belief. Try shorter or more specific terminology.

**If `status` is `ok`:** classify the returned edges into two buckets by confidence and relation type:

- **Supporting edges**: edges with `relation` of type `supports`, `extends`, `cites`, `defines`, or with `EXTRACTED` confidence where both endpoints are in the belief's concept set
- **Contradicting edges**: edges with `relation` of type `refutes`, `contradicts`, `opposes`, `differs_from`, or `AMBIGUOUS` confidence edges that link the belief's concepts to nodes in a DIFFERENT community

Render TWO DISTINCT SECTIONS:

    ## Evidence supporting
    [3–5 supporting edges — label, relation, source_file]

    ## Evidence contradicting
    [3–5 contradicting or missing-support gaps — label, relation, source_file]

If one side is empty, state so plainly — do NOT fabricate evidence.

End with a thinking-partner question: "The graph leans [toward / against / ambiguously on] this belief. Want to `/trace` the strongest supporting or contradicting node?"

Keep under 500 tokens.
