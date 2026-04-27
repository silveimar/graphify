"""Tests for routing.json atomic read-merge-write (MANIFEST-09/11)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.routing_audit import RoutingAudit


def test_subpath_isolation_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-11: two sequential flush() calls with disjoint file sets preserve union."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "graphify-out"

    # Subpath A run
    audit_a = RoutingAudit()
    audit_a.record(Path("sub_a/file1.py"), "simple", "haiku", "ep", 100, 10.0)
    audit_a.flush(out)

    # Subpath B run — different RoutingAudit instance, disjoint file set
    audit_b = RoutingAudit()
    audit_b.record(Path("sub_b/file2.py"), "complex", "sonnet", "ep2", 500, 50.0)
    audit_b.flush(out)

    data = json.loads((out / "routing.json").read_text(encoding="utf-8"))
    assert "sub_a/file1.py" in data["files"], "sub_a row must survive sub_b flush"
    assert "sub_b/file2.py" in data["files"], "sub_b row must be present"
