"""Detection-layer tests for graphify reverse-sync (Phase 70 / VRSYNC-01, Plan 02).

Covers D-08 (scope), D-09 (markdown only + recursive mirror), D-10 (vault_deleted),
and Pitfall 1 regression (must NOT use cache.file_hash which strips frontmatter).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from graphify.reverse_sync import ChangeRecord, compute_change_set


def _raw_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _make_profile(vault_dir: Path, input_dir: Path, folders=("Atlas",)) -> dict:
    return {
        "vault_path": str(vault_dir),
        "input_path": str(input_dir),
        "user_only_folders": list(folders),
        "reverse_sync": {},
        "augment": {},
    }


def _setup_dirs(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    inp = tmp_path / "input"
    (vault / "Atlas").mkdir(parents=True)
    (inp / "Atlas").mkdir(parents=True)
    return vault, inp


def test_detect_new_file(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    f = vault / "Atlas" / "foo.md"
    f.write_text("hello world\n")
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    c = changes[0]
    assert isinstance(c, ChangeRecord)
    assert c.kind == "new"
    assert c.hash_before is None
    assert c.hash_after == _raw_sha(f)
    assert c.rel_path == "Atlas/foo.md"


def test_detect_updated_file(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    vf = vault / "Atlas" / "foo.md"
    inf = inp / "Atlas" / "foo.md"
    vf.write_text("new content\n")
    inf.write_text("old content\n")
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    c = changes[0]
    assert c.kind == "update"
    assert c.hash_before == _raw_sha(inf)
    assert c.hash_after == _raw_sha(vf)
    assert c.hash_before != c.hash_after


def test_detect_skip_unchanged(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    body = "identical bytes\n"
    (vault / "Atlas" / "foo.md").write_text(body)
    (inp / "Atlas" / "foo.md").write_text(body)
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    assert changes[0].kind == "skip"
    assert changes[0].hash_before == changes[0].hash_after


def test_detect_vault_deleted(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    inf = inp / "Atlas" / "old.md"
    inf.write_text("orphaned\n")
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    c = changes[0]
    assert c.kind == "vault_deleted"
    assert c.hash_before == _raw_sha(inf)
    assert c.hash_after is None
    assert c.rel_path == "Atlas/old.md"


def test_scope_user_only_folders(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "in_scope.md").write_text("a\n")
    (vault / "Other").mkdir()
    (vault / "Other" / "out_of_scope.md").write_text("b\n")
    changes = compute_change_set(_make_profile(vault, inp, folders=("Atlas",)))
    assert {c.rel_path for c in changes} == {"Atlas/in_scope.md"}


def test_markdown_only(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "note.md").write_text("md\n")
    (vault / "Atlas" / "skip.txt").write_text("txt\n")
    (vault / "Atlas" / "doc.pdf").write_bytes(b"%PDF-1.4\n")
    (vault / "Atlas" / "img.png").write_bytes(b"\x89PNG\r\n")
    changes = compute_change_set(_make_profile(vault, inp))
    assert {c.rel_path for c in changes} == {"Atlas/note.md"}


def test_recursive_subdirs(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    deep = vault / "Atlas" / "sub" / "deep"
    deep.mkdir(parents=True)
    (deep / "note.md").write_text("nested\n")
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    c = changes[0]
    assert c.rel_path == "Atlas/sub/deep/note.md"
    assert c.kind == "new"
    # Mirrored input target preserves subdir structure
    expected_target = inp / "Atlas" / "sub" / "deep" / "note.md"
    assert c.input_path == expected_target


def test_frontmatter_only_change_detected(tmp_path):
    """Pitfall 1 regression guard: cache.file_hash strips frontmatter; we must NOT.

    Two files with identical body but different frontmatter must be flagged update,
    not skip.
    """
    vault, inp = _setup_dirs(tmp_path)
    body = "\n# Heading\n\nbody text\n"
    (vault / "Atlas" / "foo.md").write_text("---\ntags: [new]\n---\n" + body)
    (inp / "Atlas" / "foo.md").write_text("---\ntags: [old]\n---\n" + body)
    changes = compute_change_set(_make_profile(vault, inp))
    assert len(changes) == 1
    assert changes[0].kind == "update"


def test_empty_vault(tmp_path):
    vault, inp = _setup_dirs(tmp_path)
    changes = compute_change_set(_make_profile(vault, inp))
    assert changes == []
    # Also when user_only_folders points at non-existent dir
    changes2 = compute_change_set(_make_profile(vault, inp, folders=("DoesNotExist",)))
    assert changes2 == []


# ---------------------------------------------------------------------------
# Plan 03 tests: mode dispatch, prompt UX, CLI subcommand registration.
# Covers D-01, D-02, D-03, D-12, D-13 and Success Criterion 3.
# ---------------------------------------------------------------------------


def _write_profile_yaml(vault: Path, input_dir: Path, mode: str = "always_ask",
                        folders=("Atlas",)) -> None:
    """Write a minimal valid v1.8 .graphify/profile.yaml.

    `taxonomy` and `mapping.min_community_size` are required by
    _validate_required_v18_user_profile; vault_path/input_path are NOT valid
    profile keys — run_reverse_sync injects them from its arguments.
    """
    pdir = vault / ".graphify"
    pdir.mkdir(parents=True, exist_ok=True)
    folders_yaml = "\n".join(f"  - {f}" for f in folders)
    (pdir / "profile.yaml").write_text(
        "taxonomy: {}\n"
        "mapping:\n"
        "  min_community_size: 1\n"
        "user_only_folders:\n" + folders_yaml + "\n"
        "reverse_sync:\n"
        "  mode: " + mode + "\n",
        encoding="utf-8",
    )


def _scripted_input(answers):
    it = iter(answers)
    def _inp(_prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise RuntimeError("input() called more times than scripted")
    return _inp


def test_mode_always_copy_writes_without_prompt(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "a.md").write_text("alpha\n")
    (vault / "Atlas" / "b.md").write_text("beta\n")
    _write_profile_yaml(vault, inp, mode="always_copy")

    def _no_input(_p=""):
        raise AssertionError("input() must not be called in always_copy mode")
    monkeypatch.setattr("builtins.input", _no_input)

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["copied"] == 2
    assert (inp / "Atlas" / "a.md").read_text() == "alpha\n"
    assert (inp / "Atlas" / "b.md").read_text() == "beta\n"


def test_mode_never_copy_logs_only(tmp_path):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "x.md").write_text("x\n")
    (vault / "Atlas" / "y.md").write_text("y\n")
    _write_profile_yaml(vault, inp, mode="never_copy")

    # D-12: --yes does NOT override never_copy.
    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp, yes=True)
    assert result["skipped_never_copy"] == 2
    assert result["copied"] == 0
    assert not (inp / "Atlas" / "x.md").exists()
    assert not (inp / "Atlas" / "y.md").exists()


def test_mode_always_ask_yes_response(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("data\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", _scripted_input(["y"]))

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["copied"] == 1
    assert (inp / "Atlas" / "f.md").read_text() == "data\n"


def test_mode_always_ask_no_response(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("data\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", _scripted_input(["n"]))

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["skipped_user"] == 1
    assert result["copied"] == 0
    assert not (inp / "Atlas" / "f.md").exists()


def test_prompt_diff_then_yes(tmp_path, monkeypatch, capsys):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("new content\n")
    (inp / "Atlas" / "f.md").write_text("old content\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", _scripted_input(["d", "y"]))

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    out = capsys.readouterr().out
    # diff body printed (D-02)
    assert "new content" in out or "old content" in out
    assert result["copied"] == 1
    assert (inp / "Atlas" / "f.md").read_text() == "new content\n"


def test_prompt_all_response(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "a.md").write_text("a\n")
    (vault / "Atlas" / "b.md").write_text("b\n")
    (vault / "Atlas" / "c.md").write_text("c\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    # Exactly one input() call ("A") — subsequent files must auto-accept.
    monkeypatch.setattr("builtins.input", _scripted_input(["A"]))

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["copied"] == 3


def test_prompt_quit_response(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    # Deterministic ordering by rel_path: a, b, c
    (vault / "Atlas" / "a.md").write_text("a\n")
    (vault / "Atlas" / "b.md").write_text("b\n")
    (vault / "Atlas" / "c.md").write_text("c\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", _scripted_input(["y", "Q"]))

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["failed"] is False  # clean abort
    assert result["copied"] == 1
    # Files after the quit must not be touched.
    assert (inp / "Atlas" / "a.md").exists()
    assert not (inp / "Atlas" / "c.md").exists()


def test_yes_flag_overrides_always_ask(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("data\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    def _no_input(_p=""):
        raise AssertionError("input() must not be called when --yes is set")
    monkeypatch.setattr("builtins.input", _no_input)

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp, yes=True)
    assert result["copied"] == 1
    assert (inp / "Atlas" / "f.md").read_text() == "data\n"


def test_yes_does_NOT_override_never_copy(tmp_path):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("data\n")
    _write_profile_yaml(vault, inp, mode="never_copy")

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp, yes=True)
    assert result["skipped_never_copy"] == 1
    assert result["copied"] == 0
    assert not (inp / "Atlas" / "f.md").exists()


def test_non_tty_skips_conflicts(tmp_path, monkeypatch):
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "a.md").write_text("a\n")
    (vault / "Atlas" / "b.md").write_text("b\n")
    _write_profile_yaml(vault, inp, mode="always_ask")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    def _no_input(_p=""):
        raise AssertionError("input() must not be called in non-TTY mode")
    monkeypatch.setattr("builtins.input", _no_input)

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["skipped_conflict"] == 2
    assert result["copied"] == 0
    assert not (inp / "Atlas" / "a.md").exists()


def test_atomic_copy(tmp_path, monkeypatch):
    """The copy must go through a .tmp + os.replace path (no partial writes visible)."""
    import os as _os
    from graphify.reverse_sync import run_reverse_sync
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("payload\n")
    _write_profile_yaml(vault, inp, mode="always_copy")

    seen = {"replace_called": False}
    real_replace = _os.replace
    def _spy_replace(src, dst):
        seen["replace_called"] = True
        # src must be a .tmp sibling of dst (atomic-rename pattern)
        assert str(src).endswith(".tmp"), f"expected .tmp staging file, got {src}"
        return real_replace(src, dst)
    monkeypatch.setattr("os.replace", _spy_replace)

    result = run_reverse_sync(vault_dir=vault, input_dir_override=inp)
    assert result["copied"] == 1
    assert seen["replace_called"] is True


def test_path_confinement(tmp_path, monkeypatch, capsys):
    """A vault file whose mirrored target escapes input_dir must be refused."""
    from graphify.reverse_sync import run_reverse_sync, _validate_input_path
    vault, inp = _setup_dirs(tmp_path)
    # Direct unit check (compute_change_set already enforces, but apply must too).
    bad = tmp_path / "outside.md"
    assert _validate_input_path(inp, bad) is False
    good = inp / "Atlas" / "ok.md"
    assert _validate_input_path(inp, good) is True


def test_cli_subcommand_dispatch(tmp_path, monkeypatch, capsys):
    """`graphify reverse-sync --vault PATH --mode always_copy` must dispatch and exit 0."""
    import graphify.__main__ as gm
    vault, inp = _setup_dirs(tmp_path)
    (vault / "Atlas" / "f.md").write_text("hello\n")
    _write_profile_yaml(vault, inp, mode="always_ask")  # CLI --mode overrides

    monkeypatch.setattr(
        "sys.argv",
        ["graphify", "reverse-sync", "--vault", str(vault),
         "--input", str(inp), "--mode", "always_copy"],
    )

    with pytest.raises(SystemExit) as exc:
        gm.main()
    assert exc.value.code == 0
    assert (inp / "Atlas" / "f.md").read_text() == "hello\n"
