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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 22 | First milestone using GSD end-to-end; retroactive VERIFICATION pattern pioneered; 3-source audit cross-reference established |

### Cumulative Quality

| Milestone | Tests | Python LOC (graphify/) | Test LOC (tests/) | Zero-Dep Additions |
|-----------|-------|------------------------|-------------------|-------------------|
| v1.0 | 872 passing | 11,620 | 10,500 | 0 (PyYAML is optional `obsidian` extra only) |

### Top Lessons (Verified Across Milestones)

_Only one milestone so far — these lessons will be cross-validated as v1.1+ ships. The v1.0 key lessons above are the seed set._

---

_Retrospective last updated: 2026-04-11 after v1.0 milestone completion._
