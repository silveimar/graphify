# Phase 7: MCP Write-Back with Peer Modeling - Research

**Researched:** 2026-04-12
**Domain:** Python MCP server extension — JSONL persistence, sidecar state, peer identity, proposal staging
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Annotations persist forever across pipeline re-runs. If a referenced node ID disappears from the graph, the annotation becomes orphaned but is never automatically deleted. Agents/users clean up manually.
- **D-02:** Two separate sidecar files: `annotations.jsonl` for node annotations and flags (JSONL append-only), `agent-edges.json` for agent-discovered edges. Different data shapes justify separate files.
- **D-03:** JSONL compaction (dedup/pruning) runs once at MCP server startup only. Append-only during operation for crash safety. No compaction during writes.
- **D-04:** `peer_id` is an explicit optional string parameter on every mutation tool. Defaults to `"anonymous"` if omitted. Never auto-detected from environment variables or machine identity.
- **D-05:** `session_id` is a server-generated UUID4 created when the MCP server starts. All mutations during that server lifetime share the same session_id. No caller coordination needed.
- **D-06:** Session-scoped views via filter parameters on `get_annotations` tool: optional `peer_id`, `session_id`, and `time_range` filters. Returns all annotations by default, filtered subset when params provided.
- **D-07:** `graphify approve` is a non-interactive CLI. Lists all pending proposals with summary. `graphify approve <id>` to accept, `graphify approve --reject <id>` to reject, `graphify approve --all` for batch accept. Composable, scriptable.
- **D-08:** Proposals carry full note spec: suggested filename, target folder, full markdown content, frontmatter dict, note_type, peer_id, session_id, timestamp, and a rationale field explaining why the agent proposed it.
- **D-09:** Proposals persist in `graphify-out/proposals/` until explicitly approved or rejected. No automatic expiry. User can clean up with `graphify approve --reject-all` or manually.
- **D-10:** Approved proposals go through the existing merge engine (`compute_merge_plan` + `apply_merge_plan`). The proposal's note_type and target folder are suggestions — the merge engine applies the vault profile, handles conflicts, and respects `preserve_fields`. Full v1.0 pipeline guarantees.
- **D-11:** `graphify approve` requires an explicit `--vault` flag for the target vault path. No implicit state discovery. Matches D-73 pattern of explicit CLI utilities.
- **D-12:** Three separate mutation tools: `annotate_node` (free-text annotation), `flag_node` (importance: high/medium/low), `add_edge` (agent-inferred relationship). Clear intent per tool, matches MCP best practice.
- **D-13:** MCP server auto-reloads `graph.json` via mtime check before every read tool call. If mtime changed since last load, reload graph. Ensures agents always see fresh pipeline output. Negligible overhead (one `stat()` call).
- **D-14:** `propose_vault_note` accepts structured fields: `title`, `note_type`, `body_markdown`, `suggested_folder`, `tags[]`, `rationale`. The approval flow + merge engine assembles the final note with proper frontmatter from the vault profile. Agent doesn't need to know frontmatter format.
- **D-15:** Mutation tools return the full record written, including generated UUID `record_id`, `timestamp`, and `session_id`. Agent can reference records later for linking or context.
- **D-16:** Single-server assumption: only one MCP server instance runs at a time. Annotations loaded at startup + appended in-memory during the session. No multi-writer coordination needed.

### Claude's Discretion

- Internal JSONL record schema (exact field names beyond the required peer_id/session_id/timestamp)
- Compaction algorithm details (dedup strategy, handling of superseded annotations)
- `agent-edges.json` internal format (array vs object, indexing)
- Error messages for invalid node IDs, malformed inputs
- `_reload_if_stale()` implementation details (mtime caching, thread safety)
- Proposal JSON schema in `graphify-out/proposals/` (file naming, UUID format)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-01 | MCP server exposes `annotate_node` tool that adds a text annotation to any node by ID, persisted across server restarts | JSONL append pattern from cache.py; handler dispatch in serve.py |
| MCP-02 | MCP server exposes `flag_node` tool that marks a node's importance (high/medium/low), persisted across server restarts | Same JSONL append sidecar; single `annotations.jsonl` file per D-02 |
| MCP-03 | MCP server exposes `add_edge` tool for agent-discovered relationships, stored in `agent-edges.json` sidecar (never in pipeline `graph.json`) | Separate JSON file; atomic write via os.replace from cache.py pattern |
| MCP-04 | All annotations persist in `graphify-out/annotations.jsonl` using JSONL append (crash-safe, no read-modify-write race) | Filesystem append atomicity for small writes; no locking required |
| MCP-05 | Every annotation record includes `peer_id`, `session_id`, and `timestamp`; `peer_id` defaults to `"anonymous"` (never derived from environment) | uuid.uuid4() for session_id; datetime.now(timezone.utc).isoformat() for timestamp |
| MCP-06 | MCP server exposes `propose_vault_note` tool that stages a proposed note to `graphify-out/proposals/` with human approval required before vault write | Staging-only write; sanitize_label() on content; validate_vault_path() deferred to approval time |
| MCP-07 | `graphify approve` CLI command lists pending proposals and allows user to approve/reject/edit before writing to vault | `snapshot` subcommand pattern in __main__.py; merge engine for approved proposals |
| MCP-08 | Annotations and agent-edges are queryable via MCP: filter by peer, session, or time range | `get_annotations` tool with optional filter params per D-06 |
| MCP-09 | Session-scoped graph views: MCP tool to retrieve annotations relevant to a specific session context | Filter by session_id on get_annotations; or separate `get_session_annotations` tool |
| MCP-10 | `graph.json` is never mutated by MCP tools — pipeline output is read-only ground truth; all agent state lives in sidecars | Architectural invariant; `_reload_if_stale()` for freshness without mutation |

</phase_requirements>

## Summary

Phase 7 extends `serve.py` with four mutation tools and a query tool, all backed by two sidecar files in `graphify-out/`. The core architectural invariant is that `graph.json` is never touched by MCP tools — it remains the pipeline's read-only ground truth. All agent state lives in `annotations.jsonl` (JSONL, append-only for crash safety) and `agent-edges.json` (JSON, atomic write via `os.replace` from `cache.py` pattern). A fifth tool (`propose_vault_note`) stages proposed vault notes to `graphify-out/proposals/` as individual JSON files, requiring explicit human approval via the new `graphify approve` CLI subcommand before any vault is written.

The MCP handler pattern is already established in `serve.py`: a `_handlers` dict maps tool names to sync functions, wrapped by a single `async def call_tool()`. New tools slot directly into this pattern. Peer identity (`peer_id` = explicit param defaulting to `"anonymous"`) and session identity (`session_id` = UUID4 generated at server startup) follow Honcho's peer model validated in research. The `_reload_if_stale()` mtime check ensures read tools always reflect the latest pipeline output without polling.

The `graphify approve` CLI follows the `snapshot` subcommand template exactly: manual `sys.argv` parsing, `--vault` flag required (D-11), `--reject` and `--all` variants, proposals fed through the existing `compute_merge_plan` + `apply_merge_plan` pipeline (D-10). No new dependencies — this phase is entirely stdlib + the already-optional `mcp` extra.

**Primary recommendation:** Implement new tools by extending `serve.py`'s `_handlers` dict, write `annotations.jsonl` with stdlib `open(path, "a")` append, write `agent-edges.json` with `os.replace()` atomic swap, and keep all vault writes deferred to `graphify approve` CLI.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.27.0 [VERIFIED: pip show mcp] | MCP server + tool registration | Already the serve.py transport; all new tools use the same `@server.call_tool()` async wrapper |
| `json` | stdlib | JSONL serialization, proposal file writes | Already used throughout; `json.dumps()` per line for JSONL |
| `os` | stdlib | `os.replace()` atomic writes, `os.stat()` mtime check | Already the atomic write pattern in `cache.py` |
| `uuid` | stdlib | `uuid.uuid4()` for session_id and record_id | UUID4 never embeds machine identity (unlike UUID1 which encodes MAC address) |
| `datetime` | stdlib | ISO-8601 UTC timestamps on every record | `datetime.now(timezone.utc).isoformat()` matches snapshot.py pattern |
| `pathlib` | stdlib | File path handling, proposals directory | Already pervasive in codebase |
| `networkx` | 3.4.2 [VERIFIED: pip show networkx] | Graph read for `_reload_if_stale()` | Already the graph abstraction |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `graphify.security.sanitize_label` | local | Strip control chars from agent-supplied strings | Apply to all mutation tool string inputs before persistence |
| `graphify.profile.validate_vault_path` | local | Confine vault writes to vault directory | Apply at `graphify approve` time, not at proposal time |
| `graphify.merge.compute_merge_plan` + `apply_merge_plan` | local | Produce vault notes from approved proposals | Called in `graphify approve <id> --vault <path>` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONL append-only | Read-modify-write JSON | JSONL append is atomic for single-line writes; read-modify-write requires locking and risks corruption on crash — do not use |
| UUID4 for session/record IDs | UUID1 or timestamp-based | UUID1 embeds MAC address (privacy leak per pitfall #6); timestamp collisions possible under fast tests |
| `os.replace()` for agent-edges.json | Direct `open(path, "w")` | `os.replace()` is atomic — if the process dies mid-write, the old file is intact; direct write corrupts the file |

**Installation:**

No new dependencies. `mcp` is already in the optional `[mcp]` extra.

## Architecture Patterns

### Recommended File Layout

```
graphify/
├── serve.py                  # Extended: mutation tools + _reload_if_stale
graphify-out/
├── graph.json                # READ-ONLY from MCP tools (pipeline ground truth)
├── annotations.jsonl         # NEW: append-only annotation + flag records
├── agent-edges.json          # NEW: agent-inferred edges (atomic write)
└── proposals/
    ├── {uuid4}.json          # NEW: one file per staged proposal
    └── ...
```

### Pattern 1: MCP Tool Registration (Handler Dict)

**What:** All tools registered via `_handlers` dict + single `@server.call_tool()` async dispatch.
**When to use:** Every new tool in serve.py — never register a separate `@server.call_tool()` per tool.
**Example:**
```python
# Source: graphify/serve.py (existing pattern)
_handlers = {
    "query_graph": _tool_query_graph,
    # ... existing tools ...
    "annotate_node": _tool_annotate_node,   # NEW
    "flag_node": _tool_flag_node,           # NEW
    "add_edge": _tool_add_edge,             # NEW
    "propose_vault_note": _tool_propose_vault_note,  # NEW
    "get_annotations": _tool_get_annotations,        # NEW
}

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = _handlers.get(name)
    if not handler:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    try:
        return [types.TextContent(type="text", text=handler(arguments))]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Error executing {name}: {exc}")]
```

### Pattern 2: JSONL Append-Only Annotation Persistence

**What:** Each annotation/flag record is one JSON line appended to `annotations.jsonl`. No locking needed — filesystem append is atomic for small writes. At-startup compaction deduplicates.
**When to use:** `annotate_node`, `flag_node` handlers.
**Example:**
```python
# Source: cache.py os.replace pattern + stdlib append
import json
from datetime import datetime, timezone
from pathlib import Path

def _append_annotation(out_dir: Path, record: dict) -> None:
    """Append one record to annotations.jsonl (crash-safe, no locking)."""
    path = out_dir / "annotations.jsonl"
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
```

### Pattern 3: Atomic JSON Write for agent-edges.json

**What:** `agent-edges.json` is read fully at startup, modified in-memory, then written atomically via `os.replace()` on every `add_edge` call.
**When to use:** `add_edge` handler. D-16 single-server assumption means no concurrent writer coordination needed.
**Example:**
```python
# Source: cache.py save_cached() pattern (verified)
import json, os
from pathlib import Path

def _save_agent_edges(out_dir: Path, edges: list[dict]) -> None:
    target = out_dir / "agent-edges.json"
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(edges, indent=2), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```

### Pattern 4: Mtime-Based Graph Reload

**What:** `_reload_if_stale()` checks `os.stat().st_mtime` of `graph.json` before every read tool call. If mtime changed since last load, reload the graph in-place.
**When to use:** Called at the top of every read tool handler (query_graph, get_node, get_neighbors, etc.) — not mutation handlers (those don't read G).
**Example:**
```python
# Source: CONTEXT.md D-13
import os

_graph_mtime: float = 0.0

def _reload_if_stale(graph_path: str) -> None:
    """Reload G and communities in-place if graph.json has changed."""
    nonlocal G, communities, _graph_mtime
    try:
        mtime = os.stat(graph_path).st_mtime
    except OSError:
        return
    if mtime != _graph_mtime:
        G = _load_graph(graph_path)
        communities = _communities_from_graph(G)
        _graph_mtime = mtime
```

### Pattern 5: Proposal Staging (propose_vault_note)

**What:** Tool writes a single JSON file to `graphify-out/proposals/{uuid4}.json`. Never writes to vault. Content sanitized with `sanitize_label()`. `validate_vault_path()` is NOT called here — deferred to approval time.
**When to use:** `propose_vault_note` handler.
**Example:**
```python
# Source: CONTEXT.md D-14, security.py sanitize_label
import uuid, json
from datetime import datetime, timezone
from graphify.security import sanitize_label

def _tool_propose_vault_note(arguments: dict) -> str:
    record_id = str(uuid.uuid4())
    record = {
        "record_id": record_id,
        "title": sanitize_label(arguments.get("title", "")),
        "note_type": sanitize_label(arguments.get("note_type", "note")),
        "body_markdown": sanitize_label(arguments.get("body_markdown", "")),
        "suggested_folder": sanitize_label(arguments.get("suggested_folder", "")),
        "tags": [sanitize_label(t) for t in arguments.get("tags", [])],
        "rationale": sanitize_label(arguments.get("rationale", "")),
        "peer_id": sanitize_label(arguments.get("peer_id", "anonymous")),
        "session_id": _session_id,  # module-level UUID4 set at server start
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    proposals_dir = _out_dir / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    (proposals_dir / f"{record_id}.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return json.dumps({"record_id": record_id, "status": "pending"})
```

### Pattern 6: graphify approve CLI Subcommand

**What:** New `approve` subcommand in `__main__.py::main()` following the `snapshot` command pattern — manual `sys.argv` parsing, no argparse.
**When to use:** `graphify approve`, `graphify approve <id> --vault <path>`, `graphify approve --reject <id>`, `graphify approve --all --vault <path>`, `graphify approve --reject-all`.
**Example:**
```python
# Source: __main__.py snapshot subcommand (existing pattern, lines 907–1016)
if cmd == "approve":
    args = sys.argv[2:]
    vault_path = None
    reject = False
    reject_all = False
    approve_all = False
    target_id = None
    i = 0
    while i < len(args):
        if args[i] == "--vault" and i + 1 < len(args):
            vault_path = args[i + 1]; i += 2
        elif args[i] == "--reject":
            reject = True; i += 1
        elif args[i] == "--reject-all":
            reject_all = True; i += 1
        elif args[i] == "--all":
            approve_all = True; i += 1
        else:
            target_id = args[i]; i += 1
    # ... dispatch to approve helpers ...
```

### Pattern 7: JSONL Startup Compaction

**What:** At server startup, read all lines from `annotations.jsonl`, deduplicate (keep last record per node+type key), rewrite compacted file. Append-only during operation.
**When to use:** Once, in `serve()` before server starts. Never during a running session.
**Example:**
```python
# Compaction strategy (Claude's discretion — D-03 pattern)
def _compact_annotations(path: Path) -> list[dict]:
    """Load annotations.jsonl, deduplicate by (node_id, annotation_type, peer_id),
    keeping the last record per key. Returns deduplicated list."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip corrupt lines
    # Deduplicate: keep last record per (node_id, annotation_type, peer_id)
    seen: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("node_id"), r.get("annotation_type"), r.get("peer_id"))
        seen[key] = r
    compacted = list(seen.values())
    # Rewrite compacted file
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for r in compacted:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
    return compacted
```

### Anti-Patterns to Avoid

- **Mutating G from a handler:** Never call `G.add_node()`, `G.add_edge()`, or any `G` mutator inside a tool handler. `G` is the read-only pipeline view. Violating this corrupts `graph.json` indirectly and causes data loss on re-run.
- **`os.environ["USER"]` as peer_id default:** Always default to `"anonymous"`. Environment variables leak machine identity into files that may be committed.
- **`uuid.uuid1()` for session or record IDs:** UUID1 encodes MAC address. Use `uuid.uuid4()` exclusively.
- **Writing directly to vault from `propose_vault_note`:** The tool writes only to `graphify-out/proposals/`. Vault path is not even validated until `graphify approve --vault <path>`.
- **read-modify-write on `annotations.jsonl`:** Open with mode `"a"`, never `"r"` then `"w"`. Concurrent appends are safe; concurrent rewrite racing is not.
- **argparse in `__main__.py`:** The CLI uses manual `sys.argv` parsing exclusively. Do not introduce argparse — it breaks the existing pattern and adds an import that was deliberately avoided.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom locking mechanism | `os.replace(tmp, target)` from `cache.py` | Cross-platform atomic swap already tested and battle-hardened in project |
| Path confinement for vault writes | Custom path traversal checks | `validate_vault_path()` from `profile.py` | Handles `..` traversal, symlinks, and relative path edge cases |
| String sanitization for agent input | Custom regex | `sanitize_label()` from `security.py` | Strips control chars, caps length — already covers HTML-injection and terminal-escape attacks |
| UUID generation | Timestamp + random | `uuid.uuid4()` from stdlib | Privacy-safe, collision-free, no MAC address leak |
| Graph serialization for reload | Custom JSON schema | `json_graph.node_link_graph()` from networkx | Round-trip verified (all node/edge attributes survive); same format as existing `_load_graph()` |
| Proposal → vault note rendering | Custom template engine | `compute_merge_plan()` + `apply_merge_plan()` in `merge.py` | All v1.0 merge guarantees (preserve_fields, conflict detection, frontmatter policy) apply automatically |

**Key insight:** Every custom persistence or path-validation solution adds a test surface that is already covered by existing modules. Phase 7 adds behavior, not infrastructure.

## Common Pitfalls

### Pitfall 1: MCP Tools Mutating graph.json (Highest Priority)
**What goes wrong:** A handler modifies the in-memory `G` object (e.g., `G.add_edge()` for `add_edge` tool). When `_reload_if_stale()` runs and mtime hasn't changed, the mutated graph is used. When the pipeline re-runs, `graph.json` is overwritten and the agent-added edges vanish silently.
**Why it happens:** `G` is accessible in all handler closures; the temptation is to mutate it directly for `add_edge`.
**How to avoid:** `add_edge` writes ONLY to `agent-edges.json`. `G` is never mutated by any handler. Add a comment block above `_handlers` in serve.py: "Handlers must never mutate G — write to sidecar files only."
**Warning signs:** `agent-edges.json` doesn't exist but `G.edges()` shows new edges; edges disappear after pipeline re-run.

### Pitfall 2: annotations.jsonl Concurrent Write Corruption
**What goes wrong:** Two handlers (or two server instances violating D-16) both do `read → modify → rewrite` on `annotations.jsonl`. The second write overwrites the first.
**Why it happens:** Developer treats `annotations.jsonl` as a JSON array and does a full rewrite on every append.
**How to avoid:** Always open with `open(path, "a")` (append mode). One JSON object per line. Compact only at startup.
**Warning signs:** Annotation count drops unexpectedly; records from earlier in a session disappear.

### Pitfall 3: peer_id Derived from Environment
**What goes wrong:** `peer_id` defaults to `os.environ.get("USER", "anonymous")` or `socket.gethostname()`. If `graphify-out/` is committed to a shared repo, machine identity leaks.
**Why it happens:** Convenience — machine identity is available and looks useful.
**How to avoid:** Default is always the string literal `"anonymous"`. The `peer_id` parameter is caller-supplied only. Never read environment variables for identity.
**Warning signs:** `peer_id` values in `annotations.jsonl` contain hostnames or OS usernames.

### Pitfall 4: propose_vault_note Writing to Vault Directly
**What goes wrong:** The tool resolves the vault path at call time (e.g., from an env var or a graph attribute) and writes a note directly without human approval.
**Why it happens:** Impatience — it feels more responsive to write directly.
**How to avoid:** The tool writes ONLY to `graphify-out/proposals/{uuid4}.json`. No vault path is accepted as a tool argument. `validate_vault_path()` is called only inside `graphify approve`.
**Warning signs:** `graphify-out/proposals/` contains `.md` files; vault notes appear without running `graphify approve`.

### Pitfall 5: _reload_if_stale() Using mtime Alone on FAT32 / Networked FS
**What goes wrong:** FAT32 filesystems have 2-second mtime resolution. On networked filesystems, clock skew means mtime may not reflect actual changes.
**Why it happens:** `os.stat().st_mtime` returns float on POSIX but integer-second precision on some systems.
**How to avoid:** mtime check is a fast gate only (D-13). The graph is always reloaded when mtime differs from last-seen value. No hash check needed on read — the overhead is one `stat()` call. Accept that very fast sequential pipeline re-runs (sub-2s) may not trigger reload on FAT32; document as known limitation.
**Warning signs:** Agent sees stale graph data after a re-run; graph stats don't update.

### Pitfall 6: Proposal File Naming with User-Supplied Title
**What goes wrong:** Proposal file is named `{sanitized_title}.json` using the agent-supplied title. Agent sends `title="../../../etc/cron.d/backdoor"` or an extremely long title.
**Why it happens:** Human-readable filenames seem friendly.
**How to avoid:** Proposal filenames are always `{uuid4}.json` — server-generated, never based on agent input. Title is stored inside the JSON payload, sanitized with `sanitize_label()`.
**Warning signs:** Proposal files in unexpected directories; filenames with path separators.

### Pitfall 7: graphify approve Without --vault Silently Writes to CWD
**What goes wrong:** `graphify approve <id>` without `--vault` falls back to `"."` or `"graphify-out/obsidian"` as the vault path. Merge engine writes notes to an unintended location.
**Why it happens:** Developer adds a fallback to avoid a required-flag error.
**How to avoid:** Per D-11, `--vault` is required for any operation that touches a vault. If `--vault` is absent, print an error and exit 2. No fallback.
**Warning signs:** Notes appear in `graphify-out/` or CWD instead of the intended vault.

## Code Examples

Verified patterns from official sources:

### server.py serve() Skeleton with Mutation State

```python
# Source: graphify/serve.py (existing structure) + CONTEXT.md decisions
import uuid
from datetime import datetime, timezone

def serve(graph_path: str = "graphify-out/graph.json") -> None:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types

    G = _load_graph(graph_path)
    communities = _communities_from_graph(G)
    _graph_mtime = Path(graph_path).stat().st_mtime

    # Sidecar state (loaded once at startup)
    _out_dir = Path(graph_path).parent
    _annotations: list[dict] = _compact_annotations(_out_dir / "annotations.jsonl")
    _agent_edges: list[dict] = _load_agent_edges(_out_dir / "agent-edges.json")

    # Peer identity for this server lifetime (D-05)
    _session_id = str(uuid.uuid4())

    server = Server("graphify")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            # ... existing read tools ...
            types.Tool(
                name="annotate_node",
                description="Add a text annotation to a node by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string"},
                        "text": {"type": "string"},
                        "peer_id": {"type": "string", "default": "anonymous"},
                    },
                    "required": ["node_id", "text"],
                },
            ),
            # ... flag_node, add_edge, propose_vault_note, get_annotations ...
        ]
```

### annotate_node Handler

```python
# Source: CONTEXT.md D-12, D-15, D-04, D-05
def _tool_annotate_node(arguments: dict) -> str:
    node_id = sanitize_label(arguments["node_id"])
    text = sanitize_label(arguments["text"])
    peer_id = sanitize_label(arguments.get("peer_id", "anonymous"))
    record = {
        "record_id": str(uuid.uuid4()),
        "annotation_type": "annotation",
        "node_id": node_id,
        "text": text,
        "peer_id": peer_id,
        "session_id": _session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_annotation(_out_dir / "annotations.jsonl", record)
    _annotations.append(record)  # keep in-memory cache current
    return json.dumps(record)
```

### get_annotations Handler with Filters

```python
# Source: CONTEXT.md D-06, D-08, D-09
def _tool_get_annotations(arguments: dict) -> str:
    peer_filter = arguments.get("peer_id")
    session_filter = arguments.get("session_id")
    time_from = arguments.get("time_from")  # ISO-8601 string
    time_to = arguments.get("time_to")      # ISO-8601 string

    results = list(_annotations)
    if peer_filter:
        results = [r for r in results if r.get("peer_id") == peer_filter]
    if session_filter:
        results = [r for r in results if r.get("session_id") == session_filter]
    if time_from:
        results = [r for r in results if r.get("timestamp", "") >= time_from]
    if time_to:
        results = [r for r in results if r.get("timestamp", "") <= time_to]
    return json.dumps(results)
```

### graphify approve Core Logic

```python
# Source: __main__.py snapshot subcommand pattern (lines 907-1016)
def _approve_proposal(proposal_path: Path, vault_path: Path) -> None:
    """Feed an approved proposal through the merge engine."""
    from graphify.profile import load_profile, validate_vault_path as _vvp
    from graphify.merge import compute_merge_plan, apply_merge_plan
    from graphify.templates import render_note

    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    _vvp(proposal.get("suggested_folder", ""), vault_path)

    profile = load_profile(vault_path)
    # Construct a rendered note dict from proposal fields
    rendered = {
        "path": proposal.get("suggested_folder", "") + "/" + proposal["title"] + ".md",
        "content": proposal["body_markdown"],
        "note_type": proposal.get("note_type", "note"),
    }
    plan = compute_merge_plan([rendered], vault_path, profile)
    apply_merge_plan(plan, vault_path, profile)

    # Mark proposal as approved
    proposal["status"] = "approved"
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(f"approved: {proposal['title']}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON arrays for append-heavy logs | JSONL (one object per line) | ~2019 in log tooling | Append is atomic for single-line writes; no full-file rewrite lock needed |
| UUIDs derived from machine ID (UUID1) | UUID4 (random) | GDPR era (~2018) | Removes MAC address from persistent identifiers |
| Hard-wired identity from env vars | Explicit peer_id parameter | Honcho pattern (2024) | Annotations are safe to commit; no machine identity leak |
| Direct vault writes from agent tools | Staging queue + human approval | letta-obsidian pattern (2024) | Human-in-the-loop prevents agent hallucinations from corrupting vault |

**Deprecated/outdated:**
- `uuid.uuid1()`: Embeds MAC address in bytes 10-15. Never use for peer or session identity.
- Full-file JSON rewrite for logs: Replaced by JSONL append. The read-modify-write pattern on a shared log file is a data corruption hazard.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Filesystem `open(path, "a")` append is atomic for single-line writes on macOS/Linux | Standard Stack + Architecture | Concurrent appends could interleave if writes exceed one `write()` syscall (>4KB typical); risk is low for annotation records (~200 bytes each) |
| A2 | `mcp` 1.27.0 imposes no restriction on synchronous state mutation inside `call_tool` handlers | Standard Stack | If MCP SDK enforces async-only state access, handler pattern needs adjustment; confirmed against SUMMARY.md which states "MCP SDK imposes no restriction" |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

Both assumptions are LOW risk given corroborating evidence in SUMMARY.md.

## Open Questions (RESOLVED)

1. **agent-edges.json growth: load fully at startup vs. incremental append**
   - What we know: D-16 says single-server assumption; D-03 says JSONL compaction at startup for annotations
   - What's unclear: Whether `agent-edges.json` should also be JSONL or remain a full JSON array rewritten atomically
   - RESOLVED: Use full JSON array + `os.replace()` atomic write (D-02 separates the files for good reason; edges have different dedup semantics than annotations). For large edge sets (>10K), revisit in v1.2.

2. **JSONL compaction dedup key: what defines "same annotation"?**
   - What we know: D-03 says compact at startup; annotation_type + node_id + peer_id is the natural composite key
   - What's unclear: Whether two annotations for the same node/peer with different text are duplicates or updates
   - RESOLVED: Keep LAST record per (node_id, annotation_type, peer_id) tuple. Free text can change across sessions — latest is authoritative. This is left to Claude's discretion per CONTEXT.md.

3. **graphify approve --vault absent: hard error or --dry-run fallback?**
   - What we know: D-11 requires explicit `--vault`; `graphify approve` (no args) should list proposals
   - What's unclear: Whether `graphify approve` with no `<id>` and no `--vault` is a list-only mode (valid without vault) or an error
   - RESOLVED: `graphify approve` (no args) = list pending proposals (no vault needed). `graphify approve <id>` without `--vault` = error with usage message. This matches the snapshot pattern where listing doesn't require a target.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `mcp` | serve.py MCP server | Yes | 1.27.0 [VERIFIED] | Already optional extra; ImportError handled in serve() |
| `networkx` | Graph reload in serve.py | Yes | 3.4.2 [VERIFIED] | None (core dependency) |
| `uuid` stdlib | session_id, record_id generation | Yes | stdlib | None needed |
| `datetime` stdlib | ISO timestamps | Yes | stdlib | None needed |
| `os` stdlib | `os.replace()`, `os.stat()` | Yes | stdlib | None needed |
| `json` stdlib | JSONL, proposal serialization | Yes | stdlib | None needed |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — discovered by default |
| Quick run command | `pytest tests/test_serve.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | `annotate_node` persists record to `annotations.jsonl` | unit | `pytest tests/test_serve.py::test_annotate_node_persists -x` | No — Wave 0 |
| MCP-02 | `flag_node` persists importance record to `annotations.jsonl` | unit | `pytest tests/test_serve.py::test_flag_node_persists -x` | No — Wave 0 |
| MCP-03 | `add_edge` writes to `agent-edges.json`, not `graph.json` | unit | `pytest tests/test_serve.py::test_add_edge_sidecar_only -x` | No — Wave 0 |
| MCP-04 | `annotations.jsonl` uses append (crash-safe) | unit | `pytest tests/test_serve.py::test_annotation_append_only -x` | No — Wave 0 |
| MCP-05 | Every record has peer_id/session_id/timestamp; peer_id defaults to "anonymous" | unit | `pytest tests/test_serve.py::test_record_provenance_fields -x` | No — Wave 0 |
| MCP-05 | peer_id never derived from environment variables | unit | `pytest tests/test_serve.py::test_peer_id_no_env_leak -x` | No — Wave 0 |
| MCP-06 | `propose_vault_note` writes to proposals/, not vault | unit | `pytest tests/test_serve.py::test_propose_writes_to_staging_only -x` | No — Wave 0 |
| MCP-07 | `graphify approve <id> --vault <path>` applies merge engine | unit | `pytest tests/test_main_cli.py::test_approve_applies_merge_engine -x` | No — Wave 0 |
| MCP-07 | `graphify approve --reject <id>` marks proposal rejected | unit | `pytest tests/test_main_cli.py::test_approve_reject_id -x` | No — Wave 0 |
| MCP-08 | `get_annotations` filters by peer_id | unit | `pytest tests/test_serve.py::test_get_annotations_peer_filter -x` | No — Wave 0 |
| MCP-08 | `get_annotations` filters by session_id | unit | `pytest tests/test_serve.py::test_get_annotations_session_filter -x` | No — Wave 0 |
| MCP-08 | `get_annotations` filters by time_range | unit | `pytest tests/test_serve.py::test_get_annotations_time_filter -x` | No — Wave 0 |
| MCP-09 | Session-scoped view returns only current session annotations by default | unit | `pytest tests/test_serve.py::test_session_scoped_view -x` | No — Wave 0 |
| MCP-10 | `graph.json` is byte-for-byte unchanged after annotate_node, flag_node, add_edge | unit | `pytest tests/test_serve.py::test_graph_json_never_mutated -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_serve.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test functions in `tests/test_serve.py` — covers MCP-01 through MCP-10 unit tests for helper functions
- [ ] New test functions in `tests/test_main_cli.py` — covers MCP-07 (`graphify approve` CLI)
- [ ] `tests/test_serve.py` already exists — append new test functions to it (do not create a new file)

*(All new tests are additions to existing test files — no new test infrastructure needed)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No authentication in MCP tools (local stdio transport) |
| V3 Session Management | Partial | `session_id` = UUID4 at server start; not auth, but provenance tracking |
| V4 Access Control | Yes | `validate_vault_path()` from `profile.py` confines vault writes; proposals staged before vault access |
| V5 Input Validation | Yes | `sanitize_label()` on all agent-supplied strings; schema validation on required fields |
| V6 Cryptography | No | No cryptography; UUID4 is privacy-safe but not a security guarantee |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in proposal `suggested_folder` | Tampering | `validate_vault_path()` at approval time; server-generated UUID filenames in proposals/ |
| Control character injection in annotation text | Tampering | `sanitize_label()` strips `\x00-\x1f\x7f` |
| Identity leak via peer_id from `os.environ` | Info Disclosure | Default to `"anonymous"`; never read env vars for identity |
| Unbounded annotation growth | DoS | Compaction at startup; no per-write size cap needed (records are small) |
| Agent writes to vault without approval | Elevation of Privilege | `propose_vault_note` writes to `graphify-out/proposals/` only; vault path not accepted as tool argument |
| UUID1 leaking MAC address | Info Disclosure | `uuid.uuid4()` exclusively — never `uuid.uuid1()` |

## Sources

### Primary (HIGH confidence)

- `graphify/serve.py` — Existing MCP server: handler dispatch pattern, `_load_graph`, `_filter_blank_stdin`, tool registration via `types.Tool` JSON Schema
- `graphify/cache.py` — `os.replace()` atomic write pattern, `file_hash()` SHA256 — reused for `agent-edges.json` writes
- `graphify/security.py` — `sanitize_label()`, `validate_graph_path()`, `validate_url()` — source of truth for input validation
- `graphify/__main__.py` (lines 907–1016) — `snapshot` subcommand: manual sys.argv parsing, argument loop pattern — template for `approve` subcommand
- `graphify/merge.py` — `compute_merge_plan()` + `apply_merge_plan()` — used in proposal approval flow (D-10)
- `graphify/profile.py` — `validate_vault_path()` — path confinement for vault writes at approval time
- `.planning/phases/07-mcp-write-back-peer-modeling/07-CONTEXT.md` — All locked decisions D-01 through D-16
- `.planning/research/SUMMARY.md` — Verified architecture approach, critical pitfalls 1–7, Phase 7 component list

### Secondary (MEDIUM confidence)

- `.planning/notes/repo-gap-analysis.md` — Honcho peer model (peer_id as explicit param), letta-obsidian `propose_obsidian_note` staging pattern

### Tertiary (LOW confidence)

- None — all claims verified against codebase or CONTEXT.md

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via pip; no new dependencies introduced
- Architecture: HIGH — all patterns verified against existing codebase (serve.py, cache.py, __main__.py, merge.py)
- Pitfalls: HIGH — pitfalls 1–7 explicitly validated in SUMMARY.md and CONTEXT.md canonical refs
- Security: HIGH — ASVS controls map directly to existing `security.py` and `profile.py` functions

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (mcp SDK stable; stdlib patterns don't change)
