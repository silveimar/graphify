---
phase: 07-mcp-write-back-peer-modeling
plan: "01"
subsystem: serve
tags: [mcp, annotations, sidecar, persistence, peer-identity, mutation-tools]
dependency_graph:
  requires: []
  provides:
    - graphify/serve.py::_append_annotation
    - graphify/serve.py::_compact_annotations
    - graphify/serve.py::_load_agent_edges
    - graphify/serve.py::_save_agent_edges
    - graphify/serve.py::_make_annotate_record
    - graphify/serve.py::_make_flag_record
    - graphify/serve.py::_make_edge_record
    - graphify/serve.py::_filter_annotations
    - graphify/serve.py::_tool_annotate_node
    - graphify/serve.py::_tool_flag_node
    - graphify/serve.py::_tool_add_edge
    - graphify/serve.py::_tool_get_annotations
    - graphify/serve.py::_reload_if_stale
  affects:
    - graphify-out/annotations.jsonl
    - graphify-out/agent-edges.json
tech_stack:
  added: []
  patterns:
    - JSONL append-only sidecar for annotations (crash-safe, compacted at startup)
    - Atomic JSON write via os.replace() for agent-edges
    - UUID4 session identity (never UUID1, never os.environ)
    - Mtime-based graph reload on every read tool call
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "D-04 honored: peer_id defaults to 'anonymous' string literal; no os.environ access"
  - "D-05 honored: session_id is uuid.uuid4() generated once at serve() startup"
  - "D-13 honored: _reload_if_stale() injected at top of all 7 existing read tool handlers"
  - "Record helpers (_make_annotate_record, _make_flag_record, _make_edge_record, _filter_annotations) extracted as module-level functions so they can be unit-tested without starting MCP server"
  - "sanitize_label applied at record-creation time (storage layer); HTML escaping is a render-time concern per security.py design"
  - "propose_vault_note registered as placeholder returning 'Not implemented yet' to keep tool list consistent for Plan 02"
metrics:
  duration: ~10 min
  completed: "2026-04-13"
  tasks_completed: 2
  files_changed: 2
---

# Phase 07 Plan 01: MCP Sidecar Persistence and Mutation Tools Summary

MCP server extended with JSONL/JSON sidecar persistence, peer/session identity, mtime reload, startup compaction, and 4 mutation/query tool handlers — all with graph.json kept immutable.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for sidecar helpers + record helpers | dce5c72 | tests/test_serve.py |
| 1+2 (GREEN) | Sidecar helpers, record helpers, mutation tools, mtime reload | e1372c6 | graphify/serve.py, tests/test_serve.py |

## What Was Built

### Module-Level Helpers (importable without MCP server)

**Sidecar persistence:**
- `_append_annotation(out_dir, record)` — JSONL append-only write; creates parent dirs
- `_compact_annotations(path)` — deduplicates by `(node_id, annotation_type, peer_id)`, keeps last, rewrites atomically via `os.replace()`; skips corrupt lines
- `_load_agent_edges(path)` — returns `[]` for missing/corrupt files
- `_save_agent_edges(out_dir, edges)` — atomic JSON write via `os.replace()`

**Record constructors (pure functions):**
- `_make_annotate_record(node_id, text, peer_id, session_id)` — creates annotation record with UUID4 record_id, ISO-8601 UTC timestamp, sanitizes all string inputs
- `_make_flag_record(node_id, importance, peer_id, session_id)` — validates importance in {high, medium, low}, raises ValueError otherwise
- `_make_edge_record(source, target, relation, peer_id, session_id)` — INFERRED confidence, never touches G
- `_filter_annotations(annotations, peer_id, session_id, time_from, time_to)` — ISO-8601 lexicographic time comparison

### serve() Changes

**Sidecar state init (startup):**
- `_graph_mtime`, `_out_dir`, `_annotations`, `_agent_edges`, `_session_id` initialized after graph load
- `_compact_annotations` called at startup (D-03: compaction once at startup only)

**`_reload_if_stale()` closure:**
- Injected as first call in all 7 existing read tool handlers (query_graph, get_node, get_neighbors, get_community, god_nodes, graph_stats, shortest_path)
- Uses `os.stat()` mtime; reloads G + communities when changed

**5 new tools registered in list_tools() and _handlers:**
- `annotate_node` — persists to annotations.jsonl via `_append_annotation`
- `flag_node` — persists to annotations.jsonl; returns error string for invalid importance
- `add_edge` — persists to agent-edges.json via `_save_agent_edges`; never calls `G.add_edge()`
- `propose_vault_note` — placeholder returning "Not implemented yet" (Plan 02)
- `get_annotations` — filters in-memory `_annotations` list

## Security Invariants Verified

| Threat | Status |
|--------|--------|
| T-07-01: Sanitize all agent strings | MITIGATED — `sanitize_label()` applied in all `_make_*` constructors |
| T-07-02: peer_id never from environment | MITIGATED — `grep -c "os.environ" graphify/serve.py` = 0 |
| T-07-03: G never mutated by mutation tools | MITIGATED — no `G.add_edge()` in any tool handler |
| T-07-04: JSONL compaction at startup | MITIGATED — `_compact_annotations` called in `serve()` init |
| T-07-05: UUID4 only | MITIGATED — `grep -c "uuid.uuid1" graphify/serve.py` = 0 |
| T-07-06: Corrupt JSONL lines skipped | ACCEPTED — `json.JSONDecodeError` caught and skipped in compaction |

## Test Coverage

35 tests in `tests/test_serve.py` (was 17, added 18 new):

**Task 1 — Sidecar helpers:**
- `test_append_annotation_creates_file`
- `test_compact_annotations_missing_file`
- `test_compact_annotations_dedup`
- `test_compact_annotations_corrupt_line`
- `test_load_agent_edges_missing`
- `test_load_agent_edges_valid`
- `test_save_agent_edges_atomic`

**Task 2 — Record helpers and filter:**
- `test_make_annotate_record_defaults`
- `test_make_annotate_record_sanitizes`
- `test_make_flag_record_valid`
- `test_make_flag_record_invalid`
- `test_make_edge_record`
- `test_make_edge_record_never_modifies_graph`
- `test_filter_annotations_no_filter`
- `test_filter_annotations_by_peer`
- `test_filter_annotations_by_session`
- `test_filter_annotations_by_time_range`
- `test_peer_id_never_from_env`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion for `sanitize_label` XSS behavior corrected**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan's test spec said to verify `"<script>"` is not in the text after sanitize_label, but `sanitize_label` by design only strips control characters and caps length — HTML escaping is a render-time concern (see `security.py` docstring: "For direct HTML injection, wrap the result with html.escape()")
- **Fix:** Updated `test_make_annotate_record_sanitizes` to verify control characters are stripped instead, which accurately tests the `sanitize_label` contract
- **Files modified:** tests/test_serve.py
- **Commit:** e1372c6

## Known Stubs

- `_tool_propose_vault_note` returns `"Not implemented yet"` — placeholder per plan spec; full implementation is Plan 02's scope

## Self-Check: PASSED
