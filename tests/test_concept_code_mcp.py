"""MCP concept_code_hops helper tests (Phase 47 CCODE-04)."""

import json

from graphify.build import build_from_json
from graphify.serve import QUERY_GRAPH_META_SENTINEL, _run_concept_code_hops


def test_concept_code_hops_golden_path():
    extraction = {
        "nodes": [
            {"id": "c_doc", "label": "MyConcept", "file_type": "document", "source_file": "c.md"},
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
        ],
    }
    G = build_from_json(extraction)
    body = _run_concept_code_hops(
        G,
        {},
        {"entity": "Klass", "max_hops": 3, "direction": "both"},
    )
    text_part, sep, meta_part = body.partition(QUERY_GRAPH_META_SENTINEL)
    assert sep
    meta = json.loads(meta_part)
    assert meta["status"] == "ok"
    assert "c_doc" in meta["reachable_node_ids"]
    assert meta["depth_by_id"]["c_doc"] == 1
    assert "MyConcept" in text_part or "c_doc" in text_part
