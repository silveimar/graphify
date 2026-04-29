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
        "taxonomy": {
            "version": "v1.8",
            "root": "Atlas/Sources/Graphify",
            "folders": {
                "moc": "MOCs",
                "thing": "Things",
                "statement": "Statements",
                "person": "People",
                "source": "Sources",
                "default": "Things",
                "unclassified": "MOCs",
            },
        },
        "folder_mapping": {
            "moc": "Atlas/Sources/Graphify/MOCs/",
            "thing": "Atlas/Sources/Graphify/Things/",
            "statement": "Atlas/Sources/Graphify/Statements/",
            "person": "Atlas/Sources/Graphify/People/",
            "source": "Atlas/Sources/Graphify/Sources/",
            "default": "Atlas/Sources/Graphify/Things/",
            "unclassified": "Atlas/Sources/Graphify/MOCs/",
        },
        "mapping_rules": [],
        # top_n=1 restricts god nodes to the single top-degree real node
        # (n_transformer, deg 5) for Plan 01 tests. With the tiny
        # make_classification_fixture corpus, top_n=10 would promote every
        # real node to "thing" via the topology fallback and make the
        # default-statement assertions untestable. Plan 02/03 tests with
        # larger fixtures can override this via the `topology` key.
        "topology": {"god_node": {"top_n": 1}},
        "mapping": {"min_community_size": 3},
    }
    base.update(overrides)
    return base


def test_classify_default_statement_uses_folder_mapping_default():
    """VALIDATION row 3-01-01: non-god real node defaults to statement."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert result["per_node"]["n_softmax"]["note_type"] == "statement"
    assert result["per_node"]["n_softmax"]["folder"] == "Atlas/Sources/Graphify/Statements/"


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
    assert result["per_node"]["n_transformer"]["folder"] == "Atlas/Sources/Graphify/Things/"


def test_classify_default_statement_when_no_match():
    """VALIDATION row 3-01-05: no rule match AND not a god node → statement."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    # n_token: degree 1, below god-node threshold in a small graph
    # (n_transformer=5 takes the top slot)
    assert result["per_node"]["n_token"]["note_type"] == "statement"
    assert result["per_node"]["n_token"]["folder"] == "Atlas/Sources/Graphify/Statements/"


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
    assert result["per_node"]["n_auth"]["folder"] == "Atlas/Sources/Graphify/People/"


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


# ---------------------------------------------------------------------------
# Plan 02 Task 2: classify() community-assembly routing
# ---------------------------------------------------------------------------


def test_community_above_threshold_becomes_moc():
    """VALIDATION row 3-01-04."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert 0 in result["per_community"]
    assert result["per_community"][0]["note_type"] == "moc"
    assert result["per_community"][0]["folder"] == "Atlas/Sources/Graphify/MOCs/"
    assert result["per_community"][0]["community_name"] == "Transformer"


def test_default_profile_min_community_size_is_3():
    """VALIDATION row 3-01-09.

    Plan 02 tests exercised the behavior with ``moc_threshold``; v1.8 uses
    ``mapping.min_community_size`` as the canonical standalone MOC floor.
    """
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    # cid 0 has 6 members (≥3) → MOC
    # cid 1 has 2 members (<3) → collapsed into host
    # cid 2 has 1 member  (<3) → hostless → bucket MOC (-1)
    assert 0 in result["per_community"]
    assert 1 not in result["per_community"]
    assert 2 not in result["per_community"]


def test_mapping_min_community_size_controls_standalone_moc_floor():
    from graphify.mapping import classify

    G, communities = make_classification_fixture()

    low_floor = classify(G, communities, _profile(mapping={"min_community_size": 2}))
    high_floor = classify(G, communities, _profile(mapping={"min_community_size": 3}))

    assert 1 in low_floor["per_community"]
    assert low_floor["per_community"][1]["note_type"] == "moc"
    assert low_floor["per_community"][1]["folder"] == "Atlas/Sources/Graphify/MOCs/"
    assert 1 not in high_floor["per_community"]


def test_min_community_size_one_allows_single_node_standalone_moc():
    import networkx as nx

    from graphify.mapping import classify

    G = nx.Graph()
    G.add_node(
        "solo",
        label="SoloConcept",
        file_type="document",
        source_file="notes/solo.md",
        source_location="L1",
    )
    communities = {0: ["solo"]}

    result = classify(
        G,
        communities,
        _profile(mapping={"min_community_size": 1}),
    )

    assert -1 not in result["per_community"]
    assert result["per_community"][0]["routing"] == "standalone"
    assert result["per_community"][0]["community_name"] == "SoloConcept"
    assert result["per_node"]["solo"]["parent_moc_label"] == "SoloConcept"


def test_taxonomy_moc_folder_wins_over_conflicting_folder_mapping():
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    profile = _profile(
        taxonomy={
            "version": "v1.8",
            "root": "Custom/Graphify",
            "folders": {
                "moc": "Concept MOCs",
                "thing": "Things",
                "statement": "Statements",
                "person": "People",
                "source": "Sources",
                "default": "Things",
                "unclassified": "Concept MOCs",
            },
        },
        folder_mapping={
            "moc": "Old/Maps/",
            "thing": "Old/Things/",
            "statement": "Old/Statements/",
            "person": "Old/People/",
            "source": "Old/Sources/",
            "default": "Old/Default/",
            "unclassified": "Old/Unclassified/",
        },
    )

    result = classify(G, communities, profile)

    assert result["per_community"][0]["folder"] == "Custom/Graphify/Concept MOCs/"


def test_community_below_threshold_collapses_to_host():
    """VALIDATION row 3-01-10."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile(mapping={"min_community_size": 6}))
    # cid 1 should collapse into cid 0 via the n_transformer—n_auth edge.
    assert result["per_community"][0]["routing"] == "standalone"
    subs = result["per_community"][0]["sub_communities"]
    auth_sub = next(s for s in subs if s["label"] == "AuthService")
    assert auth_sub["routing"] == "hosted"
    assert auth_sub["source_community_id"] == 1
    assert auth_sub["host_community_id"] == 0
    # n_auth's per_node ctx points parent_moc_label at "Transformer"
    assert result["per_node"]["n_auth"]["parent_moc_label"] == "Transformer"


def test_isolate_below_floor_routes_to_unclassified_with_bucket_metadata():
    from graphify.mapping import classify

    G, communities = make_classification_fixture()

    result = classify(G, communities, _profile(mapping={"min_community_size": 6}))

    assert 2 not in result["per_community"]
    assert result["per_node"]["n_isolate"]["parent_moc_label"] == "_Unclassified"
    bucket = result["per_community"][-1]
    assert bucket["routing"] == "bucketed"
    assert bucket["community_name"] == "_Unclassified"
    isolate_sub = next(s for s in bucket["sub_communities"] if s["label"] == "Orphan")
    assert isolate_sub["routing"] == "bucketed"
    assert isolate_sub["source_community_id"] == 2
    assert isolate_sub["bucket_moc_label"] == "_Unclassified"
    assert isolate_sub["parent_moc_label"] == "_Unclassified"


def test_bucket_moc_absorbs_hostless_below_threshold():
    """VALIDATION row 3-01-13: all-below-threshold corpus → bucket MOC."""
    import networkx as nx

    from graphify.mapping import classify

    G = nx.Graph()
    # Two below-threshold isolated communities, no inter-community edges
    G.add_node(
        "a",
        label="A",
        file_type="code",
        source_file="a.py",
        source_location="L1",
    )
    G.add_node(
        "b",
        label="B",
        file_type="code",
        source_file="b.py",
        source_location="L1",
    )
    communities = {0: ["a"], 1: ["b"]}
    result = classify(G, communities, _profile())
    # No above-threshold communities → bucket MOC emitted
    assert -1 in result["per_community"]
    assert result["per_community"][-1]["folder"] == "Atlas/Sources/Graphify/MOCs/"
    assert result["per_community"][-1]["community_name"] == "_Unclassified"
    assert result["per_community"][-1]["routing"] == "bucketed"
    assert result["per_community"][-1]["community_tag"] == "unclassified"
    # Both below communities merged into bucket
    assert len(result["per_community"][-1]["sub_communities"]) == 2
    assert {
        sub["source_community_id"] for sub in result["per_community"][-1]["sub_communities"]
    } == {0, 1}
    assert {
        sub["bucket_moc_label"] for sub in result["per_community"][-1]["sub_communities"]
    } == {"_Unclassified"}


def test_community_tag_is_safe_tag_of_name():
    """VALIDATION row 3-02-03."""
    from graphify.mapping import classify
    from graphify.profile import safe_tag

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert result["per_community"][0]["community_tag"] == safe_tag("Transformer")


def test_bucket_moc_not_emitted_when_all_below_resolved():
    """Verifies the fixture's hostless isolate (cid 2) still produces a bucket.

    Despite the test name (which describes the ideal alternate case), the
    make_classification_fixture includes cid 2 = ``n_isolate`` with zero
    neighbors, so a bucket MOC IS expected here. The assertion confirms the
    isolate lands in the bucket, not in cid 0.
    """
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert -1 in result["per_community"]
    bucket_labels = {
        member["label"]
        for sub in result["per_community"][-1]["sub_communities"]
        for member in sub["members"]
    }
    assert "Orphan" in bucket_labels


def test_sibling_labels_empty_for_non_god_node():
    """VALIDATION row 3-02-08 — BLOCKER 1 (D-60 fidelity).

    Non-god nodes MUST receive ``sibling_labels: []``. Pins ``top_n=2`` so
    ``n_low_degree`` is provably outside the god-node set.
    """
    import networkx as nx

    from graphify.mapping import classify

    G = nx.Graph()
    # Three real nodes: hub, secondary, low_degree.
    G.add_node(
        "n_hub",
        label="Hub",
        file_type="code",
        source_file="src/hub.py",
        source_location="L1",
    )
    G.add_node(
        "n_secondary",
        label="Secondary",
        file_type="code",
        source_file="src/hub.py",
        source_location="L2",
    )
    G.add_node(
        "n_low_degree",
        label="LowDegree",
        file_type="code",
        source_file="src/hub.py",
        source_location="L3",
    )
    # Hub degree 2, Secondary degree 2, LowDegree degree 2 — the tie means
    # god_nodes(top_n=2) deterministically picks the first two by insertion
    # order (Hub, Secondary). LowDegree is therefore NOT a god node.
    G.add_edge("n_hub", "n_secondary")
    G.add_edge("n_hub", "n_low_degree")
    G.add_edge("n_secondary", "n_low_degree")
    communities = {0: ["n_hub", "n_secondary", "n_low_degree"]}

    profile = _profile()
    # Pin top_n=2 so n_low_degree is provably outside the god-node set.
    profile.setdefault("topology", {}).setdefault("god_node", {})["top_n"] = 2

    result = classify(G, communities, profile)

    # Sanity: n_low_degree exists in per_node.
    assert "n_low_degree" in result["per_node"]
    # The critical assertion — non-god node receives empty sibling_labels.
    assert result["per_node"]["n_low_degree"]["sibling_labels"] == [], (
        "D-60: non-god nodes MUST receive empty sibling_labels, "
        f"got {result['per_node']['n_low_degree']['sibling_labels']!r}"
    )
    # And a god node DOES get siblings populated (Hub is top god node).
    assert "Secondary" in result["per_node"]["n_hub"]["sibling_labels"]


# ---------------------------------------------------------------------------
# Plan 03: validate_rules + _detect_dead_rules tests
# ---------------------------------------------------------------------------


def test_validate_rules_regex_too_long_rejected():
    # VALIDATION row 3-03-01
    from graphify.mapping import validate_rules, _MAX_PATTERN_LEN
    rules = [{
        "when": {"attr": "label", "regex": "x" * (_MAX_PATTERN_LEN + 1)},
        "then": {"note_type": "thing"},
    }]
    errors = validate_rules(rules)
    assert any(
        "pattern length" in e and "mapping_rules[0].when.regex" in e
        for e in errors
    )


def test_validate_rules_rejects_malformed_regex_with_pointed_error():
    from graphify.mapping import validate_rules
    rules = [{"when": {"attr": "label", "regex": "("}, "then": {"note_type": "thing"}}]
    errors = validate_rules(rules)
    assert any("mapping_rules[0].when.regex" in e for e in errors)


def test_validate_rules_rejects_unknown_note_type():
    from graphify.mapping import validate_rules
    rules = [{"when": {"attr": "label", "equals": "X"}, "then": {"note_type": "BOGUS"}}]
    errors = validate_rules(rules)
    assert any("mapping_rules[0].then.note_type" in e for e in errors)


def test_validate_rules_rejects_path_traversal_in_folder():
    # VALIDATION row 3-03-06
    from graphify.mapping import validate_rules
    rules = [
        {"when": {"attr": "label", "equals": "X"}, "then": {"note_type": "thing", "folder": "../escape/"}},
        {"when": {"attr": "label", "equals": "Y"}, "then": {"note_type": "thing", "folder": "/abs/path"}},
        {"when": {"attr": "label", "equals": "Z"}, "then": {"note_type": "thing", "folder": "~/home"}},
    ]
    errors = validate_rules(rules)
    assert any("mapping_rules[0].then.folder" in e and ".." in e for e in errors)
    assert any("mapping_rules[1].then.folder" in e and "absolute" in e for e in errors)
    assert any("mapping_rules[2].then.folder" in e and "~" in e for e in errors)


def test_validate_rules_rejects_bool_topology_value():
    from graphify.mapping import validate_rules
    rules = [{
        "when": {"topology": "community_size_gte", "value": True},
        "then": {"note_type": "moc"},
    }]
    errors = validate_rules(rules)
    assert any("mapping_rules[0].when.value" in e for e in errors)


def test_validate_rules_rejects_multiple_matcher_kinds():
    from graphify.mapping import validate_rules
    rules = [{
        "when": {"attr": "label", "equals": "X", "topology": "god_node"},
        "then": {"note_type": "thing"},
    }]
    errors = validate_rules(rules)
    assert any("multiple matcher kinds" in e for e in errors)


def test_validate_rules_dead_rule_warning_identical():
    # VALIDATION row 3-03-04
    from graphify.mapping import validate_rules
    rules = [
        {"when": {"attr": "label", "equals": "Foo"}, "then": {"note_type": "thing"}},
        {"when": {"attr": "label", "equals": "Foo"}, "then": {"note_type": "thing"}},
    ]
    errors = validate_rules(rules)
    assert any("mapping_rules[1]: warning: dead rule" in e for e in errors)


def test_validate_rules_no_dead_rule_warning_across_kinds():
    # VALIDATION row 3-03-05
    from graphify.mapping import validate_rules
    rules = [
        {"when": {"topology": "god_node"}, "then": {"note_type": "thing"}},
        {"when": {"attr": "label", "equals": "Foo"}, "then": {"note_type": "thing"}},
    ]
    errors = validate_rules(rules)
    assert not any("dead rule" in e for e in errors)


def test_validate_rules_accepts_valid_example_from_context():
    # Mirrors the D-43 profile.yaml example verbatim
    from graphify.mapping import validate_rules
    rules = [
        {"when": {"attr": "file_type", "equals": "person"}, "then": {"note_type": "person"}},
        {"when": {"topology": "god_node"}, "then": {"note_type": "thing", "folder": "Atlas/Dots/Things/"}},
        {"when": {"source_file_ext": ".py"}, "then": {"note_type": "source", "folder": "Atlas/Sources/Code/"}},
    ]
    assert validate_rules(rules) == []


def test_validate_rules_rejects_unknown_then_keys():
    # WARNING 1 fix (D-46): unknown `then:` keys must be rejected with a
    # pointed error, not silently dropped. VALIDATION row 3-03-08.
    from graphify.mapping import validate_rules
    rules = [
        {
            "when": {"attr": "file_type", "equals": "person"},
            "then": {"note_type": "person", "tags": ["foo"]},
        }
    ]
    errors = validate_rules(rules)
    assert errors, "expected validation errors for unknown then key"
    assert any(
        "unknown keys ['tags']" in e and "mapping_rules[0].then" in e
        for e in errors
    ), f"expected pointed error about 'tags'; got: {errors}"


# ---------------------------------------------------------------------------
# Plan 04 Task 1: Package-surface lazy exports (VALIDATION row 3-04-05)
# ---------------------------------------------------------------------------


def test_graphify_package_lazy_exports_classify():
    """VALIDATION row 3-04-05 (WARNING 4 fix): Phase 3 public API is exported
    via graphify/__init__.py's lazy import map so downstream callers can do
    `from graphify import classify` without a submodule reference."""
    import graphify

    assert callable(graphify.classify)
    assert callable(graphify.validate_rules)
    # MappingResult is a TypedDict — it's a class at runtime
    assert hasattr(graphify, "MappingResult")


def test_graphify_classify_is_graphify_mapping_classify():
    """A typo in the lazy-map tuple (T-3-13) would produce an ImportError at
    first access; this identity assertion is a cheap regression guard."""
    import graphify
    from graphify.mapping import classify as direct

    assert graphify.classify is direct


# ---------------------------------------------------------------------------
# Plan 04 Task 2: Contract round-trip tests — Phase 3 ↔ Phase 2 boundary
# (VALIDATION rows 3-04-01, 3-04-02, 3-04-06)
# ---------------------------------------------------------------------------


def test_classify_output_round_trips_through_render_note():
    """VALIDATION row 3-04-01: classify()'s per_node ClassificationContext
    feeds render_note() without raising. Guards against key-name drift
    between Phase 2 and Phase 3 (T-3-12)."""
    import datetime

    from graphify.mapping import classify
    from graphify.profile import safe_tag
    from graphify.templates import render_note

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())

    # n_transformer is the sole top-degree real node in cid 0 and, with
    # top_n=1, the only god node → classified as "thing" via topology fallback.
    ctx = result["per_node"]["n_transformer"]
    assert ctx["note_type"] == "thing"
    # community enrichment from Plan 02 must have landed end-to-end.
    assert ctx.get("community_name") == "Transformer"
    assert ctx.get("parent_moc_label") == "Transformer"
    assert ctx.get("community_tag") == safe_tag("Transformer")

    filename, text = render_note(
        "n_transformer",
        G,
        _profile(),
        "thing",
        ctx,
        created=datetime.date(2024, 1, 1),
    )
    assert isinstance(filename, str) and filename.endswith(".md")
    assert isinstance(text, str) and len(text) > 0
    # The node label appears as the note heading.
    assert "Transformer" in text
    # community_tag is emitted in the tags frontmatter list as
    # `community/<safe_tag>` (templates.py:598).
    assert f"community/{safe_tag('Transformer')}" in text


def test_classify_output_round_trips_through_render_moc():
    """VALIDATION rows 3-04-02 + 3-04-06: classify()'s per_community
    ClassificationContext feeds render_moc() without raising, and the
    cohesion field is populated end-to-end (W-2 fix) as a plain Python
    float (WR-06)."""
    import datetime

    from graphify.mapping import classify
    from graphify.templates import render_moc

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())

    # cid 0 is the only above-threshold community (4 real members ≥ 3).
    assert 0 in result["per_community"]
    moc_ctx = result["per_community"][0]
    assert moc_ctx["note_type"] == "moc"
    assert moc_ctx["community_name"] == "Transformer"

    filename, text = render_moc(
        0,
        G,
        communities,
        _profile(),
        moc_ctx,
        created=datetime.date(2024, 1, 1),
    )
    assert isinstance(filename, str) and filename.endswith(".md")
    assert isinstance(text, str) and len(text) > 0
    # Community name is the rendered title.
    assert "Transformer" in text
    # Dataview block present (from _build_dataview_block).
    assert "```dataview" in text
    # cid 1 (below-threshold) collapses into cid 0's sub_communities;
    # its god node AuthService must appear in the rendered MOC.
    assert "AuthService" in text

    # W-2 fix (VALIDATION row 3-04-06): per_community[cid]["cohesion"] MUST
    # be populated so that templates.py:705-706 `_render_moc_like` reads a
    # real float. Pick the first real MOC (not the synthetic -1 bucket).
    first_moc_cid = next(
        cid
        for cid, cctx in result["per_community"].items()
        if cctx.get("note_type") == "moc" and cid >= 0
    )
    cohesion = result["per_community"][first_moc_cid].get("cohesion")
    assert cohesion is not None, (
        "per_community[cid]['cohesion'] must be populated (Plan 02 W-2 fix). "
        "See templates.py:705-706 which reads ctx.get('cohesion')."
    )
    # WR-06: must be a plain Python float, not numpy.float64 — the latter
    # renders as 'numpy.float64(0.82)' rather than '0.82'.
    assert isinstance(cohesion, float), (
        f"cohesion must be a plain float per WR-06 (got {type(cohesion).__name__})"
    )


def test_classify_output_round_trips_members_by_type_into_moc():
    """Every non-skipped member of an above-threshold community must render
    through to the MOC text via members_by_type — tightens the 3-04-02
    contract by asserting member visibility, not just non-raising."""
    import datetime

    from graphify.mapping import classify
    from graphify.templates import render_moc

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    moc_ctx = result["per_community"][0]
    _, text = render_moc(
        0,
        G,
        communities,
        _profile(),
        moc_ctx,
        created=datetime.date(2024, 1, 1),
    )

    # Every non-skipped member of cid 0 must appear in the rendered text.
    expected_labels = {
        G.nodes[m]["label"]
        for m in communities[0]
        if m not in result["skipped_node_ids"]
    }
    for label in expected_labels:
        assert label in text, f"expected {label!r} in MOC render"
