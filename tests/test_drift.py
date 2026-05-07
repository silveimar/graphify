"""Tests for graphify.drift — Jaccard community matching and edge classification.

RED-then-GREEN cycle for Phase 67 Plan 01 (CDRIFT-01, CDRIFT-02, CDRIFT-04).
"""
from __future__ import annotations

import networkx as nx
import pytest

from graphify import drift


# ---------------------------------------------------------------------------
# Fixtures (inline, pure)
# ---------------------------------------------------------------------------

def _make_graph(edges: list[tuple[str, str, str]]) -> nx.Graph:
    """Build a small graph from (source, target, relation) tuples.

    Each edge gets a default source_file for classification output.
    """
    G = nx.Graph()
    for s, t, rel in edges:
        G.add_node(s)
        G.add_node(t)
        G.add_edge(s, t, relation=rel, source_file=f"{s}.py")
    return G


# ---------------------------------------------------------------------------
# Threshold constant
# ---------------------------------------------------------------------------

def test_threshold_constant_is_0_7():
    assert drift.JACCARD_THRESHOLD == 0.7


# ---------------------------------------------------------------------------
# match_communities_by_jaccard
# ---------------------------------------------------------------------------

def test_jaccard_perfect_match_returns_pair():
    old = {0: ["a", "b", "c"], 1: ["d", "e", "f"]}
    new = {0: ["a", "b", "c"], 1: ["d", "e", "f"]}
    matches = drift.match_communities_by_jaccard(old, new)
    assert matches[0] == 0
    assert matches[1] == 1


def test_jaccard_above_threshold_matches():
    # 9 of 11 union → ~0.818 ≥ 0.7
    old = {0: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
    new = {5: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "k"]}
    matches = drift.match_communities_by_jaccard(old, new)
    assert matches.get(0) == 5


def test_jaccard_below_threshold_unmatched():
    # 1 of 19 union → ~0.05 < 0.7
    old = {0: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
    new = {0: ["a", "k", "l", "m", "n", "o", "p", "q", "r", "s"]}
    matches = drift.match_communities_by_jaccard(old, new)
    assert 0 not in matches


# ---------------------------------------------------------------------------
# classify_edges
# ---------------------------------------------------------------------------

def test_classify_stable():
    G_old = _make_graph([("a", "b", "implements")])
    G_new = _make_graph([("a", "b", "implements")])
    old_c = {0: ["a", "b"]}
    new_c = {0: ["a", "b"]}
    out = drift.classify_edges(G_old, old_c, G_new, new_c)
    assert len(out) == 1
    assert out[0]["classification"] == "stable"


def test_classify_community_renamed():
    # Membership identical, only the integer cid changed (0 → 7).
    # CDRIFT-02 anchor: this MUST classify as community-renamed, not orphaned.
    G_old = _make_graph([("a", "b", "implements")])
    G_new = _make_graph([("a", "b", "implements")])
    old_c = {0: ["a", "b", "c"]}
    new_c = {7: ["a", "b", "c"]}
    # Add c to graphs so membership lists match real nodes
    G_old.add_node("c")
    G_new.add_node("c")
    out = drift.classify_edges(G_old, old_c, G_new, new_c)
    assert len(out) == 1
    assert out[0]["classification"] == "community-renamed"


def test_classify_community_resharded():
    # Old community membership has no Jaccard ≥ 0.7 match in new partition.
    G_old = _make_graph([("a", "b", "documents")])
    G_new = _make_graph([("a", "b", "documents")])
    # Add nodes used by communities
    for n in ["c", "d", "e", "f", "g", "h", "i", "j"]:
        G_old.add_node(n)
        G_new.add_node(n)
    # Add extras only to G_new for the disjoint new community
    for n in ["x", "y", "z", "w", "v", "u", "t", "s"]:
        G_new.add_node(n)
    old_c = {0: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
    # New partition splits old community across many tiny groups → no ≥0.7 match
    new_c = {
        0: ["a"],
        1: ["b"],
        2: ["x", "y", "z", "w", "v", "u", "t", "s"],
    }
    out = drift.classify_edges(G_old, old_c, G_new, new_c)
    assert len(out) == 1
    assert out[0]["classification"] == "community-resharded"


def test_classify_orphaned():
    # Edge endpoint missing from G_new entirely.
    G_old = _make_graph([("a", "b", "tests")])
    G_new = nx.Graph()
    G_new.add_node("a")
    G_new.add_edge("a", "z", relation="tests", source_file="a.py")
    G_new.add_node("z")
    old_c = {0: ["a", "b"]}
    new_c = {0: ["a", "z"]}
    out = drift.classify_edges(G_old, old_c, G_new, new_c)
    # The (a, z) edge in G_new has endpoint 'z' missing from old → still
    # classification iterates G_new edges; 'z' not in old node→cid, so orphaned.
    classifications = {(e["source"], e["target"]): e["classification"] for e in out}
    # Either (a,z) or (z,a) — networkx undirected
    cls = classifications.get(("a", "z")) or classifications.get(("z", "a"))
    assert cls == "orphaned"


def test_classify_only_targets_implements_documents_tests():
    G_old = _make_graph([
        ("a", "b", "implements"),
        ("a", "b", "contains"),
    ])
    G_new = _make_graph([
        ("a", "b", "implements"),
        ("a", "b", "calls"),
    ])
    # NetworkX undirected simple graph collapses parallel edges; build distinct
    G_old = nx.MultiGraph()
    G_old.add_edge("a", "b", relation="implements", source_file="a.py")
    G_old.add_edge("a", "c", relation="contains", source_file="a.py")
    G_new = nx.MultiGraph()
    G_new.add_edge("a", "b", relation="implements", source_file="a.py")
    G_new.add_edge("a", "c", relation="calls", source_file="a.py")
    old_c = {0: ["a", "b", "c"]}
    new_c = {0: ["a", "b", "c"]}
    out = drift.classify_edges(G_old, old_c, G_new, new_c)
    rels = {e["relation"] for e in out}
    assert rels <= {"implements", "documents", "tests"}
    assert "contains" not in rels
    assert "calls" not in rels


# ---------------------------------------------------------------------------
# write_drift_snapshot — delegates to snapshot.save_snapshot
# ---------------------------------------------------------------------------

def test_write_drift_snapshot_uses_snapshots_dir(tmp_path):
    G = nx.Graph()
    G.add_edge("a", "b", relation="implements", source_file="a.py")
    communities = {0: ["a", "b"]}
    out = drift.write_drift_snapshot(G, communities, project_root=tmp_path)
    assert out.exists()
    # D-01: must be graphify-out/snapshots/, NOT cache/snapshots/
    assert "graphify-out/snapshots" in str(out).replace("\\", "/")
    assert "cache/snapshots" not in str(out).replace("\\", "/")


# ---------------------------------------------------------------------------
# compute_edge_drift — returns None when no prior snapshot (D-09)
# ---------------------------------------------------------------------------

def test_compute_edge_drift_returns_none_without_snapshot(tmp_path):
    G = nx.Graph()
    G.add_edge("a", "b", relation="implements", source_file="a.py")
    communities = {0: ["a", "b"]}
    result = drift.compute_edge_drift(G, communities, project_root=tmp_path)
    assert result is None


def test_compute_edge_drift_summary_after_snapshot(tmp_path):
    G_old = nx.Graph()
    G_old.add_edge("a", "b", relation="implements", source_file="a.py")
    drift.write_drift_snapshot(G_old, {0: ["a", "b"]}, project_root=tmp_path)

    G_new = nx.Graph()
    G_new.add_edge("a", "b", relation="implements", source_file="a.py")
    result = drift.compute_edge_drift(G_new, {0: ["a", "b"]}, project_root=tmp_path)
    assert result is not None
    assert "counts" in result
    assert "edges" in result
    assert result["counts"]["stable"] == 1
