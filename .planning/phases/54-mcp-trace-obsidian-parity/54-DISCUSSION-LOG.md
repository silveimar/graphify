# Phase 54: MCP, trace & Obsidian parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 54-mcp-trace-obsidian-parity
**Areas discussed:** MCP tool surface, /trace vs entity_trace, Obsidian export structure, Parity assertion bar

---

## MCP tool surface

| Option | Description | Selected |
|--------|-------------|----------|
| Add `relations` filter param (default `['implements']`) | Backward-compat default; one tool | ✓ |
| Widen by default to all 5 | Breaks Phase 47 callers | |
| New `typed_concept_hops` tool | Two tools | |
| Per-relation tools (`hops_implements`, etc.) | API explosion | |

**User's choice:** Add `relations` filter param (Recommended).
**Notes:** One tool, one set of docs, default preserves Phase 47 behavior.

---

## /trace vs entity_trace

| Option | Description | Selected |
|--------|-------------|----------|
| MCP-only update (`concept_code_hops` + `entity_trace`) | `/trace` stays temporal | ✓ |
| Also update `/trace` slash workflow | Conversational surface | |
| Defer `/trace` AND `entity_trace` | Smallest scope | |

**User's choice:** MCP-only update (Recommended).
**Notes:** CGRAPH-03 satisfied via `entity_trace` extension + `concept_code_hops` widening. `/trace` remains temporal — a future phase can address conversational concept↔code if users ask.

---

## Obsidian export structure

| Option | Description | Selected |
|--------|-------------|----------|
| Per-relation sections (`## Implements`, etc.) | Most readable | ✓ |
| Single `## Related` merged list | Inline relation tags | |
| Profile-driven (default per-relation) | CFG surface | |
| Dataview query block | View-time render | |

**User's choice:** Per-relation sections (Recommended).
**Notes:** CODE notes get forward sections; concept MOCs get inverse `## Implemented by` etc. Empty-section suppression. Canonical ordering: Implements → Documents → Tests → Realizes → Instantiates.

---

## Parity assertion bar

| Option | Description | Selected |
|--------|-------------|----------|
| Bidirectional + per-relation count | Catches both missing exports AND stale wikilinks | ✓ |
| Forward-only (graph → vault) | Misses stale wikilinks | |
| Per-relation count only | Quantity not identity | |
| Snapshot vault bytes | High false-positive | |

**User's choice:** Bidirectional + per-relation count (Recommended).
**Notes:** Three assertions on a fixture corpus: forward, backward, count. Strongest practical guarantee without snapshot brittleness.

---

## Claude's Discretion

- Exact insertion point for per-relation sections in `to_obsidian()` (around dataview block, around frontmatter trailer).
- `traversal_steps` payload key — new top-level vs replace `implements_traversal_steps` outright (with shim).
- `entity_trace` `include_concept_code` integration — shared `max_hops` vs separate `concept_code_max_hops` param.
- Test file organization (extend existing vs new files).

## Deferred Ideas

- `/trace` slash workflow concept↔code surfacing (future phase if users ask).
- Profile-driven `concept_code_layout` (defer to CFG-01).
- Dataview blocks for concept↔code (covered by TMPL-03 in Phase 56).
- Per-relation hop limits in `concept_code_hops` (YAGNI).
- Pre-milestone `graphify_version` PyPI bump (research evaluates).
