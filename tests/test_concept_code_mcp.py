"""MCP concept_code_hops helper tests (Phase 47 CCODE-04 + Phase 54 CGRAPH-03)."""

from __future__ import annotations

import json
from pathlib import Path

from graphify.build import build_from_json
from graphify.serve import QUERY_GRAPH_META_SENTINEL, _run_concept_code_hops

_FIXTURE = Path(__file__).parent / "fixtures" / "concept_code" / "round_trip.json"


def _load_round_trip_graph():
    """Phase 54: shared loader for the Phase 53 round_trip fixture."""
    extraction = json.loads(_FIXTURE.read_text())
    return build_from_json(extraction)


def _parse_meta(body: str) -> tuple[str, dict]:
    text_part, sep, meta_part = body.partition(QUERY_GRAPH_META_SENTINEL)
    assert sep, "expected QUERY_GRAPH_META_SENTINEL in helper return"
    return text_part, json.loads(meta_part)


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


# ---------------------------------------------------------------------------
# Phase 54 — RED tests for `relations` widening + payload shim (CGRAPH-03)
# ---------------------------------------------------------------------------


def test_concept_code_hops_default_relations():
    """D-54.01 / D-54.03: omitting `relations` defaults to ['implements']
    AND payload contains both new keys (`relations`, `traversal_steps`,
    `steps_by_relation`) AND the backward-compat `implements_traversal_steps`
    shim is present (because the requested set == {'implements'})."""
    G = _load_round_trip_graph()
    # D-54.01: arg key is `entity` (resolves to k_klass via label "Klass")
    body = _run_concept_code_hops(
        G,
        {},
        {"entity": "Klass", "max_hops": 3, "direction": "both"},
    )
    _, meta = _parse_meta(body)
    # D-54.01: default relations echoed
    assert meta.get("relations") == ["implements"], meta
    # D-54.03: new top-level traversal counter
    assert "traversal_steps" in meta, meta
    assert isinstance(meta["traversal_steps"], int)
    # D-54.03: per-relation breakdown is present and contains exactly the
    # requested relation when defaulting.
    assert meta.get("steps_by_relation") == {
        "implements": meta["traversal_steps"]
    }, meta
    # D-54.03: shim — implements_traversal_steps preserved for backward compat
    assert meta.get("implements_traversal_steps") == meta["traversal_steps"], meta


def test_concept_code_hops_unknown_relation_errors():
    """D-54.02: unknown values in `relations` produce a structured error
    envelope mentioning the offending value."""
    G = _load_round_trip_graph()
    body = _run_concept_code_hops(
        G,
        {},
        {"entity": "Klass", "relations": ["bogus"]},
    )
    _, meta = _parse_meta(body)
    # D-54.02: error envelope (status == "error") with diagnostic text
    assert meta.get("status") == "error", meta
    err_blob = json.dumps(meta)
    assert "bogus" in err_blob, err_blob
    # Allowed values surfaced for actionability
    for allowed in ("implements", "documents", "tests", "realizes", "instantiates"):
        assert allowed in err_blob, f"missing {allowed} in error: {err_blob}"


def test_concept_code_hops_empty_relations_errors():
    """D-54.02: empty list is rejected — caller should omit param for
    implements-only behavior, not pass `[]`."""
    G = _load_round_trip_graph()
    body = _run_concept_code_hops(
        G,
        {},
        {"entity": "Klass", "relations": []},
    )
    _, meta = _parse_meta(body)
    # D-54.02
    assert meta.get("status") == "error", meta
    err_blob = json.dumps(meta).lower()
    assert "must not be empty" in err_blob, err_blob


def test_concept_code_hops_multi_relation_traversal():
    """D-54.01 / D-54.03: requesting multiple relations widens the BFS
    AND turns the legacy `implements_traversal_steps` shim OFF (set != {implements})."""
    G = _load_round_trip_graph()
    # Start at the AuthService concept (c_concept) — both `documents` and
    # `tests` edges land there in round_trip.json.
    body = _run_concept_code_hops(
        G,
        {},
        {
            "entity": "AuthService",
            "relations": ["documents", "tests"],
            "max_hops": 2,
            "direction": "both",
        },
    )
    _, meta = _parse_meta(body)
    # D-54.01
    assert meta.get("status") == "ok", meta
    assert set(meta.get("relations", [])) == {"documents", "tests"}, meta
    # D-54.03: per-relation breakdown — keys present even if some counts are 0
    sbr = meta.get("steps_by_relation", {})
    assert set(sbr.keys()) == {"documents", "tests"}, sbr
    assert sbr["documents"] >= 1, sbr
    assert sbr["tests"] >= 1, sbr
    # D-54.03: shim NOT active when the requested set is not exactly {implements}
    assert "implements_traversal_steps" not in meta, meta


def test_concept_code_hops_payload_steps_by_relation():
    """D-54.03: `traversal_steps == sum(steps_by_relation.values())` and
    when all 5 relations are requested the breakdown carries all 5 keys."""
    G = _load_round_trip_graph()
    body = _run_concept_code_hops(
        G,
        {},
        {
            "entity": "AuthService",
            "relations": [
                "implements", "documents", "tests", "realizes", "instantiates",
            ],
            "max_hops": 3,
            "direction": "both",
        },
    )
    _, meta = _parse_meta(body)
    # D-54.03
    assert meta.get("status") == "ok", meta
    sbr = meta.get("steps_by_relation", {})
    assert set(sbr.keys()) == {
        "implements", "documents", "tests", "realizes", "instantiates",
    }, sbr
    assert meta["traversal_steps"] == sum(sbr.values()), (meta["traversal_steps"], sbr)


def test_concept_code_hops_backward_compat_implements_steps_key():
    """D-54.03: explicit `relations=["implements"]` (not omitted) MUST still
    activate the shim — the contract is set-equality, not None-vs-list."""
    G = _load_round_trip_graph()
    body = _run_concept_code_hops(
        G,
        {},
        {
            "entity": "Klass",
            "relations": ["implements"],
            "max_hops": 3,
            "direction": "both",
        },
    )
    _, meta = _parse_meta(body)
    # D-54.03: shim still active when explicit single-element list passed
    assert "implements_traversal_steps" in meta, meta
    assert meta["implements_traversal_steps"] == meta["traversal_steps"], meta
    assert meta["steps_by_relation"] == {"implements": meta["traversal_steps"]}, meta


# ---------------------------------------------------------------------------
# Drift-protection (v1.11 milestone audit recommendation #3)
# ---------------------------------------------------------------------------


def test_allowed_concept_code_relations_matches_validate_vocabulary():
    """Catch silent drift between Phase 53 schema vocabulary and Phase 54 MCP filter.

    `NEW_CONCEPT_CODE_RELATIONS` (graphify/validate.py) and
    `_ALLOWED_CONCEPT_CODE_RELATIONS` (graphify/serve.py) must stay in sync:
    the MCP set is the schema set plus the pre-existing `implements` relation
    (which lives in `KNOWN_EDGE_RELATIONS`, not in the v1.11 additions).

    Adding a new concept↔code relation to `validate.py` without also adding it
    to `serve.py` would silently exclude it from MCP `concept_code_hops` /
    `entity_trace` results — caught here before that drift can ship.
    """
    from graphify.serve import _ALLOWED_CONCEPT_CODE_RELATIONS
    from graphify.validate import NEW_CONCEPT_CODE_RELATIONS

    expected = NEW_CONCEPT_CODE_RELATIONS | {"implements"}
    assert _ALLOWED_CONCEPT_CODE_RELATIONS == expected, (
        f"MCP filter and schema vocabulary diverged.\n"
        f"  serve._ALLOWED_CONCEPT_CODE_RELATIONS = {sorted(_ALLOWED_CONCEPT_CODE_RELATIONS)}\n"
        f"  validate.NEW_CONCEPT_CODE_RELATIONS | {{'implements'}} = {sorted(expected)}\n"
        f"Add the new relation to BOTH constants, or document the asymmetry."
    )
