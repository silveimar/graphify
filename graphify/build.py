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
from pathlib import Path
from typing import Any

import networkx as nx

from .validate import validate_extraction

_CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}

# Phase 53 (D-53.02): all five concept↔code relations are oriented code → concept.
# Note: opposite-direction collapse is intentionally NOT extended to the four new
# relations — they have no `_by` synonym and merging cross-direction edges would
# silently destroy user-distinct data (see 53-RESEARCH §"Extend orientation").
CONCEPT_CODE_RELATIONS: tuple[str, ...] = (
    "implements",
    "documents",
    "tests",
    "realizes",
    "instantiates",
)


def _edge_priority(edge: dict[str, Any]) -> tuple[int, float]:
    """Higher tuple compares better: confidence ladder first, then confidence_score tie-break."""
    conf = str(edge.get("confidence", "AMBIGUOUS"))
    rank = _CONF_RANK.get(conf, 0)
    raw = edge.get("confidence_score")
    try:
        score = float(raw) if raw is not None else -1.0
    except (TypeError, ValueError):
        score = -1.0
    return (rank, score)


def _merge_edge_fields(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge two edges with same (source, target, relation); deterministic across re-runs.

    Phase 53 (D-53.05) canonicalization rules:
      - source_file: union of inputs, lex-sorted+deduped, joined with "; "
      - source_location: lex-min of non-empty values
      - confidence: highest tier (EXTRACTED > INFERRED > AMBIGUOUS)
      - confidence_score: max() across present numeric values
      - weight: sum (preserves Phase 46 semantic)
    """
    if _edge_priority(secondary) > _edge_priority(primary):
        base, other = secondary, primary
    else:
        base, other = primary, secondary
    out = dict(base)

    def _split_sf(v: Any) -> list[str]:
        if isinstance(v, list):
            return [s.strip() for s in v if isinstance(s, str) and s.strip()]
        if isinstance(v, str) and v:
            return [s.strip() for s in v.split(";") if s.strip()]
        return []

    sf_set = sorted(set(_split_sf(base.get("source_file")) + _split_sf(other.get("source_file"))))
    if sf_set:
        out["source_file"] = "; ".join(sf_set)

    locs = [v for v in (base.get("source_location"), other.get("source_location"))
            if isinstance(v, str) and v]
    if locs:
        out["source_location"] = min(locs)

    rank_b = _CONF_RANK.get(str(base.get("confidence", "")), 0)
    rank_o = _CONF_RANK.get(str(other.get("confidence", "")), 0)
    if rank_o > rank_b and other.get("confidence"):
        out["confidence"] = other["confidence"]

    scores: list[float] = []
    for v in (base.get("confidence_score"), other.get("confidence_score")):
        try:
            if v is not None:
                scores.append(float(v))
        except (TypeError, ValueError):
            pass
    if scores:
        out["confidence_score"] = max(scores)

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
        if rel in CONCEPT_CODE_RELATIONS:
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

    # Phase 53 (D-53.06): canonical sort across ALL relations — concept↔code AND structural —
    # so that edge insertion order into NetworkX is deterministic across re-runs. NetworkX
    # >= 2.0 preserves dict insertion order on iteration.
    edges.sort(key=lambda e: (
        str(e.get("source", "")),
        str(e.get("target", "")),
        str(e.get("relation", "")),
    ))


def build_from_json(
    extraction: dict,
    *,
    directed: bool = False,
    peers: list[Path] | None = None,
    local_repo: str = "",
    resolved_output=None,
    target_dir: Path | None = None,
) -> nx.Graph:
    """Build a NetworkX graph from an extraction dict.

    directed=True produces a DiGraph that preserves edge direction (source→target).
    directed=False (default) produces an undirected Graph for backward compatibility.

    Phase 66 (CFED-01, CFED-04): when ``peers`` is a non-empty list, run the
    federation engine after concept↔code edge normalization and before schema
    validation, then write the manifest atomically through the vault-aware
    output resolver. When ``peers`` is None or empty, behavior is unchanged
    (default-off invariant).
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

    # Phase 66 (CFED-01 / CFED-04): federation runs strictly between
    # concept↔code normalization and schema validation, so peer-imported nodes
    # pass validate_extraction alongside local nodes. Lazy import keeps
    # graphify.federate (and its transitive imports) out of build.py's import
    # graph when no peers are passed — preserving the default-off invariant.
    if peers:
        from .federate import federate, build_manifest, write_manifest
        merged_extraction, merges = federate(extraction, peers, local_repo=local_repo)
        extraction["nodes"] = list(merged_extraction.get("nodes", []))
        extraction["edges"] = [dict(e) for e in merged_extraction.get("edges", [])]
        manifest = build_manifest(merges)
        write_manifest(
            manifest,
            target_dir or Path.cwd(),
            resolved=resolved_output,
        )

    errors = validate_extraction(extraction)
    # Dangling edges (stdlib/external imports) are expected - only warn about real schema errors.
    real_errors = [e for e in errors if "does not match any node id" not in e]
    if real_errors:
        print(f"[graphify] Extraction warning ({len(real_errors)} issues): {real_errors[0]}", file=sys.stderr)
    G: nx.Graph = nx.DiGraph() if directed else nx.Graph()
    # Phase 53 (D-53.06 / W2): insert nodes in canonical-edge-source order so that
    # NetworkX undirected edge iteration matches the (source, target, relation)
    # ascending sort applied by _normalize_concept_code_edges. NetworkX iterates
    # edges per-node in node insertion order; if nodes are added in arbitrary
    # input order, edge iteration won't match the canonical sort even though the
    # underlying edge list is sorted. Isolated nodes (not appearing as any edge
    # endpoint) are appended afterward.
    nodes_by_id = {node["id"]: node for node in extraction.get("nodes", []) if "id" in node}
    insertion_order: list[str] = []
    seen: set[str] = set()
    # First pass: add edge SOURCES in edge order (edges already canonically sorted by
    # _normalize_concept_code_edges). This ensures every edge endpoint listed as
    # `source` has a lower node-insertion index than the corresponding `target`,
    # so NetworkX undirected iteration yields (source, target) tuples in canonical order.
    for edge in extraction.get("edges", []):
        nid = edge.get("source")
        if isinstance(nid, str) and nid in nodes_by_id and nid not in seen:
            seen.add(nid)
            insertion_order.append(nid)
    # Second pass: add edge TARGETS not yet seen.
    for edge in extraction.get("edges", []):
        nid = edge.get("target")
        if isinstance(nid, str) and nid in nodes_by_id and nid not in seen:
            seen.add(nid)
            insertion_order.append(nid)
    # Third pass: append isolated nodes (those not appearing in any edge) in original input order.
    for nid in nodes_by_id:
        if nid not in seen:
            insertion_order.append(nid)
            seen.add(nid)
    for nid in insertion_order:
        node = nodes_by_id[nid]
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
