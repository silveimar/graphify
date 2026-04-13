# Phase 6: Graph Delta Analysis & Staleness - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can see how their knowledge graph changed between runs and know how fresh each node is. This phase adds two new modules (`snapshot.py`, `delta.py`), extends `extract.py` with provenance metadata, extends the skill/pipeline with auto-snapshot + auto-delta, and adds a `graphify snapshot` CLI utility. No changes to existing pipeline behavior — purely additive.

</domain>

<decisions>
## Implementation Decisions

### Snapshot Format & Storage
- **D-01:** Snapshots contain graph data (node-link format) + community assignments + metadata (timestamp, node_count, edge_count) — no report or HTML
- **D-02:** Single JSON file per snapshot: `{"graph": ..., "communities": ..., "metadata": {...}}`. Atomic save, easy to compare
- **D-03:** Timestamp-based naming with ISO format (e.g., `2026-04-12T14-30-00.json`). Optional `--name` flag adds a label suffix (e.g., `2026-04-12T14-30-00_before-refactor.json`)

### Delta Output Design
- **D-04:** `GRAPH_DELTA.md` uses summary+archive pattern. Summary section is ~20-40 lines: counts (added/removed/changed nodes/edges), top 5 most significant changes (god node shifts, large community migrations), one-paragraph narrative. Fits agent context window
- **D-05:** Archive section uses markdown tables: Added Nodes, Removed Nodes, Community Migrations, Connectivity Changes. Human-readable, grep-searchable
- **D-06:** Connectivity changes show degree delta + specific edge lists per node (e.g., `transformer: +3 edges (calls: +2, imports: +1), -1 edge (contains: -1)`). Covers DELTA-08
- **D-07:** Default comparison is current run vs most recent snapshot. `--from` and `--to` flags allow comparing any two snapshots

### Staleness Integration
- **D-08:** `extracted_at` (ISO timestamp) and `source_hash` (SHA256 via `cache.py::file_hash()` pattern) are attached in `extract.py` at extraction time — data is born with provenance
- **D-09:** GHOST state detected at delta comparison time: `delta.py` checks if `source_file` still exists on disk. No pipeline changes needed for detection
- **D-10:** Staleness is metadata-only: FRESH/STALE/GHOST are informational attributes on nodes. No pipeline stage changes behavior based on staleness. Agents and delta reports consume it; cluster/analyze/export run unchanged

### CLI & Invocation
- **D-11:** Pipeline auto-snapshots after every successful build+cluster. Zero friction — deltas always available. FIFO retention (default cap: 10) keeps disk bounded
- **D-12:** `graphify snapshot` reads existing `graphify-out/graph.json` + communities and saves to `graphify-out/snapshots/`. No pipeline re-run. Matches D-73 (CLI = utility, not pipeline driver)
- **D-13:** Delta auto-generates after auto-snapshot by comparing against previous snapshot. `GRAPH_DELTA.md` is always fresh alongside graph output
- **D-14:** `GRAPH_DELTA.md` written to `graphify-out/GRAPH_DELTA.md` alongside `GRAPH_REPORT.md` — natural discovery in standard output directory

### Claude's Discretion
- Internal snapshot JSON schema details (exact key names, nesting structure)
- Error handling for corrupted/missing snapshots
- Edge cases in community migration tracking (node in same community but community renumbered)
- Snapshot metadata fields beyond the required three (timestamp, node_count, edge_count)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Patterns
- `graphify/cache.py` — SHA256 `file_hash()` implementation to reuse for `source_hash` metadata
- `graphify/build.py` — Graph construction from extraction dicts; understand node deduplication layers
- `graphify/export.py` lines 287-301 — `to_json()` writes `graph.json` via `json_graph.node_link_data()`; snapshot format must capture this same data
- `graphify/__main__.py` line 722+ — CLI `main()` uses manual `sys.argv` parsing; new `snapshot` command follows this pattern

### Research & Context
- `.planning/research/SUMMARY.md` — v1.1 research synthesis with Phase 6 architecture notes (~200 LOC `snapshot.py`, ~150 LOC `delta.py`)
- `.planning/notes/april-research-gap-analysis.md` — Gap analysis informing delta/staleness requirements
- `.planning/notes/repo-gap-analysis.md` — CPR summary+archive pattern reference (EliaAlberti/cpr)

### Requirements
- `.planning/REQUIREMENTS.md` — DELTA-01 through DELTA-08 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cache.py::file_hash(path)` — SHA256 of file contents + resolved path. Directly reusable for `source_hash` node metadata. Already handles markdown frontmatter stripping
- `cache.py::cache_dir(root)` — Pattern for creating `graphify-out/` subdirectories with `mkdir(parents=True, exist_ok=True)`
- `export.py::to_json()` — Uses `json_graph.node_link_data(G)` to serialize NetworkX graph. Snapshot format should capture this same serialization
- `validate.py::validate_extraction()` — Schema enforcement pattern; could inform snapshot validation

### Established Patterns
- Atomic file writes via `os.replace(tmp, target)` in `cache.py::save_cached()` — use same pattern for snapshot saves
- `graphify-out/` as standard output directory (in `.gitignore`, created at runtime)
- Manual `sys.argv` parsing in `__main__.py` (no argparse) — new subcommands follow this style
- Node dicts carry attributes as flat keys (`id`, `label`, `file_type`, `source_file`, `source_location`) — `extracted_at` and `source_hash` extend this pattern naturally

### Integration Points
- **Pipeline integration:** Auto-snapshot hooks into skill.md's pipeline orchestration, after `cluster()` returns and before `analyze()`. The skill calls `snapshot.save_snapshot()` with the graph and communities
- **CLI integration:** `graphify snapshot` added as a new command branch in `__main__.py::main()`
- **Extract integration:** Each language extractor in `extract.py` adds `extracted_at` and `source_hash` to node dicts at creation time

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-graph-delta-analysis-staleness*
*Context gathered: 2026-04-12*
