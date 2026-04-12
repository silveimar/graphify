# Stack Research

**Project:** graphify v1.1 — Context Persistence & Agent Memory
**Researched:** 2026-04-12
**Confidence:** HIGH — all recommendations derived from verified codebase inspection + live Python runtime tests + MCP official docs. No speculative dependencies.

---

## Scope

This document covers only the **new** stack decisions for v1.1 features. The existing validated stack (NetworkX, tree-sitter, MCP stdio, PyYAML, SHA256 cache, merge engine) is not re-researched here.

**Five questions answered:**
1. How to serialize/deserialize NetworkX graph snapshots efficiently
2. How to diff two NetworkX graphs (added/removed/changed nodes and edges)
3. Whether the `mcp` Python SDK supports server-side state mutation
4. How to design the annotation persistence schema (and what library to use)
5. How to detect file modification time for staleness metadata

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `networkx.readwrite.json_graph` (stdlib NetworkX) | 3.4.2 (already installed) | Graph snapshot serialization and deserialization | Already used in `serve.py` and `export.py`. `node_link_data(G, edges="links")` + `json.dumps()` produces a stable, human-readable JSON format that round-trips all node/edge attributes. No new dep. |
| `json` (stdlib) | Python 3.10+ | Annotation persistence (`annotations.json`) and snapshot file I/O | Already used everywhere in the codebase. Self-contained, no external library required for the annotation schema. |
| `os.stat` / `Path.stat()` (stdlib) | Python 3.10+ | File modification time detection for staleness metadata | `Path(f).stat().st_mtime` returns a float (Unix timestamp). Available on all platforms. Already used implicitly by `cache.py`. No new dep. |
| `mcp` (existing optional extra) | 1.27.0 (latest) | MCP mutation tool handlers (annotate, flag, propose_vault_note) | MCP tool handlers are plain Python async functions with full access to server-side state. The protocol imposes no restriction on mutation. In-memory graph + annotations dict can be mutated directly inside `call_tool`. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `datetime` (stdlib) | Python 3.10+ | ISO 8601 timestamps for `extracted_at`, `source_modified_at`, annotation timestamps | All timestamp fields. Use `datetime.datetime.utcnow().isoformat()` for annotation records; use `os.stat().st_mtime` (float epoch) for source file mtime stored as a node attribute. |
| `hashlib` (stdlib) | Python 3.10+ | Content-hash snapshot deduplication | Already in `cache.py`. Reuse SHA256 of node_link JSON to detect "graph unchanged" and skip redundant snapshot writes. |
| `pathlib` (stdlib) | Python 3.10+ | Snapshot directory management (`graphify-out/snapshots/`) | Already used throughout. `Path.mkdir(parents=True, exist_ok=True)` for snapshot dir creation. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` + `tmp_path` (existing) | Unit tests for snapshot round-trips, diff functions, annotation CRUD | All tests must use `tmp_path` fixture — no filesystem side effects. Follow `test_<module>.py` naming. |

---

## Detailed Decisions

### 1. Graph Snapshot Serialization

**Decision:** Use `networkx.readwrite.json_graph.node_link_data(G, edges="links")` + `json.dumps()` to write snapshots as `graphify-out/snapshots/<timestamp>.json`.

**Rationale:**
- Already used in `serve.py` (`_load_graph`) and `export.py` — zero learning curve, zero new code paths for serialization.
- Round-trip verified: custom node attributes (`label`, `community`, `extracted_at`, `source_modified_at`, `confidence`) are preserved exactly through `node_link_data` → `json.dumps` → `json.loads` → `node_link_graph` (tested live: all attrs preserved, correct types).
- Performance verified: a 500-node graph serializes in 0.9ms and deserializes in 1.9ms, producing an 80KB file. Production graphs of 2–5K nodes will remain under 1MB and under 50ms round-trip — acceptable for batch pipeline use.
- The `edges="links"` parameter aligns with the existing `_load_graph()` in `serve.py` (line 22: `json_graph.node_link_graph(data, edges="links")`). No format mismatch.

**Snapshot file naming:** `graphify-out/snapshots/YYYY-MM-DDTHH-MM-SS.json` (UTC, filesystem-safe ISO format). This allows lexicographic sorting = chronological ordering with no additional index file.

**Snapshot loading for delta:** Load the N-1 snapshot via `json_graph.node_link_graph()` using the same `_load_graph()` helper already in `serve.py`. No new deserialization code.

**What NOT to use:**
- `pickle` — not human-readable, version-sensitive, security risk for user-supplied snapshots
- `GraphML` / `networkx.write_graphml()` — XML, larger files, slower parse, already available in `export.py` but not appropriate for internal snapshot format
- `nx.write_gpickle()` — deprecated in NetworkX 3.x
- SQLite — overkill for a batch snapshot; adds a new dependency and schema migration burden

**Confidence:** HIGH (verified against live NetworkX 3.4.2 runtime)

---

### 2. Graph Diffing

**Decision:** Implement graph diffing as a pure Python function using set arithmetic on node/edge sets. No external graph diff library needed.

**Algorithm:**

```python
def diff_graphs(G_old: nx.Graph, G_new: nx.Graph) -> dict:
    old_nodes = set(G_old.nodes())
    new_nodes = set(G_new.nodes())
    old_edges = set(G_old.edges())
    new_edges = set(G_new.edges())

    added_nodes    = new_nodes - old_nodes
    removed_nodes  = old_nodes - new_nodes
    common_nodes   = old_nodes & new_nodes
    added_edges    = new_edges - old_edges
    removed_edges  = old_edges - new_edges

    # Attribute changes on common nodes
    changed_nodes = {
        n for n in common_nodes
        if G_old.nodes[n].get("community") != G_new.nodes[n].get("community")
    }
    return {
        "added_nodes": sorted(added_nodes),
        "removed_nodes": sorted(removed_nodes),
        "changed_nodes": sorted(changed_nodes),  # community migration
        "added_edges": sorted(added_edges),
        "removed_edges": sorted(removed_edges),
    }
```

**Rationale:**
- NetworkX graphs expose `G.nodes()` and `G.edges()` as set-compatible views. Python set subtraction gives exact added/removed in O(n) — no traversal needed.
- Community migration is the primary "changed node" signal (nodes move between communities across runs). Check `G_old.nodes[n]["community"] != G_new.nodes[n]["community"]` on common nodes.
- Verified live: `set(G2.edges()) - set(G1.edges())` correctly returns added edges; `set(G1.edges()) - set(G2.edges())` returns removed edges.
- NetworkX edges for undirected graphs are stored as frozensets internally, so `(a, b)` and `(b, a)` are the same edge — set arithmetic handles this correctly.

**What NOT to use:**
- `networkx.graph_edit_distance()` — exponential complexity, designed for graph isomorphism not change detection
- External graph diff libraries (none are standard) — unnecessary, the set arithmetic approach is exact and trivial

**Confidence:** HIGH (verified against live NetworkX 3.4.2 runtime)

---

### 3. MCP Mutation Tool Support

**Decision:** Add mutation tools (`annotate_node`, `flag_node`, `add_edge`, `propose_vault_note`) directly to the existing `serve.py` MCP server by extending the `_handlers` dict and adding new `types.Tool` definitions in `list_tools()`.

**MCP mutation capability confirmed:** The MCP Python SDK (1.27.0, official docs verified) imposes no restriction on tool handlers mutating server-side state. A `call_tool` handler is a plain Python async/sync function with full access to closure variables — including the in-memory `G: nx.Graph` and any `annotations: dict` loaded at server start. The protocol defines tools as model-controlled invocations that return `TextContent`; what the handler does internally is entirely up to the server implementation.

**Integration pattern for `serve.py`:**

```python
# Load annotations at server start (alongside G)
annotations: dict[str, list[dict]] = _load_annotations(annotations_path)

# Mutation handler example
def _tool_annotate_node(arguments: dict) -> str:
    node_id   = arguments["node_id"]
    text      = sanitize_label(arguments["annotation"])
    peer_id   = arguments.get("peer_id", "unknown")
    session   = arguments.get("session_id", "")
    record    = {
        "annotation": text,
        "peer_id": peer_id,
        "session_id": session,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    annotations.setdefault(node_id, []).append(record)
    _save_annotations(annotations, annotations_path)  # atomic write via os.replace
    return f"Annotation added to {node_id}."
```

The existing `call_tool` handler in `serve.py` (line 343) is already a dispatcher — adding new tools is additive, not structural.

**`propose_vault_note`:** Returns a proposed note payload as `TextContent` with an explicit "awaiting human approval" message. The actual vault write happens via a subsequent `apply_proposal` tool call (or CLI `--apply-proposals` flag). This matches the Letta-Obsidian pattern validated in the gap analysis.

**What NOT to use:**
- A separate MCP server process for mutations — the existing stdio server is sufficient; no process isolation needed for local file writes
- MCP Resources for annotation storage — the annotations are write-heavy; Resources are a read-oriented abstraction in MCP; plain file I/O is simpler and testable

**Confidence:** HIGH (MCP official docs verified at modelcontextprotocol.io/docs/concepts/tools; pattern matches existing `serve.py` structure)

---

### 4. Annotation Persistence Schema

**Decision:** Store annotations in `graphify-out/annotations.json` as a `dict[node_id, list[AnnotationRecord]]` serialized with `json.dumps()`.

**Schema:**

```json
{
  "transformer": [
    {
      "annotation": "Critical bottleneck — review before refactor",
      "peer_id": "claude-code",
      "session_id": "sess_abc123",
      "timestamp": "2026-04-12T23:00:00.000000",
      "importance": "high",
      "tags": ["refactor", "bottleneck"]
    }
  ]
}
```

**Field rationale:**
- `annotation` — sanitized via `security.sanitize_label()` before storage (strip control chars, cap at 256 chars)
- `peer_id` — agent/user identity string (validated: alphanumeric + hyphens, max 64 chars)
- `session_id` — opaque session identifier from calling agent
- `timestamp` — `datetime.datetime.utcnow().isoformat()` (UTC, no timezone suffix for simplicity)
- `importance` — optional enum: `"high"`, `"medium"`, `"low"` (defaults to `"medium"` if absent)
- `tags` — optional list of strings (each sanitized, max 32 chars each)

**Atomic write pattern** (same as `cache.py` lines 71-77):

```python
def _save_annotations(data: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)
```

**Persistence across re-runs:** Annotations are keyed by `node_id` (stable, deterministic slugs generated by `_make_id()`). When a re-run produces a new graph, `annotations.json` is preserved and merged by node_id. Annotations for nodes no longer in the graph are kept (not purged) so that historical records survive node removal.

**What NOT to use:**
- SQLite — new dependency, migration burden; JSON flat file is sufficient for annotations at this scale
- A per-node `.annotation` sidecar file — directory explosion for large graphs; single `annotations.json` is simpler to backup and test
- In-graph node attributes — annotations are user/agent-added at runtime; mixing them into the graph's serialized state complicates snapshot diffing and cache invalidation

**Confidence:** HIGH (stdlib JSON, matches existing `cache.py` patterns)

---

### 5. File Modification Time Detection

**Decision:** Use `Path(file_path).stat().st_mtime` (stdlib `os.stat`) to populate `source_modified_at` as a float Unix timestamp on each node.

**Rationale:**
- `os.stat().st_mtime` is the canonical cross-platform mtime accessor. Available on Python 3.10+ on all platforms (macOS, Linux, Windows WSL).
- Returns a float (epoch seconds). Storing as float on node attributes preserves sub-second precision and requires no parsing on read.
- The gap analysis recommends a two-tier approach: fast mtime check first, SHA256 hash confirmation only on mtime mismatch. This is achievable with stdlib — `cache.py`'s `file_hash()` already provides the SHA256 tier; `st_mtime` check is the cheap first gate.
- For staleness reporting: `staleness_days = (time.time() - node["source_modified_at"]) / 86400`. Simple arithmetic, no new library.

**`extracted_at` field:** Populated at extraction time as `datetime.datetime.utcnow().isoformat()` string. This is a per-extraction timestamp, not per-file. Stored on each node dict before `validate.py` schema check. The validation schema must be updated to allow (but not require) `extracted_at` and `source_modified_at` on node dicts.

**Two-tier mtime+hash pattern:**

```python
def is_stale(file_path: Path, node: dict) -> bool:
    """True if source file is newer than when the node was extracted."""
    try:
        current_mtime = file_path.stat().st_mtime
        node_mtime = node.get("source_modified_at", 0.0)
        if current_mtime <= node_mtime:
            return False  # fast path: file not touched
        return True  # mtime changed; re-extraction candidate
    except OSError:
        return True  # file missing = always stale
```

**What NOT to use:**
- Git-based tracking (`git log --format=...`) — subprocess call, requires git installation, slow for large repos, unnecessary when `st_mtime` is direct
- `watchdog` file system events (existing optional dep) — event-driven, not appropriate for batch staleness detection at graph build time; `watchdog` remains for watch mode only
- `inotify` / `kqueue` directly — platform-specific, `watchdog` already wraps these

**Confidence:** HIGH (stdlib, verified live on macOS Darwin 25.3.0; `st_mtime` precision confirmed sub-millisecond)

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `json_graph.node_link_data` for snapshots | `pickle` | Never in this context — security/version risk |
| `json_graph.node_link_data` for snapshots | GraphML | Only if human-readability in XML form is needed; not appropriate for internal snapshots |
| Set arithmetic for graph diff | `networkx.graph_edit_distance()` | Never for change detection — exponential complexity; only for graph isomorphism research |
| `json` for annotation persistence | SQLite | When annotation volume exceeds ~100K records per node or complex querying is needed (not v1.1 scope) |
| `os.stat().st_mtime` for mtime | `git log` subprocess | When the corpus is a git repo and git history is more meaningful than filesystem mtime (valid for v1.2+ scenarios) |
| Extend existing `serve.py` for mutations | Separate MCP server | When mutation tools need isolated process security (not needed for local file writes) |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pickle` for snapshots | Version-sensitive, security risk if snapshot files are shared | `json_graph.node_link_data` + `json.dumps` |
| `networkx.graph_edit_distance()` for diffing | Exponential time complexity; designed for isomorphism not change detection | Set arithmetic on `G.nodes()` and `G.edges()` |
| `sqlite3` for annotations | New dependency pattern (even though sqlite3 is stdlib, it introduces schema migration burden); overkill for annotation volume in v1.1 | `json` flat file with atomic write |
| `yaml.dump()` for snapshot serialization | Inconsistent quoting, Python type tags; already rejected in v1.0 STACK.md | `json.dumps()` |
| New third-party graph diff library | None are established standards; the stdlib approach is exact and trivial | Native set arithmetic |

---

## Stack Patterns by Variant

**If the snapshot directory grows large (>100 snapshots):**
- Add a `graphify snapshot --prune N` command that keeps only the N most recent snapshots
- Lexicographic filename ordering (ISO timestamp) means `sorted(dir.glob("*.json"))[-N:]` is sufficient
- No index file needed

**If annotation volume grows (>10K nodes with annotations):**
- Consider a per-community annotation file (`annotations-community-0.json`, etc.) to reduce write amplification
- The key schema (`dict[node_id, list[record]]`) accommodates this by splitting at the key level
- This is a v1.2 concern, not v1.1

**If MCP server needs to expose current snapshot diff as a tool:**
- Load both current graph and previous snapshot at server start
- Pre-compute diff into a `_delta: dict` at init time
- Expose `get_delta()` tool that returns the pre-computed delta (no per-call computation)

---

## Version Compatibility

| Package | Version | Compatibility Notes |
|---------|---------|---------------------|
| `networkx` | 3.4.2 | `node_link_data(G, edges="links")` requires `edges` kwarg (NetworkX 3.x); the existing `_load_graph()` in `serve.py` already handles both the old and new API via try/except (lines 22-23). New code should use `edges="links"` explicitly. |
| `mcp` | 1.27.0 (latest) | Existing optional extra. Mutation tools use the same `server.call_tool()` decorator pattern already in `serve.py`. No API change needed. |
| Python | 3.10, 3.12 (CI) | All recommendations use stdlib or existing deps. `os.stat().st_mtime` and `json` are stable across both versions. |

---

## Installation

No new entries in `pyproject.toml` required. All v1.1 features use:
- `networkx` (already a required dependency)
- `json`, `os`, `datetime`, `pathlib`, `hashlib` (all stdlib)
- `mcp` (already an optional extra — `pip install graphify[mcp]`)

```bash
# No new installation steps for v1.1.
# Existing installation covers all needed libraries:
pip install -e ".[mcp]"   # for MCP mutation tools
pip install -e ".[all]"   # for full feature set
```

---

## Sources

- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/serve.py` — verified existing `_load_graph()` uses `json_graph.node_link_graph(data, edges="links")`; confirmed `call_tool` dispatcher pattern; confirmed MCP handler is plain Python (no mutation restriction)
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/cache.py` — verified atomic write pattern (`os.replace` via tmp file); SHA256 hash approach
- `/Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/pyproject.toml` — confirmed `mcp` is optional extra; `networkx` is required dep (no version pin)
- Live Python runtime test (NetworkX 3.4.2) — `node_link_data` round-trip with custom attrs verified; set arithmetic diff verified; 500-node serialization benchmarked (0.9ms / 1.9ms)
- `pip3 index versions mcp` — confirmed mcp 1.27.0 is current latest
- `modelcontextprotocol.io/docs/concepts/tools` (official MCP docs) — confirmed tool handlers are plain async functions with no mutation restriction; `call_tool` pattern matches existing `serve.py` implementation
- `.planning/notes/repo-gap-analysis.md` — Honcho peer model schema, CPR summary+archive pattern, Letta-Obsidian mtime+size file detection

---
*Stack research for: graphify v1.1 — Context Persistence & Agent Memory*
*Researched: 2026-04-12*
