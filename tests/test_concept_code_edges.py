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


def _minimal_nodes_for(rel_test_pairs):
    """Build a minimal node list covering all (source, target) ids referenced in edges.

    Test-only id-prefix contract (W3): node ids in these tests follow a strict prefix
    convention so file_type can be inferred without spelling it out per edge:
      - "c_..." → file_type="rationale" (concept node)
      - "d_..." → file_type="document"
      - anything else (typically "k_..." for code, "t_..." for test code)
        → file_type="code"
    Tests that need a different file_type for a given id MUST construct the node list
    explicitly rather than going through this helper.
    """
    ids = set()
    for e in rel_test_pairs:
        ids.add(e["source"]); ids.add(e["target"])
    out = []
    for nid in sorted(ids):
        ftype = "rationale" if nid.startswith("c_") else ("document" if nid.startswith("d_") else "code")
        out.append({"id": nid, "label": nid, "file_type": ftype, "source_file": f"{nid}.src"})
    return out


def test_new_relations_validate_clean_with_inferred_score():
    from graphify.validate import validate_extraction
    for rel in ("documents", "tests", "realizes", "instantiates"):
        edges = [{"source": "k_a", "target": "c_b", "relation": rel,
                  "confidence": "INFERRED", "confidence_score": 0.5, "source_file": "a.py"}]
        data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
        errors = validate_extraction(data)
        assert errors == [], f"{rel} INFERRED+score should validate clean, got: {errors}"


def test_extracted_new_relation_without_evidence_rejected():
    from graphify.validate import validate_extraction
    edges = [{"source": "k_a", "target": "c_b", "relation": "tests",
              "confidence": "EXTRACTED", "source_file": "a.py"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert any("evidence" in e and "tests" in e for e in errors), f"Expected evidence-required error, got: {errors}"


def test_extracted_new_relation_unknown_evidence_rejected():
    from graphify.validate import validate_extraction
    edges = [{"source": "k_a", "target": "c_b", "relation": "realizes",
              "confidence": "EXTRACTED", "evidence": "bogus", "source_file": "a.py"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert any("unknown evidence" in e or "bogus" in e for e in errors), f"Expected unknown-evidence error, got: {errors}"


def test_extracted_new_relation_with_valid_evidence_accepted():
    from graphify.validate import validate_extraction
    edges = [{"source": "k_a", "target": "c_b", "relation": "instantiates",
              "confidence": "EXTRACTED", "evidence": "inheritance", "source_file": "a.py"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert errors == [], f"Expected clean validation, got: {errors}"


def test_ambiguous_new_relation_no_evidence_accepted():
    from graphify.validate import validate_extraction
    edges = [{"source": "d_a", "target": "c_b", "relation": "documents",
              "confidence": "AMBIGUOUS", "source_file": "a.md"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert errors == [], f"AMBIGUOUS should not require evidence, got: {errors}"


def test_inferred_new_relation_missing_score_rejected():
    from graphify.validate import validate_extraction
    edges = [{"source": "k_a", "target": "c_b", "relation": "tests",
              "confidence": "INFERRED", "source_file": "a.py"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert any("confidence_score" in e for e in errors), f"Expected score-required error, got: {errors}"


def test_implements_unchanged_extracted_no_evidence_accepted():
    """D-53.10: `implements` confidence rules unchanged from Phase 46."""
    from graphify.validate import validate_extraction
    edges = [{"source": "k_a", "target": "c_b", "relation": "implements",
              "confidence": "EXTRACTED", "source_file": "a.py"}]
    data = {"nodes": _minimal_nodes_for(edges), "edges": edges}
    errors = validate_extraction(data)
    assert errors == [], f"implements EXTRACTED should validate without evidence, got: {errors}"
