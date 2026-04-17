---
phase: 11-narrative-mode-slash-commands
plan: 02
subsystem: serve
tags: [mcp, entity-trace, snapshot, phase-11, slash-commands]
dependency_graph:
  requires: [11-01]
  provides: [entity_trace MCP tool, make_snapshot_chain fixture]
  affects: [graphify/serve.py, tests/test_serve.py, tests/conftest.py]
tech_stack:
  added: []
  patterns: [hybrid-envelope, alias-redirect-D16, memory-discipline-del-G_snap, closure-handler-split]
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
    - tests/conftest.py
decisions:
  - "_run_entity_trace extracted as pure helper at module level for testability; _tool_entity_trace is the closure inside serve() (same split as _run_graph_summary / _tool_graph_summary)"
  - "insufficient_history threshold: len(snaps) < 1 — live G counts as second data point, so one prior snapshot is the minimum for a meaningful trace"
  - "entity_not_found checked after snapshot chain walk — entity may exist in history even if absent from live graph; only if no match anywhere do we return entity_not_found"
  - "make_snapshot_chain node-id scheme: n0..n{i+1} with label=f'n{j}' — fixture docstring documents this as the contract for all downstream tests constructing G_live"
metrics:
  duration_minutes: 7
  tasks_completed: 3
  files_modified: 3
  completed_date: "2026-04-17"
requirements: [SLASH-02]
---

# Phase 11 Plan 02: entity_trace MCP Tool (SLASH-02) Summary

**One-liner:** `entity_trace` MCP tool walking snapshot chain with `del G_snap` memory discipline, Phase-9.2 hybrid envelope, 4 status codes, and Phase-10 alias redirect — backed by shared `make_snapshot_chain` conftest fixture with strict n0..n{i} id scheme.

## What Was Built

### graphify/serve.py

Added `_run_entity_trace` pure helper (module-level, testable without MCP runtime) and `_tool_entity_trace` closure inside `serve()`. The tool is registered in `list_tools()` and `_handlers`.

**`_run_entity_trace(G, snaps_dir, alias_map, arguments) -> str`:**
- Sanitizes `entity` via `sanitize_label()` (T-11-02-01)
- Clamps `budget` to `max(50, min(budget, 100000))` (T-11-02-03)
- Phase 10 D-16 alias resolution: per-call `_resolved_aliases` dict, `_resolve_alias()` closure
- Lists prior snapshots via `list_snapshots(snaps_dir)`
- Returns `insufficient_history` (with `snapshots_available: N`) when `len(snaps) < 1`
- Checks live graph for `ambiguous_entity` (multiple matches) before walking chain
- Walks snapshot chain with strict memory discipline: `del G_snap` after extracting scalars
- Returns `entity_not_found` when no match in any snapshot or live graph
- Appends live graph as `"current"` tip data point to timeline
- Emits Phase-9.2 hybrid envelope: `text_body + SENTINEL + json(meta)`
- Meta keys: `status, layer, search_strategy, cardinality_estimate, continuation_token, snapshot_count, first_seen, timeline_length, entity_id`; optional `resolved_from_alias`

**Tool registration:**
- `list_tools()` entry with `inputSchema` requiring `entity`, optional `budget`
- `_handlers["entity_trace"] = _tool_entity_trace`
- `_tool_entity_trace` adds `no_graph` short-circuit before delegating to `_run_entity_trace`

### tests/conftest.py

Added `make_snapshot_chain` fixture factory:
- Returns callable `_make(n=3, root=None) -> list[Path]`
- Node-id scheme: `n0..n{i+1}` with `label=f"n{j}"` (ids match labels — BLOCKER 2 fix)
- Each snapshot `i>0` adds edge `(n0, n{i})` for detectable per-snapshot diffs
- Saves with `name=f"snap_{i:02d}"` for deterministic mtime ordering
- Fixture docstring documents node-id scheme for downstream plan 11-03 tests

### tests/test_serve.py

Added 8 new tests under `# --- Phase 11: entity_trace ---`:

| Test | Coverage |
|------|----------|
| `test_entity_trace_insufficient_history` | 0 prior snaps → `insufficient_history`, `snapshots_available: 0` |
| `test_entity_trace_ok_timeline` | 3 snaps + live tip → `ok`, `timeline_length >= 3`, `first_seen` set |
| `test_entity_trace_alias_redirect` | `alias_map={"auth": "n0"}` → `resolved_from_alias` in meta |
| `test_entity_trace_ambiguous_entity` | "auth" matches 2 nodes → `ambiguous_entity`, 2-item candidates list |
| `test_entity_trace_entity_not_found` | label present nowhere → `entity_not_found` |
| `test_entity_trace_no_graph` | empty entity string → `no_data` |
| `test_entity_trace_memory_discipline` | weakref spy proves all `G_snap` objects released after call |
| `test_entity_trace_envelope_structure` | 9 required meta keys present on OK path |

All tests use `make_snapshot_chain` fixture; `G_live` explicitly constructed with `n{j}` id scheme in every test referencing it (BLOCKER 2 fix — no NameError).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | fa66fef | feat(11-02): add make_snapshot_chain fixture to tests/conftest.py |
| Task 2 | 11c11b7 | feat(11-02): add entity_trace MCP tool (SLASH-02) |
| Task 3 | 6513966 | test(11-02): unit tests for entity_trace tool + fixture regression |

## Deviations from Plan

None — plan executed exactly as written. The plan spec included careful BLOCKER 2 guidance about the `n{j}` id scheme which was followed precisely.

## Threat Surface Scan

No new trust boundaries introduced beyond what is documented in the plan's threat model. `sanitize_label()` applied to `entity` argument (T-11-02-01). Budget clamped (T-11-02-03). No new network endpoints or file access patterns.

## Self-Check: PASSED
