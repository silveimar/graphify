---
title: "Gap Analysis: April 2026 Research Corpus vs. Graphify"
date: 2026-04-12
context: Exploration session analyzing 12 documents in input_docs/April/ against graphify's current capabilities to identify improvement opportunities for v1.1–v1.3
---

# Gap Analysis: April 2026 Research Corpus vs. Graphify

## Source Documents Analyzed

| Document | Key Theme | Relevance to Graphify |
|----------|-----------|----------------------|
| Pied-Piper-Was-a-Documentary (TurboQuant) | KV cache compression → 6x memory, 600K+ context windows coming | Extraction pipeline should prepare for batch/cross-file semantic passes |
| Most-of-What-Youre-Building-Will-Be (Five Things AI Can't Replace) | Trust, Context, Distribution, Taste, Liability as durable verticals | Graphify is a **Context** tool — validates core mission, suggests deepening context persistence |
| The-Five-Things-AI-Cant-Replace (Prompt Kit) | Positioning audit + agent-readiness stress test | Agent-readiness framing exposes graphify's MCP discoverability gap |
| Your-GPUs-Just-Got-6x-More (Prompt Kit) | Memory architecture audit + compression calculator | Memory/context leakage patterns parallel graphify's lack of cross-session persistence |
| Alex_Prompter — LLM Council with Claude | Multi-model diversity + verbalized sampling + custom lenses | Analysis module could use multi-perspective lenses instead of single-pass metrics |
| 2026 AI Engineer Roadmap | 5 production projects: edge AI, coding agents, video AI, life OS, enterprise workflows | Memory hierarchies, reflection, learning from mistakes — graphify has none of these |
| Your harness-your memory (Harrison Chase) | Harness = memory = lock-in; open memory matters | Graphify's MCP server is read-only — no write-back means agents can't build memory through it |
| memory-harness (Sarah Wooders / Letta) | Memory isn't a plugin, it's the harness; Context Constitution | Graphify should own the context lifecycle, not just produce a snapshot |
| AI Engineer London 2026 | Token maxxing, codebase understanding as compounding tax, fog of war | Direct validation of graphify's mission; "narrative mode" for understanding is missing |
| k-llm-council (Ole Lehmann) | Single-model council with 5 advisor personas | Multi-perspective analysis pattern applicable to graph interpretation |
| Obsidian-Claude-Codebook | 12 slash commands for Obsidian as thinking OS | Natural extension: graphify-aware commands (/trace, /connect, /drift, /emerge) |
| Karpathy LLM Council (VentureBeat) | Original multi-model council + enterprise AI orchestration | Reinforces multi-perspective analysis; agent orchestration patterns |

## Gap Matrix

| Domain | Industry Direction | Graphify Today | Gap | Milestone |
|--------|-------------------|----------------|-----|-----------|
| Context persistence | Structured knowledge graphs as durable chokepoint | Graph rebuilt fresh each run; file-hash cache only | No run-over-run delta, no snapshots, no evolution tracking | v1.1 Phase 6 |
| Agent memory ownership | Read-write memory layer that agents own across sessions | MCP server is read-only, session-scoped | Agents can't annotate, tag, or evolve the graph | v1.1 Phase 7 |
| Obsidian round-trip | Bidirectional sync between tool output and user edits | One-way injection; merge engine preserves fields but not user content blocks | User modifications lost on re-run | v1.1 Phase 8 |
| Multi-perspective analysis | LLM council patterns; diverse analytical lenses | Single-pass mechanical analysis (god nodes, surprising connections, gaps) | No "what would a security reviewer / architect / newcomer see?" | v1.2 Phase 9 |
| Cross-file extraction | 600K+ context windows → send file clusters, not individual files | File-by-file semantic extraction | Cross-file relationships missed; will become suboptimal as windows grow | v1.2 Phase 10 |
| Codebase narratives | "Not understanding your codebase is a compounding tax" | Wiki module exists but not structured for onboarding | No guided walkthrough mode | v1.2 Phase 11 |
| Agent discoverability | Machine-readable service descriptions for agent evaluation | CLI + MCP + skill files (7 platforms) | No self-describing capability manifest for agent discovery | v1.3 Phase 12 |
| Obsidian thinking commands | 12 slash commands pattern for vault-as-second-brain | Vault export only; no commands that operate on graphify-enriched vaults | Users can't query graph relationships from within their workflow | v1.3 Phase 13 |

## Strategic Framing

The April corpus converges on a single structural insight: **context ownership is the durable competitive layer in the AI stack**. Graphify already builds structured context (knowledge graphs from arbitrary input). The gap is that it treats this as a one-shot export rather than a persistent, evolving layer that agents and humans interact with over time.

The three milestones progress along this axis:
- **v1.1** makes the graph persistent and writable (context *layer*)
- **v1.2** makes the analysis intelligent and the extraction future-proof (context *quality*)
- **v1.3** makes the graph discoverable and actionable from within user workflows (context *access*)

## Key Quotes from Source Material

> "Asking to plug memory into an agent harness is like asking to plug driving into a car." — Sarah Wooders (Letta)

> "AI is general. Value is specific. The companies that become the authoritative store of context own the chokepoint." — Five Things AI Can't Replace

> "Not understanding your codebase is a compounding tax. Every time you let the agent build something you don't fully understand, you prompt worse next time." — AI Engineer London 2026

> "The compression frontier will eventually deliver longer windows and cheaper tokens. But the memory problem you face right now is that every AI you use forgets you." — TurboQuant article
