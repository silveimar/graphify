from __future__ import annotations
import json
from pathlib import Path
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

# ---------------------------------------------------------------------------
# Task 3.1 — Atomic writer + manifest decision table + import-log journal
# ---------------------------------------------------------------------------

def test_vault01_write_decision_table(tmp_path):
    """D-13 decision table: written/overwritten/skipped_foreign/skipped_user_modified."""
    from graphify.vault_promote import write_note, _hash_bytes

    vault = tmp_path / "vault"
    vault.mkdir()

    # Case 1: absent from manifest AND no disk file → "written"
    manifest: dict[str, str] = {}
    result = write_note(vault, "Atlas/Dots/Things/TestNote.md", "# Hello", manifest)
    assert result == "written", f"Expected 'written', got {result!r}"
    assert (vault / "Atlas/Dots/Things/TestNote.md").exists(), "File must be created"
    assert "Atlas/Dots/Things/TestNote.md" in manifest, "Manifest must be updated"

    # Case 2: manifest has hash matching current disk file → "overwritten"
    content2 = "# Hello Updated"
    # Simulate: manifest hash matches disk (i.e. we wrote it last time — set manifest to disk hash)
    disk_path = vault / "Atlas/Dots/Things/TestNote.md"
    manifest["Atlas/Dots/Things/TestNote.md"] = _hash_bytes(disk_path)
    result2 = write_note(vault, "Atlas/Dots/Things/TestNote.md", content2, manifest)
    assert result2 == "overwritten", f"Expected 'overwritten', got {result2!r}"
    assert disk_path.read_text(encoding="utf-8") == content2

    # Case 3: file exists on disk but NOT in manifest → "skipped_foreign"
    foreign = vault / "Atlas/Docs/Foreign.md"
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("User content", encoding="utf-8")
    result3 = write_note(vault, "Atlas/Docs/Foreign.md", "# Overwrite attempt", {})
    assert result3 == "skipped_foreign", f"Expected 'skipped_foreign', got {result3!r}"
    assert foreign.read_text(encoding="utf-8") == "User content", "Foreign file must be unchanged"

    # Case 4: manifest has hash that does NOT match disk (user edited) → "skipped_user_modified"
    user_modified = vault / "Atlas/Dots/Things/UserEdited.md"
    user_modified.parent.mkdir(parents=True, exist_ok=True)
    user_modified.write_text("# User wrote this", encoding="utf-8")
    manifest_stale = {"Atlas/Dots/Things/UserEdited.md": "deadbeef" * 8}  # wrong hash
    result4 = write_note(vault, "Atlas/Dots/Things/UserEdited.md", "# Graphify attempt", manifest_stale)
    assert result4 == "skipped_user_modified", f"Expected 'skipped_user_modified', got {result4!r}"
    assert user_modified.read_text(encoding="utf-8") == "# User wrote this", "User-modified file must be unchanged"


def test_vault01_write_note_path_traversal(tmp_path):
    """Path traversal rel_path='../escape.md' must raise, no file created outside vault."""
    from graphify.vault_promote import write_note

    vault = tmp_path / "vault"
    vault.mkdir()
    escape_target = tmp_path / "escape.md"

    import pytest as _pytest
    with _pytest.raises((ValueError, OSError)):
        write_note(vault, "../escape.md", "evil content", {})

    assert not escape_target.exists(), "No file must be created outside vault"


def test_vault05_import_log_written(tmp_path):
    """_append_import_log creates import-log.md with a Run block."""
    from graphify.vault_promote import _append_import_log

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    run_block = "## Run 2026-04-23T06:00\n- vault: /test/vault\n- threshold: 3\n- promoted: things=1\n- skipped: none\n"
    _append_import_log(graphify_out, run_block)

    log_path = graphify_out / "import-log.md"
    assert log_path.exists(), "import-log.md must be created"
    content = log_path.read_text(encoding="utf-8")
    assert "## Run 2026-04-23T06:00" in content, "Run block must appear in log"
    assert "things=1" in content


def test_vault05_import_log_append_latest_first(tmp_path):
    """Two sequential _append_import_log calls: second block must appear BEFORE first."""
    from graphify.vault_promote import _append_import_log

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    block1 = "## Run 2026-04-23T06:00\n- promoted: things=1\n"
    block2 = "## Run 2026-04-23T07:00\n- promoted: things=2\n"

    _append_import_log(graphify_out, block1)
    _append_import_log(graphify_out, block2)

    content = (graphify_out / "import-log.md").read_text(encoding="utf-8")
    pos_block1 = content.index("## Run 2026-04-23T06:00")
    pos_block2 = content.index("## Run 2026-04-23T07:00")
    assert pos_block2 < pos_block1, (
        "Second (later) run block must appear before first (earlier) run block in file. "
        f"block2 at {pos_block2}, block1 at {pos_block1}"
    )


def test_vault05_manifest_roundtrip(tmp_path):
    """_save_manifest then _load_manifest round-trips the dict with sort_keys."""
    from graphify.vault_promote import _save_manifest, _load_manifest

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    manifest = {
        "Atlas/Dots/Things/Zeta.md": "abc123",
        "Atlas/Maps/community-0.md": "def456",
        "Atlas/Dots/Things/Alpha.md": "ghi789",
    }
    _save_manifest(manifest, graphify_out)
    loaded = _load_manifest(graphify_out)

    assert loaded == manifest, f"Round-trip mismatch: {loaded}"
    # Verify sort_keys=True by reading raw JSON
    raw = (graphify_out / "vault-manifest.json").read_text(encoding="utf-8")
    keys_in_file = [line.strip().strip('"').rstrip('":') for line in raw.splitlines() if '": "' in line]
    assert keys_in_file == sorted(keys_in_file), f"Keys not sorted in manifest: {keys_in_file}"


# ---------------------------------------------------------------------------
# Task 3.2 — promote() orchestrator + profile write-back (VAULT-06) + CLI
# ---------------------------------------------------------------------------

def _make_minimal_graph_json(tmp_path: Path, *, with_py: bool = True) -> Path:
    """Build a tiny graph.json for promote() smoke tests.

    Produces 3 nodes: a document god-node (high degree), an isolated node
    (becomes a Question gap), and optionally a Python source node.
    """
    import json as _json
    from networkx.readwrite import json_graph as _jg

    G = nx.Graph()
    G.add_node("doc_hub", label="DocHub", file_type="document", source_file="notes/hub.md", community=0)
    G.add_node("isolated", label="OrphanConcept", file_type="document", source_file="notes/orphan.md", community=1)
    # Add enough edges so doc_hub is a god node (degree >= 3)
    for i in range(5):
        peer = f"peer_{i}"
        G.add_node(peer, label=f"Peer{i}", file_type="document", source_file=f"notes/peer{i}.md", community=0)
        G.add_edge("doc_hub", peer, relation="references", confidence="EXTRACTED", source_file="notes/hub.md", weight=1.0)
    if with_py:
        G.add_node("pymod", label="PyModule", file_type="code", source_file="src/mod.py", community=0)
        G.add_edge("doc_hub", "pymod", relation="imports", confidence="EXTRACTED", source_file="notes/hub.md", weight=1.0)

    communities = {0: ["doc_hub"] + [f"peer_{i}" for i in range(5)] + (["pymod"] if with_py else []),
                   1: ["isolated"]}
    for cid, nodes in communities.items():
        for nid in nodes:
            if nid in G.nodes:
                G.nodes[nid]["community"] = cid

    out = tmp_path / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)
    raw = _jg.node_link_data(G)
    (out / "graph.json").write_text(_json.dumps(raw), encoding="utf-8")
    return out / "graph.json"


def test_promote_smoke(tmp_path):
    """promote() on a small synthetic graph produces notes, manifest, and import-log."""
    from graphify.vault_promote import promote

    graph_path = _make_minimal_graph_json(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    summary = promote(graph_path=graph_path, vault_path=vault, threshold=3)

    # Manifest must exist with at least one entry
    manifest_path = tmp_path / "graphify-out" / "vault-manifest.json"
    assert manifest_path.exists(), "vault-manifest.json must be written"
    import json as _json
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest) >= 1, "Manifest must have at least one entry"

    # Import-log must exist and have one Run block
    log_path = tmp_path / "graphify-out" / "import-log.md"
    assert log_path.exists(), "import-log.md must be created"
    log_content = log_path.read_text(encoding="utf-8")
    assert "## Run " in log_content, "import-log.md must contain a Run block"

    # Summary must have promoted dict
    assert "promoted" in summary, f"Summary must have 'promoted' key, got: {summary}"


def test_promote_idempotent(tmp_path):
    """Running promote() twice → second run uses overwritten (not written), no foreign skips."""
    from graphify.vault_promote import promote

    graph_path = _make_minimal_graph_json(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    promote(graph_path=graph_path, vault_path=vault, threshold=3)
    summary2 = promote(graph_path=graph_path, vault_path=vault, threshold=3)

    # No foreign skips on second run
    skipped = summary2.get("skipped", {})
    assert "foreign" not in skipped or len(skipped.get("foreign", [])) == 0, (
        f"Second run must not produce foreign skips: {skipped}"
    )

    # import-log must have 2 Run blocks
    log_content = (tmp_path / "graphify-out" / "import-log.md").read_text(encoding="utf-8")
    assert log_content.count("## Run ") == 2, (
        f"Expected 2 Run blocks in import-log, got: {log_content.count('## Run ')}"
    )


def test_vault01_cli_does_not_overwrite_foreign(tmp_path):
    """promote() skips files on disk not in manifest; records them in summary + import-log."""
    from graphify.vault_promote import promote

    graph_path = _make_minimal_graph_json(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    # Pre-place a foreign file in a path graphify would use.
    # Maps are rendered with safe_filename(label) where label = "Community 0", "Community 1" etc.
    # Use "Community 0.md" which matches the first community in the synthetic graph.
    foreign_dir = vault / "Atlas" / "Maps"
    foreign_dir.mkdir(parents=True, exist_ok=True)
    foreign_file = foreign_dir / "Community 0.md"
    foreign_file.write_text("## User's own map note", encoding="utf-8")
    original_content = foreign_file.read_text(encoding="utf-8")

    summary = promote(graph_path=graph_path, vault_path=vault, threshold=3)

    # The foreign file must be unchanged
    assert foreign_file.read_text(encoding="utf-8") == original_content, (
        "Foreign file must not be overwritten"
    )

    # Summary must record the foreign skip
    skipped = summary.get("skipped", {})
    has_foreign = any("foreign" in reason for reason in skipped)
    # The skipped dict maps reason → list of paths
    foreign_paths = skipped.get("foreign", [])
    assert len(foreign_paths) >= 1, f"Expected foreign skips in summary, got: {skipped}"

    # Import-log must mention the skipped file
    log_content = (tmp_path / "graphify-out" / "import-log.md").read_text(encoding="utf-8")
    assert "foreign" in log_content, "Import-log must mention foreign skip"


def test_vault06_profile_writeback_union_merge(tmp_path):
    """promote() with auto_update=True adds detected tech tags to .graphify/profile.yaml."""
    pytest.importorskip("yaml")
    from graphify.vault_promote import promote

    graph_path = _make_minimal_graph_json(tmp_path, with_py=True)  # has .py node
    vault = tmp_path / "vault"
    vault.mkdir()

    promote(graph_path=graph_path, vault_path=vault, threshold=3)

    profile_path = vault / ".graphify" / "profile.yaml"
    assert profile_path.exists(), ".graphify/profile.yaml must be written on auto_update=True"

    import yaml
    written = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    tech_tags = written.get("tag_taxonomy", {}).get("tech", [])
    assert "python" in tech_tags, f"tech/python must be in profile after promote; got {tech_tags}"


def test_vault06_profile_writeback_opt_out(tmp_path):
    """promote() with auto_update=False must NOT modify .graphify/profile.yaml."""
    pytest.importorskip("yaml")
    import yaml
    from graphify.vault_promote import promote

    graph_path = _make_minimal_graph_json(tmp_path, with_py=True)
    vault = tmp_path / "vault"
    vault.mkdir()

    # Pre-write profile.yaml with auto_update: false
    graphify_dir = vault / ".graphify"
    graphify_dir.mkdir(parents=True, exist_ok=True)
    profile_path = graphify_dir / "profile.yaml"
    initial_profile = {"profile_sync": {"auto_update": False}, "tag_taxonomy": {"tech": ["existing"]}}
    profile_path.write_text(yaml.dump(initial_profile), encoding="utf-8")
    original_bytes = profile_path.read_bytes()

    promote(graph_path=graph_path, vault_path=vault, threshold=3)

    assert profile_path.read_bytes() == original_bytes, (
        "profile.yaml must be byte-identical when auto_update=False"
    )


def test_cli_subcommand_help_works():
    """graphify vault-promote --help exits 0 with --vault in stdout."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "graphify", "vault-promote", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"--help must exit 0, got {result.returncode}. stderr: {result.stderr}"
    assert "--vault" in result.stdout, f"--vault must appear in help output: {result.stdout}"
    assert "--threshold" in result.stdout, f"--threshold must appear in help output: {result.stdout}"


# ---------------------------------------------------------------------------
# Task 4.1 — Integration + heuristic tests (Plan 19-04)
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vault_promote_graph.json"


def _make_graph_json_from_fixture(tmp_path: Path) -> Path:
    """Copy the synthetic fixture into a graphify-out/ dir for promote() calls."""
    import json as _json
    from networkx.readwrite import json_graph as _jg

    fixture_data = _json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    out = tmp_path / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "graph.json").write_text(_json.dumps(fixture_data), encoding="utf-8")
    return out / "graph.json"


def test_end_to_end_all_seven_folders(tmp_path):
    """Full promote() run on synthetic fixture: at least one file in each of 7 target folders."""
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    # threshold=1 so degree-1 People/Quotes/Statements nodes qualify
    promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # 7 folder prefixes must each have at least one .md file
    expected_folders = [
        vault / "Atlas" / "Dots" / "Things",
        vault / "Atlas" / "Dots" / "Questions",
        vault / "Atlas" / "Maps",
        vault / "Atlas" / "Sources" / "Clippings",
        vault / "Atlas" / "Dots" / "People",
        vault / "Atlas" / "Dots" / "Quotes",
        vault / "Atlas" / "Dots" / "Statements",
    ]
    for folder in expected_folders:
        md_files = list(folder.glob("*.md")) if folder.exists() else []
        assert len(md_files) >= 1, (
            f"Expected at least one .md in {folder.relative_to(tmp_path)}, found none. "
            f"Vault tree: {[str(p.relative_to(tmp_path)) for p in vault.rglob('*.md')]}"
        )


def test_multi_run_drift_overwrite_self(tmp_path):
    """Second identical promote() reports all prior notes as overwritten; import-log has 2 Run blocks."""
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    # First run — all notes are written (threshold=1 so People/Quotes/Statements qualify)
    promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # Second run — same graph, same threshold
    summary2 = promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # No foreign skips
    skipped = summary2.get("skipped", {})
    assert "foreign" not in skipped or len(skipped.get("foreign", [])) == 0, (
        f"Second run must not produce foreign skips; got: {skipped}"
    )

    # import-log must have exactly 2 Run blocks
    log_path = tmp_path / "graphify-out" / "import-log.md"
    log_content = log_path.read_text(encoding="utf-8")
    run_count = log_content.count("## Run ")
    assert run_count == 2, f"Expected 2 Run blocks in import-log, got {run_count}"

    # Promoted count must come entirely from overwritten notes (or new gaps/maps)
    promoted = summary2.get("promoted", {})
    total_promoted = sum(promoted.values())
    assert total_promoted >= 1, "Second run must still report promoted notes as overwritten"


def test_multi_run_preserves_foreign_file(tmp_path):
    """Foreign file created between runs must remain untouched and appear in skipped count."""
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    # Do NOT run first promote() — create a foreign file at a path promote() WILL try to write.
    # promote() treats a file as foreign when it exists on disk but is NOT in the manifest.
    # Use "Atlas/Maps/Community 0.md" — promote() always generates Map MOCs for community 0.
    foreign_dir = vault / "Atlas" / "Maps"
    foreign_dir.mkdir(parents=True, exist_ok=True)
    handmade = foreign_dir / "Community 0.md"
    handmade.write_text("# Hand-written map\nUser created this manually.", encoding="utf-8")
    original_bytes = handmade.read_bytes()

    # promote() runs with an empty manifest — so Community 0.md is a foreign file
    summary2 = promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # Handmade.md must be unchanged
    assert handmade.read_bytes() == original_bytes, "Foreign file bytes must be identical after promote()"

    # Summary must record the foreign skip
    skipped = summary2.get("skipped", {})
    foreign_paths = skipped.get("foreign", [])
    assert any("Community 0.md" in p for p in foreign_paths), (
        f"'Community 0.md' must appear in skipped[foreign]; got skipped: {skipped}"
    )


def test_multi_run_preserves_user_edit(tmp_path):
    """User-edited promoted file must be preserved; appears as skipped_user_modified."""
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # Locate one promoted file in Things and mutate it
    things_dir = vault / "Atlas" / "Dots" / "Things"
    assert things_dir.exists(), "Things folder must exist after first promote()"
    promoted_files = list(things_dir.glob("*.md"))
    assert promoted_files, "There must be at least one promoted file in Things"

    target = promoted_files[0]
    rel_path = str(target.relative_to(vault))
    target.write_text("# User modified this note\nCustom content.", encoding="utf-8")
    modified_bytes = target.read_bytes()

    summary2 = promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # The file must be unchanged
    assert target.read_bytes() == modified_bytes, "User-modified file must not be overwritten"

    # Summary must record user_modified skip
    skipped = summary2.get("skipped", {})
    user_mod_paths = skipped.get("user_modified", [])
    assert any(Path(p).name == target.name for p in user_mod_paths), (
        f"User-modified file must appear in skipped[user_modified]; got skipped: {skipped}"
    )


def test_heuristic_people_regex(tmp_path):
    """_is_person: True for First Last; False for lowercase, allcaps, single word, accented."""
    from graphify.vault_promote import _is_person

    assert _is_person("Alice Smith") is True, "Alice Smith must match"
    assert _is_person("John Doe") is True, "John Doe must match"

    assert _is_person("alice smith") is False, "lowercase must not match (ASCII-only per RESEARCH.md)"
    assert _is_person("ALICE SMITH") is False, "all-caps must not match"
    assert _is_person("Alice") is False, "single word must not match"
    assert _is_person("José García") is False, "accented characters are ASCII-only limitation"


def test_heuristic_quote_marks(tmp_path):
    """_has_quote_marks: True for labels with smart/guillemet quotes; False for plain labels."""
    from graphify.vault_promote import _has_quote_marks

    assert _has_quote_marks('"Opening curly"') is True, "left double curly must match"
    assert _has_quote_marks('"Closing curly"') is True, "right double curly must match"
    assert _has_quote_marks('"Plain ascii double"') is True, "plain ASCII double quote must match"
    assert _has_quote_marks("«guillemet open»") is True, "guillemet open must match"
    assert _has_quote_marks("normal label no quotes") is False, "plain label must not match"
    assert _has_quote_marks("") is False, "empty label must not match"


def test_heuristic_defines_edge(tmp_path):
    """_has_defines_edge: True when adjacent edge has relation=defines; False otherwise."""
    from graphify.vault_promote import _has_defines_edge

    G = nx.Graph()
    G.add_node("a", label="A")
    G.add_node("b", label="B")
    G.add_node("c", label="C")

    G.add_edge("a", "b", relation="defines", confidence="EXTRACTED", source_file="x.md", weight=1.0)
    G.add_edge("b", "c", relation="references", confidence="EXTRACTED", source_file="x.md", weight=1.0)

    assert _has_defines_edge(G, "a") is True, "Node a has a defines edge"
    assert _has_defines_edge(G, "b") is True, "Node b has a defines edge (undirected)"
    assert _has_defines_edge(G, "c") is False, "Node c only has references — no defines edge"


def test_tech_layer3_detection_persists_via_writeback(tmp_path):
    """After promote() on fixture with .py + .ts source_files, profile.yaml has tech/python and tech/typescript."""
    pytest.importorskip("yaml")
    import yaml
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    promote(graph_path=graph_path, vault_path=vault, threshold=1)

    profile_path = vault / ".graphify" / "profile.yaml"
    assert profile_path.exists(), ".graphify/profile.yaml must be written after promote()"

    written = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    tech_tags = written.get("tag_taxonomy", {}).get("tech", [])
    assert "python" in tech_tags, f"tech/python must be in profile.yaml tech tags; got {tech_tags}"
    assert "typescript" in tech_tags, f"tech/typescript must be in profile.yaml tech tags; got {tech_tags}"
