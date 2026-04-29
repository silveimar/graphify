import json
import tempfile
from pathlib import Path
import networkx as nx
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_json, to_cypher, to_graphml, to_html

FIXTURES = Path(__file__).parent / "fixtures"

def make_graph():
    return build_from_json(json.loads((FIXTURES / "extraction.json").read_text()))

def test_to_json_creates_file():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.json"
        to_json(G, communities, str(out))
        assert out.exists()

def test_to_json_valid_json():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.json"
        to_json(G, communities, str(out))
        data = json.loads(out.read_text())
        assert "nodes" in data
        assert "links" in data

def test_to_json_nodes_have_community():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.json"
        to_json(G, communities, str(out))
        data = json.loads(out.read_text())
        for node in data["nodes"]:
            assert "community" in node

def test_to_cypher_creates_file():
    G = make_graph()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cypher.txt"
        to_cypher(G, str(out))
        assert out.exists()

def test_to_cypher_contains_merge_statements():
    G = make_graph()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cypher.txt"
        to_cypher(G, str(out))
        content = out.read_text()
        assert "MERGE" in content

def test_to_graphml_creates_file():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.graphml"
        to_graphml(G, communities, str(out))
        assert out.exists()

def test_to_graphml_valid_xml():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.graphml"
        to_graphml(G, communities, str(out))
        content = out.read_text()
        assert "<graphml" in content
        assert "<node" in content

def test_to_graphml_has_community_attribute():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.graphml"
        to_graphml(G, communities, str(out))
        content = out.read_text()
        assert "community" in content

def test_to_html_creates_file():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out))
        assert out.exists()

def test_to_html_contains_visjs():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out))
        content = out.read_text()
        assert "vis-network" in content

def test_to_html_contains_search():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out))
        content = out.read_text()
        assert "search" in content.lower()

def test_to_html_contains_legend_with_labels():
    G = make_graph()
    communities = cluster(G)
    labels = {cid: f"Group {cid}" for cid in communities}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out), community_labels=labels)
        content = out.read_text()
        assert "Group 0" in content

def test_to_html_contains_nodes_and_edges():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out))
        content = out.read_text()
        assert "RAW_NODES" in content
        assert "RAW_EDGES" in content


# ---------------------------------------------------------------------------
# Phase 10 Plan 07: obsidian_dedup wiring (D-15)
# ---------------------------------------------------------------------------

def test_to_obsidian_obsidian_dedup_hydrates_merged_from(tmp_path):
    """--obsidian-dedup populates G.nodes[canonical]['merged_from'] from dedup_report.json."""
    from graphify.export import to_obsidian
    import networkx as nx
    import json

    G = nx.Graph()
    G.add_node("authservice", label="AuthService", file_type="code",
               source_file="a.py", community=0)
    # graphify-out/ layout: dedup_report.json lives as sibling of obsidian/
    out_root = tmp_path / "graphify-out"
    out_root.mkdir()
    obsidian_dir = out_root / "obsidian"
    obsidian_dir.mkdir()
    report = {
        "version": "1",
        "alias_map": {"auth": "authservice"},
        "merges": [{
            "canonical_id": "authservice",
            "canonical_label": "AuthService",
            "eliminated": [{"id": "auth", "label": "auth", "source_file": "b.py"}],
            "fuzzy_score": 0.95,
            "cosine_score": 0.90,
        }],
    }
    (out_root / "dedup_report.json").write_text(json.dumps(report), encoding="utf-8")

    result = to_obsidian(
        G,
        communities={0: ["authservice"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
        obsidian_dedup=True,
    )
    # After hydration, the node's merged_from list must include 'auth'
    assert "auth" in G.nodes["authservice"].get("merged_from", [])


def test_to_obsidian_default_no_dedup_hydration(tmp_path):
    """Backward compat: default obsidian_dedup=False leaves merged_from untouched."""
    from graphify.export import to_obsidian
    import networkx as nx

    G = nx.Graph()
    G.add_node("foo", label="Foo", file_type="code", source_file="a.py", community=0)
    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()
    to_obsidian(
        G,
        communities={0: ["foo"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
    )
    assert "merged_from" not in G.nodes["foo"]


def test_to_obsidian_no_profile_dry_run_uses_graphify_default_paths(tmp_path):
    from graphify.export import to_obsidian
    import networkx as nx

    G = nx.Graph()
    G.add_node(
        "transformer",
        label="Transformer",
        file_type="code",
        source_file="model.py",
        source_location="L1",
        community=0,
    )
    G.add_node(
        "softmax",
        label="Softmax",
        file_type="code",
        source_file="model.py",
        source_location="L2",
        community=0,
    )
    G.add_edge("transformer", "softmax", relation="calls", confidence="EXTRACTED")
    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()

    plan = to_obsidian(
        G,
        communities={0: ["transformer", "softmax"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
    )

    relative_paths = [
        action.path.relative_to(obsidian_dir).as_posix()
        for action in plan.actions
        if action.action == "CREATE"
    ]
    assert relative_paths
    assert all(path.startswith("Atlas/Sources/Graphify/") for path in relative_paths)
    assert any(path.startswith("Atlas/Sources/Graphify/MOCs/") for path in relative_paths)


def _phase33_graph():
    G = nx.Graph()
    G.add_node(
        "n_auth_session",
        label="Auth Session",
        file_type="code",
        source_file="auth/session.py",
        source_location="L10",
        community=0,
    )
    G.add_node(
        "n_refresh_token",
        label="Refresh Token",
        file_type="code",
        source_file="auth/tokens.py",
        source_location="L20",
        community=0,
    )
    G.add_node(
        "n_login_flow",
        label="Login Flow",
        file_type="document",
        source_file="docs/login.md",
        source_location="L1",
        community=0,
    )
    G.add_edges_from([
        ("n_auth_session", "n_refresh_token"),
        ("n_auth_session", "n_login_flow"),
    ])
    return G, {0: ["n_auth_session", "n_refresh_token", "n_login_flow"]}


def test_to_obsidian_resolves_concept_names_for_moc_paths(tmp_path):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"

    plan = to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        community_labels={0: "Authentication Session Flow"},
        dry_run=True,
    )

    created = [action for action in plan.actions if action.action == "CREATE"]
    assert created
    moc_paths = [action.path.relative_to(obsidian_dir).as_posix() for action in created]
    assert any(
        "Atlas/Sources/Graphify/MOCs/Authentication_Session_Flow.md" in path
        for path in moc_paths
    )


def test_to_obsidian_dry_run_does_not_write_naming_sidecar(tmp_path):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        community_labels={0: "Authentication Session Flow"},
        dry_run=True,
    )

    assert not (out_root / "concept-names.json").exists()
