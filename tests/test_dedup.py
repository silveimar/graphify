"""Tests for graphify.dedup — GRAPH-02, GRAPH-03, GRAPH-04 entity deduplication.

Wave 0 stubs: placeholders for Wave 1 (plan 10-03) to flesh out.
"""
from __future__ import annotations
import pytest


def test_dedup_module_importable():
    """Wave 1 (plan 10-03) creates graphify/dedup.py with dedup().

    Until then, this test is marked skip so pytest collection succeeds.
    """
    pytest.importorskip("graphify.dedup",
                        reason="graphify/dedup.py not created until plan 10-03")


def test_multi_file_fixture_loads(multi_file_extraction):
    """Conftest fixture loads the canonical multi-file test corpus."""
    assert "nodes" in multi_file_extraction
    assert "edges" in multi_file_extraction
    assert len(multi_file_extraction["nodes"]) >= 5
    assert any(n["label"] == "AuthService" for n in multi_file_extraction["nodes"])


def test_fake_encoder_deterministic(fake_encoder):
    """Same label must produce the same vector across calls."""
    import numpy as np
    v1 = fake_encoder(["AuthService"])
    v2 = fake_encoder(["AuthService"])
    assert np.allclose(v1, v2)
    # Must be L2-normalized
    assert abs(float(np.linalg.norm(v1[0])) - 1.0) < 1e-5


# Placeholders filled in by plan 10-03:
# - test_dedup_produces_report
# - test_fuzzy_threshold_respected
# - test_cosine_threshold_respected
# - test_cross_type_blocked_by_default
# - test_cross_type_allowed_with_flag
# - test_no_dangling_edges_after_merge
# - test_edge_weight_summed
# - test_confidence_promotion
# - test_self_loops_dropped
# - test_canonical_label_selection
# - test_provenance_fields
# - test_cross_source_graph04_acceptance  (GRAPH-04 stretch)
# - test_report_path_confined            (T-10-01)
# - test_canonical_label_sanitized       (T-10-02)
# - test_determinism_golden_report
