"""Unit tests for graphify.mapping classify() + matchers (Phase 3, Plan 01)."""
from __future__ import annotations

from tests.fixtures.template_context import make_classification_fixture


def test_fixture_degrees_match_contract() -> None:
    G, communities = make_classification_fixture()
    # Degree contract — load-bearing for god-node ranking in Plan 01/02 tests.
    assert G.degree("n_transformer") == 5
    assert G.degree("n_auth") == 2
    assert G.degree("n_isolate") == 0
    # Community partition contract
    assert len(communities) == 3
    assert len(communities[0]) == 6
    assert len(communities[1]) == 2
    assert len(communities[2]) == 1
    # Synthetic-node membership contract — D-50 filter tests depend on both
    # a file hub and a concept node being present in cid 0.
    assert "n_file_model" in G.nodes
    assert "n_concept_attn" in G.nodes


# ---------------------------------------------------------------------------
# Task 2: compile_rules + _match_when matcher dispatch tests
# ---------------------------------------------------------------------------


def test_compile_rules_rejects_malformed_regex():
    import pytest

    from graphify.mapping import compile_rules

    with pytest.raises(ValueError, match=r"mapping_rules\[0\].when.regex"):
        compile_rules([
            {"when": {"attr": "label", "regex": "("}, "then": {"note_type": "thing"}}
        ])


def test_compile_rules_stores_compiled_pattern_under_private_key():
    from graphify.mapping import _COMPILED_KEY, compile_rules

    compiled = compile_rules([
        {"when": {"attr": "label", "regex": "^Transformer$"},
         "then": {"note_type": "thing"}}
    ])
    assert _COMPILED_KEY in compiled[0]["when"]


def test_match_when_attr_regex_candidate_too_long_returns_false():
    """VALIDATION row 3-03-02: ReDoS guard on long candidate strings."""
    import re as _re

    from graphify.mapping import _COMPILED_KEY, _MatchCtx, _match_when
    from tests.fixtures.template_context import make_classification_fixture

    G, _ = make_classification_fixture()
    G.nodes["n_transformer"]["label"] = "x" * 5000
    when = {"attr": "label", "regex": "x+", _COMPILED_KEY: _re.compile("x+")}
    ctx = _MatchCtx(
        node_to_community={},
        community_sizes={},
        cohesion={},
        god_node_ids=frozenset(),
    )
    assert _match_when(when, "n_transformer", G, ctx=ctx) is False


def test_match_when_non_string_attr_contains_returns_false():
    """VALIDATION row 3-03-03: non-string attr fed to contains returns False, no crash."""
    from graphify.mapping import _MatchCtx, _match_when
    from tests.fixtures.template_context import make_classification_fixture

    G, _ = make_classification_fixture()
    G.nodes["n_transformer"]["count"] = 42  # non-string attribute
    when = {"attr": "count", "contains": "4"}
    ctx = _MatchCtx(
        node_to_community={},
        community_sizes={},
        cohesion={},
        god_node_ids=frozenset(),
    )
    assert _match_when(when, "n_transformer", G, ctx=ctx) is False
