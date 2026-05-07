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


@pytest.mark.audit_v112
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


# ------------------------------------------------------------------
# Plan 03 tests: --version block, doctor section, corrupt rendering,
# --help regression guard. (VSYNC-02, VSYNC-03, T-59.1.03-02, D-10.)
# ------------------------------------------------------------------
import subprocess
import sys as _sys

import graphify.__main__ as gmain


def _fake_two_platform_config(tmp_path: Path) -> dict:
    """Build a 2-platform _PLATFORM_CONFIG fixture under ``tmp_path``."""
    return {
        "fake_claude": {
            "skill_file": "skill.md",
            "skill_dst": Path("fake_claude") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
        "fake_codex": {
            "skill_file": "skill.md",
            "skill_dst": Path("fake_codex") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
    }


def test_render_version_block_multi_line(tmp_path, monkeypatch):
    """D-19: multi-line --version block contains pkg, stamps, python, install."""
    cfg = _fake_two_platform_config(tmp_path)
    # fake_claude installed with stamp 0.4.7
    (tmp_path / "fake_claude").mkdir()
    (tmp_path / "fake_claude" / ".graphify_version").write_text("0.4.7", encoding="utf-8")
    # fake_codex deliberately not installed

    monkeypatch.setattr(gmain, "_PLATFORM_CONFIG", cfg)
    out = gmain._render_version_block(home=tmp_path)

    assert out.startswith(f"graphify {gmain.__version__}")
    assert "skill stamps:" in out
    assert "0.4.7" in out
    assert "(not installed)" in out
    assert "python:" in out
    assert "install:" in out
    # Path should be rendered with ~ shortening since install_dir is under home
    assert "~/fake_claude" in out


def test_version_flag_does_not_write_stamp(tmp_path, monkeypatch):
    """D-10: graphify --version is side-effect-free (no .graphify_version write)."""
    cfg = _fake_two_platform_config(tmp_path)
    (tmp_path / "fake_claude").mkdir()
    stamp = tmp_path / "fake_claude" / ".graphify_version"
    stamp.write_text("0.4.7", encoding="utf-8")
    mtime_before = stamp.stat().st_mtime_ns
    content_before = stamp.read_bytes()

    monkeypatch.setattr(gmain, "_PLATFORM_CONFIG", cfg)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(_sys, "argv", ["graphify", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        gmain.main()
    assert exc_info.value.code == 0

    # Stamp content and mtime are unchanged (no heal write occurred).
    assert stamp.read_bytes() == content_before
    assert stamp.stat().st_mtime_ns == mtime_before


def test_render_version_block_handles_corrupt_stamp(tmp_path, monkeypatch):
    """T-59.1.03-02: oversized stamp renders as ``<corrupt>``; helper does not raise."""
    cfg = _fake_two_platform_config(tmp_path)
    (tmp_path / "fake_claude").mkdir()
    (tmp_path / "fake_claude" / ".graphify_version").write_bytes(b"x" * 2048)

    monkeypatch.setattr(gmain, "_PLATFORM_CONFIG", cfg)
    out = gmain._render_version_block(home=tmp_path)

    assert "<corrupt>" in out
    # The fake_claude row should carry the <corrupt> token.
    assert "fake_claude: <corrupt>" in out


def test_version_flag_help_regression(tmp_path):
    """D-10: graphify --help still works post-flag-add (regression guard)."""
    r_help = subprocess.run(
        [_sys.executable, "-m", "graphify", "--help"],
        capture_output=True,
    )
    assert r_help.returncode == 0
    assert b"usage" in r_help.stdout.lower()

    # Sanity: --version does NOT print a help-style usage banner.
    r_ver = subprocess.run(
        [_sys.executable, "-m", "graphify", "--version"],
        capture_output=True,
    )
    assert r_ver.returncode == 0
    assert b"usage:" not in r_ver.stdout.lower()
    assert b"graphify " in r_ver.stdout  # package line present


def test_doctor_version_sync_section(tmp_path, monkeypatch):
    """D-12: doctor version-sync section emits per-platform status with all states."""
    cfg = {
        "in_sync_plat": {
            "skill_file": "skill.md",
            "skill_dst": Path("in_sync_plat") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
        "newer_plat": {
            "skill_file": "skill.md",
            "skill_dst": Path("newer_plat") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
        "absent_plat": {
            "skill_file": "skill.md",
            "skill_dst": Path("absent_plat") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
    }
    (tmp_path / "in_sync_plat").mkdir()
    (tmp_path / "in_sync_plat" / ".graphify_version").write_text(
        gmain.__version__, encoding="utf-8"
    )
    (tmp_path / "newer_plat").mkdir()
    (tmp_path / "newer_plat" / ".graphify_version").write_text("99.99.99", encoding="utf-8")
    # absent_plat: no dir, no stamp

    monkeypatch.setattr(gmain, "_PLATFORM_CONFIG", cfg)
    out = gmain._render_doctor_version_sync(home=tmp_path)

    assert "version sync" in out
    assert "✓ in sync" in out
    assert "! drifted-newer" in out
    assert "— not installed" in out
    assert f"package={gmain.__version__}" in out


def test_doctor_version_sync_renders_corrupt_stamp(tmp_path, monkeypatch):
    """T-59.1.03-02: doctor renders oversized stamp as <corrupt> with drifted-newer status."""
    cfg = {
        "corrupt_plat": {
            "skill_file": "skill.md",
            "skill_dst": Path("corrupt_plat") / "SKILL.md",
            "claude_md": False,
            "commands_src_dir": "commands",
            "commands_dst": None,
            "commands_enabled": False,
            "supports": ["code"],
        },
    }
    (tmp_path / "corrupt_plat").mkdir()
    (tmp_path / "corrupt_plat" / ".graphify_version").write_bytes(b"x" * 2048)

    monkeypatch.setattr(gmain, "_PLATFORM_CONFIG", cfg)
    out = gmain._render_doctor_version_sync(home=tmp_path)

    assert "<corrupt>" in out
    assert "! drifted-newer" in out
