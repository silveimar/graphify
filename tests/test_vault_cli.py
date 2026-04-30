"""Integration tests for Phase 41 vault CLI flags (VCLI-05)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_V18_PROFILE_OUT = (
    "taxonomy:\n"
    "  version: v1.8\n"
    "  root: Atlas/Sources/Graphify\n"
    "  folders:\n"
    "    moc: MOCs\n"
    "    thing: Things\n"
    "    statement: Statements\n"
    "    person: People\n"
    "    source: Sources\n"
    "    default: Things\n"
    "    unclassified: MOCs\n"
    "mapping:\n"
    "  min_community_size: 3\n"
    "output:\n"
    "  mode: vault-relative\n"
    "  path: GraphifyOut\n"
)


def _make_vault(parent: Path, name: str) -> Path:
    v = parent / name
    v.mkdir()
    (v / ".obsidian").mkdir()
    (v / ".graphify").mkdir()
    (v / ".graphify" / "profile.yaml").write_text(_V18_PROFILE_OUT)
    return v


def test_doctor_respects_graphify_vault_env(tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, "pinned")
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GRAPHIFY_VAULT": str(vault)}
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "doctor"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "vault-env" in r.stdout
    assert "notes_dir:" in r.stdout


def test_doctor_explicit_vault_shows_source(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, "vault")
    repo = tmp_path / "repo"
    repo.mkdir()
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "graphify",
            "--vault",
            str(vault),
            "doctor",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "source: vault-cli" in r.stdout


def test_vault_list_multi_non_tty_exit_2(tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    v1 = _make_vault(tmp_path / "a", "v1")
    v2 = _make_vault(tmp_path / "b", "v2")
    lst = tmp_path / "lst.txt"
    lst.write_text(f"{v1}\n{v2}\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault-list", str(lst), "doctor"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 2
    assert "Multiple vault roots" in r.stderr
