# Phase 15: Async Background Enrichment - Research

**Researched:** 2026-04-20
**Domain:** Python async CLI, fcntl.flock, atomic sidecar writes, LLM pass orchestration, MCP overlay merge
**Confidence:** HIGH (all findings grounded in direct reads of codebase sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Serial, fixed-order execution: `description → patterns → community → staleness`. One pass at a time, one writer to `enrichment.json`, one `fcntl.flock` holder for the whole run. No internal parallelism, no DAG resolver.
- **D-02:** Per-pass atomic commit, fail-abort-preserve. When a pass completes, its section is committed via `.tmp` + `os.replace`. On pass failure, partial write rolls back; prior-pass writes survive. Whole run then aborts. Next invocation resumes at failed-pass boundary (D-07).
- **D-03:** Priority-drain allocation. `--budget TOKENS` drains in pass order: description → patterns → community. Staleness is compute-only, exempt from budget accounting, always runs last.
- **D-04:** `--dry-run` emits a D-02-style envelope (human table + `\n---GRAPHIFY-META---\n{json}` footer). Per-pass: estimated tokens, API call count, $-estimate when `routing_models.yaml:pricing` populated.
- **D-05:** Per-pass sections under versioned envelope `{version:1, snapshot_id, generated_at, passes:{description, patterns, community, staleness}}`. Missing `passes` keys = not yet run or rolled back.
- **D-06:** Overlay-merge policy: enrichment augments, `graph.json` wins on conflict. Enriched text surfaces on new `enriched_description` field — does NOT overwrite `description`. Additive, inspectable, separable.
- **D-07:** Implicit resume-by-default, `snapshot_id`-gated. If `snapshot_id` matches, completed passes are skipped. If differs (graph rebuilt), discard existing file and start fresh. No `--resume` flag. No per-node intra-pass checkpointing.

### Claude's Discretion

- **Staleness thresholds** — the FRESH/STALE/GHOST decision function (days-since-source-mtime, git-age, node-degree drop thresholds). Planner picks defaults; a future phase can tune via `routing_models.yaml` if needed.
- **Watch.py trigger wiring** — whether post-rebuild hook spawns enrichment inline-awaited, via `subprocess.Popen` with a `.enrichment.pid` heartbeat (Pitfall 4 lifecycle), or queued through the existing `watch.py` dispatcher. Planner chooses approach that minimizes new process-lifecycle surface.
- **Patterns pass cross-snapshot depth** — how many historical snapshots under `graphify-out/snapshots/` the patterns pass reads, and how it caps storage cost. Default: last 5 snapshots unless research surfaces a stronger number.
- **Description-pass skip-list criteria** — whether skip-by-routing (ENRICH-11 P2) is "file already extracted by `complex` tier per `routing.json`", "node already has a non-empty `description` in `graph.json`", or both (AND).
- **Per-pass retry policy** — LLM call-level retries within a pass (exponential backoff, max attempts) before the pass is declared failed under D-02.

### Deferred Ideas (OUT OF SCOPE)

- User-Python deriver plugins (entry-point model)
- Real-time / pipeline-blocking enrichment
- Implicit enrichment on MCP `get_node`
- Budget-less passes
- Cross-session chat memory (Phase 17)
- Additional derivation passes beyond 4
- Per-node intra-pass checkpointing
- `enrichment_models.yaml`
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENRICH-01 | New module `graphify/enrich.py` + CLI subcommand `graphify enrich [--pass description|patterns|community|staleness] [--budget TOKENS] [--graph PATH]` | `__main__.py` CLI dispatch pattern (`elif cmd == "harness":`); argparse sub-parser pattern from `harness export` handler |
| ENRICH-02 | Four built-in derivation passes: description, patterns, community, staleness | Each pass isolated in `enrich.py`; reuses `delta.classify_staleness`, `analyze.god_nodes`, `snapshot.load_snapshot`, `routing.resolve_model` |
| ENRICH-03 | Enrichment writes overlay sidecar only (`graphify-out/enrichment.json`) — `graph.json` never mutated | `_write_graph_json` whitelist grep-CI pattern; `routing_audit.py` atomic-write pattern |
| ENRICH-04 | Atomic `.tmp` + `os.replace` write on `enrichment.json`; shared `fcntl.flock` on `.enrichment.lock` | `routing_audit.py:47-53` atomic pattern; `fcntl` available on macOS (confirmed) |
| ENRICH-05 | Enrichment pins `--snapshot-id` at process start and runs against that snapshot for whole run | `snapshot.list_snapshots()` + `snapshot.load_snapshot(path)` — snapshot stem is the ID |
| ENRICH-06 | Event-driven trigger via `watch.py` post-rebuild hook (opt-in `--enrich` flag); no `apscheduler` | `watch.py:_rebuild_code()` is the integration point; `subprocess.Popen` is the safe spawn pattern |
| ENRICH-07 | Foreground `/graphify` rebuild grabs `.enrichment.lock`; enrichment SIGTERM-aborts cleanly | `fcntl.flock(fd, LOCK_EX\|LOCK_NB)` raises `BlockingIOError` when lock held; SIGTERM handler flushes + exits |
| ENRICH-08 | `serve.py::_load_enrichment_overlay(out_dir)` merges enrichment at read time post-`_load_graph` | `serve.py:1918-1925` shows `G = _load_graph(graph_path)` then sidecar loading; overlay slips in after |
| ENRICH-09 | `serve.py::_reload_if_stale()` adds mtime watch for `enrichment.json` alongside `graph.json` | `serve.py:1941-1956` `_reload_if_stale` implementation pattern; `_file_mtime_or_zero` helper already exists |
| ENRICH-10 [P2] | `graphify enrich --dry-run` emits cost preview without LLM calls | `capability.py` cost-estimation pattern; D-02 envelope via `QUERY_GRAPH_META_SENTINEL` = `"\n---GRAPHIFY-META---\n"` |
| ENRICH-11 [P2] | Soft-dependency on Phase 12 `routing.json` — description pass skips files extracted by expensive model | `routing.json` structure: `{version:1, files:{path: {class, model, endpoint, tokens_used, ms}}}` |
| ENRICH-12 [P2] | Alias redirect (D-16) threaded through enrichment writes — derived content keyed by canonical node_id | `serve.py:883` `_resolve_alias()` closure pattern; `_load_dedup_report()` returns `{eliminated_id: canonical_id}` |
</phase_requirements>

---

## Summary

Phase 15 adds `graphify/enrich.py` — a serial four-pass background enricher that reads a pinned snapshot, calls LLMs for description/patterns/community enrichment, computes staleness deterministically, and writes all results to `graphify-out/enrichment.json` as an overlay-only sidecar. The foreground pipeline (`graph.json`) is never touched. The architecture is heavily pattern-reused: atomic writes mirror `routing_audit.py`, snapshot reading mirrors `_run_entity_trace`, overlay-merge mirrors the Phase 18 `_load_enrichment_overlay` slot already referenced in `serve.py`, and the MCP envelope mirrors `capability_describe`.

The central engineering challenge is the `fcntl.flock` coordination protocol: enrichment holds an exclusive lock on `.enrichment.lock` for the entire run, and the foreground pipeline must acquire the same lock before any `graph.json` write so it can signal enrichment to abort cleanly via SIGTERM. No existing graphify code uses `fcntl.flock` — this is new surface. The SIGTERM handler pattern and `.enrichment.pid` heartbeat are the most risk-laden implementation details.

**Primary recommendation:** Implement the per-pass atomic commit protocol first (D-02), then flock coordination (ENRICH-04, ENRICH-07), then the four passes in order, then serve.py integration (ENRICH-08, ENRICH-09). This order matches D-01 serial thinking and lets each plan build on tested prior art.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Enrichment orchestration + pass sequencing | CLI / Library (`enrich.py`) | — | New module per D-18 compose-don't-plumb; earns its own file |
| flock coordination + SIGTERM cleanup | CLI / Library (`enrich.py`) | `__main__.py` (lock on foreground rebuild) | Both participants must share the same lock file path |
| `enrichment.json` atomic write | Library (`enrich.py`) | — | Same `.tmp`+`os.replace` pattern as `routing_audit.py` |
| Snapshot pinning / reading | Library (`snapshot.py`) | `enrich.py` callee | `list_snapshots()` + `load_snapshot()` already handle this |
| Description enrichment LLM calls | Library (`enrich.py` description pass) | `routing.py` for tier selection | `routing.resolve_model()` picks tier per node's source file |
| Patterns cross-snapshot detection | Library (`enrich.py` patterns pass) | `snapshot.py`, `analyze.py` | Reads N snapshots via `list_snapshots()`, composes with `surprising_connections()` |
| Community summary generation | Library (`enrich.py` community pass) | `analyze.py` for community metadata | Reads `communities_from_graph()`, generates summaries per cluster |
| Staleness computation | Library (`enrich.py` staleness pass) | `delta.classify_staleness` | Pure compute — reuses existing classifier, no LLM |
| Overlay merge at query time | MCP server (`serve.py`) | `enrich.py` (writer) | Read-time merge keeps `graph.json` as truth source |
| mtime watch for `enrichment.json` | MCP server (`serve.py::_reload_if_stale`) | — | Extends existing mtime watcher; pattern is already scaffolded |
| Post-rebuild event trigger | File watcher (`watch.py`) | `__main__.py` (spawns) | `_rebuild_code()` is the hook point for `--enrich` opt-in |
| Alias resolution for enrichment writes | Library (`enrich.py`) | `serve.py::_load_dedup_report` | D-16 requires canonical node_id on write, not only on read |
| Budget accounting | Library (`enrich.py` orchestrator) | — | Priority-drain counter drains across description → patterns → community |
| Dry-run cost preview | CLI (`__main__.py` + `enrich.py`) | `routing.py` for token estimates | D-04 envelope; no LLM calls |

---

## Standard Stack

### Core (no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fcntl` | stdlib | `flock(fd, LOCK_EX\|LOCK_NB)` for single-writer coordination | POSIX, macOS available — confirmed `import fcntl` works |
| `signal` | stdlib | `SIGTERM` handler + `signal.alarm()` for max-runtime enforcement | No deps; `alarm()` works on macOS/Linux (POSIX) |
| `os` | stdlib | `os.replace()` for atomic writes; `os.getpid()` for heartbeat | Already used everywhere |
| `json` | stdlib | Sidecar read/write | Already used everywhere |
| `pathlib.Path` | stdlib | File paths, mtime reads | Already used everywhere |

### Existing graphify modules used by Phase 15

| Module | Function/Class | What Phase 15 uses it for |
|--------|---------------|--------------------------|
| `graphify/snapshot.py` | `list_snapshots(project_root)`, `load_snapshot(path)` | Pin snapshot at process start (ENRICH-05); patterns pass reads N prior snapshots |
| `graphify/routing.py` | `Router`, `resolve_model(metrics, file_type, config)`, `load_routing_config()` | Description pass selects tier per source file; `routing.json` skip-list (ENRICH-11 P2) |
| `graphify/cache.py` | `file_hash(path, model_id="")`, `load_cached(path, root, model_id=)`, `save_cached(...)` | Cache enriched descriptions per `(node_id, pass_name, model_id, source_file_hash)` |
| `graphify/delta.py` | `classify_staleness(node_data)` | Staleness pass reuses existing FRESH/STALE/GHOST classifier |
| `graphify/analyze.py` | `surprising_connections(G, communities)`, `_node_community_map()` | Patterns pass finds cross-snapshot surprises |
| `graphify/security.py` | `validate_graph_path(path, base=out_dir)`, `sanitize_label(text)` | All enrichment I/O routes through path guard; all label renders sanitized |
| `graphify/serve.py` | `_load_dedup_report(out_dir)`, `_reload_if_stale()`, `QUERY_GRAPH_META_SENTINEL` | Alias map for D-16; extend mtime watcher (ENRICH-09); dry-run envelope sentinel |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fcntl.flock` | `filelock` (PyPI) | `filelock` cross-platform; not needed since CI is macOS/Linux; adds a dependency. Use stdlib. |
| `signal.alarm()` | `threading.Timer` | Timer fires in a daemon thread, doesn't interrupt I/O; `alarm()` sends SIGALRM to process, reliably interrupts blocking calls on POSIX. Use `alarm()`. |
| `subprocess.Popen` (watch.py trigger) | inline function call | Inline avoids process lifecycle entirely; `Popen` needed only for true background detach. Given D-01 foreground-attached default, prefer inline call from `_rebuild_code`. |

**Installation:** No new packages. All functionality uses stdlib + existing graphify deps.

---

## Architecture Patterns

### System Architecture Diagram

```
  User / watch.py
       |
       | `graphify enrich [--budget N] [--pass X] [--dry-run]`
       v
  __main__.py  ─── parse args ──────────────────────────────────────────────────┐
                                                                                 |
                                                               enrich.py::run()  |
                                                                    |            |
                                           acquire fcntl.flock(.enrichment.lock) |
                                                (BlockingIOError = abort fast)   |
                                                    |                           |
                              read existing enrichment.json ◄──────── snapshot_id check (D-07 resume)
                                                    |
                                                    |──── [--dry-run] ──► emit D-02 cost envelope, exit
                                                    |
                               ┌────────────────────┴──────────────────────────────────────┐
                               |           pass_orchestrator (serial, D-01)               |
                               |                                                           |
                               |   description pass                                        |
                               |   ├── per-node: routing.resolve_model → tier             |
                               |   ├── cache.load_cached(node_id, pass, model_id)         |
                               |   ├── [cache miss] LLM call → enriched_description        |
                               |   ├── budget drain tracking                               |
                               |   └── atomic write passes.description section ──► .tmp+os.replace
                               |                                                           |
                               |   patterns pass  [budget permitting]                     |
                               |   ├── load last N snapshots via snapshot.list_snapshots()│
                               |   ├── compute cross-snapshot edge deltas                 |
                               |   ├── LLM: "what patterns emerged across these snapshots?"│
                               |   └── atomic write passes.patterns section               |
                               |                                                           |
                               |   community pass  [budget permitting]                    |
                               |   ├── per-community: node labels + descriptions          |
                               |   ├── LLM: natural-language community summary            |
                               |   └── atomic write passes.community section              |
                               |                                                           |
                               |   staleness pass  [always runs, compute-only]            |
                               |   ├── per-node: delta.classify_staleness(node_data)     |
                               |   ├── also checks: source_file mtime vs node.source_mtime│
                               |   └── atomic write passes.staleness section              |
                               |                                                           |
                               └───────── release flock ────────────────────────────────┘
                                                    |
                                             exit 0 (success)

  Foreground /graphify rebuild (concurrent):
       |
       | acquire .enrichment.lock (LOCK_EX, blocks or sends SIGTERM to enrichment PID)
       v
  enrichment process: SIGTERM → signal_handler → flush current pass → release lock → exit 1
```

### Recommended Project Structure

```
graphify/
├── enrich.py              # NEW: orchestrator + 4 pass implementations
graphify-out/
├── enrichment.json        # NEW: overlay sidecar (atomic write, never mutated in place)
├── .enrichment.lock       # NEW: exclusive write lock file (plain file, not enrichment.json)
├── .enrichment.pid        # NEW: heartbeat JSON {pid, started_at, expires_at}
tests/
├── test_enrich.py         # NEW: one test file per module convention
```

### Pattern 1: Per-Pass Atomic Commit (D-02)

**What:** Each pass writes its result atomically to `enrichment.json` using a read-modify-write on the versioned envelope.

**When to use:** After every pass completes successfully. Never for partial pass results.

```python
# Source: routing_audit.py:34-53 (reference pattern), adapted for enrichment
import json, os
from pathlib import Path

def _commit_pass(out_dir: Path, snapshot_id: str, pass_name: str, result: dict) -> None:
    """Atomically merge one pass result into enrichment.json. D-02 pattern."""
    enrichment_path = validate_graph_path(out_dir / "enrichment.json", base=out_dir)
    # except FileNotFoundError: enrichment.json doesn't exist yet - that's fine
    
    # Read current state (or start fresh)
    try:
        envelope = json.loads(enrichment_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        envelope = {
            "version": 1,
            "snapshot_id": snapshot_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passes": {},
        }
    
    envelope["passes"][pass_name] = result
    
    tmp = (out_dir / "enrichment.json").with_suffix(".tmp")
    try:
        path = validate_graph_path(out_dir / "enrichment.json", base=out_dir)  # security gate
        tmp.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, out_dir / "enrichment.json")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```

**Note:** `validate_graph_path` raises `FileNotFoundError` when the target doesn't exist; the write path must pre-check existence differently — write to `.tmp` first, then `os.replace` which creates the target. The security check should be on the `out_dir` (base), not the target file.

### Pattern 2: fcntl.flock Single-Writer Coordination (ENRICH-04, ENRICH-07)

**What:** One exclusive lock on `.enrichment.lock` for the entire enrichment run. Foreground rebuild acquires same lock before writing `graph.json`.

**When to use:** Process start (enrichment acquires) and foreground rebuild (acquires to signal enrichment to abort).

```python
# Source: [VERIFIED: fcntl stdlib docs + macOS fcntl module confirmed available]
import fcntl
import signal
import sys

_lock_fd = None
_current_pass_tmp: Path | None = None
_abort_requested = False

def _sigterm_handler(signum: int, frame: object) -> None:
    """Clean abort: cancel current pass tmp file, release lock, exit 1."""
    global _abort_requested
    _abort_requested = True
    if _current_pass_tmp and _current_pass_tmp.exists():
        _current_pass_tmp.unlink(missing_ok=True)
    if _lock_fd is not None:
        fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        _lock_fd.close()
    sys.exit(1)

def _acquire_lock(out_dir: Path) -> int:
    """Acquire exclusive flock on .enrichment.lock. Returns fd. Raises BlockingIOError if held."""
    lock_path = out_dir / ".enrichment.lock"
    fd = open(lock_path, "w")
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises BlockingIOError if taken
    return fd

def run(out_dir: Path, snapshot_id: str, budget: int, passes: list[str]) -> None:
    global _lock_fd
    signal.signal(signal.SIGTERM, _sigterm_handler)
    signal.alarm(600)  # Pitfall 4: max 10 minutes; SIGALRM fires if exceeded
    
    try:
        _lock_fd = _acquire_lock(out_dir)
    except BlockingIOError:
        print("[graphify enrich] Another process holds the enrichment lock. Aborting.", file=sys.stderr)
        sys.exit(2)
    
    _write_heartbeat(out_dir)
    
    try:
        _run_passes(out_dir, snapshot_id, budget, passes)
    finally:
        fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        _lock_fd.close()
        signal.alarm(0)  # cancel alarm
        _clear_heartbeat(out_dir)
```

### Pattern 3: Snapshot Pinning (ENRICH-05)

**What:** The `snapshot_id` is the **stem** of the most recent snapshot file (e.g., `2026-04-20T14-30-00`). This is already the natural key since `list_snapshots()` returns `Path` objects sorted by mtime.

**When to use:** At process start, before acquiring the lock. Pin to the most recent snapshot.

```python
# Source: graphify/snapshot.py:34-45 (list_snapshots), 80-130 (save_snapshot stem pattern)
from graphify.snapshot import list_snapshots, load_snapshot

def pin_snapshot(project_root: Path) -> tuple[str, Path]:
    """Return (snapshot_id, snapshot_path) for the most recent snapshot.
    
    snapshot_id = the snapshot file stem (e.g. '2026-04-20T14-30-00').
    This is stable, deterministic, and already used as the identity by save_snapshot().
    """
    snaps = list_snapshots(project_root)  # sorted oldest-first
    if not snaps:
        raise FileNotFoundError("No snapshots found. Run /graphify first.")
    latest = snaps[-1]
    return latest.stem, latest
```

**Resume check:** On invocation, read `enrichment.json["snapshot_id"]` and compare with `pin_snapshot()[0]`. Match → resume; mismatch → discard and restart.

### Pattern 4: Overlay Merge in serve.py (ENRICH-08)

**What:** `_load_enrichment_overlay(out_dir)` reads `enrichment.json` and adds `enriched_description`, `patterns_refs`, `community_summary`, `staleness_override` to the graph's node dicts — AFTER `_load_graph()` returns.

**When to use:** At server startup (after `_load_graph`) and inside `_reload_if_stale` when enrichment.json mtime changes.

```python
# Source: serve.py:1918-1935 (serve() init) — overlay slot is already present
# serve.py:2325 _enrichment_snapshot_id() shows enrichment.json already referenced

def _load_enrichment_overlay(G: nx.Graph, out_dir: Path) -> None:
    """Merge enrichment.json overlay onto G in-place. graph.json wins on conflict (D-06).
    
    Adds only new fields: enriched_description, staleness_override.
    Never overwrites base description, source_file, label, etc.
    Called after _load_graph() returns — never inside _load_graph itself (ENRICH-08).
    """
    p = out_dir / "enrichment.json"
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    
    passes = data.get("passes", {})
    
    # Description overlay (D-06: new field only)
    desc_map: dict[str, str] = passes.get("description", {})
    for node_id, enriched in desc_map.items():
        if node_id in G.nodes:
            G.nodes[node_id]["enriched_description"] = sanitize_label(enriched)
    
    # Staleness overlay (FRESH/STALE/GHOST override)
    stale_map: dict[str, str] = passes.get("staleness", {})
    for node_id, state in stale_map.items():
        if node_id in G.nodes and state in ("FRESH", "STALE", "GHOST"):
            G.nodes[node_id]["staleness_override"] = state
```

**Integration point in serve.py:** After line 1920 (`G = _load_graph(graph_path)`), add `_load_enrichment_overlay(G, _out_dir)`. Inside `_reload_if_stale`, after re-loading G, call overlay again. The `_enrichment_snapshot_id()` helper at line 2325 already reads enrichment.json — it is the scaffold for this.

### Pattern 5: _reload_if_stale Extension (ENRICH-09)

**What:** Track `enrichment.json` mtime alongside `graph.json` mtime. When enrichment changes, re-apply the overlay.

```python
# Source: serve.py:1941-1956 (_reload_if_stale current impl)
# New nonlocal variable: _enrichment_mtime: float = 0.0

def _reload_if_stale() -> None:
    nonlocal G, communities, _graph_mtime, _branching_factor, _enrichment_mtime
    # ... existing graph.json mtime check ...
    
    # NEW: enrichment.json mtime check
    enrich_path = _out_dir / "enrichment.json"
    try:
        enrich_mtime = enrich_path.stat().st_mtime if enrich_path.exists() else 0.0
    except OSError:
        enrich_mtime = 0.0
    if enrich_mtime != _enrichment_mtime:
        _load_enrichment_overlay(G, _out_dir)
        _enrichment_mtime = enrich_mtime
```

### Pattern 6: watch.py Trigger Wiring (ENRICH-06)

**What:** After `_rebuild_code()` succeeds, optionally spawn enrichment.

**Recommendation (Claude's discretion):** Use inline subprocess call (not daemon) to match foreground-attached default. Pitfall 4 lifecycle concerns are moot for an inline-spawned process because the parent `watch.py` loop controls lifetime. The `.enrichment.pid` heartbeat is still needed for the case where the user kills the watch loop.

```python
# Source: watch.py:_rebuild_code() (returns True/False at line ~95)
# Integration point: after line ~95 where _rebuild_code returns

def _rebuild_and_maybe_enrich(watch_path: Path, enrich_budget: int | None = None) -> bool:
    """Run rebuild; if --enrich is active and rebuild succeeded, spawn enrichment."""
    ok = _rebuild_code(watch_path)
    if ok and enrich_budget is not None:
        import subprocess
        subprocess.Popen(
            ["graphify", "enrich", "--budget", str(enrich_budget), "--graph",
             str(watch_path / "graphify-out" / "graph.json")],
            # Not DETACH: parent (watch loop) stays alive; Ctrl-C kills both
        )
    return ok
```

### Anti-Patterns to Avoid

- **Writing to `graph.json` from `enrich.py`:** Violates v1.1 D-invariant. The grep-CI test asserts only `build.py` + `__main__.py` call `_write_graph_json`. Any import of `_write_graph_json` in `enrich.py` must fail the test.
- **Holding the flock inside a pass failure handler:** Release on SIGTERM must be unconditional — put it in `finally:` not in the signal handler (to avoid double-release).
- **Reading `enrichment.json` before its parent dir exists:** `validate_graph_path` raises `ValueError` if base doesn't exist. Use `out_dir.mkdir(parents=True, exist_ok=True)` before any lock or sidecar operation.
- **Accumulating all snapshots in memory for patterns pass:** `load_snapshot()` returns a full `nx.Graph` — load one at a time, extract what you need, then `del G_snap` (Phase 11 memory discipline pattern at `serve.py:1626-1628`).
- **Using `signal.alarm()` without restoring it on normal exit:** Always `signal.alarm(0)` in the `finally:` block.
- **Per-node intra-pass checkpointing:** Explicitly out of scope per D-07. Do not implement. Budget abort means the whole pass rolls back.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom rename logic | `tmp = path.with_suffix(".tmp"); os.replace(tmp, path)` | Pattern in `routing_audit.py:47-53`, `cache.py:97-103`, `snapshot.py:102-110` — proven and consistent |
| FRESH/STALE/GHOST classification | Custom staleness logic | `delta.classify_staleness(node_data)` | Already handles source_hash, source_mtime fast-gate, GHOST for missing files |
| Snapshot listing/loading | Custom glob + JSON parse | `snapshot.list_snapshots(project_root)`, `snapshot.load_snapshot(path)` | CR-01 guards prevent double-nesting; `list_snapshots` sorts by mtime |
| Alias resolution | Direct dict lookup | `_load_dedup_report(out_dir)` + `_resolve_alias()` closure pattern from `serve.py:883-891` | D-16 invariant requires canonical node_id on all writes |
| Tier/model selection | Custom routing | `routing.Router.resolve(path)` → `ResolvedRoute` | ROUTE-06 floor (code never below simple) enforced here |
| Cache lookup | Custom hash | `cache.load_cached(path, root, model_id=model_id)` | `model_id` participates in key (ROUTE-04) — no cross-tier contamination |
| Label sanitization | Custom string clean | `security.sanitize_label(text)` | Strips control chars, caps at 256, needed before any enrichment text hits JSON |
| URL/path confinement | Custom path check | `security.validate_graph_path(path, base=out_dir)` | Prevents enrichment from writing outside `graphify-out/` |

**Key insight:** Every sidecar-writing pattern in graphify already uses `tmp + os.replace`. Do not invent a new write helper for `enrichment.json` — copy the exact pattern from `routing_audit.py`.

---

## Research Question Answers

### RQ-1: Pass design — inputs, outputs, LLM prompts, node-selection criteria

**Description pass:**
- **Input:** All nodes in the pinned snapshot graph where `node_data.get("description", "").strip()` is empty AND (ENRICH-11 opt) `routing.json` does not show file as `complex`-tier extracted.
- **Node selection:** Only code and document nodes (`file_type in {"code", "document"}`). Rationale nodes already have synthetic descriptions from extract.py.
- **Per-node data sent to LLM:** `label`, `source_file`, `source_location`, `file_type`, 1-3 neighbor labels (to provide structural context without blowing budget). Estimated ~200 input tokens per node.
- **LLM prompt template:** `"You are a code analyst. Write a one-sentence description of this {file_type} entity named '{label}' from {source_file} at {source_location}. Neighbors: {neighbor_labels}. Be factual and concise."` [ASSUMED]
- **Output:** `passes.description: {canonical_node_id: "one sentence"}` — sanitized via `sanitize_label`.
- **Tier selection:** Use `routing.Router.resolve(Path(source_file))` → `ResolvedRoute.tier`. Apply ROUTE-06 floor (code = min simple). For description enrichment, recommend capping at `simple` tier unless user explicitly sets `complex` — this controls per-node cost.

**Patterns pass:**
- **Input:** Last N snapshots (default 5 per Claude's discretion) loaded via `list_snapshots(project_root)[-5:]`.
- **Cross-snapshot delta:** For each snapshot pair, call `compute_delta(G_old, comms_old, G_new, comms_new)` → extract `added_nodes`, `community_migrations`. Accumulate a cross-snapshot pattern summary.
- **LLM prompt:** Feed the accumulated delta summary (not raw node lists — too large) to LLM asking "What recurring themes or structural patterns appear across these snapshots?" [ASSUMED]
- **Output:** `passes.patterns: [{pattern_id: str, nodes: [canonical_ids], summary: str}]`
- **Memory discipline:** Load one snapshot at a time, extract delta dict, `del G_snap` before loading next (pattern from `serve.py:1628`).

**Community pass:**
- **Input:** `communities` dict from snapshot graph (community_id → [node_ids]). For each community, collect: top 3 nodes by degree, their labels, their source_files.
- **LLM prompt:** `"Summarize community {community_id} in 1-2 sentences. It contains {n} nodes. Top members: {top_labels} from {source_files}."` [ASSUMED]
- **Output:** `passes.community: {community_id_str: "summary text"}`
- **Tier:** Fixed `simple` tier for all community summaries (they are short, structured prompts).

**Staleness pass:**
- **Input:** All nodes in live `graph.json` (NOT snapshot — staleness is against current disk state).
- **Algorithm:** For each node, call `delta.classify_staleness(node_data)` → FRESH/STALE/GHOST. This already checks `source_hash` + `source_mtime` fast gate.
- **Thresholds for Claude's discretion (recommended defaults):** STALE if source_mtime > 7 days older than `node_data.extracted_at`; GHOST if source_file not found on disk. These match `classify_staleness` behavior — no new threshold logic needed for v1.4. [ASSUMED — tune if needed]
- **Output:** `passes.staleness: {node_id: "FRESH|STALE|GHOST"}`
- **No LLM:** Compute-only. Exempt from budget.

### RQ-2: Exact fcntl.flock patterns

**Lock file:** `graphify-out/.enrichment.lock` (plain empty file; the lock is on the file descriptor, not the content).

**Enrichment acquires:**
```python
import fcntl
fd = open(out_dir / ".enrichment.lock", "w")
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    fd.close()
    raise  # foreground is running; enrichment aborts
```
[VERIFIED: fcntl.LOCK_EX, LOCK_NB, LOCK_UN available on macOS — confirmed via `import fcntl; dir(fcntl)`]

**Foreground pipeline acquires (to signal enrichment to abort):**
The foreground `/graphify` rebuild does NOT need to wait for enrichment to finish — it just needs to SIGTERM the enrichment PID from `.enrichment.pid` and wait briefly. Alternatively, the foreground can try `LOCK_EX | LOCK_NB` and if it fails, read `.enrichment.pid`, send SIGTERM, then wait with blocking `LOCK_EX`. This is simpler than implementing a separate kill-and-wait mechanism.

**SIGTERM handler:**
```python
_lock_fd: int | None = None
_current_tmp: Path | None = None

def _install_sigterm(lock_fd: int) -> None:
    global _lock_fd
    _lock_fd = lock_fd
    
    def _handler(sig, frame):
        if _current_tmp and _current_tmp.exists():
            _current_tmp.unlink(missing_ok=True)  # discard partial pass write
        if _lock_fd is not None:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            # Note: do NOT close fd here — OS closes on process exit
        sys.exit(1)
    
    signal.signal(signal.SIGTERM, _handler)
```

**Rollback semantics:** A failed pass leaves `enrichment.json["passes"]` without the failed pass key (it was never committed). Prior-pass keys remain. Next invocation of `enrich.py` reads the file, checks `snapshot_id` matches, finds missing key → resumes at that pass.

**Test fixture for race simulation:** Two-thread test where one thread holds the lock and another tries to acquire:
```python
def test_flock_contention(tmp_path):
    import fcntl, threading, time
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

### RQ-3: Snapshot pinning — snapshot_id scheme

The `snapshot_id` is the **stem of the snapshot file path** (e.g., `"2026-04-20T14-30-00"` or `"2026-04-20T14-30-00_myname"`). [VERIFIED: `snapshot.py:85-90` shows `stem` is `ts` or `f"{ts}_{sanitized}"`]

No new accessor is needed — `list_snapshots(project_root)[-1].stem` is the `snapshot_id`. This is already how `_enrichment_snapshot_id()` in `serve.py:2325-2336` reads it (it looks for `data.get("snapshot_id", data.get("version"))`).

**What gets pinned:** The full `Path` to the snapshot JSON file. Enrichment loads this once at startup via `load_snapshot(snap_path)`, extracts `G` and `communities`, then uses these as the stable substrate for all passes. Foreground rebuilds write new snapshots under new stems — the pinned path never changes mid-run.

**No mid-run snapshot following:** Even if the user runs `/graphify` and creates a new snapshot during enrichment, the enrichment process ignores it (it holds a reference to the original snapshot data already loaded into memory, or reads from the pinned path which is now immutable).

### RQ-4: routing.json skip-list for ENRICH-11 P2

`routing.json` structure [VERIFIED: `graphify-out/routing.json` inspected]:
```json
{
  "version": 1,
  "files": {
    "/abs/path/to/file.py": {
      "class": "complex",
      "model": "anthropic/claude-3-5-opus-latest",
      "endpoint": "https://api.anthropic.com/v1/messages",
      "tokens_used": 1234,
      "ms": 210.5
    }
  }
}
```

**Query pattern for description-pass skip-list (ENRICH-11):**
```python
def _load_skip_list(out_dir: Path) -> set[str]:
    """Return set of source_file paths already extracted at 'complex' tier."""
    routing_path = out_dir / "routing.json"
    if not routing_path.exists():
        return set()
    try:
        data = json.loads(routing_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    files = data.get("files", {})
    return {path for path, info in files.items() if info.get("class") == "complex"}
```

**Skip-list criteria (Claude's discretion recommendation):** Use both conditions with AND:
1. `node_data.get("source_file") in complex_skip_set` (routing.json skip)
2. `node_data.get("description", "").strip()` is non-empty (already has a description in graph.json)

Rationale: Condition 1 avoids re-paying for a node already enriched by the expensive Opus model during extraction. Condition 2 skips nodes that happen to have descriptions even if routing.json is absent (the soft-dependency case where Phase 12 is not installed).

### RQ-5: Overlay merge in serve.py — exact integration point

`_load_graph(graph_path)` is defined at `serve.py:431-449`. [VERIFIED]

It returns `nx.Graph` with nodes having attributes: `label`, `file_type`, `source_file`, `source_location`, `extracted_at`, `source_hash`, `source_mtime`, `id`, `community`. [VERIFIED: graph.json node sample inspected]

**`_load_enrichment_overlay` call site:**
- **Startup:** After `serve.py:1918` (`G = _load_graph(graph_path)`), add `_load_enrichment_overlay(G, _out_dir)`. Keep `_enrichment_mtime` in the `serve()` closure alongside `_graph_mtime`.
- **`_reload_if_stale`:** After re-assigning `G = _load_graph(graph_path)`, re-apply overlay. The overlay is idempotent (it only sets new fields, never overwrites base).

**Existing test mock safety (ENRICH-08):** Tests that mock `_load_graph` return a clean `nx.Graph` without enrichment fields. Since `_load_enrichment_overlay` is called AFTER `_load_graph` returns, and since tests that mock `_load_graph` also control what the mock returns (and `enrichment.json` won't exist in test `tmp_path`), the overlay function early-returns on missing file → tests stay green.

The `_enrichment_snapshot_id()` helper at `serve.py:2325-2336` already reads `enrichment.json` — it is the reconnaissance code for this integration. The full `_load_enrichment_overlay` implementation adds the actual node-mutation step.

### RQ-6: Zombie-process mitigation depth for D-01 serial CLI

Given D-01 serial, foreground-attached, single-process enrichment, the lifecycle is straightforward:
- User runs `graphify enrich` in terminal → foreground process
- Ctrl-C → SIGINT → clean exit (stdlib behavior)
- SIGTERM → custom handler (ENRICH-07) → clean exit

**Is `atexit`/`alarm()` overkill?** For the default foreground-attached case: `alarm(600)` is still recommended per Pitfall 4 as a safety net against infinite LLM hangs. `atexit` is useful for cleanup if normal exit skips the `finally:` block (e.g., on `SystemExit` from another thread). Both are lightweight enough to include.

**`watch.py` Popen case (ENRICH-06):** When `watch.py` spawns enrichment via `subprocess.Popen`, the child process IS a background process. In this case:
- `.enrichment.pid` heartbeat IS required (so next `graphify enrich` invocation detects and purges stale lock)
- `alarm(600)` IS required (watch loop may be killed without sending SIGTERM to children on macOS)
- Parent watch loop should register `atexit` to send SIGTERM to enrichment PID on watch exit

**Recommendation:** Always write `.enrichment.pid` and always set `alarm(600)`. The cost is negligible; the safety value is high.

### RQ-7: Minimum test coverage matrix

| Test category | Test name | What it asserts |
|---------------|-----------|-----------------|
| Lifecycle: SIGTERM | `test_sigterm_aborts_cleanly` | SIGTERM during pass rolls back tmp file; prior passes preserved; exit code 1 |
| Lifecycle: alarm | `test_alarm_fires_and_exits` | `signal.alarm(1)` fires; process exits; no corrupt enrichment.json |
| Lock: contention | `test_flock_blocks_second_writer` | Second `LOCK_EX\|LOCK_NB` raises `BlockingIOError` |
| Lock: release on failure | `test_lock_released_after_pass_failure` | After simulated pass failure, lock is released and reacquirable |
| Schema: D-05 envelope | `test_enrichment_json_schema` | `version=1`, `snapshot_id`, `passes` keys present after a run |
| Schema: per-pass commit | `test_per_pass_atomic_commit` | After pass 1 completes, `passes["description"]` is present even if pass 2 fails |
| Overlay: D-06 merge | `test_overlay_augments_not_overwrites` | `enriched_description` added; `description` unchanged |
| Overlay: missing file | `test_overlay_handles_missing_enrichment_json` | No exception raised; graph unchanged |
| Resume: D-07 snapshot match | `test_resume_skips_completed_passes` | If `snapshot_id` matches and `passes["description"]` present, description pass is skipped |
| Resume: snapshot mismatch | `test_resume_discards_on_snapshot_change` | Different `snapshot_id` → file discarded → fresh run |
| Budget: drain | `test_budget_drain_aborts_remaining_passes` | If budget exhausted after description, patterns pass is not called |
| Alias: D-16 | `test_enrichment_writes_canonical_id` | Eliminated alias written under canonical ID, not alias |
| Grep-CI invariant | `test_write_graph_json_caller_whitelist` | Only `build.py` + `__main__.py` contain `_write_graph_json` |
| Staleness: compute-only | `test_staleness_pass_makes_no_llm_calls` | Staleness pass runs with mocked LLM that asserts not called |
| Watch trigger | `test_watch_spawns_enrich_on_rebuild` | `_rebuild_and_maybe_enrich` with `--enrich` spawns subprocess |

### RQ-8: Existing test patterns for signal/subprocess coordination

**No existing fcntl.flock tests in the codebase.** [VERIFIED: `grep -rn "fcntl" tests/` returned zero results]

**Existing subprocess patterns** (from `test_main_cli.py`):
```python
def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["graphify", *args],
        capture_output=True, text=True, timeout=30,
    )
```

**Recommended test patterns for Phase 15:**

For SIGTERM test (can't easily SIGTERM in-process — use threading with `os.kill`):
```python
def test_sigterm_aborts_cleanly(tmp_path):
    import threading, os, signal, time
    
    # Run enrichment in a thread that holds a simulated long pass
    results = {}
    def _run():
        results["exit"] = os.system(f"graphify enrich --graph {tmp_path}/... &")
    
    # Better: use subprocess.Popen, send SIGTERM, check exit code
    proc = subprocess.Popen(["graphify", "enrich", "--budget", "1000", 
                             "--graph", str(out_dir / "graph.json")])
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)
    assert proc.returncode == 1
```

For `_commit_pass` atomic rollback (unit test, no subprocess needed):
```python
def test_per_pass_atomic_commit(tmp_path):
    from graphify.enrich import _commit_pass
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    
    _commit_pass(out_dir, "snap1", "description", {"node_a": "A does X"})
    
    data = json.loads((out_dir / "enrichment.json").read_text())
    assert data["passes"]["description"]["node_a"] == "A does X"
    assert data["snapshot_id"] == "snap1"
    assert data["version"] == 1
```

**make_snapshot_chain fixture** is directly reusable for all snapshot-reading tests. [VERIFIED: `conftest.py:76-136`]

### RQ-9: Staleness pass signal set (no LLM)

The existing `delta.classify_staleness(node_data)` [VERIFIED: `delta.py:68-98`] already provides:
1. `source_hash` comparison (SHA256 of current file bytes vs stored)
2. `source_mtime` fast gate (avoids SHA256 when mtime unchanged)
3. GHOST detection (source_file no longer on disk)

**Phase 15 staleness pass wraps this directly.** No additional signals are needed for v1.4. If git-age were needed, it would require `subprocess.run(["git", "log", "-1", "--format=%ct", path])` — avoid this for now (shell-out in a background process risks signal/pipe interactions). Node degree change across snapshots is already captured by the patterns pass; staleness should remain focused on source-file freshness.

**Recommended staleness thresholds (Claude's discretion defaults):**
- GHOST: `source_file` not found on disk (already in `classify_staleness`)
- STALE: `source_hash` differs from current file hash (already in `classify_staleness`)
- FRESH: everything else (already in `classify_staleness`)

No new threshold logic needed. The staleness pass simply calls `classify_staleness(G.nodes[nid])` for every node and accumulates the results.

### RQ-10: Patterns pass cross-snapshot depth and storage cost

**Snapshot storage:** `graphify-out/snapshots/*.json` — each file is a full serialized `nx.Graph` + communities dict. For the graphify codebase at 4143 nodes / 4998 edges, a snapshot JSON is approximately 2-4 MB.

**Depth recommendation (Claude's discretion): last 5 snapshots.**
Rationale: 5 snapshots covers ~5 rebuild cycles (typical dev session). Loading 5 × 4 MB = 20 MB peak memory, which is acceptable. With `del G_snap` after each (memory discipline from `serve.py:1628`), peak is one snapshot at a time (4 MB). The patterns pass accumulates a delta summary dict (small) across the chain.

**Pattern detection algorithm:**
- Load snapshots oldest-first: `list_snapshots(project_root)[-5:]`
- For consecutive pairs: `compute_delta(G_old, comms_old, G_new, comms_new)` → `added_nodes`, `community_migrations`
- Accumulate: nodes that appear in `added_nodes` across 2+ delta pairs are "emerging"; communities that gain members consistently are "growing"
- Send this structured summary to LLM (not raw graphs) to generate pattern descriptions

**Storage cap:** The existing `save_snapshot(..., cap=10)` FIFO prune handles this. No new cap mechanism needed for the patterns pass — it just reads what's there.

---

## Runtime State Inventory

> Not a rename/refactor phase. Omit this section.

None — greenfield module addition, no renaming of existing state.

---

## Common Pitfalls

### Pitfall 1: Writing enrichment.json before acquiring the lock

**What goes wrong:** Enrichment starts writing immediately, then tries to acquire the lock. A concurrent foreground rebuild has already acquired the lock and is writing `graph.json`. The sidecar write races with foreground state.

**Why it happens:** Developers write the happy-path first and add locking as an afterthought.

**How to avoid:** Acquire the lock as the FIRST operation after arg parsing. All file I/O happens inside the lock scope.

**Warning signs:** Test: start enrichment write and foreground rebuild simultaneously; diff `enrichment.json` — if it contains partial data from two concurrent writers, the invariant is broken.

### Pitfall 2: Closing the lock fd inside the SIGTERM handler

**What goes wrong:** SIGTERM handler calls `fd.close()`, then the `finally:` block also tries `fcntl.flock(fd, LOCK_UN)` → `OSError: [Errno 9] Bad file descriptor`.

**How to avoid:** In the SIGTERM handler, only release the lock (`LOCK_UN`), do NOT close the fd. Let the process exit clean the fd. Put `fd.close()` only in the normal-exit `finally:` path.

### Pitfall 3: Using graph.json as the patterns-pass substrate

**What goes wrong:** Patterns pass reads live `graph.json` instead of pinned snapshot. Between the description pass and the patterns pass, the user runs `/graphify` and `graph.json` is rebuilt. Patterns pass sees a different graph than description pass.

**How to avoid:** Pin snapshot at process start (ENRICH-05). All four passes read from the pinned snapshot data (loaded once into memory or read from the snapshot file). Only the staleness pass reads live `graph.json` by design (it must check current disk state).

### Pitfall 4: ProjectRoot sentinel — passing out_dir instead of project_root

**What goes wrong:** `snapshot.list_snapshots(out_dir)` where `out_dir = graphify-out/`. This triggers the v1.3 CR-01 guard and raises `ValueError`.

**How to avoid:** Always pass `project_root = out_dir.parent` to all `snapshot.*` functions. The `ProjectRoot` dataclass in `snapshot.py` enforces this at construction time. [VERIFIED: `snapshot.py:15-31`]

### Pitfall 5: validate_graph_path raises FileNotFoundError on enrichment.json before first run

**What goes wrong:** `validate_graph_path(out_dir / "enrichment.json", base=out_dir)` raises `FileNotFoundError` when no enrichment run has happened yet.

**How to avoid:** For reads, check `p.exists()` before calling `validate_graph_path`. For writes, call `validate_graph_path` on the `out_dir` (base) only — the target file may not exist yet. Write to `.tmp` first; `os.replace` creates the target.

### Pitfall 6: Staleness pass modifying graph.json via G.nodes[x]["staleness_override"]

**What goes wrong:** `enrich.py` imports the live `nx.Graph` object and mutates node attributes, which then gets serialized back to `graph.json` by some other path.

**How to avoid:** Staleness results go ONLY to `enrichment.json["passes"]["staleness"]`. The `_load_enrichment_overlay` in `serve.py` applies staleness overrides in-memory at query time. `enrich.py` never touches the `G` object from `_load_graph`.

---

## Code Examples

### enrichment.json schema (D-05 reference)

```json
{
  "version": 1,
  "snapshot_id": "2026-04-20T14-30-00",
  "generated_at": "2026-04-20T14:35:12+00:00",
  "passes": {
    "description": {
      "graphify_extract_py": "Dual extraction module handling both deterministic tree-sitter AST and LLM semantic analysis.",
      "graphify_cache_py": "SHA256-based per-file semantic cache that skips unchanged files on re-run."
    },
    "patterns": [
      {
        "pattern_id": "emerging_security_cluster",
        "nodes": ["graphify_security_py", "graphify_validate_py"],
        "summary": "Security and validation modules are increasingly co-referenced across snapshots."
      }
    ],
    "community": {
      "0": "The extraction and caching cluster — core pipeline that transforms source files into graph nodes.",
      "1": "The MCP server cluster — serves graph queries, annotations, and overlay merging."
    },
    "staleness": {
      "graphify_extract_py": "FRESH",
      "graphify_cache_py": "STALE",
      "old_deleted_module": "GHOST"
    }
  }
}
```

### D-02 dry-run envelope format (ENRICH-10)

```
Enrichment dry-run — budget: 10000 tokens

Pass         | Est. nodes | Est. tokens | Est. API calls | Est. cost
description  | 2276       | 8,000       | 2276           | —
patterns     | 5 snaps    | 1,500       | 5              | —
community    | 919 comms  | 500         | 919            | —
staleness    | 4143 nodes | 0 (compute) | 0              | (exempt)

Total (LLM): 10,000 tokens (matches budget — will complete all 3 LLM passes)

---GRAPHIFY-META---
{"status":"ok","dry_run":true,"budget":10000,"passes":{"description":{"est_nodes":2276,"est_tokens":8000,"est_calls":2276},"patterns":{"est_tokens":1500,"est_calls":5},"community":{"est_tokens":500,"est_calls":919},"staleness":{"est_tokens":0,"compute_only":true}}}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| enrichment.jsonl append-only (Pitfall 3 default) | `enrichment.json` with versioned envelope + per-pass sections | Phase 15 decision (D-05) | Resume is per-pass, not per-record; simpler overlay merge |
| No overlay merge (flat graph dump) | Read-time overlay via `_load_enrichment_overlay` | Phase 15 (ENRICH-08) | `graph.json` stays deterministic; enrichment is inspectable and separable |
| No background enrichment | Event-driven via `watch.py` post-rebuild + explicit `graphify enrich` | Phase 15 | Graph quality improves passively without blocking foreground pipeline |

**Deprecated/outdated:**
- PITFALLS.md §Pitfall 3 mentions `enrichment.jsonl` + `enrichment_index.json` as the initial design — SUPERSEDED by D-05 versioned JSON envelope. Do not implement the JSONL approach.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `fcntl` (stdlib) | ENRICH-04, ENRICH-07 lock | Yes | Python 3.10+ stdlib (macOS, Linux) | — (no fallback; Windows not CI target) |
| `signal` (stdlib) | Pitfall 4 alarm + SIGTERM handler | Yes | Python 3.10+ stdlib | — |
| `graphify/snapshot.py` | ENRICH-05, patterns pass | Yes | Phase 15 inherits CR-01 guards | — |
| `graphify/routing.py` | ENRICH-11 skip-list | Yes (Phase 12 shipped) | Phase 12 complete | Graceful: if `routing.json` absent, skip-list is empty set |
| `graphify/delta.py::classify_staleness` | Staleness pass | Yes | Current codebase | — |
| `graphify-out/routing.json` | ENRICH-11 P2 | Optional (soft-dep) | Present if Phase 12 was run | Empty skip-list if absent — pass runs normally |
| `graphify-out/snapshots/` | ENRICH-05, patterns pass | Optional | May be empty if user never ran with snapshot | `FileNotFoundError` → user-friendly error message; enrich requires at least 1 snapshot |

**Missing dependencies with no fallback:**
- None that block the phase.

**Missing dependencies with fallback:**
- `routing.json` absent → ENRICH-11 P2 skip-list is empty (all nodes eligible for description enrichment).
- No snapshots → enrichment aborts with clear message: "No snapshots found. Run /graphify first to generate a snapshot."

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in CI) |
| Config file | none (bare `pytest tests/`) |
| Quick run command | `pytest tests/test_enrich.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENRICH-01 | `graphify enrich --help` exits 0 with correct usage | smoke | `pytest tests/test_enrich.py::test_cli_enrich_help -q` | Wave 0 |
| ENRICH-02 | All 4 passes produce correct output schema | unit | `pytest tests/test_enrich.py::test_all_passes_schema -q` | Wave 0 |
| ENRICH-03 | `graph.json` unchanged after enrichment run | unit | `pytest tests/test_enrich.py::test_graph_json_not_mutated -q` | Wave 0 |
| ENRICH-04 | Atomic write: partial write does not corrupt sidecar | unit | `pytest tests/test_enrich.py::test_atomic_write_rollback -q` | Wave 0 |
| ENRICH-04 | flock contention raises BlockingIOError | unit | `pytest tests/test_enrich.py::test_flock_blocks_second_writer -q` | Wave 0 |
| ENRICH-05 | Snapshot_id pinned at start; mid-run rebuild ignored | unit | `pytest tests/test_enrich.py::test_snapshot_pinning -q` | Wave 0 |
| ENRICH-06 | watch.py with `--enrich` spawns enrichment after rebuild | integration | `pytest tests/test_enrich.py::test_watch_enrich_trigger -q` | Wave 0 |
| ENRICH-07 | SIGTERM during pass → clean exit, prior passes preserved | integration | `pytest tests/test_enrich.py::test_sigterm_aborts_cleanly -q` | Wave 0 |
| ENRICH-08 | `_load_enrichment_overlay` adds `enriched_description`, does not overwrite `description` | unit | `pytest tests/test_enrich.py::test_overlay_augments_not_overwrites -q` | Wave 0 |
| ENRICH-09 | `_reload_if_stale` re-applies overlay when `enrichment.json` mtime changes | unit | `pytest tests/test_serve.py::test_reload_if_stale_enrichment -q` | Wave 0 (new test in existing file) |
| ENRICH-10 [P2] | `--dry-run` emits D-02 envelope, no LLM calls | unit | `pytest tests/test_enrich.py::test_dry_run_envelope -q` | Wave 0 |
| ENRICH-11 [P2] | Description pass skips complex-tier files | unit | `pytest tests/test_enrich.py::test_skip_list_complex_tier -q` | Wave 0 |
| ENRICH-12 [P2] | Enrichment writes under canonical node_id (alias redirected) | unit | `pytest tests/test_enrich.py::test_alias_redirect_in_enrichment -q` | Wave 0 |
| SC-5 invariant | Only `build.py` + `__main__.py` call `_write_graph_json` | grep-CI | `pytest tests/test_enrich.py::test_write_graph_json_caller_whitelist -q` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_enrich.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_enrich.py` — all 15 tests above (new file)
- [ ] `tests/test_serve.py::test_reload_if_stale_enrichment` — new test in existing file (ENRICH-09)
- [ ] `graphify/enrich.py` — module must exist before tests can import it (stub with `pass` bodies is sufficient for Wave 0 RED state)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not applicable — no auth in enrichment |
| V3 Session Management | no | Not applicable |
| V4 Access Control | no | Enrichment is CLI-only, same-user process |
| V5 Input Validation | yes | `security.sanitize_label(text)` on all LLM output before writing to sidecar |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for Phase 15 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM output with injected HTML/control chars in enriched_description | Tampering | `sanitize_label(text)` before write; `sanitize_label_md` before render |
| Path traversal via node_id containing `../` | Tampering | `validate_graph_path(base=out_dir)` on all write targets; node_ids are slugified (alphanumeric + underscore only by `_make_id()`) |
| enrichment.json write escaping out_dir | Tampering | `validate_graph_path(out_dir / "enrichment.json", base=out_dir)` — but note: file must exist for validation; write pattern must validate `out_dir` instead (see Pitfall 5) |
| Secret in node description exported via ENRICH-08 overlay | Information Disclosure | Pitfall 11: `enriched_description` fields must go through same allow-list as SEED-002 exports when `graphify harness export --include-annotations` is later called. Phase 15 itself doesn't export — but annotate in code that enriched fields are annotation-class data |
| Zombie enrichment process leaking PID files | Denial of Service | `.enrichment.pid` with `expires_at`; stale-PID check on next invocation; `alarm(600)` hard cutoff |
| `yaml.safe_load` requirement | Tampering | `routing_models.yaml` loaded via `yaml.safe_load` (enforced in `routing.py:load_routing_config`) — enrichment must not call `yaml.load` anywhere |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Description pass LLM prompt template produces useful 1-sentence descriptions | RQ-1: Description pass | Low — prompt can be tuned without API changes |
| A2 | 200 input tokens per node is a reasonable estimate for description pass cost preview | RQ-1, ENRICH-10 | Low — dry-run is an estimate, budget math uses it |
| A3 | "Last 5 snapshots" is the right depth for patterns pass | RQ-10 | Medium — if users have many snapshots, 5 may miss patterns; if few, 5 is fine |
| A4 | Staleness thresholds don't need tuning beyond classify_staleness defaults for v1.4 | RQ-9 | Low — staleness pass is compute-only; wrong thresholds produce wrong STALE labels but don't corrupt state |
| A5 | Inline `subprocess.Popen` (not daemon) is the right watch.py trigger pattern | RQ-6 | Medium — if users want truly non-blocking enrichment, daemon would be needed; v1.4 defers this |
| A6 | `signal.alarm()` works reliably on macOS for 600s timeout | RQ-2 | Low — POSIX-required; macOS fcntl confirmed available |

---

## Open Questions

1. **Foreground lock acquisition mechanism**
   - What we know: `__main__.py` runs `/graphify` rebuild via `build.py`; foreground must acquire `.enrichment.lock` before writing `graph.json`
   - What's unclear: Where exactly in `__main__.py` the lock acquisition goes — before `to_json()` in the pipeline, or wrapped around the entire `graphify run` command
   - Recommendation: Planner should identify the exact line in `__main__.py` where `to_json()` / `_write_graph_json` is called and insert lock acquisition there

2. **Community pass — what "community_id" is keyed on**
   - What we know: Communities are `dict[int, list[str]]`; `enrichment.json["passes"]["community"]` should key by community_id
   - What's unclear: Whether community IDs are stable across snapshot rebuilds (they are not — Leiden is re-run each time, IDs may shift)
   - Recommendation: Key by `community_id` from the PINNED SNAPSHOT communities, not the live graph communities. Include a note in the overlay-merge code that community summaries are snapshot-pinned and may be stale after rebuild.

3. **Budget estimation accuracy for ENRICH-10 dry-run**
   - What we know: Real token counts require actual LLM calls; dry-run must estimate without calling
   - What's unclear: Optimal estimation heuristic (node count × estimated tokens/node is crude)
   - Recommendation: Use `len(label) // 4 + 150` as token estimate per node (conservative), plus a fixed overhead per API call

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: graphify/snapshot.py] — `list_snapshots()`, `load_snapshot()`, `save_snapshot()`, `ProjectRoot` sentinel, snapshot_id = stem pattern
- [VERIFIED: graphify/cache.py] — `file_hash(path, model_id="")`, `load_cached`, `save_cached`, atomic write pattern
- [VERIFIED: graphify/routing.py] — `Router.resolve()`, `ResolvedRoute`, `load_routing_config()`, tier hierarchy
- [VERIFIED: graphify/routing_models.yaml] — tier→model mapping, pricing structure, ROUTE-06 floor
- [VERIFIED: graphify/routing_audit.py:34-53] — canonical atomic write pattern (tmp + os.replace)
- [VERIFIED: graphify/delta.py:68-98] — `classify_staleness()` implementation, FRESH/STALE/GHOST signals
- [VERIFIED: graphify/serve.py:431-449] — `_load_graph()` implementation and return shape
- [VERIFIED: graphify/serve.py:1909-1970] — `serve()` init, `_reload_if_stale()`, `_out_dir`, closure state
- [VERIFIED: graphify/serve.py:2325-2336] — `_enrichment_snapshot_id()` — scaffold for overlay integration
- [VERIFIED: graphify/serve.py:1941-1956] — `_reload_if_stale()` current mtime pattern
- [VERIFIED: graphify/serve.py:828] — `QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"`
- [VERIFIED: graphify/serve.py:883-891] — `_resolve_alias()` closure pattern for D-16
- [VERIFIED: graphify/security.py:144-200] — `validate_graph_path()`, `sanitize_label()`, `sanitize_label_md()`
- [VERIFIED: graphify/watch.py] — `_rebuild_code()` integration point, event loop structure
- [VERIFIED: graphify/__main__.py:1009-1080, 1740-1830] — CLI dispatch pattern, `elif cmd ==` conventions
- [VERIFIED: graphify-out/graph.json] — node attribute schema (label, file_type, source_file, community, etc.)
- [VERIFIED: graphify-out/routing.json] — `{version:1, files:{path:{class,model,endpoint,tokens_used,ms}}}` structure
- [VERIFIED: tests/conftest.py:76-136] — `make_snapshot_chain` fixture, reusable for enrich tests
- [VERIFIED: Python 3.10.19 on macOS] — `import fcntl; dir(fcntl)` shows LOCK_EX, LOCK_NB, LOCK_UN available
- [VERIFIED: graphify codebase grep] — zero existing uses of `fcntl.flock` — all new surface

### Secondary (MEDIUM confidence)

- [CITED: PITFALLS.md §Pitfall 3] — sidecar-only write, single-writer flock mitigation
- [CITED: PITFALLS.md §Pitfall 4] — zombie process mitigation, heartbeat, alarm pattern
- [CITED: PITFALLS.md §Pitfall 11] — secret over-export risk for enrichment annotations
- [CITED: 15-CONTEXT.md §Established patterns] — atomic write, MCP envelope, alias redirect, grep-CI patterns
- [CITED: ARCHITECTURE.md §Integration conventions] — D-02 envelope, D-16 alias, D-18 compose-don't-plumb

### Tertiary (LOW confidence — marked ASSUMED in text)

- LLM prompt templates (A1, A2, A3) — formative, expected to be tuned during implementation
- Staleness threshold defaults (A4) — based on `classify_staleness` behavior, not additional research

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no new deps, all existing modules verified
- Architecture: HIGH — all integration points verified in source code with line references
- Pitfalls: HIGH — grounded in PITFALLS.md + direct source reading + fcntl behavior verified
- LLM prompt templates: LOW — [ASSUMED]; only formative, easy to tune

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — no fast-moving deps, all stdlib + frozen internal modules)
