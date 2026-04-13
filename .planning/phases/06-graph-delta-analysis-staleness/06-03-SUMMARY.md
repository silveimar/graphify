---
phase: 06-graph-delta-analysis-staleness
plan: 03
subsystem: cli
tags: [snapshot, delta, cli, pipeline-integration]

requires:
  - phase: 06-01
    provides: "snapshot.py — save_snapshot, load_snapshot, list_snapshots, snapshots_dir"
  - phase: 06-02
    provides: "delta.py — compute_delta, classify_staleness, render_delta_md"
provides:
  - "graphify snapshot CLI subcommand with --name, --cap, --graph, --from, --to, --delta flags"
  - "auto_snapshot_and_delta() pipeline helper for zero-friction post-build usage"
  - "GRAPH_DELTA.md output file generation"
affects: [07-mcp-annotation, skill-orchestration]

tech-stack:
  added: []
  patterns: ["CLI arg parsing via sys.argv manual loop (matches --obsidian pattern)", "subprocess CLI integration testing pattern"]

key-files:
  created: []
  modified:
    - graphify/__main__.py
    - graphify/snapshot.py
    - graphify/__init__.py
    - tests/test_snapshot.py
    - tests/test_delta.py

key-decisions:
  - "Used gen_delta variable name instead of delta to avoid shadowing delta dict variable"
  - "--from/--to mode writes GRAPH_DELTA.md to cwd graphify-out/ (consistent with all other outputs)"

patterns-established:
  - "CLI snapshot subcommand follows exact --obsidian arg parsing pattern"
  - "auto_snapshot_and_delta combines save + delta in one call for skill/pipeline use"

requirements-completed: [DELTA-07, DELTA-01, DELTA-02]

duration: 3min
completed: 2026-04-13
---

# Phase 06 Plan 03: CLI Wiring Summary

**`graphify snapshot` CLI subcommand with --name/--cap/--from/--to/--delta flags plus auto_snapshot_and_delta pipeline helper**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-13T01:17:04Z
- **Completed:** 2026-04-13T01:20:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- auto_snapshot_and_delta() helper saves snapshot and generates GRAPH_DELTA.md in one call for pipeline/skill use
- `graphify snapshot` CLI subcommand with full flag support (--name, --cap, --graph, --from, --to, --delta)
- --from/--to enables comparing any two specific snapshots per DELTA-07
- Full test suite green: 912 passed (7 new tests: 3 auto_snapshot + 4 CLI integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add auto_snapshot_and_delta helper** - `27a5137` (feat)
2. **Task 2: Add graphify snapshot CLI subcommand** - `3a95b0b` (feat)

## Files Created/Modified
- `graphify/snapshot.py` - Added auto_snapshot_and_delta() convenience function
- `graphify/__main__.py` - Added snapshot CLI subcommand with full arg parsing
- `graphify/__init__.py` - Added lazy-load entry for auto_snapshot_and_delta
- `tests/test_snapshot.py` - 3 new tests for auto_snapshot_and_delta
- `tests/test_delta.py` - 4 new CLI integration tests

## Decisions Made
- Used `gen_delta` variable name instead of `delta` to avoid shadowing the delta dict in the same scope
- --from/--to mode writes to cwd `graphify-out/GRAPH_DELTA.md` consistent with all other outputs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Subprocess CLI tests initially failed because the editable install was stale. Re-ran `pip install -e ".[all]"` to pick up the new snapshot command. This is expected behavior for editable installs when modifying entry point routing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 06 complete: snapshot persistence (01), delta computation (02), and CLI wiring (03) all done
- Ready for Phase 07 (MCP annotation layer) which depends on snapshot/delta infrastructure
- auto_snapshot_and_delta() is the integration point for skill orchestration

---
*Phase: 06-graph-delta-analysis-staleness*
*Completed: 2026-04-13*
