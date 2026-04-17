---
name: ghost
description: Answer in the user's voice, grounded in their graph contributions and annotations.
argument-hint: <question or prompt>
disable-model-invocation: true
---

Question or prompt to answer as the user: $ARGUMENTS

Step 1: Call the graphify MCP tool `get_annotations` with:
- `peer_id`: "self"  (falls back to most-annotated peer if "self" has no annotations)

Step 2: Call the graphify MCP tool `god_nodes` with:
- `top_n`: 10

`get_annotations` returns a JSON array (not a meta envelope).
`god_nodes` returns plain text (not a meta envelope).

**If `get_annotations` returns an empty array `[]`:** render:
> No annotations found — /ghost needs your own notes or rationales in the graph to learn your voice.
> Annotate nodes via `/graphify` workflow (rationale / peer_id="self"), then re-invoke.

**If `god_nodes` returns an empty list:** render:
> No god nodes found — run `/graphify` to build the graph first.

**Otherwise:** render in the user's voice:
1. Extract voice patterns from the returned annotations — vocabulary, sentence structure, tone, idiom.
2. Extract the user's conceptual concerns from `god_nodes` — what they've been thinking about most.
3. Answer "$ARGUMENTS" AS THE USER — first-person, using their vocabulary, drawing on their conceptual universe.
4. Do NOT pretend to be a different person — this is reflective, not impersonation. Make clear the voice is learned from the user's own graph contributions.
5. Keep under 500 tokens.

End with a thinking-partner beat: "This is how you might frame it — does it match how you'd actually answer?"
