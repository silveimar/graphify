"""Tests for graphify.batch — GRAPH-01 file-cluster detection.

Wave 0 stubs: placeholders for Wave 1 (plan 10-02) to flesh out.
Keep this file importable; the assertions below are minimal sanity checks.
"""
from __future__ import annotations
from pathlib import Path
import pytest


def test_batch_module_importable():
    """Wave 1 (plan 10-02) creates graphify/batch.py with cluster_files.

    Until then, this test is marked xfail so pytest collection succeeds.
    """
    pytest.importorskip("graphify.batch",
                        reason="graphify/batch.py not created until plan 10-02")


# Placeholders filled in by plan 10-02:
# - test_cluster_files_import_connected
# - test_cluster_respects_token_budget
# - test_cluster_top_dir_cap
# - test_cluster_topological_order
# - test_cluster_cycle_fallback
