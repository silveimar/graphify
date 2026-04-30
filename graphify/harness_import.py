"""Harness memory import (Phase 40, PORT-03/05, SEC-01).

Parses on-disk harness artifacts (JSON interchange v1 or Claude markdown) into
a :func:`graphify.validate.validate_extraction`-clean dict. This module does
**not** read or rewrite ``elicitation.json`` — merge ordering stays a Phase
39 / build concern.

**Max file size:** ``security.MAX_HARNESS_IMPORT_BYTES`` (10 MiB, aligned with
``safe_fetch_text``).

**Formats:** ``json`` (interchange v1), ``claude`` (exported SOUL-style
markdown; god-node lines are extracted), ``auto`` (sniff by extension and
content).

**Round-trip (PORT-04 / 40-RESEARCH):** Interchange JSON preserves
``id``/``label``/``relation`` for graph nodes and edges. Markdown import is
intentionally summarizing; do not expect byte-identical replay from markdown.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from graphify.harness_interchange import INTERCHANGE_SCHEMA_ID
from graphify.security import (
    MAX_HARNESS_IMPORT_BYTES,
    guard_harness_injection_patterns,
    sanitize_harness_text,
    sanitize_label,
    validate_graph_path,
)
from graphify.validate import validate_extraction

_ID_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _clean_id(s: str) -> str:
    """Strip control chars and cap length without slugifying (preserve edge refs)."""
    t = _ID_CONTROL.sub("", str(s))
    return t[:512] if len(t) > 512 else t


_GOD_LINE = re.compile(
    r"^[-*]\s*\*\*([^*]+)\*\*\s*\(`([^`]+)`\)\s*",
)

_FENCE_START = re.compile(r"(?im)^##\s+God Nodes\b")


def _read_bytes_capped(path: Path, cap: int = MAX_HARNESS_IMPORT_BYTES) -> bytes:
    with path.open("rb") as f:
        data = f.read(cap + 1)
    if len(data) > cap:
        raise ValueError(
            f"harness import: file exceeds max size ({cap} bytes): {path}"
        )
    return data


def _sniff_format(path: Path, text: str) -> str:
    if path.suffix.lower() == ".json":
        return "json"
    t = text.lstrip()
    if t.startswith("{"):
        return "json"
    if path.suffix.lower() in {".md", ".markdown", ".mdx"}:
        return "claude"
    if "Graphify Memory Harness" in text or _FENCE_START.search(text):
        return "claude"
    return "json"


def _sanitize_extraction(
    data: dict[str, Any],
    *,
    path_name: str,
    strict: bool,
) -> dict[str, Any]:
    """Apply label + injection guards; return a new extraction dict."""
    nodes_in = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    edges_in = data.get("edges")
    if edges_in is None and isinstance(data.get("links"), list):
        edges_in = data["links"]
    if not isinstance(edges_in, list):
        edges_in = []

    nodes_out: list[dict[str, Any]] = []
    for n in nodes_in:
        if not isinstance(n, dict):
            continue
        nid_raw = n.get("id")
        if not isinstance(nid_raw, str):
            continue
        nid = _clean_id(nid_raw)
        if not nid:
            continue
        raw_label = str(n.get("label", "") or nid)
        lab_intermediate, _ = guard_harness_injection_patterns(
            raw_label, strict=strict, replacement=" "
        )
        lab = sanitize_label(sanitize_harness_text(lab_intermediate, max_chars=256))
        ft = n.get("file_type", "code")
        if ft not in {"code", "document", "paper", "image", "rationale"}:
            ft = "code"
        sf = n.get("source_file", "")
        if isinstance(sf, list):
            sfl = [sanitize_label(str(x)) for x in sf]
            source_file: str | list[str] = sfl
        else:
            source_file = sanitize_label(str(sf or f"harness:import:{path_name}"))

        node: dict[str, Any] = {
            "id": nid,
            "label": lab,
            "file_type": ft,
            "source_file": source_file,
        }
        if "source_location" in n and isinstance(n.get("source_location"), str):
            node["source_location"] = sanitize_label(n["source_location"][:256])
        nodes_out.append(node)

    edges_out: list[dict[str, Any]] = []
    for e in edges_in:
        if not isinstance(e, dict):
            continue
        s_raw = e.get("source")
        t_raw = e.get("target")
        if not isinstance(s_raw, str) or not isinstance(t_raw, str):
            continue
        s, t = _clean_id(s_raw), _clean_id(t_raw)
        rel_raw = str(e.get("relation", "references"))
        rel_mid, _ = guard_harness_injection_patterns(
            rel_raw, strict=strict, replacement="references"
        )
        rel = sanitize_label(sanitize_harness_text(rel_mid, max_chars=256)) or "references"
        conf = e.get("confidence", "EXTRACTED")
        if conf not in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}:
            conf = "EXTRACTED"
        sf = sanitize_label(str(e.get("source_file", f"harness:import:{path_name}")))
        edge: dict[str, Any] = {
            "source": s,
            "target": t,
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


def _parse_interchange_v1(
    obj: dict[str, Any],
    *,
    path_name: str,
    strict: bool,
) -> dict[str, Any]:
    sid_top = obj.get("interchange_schema_id")
    prov = obj.get("provenance") if isinstance(obj.get("provenance"), dict) else {}
    sid_prov = prov.get("interchange_schema_id")
    if sid_top != INTERCHANGE_SCHEMA_ID and sid_prov != INTERCHANGE_SCHEMA_ID:
        raise ValueError(
            "harness import: expected interchange v1 "
            f"({INTERCHANGE_SCHEMA_ID!r}) in interchange_schema_id or provenance"
        )
    ext = obj.get("extraction")
    if not isinstance(ext, dict):
        raise ValueError("harness import: interchange envelope missing 'extraction' object")
    return _sanitize_extraction(ext, path_name=path_name, strict=strict)


def _parse_claude_markdown(
    text: str,
    *,
    path_name: str,
    strict: bool,
) -> dict[str, Any]:
    body, _ = guard_harness_injection_patterns(
        sanitize_harness_text(text), strict=strict
    )
    nodes: list[dict[str, Any]] = []
    for line in body.splitlines():
        m = _GOD_LINE.match(line.strip())
        if m:
            label, nid = m.group(1).strip(), m.group(2).strip()
            nid_c = _clean_id(nid)
            if not nid_c:
                continue
            nodes.append(
                {
                    "id": nid_c,
                    "label": sanitize_label(label),
                    "file_type": "rationale",
                    "source_file": f"harness:import:{path_name}",
                }
            )
    if not nodes:
        nodes.append(
            {
                "id": "harness_claude_import",
                "label": "Claude harness (imported)",
                "file_type": "document",
                "source_file": f"harness:import:{path_name}",
            }
        )
    ext = {"nodes": nodes, "edges": []}
    return _sanitize_extraction(ext, path_name=path_name, strict=strict)


def import_harness_path(
    path: Path | str,
    *,
    format: str = "auto",
    strict: bool = False,
    artifacts_root: Path | None = None,
) -> dict[str, Any]:
    """Read a harness file from disk and return a validated extraction dict.

    The resolved path must exist and stay inside ``artifacts_root`` (defaults
    to ``graphify-out`` in the current working tree), via
    :func:`graphify.security.validate_graph_path`.
    """
    if format not in {"auto", "json", "claude"}:
        raise ValueError("format must be one of: auto, json, claude")

    base = (
        Path(artifacts_root).resolve()
        if artifacts_root is not None
        else Path("graphify-out").resolve()
    )
    resolved = Path(path).resolve()
    validate_graph_path(resolved, base=base)

    raw = _read_bytes_capped(resolved)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"harness import: file is not valid UTF-8: {resolved}") from exc

    fmt = format
    if fmt == "auto":
        fmt = _sniff_format(resolved, text)
    name = resolved.name

    if fmt == "json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"harness import: invalid JSON: {resolved}") from exc
        if not isinstance(obj, dict):
            raise ValueError("harness import: JSON root must be an object")
        out = _parse_interchange_v1(obj, path_name=name, strict=strict)
    elif fmt == "claude":
        out = _parse_claude_markdown(text, path_name=name, strict=strict)
    else:
        raise ValueError(f"harness import: unsupported format {fmt!r}")

    errs = validate_extraction(out)
    if errs:
        raise ValueError(
            "harness import: validation failed: " + "; ".join(errs[:20])
        )
    return out


def import_harness_bytes(
    data: bytes,
    *,
    format: str,
    path_name: str = "inline",
    strict: bool = False,
) -> dict[str, Any]:
    """Parse harness bytes (tests); skips filesystem path policy."""
    if len(data) > MAX_HARNESS_IMPORT_BYTES:
        raise ValueError("harness import: buffer exceeds max harness import size")
    text = data.decode("utf-8", errors="replace")
    fmt = format
    if fmt == "auto":
        fmt = _sniff_format(Path(path_name), text)
    if fmt == "json":
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("harness import: JSON root must be an object")
        return _parse_interchange_v1(obj, path_name=path_name, strict=strict)
    if fmt == "claude":
        return _parse_claude_markdown(text, path_name=path_name, strict=strict)
    raise ValueError(f"harness import: unsupported format {fmt!r}")
