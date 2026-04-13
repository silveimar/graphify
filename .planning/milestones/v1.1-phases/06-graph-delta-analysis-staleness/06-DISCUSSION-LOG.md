# Phase 6: Graph Delta Analysis & Staleness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 06-graph-delta-analysis-staleness
**Areas discussed:** Snapshot format & storage, Delta output design, Staleness integration, CLI & invocation

---

## Snapshot format & storage

| Option | Description | Selected |
|--------|-------------|----------|
| Graph + communities | Save graph.json (node-link data) plus community assignments. Lean and fast — ~1 file per snapshot. | ✓ |
| Graph + communities + report | Also include GRAPH_REPORT.md snapshot. Doubles storage per snapshot. | |
| Full pipeline output | Mirror everything in graphify-out/. 5-10x storage cost per snapshot. | |

**User's choice:** Graph + communities
**Notes:** Recommended option — contains everything delta.py needs to compute diffs.

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp-based | Auto-generated ISO timestamps. Optional --name label suffix. | ✓ |
| Sequential numbering | run-001, run-002, etc. Loses timing info. | |
| User-provided only | Always require a name. Adds friction for automated use. | |

**User's choice:** Timestamp-based
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Single file | One snapshot.json with graph + communities + metadata. Simpler, atomic save. | ✓ |
| Separate files | graph.json + communities.json per snapshot directory. More files to manage. | |

**User's choice:** Single file
**Notes:** None

---

## Delta output design

| Option | Description | Selected |
|--------|-------------|----------|
| Stats + highlights | Counts, top 5 significant changes, one-paragraph narrative. ~20-40 lines. | ✓ |
| Counts only | Pure numbers. Ultra-compact (~10 lines). | |
| Full itemized | List every change. Could be 200+ lines. | |

**User's choice:** Stats + highlights
**Notes:** Fits agent context window while preserving "what matters" signal.

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown tables | Human-readable tables for Added/Removed/Migrated/Connectivity. Searchable. | ✓ |
| Embedded JSON block | Raw JSON diff in fenced code block. Machine-parseable. | |
| Both | Markdown tables + collapsed JSON block. | |

**User's choice:** Markdown tables
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Degree delta + edge lists | Show degree change and list specific new/lost edges by relation type. | ✓ |
| Degree delta only | Just net degree change per node. | |
| You decide | Claude picks the right level of detail. | |

**User's choice:** Degree delta + edge lists
**Notes:** Covers DELTA-08 requirement.

| Option | Description | Selected |
|--------|-------------|----------|
| Latest by default, --from/--to for custom | Default: current vs most recent. Optional flags for any two snapshots. | ✓ |
| Always prompt for selection | Show available snapshots and ask which two. | |
| Latest only | Always compare against single most recent. No older comparisons. | |

**User's choice:** Latest by default, --from/--to for custom
**Notes:** Covers common case with zero friction.

---

## Staleness integration

| Option | Description | Selected |
|--------|-------------|----------|
| In extract.py at extraction time | Each extractor adds extracted_at and source_hash. Reuses cache.py file_hash(). | ✓ |
| In build.py at graph construction | build_from_json() stamps metadata. Extraction dicts lack provenance. | |
| In snapshot.py at snapshot time | Only stamp when saving. Nodes lack metadata between snapshots. | |

**User's choice:** In extract.py at extraction time
**Notes:** Data is born with provenance. Reuses existing file_hash() pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| At delta comparison time | delta.py checks if source_file exists on disk when comparing. | ✓ |
| At pipeline start | detect.py scans for missing files before extraction. | |
| You decide | Claude picks based on module boundaries. | |

**User's choice:** At delta comparison time
**Notes:** No pipeline changes needed — detection happens on demand.

| Option | Description | Selected |
|--------|-------------|----------|
| Metadata-only | FRESH/STALE/GHOST are informational. No pipeline behavior changes. | ✓ |
| Soft influence | Staleness affects confidence scores and analysis rankings. | |
| Filter option | --exclude-stale flag to filter stale nodes from analysis/export. | |

**User's choice:** Metadata-only
**Notes:** Agents and delta reports consume staleness; pipeline stages run unchanged.

---

## CLI & invocation

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-snapshot every run | Pipeline saves snapshot after every build+cluster. FIFO cap: 10. | ✓ |
| Explicit only | User must run graphify snapshot manually. | |
| Opt-in via flag | --snapshot flag, off by default. | |

**User's choice:** Auto-snapshot every run
**Notes:** Zero friction, deltas always available.

| Option | Description | Selected |
|--------|-------------|----------|
| Read existing graph.json | graphify snapshot reads last run output. No re-run. Matches D-73. | ✓ |
| Trigger fresh pipeline run | Runs full pipeline then saves. Violates D-73. | |
| You decide | Claude picks based on CLI patterns. | |

**User's choice:** Read existing graph.json
**Notes:** Matches D-73 (CLI = utility, not pipeline driver).

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generate after auto-snapshot | Delta auto-generates by comparing against previous snapshot. Always fresh. | ✓ |
| Separate graphify delta command | Manual CLI command for delta generation. | |
| Both | Auto-generate + graphify delta --from/--to for custom. | |

**User's choice:** Auto-generate after auto-snapshot
**Notes:** GRAPH_DELTA.md is always fresh alongside graph output.

| Option | Description | Selected |
|--------|-------------|----------|
| graphify-out/GRAPH_DELTA.md | Alongside GRAPH_REPORT.md. Natural discovery. | ✓ |
| graphify-out/snapshots/GRAPH_DELTA.md | Inside snapshots directory. Less discoverable. | |
| You decide | Claude picks based on output patterns. | |

**User's choice:** graphify-out/GRAPH_DELTA.md
**Notes:** None

---

## Claude's Discretion

- Internal snapshot JSON schema details
- Error handling for corrupted/missing snapshots
- Edge cases in community migration tracking
- Snapshot metadata fields beyond required three

## Deferred Ideas

None — discussion stayed within phase scope
