---
name: graphify-ask
description: Ask a natural-language question about the codebase and receive a graph-grounded narrative answer with citations.
argument-hint: <question>
disable-model-invocation: true
target: both
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `chat` with:
- `query`: "$ARGUMENTS"
- (omit `session_id` — slash-command is single-shot; the MCP tool will generate/accept one if the agent wants multi-turn)

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `no_results`:** render the fuzzy suggestions from `meta.suggestions` as "Did you mean: A, B, C?". Do NOT echo the original query's unmatched terms back.

**If `status` is `ok`:** render `text_body` verbatim (it is already token-capped and cited). Do NOT re-summarize. After the body, list the citations inline:
> **Cited nodes:** [label1](source_file1), [label2](source_file2), …

If `meta.resolved_from_alias` is non-empty, append a small note:
> _Note: some cited IDs were redirected from merged aliases; the canonical IDs shown are the current graph's node IDs._

Keep total output under 500 tokens (the tool already caps narrative; do not expand).
