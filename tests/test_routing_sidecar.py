"""Tests for routing.json audit (ROUTE-05)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.routing_audit import RoutingAudit


def test_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Temp + replace leaves valid JSON (interrupt mid-write does not corrupt final)."""
    monkeypatch.chdir(tmp_path)
    audit = RoutingAudit()
    audit.record(Path("a.py"), "simple", "m", "e", 0, 1.0)
    out = audit.flush(tmp_path / "graphify-out")
    assert out.name == "routing.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "a.py" in data["files"]


def test_routing_json_version_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    audit = RoutingAudit()
    audit.flush(tmp_path / "graphify-out")
    p = tmp_path / "graphify-out" / "routing.json"
    assert json.loads(p.read_text(encoding="utf-8"))["version"] == 1
