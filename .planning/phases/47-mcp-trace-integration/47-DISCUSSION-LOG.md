# Phase 47: MCP & Trace Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 47-MCP & Trace Integration
**Areas discussed:** Manifest & docs (capability / server.json / skills / RELATIONS+ARCHITECTURE)

---

## Manifest & docs

| Option | Description | Selected |
|--------|-------------|----------|
| Full stack | Registry + docstrings + YAML meta + regenerated server.json + capability tests | ✓ |
| Code + server.json only | YAML optional | |
| Minimal | Registry + docstrings; server.json manual | |

**User's choice:** Full stack lockstep when MCP surface changes.
**Notes:** Aligns with CCODE-03 “manifest/capability and skill docs reflect any new tools or parameters.”

---

## Where to document tool ↔ relation semantics

| Option | Description | Selected |
|--------|-------------|----------|
| RELATIONS subsection only | Single doc | |
| ARCHITECTURE only | RELATIONS stays vocabulary-only | |
| Both | Thin pointer in RELATIONS + fuller narrative elsewhere | ✓ |

**User's choice:** Both RELATIONS and ARCHITECTURE (or codebase pipeline doc).

---

## Skill / harness tool tables

| Option | Description | Selected |
|--------|-------------|----------|
| All skills strict parity | Update every enumerated table when tools change | ✓ |
| Canonical one + pointers | | |
| Manifest-only | De-emphasize skill tables | |

**User's choice:** Update all platform skill variants and harness enumerations.

---

## Claude's Discretion

- MCP tool naming collision with existing temporal **`entity_trace`** — user did not select “surface” area; planner proposes approach.
- `/trace` mapping, hop semantics, golden-path fixture — not selected; planner defaults.

## Deferred Ideas

- None captured as new capabilities beyond Phase 47 boundary during this session.
