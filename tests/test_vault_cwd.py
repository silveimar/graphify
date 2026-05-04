"""Phase 59 — VCWD-01..05 coverage. See .planning/phases/59-vault-cwd-aware-cli-default/59-VALIDATION.md"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_partial_vault(parent: Path, *, with_profile: bool) -> Path:
    """Create an Obsidian vault under `parent`. If with_profile, also write
    .graphify/profile.yaml so VCWD-02 auto-adopt path applies."""
    vault = parent / "vault"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    if with_profile:
        gdir = vault / ".graphify"
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "profile.yaml").write_text(
            "version: 1\nframework: ideaverse\nfolder_map: {}\n",
            encoding="utf-8",
        )
    return vault


def _make_no_vault(parent: Path) -> Path:
    """Create a regular directory with NO .obsidian/ (for VCWD-05 n/a outcome)."""
    p = parent / "not_a_vault"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _graphify(*args: str, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Subprocess runner mirroring tests/test_e2e_integration.py:_graphify.
    ALWAYS passes cwd explicitly (per RESEARCH Pitfall 3 — never inherit CWD)."""
    cmd = [sys.executable, "-m", "graphify", *args]
    base_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, env=base_env, capture_output=True, text=True, timeout=60,
    )


# Placeholder skeleton tests — RED phase for Plan 01 only.
# Plans 02..05 add their own RED tests in this file.

GATED_COMMANDS = [
    "run", "update-vault", "enrich", "vault-promote", "import-harness",
    "save-result", "snapshot", "approve", "elicit", "harness",
    # Note: --obsidian, --diagram-seeds, --init-diagram-templates, --dedup are
    # flag-style gated paths exercised via test_gate_runs_for_each_gated_cmd.
]

READONLY_COMMANDS = [
    "query", "doctor", "install", "hook", "capability", "benchmark",
]


def test_gate_runs_for_each_gated_cmd(tmp_path):
    """VCWD-01: gated commands invoke the gate from a profile-less vault CWD,
    yielding exit 2 with two-line stderr (gate refuses)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    # Include flag-style gated commands alongside subcommand-style ones.
    all_gated = list(GATED_COMMANDS) + [
        "--obsidian", "--diagram-seeds", "--init-diagram-templates", "--dedup",
    ]
    failures = []
    for cmd in all_gated:
        # Pass --help so command never starts real work; gate runs BEFORE help-parsing
        # because gate is inserted at the TOP of each dispatch branch, before argparse.
        # If the gate is wired correctly, exit will be 2 with 'refusing to write'.
        # If gate is missing for a command, exit will be 0 (help printed) or non-2.
        proc = _graphify(cmd, "--help", cwd=str(vault))
        if proc.returncode != 2:
            failures.append((cmd, proc.returncode, proc.stderr[:200]))
        elif "refusing to write into Obsidian vault" not in proc.stderr:
            failures.append((cmd, "missing-refusal-msg", proc.stderr[:200]))
    assert not failures, f"Gate did not fire for: {failures}"


def test_gate_skipped_for_readonly_cmds(tmp_path):
    """VCWD-01: read-only commands MUST NOT invoke the gate."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    for cmd in READONLY_COMMANDS:
        proc = _graphify(cmd, "--help", cwd=str(vault))
        # Help should succeed (exit 0); definitely no two-line refusal.
        assert "refusing to write into Obsidian vault" not in proc.stderr, (
            f"Gate fired for read-only cmd {cmd!r}: {proc.stderr[:200]}"
        )
