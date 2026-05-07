# validate extraction JSON against the graphify schema before graph assembly
# Relation vocabulary: docs/RELATIONS.md — KNOWN_EDGE_RELATIONS / KNOWN_HYPEREDGE_RELATIONS below.
from __future__ import annotations

import sys

VALID_FILE_TYPES = {"code", "document", "paper", "image", "rationale"}
VALID_CONFIDENCES = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}
REQUIRED_EDGE_FIELDS = {"source", "target", "relation", "confidence", "source_file"}

# Known relation strings emitted by extractors, analyze/export helpers, MCP, and tests.
# Unknown values warn once per validation pass (stderr) but do not fail schema validation.
KNOWN_EDGE_RELATIONS: frozenset[str] = frozenset({
    "implements",
    "implemented_by",
    "documents",       # Phase 53: doc/code artifact → concept (D-53.01)
    "tests",           # Phase 53: test artifact → concept (D-53.01)
    "realizes",        # Phase 53: interface/abstract → concept (D-53.01)
    "instantiates",    # Phase 53: concrete subtype → concept (D-53.01)
    "calls",
    "contains",
    "method",
    "inherits",
    "defines",
    "case_of",
    "imports",
    "imports_from",
    "includes",
    "uses_component",
    "binds_method",
    "uses",
    "rationale_for",
    "references",
    "cites",
    "conceptually_related_to",
    "shares_data_with",
    "semantically_similar_to",
    "derived_shortcut",
    "related",
    "related_to",
    # Phase 72 (REAS): reasoning relations
    "supports",
    "contradicts",
    "supersedes",
    "evolved_into",
    "depends_on",
})

# Hyperedge relation vocabulary (separate from edge relations). Kept permissive for skill payloads.
KNOWN_HYPEREDGE_RELATIONS: frozenset[str] = frozenset({
    "participate_in",
    "implement",
    "implements",
    "form",
})

# Phase 53 (D-53.07-09): the four new concept↔code relations carry stricter rules
# than the existing `implements`. EXTRACTED requires `evidence`; INFERRED requires
# `confidence_score ∈ [0.0, 1.0]`; AMBIGUOUS is permitted without either.
NEW_CONCEPT_CODE_RELATIONS: frozenset[str] = frozenset({
    "documents",
    "tests",
    "realizes",
    "instantiates",
})

# Phase 72 (REAS): REASONING_RELATIONS encode claims about ideas/documents
# (not code). Both endpoints must be non-`code` file_type (D-72.05). INFERRED
# edges in REASONING_RELATIONS require `confidence_score ∈ [0.0, 1.0]` per
# CCONF v1.13 (D-72.03/06). See docs/RELATIONS.md for orientation rules.
REASONING_RELATIONS: frozenset[str] = frozenset({
    "supports",
    "contradicts",
    "supersedes",
    "evolved_into",
    "depends_on",
})

# Allowed values for the conditional `evidence` field. Additive — extend in a
# follow-up phase if extractors emit new evidence kinds. (Per RESEARCH §"evidence rule".)
KNOWN_EVIDENCE_VALUES: frozenset[str] = frozenset({
    "annotation",
    "jsdoc",
    "docstring",
    "test_docstring",
    "inheritance",
})


def warn_unknown_relations(data: dict) -> None:
    """Emit one stderr line per distinct unknown edge or hyperedge relation (non-blocking)."""
    warned: set[str] = set()
    edge_list = data.get("edges")
    if edge_list is None and "links" in data:
        edge_list = data.get("links")
    if isinstance(edge_list, list):
        for edge in edge_list:
            if not isinstance(edge, dict):
                continue
            rel = edge.get("relation")
            if not isinstance(rel, str) or not rel:
                continue
            if rel in KNOWN_EDGE_RELATIONS:
                continue
            if rel not in warned:
                warned.add(rel)
                print(
                    f"[graphify] unknown edge relation {rel!r} — document in docs/RELATIONS.md",
                    file=sys.stderr,
                )

    hyperedges = data.get("hyperedges")
    if isinstance(hyperedges, list):
        for h in hyperedges:
            if not isinstance(h, dict):
                continue
            rel = h.get("relation")
            if not isinstance(rel, str) or not rel:
                continue
            if rel in KNOWN_HYPEREDGE_RELATIONS:
                continue
            key = f"hyperedge:{rel}"
            if key not in warned:
                warned.add(key)
                print(
                    f"[graphify] unknown hyperedge relation {rel!r} — document in docs/RELATIONS.md",
                    file=sys.stderr,
                )


def validate_extraction(data: dict) -> list[str]:
    """
    Validate an extraction JSON dict against the graphify schema.
    Returns a list of error strings - empty list means valid.
    """
    if not isinstance(data, dict):
        return ["Extraction must be a JSON object"]

    errors: list[str] = []

    # Nodes
    if "nodes" not in data:
        errors.append("Missing required key 'nodes'")
    elif not isinstance(data["nodes"], list):
        errors.append("'nodes' must be a list")
    else:
        for i, node in enumerate(data["nodes"]):
            if not isinstance(node, dict):
                errors.append(f"Node {i} must be an object")
                continue
            for field in REQUIRED_NODE_FIELDS:
                if field not in node:
                    errors.append(f"Node {i} (id={node.get('id', '?')!r}) missing required field '{field}'")
            if "file_type" in node and node["file_type"] not in VALID_FILE_TYPES:
                errors.append(
                    f"Node {i} (id={node.get('id', '?')!r}) has invalid file_type "
                    f"'{node['file_type']}' - must be one of {sorted(VALID_FILE_TYPES)}"
                )
            # D-12: source_file may be str OR list[str] after dedup
            if "source_file" in node:
                sf = node["source_file"]
                if not isinstance(sf, (str, list)):
                    errors.append(
                        f"Node {i} (id={node.get('id', '?')!r}) 'source_file' must be "
                        f"str or list[str], got {type(sf).__name__}"
                    )
                elif isinstance(sf, list) and not all(isinstance(s, str) for s in sf):
                    errors.append(
                        f"Node {i} (id={node.get('id', '?')!r}) source_file list "
                        f"must contain only strings"
                    )
            # D-11: merged_from is optional; when present must be list[str]
            if "merged_from" in node:
                mf = node["merged_from"]
                if not isinstance(mf, list) or not all(isinstance(m, str) for m in mf):
                    errors.append(
                        f"Node {i} (id={node.get('id', '?')!r}) 'merged_from' must be list[str]"
                    )

    # Edges - accept "links" (NetworkX <= 3.1) as fallback for "edges"
    edge_list = data.get("edges") if "edges" in data else data.get("links")
    if edge_list is None:
        errors.append("Missing required key 'edges'")
    elif not isinstance(edge_list, list):
        errors.append("'edges' must be a list")
    else:
        node_types: dict[str, str] = {
            n["id"]: str(n.get("file_type", ""))
            for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n
        }
        node_ids = set(node_types)
        for i, edge in enumerate(edge_list):
            if not isinstance(edge, dict):
                errors.append(f"Edge {i} must be an object")
                continue
            for field in REQUIRED_EDGE_FIELDS:
                if field not in edge:
                    errors.append(f"Edge {i} missing required field '{field}'")
            if "confidence" in edge and edge["confidence"] not in VALID_CONFIDENCES:
                errors.append(
                    f"Edge {i} has invalid confidence '{edge['confidence']}' "
                    f"- must be one of {sorted(VALID_CONFIDENCES)}"
                )
            # Phase 53 (D-53.07-09): evidence/score rule for the four new concept↔code relations.
            # `implements` is intentionally excluded (D-53.10 backward compat).
            rel = edge.get("relation")
            conf = edge.get("confidence")
            if rel in NEW_CONCEPT_CODE_RELATIONS:
                if conf == "EXTRACTED":
                    ev = edge.get("evidence")
                    if not isinstance(ev, str) or not ev:
                        errors.append(
                            f"Edge {i} relation={rel!r} confidence=EXTRACTED requires "
                            f"non-empty 'evidence' field"
                        )
                    elif ev not in KNOWN_EVIDENCE_VALUES:
                        errors.append(
                            f"Edge {i} relation={rel!r} has unknown evidence {ev!r} - "
                            f"must be one of {sorted(KNOWN_EVIDENCE_VALUES)}"
                        )
                elif conf == "INFERRED":
                    raw = edge.get("confidence_score")
                    score: float | None
                    try:
                        score = float(raw) if raw is not None else None
                    except (TypeError, ValueError):
                        score = None
                    if score is None or not (0.0 <= score <= 1.0):
                        errors.append(
                            f"Edge {i} relation={rel!r} confidence=INFERRED requires "
                            f"'confidence_score' in [0.0, 1.0]"
                        )
                # AMBIGUOUS: permitted without evidence/score (D-53.09).
            # Phase 72 (REAS): reasoning relations require non-code endpoints (D-72.05)
            # and INFERRED requires confidence_score ∈ [0.0, 1.0] (D-72.03/06).
            if rel in REASONING_RELATIONS:
                src_t = node_types.get(edge.get("source", ""), "")
                tgt_t = node_types.get(edge.get("target", ""), "")
                if src_t == "code" or tgt_t == "code":
                    errors.append(
                        f"Edge {i} relation={rel!r} requires non-code endpoints; "
                        f"got source.file_type={src_t!r}, target.file_type={tgt_t!r}"
                    )
                if conf == "INFERRED":
                    raw = edge.get("confidence_score")
                    score_r: float | None
                    try:
                        score_r = float(raw) if raw is not None else None
                    except (TypeError, ValueError):
                        score_r = None
                    if score_r is None or not (0.0 <= score_r <= 1.0):
                        errors.append(
                            f"Edge {i} relation={rel!r} confidence=INFERRED requires "
                            f"'confidence_score' in [0.0, 1.0]"
                        )
            if "source" in edge and node_ids and edge["source"] not in node_ids:
                errors.append(f"Edge {i} source '{edge['source']}' does not match any node id")
            if "target" in edge and node_ids and edge["target"] not in node_ids:
                errors.append(f"Edge {i} target '{edge['target']}' does not match any node id")

    warn_unknown_relations(data)

    return errors


def assert_valid(data: dict) -> None:
    """Raise ValueError with all errors if extraction is invalid."""
    errors = validate_extraction(data)
    if errors:
        msg = f"Extraction JSON has {len(errors)} error(s):\n" + "\n".join(f"  • {e}" for e in errors)
        raise ValueError(msg)


# ---- Phase 65 (CCONF-05): read/write split for schema_version ----------------
#
# Pre-1.13 graphs (v1.10–v1.12) were written without a `schema_version` key.
# To protect those user graphs from breaking on load while still forcing every
# new write to carry an explicit version stamp, validation is split into two
# entry points (per D-65.08, Open Question Q5):
#
#   * validate_extraction_for_read  — schema_version absent is OK (legacy)
#   * validate_extraction_for_write — schema_version REQUIRED
#
# `validate_extraction` itself is unchanged and remains the read-mode alias for
# all existing callers (backward compat).


def validate_extraction_for_read(data: dict) -> list[str]:
    """Read-mode: schema_version absent is OK (pre-1.13 legacy graphs)."""
    return validate_extraction(data)


def validate_extraction_for_write(data: dict) -> list[str]:
    """Write-mode: schema_version REQUIRED (every new graph must be stamped)."""
    errors = validate_extraction(data)
    if not isinstance(data, dict):
        # validate_extraction already reported the shape error; nothing to add.
        return errors
    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv:
        errors.append("Missing required key 'schema_version' (write-mode)")

    # Phase 71 (TEMP): write-mode requires per-edge temporal fields. NOT added to
    # REQUIRED_EDGE_FIELDS — read-mode must still accept legacy v1.13 graphs that
    # predate the temporal schema (T-71-05 mitigation).
    edge_list = data.get("edges") if "edges" in data else data.get("links")
    if isinstance(edge_list, list):
        for i, edge in enumerate(edge_list):
            if not isinstance(edge, dict):
                continue
            if "valid_from" not in edge:
                errors.append(f"Edge {i} missing required field 'valid_from' (write-mode)")
            dw = edge.get("decay_weight")
            if not isinstance(dw, (int, float)) or isinstance(dw, bool) or not (0.0 <= float(dw) <= 1.0):
                errors.append(
                    f"Edge {i} 'decay_weight' must be float in [0.0, 1.0] (write-mode)"
                )
            # valid_until: None OR ISO string — both accepted; absent is also OK
            # for write-mode (None is the canonical "still valid" value).
    return errors
