# Phase 11: Narrative Mode as Interactive Slash Commands — Research

**Researched:** 2026-04-17
**Domain:** MCP server extension + Claude Code slash-command skills + snapshot/delta traversal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Each `.claude/commands/*.md` file is a Claude Code slash-command skill. Contract: the `.md` contains a prompt that instructs Claude to (1) call the relevant MCP tool(s) against `graphify-out/graph.json`, (2) render a narrative response from the tool output. No shelling to `graphify` CLI from inside the command prompt.
- **D-02:** Output format is Claude-authored markdown with embedded tables/lists — not raw JSON and not static narrative. MCP tools return structured data; Claude renders into thinking-partner-grade paragraph+bullet output.
- **D-03:** Argument parsing lives in the command prompt itself. Claude parses `$ARGUMENTS` (Claude Code convention).
- **D-04:** Add new MCP tools to `graphify/serve.py` as needed; no new `graphify/` module.
- **D-05:** Preliminary endpoint gap analysis (see Standard Stack section for verified details).
- **D-06:** `/trace` entity resolution is label-first fuzzy via existing `_find_node()`; disambiguation on multiple matches.
- **D-07:** All new MCP identifier-accepting tools MUST honor Phase 10's alias redirect (`resolved_from_alias` meta).
- **D-08:** All new MCP tools MUST emit Phase-9.2-compatible hybrid responses — `text_body` + `\n---GRAPHIFY-META---\n` + `json(meta)` with a `status` field.
- **D-09:** Every new MCP tool accepts `budget: int` parameter and returns 3-layer progressive disclosure. Default budget 500 tokens.
- **D-10:** Missing graph: status `no_graph`, human-readable hint.
- **D-11:** Insufficient history: status `insufficient_history`, `snapshots_available: N` meta field; requires ≥2 snapshots.
- **D-12:** Ambiguous entity: status `ambiguous_entity` + list of `{id, label, source_file}` candidates.
- **D-13:** Slash commands ship via `graphify install` — extend `_PLATFORM_CONFIG` in `__main__.py` for all 7 existing platforms.
- **D-14:** `--no-commands` opt-out flag on `graphify install`/`graphify uninstall`.
- **D-15:** Command file source at `graphify/commands/*.md`, packaged via `pyproject.toml`.
- **D-16:** Add one-line section to each platform's skill file listing available slash commands.
- **D-17:** Core 5 first, stretch 2 conditional (~60% budget threshold).
- **D-18:** No new graph algorithms — Phase 11 is plumbing over existing `analyze.py` / `delta.py` / `snapshot.py`.
- **D-19:** No UI framework — markdown prompts rendered in Claude Code's chat surface.

### Claude's Discretion

- Exact MCP tool names (e.g., `graph_summary` vs `context_digest`) — final names chosen during planning to harmonize with existing 13-tool naming (verb_object style).
- Exact prompt template wording inside each `.md` command file.
- Internal representation of snapshot timelines returned by `entity_trace` (list of records vs. compressed run-length encoding).
- Whether `connect_topics` ships as a standalone composition MCP tool or the `/connect` command prompt chains two existing tool calls.
- Fallback when `graphify-out/snapshots/` exists but no `GRAPH_DELTA.md` — regenerate on demand or report `stale_delta`.

### Deferred Ideas (OUT OF SCOPE)

- Sibling thinking-skill project — if `/ghost` and `/challenge` exceed graphify's scope, they migrate there.
- Always-on JSONL event log for finer-grained `/trace` timelines.
- Command file platform variants beyond Claude Code — only materialize on evidence of divergence.
- Slash commands inside Obsidian vault (plugin development out of scope).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SLASH-01 | User can run `/context` to load a full graph-backed life-state summary (active god nodes, top communities, recent deltas) from the currently-loaded graph | New MCP tool `graph_summary` composing `god_nodes()` + community listing + `compute_delta()` against most recent snapshot — all primitives verified in `analyze.py`, `snapshot.py`, `delta.py` |
| SLASH-02 | User can run `/trace <entity>` to see how a specific entity/concept has evolved across graph snapshots | New MCP tool `entity_trace` walking `list_snapshots()` + `load_snapshot()` per path + `classify_staleness()` per node — all verified signatures in `snapshot.py`/`delta.py` |
| SLASH-03 | User can run `/connect <topic-a> <topic-b>` to find the shortest surprising bridge paths | Composes existing `shortest_path` tool + new MCP exposure of `surprising_connections()` from `analyze.py`. `/connect` command chains two MCP calls or uses a new `connect_topics` tool per planner's choice |
| SLASH-04 | User can run `/drift` to surface emerging patterns across sessions — nodes trending in community/centrality/edge density | New MCP tool `drift_nodes` consuming `list_snapshots()`, `load_snapshot()`, and computing per-node delta vectors across last N snapshots. Requires ≥2 snapshots; hard floor at 3 for trend direction |
| SLASH-05 | User can run `/emerge` to surface newly-formed clusters not present in the previous snapshot | New MCP tool `newly_formed_clusters` using `compute_delta()` from `delta.py` filtered to community-level additions. Requires ≥2 snapshots |
| SLASH-06 (stretch) | User can run `/ghost` to answer in the user's voice grounded in their graph contributions | Requires per-user contribution extraction from annotation layer (annotations.jsonl) and graph node ownership data. Defer if >60% budget consumed by core 5 |
| SLASH-07 (stretch) | User can run `/challenge <belief>` to pressure-test a stated belief against graph evidence | Requires evidence-classification query: supporting vs. contradicting edges around a free-text belief. Defer if >60% budget consumed by core 5 |
</phase_requirements>

---

## Summary

Phase 11 is almost entirely a **plumbing phase**: the analysis algorithms it needs (god nodes, surprising connections, graph diff, staleness) all exist in `analyze.py` and `delta.py`. The snapshot storage layer (`snapshot.py`) is complete with `save_snapshot`, `load_snapshot`, `list_snapshots` and the 10-snapshot FIFO cap. What is missing is MCP exposure for four of the five core commands.

The existing 13-tool MCP server in `serve.py` provides `god_nodes`, `graph_stats`, `shortest_path`, and `query_graph`. The gap is: (a) no single `graph_summary` tool that combines god nodes + communities + delta for `/context`; (b) no `entity_trace` tool that walks the snapshot chain per node; (c) no MCP exposure of `surprising_connections()` for `/connect`; (d) no per-node trend-vector tool across snapshots for `/drift`; (e) no cluster-emergence diff tool for `/emerge`. Each of these can be implemented in `serve.py` as a new closure following the exact pattern used by the existing 13 handlers.

Claude Code slash-command skills as of April 2026 are `.md` files in `.claude/commands/` or `.claude/skills/<name>/SKILL.md`. Both formats work identically. They support YAML frontmatter (optional) and `$ARGUMENTS` / `$0` / `$1` string substitution. No bash shelling is needed from inside commands — Claude Code passes the rendered prompt to Claude, which calls MCP tools via the Skill tool. This is exactly the D-01 contract. All 7 graphify platform variants (Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, Trae CN) must receive command files via `_PLATFORM_CONFIG` extension. Only Claude Code natively supports `.claude/commands/` — other platforms receive equivalent AGENTS.md-injection or skill-dir installation per the existing per-platform pattern, but the command prompt content is identical.

**Primary recommendation:** Implement the 5 new MCP tools in `serve.py` following the hybrid-response envelope pattern, ship 5 (or 7) command files in `graphify/commands/`, extend `_PLATFORM_CONFIG` and `install`/`uninstall` with command-file copying, and add `graphify/commands/*.md` to `pyproject.toml` package-data.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Graph data queries (god nodes, delta, communities) | Library (serve.py MCP tools) | — | Graph state lives in graphify-out/; only the MCP server has the loaded graph in memory |
| Snapshot chain traversal (trace, drift, emerge) | Library (serve.py MCP tools) | snapshot.py / delta.py | The MCP tool loads each snapshot via `load_snapshot`; business logic stays in serve.py closures |
| Narrative rendering (thinking-partner output) | Claude Code (command prompt) | — | D-02: Claude authors markdown from structured MCP tool responses |
| Argument parsing ($ARGUMENTS) | Claude Code (command file) | — | D-03: Claude Code passes arguments via `$ARGUMENTS` substitution |
| Installation / distribution | CLI (__main__.py) | pyproject.toml | D-13/D-15: command files packaged in wheel, copied by `graphify install` |
| Security (user input sanitization) | Library (security.py) | serve.py callers | D-07: `sanitize_label()` applied to any user-supplied argument echoed back |

---

## Standard Stack

### Core (verified in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | any | Graph data structure, `nx.Graph`, community reconstruction | Already the primary abstraction throughout the codebase |
| graphify.snapshot | internal | `save_snapshot`, `load_snapshot`, `list_snapshots`, `snapshots_dir`, `auto_snapshot_and_delta` | Already ships in v1.1; Phase 11 is a consumer, not a contributor |
| graphify.delta | internal | `compute_delta`, `classify_staleness`, `render_delta_md` | Same as above; Phase 11 calls these from new MCP tools |
| graphify.analyze | internal | `god_nodes()`, `surprising_connections()`, `graph_diff()`, `suggest_questions()` | Already used by pipeline; Phase 11 adds MCP exposure |
| graphify.security | internal | `sanitize_label(text)` | Mandatory per SECURITY.md for any user-supplied string echoed in a response |
| mcp (optional dep) | any | MCP server registration (`types.Tool`, `types.TextContent`) | Phase 11 extends the existing `serve()` function; same import pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | N/A | Meta JSON serialization for hybrid response envelope | Every new MCP tool |
| pathlib.Path (stdlib) | N/A | Snapshot path resolution | `entity_trace`, `drift_nodes`, `newly_formed_clusters` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `graphify/commands/*.md` command source | `graphify/skills/` subdirs with `SKILL.md` | Skills format is now preferred per April 2026 Claude Code docs, but `.claude/commands/` files still work and are simpler — no subdirectory required. D-15 already specifies the commands flat layout. |
| Snapshot-bounded timelines for `/trace` | Always-on JSONL event log | JSONL is richer but is new infra — explicitly deferred per CONTEXT.md. Snapshots are the shipped choice. |
| Claude chaining two tool calls for `/connect` | New `connect_topics` composition tool | Composition tool is cleaner for non-Claude MCP clients; Claude chaining is faster to ship. Planner decides per Claude's Discretion area. |

**Installation:** No new packages required. Command files are plain `.md` files packaged into the wheel.

---

## Architecture Patterns

### System Architecture Diagram

```
User types: /context [or /trace X, /connect A B, /drift, /emerge]
                      |
               Claude Code runtime
                      |
         [Reads .claude/commands/<name>.md]
                      |
         [Substitutes $ARGUMENTS → user text]
                      |
         Claude receives rendered prompt
                      |
     Claude calls MCP tool(s) via graphify MCP server
                      |
         serve.py: new handler (_tool_graph_summary,
                   _tool_entity_trace, _tool_connect_topics,
                   _tool_drift_nodes, _tool_newly_formed_clusters)
                      |
         Handler loads graph via _load_graph() / _reload_if_stale()
                      |
         For snapshot commands: list_snapshots() → load_snapshot()
                      |
         Computes result using analyze.py / delta.py primitives
                      |
         Emits: text_body + SENTINEL + json(meta)
         [status, layer, resolved_from_alias, snapshots_available, ...]
                      |
         Claude reads response, authors narrative markdown
                      |
            User sees thinking-partner output
```

### Recommended Project Structure

```
graphify/
├── serve.py           # 5 new MCP tool handlers + registration (primary change)
├── commands/          # NEW: source for slash command prompt files
│   ├── context.md     # SLASH-01
│   ├── trace.md       # SLASH-02
│   ├── connect.md     # SLASH-03
│   ├── drift.md       # SLASH-04
│   ├── emerge.md      # SLASH-05
│   ├── ghost.md       # SLASH-06 (stretch)
│   └── challenge.md   # SLASH-07 (stretch)
├── __main__.py        # extend _PLATFORM_CONFIG + install/uninstall
└── (no new modules)
```

### Pattern 1: New MCP Tool (Handler-in-Closure Pattern)

Every new MCP tool follows the exact pattern of existing handlers in `serve()`:

```python
# Source: verified in graphify/serve.py lines 1239-1432 (existing handler pattern)
def _tool_graph_summary(arguments: dict) -> str:
    _reload_if_stale()
    # Guard: graph must exist (D-10)
    # ... load graph, compute result using analyze.py primitives
    # Emit hybrid response:
    text_body = "..."  # narrative Layer 1 summary
    meta = {
        "status": "ok",          # or "no_graph", "insufficient_history"
        "layer": layer,
        "search_strategy": None,
        "cardinality_estimate": None,
        "continuation_token": None,
    }
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

Tool registered in `_handlers` dict and `list_tools()` return list — same location as existing tools.

### Pattern 2: Snapshot Chain Iteration (for `/trace`, `/drift`, `/emerge`)

```python
# Source: verified in graphify/snapshot.py lines 21-26, 123-150
from graphify.snapshot import list_snapshots, load_snapshot

snaps = list_snapshots(root)  # sorted oldest-first by mtime
if len(snaps) < 2:
    # emit status="insufficient_history", snapshots_available=len(snaps)
    ...

for path in snaps[-N:]:  # last N snapshots
    G_snap, communities_snap, metadata = load_snapshot(path)
    # metadata["timestamp"] is ISO-8601 string
    # metadata["node_count"], metadata["edge_count"] available
    ...
```

### Pattern 3: Slash Command Prompt File

```markdown
---
name: context
description: Load a full graph-backed summary of the current knowledge graph — active god nodes, top communities, and recent changes. Use when the user wants a life-state or project summary.
argument-hint: (no arguments)
disable-model-invocation: true
---

Call the graphify MCP tool `graph_summary` with:
- `budget`: 500 (default)

Render the result as a narrative markdown response with:
1. **Active god nodes** — the 5 most-connected entities; what they are, how many connections
2. **Top communities** — the 3 largest clusters; their apparent theme
3. **Recent changes** — what shifted since the last run (new nodes, migrations, staleness summary)

Tone: thinking-partner, not a report. Suggest one follow-up question ("You might want to /trace X next").

If the tool returns `status: no_graph`, tell the user: "No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command."
```

**Key observations from April 2026 Claude Code docs [VERIFIED: code.claude.com/docs/en/slash-commands]:**
- Both `.claude/commands/<name>.md` and `.claude/skills/<name>/SKILL.md` create the same `/name` command
- `$ARGUMENTS` expands to full argument string; `$0`, `$1` for positional args
- YAML frontmatter is optional; `disable-model-invocation: true` prevents Claude from auto-triggering
- `argument-hint` shows during autocomplete (useful for `/trace` and `/connect`)
- Files in `.claude/commands/` still fully supported as of Claude Code v2.1 (April 2026)
- No bash shelling needed — MCP tools are called via Claude's normal tool use, not shell commands

### Anti-Patterns to Avoid

- **Shelling to `graphify` CLI from command prompt:** D-01 forbids this. Commands must call MCP tools only.
- **Returning raw JSON as the command output:** D-02 forbids this. Claude authors narrative from tool response.
- **Building new graph algorithms in Phase 11:** D-18 forbids this. All analysis is pre-existing.
- **Multiple snapshot loads without budget guard:** `/drift` iterates up to 10 snapshots — each `load_snapshot()` deserializes a NetworkX graph. At 500+ nodes, 10 loads × ~1MB = ~10MB deserialization. Compute trend vectors incrementally, not by holding all 10 graphs in memory simultaneously.
- **Skipping alias resolution in new tools:** D-07 requires every node-identifier-accepting tool to call `_resolve_alias()` and include `resolved_from_alias` in meta when a redirect occurred.

---

## MCP Tool Inventory and Gap Analysis

### Existing 13 Tools (verified in serve.py)

[VERIFIED: graphify/serve.py lines 1054–1218]

| Tool Name | Inputs | Output | Phase 11 Use |
|-----------|--------|--------|--------------|
| `query_graph` | question, mode, depth, budget, layer, continuation_token | hybrid: subgraph text + meta | Indirectly via `/context` if needed; not a primary building block |
| `get_node` | label | plain text node detail with staleness | Reusable by `/trace` as point-in-time lookup |
| `get_neighbors` | label, relation_filter | plain text neighbor list | Reusable |
| `get_community` | community_id | plain text community member list | `/context` secondary |
| `god_nodes` | top_n | plain text ranked list | Used by new `graph_summary` tool |
| `graph_stats` | (none) | plain text stats | `/context` secondary |
| `shortest_path` | source, target, max_hops | plain text path | `/connect` primary — composes with `surprising_connections` |
| `annotate_node` | node_id, text, peer_id | JSON record | Not used in Phase 11 |
| `flag_node` | node_id, importance, peer_id | JSON record | Not used |
| `add_edge` | source, target, relation, peer_id | JSON record | Not used |
| `propose_vault_note` | title, body_markdown, ... | JSON {record_id, status} | Not used |
| `get_annotations` | peer_id, session_id, time filters | JSON array | `/ghost` (stretch) |
| `get_agent_edges` | peer_id, session_id, node_id | JSON array | Not used |

**Key finding:** `god_nodes`, `shortest_path`, `get_annotations` are the only existing tools that serve Phase 11 commands directly. All 5 core commands need either new tools or composition of MCP calls inside the command prompt.

### Net-New MCP Tools Required

[VERIFIED through serve.py audit and analyze.py/snapshot.py/delta.py inspection]

#### Tool 1: `graph_summary` (for SLASH-01 `/context`)

**Purpose:** One-shot combination of god nodes + top communities by size + most-recent delta summary.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "budget": {"type": "integer", "default": 500},
    "top_n_nodes": {"type": "integer", "default": 5},
    "top_n_communities": {"type": "integer", "default": 3}
  }
}
```

**Output fields (meta):**
- `status`: `"ok"` | `"no_graph"` | `"no_data"`
- `god_nodes`: list of `{id, label, edges}` (from `analyze.god_nodes()`)
- `top_communities`: list of `{id, size, sample_labels}` (from `_communities_from_graph()`)
- `recent_delta`: dict from `compute_delta()` against most recent previous snapshot, or `null` if only 1 snapshot exists
- `snapshot_count`: int — how many snapshots exist

**Python sources used:**
- `from graphify.analyze import god_nodes as _god_nodes` (serve.py already imports analyze lazily)
- `_communities_from_graph(G)` (already in serve.py)
- `from graphify.snapshot import list_snapshots, load_snapshot`
- `from graphify.delta import compute_delta`

#### Tool 2: `entity_trace` (for SLASH-02 `/trace`)

**Purpose:** Per-entity timeline across snapshot chain — first seen, community history, staleness.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "entity": {"type": "string", "description": "Node label or ID"},
    "budget": {"type": "integer", "default": 500},
    "max_snapshots": {"type": "integer", "default": 10}
  },
  "required": ["entity"]
}
```

**Output fields (meta):**
- `status`: `"ok"` | `"no_graph"` | `"insufficient_history"` | `"ambiguous_entity"` | `"entity_not_found"`
- `entity_id`: resolved canonical ID
- `entity_label`: display label
- `resolved_from_alias`: `{canonical_id: [alias_list]}` if alias redirect
- `snapshots_available`: int
- `timeline`: list of `{snapshot_ts, community_id, degree, staleness, found}` — one entry per snapshot

**Key implementation notes:**
- Use `_find_node(G, entity)` for initial resolution in current graph
- If multiple matches → `status: ambiguous_entity`, return candidate list per D-12
- Walk `list_snapshots()` oldest-to-newest; for each snapshot, check if node_id in `G_snap.nodes`
- `classify_staleness(G.nodes[node_id])` is only meaningful on the current graph (requires disk access); for historical snapshots, report community_id + degree only
- `first_seen`: timestamp of earliest snapshot containing the node

#### Tool 3: `connect_topics` (for SLASH-03 `/connect`) — OPTIONAL

**Purpose:** Compose shortest-path + surprising-connections for two topics in one response.

**Note on optionality:** Per Claude's Discretion, the `/connect` command prompt may instead chain two separate MCP calls (`shortest_path` + a new `surprising_connections` MCP tool). A standalone `connect_topics` tool is cleaner for non-Claude MCP clients. The planner should decide.

If `connect_topics` is implemented:

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "topic_a": {"type": "string"},
    "topic_b": {"type": "string"},
    "budget": {"type": "integer", "default": 500},
    "max_hops": {"type": "integer", "default": 8}
  },
  "required": ["topic_a", "topic_b"]
}
```

**Output:** shortest path from `nx.shortest_path()` + top 3 surprising connections from `surprising_connections(G, communities, top_n=3)`.

**Alternative (no new tool):** The `/connect` command prompt calls `shortest_path` (existing) and then calls a new minimal `graph_surprises` tool that MCP-exposes `surprising_connections()`.

#### Tool 4: `drift_nodes` (for SLASH-04 `/drift`)

**Purpose:** Per-node trend vectors across last N snapshots — community stability, centrality trend, edge density trend.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "budget": {"type": "integer", "default": 500},
    "max_snapshots": {"type": "integer", "default": 10},
    "top_n": {"type": "integer", "default": 5}
  }
}
```

**Output (meta):**
- `status`: `"ok"` | `"no_graph"` | `"insufficient_history"`
- `snapshots_used`: int
- `drifting_nodes`: list of `{id, label, community_changes, degree_trend, reason}` sorted by drift magnitude

**Key implementation notes:**
- Requires ≥2 snapshots for any output; ≥3 for reliable trend direction (2 points = single delta, not trend)
- Iterate snapshots oldest-to-newest; for each common node, record (community_id, degree) per snapshot
- Trend = monotonic direction across ≥3 consecutive snapshots; or simple delta for exactly 2
- Memory discipline: do NOT hold all 10 deserialized graphs simultaneously. Process pairwise or accumulate only node-level scalar vectors (community_id, degree) per snapshot — discard each `G_snap` after extraction.

#### Tool 5: `newly_formed_clusters` (for SLASH-05 `/emerge`)

**Purpose:** Detect communities present in current snapshot that did not exist in the previous snapshot.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "budget": {"type": "integer", "default": 500}
  }
}
```

**Output (meta):**
- `status`: `"ok"` | `"no_graph"` | `"insufficient_history"` | `"no_change"`
- `snapshots_available`: int
- `emerged_communities`: list of `{community_id, size, sample_labels, nodes_from_delta}` for clusters new since last snapshot
- `delta_summary`: string from `compute_delta()`'s summary field

**Key implementation notes:**
- Uses `list_snapshots()[-2]` and current graph for two-snapshot diff
- `compute_delta()` returns `added_nodes`; cross-reference with current `communities` to find which new nodes cluster together in a new community
- "New community" = community_id in current communities whose member nodes are predominantly from `added_nodes` (threshold: >50% of members are newly added)

#### Stretch Tool 6: `ghost_voice` (for SLASH-06 `/ghost`)

**Purpose:** Extract user's voice/style from annotations layer and graph contributions.

**Source material:** `_annotations` list (loaded at serve startup from annotations.jsonl), `_agent_edges` list. The user's "voice" is approximated from annotation texts they've written.

**Status:** Only implement if core 5 are complete within ~60% of planning budget.

#### Stretch Tool 7: `challenge_belief` (for SLASH-07 `/challenge`)

**Purpose:** Query graph for edges supporting vs. contradicting a free-text belief statement.

**Source material:** `query_graph` traversal from a belief-derived query, then classify edges as supporting (high confidence, aligned semantics) vs. contradicting (AMBIGUOUS or contradictory relation types).

**Status:** Only implement if core 5 + /ghost are complete within planning budget.

---

## Snapshot and Delta Layer — Exact Signatures

[VERIFIED: graphify/snapshot.py, graphify/delta.py full read]

### snapshot.py

```python
def snapshots_dir(root: Path = Path(".")) -> Path:
    """Returns graphify-out/snapshots/ — creates if needed."""

def list_snapshots(root: Path = Path(".")) -> list[Path]:
    """Return sorted list of snapshot Paths (oldest first by mtime)."""

def save_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    name: str | None = None,
    cap: int = 10,                 # FIFO prune: keep newest `cap` snapshots
) -> Path:
    """Atomic write via tmp+os.replace. Returns path to saved snapshot."""
    # Payload: {"graph": node_link_data, "communities": {str(k): v}, "metadata": {...}}
    # metadata keys: "timestamp" (ISO-8601), "node_count", "edge_count"

def load_snapshot(path: Path) -> tuple[nx.Graph, dict[int, list[str]], dict]:
    """Returns (graph, communities_with_int_keys, metadata_dict).
    Raises ValueError on corrupt/incomplete snapshot."""

def auto_snapshot_and_delta(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    cap: int = 10,
) -> tuple[Path, Path | None]:
    """Save snapshot and generate GRAPH_DELTA.md. Called by skill post-cluster()."""
```

**Snapshot file naming:** `{YYYY-MM-DDTHH-MM-SS}[_{sanitized_name}].json`
**Snapshot payload keys:** `graph`, `communities`, `metadata`
**Metadata keys:** `timestamp` (ISO-8601 string), `node_count` (int), `edge_count` (int)
**FIFO cap default:** 10 snapshots

### delta.py

```python
def compute_delta(
    G_old: nx.Graph,
    communities_old: dict[int, list[str]],
    G_new: nx.Graph,
    communities_new: dict[int, list[str]],
) -> dict:
    """Returns: {added_nodes, removed_nodes, added_edges, removed_edges,
                 community_migrations, connectivity_changes}"""
    # community_migrations: {node_id: (old_cid, new_cid)} for nodes that changed community
    # connectivity_changes: {node_id: {degree_delta, added_edges, removed_edges}}

def classify_staleness(node_data: dict) -> str:
    """Returns "FRESH" | "STALE" | "GHOST" based on source_hash vs disk."""
    # Requires node to have source_file + source_hash attributes
    # Falls back to "FRESH" if either is absent (no provenance)
```

### Per-entity timeline construction for `/trace`

The snapshot files do NOT store a per-node event log. The timeline must be reconstructed by iterating snapshots and checking node membership:

```python
# Pattern for entity_trace:
timeline = []
for snap_path in list_snapshots(root)[-max_snapshots:]:
    G_snap, comm_snap, meta = load_snapshot(snap_path)
    ts = meta.get("timestamp", snap_path.stem)
    if node_id in G_snap.nodes:
        node_data = G_snap.nodes[node_id]
        # Reconstruct community membership from community attribute
        comm_id = node_data.get("community")
        degree = G_snap.degree(node_id)
        timeline.append({"ts": ts, "found": True, "community": comm_id, "degree": degree})
    else:
        timeline.append({"ts": ts, "found": False})
```

**Note on staleness in historical snapshots:** `classify_staleness()` checks the current disk state of source files. For historical snapshots, source files may have changed since the snapshot was taken — the result is the *current* staleness, not the historical one. This is acceptable for Phase 11 (the user wants to know if the entity is stale now, not at every past moment).

---

## analyze.py Reuse Assessment

[VERIFIED: graphify/analyze.py full read]

### `god_nodes(G, top_n=10) -> list[dict]`

Returns `[{"id": ..., "label": ..., "edges": ...}]`. Filters out file-level hub nodes and concept nodes. Ready to use directly in `graph_summary` MCP tool. [VERIFIED: analyze.py:76]

### `surprising_connections(G, communities, top_n=5) -> list[dict]`

Returns `[{"source", "target", "source_files", "confidence", "relation", "why"}]`. Multi-source: uses cross-file edges with composite surprise score. Single-source: uses cross-community betweenness. **This is NOT the same as shortest-path.** For `/connect`, the command needs:
1. `shortest_path` (existing tool) — finds the actual path between A and B
2. `surprising_connections()` — finds independently surprising edges in the graph (not specifically between A and B)

**Gap for `/connect`:** `surprising_connections()` surfaces the globally most surprising edges, not the most surprising path *between two specific topics*. The `shortest_path` tool already finds the path. The `/connect` command narrative should combine: "Here is the shortest path (N hops)" + "Here are the most surprising edges in the graph that connect to these topics." A `connect_topics` composition tool makes this cleaner but is not strictly necessary if the command prompt chains two tool calls.

### `graph_diff(G_old, G_new) -> dict`

Located at `analyze.py:544`. Returns `{new_nodes, removed_nodes, new_edges, removed_edges, summary}`. **Note:** This is a simpler variant than `delta.compute_delta()` — it doesn't track community migrations or connectivity changes. For Phase 11, prefer `delta.compute_delta()` which is richer and the canonical delta primitive.

### `suggest_questions(G, communities, community_labels, top_n=7) -> list[dict]`

Returns questions grounded in AMBIGUOUS edges, bridge nodes, INFERRED relationships, isolated nodes. Not directly needed for Phase 11 core commands but available as an add-on for `/context` Layer 2/3.

---

## Install Path Extension

[VERIFIED: graphify/__main__.py full read]

### Current `_PLATFORM_CONFIG` (verified 11 entries)

```python
_PLATFORM_CONFIG = {
    "claude":      {"skill_file": "skill.md",          "skill_dst": .claude/skills/graphify/SKILL.md,  "claude_md": True},
    "codex":       {"skill_file": "skill-codex.md",    "skill_dst": .agents/skills/graphify/SKILL.md,  "claude_md": False},
    "opencode":    {"skill_file": "skill-opencode.md", "skill_dst": .config/opencode/skills/...,        "claude_md": False},
    "aider":       {"skill_file": "skill-aider.md",    "skill_dst": .aider/graphify/SKILL.md,           "claude_md": False},
    "copilot":     {"skill_file": "skill-copilot.md",  "skill_dst": .copilot/skills/graphify/SKILL.md,  "claude_md": False},
    "claw":        {"skill_file": "skill-claw.md",     "skill_dst": .openclaw/skills/graphify/SKILL.md, "claude_md": False},
    "droid":       {"skill_file": "skill-droid.md",    "skill_dst": .factory/skills/graphify/SKILL.md,  "claude_md": False},
    "trae":        {"skill_file": "skill-trae.md",     "skill_dst": .trae/skills/graphify/SKILL.md,     "claude_md": False},
    "trae-cn":     {"skill_file": "skill-trae.md",     "skill_dst": .trae-cn/skills/graphify/SKILL.md,  "claude_md": False},
    "antigravity": ...,
    "windows":     {"skill_file": "skill-windows.md",  "skill_dst": .claude/skills/graphify/SKILL.md,   "claude_md": True},
}
```

### Command File Destination Per Platform

[ASSUMED for non-Claude platforms — Claude Code is the only platform with a documented `commands/` convention]

| Platform | Command destination | Native support |
|----------|--------------------|--------------------|
| Claude Code (claude, windows) | `~/.claude/commands/<name>.md` | YES — native `.claude/commands/` [VERIFIED: April 2026 docs] |
| Codex | `~/.agents/commands/<name>.md` or AGENTS.md section | UNKNOWN — no documented `commands/` convention |
| OpenCode | AGENTS.md section injection | UNKNOWN |
| Aider | AGENTS.md section injection | UNKNOWN |
| OpenClaw | AGENTS.md section injection | UNKNOWN |
| Factory Droid | AGENTS.md section injection | UNKNOWN |
| Trae / Trae CN | AGENTS.md section injection | UNKNOWN |

**Practical approach:** Per D-15, start with Claude-Code-first (`.claude/commands/`). For non-Claude platforms, inject a "Available slash commands: /context /trace /connect /drift /emerge" awareness section into the existing AGENTS.md section (D-16). Only materialize per-platform command format variants if a platform is confirmed to support slash commands natively.

### `_PLATFORM_CONFIG` Extension Pattern

Each entry needs two new optional keys:

```python
"claude": {
    "skill_file": "skill.md",
    "skill_dst": ...,
    "claude_md": True,
    # Phase 11 additions:
    "commands_src_dir": "commands",          # relative to graphify/ package dir
    "commands_dst": Path(".claude") / "commands",  # relative to Path.home()
    "commands_enabled": True,                # False for platforms without commands support
},
```

### `install()` Extension

The existing `install()` function (serve.py:~110):
1. Copies skill file
2. Optionally updates CLAUDE.md / AGENTS.md

Phase 11 adds step 3:

```python
# After skill copy, before final print:
if not no_commands and cfg.get("commands_enabled"):
    _install_commands(cfg, src_dir=Path(__file__).parent / cfg["commands_src_dir"])
```

`--no-commands` flag is parsed from `sys.argv` before routing to `install()`.

### `pyproject.toml` Change

Current package-data line:
```toml
graphify = ["skill.md", "skill-codex.md", ..., "builtin_templates/*.md"]
```

Required addition:
```toml
graphify = [...existing..., "commands/*.md"]
```

---

## Claude Code Slash Command Format (April 2026)

[VERIFIED: code.claude.com/docs/en/slash-commands — WebFetch April 2026]

### Format Specification

- **File location:** `.claude/commands/<name>.md` (project-scoped) or `~/.claude/commands/<name>.md` (personal)
- **Alternative (equivalent):** `.claude/skills/<name>/SKILL.md`
- **Frontmatter:** YAML between `---` markers, fully optional
- **Command invocation:** `/name [arguments]` — filename stem becomes the slash command

### Frontmatter Fields (relevant to Phase 11)

| Field | Required | Phase 11 Usage |
|-------|----------|----------------|
| `name` | No | Use to match command name to file stem |
| `description` | Recommended | Helps Claude decide when to auto-invoke |
| `argument-hint` | No | Shown during autocomplete — use for `/trace [entity]`, `/connect [topic-a] [topic-b]` |
| `disable-model-invocation` | No | Set `true` for all Phase 11 commands — user-triggered only |
| `allowed-tools` | No | Not needed — MCP tools are always available to Claude |

### Argument Passing

```
$ARGUMENTS      → full argument string as typed by user
$0, $1, $2     → positional arguments (shell-style quoting)
$ARGUMENTS[N]  → same as $N
```

Example for `/connect`:
```markdown
Call `connect_topics` with topic_a="$0" and topic_b="$1"
```

Or the `$ARGUMENTS` approach when argument count is flexible:
```markdown
Arguments: $ARGUMENTS
Parse: topic-a is the first word/phrase, topic-b is everything after the separator.
```

### Security Sanitization Requirements for Command Prompts

When a command prompt echoes user-supplied arguments back (e.g., `/trace Transformer` renders "You asked about: Transformer"), the MCP tool must sanitize via `sanitize_label()` before including in any response text or JSON. [VERIFIED: graphify/security.py:188]

`sanitize_label()` strips control characters and caps at 256 chars. For Markdown rendering, also apply `sanitize_label_md()` which replaces backticks and HTML-escapes angle brackets. [VERIFIED: security.py:200]

---

## Phase 9.2 Hybrid Response Envelope — Complete Specification

[VERIFIED: graphify/serve.py full read + 09.2-CONTEXT.md D-02 decisions]

### SENTINEL

```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
```

Defined at serve.py:735. Parse with: `text_body, _, meta_json = response.partition(SENTINEL)` then `json.loads(meta_json)`.

### Required Meta Fields (all new tools MUST include)

```json
{
  "status": "ok",                  // "ok" | "no_graph" | "insufficient_history" | "ambiguous_entity" | ...
  "layer": 1,                      // int 1|2|3
  "search_strategy": null,         // "bfs" | "dfs" | "bidirectional" | null
  "cardinality_estimate": null,    // dict or null
  "continuation_token": null       // string or null
}
```

Phase 11 adds new status codes per D-10/D-11/D-12:
- `no_graph` — `graphify-out/graph.json` does not exist
- `insufficient_history` — fewer than 2 snapshots; include `snapshots_available: N`
- `ambiguous_entity` — label matches multiple nodes; include `candidates: [{id, label, source_file}]`
- `entity_not_found` — label matches no nodes in any snapshot
- `no_change` — diff produced no new clusters (for `/emerge`)
- `no_data` — tool ran successfully but result set is empty

### Phase 10 Alias Redirect (mandatory for identifier-accepting tools)

```json
{
  "resolved_from_alias": {
    "authentication_service": ["auth", "auth_svc"]
  }
}
```

Include in meta when `_resolved_aliases` dict is non-empty. Per D-07 + WR-03 test confirms multi-alias collapse pattern. [VERIFIED: serve.py:~900 + test_serve.py:1551]

### 3-Layer Progressive Disclosure

| Layer | Token density | What's included |
|-------|--------------|-----------------|
| 1 | ~50 tok/node | Compact summary: IDs, labels, key metrics only |
| 2 | ~200 tok/node + ~30 tok/edge | Layer 1 + edges + neighbor labels |
| 3 | ~100 tok/node + ~95 tok/edge | Full attribute dump |

For Phase 11 tools, Layer 1 should be the default (500 token budget). Layer 2/3 via follow-up with `continuation_token`. All new tools should respect the `budget` parameter and clamp content to `budget * 3` characters.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph diff between snapshots | Custom node-set comparison | `delta.compute_delta()` | Already handles node/edge/community/connectivity tracking |
| Staleness classification | File hash comparison logic | `delta.classify_staleness()` | Handles mtime gate, FRESH/STALE/GHOST, source_hash comparison |
| Snapshot storage | Custom JSON serializer | `snapshot.save_snapshot()` + `load_snapshot()` | Atomic write, payload schema, FIFO prune, mtime sort |
| Entity label matching | Substring matching | `serve._find_node(G, label)` | Case-insensitive, matches label OR node ID |
| God node ranking | Degree centrality sort | `analyze.god_nodes(G, top_n)` | Filters file-hub and concept nodes correctly |
| Surprising edge ranking | Simple confidence sort | `analyze.surprising_connections()` | Composite score (cross-file, cross-type, cross-community, peripheral→hub) |
| Input sanitization | Strip() + truncate | `security.sanitize_label()` | Control char strip + length cap; `sanitize_label_md()` for Markdown context |
| Hybrid response format | Custom separator | `QUERY_GRAPH_META_SENTINEL` + `json.dumps(meta)` | Established contract; existing clients parse this specific sentinel |

**Key insight:** Phase 11 is plumbing over existing analysis infrastructure. The algorithms are shipped; the missing piece is MCP surface area and command file authoring.

---

## Common Pitfalls

### Pitfall 1: Memory Explosion in Snapshot Iteration

**What goes wrong:** `drift_nodes` iterates up to 10 snapshots. Naively holding all 10 deserialized `nx.Graph` objects simultaneously can consume hundreds of MB.

**Why it happens:** `load_snapshot()` returns a full `nx.Graph`. NetworkX graphs with 500+ nodes and rich attributes are ~1–5MB each in memory.

**How to avoid:** Load each snapshot, extract the scalar per-node metrics you need (community_id, degree), then immediately discard the graph object. Accumulate only `dict[node_id, list[scalar]]`.

**Warning signs:** Memory usage growing proportionally to `max_snapshots * graph_size`.

### Pitfall 2: Alias Resolution Missing in New Tools

**What goes wrong:** A new tool like `entity_trace` accepts `entity: str` but doesn't call `_resolve_alias()`. Users who invoke `/trace auth` (the old pre-dedup name) get `entity_not_found` instead of a redirect.

**Why it happens:** Alias resolution is only implemented inside `_run_query_graph()` — it's not a shared middleware.

**How to avoid:** Copy the `_resolve_alias()` pattern from `_run_query_graph()` (serve.py:~810) into each new tool handler that accepts a node identifier. Check `_alias_map` (loaded from dedup_report.json at serve startup).

**Warning signs:** `entity_not_found` status when entity exists under a different name.

### Pitfall 3: `classify_staleness()` on Historical Snapshots

**What goes wrong:** Calling `classify_staleness(snap_node_data)` on a node loaded from a historical snapshot reflects the *current* state of source files on disk, not the state at snapshot time.

**Why it happens:** `classify_staleness()` reads `Path(source_file).exists()` and computes `file_hash()` against the current disk — it has no concept of "was this file stale when the snapshot was taken?"

**How to avoid:** Only call `classify_staleness()` on current graph nodes. For historical snapshot entries in `/trace` output, report community_id + degree only; omit staleness for historical entries.

**Warning signs:** `/trace` timeline shows GHOST/STALE for all historical entries even on files that exist today.

### Pitfall 4: `/connect` Conflating "Surprising" with "Shortest"

**What goes wrong:** User expects `/connect A B` to find a surprising path between A and B. `surprising_connections()` returns globally surprising edges — not specifically connecting A to B.

**Why it happens:** `surprising_connections()` scans all edges; it doesn't take source/target parameters.

**How to avoid:** `/connect` should provide two things: (1) shortest path between A and B via `shortest_path` tool, (2) global surprising connections from `surprising_connections()` as additional context. Do NOT present the global surprises as "the path between A and B." The narrative should read: "The shortest path is X hops. Also, here are surprising connections in the graph that relate to these topics."

**Warning signs:** User confusion when `/connect A B` surfaces edges not involving A or B.

### Pitfall 5: `--no-commands` Flag Scope

**What goes wrong:** `--no-commands` flag is parsed after the `install`/`uninstall` command dispatch, missing the flag entirely.

**Why it happens:** Current `main()` routes to `install(platform=...)` then exits — there's no flag-parsing step before routing.

**How to avoid:** Parse `--no-commands` from `sys.argv` before calling `install()`, then pass it as a parameter. Pattern mirrors how `--platform` is already parsed.

### Pitfall 6: Command File `$ARGUMENTS` Security

**What goes wrong:** `/trace <entity>` renders the entity name directly into the MCP tool call `entity="$0"`. If `$0` contains shell metacharacters or MCP injection characters, it could confuse the tool call.

**Why it happens:** `$ARGUMENTS` is Claude Code string substitution — it's expanded before Claude sees the prompt. The MCP tool receives the entity string through Claude's natural language processing, then as a JSON argument. This is NOT a shell injection risk (D-01 forbids shelling). However, the entity string may contain quotes, angle brackets, or control chars that should be sanitized before echoing back in responses.

**How to avoid:** In the MCP tool handler, pass any user-supplied entity through `sanitize_label()` before including in response text. The argument arrives as a Python string in `arguments["entity"]` — sanitize it before echoing.

### Pitfall 7: `no_graph` Handling in Command Files

**What goes wrong:** Command prompt doesn't handle `status: no_graph` and Claude tries to interpret empty tool output as a graph summary.

**Why it happens:** Claude renders narrative from whatever the tool returns. If the tool returns an empty `text_body` with `status: no_graph` in meta, Claude may hallucinate content.

**How to avoid:** Every command file must explicitly instruct Claude: "If the tool returns `status: no_graph`, render the hint verbatim and stop." Include the exact hint text in the command prompt (D-10): `"No graph found at graphify-out/graph.json. Run /graphify to build one, then re-invoke this command."`

---

## Code Examples

### New MCP Tool Registration (verified pattern)

```python
# Source: graphify/serve.py list_tools() handler, lines ~1054-1218
types.Tool(
    name="graph_summary",
    description=(
        "Return a full graph-backed summary: active god nodes, top communities, "
        "and recent graph changes vs. the previous snapshot. "
        "Use for /context command."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "budget": {"type": "integer", "default": 500},
            "top_n_nodes": {"type": "integer", "default": 5},
            "top_n_communities": {"type": "integer", "default": 3},
        },
    },
),
```

### Hybrid Response Emission (verified pattern)

```python
# Source: graphify/serve.py _run_query_graph, lines ~940-980
text_body = "..." # Layer 1 summary string
meta = {
    "status": "ok",
    "layer": 1,
    "search_strategy": None,
    "cardinality_estimate": None,
    "continuation_token": None,
    # Phase 11 additions:
    "snapshot_count": len(snaps),
    "snapshots_available": len(snaps),
}
if _resolved_aliases:
    meta["resolved_from_alias"] = _resolved_aliases
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

### Snapshot Chain Walk (verified API)

```python
# Source: graphify/snapshot.py list_snapshots() + load_snapshot()
from graphify.snapshot import list_snapshots, load_snapshot
from pathlib import Path

root = Path(graph_path).parent.parent  # graphify-out/../ = project root
snaps = list_snapshots(root)           # sorted oldest-to-newest by mtime
if len(snaps) < 2:
    # emit insufficient_history
    ...
for path in snaps[-10:]:
    G_snap, communities_snap, meta = load_snapshot(path)
    ts = meta.get("timestamp", path.stem)
    # process, then del G_snap to release memory
    del G_snap
```

### Command File: `/trace` (SLASH-02)

```markdown
---
name: trace
description: Trace how a named entity or concept has evolved across graph snapshots. Use when the user asks about the history, evolution, or changes to a specific concept, module, or entity.
argument-hint: <entity-name>
disable-model-invocation: true
---

The entity to trace is: $ARGUMENTS

Call the graphify MCP tool `entity_trace` with:
- `entity`: "$ARGUMENTS"
- `budget`: 500

Render the result as a narrative timeline:
1. **First seen**: when this entity first appeared in the graph (timestamp + snapshot index)
2. **Community journey**: how its community membership has changed across snapshots
3. **Connectivity trend**: whether its degree (number of connections) grew, shrank, or was stable
4. **Current status**: its staleness state today (FRESH / STALE / GHOST)

If `status` is `no_graph`: "No graph found at graphify-out/graph.json. Run `/graphify` to build one."
If `status` is `insufficient_history`: "Only N snapshot(s) found. Run `/graphify` more times to build history (need at least 2)."
If `status` is `ambiguous_entity`: "Multiple entities match '$ARGUMENTS'. Which did you mean? [list candidates]. Re-invoke with the exact ID."
If `status` is `entity_not_found`: "No entity matching '$ARGUMENTS' found in any snapshot."

End with one thinking-partner follow-up: suggest `/drift` if centrality is trending, or `/emerge` if the entity's community is new.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.claude/commands/*.md` only format | Skills (`.claude/skills/<name>/SKILL.md`) are now primary; `.claude/commands/` still works | Claude Code v2.1 (April 11, 2026) | Phase 11 can use either format; commands/ is simpler for flat file layout; D-15 already specifies commands/ |
| Single-source per-node `source_file: str` | `source_file: str | list[str]` after Phase 10 dedup | Phase 10 (April 2026) | `_iter_sources()` must be used when iterating source files; analyze.py already updated |
| No alias map in MCP server | `_load_dedup_report()` loads alias_map at startup | Phase 10 (April 2026) | New tools must pass `_alias_map` to `_resolve_alias()` — not optional |
| Static GRAPH_TOUR.md | Interactive slash commands | Phase 11 (this phase) | Static artifact was inert; commands provide live graph queries |

**Deprecated/outdated:**
- `token_budget` parameter: deprecated alias for `budget` in `query_graph`. New tools use `budget` only.
- `analyze.graph_diff()`: simpler variant at analyze.py:544. Prefer `delta.compute_delta()` for richer output (community migrations, connectivity changes).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Non-Claude platforms (Codex, OpenCode, Trae, etc.) do not have a native equivalent of `.claude/commands/` slash-command files | Install Path Extension | If they do, Phase 11 could provide native command files per-platform rather than AGENTS.md injection. Low impact: D-15 already says start Claude-Code-first. |
| A2 | 10-snapshot FIFO cap is sufficient for `/drift` trend detection (3+ snapshots = reliable direction) | drift_nodes tool | If users run graphify less than 3 times, `/drift` will always return insufficient_history. Could need documentation guidance. |
| A3 | `context: fork` and subagent execution in command files are NOT needed for Phase 11 commands — they run inline | Command File Format | If Phase 11 commands exceed Claude's inline context capacity (unlikely for short graph summaries), forked execution might be needed. |

**If this table is empty:** All other claims in this research were verified or cited.

---

## Open Questions

1. **`connect_topics` tool vs. two-call composition**
   - What we know: `shortest_path` MCP tool exists; `surprising_connections()` is in analyze.py but not MCP-exposed
   - What's unclear: Is a new `connect_topics` composition tool better than the `/connect` command prompt chaining `shortest_path` + a new minimal `graph_surprises` tool?
   - Recommendation: Planner decides per Claude's Discretion area. Either approach requires at least one new MCP tool (either `connect_topics` or `graph_surprises`). `connect_topics` is cleaner for non-Claude MCP clients.

2. **Snapshot retention cap for `/drift`**
   - What we know: Default cap is 10; D-09 says "N defaults to the configured snapshot retention cap"
   - What's unclear: Is 10 snapshots enough for meaningful trend detection? 3 is the minimum for direction; 5+ is preferable.
   - Recommendation: Keep the 10-snapshot default. Document in the `/drift` command file: "Richer drift insight with more runs." No cap adjustment in Phase 11.

3. **Non-Claude platform command file support**
   - What we know: Only Claude Code has documented `commands/` convention. Other platforms use AGENTS.md sections.
   - What's unclear: Do Codex, OpenCode, or Trae have slash command file support as of April 2026?
   - Recommendation: Proceed with Claude-Code-first. D-16 covers other platforms via the AGENTS.md awareness section. Per D-15, platform variants only materialize on evidence of divergence.

4. **`/ghost` and `/challenge` scope decision**
   - What we know: D-17 says conditional on ~60% budget threshold; CONTEXT deferred section notes possible migration to sibling skill
   - What's unclear: The planning budget estimate is unknown until planner produces PLAN.md for core 5
   - Recommendation: Plan core 5 first. Planner adds stretch items only if estimate confirms capacity.

---

## Environment Availability

Phase 11 is code-only changes to an existing Python package. No external services required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | 3.x (CI: 3.10, 3.12) | — |
| graphify (installed) | Tests | ✓ | current | `pip install -e ".[all]"` |
| mcp (optional dep) | serve.py MCP tests | Conditional | unknown | Tests that need MCP are skipped if `mcp` absent (existing pattern) |
| networkx | All graph ops | ✓ | CI-installed | — |

**Missing dependencies with no fallback:** None — Phase 11 adds no new dependencies.

---

## Validation Architecture

> `nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` or default |
| Quick run command | `pytest tests/test_serve.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SLASH-01 | `graph_summary` tool returns hybrid envelope with god_nodes, top_communities, recent_delta | unit | `pytest tests/test_serve.py::test_graph_summary_ok -x` | ❌ Wave 0 |
| SLASH-01 | `graph_summary` returns `status: no_graph` when graph file absent | unit | `pytest tests/test_serve.py::test_graph_summary_no_graph -x` | ❌ Wave 0 |
| SLASH-02 | `entity_trace` walks snapshot chain and returns timeline | unit | `pytest tests/test_serve.py::test_entity_trace_timeline -x` | ❌ Wave 0 |
| SLASH-02 | `entity_trace` returns `ambiguous_entity` on multiple label matches | unit | `pytest tests/test_serve.py::test_entity_trace_ambiguous -x` | ❌ Wave 0 |
| SLASH-02 | `entity_trace` returns `insufficient_history` with <2 snapshots | unit | `pytest tests/test_serve.py::test_entity_trace_insufficient_history -x` | ❌ Wave 0 |
| SLASH-02 | `entity_trace` honors alias redirect from dedup_report | unit | `pytest tests/test_serve.py::test_entity_trace_alias_redirect -x` | ❌ Wave 0 |
| SLASH-03 | `/connect` composition returns shortest path + surprising connections | unit | `pytest tests/test_serve.py::test_connect_topics_ok -x` | ❌ Wave 0 |
| SLASH-04 | `drift_nodes` returns trend vectors across ≥3 snapshots | unit | `pytest tests/test_serve.py::test_drift_nodes_ok -x` | ❌ Wave 0 |
| SLASH-04 | `drift_nodes` returns `insufficient_history` with <2 snapshots | unit | `pytest tests/test_serve.py::test_drift_nodes_insufficient -x` | ❌ Wave 0 |
| SLASH-05 | `newly_formed_clusters` detects new communities from delta | unit | `pytest tests/test_serve.py::test_newly_formed_clusters_ok -x` | ❌ Wave 0 |
| SLASH-05 | `newly_formed_clusters` returns `no_change` when no new clusters | unit | `pytest tests/test_serve.py::test_newly_formed_clusters_no_change -x` | ❌ Wave 0 |
| D-08 | All new MCP tools emit valid hybrid envelope (SENTINEL present, meta is valid JSON) | unit | `pytest tests/test_serve.py -k "envelope" -x` | ❌ Wave 0 |
| D-09 | All new MCP tools accept `budget` parameter and clamp response | unit | `pytest tests/test_serve.py -k "budget" -x` | ❌ Wave 0 |
| D-07 | All new identifier-accepting tools honor alias redirect | unit | `pytest tests/test_serve.py -k "alias" -x` | ❌ Wave 0 |
| D-13 | `graphify install` copies command files to .claude/commands/ | unit | `pytest tests/test_install.py::test_install_command_files -x` | ❌ Wave 0 |
| D-14 | `graphify install --no-commands` skips command file copying | unit | `pytest tests/test_install.py::test_install_no_commands_flag -x` | ❌ Wave 0 |
| D-15 | Command files exist at graphify/commands/*.md in package | unit | `pytest tests/test_commands.py::test_command_files_packaged -x` | ❌ Wave 0 |
| D-15 | pyproject.toml package-data includes commands/*.md | unit | `pytest tests/test_pyproject.py::test_commands_in_package_data -x` | ❌ Wave 0 |
| D-16 | Skill files mention available slash commands | unit | `pytest tests/test_commands.py::test_skill_files_mention_commands -x` | ❌ Wave 0 |

### Nyquist Signal Minimums

- **Snapshot-dependent tests** (SLASH-02, SLASH-04, SLASH-05): minimum 2 snapshots exercises the `insufficient_history` guard. 3 snapshots exercises trend direction in `/drift`. Fixtures must provide synthetic snapshot chains at these counts.
- **Alias redirect tests:** must run with both a dedup_report.json present and absent (covers `_load_dedup_report()` returning `{}` gracefully).
- **Envelope conformance:** parametrize across all 5 new tools — every tool must emit the SENTINEL and valid JSON meta.

### Sampling Rate

- **Per task commit:** `pytest tests/test_serve.py -q` (fast; covers MCP tool unit tests)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (must exist before implementation)

- [ ] `tests/test_serve.py` — extend with fixtures for new MCP tools (synthetic graph + synthetic snapshot chain of 3 files in `tmp_path`)
- [ ] `tests/test_commands.py` — NEW file: tests for command file format, packaging, skill-file mentions
- [ ] `tests/test_install.py` — extend with `--no-commands` flag test + command-file copy test
- [ ] `tests/test_pyproject.py` — extend with `commands/*.md` in package-data assertion
- [ ] Shared fixture: `_make_snapshot_chain(tmp_path, n=3)` helper in `conftest.py` — creates N synthetic graph snapshots with incremental changes

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | MCP server has no auth (existing design) |
| V3 Session Management | No | MCP server is stateless (existing design) |
| V4 Access Control | No | Path confinement via graphify-out/ (existing) |
| V5 Input Validation | Yes | `sanitize_label()` + `sanitize_label_md()` for all user-supplied strings echoed in responses |
| V6 Cryptography | No | No crypto in Phase 11 |

### Known Threat Patterns for Phase 11

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Entity name injection via `/trace <entity>` | Tampering | `sanitize_label(arguments["entity"])` before echoing; strip control chars, cap at 256 chars |
| Topic injection via `/connect <a> <b>` | Tampering | Same: `sanitize_label(arguments["topic_a"])`, `sanitize_label(arguments["topic_b"])` |
| Belief injection via `/challenge <belief>` (stretch) | Tampering | `sanitize_label(arguments["belief"])` — belief string must not escape JSON context |
| Snapshot path traversal | Elevation | `list_snapshots()` is confined to `graphify-out/snapshots/` via `snapshots_dir()` — do NOT accept user-supplied snapshot paths |
| Continuation token DoS | Denial of Service | Already mitigated by `_CONTINUATION_TOKEN_MAX_BYTES = 65536` in existing token decode (serve.py:~230) |
| Ghost voice injection (stretch) | Spoofing | `/ghost` responses must be clearly labeled as Claude-generated in the user's style, not impersonation |

**THREAT MODEL ENTRIES for PLAN.md:** Each new MCP tool that accepts a free-text identifier must document: (1) what sanitization is applied, (2) what the token-budget cap prevents.

---

## Sources

### Primary (HIGH confidence)

- `graphify/serve.py` (full read) — 13 existing MCP tools, hybrid response envelope, alias resolution, tool registration pattern
- `graphify/analyze.py` (full read) — `god_nodes()`, `surprising_connections()`, `graph_diff()`, `suggest_questions()` exact signatures
- `graphify/snapshot.py` (full read) — `save_snapshot`, `load_snapshot`, `list_snapshots`, `snapshots_dir`, `auto_snapshot_and_delta` exact signatures
- `graphify/delta.py` (full read) — `compute_delta()`, `classify_staleness()`, `render_delta_md()` exact signatures
- `graphify/__main__.py` (full read) — `_PLATFORM_CONFIG`, `install()`, `uninstall()` patterns
- `graphify/security.py` (grep) — `sanitize_label()`, `sanitize_label_md()` signatures
- `.planning/phases/11-narrative-mode-slash-commands/11-CONTEXT.md` (full read) — 19 locked decisions
- `.planning/REQUIREMENTS.md` (full read) — SLASH-01..07 full requirement text
- `.planning/phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md` (partial read) — hybrid envelope D-02 decisions
- `tests/test_serve.py` (head + tail) — existing test patterns, fixture shape, imports
- `tests/test_install.py` (head) — install test pattern
- `pyproject.toml` (grep) — current package-data entry

### Secondary (MEDIUM confidence)

- [Claude Code slash commands documentation](https://code.claude.com/docs/en/slash-commands) (WebFetch April 2026) — slash command format, frontmatter fields, `$ARGUMENTS`, April 2026 skills merge
- WebSearch: "Claude Code slash commands .claude/commands markdown format $ARGUMENTS 2026" — confirmed `.claude/commands/*.md` still works as of v2.1.101 (April 2026)

### Tertiary (LOW confidence)

- Platform-specific command file support for Codex, OpenCode, Trae — no documentation found for `commands/` equivalent; assumed unsupported [A1 in Assumptions Log]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules verified by direct source read
- Architecture patterns: HIGH — based on verified existing handler patterns in serve.py
- Pitfalls: HIGH — most derived from verified code behavior (staleness on historical snapshots, alias map scope)
- Install path non-Claude platforms: LOW — no documentation for platform-specific command formats

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable domain; risk is Claude Code slash-command format changes, but `.claude/commands/` confirmed to still work as of April 2026)
