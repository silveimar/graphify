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
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["naming"]["concept_names"]["budget"] = 1.0
    profile["mapping"]["min_community_size"] = 1

    plan = to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
        concept_namer=lambda _payload: "Authentication Session Flow",
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
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["naming"]["concept_names"]["budget"] = 1.0

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
        concept_namer=lambda _payload: "Authentication Session Flow",
        dry_run=True,
    )

    assert not (out_root / "concept-names.json").exists()


def test_to_obsidian_profile_repo_identity_records_sidecar(tmp_path):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = {
        "repo": {"identity": "profile-repo"},
        "naming": {"concept_names": {"enabled": False}},
    }

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
    )

    payload = json.loads((out_root / "repo-identity.json").read_text(encoding="utf-8"))
    assert payload["identity"] == "profile-repo"
    assert payload["source"] == "profile"
    assert payload["raw_value"] == "profile-repo"
    assert payload["warnings"] == []


def test_to_obsidian_fallback_repo_identity_records_sidecar(tmp_path, monkeypatch):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    project = tmp_path / "my-project"
    project.mkdir()
    monkeypatch.chdir(project)
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile={"naming": {"concept_names": {"enabled": False}}},
    )

    payload = json.loads((out_root / "repo-identity.json").read_text(encoding="utf-8"))
    assert payload["identity"] == "my-project"
    assert payload["source"] == "fallback-directory"
    assert payload["raw_value"] == "my-project"
    assert payload["warnings"] == []


def _code_paths_from_plan(plan, obsidian_dir: Path) -> list[str]:
    return sorted(
        action.path.relative_to(obsidian_dir).as_posix()
        for action in plan.actions
        if action.action == "CREATE" and action.path.name.startswith("CODE_")
    )


def test_to_obsidian_dry_run_uses_repo_prefixed_code_paths(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["repo"] = {"identity": "graphify"}
    profile["naming"]["concept_names"]["enabled"] = False

    plan = to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
        dry_run=True,
    )

    relative_paths = [
        action.path.relative_to(obsidian_dir).as_posix()
        for action in plan.actions
        if action.action == "CREATE"
    ]
    code_paths = _code_paths_from_plan(plan, obsidian_dir)

    assert code_paths
    assert any(path.endswith("CODE_graphify_Auth_Session.md") for path in code_paths)
    assert not any("_COMMUNITY_" in path for path in relative_paths)


def test_code_notes_record_repo_identity_in_frontmatter_tags_and_manifest(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["repo"] = {"identity": "Graphify"}
    profile["naming"]["concept_names"]["enabled"] = False
    profile["mapping"]["min_community_size"] = 1

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
    )

    code_note = next(obsidian_dir.rglob("CODE_graphify_Auth_Session.md"))
    assert "CODE_graphify_" in code_note.stem
    text = code_note.read_text(encoding="utf-8")
    assert "repo: graphify" in text
    assert "repo/graphify" in text

    manifest = json.loads((out_root / "vault-manifest.json").read_text(encoding="utf-8"))
    rel_key = code_note.relative_to(obsidian_dir).as_posix()
    assert manifest[rel_key]["repo_identity"] == "graphify"
    assert manifest["__graphify_run__"]["manifest_version"] == 2
    assert manifest["__graphify_run__"]["repo_identity"] == "graphify"


def test_to_obsidian_code_note_links_to_final_concept_label(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["repo"] = {"identity": "graphify"}
    profile["naming"]["concept_names"]["enabled"] = False
    profile["mapping"]["min_community_size"] = 1

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
        community_labels={0: "Auth Concepts"},
    )

    code_note = next(obsidian_dir.rglob("CODE_graphify_Auth_Session.md"))
    text = code_note.read_text(encoding="utf-8")
    assert "up:" in text
    assert "[[Auth_Concepts|Auth Concepts]]" in text
    assert "Auth Session c" not in text


def test_to_obsidian_bucketed_code_note_links_to_unclassified(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    G = nx.Graph()
    G.add_node(
        "n_orphan",
        label="Orphan Service",
        file_type="code",
        source_file="src/orphan.py",
        source_location="L1",
        community=0,
    )
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["repo"] = {"identity": "graphify"}
    profile["naming"]["concept_names"]["enabled"] = False

    to_obsidian(
        G,
        {0: ["n_orphan"]},
        output_dir=str(obsidian_dir),
        profile=profile,
    )

    code_note = next(obsidian_dir.rglob("CODE_graphify_Orphan_Service.md"))
    text = code_note.read_text(encoding="utf-8")
    assert "[[Unclassified|_Unclassified]]" in text


def _code_collision_graph(order: str) -> tuple[nx.Graph, dict[int, list[str]]]:
    G = nx.Graph()
    nodes = [
        (
            "n_auth_service",
            {
                "label": "Auth Service",
                "file_type": "code",
                "source_file": "src/auth/service.py",
                "source_location": "L10",
                "community": 0,
            },
        ),
        (
            "n_auth_service_duplicate",
            {
                "label": "Auth_Service",
                "file_type": "code",
                "source_file": "lib/auth/service.py",
                "source_location": "L20",
                "community": 0,
            },
        ),
        (
            "n_login_flow",
            {
                "label": "Login Flow",
                "file_type": "document",
                "source_file": "docs/login.md",
                "source_location": "L1",
                "community": 0,
            },
        ),
    ]
    if order == "reversed":
        nodes = list(reversed(nodes))
    for node_id, attrs in nodes:
        G.add_node(node_id, **attrs)
    G.add_edges_from([
        ("n_auth_service", "n_auth_service_duplicate"),
        ("n_auth_service", "n_login_flow"),
        ("n_auth_service_duplicate", "n_login_flow"),
    ])
    return G, {0: ["n_auth_service", "n_auth_service_duplicate", "n_login_flow"]}


def test_to_obsidian_code_collision_paths_are_order_independent(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["repo"] = {"identity": "graphify"}
    profile["naming"]["concept_names"]["enabled"] = False

    forward_graph, communities = _code_collision_graph("forward")
    forward_dir = tmp_path / "forward" / "obsidian"
    forward = to_obsidian(
        forward_graph,
        communities,
        output_dir=str(forward_dir),
        profile=profile,
        dry_run=True,
    )

    reversed_graph, reversed_communities = _code_collision_graph("reversed")
    reversed_dir = tmp_path / "reversed" / "obsidian"
    reversed_plan = to_obsidian(
        reversed_graph,
        reversed_communities,
        output_dir=str(reversed_dir),
        profile=profile,
        dry_run=True,
    )

    forward_basenames = sorted(Path(path).name for path in _code_paths_from_plan(forward, forward_dir))
    reversed_basenames = sorted(Path(path).name for path in _code_paths_from_plan(reversed_plan, reversed_dir))

    assert forward_basenames == reversed_basenames
    assert len(forward_basenames) == 2
    assert all(name.startswith("CODE_graphify_Auth_Service_") for name in forward_basenames)
    assert all(name.endswith(".md") for name in forward_basenames)


# ---- Phase 65-01: schema_version emission in to_json (CCONF-05) ----

def test_to_json_emits_schema_version(tmp_path):
    """Fresh writes via to_json must include schema_version='1.13' at top level."""
    G = nx.Graph()
    G.add_node("n1", label="A", file_type="code", source_file="a.py")
    G.add_node("n2", label="B", file_type="code", source_file="b.py")
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED",
               source_file="a.py", weight=1.0)
    out = tmp_path / "out.json"
    to_json(G, {}, str(out))
    data = json.loads(out.read_text())
    assert data.get("schema_version") == "2.0"


def test_to_json_round_trips_g_graph_attr(tmp_path):
    """If G.graph['schema_version'] is set, to_json must preserve it (no overwrite)."""
    G = nx.Graph()
    G.graph["schema_version"] = "1.12"
    G.add_node("n1", label="A", file_type="code", source_file="a.py")
    G.add_node("n2", label="B", file_type="code", source_file="b.py")
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED",
               source_file="a.py", weight=1.0)
    out = tmp_path / "out.json"
    to_json(G, {}, str(out))
    data = json.loads(out.read_text())
    assert data.get("schema_version") == "1.12"


# ---------------------------------------------------------------------------
# Phase 71-04 Task 3: temporal field round-trip across export formats
# ---------------------------------------------------------------------------


def _temporal_graph():
    """Two-node graph with two edges: one current (valid_until=None), one superseded."""
    G = nx.Graph()
    G.graph["schema_version"] = "2.0"
    G.add_node("a", label="A", file_type="code", source_file="f1.py")
    G.add_node("b", label="B", file_type="code", source_file="f1.py")
    G.add_node("c", label="C", file_type="code", source_file="f1.py")
    G.add_edge("a", "b",
               relation="calls", confidence="INFERRED", source_file="f1.py",
               weight=1.0,
               valid_from="2026-01-01T00:00:00+00:00",
               valid_until=None,
               decay_weight=0.85)
    G.add_edge("a", "c",
               relation="references", confidence="INFERRED", source_file="f1.py",
               weight=1.0,
               valid_from="2025-06-01T00:00:00+00:00",
               valid_until="2026-04-01T00:00:00+00:00",
               decay_weight=0.4)
    return G


def test_json_temporal_roundtrip(tmp_path):
    """to_json round-trips valid_from / valid_until / decay_weight on every edge."""
    G = _temporal_graph()
    out = tmp_path / "graph.json"
    to_json(G, {}, str(out))
    data = json.loads(out.read_text())
    by_pair = {tuple(sorted([lk["source"], lk["target"]])): lk for lk in data["links"]}
    cur = by_pair[("a", "b")]
    sup = by_pair[("a", "c")]
    assert cur["valid_from"] == "2026-01-01T00:00:00+00:00"
    assert cur["valid_until"] is None
    assert cur["decay_weight"] == 0.85
    assert sup["valid_until"] == "2026-04-01T00:00:00+00:00"
    assert sup["decay_weight"] == 0.4


def test_schema_version_propagates_via_export(tmp_path):
    G = _temporal_graph()
    out = tmp_path / "graph.json"
    to_json(G, {}, str(out))
    data = json.loads(out.read_text())
    assert data["schema_version"] == "2.0"


def test_graphml_none_sanitized(tmp_path):
    """Pitfall 4: edge with valid_until=None must NOT raise on nx.write_graphml,
    AND the written file must NOT carry a valid_until attr for that edge."""
    G = _temporal_graph()
    out = tmp_path / "graph.graphml"
    to_graphml(G, {}, str(out))
    H = nx.read_graphml(str(out))
    found_current = False
    found_superseded = False
    for _u, _v, data in H.edges(data=True):
        if data.get("relation") == "calls":
            assert "valid_until" not in data, f"valid_until=None leaked into graphml: {data}"
            found_current = True
        elif data.get("relation") == "references":
            assert data.get("valid_until") == "2026-04-01T00:00:00+00:00"
            found_superseded = True
    assert found_current and found_superseded


def test_graphml_iso_string_preserved(tmp_path):
    """Edges with valid_until=ISO string round-trip through GraphML."""
    G = _temporal_graph()
    out = tmp_path / "graph.graphml"
    to_graphml(G, {}, str(out))
    H = nx.read_graphml(str(out))
    for _u, _v, data in H.edges(data=True):
        if data.get("relation") == "references":
            assert data["valid_until"] == "2026-04-01T00:00:00+00:00"


def test_cypher_temporal_quoted(tmp_path):
    """to_cypher: ISO timestamps quoted; valid_until=None → Cypher null literal."""
    G = _temporal_graph()
    out = tmp_path / "graph.cypher"
    to_cypher(G, str(out))
    text = out.read_text(encoding="utf-8")
    assert "valid_until: null" in text
    assert "valid_until: '2026-04-01T00:00:00+00:00'" in text
    assert "valid_from: '2026-01-01T00:00:00+00:00'" in text
    assert "valid_from: '2025-06-01T00:00:00+00:00'" in text


def test_obsidian_no_edge_frontmatter_change(tmp_path):
    """Regression guard: to_obsidian still renders nodes (not edges) in frontmatter.

    Historical relations are rendered by wiki.py in Plan 71-05, not here."""
    from graphify.export import to_obsidian
    G = _temporal_graph()
    communities = {0: ["a", "b", "c"]}
    out = tmp_path / "vault"
    out.mkdir()
    try:
        to_obsidian(G, communities, str(out))
    except Exception:
        return
    for md in out.rglob("*.md"):
        parts = md.read_text(encoding="utf-8").split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            assert "valid_until:" not in frontmatter
            assert "decay_weight:" not in frontmatter


# ---------------------------------------------------------------------------
# Phase 72-04 (REAS-04, D-15) Obsidian frontmatter reasoning_relations
# ---------------------------------------------------------------------------


def test_obsidian_reasoning_relations_frontmatter(tmp_path):
    """to_obsidian emits a `reasoning_relations` YAML list in the per-node
    frontmatter when the node has outbound REASONING_RELATIONS edges; nodes
    without such edges have no `reasoning_relations` key.

    Items are JSON-encoded scalar strings (T-72-12: pre-coerced to
    str/float, then JSON-encoded — defense against YAML object injection).
    """
    from graphify.export import to_obsidian
    from graphify.merge import split_rendered_note
    import networkx as nx
    import json

    G = nx.Graph()
    G.add_node("doc_a", label="Doc A", file_type="document",
               source_file="a.md", community=0)
    G.add_node("doc_b", label="Doc B", file_type="document",
               source_file="b.md", community=0)
    G.add_node("doc_c", label="ADR-0028", file_type="document",
               source_file="c.md", community=0)
    G.add_node("doc_lonely", label="Doc Lonely", file_type="document",
               source_file="x.md", community=0)
    # doc_a -- supports --> doc_b (INFERRED, score 0.8)
    G.add_edge("doc_a", "doc_b", relation="supports", confidence="INFERRED",
               confidence_score=0.8, source_file="a.md",
               _src="doc_a", _tgt="doc_b", weight=1.0)
    # doc_a -- supersedes --> doc_c (EXTRACTED, no score)
    G.add_edge("doc_a", "doc_c", relation="supersedes", confidence="EXTRACTED",
               source_file="a.md", _src="doc_a", _tgt="doc_c", weight=1.0)
    # doc_lonely has no reasoning edges — still need at least one structural edge
    # so it is not orphaned out of mapping. Use a plain reference.
    G.add_edge("doc_lonely", "doc_b", relation="references",
               confidence="EXTRACTED", source_file="x.md", weight=1.0)

    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()
    plan, rendered_notes, profile, manifest_path, manifest = to_obsidian(
        G,
        communities={0: ["doc_a", "doc_b", "doc_c", "doc_lonely"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
        return_render_context=True,
    )

    # doc_a should have reasoning_relations with both items
    a_note = rendered_notes.get("doc_a")
    assert a_note is not None, f"doc_a not in rendered_notes: {list(rendered_notes)}"
    fm_fields = a_note["frontmatter_fields"]
    assert "reasoning_relations" in fm_fields
    rr = fm_fields["reasoning_relations"]
    assert isinstance(rr, list)
    assert len(rr) == 2
    parsed = [json.loads(item) for item in rr]
    types = {p["type"] for p in parsed}
    targets = {p["target"] for p in parsed}
    assert types == {"supports", "supersedes"}
    assert "Doc B" in targets and "ADR-0028" in targets
    # confidence_score present for the INFERRED supports edge, absent for EXTRACTED
    by_type = {p["type"]: p for p in parsed}
    assert by_type["supports"]["confidence_score"] == 0.8
    assert "confidence_score" not in by_type["supersedes"]

    # doc_lonely (no reasoning edges) has NO reasoning_relations key
    lonely_note = rendered_notes.get("doc_lonely")
    if lonely_note is not None:
        assert "reasoning_relations" not in lonely_note["frontmatter_fields"]

    # Round-trip: split_rendered_note on the full rendered text preserves
    # the field as a list of strings (T-72-12 / round-trip without loss).
    # Render the note text manually since RenderedNote stores fields + body.
    from graphify.profile import _dump_frontmatter
    rendered_text = _dump_frontmatter(fm_fields) + "\n" + a_note["body"]
    parsed_fm, body = split_rendered_note(rendered_text)
    assert "reasoning_relations" in parsed_fm
    assert isinstance(parsed_fm["reasoning_relations"], list)
    assert len(parsed_fm["reasoning_relations"]) == 2
    # Each round-tripped item is still json-decodable to a dict with the keys
    rt_parsed = [json.loads(item) for item in parsed_fm["reasoning_relations"]]
    rt_types = {p["type"] for p in rt_parsed}
    assert rt_types == {"supports", "supersedes"}
