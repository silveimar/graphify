# assemble node+edge dicts into a NetworkX graph, preserving edge direction
#
# Node deduplication — three layers:
#
# 1. Within a file (AST): each extractor tracks a `seen_ids` set. A node ID is
#    emitted at most once per file, so duplicate class/function definitions in
#    the same source file are collapsed to the first occurrence.
#
# 2. Between files (build): NetworkX G.add_node() is idempotent — calling it
#    twice with the same ID overwrites the attributes with the second call's
#    values. Nodes are added in extraction order (AST first, then semantic),
#    so if the same entity is extracted by both passes the semantic node
#    silently overwrites the AST node. This is intentional: semantic nodes
#    carry richer labels and cross-file context, while AST nodes have precise
#    source_location. If you need to change the priority, reorder extractions
#    passed to build().
#
# 3. Semantic merge (skill): before calling build(), the skill merges cached
#    and new semantic results using an explicit `seen` set keyed on node["id"],
#    so duplicates across cache hits and new extractions are resolved there
#    before any graph construction happens.
#
from __future__ import annotations

import sys
from typing import Any

import networkx as nx

from .validate import validate_extraction

_CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}


def _edge_priority(edge: dict[str, Any]) -> tuple[float, int]:
    """Higher tuple compares better for choosing dominant duplicate edge."""
    conf = str(edge.get("confidence", "AMBIGUOUS"))
    rank = _CONF_RANK.get(conf, 0)
    raw = edge.get("confidence_score")
    try:
        score = float(raw) if raw is not None else -1.0
    except (TypeError, ValueError):
        score = -1.0
    return (score, rank)


def _merge_edge_fields(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge two edges with same (source, target, relation); secondary loses unless stronger."""
    if _edge_priority(secondary) > _edge_priority(primary):
        base, other = secondary, primary
    else:
        base, other = primary, secondary
    out = dict(base)
    sf_b = base.get("source_file", "")
    sf_o = other.get("source_file", "")
    if isinstance(sf_b, str) and isinstance(sf_o, str) and sf_o and sf_o != sf_b:
        out["source_file"] = f"{sf_b}; {sf_o}" if sf_b else sf_o
    loc_b = base.get("source_location", "")
    loc_o = other.get("source_location", "")
    if isinstance(loc_b, str) and isinstance(loc_o, str) and loc_o and loc_o != loc_b:
        out["source_location"] = f"{loc_b}; {loc_o}" if loc_b else loc_o
    wt_b = base.get("weight", 1.0)
    wt_o = other.get("weight", 1.0)
    try:
        out["weight"] = float(wt_b) + float(wt_o)
    except (TypeError, ValueError):
        out["weight"] = wt_b
    return out


def _normalize_concept_code_edges(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    """Normalize implements / implemented_by pairs, orient code→concept, merge duplicates."""
    types: dict[str, str] = {}
    for n in nodes:
        if isinstance(n, dict) and "id" in n:
            types[str(n["id"])] = str(n.get("file_type", ""))

    def orient(src: str, tgt: str) -> tuple[str, str]:
        fs, ft = types.get(src, ""), types.get(tgt, "")
        if fs == "code" and ft != "code":
            return src, tgt
        if ft == "code" and fs != "code":
            return tgt, src
        return src, tgt

    for e in edges:
        rel = e.get("relation")
        if rel == "implemented_by":
            e["relation"] = "implements"
            e["source"], e["target"] = e["target"], e["source"]
            rel = "implements"
        if rel == "implements":
            s, t = orient(str(e["source"]), str(e["target"]))
            e["source"], e["target"] = s, t

    # Directed duplicate merge for all relation types
    merged_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    key_order: list[tuple[str, str, str]] = []
    for e in edges:
        key = (str(e["source"]), str(e["target"]), str(e.get("relation", "")))
        if key not in merged_map:
            merged_map[key] = dict(e)
            key_order.append(key)
        else:
            merged_map[key] = _merge_edge_fields(merged_map[key], dict(e))

    directed_edges = [merged_map[k] for k in key_order]

    # Collapse opposite-direction implements pairs sharing the same node pair
    impl_buckets: dict[frozenset[str], list[dict[str, Any]]] = {}
    rest: list[dict[str, Any]] = []
    for e in directed_edges:
        if e.get("relation") != "implements":
            rest.append(e)
            continue
        impl_buckets.setdefault(frozenset((str(e["source"]), str(e["target"]))), []).append(dict(e))

    impl_out: list[dict[str, Any]] = []
    for pair, grp in impl_buckets.items():
        if len(pair) != 2:
            impl_out.extend(grp)
            continue
        a, b = tuple(pair)
        ca = types.get(a, "") == "code"
        cb = types.get(b, "") == "code"
        if ca and not cb:
            canon_src, canon_tgt = a, b
        elif cb and not ca:
            canon_src, canon_tgt = b, a
        else:
            canon_src, canon_tgt = str(grp[0]["source"]), str(grp[0]["target"])
        merged = grp[0]
        for extra in grp[1:]:
            merged = _merge_edge_fields(merged, extra)
        merged["source"], merged["target"] = canon_src, canon_tgt
        merged["relation"] = "implements"
        impl_out.append(merged)

    edges[:] = rest + impl_out


def build_from_json(extraction: dict, *, directed: bool = False) -> nx.Graph:
    """Build a NetworkX graph from an extraction dict.

    directed=True produces a DiGraph that preserves edge direction (source→target).
    directed=False (default) produces an undirected Graph for backward compatibility.
    """
    # NetworkX <= 3.1 serialised edges as "links"; remap to "edges" for compatibility.
    if "edges" not in extraction and "links" in extraction:
        extraction = dict(extraction, edges=extraction["links"])
    extraction = dict(extraction)
    extraction["nodes"] = list(extraction.get("nodes", []))
    extraction["edges"] = [dict(e) for e in extraction.get("edges", [])]
    hyper_in = extraction.get("hyperedges")
    if hyper_in is not None:
        extraction["hyperedges"] = [dict(h) for h in hyper_in]

    nodes_for_norm = [n for n in extraction["nodes"] if isinstance(n, dict)]
    _normalize_concept_code_edges(nodes_for_norm, extraction["edges"])

    errors = validate_extraction(extraction)
    # Dangling edges (stdlib/external imports) are expected - only warn about real schema errors.
    real_errors = [e for e in errors if "does not match any node id" not in e]
    if real_errors:
        print(f"[graphify] Extraction warning ({len(real_errors)} issues): {real_errors[0]}", file=sys.stderr)
    G: nx.Graph = nx.DiGraph() if directed else nx.Graph()
    for node in extraction.get("nodes", []):
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
    node_set = set(G.nodes())
    for edge in extraction.get("edges", []):
        if "source" not in edge and "from" in edge:
            edge["source"] = edge["from"]
        if "target" not in edge and "to" in edge:
            edge["target"] = edge["to"]
        if "source" not in edge or "target" not in edge:
            continue
        src, tgt = edge["source"], edge["target"]
        if src not in node_set or tgt not in node_set:
            continue  # skip edges to external/stdlib nodes - expected, not an error
        attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
        # Preserve original edge direction - undirected graphs lose it otherwise,
        # causing display functions to show edges backwards.
        attrs["_src"] = src
        attrs["_tgt"] = tgt
        G.add_edge(src, tgt, **attrs)
    hyperedges = extraction.get("hyperedges", [])
    if hyperedges:
        G.graph["hyperedges"] = hyperedges
    return G


def build(
    extractions: list[dict],
    *,
    directed: bool = False,
    elicitation: dict | None = None,
) -> nx.Graph:
    """Merge multiple extraction results into one graph.

    directed=True produces a DiGraph that preserves edge direction (source→target).
    directed=False (default) produces an undirected Graph for backward compatibility.

    Extractions are merged in order. For nodes with the same ID, the last
    extraction's attributes win (NetworkX add_node overwrites). Pass AST
    results before semantic results so semantic labels take precedence, or
    reverse the order if you prefer AST source_location precision to win.

    When *elicitation* is provided, it is merged **after** all entries in
    *extractions* so interview-derived nodes overwrite duplicate IDs from
    earlier passes (elicitation wins on collision).
    """
    seq = list(extractions)
    if elicitation is not None:
        seq = seq + [elicitation]
    combined: dict = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 0, "output_tokens": 0}
    for ext in seq:
        combined["nodes"].extend(ext.get("nodes", []))
        combined["edges"].extend(ext.get("edges", []))
        combined["hyperedges"].extend(ext.get("hyperedges", []))
        combined["input_tokens"] += ext.get("input_tokens", 0)
        combined["output_tokens"] += ext.get("output_tokens", 0)
    return build_from_json(combined, directed=directed)
