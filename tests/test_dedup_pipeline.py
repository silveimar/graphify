"""End-to-end integration tests for the dedup -> build -> cluster -> analyze pipeline.

Phase 10 gap closure: UAT test 6 — verifies the full composed flow runs without
TypeError when canonical nodes carry source_file: list[str] after dedup.

(10-08-PLAN.md Task 1 — RED gate)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate
from graphify.dedup import dedup

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_encoder(labels: list[str]):
    """Deterministic mock encoder — same label -> same vector.

    Produces near-identical vectors for labels that share the same normalized
    token so dedup can find the AuthService×2 near-duplicate pair in the fixture.
    """
    result = []
    for label in labels:
        # Normalize: lowercase, strip non-alpha
        key = re.sub(r"[^a-z]", "", label.lower())
        rng = np.random.default_rng(abs(hash(key)) % (2**32))
        vec = rng.standard_normal(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        result.append(vec)
    return np.array(result)


@pytest.fixture
def composed_extraction():
    """Load the dedup_composed_extraction fixture."""
    return json.loads((FIXTURES / "dedup_composed_extraction.json").read_text())


@pytest.fixture
def deduped_graph(composed_extraction):
    """Run dedup -> build_from_json -> cluster on the composed fixture."""
    deduped, _report = dedup(
        composed_extraction,
        fuzzy_threshold=0.90,
        embed_threshold=0.85,
        encoder=_fake_encoder,
    )
    G = build_from_json(deduped)
    communities = cluster(G)
    return G, communities


def test_dedup_then_god_nodes_composes(deduped_graph):
    """dedup -> build -> cluster -> god_nodes must not raise TypeError."""
    G, communities = deduped_graph
    result = god_nodes(G, top_n=5)
    assert isinstance(result, list)
    # Each entry has the expected shape
    for item in result:
        assert "id" in item
        assert "label" in item
        assert "edges" in item


def test_dedup_then_surprising_connections_composes(deduped_graph):
    """dedup -> build -> cluster -> surprising_connections must not raise TypeError."""
    G, communities = deduped_graph
    result = surprising_connections(G, communities, top_n=3)
    assert isinstance(result, list)
    for s in result:
        # source_files values must be stringifiable (no Python list repr crash)
        for sf in s.get("source_files", []):
            _ = str(sf) if sf else ""


def test_dedup_then_report_generate_composes(deduped_graph):
    """dedup -> build -> cluster -> analyze -> report.generate must produce clean markdown.

    The surprising-connections section must NOT contain Python list repr like ['a.py', 'b.py'].
    """
    G, communities = deduped_graph
    god_nodes_out = god_nodes(G, top_n=5)
    surprises_out = surprising_connections(G, communities, top_n=3)

    report = generate(
        G=G,
        communities=communities,
        cohesion_scores={},
        community_labels={cid: f"Community {cid}" for cid in communities},
        god_node_list=god_nodes_out,
        surprise_list=surprises_out,
        detection_result={"total_files": 3, "total_words": 500},
        token_cost={"input": 0, "output": 0},
        root="test",
    )

    assert isinstance(report, str)
    assert len(report) > 0

    # Isolate the surprising-connections section
    sc_start = report.find("## Surprising Connections")
    sc_end = report.find("\n##", sc_start + 1) if sc_start >= 0 else -1
    if sc_start >= 0 and sc_end > sc_start:
        sc_section = report[sc_start:sc_end]
    elif sc_start >= 0:
        sc_section = report[sc_start:]
    else:
        sc_section = ""

    # Must NOT contain Python list repr pattern like ['path.py', 'other.py']
    list_repr_pattern = re.compile(r"\['.+\.py'")
    assert not list_repr_pattern.search(sc_section), (
        f"Surprising-connections section contains Python list repr: {sc_section!r}"
    )
