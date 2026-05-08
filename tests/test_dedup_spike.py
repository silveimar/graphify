"""Unit tests for scripts/dedup_spike.py (Phase 73 DEDUP measurement spike)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# scripts/ is not a package; add to sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import dedup_spike as ds  # noqa: E402


def test_normalize_basic():
    assert ds.normalize("Multi Head Attention.") == "multi head attention"
    assert ds.normalize("  Hello,   WORLD!  ") == "hello world"


def test_normalize_empty_and_none():
    assert ds.normalize("") == ""
    assert ds.normalize(None) == ""


def test_fingerprint_deterministic():
    a = ds.fingerprint("Transformer", "an architecture")
    b = ds.fingerprint("Transformer", "an architecture")
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_fingerprint_normalization_collision():
    assert ds.fingerprint("Transformer.", "") == ds.fingerprint("transformer", "")
    assert ds.fingerprint("Transformer.", None) == ds.fingerprint("transformer", "")


def test_fingerprint_truncates_description():
    desc_a = "x" * 200 + "AAA"
    desc_b = "x" * 200 + "BBB"
    assert ds.fingerprint("Foo", desc_a) == ds.fingerprint("Foo", desc_b)


def test_group_by_fingerprint_filters_singletons():
    nodes = [
        {"id": "n1", "label": "Alpha", "enriched_description": ""},
        {"id": "n2", "label": "alpha", "enriched_description": ""},
        {"id": "n3", "label": "Beta", "enriched_description": ""},
    ]
    groups = ds.group_by_fingerprint(nodes)
    assert len(groups) == 1
    only = next(iter(groups.values()))
    assert {n["id"] for n in only} == {"n1", "n2"}


def test_semsim_pairs_filters_relation():
    edges = [
        {"source": "a", "target": "b", "relation": "calls"},
        {"source": "a", "target": "b", "relation": "semantically_similar_to", "confidence_score": 0.9},
    ]
    pairs = ds.semsim_pairs(edges)
    assert pairs == {frozenset(("a", "b"))}


def test_semsim_pairs_min_score():
    edges = [
        {"source": "a", "target": "b", "relation": "semantically_similar_to", "confidence_score": 0.4},
        {"source": "c", "target": "d", "relation": "semantically_similar_to", "confidence_score": 0.8},
    ]
    pairs = ds.semsim_pairs(edges, min_score=0.5)
    assert pairs == {frozenset(("c", "d"))}


def test_collision_is_covered_full_clique():
    group = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    semsim = {frozenset(("a", "b")), frozenset(("b", "c")), frozenset(("a", "c"))}
    assert ds.collision_is_covered(group, semsim) is True


def test_collision_is_covered_partial():
    group = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    semsim = {frozenset(("a", "b"))}  # c is unlinked
    assert ds.collision_is_covered(group, semsim) is False


def test_load_graph_json_accepts_links_and_edges(tmp_path):
    p1 = tmp_path / "g1.json"
    p1.write_text(json.dumps({"nodes": [{"id": "x"}], "links": [{"source": "x", "target": "x", "relation": "r"}]}))
    n1, e1 = ds.load_graph_json(p1)
    assert n1 and e1

    p2 = tmp_path / "g2.json"
    p2.write_text(json.dumps({"nodes": [{"id": "y"}], "edges": [{"source": "y", "target": "y", "relation": "r"}]}))
    n2, e2 = ds.load_graph_json(p2)
    assert n2 and e2


def test_select_concept_nodes_excludes_code_by_default():
    nodes = [
        {"id": "a", "file_type": "code"},
        {"id": "b", "file_type": "document"},
        {"id": "c", "file_type": "paper"},
    ]
    out = ds.select_concept_nodes(nodes)
    assert {n["id"] for n in out} == {"b", "c"}


def test_select_concept_nodes_include_code_flag():
    nodes = [
        {"id": "a", "file_type": "code"},
        {"id": "b", "file_type": "document"},
    ]
    out = ds.select_concept_nodes(nodes, include_code=True)
    assert {n["id"] for n in out} == {"a", "b"}


def test_classify_corpus_end_to_end():
    nodes = [
        {"id": "n1", "label": "Alpha", "file_type": "document"},
        {"id": "n2", "label": "alpha", "file_type": "document"},  # collides with n1
        {"id": "n3", "label": "Beta", "file_type": "document"},
        {"id": "n4", "label": "Gamma", "file_type": "paper"},
        {"id": "n5", "label": "gamma", "file_type": "paper"},  # collides with n4, covered by sem-sim
    ]
    edges = [
        {"source": "n4", "target": "n5", "relation": "semantically_similar_to", "confidence_score": 0.9},
    ]
    stats = ds.classify_corpus(nodes, edges, include_code=False, min_score=0.0)
    assert stats["total_concept_nodes"] == 5
    assert stats["collision_groups"] == 2
    assert stats["raw_collision_nodes"] == 4  # n1,n2,n4,n5
    assert stats["residual_collision_nodes"] == 2  # only n1,n2 (n4/n5 covered)
    assert stats["raw_rate"] == pytest.approx(4 / 5)
    assert stats["residual_rate"] == pytest.approx(2 / 5)
