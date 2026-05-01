# Phase 53: Concept↔code schema & build merge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 53-concept-code-schema-build-merge
**Areas discussed:** New relation vocabulary, Stable ID strategy, Confidence rule for new relations, Stability acceptance bar

---

## New relation vocabulary

| Option | Description | Selected |
|--------|-------------|----------|
| documents | Doc/code artifact cites a concept (doc → concept). LLM-extractable. | ✓ |
| tests | Test asserts behavior of a concept (test → concept). | ✓ |
| realizes / instantiates | Stronger typed (interface→concept; concrete→concept). OO-leaning. | ✓ |
| Just harden `implements` | No new relations; only stabilize existing. | (initially also marked, then clarified out) |

**User's choice:** All three new relation families + harden `implements` (after clarification — user's first answer was multi-select all four; clarification confirmed maximum scope).
**Notes:** User wants full concept↔code coverage in this phase rather than spreading it across multiple v1.11 phases.

---

## Stable ID strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Lexicographic merge + canonical source_file list | Keep `(src, tgt, relation)` key; sort `source_files`, `max(confidence_score)`, lowest `source_location` | ✓ |
| Content hash edge ID | Add `edge_id = sha256(...)` field across the schema | |
| Enforce extractor ordering | Push burden to every extractor | |
| Decide during planning | Defer to researcher | |

**User's choice:** Lexicographic merge + canonical source_file list (Recommended).
**Notes:** Smallest invasive change, keeps existing `(src, tgt, rel)` key contract for MCP/export/telemetry consumers.

---

## Confidence rule for new relations

| Option | Description | Selected |
|--------|-------------|----------|
| INFERRED-default with explicit-EXTRACTED escape | New relations default INFERRED + score; EXTRACTED requires `evidence` field | ✓ |
| Per-relation rules | `realizes`/`instantiates` EXTRACTED-only; `documents`/`tests` INFERRED-only | |
| Free choice | Any confidence; no schema enforcement | |
| AMBIGUOUS-default | All four default AMBIGUOUS unless explicitly upgraded | |

**User's choice:** INFERRED-default with explicit-EXTRACTED escape (Recommended).
**Notes:** Structural defense against over-confident LLM tags — `evidence` field becomes a contract, not a suggestion.

---

## Stability acceptance bar

| Option | Description | Selected |
|--------|-------------|----------|
| Identical edges in identical order | Re-run produces same list (set+order); requires canonical sort | ✓ |
| Identical edge set | Order-agnostic set equality | |
| graph.json byte-for-byte | Strictest; catches export non-determinism | |
| Single-fixture regression test only | Snapshot one golden fixture | |

**User's choice:** Identical edges in identical order (Recommended).
**Notes:** Strongest guarantee Phase 53 can deliver without expanding scope into export-layer determinism. Canonical sort (D-53.06) is the enabling step.

---

## Claude's Discretion

- Test file layout (one new module vs additions to existing test files) — planner decides.
- Whether new relations get tree-sitter AST signals in this phase — researcher to evaluate; default LLM-only.
- Specific docstring/annotation format for `evidence` — researcher to investigate.

## Deferred Ideas

- `graph.json` byte-for-byte equality (export-layer determinism) — future hygiene phase.
- Content-hash edge IDs — revisit if/when MCP needs label-rename resilience.
- AST-based extractors for `realizes` / `instantiates` — extractor-coverage follow-up.
- Per-language `evidence` annotation parsers (e.g., `# graphify:`, `// @graphify`) — extractor-side follow-up phase.
