"""Tests for tacit-to-explicit elicitation (Phase 39)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.build import build
from graphify.elicit import (
    ELICITATION_SIDECAR_FILENAME,
    build_extraction_from_session,
    load_elicitation_sidecar,
    merge_elicitation_into_build_inputs,
    run_scripted_elicitation,
    save_elicitation_sidecar,
)
from graphify.validate import validate_extraction


def _sample_answers() -> dict[str, str]:
    return {
        "rhythms": "Daily standup, weekly retro",
        "decisions": "Prefer small PRs",
        "dependencies": "Platform team for deploys",
        "knowledge": "Internal runbooks are outdated",
        "friction": "Context switching",
    }


def test_scripted_path_validates() -> None:
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext = build_extraction_from_session(session)
    err = validate_extraction(ext)
    assert err == [], err
    assert len(ext["nodes"]) == 6
    assert len(ext["edges"]) == 5


def test_save_sidecar_confined_to_artifacts_dir(tmp_path: Path) -> None:
    adir = tmp_path / "graphify-out"
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext = build_extraction_from_session(session)
    out = save_elicitation_sidecar(adir, ext)
    assert out.is_file()
    assert out.name == ELICITATION_SIDECAR_FILENAME
    assert out.parent.resolve() == adir.resolve()

    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert validate_extraction(raw["extraction"]) == []


def test_second_save_without_force_merges_by_id(tmp_path: Path) -> None:
    adir = tmp_path / "out"
    a1 = _sample_answers()
    s1 = run_scripted_elicitation(a1, auto_confirm=True)
    ext1 = build_extraction_from_session(s1)
    save_elicitation_sidecar(adir, ext1, force=True)

    a2 = dict(a1)
    a2["friction"] = "Updated friction note"
    s2 = run_scripted_elicitation(a2, auto_confirm=True)
    ext2 = build_extraction_from_session(s2)
    path = save_elicitation_sidecar(adir, ext2, force=False)

    payload = json.loads(path.read_text(encoding="utf-8"))
    merged = payload["extraction"]
    assert validate_extraction(merged) == []
    by_id = {n["id"]: n for n in merged["nodes"] if isinstance(n, dict)}
    assert by_id["elicitation_friction"]["label"] == "Updated friction note"
    assert len(merged["nodes"]) == 6


def test_save_rejects_path_escape(tmp_path: Path) -> None:
    adir = tmp_path / "safe"
    adir.mkdir()
    (tmp_path / "outside").mkdir()
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext = build_extraction_from_session(session)
    with pytest.raises(ValueError, match="escapes"):
        save_elicitation_sidecar(adir, ext, filename="../outside/elicitation.json")


def test_load_roundtrip(tmp_path: Path) -> None:
    adir = tmp_path / "gfo"
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext = build_extraction_from_session(session)
    save_elicitation_sidecar(adir, ext, force=True)
    loaded = load_elicitation_sidecar(adir)
    assert loaded is not None
    assert validate_extraction(loaded) == []


def test_module_docstring_contract() -> None:
    import graphify.elicit as e

    assert e.__doc__
    assert "elicitation.json" in e.__doc__


def test_build_includes_elicitation_last_wins(tmp_path: Path) -> None:
    """Sidecar merges after base extraction; duplicate node id uses elicitation."""
    adir = tmp_path / "art"
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext_elic = build_extraction_from_session(session)
    save_elicitation_sidecar(adir, ext_elic, force=True)

    base_like = {
        "nodes": [
            {
                "id": "elicitation_hub",
                "label": "from code",
                "file_type": "code",
                "source_file": "x.py",
            }
        ],
        "edges": [],
    }
    seq = merge_elicitation_into_build_inputs([base_like], adir)
    G = build(seq)
    hub = G.nodes.get("elicitation_hub")
    assert hub is not None
    assert hub.get("file_type") == "rationale"


def test_build_explicit_elicitation_kw(tmp_path: Path) -> None:
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext_elic = build_extraction_from_session(session)
    G = build([{"nodes": [], "edges": []}], elicitation=ext_elic)
    assert "elicitation_hub" in G.nodes


def test_merge_helper_without_sidecar_returns_original() -> None:
    base = [{"nodes": [{"id": "a", "label": "A", "file_type": "code", "source_file": ""}], "edges": []}]
    assert merge_elicitation_into_build_inputs(base, None) == base


def test_write_elicitation_harness_markdown_writes_blocks(tmp_path: Path) -> None:
    from graphify.elicit import write_elicitation_harness_markdown

    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    written = write_elicitation_harness_markdown(tmp_path / "graphify-out", session)
    names = {p.name for p in written}
    assert "claude-SOUL.md" in names
    assert "claude-HEARTBEAT.md" in names
    assert "claude-USER.md" in names
    assert "fidelity.json" in names
