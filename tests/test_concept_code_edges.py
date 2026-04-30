"""Concept↔code edge normalization and relation warnings (Phase 46)."""

import json
import tempfile
from pathlib import Path

from graphify.build import build_from_json
from graphify.export import to_json
from graphify.cluster import cluster
from graphify.validate import validate_extraction


def test_implemented_by_normalizes_to_implements_orient_code_to_concept():
    extraction = {
        "nodes": [
            {"id": "c_doc", "label": "Concept", "file_type": "document", "source_file": "c.md"},
            {"id": "k_code", "label": "Klass", "file_type": "code", "source_file": "k.py"},
        ],
        "edges": [
            {
                "source": "c_doc",
                "target": "k_code",
                "relation": "implemented_by",
                "confidence": "EXTRACTED",
                "source_file": "c.md",
            },
        ],
    }
    G = build_from_json(extraction)
    assert G.number_of_edges() == 1
    _, _, data = next(iter(G.edges(data=True)))
    assert data.get("relation") == "implements"
    assert data["_src"] == "k_code"
    assert data["_tgt"] == "c_doc"


def test_duplicate_implements_merges_source_files():
    extraction = {
        "nodes": [
            {"id": "c_doc", "label": "Concept", "file_type": "document", "source_file": "c.md"},
            {"id": "k_code", "label": "Klass", "file_type": "code", "source_file": "k.py"},
        ],
        "edges": [
            {
                "source": "k_code",
                "target": "c_doc",
                "relation": "implements",
                "confidence": "EXTRACTED",
                "source_file": "k.py",
            },
            {
                "source": "k_code",
                "target": "c_doc",
                "relation": "implements",
                "confidence": "INFERRED",
                "confidence_score": 0.5,
                "source_file": "other.py",
            },
        ],
    }
    G = build_from_json(extraction)
    assert G.number_of_edges() == 1
    _, _, data = next(iter(G.edges(data=True)))
    assert data["confidence"] == "EXTRACTED"
    sf = data.get("source_file", "")
    assert "k.py" in sf and "other.py" in sf


def test_graph_json_round_trip_implements():
    extraction = {
        "nodes": [
            {"id": "c_doc", "label": "Concept", "file_type": "rationale", "source_file": "c.md"},
            {"id": "k_code", "label": "Klass", "file_type": "code", "source_file": "k.py"},
        ],
        "edges": [
            {
                "source": "k_code",
                "target": "c_doc",
                "relation": "implements",
                "confidence": "INFERRED",
                "confidence_score": 0.88,
                "source_file": "k.py",
            },
        ],
    }
    G = build_from_json(extraction)
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.json"
        to_json(G, communities, str(out))
        data = json.loads(out.read_text())
    links = data.get("links", [])
    assert len(links) == 1
    assert links[0].get("relation") == "implements"


def test_unknown_edge_relation_warns_stderr(capsys):
    extraction = {
        "nodes": [
            {"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "B", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [
            {
                "source": "n1",
                "target": "n2",
                "relation": "totally_unknown_relation_xyz",
                "confidence": "EXTRACTED",
                "source_file": "a.py",
            },
        ],
    }
    errs = validate_extraction(extraction)
    assert errs == []
    err = capsys.readouterr().err
    assert "[graphify]" in err
    assert "totally_unknown_relation_xyz" in err
    assert "docs/RELATIONS.md" in err
