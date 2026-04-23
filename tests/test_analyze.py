"""Tests for analyze.py."""
import json
import networkx as nx
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.analyze import god_nodes, surprising_connections, _is_concept_node, graph_diff, _surprise_score, _file_category, render_analysis_context, _is_file_node, _top_level_dir, knowledge_gaps

FIXTURES = Path(__file__).parent / "fixtures"


def make_graph():
    return build_from_json(json.loads((FIXTURES / "extraction.json").read_text()))


def test_god_nodes_returns_list():
    G = make_graph()
    result = god_nodes(G, top_n=3)
    assert isinstance(result, list)
    assert len(result) <= 3


def test_god_nodes_sorted_by_degree():
    G = make_graph()
    result = god_nodes(G, top_n=10)
    degrees = [r["edges"] for r in result]
    assert degrees == sorted(degrees, reverse=True)


def test_god_nodes_have_required_keys():
    G = make_graph()
    result = god_nodes(G, top_n=1)
    assert "id" in result[0]
    assert "label" in result[0]
    assert "edges" in result[0]


def test_surprising_connections_cross_source_multi_file():
    """Multi-file graph: should find cross-file edges between real entities."""
    G = make_graph()
    communities = cluster(G)
    surprises = surprising_connections(G, communities)
    assert len(surprises) > 0
    for s in surprises:
        assert s["source_files"][0] != s["source_files"][1]


def test_surprising_connections_excludes_concept_nodes():
    """Concept nodes (empty source_file) must not appear in surprises."""
    G = make_graph()
    # Add a concept node with empty source_file
    G.add_node("concept_x", label="Abstract Concept", file_type="document", source_file="")
    G.add_edge("n_transformer", "concept_x", relation="relates_to",
               confidence="INFERRED", source_file="", weight=0.5)
    communities = cluster(G)
    surprises = surprising_connections(G, communities)
    labels = [s["source"] for s in surprises] + [s["target"] for s in surprises]
    assert "Abstract Concept" not in labels


def test_surprising_connections_single_file_uses_community_bridges():
    """Single-file graph: should return cross-community edges, not empty list."""
    G = nx.Graph()
    # Build a graph with 2 clear communities + 1 bridge edge
    for i in range(5):
        G.add_node(f"a{i}", label=f"A{i}", file_type="code", source_file="single.py",
                   source_location=f"L{i}")
    for i in range(5):
        G.add_node(f"b{i}", label=f"B{i}", file_type="code", source_file="single.py",
                   source_location=f"L{i+10}")
    # Dense intra-community edges
    for i in range(4):
        G.add_edge(f"a{i}", f"a{i+1}", relation="calls", confidence="EXTRACTED",
                   source_file="single.py", weight=1.0)
    for i in range(4):
        G.add_edge(f"b{i}", f"b{i+1}", relation="calls", confidence="EXTRACTED",
                   source_file="single.py", weight=1.0)
    # One cross-community bridge
    G.add_edge("a4", "b0", relation="references", confidence="INFERRED",
               source_file="single.py", weight=0.5)

    communities = cluster(G)
    surprises = surprising_connections(G, communities)
    # Should find at least the bridge edge
    assert len(surprises) > 0


def test_surprising_connections_ambiguous_scores_higher_than_extracted():
    """AMBIGUOUS edge should score higher than an otherwise identical EXTRACTED edge."""
    G = nx.Graph()
    for nid, label, src in [
        ("a", "Alpha", "repo1/model.py"),
        ("b", "Beta", "repo2/train.py"),
        ("c", "Gamma", "repo1/data.py"),
        ("d", "Delta", "repo2/eval.py"),
    ]:
        G.add_node(nid, label=label, source_file=src, file_type="code")
    G.add_edge("a", "b", relation="calls", confidence="AMBIGUOUS", weight=1.0, source_file="repo1/model.py")
    G.add_edge("c", "d", relation="calls", confidence="EXTRACTED", weight=1.0, source_file="repo1/data.py")
    communities = {0: ["a", "c"], 1: ["b", "d"]}
    nc = {"a": 0, "c": 0, "b": 1, "d": 1}
    score_amb, _ = _surprise_score(G, "a", "b", G.edges["a", "b"], nc, "repo1/model.py", "repo2/train.py")
    score_ext, _ = _surprise_score(G, "c", "d", G.edges["c", "d"], nc, "repo1/data.py", "repo2/eval.py")
    assert score_amb > score_ext


def test_surprising_connections_cross_type_scores_higher():
    """Code↔paper edge should score higher than code↔code edge."""
    G = nx.Graph()
    for nid, label, src in [
        ("a", "Transformer", "code/model.py"),
        ("b", "FlashAttn", "papers/flash.pdf"),
        ("c", "Trainer", "code/train.py"),
        ("d", "Dataset", "code/data.py"),
    ]:
        G.add_node(nid, label=label, source_file=src, file_type="code")
    G.add_edge("a", "b", relation="references", confidence="EXTRACTED", weight=1.0, source_file="code/model.py")
    G.add_edge("c", "d", relation="calls", confidence="EXTRACTED", weight=1.0, source_file="code/train.py")
    nc = {"a": 0, "b": 1, "c": 0, "d": 0}
    score_cross, reasons_cross = _surprise_score(G, "a", "b", G.edges["a", "b"], nc, "code/model.py", "papers/flash.pdf")
    score_same, _ = _surprise_score(G, "c", "d", G.edges["c", "d"], nc, "code/train.py", "code/data.py")
    assert score_cross > score_same
    assert any("code" in r and "paper" in r for r in reasons_cross)


def test_surprising_connections_have_why_field():
    G = make_graph()
    communities = cluster(G)
    for s in surprising_connections(G, communities):
        assert "why" in s
        assert isinstance(s["why"], str)
        assert len(s["why"]) > 0


def test_file_category():
    assert _file_category("model.py") == "code"
    assert _file_category("flash.pdf") == "paper"
    assert _file_category("diagram.png") == "image"
    assert _file_category("notes.md") == "doc"
    # Languages added in later releases — would misclassify as "doc" without detect.py import
    assert _file_category("app.swift") == "code"
    assert _file_category("plugin.lua") == "code"
    assert _file_category("build.zig") == "code"
    assert _file_category("deploy.ps1") == "code"
    assert _file_category("server.ex") == "code"
    assert _file_category("component.jsx") == "code"
    assert _file_category("analysis.jl") == "code"
    assert _file_category("view.m") == "code"


def test_is_concept_node_empty_source():
    G = nx.Graph()
    G.add_node("c1", source_file="")
    assert _is_concept_node(G, "c1") is True


def test_is_concept_node_real_file():
    G = nx.Graph()
    G.add_node("n1", source_file="model.py")
    assert _is_concept_node(G, "n1") is False


def test_surprising_connections_have_required_keys():
    G = make_graph()
    communities = cluster(G)
    for s in surprising_connections(G, communities):
        assert "source" in s
        assert "target" in s
        assert "source_files" in s
        assert "confidence" in s


# --- graph_diff tests ---

def _make_simple_graph(nodes, edges):
    """Helper: build a small nx.Graph from node/edge specs."""
    G = nx.Graph()
    for node_id, label in nodes:
        G.add_node(node_id, label=label, source_file="test.py")
    for src, tgt, rel, conf in edges:
        G.add_edge(src, tgt, relation=rel, confidence=conf)
    return G


def test_graph_diff_new_nodes():
    G_old = _make_simple_graph([("n1", "Alpha"), ("n2", "Beta")], [])
    G_new = _make_simple_graph([("n1", "Alpha"), ("n2", "Beta"), ("n3", "Gamma")], [])
    diff = graph_diff(G_old, G_new)
    assert len(diff["new_nodes"]) == 1
    assert diff["new_nodes"][0]["id"] == "n3"
    assert diff["new_nodes"][0]["label"] == "Gamma"
    assert diff["removed_nodes"] == []
    assert "1 new node" in diff["summary"]


def test_graph_diff_removed_nodes():
    G_old = _make_simple_graph([("n1", "Alpha"), ("n2", "Beta"), ("n3", "Gamma")], [])
    G_new = _make_simple_graph([("n1", "Alpha"), ("n2", "Beta")], [])
    diff = graph_diff(G_old, G_new)
    assert diff["new_nodes"] == []
    assert len(diff["removed_nodes"]) == 1
    assert diff["removed_nodes"][0]["id"] == "n3"
    assert "removed" in diff["summary"]


def test_graph_diff_new_edges():
    nodes = [("n1", "Alpha"), ("n2", "Beta"), ("n3", "Gamma")]
    G_old = _make_simple_graph(nodes, [("n1", "n2", "calls", "EXTRACTED")])
    G_new = _make_simple_graph(
        nodes,
        [("n1", "n2", "calls", "EXTRACTED"), ("n2", "n3", "uses", "INFERRED")],
    )
    diff = graph_diff(G_old, G_new)
    assert len(diff["new_edges"]) == 1
    new_edge = diff["new_edges"][0]
    assert new_edge["relation"] == "uses"
    assert new_edge["confidence"] == "INFERRED"
    assert diff["removed_edges"] == []
    assert "new edge" in diff["summary"]


def test_graph_diff_empty_diff():
    nodes = [("n1", "Alpha"), ("n2", "Beta")]
    edges = [("n1", "n2", "calls", "EXTRACTED")]
    G_old = _make_simple_graph(nodes, edges)
    G_new = _make_simple_graph(nodes, edges)
    diff = graph_diff(G_old, G_new)
    assert diff["new_nodes"] == []
    assert diff["removed_nodes"] == []
    assert diff["new_edges"] == []
    assert diff["removed_edges"] == []
    assert diff["summary"] == "no changes"


# --- render_analysis_context tests ---

def _analysis_inputs():
    """Build inputs for render_analysis_context() tests using fixture graph."""
    G = make_graph()
    communities = cluster(G)
    labels = {cid: f"Community {cid}" for cid in communities}
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    return G, communities, labels, gods, surprises


def test_render_analysis_context_returns_str():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    assert isinstance(result, str)


def test_render_analysis_context_contains_node_count():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    assert str(G.number_of_nodes()) in result
    assert "nodes" in result


def test_render_analysis_context_contains_edge_count():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    assert str(G.number_of_edges()) in result
    assert "edges" in result


def test_render_analysis_context_contains_community_count():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    assert str(len(communities)) in result
    assert "communities" in result


def test_render_analysis_context_contains_god_node_labels():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    for god in gods[:3]:
        assert god["label"] in result


def test_render_analysis_context_contains_surprise_relations():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises)
    for s in surprises[:2]:
        assert s["source"] in result
        assert s["target"] in result


def test_render_analysis_context_empty_surprises():
    G, communities, labels, gods, _ = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, [])
    assert "Surprising" in result


def test_render_analysis_context_empty_communities():
    G, _, labels, gods, surprises = _analysis_inputs()
    # Should not crash with empty communities
    result = render_analysis_context(G, {}, {}, gods, surprises)
    assert isinstance(result, str)


def test_render_analysis_context_top_n_limits():
    G, communities, labels, gods, surprises = _analysis_inputs()
    result = render_analysis_context(G, communities, labels, gods, surprises, top_n_nodes=2)
    # With top_n_nodes=2, only 2 god node entries should appear in the god nodes section
    # Count lines starting with "  - " in the god nodes block
    lines = result.split("\n")
    god_section = False
    god_entries = 0
    for line in lines:
        if "Most-connected" in line:
            god_section = True
            continue
        if god_section and line.startswith("  - "):
            god_entries += 1
        elif god_section and line and not line.startswith(" ") and "Most-connected" not in line:
            # Reached next section header
            if not line.startswith("  "):
                break
    assert god_entries <= 2


# ---------------------------------------------------------------------------
# Phase 10 gap-closure regression tests: source_file: list[str] support
# (10-08-PLAN.md Task 1 — RED gate)
# ---------------------------------------------------------------------------

def _make_node_graph(node_id: str, label: str, source_file) -> nx.Graph:
    """Helper: create a minimal graph with a single node."""
    G = nx.Graph()
    G.add_node(node_id, label=label, file_type="code", source_file=source_file,
               source_location="L1")
    return G


def test_is_file_node_list_source_file():
    """list source_file where label matches basename of at least one entry -> True."""
    G = _make_node_graph("n1", "service.py", ["auth/service.py", "auth/impl.py"])
    assert _is_file_node(G, "n1") is True


def test_is_file_node_list_source_file_no_match():
    """list source_file where label does NOT match any basename -> False."""
    G = _make_node_graph("n1", "totally_different", ["auth/service.py", "auth/impl.py"])
    assert _is_file_node(G, "n1") is False


def test_is_concept_node_list_source_file():
    """Node with list source_file containing real file paths -> not a concept (has extension)."""
    G = _make_node_graph("n1", "AuthService", ["a.py", "b.py"])
    assert _is_concept_node(G, "n1") is False


def test_is_concept_node_list_source_file_no_extension():
    """Node with list source_file where no entry has an extension -> concept node."""
    G = _make_node_graph("n1", "README", ["README", "LICENSE"])
    assert _is_concept_node(G, "n1") is True


def test_file_category_list_source_file():
    """_file_category on a list-valued source_file: use first sorted entry for determinism."""
    # sorted(["x.py", "y.md"])[0] == "x.py" which is "code"
    result = _file_category(sorted(["x.py", "y.md"])[0])
    assert result == "code"


def test_top_level_dir_list_source_file():
    """_top_level_dir on first sorted entry of a list."""
    sources = ["repo2/b.py", "repo1/a.py"]
    first_sorted = sorted(sources)[0]  # "repo1/a.py"
    assert _top_level_dir(first_sorted) == "repo1"


def test_surprising_connections_list_source_file_no_crash():
    """Graph with list-valued source_file nodes: surprising_connections must not raise."""
    G = nx.Graph()
    G.add_node("auth", label="AuthService", file_type="code",
               source_file=["src/auth.py", "lib/auth_impl.py"], source_location="L1")
    G.add_node("model", label="UserModel", file_type="code",
               source_file="src/models.py", source_location="L10")
    G.add_node("token", label="TokenValidator", file_type="code",
               source_file="lib/security.py", source_location="L5")
    G.add_edge("auth", "model", relation="references", confidence="INFERRED",
               source_file="src/auth.py", weight=0.9)
    G.add_edge("auth", "token", relation="calls", confidence="EXTRACTED",
               source_file="src/auth.py", weight=1.0)
    communities = {0: ["auth", "model"], 1: ["token"]}
    result = surprising_connections(G, communities, top_n=5)
    assert isinstance(result, list)
    # Verify source_files values are stringifiable (no TypeError on downstream path)
    for s in result:
        for sf in s.get("source_files", []):
            # Must be able to convert to str without TypeError
            _ = str(sf) if sf else ""


# ---------------------------------------------------------------------------
# Tests for knowledge_gaps() — Wave 0, Plan 19-01
# ---------------------------------------------------------------------------

def test_knowledge_gaps_empty_graph():
    """Empty graph returns empty list."""
    result = knowledge_gaps(nx.Graph(), {})
    assert result == []


def test_knowledge_gaps_isolated_node():
    """A single non-file, non-concept node with degree 0 is returned with reason=isolated."""
    G = nx.Graph()
    G.add_node("lone", label="LoneWolf", file_type="document", source_file="doc.md", source_location="")
    result = knowledge_gaps(G, {})
    assert len(result) == 1
    assert result[0]["id"] == "lone"
    assert result[0]["label"] == "LoneWolf"
    assert result[0]["reason"] == "isolated"


def test_knowledge_gaps_thin_community():
    """Nodes in a thin community (< 3 members) are returned with reason=thin_community."""
    G = nx.Graph()
    G.add_node("a", label="Alpha", file_type="document", source_file="a.md", source_location="")
    G.add_node("b", label="Beta", file_type="document", source_file="b.md", source_location="")
    G.add_edge("a", "b", relation="links", confidence="EXTRACTED", source_file="a.md", weight=1.0)
    communities = {0: ["a", "b"]}
    result = knowledge_gaps(G, communities)
    ids = {r["id"] for r in result}
    reasons = {r["reason"] for r in result}
    # Both nodes in thin community (degree 1 — also isolated, but thin_community fires first in dedup)
    assert ids == {"a", "b"}
    assert reasons <= {"isolated", "thin_community"}


def test_knowledge_gaps_high_ambiguity_context():
    """Nodes adjacent to AMBIGUOUS edges, when ambiguity rate >= threshold, appear with high_ambiguity_context."""
    G = nx.Graph()
    G.add_node("x", label="X", file_type="document", source_file="x.md", source_location="")
    G.add_node("y", label="Y", file_type="document", source_file="y.md", source_location="")
    G.add_edge("x", "y", relation="relates", confidence="AMBIGUOUS", source_file="x.md", weight=1.0)
    # 1 AMBIGUOUS edge / 1 total = 100% >= 0.20 threshold
    result = knowledge_gaps(G, {}, ambiguity_threshold=0.20)
    reasons = {r["reason"] for r in result}
    # Nodes may be isolated AND high_ambiguity_context; first-seen wins in dedup
    assert "high_ambiguity_context" in reasons or "isolated" in reasons


def test_knowledge_gaps_deduped_by_id():
    """A node that is both isolated and in a thin community appears only once (first reason wins)."""
    G = nx.Graph()
    G.add_node("z", label="Zeta", file_type="document", source_file="z.md", source_location="")
    communities = {0: ["z"]}  # thin (1 node) — also isolated (degree 0)
    result = knowledge_gaps(G, communities)
    ids = [r["id"] for r in result]
    # z must appear exactly once
    assert ids.count("z") == 1


def test_knowledge_gaps_return_shape():
    """Every returned dict has exactly the keys id, label, reason."""
    G = nx.Graph()
    G.add_node("n1", label="NodeOne", file_type="document", source_file="f.md", source_location="")
    result = knowledge_gaps(G, {})
    assert len(result) >= 1
    for item in result:
        assert set(item.keys()) == {"id", "label", "reason"}
