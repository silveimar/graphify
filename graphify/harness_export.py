"""Harness memory export (SEED-002, HARNESS-01..06).

Reads snapshot sidecars and emits SOUL/HEARTBEAT/USER markdown files per a
declarative schema (``graphify/harness_schemas/claude.yaml``). Utilities-only
(D-73): no LLM calls, no skill imports, no auto-trigger from pipeline/watch.

Placeholder rendering uses ``string.Template.safe_substitute`` exclusively —
``{{ token }}`` tokens are normalized to ``${token}`` via a single regex
(HARNESS-03). No Jinja2 import anywhere in this module.
"""
from __future__ import annotations

import json
import os
import re
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml  # PyYAML — transitive via mcp / routing / obsidian extras

from graphify.harness_schemas import schema_path
from graphify.security import validate_graph_path

# HARNESS-06 / T-13-04: allow-list for annotation fields when
# ``include_annotations=False`` (the default). Free-text bodies, peer_id,
# and unknown keys are dropped before any rendering touches the output.
ANNOTATION_ALLOW_LIST: frozenset[str] = frozenset(
    {"id", "label", "source_file", "relation", "confidence"}
)

# HARNESS-03: convert ``{{ token }}`` → ``${token}`` before string.Template.
# Single regex — no grammar, no full parser, no Jinja2.
_TOKEN_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Deterministic block emission order (T-13-06 byte-stability).
_BLOCK_ORDER: tuple[str, ...] = ("soul", "heartbeat", "user")


def _normalize_placeholders(text: str) -> str:
    """HARNESS-03 single-regex normalizer — no full parser."""
    return _TOKEN_PATTERN.sub(r"${\1}", text)


# ---------------------------------------------------------------------------
# Sidecar loading (HARNESS-01)
# ---------------------------------------------------------------------------


def _load_sidecars(out_dir: Path) -> dict[str, Any]:
    """Read ``graph.json`` + optional sidecars from ``out_dir``.

    Returns a dict with keys ``graph_data`` (raw node_link dict),
    ``annotations`` (list[dict]), ``agent_edges`` (list[dict]), and
    ``telemetry`` (dict). ``graph.json`` is mandatory — missing file raises
    ``FileNotFoundError`` with a D-03 style stderr. The other three sidecars
    warn to stderr and default to empty structures (partial harness > none).
    """
    graph_path = out_dir / "graph.json"
    if not graph_path.exists():
        print(
            f"error: graph.json not found at {graph_path}",
            file=sys.stderr,
        )
        print(
            "  expected: a node_link JSON produced by 'graphify run .'",
            file=sys.stderr,
        )
        print("  regenerate:", file=sys.stderr)
        print("    graphify run .", file=sys.stderr)
        raise FileNotFoundError(f"graph.json not found: {graph_path}")

    try:
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"graph.json is not valid JSON: {exc}") from exc
    if not isinstance(graph_data, dict):
        raise ValueError("graph.json must be a JSON object (node_link dict)")

    annotations: list[dict[str, Any]] = []
    ann_path = out_dir / "annotations.jsonl"
    if ann_path.exists():
        for idx, line in enumerate(ann_path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                print(
                    f"[graphify] annotations.jsonl line {idx}: skipped (invalid JSON)",
                    file=sys.stderr,
                )
                continue
            if isinstance(rec, dict):
                annotations.append(rec)
    else:
        print(
            "[graphify] annotations.jsonl missing — continuing with empty annotations",
            file=sys.stderr,
        )

    agent_edges: list[dict[str, Any]] = []
    ae_path = out_dir / "agent-edges.json"
    if ae_path.exists():
        try:
            payload = json.loads(ae_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                agent_edges = [e for e in payload if isinstance(e, dict)]
            else:
                print(
                    "[graphify] agent-edges.json must be a JSON array — ignoring",
                    file=sys.stderr,
                )
        except json.JSONDecodeError:
            print(
                "[graphify] agent-edges.json: invalid JSON — ignoring",
                file=sys.stderr,
            )
    else:
        print(
            "[graphify] agent-edges.json missing — continuing with empty agent edges",
            file=sys.stderr,
        )

    telemetry: dict[str, Any] = {}
    tel_path = out_dir / "telemetry.json"
    if tel_path.exists():
        try:
            payload = json.loads(tel_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                telemetry = payload
            else:
                print(
                    "[graphify] telemetry.json must be a JSON object — ignoring",
                    file=sys.stderr,
                )
        except json.JSONDecodeError:
            print(
                "[graphify] telemetry.json: invalid JSON — ignoring",
                file=sys.stderr,
            )
    else:
        print(
            "[graphify] telemetry.json missing — continuing with empty telemetry",
            file=sys.stderr,
        )

    return {
        "graph_data": graph_data,
        "annotations": annotations,
        "agent_edges": agent_edges,
        "telemetry": telemetry,
    }


# ---------------------------------------------------------------------------
# Annotation filter (HARNESS-06 / T-13-04)
# ---------------------------------------------------------------------------


def _filter_annotations_allowlist(
    annotations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop any annotation field outside :data:`ANNOTATION_ALLOW_LIST`.

    This is the default (``include_annotations=False``) path. Free-text
    bodies, ``peer_id`` fields, and any unknown keys are discarded so they
    never surface in SOUL/HEARTBEAT/USER output.
    """
    return [
        {k: v for k, v in a.items() if k in ANNOTATION_ALLOW_LIST}
        for a in annotations
    ]


# ---------------------------------------------------------------------------
# Deterministic collectors (T-13-06)
# ---------------------------------------------------------------------------


def _extract_nodes(graph_data: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graph_data.get("nodes") or []
    return [n for n in nodes if isinstance(n, dict)]


def _extract_edges(graph_data: dict[str, Any]) -> list[dict[str, Any]]:
    # NetworkX node_link uses "links" by default; some exporters use "edges".
    edges = graph_data.get("links")
    if edges is None:
        edges = graph_data.get("edges") or []
    return [e for e in edges if isinstance(e, dict)]


def _degree_map(graph_data: dict[str, Any]) -> dict[str, int]:
    degree: dict[str, int] = {}
    for n in _extract_nodes(graph_data):
        nid = n.get("id")
        if isinstance(nid, str):
            degree.setdefault(nid, 0)
    for e in _extract_edges(graph_data):
        src = e.get("source")
        tgt = e.get("target")
        if isinstance(src, str):
            degree[src] = degree.get(src, 0) + 1
        if isinstance(tgt, str):
            degree[tgt] = degree.get(tgt, 0) + 1
    return degree


def _collect_god_nodes(graph_data: dict[str, Any], limit: int = 10) -> str:
    """Top-N nodes by degree. Sort by (degree DESC, id ASC) for stability."""
    nodes = _extract_nodes(graph_data)
    if not nodes:
        return "(no god nodes — graph has no nodes)"
    degree = _degree_map(graph_data)
    by_id = {n.get("id"): n for n in nodes if isinstance(n.get("id"), str)}
    ranked = sorted(
        by_id.keys(),
        key=lambda nid: (-degree.get(nid, 0), nid),
    )[:limit]
    lines: list[str] = []
    for nid in ranked:
        n = by_id[nid]
        label = n.get("label") or nid
        lines.append(f"- **{label}** (`{nid}`) — degree {degree.get(nid, 0)}")
    return "\n".join(lines) if lines else "(no god nodes)"


def _collect_recent_deltas(
    agent_edges: list[dict[str, Any]], limit: int = 10
) -> str:
    """Most recent N agent edges. Sort by (ts DESC, from ASC, to ASC)."""
    if not agent_edges:
        return "(no recent deltas)"
    sanitized = [
        {
            "from": str(e.get("from", "")),
            "to": str(e.get("to", "")),
            "relation": str(e.get("relation", "")),
            "ts": str(e.get("ts", "")),
        }
        for e in agent_edges
    ]
    ranked = sorted(
        sanitized,
        key=lambda e: (_neg_ts(e["ts"]), e["from"], e["to"]),
    )[:limit]
    lines = [
        f"- `{e['ts']}` · {e['from']} → {e['to']} ({e['relation']})"
        for e in ranked
    ]
    return "\n".join(lines)


def _neg_ts(ts: str) -> str:
    """Return a sort key that inverts lexicographic order of ISO-ish timestamps.

    Sorting ``"\uffff" - char`` per position flips DESC → ASC while remaining a
    stable deterministic string key. Falls back to empty string when ``ts``
    is empty.
    """
    if not ts:
        return ""
    # Simpler + deterministic: tuple of per-char negatives. We return a string
    # by mapping each char to its Unicode complement within a sane range.
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in ts)


def _collect_hot_paths(telemetry: dict[str, Any], limit: int = 5) -> str:
    """Pull ``telemetry['hot_paths']`` if present; else '(none recorded)'.

    Sort by (count DESC, path ASC) when entries carry a ``count``; otherwise
    sort alphabetically by path/value.
    """
    raw = telemetry.get("hot_paths")
    if not raw:
        return "(none recorded)"
    if isinstance(raw, list):
        items: list[tuple[int, str]] = []
        for entry in raw:
            if isinstance(entry, dict):
                path = str(entry.get("path", ""))
                count = entry.get("count", 0)
                try:
                    count = int(count)
                except (TypeError, ValueError):
                    count = 0
                items.append((count, path))
            else:
                items.append((0, str(entry)))
        items.sort(key=lambda x: (-x[0], x[1]))
        items = items[:limit]
        lines = [
            f"- `{path}` (count {count})" if count else f"- `{path}`"
            for count, path in items
        ]
        return "\n".join(lines) if lines else "(none recorded)"
    # Fallback: string / unexpected shape
    return f"- `{raw}`"


def _collect_agent_identity(telemetry: dict[str, Any]) -> str:
    """Single-line identity string derived from telemetry."""
    if not telemetry:
        return "graphify agent · unknown"
    tool_calls = telemetry.get("tool_calls")
    last_run = telemetry.get("last_run_ts", "unknown")
    if tool_calls is None:
        return f"graphify agent · last-run={last_run}"
    return f"graphify agent · tool_calls={tool_calls} · last-run={last_run}"


# ---------------------------------------------------------------------------
# Main export (HARNESS-01..05)
# ---------------------------------------------------------------------------


def export_claude_harness(
    out_dir: Path,
    *,
    target: str = "claude",
    include_annotations: bool = False,
    _clock: Callable[[], datetime] | None = None,
) -> list[Path]:
    """Emit SOUL/HEARTBEAT/USER markdown files under ``out_dir/harness/``.

    Parameters
    ----------
    out_dir:
        The ``graphify-out`` root containing ``graph.json`` and sidecars.
    target:
        Harness target. Only ``"claude"`` is supported at launch.
    include_annotations:
        When ``False`` (default), annotations are filtered through
        :data:`ANNOTATION_ALLOW_LIST`. The ``True`` branch is reserved for
        Plan 04 (HARNESS-07 secret scanner) — this module honors the kwarg
        but does not add a secret scanner here.
    _clock:
        Injectable ``() -> datetime`` seam used to pin ``generated_at`` in
        tests (T-13-06 byte-equality). When ``None`` (default), falls back
        to ``datetime.now(timezone.utc)`` — NOT deterministic across runs.
        Plan 04 (HARNESS-08) wires a user-facing knob on top of this seam.

    Returns
    -------
    list[Path]
        The three written paths in deterministic block order
        (SOUL, HEARTBEAT, USER).

    Raises
    ------
    ValueError
        On path escape (T-13-05) or unsupported ``target``.
    FileNotFoundError
        When ``graph.json`` is missing under ``out_dir``.
    """
    base = Path(out_dir).resolve()
    if not base.exists():
        raise ValueError(
            f"out_dir does not exist: {base}. "
            "Create it or run 'graphify run .' first."
        )

    harness_dir = base / "harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    # T-13-05: confine writes to graphify-out. ``validate_graph_path`` raises
    # ValueError on escape and FileNotFoundError if the resolved path does
    # not exist — the mkdir above guarantees it exists for a valid ``base``.
    validated_dir = validate_graph_path(harness_dir, base=base)
    # Sanity: composed file path must still resolve under the base.
    if not str(validated_dir.resolve()).startswith(str(base)):
        raise ValueError(
            f"harness_dir {validated_dir} escaped base {base}"
        )

    # Load schema first so an unknown target fails before any I/O on sidecars.
    schema_doc = yaml.safe_load(schema_path(target).read_text(encoding="utf-8"))
    if not isinstance(schema_doc, dict) or "blocks" not in schema_doc:
        raise ValueError(
            f"harness schema for target {target!r} is malformed: "
            "expected a top-level 'blocks' key."
        )
    blocks = schema_doc["blocks"]
    if not isinstance(blocks, dict):
        raise ValueError(
            f"harness schema for target {target!r} has non-dict 'blocks'."
        )

    sidecars = _load_sidecars(base)
    annotations = sidecars["annotations"]
    if not include_annotations:
        annotations = _filter_annotations_allowlist(annotations)
    # NOTE: annotations are filtered eagerly so Plan 04's include-path can wire
    # its secret scanner before this call and still respect the allow-list
    # default. The filtered list is not currently rendered into the schema
    # bodies (HARNESS-06 is about what we *never* leak); Plan 04 will add the
    # annotation-aware body blocks behind the flag.

    god_nodes = _collect_god_nodes(sidecars["graph_data"])
    recent_deltas = _collect_recent_deltas(sidecars["agent_edges"])
    hot_paths = _collect_hot_paths(sidecars["telemetry"])
    agent_identity = _collect_agent_identity(sidecars["telemetry"])

    clock = _clock or (lambda: datetime.now(timezone.utc))
    generated_at = clock().isoformat(timespec="seconds")
    graphify_version = str(sidecars["telemetry"].get("graphify_version", "unknown"))

    context: dict[str, str] = {
        "god_nodes": god_nodes,
        "recent_deltas": recent_deltas,
        "hot_paths": hot_paths,
        "agent_identity": agent_identity,
        "generated_at": generated_at,
        "graphify_version": graphify_version,
    }

    written: list[Path] = []
    for block_name in _BLOCK_ORDER:
        block = blocks.get(block_name)
        if not isinstance(block, dict):
            raise ValueError(
                f"schema block {block_name!r} missing or malformed in "
                f"{target!r} schema"
            )
        filename = block.get("filename")
        body = block.get("body")
        if not isinstance(filename, str) or not isinstance(body, str):
            raise ValueError(
                f"schema block {block_name!r} requires string 'filename' "
                "and 'body' fields"
            )

        normalized = _normalize_placeholders(body)
        rendered = string.Template(normalized).safe_substitute(context)

        out_path = validated_dir / filename
        # Final guard — filename could conceivably contain ``..``; ensure the
        # resolved child path still lives under the validated directory.
        if not str(out_path.resolve()).startswith(str(base)):
            raise ValueError(
                f"harness filename {filename!r} escapes base {base}"
            )

        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(rendered, encoding="utf-8")
        os.replace(tmp, out_path)
        written.append(out_path)

    return written
