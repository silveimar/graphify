# tests for graphify/delta.py — delta computation, staleness, rendering
from __future__ import annotations

import networkx as nx
import pytest

from graphify.delta import compute_delta


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
