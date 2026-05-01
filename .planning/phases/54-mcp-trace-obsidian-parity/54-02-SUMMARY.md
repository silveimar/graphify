---
phase: 54-mcp-trace-obsidian-parity
plan: 2
subsystem: mcp
tags: [mcp, concept-code-hops, green, cgraph-03]
requires: [54-01]
provides:
  - "_concept_code_hop_kind / _concept_code_hop_allowed (renamed, generalized over relations frozenset)"
  - "_validate_relations_arg (relations argument validator)"
  - "_ALLOWED_CONCEPT_CODE_RELATIONS frozenset (5 relations)"
  - "concept_code_hops MCP tool schema with `relations` array<string> default ['implements']"
  - "payload keys: relations, traversal_steps, steps_by_relation"
  - "backward-compat shim: implements_traversal_steps preserved when requested set == {implements}"
affects:
  - graphify/serve.py
  - graphify/mcp_tool_registry.py
  - server.json (manifest hash regenerated)
tech-stack:
  added: []
  patterns:
    - "Validator returns (value, err) tuple; None default → frozenset({'implements'})"
    - "Tuple-returning predicate (_concept_code_hop_allowed) attributes hop to relation in single lookup"
    - "Sentinel-wrapped error envelope (string, NOT dict literal)"
    - "Rule 2 entity disambiguation: exact-label match precedence over substring matches"
key-files:
  modified:
    - graphify/serve.py
    - graphify/mcp_tool_registry.py
    - server.json
  created: []
decisions:
  - "Tuple-return predicate over double lookup — single allowed-check yields (relation, kind) so steps_by_relation can attribute without re-classifying"
  - "Exact-label-match precedence added in _run_concept_code_hops (Rule 2) — necessary for round_trip fixture where 'Klass' substring-matches 3 nodes; falls through to ambiguity envelope only when truly identical labels collide"
  - "Error envelope mirrors no_data envelope shape: sentinel-wrapped string with status='error', layer/strategy/cardinality/continuation_token preserved"
metrics:
  duration: "~25 min"
  completed: "2026-04-30"
---

# Phase 54 Plan 02: MCP `concept_code_hops` 5-relation widening Summary

Wave 2 GREEN — extended `concept_code_hops` MCP tool from single-relation (`implements` only, Phase 47) to a filterable 5-relation surface (`implements`, `documents`, `tests`, `realizes`, `instantiates`) with structural backward compatibility for Phase 47 callers.

## What Changed

### `graphify/serve.py`

**Helper renames + generalization (Task 1):**

```python
_ALLOWED_CONCEPT_CODE_RELATIONS = frozenset({
    "implements", "documents", "tests", "realizes", "instantiates",
})

# OLD: _implements_hop_kind(G, u, v) -> str | None
# NEW: _concept_code_hop_kind(G, u, v, relations) -> tuple[str, str] | None
#      returns (relation, direction_kind)

# OLD: _implements_hop_allowed(G, u, v, direction) -> bool
# NEW: _concept_code_hop_allowed(G, u, v, direction, relations) -> tuple[str, str] | None
#      returns (relation, kind) when allowed, else None — caller can attribute
#      steps_by_relation in a single lookup

# NEW: _validate_relations_arg(raw) -> tuple[frozenset[str], str | None]
#   - None      → (frozenset({"implements"}), None)
#   - non-list  → error
#   - empty []  → error mentioning "must not be empty"
#   - non-str   → error
#   - unknown   → error listing allowed values
```

**`_run_concept_code_hops` (Task 2):**

1. Calls `_validate_relations_arg(arguments.get("relations"))` at the top; on error emits a sentinel-wrapped envelope with `status="error"`, mirroring the existing `no_data` envelope shape (NOT a raw dict — fixed pre-flight observation 4015).
2. Initializes `steps_by_relation: dict[str, int] = {rel: 0 for rel in requested_relations}`.
3. BFS loop now uses tuple-returning `_concept_code_hop_allowed(G, u, v, direction, requested_relations)`; on each accepted hop increments `steps_by_relation[rel_name]` and `traversals`.
4. Payload meta gains `relations: sorted(requested_relations)`, `traversal_steps: int`, `steps_by_relation: {rel: count}`.
5. Backward-compat shim: `meta["implements_traversal_steps"] = traversals` emitted ONLY when `requested_relations == frozenset({"implements"})` (D-54.03 — set-equality, not None-vs-list, so explicit `relations=["implements"]` also activates the shim).

**Exact-label-match precedence (Rule 2):** When `_find_node` substring-matches multiple candidates, prefer those whose label or id equals the term exactly (case-insensitive). Necessary because the round_trip fixture has `Klass` / `SubKlass` / `test_klass` — `_find_node("Klass")` returns all three and would otherwise hit `ambiguous_entity` instead of `status="ok"`.

### `graphify/mcp_tool_registry.py`

`concept_code_hops` inputSchema gains:

```python
"relations": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": ["implements", "documents", "tests", "realizes", "instantiates"],
    },
    "default": ["implements"],
    "description": "Concept↔code edge relations to traverse. Default: ['implements'] (Phase 47 behavior).",
}
```

Tool description updated to mention the 5-relation surface; `entity_trace` schema untouched (Plan 03 scope).

### `server.json`

Regenerated via `python scripts/sync_mcp_server_json.py` to update the manifest content hash after the schema change. New hash: `a4aa091a4746d1c5...`. `tool_count: 27` unchanged.

## Test Status

| Test File | Plan 01 RED | Plan 02 Result |
|---|---|---|
| `tests/test_concept_code_mcp.py` (7 tests, 6 RED + 1 Phase 47 golden) | 6 failing | **7/7 GREEN** |
| `tests/test_capability.py::test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` | failing | **half-GREEN** — `concept_code_hops` half passes; `entity_trace.include_concept_code` half RED (intentional, Plan 03) |
| `tests/test_capability.py::test_validate_cli_zero` | passing | GREEN (manifest hash resynced) |
| `tests/test_concept_code_obsidian.py` (7 tests) | RED | RED (intentional, Wave 4 / Plan 04) |
| `tests/test_serve.py::test_entity_trace_includes_concept_code_when_requested` | RED | RED (intentional, Wave 3 / Plan 03) |
| Phase 47 backward-compat (existing implements-only tests, golden path) | GREEN | **GREEN** (shim active by default) |
| Phase 53 backward-compat (vocabulary, orientation, evidence) | GREEN | **GREEN** (no behavior change in build/extract/export) |

Full suite: **1986 passed, 9 failed, 1 xfailed**. The 9 failures are precisely the planned downstream waves:
- 1 capability schema test (entity_trace half) — Plan 03
- 1 entity_trace serve test — Plan 03
- 7 Obsidian parity tests — Plan 04

No new failures introduced.

## Files Changed

- `graphify/serve.py` (+90 / -26)
- `graphify/mcp_tool_registry.py` (+22 / -7)
- `server.json` (manifest hash + per-tool schema delta)

## Commits

| Hash | Message |
|---|---|
| `373e250` | `feat(54-02): rename concept↔code hop helpers + add _validate_relations_arg` |
| `75dbd59` | `feat(54-02): wire relations filter into concept_code_hops + payload shim` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Exact-label-match precedence in entity resolution**
- **Found during:** Task 2 (test_concept_code_hops_default_relations was returning `ambiguous_entity` instead of `status=ok`)
- **Issue:** `_find_node("Klass")` substring-matches `k_klass` / `k_subklass` / `t_test_klass` in the round_trip fixture, triggering the `ambiguous_entity` envelope before payload assembly. Plan 01 RED tests assume exact-label resolves uniquely — but Phase 47 `_find_node` is substring-only, with no exact-match precedence.
- **Fix:** After `_find_node`, when `len(live_matches) > 1`, filter to entries whose label OR id equals the search term exactly (case-insensitive). Falls through to the `ambiguous_entity` envelope only when truly multiple distinct nodes share the identical label/id (the original disambiguation contract is preserved for that case).
- **Why Rule 2 (not Rule 4):** This is a correctness requirement — the ambiguity-envelope fast-path was masking a unique resolution. Localized to `_run_concept_code_hops` (no API surface change, no schema change). Phase 47 golden test still passes.
- **Files modified:** `graphify/serve.py`
- **Commit:** `75dbd59`

**2. [Rule 3 - Blocking] `server.json` manifest hash drift after schema change**
- **Found during:** post-Task-2 regression check
- **Issue:** `tests/test_capability.py::test_validate_cli_zero` failed with manifest hash mismatch — schema changes to `concept_code_hops` (description + new `relations` property) altered the manifest content, but the committed `server.json` was stale.
- **Fix:** Ran `python scripts/sync_mcp_server_json.py` (the project-blessed sync tool per `CLAUDE.md`); committed regenerated `server.json` alongside the schema change.
- **Files modified:** `server.json`
- **Commit:** `75dbd59`

### Architectural Changes

None.

### Auth Gates

None.

## Self-Check: PASSED

- `graphify/serve.py:_concept_code_hop_kind` defined: FOUND
- `graphify/serve.py:_concept_code_hop_allowed` defined: FOUND
- `graphify/serve.py:_validate_relations_arg` defined: FOUND
- `graphify/serve.py:_ALLOWED_CONCEPT_CODE_RELATIONS` defined: FOUND
- Old `_implements_hop_kind` / `_implements_hop_allowed` symbols removed: VERIFIED (`grep -c` returns 0)
- `graphify/mcp_tool_registry.py` schema includes `"relations"`: FOUND
- Commit `373e250`: FOUND in git log
- Commit `75dbd59`: FOUND in git log

## EXECUTION COMPLETE
