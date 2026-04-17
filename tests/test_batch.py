"""Tests for graphify.batch — GRAPH-01 file-cluster detection."""
from __future__ import annotations

from pathlib import Path

from graphify.batch import cluster_files, _build_import_graph, _topological_order


def _make_ast_result(source_file: str, imports: list[str]) -> dict:
    """Helper: build a minimal per-file extraction dict with only import edges.

    imports: list of target paths (same format as source_file). All other
    fields use placeholder values since cluster_files only looks at
    `relation == "imports"` edges.
    """
    return {
        "nodes": [],
        "edges": [
            {
                "source": Path(source_file).stem,
                "target": target,
                "relation": "imports",
                "confidence": "EXTRACTED",
                "source_file": source_file,
                "weight": 1.0,
            }
            for target in imports
        ],
    }


def test_empty_inputs_return_empty_list():
    assert cluster_files([], []) == []


def test_cluster_files_import_connected(tmp_corpus):
    """GRAPH-01: import-connected files end up in the same cluster."""
    paths = tmp_corpus({
        "auth.py": "# auth",
        "models.py": "# models",
        "utils.py": "# isolated",
    })
    auth, models, utils = paths
    ast_results = [
        _make_ast_result(str(auth), [str(models)]),
        _make_ast_result(str(models), []),
        _make_ast_result(str(utils), []),
    ]
    clusters = cluster_files(paths, ast_results)
    # Two clusters: {auth, models} and {utils}
    cluster_sets = [set(c["files"]) for c in clusters]
    assert {str(auth), str(models)} in cluster_sets
    assert {str(utils)} in cluster_sets
    # cluster_id contiguous from 0
    assert sorted(c["cluster_id"] for c in clusters) == list(range(len(clusters)))


def test_cluster_top_dir_cap(tmp_corpus):
    """GRAPH-01 / D-05: component spanning multiple top-level directories is split."""
    paths = tmp_corpus({
        "src/auth.py": "# auth",
        "tests/test_auth.py": "# test",
    })
    src_auth, test_auth = paths
    # Artificially connect them via an import edge (cross-dir)
    ast_results = [
        _make_ast_result(str(src_auth), [str(test_auth)]),
        _make_ast_result(str(test_auth), []),
    ]
    clusters = cluster_files(paths, ast_results)
    # Must be 2 clusters, one per top-level dir
    assert len(clusters) == 2
    cluster_sets = [set(c["files"]) for c in clusters]
    assert {str(src_auth)} in cluster_sets
    assert {str(test_auth)} in cluster_sets


def test_cluster_respects_token_budget(tmp_corpus):
    """GRAPH-01 / D-07: cluster exceeding token budget is split at weakest edge."""
    # Create 3 files big enough that their combined size exceeds a tiny budget
    big = "x" * 4000  # 4000 chars ~= 1000 tokens each
    paths = tmp_corpus({
        "a.py": big,
        "b.py": big,
        "c.py": big,
    })
    a, b, c = paths
    # Chain a -> b -> c (b is boundary with degree 2, others degree 1)
    ast_results = [
        _make_ast_result(str(a), [str(b)]),
        _make_ast_result(str(b), [str(c)]),
        _make_ast_result(str(c), []),
    ]
    # Budget below combined but above any single file's estimate
    clusters = cluster_files(paths, ast_results, token_budget=1500)
    # Must produce more than 1 cluster (the single component got split)
    assert len(clusters) >= 2
    # Every cluster must be within or below budget OR a singleton
    for c_ in clusters:
        assert c_["token_estimate"] <= 1500 or len(c_["files"]) == 1


def test_cluster_topological_order(tmp_corpus):
    """GRAPH-01 / D-08: files within a cluster ordered imported-first."""
    paths = tmp_corpus({
        "models.py": "# models",
        "auth.py": "# auth imports models",
        "api.py": "# api imports auth",
    })
    models, auth, api = paths
    ast_results = [
        _make_ast_result(str(auth), [str(models)]),
        _make_ast_result(str(api), [str(auth)]),
        _make_ast_result(str(models), []),
    ]
    clusters = cluster_files(paths, ast_results)
    # Exactly one cluster containing all three files
    assert len(clusters) == 1
    files = clusters[0]["files"]
    # models must come before auth; auth must come before api
    assert files.index(str(models)) < files.index(str(auth)) < files.index(str(api))


def test_cluster_cycle_fallback(tmp_corpus):
    """GRAPH-01 / D-08: import cycle falls back to alphabetical order."""
    paths = tmp_corpus({
        "a.py": "# a imports b",
        "b.py": "# b imports a",
    })
    a, b = paths
    ast_results = [
        _make_ast_result(str(a), [str(b)]),
        _make_ast_result(str(b), [str(a)]),
    ]
    clusters = cluster_files(paths, ast_results)
    assert len(clusters) == 1
    files = clusters[0]["files"]
    # Alphabetical fallback — a.py before b.py
    assert files == sorted(files)


def test_cluster_files_does_not_write_to_stdout(capsys, tmp_corpus):
    """cluster_files must be silent on stdout (matches cluster.py behavior)."""
    paths = tmp_corpus({"x.py": "# x"})
    cluster_files(paths, [_make_ast_result(str(paths[0]), [])])
    captured = capsys.readouterr()
    assert captured.out == "", f"cluster_files wrote to stdout: {captured.out!r}"


def test_cluster_token_estimate_positive(tmp_corpus):
    """Every returned cluster has token_estimate >= 1."""
    paths = tmp_corpus({"x.py": "a"})
    clusters = cluster_files(paths, [_make_ast_result(str(paths[0]), [])])
    assert all(c["token_estimate"] >= 1 for c in clusters)


def test_cluster_ids_are_contiguous(tmp_corpus):
    """cluster_id values are 0, 1, 2, ... no gaps."""
    paths = tmp_corpus({"a.py": "a", "b.py": "b", "c.py": "c"})
    clusters = cluster_files(paths, [_make_ast_result(str(p), []) for p in paths])
    ids = sorted(c["cluster_id"] for c in clusters)
    assert ids == list(range(len(clusters)))
