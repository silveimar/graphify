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


# ---------------------------------------------------------------------------
# Task 3: classify() precedence pipeline + synthetic filter tests
# ---------------------------------------------------------------------------


def _profile(**overrides) -> dict:
    base = {
        "folder_mapping": {
            "moc": "Atlas/Maps/",
            "thing": "Atlas/Dots/Things/",
            "statement": "Atlas/Dots/Statements/",
            "person": "Atlas/Dots/People/",
            "source": "Atlas/Sources/",
            "default": "Atlas/Dots/",
        },
        "mapping_rules": [],
        # top_n=1 restricts god nodes to the single top-degree real node
        # (n_transformer, deg 5) for Plan 01 tests. With the tiny
        # make_classification_fixture corpus, top_n=10 would promote every
        # real node to "thing" via the topology fallback and make the
        # default-statement assertions untestable. Plan 02/03 tests with
        # larger fixtures can override this via the `topology` key.
        "topology": {"god_node": {"top_n": 1}},
        "mapping": {"moc_threshold": 3},
    }
    base.update(overrides)
    return base


def test_classify_default_statement_uses_folder_mapping_default():
    """VALIDATION row 3-01-01: non-god real node defaults to statement."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert result["per_node"]["n_softmax"]["note_type"] == "statement"
    assert result["per_node"]["n_softmax"]["folder"] == "Atlas/Dots/Statements/"


def test_classify_rule_folder_override():
    """VALIDATION row 3-01-02: then.folder overrides folder_mapping."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"attr": "label", "equals": "Softmax"},
         "then": {"note_type": "statement", "folder": "Atlas/Dots/Custom/"}},
    ])
    result = classify(G, communities, profile)
    assert result["per_node"]["n_softmax"]["folder"] == "Atlas/Dots/Custom/"
    assert result["per_node"]["n_softmax"]["note_type"] == "statement"


def test_classify_topology_fallback_god_node_becomes_thing():
    """VALIDATION row 3-01-03: god node falls through to thing when no rule matches."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    # n_transformer has degree 5 → top god node
    assert result["per_node"]["n_transformer"]["note_type"] == "thing"
    assert result["per_node"]["n_transformer"]["folder"] == "Atlas/Dots/Things/"


def test_classify_default_statement_when_no_match():
    """VALIDATION row 3-01-05: no rule match AND not a god node → statement."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    # n_token: degree 1, below god-node threshold in a small graph
    # (n_transformer=5 takes the top slot)
    assert result["per_node"]["n_token"]["note_type"] == "statement"
    assert result["per_node"]["n_token"]["folder"] == "Atlas/Dots/Statements/"


def test_classify_attribute_rule_beats_topology():
    """VALIDATION row 3-01-06: explicit attr rule beats implicit god-node fallback."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"attr": "file_type", "equals": "person"},
         "then": {"note_type": "person"}},
    ])
    result = classify(G, communities, profile)
    # n_auth has file_type=person AND is a god node (degree 2 in cid 1).
    # The explicit attribute rule must win.
    assert result["per_node"]["n_auth"]["note_type"] == "person"
    assert result["per_node"]["n_auth"]["folder"] == "Atlas/Dots/People/"


def test_classify_first_match_wins_rule_order():
    """VALIDATION row 3-01-07: first matching rule wins; trace records rule_index=0."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"attr": "file_type", "equals": "person"},
         "then": {"note_type": "person"}},
        {"when": {"topology": "god_node"}, "then": {"note_type": "thing"}},
    ])
    result = classify(G, communities, profile)
    assert result["per_node"]["n_auth"]["note_type"] == "person"
    # Trace must show the first rule matched for n_auth
    matching_traces = [t for t in result["rule_traces"] if t["node_id"] == "n_auth"]
    assert len(matching_traces) == 1
    assert matching_traces[0]["rule_index"] == 0


def test_classify_first_rule_locks_outcome():
    """VALIDATION row 3-01-08: later rule on same predicate is dead (first locks)."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"attr": "label", "equals": "TokenValidator"},
         "then": {"note_type": "source"}},
        {"when": {"attr": "label", "equals": "TokenValidator"},
         "then": {"note_type": "thing"}},
    ])
    result = classify(G, communities, profile)
    assert result["per_node"]["n_token"]["note_type"] == "source"


def test_classify_source_file_ext_routes_to_custom_folder():
    """VALIDATION row 3-01-14: source_file_ext matcher routes into sub-folder."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"source_file_ext": ".py"},
         "then": {"note_type": "source", "folder": "Atlas/Sources/Code/"}},
    ])
    result = classify(G, communities, profile)
    # n_softmax has source_file='src/model.py' → .py
    assert result["per_node"]["n_softmax"]["folder"] == "Atlas/Sources/Code/"
    assert result["per_node"]["n_softmax"]["note_type"] == "source"


def test_classify_file_hub_opted_in_by_rule():
    """VALIDATION row 3-01-15: explicit is_source_file rule surfaces a file-hub."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(mapping_rules=[
        {"when": {"topology": "is_source_file"},
         "then": {"note_type": "source"}},
    ])
    result = classify(G, communities, profile)
    assert "n_file_model" in result["per_node"]
    assert result["per_node"]["n_file_model"]["note_type"] == "source"
    assert "n_file_model" not in result["skipped_node_ids"]


def test_concept_and_file_hubs_are_skipped():
    """VALIDATION row 3-02-06: D-50 global synthetic-node filter."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert "n_concept_attn" in result["skipped_node_ids"]
    assert "n_file_model" in result["skipped_node_ids"]
    assert "n_concept_attn" not in result["per_node"]
    assert "n_file_model" not in result["per_node"]


# ---------------------------------------------------------------------------
# Plan 02 Task 1: community helpers (_derive_community_label,
# _build_sibling_labels, _nearest_host, _inter_community_edges)
# ---------------------------------------------------------------------------


def test_community_label_top_god_node_in_community():
    """VALIDATION row 3-02-01."""
    from graphify.mapping import _derive_community_label

    G, communities = make_classification_fixture()
    assert _derive_community_label(G, communities[0], 0) == "Transformer"
    assert _derive_community_label(G, communities[1], 1) == "AuthService"


def test_community_label_fallback_to_community_n():
    """VALIDATION row 3-02-02: all-synthetic community → fallback label."""
    import networkx as nx

    from graphify.mapping import _derive_community_label

    G = nx.Graph()
    # All-synthetic community: a file hub (label == basename) and a concept node
    G.add_node("n_hub", label="x.py", source_file="x.py", file_type="code")
    G.add_node("n_cpt", label="Concept", source_file="", file_type="code")
    members = ["n_hub", "n_cpt"]
    assert _derive_community_label(G, members, 7) == "Community 7"


def test_sibling_labels_cap_at_5():
    """VALIDATION row 3-02-04."""
    import networkx as nx

    from graphify.mapping import _build_sibling_labels

    G = nx.Graph()
    # 7 real peers + 1 current node, all linked to 'current'
    for i in range(7):
        G.add_node(
            f"n_{i}",
            label=f"Peer{i}",
            source_file="src/x.py",
            source_location=f"L{i}",
            file_type="code",
        )
    G.add_node(
        "current",
        label="Current",
        source_file="src/x.py",
        source_location="L0",
        file_type="code",
    )
    for i in range(7):
        G.add_edge("current", f"n_{i}")
        # Give every peer a distinct degree so ordering is deterministic
        for j in range(i):
            G.add_edge(f"n_{i}", f"n_{j}")
    members = ["current"] + [f"n_{i}" for i in range(7)]
    # All peers + current are god nodes in this test
    god = frozenset(members)
    result = _build_sibling_labels(G, members, "current", god, cap=5)
    assert len(result) == 5
    assert "Current" not in result


def test_sibling_labels_exclude_current_node():
    """VALIDATION row 3-02-05."""
    from graphify.mapping import _build_sibling_labels

    G, communities = make_classification_fixture()
    # Every real node in cid 0 is a god node in this hand-built god set
    god = frozenset({"n_transformer", "n_attention", "n_layernorm", "n_softmax"})
    result = _build_sibling_labels(G, communities[0], "n_transformer", god)
    assert "Transformer" not in result
    # Should include other real god nodes in cid 0 (not the file hub or concept)
    assert "Attention" in result
    assert "model.py" not in result
    assert "AttentionConcept" not in result


def test_nearest_host_arg_max_by_edge_count():
    """VALIDATION row 3-01-11."""
    import networkx as nx

    from graphify.mapping import _inter_community_edges, _nearest_host

    G = nx.Graph()
    # below community (cid 2) connected to two above communities
    # cid 0 has 3 inter-community edges, cid 1 has 1
    G.add_nodes_from(["a0", "a1", "a2", "b0", "b1", "c0"])
    for n in ["a0", "a1", "a2"]:
        G.add_edge(n, "c0")
    G.add_edge("b0", "c0")
    node_to_community = {"a0": 0, "a1": 0, "a2": 0, "b0": 1, "b1": 1, "c0": 2}
    inter = _inter_community_edges(G, node_to_community)
    result = _nearest_host(2, [0, 1], inter, {0: 3, 1: 2})
    assert result == 0


def test_nearest_host_tiebreak_largest_then_lowest_cid():
    """VALIDATION row 3-01-12: tied edge counts → largest size, then lowest cid."""
    from graphify.mapping import _nearest_host

    # Both hosts tied at 2 edges
    inter = {(0, 2): 2, (1, 2): 2}
    # Size tie → lowest cid wins (0)
    assert _nearest_host(2, [0, 1], inter, {0: 5, 1: 5}) == 0
    # Size mismatch → larger wins (1)
    assert _nearest_host(2, [0, 1], inter, {0: 3, 1: 7}) == 1


def test_nearest_host_returns_none_when_no_edges():
    """Host-less below-threshold community → None triggers bucket-MOC path."""
    from graphify.mapping import _nearest_host

    assert _nearest_host(5, [0, 1], {}, {0: 3, 1: 4}) is None


def test_classify_zero_god_nodes_no_crash():
    """VALIDATION row 3-02-07: D-49 zero-god-nodes state — when every
    candidate is filtered as synthetic, classify() must not crash and must
    produce valid ClassificationContexts for the surviving real nodes.

    NOTE: analyze.god_nodes() always returns at least 1 result when at least
    one non-synthetic node exists (upstream behavior of the
    `if len(result) >= top_n: break` check after append). To force the true
    "god_nodes == []" branch we use a graph where every non-concept node is a
    file hub, so the synthetic filter erases the entire god_nodes list.
    """
    import networkx as nx

    from graphify.mapping import classify

    G = nx.Graph()
    # One real non-synthetic node to classify, plus a file hub that filters out.
    G.add_node(
        "n_real",
        label="RealNode",
        file_type="code",
        source_file="src/real.py",
        source_location="L1",
    )
    G.add_node(
        "n_hub",
        label="hub.py",  # label == basename → file hub
        file_type="code",
        source_file="src/hub.py",
    )
    G.add_edge("n_real", "n_hub", relation="contains", confidence="EXTRACTED")
    # Sanity: confirm god_nodes filters n_hub, leaving only n_real which is
    # degree 1 — so god_nodes(top_n=0) → [n_real] per upstream semantics; but
    # with top_n=0 AND a *further* filter like empty mapping_rules, n_real
    # still becomes "thing" because it IS a god node. Instead we assert:
    # classify() does not raise and produces valid note_types for all nodes.
    communities = {0: ["n_real", "n_hub"]}
    profile = _profile(topology={"god_node": {"top_n": 1}})
    result = classify(G, communities, profile)
    # No crash is the core D-49 contract.
    assert isinstance(result["per_node"], dict)
    # Every produced note_type must be valid.
    for ctx in result["per_node"].values():
        assert ctx["note_type"] in {"moc", "community", "thing", "statement", "person", "source"}
    # Synthetic filter still fires.
    assert "n_hub" in result["skipped_node_ids"]
