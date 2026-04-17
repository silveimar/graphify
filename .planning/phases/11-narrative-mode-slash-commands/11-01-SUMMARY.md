---
phase: 11-narrative-mode-slash-commands
plan: "01"
subsystem: serve
tags: [mcp, serve, analyze, phase-11, slash-commands]
dependency_graph:
  requires:
    - graphify/analyze.py (god_nodes, surprising_connections)
    - graphify/delta.py (compute_delta — 4-arg signature)
    - graphify/snapshot.py (list_snapshots, load_snapshot)
    - graphify/security.py (sanitize_label)
  provides:
    - _run_graph_summary (pure helper, testable without MCP runtime)
    - _run_connect_topics (pure helper, testable without MCP runtime)
    - graph_summary MCP tool (SLASH-01 /context server-side)
    - connect_topics MCP tool (SLASH-03 /connect server-side)
  affects:
    - graphify/serve.py (list_tools, _handlers dict, 2 new closures + 2 pure helpers)
    - tests/test_serve.py (11 new unit tests, 135 total passing)
tech_stack:
  added: []
  patterns:
    - "Phase-9.2 hybrid envelope: text_body + SENTINEL + json(meta) with status field"
    - "pure helper / thin closure split (matching _run_query_graph / _tool_query_graph pattern)"
    - "Phase-10 alias redirect via _alias_map with resolved_from_alias meta provenance"
    - "4-arg compute_delta(G_prev, comms_prev, G, communities) — BLOCKER 1 fix"
key_files:
  modified:
    - path: graphify/serve.py
      summary: "Added _run_graph_summary + _run_connect_topics pure helpers (module-level); _tool_graph_summary + _tool_connect_topics closures inside serve(); two new Tool registrations in list_tools(); two new handler entries in _handlers dict"
    - path: tests/test_serve.py
      summary: "Added Phase 11 test block with 11 new tests covering envelope shape, status codes, alias redirect, budget clamping, section-header distinctness, and 4-arg compute_delta regression"
decisions:
  - "Pure helpers (_run_graph_summary, _run_connect_topics) extracted at module level so tests can call them without MCP runtime — matches existing _run_query_graph pattern"
  - "Surprising bridges in connect_topics are GLOBAL to the graph, not A-B filtered — explicitly labelled in text_body and machine-readable via meta.surprise_scope='global' (BLOCKER 4 Option A)"
  - "No-graph short-circuit handled in closures (_tool_*), not in pure helpers — keeps helpers stateless and testable with any graph"
  - "delta_block for zero snapshots is {status: 'no_prior_snapshot'} sentinel dict, not an error — graph is brand-new"
  - "compute_delta called as compute_delta(G_prev, comms_prev, G, communities) — 4-arg fix per plan-checker BLOCKER 1; load_snapshot already returns (G, communities, meta) tuple so comms_prev is available directly"
metrics:
  duration_minutes: 45
  completed_date: "2026-04-17"
  tasks_completed: 3
  files_changed: 2
---

# Phase 11 Plan 01: graph_summary + connect_topics MCP Tools Summary

**One-liner:** Two new MCP tools (`graph_summary`, `connect_topics`) delivering SLASH-01 and SLASH-03 server-side endpoints via Phase-9.2 hybrid envelope with alias-redirect propagation and explicit global-scope surprising bridges.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `graph_summary` MCP tool (SLASH-01) | 2d0e1f5 | graphify/serve.py |
| 2 | Add `connect_topics` MCP tool (SLASH-03) | 2d0e1f5 | graphify/serve.py |
| 3 | Unit tests for both tools | 6b14512 | tests/test_serve.py |

## What Was Built

### `graph_summary` (SLASH-01 — `/context` command)

- `_run_graph_summary(G, communities, snaps_dir, arguments) -> str` — pure module-level helper
- `_tool_graph_summary(arguments) -> str` — thin closure inside `serve()`, calls `_reload_if_stale()` then delegates
- Returns: god-node list + top-5 communities + recent delta from most recent snapshot
- Delta uses correct 4-arg `compute_delta(G_prev, comms_prev, G, communities)` (BLOCKER 1 fix)
- Budget clamped `max(50, min(budget, 100000))`, top_n clamped `max(1, min(top_n, 50))`

### `connect_topics` (SLASH-03 — `/connect` command)

- `_run_connect_topics(G, communities, alias_map, arguments) -> str` — pure module-level helper
- `_tool_connect_topics(arguments) -> str` — thin closure inside `serve()`, delegates with `_alias_map`
- Returns two DISTINCT sections (RESEARCH.md Pitfall 4 mitigation):
  1. `## Shortest Path (N hops)` — BFS path between the two topics
  2. `## Surprising Bridges (global to the graph, not filtered to the A-B path)` — global surprising_connections()
- `meta.surprise_scope = "global"` makes scope machine-readable for clients
- Handles: `no_data`, `entity_not_found`, `ambiguous_entity`, `no_path` status codes
- Alias redirect via `_alias_map` with `resolved_from_alias` provenance in meta

### Tests (11 new, 135 total passing)

All new tests call pure helpers directly (no MCP server needed):

| Test | Validates |
|------|-----------|
| `test_graph_summary_envelope_no_graph` | zero snapshots → no_prior_snapshot delta, status ok |
| `test_graph_summary_envelope_ok` | populated graph with snapshot → ok + required meta keys |
| `test_graph_summary_budget_clamp` | budget 10→50, 999999999→100000, no crash |
| `test_graph_summary_no_prior_snapshot` | delta == {status: no_prior_snapshot} |
| `test_graph_summary_compute_delta_four_arg_call` | BLOCKER 1 regression — spy confirms 4-arg call |
| `test_connect_topics_envelope_ok` | ok, path_length, surprise_count, surprise_scope==global |
| `test_connect_topics_alias_redirect` | resolved_from_alias in meta when alias redirected |
| `test_connect_topics_ambiguous` | ambiguous_entity + candidates with id/label/source_file |
| `test_connect_topics_entity_not_found` | entity_not_found + missing_endpoints list |
| `test_connect_topics_no_path` | no_path for disconnected components |
| `test_connect_topics_section_headers_distinct` | both sections present, Shortest Path before Surprising Bridges, "global to the graph" label |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: input_sanitization | graphify/serve.py | topic_a and topic_b inputs pass through `sanitize_label()` before any echo or node lookup (T-11-01-01 mitigated) |

No new network endpoints or auth paths introduced. All topic inputs sanitized. Budget parameter clamped (T-11-01-03). Source_file disclosure surface unchanged from existing `get_node` tool (T-11-01-05 accepted).

## Self-Check: PASSED

- `graphify/serve.py` modified: confirmed via `git log`
- `tests/test_serve.py` modified: confirmed via `git log`
- Commits exist: `2d0e1f5` (feat), `6b14512` (test) — confirmed via `git log --oneline`
- `pytest tests/test_serve.py -q` exits 0 — 135 passed
- `grep -c QUERY_GRAPH_META_SENTINEL graphify/serve.py` = 13 (≥ 8 required)
- `grep 'compute_delta(G_prev, comms_prev, G, communities)' graphify/serve.py` matches
