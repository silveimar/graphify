# Phase 18: Focus-Aware Graph Context - Research

**Researched:** 2026-04-20
**Domain:** MCP tool composition / NetworkX ego-graph / path-confinement security
**Confidence:** HIGH

## Summary

Phase 18 adds one new MCP tool — `get_focus_context` — that maps an agent-reported focus (file path + optional function/line) to a BFS ego-graph, community summary, and citations rendered in the D-02 envelope (`text_body + SENTINEL + json(meta)`). All primitives exist: `nx.ego_graph`, `security.py::validate_graph_path`, `analyze.py._iter_sources`, `QUERY_GRAPH_META_SENTINEL`, the `_run_*_core + _tool_*_wrapper` pattern used by 19 existing tools. Per D-18 compose-don't-plumb, no new modules; everything lands in `serve.py` + a defensive rename in `snapshot.py`.

Two subtleties override training-data confidence. **First**, `nx.ego_graph(G, n, radius)` accepts a *single* node for `n` — NOT a list. Multi-seed ego-graph (D-01) requires `nx.compose_all([nx.ego_graph(G, s, r) for s in seeds])`. The CONTEXT.md claim "`nx.ego_graph` natively accepts list-of-seeds" is incorrect against NetworkX 3.4.2 and was verified empirically. **Second**, Python 3.10's `datetime.fromisoformat` rejects the `Z` suffix (added in 3.11). Since CI runs 3.10 + 3.12, FOCUS-09 parsing needs `.replace("Z", "+00:00")` as a compat shim — this is testable and cheap.

The snapshot rename (FOCUS-07) is mechanical: `root` → `project_root` across 5 functions, plus a frozen dataclass-wrapped-Path sentinel that raises at construction when `path.name == "graphify-out"`. Phases 11/12/13 already call `_out_dir.parent` (the correct project-root semantic post-CR-01); the rename just makes the contract impossible to regress.

**Primary recommendation:** 3 plans, as locked in D-13. Plan 18-01 = resolver + source_file matcher (pure, no MCP); Plan 18-02 = `get_focus_context` core + wrapper + envelope + snapshot sentinel + nested-dir fixture; Plan 18-03 = P2 debounce + freshness. All code in `serve.py` and `snapshot.py`. Zero new dependencies. Zero new algorithms. Test placement: `tests/test_serve.py` (focus resolver + dispatch), `tests/test_snapshot.py` (sentinel + nested-dir).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Multi-seed union. When `file_path` resolves to N node_ids, pass the full list as a multi-seed input to ego-graph construction (dedupe on union).
- **D-02:** `function_name` and `line` are optional narrowing filters. When provided, filter the union down to node_ids whose `source_location` matches. When absent, use the full union.
- **D-03:** No-match is indistinguishable from spoofed path. `file_path` inside `project_root` that passes security validation but doesn't resolve to any node_ids returns the exact same no-context envelope as a spoofed path.
- **D-04:** Accept absolute OR relative paths; normalize. Resolver calls `Path(p).resolve()` then confines against `project_root` via `security.py::validate_graph_path(path, base=project_root)`. Anything outside → silent ignore.
- **D-05:** `neighborhood_depth` defaults to `2`.
- **D-06:** `include_community` defaults to `true`.
- **D-07:** `budget` defaults to `2000` tokens. Clamp to `[50, 100000]`.
- **D-08:** Budget-pressure truncation drops outer hop first. When the ego-graph + community summary exceeds `budget * 3` chars, drop hop-N neighbors before hop-(N-1). Graceful degrade: the tool degrades to depth-1 then depth-0 rather than dropping the focus itself or mangling the community summary.
- **D-09:** `text_body = ""` for no-context results. Empty string.
- **D-10:** Meta shape for no-context: `{status: "no_context", node_count: 0, edge_count: 0, budget_used: 0}`.
- **D-11:** Status enum is binary: `ok | no_context` only. All failure modes collapse to `no_context`.
- **D-12:** No echo of `focus_hint` fields in meta. Never reflect `file_path`, `function_name`, or `line` back.
- **D-13:** Ship both P2 requirements in Phase 18 as Plan 18-03 (after 18-01 resolver + 18-02 MCP tool land). Total 3 plans.
- **D-14:** Debounce via module-level LRU + `time.monotonic()`. Key on `(file_path, function_name, line, depth, include_community)` tuple. Store last-call timestamp per key; if `now - last < 0.5s` return the cached envelope.
- **D-15:** `focus_hint.reported_at` is optional ISO 8601 UTC. When present and `now - reported_at > 300s`, return the `no_context` envelope. When absent, no freshness check — backward compatible. Validation path: parse via `datetime.fromisoformat`; any parse failure → `no_context`.

### Claude's Discretion

- Community summary content shape (planner default: reuse `analyze.py` community-representative logic — top-N by degree, cohesion score, member count).
- Test fixture design for the CR-01 guard (invariant: sentinel must fire if `Snapshot(project_root=Path("graphify-out"))` is ever constructed).
- Sentinel exception class naming (default `ValueError`; escalate to named subclass only if downstream phases need catchable distinct type).

### Deferred Ideas (OUT OF SCOPE)

- File-level node vs entity-level node classification — multi-seed union (D-01) handles both shapes.
- Basename-only fallback for `file_path` — rejected (collision ambiguity); raise as defect for Phase 14 if needed.
- Community summary `community_detail` enum arg (`minimal | standard | full`) — v1.5 candidate.
- `DoubleNestedRootError` named subclass — defer until a concrete caller needs it.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOCUS-01 | New MCP tool `get_focus_context(focus_hint, budget)` with structured hint | Pattern `_run_X_core + _tool_X_wrapper` replicated across 19 tools in `serve.py` (§ Standard Stack → MCP tool shape). JSON schema goes in `mcp_tool_registry.py` alongside 19 peers. |
| FOCUS-02 | Resolves `file_path` → node_ids, handles `source_file` as `str \| list[str]` | `analyze.py._iter_sources(source_file)` is the canonical helper — str→[str], list→filtered, None→[]. Must be imported or inlined in resolver. |
| FOCUS-03 | Returns BFS subgraph at depth with citations + community summary in D-02 envelope | `QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"` + `_subgraph_to_text()` + meta dict (same shape as 19 peers). Community summary field shape at planner's discretion. |
| FOCUS-04 | `validate_graph_path(path, base=project_root)` confinement; spoofed silently ignored | Existing primitive (security.py:144); must be called with explicit `base=project_root` — default base is `graphify-out/` which is wrong for source files. All three raises (ValueError escape, ValueError base-missing, FileNotFoundError) → silent no_context. |
| FOCUS-05 | Pull-model focus via MCP arg — no filesystem watcher side-channel | Enforced by design: dispatcher is pure-synchronous; no `watchdog` import, no thread creation, no timers. Grep-assertion viable. |
| FOCUS-06 | Uses `nx.ego_graph` — no new algorithms | **Critical correction:** `nx.ego_graph` is single-seed only in NX 3.x. Multi-seed pattern (D-01) requires `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])`. No new BFS — the per-seed ego_graph + compose is still "compose, not plumb." |
| FOCUS-07 | Snapshot-path-double-nesting guard: rename `root` → `project_root`; sentinel asserts `path.name != "graphify-out"` | Frozen dataclass wrapping `Path` with `__post_init__` assertion. Current callsites: `snapshots_dir` (line 14), `list_snapshots` (line 21), `save_snapshot` (line 29), `auto_snapshot_and_delta` (line 85), `load_snapshot` (line 123 — takes `path`, not `root`, so unchanged). Test in nested-dir fixture. |
| FOCUS-08 [P2] | 500 ms debounce on focus changes | Module-level `_FOCUS_DEBOUNCE_CACHE: dict[tuple, tuple[float, str]] = {}` keyed on the full tuple, `time.monotonic()` for window check. Suppress-duplicate-within-window, not defer (D-14). |
| FOCUS-09 [P2] | `reported_at` freshness (≤ 5 min) | `datetime.fromisoformat(reported_at.replace("Z", "+00:00"))` (Py 3.10 compat shim). Compare against `datetime.now(timezone.utc)`. Parse-fail OR `now - reported_at > 300s` → `no_context`. |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP tool dispatch (`get_focus_context`) | serve.py MCP server | mcp_tool_registry.py schema | All 19 existing MCP tools live in serve.py; registry owns JSON Schema. Two-file touch is the established pattern (MANIFEST-05 asserts both stay in sync). |
| Focus resolution (path → node_ids) | serve.py (new helper) | analyze.py._iter_sources | Resolver is tool-specific; `_iter_sources` is the canonical str\|list[str] handler — imported, not duplicated. |
| Path confinement | security.py (existing `validate_graph_path`) | — | Anti-leak primitive already exists. Only change: planner must confirm "file doesn't exist on disk" is handled (current impl raises FileNotFoundError; focus resolver catches this too → silent no_context). |
| Ego-graph construction | networkx (stdlib of project) | — | `nx.ego_graph` + `nx.compose_all` compose to multi-seed without new code. |
| Community summary | analyze.py (reuse degree + cohesion) | serve.py (new rendering) | Per "Claude's Discretion"; avoids duplicating community ranking logic. |
| Snapshot sentinel | snapshot.py (new `ProjectRoot` class) | — | CR-01 regression guard lives where the bug happens. Defensive construction-time check. |
| Debounce cache | serve.py (module-level dict) | — | Server-process lifetime scope; stdio server = one process per client (matches the debounce contract). No cross-process coordination needed. |
| Freshness check | serve.py (dispatch-head check) | — | Evaluated before resolver runs; fails fast to avoid useless traversal. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | 3.4.2 (current project install) | ego_graph + compose_all | Already a required dep; no new surface. `[VERIFIED: python -c "import networkx; print(networkx.__version__)"]` |
| Python stdlib `datetime` | 3.10+ | Freshness parsing | `datetime.fromisoformat` in stdlib; only caveat is 3.10 lacks `Z` suffix support `[VERIFIED: tested locally on 3.10.19]`. |
| Python stdlib `time` | 3.10+ | Debounce via `time.monotonic()` | D-14 specifies `time.monotonic` (not `time.time`) because monotonic is immune to clock adjustments (system sleep, NTP). |
| Python stdlib `dataclasses` | 3.10+ | `ProjectRoot(path)` frozen dataclass sentinel | `@dataclass(frozen=True)` + `__post_init__` is the idiomatic Py 3.10 value-type pattern. |

**No new dependencies.** CLAUDE.md constraint honored.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mcp` (optional extra) | already pinned | Tool registration | Only imported inside `serve()` — keeps Plan 18-01 resolver testable without MCP installed. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `nx.compose_all(ego_graphs)` | Hand-rolled BFS from union of seeds | `_bfs()` already exists in serve.py (line 471) and would work. But FOCUS-06 explicitly mandates `nx.ego_graph` — "no new algorithms," and the compose approach is idiomatic NetworkX. |
| frozen `@dataclass` `ProjectRoot(Path)` | Subclass `Path` directly | Subclassing Path is discouraged (Py 3.10 docs: Path has `__new__` magic). Frozen dataclass that *holds* a Path is simpler and passes mypy cleanly. |
| `time.monotonic()` debounce cache | `functools.lru_cache` with TTL | `lru_cache` has no TTL in stdlib; rolling a TTL wrapper is more code than a single-dict pattern. |
| `cachetools.TTLCache` | PyPI | Adds a required dep; CLAUDE.md forbids it. |

**Installation:** No new packages. Validate existing pins:

```bash
python3 -c "import networkx as nx; assert (3, 0) <= tuple(int(x) for x in nx.__version__.split('.')[:2])"
```

**Version verification:** NetworkX 3.4.2 verified against `~/companion-util_repos/graphify/.venv` (2026-04-20). `networkx.compose_all` and `networkx.ego_graph` APIs are stable since 2.x; no migration risk.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────┐
│  Agent Caller    │
│  (editor/skill)  │
└────────┬─────────┘
         │ focus_hint + budget
         ▼
┌────────────────────────────────────────────────────────────────┐
│  serve.py :: _tool_get_focus_context (MCP wrapper)             │
│                                                                │
│  1. _reload_if_stale()         ← existing pattern              │
│  2. Plan 18-03 FOCUS-09:       freshness gate (reported_at)    │
│  3. Plan 18-03 FOCUS-08:       debounce cache check            │
│  4. dispatch → _run_focus_core                                 │
└────────┬───────────────────────────────────────────────────────┘
         │ G, communities, _alias_map, project_root, arguments
         ▼
┌────────────────────────────────────────────────────────────────┐
│  serve.py :: _run_focus_core (PURE DISPATCH — unit-testable)   │
│                                                                │
│  step A. Parse + clamp budget (existing max(50,min) pattern)   │
│  step B. FOCUS-04: validate_graph_path(file_path, base=root)   │
│          → catches ValueError AND FileNotFoundError            │
│          → maps ALL failures to no_context envelope            │
│  step C. Plan 18-01: _resolve_focus_seeds(G, path, fn?, line?) │
│          → union node_ids, handles source_file str|list        │
│          → filter by function_name / source_location if given  │
│          → empty union → no_context (D-03)                     │
│  step D. FOCUS-06: ego_graphs = [nx.ego_graph(G, s, depth)     │
│                                  for s in seeds]               │
│          subgraph = nx.compose_all(ego_graphs)                 │
│  step E. Build community summary (D-06 default on)             │
│          → top-N by degree from analyze.py                     │
│  step F. _subgraph_to_text(...)                                │
│  step G. D-08 truncation: drop hop-N if over budget*3 chars    │
│  step H. Assemble meta:                                        │
│          ok   → {status, node_count, edge_count, budget_used,  │
│                  community_summary, seed_count}                │
│          fail → {status:"no_context", 0, 0, 0}  (D-10)         │
│  step I. Return text_body + SENTINEL + json.dumps(meta)        │
└────────────────────────────────────────────────────────────────┘
         │ envelope string
         ▼
┌──────────────────┐
│  MCP runtime     │  ← wraps in TextContent via call_tool
│  (stdio server)  │
└──────────────────┘

                    ┌──────────────────────────────────────┐
                    │  snapshot.py (FOCUS-07 rename)       │
                    │                                      │
                    │  @dataclass(frozen=True)             │
                    │  class ProjectRoot:                  │
                    │      path: Path                      │
                    │      def __post_init__(self):        │
                    │          assert path.name !=         │
                    │              "graphify-out"          │
                    │                                      │
                    │  All 5 `root: Path` params renamed   │
                    │  to `project_root: Path` (type stays │
                    │  Path for backcompat; sentinel       │
                    │  wrapping is at OPTIONAL caller use) │
                    └──────────────────────────────────────┘
```

### Recommended Project Structure

No new files. Touch only:

```
graphify/
├── serve.py       # +≈250 LOC: _resolve_focus_seeds, _run_focus_core,
│                  #             _tool_get_focus_context, _FOCUS_DEBOUNCE_CACHE,
│                  #             _check_focus_freshness
├── snapshot.py    # ≈20 LOC touched: rename root→project_root in 5 signatures;
│                  #                 new ProjectRoot frozen dataclass (≈10 LOC)
└── mcp_tool_registry.py  # +≈20 LOC: get_focus_context Tool entry + schema

tests/
├── test_serve.py     # +≈15 focus tests: resolver, envelope, binary status,
│                     #                   budget drop, debounce, freshness
└── test_snapshot.py  # +≈5 tests: sentinel fires, nested-dir fixture,
                      #            rename callsite verification
```

### Pattern 1: Pure-core + MCP-wrapper (19 existing instances)

**What:** Every MCP tool in `serve.py` follows a two-layer pattern. The `_run_X_core` (or `_run_X`) function is pure — it takes G, arguments, sidecar state as explicit parameters, returns a string envelope. The `_tool_X` closure inside `serve()` is the MCP runtime wrapper that supplies closure-captured state (`_alias_map`, `_out_dir`, etc.) and checks `_reload_if_stale()`.

**When to use:** Every new MCP tool. Tests exercise `_run_X_core` directly; MCP runtime is tested separately (currently trivially via the handlers dict key check).

**Example (abbreviated, adapted from `_run_entity_trace`):**
```python
# Source: graphify/serve.py:1238 (_run_entity_trace)
def _run_focus_core(
    G: nx.Graph,
    communities: dict,
    alias_map: dict[str, str],
    project_root: Path,
    arguments: dict,
) -> str:
    """Pure dispatch core for get_focus_context — no MCP runtime. Returns D-02 envelope."""
    focus_hint = arguments.get("focus_hint", {}) or {}
    budget = int(arguments.get("budget", 2000))
    budget = max(50, min(budget, 100000))

    file_path = focus_hint.get("file_path", "")
    function_name = focus_hint.get("function_name")
    line = focus_hint.get("line")
    depth = int(focus_hint.get("neighborhood_depth", 2))
    include_community = bool(focus_hint.get("include_community", True))

    def _no_context() -> str:
        meta = {"status": "no_context", "node_count": 0, "edge_count": 0, "budget_used": 0}
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # FOCUS-04 + D-03: all path failures collapse to no_context
    try:
        validated = validate_graph_path(file_path, base=project_root)
    except (ValueError, FileNotFoundError):
        return _no_context()

    seeds = _resolve_focus_seeds(G, validated, function_name=function_name, line=line)
    if not seeds:
        return _no_context()  # D-03: indistinguishable from spoof

    # FOCUS-06: nx.ego_graph is single-seed; multi-seed = compose_all
    subgraphs = [nx.ego_graph(G, s, radius=depth) for s in seeds]
    focused = nx.compose_all(subgraphs) if len(subgraphs) > 1 else subgraphs[0]

    # ... render + truncate + meta
```

### Pattern 2: `source_file` str|list[str] handling via `_iter_sources`

**What:** Every call-site that reads `source_file` flattens via `analyze.py._iter_sources` to avoid crashing on post-dedup list values.

**When to use:** The focus resolver. Import and reuse — do not inline.

**Example:**
```python
# Source: graphify/analyze.py:17 (_iter_sources)
from graphify.analyze import _iter_sources

def _resolve_focus_seeds(G, target_path: Path, *, function_name=None, line=None) -> list[str]:
    target = str(target_path.resolve())
    seeds = []
    for nid, data in G.nodes(data=True):
        sources = _iter_sources(data.get("source_file"))
        # D-04: normalize — compare resolved absolute strings, or relative+abs both
        if any(s == target or str(Path(s).resolve()) == target for s in sources):
            seeds.append(nid)
    # D-02: optional narrowing
    if function_name or line is not None:
        narrowed = []
        for nid in seeds:
            loc = G.nodes[nid].get("source_location", "")
            label = G.nodes[nid].get("label", "")
            if function_name and function_name not in label:
                continue
            if line is not None and loc != f"L{line}":
                continue
            narrowed.append(nid)
        seeds = narrowed
    return seeds
```

### Pattern 3: D-02 Envelope (`text_body + SENTINEL + json(meta)`)

**What:** Every MCP tool's response string is `text_body + "\n---GRAPHIFY-META---\n" + json.dumps(meta)`. The sentinel is defined once at `serve.py:757`. Downstream `_merge_manifest_meta` (serve.py:1717) splits on this sentinel and adds `manifest_content_hash` — so the core does not set that field.

**When to use:** Every MCP tool response.

**Example (no-context branch):**
```python
# Source: graphify/serve.py:849 (no_seed_nodes no-context variant)
meta = {"status": "no_context", "node_count": 0, "edge_count": 0, "budget_used": 0}
return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

### Pattern 4: Budget-drop ordering (D-08)

**What:** Render at requested depth → measure `len(text_body)` vs `budget * 3` chars → if over, rebuild with depth=depth-1 → repeat until depth=0 or fits.

**Why outer-hop-first:** Dropping middle hops mangles the ego-graph topology; dropping the focus node itself violates the semantic contract ("agent asked about X — return empty is worse than return just X"). Outer-hop drop = graceful degrade from full neighborhood → immediate neighbors → focus only.

**Example:**
```python
def _render_within_budget(G, seeds, depth, budget, include_community, communities):
    for current_depth in range(depth, -1, -1):
        subgraphs = [nx.ego_graph(G, s, radius=current_depth) for s in seeds]
        focused = nx.compose_all(subgraphs) if subgraphs else None
        text = _subgraph_to_text(focused, set(focused.nodes), list(focused.edges),
                                 token_budget=budget, layer=2)
        if include_community:
            text += "\n\n" + _render_community_summary(G, focused, communities)
        if len(text) <= budget * 3:
            return text, current_depth, focused
    # final fallback: just the seeds themselves (depth=0)
    return "", 0, None
```

### Anti-Patterns to Avoid

- **Echoing `focus_hint` fields back into meta on `no_context`** — violates D-12. An attacker sending `/etc/passwd` must receive a no-context envelope that is byte-identical to one triggered by an unindexed file.
- **Adding a third status value** — violates D-11 anti-leak invariant. Any new status (e.g., `error`, `stale`, `not_indexed`) leaks membership information via side channel.
- **Inlining `_iter_sources` logic into the resolver** — creates a second source of truth for str|list[str] handling. Phase 10 D-12 centralized this for a reason.
- **Passing `_out_dir` (= `graphify-out/`) as `root`/`project_root`** — re-introduces CR-01. Always pass `_out_dir.parent` (existing pattern in `_tool_entity_trace`, line 1952).
- **Using `time.time()` for debounce** — breaks on clock adjustments (NTP, suspend/resume). D-14 mandates `time.monotonic()`.
- **Subclassing `pathlib.Path`** for the sentinel — Path has `__new__` magic that varies by platform. Wrap Path in a frozen dataclass instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-seed ego-graph | Custom BFS from seed union | `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])` | FOCUS-06 mandate; `_bfs()` exists but conflates visited-set semantics with the ego-graph induced-subgraph semantics. `compose_all` preserves node/edge attrs automatically. |
| `source_file: str \| list[str]` flattening | Per-call-site isinstance checks | `analyze.py._iter_sources` | Phase 10 D-12 centralized this. Already used in 6+ call-sites in analyze.py + export.py. |
| Path confinement | Regex-match file paths | `security.py::validate_graph_path(path, base=project_root)` | Handles symlink resolution, `..` escape, base-doesn't-exist — all three failure modes. Plus, Pitfall 6 mitigation is already codified here. |
| D-02 envelope assembly | Hand-concatenate JSON strings | `text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)` | 19 existing tools use this exact form. `_merge_manifest_meta` depends on the sentinel string being exact. |
| ISO 8601 parsing | Manual regex | `datetime.fromisoformat(ts.replace("Z", "+00:00"))` | Py 3.10 `fromisoformat` is strict but stdlib; `Z` shim is one line. Pre-3.11 bug is documented — don't pull in `dateutil`. |
| Community summary | Custom degree ranking | `analyze.god_nodes(G_sub, top_n=N)` scoped to community | Already filters file-level hubs + concept nodes, returning clean dicts. Reuse in subgraph-scoped form. |
| Debounce cache eviction | LRU library | Module-level `dict`, cleanup on insertion if size > 256 | 5-key tuple × stdio server lifetime = tiny cache. Simpler than `cachetools`. |

**Key insight:** Phase 18 is a compose-only phase (D-18). Every net-new capability maps to an existing primitive — the *value* is the composition, not novel algorithms. Tasks that reach for stdlib beyond `networkx` / `pathlib` / `datetime` / `time` / `dataclasses` / `json` should be re-scoped.

## Runtime State Inventory

> This phase is code-only: no rename/migration of stored data, workflow configs, OS registrations, secrets, or build artifacts. Skipping per "Skip if… code-only changes" guidance.

**However, the FOCUS-07 rename is a rename-phase within a code-only phase.** The scope is limited:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `graphify-out/snapshots/*.json` payload schema uses `"metadata.timestamp"` + `"graph"` + `"communities"`, no `root` field in payload. | None. |
| Live service config | None — snapshot is called from `auto_snapshot_and_delta` (invoked by `run()` / skill), not from a running MCP server that retains the old name. | None. |
| OS-registered state | None — no scheduled tasks, no plist, no systemd. | None. |
| Secrets / env vars | None. | None. |
| Build artifacts | `graphifyy.egg-info/` (if locally installed `-e`). Stale after edits but auto-refreshed by `pip install -e .`. | Reinstall after the rename: `pip install -e ".[all]"`. |
| Internal callsites of `snapshot.py::root` | 4 callsites in `serve.py` (`_tool_entity_trace`, `_tool_drift_nodes`, `_tool_newly_formed_clusters`, `_tool_graph_summary`) — all pass `_out_dir.parent` which IS project_root. Plus `save_snapshot` / `load_snapshot` / `auto_snapshot_and_delta` calls inside the pipeline. | Rename parameter in 5 function signatures in `snapshot.py`; update 4 call-sites in `serve.py` (mechanical keyword-arg rename). The pipeline (__main__.py / skill) does not currently pass `root=` by keyword — all positional. Audit `grep -n "root=" graphify/*.py` to find any unexpected named passes. |

**Canonical question:** *After every file in the repo is updated, what runtime systems still have the old string cached/stored/registered?* → **None.** The rename is internal-to-codebase; no external caches. `[VERIFIED: grep of tests/ + graphify/ + .planning/]`

## Common Pitfalls

### Pitfall 1: `nx.ego_graph` treated as multi-seed API

**What goes wrong:** Developer assumes `nx.ego_graph(G, [a, b, c], radius=2)` works (hinted at by CONTEXT "Reusable Assets" note). Raises `nx.NodeNotFound: Source [a, b, c] is not in G`. `[VERIFIED: python3 -c "import networkx as nx; G=nx.path_graph(5); nx.ego_graph(G, [0,4], radius=1)"]`

**Why it happens:** NetworkX docs describe `n` as "A single node." Training data confuses this with `single_source_shortest_path_length` (which DOES accept a list as `source`).

**How to avoid:** Use the compose pattern: `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])`. The compose-all preserves attrs and handles overlapping neighborhoods correctly (node/edge appears once).

**Warning signs:** Tests pass with single-seed fixtures; fail first time a node has `source_file: list[str]` with ≥2 entries pointing into the graph.

### Pitfall 2: Python 3.10 `fromisoformat` rejects `Z` suffix

**What goes wrong:** `datetime.fromisoformat("2026-04-20T13:17:00Z")` raises `ValueError: Invalid isoformat string` on Py 3.10 (CI target). Works on 3.12. `[VERIFIED: tested on 3.10.19]`

**Why it happens:** `Z` suffix support was added in Python 3.11 (`bpo-35829`).

**How to avoid:** Shim before parsing: `ts.replace("Z", "+00:00")`. Per D-15, any parse failure → `no_context`, so the shim is defense-in-depth (parse failures still bucket correctly).

**Warning signs:** FOCUS-09 tests pass locally on 3.12 dev box, fail in CI's 3.10 matrix leg.

### Pitfall 3: Default `validate_graph_path` base is `graphify-out/`, not project root

**What goes wrong:** Calling `validate_graph_path(file_path)` without `base=...` confines to `graphify-out/` by default (security.py:146). A legitimate focus on `src/auth.py` would be rejected as "escapes the allowed directory." `[VERIFIED: security.py line 146 default]`

**Why it happens:** `validate_graph_path` was designed for confining *graph artifact* paths (graph.json, snapshots). Phase 18 uses it for *source file* paths — a new semantic.

**How to avoid:** Always pass `base=project_root` explicitly (= `_out_dir.parent`). Review checklist item.

**Warning signs:** Test fixtures with a real `graphify-out/` layout pass; production with agent focus on `/Users/.../repo/src/foo.py` returns no_context for every request.

### Pitfall 4: `validate_graph_path` raises `FileNotFoundError` if focus file is missing on disk

**What goes wrong:** Graph indexes a file that the user deleted. Focus points to it. `validate_graph_path` raises `FileNotFoundError` (security.py:162). If resolver only catches `ValueError`, the exception propagates and `_merge_manifest_meta` wraps the traceback into the envelope — leaks filesystem info.

**How to avoid:** Catch `(ValueError, FileNotFoundError)` together → silent no_context. Per D-03/D-11, these are indistinguishable.

**Warning signs:** Stale-graph scenarios where focus on a deleted file returns a traceback instead of a clean envelope.

### Pitfall 5: Snapshot sentinel fires on legitimate relative path

**What goes wrong:** A caller does `Snapshot(project_root=Path("graphify-out"))` — but a caller doing `Snapshot(project_root=Path("some-project/graphify-out"))` has `.name == "graphify-out"` too, which is technically the same bug shape but in a different location. The sentinel fires, the caller is confused because "but my dir exists and is called graphify-out!"

**How to avoid:** Sentinel message must be clear: "Pass the directory CONTAINING graphify-out/, not graphify-out/ itself." Include both the offending path AND the corrected form in the error (`path.parent`).

**Warning signs:** Downstream phase 15/17 integration surprises during adoption.

### Pitfall 6: Module-level debounce cache grows unbounded

**What goes wrong:** `_FOCUS_DEBOUNCE_CACHE[tuple] = (monotonic_time, envelope_string)` — never pruned. Long-running stdio server sees thousands of distinct focuses; memory grows.

**How to avoid:** On insertion, if `len(cache) > 256`, drop the oldest 64 entries (sorted by timestamp). 256 is enough for most agent sessions (one focus per active file × open windows).

**Warning signs:** Memory-profile test across 10k dispatches shows linear growth.

### Pitfall 7: Debounced envelope leaks across tool-definition changes

**What goes wrong:** Cache hit returns the prior envelope — which contains a stale `manifest_content_hash` (merged in by `_merge_manifest_meta` after the cache layer). If the manifest changes between calls within the 500ms window, the cached envelope advertises the wrong hash.

**How to avoid:** Cache the output of `_run_focus_core` (the pre-manifest-merge envelope), NOT the final MCP wrapper output. The wrapper re-applies `_merge_manifest_meta` on every call.

**Warning signs:** Rare integration flake where manifest-hash-change assertions fail within 500ms of a focus call.

### Pitfall 8: Nested-dir fixture doesn't reproduce CR-01 semantics

**What goes wrong:** Fixture builds `tmp_path/graphify-out/snapshots/*.json` and passes `tmp_path` as `root`. That's the **correct** usage — the test always passes. The bug is passing `tmp_path/graphify-out` as `root`, which is what CR-01 did.

**How to avoid:** The regression test MUST construct `Snapshot(project_root=Path("graphify-out"))` (or the tmp_path equivalent `tmp_path/"graphify-out"`) and assert the sentinel raises BEFORE any filesystem operation. Pair with a positive test that passes `tmp_path` (correct usage) and asserts success.

**Warning signs:** Fixture has `tmp_path / "graphify-out" / "snapshots"` in setup but never calls the sentinel with the wrong input.

## Code Examples

### Multi-seed ego-graph (FOCUS-06 + D-01)

```python
# VERIFIED: python3 test against networkx 3.4.2 (2026-04-20)
import networkx as nx

def _multi_seed_ego(G: nx.Graph, seeds: list[str], radius: int) -> nx.Graph:
    """Multi-seed ego-graph via compose_all — D-01 union semantics."""
    if not seeds:
        return nx.Graph()
    subgraphs = [nx.ego_graph(G, s, radius=radius) for s in seeds if s in G]
    if not subgraphs:
        return nx.Graph()
    if len(subgraphs) == 1:
        return subgraphs[0]
    return nx.compose_all(subgraphs)
```

### Snapshot sentinel (FOCUS-07)

```python
# graphify/snapshot.py — FOCUS-07 addition
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectRoot:
    """Sentinel wrapping a project root path.

    Raises at construction time if given `graphify-out/` directly — this codifies
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

### Freshness parse with Py 3.10 compat shim (FOCUS-09)

```python
# graphify/serve.py — FOCUS-09 helper
from datetime import datetime, timezone

def _check_focus_freshness(reported_at: str | None, now: datetime | None = None) -> bool:
    """Return True if focus is fresh (or no reported_at given). Per D-15."""
    if not reported_at:
        return True  # absent = backward compatible skip
    try:
        # Py 3.10 compat: fromisoformat doesn't accept 'Z' until 3.11
        ts = datetime.fromisoformat(reported_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False  # parse fail → no_context (D-11 collapse)
    # Normalize naive timestamps to UTC
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return (current - ts).total_seconds() <= 300
```

### Debounce cache (FOCUS-08)

```python
# graphify/serve.py — module-level
import time
_FOCUS_DEBOUNCE_CACHE: dict[tuple, tuple[float, str]] = {}
_FOCUS_DEBOUNCE_WINDOW = 0.5  # seconds; D-14

def _focus_debounce_key(focus_hint: dict) -> tuple:
    return (
        focus_hint.get("file_path", ""),
        focus_hint.get("function_name") or "",
        focus_hint.get("line") if focus_hint.get("line") is not None else -1,
        int(focus_hint.get("neighborhood_depth", 2)),
        bool(focus_hint.get("include_community", True)),
    )

def _focus_debounce_get(key: tuple) -> str | None:
    entry = _FOCUS_DEBOUNCE_CACHE.get(key)
    if not entry:
        return None
    ts, envelope = entry
    if time.monotonic() - ts < _FOCUS_DEBOUNCE_WINDOW:
        return envelope
    return None

def _focus_debounce_put(key: tuple, envelope: str) -> None:
    if len(_FOCUS_DEBOUNCE_CACHE) > 256:
        # Evict oldest quarter
        oldest = sorted(_FOCUS_DEBOUNCE_CACHE.items(), key=lambda kv: kv[1][0])[:64]
        for k, _ in oldest:
            _FOCUS_DEBOUNCE_CACHE.pop(k, None)
    _FOCUS_DEBOUNCE_CACHE[key] = (time.monotonic(), envelope)
```

### D-02 envelope in no_context branch (D-09 + D-10)

```python
# graphify/serve.py
def _focus_no_context() -> str:
    meta = {"status": "no_context", "node_count": 0, "edge_count": 0, "budget_used": 0}
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `nx.ego_graph(G, [a,b], radius=r)` (assumed) | `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])` | NetworkX never supported list-seeds for ego_graph; assumption was wrong | Per-seed call overhead is O(ego-size) × N seeds; negligible for depth≤2 typical focuses. |
| `fromisoformat` accepts `Z` | Py 3.11+ accepts; 3.10 requires shim | Python 3.11 (2022-10) added `Z` support | CI must run 3.10 test leg; shim adds 1 line to parse path. |
| Path as `root` parameter (ambiguous name) | `project_root: Path` + optional `ProjectRoot` sentinel wrapper | Codified in Phase 18 (FOCUS-07) from v1.3 CR-01 | Phases 12/15/17 inherit guard with zero code change; future snapshot-readers forced to use the corrected contract. |

**Deprecated/outdated:**

- Direct `pathlib.Path` subclassing — discouraged in Py 3.10 docs; prefer wrapping via dataclass or accepting-Path-but-asserting-at-construction.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project-pinned; no version lock in pyproject — uses latest on CI) |
| Config file | `pytest.ini` (absent) — pytest auto-discovers via `tests/test_*.py` |
| Quick run command | `pytest tests/test_serve.py tests/test_snapshot.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOCUS-01 | MCP tool is registered + handler dispatches | unit | `pytest tests/test_serve.py::test_get_focus_context_registered -x` | ❌ Wave 0 |
| FOCUS-02 | Resolver handles `source_file: str` | unit | `pytest tests/test_serve.py::test_focus_resolver_str_source_file -x` | ❌ Wave 0 |
| FOCUS-02 | Resolver handles `source_file: list[str]` union | unit | `pytest tests/test_serve.py::test_focus_resolver_list_source_file_multi_seed -x` | ❌ Wave 0 |
| FOCUS-03 | Envelope matches D-02 shape on success | unit | `pytest tests/test_serve.py::test_get_focus_context_envelope_ok -x` | ❌ Wave 0 |
| FOCUS-03 | Community summary included when `include_community=True` | unit | `pytest tests/test_serve.py::test_get_focus_context_community_summary -x` | ❌ Wave 0 |
| FOCUS-04 | Spoofed path (`/etc/passwd`) returns `no_context` | unit | `pytest tests/test_serve.py::test_get_focus_context_spoofed_path_silent -x` | ❌ Wave 0 |
| FOCUS-04 | Deleted-on-disk file (FileNotFoundError) returns `no_context` | unit | `pytest tests/test_serve.py::test_get_focus_context_missing_file_silent -x` | ❌ Wave 0 |
| FOCUS-05 | Pull-model: no watchdog/thread import in serve.py | static | `pytest tests/test_serve.py::test_no_watchdog_import_in_focus_path -x` | ❌ Wave 0 |
| FOCUS-06 | Multi-seed uses compose_all (not hand-rolled BFS) | unit | `pytest tests/test_serve.py::test_multi_seed_compose_all_matches_expected -x` | ❌ Wave 0 |
| FOCUS-07 | `ProjectRoot(Path("graphify-out"))` raises at construction | unit | `pytest tests/test_snapshot.py::test_project_root_sentinel_rejects_graphify_out -x` | ❌ Wave 0 |
| FOCUS-07 | Nested-dir integration fixture: snapshots found when called correctly | integration | `pytest tests/test_snapshot.py::test_nested_dir_fixture_list_snapshots -x` | ❌ Wave 0 |
| FOCUS-07 | Rename callsites in serve.py use `project_root=` kwarg | smoke | `pytest tests/test_serve.py::test_snapshot_callsites_use_project_root -x` | ❌ Wave 0 |
| FOCUS-08 [P2] | Second call within 500ms returns cached envelope | unit | `pytest tests/test_serve.py::test_focus_debounce_suppresses_duplicate -x` | ❌ Wave 0 |
| FOCUS-08 [P2] | Call after 500ms computes fresh | unit | `pytest tests/test_serve.py::test_focus_debounce_expires -x` | ❌ Wave 0 |
| FOCUS-09 [P2] | `reported_at > 300s ago` returns `no_context` | unit | `pytest tests/test_serve.py::test_focus_stale_reported_at_rejected -x` | ❌ Wave 0 |
| FOCUS-09 [P2] | `reported_at = "...Z"` parses on Py 3.10 (compat shim) | unit | `pytest tests/test_serve.py::test_focus_reported_at_z_suffix_parses -x` | ❌ Wave 0 |
| FOCUS-09 [P2] | Malformed `reported_at` string returns `no_context` | unit | `pytest tests/test_serve.py::test_focus_malformed_reported_at -x` | ❌ Wave 0 |
| D-03 (cross) | Property test: spoof / unindexed / missing all produce byte-identical envelope shape | property | `pytest tests/test_serve.py::test_binary_status_invariant -x` | ❌ Wave 0 |
| D-08 (cross) | Budget pressure drops outer hop, preserves focus | unit | `pytest tests/test_serve.py::test_budget_drop_outer_hop_first -x` | ❌ Wave 0 |
| D-12 (cross) | No-context envelope does NOT contain echoed focus_hint values | unit | `pytest tests/test_serve.py::test_no_context_does_not_echo_focus_hint -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_serve.py tests/test_snapshot.py -q` (focus module + snapshot sentinel — ~30s)
- **Per wave merge:** `pytest tests/ -q` (full suite — current ~1295 tests + ~20 new = ~1315)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] Extend `tests/test_serve.py` with focus-resolver, envelope, binary-status, budget-drop, debounce, freshness cases (≈15 tests)
- [ ] Extend `tests/test_snapshot.py` with sentinel + nested-dir fixture (≈5 tests)
- [ ] `tests/conftest.py` — add a shared `nested_project_root(tmp_path)` fixture that lays out `tmp_path/project/graphify-out/snapshots/` AND returns `tmp_path/project` as project_root. Used by both test files.
- [ ] **No framework install needed** — pytest already in dev env.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MCP stdio server operates in single-user process lifetime; no auth layer. |
| V3 Session Management | no | Stateless dispatch per-call; no sessions. |
| V4 Access Control | yes | Path confinement via `security.py::validate_graph_path(path, base=project_root)` — FOCUS-04 enforces. |
| V5 Input Validation | yes | `focus_hint` dict fields: `file_path` (str), `function_name` (str?), `line` (int?), `neighborhood_depth` (int 1-6), `include_community` (bool), `reported_at` (ISO 8601 str?). JSON Schema in `mcp_tool_registry.py` validates shape; dispatcher applies additional clamps (budget `[50, 100000]`). |
| V6 Cryptography | no | No secrets, no tokens generated in this phase. |
| V7 Error Handling / Logging | yes | D-11 binary status + D-12 no-echo → error handling cannot leak info. Must NOT log focus_hint contents via `print(file=sys.stderr)` on failure paths. |
| V8 Data Protection | yes | No-echo of `focus_hint` in meta (D-12) prevents path-reflection leaks. |
| V14 Configuration | no | Not config-bound. |

### Known Threat Patterns for serve.py

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `file_path = "../../etc/passwd"` | Tampering / Info Disclosure | `validate_graph_path(path, base=project_root)` — existing primitive. `Path.resolve()` + `relative_to(base)` defeats `..`. |
| Path spoof enumeration ("is this file in the graph?") | Information Disclosure | D-03 + D-11 binary status. Unindexed file and spoof return byte-identical envelope. Property test asserts indistinguishability. |
| Focus-hint reflection XSS / log injection | Information Disclosure | D-12 no-echo. `text_body = ""` on no_context. All user-controlled strings that DO reach rendering pass through `sanitize_label()` (existing pattern). |
| Debounce cache DoS (unbounded growth) | DoS | Eviction cap at 256 entries (Pitfall 6 mitigation). |
| Freshness replay (old `reported_at` with current request) | Tampering | D-15 300s window + `no_context` on stale. Does NOT prevent current-time-spoof with near-future timestamps — out of scope; agent-trust-boundary assumption. |
| Prompt injection via `function_name` containing newlines | Tampering | All rendered labels pass through `sanitize_label()` (strips control chars). |

## Sources

### Primary (HIGH confidence)

- `graphify/serve.py` — 19 existing MCP tool implementations, D-02 envelope sentinel, budget clamping pattern `[VERIFIED: direct read of lines 429, 677, 757, 760, 1238, 2052]`.
- `graphify/security.py` — `validate_graph_path(path, base)` definition + default behavior `[VERIFIED: direct read of lines 144-170]`.
- `graphify/snapshot.py` — current `root: Path = Path(".")` API; 5 call-sites to rename `[VERIFIED: direct read of full file, 150 lines]`.
- `graphify/analyze.py` — `_iter_sources` and `_fmt_source_file` helpers for str|list[str] handling `[VERIFIED: direct read of lines 15-45]`.
- `graphify/validate.py` — `source_file` str|list schema enforcement point `[VERIFIED: direct read of lines 38-56]`.
- NetworkX 3.4.2 `ego_graph` + `compose_all` signature + empirical multi-seed behavior `[VERIFIED: python3 -c testing in venv]`.
- Python 3.10.19 `datetime.fromisoformat` Z-suffix rejection `[VERIFIED: python3 -c testing in venv]`.
- `.planning/research/PITFALLS.md` §§ Pitfall 20 (Snapshot path regression) `[VERIFIED: lines 406-426]`.
- `.planning/milestones/v1.3-phases/11-narrative-mode-slash-commands/11-REVIEW.md` CR-01 root cause narrative `[VERIFIED: line 64]`.

### Secondary (MEDIUM confidence)

- NetworkX docs for `ego_graph` and `compose_all` `[CITED: help(nx.ego_graph) inspected locally; semantics consistent across 2.x → 3.4.2 per NetworkX changelog]`.
- Python 3.11 `fromisoformat` changelog entry documenting `Z` support addition `[CITED: CPython bpo-35829 — general knowledge; not re-fetched in this session]`.

### Tertiary (LOW confidence)

- None. All claims cross-verified against source or runtime.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `compose_all` preserves all node + edge attributes from input subgraphs when nodes overlap | Pattern 1 + code example | LOW — NetworkX docs say compose preserves attrs from last input; multi-seed ego-graphs built from the same G have identical attrs for overlapping nodes, so last-write-wins is a no-op. Would show up as attribute mismatch tests if wrong. |
| A2 | `source_location` is reliably formatted as `"L<line>"` (e.g. `"L42"`) across all languages | Code Examples → `_resolve_focus_seeds` | MEDIUM — verified for Python tree-sitter extractor (`extract.py:116`). Not audited for every language's extractor. Planner should confirm per language OR use a more tolerant parser (`re.match(r"L?(\d+)", loc)`). |
| A3 | The nested-dir fixture reproduces CR-01 by constructing `ProjectRoot(Path("graphify-out"))` directly | Validation Architecture → Wave 0 Gaps | LOW — the bug IS the construction-time invariant; reproducing is literally calling the constructor. |
| A4 | The stdio server process lifetime is one-per-client, so module-level debounce state is client-scoped | Architectural Responsibility Map → Debounce cache | LOW — `serve.py:asyncio.run(main())` blocks until client disconnects; no process reuse. Verified via `_filter_blank_stdin()` + serve signature. |
| A5 | `manifest_content_hash` is merged by `_merge_manifest_meta` AFTER the core returns, so caching the core's envelope (not the final output) is correct | Pitfall 7 | LOW — read serve.py:1717 (`_merge_manifest_meta` splits on sentinel and rewrites meta). Confirmed caching-the-core avoids stale hash. |

## Open Questions

1. **Community summary shape (Claude's Discretion)**
   - What we know: D-06 defaults `include_community=true`. `analyze.god_nodes` returns `[{id, label, edges}]`. Cohesion scores live in `cluster.py`.
   - What's unclear: Exact fields to surface — `{community_id, member_count, top_nodes: [{id, label, degree}], cohesion_score}` vs just a string summary.
   - Recommendation: Planner picks minimal shape (`community_id`, `member_count`, `top_3_nodes_by_degree`, `cohesion_score`). Matches budget-conservative default. Defer `community_detail` enum arg to v1.5 (noted in Deferred Ideas).

2. **Does the resolver need to match `source_file` with relative OR absolute paths?**
   - What we know: D-04 mandates "Accept absolute OR relative paths; normalize" via `Path.resolve()`. Graph's `source_file` may be stored as relative (e.g. `"graphify/extract.py"`) OR absolute (e.g. `"/Users/.../graphify/extract.py"`) — varies by extractor.
   - What's unclear: A single comparison strategy for both.
   - Recommendation: Compare both the raw stored string AND `Path(s).resolve()` against the target's resolved form. Example pattern in code-example section. Planner's decision to refine.

3. **Should the resolver be its own module or stay inside `serve.py`?**
   - What we know: D-18 "compose-don't-plumb; no new modules." FOCUS resolver is ≈50 LOC.
   - What's unclear: Whether this crosses the "new module" threshold.
   - Recommendation: Keep in `serve.py` as `_resolve_focus_seeds` (private helper, like `_score_nodes`, `_bfs`, `_find_node`). Do NOT create `focus.py`. Matches D-18 literally.

4. **Exception subclass naming (Claude's Discretion)**
   - What we know: Default is `ValueError`. CONTEXT cites `DoubleNestedRootError(ValueError)` as a candidate deferred idea.
   - Recommendation: Start with `ValueError`. Add named subclass only if Phase 15 or 17 need to distinguish it catchably (e.g., for graceful degradation).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core runtime | ✓ | 3.10.19 | — |
| networkx | FOCUS-06 ego_graph | ✓ | 3.4.2 | — |
| pytest | Test execution | ✓ | (installed in dev env) | — |
| mcp package | MCP server runtime (not required for core tests) | optional (per pyproject `[mcp]` extra) | — | Core functions tested without `mcp` import — follows existing pattern. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None. All Phase 18 dependencies are already pinned.

## Project Constraints (from CLAUDE.md)

- **Python 3.10+ compatibility** — enforced. Affects `datetime.fromisoformat` Z-suffix handling (Pitfall 2).
- **No new required dependencies** — honored. Only stdlib + existing `networkx`.
- **Pure unit tests, no network, no FS side effects outside `tmp_path`** — honored. Nested-dir fixture lives under `tmp_path`.
- **Test files: `test_<module>.py`, one per module** — new tests extend existing `test_serve.py` and `test_snapshot.py`, not new files.
- **`graphify/security.py`** — all external input must pass through existing validators. FOCUS-04 uses `validate_graph_path` as-is.
- **No linter/formatter** — 4-space indent, type hints on all functions, `from __future__ import annotations` at top, docstrings on public functions. Follow `serve.py` existing style.
- **CI tests on 3.10 + 3.12** — MUST exercise the Z-suffix compat shim in the 3.10 leg.
- **Relative imports within `graphify/` package** — e.g., `from .snapshot import ProjectRoot`.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries verified in local venv; no version assumptions beyond training.
- Architecture: HIGH — every pattern has a direct precedent in `serve.py` (19 MCP tools use the same shape).
- Pitfalls: HIGH — Pitfall 1 (ego_graph single-seed) and Pitfall 2 (Py 3.10 Z-suffix) empirically verified; others derived from documented CR-01 + D-14/D-15 contracts.
- Security: HIGH — V4/V5/V7/V8 mitigations are all existing primitives. Binary-status invariant (D-11) is testable via property test.
- Snapshot rename scope: HIGH — grep + direct-read confirmed 5 callsite parameters + 4 serve.py wrapper call-sites.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — NetworkX 3.x ego_graph API, Py 3.10 datetime behavior, and internal `serve.py` patterns are all highly stable; 30-day window conservative).
