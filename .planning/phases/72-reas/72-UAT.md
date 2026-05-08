---
status: complete
phase: 72-reas
source:
  - 72-01-SUMMARY.md
  - 72-02-SUMMARY.md
  - 72-03-SUMMARY.md
  - 72-04-SUMMARY.md
started: 2026-05-07T23:15:00Z
updated: 2026-05-07T23:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Reasoning-relation vocabulary accepted by validator
expected: `pytest tests/test_validate.py -x -q` → 31 passed (5 new reasoning tests).
result: pass

### 2. Skill prompt parity & cache invalidation
expected: `pytest tests/test_skill_prompt_drift.py -q` → 14 passed; PROMPT_VERSION == "1.14.0" in graphify/prompts.py; all 10 skill files contain a `BEGIN: phase-72-reas reasoning-relations block` marker.
result: pass

### 3. Build pipeline resolves reasoning targets and stamps supersedes outbound
expected: `pytest tests/test_build.py tests/test_validate.py tests/test_temporal.py -x -q` → 90 passed. _resolve_reasoning_targets rewrites label/substring matches to ids; unresolved targets dropped with stderr warning; supersedes outbound edges get valid_until stamped (idempotent, no new edges).
result: pass

### 4. Reasoning rendering across analyze / report / wiki / obsidian
expected: 10 reasoning-rendering tests pass — knowledge_gaps no longer flags reasoning-anchored doc nodes; contradictions_and_chains() returns cycle-safe chains (longest first) and contradictions (highest confidence first); GRAPH_REPORT.md emits `## Contradictions and Supersession Chains` only when populated; wiki community articles emit `## Reasoning Relations` before Relationships/Historical with html-escaped labels; Obsidian frontmatter emits a `reasoning_relations:` YAML list of JSON-scalar items.
result: pass

### 5. End-to-end graphify run on ADR fixtures surfaces reasoning artifacts
expected: Running graphify on the new tests/fixtures/adr_supersession.md and tests/fixtures/adr_contradiction.md (or any vault containing reasoning edges) produces: (a) GRAPH_REPORT.md with the Contradictions/Supersession section populated, (b) wiki article(s) with a `## Reasoning Relations` subsection, (c) obsidian notes with `reasoning_relations:` frontmatter list. No stderr cycle warning on acyclic input.
result: pass
evidence: |
  Programmatic E2E run via /tmp/uat_e2e.py with synthetic extraction (3 ADR docs + 1 concept,
  3 reasoning edges: supersedes EXTRACTED, contradicts INFERRED 0.85, depends_on EXTRACTED).
  - GRAPH_REPORT.md emitted "## Contradictions and Supersession Chains" with both subsections
    populated (chain ADR-0042 → ADR-0028; contradiction ADR-0050 ⇄ ADR-0042 conf 0.85).
  - wiki/community_0.md emitted "## Reasoning Relations" with all three relations including
    contradicts confidence annotation.
  - obsidian/Atlas/Sources/Graphify/Things/Adr-0050_Revisit.md frontmatter contained
    reasoning_relations: list with JSON-encoded scalar items round-tripping {type, target,
    confidence_score}.
  - No supersession-cycle stderr warning emitted.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
