"""Phase 40 — JSON harness interchange export (PORT-01/02)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from graphify.harness_export import export_claude_harness
from graphify.harness_interchange import (
    INTERCHANGE_SCHEMA_ID,
    export_interchange_v1,
    graph_data_to_extraction,
)
from graphify.validate import validate_extraction

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "harness"


def _copy_fixtures(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ("graph.json", "annotations.jsonl", "agent-edges.json", "telemetry.json"):
        shutil.copy(_FIXTURE_DIR / fname, dest / fname)


def test_graph_data_to_extraction_validates() -> None:
    raw = json.loads((_FIXTURE_DIR / "graph.json").read_text(encoding="utf-8"))
    ext = graph_data_to_extraction(raw)
    assert validate_extraction(ext) == []


def test_export_interchange_envelope_and_optional_run_id(tmp_path: Path) -> None:
    raw = json.loads((_FIXTURE_DIR / "graph.json").read_text(encoding="utf-8"))
    rid = str(uuid.UUID("12345678-1234-5678-1234-567812345678"))
    env = export_interchange_v1(
        raw,
        out_path=None,
        source_run_id=rid,
        graphify_version="9.9.9-test",
    )
    assert env["interchange_schema_id"] == INTERCHANGE_SCHEMA_ID
    assert env["provenance"]["interchange_schema_id"] == INTERCHANGE_SCHEMA_ID
    assert env["provenance"]["source_run_id"] == rid
    assert env["provenance"]["graphify_version"] == "9.9.9-test"
    assert validate_extraction(env["extraction"]) == []


def test_export_interchange_writes_confined_file(tmp_path: Path) -> None:
    out = tmp_path / "graphify-out"
    _copy_fixtures(out)
    harness_dir = out / "harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    raw = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    dest = harness_dir / "harness_memory.v1.json"
    export_interchange_v1(raw, out_path=dest, artifacts_base=out)
    assert dest.exists()
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["interchange_schema_id"] == INTERCHANGE_SCHEMA_ID
    assert validate_extraction(loaded["extraction"]) == []


def test_export_claude_harness_interchange_only(tmp_path: Path) -> None:
    out_dir = tmp_path / "graphify-out"
    _copy_fixtures(out_dir)
    written = export_claude_harness(out_dir, memory_format="interchange")
    assert [p.name for p in written] == ["harness_memory.v1.json", "fidelity.json"]
    mem = json.loads((out_dir / "harness" / "harness_memory.v1.json").read_text(encoding="utf-8"))
    assert validate_extraction(mem["extraction"]) == []


def test_export_claude_harness_both_includes_json(tmp_path: Path) -> None:
    out_dir = tmp_path / "graphify-out"
    _copy_fixtures(out_dir)
    written = export_claude_harness(out_dir, memory_format="both")
    names = [p.name for p in written]
    assert "harness_memory.v1.json" in names
    assert "claude-SOUL.md" in names


def test_cli_harness_export_format_interchange(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "graphify-out"
    _copy_fixtures(out_dir)
    monkeypatch.chdir(tmp_path)
    rc = subprocess.run(
        [
            sys.executable,
            "-m",
            "graphify",
            "harness",
            "export",
            "--out",
            str(out_dir),
            "--format",
            "interchange",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert rc.returncode == 0, rc.stderr
    assert (out_dir / "harness" / "harness_memory.v1.json").exists()


def test_export_import_semantic_ids_labels_relations(tmp_path: Path) -> None:
    """PORT-04: interchange export → import preserves core fields (documented limits)."""
    from graphify.harness_import import import_harness_path

    out_dir = tmp_path / "graphify-out"
    _copy_fixtures(out_dir)
    export_claude_harness(out_dir, memory_format="interchange")
    mem_path = out_dir / "harness" / "harness_memory.v1.json"
    ingested = import_harness_path(mem_path, format="json", artifacts_root=out_dir)
    raw_graph = json.loads((out_dir / "graph.json").read_text(encoding="utf-8"))
    orig_ids = {n["id"] for n in raw_graph["nodes"]}
    got_ids = {n["id"] for n in ingested["nodes"]}
    assert got_ids == orig_ids
    by_id = {n["id"]: n for n in ingested["nodes"]}
    for n in raw_graph["nodes"]:
        assert by_id[n["id"]]["label"] == n["label"]
    orig_edges = {(e["source"], e["target"], e["relation"]) for e in raw_graph["links"]}
    got_edges = {(e["source"], e["target"], e["relation"]) for e in ingested["edges"]}
    assert got_edges == orig_edges
