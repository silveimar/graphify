# Phase 9: Multi-Perspective Analysis with Autoreason Tournament - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 09-multi-perspective-analysis-autoreason-tournament
**Areas discussed:** Tournament orchestration, Lens configuration, Output shape, No-finding behavior

---

## Tournament Orchestration

| Option | Description | Selected |
|--------|-------------|----------|
| Skill-orchestrated | Tournament runs in skill.md using embedded Python blocks. analyze.py stays pure Python. Matches D-73. | ✓ |
| New Python module | New graphify/tournament.py with API calls. Breaks D-73 but testable as library code. | |
| Hybrid | Protocol logic in Python (round management, Borda scoring), LLM calls dispatched by skill. | |

**User's choice:** Skill-orchestrated (Recommended)
**Notes:** Preserves D-73 pattern. No anthropic SDK added as library dependency. Tournament only available through AI agent orchestration, which is the correct constraint.

---

## Lens Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in defaults + user override | 4 built-in lenses, all run by default, user can select subset via prompt. | ✓ |
| Profile-driven from .graphify/ | Lenses defined in profile.yaml. Custom lenses possible. | |
| Hardcoded only | 4 fixed lenses, no configuration. | |

**User's choice:** Built-in defaults + user override (Recommended)
**Notes:** Custom lenses deferred to v1.3. No config file needed for lens selection.

---

## Output Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Separate GRAPH_ANALYSIS.md | New report alongside existing GRAPH_REPORT.md. Clean separation of mechanical vs LLM-powered. | ✓ |
| Enhanced GRAPH_REPORT.md | Merge tournament findings into existing report. Single file. | |
| Structured JSON + markdown | JSON for MCP consumption plus markdown report. Most machine-readable. | |

**User's choice:** Separate GRAPH_ANALYSIS.md (Recommended)
**Notes:** GRAPH_REPORT.md stays fast and deterministic. GRAPH_ANALYSIS.md is opt-in and LLM-powered.

---

## No-Finding Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit clean verdict | "Clean" verdict with confidence score when "do nothing" wins. Shows voting rationale. | ✓ |
| Omit clean lenses | Only show lenses that found something. Shorter output. | |
| Always produce findings | Force every lens to find something. Matches current behavior. | |

**User's choice:** Explicit clean verdict (Recommended)
**Notes:** Every lens appears in report. Clean verdicts show why adversarial revision was rejected. Makes silence meaningful.

---

## Claude's Discretion

- Tournament round prompt design (role separation, context leakage prevention)
- Number of judges per Borda round
- How mechanical metrics feed into lens analysis

## Deferred Ideas

- Custom user-defined lenses via profile.yaml — v1.3
- Structured JSON output for MCP — consider for Phase 9.2
- Per-lens MCP tools — v1.3
