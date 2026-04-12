# Architecture Research: v1.1 Context Persistence & Agent Memory

**Domain:** Python CLI library — graph delta analysis, MCP write-back, Obsidian round-trip
**Researched:** 2026-04-12
**Confidence:** HIGH (based on direct codebase reading + external repo analysis)

---

## Problem Statement

v1.0 shipped a pure batch pipeline: each run builds a graph from scratch (or from cache), writes outputs, and exits. No run-over-run awareness, no write-back, no round-trip. Three v1.1 features each require breaking a different statelessness assumption:

| Feature | What Breaks |
|---------|-------------|
| Graph delta / snapshots | The graph has no memory across runs |
| MCP write-back + annotations | MCP server is read-only; no peer identity |
| Obsidian round-trip awareness | Merge engine overwrites user-edited note bodies |

None of these requires restructuring the existing 7-stage pipeline. All three integrate at the pipeline's edges or alongside it, leaving detect → extract → build → cluster → analyze → report → export untouched.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Existing 7-Stage Pipeline (unchanged)                   │
│                                                                                 │
│  detect → extract → build_graph → cluster → analyze → report → export          │
│                                                    │              │             │
│                                               [v1.1 hook]   [v1.1 hook]        │
│                                                    │              │             │
└────────────────────────────────────────────────────┼──────────────┼─────────────┘
                                                     │              │
             ┌───────────────────────────────────────┘              │
             ▼                                                       ▼
┌────────────────────────┐                            ┌──────────────────────────┐
│   snapshot.py (NEW)    │                            │  merge.py (EXTENDED)     │
│                        │                            │                          │
│  save_snapshot()       │                            │  detect_user_edits()     │
│  load_snapshot()       │                            │  (round-trip sentinel    │
│  diff_graphs()         │                            │   block detection)       │
│  staleness_metadata()  │                            └──────────────────────────┘
└────────────────────────┘
             │
             ▼
┌────────────────────────┐         ┌───────────────────────────────────────────────┐
│  delta.py (NEW)        │         │  serve.py (EXTENDED — Phase 7)                │
│                        │         │                                               │
│  build_delta_report()  │         │  annotate_node()     [write tool]            │
│  format_summary_md()   │         │  add_edge()          [write tool]            │
│  format_archive_json() │         │  flag_importance()   [write tool]            │
│                        │         │  propose_vault_note() [write tool]           │
└────────────────────────┘         │  get_session_view()  [read tool, scoped]     │
                                   │                                               │
                                   │  annotations.json ←──── persist across runs  │
                                   └───────────────────────────────────────────────┘

Storage layout (graphify-out/):
  graph.json              — current run graph (unchanged)
  snapshots/
    {timestamp}.json      — frozen graph snapshots
    {timestamp}.meta.json — snapshot metadata (run config, file counts, etc.)
  annotations.json        — all MCP-written annotations (append-only, keyed by node_id)
  GRAPH_DELTA.md          — human-readable delta summary (latest diff only)
  delta/
    {timestamp}-archive.json — full machine-readable delta (search index)
```

---

## Phase 6: Graph Delta Analysis

### New Module: `snapshot.py`

**Responsibility:** Save/load/diff the NetworkX graph as a point-in-time snapshot. Also computes per-node staleness metadata.

**Fits in pipeline:** Called at the end of the `export()` stage (or immediately after `build_graph()` before export). The skill calls it; the CLI gains a `graphify snapshot` subcommand.

**Key functions:**

```python
def save_snapshot(G: nx.Graph, root: Path = Path("."), label: str | None = None) -> Path:
    """Serialize current graph to graphify-out/snapshots/{iso_timestamp}.json.

    Returns path to written file.
    Metadata file {iso_timestamp}.meta.json stores: timestamp, node_count,
    edge_count, label (optional user-provided tag), source_files list.
    """

def load_snapshot(path: Path) -> nx.Graph:
    """Load a snapshot JSON back to nx.Graph via json_graph.node_link_graph."""

def list_snapshots(root: Path = Path(".")) -> list[dict]:
    """Return sorted list of snapshot metadata dicts (newest first)."""

def diff_graphs(G_old: nx.Graph, G_new: nx.Graph) -> dict:
    """Compute graph delta between two graph objects.

    Returns:
    {
        "nodes_added":   [node_dicts ...],
        "nodes_removed": [node_dicts ...],
        "edges_added":   [edge_dicts ...],
        "edges_removed": [edge_dicts ...],
        "community_migrations": [{"node_id", "old_community", "new_community"} ...],
        "connectivity_changes": [{"node_id", "old_degree", "new_degree"} ...],
    }
    """

def attach_staleness_metadata(G: nx.Graph, root: Path = Path(".")) -> nx.Graph:
    """Add extracted_at and source_modified_at to each node in-place.

    extracted_at: timestamp the node's cache entry was written (read from cache.py)
    source_modified_at: Path.stat().st_mtime of the source_file (or None if missing)

    Nodes where source_modified_at > extracted_at are "stale" — source changed
    but node not re-extracted. Mark with stale=True on node attribute.
    """
```

**Storage:** Plain JSON (same format as `graph.json`, using `json_graph.node_link_data`). The `snapshots/` dir is capped at N entries (configurable, default 10) — oldest deleted automatically to prevent unbounded growth.

**Integration with `cache.py`:** `attach_staleness_metadata` reads cache file mtimes from `graphify-out/cache/` to determine `extracted_at`. This is read-only access to existing cache files — no cache behavior change.

### New Module: `delta.py`

**Responsibility:** Render the diff dict from `snapshot.py` into human and machine-readable outputs.

**CPR pattern:** Two-tier output — a short summary (agent context size) and a full archive (search index). Validated by repo-gap-analysis: "summary+archive pattern."

```python
def build_delta_report(diff: dict, G_old: nx.Graph, G_new: nx.Graph) -> dict:
    """Augment raw diff with derived metrics: total changes, % churn, stale node count."""

def format_summary_md(report: dict, snapshot_label: str) -> str:
    """Render GRAPH_DELTA.md content: human-readable, agent-context-sized (~500 words).

    Sections:
    - Run metadata (timestamp, snapshot compared against)
    - Net changes: +N nodes, -N nodes, +N edges, -N edges
    - Top community migrations (up to 10)
    - Stale nodes: files modified since last extraction
    - Key connectivity shifts: nodes whose degree changed by >20%
    """

def format_archive_json(report: dict) -> str:
    """Render full JSON delta archive for graphify-out/delta/{timestamp}-archive.json."""

def write_delta_outputs(report: dict, snapshot_label: str, root: Path = Path(".")) -> None:
    """Write GRAPH_DELTA.md (overwrites) and delta/{timestamp}-archive.json (appends)."""
```

### Integration Point: `export.py` (minimal extension)

The skill calls `snapshot.save_snapshot()` after the main pipeline completes. No changes to the pipeline stages themselves.

For the CLI, `__main__.py` gains a `snapshot` subcommand:

```
graphify snapshot             # take snapshot of current graphify-out/graph.json
graphify snapshot --label "before-refactor"
graphify snapshot --diff      # diff current graph against most recent snapshot
graphify snapshot --list      # show all snapshots
```

The `run` command gains an optional `--snapshot` flag that triggers auto-snapshot after each run.

### Data Flow: Phase 6

```
existing run:
  detect → extract → build → cluster → analyze → report → export
                                                              │
                                   [if --snapshot or skill calls snapshot]
                                                              │
                                              snapshot.attach_staleness_metadata(G)
                                                              │
                                              snapshot.save_snapshot(G, root)
                                                              │
                                        [if previous snapshot exists]
                                                              │
                                              G_old = snapshot.load_snapshot(prev)
                                              diff  = snapshot.diff_graphs(G_old, G)
                                              report = delta.build_delta_report(diff, G_old, G)
                                              delta.write_delta_outputs(report, ...)
                                                              │
                                              graphify-out/GRAPH_DELTA.md
                                              graphify-out/delta/{ts}-archive.json
```

---

## Phase 7: MCP Write-Back & Peer Modeling

### Modified Module: `serve.py`

`serve.py` currently loads the graph once at startup into memory (`G = _load_graph(graph_path)`) and serves read-only tools. For write-back, it needs:

1. A mutable graph state with save-back capability
2. A persistent annotations store (loaded at startup, appended on each write)
3. A peer identity layer on every mutation tool

**Architectural constraint:** The MCP server must not write to `graph.json` directly (that is the pipeline's output). Instead, write-back tools write to `annotations.json`. The graph in memory can be augmented with annotations for query tools, but the pipeline-output graph is never mutated by MCP tools. This preserves the pipeline as ground truth.

**Implementation approach:** Minimal extension to `serve.py`. No new module needed for Phase 7 — the server is already a single-function module. New tool handlers follow the existing `_handlers` dict pattern.

```python
# New state loaded at serve() startup (alongside G):
annotations_path = Path(graph_path).parent / "annotations.json"
annotations: dict = _load_annotations(annotations_path)  # {node_id: [annotation_records]}

# Helpers:
def _load_annotations(path: Path) -> dict:
    """Load annotations.json or return empty dict if not found."""

def _save_annotation(annotations: dict, annotations_path: Path, record: dict) -> None:
    """Append-write a single annotation record to annotations.json.

    Atomic write via tmp file + os.replace (same pattern as cache.py::save_cached).
    """

# New tool: annotate_node
def _tool_annotate_node(arguments: dict) -> str:
    """Write annotation to annotations.json. Never modifies graph.json.

    Record schema (Honcho-inspired peer model):
    {
        "node_id":    str,
        "annotation": str (sanitized),
        "peer_id":    str,   # agent name, session ID, or user-provided identifier
        "session_id": str,   # MCP session identifier or UUID
        "timestamp":  str,   # ISO 8601
        "annotation_type": "note" | "importance" | "question" | "correction"
    }
    """

# New tool: propose_vault_note
def _tool_propose_vault_note(arguments: dict) -> str:
    """Write a proposal record to graphify-out/proposed_notes.json.

    Does NOT write to the vault. Returns a confirmation string.
    The user or skill reads proposed_notes.json and decides whether to apply.

    Record schema (Letta-Obsidian-inspired approval flow):
    {
        "title":       str (sanitized via safe_filename),
        "content":     str (sanitized via sanitize_label on any injected graph labels),
        "folder":      str (profile-driven, validated via validate_vault_path),
        "proposed_by": str (peer_id),
        "proposed_at": str (ISO 8601),
        "status":      "pending" | "approved" | "rejected",
        "source_node_ids": [str]  # which graph nodes the note is based on
    }
    """

# New tool: get_session_view
def _tool_get_session_view(arguments: dict) -> str:
    """Return graph subgraph filtered to nodes relevant to this session.

    Session context: nodes touched by annotations from this peer_id/session_id,
    plus their neighborhoods (depth=1). Enables 'what did I look at last time?'
    """
```

**Annotations persistence:** `annotations.json` is a flat JSON dict, keyed by `node_id`, value is a list of annotation records. New annotations are appended without re-reading the full graph. Size is bounded by number of annotated nodes × average annotations per node — expected to be small (hundreds to low thousands).

**Proposed notes persistence:** `graphify-out/proposed_notes.json` is a list of proposal records. The skill reads this list and surfaces proposals to the user. Status transitions (`pending → approved/rejected`) are written back by the skill, not by the MCP server.

**Session scoping:** The MCP server receives `peer_id` and `session_id` as tool arguments (not from transport headers — MCP stdio doesn't carry session metadata reliably). Callers are responsible for providing consistent identifiers.

### Security: Write-Back Validation

All write-back tool inputs pass through:
- `sanitize_label` on annotation text (strips control chars, HTML-escape)
- `safe_filename` on vault note titles (NFC, 200-char cap)
- `validate_vault_path` on proposed note folder paths (path traversal guard)
- Length caps on all text fields (annotation max 4096 chars, title max 200 chars)

No LLM-generated content is ever written directly without sanitization. This follows the existing `security.py` patterns documented in SECURITY.md.

### Data Flow: Phase 7

```
MCP Client (Claude, agent)
    │
    │  annotate_node({node_id, annotation, peer_id, session_id})
    ▼
serve.py::_tool_annotate_node
    │  sanitize inputs
    │  build record {node_id, annotation, peer_id, session_id, timestamp, type}
    │  _save_annotation(annotations, annotations_path, record)
    ▼
graphify-out/annotations.json  (append-only, survives pipeline re-runs)

MCP Client
    │
    │  propose_vault_note({title, content, folder, peer_id, source_node_ids})
    ▼
serve.py::_tool_propose_vault_note
    │  sanitize + validate all fields
    │  append proposal record with status="pending"
    ▼
graphify-out/proposed_notes.json

Skill (or user CLI command)
    │  reads proposed_notes.json
    │  presents proposals to user
    │  on approval: calls export.to_obsidian() variant or writes note directly
    │  updates status → "approved" | "rejected"
    ▼
Vault .md file (only written after explicit approval)
```

---

## Phase 8: Obsidian Round-Trip Awareness

### Modified Module: `merge.py`

v1.0 `merge.py` already handles CREATE/UPDATE/SKIP/REPLACE/ORPHAN decisions. What it does not do:
- Detect user-edited note bodies (it overwrites body on UPDATE)
- Preserve user-authored content blocks inside the body

v1.1 extends the merge engine with round-trip detection. The extension is additive — new logic branches within `compute_merge_plan`, not a rewrite.

**User-authored content block detection:**

The existing sentinel pattern (`graphify_managed: true` frontmatter field + `<!-- graphify:body -->` block markers, established in v1.0) provides the hook. If markers are present in existing notes, the merge engine knows which content blocks are graphify-owned and which are user-owned.

```python
# New function in merge.py:
def detect_user_edits(existing_content: str, rendered_content: str) -> dict:
    """Compare existing vault note against rendered note to detect user modifications.

    Returns:
    {
        "has_user_edits": bool,
        "user_blocks": [str],     # content blocks outside sentinel markers
        "graphify_blocks": [str], # content blocks inside sentinel markers
        "frontmatter_drift": [str], # fields in existing not in rendered (user-added)
    }
    """

def merge_with_user_blocks(existing_content: str, rendered_content: str, user_blocks: list[str]) -> str:
    """Produce merged note content: rendered graphify sections + preserved user sections.

    User blocks (content outside sentinel markers) are appended after the rendered body,
    with a visual separator. This is a conservative approach — user content is never lost,
    but may be repositioned.
    """
```

**Sentinel block shape** (extends v1.0 pattern):

```markdown
---
graphify_managed: true
...other frontmatter...
---

<!-- graphify:body:start -->
[graphify-generated body content]
<!-- graphify:body:end -->

<!-- user:content:start -->
[user-authored sections preserved here]
<!-- user:content:end -->
```

Notes that lack sentinel markers (pre-v1.1 notes, or notes not managed by graphify) fall through to the existing v1.0 merge behavior unchanged. This is backward compatible.

**New MergeAction types:** Phase 8 adds `UPDATE_PRESERVE_USER_BLOCKS` to the action vocabulary. This is a subtype of UPDATE where user-authored content blocks were detected and preserved. The merge plan summary reports how many notes had user edits preserved.

**Integration with `compute_merge_plan`:**

```
existing flow:
  if file exists:
    parse frontmatter
    apply field policies
    → UPDATE or SKIP_PRESERVE or SKIP_CONFLICT

v1.1 addition (after frontmatter resolution):
    if graphify_managed sentinel present in existing:
        detect_user_edits(existing_content, rendered_content)
        if has_user_edits:
            action = UPDATE_PRESERVE_USER_BLOCKS
            merged_content = merge_with_user_blocks(...)
        else:
            action = UPDATE  (unchanged behavior)
```

### Data Flow: Phase 8

```
graphify --obsidian (re-run)
    │
    ▼
export.to_obsidian()
    │
    ▼
merge.compute_merge_plan(rendered_notes, vault_path, profile)
    │
    for each existing note:
        │  read existing_content
        │  if graphify_managed sentinel present:
        │      detect_user_edits(existing_content, rendered_content)
        │      → has_user_edits? → UPDATE_PRESERVE_USER_BLOCKS
        │      → no user edits? → UPDATE (as before)
        │  else:
        │      → existing v1.0 logic (UPDATE/SKIP/REPLACE)
        ▼
    MergePlan with extended action types
    │
    ▼
merge.apply_merge_plan(plan, ...)
    │  for UPDATE_PRESERVE_USER_BLOCKS:
    │      write merged_content (graphify sections + user blocks appended)
    │  for all others:
    │      existing behavior unchanged
    ▼
Written vault notes with user blocks preserved
```

---

## Module Inventory: New vs. Modified

### New Modules

| Module | Lines (est.) | Responsibility | Phase |
|--------|-------------|----------------|-------|
| `graphify/snapshot.py` | ~200 | Graph snapshot save/load/diff, staleness metadata | 6 |
| `graphify/delta.py` | ~150 | Delta report rendering (summary MD + archive JSON) | 6 |

### Extended Modules

| Module | Change Type | What Changes | Phase |
|--------|------------|--------------|-------|
| `graphify/serve.py` | Add tools + state | 4 new tool handlers, annotation/proposal persistence, session view | 7 |
| `graphify/merge.py` | Add functions | `detect_user_edits()`, `merge_with_user_blocks()`, new action type | 8 |
| `graphify/__main__.py` | Add subcommand | `graphify snapshot [--diff] [--label] [--list]` | 6 |
| `graphify/cache.py` | Read-only access | `snapshot.py` reads cache entry mtimes for staleness — no changes to cache.py | 6 |

### Unchanged Modules (Pipeline Stages)

`detect.py`, `extract.py`, `build.py`, `cluster.py`, `analyze.py`, `report.py`, `export.py` (core pipeline), `profile.py`, `mapping.py`, `templates.py`, `validate.py`, `security.py`

The pipeline stages remain pure functions. v1.1 adds persistence and mutation at the boundaries without touching the pipeline interior.

---

## Build Order: Phases 6 → 7 → 8

Dependencies between phases are one-directional: each phase's outputs are independent of the others.

```
Phase 6: snapshot.py + delta.py
  │  No dependency on Phase 7 or Phase 8
  │  Prerequisite: none beyond existing graph.json output
  │  Delivers: GRAPH_DELTA.md, snapshots/, graphify snapshot CLI
  │
  ▼
Phase 7: serve.py extensions
  │  Can be built in parallel with Phase 6 (no dependency)
  │  Reads annotations.json — file created fresh if not found
  │  Optional: can query snapshot list (Phase 6) for session_view context
  │  Delivers: annotate_node, add_edge, flag_importance, propose_vault_note MCP tools
  │
  ▼
Phase 8: merge.py extensions
     Depends on: Phase 7's propose_vault_note (approval flow writes via export/merge)
     Depends on: existing v1.0 sentinel block shape (already shipped)
     Delivers: round-trip detection, user block preservation
```

**Recommended build order:** 6 → 7 → 8. Phase 8 is most valuable when agents can propose notes (Phase 7) and the vault round-trip correctly preserves what agents write. Phase 6 is independent and can ship first to validate the delta concept before adding write-back complexity.

---

## Component Responsibilities (Consolidated)

| Component | File | Owns | Communicates With |
|-----------|------|------|-------------------|
| SnapshotStore | `snapshot.py` | Snapshot I/O, graph diff, staleness metadata | `cache.py` (read), `export.py` (called after) |
| DeltaRenderer | `delta.py` | GRAPH_DELTA.md + archive JSON | `snapshot.py` (receives diff dict) |
| MCP WriteTools | `serve.py` | annotations.json, proposed_notes.json | `security.py` (sanitize), `merge.py` (proposals → merge) |
| RoundTripDetector | `merge.py` | User edit detection, block-level preservation | `profile.py` (sentinel config), `export.py` (called from) |

---

## Architectural Patterns

### Pattern 1: Append-Only Persistence

`annotations.json` and `proposed_notes.json` are append-only stores. The MCP server appends records without reading the full store; the skill reads the full store when summarizing. This avoids read-modify-write races in a stdio server context.

Implementation: same `tmp → os.replace` atomic write pattern as `cache.py::save_cached`.

### Pattern 2: Sentinel-Block Round-Trip

Sentinel HTML comments (`<!-- graphify:body:start -->`) allow the merge engine to distinguish graphify-owned content from user-authored content without a database lookup. This is the same pattern as v1.0's `graphify_managed` frontmatter field, extended to body blocks.

This pattern is borrowed from static site generators (Jekyll, Hugo front matter) and is robust against Obsidian's file operations (Obsidian preserves unknown HTML comments on save).

### Pattern 3: Proposal Queue (Letta-Obsidian pattern)

MCP tools never write to the vault directly. They write to a proposal queue (`proposed_notes.json`). The skill (or an explicit CLI command) reads the queue and executes approved proposals. This provides human-in-the-loop control without requiring a UI.

The same pattern governs `propose_vault_note`: the agent can express intent to create a note, but the note is only written after the user's explicit approval.

### Pattern 4: Summary + Archive Delta Output (CPR pattern)

GRAPH_DELTA.md is agent-context-sized (~500 words, always overwritten). The `delta/{timestamp}-archive.json` is the full machine-readable diff (searchable, not loaded into agent context). Agents load the summary; tools search the archive. This prevents context pollution from large diff payloads.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mutating `graph.json` from MCP Tools

**What people do:** Write annotations or agent-added edges directly back into `graph.json` so they appear in graph queries.
**Why it's wrong:** `graph.json` is the pipeline's output. The next `graphify` run will overwrite it. Any MCP-written data not in the source files disappears. Also causes race conditions if MCP server is running while a pipeline run executes.
**Do this instead:** Annotate nodes in `annotations.json`. The MCP query tools can merge annotations into their responses at read time without persisting anything to `graph.json`.

### Anti-Pattern 2: Storing Snapshots as Full GraphML or Pickle

**What people do:** Use NetworkX's `write_graphml()` or `pickle.dump()` for snapshots because it's one line.
**Why it's wrong:** GraphML is verbose (10x the JSON size for the same graph). Pickle is non-portable across Python versions and is a security risk if snapshot files are shared. `json_graph.node_link_data` already produces the right format — `graph.json` is already in this format.
**Do this instead:** Serialize snapshots with `json_graph.node_link_data()` (same format as `graph.json`). Diff is done by loading two such files into NetworkX and computing set differences on node/edge IDs.

### Anti-Pattern 3: Running Staleness Detection on Every Query

**What people do:** Compute staleness metadata on every MCP query tool call (checking `Path.stat().st_mtime` for each node's source file).
**Why it's wrong:** For a 5000-node graph where most nodes trace to source files, this is 5000 `stat()` syscalls per query — too slow for interactive use.
**Do this instead:** Compute staleness once at pipeline end (in `snapshot.attach_staleness_metadata`) and store the `stale=True` attribute on nodes in the graph. MCP queries read the precomputed attribute.

### Anti-Pattern 4: Overwriting User Note Body Without Sentinel Check

**What people do:** Apply UPDATE merge action to all existing notes unconditionally (v1.0 behavior).
**Why it's wrong:** Users who author content in graphify-managed notes lose their work on re-run. This destroys trust in the tool.
**Do this instead:** Check for `<!-- graphify:body:start -->` sentinel. If present and user content detected outside it, use `UPDATE_PRESERVE_USER_BLOCKS`. If no sentinel, fall back to v1.0 UPDATE behavior (notes without sentinels were not written by graphify v1.1+ and may be user-authored entirely).

### Anti-Pattern 5: Unbounded Snapshot Accumulation

**What people do:** Write a snapshot on every run without cleanup, because "storage is cheap."
**Why it's wrong:** Large codebases produce 1-5MB graph JSON. At 1 run/day over a year, that's 365-1825MB in `graphify-out/snapshots/`. CI environments with graphify runs accumulate this silently.
**Do this instead:** Cap snapshots at a configurable N (default: 10 most recent). `save_snapshot` deletes the oldest entry when the cap is exceeded. The `--list` command shows what's retained.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `snapshot.py` ↔ `cache.py` | Read-only: snapshot reads cache file mtimes | cache.py unchanged; snapshot checks `graphify-out/cache/` mtime |
| `snapshot.py` ↔ `export.py` | Called after export completes | Not imported — called by skill or CLI driver |
| `serve.py` ↔ `security.py` | All write-back input passes through sanitize_label, safe_filename, validate_vault_path | Existing security.py functions, no changes |
| `serve.py` ↔ `merge.py` | Proposed notes flow: propose → approval → apply_merge_plan variant | Loose coupling via JSON file; no direct import |
| `merge.py` ↔ `profile.py` | Sentinel config (block marker format) read from profile | Profile may configure custom sentinel strings; defaults hardcoded |
| `delta.py` ↔ `snapshot.py` | Receives diff dict; renders to string | Pure function; no I/O of its own except final write |

### External Boundaries

| External | Integration | Notes |
|----------|-------------|-------|
| MCP clients (Claude, agents) | stdio JSON-RPC (unchanged protocol) | New tools registered via `@server.list_tools()` |
| Obsidian vault | File writes via `merge.apply_merge_plan` (unchanged path) | Sentinel markers are plain HTML comments — Obsidian ignores them |
| Pipeline (skill.md) | Skill calls `snapshot.save_snapshot()` via embedded Python block | Follows D-73: CLI is utilities-only; skill drives pipeline |

---

## Scalability Considerations

| Concern | Current | With v1.1 |
|---------|---------|-----------|
| Snapshot storage | None | O(N_snapshots × graph_size_MB); cap at 10 prevents runaway |
| Annotations.json | None | O(annotations × record_size); expected small (<10K records) |
| Staleness scan | None | O(N_nodes) stat() calls at pipeline end — runs once, not per query |
| Diff computation | None | O(N_nodes + N_edges) set operations — fast even at 50K nodes |
| Round-trip detection | O(N_notes) file reads | Adds one regex pass per existing note — negligible |

---

## Sources

- Direct reading of `graphify/serve.py` (read-only MCP server architecture)
- Direct reading of `graphify/merge.py` (MergeAction vocabulary, sentinel pattern)
- Direct reading of `graphify/cache.py` (atomic write pattern, SHA256 file hash)
- Direct reading of `.planning/PROJECT.md` (v1.1 requirements, constraints, Key Decisions)
- Direct reading of `.planning/notes/repo-gap-analysis.md` (Honcho peer model, CPR summary+archive, Letta-Obsidian propose_obsidian_note, Context Constitution staleness-as-first-class)
- Existing v1.0 ARCHITECTURE.md (sentinel block pattern established in Phase 4)

*All findings HIGH confidence — based on direct codebase analysis and validated external repo patterns.*

---
*Architecture research for: graphify v1.1 Context Persistence & Agent Memory (Phases 6-8)*
*Researched: 2026-04-12*
