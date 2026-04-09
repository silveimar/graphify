import json
import tempfile
from pathlib import Path
import networkx as nx
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_json, to_cypher, to_graphml, to_html, to_obsidian, to_canvas

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
# Helper to build a small graph for obsidian/canvas tests
# ---------------------------------------------------------------------------

def _make_small_graph(nodes=None):
    """Create a minimal nx.Graph with controllable node attributes."""
    G = nx.Graph()
    if nodes is None:
        nodes = [
            ("n1", {"label": "Alpha", "file_type": "code", "source_file": "a.py", "source_location": "L1"}),
            ("n2", {"label": "Beta", "file_type": "document", "source_file": "b.md", "source_location": "L5"}),
        ]
    for node_id, attrs in nodes:
        G.add_node(node_id, **attrs)
    # Add an edge so community detection works
    if len(nodes) >= 2:
        G.add_edge(nodes[0][0], nodes[1][0], relation="references", confidence="EXTRACTED", source_file="a.py", weight=1.0)
    return G


# ---------------------------------------------------------------------------
# FIX-01: Frontmatter values with special characters are properly quoted
# ---------------------------------------------------------------------------

def test_to_obsidian_frontmatter_special_chars():
    G = _make_small_graph([
        ("n1", {"label": "My#Class", "file_type": "code", "source_file": "C:\\path:file.py", "source_location": "L42"}),
        ("n2", {"label": "Other", "file_type": "code", "source_file": "other.py", "source_location": "L1"}),
    ])
    communities = {0: ["n1", "n2"]}
    labels = {0: "Test Community"}
    with tempfile.TemporaryDirectory() as tmp:
        to_obsidian(G, communities, tmp, community_labels=labels)
        # Find the file for n1 — label "My#Class" has # stripped by safe_filename → "MyClass"
        md_files = list(Path(tmp).glob("*.md"))
        node_files = [f for f in md_files if not f.name.startswith("_COMMUNITY_")]
        # Read all node files, find the one with C:\path:file.py in frontmatter
        found = False
        for f in node_files:
            content = f.read_text(encoding="utf-8")
            if "path" in content and "file.py" in content:
                found = True
                # The colon in C:\path:file.py should be quoted
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("source_file:"):
                        # safe_frontmatter_value should have wrapped in quotes due to colon
                        assert '"' in line, f"source_file with colon should be quoted: {line}"
                        break
                break
        assert found, "Node file with special source_file not found"


# ---------------------------------------------------------------------------
# FIX-02: Filename deduplication is deterministic across re-runs
# ---------------------------------------------------------------------------

def test_to_obsidian_dedup_deterministic():
    nodes = [
        ("n1", {"label": "Widget", "file_type": "code", "source_file": "a.py"}),
        ("n2", {"label": "Widget", "file_type": "code", "source_file": "b.py"}),
        ("n3", {"label": "Widget", "file_type": "code", "source_file": "c.py"}),
    ]
    G = _make_small_graph(nodes)
    # Add edges to make it a connected graph
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED", source_file="a.py", weight=1.0)
    G.add_edge("n2", "n3", relation="calls", confidence="EXTRACTED", source_file="b.py", weight=1.0)
    communities = {0: ["n1", "n2", "n3"]}
    labels = {0: "Widgets"}

    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        to_obsidian(G, communities, tmp1, community_labels=labels)
        to_obsidian(G, communities, tmp2, community_labels=labels)

        files1 = sorted(f.name for f in Path(tmp1).glob("*.md") if not f.name.startswith("_COMMUNITY_"))
        files2 = sorted(f.name for f in Path(tmp2).glob("*.md") if not f.name.startswith("_COMMUNITY_"))
        assert files1 == files2, f"Dedup not deterministic: {files1} vs {files2}"
        # Should have Widget.md, Widget_1.md, Widget_2.md (or similar suffixed names)
        assert len(files1) == 3


# ---------------------------------------------------------------------------
# FIX-03: Community tag sanitization
# ---------------------------------------------------------------------------

def test_to_obsidian_tag_sanitization():
    G = _make_small_graph()
    communities = {0: ["n1", "n2"]}
    labels = {0: "ML/AI + Data"}
    with tempfile.TemporaryDirectory() as tmp:
        to_obsidian(G, communities, tmp, community_labels=labels)
        # Read any node file and check tag
        node_files = [f for f in Path(tmp).glob("*.md") if not f.name.startswith("_COMMUNITY_")]
        assert len(node_files) > 0
        content = node_files[0].read_text(encoding="utf-8")
        # Tag should be slugified — no / + or spaces in the tag itself
        # The tag line should be like "  - community/ml-ai-data"
        found_comm_tag = False
        for line in content.split("\n"):
            if "community/" in line and line.strip().startswith("- "):
                tag_part = line.strip().lstrip("- ")
                # Extract the part after "community/"
                slug = tag_part.split("community/")[1] if "community/" in tag_part else ""
                assert "/" not in slug, f"Tag slug contains slash: {slug}"
                assert "+" not in slug, f"Tag slug contains plus: {slug}"
                assert " " not in slug, f"Tag slug contains space: {slug}"
                found_comm_tag = True
                break
        assert found_comm_tag, "Community tag not found in frontmatter"


# ---------------------------------------------------------------------------
# OBS-01: graph.json uses tag:community/ syntax (no # after tag:)
# ---------------------------------------------------------------------------

def test_graph_json_tag_syntax():
    G = _make_small_graph()
    communities = {0: ["n1", "n2"]}
    labels = {0: "Test Group"}
    with tempfile.TemporaryDirectory() as tmp:
        to_obsidian(G, communities, tmp, community_labels=labels)
        graph_json_path = Path(tmp) / ".obsidian" / "graph.json"
        assert graph_json_path.exists(), "graph.json not created"
        data = json.loads(graph_json_path.read_text(encoding="utf-8"))
        color_groups = data.get("colorGroups", [])
        assert len(color_groups) > 0, "No colorGroups in graph.json"
        for group in color_groups:
            query = group.get("query", "")
            assert query.startswith("tag:community/"), f"Wrong tag syntax: {query}"
            assert "tag:#" not in query, f"Old tag:#community syntax found: {query}"


# ---------------------------------------------------------------------------
# OBS-02: graph.json read-merge-write preserves user settings
# ---------------------------------------------------------------------------

def test_graph_json_preserves_user_settings():
    G = _make_small_graph()
    communities = {0: ["n1", "n2"]}
    labels = {0: "Test Group"}

    with tempfile.TemporaryDirectory() as tmp:
        # Pre-populate .obsidian/graph.json with user content
        obsidian_dir = Path(tmp) / ".obsidian"
        obsidian_dir.mkdir(parents=True)
        pre_existing = {
            "colorGroups": [
                {"query": "tag:custom/mine", "color": {"a": 1, "rgb": 255}},
                {"query": "tag:community/old-graphify-entry", "color": {"a": 1, "rgb": 0}},
            ],
            "search": {"query": "some user setting"},
        }
        (obsidian_dir / "graph.json").write_text(json.dumps(pre_existing), encoding="utf-8")

        # Run to_obsidian
        to_obsidian(G, communities, tmp, community_labels=labels)

        data = json.loads((obsidian_dir / "graph.json").read_text(encoding="utf-8"))

        # (a) User's custom entry preserved
        queries = [g["query"] for g in data["colorGroups"]]
        assert "tag:custom/mine" in queries, "User custom entry lost"

        # (b) New community entries added
        community_entries = [q for q in queries if q.startswith("tag:community/")]
        assert len(community_entries) >= 1, "No new community entries"

        # (c) Old graphify community entry removed (not duplicated)
        assert "tag:community/old-graphify-entry" not in queries, "Old graphify entry not removed"

        # (d) Other user settings preserved
        assert data.get("search", {}).get("query") == "some user setting"
