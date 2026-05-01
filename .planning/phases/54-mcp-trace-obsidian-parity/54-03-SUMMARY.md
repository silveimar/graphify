---
phase: 54-mcp-trace-obsidian-parity
plan: 3
subsystem: mcp
tags: [mcp, entity-trace, concept-code, green, cgraph-03]
requires: [54-01, 54-02]
provides:
  - "_bfs_concept_code_from helper (single concept↔code BFS implementation reused by _run_concept_code_hops and _run_entity_trace)"
  - "_run_entity_trace include_concept_code branch (D-54.04) with backward-compat byte-identical default"
  - "entity_trace MCP inputSchema with include_concept_code: boolean default false"
affects:
  - graphify/serve.py
  - graphify/mcp_tool_registry.py
  - server.json (manifest hash regenerated → ac31ce60c04bee38)
tech-stack:
  added: []
  patterns:
    - "Inline closure helper (_maybe_merge_concept_code) over the include_cc flag — keeps Phase 11 envelope byte-identical when flag is absent"
    - "Pre-resolved concept↔code anchor (cc_anchor) computed once with exact-label-match precedence — usable on every return path including insufficient_history"
    - "Sorted reachable list, sorted relation keys — deterministic envelope ordering"
key-files:
  modified:
    - graphify/serve.py
    - graphify/mcp_tool_registry.py
    - server.json
  created: []
decisions:
  - "BFS factor returns full bookkeeping (depth_map, hop_labels, steps_by_relation, traversals, truncated) so _run_concept_code_hops keeps its full feature set unchanged AND _run_entity_trace projects only what it needs"
  - "include_cc merge applied at every meta-return path (insufficient_history, ambiguous_entity, entity_not_found, ok), NOT only at the final ok path — Plan 01 RED test test_entity_trace_includes_concept_code_when_requested uses tmp_path with no snapshots, so insufficient_history is the actual hot path"
  - "Pre-resolved cc_anchor uses the same exact-label-match precedence Plan 02 added to _run_concept_code_hops (Klass / SubKlass / test_klass disambiguation); without it, 'Klass' substring-matches 3 nodes and the BFS would have no single anchor"
  - "no_data path (empty entity) skips the merge — no anchor to BFS from"
metrics:
  duration: "~20 min"
  completed: "2026-04-30"
---

# Phase 54 Plan 03: MCP `entity_trace` concept↔code merge Summary

Wave 3 GREEN — extended `_run_entity_trace` with an optional `include_concept_code: bool = False` parameter that merges concept↔code traversal alongside the existing temporal trace. Backward-compat default leaves the meta envelope byte-identical to Phase 11. Updated `entity_trace` MCP inputSchema. Refactored the concept↔code BFS into a single shared helper `_bfs_concept_code_from` so both `_run_concept_code_hops` and `_run_entity_trace` use one implementation.

## What Changed

### `graphify/serve.py`

**Task 1 — BFS factor + entity_trace branch:**

```python
# NEW helper (factored from _run_concept_code_hops body):
def _bfs_concept_code_from(
    G: nx.Graph, start_id: str, max_hops: int, direction: str,
    relations: frozenset[str],
) -> tuple[dict[str, int], dict[str, str], dict[str, int], int, bool]:
    """Returns (depth_map, hop_labels, steps_by_relation, traversals, truncated).
    Pure function over G. Excludes traversals that exceed _IMPL_EDGE_BUDGET."""
```

`_run_concept_code_hops` now delegates the BFS loop body to the helper. Every Plan 02 / Phase 47 test still GREEN — no behaviour change.

`_run_entity_trace` extensions:
1. Reads `arguments.get("include_concept_code", False)` once via `bool(...)` coercion (T-54-08).
2. Defines an inline closure `_maybe_merge_concept_code(meta, candidate_id)` that no-ops when `include_cc` is False or `candidate_id not in G`.
3. Pre-resolves a single concept↔code anchor `cc_anchor` at function start (after alias resolution) with exact-label-match precedence — necessary because the round_trip fixture's `Klass` substring-matches 3 nodes (`k_klass`, `k_subklass`, `t_test_klass`).
4. Calls `_maybe_merge_concept_code` at all four meta-return paths: `insufficient_history`, `ambiguous_entity`, `entity_not_found`, and the final `ok`. The `no_data` path (empty entity) skips the merge — no anchor to BFS from.
5. When the merge fires, attaches:
   - `concept_code_reachable: list[str]` — sorted node IDs reachable via concept↔code hops (excluding the start node)
   - `concept_code_steps_by_relation: dict[str, int]` — keyed on all 5 relations in canonical sort order, populated with step counts (`max_hops=2`, `direction="both"`, `relations=_ALLOWED_CONCEPT_CODE_RELATIONS` per D-54.10)

**CRITICAL** Default path (flag absent or False): the meta dict is left byte-identical to Phase 11 — Test `test_entity_trace_default_excludes_concept_code` enforces this directly (T-54-11).

### `graphify/mcp_tool_registry.py`

**Task 2 — entity_trace inputSchema:**

```python
inputSchema={"type": "object", "properties": {
    "entity": {"type": "string"},
    "budget": {"type": "integer", "default": 500},
    "include_concept_code": {
        "type": "boolean",
        "default": False,
        "description": "When true, merge concept↔code reachable nodes and per-relation step counts into the trace meta envelope (CGRAPH-03 / D-54.04).",
    },
}, "required": ["entity"]}
```

Tool description appended with one sentence flagging the optional flag.

### `server.json`

Regenerated via `scripts/sync_mcp_server_json.py` — manifest hash `ac31ce60c04bee38…` reflects the inputSchema change. `test_capability.py::test_validate_cli_zero` now passes against the regenerated manifest.

## Test Status

| Test File | Result | Notes |
|-----------|--------|-------|
| `tests/test_serve.py::test_entity_trace_default_excludes_concept_code` | GREEN | Was Plan 01 RED; default-path keys absent (T-54-11) |
| `tests/test_serve.py::test_entity_trace_includes_concept_code_when_requested` | GREEN | Was Plan 01 RED; both keys present, types correct |
| `tests/test_capability.py::test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` | GREEN | Was Plan 01 RED (entity_trace half) — both halves now flipped (concept_code_hops by Plan 02, entity_trace by Plan 03) |
| `tests/test_capability.py` (all 26) | GREEN | server.json regen made `test_validate_cli_zero` pass |
| `tests/test_concept_code_mcp.py` (all 7) | GREEN | Plan 02 + Phase 47 untouched after BFS factor |
| `tests/test_serve.py -k "entity_trace"` (all 8 Phase 11) | GREEN | Backward compat preserved |
| `tests/test_concept_code_obsidian.py` (7 tests) | RED | Wave 4 / Plan 04 territory — expected |
| `pytest tests/ -q` | 1988 passed, 7 failed | Only Plan 04 Obsidian RED remain |

## Files Changed

- `graphify/serve.py` — +131 / −31 (BFS factor + include_concept_code branch)
- `graphify/mcp_tool_registry.py` — +14 / −2 (entity_trace schema)
- `server.json` — regenerated (hash bump)

## Commits Made

1. `1f16c5c feat(54-03): factor _bfs_concept_code_from + entity_trace include_concept_code`
2. `b2aaae9 feat(54-03): entity_trace MCP inputSchema gains include_concept_code`

## Deviations from Plan

### [Rule 1 — Bug] include_concept_code merge applied to ALL return paths (not only `ok`)

- **Found during:** Task 1 first run of `test_entity_trace_includes_concept_code_when_requested`
- **Issue:** The plan instructed inserting the branch only at the final `ok` return (around serve.py:~2125). However, the failing RED test passes `tmp_path` (no snapshots), which short-circuits to the `insufficient_history` return BEFORE the `ok` block. With the plan's specified placement, the test would still fail.
- **Fix:** Hoisted the resolution of a single concept↔code anchor (`cc_anchor`) to the top of the function (after alias resolution) using the same exact-label-match precedence Plan 02 added to `_run_concept_code_hops`. Defined a `_maybe_merge_concept_code(meta, candidate_id)` inline closure and called it at all four real meta-return paths (`insufficient_history`, `ambiguous_entity`, `entity_not_found`, final `ok`). The `no_data` path (empty entity) is intentionally skipped — without an entity there is no anchor to BFS from.
- **Files modified:** `graphify/serve.py`
- **Commit:** `1f16c5c`
- **Rationale:** This preserves the plan's invariants (default path byte-identical to Phase 11, T-54-11; no envelope smuggling) while also satisfying the actual test. Both must-haves and acceptance criteria still hold:
  - `grep -c '"concept_code_reachable"' graphify/serve.py` → ≥1 ✓
  - `grep -c '"concept_code_steps_by_relation"' graphify/serve.py` → ≥1 ✓
  - `grep -c "include_concept_code" graphify/serve.py` → ≥2 ✓ (read + branch)
  - `grep -c "def _bfs_concept_code_from(" graphify/serve.py` → 1 ✓

### [Rule 3 — Blocking] server.json regeneration

- **Found during:** Task 2 verification
- **Issue:** Adding `include_concept_code` to `entity_trace` inputSchema invalidated the embedded manifest hash, causing `test_validate_cli_zero` to fail.
- **Fix:** Ran `python scripts/sync_mcp_server_json.py` per CLAUDE.md guidance ("`server.json` regenerated by `scripts/sync_mcp_server_json.py`; manifest hash includes `graphify_version`").
- **Files modified:** `server.json`
- **Commit:** `b2aaae9` (committed alongside the schema change as one atomic unit)

## Self-Check: PASSED

- `graphify/serve.py` — FOUND
- `graphify/mcp_tool_registry.py` — FOUND
- `server.json` — FOUND
- Commit `1f16c5c` — FOUND
- Commit `b2aaae9` — FOUND
- `.planning/phases/54-mcp-trace-obsidian-parity/54-03-SUMMARY.md` — present (this file)

## EXECUTION COMPLETE
