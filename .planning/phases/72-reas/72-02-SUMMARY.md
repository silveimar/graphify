---
phase: 72-reas
plan: 02
subsystem: skill-prompt + cache-invalidation
tags: [reasoning-relations, prompt, skill-drift, cache]
requires:
  - graphify/prompts.py::PROMPT_VERSION
  - graphify/skill*.md (Phase 65 prompt-version footer anchor)
provides:
  - Step 3 Part B reasoning-relations taxonomy (5 relations + 2 ADR exemplars)
  - PROMPT_VERSION 1.14.0 (confidence cache invalidation)
  - drift-gate parity assertions for reasoning block
affects:
  - graphify/skill.md
  - graphify/skill-aider.md
  - graphify/skill-claw.md
  - graphify/skill-codex.md
  - graphify/skill-copilot.md
  - graphify/skill-droid.md
  - graphify/skill-excalidraw.md
  - graphify/skill-opencode.md
  - graphify/skill-trae.md
  - graphify/skill-windows.md
  - graphify/prompts.py
  - tests/test_skill_prompt_drift.py
tech-stack:
  added: []
  patterns: [byte-identical-block-via-html-comment-bookends, drift-gate-parametrized-parity]
key-files:
  created:
    - .planning/phases/72-reas/72-02-SUMMARY.md
  modified:
    - graphify/skill.md
    - graphify/skill-aider.md
    - graphify/skill-claw.md
    - graphify/skill-codex.md
    - graphify/skill-copilot.md
    - graphify/skill-droid.md
    - graphify/skill-excalidraw.md
    - graphify/skill-opencode.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
    - graphify/prompts.py
    - tests/test_skill_prompt_drift.py
decisions:
  - D-01-applied: extended existing semantic-extraction skill prompts (no second classifier prompt)
  - D-02-applied: focused exemplars — ADR-0042 supersedes ADR-0028; ADR-0050 contradicts ADR-0042
  - D-03-applied: confidence + confidence_score rules per CCONF v1.13 documented in block
  - D-05-applied: endpoint constraint (doc/paper/rationale/concept only, no code) noted in block
  - prompt_version: 1.14.0 (cache key invalidation per Pitfall 2)
metrics:
  duration_seconds: 540
  tasks: 2
  files_changed: 12
  completed: 2026-05-07
---

# Phase 72 Plan 02: REAS — Skill Prompt Extension Summary

Extended the semantic-extraction skill prompts across all 10 platform variants with a byte-identical
reasoning-relations taxonomy block (5 relations + 2 ADR worked exemplars), bumped PROMPT_VERSION
1.13.0 → 1.14.0 to invalidate the confidence cache, and hardened the skill-prompt-drift gate with
3 new parity assertions.

## What was built

- **Reasoning-relations block** authored once in `graphify/skill.md` and replicated byte-identically
  to the 9 platform variants. Bounded by HTML comment markers
  `<!-- BEGIN: phase-72-reas reasoning-relations block -->` /
  `<!-- END: phase-72-reas reasoning-relations block -->` so the drift gate can extract and compare
  block content directly.
- **5 relations defined** with one-line semantics: `supports`, `contradicts`,
  `supersedes` (newer → older; target is the superseded node), `evolved_into`, `depends_on`.
- **Endpoint constraint** documented: both endpoints must be document/paper/rationale/concept-typed;
  code endpoints will be rejected by validate.py (per Plan 01, REAS-01, D-05).
- **Confidence rules** documented per CCONF v1.13: `confidence` ∈ {EXTRACTED, INFERRED, AMBIGUOUS};
  INFERRED requires `confidence_score` ∈ [0.0, 1.0]; EXTRACTED may omit the score.
- **Worked example 1** — ADR-0042 supersedes ADR-0028 (EXTRACTED).
- **Worked example 2** — ADR-0050 contradicts ADR-0042 (INFERRED, score 0.85).
- **Resolution note** for the build-layer two-pass resolver (Plan 03).
- **PROMPT_VERSION** bumped 1.13.0 → 1.14.0 in `graphify/prompts.py`. The Phase 65 prompt-version
  footer in every skill file was bumped in lockstep so the existing drift gate stays green.
- **Drift gate** extended with three new tests:
  - `test_prompt_version_bumped` — asserts PROMPT_VERSION == "1.14.0".
  - `test_reasoning_relations_block_parity` — extracts the BEGIN/END block from every skill file
    and asserts byte-identical content vs `skill.md`.
  - `test_adr_supersession_exemplar_present` — asserts every block contains `ADR-0042`, `ADR-0028`,
    `adr_0050`, the contradiction fragment, the orientation note, and all 5 relation names.

## Files changed

| File | Change |
|------|--------|
| `graphify/prompts.py` | PROMPT_VERSION 1.13.0 → 1.14.0 |
| `graphify/skill.md` | Append phase-72-reas block; bump footer 1.13.0 → 1.14.0 (canonical source) |
| `graphify/skill-aider.md` | Append identical block; bump footer |
| `graphify/skill-claw.md` | Append identical block; bump footer |
| `graphify/skill-codex.md` | Append identical block; bump footer |
| `graphify/skill-copilot.md` | Append identical block; bump footer |
| `graphify/skill-droid.md` | Append identical block; bump footer |
| `graphify/skill-excalidraw.md` | Append identical block; bump footer |
| `graphify/skill-opencode.md` | Append identical block; bump footer |
| `graphify/skill-trae.md` | Append identical block; bump footer |
| `graphify/skill-windows.md` | Append identical block; bump footer |
| `tests/test_skill_prompt_drift.py` | +3 parity tests for the reasoning block |

## Commits

- `00ffaec` feat(72-02): add reasoning-relation taxonomy block to skill.md and bump PROMPT_VERSION to 1.14.0
- `d404144` test(72-02): replicate reasoning-relations block to 9 platform skills and extend drift gate

## Verification

- `pytest tests/test_skill_prompt_drift.py -q` → 14 passed (was 11; +3 new tests).
- `pytest tests/test_skill_files.py tests/test_skill_persistence.py tests/test_skill_regex_fixture.py tests/test_skill_prompt_drift.py -q` → 36 passed.
- Block parity verified programmatically across all 10 skill files (regex extract + reference compare).
- All acceptance criteria from the plan are satisfied:
  - `grep -c "BEGIN: phase-72-reas reasoning-relations block" skill*.md` == 1 per file ✓
  - All 10 files contain `ADR-0042`, `ADR-0028`, `newer -> older`, `contradicts`, `evolved_into`, `depends_on` ✓
  - `python -c "from graphify.prompts import PROMPT_VERSION; assert PROMPT_VERSION == '1.14.0'"` ✓
  - `grep -c '"1.13.0"' graphify/prompts.py` == 0 ✓

## Anchor strategy chosen

The plan said "Step 3 Part B" but excalidraw and several other variants do not share a uniform Step
3 Part B structure (`skill-excalidraw.md` is a 90-line diagram skill with no extraction subagent;
`skill-aider.md`/`skill-claw.md` use "Step B3 - Cache and merge" wording). The single universal
anchor across all 10 files is the existing Phase 65 prompt-version footer
(`### Confidence scoring (Phase 65, prompt_version 1.13.0)`). The reasoning block was inserted
immediately after that footer in every file, keeping the block byte-identical and giving the drift
gate a stable extraction target. This satisfies the spirit of the plan (extend the prompt body that
travels through cache-invalidation) without forcing a heterogeneous insertion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan asserted `ADR-0050` literal in the contradiction exemplar; emit JSON uses lowercase id `adr_0050`**
- **Found during:** Task 2 drift-gate test run.
- **Issue:** Initial `test_adr_supersession_exemplar_present` asserted `"ADR-0050"` but the worked example's emit JSON uses the canonical lowercased id `adr_0050` (matching `_make_id` convention used elsewhere in the prompt).
- **Fix:** Test asserts `adr_0050` (the emit id) and `0050-revisit` (the input fragment filename), which together prove both halves of the contradiction exemplar are present.
- **Files modified:** `tests/test_skill_prompt_drift.py`
- **Commit:** `d404144`

### Out of scope (deferred per scope boundary)

- 47 pre-existing test failures in `tests/test_vault_cwd.py` and `tests/test_vault_parity.py` are
  unrelated to this plan (verified by stashing all my changes and rerunning — same vault
  failures occurred). Logged for future investigation; not addressed here.

## Threat Flags

None — purely additive prompt content. The block contains no executable code, no template
injection points beyond what the existing prompt already accepts. T-72-04 mitigation
(BEGIN/END markers + parity assertion) is now in place.

## Self-Check: PASSED

- `graphify/prompts.py` PROMPT_VERSION == "1.14.0" — verified.
- All 10 skill files contain the BEGIN/END block — verified by grep + parity test.
- Drift gate green: `pytest tests/test_skill_prompt_drift.py -q` → 14 passed.
- Commit hashes `00ffaec` and `d404144` exist in `git log --oneline`.
