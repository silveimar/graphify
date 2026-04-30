"""Canonical JSON interchange for harness memory export (Phase 40, PORT-01/02).

Builds a versioned envelope around a graphify extraction dict derived from the
same ``graph.json`` node-link snapshot used by :func:`graphify.harness_export.export_claude_harness`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from graphify.validate import validate_extraction
from graphify.version import package_version

INTERCHANGE_SCHEMA_ID = "graphify.harness.interchange/v1"
INTERCHANGE_FILENAME = "harness_memory.v1.json"


def _package_version() -> str:
    return package_version()


def _system_clock() -> datetime:
    return datetime.now(timezone.utc)


def graph_data_to_extraction(graph_data: dict[str, Any]) -> dict[str, Any]:
    """Convert a NetworkX node-link dict into an extraction payload.

    Uses the same node/link traversal strategy as ``harness_export._extract_*``.
    """
    from graphify.harness_export import _extract_edges, _extract_nodes

    raw_nodes = _extract_nodes(graph_data)
    raw_edges = _extract_edges(graph_data)

    nodes_out: list[dict[str, Any]] = []
    for n in raw_nodes:
        nid = n.get("id")
        if not isinstance(nid, str):
            continue
        ft = n.get("file_type", "code")
        if ft not in {"code", "document", "paper", "image", "rationale"}:
            ft = "code"
        sf = n.get("source_file", "")
        if isinstance(sf, list):
            pass
        elif isinstance(sf, str):
            pass
        else:
            sf = ""
        nodes_out.append(
            {
                "id": nid,
                "label": str(n.get("label") or nid),
                "file_type": ft,
                "source_file": sf,
            }
        )

    edges_out: list[dict[str, Any]] = []
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if not isinstance(src, str) or not isinstance(tgt, str):
            continue
        rel = str(e.get("relation") or "references")
        conf = e.get("confidence", "EXTRACTED")
        if conf not in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}:
            conf = "EXTRACTED"
        sf = e.get("source_file", "")
        if not isinstance(sf, str):
            sf = ""
        edge: dict[str, Any] = {
            "source": src,
            "target": tgt,
            "relation": rel,
            "confidence": conf,
            "source_file": sf,
        }
        if "weight" in e:
            edge["weight"] = e["weight"]
        if "confidence_score" in e:
            edge["confidence_score"] = e["confidence_score"]
        edges_out.append(edge)

    return {"nodes": nodes_out, "edges": edges_out}


def export_interchange_v1(
    graph_data: dict[str, Any],
    *,
    out_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
    source_run_id: str | None = None,
    graphify_version: str | None = None,
    artifacts_base: Path | None = None,
) -> dict[str, Any]:
    """Build interchange v1 dict and optionally write it atomically.

    Parameters
    ----------
    graph_data:
        Raw node-link JSON (``nodes`` / ``links`` or ``edges``).
    out_path:
        When set, JSON is written with ``.tmp`` + ``os.replace``. Parent path
        is checked with :func:`graphify.security.validate_graph_path` when
        ``artifacts_base`` is provided.
    clock:
        Injectable UTC clock; defaults to wall time.
    source_run_id:
        Optional UUID string recorded under provenance.
    graphify_version:
        Override package version string in provenance.
    artifacts_base:
        Confined root (e.g. resolved ``graphify-out``) for ``validate_graph_path``
        when ``out_path`` is set.

    Returns
    -------
    Full interchange envelope including ``extraction`` — inner extraction always
    passes :func:`graphify.validate.validate_extraction` before write.
    """
    extraction = graph_data_to_extraction(graph_data)
    errs = validate_extraction(extraction)
    if errs:
        raise ValueError(
            "interchange export: extraction failed validation: "
            + "; ".join(errs[:12])
        )

    clk = clock or _system_clock
    dt = clk()
    if not isinstance(dt, datetime):
        dt = _system_clock()
    generated_at = dt.isoformat(timespec="seconds")
    gv = graphify_version if graphify_version is not None else _package_version()

    provenance: dict[str, Any] = {
        "interchange_schema_id": INTERCHANGE_SCHEMA_ID,
        "generated_at": generated_at,
        "graphify_version": gv,
    }
    if source_run_id:
        provenance["source_run_id"] = source_run_id

    envelope: dict[str, Any] = {
        "interchange_schema_id": INTERCHANGE_SCHEMA_ID,
        "provenance": provenance,
        "extraction": extraction,
    }

    if out_path is not None:
        outp = Path(out_path)
        base = (
            artifacts_base.resolve()
            if artifacts_base is not None
            else Path("graphify-out").resolve()
        )
        if not base.exists():
            raise ValueError(
                f"artifacts base does not exist: {base}. Run graphify first."
            )
        try:
            outp.resolve().relative_to(base)
        except ValueError as exc:
            raise ValueError(
                f"interchange output path {outp} escapes allowed base {base}"
            ) from exc
        outp.parent.mkdir(parents=True, exist_ok=True)
        tmp = outp.with_suffix(outp.suffix + ".tmp")
        text = json.dumps(envelope, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, outp)

    return envelope
