---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Agent Discoverability & Obsidian Workflows
status: executing
stopped_at: Completed 15-06-PLAN.md (Phase 15 complete — all 6 plans shipped)
last_updated: "2026-04-22T17:37:35.209Z"
last_activity: 2026-04-22
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 20
  completed_plans: 20
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-17 on v1.4 milestone open)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended in v1.1 with context persistence and agent memory, in v1.2 with multi-perspective analysis and usage-weighted self-improvement, in v1.3 with token-aware retrieval / entity dedup / interactive slash commands, now being extended in v1.4 to agent discoverability (MCP capability manifest + SEED-002 harness export), Obsidian thinking-command depth, and graph-quality-over-time via heterogeneous routing + async enrichment + focus-aware zoom + grounded chat + SPAR-Kit argumentation.
**Current focus:** Phase 15 — async-background-enrichment

## Current Position

Phase: 18
Plan: Not started
Milestone: v1.4 Agent Discoverability & Obsidian Workflows — 🚧 STARTED (2026-04-17), 3/7 phases complete (12 ✅ + 13 ✅ + 18 ✅), Phase 15 next.
Previous milestone: v1.3 Intelligent Analysis Continuation — ✅ SHIPPED 2026-04-17 (phases 9.2 + 10 + 11)
Status: Ready to execute
Last activity: 2026-04-22

Progress: [██████░░░░] 43% (3/7 phases complete — 12 ✅, 13 ✅, 18 ✅)

**Build order (locked in SUMMARY.md):**

1. Phase 12 Routing — HARD gates `cache.py` key format — ✅ COMPLETE
2. Phase 18 Focus — parallel with 12, no code overlap — ✅ COMPLETE (4/4 plans, verified 2026-04-20)
3. Phase 13 Wave A — plumbing (manifest generator + CLI + `capability_describe` tool) — ✅ COMPLETE
4. Phase 15 Enrichment — soft-depends on 12 routing.json — ⏳ next candidate
5. Phase 17 Chat — soft-depends on 18 + 15
6. Phase 16 Argumentation — soft-depends on 17 citation format; MUST NOT call 17
7. Phase 14 Obsidian Commands — HARD-depends on 18 + Plan 00 whitelist refactor
8. Phase 13 Wave B final regen — manifest final sweep after 14–18 land (no new plan IDs; just a regeneration pass)
9. SEED-002 hardening — ✅ COMPLETE (shipped with Phase 13 Plan 03 + Plan 04)

**Seeds activated in v1.4:**

- SEED-002 Harness Memory Export — bundled under Phase 13 Wave B (claude.yaml only; export-only)

**Seeds still planted:**

- SEED-001 Tacit Elicitation Engine — re-evaluate at v1.5 if onboarding/discovery becomes the milestone theme

## Performance Metrics

**Velocity (v1.0):**

- Total plans completed: 44
- Total tests: 872 passing
- Timeline: 2 days (2026-04-09 → 2026-04-11)
- Commits in milestone: ~172

**Velocity (v1.1):**

- Total plans completed: 12
- Total tests: 1,000 passing
- Timeline: 2 days (2026-04-12 → 2026-04-13)
- Commits in milestone: ~117

**Velocity (v1.2):**

- Total plans completed: 9 (3 for Phase 09 autoreason tournament, 3 for Phase 09.1 query telemetry, 3 for Phase 9.1.1 lifecycle cleanup)
- Total tests after milestone: ~1,108 passing
- Timeline: 2 days (2026-04-14 → 2026-04-15) + 1 day planning-only cleanup
- Commits in milestone: ~20 feature commits

**Velocity (v1.3):**

- Total plans completed: 19 (3 for Phase 9.2, 9 for Phase 10, 7 for Phase 11)
- Total tests after milestone: 1,234 passing (+211 over v1.2)
- Timeline: 2 days (2026-04-16 → 2026-04-17)
- Commits in milestone: ~178 (range e60d757–64e8475); +24,057 / −161 lines across 108 files

Detailed per-plan metrics are preserved in phase SUMMARY.md files and in milestone archives (`.planning/milestones/v1.N-*`).

## Accumulated Context

### Decisions

All milestone decisions are archived in:

- **PROJECT.md Key Decisions table** — architectural decisions (D-73, D-74)
- **`.planning/milestones/v1.0-MILESTONE-AUDIT.md`** — v1.0 decision trail
- **`.planning/milestones/v1.1-MILESTONE-AUDIT.md`** — v1.1 decision trail
- **`.planning/milestones/v1.2-MILESTONE-AUDIT.md`** — v1.2 decision trail
- **`.planning/milestones/v1.3-ROADMAP.md`, v1.3-REQUIREMENTS.md** — v1.3 decision trail
- **Phase SUMMARY.md files** — tactical decisions locked during plan execution

Key carry-forward decisions (affect v1.4):

- **D-73**: CLI is utilities-only; skill drives the full pipeline
- **D-74**: `to_obsidian()` is a notes pipeline, not a vault-config-file manager
- **`graph.json` is read-only** — agent state lives in JSONL/JSON sidecars
- **`peer_id` defaults to `"anonymous"`** — never derived from environment (security carry-forward)
- **User sentinel blocks are inviolable** — even under REPLACE strategy
- **D-02 (Phase 9.2)**: MCP responses use hybrid `text_body + SENTINEL + json(meta)` envelope with status codes — all future MCP tools inherit (applies to Phase 13 manifest + Phase 16 `argue_topic` + Phase 17 `chat` + Phase 18 `get_focus_context`)
- **D-16 (Phase 10)**: MCP `query_graph` transparently redirects merged-away aliases — agent callsites preserved across dedup (applies to Phases 15, 16, 17, 18)
- **D-18 (Phase 11)**: New MCP tools should compose existing `analyze.py` / `delta.py` / `snapshot.py` primitives — no new graphify/ modules for plumbing; new analysis algorithms get their own phase (applies to Phase 15 `enrich.py`, Phase 16 `argue.py`, Phase 17 chat plumbing, Phase 18 focus handler)
- **Plan 18-01 (2026-04-20)**: Focus resolver lives as two module-private helpers in `graphify/serve.py` (`_resolve_focus_seeds`, `_multi_seed_ego`). Multi-seed ego-graph MUST use `nx.compose_all([nx.ego_graph(G, s, r) for s in seeds])` — never multi-seed `nx.ego_graph(G, [seeds], r)` which raises `NodeNotFound` in NetworkX 3.x. `source_file: str | list[str]` handling delegates to `analyze._iter_sources` (never inline `isinstance` checks).
- **Plan 18-02 (2026-04-20)**: `get_focus_context` MCP tool composes the Plan 18-01 resolver into a D-02 envelope. Binary status invariant (D-03 + D-11): only `{ok, no_context}` — no intermediate `no_graph` / `insufficient_history` statuses; missing graph collapses to no_context. Path confinement MUST pass `base=project_root` explicitly (default `graphify-out/` rejects all legitimate source files); relative `file_path` resolved against project_root BEFORE validate_graph_path (Path.resolve uses CWD, not base). Silent-ignore catches BOTH `ValueError` AND `FileNotFoundError` (T-18-A + T-18-B). No focus_hint echo in no_context envelope (D-12 / T-18-D). Outer-hop-first budget degradation (D-08): shrink ego-graph radius before char-clipping.
- **Plan 18-02 (2026-04-20)**: `ProjectRoot(path: Path)` frozen-dataclass sentinel in `graphify/snapshot.py` codifies v1.3 CR-01 (Pitfall 20). Construction fails fast when `path.name == "graphify-out"`. `snapshot.py` public API renamed `root` → `project_root` across 4 signatures (`snapshots_dir`, `list_snapshots`, `save_snapshot`, `auto_snapshot_and_delta`); `load_snapshot(path)` unchanged. All repo callers migrated; `make_snapshot_chain` fixture retains `root=` alias for backwards-compat only.
- **Plan 18-03 (2026-04-20)**: Two P2 dispatch-layer guards wrap `_run_get_focus_context_core` in `_tool_get_focus_context`. FOCUS-08 debounce: module-level `_FOCUS_DEBOUNCE_CACHE` keyed on 5-tuple `(file_path, function_name, line, depth, include_community)`; `time.monotonic()` (NOT `time.time()` — immune to NTP / suspend-resume per D-14); 500ms window; bounded LRU at 256 entries, evict oldest 64 on overflow (Pitfall 6 DoS cap). FOCUS-09 freshness: `_check_focus_freshness(reported_at, now=None)` — absent = True (D-15 backward compat); 300s window; Py 3.10 `.replace("Z","+00:00")` compat shim BEFORE `datetime.fromisoformat` (Pitfall 2 — Py 3.11+ accepts Z natively but CI matrix includes 3.10). Wrapper routes: freshness-gate FIRST → debounce-get → core → debounce-put. Both rejections collapse to the 4-key no_context envelope (D-03/D-11 binary invariant). Cache stores core output pre-manifest-merge per Pitfall 7 (byte-identical replay across `_merge_manifest_meta`).

Key v1.4-origin resolutions (from REQUIREMENTS.md OQ locks 2026-04-17):

- **OQ-1 resolved**: Phase 15 ships with NO `apscheduler` dependency — manual + event-driven via `watch.py` post-rebuild hook is sufficient for v1.4.
- **OQ-2 resolved**: Phase 12 routing is per-file only — never per-function (breaks extraction atomicity).
- **OQ-3 resolved**: Phase 13 manifest exists in BOTH locations — `server.json` (MCP registry) + `graphify-out/manifest.json` (live state).
- **OQ-4 resolved**: SEED-002 inverse-import deferred to v1.4.x; v1.4 is export-only.
- **OQ-5 resolved**: SEED-002 ships `claude.yaml` only; other targets deferred to v1.4.x.
- **OQ-6 resolved**: Phase 16 INTERROGATE + persona memory are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).
- **OQ-7 resolved**: Phase 14 `/graphify-voice`, `/graphify-bridge`, `/graphify-drift-notes` are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).
- [Phase ?]: Plan 15-03: D-05 envelope schema strict-check; D-07 resume-by-default with per-pass skip gate; staleness exempt from D-03 budget
- [Phase ?]: 15-04: overlay in-memory; graph.json never mutated
- [Phase ?]: Plan 15-05: Foreground always wins; watch --enrich is strictly opt-in; atexit+running-child guard prevents zombies

### Blockers/Concerns

None. `gsd-sdk` unavailable in last execution environment — ROADMAP/STATE updated manually.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260416-okg | Add /graphify analyze entries to Usage cheat-sheet in all skill variants | 2026-04-16 | 058152b | [260416-okg-add-graphify-analyze-entries-to-usage-ch](./quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/) |
| Phase 15 P04 | 18 | 2 tasks | 2 files |
| Phase 15 P05 | 15 | 2 tasks | 4 files |
| Phase 15 P06 | 15 | 2 tasks | 5 files (3 new tests + enrich.py + test_enrich.py) |

## Session Continuity

Last session: 2026-04-22T17:25:33.532Z
Stopped at: Completed 15-06-PLAN.md (Phase 15 complete — all 6 plans shipped)
Next action: Pick next phase from v1.4 build order. Per locked sequence (12 ✅ → 18 ✅ → 13A ✅ → 15 ✅ → 17 → 16 → 14 → 13B + SEED-002), **Phase 17 Conversational Graph Chat** is the recommended candidate (soft-depends on 18 ✅ + 15 ✅). Alternative: Phase 14 Obsidian Commands (HARD-depends on 18 ✅ + Plan 00 whitelist refactor). Start with `/gsd-discuss-phase 17` or `/gsd-plan-phase 17`.
