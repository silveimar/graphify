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
