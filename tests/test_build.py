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
    """SCHEMA_VERSION is locked to '1.13' for backward compat with prior writes."""
    assert build_mod.SCHEMA_VERSION == "1.13"


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
