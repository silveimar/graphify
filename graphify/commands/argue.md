---
name: graphify-argue
description: Run a structurally-enforced multi-perspective graph debate on a decision question, grounded in the knowledge graph.
argument-hint: <decision question>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `argue_topic` with:
- `topic`: "$ARGUMENTS"
- `scope`: "topic"

The response is a D-02 envelope: a short text body, then `---GRAPHIFY-META---`, then a JSON object.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim — "No graph loaded. Run `/graphify` first to build a knowledge graph, then retry `/graphify-argue`."

**If `status` is `no_results`:** render — "The question didn't match any nodes in the graph. Try rephrasing with terms that appear in the codebase, or widen scope with the `argue_topic` tool."

**If `status` is `ok`:**
1. Read `meta.argument_package` — it contains the evidence subgraph summary (nodes, edge_count, perspectives) that the debate will be grounded in.
2. Follow the SPAR-Kit debate orchestration in skill.md `/graphify-argue` section (see §Phase 16 Graph Argumentation Mode). The skill loop runs up to 6 rounds of 4-persona debate with per-round blind labels (reusing the Phase 9 blind-label harness), validates every persona turn via `graphify.argue.validate_turn`, and writes the final advisory-only transcript to `graphify-out/GRAPH_ARGUMENT.md`.
3. After the debate completes, summarize the verdict (consensus / dissent / inconclusive), the per-round cite-overlap Jaccard trajectory, and the path to `GRAPH_ARGUMENT.md` for the user.

If `meta.resolved_from_alias` is non-empty, append a small note: "Some node references were redirected to canonical IDs: {list}."

**Advisory-only (ARGUE-09):** the transcript is strictly advisory — graphify does not and will not mutate code, the knowledge graph, or any project file as a result of `/graphify-argue`. The debate is evidence for a human decision, never an action.

Keep the user-facing summary under 400 tokens; the full transcript lives in `graphify-out/GRAPH_ARGUMENT.md`.
