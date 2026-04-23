---
phase: 10-cross-file-semantic-extraction
plan: "02"
subsystem: batch
tags: [clustering, graph, networkx, tdd, GRAPH-01]
dependency_graph:
  requires:
    - 10-cross-file-semantic-extraction/01  # validate.py schema, conftest fixtures
  provides:
    - graphify.batch.cluster_files          # consumed by 10-03 (extract integration)
  affects:
    - graphify/extract.py                   # will call cluster_files in Phase 10 Wave 2
tech_stack:
  added:
    - graphify/batch.py (pure stdlib + networkx)
  patterns:
    - weakly_connected_components on DiGraph for component detection
    - os.path.commonpath for top-dir extraction from absolute paths
key_files:
  created:
    - graphify/batch.py
  modified:
    - tests/test_batch.py
decisions:
  - "Used weakly_connected_components instead of connected_components — DiGraph requires weakly_connected_components for correct component detection (plan noted this)"
  - "Fixed _split_by_top_dir to use os.path.commonpath for absolute paths — plan used parts[0] which is '/' for absolute paths; commonpath gives the true shared prefix"
  - "Imported os inside _split_by_top_dir function body (not at module top) to keep module structure clean — single-use stdlib import"
metrics:
  duration_seconds: 480
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 10 Plan 02: batch.py — File Cluster Detection Summary

Implements `graphify/batch.py` with `cluster_files()` — GRAPH-01 foundation module. Groups import-connected files into deterministic token-bounded clusters via NetworkX weakly-connected-components, top-dir splitting (D-05), weakest-edge budget splitting (D-07), and topological ordering with alphabetical cycle fallback (D-08).

## Final cluster_files Signature

```python
def cluster_files(
    paths: list[Path],
    ast_results: list[dict],
    *,
    token_budget: int = 50_000,
) -> list[dict]:
    ...
```

Each returned dict has exactly: `{"cluster_id": int, "files": list[str], "token_estimate": int}`.

## Implementation Overview

Four-step pipeline inside `cluster_files`:

1. **Component detection** — `_build_import_graph` builds a `nx.DiGraph` (edge = "a imports b"), then `nx.weakly_connected_components` groups files.
2. **Top-dir cap (D-05)** — `_split_by_top_dir` uses `os.path.commonpath` to find the shared ancestor, then groups by first relative path component. Works with both absolute and relative paths.
3. **Token budget split (D-07)** — `_split_by_budget` recursively removes the weakest edge (min sum of endpoint degrees) from an undirected subgraph view until each piece fits within `token_budget` or is a singleton.
4. **Topological order (D-08)** — `_topological_order` checks `nx.is_directed_acyclic_graph`, applies `reversed(topological_sort)` for imported-first order, or falls back to `sorted()` on cycle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _split_by_top_dir to handle absolute paths**
- **Found during:** Task 2 test run (test_cluster_top_dir_cap failed)
- **Issue:** Plan's implementation used `Path(f).parts[0]` as the top-level directory key. For absolute paths (e.g., `/private/var/.../src/auth.py`), `parts[0]` is always `/` — so all files in a component appeared to share the same top directory, preventing the split.
- **Fix:** Replaced `parts[0]` approach with `os.path.commonpath` to find the true shared ancestor, then computed each file's first relative path component after that ancestor. This correctly distinguishes `src/` from `tests/` whether paths are absolute or relative.
- **Files modified:** `graphify/batch.py` (function `_split_by_top_dir`)
- **Commit:** 7661314

**2. [Plan note applied] Used weakly_connected_components not connected_components**
- The plan's `<action>` block included a note: "replace `nx.connected_components` with `nx.weakly_connected_components` since `import_graph` is a DiGraph." Applied as directed.

## Test Coverage (9 Tests)

| Test | GRAPH-01 Behavior | Status |
|------|-------------------|--------|
| test_empty_inputs_return_empty_list | Empty → [] | PASS |
| test_cluster_files_import_connected | Import-connected files cluster together | PASS |
| test_cluster_top_dir_cap | D-05: cross-dir component splits | PASS |
| test_cluster_respects_token_budget | D-07: over-budget split at weakest edge | PASS |
| test_cluster_topological_order | D-08: imported-first ordering | PASS |
| test_cluster_cycle_fallback | D-08: alphabetical fallback on cycle | PASS |
| test_cluster_files_does_not_write_to_stdout | No stdout writes | PASS |
| test_cluster_token_estimate_positive | token_estimate >= 1 | PASS |
| test_cluster_ids_are_contiguous | cluster_id 0, 1, 2, ... no gaps | PASS |

All 5 GRAPH-01 behavioral requirements from the plan are covered.

## No Stubs

All returned fields (`cluster_id`, `files`, `token_estimate`) are wired to real computation. No placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, or file content reads introduced. `batch.py` only calls `Path.stat().st_size` (byte count) and never opens file contents — consistent with T-10-02 disposition in the threat register.

## Self-Check: PASSED

- `graphify/batch.py` exists: FOUND
- `tests/test_batch.py` exists: FOUND
- Commit 7abac89 (feat batch.py): FOUND
- Commit 7661314 (test batch.py): FOUND
- `pytest tests/test_batch.py -q`: 9 passed
- `pytest tests/ -q`: 1113 passed, 3 pre-existing failures in test_delta.py (unrelated to this plan)
