---
phase: 16
plan: "03"
subsystem: argue
tags: [argue, skill, slash-command, spar-kit, blind-label, advisory-only, deferred-p2]
dependency_graph:
  requires:
    - graphify/argue.py (Plan 01 — ROUND_CAP, MAX_TEMPERATURE, validate_turn, compute_overlap)
    - argue_topic MCP tool (Plan 02)
    - graphify/commands/ask.md (frontmatter template)
    - graphify/skill.md Phase 9 blind-label harness (lines 1388-1550, unmodified)
  provides:
    - graphify/commands/argue.md (/graphify-argue slash command)
    - graphify/skill.md SPAR-Kit orchestration section (Phase 16 debate loop)
    - tests/test_commands.py::test_argue_md_frontmatter
  affects:
    - users invoking /graphify-argue <question>
tech_stack:
  added: []
  patterns:
    - "ask.md frontmatter mirror — name/description/argument-hint/disable-model-invocation: true, no target:"
    - "D-02 envelope parsing (no_graph/no_results/ok status) in command file body"
    - "SPAR-Kit debate loop — up to ROUND_CAP=6 rounds, 4 personas, per-round blind-label shuffle"
    - "Jaccard cite-overlap convergence detection (consensus ≥0.7×2, dissent <0.2×3, inconclusive at cap)"
    - "validate_turn + 1-retry + abstain path for fabricated cites"
    - "Advisory-only output to graphify-out/GRAPH_ARGUMENT.md (hardcoded path, validate_graph_path confinement)"
key_files:
  created:
    - graphify/commands/argue.md
  modified:
    - graphify/skill.md (added /graphify-argue SPAR-Kit section ~104 lines after Phase 9 analyze section)
    - tests/test_commands.py (added test_argue_md_frontmatter)
decisions:
  - "D-05 reuse: Phase 9 blind-label harness referenced by pointer in skill.md new section — not duplicated, not modified; test_blind_label_harness_intact anchors on line 1511 literal 'Judge 1: Analysis-1=A'"
  - "D-07 enforced: consensus detected from Jaccard overlap, no synthesizer persona; anti-pattern explicitly documented in skill.md"
  - "D-09 enforced: 1-retry max for fabricated cites; second failure = abstain {claim: '[NO VALID CLAIM]', cites: []} — abstentions dropped from Jaccard numerator/denominator"
  - "D-13 enforced: [node_id:label] inline cite format with sanitize_label + validate_graph_path at write time"
  - "ARGUE-11/12/13 disposed as documented-deferred (NOT implemented) per 16-CONTEXT.md Deferred Ideas — explicitly called out in skill.md with 'v1.4.x backlog' label"
  - "test_validate_cli_zero pre-existed as a failing test before Plan 03 — confirmed by git stash check; out-of-scope per deviation scope boundary"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-23"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
  tests_added: 1
---

# Phase 16 Plan 03: /graphify-argue Command File + SPAR-Kit Skill Orchestration Summary

**One-liner:** User-facing /graphify-argue slash command + SPAR-Kit debate orchestration block in skill.md — up to 6 rounds of 4-persona blind-labeled graph-grounded argumentation, Jaccard cite-overlap convergence detection, advisory-only transcript to graphify-out/GRAPH_ARGUMENT.md, with ARGUE-11/12/13 explicitly documented as v1.4.x backlog.

## What Was Built

### Task 1: `/graphify-argue` Command File + Frontmatter Test

`graphify/commands/argue.md` — the slash command entry point for Phase 16. Mirrors `ask.md` frontmatter exactly (`name: graphify-argue`, `disable-model-invocation: true`, `argument-hint: <decision question>`, no `target:` field). Body invokes `argue_topic` MCP tool with `$ARGUMENTS` as `topic`, parses D-02 envelope (no_graph/no_results/ok), delegates to skill.md SPAR-Kit section for ok status, and renders verdict + Jaccard trajectory + path to `GRAPH_ARGUMENT.md`. Advisory-only invariant (ARGUE-09) stated in body. Uses `resolved_from_alias` (never `alias_redirects` — Pitfall 4 guard).

`tests/test_commands.py::test_argue_md_frontmatter` — asserts all frontmatter invariants, body references argue_topic, $ARGUMENTS present, advisory language present, and `alias_redirects` absent.

### Task 2: SPAR-Kit Orchestration Section in skill.md

New section `## /graphify-argue <question> — SPAR-Kit Graph Argumentation Mode (Phase 16)` inserted in `graphify/skill.md` after the `/graphify analyze` section (at line ~1621, before `## For --watch`).

**Step B1–B5 documented:**
- B1: Call `argue_topic` with topic/scope, parse D-02 envelope, extract argument_package
- B2: Build `{EVIDENCE_SUBGRAPH}` text block via `render_analysis_context` or markdown list
- B3: Debate rounds loop (ROUND_CAP=6) with per-round A/B/C/D shuffle, 4 parallel persona calls at temperature ≤ 0.4, `validate_turn` + 1-retry + abstain, Jaccard cite-overlap + early-stop
- B4: Write advisory-only transcript to `graphify-out/GRAPH_ARGUMENT.md` in D-11/D-12/D-13 format
- B5: Report verdict + trajectory + path to user (≤400 tokens)

**Phase 9 harness preserved:** The blind-label anchor at skill.md line 1511 (`"Judge 1: Analysis-1=A, Analysis-2=B, Analysis-3=AB"`) is unmodified. The new section references it by pointer only. `test_blind_label_harness_intact` passes.

**Anti-patterns documented:** DO NOT invoke chat, DO NOT add synthesizer persona, DO NOT strip invalid cites, DO NOT echo unmatched tokens, DO NOT exceed ROUND_CAP=6, DO NOT use alias_redirects.

**P2 deferrals documented:** ARGUE-11 (INTERROGATE), ARGUE-12 (persona memory), ARGUE-13 (clash scoring) all explicitly marked `v1.4.x backlog — NOT IMPLEMENTED`.

## Decisions Made (D-series references)

- **D-04/D-05**: All 4 personas per round synchronous; A/B/C/D labels shuffled per-round (not per-turn) — simpler wiring, same bias guarantee
- **D-06/D-07**: Cite-overlap Jaccard thresholds 0.7 (consensus, 2 consecutive) and 0.2 (dissent, 3 consecutive); no synthesizer persona ever invents agreement
- **D-09**: Max 1 retry per fabricated-cite turn; second failure = `{claim: "[NO VALID CLAIM]", cites: []}` abstention; abstentions excluded from Jaccard
- **D-11/D-12/D-13**: Per-round chronological layout; Final Verdict section with trajectory; `[node_id:label]` inline cites; labels through `sanitize_label`
- **ARGUE-11/12/13 disposition**: `documented-deferred` — not implemented, not forgotten. Each has its own bullet in the skill.md backlog section with activation path described.

## Deviations from Plan

None — plan executed exactly as written.

**Pre-existing out-of-scope failure noted:** `tests/test_capability.py::test_validate_cli_zero` was already failing before Plan 03 changes (confirmed by git stash check). Logged to deferred-items per scope boundary rule.

## Known Stubs

None. The command file and skill.md section are complete orchestration prose — no hardcoded empty values or placeholder text that would prevent `/graphify-argue` from functioning once `argue_topic` (Plan 02) is available.

## Threat Flags

None beyond what was already in the plan's threat model (T-16-01 through T-16-06 and phase-9 harness deletion/drift — all mitigated by the implemented guardrails).

## Requirements Addressed

| Requirement | Status |
|-------------|--------|
| ARGUE-06 | Implemented — Phase 9 blind-label harness reused verbatim; per-round shuffle documented (D-05) |
| ARGUE-09 | Implemented — advisory-only invariant in both argue.md body and skill.md new section; GRAPH_ARGUMENT.md path hardcoded; validate_graph_path confinement documented |
| ARGUE-10 | Implemented — /graphify-argue slash command exists with ask.md-shaped frontmatter; test_argue_md_frontmatter passes |
| ARGUE-11 | Documented-deferred (v1.4.x backlog) — NOT implemented |
| ARGUE-12 | Documented-deferred (v1.4.x backlog) — NOT implemented |
| ARGUE-13 | Documented-deferred (v1.4.x backlog) — NOT implemented |

## Self-Check: PASSED

- `graphify/commands/argue.md` exists: FOUND
- `tests/test_commands.py::test_argue_md_frontmatter` added: FOUND
- `## /graphify-argue` section in skill.md: FOUND
- Phase 9 anchor `"Judge 1: Analysis-1=A"` at line 1512: FOUND (unmodified)
- Task 1 commit f4b3092: FOUND
- Task 2 commit 4d3fbb2: FOUND
- `pytest tests/test_commands.py::test_argue_md_frontmatter -q`: PASSED
- `pytest tests/test_argue.py::test_blind_label_harness_intact -q`: PASSED
- Full suite (excluding pre-existing test_validate_cli_zero failure): 1409 passed
