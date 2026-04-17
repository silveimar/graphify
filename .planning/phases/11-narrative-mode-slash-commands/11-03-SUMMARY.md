---
phase: 11-narrative-mode-slash-commands
plan: 03
subsystem: serve
tags: [mcp, drift-nodes, newly-formed-clusters, snapshot, phase-11, slash-commands]
dependency_graph:
  requires: [11-01, 11-02]
  provides: [drift_nodes MCP tool, newly_formed_clusters MCP tool]
  affects: [graphify/serve.py, tests/test_serve.py]
tech_stack:
  added: []
  patterns: [hybrid-envelope, memory-discipline-del-G_snap, set-based-community-diff, closure-handler-split, snapshot-chain-walk-Pattern-E]
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "_run_drift_nodes trend score: community_changes * 2 + abs(degree_delta) — simple weighted composition of existing data, no new clustering algorithm (D-18)"
  - "newly_formed_clusters uses pure set-based novelty rule (M_c & set(P_p) == empty) instead of compute_delta 4-arg API — avoids coupling complexity and aligns with D-18"
  - "Both tools use del G_snap / del G_prev immediately after extracting scalars from each loaded snapshot (Pattern E memory discipline)"
  - "insufficient_history threshold for both tools: len(snaps) < 1 — live G counts as second data point, same contract as entity_trace (plan 11-02)"
  - "newly_formed_clusters returns status='no_change' as first-class status when no new clusters detected, with text narrative explaining graph stability"
metrics:
  duration_minutes: 7
  tasks_completed: 3
  files_modified: 2
  completed_date: "2026-04-17"
requirements: [SLASH-04, SLASH-05]
---

# Phase 11 Plan 03: drift_nodes + newly_formed_clusters MCP Tools Summary

**One-liner:** `drift_nodes` and `newly_formed_clusters` MCP tools walking snapshot chains with `del G_snap` memory discipline, Phase-9.2 hybrid envelopes, trend-score composition, and set-based community novelty rule — all 5 Phase-11 MCP tools now registered.

## What Was Built

### graphify/serve.py

Added two pure helpers (module-level, testable without MCP runtime) and two closure handlers inside `serve()`.

**`_run_drift_nodes(G, snaps_dir, arguments) -> str`:**
- Clamps `budget` to `max(50, min(budget, 100000))`, `max_snapshots` to `max(2, min(max_snapshots, 50))`, `top_n` to `max(1, min(top_n, 100))` (T-11-03-01, T-11-03-02)
- Lists prior snapshots via `list_snapshots(snaps_dir)`
- Returns `insufficient_history` when `len(snaps) < 1`
- Walks last `max_snapshots` snapshots with strict `del G_snap` after each iteration (T-11-03-04)
- Appends live G as "current" tip data point
- Filters nodes to those with ≥ 2 data points; computes `trend_score = community_changes * 2 + abs(degree_delta)` — composition only, no new algorithm (D-18)
- Emits Phase-9.2 hybrid envelope with meta keys: `status, layer, search_strategy, cardinality_estimate, continuation_token, snapshot_count, drift_count, nodes_scanned`

**`_run_newly_formed_clusters(G, communities, snaps_dir, arguments) -> str`:**
- Loads most recent prior snapshot, extracts community dict, then `del G_prev` immediately
- Applies set-based novelty rule: current community is "new" when its member-set has zero intersection with any prior community (avoids compute_delta's 4-arg API per D-18)
- Returns `no_change` status when `len(new_clusters) == 0`
- Returns `ok` status with `new_cluster_count` and `new_cluster_ids` when new clusters found
- Emits Phase-9.2 hybrid envelope with meta keys: `status, layer, search_strategy, cardinality_estimate, continuation_token, snapshot_count, new_cluster_count, new_cluster_ids`

**Tool registrations:**
- `list_tools()` entries for `drift_nodes` and `newly_formed_clusters`
- `_tool_drift_nodes` and `_tool_newly_formed_clusters` closures inside `serve()` with `no_graph` short-circuit
- `_handlers["drift_nodes"] = _tool_drift_nodes`
- `_handlers["newly_formed_clusters"] = _tool_newly_formed_clusters`

All 5 Phase-11 MCP tools are now registered: `graph_summary`, `entity_trace`, `connect_topics`, `drift_nodes`, `newly_formed_clusters`.

### tests/test_serve.py

Added 8 new tests under `# --- Phase 11: drift_nodes + newly_formed_clusters ---`:

| Test | Coverage |
|------|----------|
| `test_drift_nodes_insufficient_history` | 0 prior snaps → `insufficient_history`, `snapshots_available: 0` |
| `test_drift_nodes_trend_vectors` | 3 snaps + live tip → `ok`, `drift_count >= 1`, `nodes_scanned >= 2` |
| `test_drift_nodes_top_n_respected` | `top_n=1` → `drift_count <= 1` |
| `test_drift_nodes_memory_discipline` | weakref spy proves all `G_snap` objects released post-call |
| `test_newly_formed_clusters_insufficient_history` | 0 prior snaps → `insufficient_history` |
| `test_newly_formed_clusters_no_change` | identical graph+communities → `no_change`, `new_cluster_count==0` |
| `test_newly_formed_clusters_new_cluster_detected` | new {new_a, new_b, new_c} triangle → `ok`, `new_cluster_count >= 1`, `99 in new_cluster_ids` |
| `test_newly_formed_clusters_envelope_structure` | all required meta keys present on OK path |

All tests use `make_snapshot_chain` fixture from conftest.py (not re-defined). `G_live` uses `n{j}` id scheme throughout.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1+2 | c71e060 | feat(11-03): add drift_nodes MCP tool (SLASH-04) and newly_formed_clusters (SLASH-05) |
| Task 3 | 0f2119a | test(11-03): unit tests for drift_nodes + newly_formed_clusters tools |

## Deviations from Plan

None — plan executed exactly as written. Both tools use exactly the primitives specified (snapshot walk Pattern E, set-based novelty rule, Phase-9.2 hybrid envelope). The plan already prescribed avoiding `compute_delta` for `newly_formed_clusters` in favor of pure set operations; this was followed precisely.

## Threat Surface Scan

No new trust boundaries introduced beyond what is documented in the plan's threat model. All agent-supplied numeric params clamped at entry (T-11-03-01, T-11-03-02). `del G_snap`/`del G_prev` applied at each snapshot load site (T-11-03-04). Set intersection computation bounded by community count (T-11-03-03). No new network endpoints or file access patterns beyond what existed in plans 11-01 and 11-02.

## Self-Check: PASSED
