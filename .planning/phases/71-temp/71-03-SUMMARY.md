---
phase: 71-temp
plan: 03
subsystem: temporal
tags: [temporal, analyze, filter, wave-2, D-7]
requires: [71-01]
provides:
  - god_nodes degree over currently-valid edges only
  - surprising_connections excludes superseded edges (both passes)
  - suggest_questions knowledge-gap pass excludes superseded AMBIGUOUS edges
  - implicit current-only filter (no CLI flag, no parameter)
affects: [graphify/analyze.py, tests/test_analyze.py]
tech_stack:
  added: []
  patterns:
    - edge_subgraph-view-with-degree-fallback-for-isolates
    - data.get(valid_until)-is-not-None-guard
    - def-anchored-grep-not-line-numbers
key_files:
  created: []
  modified:
    - graphify/analyze.py
    - tests/test_analyze.py
decisions:
  - "D-7 honored: analyze.py implicitly excludes valid_until!=None edges. No CLI flag added."
  - "Legacy compat preserved: edges without valid_until key (v1.13) treated as current via data.get(...) is None."
  - "god_nodes contract preserved: isolated nodes still surface at degree 0 — edge_subgraph view drops them, so degree dict is rebuilt over G.nodes()."
  - "T-71-10 mitigated: filter checks `is not None` strictly (empty-string valid_until kept as 'current' — read-mode validator does not produce empty strings)."
  - "T-71-11 mitigated: garbage non-string non-null valid_until safely excluded (analyze.py never parses the timestamp; just None-vs-not-None)."
  - "T-71-12 mitigated: edge_subgraph is O(E), no regression."
metrics:
  tasks_completed: 1
  commits: 2
  tests_added: 7
  duration_minutes: ~12
---

# Phase 71-03: analyze.py Currently-Valid Edge Filter Summary

Adds the temporal-currency guard at all four edge-iteration sites in
`graphify/analyze.py` so god-node ranking, surprising-connection detection,
and knowledge-gap question synthesis automatically ignore superseded edges
(`valid_until != None`). Lands ahead of plan 71-04 supersession wiring so
analytics are temporally-aware as soon as edges acquire `valid_until`.

## Edit Sites (located by def-anchored grep, not pre-baked line numbers)

`grep -n "def god_nodes\|def surprising_connections\|for u, v, data in G.edges(data=True)" graphify/analyze.py` (post-71-02 baseline) returned:

| Site | Site name (def-anchored) | Pattern at site |
| --- | --- | --- |
| 1 | `def god_nodes` (line 76) | replaced `dict(G.degree())` with `edge_subgraph` view + degree-fallback dict over `G.nodes()` |
| 2 | `for u, v, data in G.edges(data=True)` (line 246, inside `_cross_file_surprises`) | inserted `if data.get("valid_until") is not None: continue` at top of loop |
| 3 | `for u, v, data in G.edges(data=True)` (line 336, inside `_cross_community_surprises`) | same one-line guard |
| 4 | `for u, v, data in G.edges(data=True)` (line 408, inside `suggest_questions` AMBIGUOUS pass) | same one-line guard |

All four sites use `data.get("valid_until")` (not `data["valid_until"]`) so
legacy v1.13 edges without the key resolve to `None` and are preserved.

## god_nodes special handling

```python
current_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("valid_until") is None]
G_current = G.edge_subgraph(current_edges)
# edge_subgraph drops isolated nodes; rebuild degree over ALL nodes so
# zero-degree nodes still surface (preserves pre-71-03 god_nodes contract).
degree = {n: G_current.degree(n) if n in G_current else 0 for n in G.nodes()}
```

The fallback to `G.nodes()` is an Auto-fix Rule 1 deviation discovered during
GREEN regression — see "Deviations" below.

## Test Coverage

`pytest tests/test_analyze.py -q` → **53 passed** (46 pre-existing + 7 new).
`pytest tests/test_analyze.py tests/test_build.py tests/test_temporal.py tests/test_validate.py tests/test_export.py tests/test_extract.py tests/test_cluster.py tests/test_report.py -q` → **225 passed**.

| New test | Behavior gated |
| --- | --- |
| `test_god_nodes_excludes_superseded` | hub `h` has 3 raw edges, 1 superseded → degree 2 in result |
| `test_surprising_connections_excludes_superseded` | superseded cross-community INFERRED edge absent from output |
| `test_cross_community_pass_excludes_superseded` | second pass via `_cross_community_surprises` also filters |
| `test_knowledge_gaps_excludes_superseded` | `suggest_questions` AMBIGUOUS-edge questions skip superseded edges |
| `test_current_filter_is_default` | no flag/parameter required (implicit per D-7) |
| `test_legacy_graph_no_valid_until_field` | edges with no `valid_until` key counted as current |

## Invariant Checks

```
$ grep -v '^#' graphify/analyze.py | grep -c 'valid_until'
6                                  # ≥4 required (4 sites + docstring + comment)
$ grep -n 'edge_subgraph' graphify/analyze.py
84:    `edge_subgraph` view; edges without the `valid_until` key (legacy v1.13)
89:    G_current = G.edge_subgraph(current_edges)
$ grep -c "if data.get(\"valid_until\") is not None" graphify/analyze.py
3                                  # 3 loop guards (god_nodes uses edge_subgraph instead)
```

No CLI flag added — D-7 implicit-default contract honored.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 1 — Bug] Preserve isolated-node degree-0 entries in `god_nodes`.**
   - **Found during:** GREEN regression run (`pytest tests/test_export.py`).
   - **Issue:** `G.edge_subgraph(...)` drops nodes with no incident currently-valid
     edge. The first GREEN draft used `dict(G_current.degree())`, which silently
     omitted isolated nodes. `tests/test_export.py::test_to_obsidian_bucketed_code_note_links_to_unclassified`
     constructs an orphan node with zero edges and expects `god_nodes` /
     downstream `to_obsidian` to still emit a note for it. Pre-71-03 the test
     passed (verified via `git stash && pytest …; git stash pop`).
   - **Fix:** Build `degree` as a comprehension over `G.nodes()` with a
     containment check on `G_current`, so isolated nodes surface at degree 0.
     One-line change in `god_nodes`; behavior matches pre-71-03 contract.
   - **Files modified:** `graphify/analyze.py`.
   - **Commit:** d6db83c (squashed with the GREEN feat commit).

No deviations on Rules 2/3/4. No auth gates encountered.

### Test-side fix-ups (caller-signature drift, not behavior changes)

- `_cross_community_surprises(G, communities, top_n=10)` — explicit `top_n` kwarg
  (this internal helper has no default).
- `suggest_questions(G, communities=..., community_labels={0: "C0"})` — function
  is named `suggest_questions` (singular) not `suggested_questions`, and
  requires a `community_labels` dict.

These were RED-scaffold mistakes corrected pre-GREEN; they exercise the
real public API.

## Pre-Existing Failures (Out of Scope)

Same set documented in 71-01 / 71-02 SUMMARY (47 unrelated failures across
vault_*, audit_b_closure, capability, delta, enrich, explain_paths,
federate, harness_*, migration). Not touched.

## Self-Check: PASSED

- graphify/analyze.py — modified (4 edit sites: 1 edge_subgraph view + 3 one-line guards)
- tests/test_analyze.py — 7 new tests (53 total in file)
- Commits a199ac9 (RED test) and d6db83c (GREEN feat + Rule-1 fix) — both PRESENT in git log
- `grep -n 'edge_subgraph' graphify/analyze.py` → 2 hits (docstring + code site)
- `pytest tests/test_analyze.py -q` → 53 passed
