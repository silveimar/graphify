"""VOPT-03 — `--explain-paths` top-level CLI flag.

Subprocess integration tests for the introspection flag. Each test runs
`python -m graphify --explain-paths` (and variants) and inspects stdout/stderr
plus filesystem side-effects.

Pure tests: tmp_path only, no network. Subprocess inherits the test runner's
Python so the in-tree graphify package is exercised.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


_PROFILE_YAML = (
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
    "  path: .\n"
    "folder_mapping:\n"
    "  thing: Atlas/Sources/Graphify/Things/\n"
)


def _run(*args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    environ = dict(os.environ)
    if env:
        environ.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=environ,
    )


def _make_vault_no_profile(tmp_path: Path, name: str = "vopt-vault") -> Path:
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


def _make_vault_with_profile(tmp_path: Path, name: str = "vopt-vault-prof") -> Path:
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(_PROFILE_YAML, encoding="utf-8")
    return vault


def _row(stdout: str, prefix: str) -> str:
    for line in stdout.split("\n"):
        if line.startswith(prefix):
            return line
    raise AssertionError(f"prefix {prefix!r} not found in stdout:\n{stdout}")


# -----------------------------------------------------------------------------
# Baseline: exit code, no pipeline run, 5-row contract
# -----------------------------------------------------------------------------


def test_explain_paths_exit_zero(tmp_path: Path) -> None:
    proc = _run("--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"


def test_explain_paths_no_pipeline_runs(tmp_path: Path) -> None:
    proc = _run("--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0
    assert not (tmp_path / "graphify-out").exists()
    assert not (tmp_path / ".graphify-out").exists()


def test_explain_paths_five_rows_present(tmp_path: Path) -> None:
    proc = _run("--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0
    for prefix in ("cwd:", "vault:", "profile:", "resolved out:", "resolution:"):
        _row(proc.stdout, prefix)


# -----------------------------------------------------------------------------
# Resolution-label cases
# -----------------------------------------------------------------------------


def test_explain_paths_reports_default_for_plain_dir(tmp_path: Path) -> None:
    proc = _run("--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0
    assert _row(proc.stdout, "resolution:").rstrip().endswith("default")


def test_explain_paths_reports_no_vault_for_plain_dir(tmp_path: Path) -> None:
    proc = _run("--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0
    vault_row = _row(proc.stdout, "vault:")
    assert "no" in vault_row


def test_explain_paths_reports_option_b(tmp_path: Path) -> None:
    vault = _make_vault_no_profile(tmp_path)
    proc = _run("--explain-paths", cwd=vault)
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    assert "option-b (silent reroute)" in _row(proc.stdout, "resolution:")
    assert "yes" in _row(proc.stdout, "vault:")
    assert "<none>" in _row(proc.stdout, "profile:")


def test_explain_paths_reports_profile(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    vault = _make_vault_with_profile(tmp_path)
    proc = _run("--explain-paths", cwd=vault)
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    assert _row(proc.stdout, "resolution:").rstrip().endswith("profile")


def test_explain_paths_stderr_quiet(tmp_path: Path) -> None:
    vault = _make_vault_no_profile(tmp_path)
    proc = _run("--explain-paths", cwd=vault)
    assert proc.returncode == 0
    assert proc.stderr.strip() == "", f"unexpected stderr: {proc.stderr!r}"


def test_explain_paths_resolved_out_is_absolute(tmp_path: Path) -> None:
    vault = _make_vault_no_profile(tmp_path)
    proc = _run("--explain-paths", cwd=vault)
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    row = _row(proc.stdout, "resolved out:")
    # "resolved out:  <abs path>"
    path_str = row.split(":", 1)[1].strip()
    p = Path(path_str)
    assert p.is_absolute(), f"not absolute: {p}"
    assert str(p).endswith(str(Path(".graphify-out") / "obsidian")), p


# -----------------------------------------------------------------------------
# W5 — preemption when combined with subcommand
# -----------------------------------------------------------------------------


def test_explain_paths_preempts_run_subcommand(tmp_path: Path) -> None:
    vault = _make_vault_no_profile(tmp_path)
    (vault / "doc.md").write_text("# x", encoding="utf-8")
    proc = _run(
        "run", "--explain-paths", "--input", str(vault / "doc.md"), cwd=vault
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert not (vault / "graphify-out").exists()
    assert not (vault / ".graphify-out").exists()
    _row(proc.stdout, "resolution:")


# -----------------------------------------------------------------------------
# W4 — mandatory vault-pin support
# -----------------------------------------------------------------------------


def test_explain_paths_honors_vault_cli_pin(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    pinned = _make_vault_with_profile(tmp_path, name="pinned")
    proc = _run("--vault", str(pinned), "--explain-paths", cwd=tmp_path)
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    assert _row(proc.stdout, "resolution:").rstrip().endswith("profile")
    out_row = _row(proc.stdout, "resolved out:")
    assert str(pinned) in out_row, out_row


def test_explain_paths_honors_graphify_vault_env_pin(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    pinned = _make_vault_with_profile(tmp_path, name="pinned")
    proc = _run(
        "--explain-paths",
        cwd=tmp_path,
        env={"GRAPHIFY_VAULT": str(pinned)},
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    assert _row(proc.stdout, "resolution:").rstrip().endswith("profile")
