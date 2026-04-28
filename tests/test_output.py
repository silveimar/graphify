"""Unit tests for graphify/output.py — Phase 27 vault detection + resolution."""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output


# ---------------------------------------------------------------------------
# is_obsidian_vault — D-04 strict CWD-only detection
# ---------------------------------------------------------------------------

def test_is_obsidian_vault_true_when_dir_present(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    assert is_obsidian_vault(tmp_path) is True


def test_is_obsidian_vault_false_when_file_not_dir(tmp_path):
    # Pitfall 2: a stray .obsidian file must NOT be treated as a vault
    (tmp_path / ".obsidian").touch()
    assert is_obsidian_vault(tmp_path) is False


def test_is_obsidian_vault_false_when_absent(tmp_path):
    assert is_obsidian_vault(tmp_path) is False


def test_is_obsidian_vault_no_parent_walk(tmp_path):
    # D-04: strict CWD-only — nested dir under a vault is NOT detected as vault
    (tmp_path / ".obsidian").mkdir()
    nested = tmp_path / "subdir"
    nested.mkdir()
    assert is_obsidian_vault(nested) is False


# ---------------------------------------------------------------------------
# resolve_output — D-12 backcompat (no vault, no flag)
# ---------------------------------------------------------------------------

def test_resolve_output_no_vault_default_paths(tmp_path, capsys):
    result = resolve_output(tmp_path)
    assert result == ResolvedOutput(
        vault_detected=False,
        vault_path=None,
        notes_dir=Path("graphify-out/obsidian"),
        artifacts_dir=Path("graphify-out"),
        source="default",
    )
    captured = capsys.readouterr()
    # D-12 silent backcompat: NO stderr emitted in no-vault default branch
    assert "vault detected" not in captured.err
    assert "[graphify]" not in captured.err


# ---------------------------------------------------------------------------
# resolve_output — D-05 / D-02 refusal cases
# ---------------------------------------------------------------------------

def test_resolve_output_vault_no_profile_refuses(tmp_path, capsys):
    (tmp_path / ".obsidian").mkdir()
    with pytest.raises(SystemExit):
        resolve_output(tmp_path)
    captured = capsys.readouterr()
    assert "no .graphify/profile.yaml found" in captured.err


def test_resolve_output_vault_profile_no_output_block_refuses(tmp_path, capsys):
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".graphify").mkdir()
    # Profile present but no output: block
    (tmp_path / ".graphify" / "profile.yaml").write_text("naming:\n  convention: kebab-case\n")
    pytest.importorskip("yaml")
    with pytest.raises(SystemExit):
        resolve_output(tmp_path)
    captured = capsys.readouterr()
    assert "no 'output:' block" in captured.err


# ---------------------------------------------------------------------------
# resolve_output — D-01/D-03 mode resolution
# ---------------------------------------------------------------------------

def _setup_vault(tmp_path: Path, output_yaml: str) -> Path:
    """Create a vault layout with .obsidian/ + .graphify/profile.yaml containing output:."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(output_yaml)
    return vault


def test_resolve_output_vault_relative_resolves(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: vault-relative\n  path: Knowledge/Graph\n")
    result = resolve_output(vault)
    assert result.vault_detected is True
    assert result.vault_path == vault.resolve()
    assert result.notes_dir == (vault / "Knowledge" / "Graph").resolve()
    assert result.source == "profile"
    captured = capsys.readouterr()
    assert "vault detected at" in captured.err
    assert "source=profile" in captured.err


def test_resolve_output_absolute_mode(tmp_path, capsys):
    pytest.importorskip("yaml")
    target = tmp_path / "elsewhere"
    target.mkdir()
    vault = _setup_vault(tmp_path, f"output:\n  mode: absolute\n  path: {target}\n")
    result = resolve_output(vault)
    assert result.notes_dir == target.resolve()
    assert result.source == "profile"


def test_resolve_output_sibling_of_vault_mode(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: sibling-of-vault\n  path: graphify-notes\n")
    result = resolve_output(vault)
    # <vault>/../graphify-notes resolves to tmp_path/graphify-notes
    assert result.notes_dir == (tmp_path / "graphify-notes").resolve()
    assert result.source == "profile"


# ---------------------------------------------------------------------------
# D-11 split: artifacts always sibling-of-vault when vault detected
# ---------------------------------------------------------------------------

def test_resolve_output_artifacts_always_sibling_when_vault(tmp_path):
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: vault-relative\n  path: Notes\n")
    result = resolve_output(vault)
    # Even with vault-relative notes, artifacts go to <vault>/../graphify-out
    assert result.artifacts_dir == (tmp_path / "graphify-out").resolve()


# ---------------------------------------------------------------------------
# D-08 / D-09: CLI flag precedence + stderr line
# ---------------------------------------------------------------------------

def test_resolve_output_cli_flag_overrides_profile_emits_stderr(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: vault-relative\n  path: Notes\n")
    result = resolve_output(vault, cli_output="custom-out")
    assert result.source == "cli-flag"
    captured = capsys.readouterr()
    # Exact D-09 contract — the message now reports the profile mode being overridden
    assert "--output=custom-out overrides profile output" in captured.err
    assert "mode=vault-relative" in captured.err
    # And the detection report
    assert "vault detected at" in captured.err
    # Emitted exactly once (Pitfall 5)
    assert captured.err.count("overrides profile output") == 1


def test_resolve_output_cli_flag_in_vault_without_profile_output_emits_fallback_label(tmp_path, capsys):
    # Vault with no profile.yaml: D-09 falls back to (profile-not-applicable) label
    # rather than the prior invented "mode=cli-literal" token. CONTEXT D-09 reconcile.
    (tmp_path / ".obsidian").mkdir()
    # NO .graphify/profile.yaml — but cli_output bypasses the D-05 refusal path.
    result = resolve_output(tmp_path, cli_output="forced-out")
    assert result.source == "cli-flag"
    captured = capsys.readouterr()
    assert "overrides profile output" in captured.err
    assert "(profile-not-applicable)" in captured.err


def test_resolve_output_cli_flag_no_vault_silent(tmp_path, capsys):
    # No vault + cli flag: source=cli-flag, vault_detected=False, no D-09 line
    result = resolve_output(tmp_path, cli_output="my-out")
    assert result.source == "cli-flag"
    assert result.vault_detected is False
    captured = capsys.readouterr()
    assert "overrides profile output" not in captured.err
    assert "vault detected" not in captured.err


def test_resolve_output_cli_flag_absolute_path(tmp_path):
    absolute = tmp_path / "absolute-out"
    result = resolve_output(tmp_path, cli_output=str(absolute))
    assert result.notes_dir == absolute.resolve()
    assert result.source == "cli-flag"


# ---------------------------------------------------------------------------
# Pitfall 3: PyYAML missing distinct message
# ---------------------------------------------------------------------------

def test_resolve_output_pyyaml_missing_distinct_message(tmp_path, capsys, monkeypatch):
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".graphify").mkdir()
    (tmp_path / ".graphify" / "profile.yaml").write_text("output:\n  mode: vault-relative\n  path: x\n")

    # Simulate PyYAML missing
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("No module named 'yaml'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with pytest.raises(SystemExit):
        resolve_output(tmp_path)
    captured = capsys.readouterr()
    assert "PyYAML" in captured.err or "pyyaml" in captured.err.lower()
    assert "graphifyy[obsidian]" in captured.err


# ---------------------------------------------------------------------------
# ResolvedOutput data carrier shape
# ---------------------------------------------------------------------------

def test_resolved_output_namedtuple_field_order():
    # D-13 contract: field order is part of the integration contract for Phase 28/29
    assert ResolvedOutput._fields == (
        "vault_detected",
        "vault_path",
        "notes_dir",
        "artifacts_dir",
        "source",
        "exclude_globs",  # Phase 28 D-14
    )


def test_resolved_output_is_immutable():
    r = ResolvedOutput(False, None, Path("a"), Path("b"), "default")
    with pytest.raises(AttributeError):
        r.vault_detected = True  # type: ignore


def test_resolved_output_unpacks_to_tuple():
    # Phase 29 doctor may want positional unpacking
    r = ResolvedOutput(True, Path("/v"), Path("/v/n"), Path("/g"), "profile", ("*.tmp",))
    vault_detected, vault_path, notes_dir, artifacts_dir, source, exclude_globs = r
    assert vault_detected is True
    assert source == "profile"
    assert exclude_globs == ("*.tmp",)


# ---------------------------------------------------------------------------
# Sibling-of-vault edge case via resolver
# ---------------------------------------------------------------------------

def test_resolve_output_sibling_of_vault_traversal_in_path_refuses(tmp_path, capsys):
    # Schema lets sibling-of-vault path through; use-time validate_sibling_path rejects '..'
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: sibling-of-vault\n  path: ../escape\n")
    with pytest.raises(ValueError, match="\\.\\."):
        resolve_output(vault)


# ---------------------------------------------------------------------------
# validate_sibling_path filesystem-root rejection (POSIX-conditional)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not Path('/').resolve() == Path('/'),
    reason="POSIX-only: filesystem-root semantics differ on Windows"
)
def test_resolve_output_sibling_at_filesystem_root_refuses(tmp_path):
    # When vault.parent == vault (filesystem root), validate_sibling_path must reject.
    # Use the real Path('/').resolve() rather than mocking — keeps the test honest
    # and avoids dead monkeypatch infrastructure.
    from graphify.profile import validate_sibling_path
    with pytest.raises(ValueError):
        validate_sibling_path("anything", Path("/").resolve())


# ---------------------------------------------------------------------------
# Phase 28 D-14: exclude_globs field
# ---------------------------------------------------------------------------

def test_resolved_output_exclude_globs_defaults_to_empty_tuple():
    r = ResolvedOutput(False, None, Path("a"), Path("b"), "default")
    assert r.exclude_globs == ()


def test_resolve_output_exclude_globs_populated_from_profile(tmp_path):
    pytest.importorskip("yaml")
    vault = _setup_vault(
        tmp_path,
        "output:\n  mode: vault-relative\n  path: Atlas\n"
        "  exclude:\n    - '**/cache/**'\n    - '*.tmp'\n",
    )
    result = resolve_output(vault)
    assert result.exclude_globs == ("**/cache/**", "*.tmp")


def test_resolve_output_exclude_globs_empty_when_cli_flag(tmp_path):
    result = resolve_output(tmp_path, cli_output=str(tmp_path / "out"))
    assert result.exclude_globs == ()


def test_resolve_output_exclude_globs_empty_when_default(tmp_path):
    result = resolve_output(tmp_path)
    assert result.exclude_globs == ()
