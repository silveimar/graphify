"""Unit + integration tests for VAUX-01 parity helper (Phase 58)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from graphify.doctor import run_doctor
from graphify.output import ResolvedOutput, resolve_execution_paths, resolve_vault_for_parity


# ---------------------------------------------------------------------------
# Test helpers (replicated from tests/test_doctor.py — D-08 forbids cross-import)
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path, *, profile_text: str | None = None) -> Path:
    """Create a synthetic Obsidian vault under tmp_path/vault.

    - .obsidian/  marks it as a vault (D-04)
    - .git/       halts _load_graphifyignore walk-up
    - .graphify/  for profile.yaml when profile_text is provided
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    (vault / ".graphify").mkdir()
    if profile_text is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_text)
    return vault


_VALID_PROFILE = (
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
    "  path: Atlas/Generated\n"
)


# ---------------------------------------------------------------------------
# VAUX-01 parity tests
# ---------------------------------------------------------------------------

def test_parity_helper_returns_dict_with_four_dimensions(tmp_path):
    """VAUX-01: resolve_vault_for_parity returns dict with the four parity dimensions."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    parity = resolve_vault_for_parity(tmp_path, explicit_vault=vault)
    assert set(parity.keys()) == {"vault_path", "source", "profile_path", "profile_mode", "warnings"}
    assert parity["vault_path"] == vault.resolve()
    assert parity["source"] == "vault-cli"
    assert parity["profile_mode"] == "vault-relative"
    assert isinstance(parity["warnings"], list)


def test_parity_vault_cli_matches_doctor(tmp_path):
    """VAUX-01: resolve_vault_for_parity and run_doctor agree on vault_path + source."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    parity = resolve_vault_for_parity(tmp_path, explicit_vault=vault)
    # Build the same ResolvedOutput and ask doctor to validate it
    resolved = ResolvedOutput(
        True,
        parity["vault_path"],
        parity["vault_path"] / "Atlas" / "Generated",
        parity["vault_path"].parent / "graphify-out",
        parity["source"],
        (),
    )
    report = run_doctor(tmp_path, resolved_output=resolved)
    assert report.resolved_output is not None
    assert report.resolved_output.vault_path == parity["vault_path"]
    assert report.resolved_output.source == parity["source"]


def test_parity_env_var_resolution(tmp_path):
    """VAUX-01: parity helper reflects env-precedence label when env_vault is provided."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    parity = resolve_vault_for_parity(tmp_path, env_vault=str(vault))
    assert parity["vault_path"] == vault.resolve()
    assert parity["source"] == "vault-env"


def test_parity_no_vault_returns_none(tmp_path):
    """VAUX-01: with no vault resolution, vault_path is None and source reflects default."""
    # tmp_path has no .obsidian/ — triggers CWD-fallback default resolution
    cwd_no_vault = tmp_path / "not_a_vault"
    cwd_no_vault.mkdir()
    parity = resolve_vault_for_parity(cwd_no_vault)
    assert parity["vault_path"] is None
    assert parity["source"] == "default"
    assert isinstance(parity["warnings"], list)


def test_parity_helper_does_not_duplicate_resolution(tmp_path):
    """VAUX-01: helper produces same vault_path as direct resolve_execution_paths call."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    parity = resolve_vault_for_parity(tmp_path, explicit_vault=vault)
    # Direct call for comparison (suppress stderr noise)
    import contextlib, io
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        direct = resolve_execution_paths(tmp_path, explicit_vault=vault)
    assert parity["vault_path"] == direct.vault_path
    assert parity["source"] == direct.source


# ---------------------------------------------------------------------------
# VAUX-02 error format tests
# ---------------------------------------------------------------------------

def test_unknown_vault_nonexistent_path_error(tmp_path):
    """VAUX-02: --vault /nonexistent emits [graphify] error: + hint: and exits non-zero."""
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault", str(tmp_path / "no-such-dir"), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert "[graphify] error:" in r.stderr
    assert "  hint:" in r.stderr


def test_unknown_vault_no_obsidian_marker_error(tmp_path):
    """VAUX-02: --vault <dir-without-.obsidian> emits error+hint and mentions .obsidian."""
    bare_dir = tmp_path / "bare"
    bare_dir.mkdir()
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault", str(bare_dir), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert "[graphify] error:" in r.stderr
    assert "  hint:" in r.stderr
    assert ".obsidian" in r.stderr


def test_ambiguous_vault_list_exit2(tmp_path):
    """VAUX-02: vault-list with two valid vaults + non-TTY → exit 2 + hint line."""
    pytest.importorskip("yaml")
    # Create two distinct vaults under different subdirectories
    v1 = _make_vault(tmp_path / "a")
    v2 = _make_vault(tmp_path / "b")
    lst = tmp_path / "vaults.txt"
    lst.write_text(f"{v1}\n{v2}\n")
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault-list", str(lst), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 2
    assert "  hint:" in r.stderr


def test_global_local_override_warning_preserved(tmp_path):
    """VAUX-02/D-09: global --vault + per-command --vault emits the existing override warning (no behavior change)."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    r = subprocess.run(
        [
            sys.executable, "-m", "graphify",
            "--vault", str(vault),   # global pin
            "doctor",
            "--vault", str(vault),   # per-command pin (same path)
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Override is a warning, not an error — exit 0
    assert r.returncode == 0
    assert "[graphify] command --vault / --vault-list overrides global pin" in r.stderr


def test_dry_run_mismatch_uses_parity_helper(tmp_path):
    """VAUX-02: dry-run doctor output and parity helper agree on vault_path."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    # Run doctor via CLI (subprocess) and capture its stdout
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault", str(vault), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    # In-process parity helper must agree on vault_path
    parity = resolve_vault_for_parity(tmp_path, explicit_vault=vault)
    assert parity["vault_path"] == vault.resolve()
    assert parity["source"] == "vault-cli"
    # Doctor stdout must reference the vault path (parity lock)
    assert str(vault.resolve()) in r.stdout or str(vault) in r.stdout
