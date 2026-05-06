"""Tests for GRAPH_REPORT.md calibration self-check (Phase 65 / CCONF-04).

Covers:
  - 10-bin histogram bucketing
  - 3 flag rules (mode_collapse, refusal, no_negatives) with named thresholds
  - Min-edge gate (n<10 skips section gracefully — Q3 / Pitfall #4)
  - Skewed-distribution fixture (D-65.13) fires mode_collapse
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from graphify.report import (
    _CALIBRATION_MIN_EDGES,
    _CALIBRATION_MODE_COLLAPSE_THRESHOLD,
    _CALIBRATION_NEGATIVE_FLOOR,
    _CALIBRATION_REFUSAL_THRESHOLD,
    _calibration_flags,
    _calibration_histogram,
    generate,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _empty_aux():
    """Common minimal aux args required by report.generate()."""
    detection = {"total_files": 4, "total_words": 1000, "needs_graph": True, "warning": None}
    tokens = {"input": 0, "output": 0}
    return {}, {}, {}, [], [], detection, tokens


def _build_graph_with_inferred_scores(scores: list[float]) -> nx.Graph:
    """Build a simple Graph with one INFERRED concept↔code edge per score."""
    G = nx.Graph()
    for i, s in enumerate(scores):
        a = f"code_{i}"
        b = f"concept_{i}"
        G.add_node(a, label=a, file_type="code", source_file=f"{a}.py")
        G.add_node(b, label=b, file_type="rationale", source_file="doc.md")
        G.add_edge(
            a,
            b,
            relation="documents",
            confidence="INFERRED",
            confidence_score=s,
            source_file=f"{a}.py",
            weight=1.0,
        )
    return G


def test_histogram_bucketing():
    bins = _calibration_histogram([0.0, 0.05, 0.5, 0.85, 0.99, 1.0])
    assert len(bins) == 10
    assert sum(bins) == 6
    # 0.0 and 0.05 -> bin 0; 0.5 -> bin 5; 0.85 -> bin 8; 0.99 and 1.0 -> bin 9 (clamped)
    assert bins[0] == 2
    assert bins[5] == 1
    assert bins[8] == 1
    assert bins[9] == 2


def test_mode_collapse_flag_fires():
    fixture_path = FIXTURES / "skewed_distribution.json"
    data = json.loads(fixture_path.read_text())
    G = json_graph.node_link_graph(data, edges="links")
    inf_scores = [
        d.get("confidence_score", 0.5)
        for _, _, d in G.edges(data=True)
        if d.get("confidence") == "INFERRED"
    ]
    assert len(inf_scores) == 10
    bins = _calibration_histogram(inf_scores)
    flags = _calibration_flags(bins, inf_scores)
    names = [name for name, _, _ in flags]
    assert "mode_collapse" in names
    mc = next(f for f in flags if f[0] == "mode_collapse")
    assert mc[1] > _CALIBRATION_MODE_COLLAPSE_THRESHOLD
    assert mc[2] == _CALIBRATION_MODE_COLLAPSE_THRESHOLD


def test_refusal_flag_fires():
    # 12 of 20 scores exactly 0.5 -> 60% > 50%
    scores = [0.5] * 12 + [0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.1]
    bins = _calibration_histogram(scores)
    flags = _calibration_flags(bins, scores)
    names = [name for name, _, _ in flags]
    assert "refusal" in names
    refusal = next(f for f in flags if f[0] == "refusal")
    assert abs(refusal[1] - 0.6) < 1e-9
    assert refusal[2] == _CALIBRATION_REFUSAL_THRESHOLD


def test_no_negatives_flag_fires():
    scores = [0.6, 0.7, 0.8, 0.9, 0.55, 0.65, 0.75, 0.85, 0.95, 0.6,
              0.7, 0.8, 0.9, 0.55, 0.65, 0.75, 0.85, 0.95, 0.6, 0.7]
    bins = _calibration_histogram(scores)
    flags = _calibration_flags(bins, scores)
    names = [name for name, _, _ in flags]
    assert "no_negatives" in names
    nn = next(f for f in flags if f[0] == "no_negatives")
    assert nn[1] == 0.0
    assert nn[2] == _CALIBRATION_NEGATIVE_FLOOR


def test_histogram_always_rendered():
    # Well-distributed: one score per bin, n = 10.
    scores = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
    G = _build_graph_with_inferred_scores(scores)
    communities, cohesion, labels, gods, surprises, detection, tokens = _empty_aux()
    out = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./test")
    assert "## Calibration" in out
    # All 10 bin lines should be present
    for i in range(10):
        lo = i / 10
        hi = (i + 1) / 10
        assert f"[{lo:.1f}, {hi:.1f})" in out


def test_min_edge_gate_skips():
    # Only 5 INFERRED edges -> below _CALIBRATION_MIN_EDGES (10)
    scores = [0.6, 0.7, 0.8, 0.5, 0.3]
    assert len(scores) < _CALIBRATION_MIN_EDGES
    G = _build_graph_with_inferred_scores(scores)
    communities, cohesion, labels, gods, surprises, detection, tokens = _empty_aux()
    out = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./test")
    assert "calibration skipped" in out
    assert f"n={len(scores)}" in out
    # No flag lines should be rendered when skipped
    assert "flags fired" not in out
