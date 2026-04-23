# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Ideaverse Integration — Configurable Vault Adapter

**Shipped:** 2026-04-11
**Phases:** 5 | **Plans:** 22 | **Timeline:** 2 days (2026-04-09 → 2026-04-11)

### What Was Built

- **`graphify/profile.py`** — Vault-side profile loading (`.graphify/profile.yaml`) with deep-merge over built-in `_DEFAULT_PROFILE`, schema validation returning `list[str]` of actionable errors, path-traversal guard, and safety helpers (`safe_filename` with NFC + 200-char cap, `safe_tag`, `safe_frontmatter_value`).
- **`graphify/templates.py`** — Six built-in note types rendered via `string.Template.safe_substitute` + two-phase Dataview wrap. User template overrides in `.graphify/templates/` with built-in fallback on error. No Jinja2 dependency.
- **`graphify/mapping.py`** — First-match-wins classification with attribute > topology > default precedence. `compile_rules`, `_match_when`, `_detect_dead_rules`, `validate_rules`. Community-to-MOC threshold with below-threshold sub-community callouts.
- **`graphify/merge.py`** — `compute_merge_plan` (pure, returns `MergePlan` with CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN actions) and `apply_merge_plan` (atomic `.tmp` + fsync + `os.replace`). 14-key built-in field-policy table. Hand-rolled YAML frontmatter reader as strict inverse of `_dump_frontmatter`. D-67 sentinel blocks for graphify-owned body regions. Content-hash skip for idempotent re-runs. Four configurable merge strategies.
- **Refactored `graphify/export.py::to_obsidian()`** — Single orchestration point wiring profile + mapping + templates + merge. Backward-compatible when no vault profile exists. Returns `MergeResult` (live) or `MergePlan` (dry-run).
- **CLI additions** — `graphify --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run]` and `graphify --validate-profile <vault-path>` in `__main__.py:691-740`. `format_merge_plan` + `split_rendered_note` public helpers in `merge.py`.
- **Pre-existing bug fixes** — FIX-01 (YAML frontmatter injection), FIX-02 (nondeterministic filename dedup), FIX-03 (shallow tag sanitization), FIX-04 (NFC Unicode normalization), FIX-05 (filename length cap). All in Phase 1 Plan 2.

### What Worked

- **4-phase parallelization then integration**: Phases 1, 2, 3, 4 were scoped to be independently buildable (only Phase 3 depends on Phase 1), and Phase 5 wired them together. This let each phase land cleanly before wiring touched all four at once. The integration phase was the longest but had the fewest surprises because upstream phases had already verified their public APIs.
- **Pure-function merge engine**: Keeping `compute_merge_plan` a read-only pure function with `apply_merge_plan` as the atomic writer made dry-run a trivial addition in Phase 5 (literally `if dry_run: return plan`) and made the 7-fixture test suite much easier to write. The "plan" is the contract; the "apply" is the side effect.
- **Hand-rolled YAML reader as strict inverse of writer**: Instead of using PyYAML for both read and write, the merge engine hand-rolls a reader that's a byte-level inverse of `_dump_frontmatter`. This guarantees field-order preservation (MRG-06) by construction, not by testing.
- **3-source cross-reference in milestone audit**: Cross-referencing REQUIREMENTS.md × Phase VERIFICATION.md × SUMMARY frontmatter × integration trace caught OBS-01/OBS-02 as a real scope change that would have slipped past a checkbox-only review.
- **Atomic executor commits per plan task**: Each executor committed one plan task at a time, which made `git bisect` and plan-level audit trivial. Never had to recover from a half-applied plan.

### What Was Inefficient

- **Phase 01 shipped without VERIFICATION.md**: The phase pipeline ran but the goal-backward verification step was skipped. The milestone audit caught it 2 days later. Had verification run at the time, OBS-01/OBS-02 would have been flagged as "requirement survived but feature was removed" during Phase 05 verification — two days earlier.
- **SUMMARY.md frontmatter schema drift**: 5 phases used 3 different field names for requirements (`requirements-completed:`, `requirements:`, `requirements_closed:`), and Phase 02 + Phase 05 omitted the field entirely. The milestone audit had to reconstruct requirement coverage from VERIFICATION.md tables instead of trusting SUMMARY frontmatter. Should have standardized on one name from Phase 01.
- **Parallel worktree + untracked plan files**: 6 Phase 05 PLAN files were never committed to git even though their SUMMARY files were. The parallel-worktree executor pattern commits within worktrees, and the planner-side plans were produced on the main working tree and left untracked. Caught at the pre-archival cleanup, but could have silently orphaned 3,468 lines of planning artifacts.
- **`.gitignore` EOL housekeeping buried in git status**: A trivial "no newline at end of file" diff sat in the working tree as `M .gitignore` for an entire phase session, making the `git status` output noisy enough that the untracked PLAN files were harder to notice.
- **Scope-change accounting was manual**: D-74 removed `.obsidian/graph.json` generation, but nobody updated REQUIREMENTS.md to mark OBS-01/OBS-02 as out-of-scope. The test file even has a regression-anchor comment explaining the removal — but that comment lived in test code, not in the authoritative requirements log. The milestone audit was the first place the disagreement surfaced.

### Patterns Established

- **Verification artifact hierarchy**: `UAT.md` (user-observable behavior) is distinct from `VERIFICATION.md` (goal-backward evidence); both are distinct from `SUMMARY.md` (what the plan claimed to deliver). Phase 01 demonstrated that `UAT.md` alone is not a substitute for `VERIFICATION.md` at milestone-audit time — the 3-source cross-reference needs both.
- **Scope-change decision logging**: Any time a later phase removes or de-scopes a feature from an earlier phase, record it in PROJECT.md Key Decisions AND update REQUIREMENTS.md Out of Scope table AND add a regression anchor test. D-74 is now the canonical example.
- **Audit runs as a feedback loop**: Milestone audits are not a single fire-and-forget check. Run #1 surfaces gaps. Gaps get reconciled (scope changes logged, bookkeeping fixed, retroactive verifications run). Run #2 confirms the clean state. This matches the phase-level discuss→plan→execute→verify loop at the milestone scale.
- **Integration-checker trace is cacheable**: The `gsd-integration-checker` agent's findings are deterministic over source code. If no `graphify/` or `tests/` files changed between audit runs, the trace can be reused without re-spawning. Transparent reuse (with an explicit "run #1 findings" note in the report) saves ~200k tokens per re-run.
- **Retroactive VERIFICATION.md works**: Phase 01's retroactive verification (via `/gsd-verify-work 01` + direct VERIFICATION.md write at the end) successfully closed an evidence gap 2 days after the phase shipped. The pattern is reusable for any phase that missed the verification step at execution time.

### Key Lessons

1. **Run phase verification at phase completion time, not later.** Every phase must end with a `VERIFICATION.md` artifact, even if the phase "looks fine". Phase 01 is the counter-example — it delivered successfully but left the milestone audit carrying the load of verification 2 days later. Make `VERIFICATION.md` a precondition for `/gsd-next` advancing past a phase.
2. **Standardize SUMMARY.md frontmatter field names in templates.** Pick one canonical name (`requirements_completed:` is the most common) and enforce it in the executor template. Validate in `gsd-tools summary-extract` with a clear error message on missing/mismatched fields.
3. **Every de-scope needs three coordinated updates.** REQUIREMENTS.md (move to Out of Scope), PROJECT.md Key Decisions (log the D-xx decision), and a regression anchor test (preserve the invariant that survived the removal). Miss any one and the drift surfaces at milestone audit time.
4. **Always audit twice.** The 1→reconcile→2 pattern is the milestone equivalent of the phase verify→plan→execute loop. Budget for it.
5. **Parallel worktree executors need a "plans are tracked" post-condition.** Add a check to `execute-phase` that fails if any `*-PLAN.md` file in the phase directory is untracked after the phase completes.
6. **Integration-checker findings are cacheable and reusable.** Document this in the workflow so future audit runs can skip the re-spawn when only `.planning/` files changed.

### Cost Observations

- **Model mix:** ~10% opus (orchestration, audits, decision points), ~85% sonnet (plan execution via subagents, code review fixes), ~5% haiku (trivial commits, state reads). Opus was reserved for audit runs, cross-phase planning, and the milestone-complete workflow itself.
- **Sessions:** ~4-5 distinct working sessions across 2 days. Most phases landed in a single session; the milestone-complete session handled audit reconciliation end-to-end.
- **Notable:** Reusing the integration-checker trace in audit run #2 saved ~200k tokens and ~3 minutes. The retroactive Phase 01 verification took ~15 minutes of orchestrator time and fully closed the evidence gap — a strong cost/value ratio for the audit cleanup.

---

## Milestone: v1.1 — Context Persistence & Agent Memory

**Shipped:** 2026-04-13
**Phases:** 5 (6–8.2) | **Plans:** 12 | **Timeline:** 2 days (2026-04-12 → 2026-04-13)

### What Was Built

- **`graphify/snapshot.py`** — Atomic save/load/prune/list for graph snapshots in `graphify-out/snapshots/`. FIFO retention pruning on every save. `node_link_data`/`node_link_graph` for NetworkX serialization.
- **`graphify/delta.py`** — Set-arithmetic graph diff (`compute_delta`), three-state staleness classification (`classify_staleness`: FRESH/STALE/GHOST), and `GRAPH_DELTA.md` rendering with summary+archive pattern. Mtime fast-gate skips SHA256 when mtime unchanged.
- **Provenance metadata in `extract.py`** — `extracted_at`, `source_hash`, `source_mtime` injected per-file in `_extract_generic` (computed once per file, not per node).
- **MCP mutation tools in `serve.py`** — `annotate_node`, `flag_node`, `add_edge`, `propose_vault_note`, `get_annotations` with JSONL append persistence, peer identity tracking, mtime-based graph reload, and startup compaction. Module-level helper functions for testability without MCP server.
- **`graphify approve` CLI** — Human-in-the-loop proposal review: list/approve/reject/batch. Indirection helpers for monkeypatching in tests. Proposal lifecycle: approve writes to vault via merge engine, then deletes proposal file.
- **Vault manifest round-trip in `merge.py`** — `vault-manifest.json` with content-only SHA256 hashes. User-modified detection on re-run. `SKIP_PRESERVE` action for modified notes. User sentinel blocks (`GRAPHIFY_USER_START/END`) — inviolable even for REPLACE strategy. `--force` flag bypasses whole-note detection while respecting sentinels.
- **MCP query enhancements** — `get_node` surfaces provenance + staleness classification. `get_agent_edges` with peer/session/node filtering.
- **Skill pipeline wiring** — `auto_snapshot_and_delta()` called at both full-pipeline and cluster-only paths in `skill.md`.

### What Worked

- **Module-level helper pattern for MCP testability**: Extracting record builders (`_make_annotate_record`, `_make_flag_record`, etc.) and filters (`_filter_annotations`, `_filter_agent_edges`) as module-level functions made it possible to write unit tests without spinning up an MCP server. Same pattern applied to approve helpers via indirection wrappers. This yielded 57 new tests for serve.py alone.
- **TDD red-green throughout**: Every phase used strict test-first development. Phase 8's merge engine extensions (33 new tests) caught 3 edge cases in sentinel block parsing that would have been integration-time surprises.
- **Decimal phase numbering for gap closure**: Phases 8.1 and 8.2 were inserted after the milestone audit identified integration gaps (INT-01 through INT-04). The decimal numbering kept the roadmap coherent without renumbering existing phases.
- **Milestone audit before completion**: Running `/gsd-audit-milestone` before `/gsd-complete-milestone` caught 4 integration gaps (2 high, 2 low severity) and resulted in 2 gap-closure phases that strengthened the milestone. The audit-then-fix-then-re-audit pattern from v1.0 continued to pay off.
- **Sidecar-only mutation invariant**: The hard rule that `graph.json` is never mutated by MCP tools eliminated an entire class of data-loss bugs. Agent state in `annotations.jsonl` and `agent-edges.json` can be freely rewritten without risking pipeline ground truth.

### What Was Inefficient

- **SUMMARY.md one-liner extraction still fragile**: The `gsd-tools summary-extract` command pulled incomplete one-liners for several plans (showed "One-liner:" or "Sidecar persistence:" without the actual content). The MILESTONES.md entry had to be manually rewritten. Same issue as v1.0's SUMMARY frontmatter schema drift — the field names are present but the extraction logic doesn't reliably find the value.
- **STATE.md accumulated context grew large**: By Phase 8.2, the Accumulated Context section had 50+ lines of phase-specific decisions that were useful during execution but became noise after completion. Could have been pruned at each phase transition.
- **WIRING-01 (approve manifest hardcoded path) survived to audit**: The `_approve_and_write_proposal` function hardcodes `Path('graphify-out')` for the manifest path. This was flagged as low severity in the audit but not fixed — it silently degrades when `--out-dir` is overridden. Should have been caught during Phase 7 Plan 3 code review.

### Patterns Established

- **Sidecar persistence pattern**: Agent state in append-only JSONL (annotations) or atomic-write JSON (agent-edges, proposals). Pipeline ground truth (`graph.json`) is read-only. This is the canonical pattern for any future MCP mutation tools.
- **Content-hash manifest for round-trip awareness**: Write a manifest after each merge recording content hashes by relative path. On re-run, compare to detect user modifications. Atomic write via `tmp + os.replace`. This pattern is reusable for any tool that generates files users might edit.
- **Sentinel block preservation**: `<!-- TOOL_USER_START -->` / `<!-- TOOL_USER_END -->` markers define inviolable zones in generated files. Extract before rewrite, restore after. The regex pattern and extract/restore logic in `merge.py` is generalizable.
- **Gap-closure via decimal phases**: When an audit finds integration gaps, insert decimal phases (8.1, 8.2) rather than reopening completed phases or deferring to the next milestone. Keeps the shipped milestone complete while addressing real issues.

### Key Lessons

1. **Fix SUMMARY.md extraction tooling.** Two milestones in a row, the `summary-extract` command has produced incomplete accomplishments for MILESTONES.md. Either standardize the SUMMARY frontmatter schema (with validation) or switch to a different extraction approach.
2. **Prune STATE.md accumulated context at phase transitions.** Archive phase-specific decisions to SUMMARY.md and keep only carry-forward decisions in STATE.md. The file should stay under 50 lines of decisions at any time.
3. **Code review should catch hardcoded paths.** WIRING-01 (`Path('graphify-out')` in approve) is the kind of bug that code review agents are designed to catch. Ensure `--out-dir` threading is in the review checklist for any new CLI path.
4. **Module-level helpers are the MCP testing pattern.** Never put business logic inside MCP tool handler closures. Extract to module-level functions, test directly, then wire into the handler. This pattern should be documented in CLAUDE.md for future contributors.

### Cost Observations

- **Model mix:** ~15% opus (milestone audit, gap-closure planning, completion workflow), ~80% sonnet (plan execution, code review), ~5% haiku (state updates, trivial commits).
- **Sessions:** ~3-4 distinct working sessions across 2 days. Phases 6-8 each landed in roughly one session; gap-closure phases (8.1, 8.2) were a single session.
- **Notable:** The milestone audit + 2 gap-closure phases added ~4 hours but caught real integration issues. The per-plan execution time averaged 5 minutes across 12 plans — significantly faster than v1.0's average, likely due to smaller plan scopes and established patterns.

---

## Milestone: v1.2 — Intelligent Analysis & Cross-File Extraction

**Shipped:** 2026-04-15
**Phases:** 3 | **Plans:** 9 | **Timeline:** 2 days of code (2026-04-14 → 2026-04-15) + 1 day of retroactive lifecycle cleanup (2026-04-15/16)

### What Was Built

- **`graphify/analyze.py::render_analysis_context`** — Serializes the graph (nodes, edges, communities, god nodes, surprising connections) into a compact text block for tournament LLM prompts. 9 tests in `test_analyze.py`.
- **`graphify/report.py::render_analysis`** — Produces `GRAPH_ANALYSIS.md` markdown with per-lens sections, overall verdict, cross-lens synthesis (Convergences + Tensions), and tournament rationale (A/B/AB Borda scores). 14 tests in `test_report.py`.
- **`graphify/skill.md` tournament section (~260 lines)** — 6-step orchestration (A1–A6) for 4 lenses × 4 rounds (incumbent A, adversary B, synthesis AB, blind Borda). Shuffled neutral judge labels (Analysis-1/2/3), "no finding" as first-class Borda option. Writes to `GRAPH_ANALYSIS.md`; `GRAPH_REPORT.md` untouched (D-80).
- **`graphify/serve.py` telemetry** — `_record_traversal`, `_save_telemetry` (atomic `os.replace`), `_edge_weight`, `_decay_telemetry`, `_check_derived_edges`. Per-edge MCP traversal counters, decay of unused edges, 2-hop A→C derived edges with `confidence=INFERRED`, `confidence_score=0.7`, and a `via` field naming the intermediate node.
- **`graphify/report.py::_compute_hot_cold` + "Usage Patterns" section** — Percentile-based hot/cold classification surfaced in `GRAPH_REPORT.md`. `generate()` accepts `usage_data=` kwarg at all 3 call sites.
- **Retroactive lifecycle artifacts (Phase 9.1.1, zero code)** — Generated `09.1-VERIFICATION.md` from existing UAT/VALIDATION/SECURITY evidence, created project-level `.planning/REQUIREMENTS.md` with 10 v1.2 REQ-IDs + file:line traceability, reconciled ROADMAP/STATE/PROJECT into a consistent narrow-scope narrative.

### What Worked

- **Narrow-scope milestone discipline**: v1.2 originally listed 6 phases (9, 9.1, 9.2, 10, 11, 12). The `/gsd-audit-milestone` run on 2026-04-16 surfaced that phases 9 + 9.1 already delivered coherent, shippable value — autoreason tournament + usage-weighted edges form a complete feature. Rather than leave v1.2 open while queueing 4 more phases of retrieval/extraction work, the operator locked scope at 9 + 9.1 and moved the rest to a new v1.3. The re-audit confirmed v1.2 as complete on its own. This is the v1.1 "always audit twice" pattern applied to scope, not just bookkeeping.
- **Planning-only lifecycle-cleanup phase (Phase 9.1.1)**: A pure gap-closure phase that touched zero code. All 3 audit gaps (missing verification, missing REQUIREMENTS.md, scope contradictions) were closable by writing/reconciling planning artifacts. Because there was no code, no REVIEW.md, VALIDATION.md, or SECURITY.md was needed — just planning delta + verification + summary. The phase completed in under an hour and raised audit score from `gaps_found` to `passed` without touching `graphify/`.
- **Atomic sidecar writes across all agent state**: `telemetry.json`, `agent-edges.json`, `annotations.jsonl` all use `os.replace()` — no partial-write corruption possible mid-query, even under concurrent MCP traversals. v1.1 established the sidecar pattern; v1.2 locked in atomicity as the default.
- **Blind Borda prevents "agree with the first agent" failure mode**: Shuffling neutral labels (Analysis-1/2/3) and rotating the label→role mapping across 3 judges (judge 1: [A,B,AB], judge 2: [B,AB,A], judge 3: [AB,A,B]) breaks the natural bias toward accepting whichever perspective was presented first. The tournament is cheap enough (24 LLM calls total across all 4 lenses) that the blind-judging overhead is worth the decision quality.
- **Separating `GRAPH_ANALYSIS.md` from `GRAPH_REPORT.md` (D-80)**: Mechanical metrics (deterministic, regeneratable) stay in GRAPH_REPORT.md; LLM-produced interpretation (non-deterministic, expensive) lives in GRAPH_ANALYSIS.md. Users can re-run `/graphify` any time and only pay the tournament cost on explicit `/graphify analyze`.

### What Was Inefficient

- **v1.2 was never instantiated via `/gsd-new-milestone`**: REQUIREMENTS.md didn't exist at phase-execution time, so SUMMARY.md files for 09 and 09.1 have no `requirements_completed` frontmatter. The milestone audit had to cross-reference REQ-IDs from a retroactively-created REQUIREMENTS.md (Phase 9.1.1 Plan 02). The 3-source audit pattern works retroactively, but it loses the early-warning signal that catches scope drift before a phase ships.
- **VERIFICATION.md `human_needed` status never propagated to `passed` after HUMAN-UAT.md closed**: Phase 09 had 3 human checkpoints documented in VERIFICATION.md frontmatter, all resolved 3/3 in HUMAN-UAT.md on 2026-04-15. The VERIFICATION.md frontmatter still read `status: human_needed` until the milestone-close session reconciled it. `/gsd-audit-uat` counted the original 6 frontmatter expectations as "unresolved" even though HUMAN-UAT.md covered them. This is a cross-file integrity issue: HUMAN-UAT.md resolution should auto-bump VERIFICATION.md status.
- **`gsd-tools audit-open` has a bug**: `ReferenceError: output is not defined` — the comprehensive pre-close audit step couldn't run, so manual grep scans substituted. Non-blocking for this milestone but should be fixed before v1.3 close.
- **`gsd-tools summary-extract --pick one_liner` returned garbage**: The auto-generated MILESTONES.md entry had 6 accomplishment bullets, 5 of which were literal "One-liner:" strings. The entry had to be hand-rewritten from memory + VERIFICATION.md evidence. Tooling debt called out in v1.0 and v1.1 retrospectives — still unresolved.
- **09.1-SECURITY.md lacks structured YAML frontmatter**: 7 threats all CLOSED in the table body, but no `threats_total`/`threats_open` frontmatter fields — so grep-based audit extraction returns empty. The milestone audit accepted this as non-blocking, but it means subsequent tooling checks will keep re-flagging phase 09.1 until the frontmatter is added.

### Patterns Established

- **Narrow-scope milestone close**: When an audit surfaces that N of M planned phases already deliver coherent value, ship N and move M−N into a new milestone. Requires: (a) explicit ROADMAP reconciliation recording the split decision, (b) new milestone heading with "continuation" framing, (c) renaming downstream milestones if numbering collides (old v1.3 → v1.4). Documented here as the canonical pattern.
- **Planning-only lifecycle-cleanup phases**: A phase type that touches zero code, produces no VALIDATION/SECURITY/REVIEW artifacts, and exists solely to reconcile planning-artifact drift. Decimal phase numbering (9.1.1) and a "no code changes" invariant enforced by the verifier. Phase 9.1.1 is the canonical example.
- **VERIFICATION.md resolution record field**: When HUMAN-UAT.md later resolves a `human_needed` verification, add `resolution_record: <filename>` + `human_checkpoints_resolved: <ISO-date>` fields to VERIFICATION.md frontmatter and update `status` + `score`. Closes the cross-file drift documented in "What Was Inefficient" above.
- **3-source cross-reference works retroactively**: REQUIREMENTS × VERIFICATION × SUMMARY cross-reference survives a retroactively-created REQUIREMENTS.md, as long as VERIFICATION.md has sufficient evidence detail. The "registered post-hoc" pattern is legitimate tech debt, not a blocker.
- **Atomic sidecar writes are the contract**: Any agent-writable sidecar must use `os.replace()` — not direct write. This is now the enforced pattern for telemetry, annotations, and agent edges.

### Key Lessons

1. **Instantiate milestones via `/gsd-new-milestone` before phase execution.** This creates REQUIREMENTS.md at the start, so phase SUMMARYs carry `requirements_completed` frontmatter natively. Retroactive creation works but loses the early-warning signal.
2. **Don't let milestones stay open to accommodate optional scope.** If 2/6 phases already deliver the intent, close the milestone and queue the rest into the next one. Narrow-scope close + continuation milestone is cleaner than indefinite in-progress.
3. **HUMAN-UAT.md resolution must propagate to VERIFICATION.md frontmatter.** Either as an automated tooling update or as a mandatory step in the HUMAN-UAT close flow. Otherwise audit tooling surfaces stale "human_needed" for items already resolved.
4. **Fix the `summary-extract` one-liner bug before v1.3 closes.** Three milestones in a row have auto-generated garbage accomplishments. The tooling debt is now blocking efficient milestone closure.
5. **Enforce SECURITY.md frontmatter schema at phase close.** 09.1 shipped with 7 closed threats but no `threats_total`/`threats_open` fields — which invisibly breaks grep-based audit tooling. Phase verifier should check frontmatter completeness.
6. **Blind Borda + "no finding" as first-class is worth the complexity.** The architectural investment in shuffled neutral labels and 4-option Borda (A/B/AB/none) prevents the most common LLM-council failure modes. Reusable pattern for any future multi-perspective feature.

### Cost Observations

- **Model mix:** Similar to v1.1 — ~10% opus (orchestration, audits, milestone close), ~85% sonnet (plan execution, test writing), ~5% haiku. The tournament feature itself incurs LLM cost on the *user's* graph, not on GSD operations.
- **Sessions:** ~3 distinct working sessions across 3 days. Two code-phases sessions + one retroactive cleanup + audit close session.
- **Notable:** The 24-LLM-call tournament runs in ~2–3 minutes on a real corpus. Tournament cost is amortized across analysis runs (only paid on explicit `/graphify analyze`, not on `/graphify` rebuilds). Phase 9.1.1 (planning-only) added ~1 hour of orchestrator time and fully closed the audit — excellent cost/value ratio for cleanup work.

---

## Milestone: v1.3 — Intelligent Analysis Continuation

**Shipped:** 2026-04-17
**Phases:** 3 (9.2, 10, 11) | **Plans:** 19
**Timeline:** 2026-04-16 → 2026-04-17 (2 days)

### What Was Built

- **Phase 9.2 Progressive Graph Retrieval:** Token-aware 3-layer MCP `query_graph` (Layer 1 summary / Layer 2 edges / Layer 3 full subgraph) with `budget` parameter, deterministic cardinality estimator emitted before multi-hop queries, bidirectional BFS at depth ≥ 3 with 3-state status return. Established the hybrid response envelope (`text_body + SENTINEL + json(meta)` with status codes) that Phases 10 and 11 inherited.
- **Phase 10 Cross-File Semantic Extraction with Entity Deduplication:** Import-cluster batching with token-budget soft cap (50k default) + topological ordering; new `graphify/dedup.py` with fuzzy (`difflib` ≥ 0.90) + embedding (`sentence-transformers` cosine ≥ 0.85) dual-signal matching; canonical merge with weight sum + confidence_score max + EXTRACTED>INFERRED>AMBIGUOUS precedence; transparent alias redirect in MCP `query_graph` (`resolved_from_alias` meta).
- **Phase 11 Narrative Mode Slash Commands:** 5 new MCP tools (`graph_summary`, `entity_trace`, `connect_topics`, `drift_nodes`, `newly_formed_clusters`) composed from existing `analyze.py` / `delta.py` / `snapshot.py` primitives (no new `graphify/` modules per D-18); 7 `.claude/commands/*.md` prompt files (`/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge`) installable via `graphify install` with `commands_enabled: True` on Claude Code + Windows.

### What Worked

- **Plan-checker caught structural bugs before execution.** 5 blockers + 4 warnings on the Phase 11 first pass (wrong `compute_delta` signature, undefined `G_live` in test template, windows platform incorrectly disabled, ROADMAP success criterion mismatch, VALIDATION.md unfilled). Targeted revision fixed all 9 in one pass.
- **Code review found production bugs that all unit tests missed.** Phase 11's gsd-code-reviewer caught (a) `list_snapshots()` path double-nesting (`graphify-out/graphify-out/snapshots/` — all 4 snapshot-chain tools would have always returned `insufficient_history` in production; tests passed `tmp_path` directly and never tripped it), (b) `TypeError` on `graphify install --platform=cursor` from a missing `project_dir` argument. Both auto-fixed via `gsd-code-review-fix` with regression tests that match production path semantics.
- **Wave structure collapsed cleanly under sequential execution.** With `workflow.use_worktrees: false`, the planned 6-wave structure executed as a linear 7-plan run without conflict. Each wave's test suite stayed green before advancing.
- **Cross-phase invariant enforcement.** Phase 10's alias redirect contract and Phase 9.2's hybrid envelope contract explicitly carried forward into Phase 11 via CONTEXT.md D-07 and D-08. The planner read those contracts as hard requirements, not suggestions.

### What Was Inefficient

- **Roadmap-parser gap cost cycles.** `gsd-tools find-phase 11` returned `found: false` even though Phase 11 was fully scoped in ROADMAP.md — the indexer only recognizes phases with on-disk directories. Workaround was `mkdir .planning/phases/11-narrative-mode-slash-commands/` before `/gsd-discuss-phase 11` would accept the phase. Also caused 24 spurious `W002` warnings in `/gsd-health` from STATE.md history references to phase numbers the indexer couldn't see.
- **Summary one-liner extractor swallowed Phase 10/11 results.** `gsd-tools summary-extract --fields one_liner` returned raw "One-liner:" labels + stray file paths for several SUMMARY.md files whose frontmatter didn't match the expected shape. Cost a curation pass to rewrite the MILESTONES.md accomplishments block by hand.
- **`audit-open` tool bug blocked the pre-close audit.** `ReferenceError: output is not defined` at `gsd-tools.cjs:786`. Had to do manual readiness check via filesystem + grep.
- **Tooling gap surfaced mid-phase.** The `/gsd-audit-milestone` step was skipped because `audit-open` can't run, plus no pre-existing audit file for v1.3. Proceeded with manual verification (3 phases × summary files + requirements table grep + post-execution code review + verifier agent). For v1.4 the audit command needs the CLI bug fixed first.

### Patterns Established

- **Hybrid response envelope as cross-phase invariant.** Phase 9.2 introduced it, Phases 10 and 11 inherited it. All new MCP tools emit `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with a `status` field — the canonical contract for anything agents consume.
- **Alias redirect as forward-compat primitive.** When dedup merges node X into Y, `query_graph(X)` returns Y with `resolved_from_alias: "X"` meta. Phase 11 inherited this: every identifier-accepting tool in `entity_trace` / `connect_topics` honors the same contract. Old callsites don't break when the graph gets dedup'd.
- **Memory discipline for snapshot walkers.** Iterate snapshots → extract per-graph scalars (community_id, degree, staleness) → `del G_snap` → move on. Verified via weakref-based tests that assert the graph object is garbage-collected, not just out of scope.
- **No new modules for plumbing phases (D-18).** Phase 11 shipped 5 MCP tools by composing `analyze.py` + `delta.py` + `snapshot.py` primitives. When a thin wrapper delivers the requirement, resist the urge to open a new module.
- **Conditional plans with grep-verifiable gate decisions.** Plan 11-07 (stretch) has a Task 0 that writes `^GATE: proceed` or `^GATE: defer` as the first non-frontmatter line of SUMMARY.md. Subsequent tasks short-circuit via `grep -q '^GATE: defer' ... && exit 0`. Clean conditional execution without complex workflow branching.

### Key Lessons

- **Test fixtures must match production path semantics.** The Phase 11 CR-01 bug is the archetype: tests passed `tmp_path` as the `list_snapshots` root (one layout) while production code passed `graphify-out/` (another layout). Both callers were internally consistent; neither caller matched the other. For any module with filesystem layout assumptions, at least one test must construct the *production* path shape.
- **Plan-checker and code-reviewer see different bug spaces.** The planner's verifier caught *structural* bugs (wrong signatures in plan text, missing acceptance criteria). The code reviewer caught *runtime* bugs that slipped through plans AND tests. Both gates are necessary — neither is sufficient. If only one were run, a critical class of bugs would ship.
- **Auto mode is one-pass by design.** `/gsd-discuss-phase --auto` completed a full discussion in a single pass with logged recommended-default selections. Decisions were durable and downstream agents treated them as locked — no iteration, no re-asking. Works best when gray areas are well-enumerated and defaults have been thought through.
- **Phase-registration gaps compound.** Once Phase 11 failed to register, `/gsd-next` routing, `/gsd-health`, STATE.md comparison, and the pre-close audit all behaved oddly. Fix the indexer gap early in v1.4 — it's cheap leverage.

### Cost Observations

- **Model mix:** ~20% opus (planner agent, checker revisions, milestone orchestration), ~75% sonnet (executor agents across 7 plans, research, code review, fix agent), ~5% haiku-class. Opus share rose vs. v1.2 because Phase 11 was structurally more complex and required more planner/revision work.
- **Sessions:** ~2 distinct working sessions across 2 days. Phase 10 and Phase 11 executed in the same stretch with no context reset.
- **Notable:** Phase 11's 7 plans executed sequentially in ~70 minutes total wall-clock (no worktrees, so parallel waves collapsed to sequential). Quality gates (plan-checker, code-reviewer, fix agent, verifier) added ~25 minutes but caught 2 Critical + 2 Warning + 9 pre-execution findings. Net time saved vs. debugging runtime failures in production was significant.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 22 | First milestone using GSD end-to-end; retroactive VERIFICATION pattern pioneered; 3-source audit cross-reference established |
| v1.1 | 5 | 12 | Decimal phase numbering for gap closure; module-level MCP testing pattern; sidecar persistence as canonical mutation approach |
| v1.2 | 3 | 9 | Narrow-scope milestone close pattern; planning-only lifecycle-cleanup phase (9.1.1); atomic sidecar writes enforced across all agent state; blind Borda tournament with "no finding" as first-class option |

### Cumulative Quality

| Milestone | Tests | Python LOC (graphify/) | Test LOC (tests/) | Zero-Dep Additions |
|-----------|-------|------------------------|-------------------|-------------------|
| v1.0 | 872 passing | 11,620 | 10,500 | 0 (PyYAML is optional `obsidian` extra only) |
| v1.1 | 1,000 passing | 13,520 | ~12,400 | 0 (all stdlib additions) |
| v1.2 | 1,023 passing | ~14,100 | ~13,000 | 0 (all stdlib — telemetry uses `json` + `os.replace`) |
| v1.3 | 1,234 passing | ~16,481 | ~16,529 | 0 (`sentence-transformers` + `difflib` for dedup — optional extras) |
| v1.4 | 1,428+ passing | ~22,900 | ~22,100 | 0 (all stdlib — `fcntl.flock`, `threading.Event`, `os.replace` throughout) |

### Milestone: v1.4 — Agent Discoverability & Obsidian Workflows

**Shipped:** 2026-04-22
**Phases:** 9 (7 core + 2 gap closure) | **Plans:** 32 | **Timeline:** 6 days (2026-04-17 → 2026-04-22) | **Commits:** 165 | **Delta:** +35,754 / −2,481 across 155 files

#### What Was Built

Agent-discoverable MCP surface (introspection-driven capability manifest + harness export), vault-scoped thinking commands behind a `propose + approve` trust boundary, heterogeneous per-file routing with cost ceilings, async background enrichment coordinated via file locks, focus-aware BFS context, two-stage structurally-enforced chat with mandatory citations, and SPAR-Kit graph argumentation with fabrication-rejecting envelopes. See `.planning/milestones/v1.4-ROADMAP.md` for full phase detail.

#### What Worked

- **HARD-gate declaration at the milestone level.** Phase 12's `cache.py::file_hash()` key format change was declared a HARD-gate for all downstream v1.4 phases — anyone touching caching had to justify why. Prevented a whole category of cache-corruption regressions that v1.1/v1.2 would have absorbed silently.
- **Decision-as-constraint (D-02, D-16, D-18).** Three cross-cutting invariants (MCP envelope format, alias threading, compose-don't-plumb) were locked at milestone start and checked in every phase's code review. The audit found all three held across 7 phases — no bespoke handler violated the envelope contract. Upgrade over v1.3's ad-hoc re-litigation.
- **Atomic pair commits (MANIFEST-05).** `mcp_tool_registry.py` + `serve.py` extensions land together in the same plan. This pattern prevented the ship-now-wire-later failure mode that Phase 13's initial drop had for `13-VERIFICATION.md` (shipped but unverified for 5 days).
- **Gap-closure sub-phases at audit time.** Phase 18.1 and 18.2 were planned out of the initial audit's `gaps_found` status as decimal-phase gap closure (following v1.2's 9.1.1 pattern). Audit → plan-gaps → execute → re-audit → close. Four-step loop is now the canonical v1.4 pattern.
- **Recursion guards as manifest metadata.** ARGUE-07 (`composable_from: []` HARD CONSTRAINT) lived in `capability_tool_meta.yaml:72` as declarative data, not imperative logic. Agents reading the manifest before calling `argue_topic` see the constraint without executing code. Cheaper enforcement than runtime checks.

#### What Was Inefficient

- **Phase 13 shipped without any verification artifacts.** Ran all 18 REQ-IDs' plans through SUMMARYs on 2026-04-17, but `13-VERIFICATION.md`, `13-SECURITY.md`, `13-VALIDATION.md` were never produced. Milestone audit on 2026-04-22 caught it as a blocker, forcing Phase 18.1 as retrofit work. Lost ~2 hours to reconstruction. Same root cause as v1.0's Phase 01 verification gap — the pipeline can run green without the verification step running. Hook or gating needed.
- **Stale `capability_tool_meta.yaml` for new MCP tools.** Phases 17 + 18 added `chat` and `get_focus_context` as MCP tools but did not update `capability_tool_meta.yaml`. MANIFEST-06 flagged PARTIAL at audit; `cost_class` defaults served agents wrong info (`chat` marked cheap instead of expensive). Closed via Phase 18.2-01 with a set-equality guard test. Should have been a MANIFEST-06-gated atomic pair from day one.
- **REQUIREMENTS.md rollover timing.** `/gsd-new-milestone v1.5` ran 2026-04-22 before v1.4 was formally closed, rolling REQUIREMENTS.md forward to v1.5 scope. The v1.4 audit then had no REQUIREMENTS.md traceability table to check and had to reconstruct coverage from per-phase SUMMARY frontmatter. Worked, but lost the single-source-of-truth trace. Future: close milestone N before opening N+1, OR make `new-milestone` archive the previous REQUIREMENTS.md before overwriting.
- **ACE Vocabulary candidate orphaned by merge bot.** Two branch merges (`4f3761b`, `e662a51`) landed an "ACE-Aligned Vocabulary, Linking & Naming" proposal into ROADMAP.md as a `🌱 Candidate Phase` block separate from numbered phases. Semantically overlaps with Phase 19. Pre-close scope reconciliation caught it but the duplication sat in-tree for a day.
- **`/gsd-complete-milestone` default assumes in-order close.** v1.4's close after v1.5 had already been opened required deviating from the default workflow (skip `git rm REQUIREMENTS.md`, surgical archive construction from audit + SUMMARY frontmatter). If this pattern recurs, tooling should detect out-of-order close and offer a safe-mode branch.

#### Patterns Established

- **D-02 MCP envelope contract** — every new MCP tool emits `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with status codes. Inherited by v1.5+ automatically.
- **Manifest-as-metadata-source-of-truth** — `capability_tool_meta.yaml` + set-equality guard test is the canonical pattern for per-tool config. No more scattered constants across handlers.
- **Snapshot `project_root` sentinel dataclass** — codified v1.3 CR-01's snapshot-double-nesting fix so all downstream phases inherit the guard automatically.
- **Audit-driven decimal-phase gap closure** — when milestone audit returns `gaps_found`, plan-milestone-gaps creates N.1, N.2 phases to close blockers without re-opening closed phases. v1.2 9.1.1 pioneered, v1.4 18.1/18.2 productionized.
- **Out-of-order milestone close** — v1.4 closed after v1.5 opened required surgical archival (move audit file, reconstruct REQUIREMENTS from per-phase SUMMARYs, skip `git rm REQUIREMENTS.md`). Pattern now documented.

#### Key Lessons

1. **Make verification non-skippable.** Phase 13 shipping without VERIFICATION/VALIDATION/SECURITY is the third variant of this bug (v1.0 Phase 01, v1.2 `human_needed` rot, v1.4 Phase 13 total absence). Add a pipeline gate: `/gsd-execute-phase` fails to mark phase complete unless all three artifacts exist.
2. **Set-equality guard tests are cheap and catch manifest drift.** `test_capability.py` set-equality between registered tools and `capability_tool_meta.yaml` entries would have caught MANIFEST-06 at phase 17 commit time, not milestone audit time. Apply to any "manifest + implementation" pair.
3. **Close milestone N before opening N+1.** REQUIREMENTS.md rollover during an open milestone lost the traceability table for the closing milestone and forced per-phase reconstruction. Enforce one-at-a-time by workflow gate.
4. **Merge-bot-introduced candidate phases need reconciliation before scope lock.** Branch merges that add speculative proposals to ROADMAP.md should be treated as planning inputs, not committed scope. Reconcile into numbered phases or backlog at the next milestone boundary.
5. **Decimal-phase gap closure is a cheaper recovery pattern than re-opening closed phases.** v1.4's 18.1/18.2 extend the v1.2 9.1.1 pattern: keep the audit → plan-gaps → execute → re-audit loop tight. Don't retrofit verification inside already-complete phases.

#### Cost Observations

- Model mix: Opus 4.7 orchestrator on `yolo` quality profile with parallelization on; Sonnet executors per `.planning/config.json`.
- Sessions: ~20+ across 6 days (multiple /gsd-execute-phase invocations per day during mid-milestone burst).
- Notable: `/gsd-audit-milestone` re-audit loop (discover → plan-gaps → execute gap closure → re-audit) consumed less context than trying to retrofit verification inside already-completed phases. Re-audit loop = cheap.

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 22 | First milestone using GSD end-to-end; retroactive VERIFICATION pattern pioneered; 3-source audit cross-reference established |
| v1.1 | 5 | 12 | Decimal phase numbering for gap closure; module-level MCP testing pattern; sidecar persistence as canonical mutation approach |
| v1.2 | 3 | 9 | Narrow-scope milestone close pattern; planning-only lifecycle-cleanup phase (9.1.1); atomic sidecar writes enforced across all agent state; blind Borda tournament with "no finding" as first-class option |
| v1.3 | 3 | 19 | D-02 hybrid response envelope contract established; D-16 alias-redirect for dedup transparency; D-18 compose-don't-plumb design principle; cross-source ontology alignment; gsd-code-reviewer as critical-bug-catching gate |
| v1.4 | 9 (7+2) | 32 | Milestone-level HARD-gates; cross-cutting decisions-as-constraints (D-02/D-16/D-18 checked every phase review); audit-driven decimal gap-closure (18.1, 18.2); manifest-as-metadata-source-of-truth; out-of-order milestone close pattern |

### Top Lessons (Verified Across Milestones)

1. **Run phase verification at phase completion time, not later.** (v1.0) — Confirmed in v1.1 where all phases had timely verification; no retroactive gap-filling needed. v1.2 re-surfaced a variant: VERIFICATION.md `status: human_needed` must be flipped to `passed` when HUMAN-UAT.md later resolves the human checkpoints, or audit tooling keeps re-flagging closed items.
2. **Always audit twice (audit → fix → re-audit).** (v1.0, v1.1, v1.2) — Three milestones, three audit-driven gap closures before close. The pattern is now proven. v1.2 extended it: the second audit can also trigger a *scope* decision, not just a bookkeeping fix (narrow-scope close of 9+9.1, deferred 9.2/10/11/12 to v1.3).
3. **SUMMARY.md extraction tooling needs fixing.** (v1.0, v1.1, v1.2) — Three milestones of incomplete `summary-extract --pick one_liner` output. The auto-generated MILESTONES.md entry had 5/6 literal "One-liner:" bullets. Blocking efficient close — must be fixed before v1.3.
4. **Sidecar-only mutation for agent-writable state.** (v1.1) — Reinforced in v1.2: atomic `os.replace()` writes now the default across telemetry, annotations, agent edges. No torn reads under concurrent MCP traversals.
5. **Module-level helpers for MCP testability.** (v1.1) — Continues in v1.2: `_record_traversal`, `_edge_weight`, `_decay_telemetry`, `_check_derived_edges` are all module-level and directly unit-testable.
6. **Instantiate milestones before executing phases.** (v1.2) — Without `/gsd-new-milestone` run up-front, phase SUMMARYs lack `requirements_completed` frontmatter and the 3-source audit has to reconstruct REQ coverage from VERIFICATION.md evidence. Works retroactively, but loses the early-warning signal.
7. **Narrow-scope close > indefinite milestone.** (v1.2) — When N of M planned phases already deliver coherent value, close N and queue M−N into the next milestone with explicit origin anchoring. Keeps milestones shippable and traceable.

---

_Retrospective last updated: 2026-04-23 after v1.4 milestone completion (v1.3 backfilled alongside)._
