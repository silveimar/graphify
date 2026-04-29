---
name: SEED-001
description: Structured interview engine that extracts operational/tacit knowledge from humans and produces SOUL.md/HEARTBEAT.md/USER.md artifacts alongside graph nodes
status: dormant
trigger_when: Future milestone focuses on onboarding or discovery — OR a user says they can't articulate what graphify should ingest — OR v1.5+ scoping considers "upstream" features before extraction
planted_during: v1.3 scoping (2026-04-16)
planted_date: 2026-04-16
source: April 2026 docs — Your-agent-needs-a-SOUL, Obsidian-Claude-Codebook, Your-harness-your-memory
fit: adjacent-to-tight
effort: medium
---

# SEED-001: Tacit-to-Explicit Elicitation Engine

## The Idea

Most graphify inputs today (code, docs, papers, images) are *already* externalized knowledge. The 18 April 2026 docs reveal a recurring bottleneck they call the **"40-hour wall"**: agents fail because humans can't articulate their own operational knowledge in agent-readable language. Every agent platform skips this step.

Graphify could own this upstream layer with a structured interview flow:

1. **Rhythms** — recurring work patterns (daily/weekly/monthly)
2. **Decisions** — judgment calls: when/why, what trade-offs
3. **Dependencies** — who/what unblocks the user
4. **Knowledge** — what the user knows that isn't written down
5. **Friction** — what wastes time, where the agent fits

Each layer has checkpoint validation ("confirm before saving"). Output: a graph populated with elicited facts *plus* derived agent-OS artifacts (SOUL.md for decision framework, HEARTBEAT.md for recurring triggers, USER.md for profile). The graph isn't just extracted from existing artifacts — it's *co-created* with the human.

## Why This Matters

- **Moat potential**: If graphify owns the tacit→explicit layer, it becomes the upstream *every* harness wants to consume. Claude Code, Letta, OpenClaw all compete on what you do *with* memory — none of them help you *create* memory from scratch.
- **Research-backed**: The April docs (especially Your-agent-needs-a-SOUL and Obsidian-Claude-Codebook) explicitly frame this as the unsolved problem preventing agent adoption.
- **Graph-native fit**: Interview output is relational — decisions depend on rhythms, dependencies link to people, friction ties to decisions. The graph structure is the *right* shape for this data.

## Why It's a Seed, Not a Phase

- **Sibling-vs-core tension**: This feels adjacent to graphify's "any input → graph" framing. It's more of a sibling tool that *feeds* graphify than a graphify feature.
- **v1.3 priorities elsewhere**: User's North Star for v1.3 is agent-viability (9.2), graph quality (10), and human UX (11). Adding elicitation would dilute focus.
- **Uncertainty about demand**: No user has explicitly asked for this. It's a researcher-flagged opportunity, not a user-flagged pain point.

## When to Surface

Bring this back into active scoping when **any** of the following is true:

- A future milestone focuses on onboarding, discovery, or "make agents useful for new domains"
- A real user (not a researcher) says: *"I want to use graphify but I don't have docs/code/artifacts — just my head"*
- v1.5+ is being scoped and the milestone slot is available for an "upstream" feature
- A sibling project explicitly needs structured-interview output and there's reuse opportunity
- Competitors (Cognee, Letta) ship something similar — then this becomes defensive, not offensive

## Potential Shape (Non-Binding)

- New module: `graphify/elicit.py` with an interview state machine
- New CLI: `graphify elicit --profile <role>` (roles: developer, operator, owner, etc.)
- Output: graph nodes + `SOUL.md` + `HEARTBEAT.md` + `USER.md` + `operating-model.json`
- Effort estimate: 2–3 plans, medium complexity (state machine is simple; *good* interview prompts are the hard part — likely needs its own research phase)
- Dependencies: none new; reuses existing extract/build/export stack

## Related

- Companion seed: **SEED-002** (Harness Memory Export) — they pair naturally. Elicitation produces the artifacts; export makes them portable across harnesses.
- Contrast: v1.4 **Phase 14** (Obsidian Thinking Commands) — commands that *use* SOUL/HEARTBEAT, whereas this seed *produces* them. If Phase 14 ships first and users demand "where does SOUL come from?", that's a strong trigger to activate this seed.

## Risks

- Prompt-engineering-heavy, easy to ship something mediocre
- May stray into "AI coach" territory which is not graphify's mission
- Hard to evaluate: success = a *useful* SOUL.md, and "useful" is subjective
