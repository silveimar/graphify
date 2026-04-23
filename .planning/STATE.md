---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Diagram Intelligence & Excalidraw Bridge
status: executing
stopped_at: Phase 19 context gathered
last_updated: "2026-04-23T06:00:33.356Z"
last_activity: 2026-04-23
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 1
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-23 at v1.4 milestone close)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended in v1.1 with context persistence and agent memory, in v1.2 with multi-perspective analysis, in v1.3 with token-aware retrieval / entity dedup / interactive slash commands, and in v1.4 (shipped 2026-04-22) with agent discoverability (MCP capability manifest + SEED-002 harness export), Obsidian thinking-command depth, and graph-quality-over-time via heterogeneous routing + async enrichment + focus-aware zoom + grounded chat + SPAR-Kit argumentation. v1.5 extends to vault promotion (Phase 19) and diagram intelligence (Phases 20–22).
**Current focus:** Phase 19 — Vault Promotion Script (Layer B)

## Deferred Items

Items acknowledged and deferred at v1.4 milestone close on 2026-04-23:

| Category | Item | Status |
|----------|------|--------|
| verification | 13-VALIDATION.md `nyquist_compliant: false` frontmatter | cosmetic — guard test exists (commit `59298c8`); rerun `/gsd-validate-phase 13` to flip flag |
| quick_task | 260416-okg-add-graphify-analyze-entries-to-usage-ch | missing |
| quick_task | 260422-jdj-fix-manifest-json-path-collision-between | missing |
| todo | create-master-keys-work-vault.md | pending — files exist in vault; move to `completed/` when verified |
| seed | SEED-001-tacit-knowledge-elicitation-engine | dormant — re-evaluate at v1.6 if onboarding/discovery becomes the theme |
| seed | SEED-002-harness-memory-export | dormant — claude.yaml shipped in v1.4; multi-harness expansion (codex/letta/honcho/AGENTS.md) + inverse-import deferred pending prompt-injection defenses |

## Current Position

Phase: 19 (Vault Promotion Script (Layer B)) — EXECUTING
Plan: 2 of 4
Milestone: v1.5 Diagram Intelligence & Excalidraw Bridge — 🚧 STARTED (2026-04-22), 0/4 phases complete (Phase 19 pulled in from v1.4 2026-04-23)
Previous milestone: v1.4 Agent Discoverability & Obsidian Workflows — ✅ SHIPPED 2026-04-22 (phases 12–18, 32 plans, 86/86 requirements)
Status: Ready to execute
Last activity: 2026-04-23

Progress: [░░░░░░░░░░] 0% (0/3 phases complete)

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
- [Phase ?]: Plan 17-02: Composer is template slot-fill only (zero LLM)
- [Phase ?]: Plan 17-02: Fuzzy suggestions restricted to graph candidate pool (T-17-02 anti-echo)
- [Phase ?]: Plan 17-02: 500-token cap via char/4 heuristic with sentence-boundary ellipsis
- [Phase 17]: Plan 17-03: Chat citations canonical-post-dedup via `_resolve_alias` threading (CHAT-07 / D-16 / T-17-05)
- [Phase 17]: Plan 17-03: `/graphify-ask` follows connect.md frontmatter convention — no `target:` field (CONTEXT.md Clarification)
- [Phase 17]: Plan 17-03: Zero-LLM invariant enforced structurally via grep-on-source (CHAT-03 SC4 architectural test)
- [Phase ?]: D-14/D-15/D-16: argue_topic D-02 envelope with composable_from:[] recursion guard; resolved_from_alias (not alias_redirects)
- [Phase ?]: Phase 14-01: target frontmatter uses stdlib re-module (no PyYAML); missing target defaults to both for back-compat
- [Phase ?]: Phase 14-01: _PLATFORM_CONFIG supports is capability intent list, never a filename whitelist — TM-14-02 defense
- [Phase 14]: Plan 14-02: /graphify-moc ships as skill-only markdown (no Python); trust boundary (TM-14-01) enforced at test-time via grep denylist of direct-write patterns (Path.write_text, write_note_directly, open('w'))
- [Phase ?]: Phase 14 Plan 03: /graphify-related read-only; explicit no_context branch mitigates TM-14-03.
- [Phase ?]: Phase 14 Plan 04: /graphify-orphan read-only by design — OBSCMD-08 propose_vault_note intentionally N/A
- [Phase ?]: Phase 14 Plan 04: enrichment.json treated as OPTIONAL Phase 15 overlay — absence renders graceful banner
- [Phase 14]: Phase 14 Plan 05: /graphify-wayfind shipped; cross-command trust-boundary invariant codified across all P1 write commands

### Blockers/Concerns

None. `gsd-sdk` unavailable in last execution environment — ROADMAP/STATE updated manually.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260416-okg | Add /graphify analyze entries to Usage cheat-sheet in all skill variants | 2026-04-16 | 058152b | [260416-okg-add-graphify-analyze-entries-to-usage-ch](./quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/) |
| 260422-jdj | Fix manifest.json path collision between capability.py and detect.py | 2026-04-22 | 9a52fa7 | [260422-jdj-fix-manifest-json-path-collision-between](./quick/260422-jdj-fix-manifest-json-path-collision-between/) |
| Phase 15 P04 | 18 | 2 tasks | 2 files |
| Phase 15 P05 | 15 | 2 tasks | 4 files |
| Phase 15 P06 | 15 | 2 tasks | 5 files (3 new tests + enrich.py + test_enrich.py) |
| Phase 17 P01 | 15m | 2 tasks | 4 files |
| Phase 17 P02 | 10 | 2 tasks | 2 files |
| Phase 17 P03 | 12m | 2 tasks | 4 files (ask.md + serve.py + 2 test files) |
| Phase 16 P03 | 8m | 2 tasks | 3 files |
| Phase 16 P02 | 7m | 2 tasks | 5 files |
| Phase 14 P01 | 253 | 2 tasks | 12 files |
| Phase 14 P02 | 187 | 2 tasks | 2 files |
| Phase 14 P03 | 164 | 2 tasks | 2 files |
| Phase 14 P04 | 5 | 2 tasks | 2 files |
| Phase 14 P05 | 180 | 2 tasks | 2 files |

## Session Continuity

Last session: 2026-04-23T06:00:33.353Z
Stopped at: Phase 19 context gathered
Next action: /gsd-plan-phase 20 to plan Phase 20 (Diagram Seed Engine).
