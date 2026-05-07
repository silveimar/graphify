# Phase 71 (TEMP) — Temporal edge validity primitives.
#
# Public surface (consumed by build/extract/export and Plan 71-04):
#   * run_now_iso()           — pinned-clockable ISO-8601 UTC timestamp.
#   * load_decay_config()     — error-tolerant YAML loader with in-code defaults.
#   * compute_decay_weight()  — exponential half-life decay with floor + fail-open.
#   * stamp_supersessions()   — INFERRED-only history stamper (D-4/D-5/D-6).
#
# All four functions are stdlib-only at import time (PyYAML and yaml.safe_load
# are imported lazily inside load_decay_config so missing PyYAML never breaks
# import — D-3 mitigation, T-71-01).
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import networkx as nx

# In-code defaults (D-3): used when temporal_config.yaml is missing, PyYAML is
# not installed, or yaml.safe_load fails. Mirrors the shipped YAML.
_IN_CODE_DEFAULTS: dict = {
    "default": {
        "function": "exponential",
        "half_life_days": 30,
        "floor": 0.1,
    },
    "semantically_similar_to": {
        "function": "exponential",
        "half_life_days": 14,
        "floor": 0.1,
    },
}


def run_now_iso() -> str:
    """Return ISO-8601 UTC timestamp for the current run.

    GRAPHIFY_RUN_TS overrides the wall clock so tests (and reproducible runs)
    can pin the run-clock to a known value (D-1).
    """
    pin = os.environ.get("GRAPHIFY_RUN_TS")
    if pin:
        return pin
    return datetime.now(timezone.utc).isoformat()


def _defaults_copy() -> dict:
    # Deep enough copy for our flat 2-level dict — avoids accidental mutation by callers.
    return {k: dict(v) for k, v in _IN_CODE_DEFAULTS.items()}


def load_decay_config(path: Path | None = None) -> dict:
    """Load decay parameters from YAML, falling back to in-code defaults.

    Resolution order:
      1. If `path` is provided, read it directly.
      2. Otherwise, read the package-shipped graphify/temporal_config.yaml.

    All known failure modes (PyYAML missing, file missing, parse error) fall
    back to ``_IN_CODE_DEFAULTS`` (D-3 / T-71-01 mitigation). Always guarantees
    the returned dict has a "default" key.
    """
    # Lazy import — keep the module import stdlib-only so missing PyYAML cannot
    # break imports of graphify.temporal in CI environments without the [mcp]/[obsidian] extras.
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _defaults_copy()
    # `monkeypatch.setitem(sys.modules, "yaml", None)` makes the import succeed
    # but yields None — guard against that.
    if yaml is None:
        return _defaults_copy()

    text: str | None = None
    try:
        if path is not None:
            text = Path(path).read_text(encoding="utf-8")
        else:
            text = files("graphify").joinpath("temporal_config.yaml").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return _defaults_copy()
    except Exception:
        # Any other resource-resolution failure → defaults.
        return _defaults_copy()

    try:
        # NEVER use yaml.load — T-71-01 mitigation (arbitrary object construction).
        loaded = yaml.safe_load(text)
    except Exception:  # yaml.YAMLError and any pathological subclass
        return _defaults_copy()

    if not isinstance(loaded, dict):
        return _defaults_copy()

    # Ensure "default" key is present even if the user-supplied YAML omits it.
    if "default" not in loaded or not isinstance(loaded.get("default"), dict):
        loaded["default"] = dict(_IN_CODE_DEFAULTS["default"])
    else:
        # Backfill any missing default sub-keys from in-code defaults.
        for k, v in _IN_CODE_DEFAULTS["default"].items():
            loaded["default"].setdefault(k, v)
    return loaded


def _parse_iso(s: str) -> datetime | None:
    try:
        # fromisoformat in 3.10 supports "+00:00"; "Z" suffix needs replacement.
        if isinstance(s, str) and s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def compute_decay_weight(
    *,
    relation: str,
    valid_from: str,
    run_now: str,
    config: dict,
) -> float:
    """Exponential half-life decay clamped to a per-relation floor.

    Per-relation params come from config[relation], falling back to
    config["default"]. Unknown decay function → fail open at 1.0 (D-2).
    Unparseable timestamps also fail open at 1.0.
    """
    params = config.get(relation) if isinstance(config, dict) else None
    if not isinstance(params, dict):
        params = config.get("default", {}) if isinstance(config, dict) else {}

    fn = params.get("function", "exponential")
    if fn != "exponential":
        return 1.0

    try:
        half_life_days = float(params.get("half_life_days", 30))
        floor = float(params.get("floor", 0.0))
    except (TypeError, ValueError):
        return 1.0
    if half_life_days <= 0:
        return 1.0

    t0 = _parse_iso(valid_from)
    t1 = _parse_iso(run_now)
    if t0 is None or t1 is None:
        return 1.0

    age_days = max(0.0, (t1 - t0).total_seconds() / 86400.0)
    raw = 0.5 ** (age_days / half_life_days)
    return max(floor, raw)


def _coerce_prior_edges(prior_graph_path: Path) -> list[dict] | None:
    """Read+parse a prior node_link graph.json into a list of edge dicts.

    Returns None on any failure (T-71-13 mitigation): missing file, invalid
    JSON, non-dict root, networkx parse error.
    """
    try:
        text = Path(prior_graph_path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    try:
        data = json.loads(text)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        prior_g = nx.readwrite.json_graph.node_link_graph(data, edges="links")
    except Exception:
        return None

    out: list[dict] = []
    for u, v, attrs in prior_g.edges(data=True):
        d = dict(attrs)
        d.setdefault("source", u)
        d.setdefault("target", v)
        out.append(d)
    return out


def stamp_supersessions(
    *,
    new_edges: list[dict],
    prior_graph_path: Path,
    run_now: str,
) -> list[dict]:
    """Stamp INFERRED prior edges that vanished from the new run with valid_until.

    Algorithm (D-4 / D-5 / D-6):
      * INFERRED only — EXTRACTED edges are skipped (D-4).
      * Match key is the global tuple (source, target, relation) across the
        entire new run, regardless of source_file (D-5).
      * Superseded edges are appended to the returned list with valid_until
        set to ``run_now`` (history retention — D-6).

    Failure modes (T-71-13): if the prior graph cannot be located, parsed, or
    is not a dict, the function returns ``new_edges`` unchanged.
    """
    prior_edges = _coerce_prior_edges(Path(prior_graph_path))
    if prior_edges is None:
        return new_edges

    # Global match set across the whole new run (D-5).
    new_keys: set[tuple] = set()
    for e in new_edges:
        if not isinstance(e, dict):
            continue
        new_keys.add((e.get("source"), e.get("target"), e.get("relation")))

    superseded: list[dict] = []
    for pe in prior_edges:
        if pe.get("confidence") != "INFERRED":  # D-4
            continue
        key = (pe.get("source"), pe.get("target"), pe.get("relation"))
        if key in new_keys:  # D-5: reproduced anywhere → no supersession
            continue
        stamped = dict(pe)
        stamped["valid_until"] = run_now
        superseded.append(stamped)

    return list(new_edges) + superseded
