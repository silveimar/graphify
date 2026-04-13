---
phase: 06-graph-delta-analysis-staleness
plan: 01
subsystem: graph-persistence
tags: [snapshot, json, networkx, provenance, sha256, atomic-write]

# Dependency graph
requires: []
provides:
  - "save_snapshot / load_snapshot / list_snapshots / snapshots_dir in graphify/snapshot.py"
  - "Per-node provenance metadata (extracted_at, source_hash, source_mtime) in _extract_generic"
affects: [06-02-delta-computation, 06-03-cli-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Atomic write via tmp+os.replace for snapshot persistence", "FIFO retention pruning on every save", "node_link_data/node_link_graph for graph serialization"]

key-files:
  created: [graphify/snapshot.py, tests/test_snapshot.py]
  modified: [graphify/extract.py, graphify/__init__.py]

key-decisions:
  - "Provenance computed once per file in _extract_generic, not per node — avoids repeated hashing"
  - "Snapshot name sanitized with re.sub(r'[^\\w-]', '_', name)[:64] — prevents path traversal (T-06-03)"
  - "Community keys stored as strings in JSON, restored to int on load — JSON key constraint"

patterns-established:
  - "Snapshot persistence: graphify-out/snapshots/{timestamp}[_name].json with atomic write"
  - "Provenance injection: extracted_at + source_hash + source_mtime on every code node"

requirements-completed: [DELTA-02, DELTA-03]

# Metrics
duration: 3min
completed: 2026-04-13
---

# Phase 06 Plan 01: Snapshot Persistence & Provenance Summary

**Graph snapshot module with atomic save/load/prune/list and per-node provenance metadata (extracted_at, source_hash, source_mtime) injected into _extract_generic**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-13T01:06:48Z
- **Completed:** 2026-04-13T01:10:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created graphify/snapshot.py with save_snapshot, load_snapshot, snapshots_dir, list_snapshots
- Atomic writes via tmp+os.replace prevent partial snapshots on crash (T-06-01)
- FIFO pruning enforced on every save (default cap=10, T-06-04)
- Snapshot name sanitization prevents path traversal (T-06-03)
- Round-trip fidelity: save then load produces equivalent graph and communities
- Every node from _extract_generic now carries extracted_at, source_hash, source_mtime
- Lazy-load entries added to graphify/__init__.py for save_snapshot, load_snapshot, list_snapshots, snapshots_dir

## Task Commits

Each task was committed atomically:

1. **Task 1: Create snapshot.py module with save/load/prune/list** - `0941933` (feat)
2. **Task 2: Inject extracted_at and source_hash provenance into extract.py** - `9ca8f3b` (feat)

## Files Created/Modified
- `graphify/snapshot.py` - Graph snapshot persistence: save, load, prune, list
- `tests/test_snapshot.py` - 16 tests covering snapshot + provenance behaviors
- `graphify/extract.py` - Provenance metadata injection in _extract_generic add_node
- `graphify/__init__.py` - Lazy-load entries for snapshot functions

## Decisions Made
- Provenance computed once per file (not per node) to avoid repeated SHA256 hashing
- Community keys serialized as strings in JSON (JSON constraint), restored to int on load
- OSError fallback for source_hash/source_mtime (empty string/None) for robustness

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- snapshot.py provides the foundation for delta computation (Plan 02)
- Provenance metadata (extracted_at, source_hash) enables staleness detection in delta
- list_snapshots returns sorted Paths for "compare last two snapshots" pattern in Plan 02

---
*Phase: 06-graph-delta-analysis-staleness*
*Completed: 2026-04-13*
