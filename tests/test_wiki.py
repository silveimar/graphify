"""Tests for graphify.wiki — Wikipedia-style article generation."""
import pytest
from pathlib import Path
import networkx as nx
from graphify.wiki import to_wiki, _index_md, _community_article, _god_node_article


def _make_graph():
    G = nx.Graph()
    G.add_node("n1", label="parse", file_type="code", source_file="parser.py", community=0)
    G.add_node("n2", label="validate", file_type="code", source_file="parser.py", community=0)
    G.add_node("n3", label="render", file_type="code", source_file="renderer.py", community=1)
    G.add_node("n4", label="stream", file_type="code", source_file="renderer.py", community=1)
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED", weight=1.0)
    G.add_edge("n1", "n3", relation="references", confidence="INFERRED", weight=1.0)
    G.add_edge("n3", "n4", relation="calls", confidence="EXTRACTED", weight=1.0)
    return G


COMMUNITIES = {0: ["n1", "n2"], 1: ["n3", "n4"]}
LABELS = {0: "Parsing Layer", 1: "Rendering Layer"}
COHESION = {0: 0.85, 1: 0.72}
GOD_NODES = [{"id": "n1", "label": "parse", "edges": 2}]


def test_to_wiki_writes_index(tmp_path):
    G = _make_graph()
    n = to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, cohesion=COHESION, god_nodes_data=GOD_NODES)
    assert (tmp_path / "index.md").exists()


def test_to_wiki_returns_article_count(tmp_path):
    G = _make_graph()
    # 2 communities + 1 god node = 3
    n = to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, cohesion=COHESION, god_nodes_data=GOD_NODES)
    assert n == 3


def test_to_wiki_community_articles_created(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    assert (tmp_path / "Parsing_Layer.md").exists()
    assert (tmp_path / "Rendering_Layer.md").exists()


def test_to_wiki_god_node_article_created(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, god_nodes_data=GOD_NODES)
    assert (tmp_path / "parse.md").exists()


def test_index_links_all_communities(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    index = (tmp_path / "index.md").read_text()
    assert "[[Parsing Layer]]" in index
    assert "[[Rendering Layer]]" in index


def test_index_lists_god_nodes(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, god_nodes_data=GOD_NODES)
    index = (tmp_path / "index.md").read_text()
    assert "[[parse]]" in index
    assert "2 connections" in index


def test_community_article_has_cross_links(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    # n1 (parsing) references n3 (rendering) → cross-community link
    assert "[[Rendering Layer]]" in parsing


def test_community_article_shows_cohesion(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, cohesion=COHESION)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    assert "cohesion 0.85" in parsing


def test_community_article_has_audit_trail(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    assert "EXTRACTED" in parsing
    assert "INFERRED" in parsing


def test_god_node_article_has_connections(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, god_nodes_data=GOD_NODES)
    article = (tmp_path / "parse.md").read_text()
    assert "[[validate]]" in article or "[[render]]" in article


def test_god_node_article_links_community(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, god_nodes_data=GOD_NODES)
    article = (tmp_path / "parse.md").read_text()
    assert "[[Parsing Layer]]" in article


def test_to_wiki_skips_missing_god_node_ids(tmp_path):
    """God node with bad ID should not crash."""
    G = _make_graph()
    bad_gods = [{"id": "nonexistent", "label": "ghost", "edges": 99}]
    n = to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS, god_nodes_data=bad_gods)
    # 2 communities + 0 god nodes (nonexistent skipped) = 2
    assert n == 2


def test_to_wiki_no_labels_uses_fallback(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path)  # no labels
    assert (tmp_path / "Community_0.md").exists()
    assert (tmp_path / "Community_1.md").exists()


def test_article_navigation_footer(tmp_path):
    G = _make_graph()
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    article = (tmp_path / "Parsing_Layer.md").read_text()
    assert "[[index]]" in article


def test_community_article_truncation_notice(tmp_path):
    """Communities with more than 25 nodes show a truncation notice."""
    G = nx.Graph()
    nodes = [f"n{i}" for i in range(30)]
    for nid in nodes:
        G.add_node(nid, label=f"concept_{nid}", file_type="code", source_file="a.py", community=0)
    for i in range(len(nodes) - 1):
        G.add_edge(nodes[i], nodes[i + 1], relation="calls", confidence="EXTRACTED", weight=1.0)
    communities = {0: nodes}
    to_wiki(G, communities, tmp_path, community_labels={0: "Big Community"})
    article = (tmp_path / "Big_Community.md").read_text()
    assert "and 5 more nodes" in article


# --- Phase 71-05 Historical relations subsection (TEMP-04, D-11 omit-when-empty) ---

def _make_graph_with_history():
    """Community 0 has 1 historical edge (n1->n5) and current edges. Community 1 has none."""
    G = nx.Graph()
    G.add_node("n1", label="parse", file_type="code", source_file="parser.py", community=0)
    G.add_node("n2", label="validate", file_type="code", source_file="parser.py", community=0)
    G.add_node("n3", label="render", file_type="code", source_file="renderer.py", community=1)
    G.add_node("n4", label="stream", file_type="code", source_file="renderer.py", community=1)
    G.add_node("n5", label="legacy_helper", file_type="code", source_file="parser.py", community=0)
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED", weight=1.0, valid_until=None)
    G.add_edge("n3", "n4", relation="calls", confidence="EXTRACTED", weight=1.0, valid_until=None)
    G.add_edge("n1", "n5", relation="calls", confidence="INFERRED", weight=1.0,
               valid_until="2026-05-07T12:00:00+00:00")
    return G


def test_historical_relations_section(tmp_path):
    G = _make_graph_with_history()
    communities = {0: ["n1", "n2", "n5"], 1: ["n3", "n4"]}
    labels = {0: "Parsing Layer", 1: "Rendering Layer"}
    to_wiki(G, communities, tmp_path, community_labels=labels)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    assert "## Historical relations" in parsing


def test_historical_relations_omitted_when_empty(tmp_path):
    G = _make_graph_with_history()
    communities = {0: ["n1", "n2", "n5"], 1: ["n3", "n4"]}
    labels = {0: "Parsing Layer", 1: "Rendering Layer"}
    to_wiki(G, communities, tmp_path, community_labels=labels)
    rendering = (tmp_path / "Rendering_Layer.md").read_text()
    assert "## Historical relations" not in rendering


def test_historical_relations_format(tmp_path):
    G = _make_graph_with_history()
    communities = {0: ["n1", "n2", "n5"], 1: ["n3", "n4"]}
    labels = {0: "Parsing Layer", 1: "Rendering Layer"}
    to_wiki(G, communities, tmp_path, community_labels=labels)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    # Format: - [[neighbor]] (until <valid_until>)
    assert "[[n5]]" in parsing or "[[legacy_helper]]" in parsing
    assert "(until 2026-05-07T12:00:00+00:00)" in parsing


def test_historical_relations_security_escape(tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="x", file_type="code", source_file="x.py", community=0)
    G.add_node("n2", label="y", file_type="code", source_file="x.py", community=0)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED", weight=1.0,
               valid_until="<script>alert(1)</script>")
    communities = {0: ["n1", "n2"]}
    to_wiki(G, communities, tmp_path, community_labels={0: "C"})
    art = (tmp_path / "C.md").read_text()
    assert "<script>" not in art
    assert "&lt;script&gt;" in art


def test_historical_relations_length_cap(tmp_path):
    G = nx.Graph()
    long_vu = "A" * 200
    G.add_node("n1", label="x", file_type="code", source_file="x.py", community=0)
    G.add_node("n2", label="y", file_type="code", source_file="x.py", community=0)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED", weight=1.0,
               valid_until=long_vu)
    communities = {0: ["n1", "n2"]}
    to_wiki(G, communities, tmp_path, community_labels={0: "C"})
    art = (tmp_path / "C.md").read_text()
    # 64-char cap
    assert "A" * 64 in art
    assert "A" * 65 not in art


def test_currently_valid_pass_unchanged(tmp_path):
    """Regression: existing relationship/audit-trail rendering unchanged when no historical edges."""
    G = _make_graph()  # original fixture, no valid_until
    to_wiki(G, COMMUNITIES, tmp_path, community_labels=LABELS)
    parsing = (tmp_path / "Parsing_Layer.md").read_text()
    assert "## Relationships" in parsing
    assert "## Audit Trail" in parsing
    assert "## Historical relations" not in parsing
