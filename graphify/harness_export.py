"""Harness memory export (SEED-002, HARNESS-01..06).

Reads snapshot sidecars and emits SOUL/HEARTBEAT/USER markdown files per a
declarative schema (``graphify/harness_schemas/claude.yaml``). Utilities-only
(D-73): no LLM calls, no skill imports, no auto-trigger from pipeline/watch.

Placeholder rendering uses ``string.Template.safe_substitute`` exclusively —
``{{ token }}`` tokens are normalized to ``${token}`` via a single regex
(HARNESS-03). No Jinja2 import anywhere in this module.
"""
from __future__ import annotations

import hashlib
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


# ---------------------------------------------------------------------------
# HARNESS-07 / T-13-07: secret-scanner regex suite
# ---------------------------------------------------------------------------
# Module-level tuple of (name, compiled_pattern) pairs. Compiled once at
# import — runs when ``export_claude_harness`` is called with
# ``include_annotations=True``. Kept inline (no new file) per planner guidance;
# can be extracted if the suite ever exceeds 15 patterns.

# WR-01 (Phase 13 review): include the full set of AWS access-key prefixes,
# not just long-term IAM keys (AKIA). ASIA covers STS/SSO temporary creds
# and is now the most common shape in cloud-native workloads.
_AWS_KEY = re.compile(
    r"(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|AIPA)[0-9A-Z]{16}"
)
_GITHUB_PAT = re.compile(r"ghp_[A-Za-z0-9]{36}")
# CR-02 (Phase 13 review): the original ``sk-[A-Za-z0-9]{20,}`` was too
# permissive — it matched legitimate identifiers such as ``sk-learn-...``
# and arbitrary 20+ char ``sk-`` prefixed tokens, causing false positives
# in error mode and mangling unrelated content in redact mode. Tighten to
# the documented OpenAI key shapes: ``sk-<48+>`` and ``sk-proj-<64+>``.
_OPENAI_KEY = re.compile(
    r"\b(?:sk-proj-[A-Za-z0-9_-]{64,}|sk-[A-Za-z0-9]{48,})\b"
)
_SLACK_TOKEN = re.compile(r"xox[baprs]-[A-Za-z0-9-]+")
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}")
# CR-01 (Phase 13 review): match the entire PEM block — header, body, and
# footer — so redaction does not leave the base64 key material behind.
_PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN[ A-Z]+PRIVATE KEY-----"
    r".*?"
    r"-----END[ A-Z]+PRIVATE KEY-----",
    re.DOTALL,
)
# Email-style credential heuristic — only flag when ':' appears AFTER an '@'
# to reduce false positives on ordinary prose containing colons.
_EMAIL_CRED = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+:[A-Za-z0-9@#$%^&*()_+=!\-]{8,}"
)

SECRET_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("aws_access_key", _AWS_KEY),
    ("github_pat", _GITHUB_PAT),
    ("openai_api_key", _OPENAI_KEY),
    ("slack_token", _SLACK_TOKEN),
    ("bearer_token", _BEARER),
    ("pem_private_key", _PEM_PRIVATE_KEY),
    ("email_credential", _EMAIL_CRED),
)

_REDACTION_MARKER = "[REDACTED]"


def _redact_secrets(value: str) -> tuple[str, list[str]]:
    """Return ``(cleaned_value, matched_pattern_names)``.

    Applies every :data:`SECRET_PATTERNS` entry in declaration order. Matches
    are replaced with the literal marker :data:`_REDACTION_MARKER`. The
    matched name is appended once per pattern that fired (not once per
    occurrence) so callers can group findings by pattern family.
    """
    matches: list[str] = []
    cleaned = value
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(cleaned):
            matches.append(name)
            cleaned = pattern.sub(_REDACTION_MARKER, cleaned)
    return cleaned, matches


def scan_annotations_for_secrets(
    annotations: list[dict[str, Any]],
    *,
    mode: str = "redact",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan every string value in an annotation dict that is NOT in
    :data:`ANNOTATION_ALLOW_LIST`.

    The allow-list fields (``id``, ``label``, ``source_file``, ``relation``,
    ``confidence``) are treated as user-facing safe fields and bypass the
    scanner — changing them would break downstream consumers. Only the
    *delta* (free-text ``body``, ``peer_id``, and any other keys) is scanned.

    Parameters
    ----------
    annotations:
        List of annotation dicts (as loaded by :func:`_load_sidecars`).
    mode:
        ``"redact"`` replaces matches with :data:`_REDACTION_MARKER`.
        ``"error"`` raises :class:`ValueError` listing offending annotation
        ids (CLI converts to exit-code 3).

    Returns
    -------
    ``(cleaned_annotations, findings)`` where ``findings`` is a list of
    ``{"id": annotation_id, "field": key, "patterns": [name, ...]}`` dicts.

    Raises
    ------
    ValueError
        If ``mode not in {"redact", "error"}`` or (in ``"error"`` mode) at
        least one annotation field matched a secret pattern.
    """
    if mode not in {"redact", "error"}:
        raise ValueError(f"unknown secrets_mode: {mode!r}")

    cleaned: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for a in annotations:
        new_a: dict[str, Any] = {}
        ann_id = str(a.get("id") or "<unknown>")
        for k, v in a.items():
            if k in ANNOTATION_ALLOW_LIST or not isinstance(v, str):
                new_a[k] = v
                continue
            redacted, matched = _redact_secrets(v)
            new_a[k] = redacted
            if matched:
                findings.append(
                    {"id": ann_id, "field": k, "patterns": matched}
                )
        cleaned.append(new_a)

    if mode == "error" and findings:
        ids = sorted({f["id"] for f in findings})
        raise ValueError(
            "harness export: secret patterns detected in annotations; "
            f"offending annotation ids: {ids}. "
            "Re-run with --secrets-mode redact to continue."
        )
    return cleaned, findings


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
        # WR-06 (Phase 13 review): also emit an aggregate count so a
        # half-truncated sidecar surfaces as a single visible warning,
        # not just buried per-line notices.
        skipped_lines = 0
        for idx, line in enumerate(ann_path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                skipped_lines += 1
                print(
                    f"[graphify] annotations.jsonl line {idx}: skipped (invalid JSON)",
                    file=sys.stderr,
                )
                continue
            if isinstance(rec, dict):
                annotations.append(rec)
        if skipped_lines:
            print(
                f"[graphify] warning: skipped {skipped_lines} corrupt "
                f"annotations.jsonl line(s); kept {len(annotations)}",
                file=sys.stderr,
            )
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
    """Most recent N agent edges. Sort by (ts DESC, from ASC, to ASC).

    WR-05 (Phase 13 review): the previous implementation built per-char
    Unicode-complement strings (``chr(0x10FFFF - ord(c))``) to flip DESC
    order inside a single ``sorted`` key. That trick produced unreadable
    keys and risked emitting noncharacter codepoints. Python's sort is
    stable, so a two-pass sort delivers the same total order without the
    surrogate-pair hazard:

      1. ASC sort by tie-breakers ``(from, to)``
      2. DESC sort by ``ts`` (stable — preserves the ASC tie-breaker)
    """
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
    # Two-pass stable sort (WR-05): tie-breakers first, then primary key.
    ranked = sorted(sanitized, key=lambda e: (e["from"], e["to"]))
    ranked.sort(key=lambda e: e["ts"], reverse=True)
    ranked = ranked[:limit]
    lines = [
        f"- `{e['ts']}` · {e['from']} → {e['to']} ({e['relation']})"
        for e in ranked
    ]
    return "\n".join(lines)


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
# HARNESS-08: injectable clock seam + round-trip fidelity manifest helpers
# ---------------------------------------------------------------------------


def _system_clock() -> datetime:
    """Default clock — real wall-clock time in UTC."""
    return datetime.now(timezone.utc)


# Module-level override hook. Tests and the HARNESS-08 byte-equal self-check
# call :func:`set_clock` to pin ``generated_at`` across successive runs.
_default_clock: Callable[[], datetime] = _system_clock


def set_clock(fn: Callable[[], datetime]) -> None:
    """Override the default ``generated_at`` provider.

    Primary use: tests + round-trip fidelity self-check. Passing a
    ``_clock`` kwarg to :func:`export_claude_harness` still takes precedence
    over this module-level override.
    """
    global _default_clock
    _default_clock = fn


def _sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 of ``path``'s bytes.

    Mirrors :func:`graphify.capability.canonical_manifest_hash` discipline
    so round-trip comparisons use the same hashing contract as the MCP
    capability manifest.
    """
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_fidelity_manifest(
    harness_dir: Path,
    written: list[Path],
    *,
    prior: dict[str, Any] | None = None,
    target: str = "claude",
) -> Path:
    """HARNESS-08: record per-file SHA-256 + byte-length for every written file.

    On the first run ``round_trip`` is ``"first-export"``. On subsequent runs
    the existing ``fidelity.json`` is passed in as ``prior``; if every file
    matches byte-for-byte the field flips to ``"byte-equal"``, otherwise
    ``"drift"``. Written via ``.tmp`` + :func:`os.replace` so readers never
    observe a torn file.
    """
    files: dict[str, dict[str, Any]] = {}
    for p in written:
        files[p.name] = {
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        }

    round_trip = "first-export"
    if prior is not None:
        prior_files = prior.get("files") or {}
        if (
            prior_files
            and set(prior_files.keys()) == set(files.keys())
            and all(
                prior_files.get(name, {}).get("sha256") == meta["sha256"]
                and prior_files.get(name, {}).get("bytes") == meta["bytes"]
                for name, meta in files.items()
            )
        ):
            round_trip = "byte-equal"
        else:
            round_trip = "drift"

    manifest = {
        "version": 1,
        "target": target,
        "round_trip": round_trip,
        "files": files,
    }

    out = harness_dir / "fidelity.json"
    tmp = out.with_suffix(".tmp")
    payload = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, out)
    return out


# ---------------------------------------------------------------------------
# Main export (HARNESS-01..05)
# ---------------------------------------------------------------------------


def export_claude_harness(
    out_dir: Path,
    *,
    target: str = "claude",
    include_annotations: bool = False,
    secrets_mode: str = "redact",
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
        :data:`ANNOTATION_ALLOW_LIST`. When ``True``, the full annotation
        set is retained but first passed through
        :func:`scan_annotations_for_secrets` (HARNESS-07 / T-13-07) so
        matched credentials are either redacted inline or surfaced as a
        non-zero exit.
    secrets_mode:
        One of ``"redact"`` or ``"error"`` — only consulted when
        ``include_annotations=True``. ``"redact"`` (default) replaces
        matches with ``[REDACTED]`` and emits a stderr summary; ``"error"``
        raises :class:`ValueError` listing the offending annotation ids
        (the CLI converts that to exit-code 3).
    _clock:
        Injectable ``() -> datetime`` seam used to pin ``generated_at`` in
        tests (T-13-06 byte-equality). When ``None`` (default), falls back
        to the module-level clock override via :func:`set_clock` or to
        ``datetime.now(timezone.utc)``. HARNESS-08 (round-trip fidelity)
        relies on a pinned clock to produce byte-equal output.

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
    # WR-03 (Phase 13 review): the previous ``startswith(str(base))`` guard
    # is vulnerable to prefix collisions (``/tmp/out`` vs ``/tmp/outX``).
    # Use ``Path.resolve().is_relative_to(...)`` instead — semantic path
    # containment, not lexical prefix matching.
    try:
        validated_dir.resolve().relative_to(base)
    except ValueError as exc:
        raise ValueError(
            f"harness_dir {validated_dir} escaped base {base}"
        ) from exc

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
    findings: list[dict[str, Any]] = []
    if include_annotations:
        # HARNESS-07 / T-13-07: scan BEFORE skipping allow-list so redaction is
        # visible in output. ``mode='error'`` raises ValueError; the CLI maps
        # that to exit-code 3.
        annotations, findings = scan_annotations_for_secrets(
            annotations, mode=secrets_mode
        )
    else:
        annotations = _filter_annotations_allowlist(annotations)

    if findings:
        unique_ids = len({f["id"] for f in findings})
        print(
            f"[graphify] harness export: redacted {len(findings)} secret "
            f"match(es) across {unique_ids} annotation(s)",
            file=sys.stderr,
        )

    god_nodes = _collect_god_nodes(sidecars["graph_data"])
    recent_deltas = _collect_recent_deltas(sidecars["agent_edges"])
    hot_paths = _collect_hot_paths(sidecars["telemetry"])
    agent_identity = _collect_agent_identity(sidecars["telemetry"])

    # HARNESS-08: kwarg > module override > system wall clock.
    clock = _clock or _default_clock
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
        # WR-03 (Phase 13 review): use ``relative_to`` instead of string
        # prefix matching to avoid sibling-directory prefix collisions.
        try:
            out_path.resolve().relative_to(base)
        except ValueError as exc:
            raise ValueError(
                f"harness filename {filename!r} escapes base {base}"
            ) from exc

        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(rendered, encoding="utf-8")
        os.replace(tmp, out_path)
        written.append(out_path)

    # HARNESS-08: write the round-trip fidelity manifest AFTER the three
    # block files exist so the per-file SHA-256 reflects final on-disk bytes.
    prior: dict[str, Any] | None = None
    fidelity_path = validated_dir / "fidelity.json"
    if fidelity_path.exists():
        try:
            loaded = json.loads(fidelity_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prior = loaded
        except json.JSONDecodeError:
            # Corrupt prior — treat as first export rather than false-positive
            # "byte-equal" against an unreadable manifest.
            prior = None

    fidelity_out = _write_fidelity_manifest(
        validated_dir, written, prior=prior, target=target
    )
    written.append(fidelity_out)

    # Stable, grep-friendly stderr summary for CI + operators.
    try:
        rt = json.loads(fidelity_out.read_text(encoding="utf-8")).get(
            "round_trip", "unknown"
        )
    except json.JSONDecodeError:
        rt = "unknown"
    print(
        f"[graphify] harness export: round_trip={rt}",
        file=sys.stderr,
    )

    return written
