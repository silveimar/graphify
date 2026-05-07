# Wiki export - Wikipedia-style markdown articles from the knowledge graph
# Generates an agent-crawlable wiki: index.md + one article per community + god node articles
from __future__ import annotations
import html
from collections import Counter
from pathlib import Path
import networkx as nx


def _safe_filename(name: str) -> str:
    return name.replace("/", "-").replace(" ", "_").replace(":", "-")


def _cross_community_links(G: nx.Graph, nodes: list[str], own_cid: int, labels: dict[int, str]) -> list[tuple[str, int]]:
    """Return (community_label, edge_count) pairs for cross-community connections, sorted descending."""
    counts: dict[str, int] = Counter()
    for nid in nodes:
        for neighbor in G.neighbors(nid):
            nd = G.nodes[neighbor]
            ncid = nd.get("community")
            if ncid is not None and ncid != own_cid:
                counts[labels.get(ncid, f"Community {ncid}")] += 1
    return sorted(counts.items(), key=lambda x: -x[1])


def _community_article(
    G: nx.Graph,
    cid: int,
    nodes: list[str],
    label: str,
    labels: dict[int, str],
    cohesion: float | None,
) -> str:
    top_nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)[:25]
    cross = _cross_community_links(G, nodes, cid, labels)

    # Edge confidence breakdown
    conf_counts: Counter = Counter()
    for nid in nodes:
        for neighbor in G.neighbors(nid):
            ed = G.edges[nid, neighbor]
            conf_counts[ed.get("confidence", "EXTRACTED")] += 1
    total_edges = sum(conf_counts.values()) or 1

    sources = sorted({G.nodes[n].get("source_file", "") for n in nodes} - {""})

    lines: list[str] = []
    lines += [f"# {label}", ""]

    meta_parts = [f"{len(nodes)} nodes"]
    if cohesion is not None:
        meta_parts.append(f"cohesion {cohesion:.2f}")
    lines += [f"> {' · '.join(meta_parts)}", ""]

    lines += ["## Key Concepts", ""]
    for nid in top_nodes:
        d = G.nodes[nid]
        node_label = d.get("label", nid)
        src = d.get("source_file", "")
        degree = G.degree(nid)
        src_str = f" — `{src}`" if src else ""
        lines.append(f"- **{node_label}** ({degree} connections){src_str}")
    remaining = len(nodes) - len(top_nodes)
    if remaining > 0:
        lines.append(f"- *... and {remaining} more nodes in this community*")
    lines.append("")

    # --- Phase 72-04 (REAS-04, D-14) Reasoning Relations subsection ---
    # Per-community pass over outbound reasoning edges (supports / contradicts /
    # supersedes / evolved_into / depends_on). Placed BEFORE both
    # `## Relationships` and `## Historical relations`. Omitted entirely when
    # no qualifying edges exist (omit-when-empty rule). Neighbor labels are
    # html.escape'd and 64-char-capped (T-72-11 / T-71-15 precedent).
    from .validate import REASONING_RELATIONS
    reasoning: list[tuple[str, str, float | None]] = []
    seen_r: set[tuple[str, str, str]] = set()
    for nid in nodes:
        for neighbor in G.neighbors(nid):
            ed = G.edges[nid, neighbor]
            rel = ed.get("relation")
            if rel not in REASONING_RELATIONS:
                continue
            # Honor _src/_tgt for direction recovery; only emit outbound edges
            # whose source is a node in this community.
            src = ed.get("_src", nid)
            if src != nid:
                continue
            tgt = ed.get("_tgt", neighbor)
            tgt_label = G.nodes[tgt].get("label", tgt) if tgt in G else tgt
            score = ed.get("confidence_score")
            score_f: float | None = None
            if isinstance(score, (int, float)):
                score_f = float(score)
            key = (rel, str(src), str(tgt))
            if key in seen_r:
                continue
            seen_r.add(key)
            reasoning.append((rel, str(tgt_label), score_f))
    if reasoning:
        lines += ["## Reasoning Relations", ""]
        for rel, tgt_label, score_f in reasoning:
            safe_label = html.escape(str(tgt_label))[:64]
            score_str = f" (confidence {score_f:.2f})" if score_f is not None else ""
            lines.append(f"- {rel}: [[{safe_label}]]{score_str}")
        lines.append("")

    lines += ["## Relationships", ""]
    if cross:
        for other_label, count in cross[:12]:
            lines.append(f"- [[{other_label}]] ({count} shared connections)")
    else:
        lines.append("- No strong cross-community connections detected")
    lines.append("")

    if sources:
        lines += ["## Source Files", ""]
        for src in sources[:20]:
            lines.append(f"- `{src}`")
        lines.append("")

    lines += ["## Audit Trail", ""]
    for conf in ("EXTRACTED", "INFERRED", "AMBIGUOUS"):
        n = conf_counts.get(conf, 0)
        pct = round(n / total_edges * 100)
        lines.append(f"- {conf}: {n} ({pct}%)")
    lines.append("")

    # --- Phase 71-05 (TEMP-04, D-11) Historical relations ---
    # Second filtered pass over edges incident to this community: any edge with
    # valid_until set is rendered as `- [[neighbor_label]] (until <valid_until>)`.
    # Heading omitted entirely when empty (D-11). valid_until is html.escape'd
    # and 64-char-capped (T-71-15 / T-71-19) as defense in depth even though
    # build-time stamping controls the value.
    historical: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for nid in nodes:
        for neighbor in G.neighbors(nid):
            ed = G.edges[nid, neighbor]
            vu = ed.get("valid_until")
            if vu is None:
                continue
            key = tuple(sorted((nid, neighbor)))
            if key in seen:
                continue
            seen.add(key)
            neighbor_label = G.nodes[neighbor].get("label", neighbor)
            historical.append((neighbor_label, str(vu)))
    if historical:
        lines += ["## Historical relations", ""]
        for neighbor_label, vu in historical:
            vu_safe = html.escape(vu)[:64]
            lines.append(f"- [[{neighbor_label}]] (until {vu_safe})")
        lines.append("")

    lines += ["---", "", "*Part of the graphify knowledge wiki. See [[index]] to navigate.*"]
    return "\n".join(lines)


def _god_node_article(G: nx.Graph, nid: str, labels: dict[int, str]) -> str:
    d = G.nodes[nid]
    node_label = d.get("label", nid)
    src = d.get("source_file", "")
    cid = d.get("community")
    community_name = labels.get(cid, f"Community {cid}") if cid is not None else None

    lines: list[str] = []
    lines += [f"# {node_label}", ""]
    lines += [f"> God node · {G.degree(nid)} connections · `{src}`", ""]

    if community_name:
        lines += [f"**Community:** [[{community_name}]]", ""]

    # Group neighbors by relation type
    by_relation: dict[str, list[str]] = {}
    for neighbor in sorted(G.neighbors(nid), key=lambda n: G.degree(n), reverse=True):
        nd = G.nodes[neighbor]
        ed = G.edges[nid, neighbor]
        rel = ed.get("relation", "related")
        neighbor_label = nd.get("label", neighbor)
        conf = ed.get("confidence", "")
        conf_str = f" `{conf}`" if conf else ""
        by_relation.setdefault(rel, []).append(f"[[{neighbor_label}]]{conf_str}")

    lines += ["## Connections by Relation", ""]
    for rel, targets in sorted(by_relation.items()):
        lines.append(f"### {rel}")
        for t in targets[:20]:
            lines.append(f"- {t}")
        lines.append("")

    lines += ["---", "", "*Part of the graphify knowledge wiki. See [[index]] to navigate.*"]
    return "\n".join(lines)


def _index_md(
    communities: dict[int, list[str]],
    labels: dict[int, str],
    god_nodes_data: list[dict],
    total_nodes: int,
    total_edges: int,
) -> str:
    lines: list[str] = [
        "# Knowledge Graph Index",
        "",
        "> Auto-generated by graphify. Start here — read community articles for context, then drill into god nodes for detail.",
        "",
        f"**{total_nodes} nodes · {total_edges} edges · {len(communities)} communities**",
        "",
        "---",
        "",
        "## Communities",
        "(sorted by size, largest first)",
        "",
    ]

    for cid, nodes in sorted(communities.items(), key=lambda x: -len(x[1])):
        label = labels.get(cid, f"Community {cid}")
        lines.append(f"- [[{label}]] — {len(nodes)} nodes")
    lines.append("")

    if god_nodes_data:
        lines += ["## God Nodes", "(most connected concepts — the load-bearing abstractions)", ""]
        for node in god_nodes_data:
            lines.append(f"- [[{node['label']}]] — {node['edges']} connections")
        lines.append("")

    lines += [
        "---",
        "",
        "*Generated by [graphify](https://github.com/silveimar/graphify)*",
    ]
    return "\n".join(lines)


def to_wiki(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str | Path,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    god_nodes_data: list[dict] | None = None,
) -> int:
    """Generate a Wikipedia-style wiki from the graph.

    Writes:
      - index.md            — agent entry point, catalog of all articles
      - <CommunityName>.md  — one article per community
      - <GodNodeLabel>.md   — one article per god node

    Returns the number of articles written (excluding index.md).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    labels = community_labels or {cid: f"Community {cid}" for cid in communities}
    cohesion = cohesion or {}
    god_nodes_data = god_nodes_data or []

    count = 0

    # Community articles
    for cid, nodes in communities.items():
        label = labels.get(cid, f"Community {cid}")
        article = _community_article(G, cid, nodes, label, labels, cohesion.get(cid))
        (out / f"{_safe_filename(label)}.md").write_text(article)
        count += 1

    # God node articles
    for node_data in god_nodes_data:
        nid = node_data.get("id")
        if nid and nid in G:
            article = _god_node_article(G, nid, labels)
            (out / f"{_safe_filename(node_data['label'])}.md").write_text(article)
            count += 1

    # Index
    (out / "index.md").write_text(
        _index_md(communities, labels, god_nodes_data, G.number_of_nodes(), G.number_of_edges())
    )

    return count
