from __future__ import annotations
import json
import pytest
import networkx as nx
from networkx.readwrite import json_graph


# ---------------------------------------------------------------------------
# Helpers — build synthetic graphs for tests
# ---------------------------------------------------------------------------

def _make_graph_with_nodes(nodes: list[dict], edges: list[dict] | None = None) -> nx.Graph:
    """Build a NetworkX graph from hand-crafted node/edge dicts."""
    G = nx.Graph()
    for n in nodes:
        nid = n["id"]
        G.add_node(nid, **{k: v for k, v in n.items() if k != "id"})
    for e in (edges or []):
        G.add_edge(e["source"], e["target"], **{k: v for k, v in e.items() if k not in ("source", "target")})
    return G


def _make_communities(G: nx.Graph, mapping: dict[int, list[str]]) -> dict[int, list[str]]:
    """Stamp community attribute onto graph nodes and return the communities dict."""
    for cid, nodes in mapping.items():
        for nid in nodes:
            if nid in G.nodes:
                G.nodes[nid]["community"] = cid
    return mapping


# ---------------------------------------------------------------------------
# Task 2.1 — Graph loader + classifier
# ---------------------------------------------------------------------------

def test_vault03_things_dispatch(tmp_path):
    """Things bucket: god_nodes with file_type != 'code'; code-typed nodes excluded."""
    from graphify.vault_promote import classify_nodes

    G = nx.Graph()
    # High-degree non-code node — should land in Things
    G.add_node("thing1", label="MyClass", file_type="document", source_file="foo.md", community=0)
    # High-degree code node — must NOT land in Things (D-10)
    G.add_node("code1", label="CodeFunc", file_type="code", source_file="src.py", community=0)
    # Add many edges so both qualify as god_nodes (degree >= threshold)
    for i in range(6):
        pivot = f"edge_node_{i}"
        G.add_node(pivot, label=f"N{i}", file_type="document", source_file="foo.md", community=0)
        G.add_edge("thing1", pivot, relation="contains", confidence="EXTRACTED", source_file="foo.md")
        G.add_edge("code1", pivot, relation="calls", confidence="EXTRACTED", source_file="src.py")

    communities = _make_communities(G, {0: ["thing1", "code1"] + [f"edge_node_{i}" for i in range(6)]})
    profile = {}
    threshold = 2

    result = classify_nodes(G, communities, profile, threshold)

    thing_ids = [r["node_id"] for r in result["things"]]
    assert "thing1" in thing_ids, "Non-code god_node must be in Things"
    assert "code1" not in thing_ids, "Code-typed god_node must NOT be in Things (D-10)"


def test_vault03_questions_always_promoted(tmp_path):
    """Questions bypass threshold gate entirely (D-09)."""
    from graphify.vault_promote import classify_nodes
    from graphify.analyze import knowledge_gaps

    G = nx.Graph()
    # Isolated node — will be a knowledge gap
    G.add_node("isolated1", label="OrphanConcept", file_type="document", source_file="x.md", community=0)
    # Tiny community (< 3 members) to trigger thin_community
    G.add_node("nodeA", label="A", file_type="document", source_file="a.md", community=1)
    G.add_node("nodeB", label="B", file_type="document", source_file="b.md", community=1)

    communities = {0: ["isolated1"], 1: ["nodeA", "nodeB"]}
    for cid, nodes in communities.items():
        for nid in nodes:
            G.nodes[nid]["community"] = cid

    # threshold set absurdly high — Questions must still appear
    result = classify_nodes(G, communities, {}, threshold=999)

    question_ids = [r["node_id"] for r in result["questions"]]
    assert len(question_ids) > 0, "Questions must be non-empty even at threshold=999"
    assert "isolated1" in question_ids, "Isolated node must appear in Questions"


def test_vault03_maps_moc_frontmatter(tmp_path):
    """Maps bucket: one record per community; each record has community_id and members."""
    from graphify.vault_promote import classify_nodes

    G = nx.Graph()
    G.add_node("n1", label="Alpha", file_type="document", source_file="a.md", community=0)
    G.add_node("n2", label="Beta", file_type="document", source_file="b.md", community=0)
    G.add_node("n3", label="Gamma", file_type="code", source_file="c.py", community=1)

    communities = {0: ["n1", "n2"], 1: ["n3"]}
    for cid, nodes in communities.items():
        for nid in nodes:
            G.nodes[nid]["community"] = cid

    result = classify_nodes(G, communities, {}, threshold=0)

    maps = result["maps"]
    assert len(maps) == 2, f"Expected 2 Map records (one per community), got {len(maps)}"
    community_ids = {r["community_id"] for r in maps}
    assert community_ids == {0, 1}, f"Map records must cover all community IDs, got {community_ids}"
    # Each record must carry member list
    for rec in maps:
        assert "members" in rec, "Map record must have 'members' field"
        assert isinstance(rec["members"], list)


# ---------------------------------------------------------------------------
# Task 2.2 — Render pipeline (frontmatter + templates + tags + taxonomy)
# ---------------------------------------------------------------------------

def _make_render_graph() -> tuple[nx.Graph, dict[int, list[str]]]:
    """Build a small graph for render pipeline tests."""
    G = nx.Graph()
    G.add_node("main_node", label="MainNode", file_type="document", source_file="notes/main.md", community=0)
    G.add_node("extracted_peer", label="ExtractedPeer", file_type="document", source_file="notes/peer.md", community=0)
    G.add_node("inferred_peer", label="InferredPeer", file_type="document", source_file="notes/other.md", community=0)
    G.add_node("code_node", label="CodeHelper", file_type="code", source_file="src/helper.py", community=1)

    G.add_edge("main_node", "extracted_peer",
               relation="references", confidence="EXTRACTED", source_file="notes/main.md", weight=1.0)
    G.add_edge("main_node", "inferred_peer",
               relation="semantically_similar_to", confidence="INFERRED", source_file="notes/main.md",
               confidence_score=0.7, weight=1.0)
    G.add_edge("code_node", "main_node",
               relation="imports", confidence="EXTRACTED", source_file="src/helper.py", weight=1.0)

    communities = {0: ["main_node", "extracted_peer", "inferred_peer"], 1: ["code_node"]}
    for cid, nodes in communities.items():
        for nid in nodes:
            G.nodes[nid]["community"] = cid

    return G, communities


def test_vault02_frontmatter_has_required_fields(tmp_path):
    """Rendered frontmatter must contain all required Ideaverse fields."""
    from graphify.vault_promote import render_note, classify_nodes
    from graphify.profile import load_profile

    G, communities = _make_render_graph()
    profile = load_profile(None)
    threshold = 0

    # Create a Thing-like record manually
    record = {
        "node_id": "main_node",
        "label": "MainNode",
        "folder": "Atlas/Dots/Things/",
        "score": G.degree("main_node"),
    }
    run_meta = {"project": "test-project", "run_id": "2026-04-23T00:00:00Z", "threshold": threshold}

    filename_stem, rendered = render_note(record, "Things", G, profile, run_meta)

    assert "---" in rendered, "Frontmatter delimiters must be present"
    assert "up:" in rendered
    assert "created:" in rendered
    assert "graphifyProject:" in rendered
    assert "graphifyRun:" in rendered
    assert "graphifyScore:" in rendered
    assert "graphifyThreshold:" in rendered
    assert "tags:" in rendered


def test_vault02_frontmatter_tags_namespaces(tmp_path):
    """Every rendered note must have at least one tag from garden/, source/, graph/."""
    import re
    from graphify.vault_promote import render_note
    from graphify.profile import load_profile

    G, communities = _make_render_graph()
    profile = load_profile(None)

    record = {
        "node_id": "main_node",
        "label": "MainNode",
        "folder": "Atlas/Dots/Things/",
        "score": G.degree("main_node"),
    }
    run_meta = {"project": "test-proj", "run_id": "2026-04-23T00:00:00Z", "threshold": 0}

    _, rendered = render_note(record, "Things", G, profile, run_meta)

    # Extract tags from frontmatter
    tags = re.findall(r"^\s+- (.+)$", rendered, re.MULTILINE)
    namespaces = {t.split("/")[0] for t in tags if "/" in t}
    for ns in ("garden", "source", "graph"):
        assert ns in namespaces, f"Expected tag namespace '{ns}/' missing. Tags found: {tags}"


def test_vault04_related_extracted_only(tmp_path):
    """related: field must contain ONLY EXTRACTED-confidence neighbors (D-21 / VAULT-04)."""
    from graphify.vault_promote import render_note
    from graphify.profile import load_profile

    G, communities = _make_render_graph()
    profile = load_profile(None)

    record = {
        "node_id": "main_node",
        "label": "MainNode",
        "folder": "Atlas/Dots/Things/",
        "score": G.degree("main_node"),
    }
    run_meta = {"project": "test-proj", "run_id": "2026-04-23T00:00:00Z", "threshold": 0}

    _, rendered = render_note(record, "Things", G, profile, run_meta)

    # InferredPeer must NOT appear in related:
    assert "InferredPeer" not in rendered or _only_in_body(rendered, "InferredPeer"), \
        "INFERRED edge neighbor must not appear in related: frontmatter field"
    # ExtractedPeer MUST appear somewhere in related:
    assert "ExtractedPeer" in rendered, \
        "EXTRACTED edge neighbor must appear in related: frontmatter field"


def _only_in_body(rendered: str, label: str) -> bool:
    """Return True if the label only appears in the markdown body (after second ---)."""
    parts = rendered.split("---", 2)
    if len(parts) < 3:
        return False
    body = parts[2]
    return label in body


def test_vault07_tag_taxonomy_layer_merge(tmp_path):
    """Layer-3 tech detection: .py source_file contributes tech/python to taxonomy."""
    from graphify.vault_promote import resolve_taxonomy, _detect_tech_tags
    from graphify.profile import load_profile

    G = nx.Graph()
    G.add_node("py_node", label="PythonHelper", file_type="code", source_file="src/helper.py", community=0)
    G.add_node("ts_node", label="TSComponent", file_type="code", source_file="ui/App.tsx", community=0)
    G.add_node("no_ext", label="NoConcept", file_type="document", source_file="", community=0)

    communities = {0: ["py_node", "ts_node", "no_ext"]}
    for cid, nodes in communities.items():
        for nid in nodes:
            G.nodes[nid]["community"] = cid

    profile = load_profile(None)
    taxonomy = resolve_taxonomy(G, profile)

    assert "tech" in taxonomy, "Taxonomy must have tech namespace after Layer-3 merge"
    tech_tags = taxonomy["tech"]
    assert "python" in tech_tags, f"python must be in tech tags; got {tech_tags}"
    assert "typescript" in tech_tags, f"typescript must be in tech tags for .tsx; got {tech_tags}"


def test_vault03_maps_moc_frontmatter_rendered(tmp_path):
    """Map MOC rendered frontmatter has stateMaps: 🟥 and NO related: key."""
    from graphify.vault_promote import render_note
    from graphify.profile import load_profile

    G, communities = _make_render_graph()
    profile = load_profile(None)

    map_record = {
        "community_id": 0,
        "label": "Community 0",
        "folder": "Atlas/Maps/",
        "score": 0,
        "members": ["main_node", "extracted_peer", "inferred_peer"],
    }
    run_meta = {"project": "test-proj", "run_id": "2026-04-23T00:00:00Z", "threshold": 0}

    _, rendered = render_note(map_record, "Maps", G, profile, run_meta)

    assert "stateMaps" in rendered, "Map MOC must have stateMaps field"
    assert "🟥" in rendered, "Map MOC must have 🟥 emoji"

    # Extract frontmatter block (between first --- and second ---)
    parts = rendered.split("---", 2)
    assert len(parts) >= 3
    frontmatter_block = parts[1]
    assert "related:" not in frontmatter_block, "Maps must NOT have related: in frontmatter"


def test_vault_no_leftover_template_tokens(tmp_path):
    """Rendered notes must not contain leftover ${...} template tokens (Pitfall 8)."""
    from graphify.vault_promote import render_note
    from graphify.profile import load_profile

    G, communities = _make_render_graph()
    profile = load_profile(None)

    records_and_types = [
        ({"node_id": "main_node", "label": "MainNode", "folder": "Atlas/Dots/Things/", "score": 2}, "Things"),
        ({"community_id": 0, "label": "Community 0", "folder": "Atlas/Maps/", "score": 0,
          "members": ["main_node"]}, "Maps"),
    ]
    run_meta = {"project": "test-proj", "run_id": "2026-04-23T00:00:00Z", "threshold": 0}

    for record, folder_type in records_and_types:
        _, rendered = render_note(record, folder_type, G, profile, run_meta)
        assert "${" not in rendered, \
            f"Leftover template token found in {folder_type} note:\n{rendered}"


# ---------------------------------------------------------------------------
# Write-phase tests (Plan 03 / Plan 04) — remain skipped
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Plan 03 implements vault writes")
def test_vault01_cli_does_not_overwrite_foreign(tmp_path): ...

@pytest.mark.skip(reason="Plan 03 implements vault writes")
def test_vault01_write_decision_table(tmp_path): ...

@pytest.mark.skip(reason="Plan 03 implements vault writes")
def test_vault05_import_log_written(tmp_path): ...

@pytest.mark.skip(reason="Plan 03 implements vault writes")
def test_vault05_import_log_append_latest_first(tmp_path): ...

@pytest.mark.skip(reason="Plan 04 implements profile writeback")
def test_vault06_profile_writeback_union_merge(tmp_path): ...

@pytest.mark.skip(reason="Plan 04 implements profile writeback")
def test_vault06_profile_writeback_opt_out(tmp_path): ...
