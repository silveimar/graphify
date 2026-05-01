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


import json
from pathlib import Path

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "concept_code" / "round_trip.json"


def _load_fixture():
    return json.loads(_FIXTURE_PATH.read_text())


def test_round_trip_list_equality_across_reruns():
    """D-53.11: identical edges in identical order across two builds of the same input.

    Also asserts (W2) that NetworkX iteration order matches the canonical
    (source, target, relation) ascending sort produced by edges.sort in
    _normalize_concept_code_edges — i.e., NetworkX preserves insertion order
    through G.add_edge for undirected graphs.
    """
    from graphify.build import build_from_json
    f1 = _load_fixture()
    f2 = _load_fixture()
    g1 = build_from_json(f1)
    g2 = build_from_json(f2)
    e1 = list(g1.edges(data=True))
    e2 = list(g2.edges(data=True))
    assert e1 == e2, f"Round-trip drift detected:\n  g1={e1}\n  g2={e2}"
    # W2: verify iteration order matches canonical sort. Use the original orient-aware
    # endpoints (_src/_tgt fall back to s/t) so the assertion holds regardless of how
    # NetworkX names the undirected edge tuple.
    keys = [(d.get("_src", s), d.get("_tgt", t), d.get("relation", "")) for s, t, d in e1]
    assert keys == sorted(keys), (
        f"NetworkX iteration order does not match canonical (source,target,relation) sort:\n{keys}"
    )


def test_mergeable_duplicates_canonical_source_files():
    """D-53.05: source_files lex-sorted+deduped+joined; max confidence_score; highest tier wins."""
    from graphify.build import build_from_json
    g = build_from_json(_load_fixture())
    # Edges 0+1 of fixture share (k_klass, c_concept, implements). Base is the EXTRACTED edge with
    # source_file="other.py"; the INFERRED duplicate carries source_file="k.py". On current main
    # _merge_edge_fields concatenates as "other.py; k.py" (NOT lex-sorted) — so this single duplicate
    # pair alone forces RED. Edge 6 is the AMBIGUOUS reverse which collapses into the same canonical
    # pair via opposite-direction collapse.
    impl = [(s, t, d) for s, t, d in g.edges(data=True) if d.get("relation") == "implements"]
    assert len(impl) == 1, f"Expected 1 implements edge after merge+collapse, got {len(impl)}: {impl}"
    _, _, data = impl[0]
    sf = data.get("source_file", "")
    parts = [p.strip() for p in sf.split(";")]
    assert parts == sorted(parts), f"source_file parts not lex-sorted: {parts}"
    assert "k.py" in parts and "other.py" in parts, f"Expected k.py & other.py in {parts}"
    assert data.get("confidence") == "EXTRACTED", f"Expected highest tier EXTRACTED, got {data.get('confidence')}"


def test_mergeable_duplicates_max_confidence_score():
    """D-53.05: confidence_score = max() across merged duplicates."""
    from graphify.build import build_from_json
    nodes = [
        {"id": "k_a", "label": "A", "file_type": "code",      "source_file": "a.py"},
        {"id": "c_b", "label": "B", "file_type": "rationale", "source_file": "d.md"},
    ]
    edges = [
        {"source": "k_a", "target": "c_b", "relation": "realizes",
         "confidence": "INFERRED", "confidence_score": 0.4, "source_file": "a.py"},
        {"source": "k_a", "target": "c_b", "relation": "realizes",
         "confidence": "INFERRED", "confidence_score": 0.7, "source_file": "b.py"},
    ]
    g = build_from_json({"nodes": nodes, "edges": edges})
    realizes = [d for _, _, d in g.edges(data=True) if d.get("relation") == "realizes"]
    assert len(realizes) == 1, f"Expected 1 merged realizes edge, got {len(realizes)}"
    assert realizes[0].get("confidence_score") == 0.7, (
        f"Expected max() == 0.7, got {realizes[0].get('confidence_score')}"
    )


def test_canonical_sort_across_all_relations():
    """D-53.06: final edge ordering sorted by (source, target, relation) ascending across ALL edges."""
    from graphify.build import build_from_json
    g = build_from_json(_load_fixture())
    keys = [(d.get("_src", s), d.get("_tgt", t), d.get("relation", "")) for s, t, d in g.edges(data=True)]
    assert keys == sorted(keys), f"Edges not in canonical (source,target,relation) order:\n{keys}"


def test_direction_normalize_realizes_reverse():
    """Fixture edge `c_concept2 → k_klass realizes` must flip to k_klass → c_concept2 (code → concept)."""
    from graphify.build import build_from_json
    g = build_from_json(_load_fixture())
    realizes = [d for _, _, d in g.edges(data=True) if d.get("relation") == "realizes"]
    assert len(realizes) == 1, f"Expected 1 realizes edge, got {len(realizes)}"
    d = realizes[0]
    assert d.get("_src") == "k_klass" and d.get("_tgt") == "c_concept2", (
        f"Expected k_klass → c_concept2, got _src={d.get('_src')} _tgt={d.get('_tgt')}"
    )


def test_direction_normalize_all_concept_code_relations():
    """All 4 new relations + implements orient code → concept when one endpoint is code."""
    from graphify.build import build_from_json
    nodes = [
        {"id": "k_x", "label": "X", "file_type": "code",      "source_file": "x.py"},
        {"id": "c_y", "label": "Y", "file_type": "rationale", "source_file": "d.md"},
    ]
    for rel, conf, extra in [
        ("realizes",     "INFERRED",  {"confidence_score": 0.5}),
        ("instantiates", "INFERRED",  {"confidence_score": 0.5}),
        ("tests",        "INFERRED",  {"confidence_score": 0.5}),
        ("implements",   "EXTRACTED", {}),
    ]:
        edge = {"source": "c_y", "target": "k_x", "relation": rel,
                "confidence": conf, "source_file": "x.py", **extra}
        g = build_from_json({"nodes": nodes, "edges": [edge]})
        out = [(d.get("_src"), d.get("_tgt")) for _, _, d in g.edges(data=True)]
        assert out == [("k_x", "c_y")], f"{rel} did not orient code→concept; got {out}"


def test_documents_relation_no_orient_when_neither_endpoint_code():
    """`documents` runs through orient() but is a no-op when neither endpoint is code."""
    from graphify.build import build_from_json
    nodes = [
        {"id": "d_doc",  "label": "Doc",     "file_type": "document",  "source_file": "r.md"},
        {"id": "c_conc", "label": "Concept", "file_type": "rationale", "source_file": "d.md"},
    ]
    edges = [{"source": "d_doc", "target": "c_conc", "relation": "documents",
              "confidence": "INFERRED", "confidence_score": 0.5, "source_file": "r.md"}]
    g = build_from_json({"nodes": nodes, "edges": edges})
    out = [(d.get("_src"), d.get("_tgt")) for _, _, d in g.edges(data=True)]
    assert out == [("d_doc", "c_conc")], f"documents direction altered unexpectedly: {out}"
