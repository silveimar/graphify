# Phase 15: Async Background Enrichment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `15-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 15-async-background-enrichment
**Areas discussed:** Pass orchestration, Budget policy, enrichment.json schema, Resumability after abort

---

## Pass orchestration

### Q1: How should the 4 passes execute within a single `graphify enrich` run?

| Option | Description | Selected |
|--------|-------------|----------|
| Serial fixed order | description → patterns → community → staleness, one at a time. Single writer to enrichment.json, one fcntl.flock holder, trivial SIGTERM handling. | ✓ |
| Serial + declared DAG | Community waits for description; staleness + patterns independent. More orchestrator logic. | |
| Parallel workers + queue | 4 concurrent workers routed through single-writer queue. Fastest wall-clock, multiplies API pressure, complicates SIGTERM. | |
| You decide | Claude picks simplest viable during planning. | |

**User's choice:** Serial fixed order (Recommended)
**Notes:** Aligns with Pitfall 3 single-writer invariant and Pitfall 4 simple SIGTERM model. Pass order (description → patterns → community → staleness) is part of the decision, not an implementation detail.

---

### Q2: If one pass fails mid-run, what happens to remaining passes?

| Option | Description | Selected |
|--------|-------------|----------|
| Abort whole run, preserve prior-pass writes | Failed pass rolls back; prior committed passes stay. Next run resumes at failed-pass boundary. | ✓ |
| Continue remaining passes, log failure | Skip failed pass, run rest, surface in exit code. Partial state in enrichment.json. | |
| Fail-fast, roll back entire run | Any failure voids the whole run. Strictest, wastes tokens on successful passes. | |

**User's choice:** Abort whole run, preserve prior-pass writes (Recommended)
**Notes:** Establishes per-pass atomic commit as the resume boundary — feeds directly into D-07 resumability semantics.

---

## Budget policy

### Q3: How should `--budget TOKENS` be allocated across the 4 passes?

| Option | Description | Selected |
|--------|-------------|----------|
| Priority-drain in pass order | Budget drains sequentially through description → patterns → community. Staleness exempt (compute-only). One flag, no config. | ✓ |
| Equal quarters | Each LLM pass gets budget/3. Predictable but wastes unused allocation. | |
| Declarative ratios in routing_models.yaml | YAML `enrichment: { description: 0.5, ... }`. Tunable, adds config surface. | |
| Per-pass sub-flags | `--budget-description N --budget-patterns N`. Most control, most CLI surface. | |

**User's choice:** Priority-drain in pass order (Recommended)
**Notes:** Staleness explicitly carved out as compute-only — no LLM calls, no budget accounting, always runs. No new YAML config surface introduced.

---

### Q4: `graphify enrich --dry-run` (ENRICH-10 P2) — what should it output?

| Option | Description | Selected |
|--------|-------------|----------|
| D-02 MCP envelope to stdout | Human table + `---GRAPHIFY-META---\n{json}` footer. Matches Phase 13 `capability --stdout` + Phase 18 `get_focus_context`. Per-pass: tokens, calls, $estimate. | ✓ |
| JSON only to stdout | Pure JSON, agent-first. Deviates from D-02 convention. | |
| Human table only to stderr | No JSON. Breaks agent consumption. | |
| You decide | Claude picks during planning. | |

**User's choice:** D-02 MCP envelope to stdout (Recommended)
**Notes:** $-estimate column appears only when `routing_models.yaml:pricing` is populated; otherwise tokens + API call counts only.

---

## enrichment.json schema

### Q5: How should `enrichment.json` be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-pass sections under versioned envelope | `{version, snapshot_id, generated_at, passes: {description, patterns, community, staleness}}`. Per-pass atomic commits align with D-02. | ✓ |
| Flat per-node map | `{node_id: {description, patterns_refs, community_summary_ref, staleness}}`. Simplest overlay-merge, but community + patterns aren't node-keyed — forces back-refs. | |
| JSONL append-only (PITFALLS.md default) | `enrichment.jsonl` + `enrichment_index.json`. Contradicts ENRICH-03/04 locked form. | |

**User's choice:** Per-pass sections under versioned envelope (Recommended)
**Notes:** User selected the preview showing the full schema shape — this is the committed form. `version: 1` reserved for forward-compatible additions from Phase 16/17.

---

### Q6: Overlay merge — when both graph.json and enrichment.json have a description, which wins?

| Option | Description | Selected |
|--------|-------------|----------|
| Enrichment augments, graph.json wins on conflict | Base description stays; enrichment surfaces as `enriched_description` field. graph.json remains source of truth. | ✓ |
| Enrichment replaces graph.json description | Polished output per node, but enrichment becomes load-bearing. | |
| Enrichment replaces only when graph.json description is empty/missing | Middle path — extracted wins, enrichment fills gaps. | |

**User's choice:** Enrichment augments, graph.json wins on conflict (Recommended)
**Notes:** Critical for test stability — assertions on `node["description"]` stay unchanged; new assertions check `node["enriched_description"]`.

---

## Resumability after abort

### Q7: After enrichment SIGTERM-aborts, what should the next `graphify enrich` invocation do?

| Option | Description | Selected |
|--------|-------------|----------|
| Resume from next incomplete pass, same snapshot_id | Read existing enrichment.json; if snapshot_id matches, skip completed passes. If snapshot_id differs, discard and start fresh. Zero token waste on successful passes. | ✓ |
| Always start fresh, overwrite prior enrichment | Simplest, but contradicts D-02 preserve-prior-writes. | |
| Per-node checkpointing within passes | Most granular, most complex. Requires partial-pass state in schema. | |
| Resume only if `--resume` flag passed, else fresh | Explicit opt-in. Reduces surprise, more user knowledge required. | |

**User's choice:** Resume from next incomplete pass, same snapshot_id (Recommended)
**Notes:** Implicit resume — no `--resume` flag. `snapshot_id` is the gate; any change to pinned snapshot discards prior enrichment and runs fresh. No per-node intra-pass checkpointing.

---

## Claude's Discretion (deferred to planner)

- Staleness FRESH/STALE/GHOST thresholds (days-since-mtime / git-age / degree-drop signals)
- Watch.py post-rebuild hook wiring (inline-await vs Popen+heartbeat vs dispatcher queue)
- Patterns pass cross-snapshot depth (default 5 snapshots unless research suggests otherwise)
- ENRICH-11 P2 description-pass skip-list criteria (routing.json complex-tier flag vs non-empty graph.json description vs both)
- Per-pass LLM-call retry policy (backoff, max attempts before pass declared failed)

## Deferred Ideas (noted for future phases)

- User-Python deriver plugins (entry-point model) — post-v1.4 if needed
- Real-time / pipeline-blocking enrichment — permanently OOS
- Implicit enrichment on MCP `get_node` — permanently OOS
- Budget-less "unlimited" passes — rejected
- Cross-session memory — Phase 17 scope
- Additional derivation passes — schema `version: 1` reserved; future phase
- Per-node intra-pass checkpointing — considered, rejected under D-07
- `enrichment_models.yaml` — considered, rejected (reuse `routing_models.yaml`)
