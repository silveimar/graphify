# Phase 72: REAS - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 72-REAS
**Areas discussed:** Extraction trigger & prompt shape, Cross-document edges & dangling targets, Interaction with Phase 71 temporal layer, Contradictions & supersession-chain rendering

---

## Extraction trigger & prompt shape

### Q1: Where reasoning extraction lives

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing semantic prompt | Single LLM pass per doc, cheaper, prompt grows | ✓ |
| Second-pass classifier prompt | Cleaner separation, ~2x token cost | |
| Gated second-pass (signal-triggered) | Cheap when no signal; full classifier when signal present | |

**User's choice:** Extend existing semantic prompt.

### Q2: Prompt exemplar depth

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: one example per relation | 5 short one-liners | |
| Focused: ADR supersession + contradiction only | Two worked ADR examples; one-liner defs for the rest | ✓ |
| Comprehensive: ADR + non-ADR per relation | 2 examples per relation; ~2x prompt growth | |

**User's choice:** Focused — matches REAS-02's literal mandate.

---

## Cross-document edges & dangling targets

### Q1: Unresolved-target handling

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve at build time, drop unresolved with warning | Mirrors dangling stdlib import pattern | |
| Resolve at build time, create stub document node | Risk: noisy graph with stub nodes | |
| Two-pass build: resolve only after all docs extracted | More logic; better resolution rate | ✓ |

**User's choice:** Two-pass build.

### Q2: Cross-type rule for reasoning edges

| Option | Description | Selected |
|--------|-------------|----------|
| Source must be doc/concept; target unrestricted | Strict on source only, matches REAS-01 wording | |
| Both endpoints must be doc/concept | Cleanest semantics; rejects doc→code reasoning | ✓ |
| Source doc/concept; target must exist (no synthesizing) | Source-strict + post-resolve target validation | |

**User's choice:** Both endpoints must be doc/concept.

---

## Interaction with Phase 71 temporal layer

### Q1: Auto-stamp on supersedes

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — supersedes auto-stamps valid_until on superseded node's outbound edges | Tightly couples reasoning + temporal | ✓ |
| Yes — but only stamp the supersedes edge's history | Symmetric; minimal new logic | |
| No — reasoning + temporal are independent layers | Cleanest separation | |

**User's choice:** Auto-stamp outbound edges of superseded node.

### Q2: Stamp scope

| Option | Description | Selected |
|--------|-------------|----------|
| All outbound edges of superseded node | Maximal historical capture | ✓ |
| Only outbound REASONING edges | Structural references stay valid | |
| Only outbound EXTRACTED reasoning edges | Minimal overlap with Phase 71's decay | |

**User's choice:** All outbound edges.

---

## Contradictions & supersession-chain rendering

### Q1: analyze.py inclusion threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Everything detected, longest chains first | Full audit trail, may be noisy | |
| Confidence-gated: confidence_score >= 0.5 | Cuts noise; matches CCONF mid-confidence threshold | ✓ |
| Top-N capped (chains: 10; pairs: 20) | Predictable report size | |

**User's choice:** Confidence-gated.

### Q2: Wiki + Obsidian distinguishability

| Option | Description | Selected |
|--------|-------------|----------|
| Inline with structural, prefixed by relation type | Minimal new UI | |
| Separate `## Reasoning Relations` subsection | Clearest UX; Obsidian frontmatter `reasoning_relations:` list | ✓ |
| Separate subsection for chains/contradictions only; inline for the rest | Hybrid | |

**User's choice:** Separate subsection + frontmatter list.

---

## Claude's Discretion

- Exact placement of two-pass resolution helper in `build.py`.
- Whether to share resolution code with the existing dangling stdlib import warning pattern.
- Whether prompt extension lives inline in existing prompt or as appended block in `prompts.py` (researcher decision; coordinate `PROMPT_VERSION` bump).
- Concrete YAML key naming in Obsidian frontmatter beyond `reasoning_relations`.
- Whether reasoning edges need an `evidence` field analogous to Phase 53's rule.

## Deferred Ideas

- Top-N caps on report sections (revisit if noisy).
- Stub-node creation for unresolved targets.
- Second-pass dedicated reasoning classifier prompt (revisit if quality is poor at ship).
- Signal-triggered gated extraction.
- Per-relation `evidence` field for reasoning edges.
