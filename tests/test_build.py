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
