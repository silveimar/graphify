"""Integration tests for --output flag wiring in graphify CLI (Phase 27)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess.

    Prepends the worktree root to PYTHONPATH so subprocesses pick up the
    in-worktree graphify/ package rather than the editable install (which
    points at the main repo checkout). Without this, parallel-executor
    worktrees can't validate their own __main__.py changes via subprocess.
    """
    full_env = os.environ.copy()
    # Worktree root = three parents up from this test file (tests/test_main_flags.py).
    worktree_root = Path(__file__).resolve().parent.parent
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
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


_V18_PROFILE_BASE = (
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
        _V18_PROFILE_BASE + "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
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
    (vault / ".graphify" / "profile.yaml").write_text(_V18_PROFILE_BASE)
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
        _V18_PROFILE_BASE + "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
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
        _V18_PROFILE_BASE + "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
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


# ---------------------------------------------------------------------------
# Phase 29 / VAULT-14 / VAULT-15: doctor subcommand wiring
# ---------------------------------------------------------------------------

_DOCTOR_VALID_PROFILE = (
    _V18_PROFILE_BASE +
    "output:\n"
    "  mode: vault-relative\n"
    "  path: Atlas/Generated\n"
)


def _make_doctor_vault(tmp_path: Path, *, profile_text: str | None) -> Path:
    """Mirror tests/test_doctor.py::_make_vault for CLI subprocess fixtures."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    (vault / ".graphify").mkdir()
    if profile_text is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_text)
    return vault


def test_doctor_clean_exit_zero(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_doctor_vault(tmp_path, profile_text=_DOCTOR_VALID_PROFILE)
    result = _graphify(["doctor"], cwd=vault)
    assert result.returncode == 0, (
        f"expected exit 0; got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    for section in (
        "Vault Detection",
        "Profile Validation",
        "Output Destination",
        "Ignore-List",
        "Recommended Fixes",
    ):
        assert section in result.stdout, f"missing section {section!r} in stdout"
    assert "No issues detected." in result.stdout


def test_doctor_misconfig_exit_one(tmp_path):
    pytest.importorskip("yaml")
    # Profile with invalid output.mode → resolve_output _refuse() → exit 1.
    bad = (
        _V18_PROFILE_BASE +
        "output:\n"
        "  mode: nonsense\n"
        "  path: Atlas/Generated\n"
    )
    vault = _make_doctor_vault(tmp_path, profile_text=bad)
    result = _graphify(["doctor"], cwd=vault)
    assert result.returncode == 1, (
        f"expected exit 1; got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "Recommended Fixes" in result.stdout
    assert "[graphify] FIX:" in result.stdout


def test_doctor_dry_run_flag(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_doctor_vault(tmp_path, profile_text=_DOCTOR_VALID_PROFILE)
    (vault / "alpha.py").write_text("def a(): return 1\n")

    def _snapshot(p: Path) -> set[Path]:
        return {q for q in p.rglob("*") if q.is_file()}

    before = _snapshot(tmp_path)
    result = _graphify(["doctor", "--dry-run"], cwd=vault)
    after = _snapshot(tmp_path)
    assert "Would ingest:" in result.stdout, (
        f"missing 'Would ingest:' in stdout\nstdout={result.stdout}"
    )
    assert "Would write notes to:" in result.stdout
    new_files = after - before
    assert new_files == set(), f"doctor --dry-run wrote files: {sorted(new_files)}"


def test_doctor_in_help(tmp_path):
    result = _graphify(["--help"], cwd=tmp_path)
    assert "doctor" in result.stdout
    assert "--dry-run" in result.stdout
