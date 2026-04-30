# Phase 47 — Technical research: MCP & trace for concept↔code

**Date:** 2026-04-30  
**Question answered:** What do we need to know to plan MCP/trace for `implements` / `implemented_by`?

## Findings

### Existing surfaces

- **`entity_trace` MCP** (`serve._run_entity_trace`) = **temporal** presence across snapshots — **not** concept↔code graph hops. Satisfying **CCODE-04** by overloading this name would confuse agents; prefer a **new tool** (e.g. `concept_code_hops`) or a clearly named mode with defaults preserving old behavior.
- **`get_neighbors`** already accepts `relation_filter` — one-hop `implements` listing is possible today but **not documented** as the CCODE-03 primary path; multi-hop bounded walk still needs a dedicated helper or tool.
- **Manifest pipeline (Phase 13):** `mcp_tool_registry.build_mcp_tools()`, `capability.py`, `capability_tool_meta.yaml`, `server.json` via `graphify capability --stdout` — must stay aligned (**D-47.01**).

### Recommended approach

1. **Pure helper** `_run_concept_code_hops` (name TBD) in `serve.py`: inputs `entity` (label/id), `max_hops` (cap e.g. 4), optional `direction` (`code_to_concept` | `both`). Walk only edges with relation `implements` in the stored orientation (code `_src` → concept `_tgt` per `build` normalization). Return hybrid envelope + structured meta (nodes/edges visited).
2. **MCP tool** registering that helper — satisfies **CCODE-03** traversal; docstring `Examples:` for manifest.
3. **`/trace` in skills:** Document the same golden-path: call the new MCP tool (or CLI `query` if extended) — satisfies **CCODE-04** “slash **or** MCP” if tests cover one path; implementing both doc + one automated path is enough.
4. **Tests:** Extend `tests/test_concept_code_edges.py` or add `tests/test_concept_code_mcp.py` calling the pure helper with a tiny `nx.Graph` from `build_from_json` — no stdio MCP server.

### Security

- Reuse **`sanitize_label`** / existing graph tool patterns for any user-provided entity string; no new unsanitized fields in JSON meta.

---

## Validation Architecture

| Dimension | Strategy |
|-----------|----------|
| Automated | `pytest tests/test_concept_code_edges.py` + new trace/hops tests; `pytest tests/` subset after manifest regen if hash tests exist |
| Contract | New tool appears in `build_mcp_tools()` list and regenerated `server.json` tool_count |
| Docs | `grep` for CCODE-03/04 keywords in `docs/RELATIONS.md` and skill fragments |

## RESEARCH COMPLETE

Planning may proceed.
