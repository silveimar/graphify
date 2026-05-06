# Phase 67: CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 67-CDRIFT + CQUERY
**Areas discussed:** Snapshot trigger & retention, Jaccard match threshold, Drift report scope & placement, CQUERY parameter semantics

---

## Snapshot trigger & retention

| Option | Description | Selected |
|--------|-------------|----------|
| Every successful run | Auto-snapshot at end of pipeline. Zero-friction drift over time; retention policy keeps disk bounded. | ✓ |
| Only with --snapshot flag | Explicit opt-in per run. No accidental disk usage; user controls drift cadence. | |
| Only on manifest-hash change | Skip snapshots when graph is byte-identical to previous. Saves disk on no-op reruns; trickier to reason about. | |

**User's choice:** Every successful run (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Count-based: keep last 10 | Simple, predictable disk footprint. FIFO eviction by mtime. | ✓ |
| Age-based: keep ≤ 30 days | Time-windowed history. | |
| Both: count<=20 AND age<=90d | Belt-and-suspenders. | |

**User's choice:** Count-based, keep last 10 (Recommended).
**Notes:** Auto-snapshot + FIFO retention = predictable disk footprint with no opt-in friction.

---

## Jaccard match threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 0.5 — majority overlap | Lenient; risks treating big merges as renames. | |
| 0.7 | Standard clustering-stability cutoff. | ✓ |
| 0.9 — near-identical only | Strict; most edges drift to community-resharded on any churn. | |

**User's choice:** 0.7 (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded constant | Single source of truth in drift.py. | ✓ |
| Env var override only | Power-user escape hatch. | |
| CLI flag (--drift-jaccard) | First-class config. | |

**User's choice:** Hardcoded constant (Recommended).
**Notes:** Avoid premature config knobs; extract to flag later only if a concrete use case appears.

---

## Drift report scope & placement

| Option | Description | Selected |
|--------|-------------|----------|
| After Federation | Order: Communities → Federation → Drift. Mirrors Phase 66 placement. | ✓ |
| After Communities, before Federation | Drift adjacent to Communities since both deal with membership. | |

**User's choice:** After Federation (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Summary table + per-class top-N edges | 4-class counts + first 10 edges per non-stable class. | ✓ |
| Counts only | Just the 4-class tally. | |
| Full per-edge listing | Every classified edge in the report. | |

**User's choice:** Summary table + per-class top-N (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Render section with 'no drift edges' note | Section appears with 0/0/0/0 + brief note. | ✓ |
| Omit section entirely | Treat empty-edge case identically to no-snapshot case. | |

**User's choice:** Render with note (Recommended). Predictable section presence aids automation.

---

## CQUERY parameter semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Enum: high\|medium\|low | Discoverable, MCP-schema-friendly. | ✓ |
| Numeric tuple [min, max] | Open-ended range; overlaps min_confidence. | |
| Both — enum primary, tuple alt | Doubles validation surface. | |

**User's choice:** Enum (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| AND — both must pass | Predictable; either may be None. | ✓ |
| confidence_band overrides min_confidence | Silent override is a footgun. | |
| Reject the combination | Cleanest semantics; user-hostile. | |

**User's choice:** AND (Recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Whitelist; default None = all; empty list [] = zero results | Explicit semantics; empty-list ≠ no filter. | ✓ |
| Whitelist; empty list [] = same as None | Forgiving but ambiguous. | |

**User's choice:** Whitelist with strict empty-list semantics (Recommended).

---

## Claude's Discretion

- Internal data structures inside `drift.py` (snapshot file format, in-memory dataclasses).
- Snapshot filename shape (timestamp vs manifest hash) — researcher decides.
- Whether to extend `report.py` in place (per Phase 66 Federation pattern) or split a `drift_report.py` helper.
- Exact confidence cutpoints for the `confidence_band` enum — sanity-check during research against Phase 65 distribution.

## Deferred Ideas

- Coverage-lens query (D-3 in REQUIREMENTS.md) — depends on CQUERY shipping first.
- Drift exposure via MCP/CLI (`drift_query` tool, `graphify drift` subcommand).
- Age-based snapshot retention — only if count=10 proves insufficient.
- User-tunable Jaccard threshold (env var or CLI flag).
- HTML viz of drift in the vis.js export.
