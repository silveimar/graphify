# Phase 71 DISCUSSION LOG — TEMP

**Date:** 2026-05-07
**Mode:** default (4 areas, single-question turns)

## Areas selected
All four offered: Timestamp source & format; Decay function & config shape; Supersession detection; Backward-compat + Temporal Health rendering.

## Q&A

### Area 1 — Timestamp source & format
**Q:** What should fill valid_from / valid_until on edges?
- ISO8601 UTC wall-clock (per-edge) ← **chosen**
- Run-id manifest + ISO timestamp
- ISO timestamp + optional run_id field

### Area 2 — Decay config & shape
**Q1:** How should decay be configured?
- YAML at `graphify/temporal_config.yaml` ← **chosen**
- Python constants in new `graphify/temporal.py`
- Section in `pyproject.toml [tool.graphify.temporal]`

**Q2:** Default decay function?
- Exponential half-life ← **chosen**
- Linear ramp with floor
- Step function (grace + cliff)

### Area 3 — Supersession detection
**Q1:** Match key for "no longer produced"?
- (source, target, relation, source_file)
- (source, target, relation) global ← **chosen**
- Hybrid: per-file EXTRACTED, global INFERRED

**Q2:** Behavior on source_file deletion?
- Stamp valid_until on all edges from that file ← **chosen**
- Keep valid if same tuple appears from another file
- Defer to researcher

**Reconciliation note:** Global rule (Q1) is primary. File-deletion stamping (Q2) applies only when no other file produces the same `(source, target, relation)` in the current run. Captured in CONTEXT.md.

### Area 4 — Backward compat + Temporal Health rendering
**Q1:** Pre-v2.0 graph handling?
- Read-tolerant, write-strict, bump SCHEMA_VERSION to 2.0 ← **chosen**
- + one-shot migrate CLI
- Read-tolerant + on-load lazy backfill

**Q2:** Temporal Health subsection content?
- Minimal: counts only ← **chosen**
- Counts + histogram + top-N decayed relations
- Full: counts + histogram + supersession timeline

**Q3:** Wiki rendering of superseded edges?
- Separate "Historical relations" subsection ← **chosen**
- Inline strikethrough with date footnote
- Hide by default; link to history page

## Deferred ideas
- Richer Temporal Health views (histogram, timeline, top-N decayed relations)
- `graphify migrate` CLI command for explicit pre-v2.0 rewrite
- Promoting PyYAML from `[routing]` extra to core dep

## Claude's discretion (left to researcher/planner)
- Test-time clock injection mechanism (env var vs injectable clock vs fixture)
- Exact `analyze.py` filter predicate locations
- Per-relation default `half_life_days` tuning
- Whether `cache.py` already supports the run-scoped edge-set diff needed for global supersession
