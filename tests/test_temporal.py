"""Phase 71 Wave 0 — unit tests for graphify.temporal.

Covers run_now_iso (env override + UTC default), load_decay_config (PyYAML
guard, FileNotFoundError, YAMLError, default key merge), compute_decay_weight
(half-life, floor, fail-open on unknown function), and stamp_supersessions
(D-4 INFERRED-only, D-5 global tuple match, D-6 history retention, no-prior,
malformed-prior).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from graphify.temporal import (
    compute_decay_weight,
    load_decay_config,
    run_now_iso,
    stamp_supersessions,
)


# --- run_now_iso ----------------------------------------------------------

def test_run_now_iso_default_is_utc_iso():
    out = run_now_iso()
    assert isinstance(out, str)
    # ISO-8601 UTC indicators
    assert "T" in out
    assert ("+00:00" in out) or out.endswith("Z")


def test_run_now_iso_env_override(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_RUN_TS", "2026-05-07T12:00:00+00:00")
    assert run_now_iso() == "2026-05-07T12:00:00+00:00"


def test_pinned_run_ts_fixture(pinned_run_ts):
    # Fixture from conftest.py pins the env var
    assert run_now_iso() == "2026-05-07T12:00:00+00:00"


# --- load_decay_config ----------------------------------------------------

DEFAULT_REQUIRED_KEYS = {"function", "half_life_days", "floor"}


def test_load_decay_config_returns_default_when_pyyaml_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    cfg = load_decay_config()
    assert "default" in cfg
    assert DEFAULT_REQUIRED_KEYS <= set(cfg["default"].keys())


def test_load_decay_config_returns_default_on_missing_file(tmp_path):
    cfg = load_decay_config(path=tmp_path / "does_not_exist.yaml")
    assert "default" in cfg
    assert DEFAULT_REQUIRED_KEYS <= set(cfg["default"].keys())


def test_load_decay_config_returns_default_on_yaml_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("default:\n  function: : : :\n  half_life_days\n")
    cfg = load_decay_config(path=bad)
    assert "default" in cfg
    assert DEFAULT_REQUIRED_KEYS <= set(cfg["default"].keys())


def test_load_decay_config_merges_default_when_user_omits_it(tmp_path):
    # Only a per-relation key, no "default" — loader must inject default.
    user = tmp_path / "user.yaml"
    user.write_text(
        "semantically_similar_to:\n"
        "  function: exponential\n"
        "  half_life_days: 7\n"
        "  floor: 0.05\n"
    )
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("PyYAML not installed; skipping yaml-roundtrip test")
    cfg = load_decay_config(path=user)
    assert "default" in cfg
    assert DEFAULT_REQUIRED_KEYS <= set(cfg["default"].keys())


# --- compute_decay_weight -------------------------------------------------

def _cfg(half_life=30, floor=0.1, function="exponential"):
    return {
        "default": {
            "function": function,
            "half_life_days": half_life,
            "floor": floor,
        }
    }


def test_compute_decay_weight_age_zero_is_one():
    w = compute_decay_weight(
        relation="calls",
        valid_from="2026-05-07T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=_cfg(),
    )
    assert w == pytest.approx(1.0)


def test_compute_decay_weight_at_half_life_is_about_half():
    # 30 days after valid_from, half_life=30 → 0.5
    w = compute_decay_weight(
        relation="calls",
        valid_from="2026-04-07T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=_cfg(half_life=30, floor=0.0),
    )
    assert w == pytest.approx(0.5, abs=0.01)


def test_compute_decay_weight_floor_clamp():
    # 300 days, half_life 30 → 0.5**10 ≈ 0.001 → clamped to floor 0.1
    w = compute_decay_weight(
        relation="calls",
        valid_from="2025-07-11T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=_cfg(half_life=30, floor=0.1),
    )
    assert w == pytest.approx(0.1)


def test_compute_decay_weight_unknown_function_fails_open():
    w = compute_decay_weight(
        relation="calls",
        valid_from="2026-04-07T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=_cfg(function="cubic-bezier-of-doom"),
    )
    assert w == 1.0


def test_compute_decay_weight_per_relation_lookup():
    cfg = {
        "default": {"function": "exponential", "half_life_days": 30, "floor": 0.0},
        "semantically_similar_to": {"function": "exponential", "half_life_days": 14, "floor": 0.0},
    }
    # Same age (14d) — default gives 0.5**(14/30); per-relation gives 0.5
    w_default = compute_decay_weight(
        relation="calls",
        valid_from="2026-04-23T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=cfg,
    )
    w_rel = compute_decay_weight(
        relation="semantically_similar_to",
        valid_from="2026-04-23T12:00:00+00:00",
        run_now="2026-05-07T12:00:00+00:00",
        config=cfg,
    )
    assert w_rel == pytest.approx(0.5, abs=0.01)
    assert w_default > w_rel  # default decays slower


# --- stamp_supersessions --------------------------------------------------

RUN_NOW = "2026-05-07T12:00:00+00:00"


def _write_prior_graph(path: Path, edges: list[dict], nodes: list[dict] | None = None):
    nodes = nodes or [
        {"id": "a", "label": "a", "file_type": "code", "source_file": "a.py"},
        {"id": "b", "label": "b", "file_type": "code", "source_file": "b.py"},
        {"id": "c", "label": "c", "file_type": "code", "source_file": "c.py"},
    ]
    data = {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": nodes,
        "links": edges,
    }
    path.write_text(json.dumps(data))


def test_stamp_supersessions_no_prior_returns_unchanged(tmp_path):
    new_edges = [{"source": "a", "target": "b", "relation": "calls",
                  "confidence": "INFERRED", "source_file": "a.py"}]
    out = stamp_supersessions(
        new_edges=new_edges,
        prior_graph_path=tmp_path / "missing.json",
        run_now=RUN_NOW,
    )
    assert out == new_edges


def test_stamp_supersessions_inferred_missing_is_appended(tmp_path):
    prior = tmp_path / "graph.json"
    _write_prior_graph(prior, [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "INFERRED", "source_file": "a.py",
         "valid_from": "2026-01-01T00:00:00+00:00"},
    ])
    new_edges = []  # nothing in new run
    out = stamp_supersessions(new_edges=new_edges, prior_graph_path=prior, run_now=RUN_NOW)
    assert len(out) == 1
    assert out[0]["valid_until"] == RUN_NOW
    assert out[0]["confidence"] == "INFERRED"
    assert out[0]["source"] == "a" and out[0]["target"] == "b"


def test_stamp_supersessions_extracted_missing_is_not_stamped(tmp_path):
    prior = tmp_path / "graph.json"
    _write_prior_graph(prior, [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "EXTRACTED", "source_file": "a.py"},
    ])
    out = stamp_supersessions(new_edges=[], prior_graph_path=prior, run_now=RUN_NOW)
    assert out == []  # EXTRACTED never stamped (D-4)


def test_stamp_supersessions_global_tuple_match_skips(tmp_path):
    # Prior INFERRED edge from file a.py; new run reproduces same (s,t,r) from b.py.
    # D-5: global rule wins — no supersession.
    prior = tmp_path / "graph.json"
    _write_prior_graph(prior, [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "INFERRED", "source_file": "a.py"},
    ])
    new_edges = [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "INFERRED", "source_file": "b.py"},
    ]
    out = stamp_supersessions(new_edges=new_edges, prior_graph_path=prior, run_now=RUN_NOW)
    assert len(out) == 1
    assert "valid_until" not in out[0] or out[0].get("valid_until") in (None,)


def test_stamp_supersessions_history_retained(tmp_path):
    prior = tmp_path / "graph.json"
    _write_prior_graph(prior, [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "INFERRED", "source_file": "a.py",
         "valid_from": "2026-01-01T00:00:00+00:00"},
        {"source": "b", "target": "c", "relation": "uses",
         "confidence": "INFERRED", "source_file": "b.py",
         "valid_from": "2026-02-01T00:00:00+00:00"},
    ])
    new_edges = [
        {"source": "a", "target": "b", "relation": "calls",
         "confidence": "INFERRED", "source_file": "a.py"},
    ]
    out = stamp_supersessions(new_edges=new_edges, prior_graph_path=prior, run_now=RUN_NOW)
    # New a→b stays; prior b→c (INFERRED missing) stamped with valid_until.
    assert len(out) == 2
    superseded = [e for e in out if e.get("valid_until") == RUN_NOW]
    assert len(superseded) == 1
    assert superseded[0]["source"] == "b" and superseded[0]["target"] == "c"
    # original valid_from preserved
    assert superseded[0].get("valid_from") == "2026-02-01T00:00:00+00:00"


def test_stamp_supersessions_malformed_prior_returns_unchanged(tmp_path):
    bad = tmp_path / "graph.json"
    bad.write_text("{not valid json")
    new_edges = [{"source": "a", "target": "b", "relation": "calls",
                  "confidence": "INFERRED", "source_file": "a.py"}]
    out = stamp_supersessions(new_edges=new_edges, prior_graph_path=bad, run_now=RUN_NOW)
    assert out == new_edges


def test_stamp_supersessions_non_dict_prior_returns_unchanged(tmp_path):
    bad = tmp_path / "graph.json"
    bad.write_text(json.dumps([1, 2, 3]))
    new_edges = [{"source": "a", "target": "b", "relation": "calls",
                  "confidence": "INFERRED", "source_file": "a.py"}]
    out = stamp_supersessions(new_edges=new_edges, prior_graph_path=bad, run_now=RUN_NOW)
    assert out == new_edges
