"""Tests for graphify.dedup — GRAPH-02, GRAPH-03, GRAPH-04 entity dedup."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from graphify.dedup import (
    dedup,
    write_dedup_reports,
    corpus_hash,
    _select_canonical,
    _merge_extraction,
)


# ---------- Helpers ----------

def _forced_merge_encoder(labels: list[str]) -> np.ndarray:
    """Encoder that returns the SAME vector for every label, forcing cosine=1.0.

    Use in tests that want to isolate the fuzzy gate (all pairs pass cosine).
    """
    vec = np.ones(384, dtype=np.float32)
    vec /= np.linalg.norm(vec)
    return np.array([vec for _ in labels])


def _never_merge_encoder(labels: list[str]) -> np.ndarray:
    """Encoder that returns orthogonal vectors (cosine ~= 0.0) for every label."""
    result = []
    for i, _ in enumerate(labels):
        v = np.zeros(384, dtype=np.float32)
        v[i % 384] = 1.0
        result.append(v)
    return np.array(result)


# ---------- Baseline ----------

def test_empty_extraction_returns_empty_report(fake_encoder):
    result_ext, report = dedup({"nodes": [], "edges": []}, encoder=fake_encoder)
    assert report["summary"]["merges"] == 0
    assert report["alias_map"] == {}
    assert report["merges"] == []


def test_dedup_produces_report(fake_encoder):
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "AuthService", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    _, report = dedup(extraction, encoder=_forced_merge_encoder)
    assert "merges" in report
    assert "alias_map" in report
    assert "summary" in report
    assert report["version"] == "1"
    assert isinstance(report["merges"], list)


# ---------- GRAPH-02: fuzzy + cosine gates ----------

def test_fuzzy_threshold_respected(fake_encoder):
    """Pair below 0.90 fuzzy ratio must NOT merge, even with high cosine."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "Authorizer", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    # Both labels start with "auth" (same prefix block), length ratio 11/10 = 0.91 > 0.7
    # Fuzzy ratio is ~0.56 (below 0.90)
    result, report = dedup(extraction, encoder=_forced_merge_encoder,
                            fuzzy_threshold=0.90, embed_threshold=0.85)
    assert report["summary"]["merges"] == 0
    assert len(result["nodes"]) == 2


def test_cosine_threshold_respected():
    """Pair above 0.90 fuzzy but low cosine must NOT merge (D-02 AND gate)."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    # Labels have fuzzy ratio ~0.957 (above 0.90) — would merge if cosine passed
    result, report = dedup(extraction, encoder=_never_merge_encoder,
                            fuzzy_threshold=0.90, embed_threshold=0.85)
    assert report["summary"]["merges"] == 0
    assert len(result["nodes"]) == 2


def test_both_gates_pass_triggers_merge():
    """Pair above both thresholds merges."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    result, report = dedup(extraction, encoder=_forced_merge_encoder,
                            fuzzy_threshold=0.90, embed_threshold=0.85)
    assert report["summary"]["merges"] == 1
    assert len(result["nodes"]) == 1
    # alias_map points from eliminated -> canonical
    assert len(report["alias_map"]) == 1


# ---------- GRAPH-02 / D-13: cross-type guard ----------

def test_cross_type_blocked_by_default():
    """Code + document pair with identical labels must NOT merge when cross_type=False."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "User", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "User", "file_type": "document", "source_file": "b.md"},
        ],
        "edges": [],
    }
    result, report = dedup(extraction, encoder=_forced_merge_encoder)
    assert report["summary"]["merges"] == 0
    assert len(result["nodes"]) == 2


def test_cross_type_allowed_with_flag():
    """cross_type=True allows code+document pair to merge via cosine alone."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "auth", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "authentication", "file_type": "document", "source_file": "b.md"},
        ],
        "edges": [],
    }
    # Cross-type: fuzzy gate bypassed, cosine=1.0 forces merge
    result, report = dedup(extraction, encoder=_forced_merge_encoder,
                            cross_type=True, embed_threshold=0.85)
    assert report["summary"]["merges"] == 1
    # Canonical label is "authentication" (longer per D-09)
    canonical = result["nodes"][0]
    assert canonical["label"] == "authentication"


# ---------- GRAPH-03: edge re-routing, weight aggregation, confidence promotion ----------

def test_no_dangling_edges_after_merge():
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
            {"id": "h", "label": "handler", "file_type": "code", "source_file": "c.py"},
        ],
        "edges": [
            {"source": "a1", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
            {"source": "a2", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0},
        ],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    node_ids = {n["id"] for n in result["nodes"]}
    for edge in result["edges"]:
        assert edge["source"] in node_ids, f"dangling source {edge['source']}"
        assert edge["target"] in node_ids, f"dangling target {edge['target']}"


def test_edge_weight_summed():
    """D-10: parallel edges to same target have weights summed."""
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
            {"id": "h", "label": "handler", "file_type": "code", "source_file": "c.py"},
        ],
        "edges": [
            {"source": "a1", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
            {"source": "a2", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0},
        ],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    assert len(result["edges"]) == 1
    assert result["edges"][0]["weight"] == 2.0


def test_confidence_promotion():
    """D-10: confidence enum EXTRACTED > INFERRED > AMBIGUOUS."""
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
            {"id": "h", "label": "handler", "file_type": "code", "source_file": "c.py"},
        ],
        "edges": [
            {"source": "a1", "target": "h", "relation": "calls",
             "confidence": "INFERRED", "source_file": "a.py", "weight": 1.0, "confidence_score": 0.5},
            {"source": "a2", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0, "confidence_score": 0.9},
        ],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    merged_edge = result["edges"][0]
    assert merged_edge["confidence"] == "EXTRACTED"
    assert merged_edge["confidence_score"] == 0.9  # max


def test_self_loops_dropped():
    """Pitfall 6: edge from merged node to its canonical becomes self-loop, dropped."""
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [
            # a1 -> a2 edge becomes canonical->canonical after merge == self-loop
            {"source": "a1", "target": "a2", "relation": "references",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
        ],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    for edge in result["edges"]:
        assert edge["source"] != edge["target"], "self-loop not dropped"
    assert len(result["edges"]) == 0


def test_canonical_label_selection():
    """D-09: longest label wins, then pre-dedup degree, then alphabetical."""
    nodes_by_id = {
        "short": {"label": "auth"},
        "long": {"label": "authentication_service"},
        "mid": {"label": "auth_service"},
    }
    pre_degree = {"short": 10, "long": 1, "mid": 5}
    canonical = _select_canonical(list(nodes_by_id.keys()), nodes_by_id, pre_degree)
    assert canonical == "long"  # longest label wins despite lowest degree


def test_canonical_tie_break_by_degree():
    """D-09: equal-length labels break ties on degree."""
    nodes_by_id = {
        "a": {"label": "alpha"},
        "b": {"label": "betaX"},  # same length (5)
    }
    pre_degree = {"a": 3, "b": 7}
    canonical = _select_canonical(list(nodes_by_id.keys()), nodes_by_id, pre_degree)
    assert canonical == "b"  # higher degree wins


def test_canonical_tie_break_alphabetical():
    """D-09: equal-length + equal-degree breaks ties alphabetically."""
    nodes_by_id = {"b": {"label": "zzz"}, "a": {"label": "yyy"}}
    pre_degree = {"a": 0, "b": 0}
    canonical = _select_canonical(["a", "b"], nodes_by_id, pre_degree)
    assert canonical == "a"  # zzz vs yyy — yyy is alphabetically smaller


def test_provenance_fields():
    """D-11: canonical node has source_file list + merged_from list."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    canon = result["nodes"][0]
    assert "merged_from" in canon
    assert isinstance(canon["merged_from"], list)
    assert len(canon["merged_from"]) == 1
    assert isinstance(canon["source_file"], list)
    assert set(canon["source_file"]) == {"a.py", "b.py"}


# ---------- GRAPH-04 stretch acceptance ----------

def test_cross_source_graph04_acceptance(multi_file_extraction):
    """GRAPH-04 stretch: auth.py function + docs.md heading + tests/AuthService -> one canonical.

    Uses cross_type=True with a forced-merge encoder. The input fixture is
    tests/fixtures/multi_file_extraction.json which contains 4 duplicate-
    candidates across code/document/code file types.
    """
    result, report = dedup(
        multi_file_extraction,
        encoder=_forced_merge_encoder,
        cross_type=True,
        fuzzy_threshold=0.90,
        embed_threshold=0.85,
    )
    # At least 3 nodes should merge into one canonical (the 4 AuthService candidates)
    assert report["summary"]["merges"] >= 1
    # UserProfile must NOT merge (distinct label)
    labels = [n["label"] for n in result["nodes"]]
    assert "UserProfile" in labels
    # The canonical for the auth cluster has source_file list spanning code + doc + test files
    auth_canonicals = [
        n for n in result["nodes"]
        if isinstance(n.get("source_file"), list) and len(n["source_file"]) >= 3
    ]
    assert len(auth_canonicals) >= 1, (
        "No canonical node with >=3 contributing source_files — "
        "GRAPH-04 stretch acceptance test failed"
    )


# ---------- Security ----------

def test_report_path_confined(tmp_path, fake_encoder):
    """T-10-01: write_dedup_reports must reject paths escaping cwd."""
    # Create a path outside cwd by using tmp_path (which is outside project root)
    outside_dir = tmp_path.parent / "escape_test"
    outside_dir.mkdir(exist_ok=True)
    report = {"version": "1", "summary": {}, "alias_map": {}, "merges": []}
    # On most systems, tmp_path is outside cwd, so write should raise ValueError
    cwd = Path.cwd().resolve()
    try:
        outside_dir.resolve().relative_to(cwd)
        pytest.skip("tmp_path is inside cwd — cannot test path-escape on this platform")
    except ValueError:
        pass
    with pytest.raises(ValueError, match="escapes"):
        write_dedup_reports(report, outside_dir)


def test_canonical_label_sanitized(tmp_path, monkeypatch):
    """T-10-02: canonical labels with HTML/injection chars are sanitized in MD output."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "graphify-out"
    out.mkdir()
    report = {
        "version": "1",
        "generated_at": "2026-04-16T00:00:00Z",
        "summary": {"total_nodes_before": 2, "total_nodes_after": 1, "merges": 1},
        "alias_map": {"b": "a"},
        "merges": [{
            "canonical_id": "a",
            "canonical_label": "<script>alert(1)</script>",
            "eliminated": [{"id": "b", "label": "<img src=x>", "source_file": "b.py"}],
            "fuzzy_score": 0.95,
            "cosine_score": 0.9,
        }],
    }
    write_dedup_reports(report, out)
    md_body = (out / "dedup_report.md").read_text(encoding="utf-8")
    # Raw <script> must NOT appear — must be sanitized
    assert "<script>" not in md_body
    # Fail-safe: canonical label should be present in some sanitized form
    assert "alert" in md_body


# ---------- Determinism / golden report ----------

def test_determinism_golden_report(multi_file_extraction, tmp_path, monkeypatch):
    """Two dedup runs on the same input produce byte-identical JSON reports."""
    monkeypatch.chdir(tmp_path)
    _, r1 = dedup(multi_file_extraction, encoder=_forced_merge_encoder, cross_type=True)
    _, r2 = dedup(multi_file_extraction, encoder=_forced_merge_encoder, cross_type=True)
    # Strip generated_at (time-dependent) before comparing
    r1_stable = {**r1, "generated_at": ""}
    r2_stable = {**r2, "generated_at": ""}
    assert json.dumps(r1_stable, sort_keys=True) == json.dumps(r2_stable, sort_keys=True)


def test_write_reports_creates_both_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "graphify-out"
    out.mkdir()
    report = {
        "version": "1", "generated_at": "x",
        "summary": {"total_nodes_before": 0, "total_nodes_after": 0, "merges": 0},
        "alias_map": {}, "merges": [],
    }
    write_dedup_reports(report, out)
    assert (out / "dedup_report.json").exists()
    assert (out / "dedup_report.md").exists()
    loaded = json.loads((out / "dedup_report.json").read_text(encoding="utf-8"))
    assert loaded["version"] == "1"


# ---------- Corpus hash ----------

def test_corpus_hash_deterministic(tmp_path):
    """Corpus hash is SHA256 of sorted per-file hashes — same files same hash."""
    f1 = tmp_path / "a.py"; f1.write_text("a")
    f2 = tmp_path / "b.py"; f2.write_text("b")
    h1 = corpus_hash([str(f1), str(f2)])
    h2 = corpus_hash([str(f2), str(f1)])  # swapped input order
    assert h1 == h2  # order-independent
    assert len(h1) == 64  # SHA256 hex


def test_corpus_hash_changes_on_added_file(tmp_path):
    """Adding a file changes the corpus hash (Pitfall 5)."""
    f1 = tmp_path / "a.py"; f1.write_text("a")
    h1 = corpus_hash([str(f1)])
    f2 = tmp_path / "b.py"; f2.write_text("b")
    h2 = corpus_hash([str(f1), str(f2)])
    assert h1 != h2
