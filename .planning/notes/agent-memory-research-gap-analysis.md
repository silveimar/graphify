# Agent Memory & Autoreason Research — Gap Analysis

**Date:** 2026-04-14
**Sources researched:**
- `input_docs/Build-agents-that-never-forget.md` — Cognee graph-vector hybrid memory (topoteretes/cognee)
- `input_docs/5-Structural-Shifts-in-AI-That.md` — Structural shifts prompt kit (inference economics, multi-perspective analysis frameworks)
- `NousResearch/autoreason` — Tournament-based self-refinement with blind Borda voting
- `rohitg00/agentmemory` — 4-tier memory consolidation (working→episodic→semantic→procedural), triple-stream retrieval (BM25+vector+graph), 43 MCP tools
- `thedotmack/claude-mem` — Progressive disclosure 3-layer retrieval, SQLite+Chroma, lifecycle hooks

## Decisions Made

### Incorporated into roadmap:

1. **Phase 9 upgraded** — Replaced 3-stage council protocol with autoreason tournament (incumbent/adversarial/synthesis + blind Borda voting + "no finding" as first-class option)
2. **Phase 9.1 added** — Query Telemetry & Usage-Weighted Edges (from Cognee memify + agentmemory consolidation patterns)
3. **Phase 9.2 added** — Progressive Graph Retrieval (from claude-mem 3-layer disclosure + agentmemory triple-stream retrieval)

### Explicitly excluded:

- **Vector embeddings / semantic search** — Changes graphify's identity from graph-topology tool to Cognee competitor
- **4-tier memory consolidation** — Solves session memory, not knowledge graph building
- **43 MCP tools expansion** — Would bloat API surface without strengthening core
- **Lifecycle hooks (SessionStart, etc.)** — Graphify input is explicit (`graphify run`), not ambient capture

## Key Insights

- Graphify IS the graph layer that Cognee positions as the missing piece beyond vector search
- Autoreason's "do nothing competes fairly" principle prevents hallucinated findings in clean graphs
- Usage-weighted edges (from memify) are the biggest gap — no planned phase addressed retrieval-driven graph learning
- Progressive disclosure solves the context blowout problem graphify will hit at 500+ nodes
