from __future__ import annotations

"""Unit tests for graphify/argue.py — zero-LLM argumentation substrate.

Covers ARGUE-01, ARGUE-02, ARGUE-03, ARGUE-05, ARGUE-06, ARGUE-08.
All tests are pure unit tests — no network calls, no filesystem side effects
outside tmp_path.
"""

import json
import math
from pathlib import Path

import networkx as nx
import pytest

from graphify.argue import (
    ArgumentPackage,
    MAX_TEMPERATURE,
    NodeCitation,
    PerspectiveSeed,
    ROUND_CAP,
    compute_overlap,
    populate,
    validate_turn,
)


# ---------------------------------------------------------------------------
# Shared fixture graph
# ---------------------------------------------------------------------------

def _make_argue_graph() -> nx.DiGraph:
    """Minimal graph for argue.py unit tests — 5 core pipeline nodes."""
    G = nx.DiGraph()
    nodes = [
        ("n_extract", "Extract", "graphify/extract.py"),
        ("n_build", "Build", "graphify/build.py"),
        ("n_cluster", "Cluster", "graphify/cluster.py"),
        ("n_analyze", "Analyze", "graphify/analyze.py"),
        ("n_report", "Report", "graphify/report.py"),
    ]
    for nid, label, src in nodes:
        G.add_node(nid, label=label, source_file=src)
    edges = [
        ("n_extract", "n_build"),
        ("n_build", "n_cluster"),
        ("n_cluster", "n_analyze"),
        ("n_analyze", "n_report"),
    ]
    for src, tgt in edges:
        G.add_edge(src, tgt, relation="imports", confidence="EXTRACTED")
    return G


# ---------------------------------------------------------------------------
# ARGUE-02: ArgumentPackage dataclass fields
# ---------------------------------------------------------------------------

def test_argument_package_fields() -> None:
    """ARGUE-02: ArgumentPackage has subgraph, perspectives, evidence fields."""
    G = _make_argue_graph()
    pkg = ArgumentPackage(subgraph=G, perspectives=[], evidence=[])
    assert hasattr(pkg, "subgraph")
    assert hasattr(pkg, "perspectives")
    assert hasattr(pkg, "evidence")
    assert isinstance(pkg.subgraph, nx.Graph)
    assert isinstance(pkg.perspectives, list)
    assert isinstance(pkg.evidence, list)


# ---------------------------------------------------------------------------
# ARGUE-02: Fixed 4 perspectives (D-01)
# ---------------------------------------------------------------------------

def test_four_perspectives() -> None:
    """ARGUE-02 D-01: populate always returns exactly 4 PerspectiveSeed lenses."""
    G = _make_argue_graph()
    pkg = populate(G, "extract")
    assert len(pkg.perspectives) == 4
    lens_names = [p.lens for p in pkg.perspectives]
    assert lens_names == ["security", "architecture", "complexity", "onboarding"]


# ---------------------------------------------------------------------------
# ARGUE-01: populate() returns ArgumentPackage
# ---------------------------------------------------------------------------

def test_populate_returns_argument_package() -> None:
    """ARGUE-01: populate(G, topic) returns ArgumentPackage with non-empty subgraph."""
    G = _make_argue_graph()
    pkg = populate(G, "extract")
    assert isinstance(pkg, ArgumentPackage)
    assert pkg.subgraph.number_of_nodes() >= 1
    assert len(pkg.evidence) >= 1


def test_populate_scope_subgraph() -> None:
    """ARGUE-01 D-03: scope='subgraph' includes specified node_ids."""
    G = _make_argue_graph()
    pkg = populate(G, "", scope="subgraph", node_ids=["n_extract"])
    assert "n_extract" in pkg.subgraph.nodes


def test_populate_scope_community() -> None:
    """ARGUE-01 D-03: scope='community' uses communities kwarg, includes members."""
    G = _make_argue_graph()
    communities = {0: ["n_extract", "n_build"]}
    pkg = populate(G, "", scope="community", community_id=0, communities=communities)
    assert "n_extract" in pkg.subgraph.nodes


def test_populate_empty_topic() -> None:
    """ARGUE-01: populate with empty topic returns empty ArgumentPackage (silent-ignore)."""
    G = _make_argue_graph()
    pkg = populate(G, "")
    assert pkg.subgraph.number_of_nodes() == 0
    assert pkg.perspectives == []
    assert pkg.evidence == []


def test_populate_budget_clamp() -> None:
    """ARGUE-01 D-02: budget clamps subgraph to at most budget nodes; giant budget clamps to <=100000."""
    G = _make_argue_graph()
    pkg_small = populate(G, "extract", budget=10)
    assert pkg_small.subgraph.number_of_nodes() <= 10

    pkg_huge = populate(G, "extract", budget=10**9)
    assert pkg_huge.subgraph.number_of_nodes() <= 100000


# ---------------------------------------------------------------------------
# ARGUE-05: validate_turn fabrication guard (D-08, D-10)
# ---------------------------------------------------------------------------

def test_validate_turn_valid() -> None:
    """ARGUE-05 D-08: validate_turn returns [] for fully-valid cites."""
    G = _make_argue_graph()
    result = validate_turn({"claim": "x", "cites": ["n_extract"]}, G)
    assert result == []


def test_validate_turn_fabricated() -> None:
    """ARGUE-05 D-08: validate_turn returns unknown node_ids; fixture-driven negative test."""
    G = _make_argue_graph()
    result = validate_turn({"claim": "x", "cites": ["n_fake"]}, G)
    assert result == ["n_fake"]

    # Fixture-based negative test
    fixture_path = Path("tests/fixtures/argue_fabricated.json")
    fixture = json.loads(fixture_path.read_text())
    invalid = validate_turn({"claim": fixture["claim"], "cites": fixture["cites"]}, G)
    assert set(invalid) == set(fixture["expected_invalid"])


def test_validate_turn_empty_cites() -> None:
    """ARGUE-05 D-08: empty cites list (abstention) is valid — returns []."""
    G = _make_argue_graph()
    result = validate_turn({"claim": "abstain", "cites": []}, G)
    assert result == []


def test_validate_turn_missing_cites_key() -> None:
    """ARGUE-05 D-10: missing 'cites' key uses .get default — returns []."""
    G = _make_argue_graph()
    result = validate_turn({"claim": "x"}, G)
    assert result == []


# ---------------------------------------------------------------------------
# ARGUE-08: compute_overlap Jaccard (D-06)
# ---------------------------------------------------------------------------

def test_compute_overlap_jaccard() -> None:
    """ARGUE-08 D-06: Jaccard of [{a,b},{b,c},{b},{b,a}] = |{b}|/|{a,b,c}| = 1/3."""
    cite_sets = [{"a", "b"}, {"b", "c"}, {"b"}, {"b", "a"}]
    result = compute_overlap(cite_sets)
    assert math.isclose(result, 1 / 3, rel_tol=1e-9)


def test_compute_overlap_drops_abstentions() -> None:
    """ARGUE-08 D-06: empty sets (abstentions) excluded before Jaccard computation."""
    # Non-empty: [{a,b}, {a}] → intersection={a}, union={a,b} → 0.5
    cite_sets = [{"a", "b"}, set(), {"a"}, set()]
    result = compute_overlap(cite_sets)
    assert math.isclose(result, 0.5, rel_tol=1e-9)


def test_compute_overlap_all_empty() -> None:
    """ARGUE-08 D-06: all abstentions → returns 0.0."""
    result = compute_overlap([set(), set(), set(), set()])
    assert result == 0.0


def test_compute_overlap_single_nonempty() -> None:
    """ARGUE-08 D-06: fewer than 2 non-empty sets → returns 0.0."""
    result = compute_overlap([{"a", "b"}, set(), set(), set()])
    assert result == 0.0


# ---------------------------------------------------------------------------
# ARGUE-08: Round cap and temperature constants
# ---------------------------------------------------------------------------

def test_round_cap_constant() -> None:
    """ARGUE-08 D-06: ROUND_CAP == 6."""
    import graphify.argue as argue
    assert argue.ROUND_CAP == 6


def test_max_temperature_constant() -> None:
    """ARGUE-08 D-04: MAX_TEMPERATURE == 0.4."""
    import graphify.argue as argue
    assert argue.MAX_TEMPERATURE == 0.4


# ---------------------------------------------------------------------------
# ARGUE-03: Zero-LLM enforcement (grep-based)
# ---------------------------------------------------------------------------

def test_argue_zero_llm_calls() -> None:
    """ARGUE-03: argue.py source must not import any LLM client."""
    src = Path("graphify/argue.py").read_text()
    forbidden = (
        "import anthropic",
        "from anthropic",
        "import openai",
        "from openai",
        "from graphify.llm",
        "import graphify.llm",
        "import langchain",
        "from langchain",
    )
    for needle in forbidden:
        assert needle not in src, f"argue.py introduced LLM dependency: {needle!r}"


# ---------------------------------------------------------------------------
# ARGUE-06 SC4: Phase 9 blind-label harness regression anchor
# ---------------------------------------------------------------------------

def test_blind_label_harness_intact() -> None:
    """ARGUE-06 SC4: Phase 9 shuffle harness at skill.md:1512 is unmodified.

    Asserts the literal string 'Judge 1: Analysis-1=A' still exists in skill.md —
    the per-judge rotation introduced in Phase 9. Any edit to this section would
    break ARGUE-06's bias-suite invariant.
    """
    src = Path("graphify/skill.md").read_text()
    assert "Judge 1: Analysis-1=A" in src, (
        "Phase 9 blind-label harness anchor missing from skill.md — "
        "the shuffle rotation at ~line 1512 has been modified or deleted."
    )
