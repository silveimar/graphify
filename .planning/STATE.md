---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Agent Discoverability & Obsidian Workflows
status: Roadmap complete — ready to plan Phase 12
stopped_at: v1.4 roadmap written; 86 REQ-IDs mapped to 7 phases (100% coverage); Phase 13 bundles SEED-002 via two-wave execution
last_updated: "2026-04-17T19:45:00.000Z"
last_activity: 2026-04-17
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-17 on v1.4 milestone open)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended in v1.1 with context persistence and agent memory, in v1.2 with multi-perspective analysis and usage-weighted self-improvement, in v1.3 with token-aware retrieval / entity dedup / interactive slash commands, now being extended in v1.4 to agent discoverability (MCP capability manifest + SEED-002 harness export), Obsidian thinking-command depth, and graph-quality-over-time via heterogeneous routing + async enrichment + focus-aware zoom + grounded chat + SPAR-Kit argumentation.
**Current focus:** v1.4 roadmap locked. Next step is `/gsd-discuss-phase 12` or `/gsd-plan-phase 12` to begin Heterogeneous Extraction Routing (the HARD gate for `cache.py` key format).

## Current Position

Phase: Not started (roadmap complete; Phase 12 ready to plan)
Plan: —
Milestone: v1.4 Agent Discoverability & Obsidian Workflows — 🚧 STARTED (2026-04-17)
Previous milestone: v1.3 Intelligent Analysis Continuation — ✅ SHIPPED 2026-04-17 (phases 9.2 + 10 + 11)
Status: Roadmap complete, awaiting Phase 12 planning
Last activity: 2026-04-17 — v1.4 ROADMAP.md written with 7 phases, 86 REQ-IDs mapped

Progress: [░░░░░░░░░░] 0% (0/7 phases complete)

**Build order (locked in SUMMARY.md):**
1. Phase 12 Routing — HARD gates `cache.py` key format
2. Phase 18 Focus — parallel with 12, no code overlap
3. Phase 13 Wave A — plumbing (manifest generator + CLI + `capability_describe` tool)
4. Phase 15 Enrichment — soft-depends on 12 routing.json
5. Phase 17 Chat — soft-depends on 18 + 15
6. Phase 16 Argumentation — soft-depends on 17 citation format; MUST NOT call 17
7. Phase 14 Obsidian Commands — HARD-depends on 18 + Plan 00 whitelist refactor
8. Phase 13 Wave B + SEED-002 — final manifest regen with full surface

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

Key v1.4-origin resolutions (from REQUIREMENTS.md OQ locks 2026-04-17):

- **OQ-1 resolved**: Phase 15 ships with NO `apscheduler` dependency — manual + event-driven via `watch.py` post-rebuild hook is sufficient for v1.4.
- **OQ-2 resolved**: Phase 12 routing is per-file only — never per-function (breaks extraction atomicity).
- **OQ-3 resolved**: Phase 13 manifest exists in BOTH locations — `server.json` (MCP registry) + `graphify-out/manifest.json` (live state).
- **OQ-4 resolved**: SEED-002 inverse-import deferred to v1.4.x; v1.4 is export-only.
- **OQ-5 resolved**: SEED-002 ships `claude.yaml` only; other targets deferred to v1.4.x.
- **OQ-6 resolved**: Phase 16 INTERROGATE + persona memory are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).
- **OQ-7 resolved**: Phase 14 `/graphify-voice`, `/graphify-bridge`, `/graphify-drift-notes` are P2 in v1.4 scope (not deferred — user confirmed P1+P2 complete 2026-04-17).

### Blockers/Concerns

None. Phase 12 ready to plan.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260416-okg | Add /graphify analyze entries to Usage cheat-sheet in all skill variants | 2026-04-16 | 058152b | [260416-okg-add-graphify-analyze-entries-to-usage-ch](./quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/) |

## Session Continuity

Last session: 2026-04-17T19:45:00.000Z
Stopped at: v1.4 roadmap written — 7 phases, 86 REQ-IDs mapped (100% coverage), Phase 13 bundles SEED-002 via Wave A (plumbing, 3rd in build order) + Wave B (final regen, 8th in build order); build order locked per SUMMARY.md; cross-phase rules locked (D-02 envelope, D-16 alias, D-18 compose, Phase 16→17 forbidden composition, Phase 18 codifies v1.3 CR-01 snapshot-root rename, Phase 14 Plan 00 whitelist refactor gates new commands).
Next action: `/gsd-discuss-phase 12 ${GSD_WS}` or `/gsd-plan-phase 12 ${GSD_WS}` to begin Heterogeneous Extraction Routing (the HARD gate for `cache.py` key format).
