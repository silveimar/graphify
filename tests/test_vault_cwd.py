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
    """Phase 63 VOPT-01: gated commands from a profile-less vault CWD now silently
    reroute via Option B (no exit-2 refusal). Each gated branch must emit the
    `[graphify] info: vault CWD without .graphify/profile.yaml` breadcrumb."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    # Include flag-style gated commands alongside subcommand-style ones.
    all_gated = list(GATED_COMMANDS) + [
        "--obsidian", "--diagram-seeds", "--init-diagram-templates", "--dedup",
    ]
    failures = []
    for cmd in all_gated:
        # Pass --help so command never starts real work. After Option B harmonization
        # the gate downgrades to "option-b" rather than raising EXIT_VAULT_GATE,
        # so every gated branch should reach the resolver and emit the info
        # breadcrumb (exit code is irrelevant — usually 0 for --help, or 2 for
        # branches that treat --help as unknown — never the gate's exit-2).
        proc = _graphify(cmd, "--help", cwd=str(vault))
        if "refusing to write into Obsidian vault" in proc.stderr:
            failures.append((cmd, "still-refuses", proc.stderr[:200]))
        elif "info: vault CWD without .graphify/profile.yaml" not in proc.stderr:
            failures.append((cmd, "missing-info-breadcrumb", proc.stderr[:200]))
    assert not failures, f"Option B breadcrumb missing for: {failures}"


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
    notice = "[graphify] info: auto-adopted vault at"
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


OPTION_B_INFO_PREFIX = "[graphify] info: vault CWD without .graphify/profile.yaml — Option B reroute active"
OPTION_B_HINT_PREFIX = "  hint: outputs → "


def test_refusal_exit_code_and_format(tmp_path):
    """Phase 63 VOPT-01/02: profile-less vault CWD now silently reroutes via Option B.
    Stderr carries the two-line info: / hint: breadcrumb; exit code is no longer 2."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    assert proc.returncode != 2, (
        f"Option B should not exit 2; got {proc.returncode}\nstderr:\n{proc.stderr}"
    )
    err_lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    info_idx = next(
        (i for i, ln in enumerate(err_lines) if ln.startswith(OPTION_B_INFO_PREFIX)),
        None,
    )
    assert info_idx is not None, f"missing info line:\n{proc.stderr}"
    assert err_lines[info_idx + 1].startswith(OPTION_B_HINT_PREFIX), (
        f"hint line mismatch.\n  expected prefix: {OPTION_B_HINT_PREFIX!r}\n"
        f"  actual: {err_lines[info_idx + 1]!r}\nfull stderr:\n{proc.stderr}"
    )


def test_refusal_message_text(tmp_path):
    """Phase 63 VOPT-02: hint line points at <vault>/.graphify-out/ (absolute)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    hint_line = next(
        (ln for ln in proc.stderr.splitlines() if ln.startswith(OPTION_B_HINT_PREFIX)),
        None,
    )
    assert hint_line is not None, f"missing hint line:\n{proc.stderr}"
    # Hint shape: "  hint: outputs → <abs-path>/"
    arrow = "outputs → "
    body = hint_line[len(OPTION_B_HINT_PREFIX):]
    assert body.endswith("/"), f"hint must end with trailing slash: {hint_line!r}"
    # The path itself starts after the OPTION_B_HINT_PREFIX in `body` (no arrow inside it).
    path_str = body.rstrip("/")
    assert Path(path_str).is_absolute(), f"hint path must be absolute: {path_str!r}"
    expected = (vault / ".graphify-out").resolve()
    assert Path(path_str).resolve() == expected, (
        f"hint path {path_str!r} should equal {expected!r}"
    )


# ---------------------------------------------------------------------------
# Plan 04 — VCWD-04: --write-into-vault flag plumbing + precedence
# ---------------------------------------------------------------------------


def test_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: per-command --write-into-vault suppresses VCWD-03 refusal.

    Phase 63 update: pass an existing corpus dir (``.``) so ``run`` does not
    misinterpret ``--help`` as a missing path (post-Option-B the resolver no
    longer short-circuits with exit-1 before path validation).
    """
    vault = _make_partial_vault(tmp_path, with_profile=False)
    (vault / "doc.md").write_text("# x", encoding="utf-8")
    proc = _graphify("run", "--write-into-vault", str(vault / "doc.md"), cwd=str(vault))
    assert "refusing to write into Obsidian vault" not in proc.stderr, (
        f"--write-into-vault should suppress refusal; got:\n{proc.stderr}"
    )
    assert proc.returncode != 2, f"unexpected exit 2 with --write-into-vault: stderr=\n{proc.stderr}"


def test_global_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: leading global --write-into-vault (before subcommand) suppresses refusal.

    Phase 63 update: pass an existing corpus path (see sibling test).
    """
    vault = _make_partial_vault(tmp_path, with_profile=False)
    (vault / "doc.md").write_text("# x", encoding="utf-8")
    proc = _graphify("--write-into-vault", "run", str(vault / "doc.md"), cwd=str(vault))
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
    assert "[graphify] info: auto-adopted vault at" in proc.stderr, (
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
    # Phase 63 VOPT-01: vault-no-profile is now Option B silent reroute, not refuse.
    assert "option-b" in s3, f"vault-no-profile → option-b expected; got: {s3!r}"


def test_doctor_runtime_parity(tmp_path):
    """Phase 63 VOPT-01 parity contract: doctor predicts 'option-b' and runtime
    silently reroutes (no exit-2). Both halves of the parity contract flip."""
    bare = _make_partial_vault(tmp_path, with_profile=False)
    doctor = _graphify("doctor", cwd=str(bare))
    runtime = _graphify("run", cwd=str(bare))
    doc_section = " ".join(_doctor_section_lines(doctor.stdout))
    assert "option-b" in doc_section, (
        f"doctor should predict option-b; got: {doc_section!r}"
    )
    assert runtime.returncode != 2, (
        f"runtime must not exit 2 on Option B path; stderr:\n{runtime.stderr}"
    )
    assert "info: vault CWD without .graphify/profile.yaml" in runtime.stderr, (
        f"runtime should emit Option B info breadcrumb; stderr:\n{runtime.stderr}"
    )


def test_env_pin_disables_gate(tmp_path):
    """Cross-cutting: GRAPHIFY_VAULT env pin treated as explicit routing — gate returns n/a."""
    pytest.importorskip("yaml")
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    # pin_target needs a fully valid profile so doctor doesn't SystemExit
    # when _had_pin=True propagates the SystemExit on resolution failure.
    pin_target = _make_profile_vault(tmp_path / "pinVault")
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
    # pin_target needs a fully valid profile so --vault-list routing succeeds.
    pin_target = _make_profile_vault(tmp_path / "pinVault")
    list_file = tmp_path / "vaults.txt"
    list_file.write_text(f"{pin_target}\n", encoding="utf-8")
    proc = _graphify(
        "--vault-list", str(list_file), "run", "--help",
        cwd=str(bare),
    )
    assert "refusing to write" not in proc.stderr, (
        f"--vault-list should suppress VCWD-03; got:\n{proc.stderr}"
    )


# Plan 62.1-01 — VCWD-argparse-required defect: update-vault + vault-promote
# RED tests (TDD gate). These must FAIL before the fix and PASS after.
# Root cause: _check_vault_cwd_gate auto-adopts BEFORE argparse runs, but
# --vault is declared required=True so argparse exits 2 regardless.
# ---------------------------------------------------------------------------


def test_update_vault_auto_adopt_no_vault_flag(tmp_path):
    """VCWD-argparse-required: update-vault from a profile vault CWD without --vault
    must NOT exit with argparse error 2 ('required: --vault').

    Currently FAILS (RED) because argparse required=True fires before the
    post-parse auto-adopt fallback can fill in opts.vault.
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    # Pass a non-existent --input so the command fails for a *business* reason
    # (not argparse), proving argparse accepted the call.
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

    Currently FAILS (RED) because argparse required=True fires before the
    post-parse auto-adopt fallback can fill in opts.vault.
    """
    pytest.importorskip("yaml")
    vault = _make_profile_vault(tmp_path)
    # Pass a non-existent --graph so the command fails for a *business* reason.
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
    user-facing 'error: --vault is required' and exit EXIT_VAULT_REFUSAL (=1).
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
    assert proc.returncode == 1, (
        f"expected EXIT_VAULT_REFUSAL=1, got {proc.returncode}; stderr: {proc.stderr}"
    )


# ---------------------------------------------------------------------------
# Phase 63 — B2: --output from `graphify run` suppresses Option B globally
# ---------------------------------------------------------------------------


def test_option_b_suppressed_by_cli_output_via_run_subcommand(tmp_path):
    """B2 strict-trigger: `graphify run --output <path>` from a vault CWD must
    write to <path> and never trigger the Option B reroute."""
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    # Tiny corpus so `run` has something to ingest.
    (vault / "doc.md").write_text("# x", encoding="utf-8")
    explicit = tmp_path / "explicit_out"
    proc = _graphify(
        "run", "--no-llm", "--output", str(explicit), str(vault / "doc.md"),
        cwd=str(vault),
    )
    # B2 invariant 1: Option B did NOT fire — no .graphify-out inside the vault.
    assert not (vault / ".graphify-out").exists(), (
        f"Option B reroute fired despite --output; stderr:\n{proc.stderr}"
    )
    # B2 invariant 2: info breadcrumb did NOT appear (D-02 strict trigger).
    assert "info: vault CWD without .graphify/profile.yaml" not in proc.stderr, (
        f"Option B breadcrumb fired despite --output; stderr:\n{proc.stderr}"
    )
    # B2 invariant 3: outputs landed at the explicit location (or run produced
    # at least the directory). We tolerate run's own non-zero exit codes from
    # missing optional deps (LLM, etc.); the gate / reroute checks above are
    # the contract this test locks in.
    if proc.returncode == 0:
        assert explicit.exists(), (
            f"explicit out dir not created; stderr:\n{proc.stderr}"
        )


def test_vault_promote_no_vault_flag_outside_vault_friendly_error(tmp_path):
    """VCWD-argparse-required friendly-error branch for vault-promote."""
    proc = _graphify(
        "vault-promote", "--graph", str(tmp_path / "nonexistent.json"),
        cwd=str(tmp_path),
    )
    assert "required: --vault" not in proc.stderr, (
        f"argparse 'required: --vault' must not fire; got stderr: {proc.stderr}"
    )
    assert "--vault is required" in proc.stderr, (
        f"expected friendly error 'error: --vault is required'; got stderr: {proc.stderr}"
    )
    assert proc.returncode == 1, (
        f"expected EXIT_VAULT_REFUSAL=1, got {proc.returncode}; stderr: {proc.stderr}"
    )
