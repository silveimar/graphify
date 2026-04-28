"""Integration tests for --output flag wiring in graphify CLI (Phase 27)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# D-12 backcompat: no vault, no --output
# ---------------------------------------------------------------------------

def test_run_no_vault_no_output_no_stderr_noise(tmp_path):
    (tmp_path / "sample.md").write_text("# Sample\nHello world\n")
    result = _graphify(["run", str(tmp_path), "--router"], cwd=tmp_path)
    assert "[graphify] vault detected" not in result.stderr


def test_obsidian_no_vault_no_output_no_stderr_noise(tmp_path):
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        '{"directed":false,"multigraph":false,"graph":{},"nodes":[],"links":[]}'
    )
    result = _graphify(
        ["--obsidian", "--graph", str(tmp_path / "graphify-out" / "graph.json")],
        cwd=tmp_path,
    )
    assert "[graphify] vault detected" not in result.stderr


# ---------------------------------------------------------------------------
# VAULT-08: vault detection emits stderr report
# ---------------------------------------------------------------------------

def test_run_in_vault_emits_detection_report(tmp_path):
    pytest.importorskip("yaml")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
        "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
    )
    result = _graphify(["run", "--router"], cwd=vault)
    assert "[graphify] vault detected at" in result.stderr
    assert "source=profile" in result.stderr


# ---------------------------------------------------------------------------
# D-05 / D-02: refusal when vault but no profile / no output block
# ---------------------------------------------------------------------------

def test_run_in_vault_no_profile_refuses(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    result = _graphify(["run", "--router"], cwd=vault)
    assert result.returncode != 0
    assert "no .graphify/profile.yaml found" in result.stderr


def test_run_in_vault_profile_no_output_block_refuses(tmp_path):
    pytest.importorskip("yaml")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text("naming:\n  convention: kebab-case\n")
    result = _graphify(["run", "--router"], cwd=vault)
    assert result.returncode != 0
    assert "no 'output:' block" in result.stderr


# ---------------------------------------------------------------------------
# VAULT-10: --output flag precedence + D-09 stderr line
# ---------------------------------------------------------------------------

def test_run_output_flag_overrides_profile_emits_d09_line(tmp_path):
    pytest.importorskip("yaml")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
        "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
    )
    custom = tmp_path / "elsewhere"
    result = _graphify(["run", "--output", str(custom), "--router"], cwd=vault)
    assert f"--output={custom} overrides profile output" in result.stderr
    assert result.stderr.count("overrides profile output") == 1


def test_run_output_flag_no_vault_silent_about_precedence(tmp_path):
    result = _graphify(["run", str(tmp_path), "--output", "myout", "--router"], cwd=tmp_path)
    assert "overrides profile output" not in result.stderr
    assert "[graphify] vault detected" not in result.stderr


# ---------------------------------------------------------------------------
# D-12 byte-identical: legacy --obsidian-dir without vault still honored
# ---------------------------------------------------------------------------

def test_obsidian_legacy_flag_unchanged_when_no_vault(tmp_path):
    (tmp_path / "graph.json").write_text(
        '{"directed":false,"multigraph":false,"graph":{},"nodes":[],"links":[]}'
    )
    custom = tmp_path / "my-obsidian-out"
    result = _graphify(
        ["--obsidian", "--graph", str(tmp_path / "graph.json"),
         "--obsidian-dir", str(custom), "--force"],
        cwd=tmp_path,
    )
    assert "[graphify] vault detected" not in result.stderr


# ---------------------------------------------------------------------------
# D-08: --output > --obsidian-dir precedence
# ---------------------------------------------------------------------------

def test_obsidian_output_flag_takes_precedence_over_obsidian_dir(tmp_path):
    pytest.importorskip("yaml")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
        "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
    )
    (vault / "graph.json").write_text(
        '{"directed":false,"multigraph":false,"graph":{},"nodes":[],"links":[]}'
    )
    custom = tmp_path / "winner"
    result = _graphify(
        ["--obsidian", "--graph", str(vault / "graph.json"),
         "--obsidian-dir", str(tmp_path / "loser"),
         "--output", str(custom), "--force"],
        cwd=vault,
    )
    assert f"--output={custom} overrides profile output" in result.stderr
    assert "loser" not in result.stderr.split("overrides")[0]
