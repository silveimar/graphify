---
seed_id: SEED-bidirectional-concept-code-links
trigger_when: a future milestone treats the graph as a navigable knowledge tool (not just an output dump) — likely follows v1.8's two-class god-node taxonomy
planted_during: /gsd-explore for v1.8 scoping
planted_date: 2026-04-28
status: dormant
---

# SEED: Bidirectional Concept↔Code Links as a First-Class Graph Feature

## Idea

v1.8 introduces frontmatter-level bidirectional links between code-derived god nodes (`CODE_<repo>_<name>.md`) and their parent concept MOC (`concept_moc: [[<MOC>]]` ↔ `members: [[CODE_...]]`). These are *output-layer* links — written into Obsidian frontmatter at export time.

This seed proposes promoting the relationship to a first-class feature of the graph itself: concept ↔ implementation as a typed edge in the NetworkX graph, queryable via MCP, traceable via `/trace`, with its own confidence scoring and provenance.

## Why This Matters

Today graphify's edges are dominated by structural relations (`contains`, `imports`, `calls`, `defines_class`). The conceptual relations are flat tags or community membership integers — semantically thin.

If concept↔code became a typed edge:
- `/trace AuthService` could surface "this is an implementation of [Authentication Architecture concept]" instead of just "this is a class in portal-api"
- Cross-repo concept identity becomes possible: AuthService in portal-api and AuthHandler in mobile-api both link to the same `Authentication Architecture` MOC
- Graph queries could ask "show me all implementations of [Caching Strategy] across the vault"
- Concept drift becomes detectable: when a community gets renamed by the LLM (F4 cache invalidates), the old-concept ↔ new-concept transition is a real graph signal

## Trigger Conditions to Surface

Surface this seed when ANY of the following are true:

1. A future milestone explicitly themes around "graph as knowledge tool" or "concept-level reasoning"
2. v1.8 ships and users start asking for cross-repo concept tracking
3. The MCP server `/connect` or `/trace` slash commands show high usage and users want richer traversal targets than `contains`/`calls`
4. Multi-vault federation becomes a goal (concept identity across vaults requires concept-level edges to be first-class)
5. The autoreason tournament from v1.2 gets extended to evaluate "is this code an instance of this concept?" predicates

## Why Not Now (v1.8)

v1.8's frontmatter-level approach is enough to deliver the user's immediate need (visual distinction, navigability in Obsidian). Promoting concept↔code to a typed graph edge requires:
- Schema change to `validate.py` (new edge relation type)
- Storage decision (do these edges persist in the cluster output, or get derived at export time?)
- Cost amplification (LLM calls now need to assign confidence per edge, not just name communities)

That's a meaningful chunk of work that would distract from v1.8's already-sizable scope. Better to ship v1.8's frontmatter approach, validate the user-facing pattern works, then promote it to graph-level if usage justifies the lift.

## Related Artifacts

- v1.8 MILESTONE-CONTEXT.md F5 (two-class god-node taxonomy — the frontmatter precursor)
- v1.3 SLASH-02 `/trace` command — would benefit from typed concept edges
- v1.3 GRAPH-04 cross-source ontology alignment — already does entity-level cross-source merging; concept-level edges are the next layer up
- v1.2 REQ-09 analysis lenses — could include a "concept coverage" lens once typed edges exist
