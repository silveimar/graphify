# Phase 18: Focus-Aware Graph Context - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 5 (2 modified in `graphify/`, 3 modified in `tests/`)
**Analogs found:** 5 / 5 (all have strong same-role matches in the existing codebase)

---

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `graphify/serve.py` (additive: `_resolve_focus_seeds`, `_run_get_focus_context_core`, `_tool_get_focus_context`, `_FOCUS_DEBOUNCE_CACHE`, `_check_focus_freshness`) | MCP handler (pure-core + closure wrapper) | request-response (stdio → dispatcher → envelope) | `_run_entity_trace` + `_tool_entity_trace` (serve.py:1238, 1938) and `_run_graph_summary` + `_tool_graph_summary` (serve.py:981, 1908) | **exact** — same 2-layer pattern, same signature family (`G, communities, snaps_dir|alias_map, arguments`) |
| `graphify/snapshot.py` (rename `root`→`project_root` in 5 signatures; add `ProjectRoot` frozen dataclass sentinel) | data model + value-object sentinel | config/parameter | No existing frozen-dataclass sentinel in codebase; stdlib `@dataclass(frozen=True)` + `__post_init__` is the idiomatic pattern (per RESEARCH Pattern / Standard Stack) | **role-match** — no in-repo precedent; stdlib pattern |
| `graphify/mcp_tool_registry.py` (additive: `get_focus_context` Tool entry + inputSchema) | MCP schema | schema/config | `entity_trace` Tool entry (mcp_tool_registry.py:223-229) and `connect_topics` (lines 214-222) | **exact** |
| `tests/test_serve.py` (~15 new focus tests) | unit test | request-response envelope asserts | `test_graph_summary_envelope_ok` (test_serve.py:1593), `test_graph_summary_snapshot_root_not_double_nested` (line 1689), `test_entity_trace_*` (lines 1860-2027) | **exact** |
| `tests/test_snapshot.py` (~5 sentinel/nested-dir tests) | unit test | construction invariant | `test_snapshots_dir_creates_directory` (test_snapshot.py:29), `test_list_snapshots_sorted_oldest_first` (line 160) | **exact** |
| `tests/conftest.py` (add `nested_project_root(tmp_path)` fixture) | shared pytest fixture | factory fixture | `make_snapshot_chain` (conftest.py:77-137), `tmp_corpus` (line 30) | **exact** — same factory-returning-closure idiom |

---

## Pattern Assignments

### `graphify/serve.py` — new focus handlers (MCP handler, request-response)

**Primary analog:** `_run_entity_trace` + `_tool_entity_trace`
**Secondary analog:** `_run_graph_summary` + `_tool_graph_summary`

#### P1.1 — Pure-core signature + budget clamp + D-02 envelope (from `_run_entity_trace`, serve.py:1238-1271)

```python
def _run_entity_trace(
    G: "nx.Graph",
    snaps_dir: "Path",
    alias_map: "dict[str, str]",
    arguments: dict,
) -> str:
    """Pure helper for entity_trace MCP tool (Phase 11 SLASH-02).

    Testable without MCP runtime. Returns the full hybrid envelope string.
    ...
    """
    from .snapshot import list_snapshots, load_snapshot

    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))

    entity_raw = sanitize_label(str(arguments.get("entity", "")))
    if not entity_raw:
        meta: dict = {
            "status": "no_data",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**Copy for `_run_get_focus_context_core`:**
- Signature: `(G, communities, alias_map, project_root: Path, arguments: dict) -> str`
- Early-arg parsing (budget clamp, focus_hint extraction) at the top
- Local `_no_context()` closure that returns empty text_body + SENTINEL + D-10 meta (`{status:"no_context", node_count:0, edge_count:0, budget_used:0}`)
- Return the D-02 envelope string unconditionally (never raise)

#### P1.2 — Happy-path envelope + meta assembly (from `_run_entity_trace`, serve.py:1398-1418)

```python
entity_id_out = live_matches[0] if live_matches else entity_resolved
meta = {
    "status": "ok",
    "layer": 1,
    "search_strategy": "trace",
    "cardinality_estimate": None,
    "continuation_token": None,
    "snapshot_count": len(snaps),
    "first_seen": first_seen_ts,
    "timeline_length": len(timeline),
    "entity_id": entity_id_out,
}
if _resolved_aliases:
    meta["resolved_from_alias"] = _resolved_aliases
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**Copy for focus `ok` path:** replace `entity_id` / `first_seen` etc. with `node_count`, `edge_count`, `budget_used`, `community_summary`, `seed_count`. Keep `status: "ok"` wording identical. **Do NOT** add any `focus_hint` echo fields (violates D-12).

#### P1.3 — Budget-pressure truncation (from `_run_entity_trace`, serve.py:1391-1393)

```python
text_body = "\n".join(lines)
max_chars = budget * 3
if len(text_body) > max_chars:
    text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"
```

**Adapt for D-08 outer-hop-first truncation:** wrap this in the `_render_within_budget` loop from RESEARCH Pattern 4 — re-compose at `depth-1` before clipping body characters. The character-clip above is the fallback at `depth=0`.

#### P1.4 — MCP wrapper with no-graph guard (from `_tool_entity_trace`, serve.py:1938-1951)

```python
def _tool_entity_trace(arguments: dict) -> str:
    """Phase 11 SLASH-02: entity evolution timeline across graph snapshots."""
    _reload_if_stale()
    if not Path(graph_path).exists():
        meta: dict = {
            "status": "no_graph",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
        return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    return _run_entity_trace(G, _out_dir.parent, _alias_map, arguments)
```

**Copy for `_tool_get_focus_context`:**
- Use the **same** `_reload_if_stale()` call first
- Pass `_out_dir.parent` as `project_root` (NOT `_out_dir` — per Pitfall 3; this is the CR-01 invariant)
- Per D-11 (binary `ok | no_context`), **DO NOT** return a `no_graph` envelope — collapse missing graph into the same `no_context` that the core returns, so the status enum stays binary
- After `_run_get_focus_context_core`, cache into `_FOCUS_DEBOUNCE_CACHE` **before** the final return (but caching happens to the core's envelope — `_merge_manifest_meta` runs later in `call_tool`; see Pitfall 7)

#### P1.5 — Registering the new tool in `_handlers` dict (serve.py:2051-2070)

```python
_handlers = {
    "query_graph": _tool_query_graph,
    ...
    "entity_trace": _tool_entity_trace,
    "drift_nodes": _tool_drift_nodes,
    "newly_formed_clusters": _tool_newly_formed_clusters,
    "capability_describe": _tool_capability_describe,
}

_reg_tools = build_mcp_tools()
if {t.name for t in _reg_tools} != set(_handlers.keys()):
    raise RuntimeError("MCP tool registry and _handlers keys must match (MANIFEST-05)")
```

**Copy:** add `"get_focus_context": _tool_get_focus_context,` — MUST also add matching entry to `mcp_tool_registry.build_mcp_tools()` or the MANIFEST-05 assertion above raises at `serve()` boot.

#### P1.6 — `source_file: str | list[str]` flattening via `_iter_sources` (analyze.py:11-28)

```python
def _iter_sources(source_file: "str | list[str] | None") -> list[str]:
    """Normalize source_file to a flat list of non-empty strings.
    ...
    str   -> [str]  (unchanged single-source nodes)
    list  -> filtered list of non-empty str elements
    None/empty -> []
    """
    if not source_file:
        return []
    if isinstance(source_file, str):
        return [source_file]
    if isinstance(source_file, list):
        return [s for s in source_file if isinstance(s, str) and s]
    return []
```

**Copy for `_resolve_focus_seeds`:** `from .analyze import _iter_sources` and call it — do **NOT** inline isinstance checks (RESEARCH Anti-Patterns: "Inlining `_iter_sources` logic creates a second source of truth").

#### P1.7 — Path confinement with explicit `base=project_root` (security.py:144-170, per Pitfall 3)

```python
def validate_graph_path(path: str | Path, base: Path | None = None) -> Path:
    """Resolve *path* and verify it stays inside *base*.
    ...
    Raises:
        ValueError  - path escapes base, or base does not exist
        FileNotFoundError - resolved path does not exist
    """
    if base is None:
        base = Path("graphify-out").resolve()
    ...
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(...)
    if not resolved.exists():
        raise FileNotFoundError(...)
    return resolved
```

**Copy for focus resolver:** call `validate_graph_path(file_path, base=project_root)` explicitly (default base is `graphify-out/`, which would reject legitimate source-file focuses). Wrap in `try/except (ValueError, FileNotFoundError)` → `return _no_context()` (Pitfall 4: both exceptions must be caught together to prevent traceback leaks).

---

### `graphify/snapshot.py` — rename + `ProjectRoot` sentinel (data model, config)

**Analog:** No existing frozen-dataclass sentinel in the repo. The snapshot module itself is the only site using bare `root: Path = Path(".")` — the rename IS the pattern refactor.

#### P2.1 — Current `root` signatures to rename (snapshot.py:14, 21, 29, 85)

```python
def snapshots_dir(root: Path = Path(".")) -> Path:
    """Returns graphify-out/snapshots/ - creates it if needed."""
    d = Path(root) / "graphify-out" / "snapshots"
    ...

def list_snapshots(root: Path = Path(".")) -> list[Path]:
    """Return sorted list of snapshot Paths (oldest first by mtime)."""
    d = snapshots_dir(root)
    ...

def save_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    name: str | None = None,
    cap: int = 10,
) -> Path:
    ...

def auto_snapshot_and_delta(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    cap: int = 10,
) -> tuple[Path, Path | None]:
    ...
```

**Rename action:** `root` → `project_root` in all 4 signatures above. `load_snapshot(path: Path)` at line 123 takes `path` (not `root`) and **stays unchanged** (per RESEARCH FOCUS-07 table). Also update 4 call-sites inside `auto_snapshot_and_delta` body (lines 100, 103, 118) and update the existing body refs to `Path(root)` → `Path(project_root)`.

#### P2.2 — `ProjectRoot` frozen dataclass (RESEARCH Code Examples — new pattern, no in-repo precedent)

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectRoot:
    """Sentinel wrapping a project root path.

    Raises at construction time if given `graphify-out/` directly — codifies
    v1.3 CR-01 (Pitfall 20) where `_out_dir` was passed as root, causing
    list_snapshots() to scan `graphify-out/graphify-out/snapshots/`.
    """
    path: Path

    def __post_init__(self) -> None:
        if self.path.name == "graphify-out":
            raise ValueError(
                f"ProjectRoot received {self.path!r} which has name 'graphify-out'. "
                f"Pass the directory CONTAINING graphify-out/, not graphify-out/ itself. "
                f"Try: ProjectRoot({self.path.parent!r})"
            )
```

**Design notes (from RESEARCH):**
- Function param types stay `Path` (not `ProjectRoot`) for backwards compatibility — the sentinel is **optional at call-sites** that want defense-in-depth
- Exception class: `ValueError` (not a named subclass — per D-15 Discretion; `DoubleNestedRootError` deferred)
- Error message must include BOTH the offending path AND the corrected form `self.path.parent` (per Pitfall 5 — sentinel guidance must help, not just fail)

#### P2.3 — Call-site updates in `serve.py` (4 wrapper functions)

RESEARCH identifies 4 wrappers that pass a project-root arg to snapshot helpers: `_tool_entity_trace`, `_tool_drift_nodes`, `_tool_newly_formed_clusters`, `_tool_graph_summary`. All already pass `_out_dir.parent` positionally (correct semantics). Rename is purely mechanical keyword clarity if any named passes exist — verify via `grep -n "root=" graphify/*.py`.

---

### `graphify/mcp_tool_registry.py` — schema entry (MCP schema)

**Analog:** `entity_trace` Tool entry (mcp_tool_registry.py:223-229)

```python
types.Tool(
    name="entity_trace",
    description="Return the evolution of a named entity across graph snapshots: first-seen, per-snapshot community and degree, current status. Used by the /trace slash command.",
    inputSchema={"type": "object", "properties": {
        "entity": {"type": "string"},
        "budget": {"type": "integer", "default": 500},
    }, "required": ["entity"]},
),
```

**Copy for `get_focus_context`:**
- Required top-level field: `focus_hint` (object)
- Nested properties inside `focus_hint`: `file_path` (str, required), `function_name` (str?), `line` (integer?), `neighborhood_depth` (integer, default 2, 1..6), `include_community` (boolean, default true), `reported_at` (string, ISO 8601)
- Top-level: `budget` (integer, default 2000, min 50, max 100000)

---

### `tests/test_serve.py` — ~15 new focus tests (unit test, request-response)

**Primary analog template:** `test_graph_summary_envelope_ok` and `test_graph_summary_snapshot_root_not_double_nested`
**Secondary:** the entire `test_entity_trace_*` family (test_serve.py:1860-2027)

#### T1.1 — Imports / module fixtures (test_serve.py:1-41)

```python
"""Tests for serve.py - MCP graph query helpers (no mcp package required)."""
import base64
import json
import pytest
import networkx as nx
from networkx.readwrite import json_graph

from graphify.serve import (
    _communities_from_graph,
    ...
    _run_entity_trace,
    _run_drift_nodes,
    _run_newly_formed_clusters,
    QUERY_GRAPH_META_SENTINEL,
)
```

**Copy:** add `_run_get_focus_context_core`, `_resolve_focus_seeds`, `_check_focus_freshness`, `_FOCUS_DEBOUNCE_CACHE` to this import block. Tests exercise pure core — no MCP dependency.

#### T1.2 — D-02 envelope assertion template (test_serve.py:1593-1615)

```python
def test_graph_summary_envelope_ok(tmp_path):
    """On a populated graph: meta.status == 'ok', required keys present."""
    from graphify.snapshot import save_snapshot
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    save_snapshot(G, communities, tmp_path)
    ...
    response = _run_graph_summary(G2, communities2, tmp_path, {"top_n": 3, "budget": 500})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["layer"] == 1
    assert "snapshot_count" in meta
```

**Copy for focus tests:**
- `test_get_focus_context_envelope_ok`: assert `meta["status"] == "ok"`, `meta["node_count"] >= 1`, `meta["edge_count"] >= 0`
- `test_get_focus_context_spoofed_path_silent`: pass `file_path="/etc/passwd"`, assert `meta["status"] == "no_context"` AND `parts[0] == ""` (D-09 empty text_body)
- `test_no_context_does_not_echo_focus_hint`: assert `"file_path" not in meta`, `"function_name" not in meta`, `"line" not in meta` (D-12)

#### T1.3 — Nested-dir / CR-01 guard template (test_serve.py:1689-1728)

```python
def test_graph_summary_snapshot_root_not_double_nested(tmp_path):
    """Regression: CR-01 — _out_dir.parent (project root) must be passed, not _out_dir.

    Simulates the production path: graph_path = "graphify-out/graph.json"
    so _out_dir = tmp_path / "graphify-out".
    save_snapshot(..., root=tmp_path) writes to tmp_path/graphify-out/snapshots/.
    If _run_graph_summary receives _out_dir instead of _out_dir.parent, list_snapshots()
    would scan _out_dir/graphify-out/snapshots/ (double-nested, non-existent), returning []
    ...
    """
    from graphify.snapshot import save_snapshot
    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    save_snapshot(G, communities, root=tmp_path)
    ...
    response = _run_graph_summary(G2, communities2, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
```

**Copy for `test_snapshot_callsites_use_project_root`:** grep-assertion that `_tool_get_focus_context` source code contains `project_root=` (keyword) when calling the snapshot helpers, OR that the positional passes `_out_dir.parent` (not `_out_dir`).

#### T1.4 — Entity-trace chain fixture usage (test_serve.py:1877-1898)

```python
def test_entity_trace_ok_timeline(make_snapshot_chain, tmp_path):
    """With >=2 snapshots where entity n0 exists throughout: status ok, timeline_length>=3."""
    snaps = make_snapshot_chain(n=3, root=tmp_path)
    # Build G_live with same id scheme as fixture (BLOCKER 2 fix)
    G_live = nx.Graph()
    for j in range(4):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    ...
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
```

**Copy for `test_focus_resolver_list_source_file_multi_seed`:**
- Build `G_live` with 2+ nodes whose `source_file` is a list: `source_file=["src/auth.py", "src/helpers.py"]`
- Pass `focus_hint.file_path = "src/auth.py"` → expect both nodes in seeds (D-01 multi-seed union)
- Assert `meta["seed_count"] >= 2`

#### T1.5 — Debounce test (new pattern, no exact analog — but follow T1.2 structure)

```python
# Template (adapt from T1.2):
def test_focus_debounce_suppresses_duplicate(tmp_path):
    """Second call within 500ms returns the same envelope (FOCUS-08)."""
    # Clear cache
    from graphify.serve import _FOCUS_DEBOUNCE_CACHE
    _FOCUS_DEBOUNCE_CACHE.clear()
    ...
    first = _run_get_focus_context_core(G, communities, {}, tmp_path, args)
    second = _run_get_focus_context_core(G, communities, {}, tmp_path, args)
    assert first == second  # byte-identical envelope
```

Use `time.monotonic()` manipulation via `monkeypatch.setattr("graphify.serve.time.monotonic", ...)` for the expiry test.

---

### `tests/test_snapshot.py` — ~5 sentinel/nested-dir tests (unit test, construction invariant)

**Primary analog:** `test_snapshots_dir_creates_directory` (test_snapshot.py:29-34) for construction shape, `test_list_snapshots_sorted_oldest_first` (line 160) for the integration flavor.

#### T2.1 — Construction-time assertion template (test_snapshot.py:29-34)

```python
def test_snapshots_dir_creates_directory(tmp_path):
    from graphify.snapshot import snapshots_dir

    d = snapshots_dir(tmp_path)
    assert d.exists()
    assert d == tmp_path / "graphify-out" / "snapshots"
```

**Copy for `test_project_root_sentinel_rejects_graphify_out`:**
```python
def test_project_root_sentinel_rejects_graphify_out(tmp_path):
    from graphify.snapshot import ProjectRoot
    bad = tmp_path / "graphify-out"
    bad.mkdir()
    with pytest.raises(ValueError, match="graphify-out"):
        ProjectRoot(path=bad)
```

And positive counterpart `test_project_root_sentinel_accepts_project_root(tmp_path)`: `ProjectRoot(path=tmp_path)` must succeed without raising.

#### T2.2 — Nested-dir integration (adapt `test_list_snapshots_sorted_oldest_first`, test_snapshot.py:160-174)

```python
def test_list_snapshots_sorted_oldest_first(tmp_path):
    from graphify.snapshot import save_snapshot, list_snapshots

    G = _make_graph()
    comms = _make_communities()
    save_snapshot(G, comms, tmp_path, name="aaa")
    time.sleep(0.05)
    save_snapshot(G, comms, tmp_path, name="bbb")
    snaps = list_snapshots(tmp_path)
    assert len(snaps) == 2
```

**Copy for `test_nested_dir_fixture_list_snapshots`:** use the new `nested_project_root` conftest fixture and assert `list_snapshots(nested_project_root)` returns the expected count. Paired with a companion that asserts `list_snapshots(nested_project_root / "graphify-out")` triggers the sentinel if wrapped in `ProjectRoot`.

---

### `tests/conftest.py` — `nested_project_root(tmp_path)` fixture (shared pytest fixture)

**Primary analog:** `make_snapshot_chain` (conftest.py:77-137) for factory-fixture style. `tmp_corpus` (conftest.py:30-47) for single-purpose factory.

#### F1 — Factory fixture template (conftest.py:77-137)

```python
@pytest.fixture
def make_snapshot_chain(tmp_path):
    """Factory fixture: create a chain of N synthetic snapshots under `root`.

    Usage::
        def test_something(make_snapshot_chain, tmp_path):
            snaps = make_snapshot_chain(n=3, root=tmp_path)
    ...
    """
    import networkx as nx
    from graphify.snapshot import save_snapshot

    def _make(n: int = 3, root: "Path | None" = None) -> "list[Path]":
        base = Path(root) if root is not None else tmp_path
        ...
        return paths

    return _make
```

**Copy for `nested_project_root`:**
- Function-scope (default), no explicit scope
- Docstring shows the layout: `tmp_path/project/graphify-out/snapshots/`
- Return the project root Path (i.e. `tmp_path / "project"`, NOT `tmp_path / "project" / "graphify-out"`)
- Optionally lay down one snapshot + one source file inside `project/src/` so focus-resolver integration tests can exercise end-to-end
- Naming: lowercase_with_underscores, matches `make_snapshot_chain` / `tmp_corpus` convention

```python
@pytest.fixture
def nested_project_root(tmp_path):
    """Lay out tmp_path/project/graphify-out/snapshots/ and tmp_path/project/src/*.py.

    Returns the project root (tmp_path/project) — NOT graphify-out/ — so the
    sentinel passes and focus-resolver path confinement matches production semantics.
    """
    project = tmp_path / "project"
    (project / "graphify-out" / "snapshots").mkdir(parents=True)
    (project / "src").mkdir()
    (project / "src" / "auth.py").write_text("def login(): pass\n")
    return project
```

---

## Shared Patterns

### The D-02 Envelope (applies to every new envelope return in serve.py)

**Source:** `graphify/serve.py:757`
```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
```

**Usage pattern (20 existing occurrences in serve.py):**
```python
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**Apply to:** Every `return` in `_run_get_focus_context_core` and `_tool_get_focus_context`. Never hand-concatenate JSON; always go through this exact form. `_merge_manifest_meta` (serve.py:1716-1728) splits on the sentinel downstream and adds `manifest_content_hash` — do not set that field in the core.

### Budget Clamping (applies to all new budget-taking handlers)

**Source:** `graphify/serve.py:794-795` (in `_run_query_graph`), `serve.py:1258-1259` (in `_run_entity_trace`), `serve.py:991-992` (in `_run_graph_summary`)
```python
budget = int(arguments.get("budget", 2000))
budget = max(50, min(budget, 100000))
```

**Apply to:** Top of `_run_get_focus_context_core`. Default is **2000** per D-07 (matches `query_graph`), not 500.

### Silent-ignore on Path Violations (applies to FOCUS-04 path confinement)

**Source:** `graphify/security.py:144-170`
**Pitfalls 3 + 4 mitigation:** catch BOTH exception types.

```python
try:
    validated = validate_graph_path(file_path, base=project_root)
except (ValueError, FileNotFoundError):
    return _no_context()
```

**Apply to:** Plan 18-01 resolver entrypoint. Never let these exceptions bubble up — `_merge_manifest_meta` would wrap the traceback into a leak.

### `_iter_sources` for `str | list[str]` Handling (applies to focus resolver)

**Source:** `graphify/analyze.py:11-28`
**Apply to:** `_resolve_focus_seeds`. Import: `from .analyze import _iter_sources`. Do not re-implement isinstance checks (RESEARCH Anti-Pattern).

### `sanitize_label` for User-Controlled Strings (applies to rendering path)

**Source:** `graphify/security.py` (re-exported in `serve.py:14`)
**Apply to:** Any `focus_hint` field that reaches a rendered `text_body` — `function_name` is the likely candidate. Strips control chars, caps length. Entity_trace uses this on `entity` at serve.py:1258.

### `_reload_if_stale()` Before Tool Body (applies to `_tool_get_focus_context`)

**Source:** `graphify/serve.py` — called at the top of every `_tool_X` closure (20 instances). Reads `graph_path` from serve() closure — no args.
**Apply to:** First statement in `_tool_get_focus_context`, before debounce or freshness checks.

---

## No Analog Found

Files with no close in-repo match — planner should follow RESEARCH.md code examples directly:

| Pattern | Role | Reason | RESEARCH Reference |
|---------|------|--------|--------------------|
| Frozen dataclass sentinel (`ProjectRoot`) | value-object | No existing `@dataclass(frozen=True)` + `__post_init__` pattern in `graphify/` — this is the first one | RESEARCH § Code Examples → "Snapshot sentinel (FOCUS-07)" |
| Module-level debounce cache with eviction | cache | No existing `time.monotonic`-based cache in the repo; `_manifest_hash_val` at serve.py:1693-1707 is closure-scoped (not module-level) | RESEARCH § Code Examples → "Debounce cache (FOCUS-08)" |
| ISO 8601 freshness parsing (Py 3.10 `Z`-suffix shim) | time parser | No existing `datetime.fromisoformat` call in serve.py that requires the shim | RESEARCH § Code Examples → "Freshness parse (FOCUS-09)" |
| `nx.compose_all` multi-seed ego-graph | graph traversal | `_bfs` at serve.py:471 exists but conflates visited-set vs. induced-subgraph semantics; FOCUS-06 explicitly mandates `nx.ego_graph` | RESEARCH § Code Examples → "Multi-seed ego-graph" |

For each of these, use the RESEARCH.md code example **verbatim** — it is already adapted for project Python version, type hints, and `from __future__ import annotations` style.

---

## Metadata

**Analog search scope:**
- `graphify/serve.py` (2107 lines; 20 MCP tool handlers inventoried)
- `graphify/snapshot.py` (150 lines; all 5 signatures confirmed)
- `graphify/security.py` (207 lines; `validate_graph_path` / `sanitize_label` confirmed)
- `graphify/analyze.py` (625 lines; `_iter_sources` + `_fmt_source_file` helpers confirmed)
- `graphify/mcp_tool_registry.py` (registry entry shapes for 19 existing tools)
- `tests/test_serve.py` (2214 lines; 80+ existing test functions indexed)
- `tests/test_snapshot.py` (285 lines; 19 test functions inventoried)
- `tests/conftest.py` (137 lines; 5 shared fixtures inventoried)

**Files scanned:** 8
**Pattern extraction date:** 2026-04-20
