---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Agent Discoverability & Obsidian Workflows
status: in_progress
stopped_at: Phase 18 Plan 02 complete — ready to execute Plan 18-03 (P2 debounce + freshness)
last_updated: "2026-04-20T20:37:11Z"
last_activity: 2026-04-20 — Plan 18-02 shipped (get_focus_context MCP tool + ProjectRoot sentinel + root→project_root rename; 13 tests; FOCUS-01/03/04/05/07 closed); commits 6c63501 / 39a8236 / 1d0169c / b058d37 / 4da9efb.
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-17 on v1.4 milestone open)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended in v1.1 with context persistence and agent memory, in v1.2 with multi-perspective analysis and usage-weighted self-improvement, in v1.3 with token-aware retrieval / entity dedup / interactive slash commands, now being extended in v1.4 to agent discoverability (MCP capability manifest + SEED-002 harness export), Obsidian thinking-command depth, and graph-quality-over-time via heterogeneous routing + async enrichment + focus-aware zoom + grounded chat + SPAR-Kit argumentation.
**Current focus:** Phases 12 + 13 done. v1.4 build order next candidates: **Phase 18** (parallel, no code overlap) or **Phase 15** (soft-depends on 12 routing.json) — pick per capacity; see Build order list below.

## Current Position

Phase: 18 Focus-Aware Graph Context — 🚧 IN PROGRESS (2/3 plans, FOCUS-01/02/03/04/05/06/07 closed). Plans 18-01 resolver ✅ (Wave 1), 18-02 MCP tool + sentinel ✅ (Wave 2), 18-03 P2 debounce + freshness ⏳ (Wave 3).
Plan: Plan 18-02 ✅ COMPLETE (RED 6c63501 → GREEN 39a8236 → RED 1d0169c → GREEN b058d37 → CHORE 4da9efb). Ready to execute Plan 18-03 (P2 debounce + freshness gate).
Milestone: v1.4 Agent Discoverability & Obsidian Workflows — 🚧 STARTED (2026-04-17), 2/7 phases complete, Phase 18 in flight.
Previous milestone: v1.3 Intelligent Analysis Continuation — ✅ SHIPPED 2026-04-17 (phases 9.2 + 10 + 11)
Status: Phase 18 Plan 02 ships the `get_focus_context` MCP tool (pull-model focus → scoped ego-graph + community summary via D-02 envelope), the `ProjectRoot` frozen-dataclass sentinel in snapshot.py (codifies v1.3 CR-01 / Pitfall 20), and the `root`→`project_root` rename across 4 snapshot signatures (load_snapshot unchanged). Binary status invariant (D-03 + D-11) holds: spoofed / unindexed / missing-on-disk paths all yield byte-identical no_context envelopes with no focus_hint echo (D-12). Outer-hop-first budget degradation (D-08) shrinks ego-graph radius before char-clipping. 13 TDD-locked tests pass (10 in test_serve.py, 3 in test_snapshot.py). Full suite: 1320 tests passing (was 1307 → +13 additive).
Last activity: 2026-04-20 — commits 6c63501 (RED snapshot), 39a8236 (GREEN snapshot), 1d0169c (RED serve), b058d37 (GREEN serve), 4da9efb (server.json hash regen) on main; Plan 18-02 SUMMARY.md written; ready for Plan 18-03 execution.

Progress: [███░░░░░░░] 29% (2/7 phases complete — 12 ✅, 13 ✅)

**Build order (locked in SUMMARY.md):**

1. Phase 12 Routing — HARD gates `cache.py` key format — ✅ COMPLETE
2. Phase 18 Focus — parallel with 12, no code overlap — 🚧 IN PROGRESS (Plan 01 ✅, Plans 02+03 pending)
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

- Total plans completed: 38
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

Key v1.4-origin resolutions (from REQUIREMENTS.md OQ locks 2026-04-17):

- **OQ-1 resolved**: Phase 15 ships with NO `apscheduler` dependency — manual + event-driven via `watch.py` post-rebuild hook is sufficient for v1.4.
- **OQ-2 resolved**: Phase 12 routing is per-file only — never per-function (breaks extraction atomicity).
- **OQ-3 resolved**: Phase 13 manifest exists in BOTH locations — `server.json` (MCP registry) + `graphify-out/manifest.json` (live state).
- **OQ-4 resolved**: SEED-002 inverse-import deferred to v1.4.x; v1.4 is export-only.
- **OQ-5 resolved**: SEED-002 ships `claude.yaml` only; other targets deferred to v1.4.x.
- **OQ-6 resolved**: Phase 16 INTERROGATE + persona memory are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).
- **OQ-7 resolved**: Phase 14 `/graphify-voice`, `/graphify-bridge`, `/graphify-drift-notes` are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).

### Blockers/Concerns

None. `gsd-sdk` unavailable in last execution environment — ROADMAP/STATE updated manually.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260416-okg | Add /graphify analyze entries to Usage cheat-sheet in all skill variants | 2026-04-16 | 058152b | [260416-okg-add-graphify-analyze-entries-to-usage-ch](./quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/) |

## Session Continuity

Last session: 2026-04-20T20:10:00.000Z
Stopped at: Phase 18 Plan 01 complete — ready to execute Plan 18-02
Next action: Execute Plan 18-02 (MCP tool `get_focus_context` + `ProjectRoot` sentinel + `snapshot.py` `root→project_root` rename + nested-dir fixture). Helpers from 18-01 (`_resolve_focus_seeds`, `_multi_seed_ego`) are ready for composition. Then Plan 18-03 (P2 debounce + Py 3.10 freshness shim) gated on 18-02. Pitfalls still pre-resolved in Plans 02+03: (1) datetime.fromisoformat Z-suffix → .replace("Z","+00:00") shim; (2) validate_graph_path base=project_root explicit override; (3) construction-time sentinel rejects `path.name == "graphify-out"` per v1.3 CR-01.
