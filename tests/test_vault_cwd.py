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


# ---------------------------------------------------------------------------
# Plan 02 — VCWD-02: auto-adopt routing parity + single-line notice
# ---------------------------------------------------------------------------


def _make_profile_vault(parent: Path) -> Path:
    """Create a fully valid Obsidian vault with .graphify/profile.yaml that
    passes v1.8 schema validation (has taxonomy + mapping.min_community_size)
    and includes a vault-relative output block so resolve_output() succeeds.
    Used by VCWD-02 tests only."""
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
    # Create the notes dir so validate_vault_path can resolve it inside the vault.
    (vault / "notes").mkdir(parents=True, exist_ok=True)
    return vault


def test_auto_adopt_notice_emitted_once(tmp_path):
    """VCWD-02: auto-adopt path emits the notice EXACTLY once per process.

    Uses `run --help`: gate fires BEFORE manual arg-parsing in the run branch,
    so the auto-adopt notice lands in stderr before the branch tries to handle
    --help (which it treats as an unknown flag and exits 2). Exit code is
    irrelevant; we only inspect stderr for the notice text.
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    proc = _graphify("run", "--help", cwd=str(vault))
    notice = "[graphify] auto-adopted vault at"
    occurrences = proc.stderr.count(notice)
    assert occurrences == 1, (
        f"expected exactly 1 auto-adopt notice, got {occurrences}\nstderr:\n{proc.stderr}"
    )
    assert "(profile: .graphify/profile.yaml)" in proc.stderr, (
        f"notice missing profile suffix\nstderr:\n{proc.stderr}"
    )


def test_auto_adopt_matches_explicit_vault(tmp_path):
    """VCWD-02: auto-adopt (no flags) routes artifacts_dir identically to --vault $CWD.

    Uses `elicit --dry-run --demo` which prints JSON with artifacts_dir to stdout
    and exits 0 without real work, exercising _resolve_cli_paths in the elicit branch.
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)

    # Run 1: auto-adopt path (no routing flags)
    proc_auto = _graphify("elicit", "--dry-run", "--demo", cwd=str(vault))
    # Run 2: explicit --vault $CWD (should produce identical resolution)
    proc_explicit = _graphify(
        "--vault", str(vault), "elicit", "--dry-run", "--demo", cwd=str(vault)
    )

    import json as _json

    def _artifacts(proc: subprocess.CompletedProcess) -> str | None:
        try:
            data = _json.loads(proc.stdout)
            return data.get("artifacts_dir")
        except Exception:
            return None

    auto_path = _artifacts(proc_auto)
    explicit_path = _artifacts(proc_explicit)
    assert auto_path is not None, (
        f"auto-adopt elicit --dry-run produced no artifacts_dir\n"
        f"stdout: {proc_auto.stdout}\nstderr: {proc_auto.stderr}"
    )
    assert explicit_path is not None, (
        f"explicit --vault elicit --dry-run produced no artifacts_dir\n"
        f"stdout: {proc_explicit.stdout}\nstderr: {proc_explicit.stderr}"
    )
    assert auto_path == explicit_path, (
        f"auto-adopt {auto_path!r} != explicit-vault {explicit_path!r}"
    )


def test_explicit_vault_no_auto_adopt_notice(tmp_path):
    """VCWD-02: passing --vault $CWD explicitly must NOT trigger the auto-adopt notice."""
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    proc = _graphify(
        "--vault", str(vault), "elicit", "--dry-run", "--demo", cwd=str(vault)
    )
    assert "auto-adopted vault" not in proc.stderr, (
        f"explicit --vault must not trigger auto-adopt notice\nstderr:\n{proc.stderr}"
    )


# ---------------------------------------------------------------------------
# Plan 03 — VCWD-03: verbatim refusal text + exit code 2
# ---------------------------------------------------------------------------

REFUSAL_MSG_PREFIX = "[graphify] error: refusing to write into Obsidian vault at "
REFUSAL_MSG_SUFFIX = " — no .graphify/profile.yaml found"
REFUSAL_HINT_LINE = "  hint: create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override"


def test_refusal_exit_code_and_format(tmp_path):
    """VCWD-03: profile-less vault CWD → exit 2 + two-line stderr."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}\nstderr:\n{proc.stderr}"
    # Two-line shape: error line + hint line. Allow trailing newline; reject extra non-empty lines.
    err_lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    # The two VCWD-03 lines must appear consecutively.
    error_idx = next((i for i, ln in enumerate(err_lines) if ln.startswith(REFUSAL_MSG_PREFIX)), None)
    assert error_idx is not None, f"missing error line:\n{proc.stderr}"
    assert err_lines[error_idx + 1] == REFUSAL_HINT_LINE, (
        f"hint line mismatch.\n"
        f"  expected: {REFUSAL_HINT_LINE!r}\n"
        f"  actual:   {err_lines[error_idx + 1]!r}\n"
        f"full stderr:\n{proc.stderr}"
    )


def test_refusal_message_text(tmp_path):
    """VCWD-03: error line MUST match CONTEXT D-04 verbatim (prefix + suffix shape)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    error_line = next(
        (ln for ln in proc.stderr.splitlines() if ln.startswith(REFUSAL_MSG_PREFIX)),
        None,
    )
    assert error_line is not None
    assert error_line.endswith(REFUSAL_MSG_SUFFIX), f"suffix mismatch: {error_line!r}"
    # Path between prefix and suffix is the resolved cwd. It MUST be absolute.
    cwd_in_msg = error_line[len(REFUSAL_MSG_PREFIX):-len(REFUSAL_MSG_SUFFIX)]
    assert Path(cwd_in_msg).is_absolute(), f"cwd in msg must be absolute: {cwd_in_msg!r}"
    # Sanity check: the cwd in the message resolves to our test vault.
    assert Path(cwd_in_msg).resolve() == vault.resolve(), (
        f"cwd in msg {cwd_in_msg!r} should equal {vault!r}"
    )


# ---------------------------------------------------------------------------
# Plan 04 — VCWD-04: --write-into-vault flag plumbing + precedence
# ---------------------------------------------------------------------------


def test_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: per-command --write-into-vault suppresses VCWD-03 refusal."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", "--write-into-vault", "--help", cwd=str(vault))
    # No exit-2 refusal: the flag suppresses it. exit code 0 (help) or another
    # non-2 value is acceptable; the assertion is that VCWD-03 stderr does NOT appear.
    assert "refusing to write into Obsidian vault" not in proc.stderr, (
        f"--write-into-vault should suppress refusal; got:\n{proc.stderr}"
    )
    assert proc.returncode != 2, f"unexpected exit 2 with --write-into-vault: stderr=\n{proc.stderr}"


def test_global_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: leading global --write-into-vault (before subcommand) suppresses refusal."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("--write-into-vault", "run", "--help", cwd=str(vault))
    assert "refusing to write into Obsidian vault" not in proc.stderr, (
        f"global --write-into-vault should suppress refusal; got:\n{proc.stderr}"
    )
    assert proc.returncode != 2


def test_write_into_vault_silent_precedence(tmp_path):
    """VCWD-04: combined with --vault / --output, explicit wins silently (no warning)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    out_dir = tmp_path / "outside"
    out_dir.mkdir()
    proc = _graphify(
        "--vault", str(vault), "--write-into-vault",
        "run", "--help",
        cwd=str(vault),
    )
    # Silent precedence: NO warning about flag conflict / no-op redundancy.
    forbidden_phrases = [
        "ignored", "ignoring", "redundant", "no-op", "warning:",
        "--write-into-vault has no effect",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in proc.stderr.lower(), (
            f"silent precedence violated: stderr contains {phrase!r}\n{proc.stderr}"
        )


def test_write_into_vault_yields_to_profile(tmp_path):
    """VCWD-04: --write-into-vault does NOT suppress VCWD-02 auto-adopt (profile wins)."""
    pytest.importorskip("yaml")
    vault = _make_partial_vault(tmp_path, with_profile=True)
    proc = _graphify("--write-into-vault", "run", "--help", cwd=str(vault))
    # Profile present: auto-adopt path takes priority. Notice still appears.
    assert "[graphify] auto-adopted vault at" in proc.stderr, (
        f"--write-into-vault must NOT suppress auto-adopt notice; stderr:\n{proc.stderr}"
    )


# ---------------------------------------------------------------------------
# Plan 05 — VCWD-05: graphify doctor [vault-cwd] section + parity contract
# ---------------------------------------------------------------------------


def _doctor_section_lines(stdout: str) -> list[str]:
    """Extract just the [vault-cwd] lines from doctor output."""
    return [ln for ln in stdout.splitlines() if ln.startswith("[vault-cwd]")]


def test_doctor_vault_cwd_section_always_shown(tmp_path):
    """VCWD-05: doctor [vault-cwd] section appears for non-vault CWD too (n/a outcome)."""
    plain = _make_no_vault(tmp_path)
    proc = _graphify("doctor", cwd=str(plain))
    assert proc.returncode == 0, f"doctor failed: {proc.stderr}"
    section_lines = _doctor_section_lines(proc.stdout)
    assert section_lines, f"missing [vault-cwd] section in doctor output:\n{proc.stdout}"
    assert any("n/a" in ln for ln in section_lines), (
        f"non-vault CWD should yield n/a outcome; got: {section_lines}"
    )


def test_doctor_three_outcomes(tmp_path):
    """VCWD-05: all three outcomes (auto-adopt / refuse / n/a) reachable."""
    pytest.importorskip("yaml")

    # n/a
    plain = _make_no_vault(tmp_path / "noVault")
    p1 = _graphify("doctor", cwd=str(plain))
    # auto-adopt
    full = _make_partial_vault(tmp_path / "fullVault", with_profile=True)
    p2 = _graphify("doctor", cwd=str(full))
    # refuse
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    p3 = _graphify("doctor", cwd=str(bare))

    s1 = " ".join(_doctor_section_lines(p1.stdout))
    s2 = " ".join(_doctor_section_lines(p2.stdout))
    s3 = " ".join(_doctor_section_lines(p3.stdout))
    assert "n/a" in s1, f"plain dir → n/a expected; got: {s1!r}"
    assert "auto-adopt" in s2, f"vault+profile → auto-adopt expected; got: {s2!r}"
    assert "refuse" in s3, f"vault-no-profile → refuse expected; got: {s3!r}"


def test_doctor_runtime_parity(tmp_path):
    """VCWD-05 parity contract: doctor's prediction matches runtime gate behavior."""
    # refuse case
    bare = _make_partial_vault(tmp_path, with_profile=False)
    doctor = _graphify("doctor", cwd=str(bare))
    runtime = _graphify("run", cwd=str(bare))
    doc_section = " ".join(_doctor_section_lines(doctor.stdout))
    assert "refuse" in doc_section
    assert runtime.returncode == 2 and "refusing to write" in runtime.stderr, (
        f"doctor predicted refuse; runtime should refuse. runtime stderr:\n{runtime.stderr}"
    )


def test_env_pin_disables_gate(tmp_path):
    """Cross-cutting: GRAPHIFY_VAULT env pin treated as explicit routing — gate returns n/a."""
    pytest.importorskip("yaml")
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    pin_target = _make_partial_vault(tmp_path / "pinVault", with_profile=True)
    proc = _graphify(
        "run", "--help",
        cwd=str(bare),
        env={"GRAPHIFY_VAULT": str(pin_target)},
    )
    assert "refusing to write" not in proc.stderr, (
        f"GRAPHIFY_VAULT pin should suppress VCWD-03; got:\n{proc.stderr}"
    )
    # Doctor parity: with env pin set, [vault-cwd] should report n/a (explicit route wins).
    proc_doc = _graphify(
        "doctor",
        cwd=str(bare),
        env={"GRAPHIFY_VAULT": str(pin_target)},
    )
    section = " ".join(_doctor_section_lines(proc_doc.stdout))
    assert "n/a" in section, f"doctor parity broken with env pin: {section!r}"


def test_vault_list_disables_gate(tmp_path):
    """Cross-cutting: --vault-list file treated as explicit routing — gate returns n/a."""
    pytest.importorskip("yaml")
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    pin_target = _make_partial_vault(tmp_path / "pinVault", with_profile=True)
    list_file = tmp_path / "vaults.txt"
    list_file.write_text(f"{pin_target}\n", encoding="utf-8")
    proc = _graphify(
        "--vault-list", str(list_file), "run", "--help",
        cwd=str(bare),
    )
    assert "refusing to write" not in proc.stderr, (
        f"--vault-list should suppress VCWD-03; got:\n{proc.stderr}"
    )
