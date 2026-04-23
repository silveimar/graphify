"""SC-1 + SC-3: graph.json is byte-identical before and after enrichment.

Phase 15 v1.1 D-invariant: ``graph.json`` must be read-only to the enrichment
subsystem. This test file seeds a minimal fixture graph.json + snapshot, runs
the full enrichment pipeline (all 4 passes with a mocked LLM), then hashes
the file and asserts it is byte-identical to the pre-run hash. A successful
run also produces a valid ``enrichment.json`` envelope.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX fcntl+signal only")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture_graph_json(out_dir: Path) -> Path:
    """Minimal node-link JSON graph + matching snapshot so pin_snapshot succeeds."""
    graph_payload = {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": [
            {
                "id": "N1", "label": "n1",
                "description": "base",
                "source_file": "x.py", "source_hash": "abc",
                "source_mtime": 0.0, "file_type": "code",
            },
            {
                "id": "N2", "label": "n2",
                "description": "",
                "source_file": "y.py", "source_hash": "def",
                "source_mtime": 0.0, "file_type": "code",
            },
        ],
        "links": [
            {
                "source": "N1", "target": "N2",
                "relation": "contains", "confidence": "EXTRACTED",
                "source_file": "x.py",
            }
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / "graph.json"
    # Use sort_keys + indent=2 so the bytes are stable across runs.
    graph_path.write_text(
        json.dumps(graph_payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    # Snapshot payload wraps the graph under `graph` + adds `communities`.
    snap_payload = {
        "graph": graph_payload,
        "communities": {"0": ["N1", "N2"]},
        "metadata": {"snapshot_id": "2026-04-20T14-30-00"},
    }
    snap_dir = out_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    (snap_dir / "2026-04-20T14-30-00.json").write_text(
        json.dumps(snap_payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return graph_path


def test_graph_json_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-1: a full enrichment run does NOT modify graph.json — byte equality."""
    out_dir = tmp_path / "graphify-out"
    graph_path = _write_fixture_graph_json(out_dir)
    pre_sha = _sha256(graph_path)
    pre_bytes = graph_path.read_bytes()

    # Mock _call_llm to produce deterministic output (no network).
    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("fake enriched text", 50)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    from graphify.enrich import run_enrichment
    result = run_enrichment(
        out_dir,
        budget=10000,
        passes=None,
        dry_run=False,
        project_root=tmp_path,
    )
    assert result is not None

    post_sha = _sha256(graph_path)
    post_bytes = graph_path.read_bytes()
    assert pre_sha == post_sha, (
        f"SC-1 VIOLATION: graph.json modified by enrichment run "
        f"(pre={pre_sha}, post={post_sha})"
    )
    assert pre_bytes == post_bytes, "SC-1 VIOLATION: graph.json bytes changed"

    # Sanity: enrichment.json IS produced, is valid JSON, has v1 shape.
    enrich_path = out_dir / "enrichment.json"
    assert enrich_path.exists(), "enrichment.json not produced by enrichment run"
    envelope = json.loads(enrich_path.read_text(encoding="utf-8"))
    assert envelope.get("version") == 1
    assert envelope.get("snapshot_id") == "2026-04-20T14-30-00"
    assert isinstance(envelope.get("passes"), dict)


def test_graph_json_unchanged_after_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC-3: a dry-run must not touch graph.json OR produce enrichment.json."""
    out_dir = tmp_path / "graphify-out"
    graph_path = _write_fixture_graph_json(out_dir)
    pre_sha = _sha256(graph_path)

    # Guard: dry-run must NEVER call the LLM. Any invocation fails the test.
    def forbidden_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        raise AssertionError("LLM called during dry-run — ENRICH-10 P2 violation")
    monkeypatch.setattr("graphify.enrich._call_llm", forbidden_llm)

    from graphify.enrich import run_enrichment
    result = run_enrichment(
        out_dir,
        budget=10000,
        passes=None,
        dry_run=True,
        project_root=tmp_path,
    )
    assert result.dry_run is True

    post_sha = _sha256(graph_path)
    assert pre_sha == post_sha, "SC-3 VIOLATION: dry-run modified graph.json"

    # Dry-run leaves disk untouched — no enrichment.json produced.
    enrich_path = out_dir / "enrichment.json"
    assert not enrich_path.exists(), (
        "dry-run must NOT produce enrichment.json (disk untouched)"
    )
