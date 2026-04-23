# Phase 18: Focus-Aware Graph Context - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a new MCP tool `get_focus_context(focus_hint, budget)` that takes an agent-reported focus (file path, optional function_name / line / neighborhood_depth / include_community) and returns a scoped subgraph — BFS ego-graph + community summary + citations — in the D-02 envelope. Scope is `serve.py` only, plus a defensive rename in `snapshot.py` (`root` → `project_root`) with a construction-time sentinel that codifies v1.3 CR-01 (Pitfall 20). Nine REQ-IDs locked: FOCUS-01..09.

</domain>

<decisions>
## Implementation Decisions

### Focus Resolution (Area 1)

- **D-01:** **Multi-seed union.** When `file_path` resolves to N node_ids (v1.3 `source_file: str | list[str]`), the resolver collects ALL matching node_ids and passes the list as a multi-seed input to `nx.ego_graph` (dedupe on union). Preserves the semantic "everything from this file + its neighborhood."
- **D-02:** **`function_name` and `line` are optional narrowing filters.** When provided, filter the union down to node_ids whose `source_location` matches. When absent, use the full union. Keeps the common case simple; precision available on demand.
- **D-03:** **No-match is indistinguishable from spoofed path.** A `file_path` that is inside `project_root` and passes security validation but doesn't resolve to any node_ids returns the exact same no-context envelope as a spoofed path. Strongest anti-leak: callers cannot enumerate which files are graphed.
- **D-04:** **Accept absolute OR relative paths; normalize.** Resolver calls `Path(p).resolve()` then confines against `project_root` via `security.py::validate_graph_path(path, base=project_root)`. Anything outside → silent ignore. Matches how agents actually report focus (editors give absolute paths).

### Defaults & Budget Behavior (Area 2)

- **D-05:** **`neighborhood_depth` defaults to `2`.** Depth-1 in code graphs usually yields just a class's own method stubs (contains edges); depth-2 captures other classes it calls/imports.
- **D-06:** **`include_community` defaults to `true`.** The phase's whole point is giving agents cluster context alongside local structure; opt-in would hide the feature from most callers. Community attrs already set during `cluster()` — cheap to look up.
- **D-07:** **`budget` defaults to `2000` tokens.** Matches `query_graph` (closest analog — both return full subgraphs + citations). Consistency across MCP tools > tool-specific tuning. Clamp to `[50, 100000]` per the existing pattern in `serve.py`.
- **D-08:** **Budget-pressure truncation drops outer hop first.** When the ego-graph + community summary exceeds `budget * 3` chars, drop hop-N neighbors before hop-(N-1). Graceful degrade: the tool degrades to depth-1 then depth-0 rather than dropping the focus itself or mangling the community summary.

### Silent-Ignore Envelope (Area 3)

- **D-09:** **`text_body = ""` for no-context results.** Empty string. The D-02 sentinel + meta JSON still follow (parsers don't break). Matches how `entity_trace` handles zero-result sections.
- **D-10:** **Meta shape for no-context:** `{status: "no_context", node_count: 0, edge_count: 0, budget_used: 0}`. Minimal, stable schema. Agents detect failure via `status !== "ok"` OR `node_count === 0` — redundant on purpose so either check works.
- **D-11:** **Status enum is binary: `ok | no_context` only.** All failure modes (spoofed path, unindexed file, stale `reported_at`, future additions) collapse to `no_context`. One failure mode, indistinguishable from outside. Any future "error" status must be justified against this anti-leak invariant.
- **D-12:** **No echo of `focus_hint` fields in meta.** Never reflect `file_path`, `function_name`, or `line` back. An attacker spoofing `/etc/passwd` gets zero confirmation their path was received. On `status: ok`, the envelope's node citations already give the agent everything it needs.

### P2 Guards (Area 4) — FOCUS-08 + FOCUS-09

- **D-13:** **Ship both P2 requirements in Phase 18 as Plan 18-03** (after 18-01 resolver + 18-02 MCP tool land). Total 3 plans. Debounce + freshness are cheap (≤100 LOC combined) and become landmines if deferred past Phase 14 (Obsidian Commands will hammer this endpoint).
- **D-14:** **Debounce via module-level LRU + `time.monotonic()`.** Key on `(file_path, function_name, line, depth, include_community)` tuple. Store last-call timestamp per key; if `now - last < 0.5s` return the cached envelope. No new deps; works inside stdio server process lifetime. Interpretation: debounce = suppress-duplicate-within-window, not defer.
- **D-15:** **`focus_hint.reported_at` is optional ISO 8601 UTC.** When present and `now - reported_at > 300s`, return the `no_context` envelope (indistinguishable from spoof — honors D-11). When absent, no freshness check — backward compatible so Phase 14 can adopt gradually. Validation path: parse via `datetime.fromisoformat`; any parse failure → `no_context`.

### Claude's Discretion

- **Community summary content shape.** REQ-03 says "community summary" but leaves the exact fields to planning. Default to reusing `analyze.py` community-representative logic (top-N nodes by degree, cohesion score, member count). Planner may adjust based on budget impact.
- **Test fixture design for the CR-01 guard.** REQ-07 mandates a nested-dir integration fixture. Planner decides exact fixture layout; the invariant is that the sentinel must fire if `snapshot.py::project_root` is ever constructed with `path.name == "graphify-out"`.
- **Sentinel exception class naming.** `ValueError` vs a named subclass (e.g., `DoubleNestedRootError`). Default to `ValueError` for simplicity; escalate only if downstream phases need a catchable distinct type.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements

- `.planning/ROADMAP.md` §§ "Phase 18: Focus-Aware Graph Context" — goal, success criteria (5 items), cross-phase rule citing CR-01, plan count guidance (2–3 plans expected — locked to 3 per D-13).
- `.planning/REQUIREMENTS.md` §§ FOCUS-01..09 (lines 117–125, 264–272, 281) — 9 REQ-IDs locked; P1 = FOCUS-01..07, P2 = FOCUS-08/09.
- `.planning/STATE.md` §§ "Current Position", "Build order" — Phase 18 is next candidate in the locked build order; must land before Phase 14 (Obsidian Commands HARD-depends on FOCUS-07 sentinel).

### Prior-phase decision lineage

- `.planning/milestones/v1.3-phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md` — origin of the D-02 envelope (`text_body + "---GRAPHIFY-META---" + json.dumps(meta)`). Phase 18's new tool MUST match this shape.
- `.planning/milestones/v1.3-phases/11-narrative-mode-slash-commands/11-CONTEXT.md` — D-18 "compose-don't-plumb" decision. Phase 18 follows this: no new modules; compose `nx.ego_graph` + existing `security.py` + existing community data.
- `.planning/milestones/v1.3-phases/10-cross-file-semantic-extraction/10-CONTEXT.md` — `source_file: str | list[str]` schema upgrade. Resolver MUST handle both shapes (D-01).
- `.planning/phases/12-heterogeneous-extraction-routing/12-CONTEXT.md` §§ "Reference anchors" — reinforces D-02 for MCP-facing summaries.
- `.planning/phases/13-agent-capability-manifest/13-CONTEXT.md` §§ D-02 — capability_describe uses the same envelope; set the precedent for new tools matching hash-extended meta.

### Cross-cutting patterns & pitfalls

- `.planning/RETROSPECTIVE.md` §§ Phase 11 narrative mode, "No new modules for plumbing phases (D-18)", "Test fixtures must match production path semantics" (lines 178, 199, 204) — D-18 compose pattern and CR-01 root-cause analysis.

### Production code touch points

- `graphify/serve.py` §§ `QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"` (line 757), `_subgraph_to_text` (line 681), `query_graph` dispatcher (line 769) — reference implementations for D-02 envelope shape, budget clamping, and text_body construction that the new `get_focus_context` tool must match.
- `graphify/security.py::validate_graph_path(path, base)` (line 144) — existing silent-ignore pattern the resolver reuses for FOCUS-04.
- `graphify/snapshot.py` — refactor target: `root` field → `project_root` across `snapshots_dir` (line 14), `list_snapshots` (line 21), `save_snapshot` (line 29), `auto_snapshot_and_delta` (line 85), `load_snapshot` (line 123). Sentinel asserts `path.name != "graphify-out"` at construction.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`graphify/serve.py` D-02 helpers** — `QUERY_GRAPH_META_SENTINEL`, the `text_body + SENTINEL + json.dumps(meta)` pattern, and budget clamping `max(50, min(budget, 100000))` are already in place across 6 MCP tools. The new `get_focus_context` dispatcher is a parallel addition, not a new pattern.
- **`graphify/security.py::validate_graph_path(path, base)`** — returns a confined path or raises for out-of-root. The resolver catches and maps to silent-ignore envelope per D-03/D-04.
- **`nx.ego_graph(G, nodes, radius)`** — NetworkX stdlib API already accepts a list of seed nodes for multi-source ego graphs. D-01 multi-seed union is a single call, no custom BFS needed.
- **`graphify/analyze.py`** — community-representative selection logic (top-N by degree, cohesion scoring) reusable for the community summary field (Claude's Discretion above).
- **`_load_graph(graph_path)`** (serve.py:429) + `_communities_from_graph(G)` (serve.py:450) — existing loaders; new tool reads the same `graphify-out/graph.json`.

### Established Patterns

- **MCP tool dispatch** — every tool has a pure-dispatch core (`..._core`) that returns the envelope string; an MCP runtime wrapper at the bottom invokes it. New `get_focus_context_core` + MCP wrapper follows this shape (testable without mcp runtime).
- **Budget clamping** — always `int(arguments.get("budget", DEFAULT))` → `max(50, min(budget, 100000))`. Char budget = `budget * 3`. Truncation appends `"\n... (truncated to ~{budget} token budget)"` before the sentinel.
- **Silent-ignore on path violations** — caught ValueError from `validate_graph_path` maps to empty-envelope return; never re-raised to caller.

### Integration Points

- **New tool registration** — the MCP server exposes tools via a dispatcher dict near the bottom of `serve.py`. Adding `get_focus_context` is a single dict entry + the wrapper function.
- **No new files expected** — D-18 compose-don't-plumb. All new code lives in `serve.py` (new core + wrapper, ~250 LOC) plus `snapshot.py` rename (mechanical, ~20 LOC touched across 5 functions).
- **Test placement** — `tests/test_serve.py` already exercises D-02 envelopes for other tools; add `test_get_focus_context_*` cases + nested-dir fixture in `tests/test_snapshot.py` (or new `test_snapshot_sentinel.py`) per planner's call.

</code_context>

<specifics>
## Specific Ideas

- **"Indistinguishable from spoof"** (D-03 + D-11) is the single strongest invariant — every future FOCUS enhancement must be tested against it. The two-valued `status` enum is the structural enforcement (D-11): adding any third value breaks the invariant and requires a phase-level decision, not a drive-by commit.
- **The `snapshot.py` rename is a retrospective action** codifying CR-01 (Pitfall 20). Its purpose is LOUD failure — a construction-time `AssertionError` / `ValueError` the first time a buggy caller passes `graphify-out/` as `project_root`. The test fixture exists to prove this fails; downstream phases (12, 15, 17) passively benefit without changes.
- **P2 debounce = suppress-duplicate-within-window, not deferral.** (D-14). The cache RETURNS the previous envelope on cache hit within 500ms — it does not delay or batch. No new timer threads, no new complexity. A subsequent call after the window computes fresh.

</specifics>

<deferred>
## Deferred Ideas

- **File-level node vs entity-level node classification** — considered but rejected as unnecessary. Multi-seed union (D-01) handles both shapes without a classifier. If downstream phases need this distinction, open it as a separate ADR.
- **Basename-only fallback for `file_path`** — rejected for Phase 18 (ambiguity when basenames collide). If real agents report stripped paths, raise as a defect for Phase 14 scope.
- **Community summary field list** — deferred to Claude's Discretion within Phase 18 planning. Candidate enhancement for v1.5: make the community payload shape an enum arg (`community_detail: "minimal" | "standard" | "full"`).
- **Named exception class for the snapshot sentinel** — `DoubleNestedRootError(ValueError)` subclass would let downstream code catch specifically. Defer unless a concrete caller needs to distinguish it from generic `ValueError`.

</deferred>

---

*Phase: 18-focus-aware-graph-context*
*Context gathered: 2026-04-20*
