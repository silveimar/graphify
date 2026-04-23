# Phase 15: Async Background Enrichment - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Graphify ships a background enricher — a new module `graphify/enrich.py` plus a `graphify enrich` CLI subcommand — that runs four derivation passes (description, patterns, community, staleness) over a pinned snapshot and writes the results to an overlay-only sidecar (`graphify-out/enrichment.json`). The foreground `/graphify` pipeline and `graph.json` are never modified by this phase. Scope covers: the enrichment orchestrator + CLI, the four passes, the atomic-write + flock-coordinated abort machinery, the `serve.py::_load_enrichment_overlay` overlay merge, `_reload_if_stale` mtime watch extension, the post-rebuild `watch.py` trigger hook, the `--dry-run` cost preview, and D-16 alias redirect threading. Out of scope: user-Python deriver plugins, real-time pipeline-blocking enrichment, implicit LLM calls from MCP `get_node`, and budget-less pass execution.

</domain>

<decisions>
## Implementation Decisions

### Pass orchestration
- **D-01:** Serial, fixed-order execution: `description → patterns → community → staleness`. One pass at a time, one writer to `enrichment.json`, one `fcntl.flock` holder for the whole run. No internal parallelism, no DAG resolver. This matches the Pitfall 3 single-writer invariant and keeps SIGTERM handling a single decision point (flush current pass, release lock, exit).
- **D-02:** **Per-pass atomic commit, fail-abort-preserve.** When a pass completes successfully, its section in `enrichment.json` is committed via `.tmp` + `os.replace`. If a pass fails mid-run (LLM error, budget exhausted, validation error), the partial pass write rolls back; already-committed prior passes stay in the file. The whole run then aborts — no "continue remaining passes" behavior. Next invocation resumes at the failed pass boundary (see D-07).

### Budget policy
- **D-03:** **Priority-drain allocation.** `--budget TOKENS` is a single top-level cap that drains in pass order — description consumes until it completes or hits the remaining budget, then patterns, then community. No equal-quarters split, no per-pass sub-flags. Staleness is **compute-only** (graph topology + file mtimes, no LLM calls) and is exempt from budget accounting — it always runs last.
- **D-04:** **`--dry-run` emits a D-02-style envelope** (human table + `\n---GRAPHIFY-META---\n{json}` footer). Per-pass breakdown: estimated tokens, API call count, and $-estimate (only when `routing_models.yaml:pricing` is populated — otherwise tokens + calls only). Matches the Phase 13 `graphify capability --stdout` precedent so agents can parse the JSON and humans can read the table from the same output.

### enrichment.json schema
- **D-05:** **Per-pass sections under a versioned envelope.** Top-level:
  ```json
  {
    "version": 1,
    "snapshot_id": "<snapshot pinned at process start>",
    "generated_at": "<ISO-8601>",
    "passes": {
      "description": { "<node_id>": "<enriched text>" },
      "patterns":    [ { "pattern_id": "...", "nodes": [...], "summary": "..." } ],
      "community":   { "<community_id>": "<summary text>" },
      "staleness":   { "<node_id>": "FRESH|STALE|GHOST" }
    }
  }
  ```
  The `passes` sub-object is the resume unit — each key's presence means "that pass completed for this snapshot_id". Missing keys indicate passes not yet run (or rolled back via D-02). `version: 1` is reserved for forward-compatible additions.
- **D-06:** **Overlay-merge policy in `serve.py::_load_enrichment_overlay(out_dir)`: enrichment augments, `graph.json` wins on conflict.** If a node has both a `description` from extraction and a `description` in `enrichment.json:passes.description`, the overlay surfaces the enriched text on a new `enriched_description` field — it does NOT overwrite the base `description`. Keeps `graph.json` as the deterministic source of truth; enrichment is additive, inspectable, and separable in MCP/CLI responses.

### Resumability
- **D-07:** **Implicit resume-by-default, snapshot_id-gated.** On invocation, `graphify enrich` reads any existing `enrichment.json`. If `snapshot_id` matches the pinned snapshot for this run, completed passes are skipped and execution resumes at the first missing/rolled-back pass. If `snapshot_id` differs (graph was rebuilt), the existing file is discarded and a fresh run begins. No `--resume` flag — resume is the default. Per-node intra-pass checkpointing is explicitly NOT done (complexity not worth the token savings on sub-pass aborts).

### Claude's Discretion
- **Staleness thresholds** — the FRESH/STALE/GHOST decision function (days-since-source-mtime, git-age, node-degree drop thresholds). Planner picks defaults; a future phase can tune via `routing_models.yaml` if needed.
- **Watch.py trigger wiring** — whether the post-rebuild hook spawns enrichment inline-awaited, via `subprocess.Popen` with a `.enrichment.pid` heartbeat (Pitfall 4 lifecycle), or queued through the existing `watch.py` dispatcher. Planner chooses the approach that minimizes new process-lifecycle surface.
- **Patterns pass cross-snapshot depth** — how many historical snapshots under `graphify-out/snapshots/NNNN/` the patterns pass reads, and how it caps storage cost. Default: last 5 snapshots unless research surfaces a stronger number.
- **Description-pass skip-list criteria** — whether skip-by-routing (ENRICH-11 P2) is "file already extracted by `complex` tier per `routing.json`", "node already has a non-empty `description` in `graph.json`", or both (AND).
- **Per-pass retry policy** — LLM call-level retries within a pass (exponential backoff, max attempts) before the pass is declared failed under D-02.

### Folded Todos
None — `list-todos` returned zero pending items.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements (MANDATORY before research)
- `.planning/ROADMAP.md` §"Phase 15: Async Background Enrichment" — phase goal, dependencies, 5 success criteria, cross-phase rule (`graph.json` never mutated)
- `.planning/REQUIREMENTS.md` §"Async Background Enrichment (Phase 15)" — 12 REQ-IDs (ENRICH-01..12; 9 P1 + 3 P2)
- `.planning/ROADMAP.md` §"Milestone-level invariants" — D-02 MCP envelope, D-16 alias redirect, D-18 compose-don't-plumb, `graph.json` read-only, `peer_id="anonymous"` default, `security.py` gate

### Critical pitfalls (MUST mitigate)
- `.planning/research/PITFALLS.md` §"Pitfall 3" — Background enrichment overwrites `graph.json`; sidecar + single-writer flock mitigation; grep-CI `_write_graph_json` guard
- `.planning/research/PITFALLS.md` §"Pitfall 4" — Zombie enrichment processes; heartbeat `.enrichment.pid`, `alarm(max_runtime_seconds)`, `atexit` cleanup, no auto-spawn from `/graphify`
- `.planning/research/PITFALLS.md` §"Pitfall 11" — SEED-002 over-exports secrets from enrichment annotations (relevant when Phase 13's harness export reads `enriched_description` fields)

### Cross-phase integration points
- `.planning/phases/12-heterogeneous-extraction-routing/12-CONTEXT.md` §"Routing ↔ Phase 10 batch extraction" — `routing.json` schema, tier classification, `model_id` cache-hash inclusion. Relevant to ENRICH-11 P2 skip-list for description pass.
- `graphify/routing_models.yaml` — tier → model_id map (trivial=Haiku, simple=Sonnet, complex=Opus, vision slot). Enrichment passes reuse these tiers; do not introduce `enrichment_models.yaml`.
- `.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md` (if present) — `serve.py::_run_get_focus_context_core` established the `validate_graph_path(..., base=project_root)` sentinel pattern and D-02 envelope composition. Overlay-merge in `_load_enrichment_overlay` will thread through the same MCP-response path.

### Security & validation gates
- `graphify/security.py` — `validate_graph_path(path, base=...)`, `sanitize_label`, `sanitize_label_md`. Every enrichment I/O routes through `validate_graph_path(base=out_dir)`; every label rendered into enrichment summaries is sanitized.
- `graphify/validate.py` — extraction schema enforcer; reuse validation patterns when defining enrichment-schema guards.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`graphify/cache.py`** — SHA256 content-hash cache. Post-Phase 12, cache keys include `model_id`. Enrichment passes should cache per-(node_id, pass, model_id) so re-runs with the same snapshot_id skip nodes already enriched at the same tier.
- **`graphify/routing.py` + `graphify/routing_models.yaml`** — tier classification (trivial/simple/complex/vision) + model_id map. Description pass can call `routing.resolve_route(file, metrics)` to pick its per-node tier; patterns/community may pick a fixed tier.
- **`graphify/snapshot.py`** — snapshot helpers with Phase 18 CR-01 inline `validate_graph_path(base=project_root)` guards. Enrichment reads snapshots via these helpers; `snapshot_id` pinning (ENRICH-05) uses the same ID scheme.
- **`graphify/serve.py::_reload_if_stale`** — existing mtime-watch pattern for `graph.json`. Extend to watch `enrichment.json` per ENRICH-09.
- **`graphify/watch.py`** — existing post-rebuild hook dispatcher. ENRICH-06 trigger wires in here behind an opt-in `--enrich` flag; do NOT introduce apscheduler or a new daemon subsystem.
- **`graphify/analyze.py`** — community detection + god-node ranking. Community pass composes over existing `cluster.py` / `analyze.py` results; D-18 forbids new plumbing modules for this.

### Established patterns
- **Atomic sidecar writes** — `.tmp` + `os.replace` pattern is used by `routing.json`, `manifest.json`, `dedup.json`. Reuse exactly; do not invent a new write helper.
- **MCP response envelope (D-02)** — `text_body + "\n---GRAPHIFY-META---\n" + json(meta)`. Required for `--dry-run` output per D-04. See Phase 13 `capability_describe` and Phase 18 `get_focus_context` for reference implementations.
- **Alias redirect (D-16)** — every public ID is passed through `_resolve_alias` before storage or lookup. Enrichment writes key by canonical node_id (ENRICH-12). Apply in three places: description-pass write, patterns-pass `nodes: [...]` list, community-pass nodes-per-community resolution.
- **Grep-CI invariant tests** — Phase 12 / 13 / 18 established the test pattern: a test file that runs `grep` over the codebase and asserts a specific call graph. Reuse for SC-5 (`_write_graph_json` caller whitelist).
- **Security-gated file I/O** — every `open(path, ...)` for writing is preceded by `path = validate_graph_path(path, base=out_dir)`. No exceptions.

### Integration points
- **`serve.py::_load_graph`** — runs once at server startup. Overlay merge must happen AFTER `_load_graph` returns (ENRICH-08) so existing test mocks of `_load_graph` stay green.
- **`serve.py::_reload_if_stale`** — currently watches `graph.json` mtime. Extend with an `enrichment.json` mtime watcher (ENRICH-09).
- **`__main__.py` CLI dispatch** — add `graphify enrich` subcommand alongside `run`, `query`, `watch`, `capability`. Match existing argparse conventions (`--budget`, `--graph`, `--pass`, `--dry-run`).
- **`build.py` + `__main__.py`** — ONLY callers of `_write_graph_json`. Enrichment must never touch this function; grep-CI test asserts the whitelist.
- **`cache.py`** — extend hash inputs for enrichment: `(node_id, pass_name, model_id, source_file_hash)`.

</code_context>

<specifics>
## Specific Ideas

- **"graphify runs four derivation passes in the background after each rebuild"** (ROADMAP goal) — mentally this is the "quiet background thread" that improves the graph while the user works, not a new daemon subsystem. Any design that introduces `apscheduler`, a `systemd` unit, or a double-fork+setsid pattern by default is out of step with this framing.
- **"graph.json is never mutated"** — the whole phase hinges on this invariant. The grep-CI test for `_write_graph_json` caller whitelist (SC-5) is the structural enforcement; no process should have to "remember" the rule.
- **`enrichment.json` is the forever-file.** Schema `version: 1` is a commitment — future passes (Phase 17 chat, Phase 16 argumentation) may read/write additional sections, but `passes.description` / `patterns` / `community` / `staleness` keys are stable from Phase 15 forward.
- **Foreground always wins.** If enrichment is running and the user triggers `/graphify`, the enricher drops its lock and SIGTERM-aborts within one pass boundary. Never the other way around.

</specifics>

<deferred>
## Deferred Ideas

- **User-Python deriver plugins** (entry-point model) — REQUIREMENTS.md OOS; revisit post-v1.4 if a real use case emerges.
- **Real-time / pipeline-blocking enrichment** — contradicts Phase 6 delta machinery + Pitfall 3. Permanently out of scope.
- **Implicit enrichment on MCP `get_node`** — no surprise LLM calls in query paths. Agents invoke enrichment explicitly via CLI or event-driven watch hook.
- **Budget-less passes** — all LLM passes must accept `--budget`. No "unlimited" mode.
- **Cross-session chat memory** — that's Phase 17's scope.
- **Additional derivation passes beyond 4** — schema `version: 1` leaves room, but new passes are their own future phase.
- **Per-node intra-pass checkpointing** — considered and rejected under D-07; complexity not justified by token savings on mid-pass aborts.
- **`enrichment_models.yaml`** — considered under budget-policy; rejected in favor of reusing `routing_models.yaml` tiers (no new config surface).

### Reviewed Todos (not folded)
None — todo backlog was empty at discussion time.

</deferred>

---

*Phase: 15-async-background-enrichment*
*Context gathered: 2026-04-20*
