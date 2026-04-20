"""Phase 13 — capability manifest, registry alignment, CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def test_validate_cli_drift_message_includes_field_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-04 (Phase 13 review): the drift error must surface graphify_version
    and tool_count so operators can identify the source of the diff without
    rebuilding locally.
    """
    bogus_server = {
        "name": "graphify",
        "_meta": {
            "manifest_content_hash": "0" * 64,
            "graphify_version": "0.0.0-stale",
            "tool_count": 1,
        },
    }
    monkeypatch.setattr(
        "graphify.capability.load_committed_server_json",
        lambda repo_root=None: bogus_server,
    )
    code, err = validate_cli(repo_root=tmp_path)
    assert code != 0
    assert "graphify_version" in err
    assert "tool_count" in err
    assert "committed=0.0.0-stale" in err
    assert "committed=1" in err


def test_validate_cli_narrows_exception_type_in_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-02 (Phase 13 review): bare ``except Exception`` was replaced by a
    narrowed catch list; the error message must surface the exception type
    name so CI logs distinguish failure modes.
    """
    def _explode(repo_root: Path | None = None) -> dict[str, Any]:
        raise FileNotFoundError("server.json missing in test")

    monkeypatch.setattr(
        "graphify.capability.load_committed_server_json", _explode
    )
    code, err = validate_cli(repo_root=tmp_path)
    assert code != 0
    assert "FileNotFoundError" in err
    assert "server.json missing in test" in err


# -------------------------------------------------------------------------
# Phase 13 Plan 02 — MANIFEST-10 docstring → _meta.examples tests
# -------------------------------------------------------------------------


def test_extract_tool_examples_parses_examples_block() -> None:
    """Deterministic, order-preserving extraction of an Examples: block."""
    from graphify.capability import extract_tool_examples

    doc = (
        "Query the graph.\n"
        "\n"
        "Examples:\n"
        "  query_graph(query='transformer')\n"
        "  query_graph(query='attention', limit=5)\n"
    )
    assert extract_tool_examples(doc) == [
        "query_graph(query='transformer')",
        "query_graph(query='attention', limit=5)",
    ]


def test_extract_tool_examples_empty_when_no_block() -> None:
    """Docstring without an Examples: header → [] (not None, not omitted)."""
    from graphify.capability import extract_tool_examples

    doc = "Query the graph.\n\nArgs:\n  query: str\n"
    assert extract_tool_examples(doc) == []


def test_extract_tool_examples_empty_on_none_docstring() -> None:
    """None input is safe."""
    from graphify.capability import extract_tool_examples

    assert extract_tool_examples(None) == []


def test_extract_tool_examples_stops_at_next_section() -> None:
    """Collection terminates on blank line OR next 'Header:' section (e.g. Args:, Returns:)."""
    from graphify.capability import extract_tool_examples

    doc = (
        "Do a thing.\n"
        "\n"
        "Examples:\n"
        "  do_thing(a=1)\n"
        "  do_thing(a=2)\n"
        "Returns:\n"
        "  str\n"
    )
    # 'Returns:' header ends the Examples block; only first two lines captured.
    assert extract_tool_examples(doc) == ["do_thing(a=1)", "do_thing(a=2)"]


def test_meta_examples_populated_in_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-10: at least one tool carries a non-empty _meta.examples list
    when a handler docstring has an Examples: block."""
    from graphify.capability import build_manifest_dict
    from graphify.mcp_tool_registry import tool_names_ordered

    names = tool_names_ordered()
    assert names, "registry must expose at least one tool"
    target_name = names[0]
    monkeypatch.setattr(
        "graphify.mcp_tool_registry.build_handler_docstrings",
        lambda: {
            target_name: (
                "Do something.\n\nExamples:\n  "
                f"{target_name}(a=1)\n  {target_name}(a=2)\n"
            )
        },
    )
    manifest = build_manifest_dict()
    entry = next(t for t in manifest["CAPABILITY_TOOLS"] if t["name"] == target_name)
    assert entry["_meta"]["examples"] == [
        f"{target_name}(a=1)",
        f"{target_name}(a=2)",
    ]


def test_meta_examples_uniform_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-10: tools without Examples: get _meta.examples == [] (field present, empty)."""
    from graphify.capability import build_manifest_dict

    monkeypatch.setattr(
        "graphify.mcp_tool_registry.build_handler_docstrings",
        lambda: {},  # no docstrings → every tool gets []
    )
    manifest = build_manifest_dict()
    for entry in manifest["CAPABILITY_TOOLS"]:
        assert "_meta" in entry
        assert "examples" in entry["_meta"]
        assert entry["_meta"]["examples"] == []


def test_manifest_hash_stable_after_examples_added() -> None:
    """Determinism: two successive build_manifest_dict calls produce identical hash
    (examples list is order-preserving and registry order is stable)."""
    a = build_manifest_dict()
    b = build_manifest_dict()
    assert canonical_manifest_hash(a) == canonical_manifest_hash(b)
    # And every tool carries the examples key:
    for entry in a["CAPABILITY_TOOLS"]:
        assert "_meta" in entry
        assert "examples" in entry["_meta"]
        assert isinstance(entry["_meta"]["examples"], list)
