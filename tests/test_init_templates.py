"""Phase 21 TMPL-01..05: tests for Excalidraw template stub renderer/writer.

Covers:
- render_stub output shape (frontmatter, ``## Text Elements``, ``## Drawing``)
- compress: false one-way door
- scene JSON parses and has ``type:excalidraw, version:2, source:graphify``
- write_stubs writes 6 files from _DEFAULT_PROFILE
- Idempotency (no --force leaves existing files alone)
- --force overwrites
- Profile subset (3 entries -> 3 files)
- Path traversal blocked (T-21-10 mitigation)
- CLI dispatch via ``python -m graphify --init-diagram-templates`` under tmp_path
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from graphify.excalidraw import render_stub, write_stubs
from graphify.profile import _DEFAULT_PROFILE


# ---------------------------------------------------------------------------
# render_stub
# ---------------------------------------------------------------------------


def test_render_stub_contains_compress_false():
    out = render_stub({"name": "architecture"})
    assert "compress: false" in out
    assert "excalidraw-plugin: parsed" in out


def test_render_stub_has_required_sections():
    out = render_stub({"name": "workflow"})
    assert "## Text Elements" in out
    assert "## Drawing" in out


def test_render_stub_scene_json_parses():
    out = render_stub({"name": "mind-map"})
    m = re.search(r"```json\n(.+?)\n```", out, re.S)
    assert m, "No ```json``` fence in stub"
    scene = json.loads(m.group(1))
    assert scene["type"] == "excalidraw"
    assert scene["version"] == 2
    assert scene["source"] == "graphify"
    assert scene["appState"]["currentItemFontFamily"] == 5


def test_render_stub_sanitizes_label():
    # A label with YAML-special characters must be quoted via
    # safe_frontmatter_value to avoid frontmatter corruption.
    out = render_stub({"name": "evil: name"})
    # Value should be quoted; colon inside name must not break the
    # ``tags:`` YAML line.
    assert "evil" in out
    # No raw newlines or unescaped colon structure breakage:
    lines = [ln for ln in out.splitlines() if ln.startswith("tags:")]
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# write_stubs
# ---------------------------------------------------------------------------


def test_write_stubs_writes_6_files(tmp_path):
    written = write_stubs(tmp_path, _DEFAULT_PROFILE["diagram_types"])
    assert len(written) == 6
    files = list((tmp_path / "Excalidraw" / "Templates").glob("*.excalidraw.md"))
    assert len(files) == 6


def test_write_stubs_idempotent_without_force(tmp_path):
    dts = _DEFAULT_PROFILE["diagram_types"]
    first = write_stubs(tmp_path, dts)
    assert len(first) == 6
    mtimes_before = {p: p.stat().st_mtime_ns for p in first}
    # Small sleep to ensure mtime granularity would detect changes
    time.sleep(0.01)
    second = write_stubs(tmp_path, dts)
    assert second == []
    for p, m in mtimes_before.items():
        assert p.stat().st_mtime_ns == m, f"{p} mtime changed on idempotent run"


def test_write_stubs_force_overwrites(tmp_path):
    dts = _DEFAULT_PROFILE["diagram_types"]
    first = write_stubs(tmp_path, dts)
    assert len(first) == 6
    # Mutate one file so we can detect overwrite
    first[0].write_text("SENTINEL", encoding="utf-8")
    third = write_stubs(tmp_path, dts, force=True)
    assert len(third) == 6
    assert "SENTINEL" not in first[0].read_text(encoding="utf-8")
    assert "compress: false" in first[0].read_text(encoding="utf-8")


def test_write_stubs_profile_subset(tmp_path):
    subset = _DEFAULT_PROFILE["diagram_types"][:3]
    written = write_stubs(tmp_path, subset)
    assert len(written) == 3
    files = list((tmp_path / "Excalidraw" / "Templates").glob("*.excalidraw.md"))
    assert len(files) == 3


def test_write_stubs_path_traversal_blocked(tmp_path):
    bad = [{"name": "evil", "template_path": "../../etc/passwd"}]
    with pytest.raises(ValueError, match="escape vault directory"):
        write_stubs(tmp_path, bad)


# ---------------------------------------------------------------------------
# CLI dispatch (subprocess + tmp_path)
# ---------------------------------------------------------------------------


def _run_cli(*args, cwd):
    """Invoke graphify CLI via `python -m graphify`."""
    env = os.environ.copy()
    # Ensure package import from the repo checkout, not any installed copy
    repo_root = Path(__file__).resolve().parent.parent
    env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def test_cli_init_writes_six_stubs_tmp_path(tmp_path):
    result = _run_cli("--init-diagram-templates", "--vault", str(tmp_path), cwd=tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    stubs = list((tmp_path / "Excalidraw" / "Templates").glob("*.excalidraw.md"))
    assert len(stubs) == 6
    assert "wrote 6 stub" in result.stdout


def test_cli_init_idempotent_second_run_zero(tmp_path):
    first = _run_cli("--init-diagram-templates", "--vault", str(tmp_path), cwd=tmp_path)
    assert first.returncode == 0
    second = _run_cli("--init-diagram-templates", "--vault", str(tmp_path), cwd=tmp_path)
    assert second.returncode == 0
    assert "wrote 0 stub" in second.stdout


def test_cli_init_force_overwrites_six(tmp_path):
    _run_cli("--init-diagram-templates", "--vault", str(tmp_path), cwd=tmp_path)
    forced = _run_cli(
        "--init-diagram-templates", "--vault", str(tmp_path), "--force", cwd=tmp_path
    )
    assert forced.returncode == 0
    assert "wrote 6 stub" in forced.stdout


def test_cli_init_missing_vault_errors(tmp_path):
    result = _run_cli("--init-diagram-templates", cwd=tmp_path)
    assert result.returncode == 2
    assert "--vault" in result.stderr


def test_cli_init_unknown_option_errors(tmp_path):
    result = _run_cli(
        "--init-diagram-templates", "--vault", str(tmp_path), "--bogus", cwd=tmp_path
    )
    assert result.returncode == 2
    assert "unknown" in result.stderr.lower()
