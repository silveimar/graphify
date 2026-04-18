"""Phase 13 — capability manifest, registry alignment, CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.capability import (
    build_manifest_dict,
    canonical_manifest_hash,
    validate_manifest,
    validate_cli,
    write_manifest_atomic,
)


def test_manifest_hash_stable() -> None:
    a = build_manifest_dict()
    b = build_manifest_dict()
    assert canonical_manifest_hash(a) == canonical_manifest_hash(b)


def test_schema_validates_built_manifest() -> None:
    m = build_manifest_dict()
    validate_manifest(m)


def test_manifest_tool_names_match_registry() -> None:
    from graphify.mcp_tool_registry import build_mcp_tools

    m = build_manifest_dict()
    reg = {t.name for t in build_mcp_tools()}
    man = {t["name"] for t in m["CAPABILITY_TOOLS"]}
    assert reg == man


def test_validate_cli_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = Path(__file__).resolve().parents[1]
    server_src = root / "server.json"
    (tmp_path / "server.json").write_text(server_src.read_text(encoding="utf-8"), encoding="utf-8")
    code, err = validate_cli(repo_root=tmp_path)
    assert code == 0
    assert err == ""


def test_atomic_manifest_roundtrip(tmp_path: Path) -> None:
    m = build_manifest_dict()
    p = write_manifest_atomic(tmp_path, m)
    assert p.exists()
    roundtrip = json.loads(p.read_text(encoding="utf-8"))
    assert canonical_manifest_hash(roundtrip) == canonical_manifest_hash(m)


def test_pipeline_writes_manifest_json(tmp_path: Path) -> None:
    """MANIFEST-02: export.to_json triggers manifest.json (uses same deps as CI [mcp])."""
    from networkx import Graph
    from graphify.export import to_json

    G = Graph()
    G.add_node("a", label="a", source_file="x", source_location="", file_type="py", community=0)
    to_json(G, {0: ["a"]}, str(tmp_path / "graph.json"))
    man = tmp_path / "manifest.json"
    assert man.exists()
    data = json.loads(man.read_text(encoding="utf-8"))
    validate_manifest(data)


# -------------------------------------------------------------------------
# Phase 13 Plan 02 — MANIFEST-09 CI drift gate tests (D-03 stderr contract)
# -------------------------------------------------------------------------


def test_validate_cli_drift_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MANIFEST-09 + D-03: committed hash differs from live → non-zero exit,
    stderr contains expected-hash, actual-hash, server.json path, and regenerate command."""
    bogus_server = {
        "name": "graphify",
        "_meta": {"manifest_content_hash": "0" * 64},
    }
    monkeypatch.setattr(
        "graphify.capability.load_committed_server_json",
        lambda repo_root=None: bogus_server,
    )
    code, err = validate_cli(repo_root=tmp_path)
    assert code != 0
    # D-03 stability — assert each literal token independently:
    assert "expected" in err
    assert "actual" in err
    assert "server.json" in err
    assert "graphify capability --stdout > server.json" in err


def test_validate_cli_clean_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """validate_cli returns 0 when committed hash matches live hash."""
    from graphify.capability import build_manifest_dict, canonical_manifest_hash

    live_hash = canonical_manifest_hash(build_manifest_dict())
    clean_server = {
        "name": "graphify",
        "_meta": {"manifest_content_hash": live_hash},
    }
    monkeypatch.setattr(
        "graphify.capability.load_committed_server_json",
        lambda repo_root=None: clean_server,
    )
    code, err = validate_cli(repo_root=tmp_path)
    assert code == 0
    assert err == ""


def test_validate_cli_no_huge_diff_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-03: 'no huge unified diffs by default' — minimal failure path stays short."""
    bogus_server = {
        "name": "graphify",
        "_meta": {"manifest_content_hash": "0" * 64},
    }
    monkeypatch.setattr(
        "graphify.capability.load_committed_server_json",
        lambda repo_root=None: bogus_server,
    )
    code, err = validate_cli(repo_root=tmp_path)
    assert code != 0
    assert len(err) < 2000
