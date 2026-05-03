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
