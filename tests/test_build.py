import json
from pathlib import Path
import graphify.build as build_mod
import graphify.export as export_mod
from graphify.build import build_from_json, build

FIXTURES = Path(__file__).parent / "fixtures"

def load_extraction():
    return json.loads((FIXTURES / "extraction.json").read_text())

def test_build_from_json_node_count():
    G = build_from_json(load_extraction())
    assert G.number_of_nodes() == 4

def test_build_from_json_edge_count():
    G = build_from_json(load_extraction())
    assert G.number_of_edges() == 4

def test_nodes_have_label():
    G = build_from_json(load_extraction())
    assert G.nodes["n_transformer"]["label"] == "Transformer"

def test_edges_have_confidence():
    G = build_from_json(load_extraction())
    data = G.edges["n_attention", "n_concept_attn"]
    assert data["confidence"] == "INFERRED"

def test_ambiguous_edge_preserved():
    G = build_from_json(load_extraction())
    data = G.edges["n_layernorm", "n_concept_attn"]
    assert data["confidence"] == "AMBIGUOUS"

def test_build_merges_multiple_extractions():
    ext1 = {"nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
            "edges": [], "input_tokens": 0, "output_tokens": 0}
    ext2 = {"nodes": [{"id": "n2", "label": "B", "file_type": "document", "source_file": "b.md"}],
            "edges": [{"source": "n1", "target": "n2", "relation": "references",
                       "confidence": "INFERRED", "source_file": "b.md", "weight": 1.0}],
            "input_tokens": 0, "output_tokens": 0}
    G = build([ext1, ext2])
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1


def test_build_from_json_default_off():
    """CFED-01: build_from_json without peers kwarg behaves identically to pre-Phase-66."""
    G = build_from_json(load_extraction())
    # Snapshot baseline values captured BEFORE Phase 66 changes:
    assert G.number_of_nodes() == 4
    assert G.number_of_edges() == 4


# Phase 70.2-02 (CCONF-05 / CFED-03): SCHEMA_VERSION single source of truth.

def _minimal_extraction():
    return {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
        "edges": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }


def test_schema_version_constant_value():
    """SCHEMA_VERSION bumped to '2.0' by Phase 71 (TEMP, D-8) for temporal schema."""
    assert build_mod.SCHEMA_VERSION == "2.0"


def test_build_from_json_stamps_schema_version():
    """build_from_json must stamp schema_version on the returned graph."""
    G = build_from_json(_minimal_extraction())
    assert G.graph["schema_version"] == build_mod.SCHEMA_VERSION


def test_build_stamps_schema_version():
    """build() must stamp schema_version on the returned graph."""
    G = build([_minimal_extraction()])
    assert G.graph["schema_version"] == build_mod.SCHEMA_VERSION


def test_export_uses_build_schema_version():
    """export.py must source SCHEMA_VERSION from build (no duplicate literal)."""
    assert getattr(export_mod, "SCHEMA_VERSION", None) is build_mod.SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Phase 71-02 (TEMP-01 / TEMP-02): build-time temporal stamping.
# ---------------------------------------------------------------------------

def _temporal_extraction(confidence: str = "EXTRACTED", relation: str = "contains",
                         valid_from: str | None = None) -> dict:
    edge = {
        "source": "n1",
        "target": "n2",
        "relation": relation,
        "confidence": confidence,
        "source_file": "a.py",
        "weight": 1.0,
    }
    if valid_from is not None:
        edge["valid_from"] = valid_from
    return {
        "nodes": [
            {"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "B", "file_type": "code", "source_file": "a.py"},
        ],
        "edges": [edge],
        "input_tokens": 0,
        "output_tokens": 0,
    }


def test_build_stamps_valid_from(pinned_run_ts):
    G = build_from_json(_temporal_extraction())
    for _, _, data in G.edges(data=True):
        assert data["valid_from"] == pinned_run_ts


def test_build_valid_until_none_default(pinned_run_ts):
    G = build_from_json(_temporal_extraction())
    for _, _, data in G.edges(data=True):
        assert data["valid_until"] is None


def test_build_extracted_decay_one(pinned_run_ts):
    G = build_from_json(_temporal_extraction(confidence="EXTRACTED"))
    for _, _, data in G.edges(data=True):
        assert data["decay_weight"] == 1.0


def test_build_inferred_decays(pinned_run_ts):
    # Edge pre-stamped 60 days before pinned_run_ts → INFERRED should decay
    old_ts = "2026-03-08T12:00:00+00:00"
    G = build_from_json(_temporal_extraction(
        confidence="INFERRED", relation="references", valid_from=old_ts
    ))
    for _, _, data in G.edges(data=True):
        assert 0.0 <= data["decay_weight"] < 1.0


def test_build_ambiguous_decays_like_inferred(pinned_run_ts):
    # Pitfall 6 / Assumption A4: AMBIGUOUS decays just like INFERRED.
    old_ts = "2026-03-08T12:00:00+00:00"
    G = build_from_json(_temporal_extraction(
        confidence="AMBIGUOUS", relation="references", valid_from=old_ts
    ))
    for _, _, data in G.edges(data=True):
        assert 0.0 <= data["decay_weight"] < 0.5


def test_schema_version_2_0_in_memory(pinned_run_ts):
    G1 = build_from_json(_temporal_extraction())
    assert G1.graph["schema_version"] == "2.0"
    G2 = build([_temporal_extraction()])
    assert G2.graph["schema_version"] == "2.0"


def test_run_now_computed_once(pinned_run_ts, monkeypatch):
    """Pitfall 3 / D-1: run_now_iso must be called exactly once per build_from_json."""
    counter = {"n": 0}
    real = build_mod.run_now_iso

    def counting():
        counter["n"] += 1
        return real()

    monkeypatch.setattr(build_mod, "run_now_iso", counting)
    # Multi-edge extraction to ensure the call is not inside the per-edge loop.
    ext = {
        "nodes": [
            {"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "B", "file_type": "code", "source_file": "a.py"},
            {"id": "n3", "label": "C", "file_type": "code", "source_file": "a.py"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "relation": "contains",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
            {"source": "n2", "target": "n3", "relation": "contains",
             "confidence": "INFERRED", "source_file": "a.py", "weight": 1.0},
            {"source": "n1", "target": "n3", "relation": "references",
             "confidence": "AMBIGUOUS", "source_file": "a.py", "weight": 1.0},
        ],
        "input_tokens": 0,
        "output_tokens": 0,
    }
    build_from_json(ext)
    assert counter["n"] == 1


def test_existing_temporal_fields_preserved(pinned_run_ts):
    """T-71-08: pre-stamped valid_from must NOT be overwritten (setdefault, not assign)."""
    pre_ts = "2025-01-01T00:00:00+00:00"
    G = build_from_json(_temporal_extraction(
        confidence="EXTRACTED", valid_from=pre_ts
    ))
    for _, _, data in G.edges(data=True):
        assert data["valid_from"] == pre_ts


# ---------------------------------------------------------------------------
# Phase 71-04 Task 1: stamp_supersessions integration into build_from_json
# ---------------------------------------------------------------------------


def _write_prior_graph(out_dir: Path, edges: list[dict], nodes: list[dict] | None = None) -> Path:
    """Write a prior graphify-out/graph.json under out_dir with the given edges."""
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "directed": False,
        "multigraph": False,
        "graph": {"schema_version": "2.0"},
        "nodes": nodes or [
            {"id": "a", "label": "A", "file_type": "code", "source_file": "f1.py"},
            {"id": "b", "label": "B", "file_type": "code", "source_file": "f1.py"},
        ],
        "links": edges,
        "schema_version": "2.0",
    }
    p = out_dir / "graph.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _ext_two_nodes(extra_edges: list[dict] | None = None) -> dict:
    return {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "code", "source_file": "f1.py"},
            {"id": "b", "label": "B", "file_type": "code", "source_file": "f1.py"},
        ],
        "edges": list(extra_edges or []),
        "input_tokens": 0,
        "output_tokens": 0,
    }


def test_supersession_inferred_integration(pinned_run_ts, tmp_path):
    """D-4 / D-6: prior INFERRED edge missing in new run → stamped with valid_until=run_now."""
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 0.7,
    }
    _write_prior_graph(tmp_path / "graphify-out", [prior_edge])
    # New run does NOT contain (a,b,calls).
    G = build_from_json(_ext_two_nodes(extra_edges=[]), target_dir=tmp_path)
    # Edge must persist in graph with valid_until set (D-6 history retained).
    assert G.has_edge("a", "b")
    data = G.get_edge_data("a", "b")
    assert data["valid_until"] == pinned_run_ts
    assert data["confidence"] == "INFERRED"


def test_supersession_extracted_not_stamped_integration(pinned_run_ts, tmp_path):
    """D-4: prior EXTRACTED edge missing in new run → NOT stamped, NOT appended."""
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "EXTRACTED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 1.0,
    }
    _write_prior_graph(tmp_path / "graphify-out", [prior_edge])
    G = build_from_json(_ext_two_nodes(extra_edges=[]), target_dir=tmp_path)
    # EXTRACTED prior is never carried forward as superseded.
    assert not G.has_edge("a", "b")


def test_supersession_global_rule_integration(pinned_run_ts, tmp_path):
    """D-5: prior (a,b,calls) from f1.py; new run produces same tuple from f2.py → NO supersession."""
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 0.7,
    }
    _write_prior_graph(tmp_path / "graphify-out", [prior_edge])
    new_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f2.py", "weight": 1.0,
    }
    G = build_from_json(_ext_two_nodes(extra_edges=[new_edge]), target_dir=tmp_path)
    # Single edge remains current — no superseded duplicate.
    assert G.has_edge("a", "b")
    data = G.get_edge_data("a", "b")
    assert data["valid_until"] is None


def test_supersession_persists_in_graph(pinned_run_ts, tmp_path):
    """D-6: superseded edge appears in nx.Graph result with valid_until set."""
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 0.7,
    }
    _write_prior_graph(tmp_path / "graphify-out", [prior_edge])
    G = build_from_json(_ext_two_nodes(extra_edges=[]), target_dir=tmp_path)
    # graph contains the edge (history not deleted)
    assert G.number_of_edges() == 1
    data = G.get_edge_data("a", "b")
    assert data["valid_until"] == pinned_run_ts


def test_supersession_no_prior_graph(pinned_run_ts, tmp_path):
    """Pitfall 1: first-ever run (no prior graph.json) → no supersession, no error."""
    new_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
    }
    # No prior graph.json exists under tmp_path.
    G = build_from_json(_ext_two_nodes(extra_edges=[new_edge]), target_dir=tmp_path)
    assert G.has_edge("a", "b")
    data = G.get_edge_data("a", "b")
    assert data["valid_until"] is None


def test_supersession_path_resolution_default_mode(pinned_run_ts, tmp_path, monkeypatch):
    """Default mode: prior path = target_dir/graphify-out/graph.json (mirrors __main__.py)."""
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 0.7,
    }
    _write_prior_graph(tmp_path / "graphify-out", [prior_edge])
    monkeypatch.chdir(tmp_path)
    # No target_dir, no resolved_output → cwd/graphify-out/graph.json
    G = build_from_json(_ext_two_nodes(extra_edges=[]))
    assert G.has_edge("a", "b")
    assert G.get_edge_data("a", "b")["valid_until"] == pinned_run_ts


def test_supersession_path_resolution_vault_mode(pinned_run_ts, tmp_path):
    """Pitfall 1: vault output mode resolves prior graph path via ResolvedOutput.artifacts_dir."""
    from graphify.output import ResolvedOutput
    artifacts_dir = tmp_path / "vault" / ".graphify"
    prior_edge = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
        "valid_from": "2025-12-01T00:00:00+00:00", "valid_until": None,
        "decay_weight": 0.7,
    }
    # In vault mode, prior graph.json lives directly under artifacts_dir, not under
    # artifacts_dir/graphify-out (artifacts_dir IS the graphify-out equivalent).
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "graph.json").write_text(
        json.dumps({
            "directed": False,
            "multigraph": False,
            "graph": {"schema_version": "2.0"},
            "nodes": [
                {"id": "a", "label": "A", "file_type": "code", "source_file": "f1.py"},
                {"id": "b", "label": "B", "file_type": "code", "source_file": "f1.py"},
            ],
            "links": [prior_edge],
            "schema_version": "2.0",
        }),
        encoding="utf-8",
    )
    resolved = ResolvedOutput(
        vault_detected=True,
        vault_path=tmp_path / "vault",
        notes_dir=tmp_path / "vault",
        artifacts_dir=artifacts_dir,
        source="vault",
    )
    G = build_from_json(_ext_two_nodes(extra_edges=[]), resolved_output=resolved)
    assert G.has_edge("a", "b")
    assert G.get_edge_data("a", "b")["valid_until"] == pinned_run_ts


# ---------------------------------------------------------------------------
# Phase 71-04 Task 2: _merge_edge_fields temporal awareness (Pitfall 5)
# ---------------------------------------------------------------------------

from graphify.build import _merge_edge_fields  # noqa: E402


def _base_edge(**kw):
    e = {
        "source": "a", "target": "b", "relation": "calls",
        "confidence": "INFERRED", "source_file": "f1.py", "weight": 1.0,
    }
    e.update(kw)
    return e


def test_merge_mixed_temporal_status_current_wins():
    """Pitfall 5: any input with valid_until=None → merged result is None (current wins)."""
    e1 = _base_edge(valid_from="2025-01-01T00:00:00+00:00", valid_until=None)
    e2 = _base_edge(valid_from="2025-06-01T00:00:00+00:00",
                    valid_until="2026-01-01T00:00:00+00:00")
    merged = _merge_edge_fields(e1, e2)
    assert merged["valid_until"] is None


def test_merge_preserves_earliest_valid_from():
    """Earliest valid_from preserved (lex sort works for ISO-8601 UTC)."""
    e1 = _base_edge(valid_from="2025-06-01T00:00:00+00:00", valid_until=None)
    e2 = _base_edge(valid_from="2025-01-01T00:00:00+00:00", valid_until=None)
    merged = _merge_edge_fields(e1, e2)
    assert merged["valid_from"] == "2025-01-01T00:00:00+00:00"


def test_merge_both_superseded_keeps_latest_valid_until():
    """When ALL inputs have valid_until set, result keeps the LATEST."""
    e1 = _base_edge(valid_from="2025-01-01T00:00:00+00:00",
                    valid_until="2025-12-01T00:00:00+00:00")
    e2 = _base_edge(valid_from="2025-02-01T00:00:00+00:00",
                    valid_until="2026-03-01T00:00:00+00:00")
    merged = _merge_edge_fields(e1, e2)
    assert merged["valid_until"] == "2026-03-01T00:00:00+00:00"


def test_merge_preserves_decay_weight_max():
    """decay_weight = max(inputs) — current/highest-confidence dominates merge."""
    e1 = _base_edge(decay_weight=0.3)
    e2 = _base_edge(decay_weight=0.9)
    merged = _merge_edge_fields(e1, e2)
    assert merged["decay_weight"] == 0.9


def test_merge_no_temporal_fields():
    """Regression guard: legacy merge path (no temporal fields) is unaffected."""
    e1 = _base_edge()
    e2 = _base_edge(source_file="f2.py")
    merged = _merge_edge_fields(e1, e2)
    assert "valid_from" not in merged
    assert "valid_until" not in merged
    assert "decay_weight" not in merged
    # Existing semantics still hold:
    assert "f1.py" in merged["source_file"] and "f2.py" in merged["source_file"]
