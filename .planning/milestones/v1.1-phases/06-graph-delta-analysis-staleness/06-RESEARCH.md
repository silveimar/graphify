# Phase 6: Graph Delta Analysis & Staleness - Research

**Researched:** 2026-04-13
**Domain:** Graph snapshot serialization, set-arithmetic diff, staleness metadata, Python stdlib atomic I/O
**Confidence:** HIGH

## Summary

Phase 6 adds two new modules (`snapshot.py`, `delta.py`) and a `graphify snapshot` CLI subcommand. All decisions are locked in CONTEXT.md and the patterns are directly derivable from code already in the codebase. The snapshot format reuses the `node_link_data` serialization already proven in `export.py` and `serve.py`. The diff algorithm is pure set arithmetic on node/edge sets. The staleness system reuses the SHA256 pattern from `cache.py`. The atomic write pattern is the same `os.replace(tmp, target)` pattern from `cache.py::save_cached()`. No new dependencies are required.

The phase is low-risk: all five core mechanisms (serialize, diff, prune, stale-detect, render) are stdlib-only, well-tested in isolation, and are validated live in this session. The only design area left to Claude's discretion is the internal snapshot JSON schema (exact key names), error handling for corrupted/missing snapshots, edge cases in community-renumbering detection, and optional metadata fields beyond the required three.

**Primary recommendation:** Implement `snapshot.py` first (serialization + pruning + metadata), then `delta.py` (diff computation + GRAPH_DELTA.md rendering), then `__main__.py` snapshot subcommand, then wire auto-snapshot into the skill. Extract.py `extracted_at`/`source_hash` injection is a prerequisite for staleness — do it in the same wave as `snapshot.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Snapshots contain graph data (node-link format) + community assignments + metadata (timestamp, node_count, edge_count) — no report or HTML
- **D-02:** Single JSON file per snapshot: `{"graph": ..., "communities": ..., "metadata": {...}}`. Atomic save, easy to compare
- **D-03:** Timestamp-based naming with ISO format (e.g., `2026-04-12T14-30-00.json`). Optional `--name` flag adds a label suffix (e.g., `2026-04-12T14-30-00_before-refactor.json`)
- **D-04:** `GRAPH_DELTA.md` uses summary+archive pattern. Summary section is ~20-40 lines: counts (added/removed/changed nodes/edges), top 5 most significant changes (god node shifts, large community migrations), one-paragraph narrative. Fits agent context window
- **D-05:** Archive section uses markdown tables: Added Nodes, Removed Nodes, Community Migrations, Connectivity Changes. Human-readable, grep-searchable
- **D-06:** Connectivity changes show degree delta + specific edge lists per node (e.g., `transformer: +3 edges (calls: +2, imports: +1), -1 edge (contains: -1)`). Covers DELTA-08
- **D-07:** Default comparison is current run vs most recent snapshot. `--from` and `--to` flags allow comparing any two snapshots
- **D-08:** `extracted_at` (ISO timestamp) and `source_hash` (SHA256 via `cache.py::file_hash()` pattern) are attached in `extract.py` at extraction time — data is born with provenance
- **D-09:** GHOST state detected at delta comparison time: `delta.py` checks if `source_file` still exists on disk. No pipeline changes needed for detection
- **D-10:** Staleness is metadata-only: FRESH/STALE/GHOST are informational attributes on nodes. No pipeline stage changes behavior based on staleness. Agents and delta reports consume it; cluster/analyze/export run unchanged
- **D-11:** Pipeline auto-snapshots after every successful build+cluster. Zero friction — deltas always available. FIFO retention (default cap: 10) keeps disk bounded
- **D-12:** `graphify snapshot` reads existing `graphify-out/graph.json` + communities and saves to `graphify-out/snapshots/`. No pipeline re-run. Matches D-73 (CLI = utility, not pipeline driver)
- **D-13:** Delta auto-generates after auto-snapshot by comparing against previous snapshot. `GRAPH_DELTA.md` is always fresh alongside graph output
- **D-14:** `GRAPH_DELTA.md` written to `graphify-out/GRAPH_DELTA.md` alongside `GRAPH_REPORT.md` — natural discovery in standard output directory

### Claude's Discretion

- Internal snapshot JSON schema details (exact key names, nesting structure)
- Error handling for corrupted/missing snapshots
- Edge cases in community migration tracking (node in same community but community renumbered)
- Snapshot metadata fields beyond the required three (timestamp, node_count, edge_count)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DELTA-01 | User can compare current graph run against previous run and see added/removed/changed nodes and edges in `GRAPH_DELTA.md` | `delta.py` renders diff dict using set arithmetic; GRAPH_DELTA.md written to `graphify-out/` |
| DELTA-02 | Graph snapshots persist to `graphify-out/snapshots/` after each pipeline run with automatic retention (default: keep last 10) | `snapshot.save_snapshot()` uses `cache_dir` pattern + FIFO prune; verified live |
| DELTA-03 | Every extracted node carries `extracted_at` (ISO timestamp) and `source_hash` (SHA256 of source file at extraction time) metadata | Injected in `extract.py` at node creation; `cache.py::file_hash()` reused for hash |
| DELTA-04 | Nodes have three-state staleness: FRESH (hash matches source), STALE (hash mismatch), GHOST (source file deleted/renamed) | SHA256 comparison + `Path.exists()` check in `delta.py`; mtime as fast gate |
| DELTA-05 | `GRAPH_DELTA.md` uses summary+archive pattern: concise summary section (loadable into agent context) plus full structural diff section (searchable but not loaded) | CPR summary+archive pattern; two-tier markdown in `delta.py` |
| DELTA-06 | Community migration is tracked: which nodes moved between communities across runs | Set arithmetic on community membership dicts from two snapshots |
| DELTA-07 | `graphify snapshot` CLI command saves an explicit named snapshot without requiring a full pipeline re-run | New branch in `__main__.py::main()`; reads `graph.json` from disk (same pattern as `--obsidian` command) |
| DELTA-08 | Connectivity change metrics per node (degree delta, new/lost edges) are included in delta output | `G.degree()` comparison between snapshots; edge set diff per node |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `networkx.readwrite.json_graph` | 3.4.2 (installed) | Snapshot serialization/deserialization via `node_link_data` | Already in use by `export.py::to_json()` and `serve.py::_load_graph()`; round-trip fidelity of all node attributes verified |
| `hashlib` (stdlib) | 3.10+ | SHA256 `source_hash` generation | Pattern already in `cache.py::file_hash()` — reuse directly |
| `datetime` (stdlib) | 3.10+ | ISO-8601 `extracted_at` timestamps | `datetime.datetime.now(datetime.timezone.utc).isoformat()` produces correct UTC ISO string |
| `os.replace()` (stdlib) | 3.10+ | Atomic snapshot writes | Already proven in `cache.py::save_cached()` — write to `.tmp`, then `os.replace(tmp, target)` |
| `pathlib.Path` (stdlib) | 3.10+ | Directory management for `graphify-out/snapshots/` | Used throughout codebase; `mkdir(parents=True, exist_ok=True)` is the established pattern |
| `json` (stdlib) | 3.10+ | Snapshot and delta archive serialization | Standard in all pipeline modules |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `os.stat().st_mtime` (stdlib) | 3.10+ | Fast mtime gate before SHA256 comparison | First check in staleness detection; skip full hash if mtime unchanged |
| `re` (stdlib) | 3.10+ | Filename sanitization for `--name` label suffix | Same `re.sub` pattern as `report.py::_safe_community_name()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json_graph.node_link_data` | Custom serialization | Custom would duplicate proven code and risk attribute loss |
| `os.replace()` atomic write | `open(path, 'w')` direct write | Direct write risks corrupt snapshot if process dies mid-write |
| `cache.py::file_hash()` reuse | New SHA256 implementation | New implementation adds divergence risk; existing is tested |

**Installation:** No new packages required. All features are stdlib-only additions on top of networkx (already installed).

**Version verification:**
```
networkx 3.4.2 — VERIFIED via live import in this session [VERIFIED: runtime]
Python 3.10.19 — VERIFIED via live runtime check [VERIFIED: runtime]
```

## Architecture Patterns

### Recommended Project Structure

Two new modules, minimal extension to existing modules:

```
graphify/
├── snapshot.py          # NEW: save/load/prune snapshots; staleness metadata
├── delta.py             # NEW: compute diff dict; render GRAPH_DELTA.md
├── extract.py           # EXTEND: add extracted_at + source_hash to node dicts
├── __main__.py          # EXTEND: add `snapshot` subcommand branch
graphify-out/
├── snapshots/           # Created by snapshot.py
│   ├── 2026-04-13T14-30-00.json
│   └── 2026-04-13T14-30-00_before-refactor.json
├── delta/               # Created by delta.py (archive tier)
│   └── 2026-04-13T14-30-00-archive.json
├── GRAPH_DELTA.md       # Written by delta.py (summary tier)
└── GRAPH_REPORT.md      # Existing — unchanged
```

### Pattern 1: Snapshot Save with Atomic Write + FIFO Prune

**What:** Save graph + communities + metadata to a timestamped JSON file under `graphify-out/snapshots/`. Prune old snapshots on every save to enforce retention cap.

**When to use:** Called by skill after `cluster()` returns (auto-snapshot D-11), and by `graphify snapshot` CLI subcommand (D-12).

**Example:**
```python
# Source: cache.py::save_cached() atomic write pattern [VERIFIED: codebase]
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from networkx.readwrite import json_graph
import networkx as nx


def snapshots_dir(root: Path = Path(".")) -> Path:
    d = Path(root) / "graphify-out" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    name: str | None = None,
    cap: int = 10,
) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    stem = f"{ts}_{name}" if name else ts
    target = snapshots_dir(root) / f"{stem}.json"
    tmp = target.with_suffix(".tmp")

    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)

    payload = {
        "graph": data,
        "communities": {str(k): v for k, v in communities.items()},
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
        },
    }
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, target)

    # FIFO prune — enforce cap on every write
    snaps = sorted(snapshots_dir(root).glob("*.json"), key=lambda p: p.stat().st_mtime)
    for p in snaps[:-cap]:
        p.unlink()

    return target
```

### Pattern 2: Load Snapshot for Diff

**What:** Load a previously saved snapshot back into a graph + communities dict.

**When to use:** In `delta.py` when computing diff between two snapshots.

```python
# Source: serve.py::_load_graph() pattern [VERIFIED: codebase]
def load_snapshot(path: Path) -> tuple[nx.Graph, dict[int, list[str]], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        G = json_graph.node_link_graph(payload["graph"], edges="links")
    except TypeError:
        G = json_graph.node_link_graph(payload["graph"])
    communities = {int(k): v for k, v in payload["communities"].items()}
    metadata = payload.get("metadata", {})
    return G, communities, metadata
```

### Pattern 3: Set Arithmetic Diff

**What:** Compute added/removed/migrated nodes and edges between two graph snapshots.

**When to use:** Core of `delta.py::compute_delta()`.

```python
# Source: Python stdlib set arithmetic [VERIFIED: runtime]
def compute_delta(
    G_old: nx.Graph,
    communities_old: dict[int, list[str]],
    G_new: nx.Graph,
    communities_new: dict[int, list[str]],
) -> dict:
    old_nodes = set(G_old.nodes())
    new_nodes = set(G_new.nodes())
    old_edges = set(G_old.edges())
    new_edges = set(G_new.edges())

    added_nodes = new_nodes - old_nodes
    removed_nodes = old_nodes - new_nodes
    common_nodes = old_nodes & new_nodes

    # Community membership maps: node_id -> community_id
    old_membership = {n: cid for cid, ns in communities_old.items() for n in ns}
    new_membership = {n: cid for cid, ns in communities_new.items() for n in ns}

    migrations = {
        n: (old_membership.get(n), new_membership.get(n))
        for n in common_nodes
        if old_membership.get(n) != new_membership.get(n)
    }

    # Per-node connectivity delta
    connectivity = {}
    for n in common_nodes:
        old_degree = G_old.degree(n)
        new_degree = G_new.degree(n)
        if old_degree != new_degree:
            old_edges_n = set(G_old.edges(n))
            new_edges_n = set(G_new.edges(n))
            connectivity[n] = {
                "degree_delta": new_degree - old_degree,
                "added_edges": list(new_edges_n - old_edges_n),
                "removed_edges": list(old_edges_n - new_edges_n),
            }

    return {
        "added_nodes": list(added_nodes),
        "removed_nodes": list(removed_nodes),
        "community_migrations": migrations,
        "connectivity_changes": connectivity,
        "added_edges": list(new_edges - old_edges),
        "removed_edges": list(old_edges - new_edges),
    }
```

### Pattern 4: Staleness Detection (Three-State)

**What:** Classify each node as FRESH, STALE, or GHOST using mtime as a fast gate and SHA256 as the authoritative signal.

**When to use:** In `delta.py` when building staleness metadata for nodes in the current graph.

```python
# Source: cache.py::file_hash() pattern [VERIFIED: codebase]
import os
from pathlib import Path

def classify_staleness(node_data: dict) -> str:
    source_file = node_data.get("source_file", "")
    stored_hash = node_data.get("source_hash")
    if not source_file or not stored_hash:
        return "FRESH"  # no provenance to check

    p = Path(source_file)
    if not p.exists():
        return "GHOST"

    # Fast mtime gate: if mtime unchanged, skip full hash
    try:
        current_mtime = p.stat().st_mtime
        stored_mtime = node_data.get("source_mtime")
        if stored_mtime is not None and current_mtime == stored_mtime:
            return "FRESH"
    except OSError:
        return "GHOST"

    # Full hash comparison as authoritative signal
    from graphify.cache import file_hash
    current_hash = file_hash(p)
    return "FRESH" if current_hash == stored_hash else "STALE"
```

### Pattern 5: Extracted_at + Source_hash Injection in extract.py

**What:** At node creation time in each language extractor, attach `extracted_at` and `source_hash` to the node dict.

**When to use:** In every language-specific extractor in `extract.py` when building node dicts.

```python
# Source: cache.py::file_hash() and datetime.timezone.utc pattern [VERIFIED: runtime]
from datetime import datetime, timezone
from graphify.cache import file_hash
from pathlib import Path

def _node_provenance(path: str) -> dict:
    """Return extracted_at and source_hash metadata for a source file."""
    p = Path(path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        h = file_hash(p)
        mtime = p.stat().st_mtime
    except OSError:
        h = ""
        mtime = None
    return {"extracted_at": now, "source_hash": h, "source_mtime": mtime}
```

### Pattern 6: CLI Subcommand Branch (snapshot)

**What:** Add `snapshot` as a new command branch in `__main__.py::main()`, following the `--obsidian` pattern of reading `graph.json` from disk without re-running the pipeline.

**When to use:** D-12 — `graphify snapshot` saves current graph.json as a named snapshot.

```python
# Source: __main__.py::main() --obsidian branch pattern [VERIFIED: codebase]
# Lines 813-890 of __main__.py show the exact pattern to follow
if cmd == "snapshot":
    graph_path = "graphify-out/graph.json"
    name = None
    cap = 10
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--graph" and i + 1 < len(args):
            graph_path = args[i + 1]; i += 2
        elif args[i] == "--name" and i + 1 < len(args):
            name = args[i + 1]; i += 2
        elif args[i] == "--cap" and i + 1 < len(args):
            cap = int(args[i + 1]); i += 2
        else:
            print(f"error: unknown snapshot option: {args[i]}", file=sys.stderr)
            sys.exit(2)

    # Load graph.json — reuse the exact --obsidian pattern
    from graphify.snapshot import save_snapshot
    # ... load G + communities from graph_path (identical to --obsidian pattern)
    saved = save_snapshot(G, communities, name=name, cap=cap)
    print(f"snapshot saved: {saved}")
```

### Anti-Patterns to Avoid

- **Direct file write without `os.replace`:** Writing snapshot JSON directly with `open(path, 'w')` risks a partially-written file if the process is killed mid-write. Always write to `.tmp` then `os.replace(tmp, target)`.
- **Pruning only on explicit command:** Pruning must happen inside `save_snapshot()` on every write (D-11 says "FIFO retention keeps disk bounded"). Leaving pruning to a separate optional command means snapshots grow unbounded in practice.
- **Mtime-only staleness:** Using only `os.stat().st_mtime` for staleness misses file renames (same mtime, different content) and clock skew. SHA256 hash is the authoritative signal; mtime is only a fast first gate.
- **Mutating G in-place with staleness flags:** Staleness attributes (FRESH/STALE/GHOST) are computed at diff time, not written back to graph nodes. The pipeline graph is read-only after `export()`. Write staleness into the delta dict, not into G.
- **Community ID equality across runs:** Community IDs are re-indexed by size descending after each run (Leiden seed=42 is deterministic but community _numbering_ depends on run's partition). Two nodes may have the same community ID in different runs but belong to different communities. Compare by membership composition, not by ID.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph serialization | Custom JSON encoder for nx.Graph | `json_graph.node_link_data(G, edges="links")` | Handles all NetworkX edge/node attributes; already tested in export.py |
| Atomic file write | Custom temp-file pattern | `os.replace(tmp, target)` | POSIX-atomic on all major filesystems; existing codebase pattern |
| SHA256 of source file | Custom hash function | `cache.py::file_hash(path)` | Already handles `.md` frontmatter stripping; collision-resistant with path included in hash |
| Directory creation | `os.makedirs()` with checks | `Path.mkdir(parents=True, exist_ok=True)` | Idiomatic; existing pattern in `cache.py::cache_dir()` |
| Filename sanitization for `--name` | Custom regex | `re.sub(r'[^\w-]', '_', name)` or same pattern as `report.py::_safe_community_name()` | Consistent with existing safe-name pattern |

**Key insight:** Every mechanism needed for Phase 6 already exists in the codebase. The task is composition, not invention.

## Common Pitfalls

### Pitfall 1: Community ID Equality Is Not Community Identity
**What goes wrong:** Comparing `node.community == old_node.community` across two snapshot files and concluding "same community, no migration." In reality, community IDs are re-indexed by cluster size on every run. Community 0 in run A and community 0 in run B may be entirely different communities.
**Why it happens:** The `community` attribute on nodes in `graph.json` is an integer from the Leiden partition, re-indexed post-run. There is no stable community identity across runs.
**How to avoid:** Track community membership by node composition: for each node, record which other nodes it was grouped with. A "community migration" is when a node's co-members change, not just when its community ID changes. Alternatively, use the community label (from `community_labels` dict) as a proxy identity if it's stable — but labels are also computed per-run from the hub node's label.
**Warning signs:** Delta reports showing 100% community migration on a run where nothing conceptually changed.

### Pitfall 2: Snapshot Directory Does Not Exist on First Run
**What goes wrong:** `save_snapshot()` fails with `FileNotFoundError` on first pipeline run because `graphify-out/snapshots/` doesn't exist yet.
**Why it happens:** `graphify-out/` is created by the pipeline, but subdirectories are not pre-created.
**How to avoid:** Call `snapshots_dir(root)` at the start of `save_snapshot()` — this function calls `mkdir(parents=True, exist_ok=True)`, which is the established pattern in `cache.py::cache_dir()`. [VERIFIED: codebase]

### Pitfall 3: Delta with No Previous Snapshot
**What goes wrong:** On the very first pipeline run, there is no previous snapshot to diff against. `delta.py` tries to load the "most recent snapshot" and fails or produces garbage output.
**Why it happens:** Auto-snapshot (D-11) + auto-delta (D-13) runs after every pipeline build. On run 1, there is no prior snapshot.
**How to avoid:** Check `len(list(snapshots_dir(root).glob("*.json")))` before computing delta. If fewer than 2 snapshots exist after saving the current one, skip delta generation and write a sentinel `GRAPH_DELTA.md` with "First run — no previous snapshot to compare." This is a valid, user-friendly output.

### Pitfall 4: `source_hash` Mismatch Due to Frontmatter Stripping
**What goes wrong:** A node's `source_hash` was computed when the file had no frontmatter. Later, graphify writes Obsidian vault notes with YAML frontmatter to the same directory. If a node's `source_file` points to an `.md` file that now has frontmatter, `file_hash()` strips the frontmatter before hashing, producing a different hash than the original — falsely triggering STALE.
**Why it happens:** `cache.py::file_hash()` strips YAML frontmatter from `.md` files before hashing (by design, to prevent metadata-only changes from invalidating cache). This is the correct behavior for source `.md` files the user authors, but may produce unexpected behavior if `source_file` ever points to a graphify-generated note.
**How to avoid:** This is correct behavior for user-authored `.md` files — metadata-only changes (tags, status) should not mark a node stale. Document this behavior clearly. Nodes from Python/TS/other code files are not affected.

### Pitfall 5: `--name` Label Creates Invalid Filenames
**What goes wrong:** User runs `graphify snapshot --name "before refactor: auth"` and the colon causes a filesystem error on Windows (colons are reserved in Windows paths).
**Why it happens:** The `--name` label is appended to the ISO timestamp to form the filename. User-supplied strings may contain path-unsafe characters.
**How to avoid:** Sanitize `--name` value using the same pattern as `report.py::_safe_community_name()`: strip characters not in `[a-zA-Z0-9_-]`, replace spaces with hyphens, cap length at 64 chars. [VERIFIED: codebase pattern]

### Pitfall 6: Delta Archive JSON Growing Without Bound
**What goes wrong:** `delta/{timestamp}-archive.json` files accumulate in `graphify-out/delta/` with no pruning. After 100 pipeline runs, the delta archive directory contains 100 files.
**Why it happens:** The snapshot directory has explicit FIFO pruning (D-02 mandates cap: 10). The delta archive directory has no equivalent constraint specified in CONTEXT.md.
**How to avoid:** Apply the same FIFO pruning logic to `graphify-out/delta/` archive files as is applied to snapshots. Cap at the same default (10). This is a Claude's Discretion area — implement proactively.

### Pitfall 7: `node_link_data` kwargs Compatibility
**What goes wrong:** `json_graph.node_link_data(G, edges="links")` raises `TypeError` on older NetworkX versions that don't support the `edges` kwarg.
**Why it happens:** The `edges` parameter was added in NetworkX 3.x. The codebase runs on Python 3.10 which may have an older NetworkX installed in some environments.
**How to avoid:** Use the same try/except pattern already in `export.py::to_json()` and `serve.py::_load_graph()`:
```python
try:
    data = json_graph.node_link_data(G, edges="links")
except TypeError:
    data = json_graph.node_link_data(G)
```
[VERIFIED: codebase — this exact pattern is in export.py lines 290-292]

## Code Examples

### Injecting provenance metadata in extract.py node dicts
```python
# Source: cache.py::file_hash() and datetime stdlib [VERIFIED: runtime]
from datetime import datetime, timezone
from graphify.cache import file_hash
from pathlib import Path

# In each language extractor, when building a node dict:
p = Path(source_file)
now_iso = datetime.now(timezone.utc).isoformat()
try:
    node_hash = file_hash(p)
    node_mtime = p.stat().st_mtime
except OSError:
    node_hash = ""
    node_mtime = None

node = {
    "id": node_id,
    "label": label,
    "source_file": str(p),
    "source_location": source_location,
    "file_type": file_type,
    "extracted_at": now_iso,
    "source_hash": node_hash,
    "source_mtime": node_mtime,
}
```

### Loading two snapshots and computing a diff
```python
# Source: Python stdlib set arithmetic [VERIFIED: runtime]
snaps = sorted(snapshots_dir(root).glob("*.json"), key=lambda p: p.stat().st_mtime)
if len(snaps) < 2:
    return None  # not enough snapshots to diff

G_old, comms_old, meta_old = load_snapshot(snaps[-2])
G_new, comms_new, meta_new = load_snapshot(snaps[-1])

delta = compute_delta(G_old, comms_old, G_new, comms_new)
```

### Rendering the summary tier of GRAPH_DELTA.md
```python
# Source: report.py::generate() rendering pattern [VERIFIED: codebase]
def render_delta_summary(delta: dict, meta_old: dict, meta_new: dict) -> str:
    lines = [
        "# Graph Delta",
        "",
        f"**From:** {meta_old.get('timestamp', 'unknown')}  "
        f"**To:** {meta_new.get('timestamp', 'now')}",
        "",
        "## Summary",
        f"- Nodes: +{len(delta['added_nodes'])} added, "
        f"-{len(delta['removed_nodes'])} removed",
        f"- Edges: +{len(delta['added_edges'])} added, "
        f"-{len(delta['removed_edges'])} removed",
        f"- Community migrations: {len(delta['community_migrations'])} nodes moved",
        f"- Connectivity changes: {len(delta['connectivity_changes'])} nodes affected",
        "",
        "## Top Changes",
        # ... top 5 by degree delta magnitude
    ]
    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No snapshot persistence | FIFO-pruned JSON snapshots in `graphify-out/snapshots/` | Phase 6 (this phase) | Users can compare graph evolution over time |
| No node provenance | `extracted_at` + `source_hash` + `source_mtime` on every node | Phase 6 (this phase) | Agents can judge data freshness without re-running extraction |
| Full GRAPH_REPORT.md loaded into context | Summary+archive split: ~40-line summary + full machine-readable archive | Phase 6 (this phase) | Agent context window stays bounded regardless of graph size |

**Not deprecated by this phase:** `GRAPH_REPORT.md` continues to be written unchanged. `GRAPH_DELTA.md` is additive alongside it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `source_mtime` stored as `float` (os.stat().st_mtime return type) will survive JSON serialization round-trip without precision loss | Code Examples | mtime comparison for fast gate would fail; fall back to hash-only comparison |

All other claims in this research were verified or cited — only A1 requires confirmation at implementation time.

## Open Questions

1. **Community migration: renumbering vs actual migration**
   - What we know: Community IDs are not stable across runs; membership composition is the only reliable identity
   - What's unclear: Whether the planner should define a "community identity" heuristic (e.g., largest common node set) to group migrations by (old_label, new_label) pair, or report them as raw node-level community changes
   - Recommendation: For DELTA-06, report per-node migration as `node: community_id A -> community_id B`. Grouping by label pairs is a "should have" enhancement (listed in research SUMMARY.md). Do not block DELTA-06 on it.

2. **Where exactly in extract.py to inject `extracted_at`/`source_hash`**
   - What we know: Each language extractor builds node dicts independently; there are 16+ language extractors in extract.py
   - What's unclear: Whether injection should happen at a central point (e.g., in the `extract()` dispatcher after all extractors return) or per-extractor
   - Recommendation: Inject at the dispatcher level in `extract()` after extraction returns, rather than in each individual language extractor. This avoids 16 repetitive changes and ensures all extractors — including future ones — automatically get provenance metadata.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.10.19 | — |
| networkx | Snapshot serialization | ✓ | 3.4.2 | — |
| hashlib (stdlib) | source_hash | ✓ | stdlib | — |
| datetime (stdlib) | extracted_at | ✓ | stdlib | — |
| os.replace (stdlib) | Atomic writes | ✓ | stdlib | — |
| pathlib (stdlib) | Directory management | ✓ | stdlib | — |

No missing dependencies. Phase 6 is purely stdlib + already-installed networkx.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (uses default discovery) |
| Quick run command | `pytest tests/test_snapshot.py tests/test_delta.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DELTA-01 | `compute_delta()` produces added/removed/changed node/edge sets | unit | `pytest tests/test_delta.py::test_compute_delta_added_removed -x` | ❌ Wave 0 |
| DELTA-01 | `GRAPH_DELTA.md` written to `graphify-out/GRAPH_DELTA.md` | unit | `pytest tests/test_delta.py::test_render_delta_creates_file -x` | ❌ Wave 0 |
| DELTA-02 | `save_snapshot()` writes JSON to `graphify-out/snapshots/` | unit | `pytest tests/test_snapshot.py::test_save_snapshot_creates_file -x` | ❌ Wave 0 |
| DELTA-02 | FIFO pruning: write 15 snapshots, assert only 10 remain | unit | `pytest tests/test_snapshot.py::test_fifo_pruning -x` | ❌ Wave 0 |
| DELTA-03 | Extracted nodes carry `extracted_at` and `source_hash` | unit | `pytest tests/test_snapshot.py::test_node_provenance_fields -x` | ❌ Wave 0 |
| DELTA-04 | FRESH/STALE/GHOST classification | unit | `pytest tests/test_snapshot.py::test_staleness_classification -x` | ❌ Wave 0 |
| DELTA-05 | Summary section is ≤40 lines; archive section present | unit | `pytest tests/test_delta.py::test_summary_line_count -x` | ❌ Wave 0 |
| DELTA-06 | Community migrations detected when node moves between communities | unit | `pytest tests/test_delta.py::test_community_migration_detection -x` | ❌ Wave 0 |
| DELTA-07 | `graphify snapshot` CLI saves snapshot without re-running pipeline | unit | `pytest tests/test_main_cli.py::test_snapshot_cli_command -x` | ❌ Wave 0 (new test in existing file) |
| DELTA-08 | Connectivity delta shows degree change + added/removed edge lists | unit | `pytest tests/test_delta.py::test_connectivity_changes -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_snapshot.py tests/test_delta.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_snapshot.py` — covers DELTA-02, DELTA-03, DELTA-04
- [ ] `tests/test_delta.py` — covers DELTA-01, DELTA-05, DELTA-06, DELTA-08
- [ ] DELTA-07 test added to existing `tests/test_main_cli.py`

No framework install needed — pytest already in CI.

## Security Domain

> `security_enforcement` not set to false in config.json — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `--name` label sanitization via `re.sub`; snapshot path confined to `graphify-out/` |
| V6 Cryptography | no | SHA256 used for integrity/identity, not confidentiality — no key management needed |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--name` flag | Tampering | Sanitize `--name` with `re.sub(r'[^\w-]', '_', name)` before appending to filename; cap at 64 chars |
| Path traversal via `--graph` flag | Tampering | Resolve and confine to expected path (same pattern as `--obsidian` command validation in `__main__.py`) |
| Snapshot JSON injection via node labels | Tampering | Node labels pass through `sanitize_label()` from `security.py` at extraction time; snapshot inherits safe labels |
| Snapshot directory escape | Elevation of Privilege | Use `Path.resolve()` and verify path stays inside `graphify-out/snapshots/` before writing |

## Sources

### Primary (HIGH confidence)

- `graphify/cache.py` — SHA256 `file_hash()`, `os.replace()` atomic write, `cache_dir()` pattern [VERIFIED: codebase read]
- `graphify/export.py` lines 287-301 — `to_json()` uses `json_graph.node_link_data(G, edges="links")` with TypeError fallback [VERIFIED: codebase read]
- `graphify/serve.py` lines 11-26 — `_load_graph()` uses `json_graph.node_link_graph(data, edges="links")` with TypeError fallback [VERIFIED: codebase read]
- `graphify/__main__.py` lines 813-890 — `--obsidian` subcommand as template for `snapshot` subcommand pattern [VERIFIED: codebase read]
- `graphify/report.py` lines 1-176 — markdown rendering pattern for two-tier output [VERIFIED: codebase read]
- Live Python 3.10.19 runtime — `node_link_data` round-trip, set arithmetic, atomic write, FIFO prune all verified [VERIFIED: runtime]
- `.planning/phases/06-graph-delta-analysis-staleness/06-CONTEXT.md` — locked decisions D-01 through D-14 [VERIFIED: file read]
- `.planning/research/SUMMARY.md` — architecture notes, pitfalls, benchmarks [VERIFIED: file read]

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — DELTA-01 through DELTA-08 acceptance criteria [VERIFIED: file read]
- `.planning/STATE.md` — carry-forward decisions D-73, D-74 [VERIFIED: file read]

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via live runtime; no new dependencies
- Architecture: HIGH — patterns directly derived from existing codebase modules
- Pitfalls: HIGH — grounded in actual codebase code paths with specific line references
- Test map: HIGH — one test file per module follows established project convention

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable stdlib patterns; networkx 3.4.x API is stable)
