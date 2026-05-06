---
phase: 64-audit-a-stderr-format-snapshot-lock-sweep
plan: "03"
title: "AUDIT-02 Skill Regex Fixture — 7 Platform SKILL.md Contracts (TDD)"
subsystem: testing
tags: [tdd, stderr-contract, skill-regex, audit]
requirements: [AUDIT-02]
depends_on: ["64-01"]

dependency_graph:
  requires:
    - tests/fixtures/stderr_contract.txt (Plan 64-01 — locked golden fixture)
  provides:
    - tests/fixtures/skill_stderr_regexes.yaml
    - tests/test_skill_regex_fixture.py
  affects:
    - CI: any change to [graphify] stderr format will fail test_each_regex_matches_locked_contract

tech_stack:
  added: []
  patterns:
    - pytest.importorskip for optional PyYAML dependency guard
    - TDD RED/GREEN/REFACTOR gate sequence

key_files:
  created:
    - tests/fixtures/skill_stderr_regexes.yaml
    - tests/test_skill_regex_fixture.py
    - tests/fixtures/stderr_contract.txt
  modified: []

decisions:
  - "All 7 platforms share the same default contract regex because every platform SKILL.md embeds identical Python emitter code using the [graphify] prefix convention; no platform asserts a bespoke format."
  - "trae-cn: graphify/skill-trae-cn.md does not exist; permissive default regex used and deviation documented."
  - "Combined regex pattern covers both primary lines ([graphify] error/info) and continuation hint lines (  hint: ...)"

metrics:
  duration: "~10 minutes"
  completed: "2026-05-06T17:51:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 64 Plan 03: AUDIT-02 Skill Regex Fixture — 7 Platform SKILL.md Contracts (TDD) Summary

**One-liner:** Hand-curated YAML fixture mapping 7 platform SKILL.md files to their shared `[graphify]` stderr contract regex, validated against the locked Plan 64-01 snapshot.

## What Was Built

- `tests/fixtures/skill_stderr_regexes.yaml` — 7-entry YAML mapping platform slugs to their stderr contract regex pattern
- `tests/test_skill_regex_fixture.py` — 3-test pytest module: platform key completeness, regex compilation, and match against locked contract lines
- `tests/fixtures/stderr_contract.txt` — Copied from Plan 64-01 worktree (same byte-exact content: 3 `[graphify]` lines + 3 `  hint:` continuation lines)

## TDD Gate Compliance

| Gate | Commit | Description |
|------|--------|-------------|
| RED | 99f0384 | `test(64-03): RED skill regex fixture scaffold (AUDIT-02)` |
| GREEN | 9e09877 | `test(64-03): GREEN — hand-curated 7 platform skill regex fixture (AUDIT-02)` |
| REFACTOR | (none) | Regex was tight enough; no cleanup needed |

## Platform Regex Coverage

| Platform | SKILL.md Source | Regex | Notes |
|----------|-----------------|-------|-------|
| claude-code | `graphify/skill.md` | `^\[graphify\] (error\|info): .+\|^  hint: .+` | Default — no bespoke pattern |
| codex | `graphify/skill-codex.md` | same | Default |
| opencode | `graphify/skill-opencode.md` | same | Default |
| openclaw | `graphify/skill-claw.md` | same | Default |
| factory-droid | `graphify/skill-droid.md` | same | Default |
| trae | `graphify/skill-trae.md` | same | Default |
| trae-cn | MISSING | same | Permissive default — see Deviations |

All 7 regexes match all 6 non-empty lines in `tests/fixtures/stderr_contract.txt`.

## Deviations from Plan

### Missing Platform SKILL.md (Rule 2 — documented)

**1. [Deviation] `graphify/skill-trae-cn.md` does not exist**
- **Found during:** Task 2 (GREEN) — `ls graphify/skill-trae*.md` returned only `skill-trae.md`
- **Action taken:** Used permissive default regex (`^\[graphify\] (error|info): .+|^  hint: .+`) for the `trae-cn` platform key, which is the correct fallback per plan instructions
- **Impact:** The `trae-cn` fixture entry is present with a valid regex that matches the contract, but it is NOT derived from an actual SKILL.md file
- **Resolution needed:** If `skill-trae-cn.md` is created in the future, update the `trae-cn` entry and the fixture comment

### stderr_contract.txt sourced from worktree

**2. [Deviation] `tests/fixtures/stderr_contract.txt` not yet on `main`**
- **Found during:** Task 1 (RED) — the file existed only in the Plan 64-01 worktree (`worktree-agent-a5970374d2e6623c1`)
- **Action taken:** Re-created the file with identical content (verified via `git show worktree-agent-a5970374d2e6623c1:tests/fixtures/stderr_contract.txt`)
- **Impact:** File is now committed to main; no functional difference

## Known Stubs

None — all 7 platform entries have real, validated regex patterns.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `tests/fixtures/skill_stderr_regexes.yaml` exists | FOUND |
| `tests/test_skill_regex_fixture.py` exists | FOUND |
| `tests/fixtures/stderr_contract.txt` exists | FOUND |
| Commit 99f0384 (RED) | FOUND |
| Commit 9e09877 (GREEN) | FOUND |
| pytest tests/test_skill_regex_fixture.py | 3 passed |
