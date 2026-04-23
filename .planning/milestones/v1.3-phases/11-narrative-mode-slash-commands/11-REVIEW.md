---
phase: 11-narrative-mode-slash-commands
reviewed: 2026-04-17T11:45:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - graphify/serve.py
  - graphify/__main__.py
  - graphify/commands/context.md
  - graphify/commands/trace.md
  - graphify/commands/connect.md
  - graphify/commands/drift.md
  - graphify/commands/emerge.md
  - graphify/commands/ghost.md
  - graphify/commands/challenge.md
  - graphify/skill.md
  - graphify/skill-codex.md
  - graphify/skill-opencode.md
  - graphify/skill-aider.md
  - graphify/skill-copilot.md
  - graphify/skill-claw.md
  - graphify/skill-droid.md
  - graphify/skill-trae.md
  - graphify/skill-windows.md
  - pyproject.toml
  - tests/conftest.py
  - tests/test_serve.py
  - tests/test_commands.py
  - tests/test_install.py
  - tests/test_pyproject.py
  - tests/test_skill_files.py
findings:
  critical: 2
  warning: 2
  info: 3
  total: 7
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-04-17T11:45:00Z
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

Phase 11 adds five narrative-mode slash commands (`/context`, `/trace`, `/connect`, `/drift`, `/emerge`) plus two stretch commands (`/ghost`, `/challenge`). The MCP layer is implemented cleanly with pure-function helpers (`_run_*`), Phase 9.2 hybrid envelopes with the correct `\n---GRAPHIFY-META---\n` sentinel, alias-map support throughout, and explicit `del G_snap` memory discipline in all snapshot-chain walkers.

Two critical bugs were found:

1. **Snapshot path double-nesting**: All four Phase 11 snapshot-aware tools (`graph_summary`, `entity_trace`, `drift_nodes`, `newly_formed_clusters`) will silently return `insufficient_history` in production because `_out_dir` (which is `graphify-out/`) is passed as the `root` parameter to `list_snapshots()`, causing it to scan `graphify-out/graphify-out/snapshots/` instead of `graphify-out/snapshots/`. Tests are written with `tmp_path` as the root so they never expose this bug.

2. **`_cursor_install()` called without required argument**: `install(platform="cursor")` calls `_cursor_install()` with zero arguments, but the function signature is `_cursor_install(project_dir: Path)` with no default. This raises `TypeError` at runtime for any cursor install invocation via the `install()` helper.

---

## Critical Issues

### CR-01: Snapshot path double-nesting — Phase 11 tools always return `insufficient_history` in production

**File:** `graphify/serve.py:1677,2083,2113,2128,2143`
**Issue:** `serve()` initialises `_out_dir = Path(graph_path).parent`. When `graph_path = "graphify-out/graph.json"`, `_out_dir = Path("graphify-out")`. All four Phase 11 snapshot-aware tool closures pass `_out_dir` as the `root` parameter to `_run_graph_summary`, `_run_entity_trace`, `_run_drift_nodes`, and `_run_newly_formed_clusters`. Each of those functions calls `list_snapshots(snaps_dir)` from `graphify/snapshot.py`, which expands to `root / "graphify-out" / "snapshots"`. With `_out_dir` as root, the resolved path is `graphify-out/graphify-out/snapshots/` — a directory that never exists. The result is that `list_snapshots()` always returns `[]`, and all four tools always short-circuit to `status: insufficient_history`, even after many graph builds.

Tests pass because they call `_run_*(..., tmp_path, ...)` where `tmp_path` is the project root, matching how `save_snapshot(G, communities)` (no `root` kwarg) writes to `./graphify-out/snapshots/`.

**Fix:**
```python
# serve.py — change _out_dir usage when passing to snapshot-chain tools:
# Option A (minimal): pass _out_dir.parent as snaps_dir
return _run_graph_summary(G, communities, _out_dir.parent, arguments)
return _run_entity_trace(G, _out_dir.parent, _alias_map, arguments)
return _run_drift_nodes(G, _out_dir.parent, arguments)
return _run_newly_formed_clusters(G, communities, _out_dir.parent, arguments)

# Or Option B: rename the parameter in _run_* helpers from snaps_dir to project_root
# and document that it is the directory CONTAINING graphify-out/, not graphify-out/ itself.
```

---

### CR-02: `_cursor_install()` called without required `project_dir` argument

**File:** `graphify/__main__.py:181`
**Issue:** `install(platform: str = "claude", ...)` at line 181 calls `_cursor_install()` with zero arguments. The function signature at line 502 is `def _cursor_install(project_dir: Path) -> None:` with no default value. Any call to `install(platform="cursor")` — via CLI `graphify install --platform cursor` or directly from Python — raises `TypeError: _cursor_install() missing 1 required positional argument: 'project_dir'`. The correct call at line 1618 (CLI direct path) already passes `_cursor_install(Path("."))`.

**Fix:**
```python
# graphify/__main__.py line 181 — add the missing argument:
if platform == "cursor":
    _cursor_install(Path("."))   # was: _cursor_install()
    return
```

---

## Warnings

### WR-01: `_run_graph_summary` — `comms_prev` from snapshot not explicitly deleted

**File:** `graphify/serve.py:1059-1068`
**Issue:** Inside `_run_graph_summary`, `load_snapshot(snaps[-1])` returns `(G_prev, comms_prev, _meta_prev)`. `del G_prev` is correctly issued after scalar extraction (line 1068). However, `comms_prev` (a `dict[int, list[str]]` retaining all prior node-ID strings) is never deleted. The per-run memory discipline requirement from the Phase 11 spec explicitly states "del G_snap after per-snapshot scalar extraction". While `comms_prev` is not a full graph, it retains all prior node IDs in memory for the function's lifetime. Consistent treatment with the other snapshot walkers (`_run_entity_trace`, `_run_drift_nodes`, `_run_newly_formed_clusters`) which do `del G_snap` on every iteration would apply the same pattern here.

**Fix:**
```python
    if len(snaps) >= 1:
        G_prev, comms_prev, _meta_prev = load_snapshot(snaps[-1])
        delta = compute_delta(G_prev, comms_prev, G, communities)
        delta_block = {
            "added_nodes": len(delta["added_nodes"]),
            "removed_nodes": len(delta["removed_nodes"]),
            "added_edges": len(delta["added_edges"]),
            "removed_edges": len(delta["removed_edges"]),
        }
        del G_prev
        del comms_prev  # add this line
```

---

### WR-02: `ghost.md` instructs parsing `meta.status` on tools that return plain text — dead guard

**File:** `graphify/commands/ghost.md:16-19`
**Issue:** `ghost.md` instructs: *"Parse `meta.status` on both responses. If either response has `status` == `no_graph`..."*. However, neither `get_annotations` nor `god_nodes` returns a Phase 9.2 hybrid envelope — both return plain text/JSON. `get_annotations` returns `json.dumps(list)` (a raw JSON array), and `god_nodes` returns a plain multi-line string. Neither emits the `---GRAPHIFY-META---` sentinel or a `meta.status` field. The `no_graph` guard will never fire from these tools. In practice, if the graph is absent, `serve()` calls `sys.exit(1)` before the MCP server starts, so the MCP client would receive a connection error rather than a `no_graph` status.

This means:
1. The `no_graph` guard in ghost.md is unreachable dead logic.
2. An agent following the instruction literally will fail to parse an empty or plain response as a status struct.

**Fix:** Replace the instruction with correct response-type descriptions:
```markdown
# In ghost.md, replace:
Parse `meta.status` on both responses.

**If either response has `status` == `no_graph`:** ...

# With:
`get_annotations` returns a JSON array (not a meta envelope).
`god_nodes` returns plain text (not a meta envelope).

**If `get_annotations` returns an empty array `[]`:** render:
> No annotations found — /ghost needs your own notes...

**If `god_nodes` returns an empty list:** render:
> No god nodes found — run `/graphify` to build the graph first.
```

---

## Info

### IN-01: `test_serve.py` has no test for entity present in snapshot history but absent from live graph

**File:** `tests/test_serve.py`
**Issue:** `_run_entity_trace` has a code path where the entity is found in at least one prior snapshot (`first_seen_ts` is set) but is absent from the live graph (`live_matches` is empty). This results in `status: ok` with `"current": {"present": False}` in the timeline. There is no test covering this "historical entity" path — only tests for `ok` (present everywhere) and `entity_not_found` (absent everywhere). A regression here could cause `entity_id` to be set incorrectly or the `first_seen` metadata to be wrong.

**Fix:** Add a test fixture where the snapshot chain contains the entity but the live `G_live` does not:
```python
def test_entity_trace_historical_entity(make_snapshot_chain, tmp_path):
    """Entity in snapshots but not in live graph: status ok, current entry has present=False."""
    snaps = make_snapshot_chain(n=2, root=tmp_path)
    G_live = nx.Graph()  # n0 is NOT in live graph
    G_live.add_node("other", label="other", source_file="other.py", community=0)
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ok"
    assert meta["first_seen"] is not None
```

---

### IN-02: `_filter_blank_stdin` uses bare `except Exception: pass` that silences relay errors

**File:** `graphify/serve.py:1011-1017`
**Issue:** The `_relay()` thread inside `_filter_blank_stdin()` catches all exceptions with `except Exception: pass`. If the relay thread encounters an unexpected error (e.g. an OS-level pipe error distinct from a normal EOF), the error is silently dropped and the stdin relay simply stops. In that scenario MCP messages would cease to flow without any diagnostic. This is a low-impact issue (the OS-level pipe is generally reliable) but any relay failure would manifest as a mysterious MCP hang.

**Fix:** At minimum, print a stderr warning on unexpected failures:
```python
def _relay() -> None:
    try:
        with open(saved_fd, "rb") as src, open(w_fd, "wb") as dst:
            for line in src:
                if line.strip():
                    dst.write(line)
                    dst.flush()
    except OSError:
        pass  # normal EOF/broken-pipe on server shutdown
    except Exception as exc:
        print(f"[graphify] warning: stdin relay failed: {exc}", file=sys.stderr)
```

---

### IN-03: `pyproject.toml` does not include `skill-copilot.md` by explicit name, but is listed

**File:** `pyproject.toml:63`
**Issue:** The `[tool.setuptools.package-data]` section for `graphify` includes `skill-copilot.md` by name. The file is present and the test `test_all_skill_files_exist_in_package` does not check for `skill-copilot.md` (it checks `skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-claw.md`, `skill-windows.md`, `skill-droid.md`, `skill-trae.md` — seven files, with `skill-copilot.md` and `skill-aider.md` omitted from the assertion). The test gap means a future removal of `skill-copilot.md` or `skill-aider.md` from the package would not fail CI.

**Fix:** Add both files to the assertion in `test_all_skill_files_exist_in_package`:
```python
# tests/test_install.py — extend the tuple:
for name in ("skill.md", "skill-codex.md", "skill-opencode.md", "skill-claw.md",
             "skill-windows.md", "skill-droid.md", "skill-trae.md",
             "skill-aider.md", "skill-copilot.md"):   # add these two
    assert (pkg / name).exists(), f"Missing: {name}"
```

---

_Reviewed: 2026-04-17T11:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
