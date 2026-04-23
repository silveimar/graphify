"""CLI `graphify run` smoke tests (Phase 12)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_run_help_lists_router(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["graphify", "--help"])
    import graphify.__main__ as m

    m.main()
    out = capsys.readouterr().out
    assert "run" in out
    assert "router" in out.lower() or "--router" in out


def test_run_empty_dir_exit_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "run", "."])
    import graphify.__main__ as m

    m.main()
