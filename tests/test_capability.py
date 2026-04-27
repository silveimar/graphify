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


def test_argue_topic_not_composable() -> None:
    """ARGUE-07 D-15: argue_topic.composable_from must be [] — Phase 17 chat recursion guard."""
    m = build_manifest_dict()
    tool = next((t for t in m["CAPABILITY_TOOLS"] if t["name"] == "argue_topic"), None)
    assert tool is not None, "argue_topic missing from manifest"
    assert tool.get("composable_from") == [], (
        "argue_topic.composable_from must be [] to prevent Phase 17 chat recursion"
    )


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


def test_pipeline_writes_capability_json(tmp_path: Path) -> None:
    """MANIFEST-02: export.to_json triggers capability.json (uses same deps as CI [mcp]).

    Regression (quick-260422-jdj): the capability manifest was previously written
    to graphify-out/manifest.json, colliding with detect.py's incremental mtime
    manifest at the same path. The capability writer now targets capability.json;
    the detect incremental manifest remains at manifest.json.
    """
    from networkx import Graph
    from graphify.export import to_json

    G = Graph()
    G.add_node("a", label="a", source_file="x", source_location="", file_type="py", community=0)
    to_json(G, {0: ["a"]}, str(tmp_path / "graph.json"))
    cap = tmp_path / "capability.json"
    assert cap.exists()
    data = json.loads(cap.read_text(encoding="utf-8"))
    validate_manifest(data)
    # Negative assertion: the capability writer MUST NOT clobber manifest.json
    # (owned by detect.py for incremental mtime tracking).
    assert not (tmp_path / "manifest.json").exists()


def test_capability_writer_basename_is_not_manifest_json(tmp_path: Path) -> None:
    """Regression (quick-260422-jdj): capability writer MUST NOT target 'manifest.json'
    (collides with detect incremental manifest at graphify-out/manifest.json)."""
    target = write_manifest_atomic(tmp_path, {"CAPABILITY_TOOLS": []})
    assert target.name == "capability.json"
    assert target.name != "manifest.json"
    assert not (tmp_path / "manifest.json").exists()


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
    """Deterministic, order-preserving extraction of an Examples: block.

    WR-07 (Phase 13 review): the new grammar treats blank lines as the
    entry-separator inside the Examples block. Each contiguous run of
    non-blank lines becomes one entry, with relative indentation
    preserved.
    """
    from graphify.capability import extract_tool_examples

    doc = (
        "Query the graph.\n"
        "\n"
        "Examples:\n"
        "  query_graph(query='transformer')\n"
        "\n"
        "  query_graph(query='attention', limit=5)\n"
    )
    assert extract_tool_examples(doc) == [
        "query_graph(query='transformer')",
        "query_graph(query='attention', limit=5)",
    ]


def test_extract_tool_examples_preserves_multiline_indentation() -> None:
    """WR-07 (Phase 13 review): a multi-line example (e.g. an indented
    if-body) must keep its internal newlines and relative indentation —
    the old per-line ``.strip()`` collapsed both.
    """
    from graphify.capability import extract_tool_examples

    doc = (
        "Run a thing.\n"
        "\n"
        "Examples:\n"
        "    if x is None:\n"
        "        run(default=True)\n"
        "    else:\n"
        "        run(value=x)\n"
        "\n"
        "    run(value=2)\n"
    )
    examples = extract_tool_examples(doc)
    assert len(examples) == 2
    # First entry preserves internal newlines and the 4-space relative
    # indent of the if/else bodies after textwrap.dedent removes the
    # common 4-space leader.
    assert examples[0] == (
        "if x is None:\n"
        "    run(default=True)\n"
        "else:\n"
        "    run(value=x)"
    )
    assert examples[1] == "run(value=2)"


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
    """Collection terminates on the next 'Header:' section (Args:, Returns:).

    WR-07 (Phase 13 review): a blank line inside the Examples block is now
    only an entry-separator — it does NOT close the block. Only a section
    header (or EOF) closes it.
    """
    from graphify.capability import extract_tool_examples

    doc = (
        "Do a thing.\n"
        "\n"
        "Examples:\n"
        "  do_thing(a=1)\n"
        "\n"
        "  do_thing(a=2)\n"
        "Returns:\n"
        "  str\n"
    )
    # 'Returns:' header ends the Examples block; the two example calls are
    # captured as separate entries thanks to the blank-line separator.
    assert extract_tool_examples(doc) == ["do_thing(a=1)", "do_thing(a=2)"]


def test_meta_examples_populated_in_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-10: at least one tool carries a non-empty _meta.examples list
    when a handler docstring has an Examples: block."""
    from graphify.capability import build_manifest_dict
    from graphify.mcp_tool_registry import tool_names_ordered

    names = tool_names_ordered()
    assert names, "registry must expose at least one tool"
    target_name = names[0]
    # WR-07 (Phase 13 review): blank line is the entry-separator under
    # the new grammar so each call becomes its own _meta.examples entry.
    monkeypatch.setattr(
        "graphify.mcp_tool_registry.build_handler_docstrings",
        lambda: {
            target_name: (
                "Do something.\n\nExamples:\n  "
                f"{target_name}(a=1)\n\n  {target_name}(a=2)\n"
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


def test_all_registered_tools_have_explicit_meta_yaml() -> None:
    """MANIFEST-06: every registered MCP tool must have an explicit entry in
    capability_tool_meta.yaml — no silent cascade to defaults. Guards against
    the `chat` / `get_focus_context` drift found in v1.4 milestone audit."""
    import yaml

    from graphify.mcp_tool_registry import build_mcp_tools

    meta_path = Path(__file__).resolve().parent.parent / "graphify" / "capability_tool_meta.yaml"
    meta_keys = set(yaml.safe_load(meta_path.read_text()).keys())
    registry_names = {t.name for t in build_mcp_tools()}
    missing = registry_names - meta_keys
    assert not missing, (
        f"Registered MCP tools missing explicit metadata in capability_tool_meta.yaml: "
        f"{sorted(missing)}. Add entries with cost_class, deterministic, "
        f"cacheable_until, composable_from."
    )


def test_chat_cost_class_expensive() -> None:
    """MANIFEST-06: chat must not cascade to default cheap — it is expensive."""
    m = build_manifest_dict()
    tool = next((t for t in m["CAPABILITY_TOOLS"] if t["name"] == "chat"), None)
    assert tool is not None, "chat missing from manifest"
    assert tool.get("cost_class") == "expensive", (
        f"chat.cost_class must be 'expensive', got {tool.get('cost_class')!r} — "
        f"likely cascaded to default because capability_tool_meta.yaml lacks a `chat:` entry."
    )
    assert tool.get("deterministic") is False
    assert tool.get("composable_from") == [], (
        "chat.composable_from must be [] — recursion guard pairs with argue_topic."
    )


def test_get_focus_context_metadata_declared() -> None:
    """MANIFEST-06: get_focus_context must have explicit metadata, not cascade defaults."""
    m = build_manifest_dict()
    tool = next((t for t in m["CAPABILITY_TOOLS"] if t["name"] == "get_focus_context"), None)
    assert tool is not None, "get_focus_context missing from manifest"
    assert tool.get("cost_class") == "cheap"
    assert tool.get("deterministic") is True
    assert tool.get("cacheable_until") == "graph_mtime"


def test_subpath_isolation_capability_manifest(tmp_path: Path) -> None:
    """MANIFEST-11: two sequential write_manifest_atomic() calls with disjoint tool sets preserve union."""
    import json

    data_a = {
        "manifest_version": "1",
        "graphify_version": "test",
        "CAPABILITY_TOOLS": [{"name": "tool_alpha", "description": "a", "inputSchema": {}}],
    }
    data_b = {
        "manifest_version": "1",
        "graphify_version": "test",
        "CAPABILITY_TOOLS": [{"name": "tool_beta", "description": "b", "inputSchema": {}}],
    }
    write_manifest_atomic(tmp_path, data_a)
    write_manifest_atomic(tmp_path, data_b)

    result = json.loads((tmp_path / "capability.json").read_text(encoding="utf-8"))
    names = {t["name"] for t in result["CAPABILITY_TOOLS"]}
    assert "tool_alpha" in names, "tool_alpha (sub_a run) must survive sub_b write"
    assert "tool_beta" in names, "tool_beta (sub_b run) must be present"
