---
name: SEED-002
description: Export graphify memory artifacts (SOUL.md, HEARTBEAT.md, operating-model.json) in a harness-agnostic format so Claude Code, Letta, OpenClaw, Cursor, etc. can all consume without lock-in
status: dormant
trigger_when: Multi-harness support becomes a real user ask — OR lock-in friction appears in a UAT — OR v1.4 Phase 13 (Agent Capability Manifest) is being planned (natural companion)
planted_during: v1.3 scoping (2026-04-16)
planted_date: 2026-04-16
source: April 2026 docs — Your-harness-your-memory (Harrison Chase), memory-harness (Sarah Wooders/Letta), Structural-Shifts-in-AI
fit: adjacent
effort: medium
---

# SEED-002: Harness Memory Export

## The Idea

The April 2026 docs name **memory lock-in** as a structural threat: whoever owns the harness owns the memory format, and users who invest in Claude Code's `CLAUDE.md` can't easily migrate to OpenClaw, Letta, Cursor, or future harnesses. Each harness has diverging schema for the "agent OS" files.

Graphify could become the **neutral memory hub** — serialize graphify's internal state (graph + annotations + agent edges + elicited facts) out to a canonical set of portable artifacts:

- `SOUL.md` — decision framework (portable across all major harnesses)
- `HEARTBEAT.md` — recurring triggers / scheduled reflection
- `USER.md` — user profile + preferences
- `operating-model.json` — executable workflow logic
- `AGENTS.md` — harness-agnostic agent definitions
- `CLAUDE.md` — Claude Code-native mirror (generated from the above)

**Inverse direction also matters**: *ingest* existing `CLAUDE.md` / `AGENTS.md` / harness memory into graphify's graph so the user's investment in one harness becomes migratable to another.

## Why This Matters

- **Anti-lock-in positioning**: As harnesses compete on memory, users rationally avoid deep investment. A neutral hub removes that risk.
- **Distribution advantage**: Graphify becomes the tool you run *before* committing to a harness — and stays useful after.
- **Low implementation risk**: These are mostly format-conversion problems, not novel algorithms. Schemas exist; we just need a canonical round-trip.

## Why It's a Seed, Not a Phase

- **Too early**: Most users haven't hit harness lock-in yet because they haven't invested enough in any single harness. The pain point is real but not acute.
- **Requires SEED-001 or v1.4 Phase 14 to exist first**: Without elicited SOUL/HEARTBEAT artifacts (or a user-authored set), there's nothing to export. This seed depends on upstream data sources.
- **v1.3 priorities elsewhere**: User's North Star is agent-viability, graph quality, human UX — not portability.

## When to Surface

Activate when **any** of the following is true:

- Multi-harness support becomes a real user ask (someone says "I want to use graphify output with both Claude Code and Letta")
- Lock-in friction appears in a UAT (user can't migrate something because the format is proprietary)
- v1.4 **Phase 13** (Agent Capability Manifest) is being planned — these are natural companions: Manifest declares *what* graphify exposes; Export declares *how* its memory travels
- SEED-001 ships — at that point, we *have* SOUL/HEARTBEAT artifacts to export and the companion feature is obvious
- A competitor (Cognee, Letta) publishes an open memory interchange format — we should match or exceed it

## Potential Shape (Non-Binding)

- New module: `graphify/harness_export.py` + mirror `harness_import.py`
- New CLI: `graphify export-harness [--format soul|heartbeat|claude|agents|all] --out <path>`
- New CLI: `graphify import-harness <file>` (inverse — brings external CLAUDE.md / AGENTS.md into graph)
- Format layer: A `graphify/harness_schemas/*.yaml` directory capturing field mappings per harness
- Effort estimate: 2 plans, medium complexity. Schema definition is the bulk; serialization is mechanical.
- Dependencies: PyYAML (already optional); no new required deps

## Related

- Companion seed: **SEED-001** (Tacit Knowledge Elicitation) — they pair naturally. Elicitation produces the artifacts; this exports them.
- Adjacent: v1.4 **Phase 13** (Agent Capability Manifest) — `Capability Manifest` declares the MCP surface; this declares the data portability surface. Consider shipping together.
- Contrast: v1.4 **Phase 14** (Obsidian Thinking Commands) — `commands consume memory from the graph`; this seed exports memory *out of* the graph. Different directions of flow.

## Risks

- Harness formats diverge rapidly; the canonical schema may become a maintenance tax
- "Harness-agnostic" is aspirational — we'll always lag the newest harness's proprietary format by some weeks
- Low pain → low demand today → easy to over-invest
