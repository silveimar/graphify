"""File-cluster detection for batched semantic extraction (Phase 10, GRAPH-01).

Groups import-connected files into batch units so the skill can issue one
LLM call per cluster instead of one per file. Pure function: takes
extraction ast_results, returns list of FileCluster dicts.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import networkx as nx

from graphify.routing import ResolvedRoute, Router

_DEFAULT_TOKEN_BUDGET = 50_000
_CHARS_PER_TOKEN = 4  # conservative heuristic (RESEARCH Pattern 8, A3)


def cluster_files(
    paths: list[Path],
    ast_results: list[dict],
    *,
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
) -> list[dict]:
    """Group import-connected files into FileCluster dicts.

    Parameters
    ----------
    paths : list[Path]
        The files to cluster. Order does not matter.
    ast_results : list[dict]
        Per-file extraction results (nodes + edges). Only `imports` edges
        with both source_file AND target inside `paths` are used for
        clustering. Other edges are ignored for clustering purposes.
    token_budget : int
        Soft cap per cluster. Clusters exceeding the budget are split at
        the weakest import edge (lowest-degree boundary node). Default 50000.

    Returns
    -------
    list[dict]
        Each cluster: {"cluster_id": int, "files": list[str],
        "token_estimate": int}. `files` ordered imported-first via
        topological sort (alphabetical fallback on cycles, D-08).
        `cluster_id` is 0-indexed and stable across runs for identical input.
    """
    if not paths:
        return []

    path_strs = sorted(str(p) for p in paths)  # determinism anchor
    import_graph = _build_import_graph(path_strs, ast_results)

    # Step 1: weakly connected components (correct DiGraph API)
    raw_components = [sorted(c) for c in nx.weakly_connected_components(import_graph)]
    raw_components.sort(key=lambda c: (len(c), c[0] if c else ""))

    # Step 2: top-level directory cap (D-05)
    after_dir_cap: list[list[str]] = []
    for component in raw_components:
        after_dir_cap.extend(_split_by_top_dir(component))

    # Step 3: token budget split (D-07)
    after_budget: list[list[str]] = []
    for component in after_dir_cap:
        after_budget.extend(
            _split_by_budget(component, import_graph, token_budget)
        )

    # Step 4: topological order within each cluster + emit
    clusters: list[dict] = []
    for cid, files in enumerate(after_budget):
        ordered = _topological_order(files, import_graph)
        clusters.append({
            "cluster_id": cid,
            "files": ordered,
            "token_estimate": _estimate_tokens(ordered),
        })
    return clusters


def _build_import_graph(path_strs: list[str], ast_results: list[dict]) -> nx.DiGraph:
    """Build a DIRECTED import graph: edge (a, b) means `a imports b`.

    Isolated files still appear as nodes (for weakly_connected_components
    correctness). Only edges whose source_file AND target are in path_strs
    are retained.
    """
    G = nx.DiGraph()
    path_set = set(path_strs)
    for p in path_strs:
        G.add_node(p)
    for result in ast_results:
        for edge in result.get("edges", []):
            if edge.get("relation") != "imports":
                continue
            src = edge.get("source_file", "")
            tgt = edge.get("target", "")
            # target may be a file path OR a module stem; only file-path hits cluster
            if src in path_set and tgt in path_set:
                G.add_edge(src, tgt)
    return G


def _split_by_top_dir(component: list[str]) -> list[list[str]]:
    """D-05: split a connected component if it spans >1 top-level directory.

    Top-level directory is the first path component relative to the common
    ancestor of all files in the component. Works with both absolute and
    relative paths. A file sitting directly in the common ancestor (no
    subdirectory) uses `""` as its top-level key.
    Splits deterministically (alphabetical by top-dir).
    """
    if len(component) <= 1:
        return [sorted(component)]

    paths = [Path(f) for f in component]

    # Find the common ancestor directory
    try:
        # len(paths) > 1 is guaranteed by the early return above (`if len(component) <= 1`)
        common = Path(os.path.commonpath([str(p) for p in paths]))
        # commonpath may land on a file component; use its parent if it's a file
        if common.is_file() or (not common.exists() and common.suffix):
            common = common.parent
    except ValueError:
        # Different drives on Windows — treat all as same group
        return [sorted(component)]

    by_dir: dict[str, list[str]] = {}
    for f, p in zip(component, paths):
        try:
            rel = p.relative_to(common)
            top = rel.parts[0] if len(rel.parts) > 1 else ""
        except ValueError:
            top = ""
        by_dir.setdefault(top, []).append(f)

    if len(by_dir) <= 1:
        return [sorted(component)]
    return [sorted(by_dir[k]) for k in sorted(by_dir.keys())]


def _split_by_budget(
    files: list[str],
    import_graph: nx.DiGraph,
    token_budget: int,
) -> list[list[str]]:
    """D-07: if token_estimate > budget, split at weakest import edge.

    Weakest edge = boundary between two halves where removing it minimizes
    the sum of endpoint degree-centrality (i.e., least-connected boundary).
    Recursively splits until every chunk fits or is a single file.
    """
    if _estimate_tokens(files) <= token_budget or len(files) <= 1:
        return [sorted(files)]
    # Use undirected view for min-cut-like splitting
    subgraph = import_graph.subgraph(files).to_undirected()
    if subgraph.number_of_edges() == 0:
        # No edges to cut: fall back to alphabetical half-split
        mid = len(files) // 2
        left, right = sorted(files)[:mid], sorted(files)[mid:]
        return (
            _split_by_budget(left, import_graph, token_budget)
            + _split_by_budget(right, import_graph, token_budget)
        )
    degree = dict(subgraph.degree())
    # Score each edge by sum of endpoint degrees; lowest = weakest
    weakest = min(
        subgraph.edges(),
        key=lambda e: (degree.get(e[0], 0) + degree.get(e[1], 0), sorted(e)),
    )
    cut_graph = subgraph.copy()
    cut_graph.remove_edge(*weakest)
    pieces = [sorted(c) for c in nx.connected_components(cut_graph)]
    if len(pieces) < 2:
        # Fallback: alphabetical half-split
        mid = len(files) // 2
        pieces = [sorted(files)[:mid], sorted(files)[mid:]]
    result: list[list[str]] = []
    for piece in pieces:
        result.extend(_split_by_budget(piece, import_graph, token_budget))
    return result


def _topological_order(files: list[str], import_graph: nx.DiGraph) -> list[str]:
    """D-08: imported-first, importer-last. Alphabetical fallback on cycle.

    `import_graph` has edge (a, b) meaning a imports b. Topological sort on
    the directed subgraph returns nodes in dependency-order (b before a)
    after reversal.
    """
    subgraph = import_graph.subgraph(files)
    if not files:
        return []
    if nx.is_directed_acyclic_graph(subgraph):
        # topological_sort returns importers before importees; reverse for dep-order
        return list(reversed(list(nx.topological_sort(subgraph))))
    return sorted(files)


def _estimate_tokens(files: list[str]) -> int:
    """Rough token estimate: sum of file byte sizes / chars-per-token.

    Missing / unreadable files fall back to ~1000 tokens each. Returns >= 1.
    """
    total = 0
    for f in files:
        try:
            total += Path(f).stat().st_size
        except OSError:
            total += 4000  # ~1000-token fallback per missing file
    return max(1, total // _CHARS_PER_TOKEN)


def max_tier_route(cluster_files: list[Path], router: Router) -> ResolvedRoute:
    """Return the highest tier route among cluster members (Phase 12, CONTEXT D-01).

    Ordering: trivial < simple < complex < vision.
    """
    if not cluster_files:
        return ResolvedRoute(tier="trivial", model_id="", endpoint="", skip_extraction=False)
    best: ResolvedRoute | None = None
    for p in cluster_files:
        r: ResolvedRoute = router.resolve(p)
        if best is None or r.rank() > best.rank():
            best = r
    assert best is not None
    return best
