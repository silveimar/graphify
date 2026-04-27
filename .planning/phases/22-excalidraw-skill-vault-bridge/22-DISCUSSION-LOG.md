# Phase 22: Excalidraw Skill & Vault Bridge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 22-excalidraw-skill-vault-bridge
**Areas discussed:** Pure-Python fallback layout, Install surface, Vault write semantics, `.mcp.json` delivery

---

## Pure-Python Fallback Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Per-layout-type dispatch | Switch on profile diagram_types[].layout_type; deterministic algo per type (grid/hierarchical/concentric); stable for tests. | ✓ |
| Single deterministic grid | Ignore layout_type; always N×N grid sized by node count. Simplest. | |
| Force-directed with fixed seed | Spring layout, seed=42. Better for arbitrary graphs but adds numerical dep footprint. | |
| Defer layout — emit at (0,0) | Structural only; user arranges in Excalidraw. Minimum viable. | |

**User's choice:** Per-layout-type dispatch (Recommended).
**Notes:** Matches Phase 21's 6 built-in diagram_types semantics; reuses the `layout_type` field already on each profile entry.

---

## Install Surface (`_PLATFORM_CONFIG`)

| Option | Description | Selected |
|--------|-------------|----------|
| Peer platform entry | New top-level _PLATFORM_CONFIG key; `graphify install excalidraw`. Matches existing platform-positional pattern. | ✓ |
| `--excalidraw` flag on install | `graphify install --excalidraw`; matches roadmap wording verbatim. Asymmetric with positional pattern. | |
| Sub-entry under claude only | `graphify install claude --excalidraw`. Tightest scope; new flag pattern. | |
| Both peer entry + flag | Two install paths, one source of truth in dict. | |

**User's choice:** Peer platform entry (Recommended).
**Notes:** Roadmap's `--excalidraw` reads as a label; the actual surface is `graphify install excalidraw` (positional). All existing platforms use the same shape.

---

## Vault Write Semantics

### Collision behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse by default; `force` to override | Default: skill writes only if path is free; on collision, exit cleanly. Re-run with explicit force. | ✓ |
| Auto-suffix on collision | Write `name-2.excalidraw.md`, `-3`, etc. Never blocks; pollutes vault. | |
| Always overwrite | One seed = one canonical diagram. Risk: lose user edits. | |
| Prompt user inline | Conversational at step 6; adds a turn to the pipeline. | |

**User's choice:** Refuse by default; user re-runs with force (Recommended).
**Notes:** Matches Phase 21's `--init-diagram-templates` idempotency stance. Safe for re-runs.

### Output path source

| Option | Description | Selected |
|--------|-------------|----------|
| Profile-driven with built-in fallback | Read from profile.yaml diagram_types entry; fall back to `Excalidraw/Diagrams/`. | ✓ |
| Hardcoded `Excalidraw/Diagrams/` | No profile lookup. Simple but breaks configurable-vault-adapter philosophy. | |
| Profile-driven, required field | No fallback; missing field is an error. Tighter; default-profile users get errors. | |

**User's choice:** Profile-driven with built-in fallback (Recommended).
**Notes:** One profile entry, two path slots — template input (Phase 21) + diagram output (Phase 22).

---

## `.mcp.json` Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Documented snippet inside SKILL.md | Fenced block; user copies. graphify never touches user `.mcp.json`. | ✓ |
| Auto-merge at install time | graphify reads, merges, writes `.mcp.json`. Risk of corrupting user config. | |
| Separate `graphify mcp install` command | Two-step install; each step has one job. New CLI surface. | |
| Print to stdout post-install | Snippet in SKILL.md + post-install message; needs single source. | |

**User's choice:** Documented snippet inside SKILL.md (Recommended).
**Notes:** Matches project ethos — graphify writes its own files, never edits user config. Idempotent by definition.

---

## Claude's Discretion

- Exact public API of new layout helpers (function names, parameter shapes).
- Whether layout primitives live in `graphify/excalidraw.py` or a new submodule.
- Test fixture organization (per-layout fixtures vs parametrized).
- Phrasing of the skill-level `force` argument the agent passes on collision.

## Deferred Ideas

- Auto-merge `.mcp.json` (revisit as `graphify mcp install` in v1.6+).
- Multi-seed diagrams.
- Layout customization beyond `layout_type` (spacing, edge routing).
- Force-directed / spring layouts in the fallback.
- Inline overwrite-vs-cancel prompt at write time.
- Auto-suffix on collision.
