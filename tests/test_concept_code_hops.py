"""Phase 67 Plan 02 — CQUERY validator + filter predicate factory tests.

Tests the new sibling helpers added to ``graphify/serve.py``:
    - ``_validate_relations_filter_arg`` (NEW; accepts [])
    - ``_resolve_confidence_band``       (NEW; D-10 cutpoints)
    - ``_build_concept_hops_filter``     (NEW; AND semantics, D-11/D-13)

Also pins the legacy ``_validate_relations_arg`` (line 2245) contract: it
must STILL reject ``[]`` (D-12 revised — legacy v1.12 path is preserved).
"""
from __future__ import annotations

import pytest

from graphify.serve import (
    _build_concept_hops_filter,
    _resolve_confidence_band,
    _validate_relations_arg,
    _validate_relations_filter_arg,
)


# ---------------------------------------------------------------------------
# _validate_relations_filter_arg (NEW)
# ---------------------------------------------------------------------------


def test_relations_filter_accepts_empty_list():
    """D-12: explicit `[]` is a valid zero-match filter, NOT an error."""
    assert _validate_relations_filter_arg([]) == []


def test_relations_filter_accepts_none():
    assert _validate_relations_filter_arg(None) is None


def test_relations_filter_accepts_string_list():
    assert _validate_relations_filter_arg(["implements", "tests"]) == [
        "implements",
        "tests",
    ]


@pytest.mark.parametrize("bad", [{}, "implements", 42, 3.14, ()])
def test_relations_filter_rejects_non_list(bad):
    with pytest.raises(ValueError):
        _validate_relations_filter_arg(bad)


def test_relations_filter_rejects_nonstring_members():
    with pytest.raises(ValueError):
        _validate_relations_filter_arg([1, 2])
    with pytest.raises(ValueError):
        _validate_relations_filter_arg(["ok", 7])


# ---------------------------------------------------------------------------
# Legacy validator preservation (D-12 revised)
# ---------------------------------------------------------------------------


def test_legacy_validator_still_rejects_empty():
    """Legacy ``_validate_relations_arg`` (serve.py:2245) MUST reject [].

    The legacy contract returns ``(set, err)`` where ``err`` is non-None on
    failure. v1.12 callers depend on this — Plan 02 must not regress it.
    """
    relset, err = _validate_relations_arg([])
    assert err is not None
    assert "empty" in err.lower()
    assert relset == frozenset()


# ---------------------------------------------------------------------------
# _resolve_confidence_band (NEW; D-10 cutpoints)
# ---------------------------------------------------------------------------


def test_band_high():
    lo, hi = _resolve_confidence_band("high")
    # high covers x >= 0.8
    assert lo == pytest.approx(0.8)
    assert 0.85 >= lo and 0.85 < hi
    assert 0.8 >= lo and 0.8 < hi
    assert not (0.79 >= lo and 0.79 < hi)


def test_band_medium():
    lo, hi = _resolve_confidence_band("medium")
    # medium covers 0.5 <= x < 0.8
    assert lo == pytest.approx(0.5)
    assert hi == pytest.approx(0.8)
    assert 0.5 >= lo and 0.5 < hi
    assert 0.79 >= lo and 0.79 < hi
    assert not (0.8 >= lo and 0.8 < hi)
    assert not (0.49 >= lo and 0.49 < hi)


def test_band_low():
    lo, hi = _resolve_confidence_band("low")
    # low covers x < 0.5
    assert lo == pytest.approx(0.0)
    assert hi == pytest.approx(0.5)
    assert 0.0 >= lo and 0.0 < hi
    assert 0.49 >= lo and 0.49 < hi
    assert not (0.5 >= lo and 0.5 < hi)


def test_band_none_returns_none():
    assert _resolve_confidence_band(None) is None


def test_band_invalid():
    with pytest.raises(ValueError):
        _resolve_confidence_band("extreme")


# ---------------------------------------------------------------------------
# _build_concept_hops_filter (NEW; AND semantics)
# ---------------------------------------------------------------------------


def test_predicate_min_confidence_only():
    pred = _build_concept_hops_filter(min_confidence=0.7)
    assert pred is not None
    assert pred({"confidence_score": 0.8, "relation": "x"}) is True
    assert pred({"confidence_score": 0.6, "relation": "x"}) is False


def test_predicate_relations_empty_drops_all():
    """D-12: relations=[] means strict zero-match — drop every edge."""
    pred = _build_concept_hops_filter(relations=[])
    assert pred is not None
    assert pred({"confidence_score": 0.99, "relation": "implements"}) is False
    assert pred({"confidence_score": 0.5, "relation": "tests"}) is False


def test_predicate_relations_none_keeps_all():
    pred = _build_concept_hops_filter(min_confidence=0.0)
    # min_confidence=0.0 with no other gate → keeps edges with any score
    assert pred is not None
    assert pred({"confidence_score": 0.1, "relation": "anything"}) is True
    assert pred({"confidence_score": 0.99, "relation": "whatever"}) is True


def test_predicate_band_and_min_confidence_AND():
    """D-11: AND semantics across all three gates."""
    pred = _build_concept_hops_filter(min_confidence=0.8, confidence_band="high")
    assert pred is not None
    assert pred({"confidence_score": 0.85, "relation": "x"}) is True
    # 0.79 fails both gates (band high requires >=0.8)
    assert pred({"confidence_score": 0.79, "relation": "x"}) is False
    # 0.8 passes min_confidence and band high
    assert pred({"confidence_score": 0.8, "relation": "x"}) is True


def test_predicate_band_and_relations_AND():
    pred = _build_concept_hops_filter(
        confidence_band="high", relations=["implements"]
    )
    assert pred is not None
    assert pred({"confidence_score": 0.9, "relation": "implements"}) is True
    # right relation, wrong band
    assert pred({"confidence_score": 0.6, "relation": "implements"}) is False
    # right band, wrong relation
    assert pred({"confidence_score": 0.9, "relation": "tests"}) is False


def test_predicate_all_none_is_identity():
    """D-13: all three None → return None to preserve v1.12 byte-identity."""
    pred = _build_concept_hops_filter(
        min_confidence=None, relations=None, confidence_band=None
    )
    assert pred is None


def test_predicate_missing_confidence_score_with_min():
    pred = _build_concept_hops_filter(min_confidence=0.5)
    assert pred is not None
    # Missing score should fail a min_confidence gate
    assert pred({"relation": "x"}) is False


def test_predicate_missing_confidence_score_with_band():
    pred = _build_concept_hops_filter(confidence_band="medium")
    assert pred is not None
    assert pred({"relation": "x"}) is False


# ---------------------------------------------------------------------------
# Phase 67 Plan 04 — CQUERY-01 BFS integration + CQUERY-02 byte-identity oracle
# ---------------------------------------------------------------------------

import json
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from graphify.serve import _run_concept_code_hops, QUERY_GRAPH_META_SENTINEL


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cquery_v1_12"


def _load_fixture_graph() -> nx.Graph:
    with open(_FIXTURE_DIR / "graph.json") as f:
        data = json.load(f)
    return json_graph.node_link_graph(data, edges="links")


def _invoke(arguments: dict) -> tuple[str, dict]:
    G = _load_fixture_graph()
    raw = _run_concept_code_hops(G, {}, arguments)
    text_body, _, meta_json = raw.partition(QUERY_GRAPH_META_SENTINEL)
    return text_body, json.loads(meta_json)


def test_v1_12_byte_identity():
    """CQUERY-02: with no new kwargs, output is deep-equal to the frozen golden."""
    G = _load_fixture_graph()
    raw = _run_concept_code_hops(G, {}, {"entity": "Authentication"})
    text_body, _, meta_json = raw.partition(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(meta_json)
    with open(_FIXTURE_DIR / "golden_concept_code_hops.json") as f:
        golden = json.load(f)
    result = {"text_body": text_body, "meta": meta}
    expected = {"text_body": golden["text_body"], "meta": golden["meta"]}
    assert result == expected


def test_min_confidence_filters_low_score_edge():
    args_low = {
        "entity": "Authentication",
        "relations": ["implements", "documents"],
        "min_confidence": 0.7,
    }
    _, meta = _invoke(args_low)
    # auth.md (documents, 0.65) should be excluded by min_confidence=0.7
    assert "file_auth_md" not in meta["reachable_node_ids"]


def test_relations_filter_empty_returns_zero_edges():
    args = {"entity": "Authentication", "relations_filter": []}
    _, meta = _invoke(args)
    # zero-match: only the start node remains
    assert meta["reachable_node_ids"] == ["concept_auth"]
    assert meta["traversal_steps"] == 0


def test_relations_filter_whitelist_only_tests():
    args = {
        "entity": "Authentication",
        "relations": ["implements", "tests"],
        "relations_filter": ["tests"],
    }
    _, meta = _invoke(args)
    # tests edge needs file_auth_py reachable first via implements; that
    # implements edge is excluded by relations_filter=['tests'], so only the
    # start node remains.
    assert meta["reachable_node_ids"] == ["concept_auth"]


def test_confidence_band_high_keeps_only_high_edges():
    args = {
        "entity": "Authentication",
        "relations": ["implements", "documents", "tests"],
        "confidence_band": "high",
    }
    _, meta = _invoke(args)
    assert "file_auth_py" in meta["reachable_node_ids"]
    assert "file_auth_md" not in meta["reachable_node_ids"]


def test_AND_semantics_min_confidence_and_band():
    # min_confidence=0.9 + confidence_band="high" excludes the 0.85 tests edge
    # (passes band high>=0.8 but fails min_confidence>=0.9).
    args = {
        "entity": "Authentication",
        "relations": ["implements", "tests"],
        "min_confidence": 0.9,
        "confidence_band": "high",
    }
    _, meta = _invoke(args)
    assert "file_auth_py" in meta["reachable_node_ids"]
    assert "file_test_auth_py" not in meta["reachable_node_ids"]


def test_invalid_confidence_band_raises():
    args = {"entity": "Authentication", "confidence_band": "BOGUS"}
    with pytest.raises(ValueError):
        _invoke(args)
