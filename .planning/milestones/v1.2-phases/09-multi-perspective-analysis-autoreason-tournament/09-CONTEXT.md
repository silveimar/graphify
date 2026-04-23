# Phase 9: Multi-Perspective Analysis with Autoreason Tournament - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade graphify's analysis from mechanical graph metrics (current `analyze.py` — degree counting, betweenness centrality, cross-community edges) to LLM-assisted multi-perspective interpretation using autoreason's tournament protocol. Four configurable analysis "lenses" independently analyze the graph, compete in adversarial tournaments, and produce a unified analysis report where "no finding" is a valid, explicit verdict.

</domain>

<decisions>
## Implementation Decisions

### Tournament Orchestration
- **D-75:** Tournament runs in skill orchestration (skill.md), not in Python library code. Preserves D-73 (CLI is utilities-only; skill drives pipeline). `analyze.py` stays pure Python for mechanical metrics (god_nodes, surprising_connections, knowledge_gaps). Tournament rounds use embedded LLM calls in the skill.
- **D-76:** Tournament protocol follows autoreason pattern: (1) lens produces incumbent analysis (A), (2) adversarial agent generates competing revision (B), (3) synthesis agent merges (AB), (4) fresh blind judges score A/B/AB via Borda count with no shared context.

### Lens Configuration
- **D-77:** Ship 4 built-in lenses: security, architecture, complexity, onboarding. All 4 run by default when multi-perspective analysis is triggered.
- **D-78:** User can select a subset of lenses via skill prompt (e.g., "analyze for security and architecture"). No config file needed for lens selection.
- **D-79:** Custom user-defined lenses deferred to v1.3 (potential profile-driven via `.graphify/` alongside vault config).

### Output Shape
- **D-80:** Tournament produces a separate `GRAPH_ANALYSIS.md` in `graphify-out/`. Existing `GRAPH_REPORT.md` (mechanical metrics) is untouched. Clean separation: mechanical report is fast/deterministic (no LLM), analysis report is LLM-powered and opt-in.
- **D-81:** `GRAPH_ANALYSIS.md` contains: per-lens findings with verdicts, convergences across lenses, tensions/disagreements between lenses, top insight per lens, and overall verdict.

### No-Finding Behavior
- **D-82:** When "do nothing" (incumbent with no issues) wins the Borda vote for a lens, emit an explicit "Clean" verdict with confidence score. Show the tournament voting rationale — why the adversarial revision was rejected.
- **D-83:** Every lens always appears in `GRAPH_ANALYSIS.md` — clean lenses show their verdict, not silence. Makes "we checked and it's fine" a meaningful, auditable signal.

### Claude's Discretion
- Tournament round prompts (system prompts for incumbent/adversary/synthesizer/judge roles) — design for maximum separation and minimal context leakage
- Number of judges per Borda round (2-3 is typical in autoreason)
- How mechanical metrics from `analyze.py` feed into lens analysis (as context, not as findings to defend)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Autoreason Protocol
- `input_docs/Build-agents-that-never-forget.md` — Cognee graph-vector hybrid memory architecture (context for why graph self-improvement matters)
- `.planning/notes/agent-memory-research-gap-analysis.md` — Gap analysis decisions and exclusions for all 5 researched sources

### Existing Analysis Code
- `graphify/analyze.py` — Current mechanical analysis (523 lines). god_nodes(), surprising_connections(), knowledge_gaps(). Pure Python, no API calls.
- `graphify/report.py` — Current GRAPH_REPORT.md renderer (155 lines). Template for how GRAPH_ANALYSIS.md should be structured.
- `graphify/skill.md` — Main skill file. Contains existing LLM integration pattern for semantic extraction. Tournament orchestration will follow this pattern.

### Architecture Decisions
- `.planning/codebase/ARCHITECTURE.md` — Pipeline architecture: detect→extract→build→cluster→analyze→report→export
- `graphify/serve.py` — MCP server with 14 tools. Future consumer of richer analysis data.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analyze.py`: `god_nodes()`, `surprising_connections()`, `knowledge_gaps()` — mechanical metrics that feed into tournament as context
- `report.py`: `render_report()` — template pattern for generating markdown reports from structured data
- `skill.md`: Existing LLM call pattern for semantic extraction — reusable for tournament round calls
- `validate.py`: Schema validation pattern — could validate tournament output structure

### Established Patterns
- Analysis returns plain dicts: `{"god_nodes": [...], "surprising_connections": [...], "knowledge_gaps": [...]}`
- Reports are markdown rendered from dicts — no templating library
- LLM integration is skill-orchestrated with embedded Python blocks
- All output goes to `graphify-out/` directory

### Integration Points
- Tournament sits between `analyze()` and `report()` in the pipeline
- `skill.md` will call `analyze.py` for mechanical metrics, then run tournament rounds, then write `GRAPH_ANALYSIS.md`
- MCP server could later serve per-lens findings via new tools (Phase 9.2 scope)

</code_context>

<specifics>
## Specific Ideas

- Autoreason's blind Borda voting with separated roles (critic, author, synthesizer, judges share no context) — directly from NousResearch/autoreason
- "Do nothing competes fairly" — the incumbent (no issues) is always option A in the tournament
- The knowledge graph itself is the "shared cognitive map" (SPAR-Kit's ABSTRACT step) that all perspectives reason over — graphify's unique differentiator
- Confidence scores on verdicts reflect judge agreement (unanimous = high, split = low)

</specifics>

<deferred>
## Deferred Ideas

- Custom user-defined lenses via `.graphify/profile.yaml` — v1.3 scope
- Structured JSON output (`analysis.json`) for MCP consumption — consider for Phase 9.2
- Per-lens MCP tools (`get_security_findings`, etc.) — v1.3 scope
- Graph argumentation mode (Phase 16) builds on this tournament as interactive decision support

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-multi-perspective-analysis-autoreason-tournament*
*Context gathered: 2026-04-14*
