"""Tests for graphify.augment — allowlist frontmatter merge for user files.

Phase 70 / VPROF-03 augmentation half. Decisions D-04, D-05, D-06, D-07, D-16.
"""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from graphify.augment import augment_user_file_frontmatter
from graphify.merge import _find_body_start, _parse_frontmatter


# ---------------------------------------------------------------------------
# Local helpers (kept here rather than conftest.py to keep this test file
# self-contained; conftest factory is exposed below for cross-test reuse).
# ---------------------------------------------------------------------------

def _write(target: Path, frontmatter: dict | None, body: str) -> Path:
    from graphify.profile import _dump_frontmatter
    if frontmatter is None:
        text = body
    else:
        text = _dump_frontmatter(frontmatter) + "\n" + body
    target.write_text(text, encoding="utf-8")
    return target


def _read_fm(target: Path) -> dict:
    return _parse_frontmatter(target.read_text(encoding="utf-8")) or {}


def _read_body(target: Path) -> bytes:
    raw = target.read_bytes()
    text = raw.decode("utf-8")
    if text.startswith("﻿"):
        text = text[1:]
    return text[_find_body_start(text):].encode("utf-8")


# ---------------------------------------------------------------------------
# D-04: list keys union with user order preserved
# ---------------------------------------------------------------------------

def test_list_keys_union_preserve_order(tmp_path):
    f = _write(tmp_path / "n.md", {"tags": ["a", "b"]}, "body\n")
    augment_user_file_frontmatter(f, {"tags": ["b", "c"]}, profile={})
    assert _read_fm(f)["tags"] == ["a", "b", "c"]


def test_list_keys_create_when_absent(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"tags": ["x"]}, profile={})
    assert _read_fm(f)["tags"] == ["x"]


# ---------------------------------------------------------------------------
# D-05: scalar keys only-if-absent
# ---------------------------------------------------------------------------

def test_scalar_keys_only_if_absent(tmp_path):
    f = _write(tmp_path / "n.md", {"type": "note"}, "body\n")
    augment_user_file_frontmatter(f, {"type": "ml"}, profile={})
    assert _read_fm(f)["type"] == "note"


def test_scalar_added_when_absent(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"type": "ml"}, profile={})
    assert _read_fm(f)["type"] == "ml"


# ---------------------------------------------------------------------------
# D-16: community gate
# ---------------------------------------------------------------------------

def test_community_gate_default_false(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"community": "x"}, profile={})
    assert "community" not in _read_fm(f)


def test_community_gate_enabled(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(
        f, {"community": "x"}, profile={"augment": {"allow_community": True}}
    )
    assert _read_fm(f).get("community") == "x"


# ---------------------------------------------------------------------------
# Allowlist enforcement
# ---------------------------------------------------------------------------

def test_non_allowlist_keys_ignored(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"random_key": "x"}, profile={})
    assert "random_key" not in _read_fm(f)


# ---------------------------------------------------------------------------
# D-07: body bytes identical (property test, 50 randomized bodies)
# ---------------------------------------------------------------------------

def _random_body(rng: random.Random) -> str:
    """Generate a randomized markdown body covering tricky shapes."""
    pieces = []
    n_lines = rng.randint(0, 12)
    for _ in range(n_lines):
        choice = rng.randint(0, 6)
        if choice == 0:
            pieces.append("")
        elif choice == 1:
            pieces.append("# heading " + str(rng.randint(0, 99)))
        elif choice == 2:
            pieces.append("---")  # horizontal rule mid-body — must NOT confuse parser
        elif choice == 3:
            pieces.append("plain text line " + "x" * rng.randint(0, 40))
        elif choice == 4:
            pieces.append("- list item")
        elif choice == 5:
            pieces.append("```")
        else:
            pieces.append("paragraph with : colon and -- dashes")
    sep = "\r\n" if rng.random() < 0.3 else "\n"
    body = sep.join(pieces)
    if rng.random() < 0.5:
        body += sep
    if rng.random() < 0.2:
        body = "﻿" + body  # BOM prefix on the *file*; body itself is post-FM
    return body


def test_body_byte_identical_property(tmp_path):
    rng = random.Random(20260505)
    for i in range(50):
        body = _random_body(rng)
        f = tmp_path / f"n{i}.md"
        # Write with frontmatter so there IS a body separator to find
        _write(f, {"tags": ["seed"]}, body if not body.startswith("﻿") else body[1:])
        body_before = _read_body(f)
        augment_user_file_frontmatter(f, {"tags": ["seed", "added"]}, profile={})
        body_after = _read_body(f)
        assert body_before == body_after, f"iter {i}: body bytes diverged"


# ---------------------------------------------------------------------------
# D-04/D-05: idempotent re-augment
# ---------------------------------------------------------------------------

def test_idempotent_reaugment(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"tags": ["a"], "type": "ml"}, profile={})
    _, changed = augment_user_file_frontmatter(
        f, {"tags": ["a"], "type": "ml"}, profile={}
    )
    assert changed == []


# ---------------------------------------------------------------------------
# D-06: stateless re-add (graphify never tracks "I deleted that")
# ---------------------------------------------------------------------------

def test_d06_stateless_readd(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    augment_user_file_frontmatter(f, {"tags": ["a"]}, profile={})
    # User strips the tag manually
    _write(f, {}, "body\n")
    augment_user_file_frontmatter(f, {"tags": ["a"]}, profile={})
    assert _read_fm(f).get("tags") == ["a"]


# ---------------------------------------------------------------------------
# Return contract
# ---------------------------------------------------------------------------

def test_returns_changed_keys_list(tmp_path):
    f = _write(tmp_path / "n.md", {}, "body\n")
    target, changed = augment_user_file_frontmatter(
        f, {"tags": ["a"], "type": "ml"}, profile={}
    )
    assert target == f
    assert set(changed) == {"tags", "type"}
    assert changed == sorted(changed)  # deterministic


# ---------------------------------------------------------------------------
# Atomic write: a write failure must leave the original file intact
# ---------------------------------------------------------------------------

def test_atomic_write(tmp_path, monkeypatch):
    f = _write(tmp_path / "n.md", {"tags": ["a"]}, "body\n")
    original = f.read_bytes()

    import os as _os
    real_replace = _os.replace

    def boom(src, dst):  # noqa: ARG001
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("graphify.augment.os.replace", boom)
    with pytest.raises(RuntimeError):
        augment_user_file_frontmatter(f, {"tags": ["b"]}, profile={})
    assert f.read_bytes() == original
    monkeypatch.setattr("graphify.augment.os.replace", real_replace)
