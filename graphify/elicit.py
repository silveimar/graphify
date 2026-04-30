"""Tacit-to-explicit elicitation (Phase 39, SEED-001).

Hybrid interview: deterministic scripted backbone plus optional LLM deepening
(:func:`maybe_deepen_session`, no-op unless explicitly enabled by caller/env).

Sidecar contract (Phase 39-02 merge):
    Filename: ``elicitation.json`` beside ``graph.json`` under
    ``ResolvedOutput.artifacts_dir`` (or any validated artifacts root).

    Top-level JSON keys::

        version: int   # currently 1
        extraction: {\"nodes\": [...], \"edges\": [...]}  # graphify schema
        meta: {...}    # optional session metadata for tooling

    Merge order when combining with file extraction in :func:`graphify.build.build`:
    file extractions first, then sidecar ``extraction`` last (later wins on
    duplicate node ``id``). Phase 39-02 wires this; callers must only persist
    schema-valid dicts.

Paths: writes use :func:`_validate_new_file_under_base` so the target file may
not exist yet (unlike :func:`graphify.security.validate_graph_path`, which is
for reading existing graph artifacts).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from graphify.security import sanitize_label
from graphify.validate import validate_extraction

ELICITATION_SIDECAR_FILENAME = "elicitation.json"
_MAX_SIDECAR_BYTES = 4_194_304  # 4 MiB cap for JSON sidecar reads


class ElicitationState(str, Enum):
    """Interview backbone states (scripted path advances in order)."""

    RHYTHMS = "rhythms"
    DECISIONS = "decisions"
    DEPENDENCIES = "dependencies"
    KNOWLEDGE = "knowledge"
    FRICTION = "friction"
    CONFIRM = "confirm"
    DONE = "done"


_DIMENSION_ORDER: tuple[ElicitationState, ...] = (
    ElicitationState.RHYTHMS,
    ElicitationState.DECISIONS,
    ElicitationState.DEPENDENCIES,
    ElicitationState.KNOWLEDGE,
    ElicitationState.FRICTION,
)


def _slug_dimension(st: ElicitationState) -> str:
    return st.value


@dataclass
class ElicitationSession:
    """In-memory session for scripted or interactive flows."""

    answers: dict[str, str] = field(default_factory=dict)
    state: ElicitationState = ElicitationState.RHYTHMS
    confirmed: bool = False

    def dimension_keys(self) -> tuple[str, ...]:
        return tuple(_slug_dimension(s) for s in _DIMENSION_ORDER)


def run_scripted_elicitation(
    answers: Mapping[str, str],
    *,
    auto_confirm: bool = True,
) -> ElicitationSession:
    """Drive the interview using fixed answers (tests and batch tooling).

    *answers* maps dimension key (e.g. ``\"rhythms\"``) → free-text answer.
    Missing keys default to empty string. After loading answers, moves through
    ``CONFIRM`` to ``DONE`` when *auto_confirm* is True.
    """
    session = ElicitationSession(answers=dict(answers))
    for dim in _DIMENSION_ORDER:
        k = _slug_dimension(dim)
        session.answers.setdefault(k, "")
    if auto_confirm:
        session.confirmed = True
        session.state = ElicitationState.DONE
    else:
        session.state = ElicitationState.CONFIRM
    return session


def build_extraction_from_session(session: ElicitationSession) -> dict[str, Any]:
    """Return an extraction-shaped dict from a completed session.

    Nodes use ``file_type=\"rationale\"`` for elicited statements. Labels are
    sanitized. Hub id ``elicitation_hub`` links to each dimension node.
    """
    hub_id = "elicitation_hub"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    nodes.append(
        {
            "id": hub_id,
            "label": sanitize_label("Elicitation session"),
            "file_type": "rationale",
            "source_file": "elicitation/session",
            "source_location": "",
        }
    )

    for dim in _DIMENSION_ORDER:
        key = _slug_dimension(dim)
        raw = session.answers.get(key, "")
        label = sanitize_label(raw) if raw else sanitize_label(f"(empty: {key})")
        nid = f"elicitation_{key}"
        nodes.append(
            {
                "id": nid,
                "label": label,
                "file_type": "rationale",
                "source_file": "elicitation/session",
                "source_location": key,
            }
        )
        edges.append(
            {
                "source": hub_id,
                "target": nid,
                "relation": "contains",
                "confidence": "EXTRACTED",
                "source_file": "elicitation/session",
            }
        )

    return {"nodes": nodes, "edges": edges}


def maybe_deepen_session(
    session: ElicitationSession,
    *,
    enable_llm: bool | None = None,
) -> ElicitationSession:
    """Optional LLM deepening hook (Phase 39): default is identity.

    When *enable_llm* is None, reads env ``GRAPHIFY_ELICIT_LLM`` (``\"1\"`` /
    ``\"true\"`` / ``\"yes\"`` enables). Tests never set this.
    """
    if enable_llm is None:
        flag = os.environ.get("GRAPHIFY_ELICIT_LLM", "").lower()
        enable_llm = flag in ("1", "true", "yes")
    if not enable_llm:
        return session
    # Placeholder: deeper prompts would run here without breaking determinism when off.
    return session


def _validate_new_file_under_base(candidate: Path, base: Path) -> Path:
    """Ensure *candidate* is inside *base* (allows non-existent file)."""
    base_r = base.resolve()
    cand_r = candidate.resolve()
    try:
        cand_r.relative_to(base_r)
    except ValueError as exc:
        raise ValueError(
            f"Path {candidate!r} escapes artifacts directory {base_r}"
        ) from exc
    return cand_r


def _merge_extractions_by_node_id(
    prior: dict[str, Any], new: dict[str, Any]
) -> dict[str, Any]:
    """Merge node lists by id (later wins); concatenate edges de-duplicated."""
    nodes_out: dict[str, dict[str, Any]] = {}
    for n in prior.get("nodes", []):
        if isinstance(n, dict) and "id" in n:
            nodes_out[str(n["id"])] = dict(n)
    for n in new.get("nodes", []):
        if isinstance(n, dict) and "id" in n:
            nodes_out[str(n["id"])] = dict(n)

    edge_key = lambda e: (
        e.get("source"),
        e.get("target"),
        e.get("relation"),
        e.get("source_file", ""),
    )
    seen: set[tuple[Any, ...]] = set()
    edges_out: list[dict[str, Any]] = []
    for group in (prior.get("edges", []), new.get("edges", [])):
        for e in group:
            if not isinstance(e, dict):
                continue
            k = edge_key(e)
            if k in seen:
                continue
            seen.add(k)
            edges_out.append(dict(e))

    return {"nodes": list(nodes_out.values()), "edges": edges_out}


def save_elicitation_sidecar(
    artifacts_dir: Path | str,
    data: dict[str, Any],
    *,
    mode: str = "write",
    force: bool = False,
    filename: str = ELICITATION_SIDECAR_FILENAME,
) -> Path:
    """Persist extraction (+ meta) to *artifacts_dir* / *filename*.

    *mode* is reserved (``\"write\"`` | ``\"merge\"``); merge behavior for
    duplicate node ids is controlled by *force*:

    - ``force=True``: overwrite prior extraction with *data* as-is.
    - ``force=False``: if file exists, merge extractions by node id (later wins).

    Validates write path under *artifacts_dir* before creating parents.
    """
    base = Path(artifacts_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    target = _validate_new_file_under_base(base / filename, base)

    extraction = dict(data)
    errors = validate_extraction(extraction)
    if errors:
        raise ValueError("Invalid extraction for sidecar: " + "; ".join(errors[:5]))

    payload: dict[str, Any] = {
        "version": 1,
        "extraction": extraction,
        "meta": {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
        },
    }

    if target.exists() and not force:
        try:
            prev_raw = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev_raw = {}
        prev_ext = (
            prev_raw.get("extraction")
            if isinstance(prev_raw.get("extraction"), dict)
            else {}
        )
        merged = _merge_extractions_by_node_id(prev_ext, extraction)
        payload["extraction"] = merged
        payload["meta"]["merged"] = True

    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_elicitation_sidecar(
    artifacts_dir: Path | str,
    *,
    filename: str = ELICITATION_SIDECAR_FILENAME,
) -> dict[str, Any] | None:
    """Load extraction dict from sidecar, or None if missing."""
    base = Path(artifacts_dir).resolve()
    path = _validate_new_file_under_base(base / filename, base)
    if not path.exists():
        return None
    try:
        sz = path.stat().st_size
    except OSError:
        return None
    if sz > _MAX_SIDECAR_BYTES:
        print(
            f"[graphify] elicitation sidecar too large ({sz} bytes) — skipping",
            file=sys.stderr,
        )
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(
            f"[graphify] elicitation sidecar invalid JSON — skipping: {path}",
            file=sys.stderr,
        )
        return None
    ext = raw.get("extraction")
    return ext if isinstance(ext, dict) else None


def merge_elicitation_into_build_inputs(
    extractions: list[dict[str, Any]],
    artifacts_dir: Path | str | None,
) -> list[dict[str, Any]]:
    """Append elicitation extraction after *extractions* when sidecar exists."""
    if artifacts_dir is None:
        return list(extractions)
    loaded = load_elicitation_sidecar(artifacts_dir)
    if loaded is None:
        return list(extractions)
    return list(extractions) + [loaded]


def write_elicitation_harness_markdown(
    artifacts_dir: Path | str,
    session: ElicitationSession,
    *,
    target: str = "claude",
    _clock: Callable[[], datetime] | None = None,
) -> list[Path]:
    """Write SOUL/HEARTBEAT/USER files under ``artifacts_dir/harness/`` from a session.

    Fast path for D-04: no ``graph.json`` required. Uses ``claude.yaml`` blocks
    and the same placeholder normalization as :func:`graphify.harness_export.export_claude_harness`.
    """
    import string

    import yaml

    from graphify.harness_export import (
        _BLOCK_ORDER,
        _collect_god_nodes,
        _normalize_placeholders,
        _write_fidelity_manifest,
    )
    from graphify.harness_schemas import schema_path
    from graphify.security import validate_graph_path

    from graphify.version import package_version as _pkg_version

    graphify_version = _pkg_version()

    base = Path(artifacts_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    harness_dir = base / "harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    validated_dir = validate_graph_path(harness_dir, base=base)

    ext = build_extraction_from_session(session)
    graph_data: dict[str, Any] = {
        "nodes": ext.get("nodes", []),
        "links": ext.get("edges", []),
    }
    god_nodes = _collect_god_nodes(graph_data)
    recent = "\n".join(
        f"- **{k}**: {sanitize_label(v)}"
        for k, v in sorted(session.answers.items())
    )
    if not recent.strip():
        recent = "(no elicitation answers yet)"

    clock_fn = _clock or (lambda: datetime.now(timezone.utc))
    generated_at = clock_fn().isoformat(timespec="seconds")

    context: dict[str, str] = {
        "god_nodes": god_nodes,
        "recent_deltas": recent,
        "hot_paths": sanitize_label(session.answers.get("friction", "(none)"))[:2000],
        "agent_identity": "elicitation session · graphify",
        "generated_at": generated_at,
        "graphify_version": graphify_version,
    }

    schema_doc = yaml.safe_load(schema_path(target).read_text(encoding="utf-8"))
    blocks = schema_doc.get("blocks")
    if not isinstance(blocks, dict):
        raise ValueError(f"harness schema for {target!r} missing blocks")

    md_written: list[Path] = []
    for block_name in _BLOCK_ORDER:
        block = blocks.get(block_name)
        if not isinstance(block, dict):
            raise ValueError(f"schema block {block_name!r} missing")
        filename = block.get("filename")
        body = block.get("body")
        if not isinstance(filename, str) or not isinstance(body, str):
            raise ValueError(f"schema block {block_name!r} needs filename and body")
        normalized = _normalize_placeholders(body)
        rendered = string.Template(normalized).safe_substitute(context)
        out_path = validated_dir / filename
        try:
            out_path.resolve().relative_to(base)
        except ValueError as exc:
            raise ValueError(f"harness filename {filename!r} escaped base") from exc
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(rendered, encoding="utf-8")
        os.replace(tmp, out_path)
        md_written.append(out_path)

    prior: dict[str, Any] | None = None
    fid = validated_dir / "fidelity.json"
    if fid.exists():
        try:
            loaded = json.loads(fid.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prior = loaded
        except json.JSONDecodeError:
            prior = None
    fidelity_out = _write_fidelity_manifest(
        validated_dir, md_written, prior=prior, target=target
    )
    return md_written + [fidelity_out]
