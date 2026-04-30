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
    "calls",
    "contains",
    "method",
    "inherits",
    "defines",
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
})

# Hyperedge relation vocabulary (separate from edge relations). Kept permissive for skill payloads.
KNOWN_HYPEREDGE_RELATIONS: frozenset[str] = frozenset({
    "participate_in",
    "implement",
    "implements",
    "form",
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
        node_ids = {n["id"] for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n}
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
