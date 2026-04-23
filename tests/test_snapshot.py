"""Tests for graphify.snapshot — save, load, prune, list."""
from __future__ import annotations

import json
import time
from pathlib import Path

import networkx as nx
import pytest


def _make_graph():
    """Create a small test graph with 3 nodes and 2 edges."""
    G = nx.Graph()
    G.add_node("a", label="Alpha", file_type="code", source_file="a.py")
    G.add_node("b", label="Beta", file_type="code", source_file="b.py")
    G.add_node("c", label="Gamma", file_type="code", source_file="c.py")
    G.add_edge("a", "b", relation="calls", confidence="EXTRACTED")
    G.add_edge("b", "c", relation="imports", confidence="INFERRED")
    return G


def _make_communities():
    return {0: ["a", "b"], 1: ["c"]}


# --- snapshots_dir ---

def test_snapshots_dir_creates_directory(tmp_path):
    from graphify.snapshot import snapshots_dir

    d = snapshots_dir(tmp_path)
    assert d.exists()
    assert d == tmp_path / "graphify-out" / "snapshots"


# --- save_snapshot ---

def test_save_snapshot_creates_json_file(tmp_path):
    from graphify.snapshot import save_snapshot

    G = _make_graph()
    comms = _make_communities()
    result = save_snapshot(G, comms, tmp_path)
    assert result.exists()
    assert result.suffix == ".json"
    assert result.parent == tmp_path / "graphify-out" / "snapshots"


def test_save_snapshot_content_structure(tmp_path):
    from graphify.snapshot import save_snapshot

    G = _make_graph()
    comms = _make_communities()
    p = save_snapshot(G, comms, tmp_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "graph" in data
    assert "communities" in data
    assert "metadata" in data
    meta = data["metadata"]
    assert meta["node_count"] == 3
    assert meta["edge_count"] == 2
    assert "timestamp" in meta


def test_save_snapshot_with_name(tmp_path):
    from graphify.snapshot import save_snapshot

    G = _make_graph()
    comms = _make_communities()
    p = save_snapshot(G, comms, tmp_path, name="my run")
    # name sanitized: spaces become underscores or hyphens
    assert "my" in p.stem


def test_save_snapshot_name_sanitization(tmp_path):
    from graphify.snapshot import save_snapshot

    G = _make_graph()
    comms = _make_communities()
    # dangerous chars stripped
    p = save_snapshot(G, comms, tmp_path, name="../../etc/passwd")
    assert "/" not in p.stem
    assert ".." not in p.stem


# --- FIFO prune ---

def test_fifo_prune_removes_oldest(tmp_path):
    from graphify.snapshot import save_snapshot, list_snapshots

    G = _make_graph()
    comms = _make_communities()
    # Create 3 snapshots with cap=2
    save_snapshot(G, comms, tmp_path, name="first", cap=10)
    time.sleep(0.05)
    save_snapshot(G, comms, tmp_path, name="second", cap=10)
    time.sleep(0.05)
    save_snapshot(G, comms, tmp_path, name="third", cap=2)
    snaps = list_snapshots(tmp_path)
    assert len(snaps) == 2
    # oldest (first) should be gone
    stems = [s.stem for s in snaps]
    assert not any("first" in s for s in stems)


# --- load_snapshot ---

def test_load_snapshot_round_trip(tmp_path):
    from graphify.snapshot import save_snapshot, load_snapshot

    G = _make_graph()
    comms = _make_communities()
    p = save_snapshot(G, comms, tmp_path)

    G2, comms2, meta = load_snapshot(p)
    assert set(G2.nodes()) == set(G.nodes())
    assert G2.number_of_edges() == G.number_of_edges()
    assert comms2 == comms
    assert meta["node_count"] == 3


def test_load_snapshot_communities_int_keys(tmp_path):
    from graphify.snapshot import save_snapshot, load_snapshot

    G = _make_graph()
    comms = _make_communities()
    p = save_snapshot(G, comms, tmp_path)
    _, comms2, _ = load_snapshot(p)
    assert all(isinstance(k, int) for k in comms2.keys())


def test_load_snapshot_corrupt_file(tmp_path):
    from graphify.snapshot import load_snapshot

    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json at all", encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(bad_file)


def test_load_snapshot_missing_keys(tmp_path):
    from graphify.snapshot import load_snapshot

    bad_file = tmp_path / "partial.json"
    bad_file.write_text(json.dumps({"graph": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(bad_file)


# --- list_snapshots ---

def test_list_snapshots_empty(tmp_path):
    from graphify.snapshot import list_snapshots

    result = list_snapshots(tmp_path)
    assert result == []


def test_list_snapshots_sorted_oldest_first(tmp_path):
    from graphify.snapshot import save_snapshot, list_snapshots

    G = _make_graph()
    comms = _make_communities()
    save_snapshot(G, comms, tmp_path, name="aaa")
    time.sleep(0.05)
    save_snapshot(G, comms, tmp_path, name="bbb")
    snaps = list_snapshots(tmp_path)
    assert len(snaps) == 2
    # oldest first
    assert "aaa" in snaps[0].stem
    assert "bbb" in snaps[1].stem


# --- atomic write ---

def test_save_snapshot_atomic_write_no_tmp_leftover(tmp_path):
    from graphify.snapshot import save_snapshot, snapshots_dir

    G = _make_graph()
    comms = _make_communities()
    save_snapshot(G, comms, tmp_path)
    d = snapshots_dir(tmp_path)
    tmp_files = list(d.glob("*.tmp"))
    assert tmp_files == []


# --- provenance metadata (Task 2) ---

# --- auto_snapshot_and_delta ---

def test_auto_snapshot_and_delta_first_run(tmp_path):
    """On first call, snapshot is saved and GRAPH_DELTA.md contains 'First run'."""
    from graphify.snapshot import auto_snapshot_and_delta

    G = _make_graph()
    comms = _make_communities()
    snap_path, delta_path = auto_snapshot_and_delta(G, comms, project_root=tmp_path)
    assert snap_path.exists()
    assert delta_path is not None
    assert delta_path.exists()
    content = delta_path.read_text(encoding="utf-8")
    assert "First run" in content


def test_auto_snapshot_and_delta_second_run(tmp_path):
    """After two calls with different graphs, GRAPH_DELTA.md contains change summary."""
    from graphify.snapshot import auto_snapshot_and_delta

    G1 = _make_graph()
    comms1 = _make_communities()
    auto_snapshot_and_delta(G1, comms1, project_root=tmp_path)

    time.sleep(0.05)

    # Second graph: add a node
    G2 = _make_graph()
    G2.add_node("d", label="Delta", file_type="code", source_file="d.py")
    G2.add_edge("c", "d", relation="calls", confidence="EXTRACTED")
    comms2 = {0: ["a", "b"], 1: ["c", "d"]}
    snap_path, delta_path = auto_snapshot_and_delta(G2, comms2, project_root=tmp_path)

    assert snap_path.exists()
    assert delta_path is not None
    content = delta_path.read_text(encoding="utf-8")
    assert "First run" not in content
    # Should mention the added node
    assert "d" in content.lower() or "Added" in content


def test_auto_snapshot_and_delta_writes_to_graphify_out(tmp_path):
    """delta_path is {root}/graphify-out/GRAPH_DELTA.md."""
    from graphify.snapshot import auto_snapshot_and_delta

    G = _make_graph()
    comms = _make_communities()
    _, delta_path = auto_snapshot_and_delta(G, comms, project_root=tmp_path)
    assert delta_path == tmp_path / "graphify-out" / "GRAPH_DELTA.md"


# --- provenance metadata (Task 2) ---

def test_extract_python_provenance_fields(tmp_path):
    """Nodes from extract_python carry extracted_at, source_hash, source_mtime."""
    from graphify.extract import extract_python

    py_file = tmp_path / "sample.py"
    py_file.write_text("class Foo:\n    def bar(self):\n        pass\n", encoding="utf-8")
    result = extract_python(py_file)
    nodes = result.get("nodes", [])
    assert len(nodes) > 0, "extract_python should produce at least one node"
    for n in nodes:
        assert "extracted_at" in n, f"Node {n['id']} missing extracted_at"
        assert "source_hash" in n, f"Node {n['id']} missing source_hash"
        assert "source_mtime" in n, f"Node {n['id']} missing source_mtime"


def test_provenance_source_hash_matches_file_hash(tmp_path):
    """source_hash on extracted nodes matches cache.file_hash() for the same file."""
    from graphify.extract import extract_python
    from graphify.cache import file_hash

    py_file = tmp_path / "hashcheck.py"
    py_file.write_text("def hello():\n    return 1\n", encoding="utf-8")
    result = extract_python(py_file)
    nodes = result.get("nodes", [])
    assert len(nodes) > 0
    expected_hash = file_hash(py_file)
    for n in nodes:
        assert n["source_hash"] == expected_hash


def test_provenance_extracted_at_is_iso8601(tmp_path):
    """extracted_at is a valid ISO 8601 string."""
    from datetime import datetime
    from graphify.extract import extract_python

    py_file = tmp_path / "isocheck.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    result = extract_python(py_file)
    nodes = result.get("nodes", [])
    assert len(nodes) > 0
    for n in nodes:
        # Should not raise
        datetime.fromisoformat(n["extracted_at"])


# --- Phase 18 FOCUS-07: ProjectRoot sentinel + nested-dir integration (CR-01 regression) ---

def test_project_root_sentinel_rejects_graphify_out(tmp_path):
    """FOCUS-07 + T-18-C: construction must fail fast when path.name == 'graphify-out' (CR-01 guard)."""
    from graphify.snapshot import ProjectRoot
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        ProjectRoot(path=bad)


def test_project_root_sentinel_accepts_project_root(tmp_path):
    """FOCUS-07: positive — normal project root constructs without raising."""
    from graphify.snapshot import ProjectRoot
    pr = ProjectRoot(path=tmp_path)
    assert pr.path == tmp_path


def test_nested_dir_fixture_list_snapshots(nested_project_root):
    """FOCUS-07 integration: save + list snapshots under the nested-dir fixture layout."""
    import networkx as nx
    from graphify.snapshot import save_snapshot, list_snapshots
    G = nx.Graph()
    G.add_node("n1", label="one")
    save_snapshot(G, {0: ["n1"]}, project_root=nested_project_root, name="one")
    snaps = list_snapshots(nested_project_root)
    assert len(snaps) == 1
    assert "one" in snaps[0].name


# --- Plan 18-04 WR-01 / SC4 gap closure: production-callsite sentinel tests ---

def test_snapshots_dir_rejects_graphify_out_as_project_root(tmp_path):
    """FOCUS-07 + SC4 + WR-01: production callsite guard — snapshots_dir must reject graphify-out/ itself."""
    from graphify.snapshot import snapshots_dir
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        snapshots_dir(bad)


def test_list_snapshots_rejects_graphify_out_as_project_root(tmp_path):
    """FOCUS-07 + SC4 + WR-01: production callsite guard — list_snapshots must reject graphify-out/ itself."""
    from graphify.snapshot import list_snapshots
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        list_snapshots(bad)


def test_save_snapshot_rejects_graphify_out_as_project_root(tmp_path):
    """FOCUS-07 + SC4 + WR-01: production callsite guard — save_snapshot must reject graphify-out/ itself."""
    import networkx as nx
    from graphify.snapshot import save_snapshot
    G = nx.Graph()
    G.add_node("n1", label="one")
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        save_snapshot(G, {}, project_root=bad)


def test_auto_snapshot_and_delta_rejects_graphify_out_as_project_root(tmp_path):
    """FOCUS-07 + SC4 + WR-01: production callsite guard — auto_snapshot_and_delta must reject graphify-out/ itself."""
    import networkx as nx
    from graphify.snapshot import auto_snapshot_and_delta
    G = nx.Graph()
    G.add_node("n1", label="one")
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        auto_snapshot_and_delta(G, {}, project_root=bad)
