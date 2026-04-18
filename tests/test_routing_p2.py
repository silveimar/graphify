"""P2 routing tests: cost ceiling, canary, vision skip (ROUTE-08/09/10)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from graphify.routing import Router, classify_file, load_routing_config, resolve_model
from graphify.routing_canary import emit_canary_warning_if_needed
from graphify.routing_cost import CostCeilingError, enforce_cost_ceiling


def test_cost_ceiling_aborts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAPHIFY_COST_CEILING", "1")
    cfg = load_routing_config()
    router = Router(cfg)
    p = tmp_path / "big.py"
    p.write_bytes(b"x" * 10_000)
    with pytest.raises(CostCeilingError):
        enforce_cost_ceiling([p], router)


def test_canary_warns(capsys: pytest.CaptureFixture[str]) -> None:
    emit_canary_warning_if_needed(cheap_edges=10, expensive_edges=3)
    err = capsys.readouterr().err
    assert "routing quality regressed" in err


def test_image_skip_no_vision_model(tmp_path: Path) -> None:
    cfg = load_routing_config()
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    m = classify_file(img)
    assert m.file_type == "image"
    r = resolve_model(m, "image", cfg)
    assert r.skip_extraction is True
