# Phase 15: Async Background Enrichment - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 9 (5 new, 4 modified)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/enrich.py` | new-module (orchestrator + 4 passes) | batch, file-I/O, request-response (LLM) | `graphify/routing.py` | role-match (standalone module, YAML config, sidecar write) |
| `graphify/__main__.py` | CLI-subcommand extension | request-response | `graphify/__main__.py` (harness/capability dispatch) | exact (same file, add `elif cmd == "enrich":`) |
| `graphify/serve.py` | service-extension (overlay merge + mtime watch) | request-response, event-driven | `graphify/serve.py` (`_maybe_reload_dedup`, `_reload_if_stale`) | exact (same file, extend existing patterns) |
| `graphify/watch.py` | service-extension (post-rebuild trigger hook) | event-driven | `graphify/watch.py` (`_rebuild_code` + `watch()`) | exact (same file, extend `_rebuild_code`) |
| `graphify/cache.py` | utility-extension (enrichment cache key) | batch | `graphify/cache.py` (`file_hash`, `save_cached`) | exact (same file, add pass_name to key) |
| `tests/test_enrich.py` | test-unit | CRUD, request-response | `tests/test_routing.py` | exact (same shape: imports, unit assertions, grep-CI function) |
| `tests/test_enrichment_lifecycle.py` | test-integration | event-driven, subprocess | `tests/test_main_cli.py` + `tests/test_delta.py` | role-match (subprocess fixture, timeout=30, check=False) |
| `tests/test_enrich_invariant.py` | test-invariant | file-I/O | `tests/test_routing.py::test_grep_router_api` | role-match (read source, assert key symbol absent) |
| `tests/test_enrich_grep_guard.py` | test-grep-CI | file-I/O | `tests/test_routing.py::test_grep_router_api` | exact (read source files, assert caller whitelist) |

---

## Pattern Assignments

### `graphify/enrich.py` (new-module, orchestrator + 4 passes)

**Analog:** `graphify/routing.py`

**Imports pattern** (`routing.py` lines 1-18):
```python
"""Per-file complexity classification and model routing (Phase 12, ROUTE-01..07)."""
from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:
    yaml = None  # type: ignore[assignment]
    _YAML_ERR = e
else:
    _YAML_ERR = None
```
For `enrich.py`: replace yaml-optional block with fcntl/signal/json imports. All are stdlib — no optional-import guard needed. Add `import fcntl`, `import signal`, `import json`, `from datetime import datetime, timezone`.

**Module-level function shape** (`routing.py` lines 75-85 — `load_routing_config`):
```python
def load_routing_config(path: Path | None = None) -> dict[str, Any]:
    """Load routing YAML via yaml.safe_load only (no eval). Merges safe defaults."""
    if yaml is None:
        raise ImportError(
            "graphify routing requires PyYAML — pip install 'graphifyy[routing]' or PyYAML"
        ) from _YAML_ERR
    p = path or _package_yaml_path()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return dict(_DEFAULT_CONFIG)
    return raw
```
For `enrich.py`: the entry-point function `run(graph_path, out_dir, budget, pass_filter, dry_run)` follows the same shape — accepts Path arguments, validates, dispatches.

**Atomic sidecar write — canonical pattern** (`routing_audit.py` lines 34-56):
```python
def flush(self, out_dir: Path) -> Path:
    """Write routing.json under out_dir using atomic replace."""
    out_dir = Path(out_dir).resolve()
    cwd = Path.cwd().resolve()
    try:
        out_dir.relative_to(cwd)
    except ValueError as e:
        raise ValueError(
            f"routing audit output path {out_dir} escapes working directory {cwd}"
        ) from e
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "files": dict(sorted(self._files.items()))}
    dest = out_dir / "routing.json"
    tmp = dest.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return dest
```
**Copy verbatim** for `_commit_pass(out_dir, snapshot_id, pass_name, result)` in `enrich.py`. Replace `routing.json` with `enrichment.json`. The tmp suffix must be `.json.tmp` (not `.tmp`) to match existing convention.

**cache.py atomic write** (`cache.py` lines 94-110 — `save_cached`):
```python
def save_cached(path, result, root=Path("."), *, model_id="") -> None:
    key = file_hash(path, model_id=model_id)
    entry = cache_dir(root) / _cache_json_filename(key)
    tmp = entry.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result), encoding="utf-8")
        os.replace(tmp, entry)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```
For enrichment cache: call `save_cached(Path(source_file), {pass_name: enriched_text}, root, model_id=model_id)`. Key already includes `model_id` from Phase 12.

**Staleness pass reuse** (`delta.py` lines 68-98 — `classify_staleness`):
```python
def classify_staleness(node_data: dict) -> str:
    """Classify a node as FRESH, STALE, or GHOST based on source file state."""
    source_file = node_data.get("source_file", "")
    stored_hash = node_data.get("source_hash")
    if not source_file or not stored_hash:
        return "FRESH"
    p = Path(source_file)
    if not p.exists():
        return "GHOST"
    try:
        current_mtime = p.stat().st_mtime
        stored_mtime = node_data.get("source_mtime")
        if stored_mtime is not None and isinstance(stored_mtime, float) and current_mtime == stored_mtime:
            return "FRESH"
    except OSError:
        return "GHOST"
    from .cache import file_hash
    try:
        current_hash = file_hash(p)
    except OSError:
        return "GHOST"
    return "FRESH" if current_hash == stored_hash else "STALE"
```
**Reuse verbatim** — call `delta.classify_staleness(node_data)` for every node in the staleness pass. Do not reimplement.

**Snapshot enumeration** (`snapshot.py` lines 48-62 — `list_snapshots`):
```python
def list_snapshots(project_root: Path = Path(".")) -> list[Path]:
    """Return sorted list of snapshot Paths (oldest first by mtime)."""
    if Path(project_root).name == "graphify-out":
        raise ValueError(...)   # CR-01 guard
    d = snapshots_dir(project_root)
    snaps = list(d.glob("*.json"))
    snaps.sort(key=lambda p: p.stat().st_mtime)
    return snaps
```
For patterns pass: `list_snapshots(project_root)[-5:]` to get last 5. Always pass `project_root` (the directory CONTAINING `graphify-out/`), never `out_dir` itself.

**snapshot_id pinning scheme** (`snapshot.py` lines 63-76 — `save_snapshot`): The `snapshot_id` is `target.stem` (e.g., `"2026-04-20T14-30-00"` or `"2026-04-20T14-30-00_label"`). Pin at process start with `pinned_id = list_snapshots(project_root)[-1].stem`.

**fcntl.flock pattern** (no existing analog in codebase — RESEARCH.md RQ-2):
```python
import fcntl

# Enrichment process acquires on startup:
fd = open(out_dir / ".enrichment.lock", "w")
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    fd.close()
    print("[graphify enrich] Another enrichment run is active — aborting.", file=sys.stderr)
    sys.exit(1)

# SIGTERM handler (module-level globals for signal handler access):
_lock_fd: int | None = None
_current_tmp: Path | None = None

def _install_sigterm(lock_fd: int) -> None:
    global _lock_fd
    _lock_fd = lock_fd
    def _handler(sig, frame):
        if _current_tmp and _current_tmp.exists():
            _current_tmp.unlink(missing_ok=True)
        if _lock_fd is not None:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        sys.exit(1)
    signal.signal(signal.SIGTERM, _handler)
```

**Error handling pattern** (mirrors `routing.py` and `security.py`):
```python
# Domain-specific exceptions with clear messages
raise ValueError(f"[graphify enrich] graph.json not found: {graph_path}")
# Warning to stderr
print(f"[graphify enrich] budget exhausted after description pass", file=sys.stderr)
```

---

### `graphify/__main__.py` — add `graphify enrich` subcommand

**Analog:** Same file — `elif cmd == "capability":` block (lines 1760-1773) and `elif cmd == "harness":` block (lines 1788-1819).

**Argparse subcommand registration pattern** (`__main__.py` lines 1788-1819 — harness dispatch):
```python
elif cmd == "harness":
    rest = list(sys.argv[2:])
    if not rest or rest[0] != "export":
        print("Usage: ...", file=sys.stderr)
        sys.exit(2)

    import argparse as _ap
    from graphify.harness_export import export_claude_harness

    parser = _ap.ArgumentParser(prog="graphify harness export")
    parser.add_argument("--target", default="claude", choices=["claude"])
    parser.add_argument("--out", default="graphify-out")
    parser.add_argument("--include-annotations", action="store_true")
    opts = parser.parse_args(rest[1:])

    out_dir = Path(opts.out).resolve()
    try:
        written = export_claude_harness(out_dir, target=opts.target, ...)
    except ValueError as exc:
        print(f"[graphify] {exc}", file=sys.stderr)
        sys.exit(3)
    for p in written:
        print(str(p))
    sys.exit(0)
```
For `enrich`:
```python
elif cmd == "enrich":
    import argparse as _ap
    from graphify.enrich import run as _enrich_run

    parser = _ap.ArgumentParser(prog="graphify enrich")
    parser.add_argument("--graph", default="graphify-out/graph.json")
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--pass", dest="pass_filter",
                        choices=["description", "patterns", "community", "staleness"],
                        default=None)
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args(sys.argv[2:])

    graph_path = Path(opts.graph).resolve()
    out_dir = graph_path.parent
    # Acquire foreground .enrichment.lock before launch (foreground wins per CONTEXT §Specifics)
    import fcntl as _fcntl
    lock_path = out_dir / ".enrichment.lock"
    lock_path.touch(exist_ok=True)
    lock_fd = open(lock_path, "w")
    try:
        _fcntl.flock(lock_fd, _fcntl.LOCK_EX)  # blocking — wait for enrichment to release
    except OSError as exc:
        print(f"[graphify] Could not acquire enrichment lock: {exc}", file=sys.stderr)
        sys.exit(1)
    # Lock held: enrichment subprocess has exited or been killed before we reach here
    _enrich_run(graph_path, out_dir, opts.budget, opts.pass_filter, opts.dry_run)
    sys.exit(0)
```

**Help text registration pattern** (`__main__.py` lines 1030-1057 — `print("Commands:...")` block):
Add one line:
```python
print("  enrich [--graph P] --budget N [--pass X] [--dry-run]  Run 4 enrichment passes (Phase 15)")
```
Follow the same column alignment as existing `snapshot` and `capability` lines.

**to_json / _write_graph_json whitelist** (`export.py` lines 287-303 — `to_json`): `enrich.py` must NEVER import or call `to_json`. The grep-CI test (`test_enrich_grep_guard.py`) asserts that only `build.py` and `__main__.py` call `to_json`. Verified: `__main__.py` calls `to_json` via `from graphify.export import to_json` in the `watch.py` rebuild path (`watch.py` line 78: `to_json(G, communities, str(out / "graph.json"))`).

---

### `graphify/serve.py` — implement `_load_enrichment_overlay` + extend `_reload_if_stale`

**Analog:** Same file — `_maybe_reload_dedup` (lines 1941+49 = ~1990) and `_reload_if_stale` (lines 1941-1958).

**`_reload_if_stale` mtime-watch pattern to extend** (`serve.py` lines 1941-1958):
```python
def _reload_if_stale() -> None:
    """Reload G and communities if graph.json mtime has changed (D-13)."""
    nonlocal G, communities, _graph_mtime, _branching_factor
    try:
        mtime = os.stat(graph_path).st_mtime
    except OSError:
        return
    if mtime != _graph_mtime:
        G = _load_graph(graph_path)
        communities = _communities_from_graph(G)
        _branching_factor = _compute_branching_factor(G)
        _graph_mtime = mtime
```
For ENRICH-09: add a parallel `_enrichment_mtime: float = 0.0` closure var (alongside `_graph_mtime`). Extend `_reload_if_stale` to also check `(_out_dir / "enrichment.json").stat().st_mtime` and reload overlay when changed. Follow the exact `try/except OSError: return` guard.

**`_maybe_reload_dedup` — mtime-watcher pattern** (`serve.py` lines ~1990-2003):
```python
def _maybe_reload_dedup() -> None:
    nonlocal _alias_map, _dedup_mtime
    p = _out_dir / "dedup_report.json"
    try:
        mt = p.stat().st_mtime if p.exists() else 0.0
    except OSError:
        mt = 0.0
    if mt != _dedup_mtime:
        _alias_map = _load_dedup_report(_out_dir)
        _dedup_mtime = mt
```
Copy this exact pattern for `_enrichment_mtime` tracking. The overlay dict is reloaded when `enrichment.json` mtime changes.

**`_enrichment_snapshot_id` scaffold** (`serve.py` lines 2325-2335 — already present):
```python
def _enrichment_snapshot_id() -> str | None:
    p = _out_dir / "enrichment.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    sid = data.get("snapshot_id", data.get("version"))
    return str(sid) if sid is not None else None
```
This scaffold is already written. `_load_enrichment_overlay` follows the same `json.loads` + `try/except (json.JSONDecodeError, OSError)` pattern.

**`_load_graph` insertion point** (`serve.py` lines 431-448): `_load_enrichment_overlay(out_dir)` is called AFTER `G = _load_graph(graph_path)` at line 1918 inside `serve()`. Add at line 1919 (immediately after):
```python
G = _load_graph(graph_path)
_overlay = _load_enrichment_overlay(_out_dir)  # additive, augments G node attrs
```

**Overlay merge policy** (D-06 — `enriched_description` not overwriting `description`):
```python
def _load_enrichment_overlay(out_dir: Path) -> dict:
    """Load enrichment.json passes dict; return empty dict if missing/corrupt."""
    p = out_dir / "enrichment.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data.get("passes", {})
```
When surfacing in MCP responses: add `enriched_description` only, never mutate `description` on the graph node.

---

### `graphify/watch.py` — opt-in post-rebuild enrichment trigger

**Analog:** Same file — `_rebuild_code(watch_path)` (lines 14-92) and `watch()` (lines 110-173).

**Post-rebuild hook extension pattern** (`watch.py` lines 158-168 — `watch()` debounce loop):
```python
try:
    while True:
        time.sleep(0.5)
        if pending and (time.monotonic() - last_trigger) >= debounce:
            pending = False
            batch = list(changed)
            changed.clear()
            print(f"\n[graphify watch] {len(batch)} file(s) changed")
            if _has_non_code(batch):
                _notify_only(watch_path)
            else:
                _rebuild_code(watch_path)
```
For ENRICH-06: add `enrich_budget: int | None = None` parameter to `watch()` and `_rebuild_code()`. After `_rebuild_code(watch_path)` succeeds, trigger enrichment via `subprocess.Popen` only when `enrich_budget is not None`:
```python
# watch.py — extend _rebuild_code signature:
def _rebuild_code(watch_path: Path, *, enrich_budget: int | None = None,
                  follow_symlinks: bool = False) -> bool:
    ...
    ok = True   # (existing return True path)
    if ok and enrich_budget is not None:
        import subprocess
        subprocess.Popen(
            [sys.executable, "-m", "graphify", "enrich",
             "--budget", str(enrich_budget),
             "--graph", str(watch_path / "graphify-out" / "graph.json")],
        )
    return ok
```
`Popen` (not `run`) so the watch loop is not blocked. Not detached — parent (watch loop) stays alive; Ctrl-C kills both. No new daemon process or apscheduler.

---

### `graphify/cache.py` — extend hash inputs for enrichment

**Analog:** Same file — `file_hash(path, model_id="")` (lines 58-67) and `_cache_key_string` (lines 44-48).

**Current hash key composition** (`cache.py` lines 44-48):
```python
def _cache_key_string(inner: str, model_id: str) -> str:
    """ROUTE-04: returned file_hash string; empty model_id preserves legacy 64-char hex."""
    if not model_id:
        return inner
    return f"{inner}:{model_id}"
```

**Extension for enrichment** — add `pass_name` as a third key component:
```python
def enrichment_cache_key(node_id: str, pass_name: str, model_id: str, source_file_hash: str) -> str:
    """Stable cache key for per-(node_id, pass, model_id) enrichment results.

    Composed as sha256(node_id + pass_name + model_id + source_file_hash) to
    avoid ':' collisions and stay filesystem-safe.
    """
    raw = f"{node_id}\x00{pass_name}\x00{model_id}\x00{source_file_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```
This follows `_cache_json_filename`'s pattern of hashing composite keys when `:` separators would be ambiguous. The enrichment cache entry stores `{pass_name: enriched_text}` and is keyed by this function.

**Existing save_cached pattern to call** (`cache.py` lines 94-110): Use `save_cached(source_file_path, result_dict, root, model_id=model_id)` directly for per-source-file enrichment results — the Phase 12 `model_id` participation is already present. The `pass_name` compound key is needed only when caching per-node results independently of the source file.

---

### `tests/test_enrich.py` (test-unit, CRUD/request-response)

**Analog:** `tests/test_routing.py`

**File header and imports pattern** (`test_routing.py` lines 1-16):
```python
"""Tests for graphify/routing.py (Phase 12, ROUTE-01/02/06/10)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from graphify.routing import (
    CODE_SUFFIXES,
    Router,
    classify_file,
    load_routing_config,
    resolve_model,
    tier_rank,
)
```
For `test_enrich.py`:
```python
"""Tests for graphify/enrich.py (Phase 15, ENRICH-01..12)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from graphify.enrich import run, PassResult   # adjust to actual public API
```

**Unit test shape** (`test_routing.py` lines 19-21, `test_yaml_loads` at 23-26):
```python
def test_tier_order_deterministic() -> None:
    assert tier_rank("trivial") < tier_rank("simple") < tier_rank("complex") < tier_rank("vision")

def test_yaml_loads() -> None:
    cfg = load_routing_config()
    assert "tiers" in cfg
    assert "trivial" in cfg["tiers"]
```
For `test_enrich.py` — same flat function style, `tmp_path` fixture for I/O tests:
```python
def test_cli_missing_graph(tmp_path) -> None:
    """ENRICH-01: exits non-zero with actionable error when graph.json missing."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "enrich", "--budget", "1000",
         "--graph", str(tmp_path / "graphify-out" / "graph.json")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "graph.json" in result.stderr or "not found" in result.stderr
```

**grep-CI test pattern** (`test_routing.py` lines 85-91):
```python
def test_grep_router_api() -> None:
    from graphify import routing as R
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert "def classify_file" in src
    assert "def resolve_model" in src
    assert "class Router" in src
```
For `test_enrich.py` — smoke imports check:
```python
def test_enrich_public_api() -> None:
    from graphify import enrich as E
    src = Path(E.__file__).read_text(encoding="utf-8")
    assert "def run" in src
    assert "_commit_pass" in src
    assert "fcntl" in src
```

---

### `tests/test_enrichment_lifecycle.py` (test-integration, subprocess/event-driven)

**Analog:** `tests/test_main_cli.py` (subprocess fixture) + `tests/test_delta.py` (subprocess.run + assertions)

**Subprocess fixture pattern** (`test_main_cli.py` lines 29-39):
```python
def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke `python -m graphify <args...>` and return the completed process.

    Uses check=False so the caller owns exit-code assertions.
    """
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        capture_output=True,
        text=True,
        check=False,
    )
```
Copy verbatim. All lifecycle tests use `_run_cli("enrich", "--budget", "1000", "--graph", str(graph_path))`.

**Integration test with timeout** (`test_delta.py` lines 247-260):
```python
def test_cli_snapshot_saves_file(tmp_path):
    ...
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "snapshot", "--graph", str(graph_json)],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
```
All lifecycle tests use `timeout=30` and `cwd=str(tmp_path)`. The flock race test uses `threading` (not subprocess) per RESEARCH.md RQ-2 pattern:
```python
def test_flock_race(tmp_path) -> None:
    """ENRICH-04: concurrent second enrich attempt gets BlockingIOError."""
    import fcntl, threading
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    lock_path = out_dir / ".enrichment.lock"
    lock_path.write_text("")

    first_fd = open(lock_path, "w")
    fcntl.flock(first_fd, fcntl.LOCK_EX)
    with pytest.raises(BlockingIOError):
        second_fd = open(lock_path, "w")
        fcntl.flock(second_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(first_fd, fcntl.LOCK_UN)
    first_fd.close()
```

**conftest.py fixture pattern** (`conftest.py` lines 75-120 — `make_snapshot_chain`):
```python
@pytest.fixture
def make_snapshot_chain(tmp_path):
    """Factory fixture: create a chain of N synthetic snapshots under root."""
    import networkx as nx
    from graphify.snapshot import save_snapshot

    def _make(n: int = 3, project_root=None) -> list[Path]:
        base = Path(project_root) if project_root else tmp_path
        paths = []
        for i in range(n):
            G = nx.Graph()
            for j in range(i + 2):
                G.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py", ...)
            ...
            paths.append(save_snapshot(G, ..., project_root=base, name=f"snap_{i:02d}"))
        return paths
    return _make
```
For `test_enrichment_lifecycle.py`: add fixture `enrich_graph(tmp_path)` that writes a minimal `graph.json` + snapshot, then runs `graphify enrich`. Follow the `make_snapshot_chain` factory pattern.

---

### `tests/test_enrich_invariant.py` (test-invariant, file-I/O)

**Analog:** `tests/test_routing.py::test_grep_router_api` (source file read + assertion)

**Pattern** (`test_routing.py` lines 85-91):
```python
def test_grep_router_api() -> None:
    from graphify import routing as R
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert "def classify_file" in src
    assert "def resolve_model" in src
    assert "class Router" in src
```
For `test_enrich_invariant.py` — byte-equality check that `graph.json` is unchanged after enrichment run:
```python
def test_graph_json_unchanged(tmp_path) -> None:
    """ENRICH-03: graph.json bytes are identical before and after enrich run."""
    graph_json = _write_fixture_graph_json(tmp_path)
    before = graph_json.read_bytes()

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "enrich", "--budget", "100",
         "--graph", str(graph_json)],
        capture_output=True, text=True, check=False, timeout=30,
    )

    after = graph_json.read_bytes()
    assert before == after, "graph.json was mutated by enrich — invariant violated"
```
This is an exact byte-equality check, not a JSON-parse comparison, so even whitespace changes are caught.

---

### `tests/test_enrich_grep_guard.py` (test-grep-CI, file-I/O)

**Analog:** `tests/test_routing.py::test_grep_router_api` — read source files, assert symbol presence/absence.

**Pattern** (`test_routing.py` lines 85-91):
```python
def test_grep_router_api() -> None:
    from graphify import routing as R
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert "def classify_file" in src
```

For `test_enrich_grep_guard.py` — SC-5: `_write_graph_json` caller whitelist:
```python
"""Grep-CI guard: only build.py + __main__.py may call to_json (write graph.json). SC-5."""
from __future__ import annotations
import re
from pathlib import Path


def test_write_graph_json_callers() -> None:
    """Assert that enrich.py does NOT import or call to_json / _write_graph_json.

    Only build.py and __main__.py (via export.to_json) are permitted callers.
    """
    pkg = Path(__file__).resolve().parent.parent / "graphify"

    enrich_src = (pkg / "enrich.py").read_text(encoding="utf-8")
    # enrich.py must not import or call to_json
    assert "to_json" not in enrich_src, (
        "enrich.py must not call to_json — graph.json is read-only to Phase 15"
    )
    assert "_write_graph_json" not in enrich_src, (
        "enrich.py must not call _write_graph_json"
    )

    # Positive check: build.py and __main__.py are the canonical callers
    build_src = (pkg / "build.py").read_text(encoding="utf-8")
    # build.py uses build_from_json (not to_json) — the caller check is in export/main
    main_src = (pkg / "__main__.py").read_text(encoding="utf-8")
    assert "to_json" in main_src or "to_json" in build_src, (
        "Whitelist check failed: neither build.py nor __main__.py call to_json"
    )
```
Note: also assert `watch.py` is the only indirect caller via `_rebuild_code`, not `enrich.py`. Read `watch.py` source and assert `to_json` appears in watch (allowed via rebuild) but not in enrich.

---

## Shared Patterns

### Atomic Write (`.tmp` + `os.replace`)
**Source:** `graphify/routing_audit.py` lines 46-53
**Apply to:** All writes to `enrichment.json` in `enrich.py` (per-pass commits, dry-run)
```python
tmp = dest.with_suffix(".json.tmp")
try:
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, dest)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

### Security-Gated File I/O
**Source:** `graphify/security.py` (`validate_graph_path`)
**Apply to:** Every `open()` for writing in `enrich.py`; every overlay read in `serve.py::_load_enrichment_overlay`
Pattern: `path = validate_graph_path(out_dir / "enrichment.json", base=out_dir)` before write.

### MCP Response Envelope (D-02 format)
**Source:** `graphify/serve.py` — `_tool_capability_describe` (lines 2325-2375)
**Apply to:** `--dry-run` output in `enrich.py` and `__main__.py` dispatch
```python
text_body = "\n".join(lines)
meta = {"status": "ok", "layer": 0, ...}
return text_body + "\n---GRAPHIFY-META---\n" + json.dumps(meta)
```

### D-16 Alias Redirect (canonical node_id on all writes)
**Source:** `graphify/serve.py` — `_load_dedup_report` + `_resolve_alias` closure (~lines 883-891)
**Apply to:** `enrich.py` description-pass write, patterns-pass `nodes: [...]` list, community-pass resolution
Pattern: load `_alias_map = _load_dedup_report(out_dir)` once at process start; for each node_id write: `node_id = _alias_map.get(node_id, node_id)`.

### Warning/Error Logging
**Source:** All graphify modules
**Apply to:** All `enrich.py` and modified modules
```python
print(f"[graphify enrich] <message>", file=sys.stderr)  # errors/warnings
print(f"[graphify enrich] <message>")  # user-facing progress
```

### `from __future__ import annotations` + module docstring
**Source:** Every graphify module (e.g., `routing.py` line 1-2, `cache.py` line 1-2)
**Apply to:** `enrich.py` must start with module docstring then `from __future__ import annotations`

---

## No Analog Found

All Phase 15 files have analogs. The only truly novel patterns (no existing analog in codebase) are:

| Pattern | File | Reason | Use Instead |
|---------|------|--------|-------------|
| `fcntl.flock` single-writer coordination | `enrich.py`, `__main__.py` | No existing flock usage in codebase | Copy pattern from RESEARCH.md RQ-2 exactly as specified |
| `signal.SIGTERM` handler with lock release | `enrich.py` | No signal handlers in current graphify code | Follow RESEARCH.md RQ-2 `_install_sigterm` pattern |
| `signal.alarm()` max-runtime enforcement | `enrich.py` | No alarm usage in codebase | POSIX stdlib; install in `_install_sigterm`, clear with `signal.alarm(0)` in `finally:` |

---

## Metadata

**Analog search scope:** `graphify/` (all 40+ modules), `tests/` (50+ test files)
**Files scanned:** 15 analog files read in full or by targeted section
**Key finding:** `serve.py` already contains `_enrichment_snapshot_id()` scaffold (line 2325) and `_sidecar_paths_for_manifest()` includes `enrichment.json` (line 1984) — Phase 15 must fill in `_load_enrichment_overlay` and extend `_reload_if_stale`, not create new scaffold
**Pattern extraction date:** 2026-04-20
