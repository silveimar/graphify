# Phase 11: Narrative Mode as Slash Commands — Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 17 (new or modified)
**Analogs found:** 17 / 17

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/serve.py` (5 new MCP handlers) | service | request-response | `graphify/serve.py` existing 13 handlers | exact |
| `graphify/commands/context.md` | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/trace.md` | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/connect.md` | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/drift.md` | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/emerge.md` | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/ghost.md` (stretch) | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/commands/challenge.md` (stretch) | command prompt | request-response | `graphify/skill.md` | role-match |
| `graphify/__main__.py` (`_PLATFORM_CONFIG` + `install`) | config + CLI | request-response | `graphify/__main__.py` existing `_PLATFORM_CONFIG` block | exact |
| `pyproject.toml` (package-data) | config | transform | `pyproject.toml` existing package-data entry | exact |
| `graphify/skill.md` + 8 variants (slash-commands discoverability line) | config | transform | existing skill file body | exact |
| `tests/test_serve.py` (extensions) | test | request-response | `tests/test_serve.py` existing test pattern | exact |
| `tests/test_commands.py` (new) | test | transform | `tests/test_install.py` | role-match |
| `tests/test_install.py` (extensions) | test | request-response | `tests/test_install.py` existing pattern | exact |
| `tests/test_pyproject.py` (extensions) | test | transform | `tests/test_pyproject.py` existing pattern | exact |
| `tests/conftest.py` (snapshot chain fixture) | test utility | batch | `tests/test_snapshot.py` `_make_graph()` | role-match |

---

## Pattern Assignments

### `graphify/serve.py` — 5 new MCP tool handlers

**Analog:** `graphify/serve.py` existing handler closures inside `serve()`

This is the primary file Phase 11 modifies. All 5 new handlers follow the exact same closure-inside-`serve()` pattern as the existing 13 handlers. Three concrete patterns are extracted below.

---

#### Pattern A: Handler-in-Closure (simple, no snapshot walk)

**Analog:** `_tool_god_nodes` and `_tool_graph_stats` in `serve.py`

**Core handler pattern** (lines 1282–1316):
```python
def _tool_god_nodes(arguments: dict) -> str:
    _reload_if_stale()
    from .analyze import god_nodes as _god_nodes
    nodes = _god_nodes(G, top_n=int(arguments.get("top_n", 10)))
    lines = ["God nodes (most connected):"]
    lines += [f"  {i}. {n['label']} - {n['edges']} edges" for i, n in enumerate(nodes, 1)]
    return "\n".join(lines)

def _tool_graph_stats(_: dict) -> str:
    _reload_if_stale()
    confs = [d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True)]
    total = len(confs) or 1
    return (
        f"Nodes: {G.number_of_nodes()}\n"
        f"Edges: {G.number_of_edges()}\n"
        f"Communities: {len(communities)}\n"
        f"EXTRACTED: {round(confs.count('EXTRACTED')/total*100)}%\n"
        f"INFERRED: {round(confs.count('INFERRED')/total*100)}%\n"
        f"AMBIGUOUS: {round(confs.count('AMBIGUOUS')/total*100)}%\n"
    )
```

**`graph_summary` tool copies this pattern, adds hybrid envelope.** It calls `_god_nodes(G, top_n)`, extracts communities from `_communities_from_graph(G)`, calls `list_snapshots()` + `compute_delta()` if ≥2 snapshots exist, then emits the D-08 envelope.

---

#### Pattern B: Hybrid Response Envelope (D-08 mandatory for all 5 new tools)

**Analog:** `_run_query_graph` in `serve.py` (lines ~940–980)

**SENTINEL constant** (line ~745):
```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
```

**Envelope emission pattern** (lines ~940–980 in `_run_query_graph`):
```python
text_body = "..."  # Layer 1 summary string
meta = {
    "status": "ok",                  # or "no_graph" | "insufficient_history" | "ambiguous_entity" | "no_data"
    "layer": 1,
    "search_strategy": None,
    "cardinality_estimate": None,
    "continuation_token": None,
    # Phase 11 tool-specific additions (examples):
    "snapshot_count": len(snaps),    # for graph_summary, entity_trace, drift_nodes, newly_formed_clusters
    "snapshots_available": len(snaps),
}
if _resolved_aliases:               # Phase 10 D-07 — alias redirect provenance
    meta["resolved_from_alias"] = _resolved_aliases
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**Phase 11 adds these new `status` values** (Phase 9.2 codes also remain valid):
- `no_graph` — graph.json absent
- `insufficient_history` — fewer than 2 snapshots; add `snapshots_available: N` to meta
- `ambiguous_entity` — label fuzzy-matches multiple nodes; add `candidates: [{id, label, source_file}]`
- `entity_not_found` — label matches no node in any snapshot
- `no_change` — `newly_formed_clusters` diff produced zero new clusters
- `no_data` — tool ran but result set is empty

**`budget` parameter pattern** (lines ~775–785 in `_run_query_graph`):
```python
budget = int(arguments.get("budget", arguments.get("token_budget", 2000)))
budget = max(50, min(budget, 100000))
# ... clamp output:
if len(output) > budget * 3:  # ~3 chars/token approximation
    output = output[:budget * 3] + f"\n... (truncated to ~{budget} token budget)"
```
New tools use `default 500` (not 2000) per D-09.

---

#### Pattern C: Alias Resolution (D-07 mandatory for `entity_trace`)

**Analog:** `_run_query_graph` alias resolution block (lines ~810–845 in `serve.py`)

**The `_resolve_alias` helper pattern:**
```python
_resolved_aliases: dict[str, list[str]] = {}  # {canonical_id: [original_alias, ...]}
_effective_alias_map: dict[str, str] = alias_map or {}  # passed from serve() closure

def _resolve_alias(node_id: str) -> str:
    """Return canonical ID for node_id; record redirect if it occurred."""
    canonical = _effective_alias_map.get(node_id)
    if canonical and canonical != node_id:
        aliases = _resolved_aliases.setdefault(canonical, [])
        if node_id not in aliases:
            aliases.append(node_id)
        return canonical
    return node_id
```

**Note:** `_alias_map` is loaded at `serve()` startup as `_alias_map: dict[str, str] = _load_dedup_report(_out_dir)`. Each new handler that accepts a node identifier must receive `_alias_map` from the closure (it is already in scope inside `serve()`).

---

#### Pattern D: Tool Registration (list_tools + _handlers dict)

**Analog:** The `list_tools()` coroutine and `_handlers` dict (lines ~1054–1430 in `serve.py`)

**Tool declaration pattern** (lines ~1054–1100):
```python
types.Tool(
    name="god_nodes",
    description="Return the most connected nodes - the core abstractions of the knowledge graph.",
    inputSchema={"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}},
),
```

**Handler registration pattern** (lines ~1405–1420):
```python
_handlers = {
    "query_graph":       _tool_query_graph,
    "get_node":          _tool_get_node,
    # ... 11 more ...
    "get_agent_edges":   _tool_get_agent_edges,
    # Phase 11 additions:
    "graph_summary":     _tool_graph_summary,
    "entity_trace":      _tool_entity_trace,
    "connect_topics":    _tool_connect_topics,   # or "graph_surprises" if planner prefers split
    "drift_nodes":       _tool_drift_nodes,
    "newly_formed_clusters": _tool_newly_formed_clusters,
}
```

**`call_tool` dispatcher** (lines ~1422–1430) — unchanged, picks up new entries from `_handlers` automatically:
```python
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

---

#### Pattern E: Snapshot Chain Iteration (for `entity_trace`, `drift_nodes`, `newly_formed_clusters`)

**Analog:** `tests/test_snapshot.py` + verified API from `graphify/snapshot.py`

**The canonical iteration pattern:**
```python
from graphify.snapshot import list_snapshots, load_snapshot
from pathlib import Path

root = Path(graph_path).parent.parent  # graphify-out/../ = project root
snaps = list_snapshots(root)           # sorted oldest-to-newest by mtime

if len(snaps) < 2:
    meta = {
        "status": "insufficient_history",
        "layer": 1,
        "search_strategy": None,
        "cardinality_estimate": None,
        "continuation_token": None,
        "snapshots_available": len(snaps),
    }
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

for path in snaps[-10:]:              # last N snapshots (memory discipline)
    G_snap, communities_snap, meta_snap = load_snapshot(path)
    ts = meta_snap.get("timestamp", path.stem)
    # ... extract only scalar metrics from G_snap ...
    del G_snap                         # CRITICAL: release memory immediately
```

**Memory discipline note** (anti-pattern from RESEARCH.md): Never hold all 10 deserialized `nx.Graph` objects in memory simultaneously. After extracting the scalars you need (community_id, degree), `del G_snap` to release.

**`load_snapshot` return signature** (verified `snapshot.py`):
```python
def load_snapshot(path: Path) -> tuple[nx.Graph, dict[int, list[str]], dict]:
    # Returns (graph, communities_with_int_keys, metadata_dict)
    # metadata keys: "timestamp" (ISO-8601), "node_count", "edge_count"
```

---

#### Pattern F: `_find_node` for entity resolution

**Analog:** `_find_node` at `serve.py` line ~744

```python
def _find_node(G: nx.Graph, label: str) -> list[str]:
    """Return node IDs whose label or ID matches the search term (case-insensitive)."""
    term = label.lower()
    return [nid for nid, d in G.nodes(data=True)
            if term in d.get("label", "").lower() or term == nid.lower()]
```

**`entity_trace` uses this for initial resolution:**
```python
entity = sanitize_label(arguments["entity"])
entity = _resolve_alias(entity)  # alias redirect first
matches = _find_node(G, entity)
if len(matches) > 1:
    candidates = [{"id": m, "label": G.nodes[m].get("label", m),
                   "source_file": G.nodes[m].get("source_file", "")} for m in matches]
    meta = {"status": "ambiguous_entity", "candidates": candidates, ...}
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
if not matches:
    meta = {"status": "entity_not_found", ...}
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
node_id = matches[0]
```

---

### `graphify/commands/context.md` (command prompt, request-response)

**Analog:** `graphify/skill.md` — tone and structure reference

**Slash command file format** (April 2026 Claude Code spec, verified):
```markdown
---
name: context
description: Load a full graph-backed summary of the current knowledge graph — active god nodes, top communities, and recent changes.
argument-hint: (no arguments)
disable-model-invocation: true
---

[prompt body]
```

**Frontmatter fields used by all 5 command files:**
- `name`: matches filename stem
- `description`: used by Claude Code autocomplete and auto-invocation matching
- `argument-hint`: shown during autocomplete — leave empty for `/context`, use `<entity-name>` for `/trace`, `<topic-a> <topic-b>` for `/connect`
- `disable-model-invocation: true`: prevents Claude from auto-triggering the command

**Tone pattern from `graphify/skill.md` (lines 1–60):**

The skill.md voice is direct, practical, and thinking-partner grade. Key phrases: "Turn any folder of files into...", "Three things it does that Claude alone cannot". Commands should match: first-person partner address, concrete actions, one follow-up suggestion per response.

**`no_graph` guard — required in every command prompt body:**
```markdown
If the tool returns `status: no_graph`, render verbatim:
"No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command."
Do not embellish — show this text as-is.
```

**`insufficient_history` guard — required in trace/drift/emerge prompts:**
```markdown
If `status` is `insufficient_history`: "Only N snapshot(s) found (need ≥2). Run `/graphify` more times to build history — snapshots auto-save on each run."
(Substitute N from `meta.snapshots_available`.)
```

**`$ARGUMENTS` usage for parameterized commands:**
```markdown
# In trace.md:
The entity to trace is: $ARGUMENTS

Call the graphify MCP tool `entity_trace` with:
- `entity`: "$ARGUMENTS"
- `budget`: 500

# In connect.md:
Arguments: $ARGUMENTS
Parse: topic_a is the first word or phrase, topic_b is everything after "and" or the second distinct term.

Call the graphify MCP tool `connect_topics` with:
- `topic_a`: [first topic parsed from $ARGUMENTS]
- `topic_b`: [second topic parsed from $ARGUMENTS]
- `budget`: 500
```

---

### `graphify/commands/trace.md` (command prompt, request-response)

**Analog:** `graphify/skill.md` + RESEARCH.md command file example (lines 954–990)

**`$ARGUMENTS` argument-hint:**
```markdown
argument-hint: <entity-name>
```

**Additional status guards beyond `no_graph` / `insufficient_history`:**
```markdown
If `status` is `ambiguous_entity`:
"Multiple entities match '$ARGUMENTS'. Which did you mean?
[list candidates from meta.candidates as a numbered list: ID — label (source_file)]
Re-invoke with the exact ID: `/trace <id>`"

If `status` is `entity_not_found`:
"No entity matching '$ARGUMENTS' found in any snapshot. Try a shorter search term or check spelling."
```

**Narrative rendering instruction:**
```markdown
Render the result as a timeline:
1. **First seen**: timestamp + snapshot number (e.g., "Snapshot 1 of 5, 2026-03-01")
2. **Community journey**: list of (snapshot_ts, community_id) — highlight changes
3. **Connectivity trend**: degree per snapshot — growing / shrinking / stable
4. **Current status**: staleness today (FRESH / STALE / GHOST)

End with one thinking-partner follow-up question. Example: if community changed, suggest `/drift`; if entity just appeared, suggest `/emerge`.
```

---

### `graphify/commands/connect.md` (command prompt, request-response)

**Analog:** `graphify/skill.md`

**Tool call pattern (depends on planner's `connect_topics` vs. two-call decision):**

Option A (single `connect_topics` tool):
```markdown
Call the graphify MCP tool `connect_topics` with:
- `topic_a`: [first topic from $ARGUMENTS]
- `topic_b`: [second topic from $ARGUMENTS]
- `budget`: 500
```

Option B (two existing tool calls):
```markdown
1. Call `shortest_path` with source=[topic_a], target=[topic_b], max_hops=8
2. Call `god_nodes` with top_n=5 to surface globally surprising hubs near these topics
```

**Critical rendering note** (RESEARCH.md Pitfall 4 — do NOT conflate):
```markdown
Render two distinct sections:
**Shortest path** (N hops): [path from shortest_path result]
**Surprising bridges in the graph**: [surprising_connections result — NOT presented as "the path between A and B"]
```

---

### `graphify/commands/drift.md` (command prompt, request-response)

**Analog:** `graphify/skill.md`

**Rendering instruction:**
```markdown
Call the graphify MCP tool `drift_nodes` with:
- `budget`: 500
- `max_snapshots`: 10

Render as narrative, not a table:
- Name the nodes that have drifted most: what communities did they cross?
- Is the drift directional (consistently moving toward/away from X)?
- End with one thinking-partner question: "You've been circling [X] — want to look at [Y]?"

If `insufficient_history`: "[N] snapshot(s) available. Need at least 2. Run `/graphify` more times — drift patterns emerge over multiple sessions."
```

---

### `graphify/commands/emerge.md` (command prompt, request-response)

**Analog:** `graphify/skill.md`

**Tool call:**
```markdown
Call the graphify MCP tool `newly_formed_clusters` with:
- `budget`: 500
```

**Status handling:**
```markdown
If `status` is `no_change`: "No new clusters formed since the last run. The graph structure is stable."
If `status` is `insufficient_history`: "[N] snapshot(s) available. Need at least 2."
```

**Narrative rendering:**
```markdown
For each emerged community: name it by the dominant labels, note how many nodes it contains, name 2-3 representative members.
End with: "These topics weren't a cluster before — want to /trace any of them to see where they came from?"
```

---

### `graphify/__main__.py` — `_PLATFORM_CONFIG` + `install()` extensions

**Analog:** Existing `_PLATFORM_CONFIG` dict and `install()` function (lines 49–156)

**Current `_PLATFORM_CONFIG` entry shape** (lines 49–102):
```python
_PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "skill_file": "skill.md",
        "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
        "claude_md": True,
    },
    "codex": {
        "skill_file": "skill-codex.md",
        "skill_dst": Path(".agents") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    # ... 9 more entries with same shape ...
}
```

**Phase 11 addition — two new optional keys per entry:**
```python
"claude": {
    "skill_file": "skill.md",
    "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
    "claude_md": True,
    # Phase 11:
    "commands_src_dir": "commands",           # relative to graphify/ package dir
    "commands_dst": Path(".claude") / "commands",  # relative to Path.home()
    "commands_enabled": True,                 # False for platforms without commands support
},
```

Non-Claude platforms set `"commands_enabled": False` (no native `commands/` convention).

**`install()` extension pattern** (insert after the existing `shutil.copy` + CLAUDE.md block, lines ~128–155):
```python
# Phase 11: install command files (D-13)
if not no_commands and cfg.get("commands_enabled"):
    _install_commands(cfg, src_dir=Path(__file__).parent / cfg["commands_src_dir"])
```

**New `_install_commands()` helper** (copy from the existing `install()` pattern of `shutil.copy` + mkdir):
```python
def _install_commands(cfg: dict, src_dir: Path) -> None:
    """Copy all command .md files from src_dir to cfg["commands_dst"] under home."""
    dst_dir = Path.home() / cfg["commands_dst"]
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in src_dir.glob("*.md"):
        dst = dst_dir / src.name
        shutil.copy(src, dst)
        print(f"  command installed  ->  {dst}")
```

**`--no-commands` flag** — parse from `sys.argv` in `main()` before routing to `install()`:
```python
# Pattern mirrors how --platform is already parsed in main() (lines ~1600+)
no_commands = "--no-commands" in sys.argv
if no_commands:
    sys.argv.remove("--no-commands")
```

---

### `pyproject.toml` — package-data extension

**Analog:** Existing `package-data` line (line 63):

**Current line:**
```toml
[tool.setuptools.package-data]
graphify = ["skill.md", "skill-codex.md", "skill-opencode.md", "skill-aider.md", "skill-copilot.md", "skill-claw.md", "skill-windows.md", "skill-droid.md", "skill-trae.md", "builtin_templates/*.md"]
```

**Phase 11 addition** — append `"commands/*.md"` to the list:
```toml
graphify = ["skill.md", "skill-codex.md", ..., "builtin_templates/*.md", "commands/*.md"]
```

---

### `graphify/skill.md` + 8 platform variants — discoverability line (D-16)

**Analog:** Each skill file's usage section (lines ~14–45 of `skill.md`)

**Pattern:** Add one short section near the top of each skill file's "Usage" block:

```markdown
## Available slash commands

After `graphify install`, these commands are available in Claude Code:
`/context` `/trace <entity>` `/connect <topic-a> <topic-b>` `/drift` `/emerge`
```

This is a one-liner injection — find the existing "Usage" heading in each skill file and append below it. No platform variants are needed for this line (content is identical; only the Claude Code skill file has the commands native, but other platforms benefit from the mention for documentation purposes).

---

### `tests/test_serve.py` — extension for new MCP tools

**Analog:** Existing test patterns in `tests/test_serve.py`

**Fixture pattern** (lines 35–65 of `test_serve.py`):
```python
def _make_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L10", community=0)
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L5", community=0)
    G.add_node("n3", label="build", source_file="build.py", source_location="L1", community=1)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED")
    G.add_edge("n2", "n3", relation="imports", confidence="EXTRACTED")
    return G
```

**Hybrid envelope assertion pattern** (lines 1143–1157):
```python
def test_response_format_sentinel_splits_cleanly():
    G = _make_graph()
    response = _run_query_graph(G, communities, 1000.0, bf, telemetry, {...})
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2          # exactly one sentinel
    json.loads(parts[1])            # valid JSON meta
```

**New tools follow the same `_run_*` / `_tool_*` split**: extract a pure `_run_graph_summary(G, communities, snaps, arguments)` function that returns a string, so tests can call it without standing up the MCP server — matching how `_run_query_graph` is tested directly.

**Alias redirect test pattern** (lines 1361–1413):
```python
def test_entity_trace_alias_redirect():
    G = nx.Graph()
    G.add_node("authentication_service", label="authentication service",
               file_type="code", community=0, source_file="auth.py", source_location="L1")
    # ... make snapshot chain ...
    alias_map = {"auth": "authentication_service"}
    response = _run_entity_trace(G, snaps, arguments={"entity": "auth"}, alias_map=alias_map)
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "ok"
    assert "resolved_from_alias" in meta
    assert meta["resolved_from_alias"] == {"authentication_service": ["auth"]}
```

**Insufficient history pattern** (based on Phase 9.2 status code tests):
```python
def test_entity_trace_insufficient_history(tmp_path):
    snaps = _make_snapshot_chain(tmp_path, n=1)   # only 1 snapshot
    response = _run_entity_trace(G, snaps, arguments={"entity": "extract"})
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "insufficient_history"
    assert meta["snapshots_available"] == 1
```

---

### `tests/test_commands.py` (new file)

**Analog:** `tests/test_install.py` (lines 1–80)

**File layout to copy:**
```python
"""Tests for graphify commands — file format, packaging, skill-file discoverability."""
from __future__ import annotations
from pathlib import Path
import graphify


def test_command_files_exist_in_package():
    """D-15: all 5 core command files must exist under graphify/commands/."""
    commands_dir = Path(graphify.__file__).parent / "commands"
    for name in ("context", "trace", "connect", "drift", "emerge"):
        assert (commands_dir / f"{name}.md").exists(), f"Missing commands/{name}.md"


def test_skill_files_mention_commands():
    """D-16: skill.md must mention available slash commands."""
    skill = (Path(graphify.__file__).parent / "skill.md").read_text(encoding="utf-8")
    assert "/context" in skill
    assert "/trace" in skill
    assert "/connect" in skill
    assert "/drift" in skill
    assert "/emerge" in skill
```

**Pattern from `test_install.py`** (lines 8–30) for fixture/patch idiom:
```python
def _install(tmp_path, platform, no_commands=False):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform, no_commands=no_commands)
```

---

### `tests/test_install.py` — extensions

**Analog:** Existing `test_install.py` `_install()` + `test_install_*` pattern

**New tests to add:**
```python
def test_install_command_files_claude(tmp_path):
    """D-13: install on claude platform copies command files to .claude/commands/."""
    _install(tmp_path, "claude")
    commands_dir = tmp_path / ".claude" / "commands"
    assert (commands_dir / "context.md").exists()
    assert (commands_dir / "trace.md").exists()

def test_install_no_commands_flag(tmp_path):
    """D-14: --no-commands skips command file copying."""
    _install(tmp_path, "claude", no_commands=True)
    commands_dir = tmp_path / ".claude" / "commands"
    assert not commands_dir.exists() or not any(commands_dir.glob("*.md"))

def test_install_idempotent_commands(tmp_path):
    """D-14: re-running install upgrades command files in place."""
    _install(tmp_path, "claude")
    _install(tmp_path, "claude")   # second run must not raise
    assert (tmp_path / ".claude" / "commands" / "context.md").exists()
```

---

### `tests/test_pyproject.py` — extension

**Analog:** Existing `test_package_data_includes_builtin_templates` (lines ~40–53)

**New assertion to add:**
```python
def test_package_data_includes_commands():
    """D-15: pyproject.toml must include commands/*.md in package-data."""
    data = _load_pyproject()
    package_data = data["tool"]["setuptools"]["package-data"]["graphify"]
    assert "commands/*.md" in package_data, (
        "pyproject.toml package-data is missing 'commands/*.md'. "
        "Phase 11 requires command files to be included in wheel installs. "
        "Add 'commands/*.md' to [tool.setuptools.package-data] graphify list."
    )
```

---

### `tests/conftest.py` — `_make_snapshot_chain` fixture

**Analog:** `tests/test_snapshot.py` `_make_graph()` helper + `conftest.py` `tmp_corpus` fixture

**New shared fixture** (add to `conftest.py`):
```python
@pytest.fixture
def make_snapshot_chain(tmp_path):
    """Factory: create N synthetic graph snapshots with incremental changes.

    Returns a callable `make(n=3) -> list[Path]` of saved snapshot paths,
    oldest-first. Each successive snapshot adds one new node so per-snapshot
    diffs are detectable in entity_trace / drift_nodes / newly_formed_clusters tests.
    """
    from graphify.snapshot import save_snapshot

    def _make(n: int = 3) -> list[Path]:
        paths = []
        for i in range(n):
            G = nx.Graph()
            for j in range(i + 2):           # each snapshot has one more node
                G.add_node(f"n{j}", label=f"node{j}", source_file=f"f{j}.py",
                           source_location=f"L{j}", file_type="code", community=j % 2)
            if i > 0:
                G.add_edge("n0", f"n{i}", relation="calls", confidence="EXTRACTED")
            comms = {k: [n] for k, n in enumerate(G.nodes())}
            p = save_snapshot(G, comms, tmp_path, name=f"snap_{i:02d}")
            paths.append(p)
        return paths

    return _make
```

---

## Shared Patterns

### D-08: Hybrid Response Envelope
**Source:** `graphify/serve.py` lines 742–745 (`QUERY_GRAPH_META_SENTINEL`) + `_run_query_graph` emit block (~lines 960–980)
**Apply to:** All 5 new MCP tools (`graph_summary`, `entity_trace`, `connect_topics`/`graph_surprises`, `drift_nodes`, `newly_formed_clusters`)

```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
# Minimum required meta fields:
meta = {
    "status": "ok",
    "layer": 1,
    "search_strategy": None,
    "cardinality_estimate": None,
    "continuation_token": None,
}
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

### D-07: Alias Redirect (Phase 10 mandatory)
**Source:** `graphify/serve.py` `_resolve_alias` closure + `_resolved_aliases` tracking (~lines 810–845, 960–967)
**Apply to:** `entity_trace` (accepts `entity`), `connect_topics` (accepts `topic_a`, `topic_b`)

```python
if _resolved_aliases:
    meta["resolved_from_alias"] = _resolved_aliases
```

### Input Sanitization
**Source:** `graphify/security.py` `sanitize_label()` (line ~188)
**Apply to:** All new MCP tools that echo user-supplied arguments in response text (`entity_trace`, `connect_topics`, `challenge_belief` stretch)

```python
from graphify.security import sanitize_label
entity = sanitize_label(arguments["entity"])  # strip control chars, cap at 256
```

### `_reload_if_stale()` Guard
**Source:** `graphify/serve.py` `_reload_if_stale()` closure (~lines 1238–1248)
**Apply to:** All 5 new MCP tool handlers (first line of every handler)

```python
def _tool_graph_summary(arguments: dict) -> str:
    _reload_if_stale()   # always first — picks up graph rebuilds
    # ... handler body
```

### No-Graph Short-Circuit
**Source:** Pattern established by `_run_query_graph` continuation_token short-circuit (~lines 830–840)
**Apply to:** All 5 new MCP tools

```python
if not Path(graph_path).exists():
    meta = {
        "status": "no_graph",
        "layer": 1,
        "search_strategy": None,
        "cardinality_estimate": None,
        "continuation_token": None,
    }
    hint = "No graph found at graphify-out/graph.json. Run /graphify to build one."
    return hint + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

---

## No Analog Found

All files have close analogs in the codebase. No file requires pure RESEARCH.md-only patterns.

| File | Reason |
|------|--------|
| `graphify/commands/` directory (new) | No existing analog directory; pattern derived from `graphify/builtin_templates/` (similar: flat .md files packaged via pyproject.toml). The closest copy target for directory creation is `graphify/builtin_templates/`. |

---

## Metadata

**Analog search scope:** `graphify/serve.py`, `graphify/__main__.py`, `graphify/skill.md`, `graphify/security.py`, `graphify/snapshot.py`, `graphify/delta.py`, `tests/test_serve.py`, `tests/test_install.py`, `tests/test_pyproject.py`, `tests/conftest.py`, `pyproject.toml`
**Files scanned:** 11 source files read in full or in targeted sections
**Pattern extraction date:** 2026-04-17

**Key observations:**
1. The handler-in-closure pattern inside `serve()` is perfectly uniform across all 13 existing tools — new handlers are a direct copy-extend.
2. `_run_query_graph` is the single source of truth for the hybrid envelope; all 5 new tools must produce the same shape (identical required meta keys).
3. `_alias_map` is already loaded into the `serve()` closure scope — new handlers access it for free; no new loading needed.
4. `list_snapshots()` returns oldest-first by mtime — no sorting needed in handler code.
5. The `graphify/commands/` directory has no analog in the package (first of its kind), but `graphify/builtin_templates/` establishes the pattern: flat `.md` files registered under `[tool.setuptools.package-data]`.
