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


def test_sidecar_node_id_collision_elicitation_wins(tmp_path: Path) -> None:
    """ELIC-01 D-02: elicitation node attrs win over base extraction node attrs."""
    adir = tmp_path / "art"
    base = {
        "nodes": [
            {
                "id": "shared",
                "label": "from code",
                "file_type": "code",
                "source_file": "x.py",
            }
        ],
        "edges": [],
    }
    elic = {
        "nodes": [
            {
                "id": "shared",
                "label": "from elicit",
                "file_type": "rationale",
                "source_file": "",
            }
        ],
        "edges": [],
    }
    save_elicitation_sidecar(adir, elic, force=True)
    seq = merge_elicitation_into_build_inputs([base], adir)
    G = build(seq)
    assert G.nodes["shared"]["label"] == "from elicit"
    assert G.nodes["shared"]["file_type"] == "rationale"


def test_sidecar_edge_conflicting_relation_last_wins(tmp_path: Path) -> None:
    """ELIC-01 D-02: elicitation relation overwrites base on same (source,target)."""
    adir = tmp_path / "art"
    base = {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "code", "source_file": "f.py"},
            {"id": "b", "label": "B", "file_type": "code", "source_file": "f.py"},
        ],
        "edges": [
            {
                "source": "a",
                "target": "b",
                "relation": "calls",
                "confidence": "EXTRACTED",
                "source_file": "f.py",
            }
        ],
    }
    elic = {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "code", "source_file": ""},
            {"id": "b", "label": "B", "file_type": "code", "source_file": ""},
        ],
        "edges": [
            {
                "source": "a",
                "target": "b",
                "relation": "depends_on",
                "confidence": "INFERRED",
                "source_file": "",
            }
        ],
    }
    save_elicitation_sidecar(adir, elic, force=True)
    seq = merge_elicitation_into_build_inputs([base], adir)
    G = build(seq)
    assert G.edges["a","b"]["relation"] == "depends_on"
    assert G.edges["a","b"]["confidence"] == "INFERRED"


def test_sidecar_preserves_confidence_across_merge(tmp_path: Path) -> None:
    """ELIC-01 D-02: confidence value is preserved across the sidecar merge."""
    adir = tmp_path / "art"
    base = {"nodes": [], "edges": []}
    elic = {
        "nodes": [
            {"id": "x", "label": "X", "file_type": "rationale", "source_file": ""}
        ],
        "edges": [
            {
                "source": "x",
                "target": "x",
                "relation": "refs",
                "confidence": "AMBIGUOUS",
                "source_file": "",
            }
        ],
    }
    save_elicitation_sidecar(adir, elic, force=True)
    seq = merge_elicitation_into_build_inputs([base], adir)
    G = build(seq)
    assert G.edges["x", "x"]["confidence"] == "AMBIGUOUS"


def test_malformed_sidecar_loader_returns_none(tmp_path: Path, capsys) -> None:
    """ELIC-01 D-03: malformed JSON returns None and warns to stderr."""
    adir = tmp_path / "art"
    adir.mkdir()
    (adir / "elicitation.json").write_bytes(b"{this is not json")
    assert load_elicitation_sidecar(adir) is None
    err = capsys.readouterr().err
    assert "[graphify] elicitation sidecar invalid JSON" in err


def test_sidecar_missing_required_fields_rejected(tmp_path: Path) -> None:
    """ELIC-01 D-03: save rejects extraction missing required node fields."""
    bad_extraction = {
        "nodes": [{"id": "x", "label": "X", "source_file": "f.py"}],
        "edges": [],
    }
    with pytest.raises(ValueError):
        save_elicitation_sidecar(tmp_path / "art", bad_extraction, force=True)


def test_sidecar_edge_referencing_absent_node(tmp_path: Path) -> None:
    """ELIC-01 D-03: build() tolerates dangling edges from sidecar without exception.

    The save-time validator (validate_extraction) rejects dangling edges, so we author
    the sidecar payload directly on disk to simulate a sidecar produced by a future
    relaxed validator or external tooling. This locks build()'s tolerance: dangling
    edges are silently filtered (no exception), the explicit node is preserved, and
    the absent endpoint is NOT auto-created (build_from_json filters edges where
    either endpoint is missing from node_set — "dangling edges to external/stdlib
    nodes — expected, not an error", per build.py).
    """
    adir = tmp_path / "art"
    adir.mkdir()
    payload = {
        "version": 1,
        "extraction": {
            "nodes": [
                {"id": "x", "label": "X", "file_type": "rationale", "source_file": ""}
            ],
            "edges": [
                {
                    "source": "x",
                    "target": "ghost",
                    "relation": "refs",
                    "confidence": "AMBIGUOUS",
                    "source_file": "",
                }
            ],
        },
        "meta": {},
    }
    (adir / "elicitation.json").write_text(json.dumps(payload), encoding="utf-8")
    seq = merge_elicitation_into_build_inputs([{"nodes": [], "edges": []}], adir)
    G = build(seq)  # must not raise
    assert "x" in G.nodes
    # Dangling edge is silently dropped by build_from_json (endpoint not in node_set).
    assert "ghost" not in G.nodes
    assert ("x", "ghost") not in G.edges and ("ghost", "x") not in G.edges


# ---------------------------------------------------------------------------
# ELIC-02 / HARN-01 doc-content regression locks (Phase 57 Plan 02)
# ---------------------------------------------------------------------------

_DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "ELICITATION.md"


def test_doc_has_trust_boundaries_section() -> None:
    """ELIC-02: docs/ELICITATION.md surfaces the trust-boundary contract."""
    text = _DOC_PATH.read_text(encoding="utf-8")
    assert "## Trust Boundaries" in text
    assert "resolve_output" in text
    assert "<artifacts_dir>/elicitation.json" in text
    assert "sanitize_harness_text" in text


def test_doc_has_milestone_non_goals_section() -> None:
    """ELIC-02: heading renamed in place to milestone-scoped Non-Goals."""
    text = _DOC_PATH.read_text(encoding="utf-8")
    assert "## Milestone Non-Goals (v1.11)" in text
    assert "## Non-goals (other phases)" not in text
    assert "Real inverse round-trip" in text


def test_doc_has_canonical_mapping() -> None:
    """HARN-01: doc carries canonical mapping section + schema id + mapping fn name."""
    text = _DOC_PATH.read_text(encoding="utf-8")
    assert "## Canonical Harness Interchange (v1) Mapping" in text
    assert "graphify.harness.interchange/v1" in text
    assert "graph_data_to_extraction" in text
