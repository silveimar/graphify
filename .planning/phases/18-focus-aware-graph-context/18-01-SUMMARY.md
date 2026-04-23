---
phase: 18
plan: 01
subsystem: serve
tags: [networkx, ego-graph, resolver, source-file, serve, tdd]
requirements_closed: [FOCUS-02, FOCUS-06]
dependency_graph:
  requires:
    - graphify/analyze.py::_iter_sources
    - networkx>=3.0 (nx.ego_graph, nx.compose_all)
  provides:
    - graphify/serve.py::_resolve_focus_seeds
    - graphify/serve.py::_multi_seed_ego
  affects:
    - (none; additive — no existing call sites changed)
tech_stack:
  added: []
  patterns:
    - "Multi-seed ego-graph via nx.compose_all composition (not nx.ego_graph(G, [seeds], r) — that raises NodeNotFound in NetworkX 3.x)"
    - "source_file: str | list[str] normalization via analyze._iter_sources (v1.3 FOCUS-02 schema)"
    - "Silent-ignore-on-no-match: empty list return signals no_context downstream (D-03)"
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "Resolver compares target_path against both stored source_file string AND resolved absolute form (D-04); handles relative + absolute paths uniformly without requiring the target file to exist."
  - "_multi_seed_ego defensively filters seeds not in G rather than raising NodeNotFound — lets Wave 2 callers collapse stale paths to no_context per D-03."
  - "D-02 narrowing (function_name / line) is applied AFTER seed collection, not during, so the narrowing filter is orthogonal to source_file shape handling."
metrics:
  duration_seconds: 204
  completed: "2026-04-20T20:08:41Z"
  tasks_completed: 3
  files_modified: 2
  tests_added: 3
  tests_total_after: 1307
---

# Phase 18 Plan 01: Focus Resolver Helpers Summary

Standalone, importable `_resolve_focus_seeds` + `_multi_seed_ego` helpers in `graphify/serve.py` that close FOCUS-02 (path-to-node_id resolution handling `source_file: str | list[str]`) and FOCUS-06 (multi-seed ego-graph via `nx.compose_all`), with 3 TDD-driven unit tests gated by locked VALIDATION.md names.

## What Shipped

### Symbols Added (graphify/serve.py)

- **`_multi_seed_ego(G, seeds, radius) -> nx.Graph`** — Multi-seed ego-graph composer. Runs `nx.ego_graph(G, s, radius=radius)` per seed then calls `nx.compose_all(subgraphs)`. Filters seeds not in G (never raises NodeNotFound); empty seeds → empty graph; single seed short-circuits the compose.
- **`_resolve_focus_seeds(G, target_path, *, function_name=None, line=None) -> list[str]`** — File path → node_id resolver. Iterates `G.nodes(data=True)`, normalizes each node's `source_file` via `analyze._iter_sources`, matches against `target_raw`, `target_abs`, OR the resolved-absolute form of each stored source. Optional `function_name` (substring-in-label) and `line` (`source_location == f"L{line}"`) filters narrow the union per D-02.

### Import Added

- `from graphify.analyze import _iter_sources` (line 16 of serve.py, alongside `sanitize_label` / `classify_staleness`). No new runtime dependencies.

### Tests Added (tests/test_serve.py)

All three names locked verbatim per 18-VALIDATION.md rows 18-01-01..03:

1. `test_focus_resolver_str_source_file` — Node with `source_file="src/auth.py"` (str shape) returns `["n_login"]` for `_resolve_focus_seeds(G, Path("src/auth.py"))`; unrelated node excluded.
2. `test_focus_resolver_list_source_file_multi_seed` — Two nodes with list-shape `source_file=["src/auth.py", ...]` both selected as seeds (multi-seed union); third node with unmatched str-shape excluded. Asserts via `set(seeds) == {"n_a", "n_b"}` (order-independent).
3. `test_multi_seed_compose_all_matches_expected` — On `nx.path_graph(5)`, `_multi_seed_ego(G, [0, 2], radius=1)` returns node set `{0, 1, 2, 3}` (union of ego(0) + ego(2)); attrs preserved (`subgraph.nodes[0]["label"] == "0"`); empty seeds → empty graph; missing seeds filtered without raising.

## Commits

| # | Gate | Hash | Message |
|---|------|------|---------|
| 1 | RED | `529e4e9` | `test(18-01): add failing tests for focus resolver + multi-seed ego-graph` |
| 2 | GREEN | `cb04973` | `feat(18-01): add _resolve_focus_seeds + _multi_seed_ego helpers` |

Task 18-01-03 (smoke gate) produced no code changes — `pytest tests/test_serve.py -q` passed 155/155 and full `pytest tests/ -q` passed 1307/1307, so no commit was created per the plan's "do NOT add any extra code" directive.

## Verification Results

```text
$ grep -Fn "def _resolve_focus_seeds" graphify/serve.py
772:def _resolve_focus_seeds(

$ grep -Fn "def _multi_seed_ego" graphify/serve.py
755:def _multi_seed_ego(G: "nx.Graph", seeds: "list", radius: int) -> "nx.Graph":

$ grep -Fn "nx.compose_all" graphify/serve.py
769:    return nx.compose_all(subgraphs)

$ grep -Fn "from graphify.analyze import" graphify/serve.py | grep -F "_iter_sources"
16:from graphify.analyze import _iter_sources

$ grep -En "nx\.ego_graph\(G, *\[" graphify/serve.py
(zero lines — anti-pattern absent)

$ pytest tests/test_serve.py::test_focus_resolver_str_source_file \
         tests/test_serve.py::test_focus_resolver_list_source_file_multi_seed \
         tests/test_serve.py::test_multi_seed_compose_all_matches_expected -x
3 passed in 0.13s

$ pytest tests/test_serve.py -q
155 passed in 0.29s

$ pytest tests/ -q
1307 passed, 2 warnings in 37.83s
```

All 7 success-criteria items from the plan are satisfied:

- [x] `_resolve_focus_seeds` and `_multi_seed_ego` exist in serve.py and are importable.
- [x] Both handle `source_file: str | list[str]` via `_iter_sources` (no inlined isinstance).
- [x] Multi-seed composition uses `nx.compose_all([nx.ego_graph(G, s, r) for s in seeds])`.
- [x] 3 VALIDATION.md-locked tests pass by name.
- [x] No regressions in `tests/test_serve.py` (155 passed) or full suite (1307 passed).
- [x] No new runtime dependencies.
- [x] No new modules (D-18 compose-don't-plumb honored).

## Attrs-Preservation Notes from `nx.compose_all`

Observed behavior confirmed during implementation:
- `nx.ego_graph(G, s, radius=r)` returns a **subgraph view** that inherits all node/edge attrs from G (verified in test_multi_seed_compose_all_matches_expected — `subgraph.nodes[0]["label"] == "0"` survives the composition).
- `nx.compose_all(subgraphs)` is **last-writer-wins on attribute conflicts**, but since all subgraph views reference the same underlying G, conflicts never occur in our use case — every seed's ego-graph sees the same attrs for shared nodes.
- Empty subgraph list → we explicitly return `nx.Graph()` rather than calling `nx.compose_all([])` (which raises `ValueError`).

## Deviations from Plan

**None** — all three tasks executed exactly as written. Each locked test name, each acceptance criterion, and the GREEN verification pattern matched the plan precisely. The hook-injected build output during each commit is cosmetic graphify self-indexing and does not affect correctness.

## Expected Interface for Plan 18-02 Consumer

Plan 18-02 (MCP tool `get_focus_context`) should compose these helpers as:

```python
# Inside _run_get_focus_context_core (or whatever Plan 18-02 names it):
from pathlib import Path

seeds = _resolve_focus_seeds(
    G,
    Path(validated_focus_path),
    function_name=focus_hint.get("function_name"),
    line=focus_hint.get("line"),
)
if not seeds:
    return _no_context_envelope()  # D-03 + D-11 binary status

subgraph = _multi_seed_ego(G, seeds, radius=neighborhood_depth)
# ... then render subgraph via _subgraph_to_text + community summary per D-02 envelope
```

**Contracts Plan 18-02 must honor:**

- `_resolve_focus_seeds` returns `list[str]` — order is `G.nodes` iteration order (not sorted). Callers requiring deterministic ordering should wrap in `sorted(...)`.
- `_multi_seed_ego` with `radius=0` returns only the seed nodes themselves — matches D-08 "drop to depth-0" degradation step.
- Neither helper raises on missing nodes / spoofed paths. Path confinement (FOCUS-04) remains the caller's responsibility via `security.validate_graph_path`.

## Self-Check: PASSED

- graphify/serve.py::_resolve_focus_seeds — FOUND (line 772)
- graphify/serve.py::_multi_seed_ego — FOUND (line 755)
- graphify/serve.py::from graphify.analyze import _iter_sources — FOUND (line 16)
- tests/test_serve.py::test_focus_resolver_str_source_file — FOUND (line 2222)
- tests/test_serve.py::test_focus_resolver_list_source_file_multi_seed — FOUND (line 2239)
- tests/test_serve.py::test_multi_seed_compose_all_matches_expected — FOUND (line 2254)
- commit 529e4e9 (test RED) — FOUND in git log
- commit cb04973 (feat GREEN) — FOUND in git log
- anti-pattern `nx.ego_graph(G, [` — ABSENT (as required)
