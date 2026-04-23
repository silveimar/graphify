# Phase 18: Focus-Aware Graph Context - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 18-focus-aware-graph-context
**Areas discussed:** Focus resolution, Defaults & budget, Silent-ignore envelope, P2 ship-or-defer

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Focus resolution | Multi-match anchor behavior, function_name/line role, no-match, path shape | ✓ |
| Defaults & budget | neighborhood_depth / include_community / budget defaults + truncation order | ✓ |
| Silent-ignore envelope | text_body, meta shape, status enum, echo behavior for no-context results | ✓ |
| P2 ship-or-defer | FOCUS-08 debounce + FOCUS-09 reported_at freshness: Phase 18 vs sub-phase vs v1.5 | ✓ |

**User's choice:** All four areas selected for discussion.

---

## Focus Resolution

### Q1 — Multi-match strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-seed union (Rec.) | All matching node_ids → `ego_graph` on the union, deduped | ✓ |
| Highest-degree anchor | Pick the single most-connected node_id | |
| File-level node + fallback | Use file-level node if exists, else union | |

**User's choice:** Multi-seed union (Rec.)
**Notes:** Matches `nx.ego_graph` native list-of-seeds API. Preserves "everything from this file" semantic.

### Q2 — Role of `function_name` / `line`

| Option | Description | Selected |
|--------|-------------|----------|
| Optional narrowing filter (Rec.) | When present, filter union by source_location; absent = full union | ✓ |
| Hard disambiguation | Required when N>1; tool returns 'disambiguate' status otherwise | |
| AND-filter always | Always applied; zero matches → silent-ignore | |

**User's choice:** Optional narrowing filter (Rec.)
**Notes:** Keeps common case simple, adds precision on demand without forcing conversational retries.

### Q3 — No-match behavior (valid but unindexed file)

| Option | Description | Selected |
|--------|-------------|----------|
| Indistinguishable from spoof (Rec.) | Same empty envelope; status=`no_context`, node_count=0 | ✓ |
| Distinct meta status | Same text_body, but meta status differs for access_denied vs not_indexed | |
| Informative in meta only | Silent text_body, but meta carries `reason` field | |

**User's choice:** Indistinguishable from spoof (Rec.)
**Notes:** Strongest anti-leak. Prevents enumeration of which files are graphed.

### Q4 — Path shape accepted

| Option | Description | Selected |
|--------|-------------|----------|
| Abs + rel, normalize (Rec.) | Accept both; `Path.resolve()` + confine against project_root | ✓ |
| Relative only | Reject absolute paths before resolution | |
| Abs/rel + basename fallback | Like #1, plus basename-only match when exact fails | |

**User's choice:** Abs + rel, normalize (Rec.)
**Notes:** Matches how editors/agents actually report focus (absolute paths). Basename fallback deferred (ambiguity concern).

---

## Defaults & Budget

### Q1 — `neighborhood_depth` default

| Option | Description | Selected |
|--------|-------------|----------|
| 2 hops (Rec.) | Immediate + neighbors-of-neighbors | ✓ |
| 1 hop | Only direct neighbors (often just method stubs for class nodes) | |
| 3 hops | Risks exponential blow-up; usually truncated anyway | |

**User's choice:** 2 hops (Rec.)

### Q2 — `include_community` default

| Option | Description | Selected |
|--------|-------------|----------|
| true (Rec.) | Include community summary by default | ✓ |
| false | Lean default; agent must opt in | |

**User's choice:** true (Rec.)

### Q3 — `budget` default

| Option | Description | Selected |
|--------|-------------|----------|
| 2000 — match query_graph (Rec.) | Consistency with closest analog MCP tool | ✓ |
| 1500 — tighter than query_graph | Ego-graphs bounded by depth, need less headroom | |
| 500 — match narrative tools | Cheap but forces constant truncation | |

**User's choice:** 2000 — match query_graph (Rec.)

### Q4 — Budget-pressure truncation order

| Option | Description | Selected |
|--------|-------------|----------|
| Outer hop first (Rec.) | Drop hop-N before hop-(N-1); degrade to depth-1 then depth-0 | ✓ |
| Lowest-degree first | Keep hubs, drop leaves | |
| Community summary first | Preserve ego-graph, drop meta-context (contradicts include_community=true default) | |

**User's choice:** Outer hop first (Rec.)

---

## Silent-Ignore Envelope

### Q1 — `text_body` for no-context

| Option | Description | Selected |
|--------|-------------|----------|
| Empty string (Rec.) | `text_body = ""` | ✓ |
| Static marker "(no context)" | Human-readable string on zero-result | |
| Newline only | `text_body = "\n"` | |

**User's choice:** Empty string (Rec.)

### Q2 — Meta shape for no-context

| Option | Description | Selected |
|--------|-------------|----------|
| status + node_count=0 (Rec.) | `{status, node_count, edge_count, budget_used}` — minimal, stable | ✓ |
| Match full D-02 schema with zeros | All success fields present, zeroed/null | |
| Status only | Smallest possible; breaks stable-schema pattern | |

**User's choice:** status + node_count=0 (Rec.)

### Q3 — Status enum

| Option | Description | Selected |
|--------|-------------|----------|
| Two: ok, no_context (Rec.) | All failure modes collapse to no_context | ✓ |
| Three: ok, no_context, error | `error` reserved for protocol/schema failures | |
| Many: ok, not_indexed, access_denied, stale, malformed | Fine-grained but leaks membership info | |

**User's choice:** Two: ok, no_context (Rec.)

### Q4 — Echo input fields in meta

| Option | Description | Selected |
|--------|-------------|----------|
| No echo (Rec.) | Never reflect focus_hint fields back | ✓ |
| Echo resolved-only on success | Echo node_ids_resolved on ok; nothing on no_context | |
| Always echo focus_hint | Reflect full focus_hint back regardless of status | |

**User's choice:** No echo (Rec.)

---

## P2 Ship-or-Defer

### Q1 — Scope decision

| Option | Description | Selected |
|--------|-------------|----------|
| Ship both in Phase 18 (Rec.) | Bundle FOCUS-08 + FOCUS-09 into Plan 18-03 | ✓ |
| Defer to Phase 18.1 after verification | Ship P1 only; decimal sub-phase later | |
| Defer to v1.5 | Drop from v1.4 entirely | |

**User's choice:** Ship both in Phase 18 (Rec.)
**Notes:** 3 plans total: 18-01 resolver, 18-02 MCP tool + envelope, 18-03 debounce + freshness.

### Q2 — Debounce implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level LRU + monotonic clock (Rec.) | `(file_path, function_name, line, depth, include_community)` keyed cache + time.monotonic() | ✓ |
| Per-call time gate | Dict-based last-call timestamp per focus tuple | |
| No debounce in tool, agent-side only | Document the contract; don't enforce | |

**User's choice:** Module-level LRU + monotonic clock (Rec.)

### Q3 — `reported_at` freshness

| Option | Description | Selected |
|--------|-------------|----------|
| Optional ISO 8601, reject >5min (Rec.) | Parse via datetime.fromisoformat; stale → no_context envelope | ✓ |
| Required unix seconds | Mandatory int timestamp | |
| Optional, soft-warn only in meta | Return data with `meta.freshness: "stale"` | |

**User's choice:** Optional ISO 8601, reject >5min (Rec.)
**Notes:** Backward compatible — agents not setting `reported_at` skip the check entirely.

---

## Claude's Discretion

- Community summary field list (reusing `analyze.py` representative logic by default).
- Test fixture layout for the CR-01 nested-dir guard (invariant: sentinel must fire when `path.name == "graphify-out"`).
- Sentinel exception class (default `ValueError`; escalate to named subclass only if a concrete caller needs catchable distinction).

## Deferred Ideas

- File-level vs entity-level node classification — multi-seed union makes it unnecessary for Phase 18.
- Basename-only path fallback — deferred to Phase 14 scope if real agents report stripped paths.
- Community summary `community_detail` enum arg (`minimal | standard | full`) — v1.5 candidate.
- `DoubleNestedRootError` named exception subclass — defer until a concrete caller needs it.
