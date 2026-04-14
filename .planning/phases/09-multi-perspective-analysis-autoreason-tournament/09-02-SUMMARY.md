---
phase: "09"
plan: "02"
subsystem: skill
tags: [skill, tournament, autoreason, multi-perspective, analysis]
dependency_graph:
  requires: [render_analysis_context, render_analysis]
  provides: [graphify_analyze_command]
  affects: [graphify/skill.md]
tech_stack:
  added: []
  patterns: [autoreason-tournament, blind-borda-judges, lens-selection, bash-python-block]
key_files:
  created: []
  modified:
    - graphify/skill.md
decisions:
  - "D-75 honored: tournament runs in skill.md orchestration, not Python library"
  - "D-76 honored: autoreason pattern A→B→AB→blind Borda implemented in 4 rounds"
  - "D-77 honored: 4 built-in lenses defined (security, architecture, complexity, onboarding)"
  - "D-78 honored: lens selection from user prompt with subset support"
  - "D-80 honored: output to GRAPH_ANALYSIS.md separate from GRAPH_REPORT.md"
  - "D-82 honored: clean verdict includes voting rationale"
  - "D-83 honored: all selected lenses always appear in output"
  - "T-09-04 mitigated: judge output validated against expected format; malformed responses skipped (degrade to 2 judges)"
  - "T-09-05 mitigated: ANTI-PATTERN comments enforce round isolation — only TEXT flows between rounds"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-14"
  tasks_completed: 1
  files_modified: 1
  tests_added: 0
---

# Phase 9 Plan 02: Autoreason Tournament Orchestration in skill.md Summary

**One-liner:** Tournament orchestration section added to skill.md implementing the full 4-round autoreason protocol (incumbent/adversary/synthesis/blind-Borda judges) for 4 built-in analysis lenses producing GRAPH_ANALYSIS.md.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add tournament orchestration section to skill.md | b2b88d2 | graphify/skill.md |

## What Was Built

### `## For /graphify analyze` section in graphify/skill.md

A complete skill orchestration section inserted after `## For /graphify add` (line 1286) and before `## For --watch`, containing:

**Step A1 — Load graph context:**
Bash block that reads `.graphify_analysis.json` and `graph.json`, builds the NetworkX graph, calls `render_analysis_context()` to serialize graph structure, and writes the result to `.graphify_lens_context.txt`.

**Step A2 — Lens focus definitions:**
Reference text for the 4 built-in lenses substituted into tournament prompts:
- `security`: auth/authz patterns, input validation, secrets exposure, trust boundary violations
- `architecture`: god node coupling, cohesion gaps, circular deps, layering violations
- `complexity`: fan-in/fan-out nodes, deep call chains, low cohesion communities
- `onboarding`: entry point clarity, documentation coverage, path to core abstractions

**Step A3 — Tournament rounds:**
Four sequential LLM calls per lens:
1. Incumbent Analysis (A) — expert analyst perspective
2. Adversarial Revision (B) — devil's advocate challenges A
3. Synthesis (AB) — neutral synthesizer merges best of A and B
4. Blind Borda Judges — 3 judges rank Analysis-1/2/3 (shuffled, identity hidden)

**Step A4 — Borda score computation:**
Bash block computing standard Borda count (1st=2pts, 2nd=1pt, 3rd=0pts), winner determination, confidence ratio, and lens result dict assembly with verdict/top_finding/voting_rationale.

**Step A5 — render_analysis() call:**
Bash block that passes all lens result dicts to `render_analysis()` from `graphify.report` and writes GRAPH_ANALYSIS.md.

**Step A6 — User report:**
Post-tournament summary format: lenses run, per-lens verdict+confidence, top finding per lens, file location.

### Threat Mitigations Applied

- **T-09-04**: Judge response validated against "1st: Analysis-N / 2nd: Analysis-N / 3rd: Analysis-N" format; malformed responses skipped with graceful degradation to 2 judges
- **T-09-05**: Three ANTI-PATTERN HTML comments enforce round isolation, blind judge labels, and module placement

## Deviations from Plan

None - plan executed exactly as written. The section content matches the plan specification including all prompt templates, bash block patterns, anti-pattern comments, and step ordering.

## Known Stubs

The `JUDGE_RANKINGS_PLACEHOLDER` and `LENS_RESULTS_PLACEHOLDER` / `LENSES_RUN_PLACEHOLDER` and `INPUT_PATH` markers in the bash blocks are intentional skill.md orchestration placeholders. The skill orchestrator (Claude Code agent) substitutes real values when executing the tournament. This is the standard skill.md pattern — not stubs in the product sense. The tournament fully wires to `render_analysis_context()` and `render_analysis()` from Phase 9 Plan 01.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced. The skill.md section reads `.graphify_analysis.json` (already written by Step 4 of the main pipeline) and writes `.graphify_lens_context.txt` and `GRAPH_ANALYSIS.md` to `graphify-out/` — both within the established output path. LLM calls are initiated by the skill orchestrator, not by Python code in the library.

## Self-Check: PASSED

- graphify/skill.md: FOUND
- Commit b2b88d2: FOUND
- `## For /graphify analyze` section: grep returns 1 (PASSED)
- `render_analysis_context` in skill.md: grep returns 2 (PASSED, >=1 required)
- `render_analysis` in skill.md: grep returns 5 (PASSED, >=2 required)
- `GRAPH_ANALYSIS.md` in skill.md: grep returns 4 (PASSED, >=2 required)
- `.graphify_lens_context.txt` in skill.md: grep returns 2 (PASSED, >=2 required)
- `borda` in skill.md (case-insensitive): grep returns 5 (PASSED, >=1 required)
- `Analysis-1` in skill.md: grep returns 7 (PASSED, >=1 required)
- `no issues found` in skill.md: grep returns 2 (PASSED, >=1 required)
- `ANTI-PATTERN` in skill.md: grep returns 3 (PASSED, >=3 required)
- All 4 lens names present: security, architecture, complexity, onboarding (PASSED)
- All 4 tournament roles present: incumbent, devil's advocate, synthesizer, evaluator (PASSED)
- `## For /graphify analyze` at line 1286 BEFORE `## For --watch` at line 1517 (PASSED)
- pytest 1023 tests passing (PASSED, no regression)
