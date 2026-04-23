"""Graph analysis: god nodes (most connected), surprising connections (cross-community), suggested questions."""
from __future__ import annotations
import networkx as nx


def _node_community_map(communities: dict[int, list[str]]) -> dict[str, int]:
    """Invert communities dict: node_id -> community_id."""
    return {n: cid for cid, nodes in communities.items() for n in nodes}


def _iter_sources(source_file: "str | list[str] | None") -> list[str]:
    """Normalize source_file to a flat list of non-empty strings.

    Canonical nodes produced by dedup may carry source_file: list[str] when
    they were merged from multiple source files (Phase 10 D-12). All analyze.py
    call sites that read source_file MUST go through this helper so that both
    str and list[str] shapes are handled identically.

    str   -> [str]  (unchanged single-source nodes)
    list  -> filtered list of non-empty str elements
    None/empty -> []
    """
    if not source_file:
        return []
    if isinstance(source_file, str):
        return [source_file]
    if isinstance(source_file, list):
        return [s for s in source_file if isinstance(s, str) and s]
    return []


def _fmt_source_file(source_file: "str | list[str] | None") -> str:
    """Flatten source_file to a display string for report rendering.

    list[str] -> comma-joined string (e.g. "src/auth.py, lib/auth_impl.py")
    str       -> unchanged
    None/empty -> ""

    Prevents Python list repr (``['a.py', 'b.py']``) from appearing in
    GRAPH_REPORT.md surprising-connections rows.
    """
    sources = _iter_sources(source_file)
    if not sources:
        return ""
    return ", ".join(sources)


def _is_file_node(G: nx.Graph, node_id: str) -> bool:
    """
    Return True if this node is a file-level hub node (e.g. 'client', 'models')
    or an AST method stub (e.g. '.auth_flow()', '.__init__()').

    These are synthetic nodes created by the AST extractor and should be excluded
    from god nodes, surprising connections, and knowledge gap reporting.
    """
    attrs = G.nodes[node_id]
    label = attrs.get("label", "")
    if not label:
        return False
    # File-level hub: label matches the actual source filename (not just any label ending in .py)
    source_file = attrs.get("source_file", "")
    if source_file:
        from pathlib import Path as _Path
        if any(label == _Path(s).name for s in _iter_sources(source_file)):
            return True
    # Method stub: AST extractor labels methods as '.method_name()'
    if label.startswith(".") and label.endswith("()"):
        return True
    # Module-level function stub: labeled 'function_name()' - only has a contains edge
    # These are real functions but structurally isolated by definition; not a gap worth flagging
    if label.endswith("()") and G.degree(node_id) <= 1:
        return True
    return False


def god_nodes(G: nx.Graph, top_n: int = 10) -> list[dict]:
    """Return the top_n most-connected real entities - the core abstractions.

    File-level hub nodes are excluded: they accumulate import/contains edges
    mechanically and don't represent meaningful architectural abstractions.
    """
    degree = dict(G.degree())
    sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    result = []
    for node_id, deg in sorted_nodes:
        if _is_file_node(G, node_id) or _is_concept_node(G, node_id):
            continue
        # Phase 20-01 / D-18: tag selected god nodes as possible diagram seeds.
        # This node attribute is the sole auto-detection signal consumed by
        # graphify.seed (Plan 20-02). Do not reimplement detection elsewhere.
        G.nodes[node_id]["possible_diagram_seed"] = True
        result.append({
            "id": node_id,
            "label": G.nodes[node_id].get("label", node_id),
            "edges": deg,
        })
        if len(result) >= top_n:
            break
    return result


def surprising_connections(
    G: nx.Graph,
    communities: dict[int, list[str]] | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Find connections that are genuinely surprising - not obvious from file structure.

    Strategy:
    - Multi-file corpora: cross-file edges between real entities (not concept nodes).
      Sorted AMBIGUOUS → INFERRED → EXTRACTED.
    - Single-file / single-source corpora: cross-community edges that bridge
      distant parts of the graph (betweenness centrality on edges).
      These reveal non-obvious structural couplings.

    Concept nodes (empty source_file, or injected semantic annotations) are excluded
    from surprising connections because they are intentional, not discovered.
    """
    # Identify unique source files (ignore empty/null source_file).
    # source_file may be str or list[str] after dedup; flatten via _iter_sources.
    source_files = {
        s
        for _, data in G.nodes(data=True)
        for s in _iter_sources(data.get("source_file", ""))
    }
    is_multi_source = len(source_files) > 1

    if is_multi_source:
        return _cross_file_surprises(G, communities or {}, top_n)
    else:
        return _cross_community_surprises(G, communities or {}, top_n)


def _is_concept_node(G: nx.Graph, node_id: str) -> bool:
    """
    Return True if this node is a manually-injected semantic concept node
    rather than a real entity found in source code.

    Signals:
    - Empty source_file
    - source_file doesn't look like a real file path (no extension)
    """
    data = G.nodes[node_id]
    source = data.get("source_file", "")
    sources = _iter_sources(source)
    if not sources:
        return True
    # Node is concrete if ANY source looks like a real file (has an extension).
    # A node is a concept only if NONE of its sources have a file extension.
    return not any("." in s.split("/")[-1] for s in sources)


from graphify.detect import CODE_EXTENSIONS, DOC_EXTENSIONS, PAPER_EXTENSIONS, IMAGE_EXTENSIONS


def _file_category(path: str) -> str:
    ext = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in PAPER_EXTENSIONS:
        return "paper"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return "doc"


def _top_level_dir(path: str) -> str:
    """Return the first path component - used to detect cross-repo edges."""
    return path.split("/")[0] if "/" in path else path


def _surprise_score(
    G: nx.Graph,
    u: str,
    v: str,
    data: dict,
    node_community: dict[str, int],
    u_source: str,
    v_source: str,
) -> tuple[int, list[str]]:
    """Score how surprising a cross-file edge is. Returns (score, reasons)."""
    score = 0
    reasons: list[str] = []

    # 1. Confidence weight - uncertain connections are more noteworthy
    conf = data.get("confidence", "EXTRACTED")
    conf_bonus = {"AMBIGUOUS": 3, "INFERRED": 2, "EXTRACTED": 1}.get(conf, 1)
    score += conf_bonus
    if conf in ("AMBIGUOUS", "INFERRED"):
        reasons.append(f"{conf.lower()} connection - not explicitly stated in source")

    # 2. Cross file-type bonus - code↔paper or code↔image is non-obvious
    cat_u = _file_category(u_source)
    cat_v = _file_category(v_source)
    if cat_u != cat_v:
        score += 2
        reasons.append(f"crosses file types ({cat_u} ↔ {cat_v})")

    # 3. Cross-repo bonus - different top-level directory
    if _top_level_dir(u_source) != _top_level_dir(v_source):
        score += 2
        reasons.append("connects across different repos/directories")

    # 4. Cross-community bonus - Leiden says these are structurally distant
    cid_u = node_community.get(u)
    cid_v = node_community.get(v)
    if cid_u is not None and cid_v is not None and cid_u != cid_v:
        score += 1
        reasons.append("bridges separate communities")

    # 4b. Semantic similarity bonus - non-obvious conceptual links score higher
    if data.get("relation") == "semantically_similar_to":
        score = int(score * 1.5)
        reasons.append("semantically similar concepts with no structural link")

    # 5. Peripheral→hub: a low-degree node connecting to a high-degree one
    deg_u = G.degree(u)
    deg_v = G.degree(v)
    if min(deg_u, deg_v) <= 2 and max(deg_u, deg_v) >= 5:
        score += 1
        peripheral = G.nodes[u].get("label", u) if deg_u <= 2 else G.nodes[v].get("label", v)
        hub = G.nodes[v].get("label", v) if deg_u <= 2 else G.nodes[u].get("label", u)
        reasons.append(f"peripheral node `{peripheral}` unexpectedly reaches hub `{hub}`")

    return score, reasons


def _cross_file_surprises(G: nx.Graph, communities: dict[int, list[str]], top_n: int) -> list[dict]:
    """
    Cross-file edges between real code/doc entities, ranked by a composite
    surprise score rather than confidence alone.

    Surprise score accounts for:
    - Confidence (AMBIGUOUS > INFERRED > EXTRACTED)
    - Cross file-type (code↔paper is more surprising than code↔code)
    - Cross-repo (different top-level directory)
    - Cross-community (Leiden says structurally distant)
    - Peripheral→hub (low-degree node reaching a god node)

    Each result includes a 'why' field explaining what makes it non-obvious.
    """
    node_community = _node_community_map(communities)
    candidates = []

    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "")
        if relation in ("imports", "imports_from", "contains", "method"):
            continue
        if _is_concept_node(G, u) or _is_concept_node(G, v):
            continue
        if _is_file_node(G, u) or _is_file_node(G, v):
            continue

        u_source_raw = G.nodes[u].get("source_file", "")
        v_source_raw = G.nodes[v].get("source_file", "")

        u_sources = tuple(sorted(_iter_sources(u_source_raw)))
        v_sources = tuple(sorted(_iter_sources(v_source_raw)))

        if not u_sources or not v_sources or u_sources == v_sources:
            continue

        # Use the first sorted source for single-string helpers (_file_category, _top_level_dir)
        u_source = u_sources[0]
        v_source = v_sources[0]

        score, reasons = _surprise_score(G, u, v, data, node_community, u_source, v_source)
        src_id = data.get("_src", u)
        if src_id not in G.nodes:
            src_id = u
        tgt_id = data.get("_tgt", v)
        if tgt_id not in G.nodes:
            tgt_id = v
        candidates.append({
            "_score": score,
            "source": G.nodes[src_id].get("label", src_id),
            "target": G.nodes[tgt_id].get("label", tgt_id),
            "source_files": [
                _fmt_source_file(G.nodes[src_id].get("source_file", "")),
                _fmt_source_file(G.nodes[tgt_id].get("source_file", "")),
            ],
            "confidence": data.get("confidence", "EXTRACTED"),
            "relation": relation,
            "why": "; ".join(reasons) if reasons else "cross-file semantic connection",
        })

    candidates.sort(key=lambda x: x["_score"], reverse=True)
    for c in candidates:
        c.pop("_score")

    if candidates:
        return candidates[:top_n]

    return _cross_community_surprises(G, communities, top_n)


def _cross_community_surprises(
    G: nx.Graph,
    communities: dict[int, list[str]],
    top_n: int,
) -> list[dict]:
    """
    For single-source corpora: find edges that bridge different communities.
    These are surprising because Leiden grouped everything else tightly -
    these edges cut across the natural structure.

    Falls back to high-betweenness edges if no community info is provided.
    """
    if not communities:
        # No community info - use edge betweenness centrality
        if G.number_of_edges() == 0:
            return []
        betweenness = nx.edge_betweenness_centrality(G)
        top_edges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_n]
        result = []
        for (u, v), score in top_edges:
            data = G.edges[u, v]
            result.append({
                "source": G.nodes[u].get("label", u),
                "target": G.nodes[v].get("label", v),
                "source_files": [
                    _fmt_source_file(G.nodes[u].get("source_file", "")),
                    _fmt_source_file(G.nodes[v].get("source_file", "")),
                ],
                "confidence": data.get("confidence", "EXTRACTED"),
                "relation": data.get("relation", ""),
                "why": f"Bridges graph structure (betweenness={score:.3f})",
            })
        return result

    # Build node → community map
    node_community = _node_community_map(communities)

    surprises = []
    for u, v, data in G.edges(data=True):
        cid_u = node_community.get(u)
        cid_v = node_community.get(v)
        if cid_u is None or cid_v is None or cid_u == cid_v:
            continue
        # Skip file hub nodes and plain structural edges
        if _is_file_node(G, u) or _is_file_node(G, v):
            continue
        relation = data.get("relation", "")
        if relation in ("imports", "imports_from", "contains", "method"):
            continue
        # This edge crosses community boundaries - interesting
        confidence = data.get("confidence", "EXTRACTED")
        src_id = data.get("_src", u)
        if src_id not in G.nodes:
            src_id = u
        tgt_id = data.get("_tgt", v)
        if tgt_id not in G.nodes:
            tgt_id = v
        surprises.append({
            "source": G.nodes[src_id].get("label", src_id),
            "target": G.nodes[tgt_id].get("label", tgt_id),
            "source_files": [
                _fmt_source_file(G.nodes[src_id].get("source_file", "")),
                _fmt_source_file(G.nodes[tgt_id].get("source_file", "")),
            ],
            "confidence": confidence,
            "relation": relation,
            "why": f"Bridges community {cid_u} → community {cid_v}",
            "_pair": tuple(sorted([cid_u, cid_v])),
            "_src_id": src_id,
            "_tgt_id": tgt_id,
        })

    # Sort: AMBIGUOUS first, then INFERRED, then EXTRACTED
    order = {"AMBIGUOUS": 0, "INFERRED": 1, "EXTRACTED": 2}
    surprises.sort(key=lambda x: order.get(x["confidence"], 3))

    # Deduplicate by community pair - one representative edge per (A→B) boundary.
    # Without this, a single high-betweenness god node dominates all results.
    seen_pairs: set[tuple] = set()
    deduped = []
    for s in surprises:
        pair = s.pop("_pair")
        src_id = s.pop("_src_id")
        tgt_id = s.pop("_tgt_id")
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            # Phase 20-01 / D-18: tag both endpoints of each emitted
            # cross-community bridge as a possible diagram seed. Consumed by
            # graphify.seed (Plan 20-02) via detect_user_seeds().
            G.nodes[src_id]["possible_diagram_seed"] = True
            G.nodes[tgt_id]["possible_diagram_seed"] = True
            deduped.append(s)
    return deduped[:top_n]


def suggest_questions(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    top_n: int = 7,
) -> list[dict]:
    """
    Generate questions the graph is uniquely positioned to answer.
    Based on: AMBIGUOUS edges, bridge nodes, underexplored god nodes, isolated nodes.
    Each question has a 'type', 'question', and 'why' field.
    """
    questions = []
    node_community = _node_community_map(communities)

    # 1. AMBIGUOUS edges → unresolved relationship questions
    for u, v, data in G.edges(data=True):
        if data.get("confidence") == "AMBIGUOUS":
            ul = G.nodes[u].get("label", u)
            vl = G.nodes[v].get("label", v)
            relation = data.get("relation", "related to")
            questions.append({
                "type": "ambiguous_edge",
                "question": f"What is the exact relationship between `{ul}` and `{vl}`?",
                "why": f"Edge tagged AMBIGUOUS (relation: {relation}) - confidence is low.",
            })

    # 2. Bridge nodes (high betweenness) → cross-cutting concern questions
    if G.number_of_edges() > 0:
        betweenness = nx.betweenness_centrality(G)
        # Top bridge nodes that are NOT file-level hubs
        bridges = sorted(
            [(n, s) for n, s in betweenness.items()
             if not _is_file_node(G, n) and not _is_concept_node(G, n) and s > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        for node_id, score in bridges:
            label = G.nodes[node_id].get("label", node_id)
            cid = node_community.get(node_id)
            comm_label = community_labels.get(cid, f"Community {cid}") if cid is not None else "unknown"
            neighbors = list(G.neighbors(node_id))
            neighbor_comms = {node_community.get(n) for n in neighbors if node_community.get(n) != cid}
            if neighbor_comms:
                other_labels = [community_labels.get(c, f"Community {c}") for c in neighbor_comms]
                questions.append({
                    "type": "bridge_node",
                    "question": f"Why does `{label}` connect `{comm_label}` to {', '.join(f'`{l}`' for l in other_labels)}?",
                    "why": f"High betweenness centrality ({score:.3f}) - this node is a cross-community bridge.",
                })

    # 3. God nodes with many INFERRED edges → verification questions
    degree = dict(G.degree())
    top_nodes = sorted(
        [(n, d) for n, d in degree.items() if not _is_file_node(G, n)],
        key=lambda x: x[1],
        reverse=True,
    )[:5]
    for node_id, _ in top_nodes:
        inferred = [
            (u, v, d) for u, v, d in G.edges(node_id, data=True)
            if d.get("confidence") == "INFERRED"
        ]
        if len(inferred) >= 2:
            label = G.nodes[node_id].get("label", node_id)
            # Use _src/_tgt to get the correct direction; fall back to v (the other node)
            others = []
            for u, v, d in inferred[:2]:
                src_id = d.get("_src", u)
                if src_id not in G.nodes:
                    src_id = u
                tgt_id = d.get("_tgt", v)
                if tgt_id not in G.nodes:
                    tgt_id = v
                other_id = tgt_id if src_id == node_id else src_id
                others.append(G.nodes[other_id].get("label", other_id))
            questions.append({
                "type": "verify_inferred",
                "question": f"Are the {len(inferred)} inferred relationships involving `{label}` (e.g. with `{others[0]}` and `{others[1]}`) actually correct?",
                "why": f"`{label}` has {len(inferred)} INFERRED edges - model-reasoned connections that need verification.",
            })

    # 4. Isolated or weakly-connected nodes → exploration questions
    isolated = [
        n for n in G.nodes()
        if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)
    ]
    if isolated:
        labels = [G.nodes[n].get("label", n) for n in isolated[:3]]
        questions.append({
            "type": "isolated_nodes",
            "question": f"What connects {', '.join(f'`{l}`' for l in labels)} to the rest of the system?",
            "why": f"{len(isolated)} weakly-connected nodes found - possible documentation gaps or missing edges.",
        })

    # 5. Low-cohesion communities → structural questions
    from .cluster import cohesion_score
    for cid, nodes in communities.items():
        score = cohesion_score(G, nodes)
        if score < 0.15 and len(nodes) >= 5:
            label = community_labels.get(cid, f"Community {cid}")
            questions.append({
                "type": "low_cohesion",
                "question": f"Should `{label}` be split into smaller, more focused modules?",
                "why": f"Cohesion score {score} - nodes in this community are weakly interconnected.",
            })

    if not questions:
        return [{
            "type": "no_signal",
            "question": None,
            "why": (
                "Not enough signal to generate questions. "
                "This usually means the corpus has no AMBIGUOUS edges, no bridge nodes, "
                "no INFERRED relationships, and all communities are tightly cohesive. "
                "Add more files or run with --mode deep to extract richer edges."
            ),
        }]

    return questions[:top_n]


def render_analysis_context(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    top_n_nodes: int = 20,
) -> str:
    """Serialize graph structure to a compact prompt-safe text block for tournament lens agents."""
    lines = [
        f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities",
        "",
        "Most-connected entities (god nodes):",
    ]

    for n in god_node_list[:top_n_nodes]:
        label = n.get("label", n.get("id", ""))
        edges = n.get("edges", 0)
        lines.append(f"  - {label} ({edges} connections)")

    lines += ["", "Surprising cross-file connections:"]
    if surprise_list:
        for s in surprise_list:
            src = s.get("source", "")
            tgt = s.get("target", "")
            rel = s.get("relation", "")
            conf = s.get("confidence", "")
            why = s.get("why", "")
            lines.append(f"  - {src} --{rel}--> {tgt} [{conf}]: {why}")
    else:
        lines.append("  - None detected")

    lines += ["", "Communities:"]
    for cid, nodes in communities.items():
        label = community_labels.get(cid, f"Community {cid}")
        sample = nodes[:5]
        node_labels = [G.nodes[n].get("label", n) for n in sample if n in G.nodes]
        suffix = f", ... (+{len(nodes) - 5} more)" if len(nodes) > 5 else ""
        lines.append(f"  - {label}: {', '.join(node_labels)}{suffix}")

    return "\n".join(lines)


def graph_diff(G_old: nx.Graph, G_new: nx.Graph) -> dict:
    """Compare two graph snapshots and return what changed.

    Returns:
        {
          "new_nodes": [{"id": ..., "label": ...}],
          "removed_nodes": [{"id": ..., "label": ...}],
          "new_edges": [{"source": ..., "target": ..., "relation": ..., "confidence": ...}],
          "removed_edges": [...],
          "summary": "3 new nodes, 5 new edges, 1 node removed"
        }
    """
    old_nodes = set(G_old.nodes())
    new_nodes = set(G_new.nodes())

    added_node_ids = new_nodes - old_nodes
    removed_node_ids = old_nodes - new_nodes

    new_nodes_list = [
        {"id": n, "label": G_new.nodes[n].get("label", n)}
        for n in added_node_ids
    ]
    removed_nodes_list = [
        {"id": n, "label": G_old.nodes[n].get("label", n)}
        for n in removed_node_ids
    ]

    def edge_key(G: nx.Graph, u: str, v: str, data: dict) -> tuple:
        if G.is_directed():
            return (u, v, data.get("relation", ""))
        return (min(u, v), max(u, v), data.get("relation", ""))

    old_edge_keys = {
        edge_key(G_old, u, v, d)
        for u, v, d in G_old.edges(data=True)
    }
    new_edge_keys = {
        edge_key(G_new, u, v, d)
        for u, v, d in G_new.edges(data=True)
    }

    added_edge_keys = new_edge_keys - old_edge_keys
    removed_edge_keys = old_edge_keys - new_edge_keys

    new_edges_list = []
    for u, v, d in G_new.edges(data=True):
        if edge_key(G_new, u, v, d) in added_edge_keys:
            new_edges_list.append({
                "source": u,
                "target": v,
                "relation": d.get("relation", ""),
                "confidence": d.get("confidence", ""),
            })

    removed_edges_list = []
    for u, v, d in G_old.edges(data=True):
        if edge_key(G_old, u, v, d) in removed_edge_keys:
            removed_edges_list.append({
                "source": u,
                "target": v,
                "relation": d.get("relation", ""),
                "confidence": d.get("confidence", ""),
            })

    parts = []
    if new_nodes_list:
        parts.append(f"{len(new_nodes_list)} new node{'s' if len(new_nodes_list) != 1 else ''}")
    if new_edges_list:
        parts.append(f"{len(new_edges_list)} new edge{'s' if len(new_edges_list) != 1 else ''}")
    if removed_nodes_list:
        parts.append(f"{len(removed_nodes_list)} node{'s' if len(removed_nodes_list) != 1 else ''} removed")
    if removed_edges_list:
        parts.append(f"{len(removed_edges_list)} edge{'s' if len(removed_edges_list) != 1 else ''} removed")
    summary = ", ".join(parts) if parts else "no changes"

    return {
        "new_nodes": new_nodes_list,
        "removed_nodes": removed_nodes_list,
        "new_edges": new_edges_list,
        "removed_edges": removed_edges_list,
        "summary": summary,
    }


def knowledge_gaps(
    G: "nx.Graph",
    communities: dict[int, list[str]],
    ambiguity_threshold: float = 0.20,
) -> list[dict]:
    """Return nodes representing knowledge gaps.

    Each result is {"id": str, "label": str, "reason": str} where reason is one of
    "isolated", "thin_community", "high_ambiguity_context". Deduped by id (first reason wins).

    These nodes are candidates for promotion to Questions/ folder regardless of degree threshold.
    """
    results: list[dict] = []
    seen: set[str] = set()

    def _push(nid: str, reason: str) -> None:
        if nid in seen:
            return
        seen.add(nid)
        results.append({"id": nid, "label": G.nodes[nid].get("label", nid), "reason": reason})

    # Isolated: degree <= 1, not a file/concept node
    for n in G.nodes():
        if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n):
            _push(n, "isolated")

    # Thin communities: fewer than 3 members
    for cid, nodes in communities.items():
        if len(nodes) < 3:
            for n in nodes:
                if not _is_file_node(G, n) and not _is_concept_node(G, n):
                    _push(n, "thin_community")

    # High ambiguity context: AMBIGUOUS edge rate >= threshold
    total = G.number_of_edges()
    if total:
        ambiguous = [(u, v) for u, v, d in G.edges(data=True) if d.get("confidence") == "AMBIGUOUS"]
        if len(ambiguous) / total >= ambiguity_threshold:
            for u, v in ambiguous:
                for n in (u, v):
                    if not _is_file_node(G, n) and not _is_concept_node(G, n):
                        _push(n, "high_ambiguity_context")

    return results
