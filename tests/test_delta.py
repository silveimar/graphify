# tests for graphify/delta.py — delta computation, staleness, rendering
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx
import pytest
from networkx.readwrite import json_graph

from graphify.delta import classify_staleness, compute_delta, render_delta_md


def _make_graph(nodes, edges=None):
    """Helper: build nx.Graph from node ID list and optional edge tuples."""
    G = nx.Graph()
    for n in nodes:
        G.add_node(n, label=n, file_type="code", source_file=f"{n}.py")
    for src, tgt in (edges or []):
        G.add_edge(src, tgt, relation="calls", confidence="EXTRACTED")
    return G


# --- compute_delta tests ---


def test_identical_graphs_empty_delta():
    G = _make_graph(["a", "b"], [("a", "b")])
    comms = {0: ["a", "b"]}
    delta = compute_delta(G, comms, G, comms)
    assert delta["added_nodes"] == []
    assert delta["removed_nodes"] == []
    assert delta["added_edges"] == []
    assert delta["removed_edges"] == []
    assert delta["community_migrations"] == {}
    assert delta["connectivity_changes"] == {}


def test_added_node():
    G_old = _make_graph(["a"])
    G_new = _make_graph(["a", "b"])
    delta = compute_delta(G_old, {}, G_new, {})
    assert "b" in delta["added_nodes"]
    assert "a" not in delta["added_nodes"]


def test_removed_node():
    G_old = _make_graph(["a", "b"])
    G_new = _make_graph(["a"])
    delta = compute_delta(G_old, {}, G_new, {})
    assert "b" in delta["removed_nodes"]
    assert "a" not in delta["removed_nodes"]


def test_added_edge():
    G_old = _make_graph(["a", "b"])
    G_new = _make_graph(["a", "b"], [("a", "b")])
    delta = compute_delta(G_old, {}, G_new, {})
    assert ("a", "b") in delta["added_edges"]


def test_removed_edge():
    G_old = _make_graph(["a", "b"], [("a", "b")])
    G_new = _make_graph(["a", "b"])
    delta = compute_delta(G_old, {}, G_new, {})
    assert ("a", "b") in delta["removed_edges"]


def test_community_migration():
    G = _make_graph(["a", "b", "c"])
    comms_old = {0: ["a", "b"], 1: ["c"]}
    comms_new = {0: ["a"], 1: ["b", "c"]}
    delta = compute_delta(G, comms_old, G, comms_new)
    assert "b" in delta["community_migrations"]
    assert delta["community_migrations"]["b"] == (0, 1)


def test_connectivity_change():
    G_old = _make_graph(["a", "b", "c"], [("a", "b")])
    G_new = _make_graph(["a", "b", "c"], [("a", "b"), ("a", "c")])
    delta = compute_delta(G_old, {}, G_new, {})
    assert "a" in delta["connectivity_changes"]
    assert delta["connectivity_changes"]["a"]["degree_delta"] == 1


def test_empty_graphs():
    G_old = nx.Graph()
    G_new = nx.Graph()
    delta = compute_delta(G_old, {}, G_new, {})
    assert delta["added_nodes"] == []
    assert delta["removed_nodes"] == []
    assert delta["added_edges"] == []
    assert delta["removed_edges"] == []
    assert delta["community_migrations"] == {}
    assert delta["connectivity_changes"] == {}


# --- classify_staleness tests ---


def test_classify_staleness_fresh(tmp_path):
    """Node whose source_hash matches current file hash returns FRESH."""
    f = tmp_path / "hello.py"
    f.write_text("print('hi')")
    from graphify.cache import file_hash

    h = file_hash(f)
    node = {"source_file": str(f), "source_hash": h, "source_mtime": f.stat().st_mtime}
    assert classify_staleness(node) == "FRESH"


def test_classify_staleness_stale(tmp_path):
    """Node whose source_hash differs from current file hash returns STALE."""
    f = tmp_path / "hello.py"
    f.write_text("print('hi')")
    from graphify.cache import file_hash

    old_hash = file_hash(f)
    # Modify the file so hash changes
    f.write_text("print('changed')")
    node = {"source_file": str(f), "source_hash": old_hash, "source_mtime": 0.0}
    assert classify_staleness(node) == "STALE"


def test_classify_staleness_ghost():
    """Node whose source_file does not exist returns GHOST."""
    node = {
        "source_file": "/nonexistent/path/to/file.py",
        "source_hash": "abc123",
    }
    assert classify_staleness(node) == "GHOST"


def test_classify_staleness_no_provenance():
    """Node without source_hash returns FRESH (no provenance to check)."""
    node = {"source_file": "something.py"}
    assert classify_staleness(node) == "FRESH"

    node2 = {}
    assert classify_staleness(node2) == "FRESH"


# --- render_delta_md tests ---


def test_render_delta_md_empty():
    """Empty delta produces 'No changes detected'."""
    delta = {
        "added_nodes": [],
        "removed_nodes": [],
        "added_edges": [],
        "removed_edges": [],
        "community_migrations": {},
        "connectivity_changes": {},
    }
    md = render_delta_md(delta)
    assert "No changes detected" in md
    assert "# Graph Delta Report" in md


def test_render_delta_md_with_changes():
    """Delta with adds/removes produces Summary + Archive sections."""
    G_new = _make_graph(["a", "b", "c"], [("a", "b")])
    delta = {
        "added_nodes": ["c"],
        "removed_nodes": ["d"],
        "added_edges": [("a", "b")],
        "removed_edges": [("x", "y")],
        "community_migrations": {"a": (0, 1)},
        "connectivity_changes": {"a": {"degree_delta": 1, "added_edges": [("a", "b")], "removed_edges": []}},
    }
    md = render_delta_md(delta, G_new=G_new, communities_new={0: ["b", "c"], 1: ["a"]})
    assert "## Summary" in md
    assert "## Archive" in md
    assert "### Added Nodes" in md
    assert "### Removed Nodes" in md


def test_render_delta_md_first_run():
    """first_run=True produces sentinel message."""
    md = render_delta_md({}, first_run=True)
    assert "First run" in md
    assert "no previous snapshot" in md


def test_render_delta_md_connectivity():
    """Connectivity changes appear in archive table with degree delta."""
    delta = {
        "added_nodes": [],
        "removed_nodes": [],
        "added_edges": [],
        "removed_edges": [],
        "community_migrations": {},
        "connectivity_changes": {"a": {"degree_delta": 2, "added_edges": [("a", "b"), ("a", "c")], "removed_edges": []}},
    }
    md = render_delta_md(delta)
    assert "### Connectivity Changes" in md
    assert "+2" in md


def test_render_delta_md_staleness(tmp_path):
    """When G_new provided with GHOST nodes, staleness section appears."""
    G_new = nx.Graph()
    G_new.add_node("a", label="a", source_file="/nonexistent/ghost.py", source_hash="abc123")
    G_new.add_node("b", label="b", source_file="", source_hash="")
    delta = {
        "added_nodes": [],
        "removed_nodes": [],
        "added_edges": [],
        "removed_edges": [],
        "community_migrations": {},
        "connectivity_changes": {},
    }
    md = render_delta_md(delta, G_new=G_new)
    assert "Stale" in md or "GHOST" in md


# --- CLI integration tests ---


def _write_graph_json(path: Path, nodes, edges=None, communities=None):
    """Write a graph.json fixture at the given path."""
    G = nx.Graph()
    for n in nodes:
        cid = None
        if communities:
            for c, members in communities.items():
                if n in members:
                    cid = c
                    break
        G.add_node(n, label=n, file_type="code", source_file=f"{n}.py", community=cid)
    for src, tgt in (edges or []):
        G.add_edge(src, tgt, relation="calls", confidence="EXTRACTED")
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_cli_snapshot_help():
    """Running graphify --help shows 'snapshot' in output."""
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert "snapshot" in result.stdout


def test_cli_snapshot_saves_file(tmp_path):
    """graphify snapshot --graph {path} creates a snapshot file."""
    graph_json = tmp_path / "graphify-out" / "graph.json"
    _write_graph_json(graph_json, ["a", "b"], [("a", "b")], {0: ["a", "b"]})
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "snapshot", "--graph", str(graph_json)],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "snapshot saved:" in result.stdout
    snaps = list((tmp_path / "graphify-out" / "snapshots").glob("*.json"))
    assert len(snaps) >= 1


def test_cli_snapshot_with_name(tmp_path):
    """graphify snapshot --name test-label creates file with 'test-label' in name."""
    graph_json = tmp_path / "graphify-out" / "graph.json"
    _write_graph_json(graph_json, ["a", "b"], [("a", "b")], {0: ["a", "b"]})
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "snapshot", "--graph", str(graph_json), "--name", "test-label"],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    snaps = list((tmp_path / "graphify-out" / "snapshots").glob("*.json"))
    assert any("test-label" in s.stem for s in snaps)


def test_cli_snapshot_from_to(tmp_path):
    """graphify snapshot --from snap1 --to snap2 writes GRAPH_DELTA.md."""
    from graphify.snapshot import save_snapshot

    G1 = _make_graph(["a", "b"], [("a", "b")])
    comms1 = {0: ["a", "b"]}
    snap1 = save_snapshot(G1, comms1, project_root=tmp_path, name="snap1")
    time.sleep(0.05)

    G2 = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
    comms2 = {0: ["a", "b"], 1: ["c"]}
    snap2 = save_snapshot(G2, comms2, project_root=tmp_path, name="snap2")

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "snapshot", "--from", str(snap1), "--to", str(snap2)],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "delta written:" in result.stdout
    delta_file = tmp_path / "graphify-out" / "GRAPH_DELTA.md"
    assert delta_file.exists()
    content = delta_file.read_text(encoding="utf-8")
    assert "Graph Delta Report" in content
