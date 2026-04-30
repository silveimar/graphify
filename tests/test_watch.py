"""Tests for watch.py - file watcher helpers (no watchdog required)."""
import time
from pathlib import Path
import pytest

from graphify.watch import _notify_only, _WATCHED_EXTENSIONS


# --- _notify_only ---

def test_notify_only_creates_flag(tmp_path):
    _notify_only(tmp_path)
    flag = tmp_path / "graphify-out" / "needs_update"
    assert flag.exists()
    assert flag.read_text() == "1"

def test_notify_only_creates_flag_dir(tmp_path):
    # graphify-out dir does not exist yet
    assert not (tmp_path / "graphify-out").exists()
    _notify_only(tmp_path)
    assert (tmp_path / "graphify-out").is_dir()

def test_notify_only_idempotent(tmp_path):
    _notify_only(tmp_path)
    _notify_only(tmp_path)
    flag = tmp_path / "graphify-out" / "needs_update"
    assert flag.read_text() == "1"


# --- _WATCHED_EXTENSIONS ---

def test_watched_extensions_includes_code():
    assert ".py" in _WATCHED_EXTENSIONS
    assert ".ts" in _WATCHED_EXTENSIONS
    assert ".go" in _WATCHED_EXTENSIONS
    assert ".rs" in _WATCHED_EXTENSIONS

def test_watched_extensions_includes_docs():
    assert ".md" in _WATCHED_EXTENSIONS
    assert ".txt" in _WATCHED_EXTENSIONS
    assert ".pdf" in _WATCHED_EXTENSIONS

def test_watched_extensions_includes_images():
    assert ".png" in _WATCHED_EXTENSIONS
    assert ".jpg" in _WATCHED_EXTENSIONS

def test_watched_extensions_excludes_noise():
    assert ".json" not in _WATCHED_EXTENSIONS
    assert ".pyc" not in _WATCHED_EXTENSIONS
    assert ".log" not in _WATCHED_EXTENSIONS


# --- watch() import error without watchdog ---

def test_watch_raises_without_watchdog(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "watchdog.observers" or name == "watchdog.events":
            raise ImportError("mocked missing watchdog")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    from graphify.watch import watch
    with pytest.raises(ImportError, match="watchdog not installed"):
        watch(tmp_path)


# ---------------------------------------------------------------------------
# Plan 15-05 Task 2: opt-in --enrich trigger + atexit cleanup (ENRICH-06, Pitfall 4)
# ---------------------------------------------------------------------------

def test_enrichment_trigger_opt_in(tmp_path, monkeypatch):
    """ENRICH-06: enabled=False spawns nothing; enabled=True spawns exactly one child."""
    import subprocess as _subprocess
    import graphify.watch as watch_mod

    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()

    popen_calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, argv, **kw):
            popen_calls.append(list(argv))
            self.pid = 99999

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            pass

        def kill(self):
            pass

    fake_subprocess = type("M", (), {
        "Popen": _FakePopen,
        "DEVNULL": None,
        "TimeoutExpired": _subprocess.TimeoutExpired,
    })
    monkeypatch.setattr(watch_mod, "subprocess", fake_subprocess)

    watch_mod._active_enrichment_child = None
    try:
        # enabled=False → no call
        watch_mod._maybe_trigger_enrichment(out_dir, enabled=False)
        assert popen_calls == []

        # enabled=True → exactly one call, argv contains 'enrich' + '--graph'
        watch_mod._maybe_trigger_enrichment(out_dir, enabled=True)
        assert len(popen_calls) == 1
        assert "enrich" in popen_calls[0]
        assert "--graph" in popen_calls[0]

        # If a child is still running (poll() is None), subsequent calls skip
        watch_mod._maybe_trigger_enrichment(out_dir, enabled=True)
        assert len(popen_calls) == 1, "prior running child should suppress new spawn"
    finally:
        watch_mod._active_enrichment_child = None


def test_watch_atexit_terminates_child(monkeypatch):
    """Pitfall 4: atexit handler SIGTERMs a still-running enrichment child."""
    import graphify.watch as watch_mod

    terminated: list[bool] = []

    class _RunningChild:
        pid = 12345

        def poll(self):
            return None

        def terminate(self):
            terminated.append(True)

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    watch_mod._active_enrichment_child = _RunningChild()
    try:
        watch_mod._cleanup_on_exit()
        assert terminated == [True]
    finally:
        watch_mod._active_enrichment_child = None


# ---------------------------------------------------------------------------
# Phase 43 (ELIC-02): watch rebuild merges elicitation sidecar
# ---------------------------------------------------------------------------


def test_rebuild_code_includes_elicitation_sidecar_nodes(tmp_path):
    """ELIC-02: watch rebuild merges graphify-out/elicitation.json before build."""
    import json

    from graphify.elicit import (
        build_extraction_from_session,
        run_scripted_elicitation,
        save_elicitation_sidecar,
    )
    from graphify.watch import _rebuild_code

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "tiny.py").write_text(
        "def foo():\n    return 42\n",
        encoding="utf-8",
    )
    out = proj / "graphify-out"
    out.mkdir(parents=True)
    session = run_scripted_elicitation(
        {
            "rhythms": "Daily standup, weekly retro",
            "decisions": "Prefer small PRs",
            "dependencies": "Platform team for deploys",
            "knowledge": "Internal runbooks are outdated",
            "friction": "Context switching",
        },
        auto_confirm=True,
    )
    ext = build_extraction_from_session(session)
    save_elicitation_sidecar(out, ext, force=True)

    ok = _rebuild_code(proj)
    assert ok is True
    graph_path = out / "graph.json"
    assert graph_path.exists()
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    node_ids = {n["id"] for n in data.get("nodes", [])}
    assert "elicitation_hub" in node_ids
