"""Tests for silent auto-self-heal of the skill stamp.

Covers Phase 59.1 plan 02 decisions D-01..D-06, D-13, D-16..D-18 and threat
mitigation T-59.1.02-02 (oversized stamp size guard).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.__main__ import _check_skill_version, __version__


def _make_skill_dst(tmp_path: Path) -> Path:
    """Create a fake skill destination file path under ``tmp_path``.

    The version stamp lives at ``skill_dst.parent / ".graphify_version"``.
    """
    skill_dst = tmp_path / "skill.md"
    skill_dst.write_text("# stub skill\n", encoding="utf-8")
    return skill_dst


def test_heal_happy_path_silent(tmp_path, capsys):
    """D-16: stamp older than running package is silently rewritten to __version__."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    version_file.write_text("0.4.7", encoding="utf-8")

    result = _check_skill_version(skill_dst)

    assert result is None
    err = capsys.readouterr().err
    assert err == "", f"expected silent heal, got stderr: {err!r}"
    assert version_file.read_text(encoding="utf-8").strip() == __version__


def test_stamp_newer_warning_preserved(tmp_path, capsys):
    """D-18: stamp newer than running package emits warning and is NOT rewritten."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    version_file.write_text("99.99.99", encoding="utf-8")

    _check_skill_version(skill_dst)

    err = capsys.readouterr().err
    assert "newer than the installed package" in err
    # Stamp file content is NOT rewritten downward.
    assert version_file.read_text(encoding="utf-8").strip() == "99.99.99"


def test_write_failure_falls_back_to_warning(tmp_path, capsys, monkeypatch):
    """D-17: if heal-path write_text fails, fall back to the existing two-line warning."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    version_file.write_text("0.4.7", encoding="utf-8")

    real_write_text = Path.write_text

    def _raising_write_text(self, data, *args, **kwargs):
        if self.name == ".graphify_version":
            raise PermissionError("denied")
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _raising_write_text)

    # Must not raise.
    _check_skill_version(skill_dst)

    err = capsys.readouterr().err
    assert "older than the installed package; run 'graphify install'" in err


def test_silent_abort_when_package_version_unresolvable(tmp_path, capsys, monkeypatch):
    """D-05: empty/falsy __version__ -> silent abort, no stamp write, no warning."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    version_file.write_text("0.4.7", encoding="utf-8")

    monkeypatch.setattr("graphify.__main__.__version__", "", raising=False)

    _check_skill_version(skill_dst)

    err = capsys.readouterr().err
    assert err == "", f"expected silent abort, got stderr: {err!r}"
    # Stamp content is unchanged byte-for-byte.
    assert version_file.read_text(encoding="utf-8") == "0.4.7"


def test_missing_stamp_is_noop(tmp_path, capsys):
    """D-02: missing .graphify_version file is a silent no-op."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    assert not version_file.exists()

    _check_skill_version(skill_dst)

    err = capsys.readouterr().err
    assert err == ""
    assert not version_file.exists()


def test_oversized_stamp_treated_as_corrupt(tmp_path, capsys):
    """T-59.1.02-02: stamps larger than 1024 bytes are treated as corrupt (silent)."""
    skill_dst = _make_skill_dst(tmp_path)
    version_file = tmp_path / ".graphify_version"
    version_file.write_bytes(("0.4.7\n" + "x" * 2048).encode("utf-8"))
    assert version_file.stat().st_size > 1024

    _check_skill_version(skill_dst)

    err = capsys.readouterr().err
    # Corrupt is treated as silent fallback (no stderr warning emitted).
    assert err == "", f"expected silent fallback for corrupt stamp, got stderr: {err!r}"
    # Function did not raise.
