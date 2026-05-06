"""RED regression matrix for VFIX-01 — locks the cwd × --obsidian-dir × profile.output
path-resolution invariants.

These tests encode the *intended post-fix* behavior. At least one is expected to fail
today (RED phase of TDD cycle 70.1). Plan 70.1-02 turns them GREEN by fixing the
production resolver in graphify/output.py and the --obsidian dispatch path in
graphify/__main__.py.

Pure unit tests: tmp_path only, no network, no fs side-effects outside tmp_path,
no global cwd mutation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.output import resolve_execution_paths, resolve_output


# ---------------------------------------------------------------------------
# Fixture helper — minimal Ideaverse-style v1.8 vault with output.path = "."
# ---------------------------------------------------------------------------

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


def _make_vault(tmp_path: Path, name: str = "uat70-vault") -> Path:
    """Build a tmp_path/<name>/ vault with .obsidian/ + .graphify/profile.yaml."""
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(_PROFILE_YAML, encoding="utf-8")
    return vault


def _make_vault_no_profile(tmp_path: Path, name: str = "vopt-vault") -> Path:
    """Phase 63: vault directory with .obsidian/ but NO .graphify/profile.yaml.

    Triggers Option B silent reroute in resolve_output() (VOPT-01).
    """
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


def _no_doubled_segment(notes_dir: Path, vault_name: str) -> bool:
    """Regression sentinel: vault.name must appear at most once in notes_dir.parts."""
    return [p for p in notes_dir.parts if p == vault_name].count(vault_name) <= 1


# ---------------------------------------------------------------------------
# Test 1 — cwd inside vault, profile.output.path == "." → notes_dir == vault root
# ---------------------------------------------------------------------------

def test_cwd_in_vault_profile_dot_resolves_to_vault_root(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    resolved = resolve_output(vault)
    capsys.readouterr()  # drain detection stderr line
    assert resolved.vault_detected is True
    assert resolved.source == "profile"
    assert resolved.notes_dir == vault.resolve()
    assert _no_doubled_segment(resolved.notes_dir, vault.name)


# ---------------------------------------------------------------------------
# Test 2 — cwd inside vault + explicit_vault pin → identical resolution
# ---------------------------------------------------------------------------

def test_cwd_in_vault_with_explicit_vault_pin_resolves_identically(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    resolved = resolve_execution_paths(vault, explicit_vault=vault)
    capsys.readouterr()
    assert resolved.vault_detected is True
    assert resolved.notes_dir == vault.resolve()
    assert _no_doubled_segment(resolved.notes_dir, vault.name)


# ---------------------------------------------------------------------------
# Test 3 — cwd at parent + explicit_vault pin → must NOT prepend parent onto vault
# ---------------------------------------------------------------------------

def test_cwd_parent_with_explicit_vault_pin_resolves_identically(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    parent = tmp_path  # parent has no .obsidian/
    resolved = resolve_execution_paths(parent, explicit_vault=vault)
    capsys.readouterr()
    assert resolved.vault_detected is True
    assert resolved.notes_dir == vault.resolve()
    assert _no_doubled_segment(resolved.notes_dir, vault.name)


# ---------------------------------------------------------------------------
# Test 4 — cwd at parent (no vault, no pin, no cli) → default no-vault paths (D-12)
# ---------------------------------------------------------------------------

def test_cwd_parent_no_pin_no_cli_returns_default_no_vault(tmp_path, capsys):
    # No vault here — locks "do not silently scan parent for vault" behavior
    parent = tmp_path
    resolved = resolve_output(parent)
    capsys.readouterr()
    assert resolved.vault_detected is False
    assert resolved.source == "default"
    assert resolved.notes_dir == Path("graphify-out/obsidian")


# ---------------------------------------------------------------------------
# Test 5 — CLI --output overrides profile.output.path == "." (D-08 precedence)
# ---------------------------------------------------------------------------

def test_cli_output_overrides_profile_path_dot(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    custom_out = tmp_path / "custom-out"
    resolved = resolve_output(vault, cli_output=str(custom_out))
    capsys.readouterr()
    assert resolved.source == "cli-flag"
    assert resolved.notes_dir == custom_out.resolve()


# ---------------------------------------------------------------------------
# Test 6 — Regression sentinel: no doubled vault-name segment across resolutions
# ---------------------------------------------------------------------------

def test_no_doubled_vault_name_segment_in_any_resolution(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    parent = tmp_path
    custom_out = tmp_path / "custom-out"

    r1 = resolve_output(vault)
    r2 = resolve_execution_paths(vault, explicit_vault=vault)
    r3 = resolve_execution_paths(parent, explicit_vault=vault)
    r5 = resolve_output(vault, cli_output=str(custom_out))
    capsys.readouterr()

    for label, resolved in [("r1", r1), ("r2", r2), ("r3", r3), ("r5", r5)]:
        doubled = [p for p in resolved.notes_dir.parts if p == vault.name]
        assert len(doubled) <= 1, (
            f"{label}: doubled '{vault.name}' segment in {resolved.notes_dir!s}"
        )


# ---------------------------------------------------------------------------
# Test 7 — --obsidian dispatch precedence: parent_cwd + obsidian_dir → vault root
# ---------------------------------------------------------------------------

def test_obsidian_dispatch_parent_cwd_with_obsidian_dir_no_doubled_segment(
    tmp_path, capsys, monkeypatch
):
    """End-to-end sentinel: --obsidian + --obsidian-dir <vault> from parent cwd.

    Simulates the Phase 70 UAT failure where notes landed at
    `<vault>/<vault.name>/Atlas/Sources/Graphify/...` instead of
    `<vault>/Atlas/Sources/Graphify/...`. Drives a minimal graph through
    `to_obsidian` with the exact profile that triggered the bug.

    This is the dedicated RED regression sentinel. It exercises real production
    code (graphify.export.to_obsidian + profile loading + classify/render).
    Plan 70.1-02 turns it GREEN by fixing the dispatch / writer path join.
    """
    pytest.importorskip("yaml")
    pytest.importorskip("networkx")

    import networkx as nx

    from graphify.export import to_obsidian

    vault = _make_vault(tmp_path)

    # Pin cwd to the vault's parent so the relative `obsidian_dir` arg the
    # dispatcher forwards resolves inside tmp_path (not into the repo root).
    # This is the exact UAT scenario: invocation from the vault's parent
    # directory with `--obsidian-dir <vault-name>`. Required to keep all fs
    # side-effects confined to tmp_path per the project test conventions.
    monkeypatch.chdir(tmp_path)

    # Tiny graph with one community of 3 nodes — enough to drive render+merge.
    G = nx.Graph()
    for nid, label in [
        ("alpha", "Alpha"),
        ("beta", "Beta"),
        ("gamma", "Gamma"),
    ]:
        G.add_node(
            nid,
            label=label,
            file_type="code",
            source_file="src/x.py",
            source_location="L1",
            community=0,
        )
    G.add_edge("alpha", "beta", relation="calls", confidence="EXTRACTED",
               source_file="src/x.py", weight=1.0)
    G.add_edge("beta", "gamma", relation="calls", confidence="EXTRACTED",
               source_file="src/x.py", weight=1.0)

    communities = {0: ["alpha", "beta", "gamma"]}

    # Resolve as the --obsidian dispatch would: vault profile → notes_dir == vault.
    resolved = resolve_execution_paths(tmp_path, explicit_vault=vault)
    capsys.readouterr()
    assert resolved.notes_dir == vault.resolve(), (
        "resolver invariant: profile output.path='.' must yield vault root"
    )

    # Emulate the buggy __main__.py dispatch path the UAT exercised:
    #   user runs `graphify --obsidian --obsidian-dir uat70-vault` from the
    #   PARENT of the vault, with no --vault pin. Per __main__.py:1869 the
    #   dispatcher takes the user_passed_obsidian_dir branch and forwards the
    #   *relative* arg "uat70-vault" verbatim into to_obsidian as output_dir.
    #   to_obsidian then `Path(output_dir).resolve()` — which resolves against
    #   process cwd (parent), not the vault. Combined with the profile being
    #   re-discovered inside that resolved dir, the writer plans paths under
    #   <parent>/uat70-vault/uat70-vault/Atlas/... — the doubled-segment bug.
    #
    # Plan 70.1-02 will fix dispatch so that --obsidian-dir is resolved against
    # cwd up front and never produces a doubled segment. Until then, this test
    # uses the same relative-path forwarding the buggy dispatcher does.
    obsidian_dir = vault.name  # relative — exactly what dispatch forwards today

    # Drive the writer end-to-end. dry_run=True is sufficient — we only need to
    # observe the *planned* paths, not actually write files.
    result = to_obsidian(
        G,
        communities,
        obsidian_dir,
        dry_run=True,
    )
    capsys.readouterr()

    # Extract planned write paths from the MergePlan returned by dry_run.
    actions = getattr(result, "actions", None)
    if actions is None and isinstance(result, dict):
        actions = result.get("actions")
    assert actions, (
        f"expected to_obsidian dry_run to return MergePlan.actions; got {result!r}"
    )
    planned_paths = [Path(getattr(a, "path", a)) for a in actions]

    # Each planned path must be inside the vault and contain `vault.name` exactly
    # once. The Phase 70 UAT bug produced paths with vault.name DOUBLED — this is
    # the dedicated regression sentinel for that nested-folder failure mode.
    for p in planned_paths:
        resolved_p = p.resolve()
        # Must be inside the vault
        try:
            resolved_p.relative_to(vault.resolve())
        except ValueError:
            pytest.fail(
                f"planned path {resolved_p!s} escapes vault {vault.resolve()!s}"
            )
        # And must NOT contain the vault directory name twice
        doubled = [seg for seg in resolved_p.parts if seg == vault.name]
        assert len(doubled) == 1, (
            f"doubled '{vault.name}' segment in planned path {resolved_p!s}; "
            f"parts={resolved_p.parts}"
        )

    # Additional invariant: the user-visible folder mapping (`thing` →
    # `Atlas/Sources/Graphify/Things/`) must land at vault/Atlas/Sources/Graphify/
    # — NOT at vault/<vault.name>/Atlas/Sources/Graphify/ (the UAT bug).
    things_paths = [p for p in planned_paths if "Things" in p.parts]
    assert things_paths, "expected at least one Things/ note in dry_run plan"
    for p in things_paths:
        expected_prefix = vault.resolve() / "Atlas" / "Sources" / "Graphify" / "Things"
        assert str(p.resolve()).startswith(str(expected_prefix)), (
            f"Things note {p!s} not under {expected_prefix!s} — "
            f"likely doubled vault.name segment (UAT70 nested-folder bug)"
        )


# ---------------------------------------------------------------------------
# Phase 63 — VOPT-01/02: Option B silent reroute
# ---------------------------------------------------------------------------


def test_option_b_vault_no_profile_reroutes_to_hidden(tmp_path, capsys):
    """VOPT-01: vault CWD without profile → source='option-b', hidden .graphify-out/."""
    vault = _make_vault_no_profile(tmp_path)
    resolved = resolve_output(vault)
    capsys.readouterr()
    assert resolved.source == "option-b"
    assert resolved.vault_detected is True
    assert resolved.vault_path == vault.resolve()
    assert resolved.notes_dir == (vault / ".graphify-out" / "obsidian").resolve()
    assert resolved.artifacts_dir == (vault / ".graphify-out").resolve()
    assert _no_doubled_segment(resolved.notes_dir, vault.name)


def test_option_b_breadcrumb_shape(tmp_path, capsys):
    """VOPT-02: exactly two non-empty stderr lines, info: + hint:; VAULT-08 suppressed."""
    vault = _make_vault_no_profile(tmp_path)
    resolve_output(vault)
    err = capsys.readouterr().err
    assert (
        "[graphify] info: vault CWD without .graphify/profile.yaml — Option B reroute active"
        in err
    )
    assert f"  hint: outputs → {(vault / '.graphify-out').resolve()}/" in err
    # VAULT-08 single-line "vault detected at" suppressed on Option B branch:
    assert "[graphify] vault detected at" not in err
    # Robust shape (W6): exactly two non-empty stderr lines.
    non_empty = [ln for ln in err.splitlines() if ln.strip()]
    assert len(non_empty) == 2, f"expected 2 non-empty stderr lines, got {non_empty!r}"


def test_option_b_suppressed_by_cli_output(tmp_path, capsys):
    """D-02 strict trigger: --output suppresses Option B (yields source='cli-flag')."""
    vault = _make_vault_no_profile(tmp_path)
    out = tmp_path / "explicit"
    resolved = resolve_output(vault, cli_output=str(out))
    capsys.readouterr()
    assert resolved.source == "cli-flag"


def test_option_b_suppressed_by_obsidian_dir_override(tmp_path):
    """D-02 strict trigger: obsidian_dir_override=True → legacy refuse semantics."""
    vault = _make_vault_no_profile(tmp_path)
    with pytest.raises(SystemExit):
        resolve_output(vault, obsidian_dir_override=True)


def test_option_b_non_vault_cwd_unchanged(tmp_path, capsys):
    """Regression: non-vault CWD path is untouched (source='default')."""
    plain = tmp_path / "plain"
    plain.mkdir()
    resolved = resolve_output(plain)
    capsys.readouterr()
    assert resolved.source == "default"
    assert resolved.vault_detected is False


def test_option_b_paths_are_absolute(tmp_path, capsys):
    """A1: Option B notes_dir / artifacts_dir are absolute and contain '.graphify-out'."""
    vault = _make_vault_no_profile(tmp_path)
    resolved = resolve_output(vault)
    capsys.readouterr()
    assert resolved.notes_dir.is_absolute()
    assert resolved.artifacts_dir.is_absolute()
    assert ".graphify-out" in resolved.notes_dir.parts


def test_option_b_idempotent_across_calls(tmp_path, capsys):
    """Option B path is stable: two calls on the same vault produce identical
    notes_dir / artifacts_dir / source values (no hidden state)."""
    vault = _make_vault_no_profile(tmp_path, name="idem-vault")
    r1 = resolve_output(vault)
    r2 = resolve_output(vault)
    capsys.readouterr()
    assert r1.source == r2.source == "option-b"
    assert r1.notes_dir == r2.notes_dir
    assert r1.artifacts_dir == r2.artifacts_dir
