"""Phase 5 integration tests — full to_obsidian() pipeline against profile-driven vaults.

These tests replace the legacy tests/test_export.py::test_to_obsidian_* suite.
They assert on MergeResult.summary counts and Atlas/-shaped target paths
produced by the default profile, not on the pre-Phase-5 flat vault shape.

Regression invariants preserved from the old suite:
  - FIX-01: frontmatter values with special chars are properly quoted
  - FIX-02: deterministic dedup across re-runs
  - FIX-03: community tag sanitization
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from graphify.export import to_obsidian
from graphify.merge import MergePlan, MergeResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_graph(
    nodes: list[tuple[str, dict]],
    edges: list[tuple[str, str, dict]] | None = None,
) -> nx.Graph:
    G = nx.Graph()
    for node_id, data in nodes:
        G.add_node(node_id, **data)
    for u, v, data in (edges or []):
        G.add_edge(u, v, **data)
    return G


def _minimal_graph() -> tuple[nx.Graph, dict[int, list[str]], dict[int, str]]:
    G = _make_graph(
        nodes=[
            ("n1", {"label": "Transformer", "file_type": "code", "source_file": "model.py"}),
            ("n2", {"label": "Attention", "file_type": "code", "source_file": "model.py"}),
            ("n3", {"label": "LayerNorm", "file_type": "code", "source_file": "model.py"}),
            ("n4", {"label": "SGD Optimizer", "file_type": "code", "source_file": "train.py"}),
        ],
        edges=[
            ("n1", "n2", {"relation": "contains", "confidence": "EXTRACTED", "source_file": "model.py", "weight": 1.0}),
            ("n1", "n3", {"relation": "contains", "confidence": "EXTRACTED", "source_file": "model.py", "weight": 1.0}),
            ("n2", "n3", {"relation": "uses", "confidence": "EXTRACTED", "source_file": "model.py", "weight": 1.0}),
        ],
    )
    communities = {0: ["n1", "n2", "n3"], 1: ["n4"]}
    labels = {0: "Neural Architecture", 1: "Training"}
    return G, communities, labels


# ---------------------------------------------------------------------------
# MUST-HAVE 1 — default-profile backward compat (MRG-05 re-interpreted per D-74)
# ---------------------------------------------------------------------------

def test_to_obsidian_default_profile_returns_merge_result(tmp_path):
    G, communities, labels = _minimal_graph()
    result = to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    assert isinstance(result, MergeResult), f"expected MergeResult, got {type(result).__name__}"
    assert isinstance(result.plan, MergePlan)
    # Default profile produces Atlas/-shaped layout with at least one CREATE
    assert result.plan.summary.get("CREATE", 0) > 0


def test_to_obsidian_default_profile_writes_atlas_layout(tmp_path):
    G, communities, labels = _minimal_graph()
    to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    # Per _DEFAULT_PROFILE folder_mapping: thing→Atlas/Dots/Things, moc→Atlas/Maps
    things_dir = tmp_path / "Atlas" / "Dots" / "Things"
    maps_dir = tmp_path / "Atlas" / "Maps"
    produced_any = (
        things_dir.exists()
        or maps_dir.exists()
        or (tmp_path / "Atlas" / "Dots" / "Statements").exists()
    )
    assert produced_any, (
        f"No Atlas/-shaped output found under {tmp_path}; "
        f"contents: {sorted(p.relative_to(tmp_path) for p in tmp_path.rglob('*'))}"
    )


# ---------------------------------------------------------------------------
# MUST-HAVE 2 — dry-run produces MergePlan and writes NOTHING (MRG-03)
# ---------------------------------------------------------------------------

def test_to_obsidian_dry_run_returns_plan(tmp_path):
    G, communities, labels = _minimal_graph()
    result = to_obsidian(
        G, communities, str(tmp_path),
        community_labels=labels, dry_run=True,
    )
    assert isinstance(result, MergePlan), f"dry_run should return MergePlan, got {type(result).__name__}"
    assert result.summary.get("CREATE", 0) > 0


def test_to_obsidian_dry_run_writes_zero_md_files(tmp_path):
    G, communities, labels = _minimal_graph()
    to_obsidian(
        G, communities, str(tmp_path),
        community_labels=labels, dry_run=True,
    )
    md_files = list(tmp_path.rglob("*.md"))
    assert md_files == [], f"Dry run wrote .md files: {md_files}"


# ---------------------------------------------------------------------------
# FIX-01 — frontmatter injection via special chars (migrated from test_export.py L155)
# ---------------------------------------------------------------------------

def test_fix01_frontmatter_special_chars_quoted(tmp_path):
    G = _make_graph(
        [
            ("n1", {"label": "My#Class", "file_type": "code", "source_file": "C:\\path:file.py", "source_location": "L42"}),
            ("n2", {"label": "Other", "file_type": "code", "source_file": "other.py", "source_location": "L1"}),
        ],
        edges=[
            ("n1", "n2", {"relation": "calls", "confidence": "EXTRACTED", "source_file": "other.py", "weight": 1.0}),
        ],
    )
    communities = {0: ["n1", "n2"]}
    labels = {0: "Test Community"}
    to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    hits = [
        p for p in tmp_path.rglob("*.md")
        if "file.py" in p.read_text(encoding="utf-8")
    ]
    assert hits, (
        f"No file contains the problematic source path; "
        f"layout: {sorted(p.relative_to(tmp_path) for p in tmp_path.rglob('*.md'))}"
    )
    content = hits[0].read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("source_file:"):
            assert '"' in line, f"source_file with colon not quoted: {line}"
            break
    else:
        pytest.fail("source_file line not found in frontmatter")


# ---------------------------------------------------------------------------
# FIX-02 — deterministic dedup (migrated from test_export.py L188)
# ---------------------------------------------------------------------------

def test_fix02_dedup_deterministic_across_runs(tmp_path):
    def _build():
        return _make_graph(
            [
                ("n1", {"label": "Widget", "file_type": "code", "source_file": "a.py"}),
                ("n2", {"label": "Widget", "file_type": "code", "source_file": "b.py"}),
                ("n3", {"label": "Widget", "file_type": "code", "source_file": "c.py"}),
            ],
            edges=[
                ("n1", "n2", {"relation": "calls", "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0}),
                ("n2", "n3", {"relation": "calls", "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0}),
            ],
        )

    communities = {0: ["n1", "n2", "n3"]}
    labels = {0: "Widgets"}
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    dir1.mkdir()
    dir2.mkdir()
    to_obsidian(_build(), communities, str(dir1), community_labels=labels)
    to_obsidian(_build(), communities, str(dir2), community_labels=labels)
    files1 = sorted(str(p.relative_to(dir1)) for p in dir1.rglob("*.md"))
    files2 = sorted(str(p.relative_to(dir2)) for p in dir2.rglob("*.md"))
    assert files1 == files2, f"Non-deterministic dedup: {files1} vs {files2}"


# ---------------------------------------------------------------------------
# FIX-03 — community tag sanitization (migrated from test_export.py L216)
# ---------------------------------------------------------------------------

def test_fix03_community_tag_sanitization(tmp_path):
    G, communities, _ = _minimal_graph()
    labels = {0: "ML/AI + Data", 1: "Training"}
    to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    found = False
    for p in tmp_path.rglob("*.md"):
        content = p.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "community/" in line:
                after = line.split("community/", 1)[1].split()[0].rstrip("]")
                slug = after.strip('"').strip("'")
                assert "/" not in slug, f"slug contains /: {slug!r} in line {line!r}"
                assert "+" not in slug, f"slug contains +: {slug!r}"
                assert " " not in slug, f"slug contains space: {slug!r}"
                found = True
    assert found, "No community/ tag found in any rendered note"


# ---------------------------------------------------------------------------
# MergeResult structural sanity
# ---------------------------------------------------------------------------

def test_merge_result_shape_after_normal_run(tmp_path):
    G, communities, labels = _minimal_graph()
    result = to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    assert isinstance(result.succeeded, list)
    assert isinstance(result.failed, list)
    assert isinstance(result.skipped_identical, list)
    # summary is a sparse dict — zero-count keys are omitted. Verify all valid keys
    # are a subset of the expected key set (no unknown keys emitted).
    valid_keys = {"CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"}
    unexpected = set(result.plan.summary) - valid_keys
    assert not unexpected, f"Unexpected keys in summary: {unexpected}"
    # At least one action must have occurred on a fresh run.
    assert sum(result.plan.summary.values()) > 0, f"Empty summary: {result.plan.summary}"


def test_re_run_is_idempotent(tmp_path):
    G, communities, labels = _minimal_graph()
    r1 = to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    r2 = to_obsidian(G, communities, str(tmp_path), community_labels=labels)
    assert len(r2.skipped_identical) > 0, (
        f"Second run wrote new content despite identical graph; "
        f"r1.succeeded={len(r1.succeeded)}, r2.skipped_identical={len(r2.skipped_identical)}"
    )
