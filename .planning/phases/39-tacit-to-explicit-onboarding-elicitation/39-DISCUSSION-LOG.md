# Phase 39: tacit-to-explicit-onboarding-elicitation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 39-tacit-to-explicit-onboarding-elicitation
**Areas discussed:** Entry surface, Interview engine, Output wiring, Graph ingestion, Requirements & documentation

---

## Entry surface

| Option | Description | Selected |
|--------|-------------|----------|
| CLI only | `graphify elicit` as sole surface | |
| Skill only | Slash command only | |
| Both (CLI canonical) | CLI source of truth; skill thin wrapper | ✓ |
| Both (skill-first) | Skill-first; CLI for scripting | |

**User's choice:** Both: CLI canonical; skill thin wrapper.

---

## When to emphasize elicitation

| Option | Description | Selected |
|--------|-------------|----------|
| Empty/tiny corpus | Onboarding path | ✓ |
| Always | Alongside every run | |
| Explicit only | No funnel | |

**User's choice:** Emphasize when corpus is empty or tiny.

---

## Interview engine

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic | State machine only | |
| LLM-led | Adaptive only | |
| Hybrid | Scripted backbone + optional LLM deepening | ✓ |

**User's choice:** Hybrid.

---

## Output wiring — production path

| Option | Description | Selected |
|--------|-------------|----------|
| Via harness only | Graph then `harness export` | |
| Direct only | Render from elicitation state | |
| Both paths | MVP direct + harness when graph exists | ✓ |

**User's choice:** Both paths supported.

---

## Output wiring — default location

| Option | Description | Selected |
|--------|-------------|----------|
| graphify-out only | Match legacy harness default | |
| Vault-resolved | Profile / ResolvedOutput when vault context exists | ✓ |
| Explicit --out | No vault default | |

**User's choice:** Vault-resolved default when vault applies.

---

## Graph ingestion

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic extraction dict | Merge like extract() output | |
| Extend schema | New types in validate.py | |
| Sidecar merge | JSON sidecar merged in build with rules | ✓ |

**User's choice:** Sidecar merge.

---

## ELIC requirements location

| Option | Description | Selected |
|--------|-------------|----------|
| REQUIREMENTS.md first | Numbered ELIC before/at start of implementation | ✓ |
| CONTEXT/PLAN only | REQ file later | |
| User drafts separately | Planner traces IDs only | |

**User's choice:** Add ELIC requirements to REQUIREMENTS.md first.

---

## Discovery-first documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Extend README/CONFIGURING | Sections only | |
| New dedicated doc | New file under docs or project root | ✓ |
| --help only | Defer prose | |

**User's choice:** New dedicated documentation file.

---

## Claude's Discretion

- Exact CLI naming, sidecar schema filename, LLM flag shape, and merge implementation layering (modules) — planner/researcher within constraints above.

## Deferred Ideas

None captured beyond phase boundary (Phases 40–41 deferred explicitly in CONTEXT).
