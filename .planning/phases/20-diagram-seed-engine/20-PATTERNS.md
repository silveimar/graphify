# Phase 20: Diagram Seed Engine — Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 9 (5 modified, 1 new module, 3 test file extensions/creations)
**Analogs found:** 9 / 9 (all have strong or exact in-repo matches)

---

## File Classification

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `graphify/analyze.py` (modified) | service / analyzer | transform (graph → dicts) | self (`god_nodes`, `_cross_community_surprises`) | exact (extension in place) |
| `graphify/seed.py` (new) | service / file-I/O writer | transform + batch file output + manifest | `graphify/vault_promote.py` (atomic write + manifest pattern, `promote()` orchestrator) | exact (same lifecycle, different domain) |
| `graphify/__main__.py` (modified) | CLI entrypoint | request-response (argv → stdout/stderr) | `__main__.py::--obsidian` handler (lines 1275–1340) and `vault-promote` subcommand (lines 2111–2142) | exact |
| `graphify/serve.py` (modified) | MCP tool wiring | request-response (D-02 envelope) | `_run_get_focus_context_core` + `_tool_get_focus_context` pair (lines 2374–2500, 2948–2990) | exact |
| `graphify/mcp_tool_registry.py` (modified) | config / schema registry | declarative | `Tool(name="get_focus_context", ...)` block (lines ~320-355) | exact |
| `graphify/merge.py::compute_merge_plan` (call site) | service (not edited — consumed) | transform | existing contract (line 863) with `tags: "union"` at line 70 | N/A (reuse) |
| `tests/test_seed.py` (new) | test / unit | pure-unit | `tests/test_vault_promote.py` (atomic-write + manifest roundtrip + CLI subprocess tests) | exact |
| `tests/test_analyze.py` (extension) | test / unit | pure-unit | existing `test_god_nodes_*` tests (lines 16–36) | exact |
| `tests/test_serve.py` (extension) | test / unit | pure-unit (envelope assertion) | `test_get_focus_context_envelope_ok` et al. (lines 2315–2378) | exact |
| `tests/test_main.py` or additions to `test_vault_promote.py::test_cli_subcommand_help_works` | test / CLI | subprocess | `test_cli_subcommand_help_works` (lines 604–615) | exact |

> **Note:** Context document references `vault_adapter.py::compute_merge_plan`, but the actual module is `graphify/merge.py` (no file named `vault_adapter.py` exists in-tree). All SEED-03 / D-08 tag-writeback routing targets `graphify.merge.compute_merge_plan` with the `tags: "union"` entry in the `_DEFAULT_FIELD_POLICY` dict at **merge.py:70**. Planner: confirm this in 20-01-PLAN.md.

---

## Pattern Assignments

### 1. `graphify/analyze.py` (MODIFY — Plan 20-01)

**Analog:** self — extend `god_nodes()` (analyze.py:76–95) and `_cross_community_surprises()` (analyze.py:294–378) to emit `possible_diagram_seed: true` on the matched node. Add new `detect_user_seeds(G)`.

**Imports pattern** (analyze.py:1–3 — keep unchanged):
```python
"""Graph analysis: god nodes (most connected), surprising connections (cross-community), suggested questions."""
from __future__ import annotations
import networkx as nx
```

**god_nodes extension pattern** (analyze.py:76–95) — add node-attribute side-effect in the loop:
```python
def god_nodes(G: nx.Graph, top_n: int = 10) -> list[dict]:
    """Return the top_n most-connected real entities - the core abstractions."""
    degree = dict(G.degree())
    sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    result = []
    for node_id, deg in sorted_nodes:
        if _is_file_node(G, node_id) or _is_concept_node(G, node_id):
            continue
        # NEW (Plan 20-01): tag selected node for downstream diagram-seed detection.
        G.nodes[node_id]["possible_diagram_seed"] = True
        result.append({"id": node_id, "label": G.nodes[node_id].get("label", node_id), "edges": deg})
        if len(result) >= top_n:
            break
    return result
```

**Cross-community tagging pattern** (analyze.py:294–378): mirror the same one-line attribute assignment for each selected endpoint in the final `deduped` list before returning.

**detect_user_seeds — new function, pattern matches existing helpers** (analyze.py style):
```python
def detect_user_seeds(G: nx.Graph) -> dict[str, list[dict]]:
    """Read node `tags` attribute for gen-diagram-seed and gen-diagram-seed/<type>.

    Returns {"auto_seeds": [...], "user_seeds": [...]} where each entry is
    {"id": node_id, "label": ..., "layout_hint": "<type>" | None}.

    D-18 invariant: seed.py calls this; never reimplements tag parsing.
    """
    auto_seeds: list[dict] = []
    user_seeds: list[dict] = []
    for node_id, data in G.nodes(data=True):
        if data.get("possible_diagram_seed"):
            auto_seeds.append({"id": node_id, "label": data.get("label", node_id), "layout_hint": None})
        tags = data.get("tags") or []
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if not isinstance(tag, str):
                continue
            if tag == "gen-diagram-seed":
                user_seeds.append({"id": node_id, "label": data.get("label", node_id), "layout_hint": None})
            elif tag.startswith("gen-diagram-seed/"):
                layout_hint = tag.split("/", 1)[1] or None
                user_seeds.append({"id": node_id, "label": data.get("label", node_id), "layout_hint": layout_hint})
    return {"auto_seeds": auto_seeds, "user_seeds": user_seeds}
```

**Return shape (consistent with surrounding module):** plain `dict[str, list[dict]]` — matches the `list[dict]` return of `god_nodes`, `surprising_connections`, `knowledge_gaps`.

---

### 2. `graphify/seed.py` (NEW — Plan 20-02)

**Analog:** `graphify/vault_promote.py`. This file is the dominant architectural template. Reuse its atomic-write + manifest-last sequence, its orchestrator shape (`promote()` → `build_all_seeds()`), and the `_hash_bytes` / `_write_atomic` / `_load_manifest` / `_save_manifest` trio. Lift them verbatim (or import them; see caveat below).

**Imports pattern** (lift from vault_promote.py:1–30 style):
```python
"""Diagram seed engine: ego-graph extraction, layout heuristic, atomic seed file output."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import networkx as nx

from graphify.analyze import god_nodes, detect_user_seeds  # D-18: compose only
from graphify.security import validate_graph_path
```

**Atomic write pattern — lift verbatim from `vault_promote._write_atomic`** (vault_promote.py:627–647):
```python
def _write_atomic(target: Path, content: str) -> None:
    """Write *content* to *target* atomically via .tmp + os.replace (with fsync).

    Lifted verbatim from merge.py::_write_atomic / vault_promote.py:_write_atomic.
    """
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

**Manifest load/save pattern — lift from `vault_promote._load_manifest` / `_save_manifest`** (vault_promote.py:650–684):
```python
def _load_seeds_manifest(graphify_out: Path) -> list[dict]:
    """Load seeds-manifest.json from graphify_out/seeds/, returning [] if missing or corrupt."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        print(
            "[graphify] seeds-manifest.json corrupted or unreadable — treating all seeds as new",
            file=sys.stderr,
        )
        return []


def _save_seeds_manifest(entries: list[dict], graphify_out: Path) -> None:
    """Write seeds-manifest.json atomically with indent=2."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(entries, indent=2, ensure_ascii=False))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, manifest_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

**Orchestrator shape — mirror `vault_promote.promote()` (vault_promote.py:876–977):** Same 9-step structure, adapted:
1. Load graph (reuse `load_graph_and_communities` from vault_promote.py or `_load_graph` from serve.py:506)
2. Compute auto + user seeds via `god_nodes()` + `detect_user_seeds()` + cross-community bridges
3. D-04 overlap resolution (user wins)
4. D-05 layout-heuristic precedence
5. D-06 template recommender (hard-coded layout_type → filename map)
6. Apply >60% overlap dedup (SEED-05)
7. Apply `max_seeds=20` cap on auto seeds (SEED-06) — emit stderr warning (D-07)
8. Load prior manifest → delete orphaned `*-seed.json` files (D-02)
9. Write each `{node_id}-seed.json` atomically → **last:** write `seeds-manifest.json` atomically (D-01, MANIFEST-05 atomic pair)

**Deterministic hashing pattern** (SEED-08) — matches `cache.py`/`merge.py` idiom:
```python
def _element_id(node_id: str) -> str:
    """SEED-08: sha256(node_id)[:16]. Label-derived IDs forbidden."""
    return hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:16]


def _version_nonce(node_id: str, x: float, y: float) -> int:
    """SEED-08: int(sha256(node_id + str(x) + str(y))[:8], 16). Deterministic."""
    h = hashlib.sha256(f"{node_id}{x}{y}".encode("utf-8")).hexdigest()[:8]
    return int(h, 16)
```

**Stderr warning pattern** (D-07) — matches project convention:
```python
print(
    f"[graphify] Capped at 20 auto seeds; {dropped} dropped (see seeds-manifest.json)",
    file=sys.stderr,
)
```

**build_seed signature pattern — mirrors analyze.py dict returns:**
```python
def build_seed(
    G: nx.Graph,
    node_id: str,
    trigger: str,  # "auto" | "user"
    layout_hint: str | None = None,
) -> dict:
    """Return SeedDict: main_nodes, supporting_nodes, relations, suggested_layout_type,
    suggested_template, trigger. Ego-graph radius-1 / radius-2 via nx.ego_graph(G, node_id, radius=N).
    """
```

---

### 3. `graphify/__main__.py` (MODIFY — Plan 20-02)

**Analog:** the `--obsidian` flag handler at lines 1275–1340 (closest flag-style match; D-08 says `--diagram-seeds` is a top-level flag, not a subcommand). Also reference the `vault-promote` subcommand block (lines 2111–2142) for the `--vault` argument pairing and the `[graphify]` stdout summary line.

**Flag dispatch pattern — lift from `cmd == "--obsidian"` block:**
```python
if cmd == "--diagram-seeds":
    graph_path = "graphify-out/graph.json"
    vault_path: Path | None = None   # D-08: opt-in tag write-back
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--graph" and i + 1 < len(args):
            graph_path = args[i + 1]; i += 2
        elif args[i].startswith("--graph="):
            graph_path = args[i].split("=", 1)[1]; i += 1
        elif args[i] == "--vault" and i + 1 < len(args):
            vault_path = Path(args[i + 1]); i += 2
        elif args[i].startswith("--vault="):
            vault_path = Path(args[i].split("=", 1)[1]); i += 1
        else:
            print(f"error: unknown --diagram-seeds option: {args[i]}", file=sys.stderr)
            sys.exit(2)

    # Load graph — exact same lines as --obsidian (lines 1303–1323)
    gp = Path(graph_path).resolve()
    if not gp.exists():
        print(f"error: graph file not found: {gp}", file=sys.stderr)
        print("hint: run /graphify to produce graphify-out/graph.json first", file=sys.stderr)
        sys.exit(1)
    # ... [verbatim: load + json_graph.node_link_graph] ...

    from graphify.seed import build_all_seeds
    summary = build_all_seeds(G, graphify_out=gp.parent, vault=vault_path)
    print(f"[graphify] diagram-seeds complete: {summary}")
    sys.exit(0)
```

**Vault-mutation gating pattern** (D-08): vault_path defaults to `None`; only when passed do we import and call `graphify.merge.compute_merge_plan`. Mirrors `vault-promote --vault` contract at __main__.py:2111–2142.

---

### 4. `graphify/serve.py` (MODIFY — Plan 20-03, atomic with registry)

**Analog:** `_run_get_focus_context_core` (serve.py:2374–2495) + `_tool_get_focus_context` (serve.py:2948–2990). This is the closest in-repo template because it (a) takes plain arguments dict, (b) returns D-02 envelope string, (c) uses `_resolve_alias` closure for D-16 alias threading, (d) collapses all failure modes to a uniform status-bearing envelope, (e) never raises. Both new tools (`list_diagram_seeds`, `get_diagram_seed`) must mirror this shape.

**D-02 envelope pattern** (serve.py:903, used throughout):
```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
# ...
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**D-16 alias-threading closure — lift from `_run_query_graph` (serve.py:1526–1549) or `_run_chat_core` (serve.py:1234–1250):**
```python
_resolved_aliases: dict[str, list[str]] = {}
_effective_alias_map: dict[str, str] = alias_map or {}

def _resolve_alias(node_id: str) -> str:
    canonical = _effective_alias_map.get(node_id)
    if canonical and canonical != node_id:
        aliases = _resolved_aliases.setdefault(canonical, [])
        if node_id not in aliases:
            aliases.append(node_id)
        return canonical
    return node_id
```

**`_run_list_diagram_seeds_core` signature** (mirrors serve.py:2374):
```python
def _run_list_diagram_seeds_core(
    G: "nx.Graph",
    project_root: "Path",
    arguments: dict,
    alias_map: dict[str, str] | None = None,
) -> str:
    """Pure dispatch core for list_diagram_seeds MCP tool (SEED-09).

    Reads graphify-out/seeds/seeds-manifest.json + per-seed files.
    Returns D-02 envelope. Never raises — missing dir / corrupt manifest
    collapses to status='no_seeds' envelope (empty text_body + 4-key meta).

    Node IDs in the response are threaded through _resolve_alias per D-16.
    """
```

**`_run_get_diagram_seed_core` signature** (same template):
```python
def _run_get_diagram_seed_core(
    G: "nx.Graph",
    project_root: "Path",
    arguments: dict,
    alias_map: dict[str, str] | None = None,
) -> str:
    """Pure dispatch core for get_diagram_seed MCP tool (SEED-10).

    Reads graphify-out/seeds/{seed_id}-seed.json. Non-existent seed_id →
    status='not_found' envelope. Never crashes.
    """
```

**Failure-mode envelope pattern — lift from `_no_context` closure (serve.py:2404–2408):**
```python
def _no_seeds() -> str:
    meta_nc = {"status": "no_seeds", "seed_count": 0, "budget_used": 0}
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta_nc, ensure_ascii=False)

def _not_found(seed_id: str) -> str:
    meta_nf = {"status": "not_found", "seed_id": seed_id, "budget_used": 0}
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta_nf, ensure_ascii=False)
```

**Thin `_tool_*` wrapper pattern — lift from `_tool_get_focus_context` (serve.py:2948–2990):**
```python
def _tool_list_diagram_seeds(arguments: dict) -> str:
    _reload_if_stale()
    if not Path(graph_path).exists():
        return _no_seeds_envelope()
    return _run_list_diagram_seeds_core(G, _out_dir.parent, arguments, alias_map=_alias_map)

def _tool_get_diagram_seed(arguments: dict) -> str:
    _reload_if_stale()
    if not Path(graph_path).exists():
        return _not_found_envelope("")
    return _run_get_diagram_seed_core(G, _out_dir.parent, arguments, alias_map=_alias_map)
```

**Handler dispatch-table registration** (serve.py:3091–3110): add both entries to `_handlers` dict. The `MANIFEST-05` invariant check at serve.py:3115–3117 enforces parity with `build_mcp_tools()` — registry and serve must change in the same commit.

---

### 5. `graphify/mcp_tool_registry.py` (MODIFY — Plan 20-03, atomic with serve.py)

**Analog:** the `get_focus_context` Tool block at mcp_tool_registry.py:~316–350 (nested `focus_hint` object schema) for `get_diagram_seed`; the `newly_formed_clusters` simple block (lines ~285–295) for `list_diagram_seeds` (no-argument tool).

**Tool declaration pattern — lift from `get_focus_context` block:**
```python
types.Tool(
    name="list_diagram_seeds",
    description=(
        "List all available diagram seeds in graphify-out/seeds/. Returns per-seed: "
        "seed_id, main_node_label, suggested_layout_type, trigger (auto|user), node_count. "
        "D-02 envelope. Alias-resolved per D-16. Returns no_seeds envelope when directory empty."
    ),
    inputSchema={"type": "object", "properties": {
        "budget": {"type": "integer", "default": 500},
    }},
),
types.Tool(
    name="get_diagram_seed",
    description=(
        "Return the full SeedDict for a specific seed by seed_id. Non-existent seed_id "
        "returns a not_found envelope; never crashes. D-02 envelope. Alias-resolved per D-16."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "seed_id": {"type": "string", "description": "Seed identifier from list_diagram_seeds"},
            "budget": {"type": "integer", "default": 2000},
        },
        "required": ["seed_id"],
    },
),
```

**MANIFEST-05 atomic invariant** (mcp_tool_registry.py consumed by serve.py:3115): `{t.name for t in build_mcp_tools()} == set(_handlers.keys())` is asserted at server start. Registry + handler additions must land in the same plan (and commit) per D-02 atomic-pair.

---

### 6. `tests/test_seed.py` (NEW — Plan 20-02)

**Analog:** `tests/test_vault_promote.py`. Lift four test shapes:

**Atomic write + manifest roundtrip** (test_vault_promote.py:411–430):
```python
def test_seeds_manifest_roundtrip(tmp_path):
    from graphify.seed import _save_seeds_manifest, _load_seeds_manifest
    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()
    entries = [{"node_id": "n1", "seed_file": "n1-seed.json", "trigger": "auto"}]
    _save_seeds_manifest(entries, graphify_out)
    loaded = _load_seeds_manifest(graphify_out)
    assert loaded == entries
```

**Decision-table pattern** for D-02 cleanup (mirror test_vault_promote.py:316–355): prior manifest → new run → orphaned `*-seed.json` must be deleted.

**End-to-end `build_all_seeds` smoke test** — lift shape from `test_promote_smoke` (test_vault_promote.py:472–498): synthetic graph fixture → call orchestrator → assert `seeds/` dir populated + manifest present.

**CLI subcommand help-text test** — lift from `test_cli_subcommand_help_works` (test_vault_promote.py:604–615):
```python
def test_cli_diagram_seeds_help():
    import subprocess
    result = subprocess.run(
        ["python", "-m", "graphify", "--diagram-seeds", "--help"],
        capture_output=True, text=True,
    )
    # adapt assertion: `--diagram-seeds` is a flag not a subcommand — may have no --help;
    # substitute with a "unknown option" error check or a dry-run of the flag itself.
```

**Fixture-graph builder pattern** — lift `_make_graph_with_nodes` from test_analyze.py has no equivalent; use test_vault_promote.py's `_make_minimal_graph_json` (lines ~438–470) directly.

**Pure-unit invariants (TESTING.md):** all tests use `tmp_path`, no network, no filesystem writes outside `tmp_path`.

---

### 7. `tests/test_analyze.py` extension (Plan 20-01)

**Analog:** existing `test_god_nodes_*` tests (test_analyze.py:16–36).

**Attribute-tagging test pattern:**
```python
def test_god_nodes_tags_possible_diagram_seed():
    G = make_graph()
    result = god_nodes(G, top_n=3)
    for entry in result:
        assert G.nodes[entry["id"]].get("possible_diagram_seed") is True
```

**detect_user_seeds test pattern** (lift `_make_graph_with_nodes` helper style from test_vault_promote.py:13–22):
```python
def test_detect_user_seeds_reads_tags():
    import networkx as nx
    from graphify.analyze import detect_user_seeds
    G = nx.Graph()
    G.add_node("a", label="A", tags=["gen-diagram-seed"])
    G.add_node("b", label="B", tags=["gen-diagram-seed/workflow"])
    G.add_node("c", label="C", tags=["unrelated"])
    result = detect_user_seeds(G)
    assert {e["id"] for e in result["user_seeds"]} == {"a", "b"}
    b_entry = next(e for e in result["user_seeds"] if e["id"] == "b")
    assert b_entry["layout_hint"] == "workflow"
```

---

### 8. `tests/test_serve.py` extension (Plan 20-03)

**Analog:** `test_get_focus_context_*` (test_serve.py:2315–2376). Lift all five shapes:

**Tool-registered test** (test_serve.py:2315–2320):
```python
def test_list_diagram_seeds_registered():
    from graphify.mcp_tool_registry import build_mcp_tools
    names = {t.name for t in build_mcp_tools()}
    assert "list_diagram_seeds" in names
    assert "get_diagram_seed" in names
```

**Envelope-ok test** (lift from test_serve.py:2322–2337):
```python
def test_list_diagram_seeds_envelope_ok(tmp_path):
    from graphify.serve import _run_list_diagram_seeds_core, QUERY_GRAPH_META_SENTINEL
    # Setup: create tmp_path/graphify-out/seeds/ with one seed file + manifest
    # ... build G, call core, split on sentinel, assert meta["status"] == "ok"
```

**No-seeds envelope** (lift from test_serve.py:2351–2361):
```python
def test_list_diagram_seeds_empty_directory(tmp_path):
    # No seeds/ dir → envelope has status="no_seeds", empty text_body
```

**Not-found envelope** for `get_diagram_seed`:
```python
def test_get_diagram_seed_not_found(tmp_path):
    # seed_id="nonexistent" → status="not_found" envelope, no crash
```

**D-16 alias-threading test** (lift pattern from existing alias tests — search test_serve.py for `alias_map=` usage):
```python
def test_get_diagram_seed_resolves_alias(tmp_path):
    # seed_id passed as alias → response contains canonical node_id,
    # meta["resolved_from_alias"] maps canonical → [alias, ...]
```

**D-02 envelope shape invariant** (lift from test_serve.py:1160):
```python
text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
meta = json.loads(meta_json)
```

Target: 8+ test cases per SEED-11 plan.

---

### 9. `tests/test_main.py` (or extension to test_vault_promote.py::test_cli_subcommand_help_works)

**Analog:** `test_cli_subcommand_help_works` (test_vault_promote.py:604–615):
```python
def test_cli_diagram_seeds_flag_accepted():
    import subprocess
    # Use a minimal tmp graph.json; assert returncode 0 and stdout contains "[graphify] diagram-seeds complete:"
```

Subprocess pattern: `["python", "-m", "graphify", "--diagram-seeds", "--graph", str(tmp_graph)]`.

---

## Shared Patterns

### SP-1. Atomic Write + Manifest-Last Sequence
**Source:** `graphify/vault_promote.py:627–684` (`_write_atomic`, `_load_manifest`, `_save_manifest`).
**Apply to:** `graphify/seed.py` (SEED-01, D-01, D-02, MANIFEST-05).
**Rule:** tempfile (`target.with_suffix(target.suffix + ".tmp")`) → write → flush → fsync → `os.replace` → best-effort unlink `.tmp` on error. Manifest ALWAYS the final atomic step; no partial visible state ever leaks.

### SP-2. `[graphify]`-Prefixed Stderr Warnings
**Source:** `graphify/vault_promote.py:660` (manifest-corrupt warning) and throughout.
**Apply to:** `seed.py` D-07 cap warning; all operational warnings in the new module.
**Format:** `print(f"[graphify] <message>", file=sys.stderr)`. No logging module.

### SP-3. D-02 Envelope
**Source:** `graphify/serve.py:903` (`QUERY_GRAPH_META_SENTINEL`), `serve.py:2495` (emission).
**Apply to:** `_run_list_diagram_seeds_core`, `_run_get_diagram_seed_core` (SEED-09, SEED-10).
**Shape:** `text_body + "\n---GRAPHIFY-META---\n" + json.dumps(meta, ensure_ascii=False)`.
**Binary-status invariant (from FOCUS-01 / D-11):** every non-ok path emits a uniform 4-or-fewer-key meta with empty `text_body`. No argument echoing.

### SP-4. D-16 Alias Threading
**Source:** `graphify/serve.py:1234–1250` (`_run_chat_core` closure) and `serve.py:1526–1549` (`_run_query_graph`).
**Apply to:** Both new MCP tool cores.
**Rule:** build `_resolve_alias(node_id)` closure that consults `alias_map`, records redirects into `_resolved_aliases: dict[str, list[str]]`, returns canonical. Shallow-copy `arguments` before rewriting. Include `meta["resolved_from_alias"]` when any redirect fired.

### SP-5. Deterministic Hashing for Stable IDs
**Source:** `graphify/merge.py` (sha256 idiom), `graphify/cache.py` (per-file hash), `graphify/vault_promote.py:622` (`_hash_bytes`).
**Apply to:** `seed.py` `_element_id` (SEED-08: `sha256(node_id)[:16]`) and `_version_nonce` (SEED-08: `int(sha256(node_id + str(x) + str(y))[:8], 16)`).
**Rule:** always `encode("utf-8")` → `hashlib.sha256(...).hexdigest()` → slice. No label-derived IDs.

### SP-6. `[graphify]` Stdout Summary Line on CLI Completion
**Source:** `__main__.py:2142` (`[graphify] vault-promote complete: promoted=..., skipped=...`).
**Apply to:** `--diagram-seeds` handler: emit `[graphify] diagram-seeds complete: ...` before `sys.exit(0)`.

### SP-7. MANIFEST-05 Atomic Pair (Registry + Serve)
**Source:** `serve.py:3115–3117` invariant check.
**Apply to:** Plan 20-03 — `mcp_tool_registry.py::build_mcp_tools` additions MUST land in the same commit as `serve.py::_handlers` additions. Running tests catches drift via the `RuntimeError("MCP tool registry and _handlers keys must match (MANIFEST-05)")` assertion.

### SP-8. Never-Raise-in-Tool-Core Contract
**Source:** `_run_get_focus_context_core` (serve.py:2381 docstring, 2404 `_no_context`, 2424 `except (ValueError, FileNotFoundError)`).
**Apply to:** `_run_list_diagram_seeds_core` and `_run_get_diagram_seed_core`. All failure paths must collapse to a status-bearing D-02 envelope — missing dir, corrupt manifest, unknown seed_id, IOError.

### SP-9. `tags: "union"` Write-Back Policy (D-08 opt-in)
**Source:** `graphify/merge.py:70` (`_DEFAULT_FIELD_POLICY["tags"] = "union"`) and `compute_merge_plan` signature at `merge.py:863`.
**Apply to:** `seed.py` when invoked with `--vault` (D-08). Construct `rendered_notes` dict keyed by node_id with `tags=["gen-diagram-seed"]`; pass through `compute_merge_plan(vault_dir, rendered_notes, profile)`. **Never** write frontmatter directly; SEED-03 forbids it.

### SP-10. `from __future__ import annotations` + `str | None` Style
**Source:** every module (e.g. analyze.py:2, merge.py top, serve.py top).
**Apply to:** new `seed.py` first import line must be `from __future__ import annotations`. Type hints use `str | None`, `list[dict]`, `dict[str, int]` — not `Optional`/`List`/`Dict`.

---

## No Analog Found

| File/Concern | Reason | Planner Action |
|---|---|---|
| Excalidraw scene JSON / `.excalidraw.md` structure | Phase 22 concern; no in-repo analog yet. Seeds contain scene-buildable data but do NOT themselves produce `.excalidraw.md` in Phase 20. | Use SEED-08 hashing rules as the only commitment; defer scene-shape patterns to Phase 22. |
| Overlap-dedup (>60% node overlap, degree-sorted single-pass) | Novel algorithm in this codebase. | Planner: specify the single-pass algorithm directly in 20-02-PLAN.md; no analog to copy. Mirror style of `_cross_community_surprises` dedup loop (analyze.py:375–386) for shape. |
| Layout heuristic (6 NetworkX predicates with precedence) | Novel in this codebase. | Planner: reference `nx.is_tree`, `nx.is_directed_acyclic_graph`, `nx.topological_generations` directly in 20-02-PLAN.md. |

---

## Metadata

**Analog search scope:**
- `graphify/` (all `.py` modules) — primary source of patterns.
- `tests/` (test_analyze, test_serve, test_vault_promote) — test-shape analogs.
- `.planning/phases/19-*/` — referenced via CONTEXT.md for atomic-write + manifest pedigree.

**Files scanned (via grep outline):** 7 modules + 4 test files.

**Pattern extraction date:** 2026-04-23.

**Critical caveat for planner:** The CONTEXT.md refers to `vault_adapter.py::compute_merge_plan`, but the repository has no `vault_adapter.py`. The compute_merge_plan function lives in `graphify/merge.py` (line 863), and the `tags: "union"` policy is set in `_DEFAULT_FIELD_POLICY` at `merge.py:70`. All Plan 20-01 and 20-02 references to vault_adapter must be rewritten to target `graphify.merge.compute_merge_plan`.
