"""Tests for graphify/routing.py (Phase 12, ROUTE-01/02/06/10)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from graphify.routing import (
    CODE_SUFFIXES,
    Router,
    classify_file,
    load_routing_config,
    resolve_model,
    tier_rank,
)


def test_tier_order_deterministic() -> None:
    assert tier_rank("trivial") < tier_rank("simple") < tier_rank("complex") < tier_rank("vision")


def test_yaml_loads() -> None:
    cfg = load_routing_config()
    assert "tiers" in cfg
    assert "trivial" in cfg["tiers"]


def test_code_floor_bumps_trivial_to_simple(tmp_path: Path) -> None:
    """ROUTE-06: trivial-by-metrics Python still resolves to at least simple for code."""
    p = tmp_path / "tiny.py"
    p.write_text("x = 1\n", encoding="utf-8")
    cfg = load_routing_config()
    m = classify_file(p, thresholds=cfg.get("thresholds") or {})
    assert m.file_type == "code"
    assert m.suggested_tier == "trivial"
    r = resolve_model(m, "code", cfg)
    assert r.tier == "simple"


def test_yaml_override_changes_model_id(tmp_path: Path) -> None:
    """Alternative routing_models.yaml overrides tiers.simple.model_id."""
    y = tmp_path / "routing_models.yaml"
    y.write_text(
        textwrap.dedent(
            """
            tiers:
              trivial:
                model_id: model-A
                endpoint: https://a
              simple:
                model_id: model-OVERRIDE
                endpoint: https://b
              complex:
                model_id: model-C
                endpoint: https://c
            vision:
              model_id: ""
              endpoint: https://v
            thresholds:
              trivial_max_cc: 100
              simple_max_cc: 200
            """
        ).strip(),
        encoding="utf-8",
    )
    cfg = load_routing_config(y)
    p = tmp_path / "f.py"
    p.write_text("def a():\n    return 1\n" * 5, encoding="utf-8")
    m = classify_file(p, thresholds=cfg.get("thresholds") or {})
    r = resolve_model(m, "code", cfg)
    assert r.model_id == "model-OVERRIDE"


def test_router_classify_resolve() -> None:
    r = Router(load_routing_config())
    p = Path(__file__).resolve()
    m = r.classify(p)
    assert m.path == p
    out = r.resolve(p)
    assert out.model_id
    assert out.tier in ("simple", "complex", "trivial")


def test_grep_router_api() -> None:
    from graphify import routing as R

    src = Path(R.__file__).read_text(encoding="utf-8")
    assert "def classify_file" in src
    assert "def resolve_model" in src
    assert "class Router" in src


def test_code_suffixes_cover_extract_dispatch() -> None:
    assert ".py" in CODE_SUFFIXES
