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
