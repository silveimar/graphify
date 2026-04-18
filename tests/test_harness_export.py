"""Phase 13 — SEED-002 harness export (HARNESS-01..06)."""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from graphify.harness_export import (
    ANNOTATION_ALLOW_LIST,
    _filter_annotations_allowlist,
    _normalize_placeholders,
    export_claude_harness,
)

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "harness"


def _copy_fixtures(dest: Path) -> None:
    """Copy all harness fixture files into ``dest`` (flat)."""
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ("graph.json", "annotations.jsonl", "agent-edges.json", "telemetry.json"):
        shutil.copy(_FIXTURE_DIR / fname, dest / fname)


class _FrozenDatetime:
    """Test shim: deterministic datetime for byte-equality assertions."""

    _frozen = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz: timezone | None = None) -> datetime:  # pragma: no cover - trivial
        return cls._frozen


def _frozen_clock() -> datetime:
    return datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# HARNESS-01 / HARNESS-05: writes three files with canonical filenames
# ---------------------------------------------------------------------------


def test_export_writes_three_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    written = export_claude_harness(out_dir)

    assert len(written) == 3
    assert [p.name for p in written] == [
        "claude-SOUL.md",
        "claude-HEARTBEAT.md",
        "claude-USER.md",
    ]
    for p in written:
        assert p.exists(), f"expected {p} to exist"
        assert p.parent == out_dir / "harness"
    # Content sanity: SOUL file mentions god nodes heading from the schema.
    soul = (out_dir / "harness" / "claude-SOUL.md").read_text(encoding="utf-8")
    assert "God Nodes" in soul
    assert "Transformer" in soul  # label for the top-degree node in fixture


# ---------------------------------------------------------------------------
# T-13-05: output confined to graphify-out/ (path escape fails cleanly)
# ---------------------------------------------------------------------------


def test_output_confined_to_graphify_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    def _raise_escape(*_a, **_kw):
        raise ValueError(
            "Path '/escape' escapes the allowed directory. Only paths inside "
            "graphify-out/ are permitted."
        )

    monkeypatch.setattr(
        "graphify.harness_export.validate_graph_path", _raise_escape
    )

    with pytest.raises(ValueError, match="escapes the allowed directory"):
        export_claude_harness(out_dir)

    # Nothing was written under the harness dir (beyond the mkdir itself).
    harness_dir = out_dir / "harness"
    if harness_dir.exists():
        assert list(harness_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# HARNESS-06 / T-13-04: annotations allow-list filters secrets by default
# ---------------------------------------------------------------------------


def test_annotations_allow_list_default() -> None:
    annotations = [
        {
            "id": "n1",
            "label": "Node1",
            "peer_id": "SECRET_PEER",
            "body": "free-text leak with api_key=sk-LEAK",
        }
    ]
    filtered = _filter_annotations_allowlist(annotations)
    assert filtered == [{"id": "n1", "label": "Node1"}]
    payload = json.dumps(filtered)
    assert "SECRET_PEER" not in payload
    assert "free-text leak" not in payload
    assert "sk-LEAK" not in payload
    assert ANNOTATION_ALLOW_LIST == frozenset(
        {"id", "label", "source_file", "relation", "confidence"}
    )


# ---------------------------------------------------------------------------
# HARNESS-03: placeholder token regex normalization
# ---------------------------------------------------------------------------


def test_placeholder_token_regex_normalization() -> None:
    assert _normalize_placeholders("{{ god_nodes }}") == "${god_nodes}"
    assert _normalize_placeholders("{{god_nodes}}") == "${god_nodes}"
    assert _normalize_placeholders("{{  spaced  }}") == "${spaced}"
    assert _normalize_placeholders("no tokens here") == "no tokens here"
    # Single $ sigil is untouched — regex only matches double-brace tokens.
    assert _normalize_placeholders("$already_dollar") == "$already_dollar"


# ---------------------------------------------------------------------------
# T-13-06: deterministic output across runs with a pinned clock
# ---------------------------------------------------------------------------


def test_deterministic_output_across_runs(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    _copy_fixtures(out1)
    _copy_fixtures(out2)

    export_claude_harness(out1, _clock=_frozen_clock)
    export_claude_harness(out2, _clock=_frozen_clock)

    for fname in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md"):
        a = (out1 / "harness" / fname).read_bytes()
        b = (out2 / "harness" / fname).read_bytes()
        assert a == b, f"byte-equality broken for {fname}"


# ---------------------------------------------------------------------------
# Locked decision: no Jinja2 touched during harness export module import
# ---------------------------------------------------------------------------


def test_no_jinja2_import() -> None:
    # Jinja2 may already be imported transitively by other tests in the
    # session; the contract is that *our* module never imports it.
    removed = sys.modules.pop("graphify.harness_export", None)
    jinja_was_present = "jinja2" in sys.modules
    importlib.import_module("graphify.harness_export")
    if not jinja_was_present:
        assert "jinja2" not in sys.modules, (
            "graphify.harness_export must not import jinja2"
        )
    # Hard guard regardless of prior state — the module text must not import it.
    source = (
        Path(__file__).resolve().parent.parent
        / "graphify"
        / "harness_export.py"
    ).read_text(encoding="utf-8")
    assert "import jinja2" not in source
    assert "from jinja2" not in source
    # Restore original module so no test state leaks.
    if removed is not None:
        sys.modules["graphify.harness_export"] = removed


# ---------------------------------------------------------------------------
# HARNESS-04: CLI subcommand dispatcher invokes the exporter
# ---------------------------------------------------------------------------


def test_cli_harness_export_invokes_exporter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    monkeypatch.setattr(
        sys, "argv", ["graphify", "harness", "export", "--out", str(out_dir)]
    )

    from graphify import __main__ as g_main

    with pytest.raises(SystemExit) as exc:
        g_main.main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    out_lines = [ln for ln in captured.out.splitlines() if ln.strip()]
    # All three canonical paths printed in SOUL/HEARTBEAT/USER order.
    assert len(out_lines) == 3
    assert out_lines[0].endswith("claude-SOUL.md")
    assert out_lines[1].endswith("claude-HEARTBEAT.md")
    assert out_lines[2].endswith("claude-USER.md")

    for fname in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md"):
        assert (out_dir / "harness" / fname).exists()
