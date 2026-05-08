# Phase 73 — DEDUP: Discussion Log

**Date**: 2026-05-08
**Mode**: discuss (default)

## Areas Selected
All four gray areas: Corpus selection, Normalization recipe, Genuine-collision classification, Artifact location & format.

## Q&A

### Q1 — Corpus selection
**Options**: Self-corpus (graphify) | Mixed (graphify + sibling + arxiv) | Heavy mixed (3 distinct external sources)
**Selected**: Heavy mixed — 3 distinct external sources (code repo + doc-heavy repo + paper set)
**Rationale**: Strongest representativeness; matches DEDUP-01 wording literally. Researcher will pick concrete paths from `companion-util_repos/` siblings.

### Q2 — Normalization recipe
**Options**: Conservative (label-only, lowercase) | Standard (label, lowercase + strip punct) | Aggressive (label + description[:200], full normalize) | Run multiple recipes
**Selected**: Aggressive — `sha256(norm(label) + "|" + norm(description[:200]))`, lowercase + strip-punct + collapse-whitespace. Stemming optional, off by default.
**Rationale**: Spike measures worst-case dedup pressure; conservative would under-count.

### Q3 — Genuine-collision classification
**Options**: Manual sample (30 pairs) | LLM-judge | Cross-check vs semantically_similar_to | Manual + cross-check
**Selected**: Cross-check vs semantically_similar_to edges — fully deterministic.
**Rationale**: Re-runnable by anyone, no LLM cost, no human-sample bias. Closes the third measurement point of Q-2026-05-07-01 directly. Decision rule updated: **Ship if raw > 5% AND residual (un-covered by sem-sim) > 5%**.

### Q4 — Artifact location & format
**Options**: 73-SPIKE.md in phase dir | Q-...-results.md in research dir | Both with cross-link
**Selected**: Phase-scoped `73-SPIKE.md` as canonical, optional lightweight cross-link from questions.md.
**Rationale**: Phase-scoped artifact stays auditable inside the milestone with predictable GSD shape; researcher/verifier know where to find it.

## Deferred Ideas Captured
- Implementation of node-level fingerprint dedup (DEDUP-02..N — gated by this spike)
- Manual/LLM-judge classification (rejected for this phase, available for future deeper analysis)
- Embedding-based detection (project-level out-of-scope)
- Multi-recipe comparison (rejected to keep timeboxed)

## Claude's Discretion (not asked)
- Researcher will confirm exact corpus paths; spike-script lives at `scripts/dedup_spike.py` by default.
- NLTK stemming off by default; on only if it materially changes the rate, then both reported.
- `confidence_score` threshold for sem-sim edges defaults to "any edge counts" unless researcher finds a reason to threshold.
