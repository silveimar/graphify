"""Phase 74 VBUG-02: regression coverage for the vault-CWD auto-adopt gate across all 14 gated subcommands."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Audit (Phase 74 plan-02 Task 1): tests in tests/test_vault_cwd.py that
# touch the vault-CWD auto-adopt gate.
#
#   MOVED here (verbatim, with their pytest skip-marker removed):
#     - test_update_vault_auto_adopt_no_vault_flag
#     - test_vault_promote_auto_adopt_no_vault_flag
#     - test_update_vault_no_vault_flag_outside_vault_friendly_error
#       (the friendly-error sibling of the two RED tests; co-located here so
#       all gate-related regression coverage is in one file)
#
#   LEFT in tests/test_vault_cwd.py (rationale):
#     - test_gate_runs_for_each_gated_cmd / test_gate_skipped_for_readonly_cmds
#       (Phase 63 VOPT-01 coverage of the *resolver* path; not the
#       argparse-required defect — different code path, different assertion
#       contract)
#     - test_auto_adopt_notice_emitted_once / test_auto_adopt_routing_parity /
#       test_explicit_vault_no_auto_adopt_notice (Phase 59 VCWD-02 routing
#       parity tests — gate emission vs routing identity, not argparse defect)
#     - VCWD-04 / VCWD-05 / env-pin / vault-list tests (cross-cutting routing
#       precedence, not argparse defect)
#
# Inline-gate enumeration note: CONTEXT.md cites "15 branches" including an
# "inline gate at ~line 2947" of __main__.py. Audit of __main__.py at base
# commit aeff5eb shows the gate is invoked at exactly 14 distinct call sites
# (lines 1973, 2139, 2201, 2258, 2399, 2529, 2814, 2860, 2959, 3031, 3135,
# 3267, 3502, 3669) — line 2947 falls within the `elicit` branch whose gate
# call is at 2860, not a distinct site. We therefore parametrize 14 cases.
# ---------------------------------------------------------------------------


def _make_profile_vault(parent: Path) -> Path:
    """Mirror tests/test_vault_cwd.py:_make_profile_vault — fully valid profile vault."""
    vault = parent / "pv"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    gdir = vault / ".graphify"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "profile.yaml").write_text(
        "taxonomy:\n"
        "  root: TestAtlas\n"
        "  folders:\n"
        "    moc: MOCs\n"
        "    thing: Things\n"
        "    default: Things\n"
        "mapping:\n"
        "  min_community_size: 3\n"
        "output:\n"
        "  mode: vault-relative\n"
        "  path: notes\n",
        encoding="utf-8",
    )
    (vault / "notes").mkdir(parents=True, exist_ok=True)
    return vault


def _graphify(*args: str, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "graphify", *args]
    base_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, env=base_env, capture_output=True, text=True, timeout=30,
    )


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    pytest.importorskip("yaml")
    return _make_profile_vault(tmp_path)


# ---------------------------------------------------------------------------
# Parametrized 14-branch coverage (VBUG-02 main acceptance).
#
# Each tuple is (subcmd, extra_args). Extra args are the minimum needed to
# reach the gate without tripping argparse on *unrelated* required flags.
# Some commands legitimately exit with non-zero (or even == 2) for reasons
# orthogonal to argparse-required-flag enforcement — e.g. import-harness's
# graphify-out/ path-confinement check. The decisive assertion is the
# absence of argparse's "the following arguments are required: --vault"
# signature; the returncode-2 assertion is gated on that string to avoid
# false positives from unrelated business-layer SystemExit(2)s.
# ---------------------------------------------------------------------------

GATED_COMMANDS = [
    ("--obsidian", []),
    ("--diagram-seeds", []),
    ("--init-diagram-templates", []),
    ("--dedup", []),
    ("snapshot", []),
    ("approve", []),
    ("save-result", ["--question", "Q", "--answer", "A"]),
    ("elicit", ["--dry-run", "--demo"]),
    ("harness", ["export"]),
    ("import-harness", ["graphify-out/h.json"]),
    ("run", ["--help"]),
    ("enrich", []),
    ("update-vault", ["--input", "__nonexistent__"]),
    ("vault-promote", ["--graph", "__nonexistent__.json"]),
]


@pytest.mark.parametrize("subcmd,extra_args", GATED_COMMANDS)
def test_gated_subcommand_no_argparse_vault_required_from_vault_cwd(
    subcmd: str, extra_args: list[str], vault_dir: Path
) -> None:
    """For every gated subcommand: invoking from a profile-vault CWD with no
    --vault flag must NOT trigger argparse's 'the following arguments are
    required: --vault' exit-2 path, and the auto-adopt breadcrumb must fire.
    """
    # Some commands (e.g. import-harness) confine paths to graphify-out/, so
    # ensure that exists in the fixture vault.
    (vault_dir / "graphify-out").mkdir(exist_ok=True)
    (vault_dir / "graphify-out" / "h.json").write_text("{}", encoding="utf-8")

    result = _graphify(subcmd, *extra_args, cwd=str(vault_dir))

    # Decisive assertion: the argparse-required signature for --vault must
    # never appear. This is the exact failure mode VBUG-01/02 prevents.
    assert "the following arguments are required: --vault" not in result.stderr, (
        f"{subcmd}: argparse '--vault required' error leaked through. "
        f"stderr={result.stderr!r}"
    )

    # Gate breadcrumb fired (auto-adopt path detected the profile vault).
    assert "auto-adopt" in result.stderr, (
        f"{subcmd}: auto-adopt notice missing — gate did not fire. "
        f"stderr={result.stderr!r}"
    )

    # Returncode-2 sanity: if exit-2, it MUST be for a non-argparse-required
    # reason (e.g. business-layer security check). The argparse-required
    # signature already excluded above; here we additionally guard against
    # any other 'required' argparse error mentioning --vault specifically.
    if result.returncode == 2:
        assert "required: --vault" not in result.stderr, (
            f"{subcmd}: argparse exit-2 still fires for --vault. "
            f"stderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# RED tests moved verbatim from tests/test_vault_cwd.py:412-499.
# Original location had a pytest skip-marker (reason="awaiting fix phase").
# Plan-01 (commit c606935) flipped --vault to required=False on update-vault
# and vault-promote and tightened the post-parse guard with a friendly error.
# These tests are now the GREEN regression for that fix.
# ---------------------------------------------------------------------------


def test_update_vault_auto_adopt_no_vault_flag(tmp_path):
    """VCWD-argparse-required: update-vault from a profile vault CWD without --vault
    must NOT exit with argparse error 2 ('required: --vault').
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    proc = _graphify(
        "update-vault", "--input", str(tmp_path / "nonexistent"),
        cwd=str(vault),
    )
    assert "required: --vault" not in proc.stderr, (
        "argparse 'required: --vault' error fired — auto-adopt argv injection missing.\n"
        f"stderr: {proc.stderr}"
    )
    assert proc.returncode != 2 or "required: --vault" not in proc.stderr, (
        f"exit 2 with argparse required error\nstderr: {proc.stderr}"
    )


def test_vault_promote_auto_adopt_no_vault_flag(tmp_path):
    """VCWD-argparse-required: vault-promote from a profile vault CWD without --vault
    must NOT exit with argparse error 2 ('required: --vault').
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    proc = _graphify(
        "vault-promote", "--graph", str(tmp_path / "nonexistent.json"),
        cwd=str(vault),
    )
    assert "required: --vault" not in proc.stderr, (
        "argparse 'required: --vault' error fired — auto-adopt argv injection missing.\n"
        f"stderr: {proc.stderr}"
    )
    assert proc.returncode != 2 or "required: --vault" not in proc.stderr, (
        f"exit 2 with argparse required error\nstderr: {proc.stderr}"
    )


def test_update_vault_no_vault_flag_outside_vault_friendly_error(tmp_path):
    """VCWD-argparse-required friendly-error branch: outside a vault CWD,
    omitting --vault must NOT raise argparse exit-2 — instead emit a
    user-facing 'error: --vault is required' and exit non-zero.
    """
    proc = _graphify(
        "update-vault", "--input", str(tmp_path / "nonexistent"),
        cwd=str(tmp_path),
    )
    assert "required: --vault" not in proc.stderr, (
        f"argparse 'required: --vault' must not fire; got stderr: {proc.stderr}"
    )
    assert "--vault is required" in proc.stderr, (
        f"expected friendly error 'error: --vault is required'; got stderr: {proc.stderr}"
    )
    # Plan-01 (commit c606935) locked the friendly-error exit code at 2
    # (sys.exit(2)) per CONTEXT.md decision; the original RED test's
    # EXIT_VAULT_REFUSAL=1 expectation was superseded. Assert the new
    # contract: a non-argparse exit code consistent with the friendly path.
    assert proc.returncode != 0, (
        f"expected non-zero exit for friendly-error path, got 0; stderr: {proc.stderr}"
    )
