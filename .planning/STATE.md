---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Vault Adapter UX & Template Polish
status: executing
stopped_at: Phase 30 context gathered
last_updated: "2026-04-28T16:07:20.985Z"
last_activity: 2026-04-28 -- Phase 30 planning complete
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 12
  completed_plans: 9
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-27 at v1.6 milestone close)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended through v1.4 (agent discoverability + Obsidian thinking-command depth + graph-quality-over-time), v1.5 (vault promotion CLI + diagram intelligence), and now v1.6 (stability hardening: list-form source_file dedup fix, atomic read-merge-write across 5 manifest writers, drift-locked dual-artifact persistence in all 9 platform skill variants, end-to-end v1.5 walkthrough doc).
**Current focus:** Phase 28 — self-ingestion-hardening

## Deferred Items

Items acknowledged and deferred at v1.6 milestone close on 2026-04-27:

| Category | Item | Status |
|----------|------|--------|
| seed | SEED-001-tacit-knowledge-elicitation-engine | dormant — carry into v1.7; re-evaluate if onboarding/discovery becomes the theme |
| seed | SEED-002-harness-memory-export | dormant — carry into v1.7; multi-harness expansion (codex/letta/honcho/AGENTS.md) + inverse-import deferred pending prompt-injection defenses |
| baseline-test | tests/test_detect.py::test_detect_skips_dotfiles | pre-existing failure on base 24810ec, predates v1.6 — recommend dedicated /gsd-debug session in v1.7 |
| baseline-test | tests/test_extract.py::test_collect_files_from_dir | pre-existing failure on base 24810ec, predates v1.6 — recommend dedicated /gsd-debug session in v1.7 |

Items resolved or carried forward at v1.5 milestone close on 2026-04-27 (historical):

| Category | Item | Status |
|----------|------|--------|
| seed | SEED-001-tacit-knowledge-elicitation-engine | dormant at v1.5 close — carried to v1.6, deferred again |
| seed | SEED-002-harness-memory-export | dormant at v1.5 close — carried to v1.6, deferred again |

Resolved during v1.5 close (removed via `git rm`):

- quick_task `260416-okg-add-graphify-analyze-entries-to-usage-ch` — work shipped, PLAN/SUMMARY removed
- quick_task `260422-jdj-fix-manifest-json-path-collision-between` — work shipped, PLAN/SUMMARY removed
- todo `create-master-keys-work-vault.md` — all 4 master key files created 2026-04-22, todo file removed

Prior carryover from v1.4 close (2026-04-23) — now superseded:

- verification: 13-VALIDATION.md `nyquist_compliant` frontmatter (cosmetic; not blocking v1.5)

## Current Position

Phase: 28 (self-ingestion-hardening) — EXECUTING
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-04-28 -- Phase 30 planning complete

## Performance Metrics

**Velocity (v1.0):**

- Total plans completed: 47
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
- [Phase ?]: promote() returns {promoted, skipped, writeback} enabling idempotent re-runs and structured import-log
- [Phase ?]: validate_vault_path called before every vault write — T-19-03-01/02 path traversal mitigated
- [Phase ?]: _writeback_profile: PyYAML optional guard, returns skipped_no_yaml on ImportError, never crashes pipeline
- [Phase ?]: Phase 20-01: D-18 detection boundary enforced; tag write-back exclusively via graphify.merge.compute_merge_plan
- [Phase ?]: Plan 20-02: seed.py composes god_nodes+detect_user_seeds from analyze.py (D-18); atomic-write + manifest-last pattern lifted from vault_promote.py; --vault opt-in tag write-back via graphify.merge.compute_merge_plan (D-08)
- [Phase ?]: Phase 22 Plan 01: pure-Python Excalidraw fallback (write_diagram + 4 layout helpers + skill prompt) ships; profile schema gains layout_type/output_path; no new required deps; SKILL-06 ordering invariant honored
- [Phase 26]: Phase 26-01 quoted MCP tool source verbatim (mcp_tool_registry.py + serve.py:1234-1250) rather than paraphrasing — guarantees DOCS-03 contract that an agent author can integrate without reading source. — Per RESEARCH §4: the loader's allowlist would reject any new diagram_types[*] keys, and CONTEXT D-05/D-06 thresholds are author policies not loader gates.
- [Phase 26]: Phase 26-01 ships D-05/D-06 policy values (>=3 outbound branches, betweenness centrality) as inline YAML # comments rather than new schema keys. — Profile loader allowlist (graphify/profile.py:106-108 top-level + 367-404 diagram_types[*]) rejects any unknown keys; only min_main_nodes is the loader-enforced gate per seed.py:265-289.
- [Phase ?]: D-29: manifest writes happen ONLY after successful export — --obsidian write in else block post-exit(1); run branch write on try-success path before finally
- [Phase ?]: D-26: always read from resolved.artifacts_dir (stable anchor); notes_dir rename is transparent to prior_files prune (VAULT-13)

### Blockers/Concerns

None. `gsd-sdk` unavailable in last execution environment — ROADMAP/STATE updated manually.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260416-okg | Add /graphify analyze entries to Usage cheat-sheet in all skill variants | 2026-04-16 | 058152b | [260416-okg-add-graphify-analyze-entries-to-usage-ch](./quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/) |
| 260422-jdj | Fix manifest.json path collision between capability.py and detect.py | 2026-04-22 | 9a52fa7 | [260422-jdj-fix-manifest-json-path-collision-between](./quick/260422-jdj-fix-manifest-json-path-collision-between/) |
| 260427-rc7 | Fix detect.py self-ingestion: prune graphify-out/ from default scan to stop nested obsidian export loop | 2026-04-28 | 59d8b2f | [260427-rc7-fix-detect-self-ingestion](./quick/260427-rc7-fix-detect-self-ingestion/) |
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
| Phase 19 P02 | 6 min | 2 tasks | 2 files |
| Phase 19 P03 | 374 | 2 tasks | 3 files |
| Phase 19 P04 | 12m | 2 tasks | 6 files |
| Phase 20 P20-01 | 282 | 2 tasks | 2 files |
| Phase 20 P20-02 | 671 | 2 tasks | 4 files |
| Phase 22 P01 | 30min | 5 tasks | 6 files |
| Phase 22 P02 | 5min | 1 tasks | 3 files |
| Phase 24-manifest-writer-audit-atomic-read-merge-write-hardening P02 | 150 | 1 tasks | 1 files |
| Phase 26 P01 | 237 | 3 tasks | 4 files |
| Phase 28-self-ingestion-hardening P03 | 383 | 3 tasks | 3 files |

## Session Continuity

Last session: 2026-04-28T15:33:20.939Z
Stopped at: Phase 30 context gathered
Next action: /gsd-plan-phase 20 to plan Phase 20 (Diagram Seed Engine).
