# Phase 47 — UI / interaction contract (slash `/trace`)

**Scope:** Conversational slash-command and MCP response shape only. No pixel layout, components, or visual design system.

## In scope

- **`/trace`** (and narrative equivalents): user names an entity; graphify returns a **bounded, readable** summary of **concept↔code** linkage hops (`implements` / `implemented_by` semantics per Phase 46), consistent with MCP tool output where shared.
- **Empty / ambiguous entity:** same disambiguation patterns as existing narrative tools (candidate list in meta where applicable).

## Out of scope

- New Obsidian theme, CSS, or editor chrome.
- Changing temporal **`entity_trace`** snapshot UX (that tool remains snapshot-oriented unless replanned).

## States

| State | Behavior |
|-------|----------|
| Resolved | Single node match → show hop summary |
| Ambiguous | Multiple matches → list candidates, no silent pick |
| No links | Node exists but no `implements` edges in hop window → explicit “no concept↔code hops” message |

## Acceptance (UAT-level)

- Slash or MCP path can complete **one golden-path** scenario (documented in plan) without manual graph inspection.
