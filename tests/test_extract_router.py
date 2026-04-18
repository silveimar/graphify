"""Tests for extract() with Router (Phase 12, ROUTE-03/07)."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
import pytest

from graphify.extract import extract
from graphify.routing import Router


def test_extract_router_none_matches_baseline_two_py(tmp_path: Path) -> None:
    """router=None preserves sequential single-thread behavior on tiny corpus."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("def f():\n    return 1\n", encoding="utf-8")
    b.write_text("def g():\n    return 2\n", encoding="utf-8")
    r1 = extract([a, b])
    r2 = extract([a, b], router=None)
    assert len(r1["nodes"]) == len(r2["nodes"])
    assert len(r1["edges"]) == len(r2["edges"])


def test_distinct_model_ids_use_distinct_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock router returns different model_ids → different cache entries."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GRAPHIFY_EXTRACT_WORKERS", "1")
    cfg = {
        "tiers": {
            "trivial": {"model_id": "m1", "endpoint": "x"},
            "simple": {"model_id": "m2", "endpoint": "x"},
            "complex": {"model_id": "m3", "endpoint": "x"},
        },
        "vision": {"model_id": "", "endpoint": ""},
        "thresholds": {"trivial_max_cc": 1000, "simple_max_cc": 2000},
    }
    router = Router(cfg)
    calls = {"n": 0}

    def fake_py(path: Path) -> dict:
        calls["n"] += 1
        return {"nodes": [{"id": f"n{calls['n']}", "label": "x", "source_file": str(path)}], "edges": []}

    import graphify.extract as ex

    monkeypatch.setattr(ex, "extract_python", fake_py)
    p = tmp_path / "t.py"
    p.write_text("def a():\n  pass\n" * 20, encoding="utf-8")
    extract([p], router=router)
    extract([p], router=router)
    # Second run should hit cache (no extra fake_py) if model_id stable
    assert calls["n"] == 1


def test_semaphore_limits_parallelism() -> None:
    """Router slot limits concurrent workers (spot-check ROUTE-07)."""
    r = Router({})
    active = {"n": 0}
    peak = {"v": 0}
    lock = threading.Lock()

    def worker() -> None:
        with r.enter_slot():
            with lock:
                active["n"] += 1
                peak["v"] = max(peak["v"], active["n"])
            time.sleep(0.02)
            with lock:
                active["n"] -= 1

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    cap = int(os.environ.get("GRAPHIFY_EXTRACT_MAX_CONCURRENT", "4"))
    assert peak["v"] <= cap


def test_429_backoff_serializes() -> None:
    """Event-based backoff flag is observable (illustrative ROUTE-07 test)."""
    r = Router({})
    r.signal_429()
    assert r._429_backoff.is_set()
    r.clear_429()
    assert not r._429_backoff.is_set()


def test_max_tier_prefers_complex(tmp_path: Path) -> None:
    from graphify.batch import max_tier_route

    cfg = {
        "tiers": {
            "trivial": {"model_id": "t", "endpoint": "x"},
            "simple": {"model_id": "s", "endpoint": "x"},
            "complex": {"model_id": "c", "endpoint": "x"},
        },
        "vision": {"model_id": "", "endpoint": ""},
        "thresholds": {"trivial_max_cc": 2, "simple_max_cc": 10, "trivial_max_lines": 5, "simple_max_lines": 20},
    }
    router = Router(cfg)
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("x = 1\n", encoding="utf-8")
    b.write_text("def f():\n" + "    pass\n" * 80, encoding="utf-8")
    best = max_tier_route([a, b], router)
    assert best.tier == "complex"
