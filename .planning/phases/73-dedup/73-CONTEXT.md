# Phase 73 — DEDUP: Phase Context

**Phase**: 73 (DEDUP)
**Date**: 2026-05-08
**Milestone**: v2.0 — Graph Schema Deepening
**Status**: Context captured, ready for research/planning

<domain>
Measurement-only spike. Run graphify against a representative multi-source corpus, fingerprint normalized concept-node labels+descriptions with SHA-256, measure the near-duplicate collision rate, cross-check against existing `semantically_similar_to` edges to compute residual coverage gap, and exit with a ship/defer recommendation in a phase-scoped artifact. **No `_make_id()` or `build.py` changes ship in this phase regardless of outcome.** DEDUP-02..N implementation is gated on this spike clearing >5% AND residual not already collapsed by sem-sim edges.
</domain>

<canonical_refs>
- `.planning/ROADMAP.md` — Phase 73 entry, success criteria
- `.planning/REQUIREMENTS.md` — DEDUP-01 (locked threshold and corpus shape); DEDUP-02..N backlog
- `.planning/research/questions.md` — Q-2026-05-07-01 (origin question; this phase resolves it)
- `.planning/notes/ob1-comparison-2026-05-07.md` — § P2 item #4 (origin context, OB1's `recipes/content-fingerprint-dedup`)
- `graphify/extract.py` — `_make_id()` (current name-based dedup, the baseline being measured against)
- `graphify/build.py` — node deduplication seams (3-level dedup mentioned in CLAUDE.md)
- `graphify/cluster.py` — Leiden community detection (downstream consumer of any dedup change)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md` — pipeline shape, schema invariants
</canonical_refs>

<prior_decisions>
**Project-level (PROJECT.md / REQUIREMENTS.md):**
- Spike-only deliverable; implementation gated by measurement
- Threshold locked: >5% AND genuine collisions → ship; else defer
- Corpus shape locked: ≥1 code repo + ≥1 doc-heavy directory + ≥1 PDF/paper set
- Fingerprint algorithm locked: SHA-256 of normalized label/description
- DEDUP-02..N stays in backlog regardless of outcome

**From v2.0 milestone setup (memory S173, S172):**
- v2.0 is "Graph Schema Deepening" — deeper edge semantics over new features
- OB1-RECIPE seeded as a future integration; this dedup question came from that comparison

**No prior CONTEXT.md decisions in v2.0 conflict** — Phase 71 (TEMP) and Phase 72 (REAS) touch edges, not the node-id pipeline.
</prior_decisions>

<decisions>

### Corpus selection — Heavy mixed (3 distinct external sources)
- **What**: Pick three concrete corpora at research time:
  1. A real **code repo** (candidate: `~/Documents/silogia-repos/engineering-tools/claude-code-templates` or similar sibling under `companion-util_repos/`)
  2. A **doc-heavy repo** (candidate: `claude-cookbooks` or similar)
  3. A **paper set** (candidate: PDFs from `awesome-ai-agent-papers` or arxiv mirror in companion repos)
- **Why**: Strongest representativeness; matches the literal "≥1 code repo + ≥1 doc-heavy directory + ≥1 PDF/paper set" of DEDUP-01.
- **Constraint**: Must fit within a reasonable spike timebox. If runtime exceeds ~1h, researcher may downsample within each source rather than swapping for narrower sources.
- **Researcher task**: Confirm exact paths exist, document command invocations, and capture corpus size metrics (file count, byte size, est. node count) for reproducibility.

### Normalization recipe — Aggressive (label + description[:200], full normalize)
- **Formula**:
  ```
  norm(s) = collapse_ws( strip_punct( s.lower() ) )
  fingerprint = sha256( norm(label) + "|" + norm(description[:200]) )
  ```
- **Rules**:
  - `lower()` → ASCII case-fold
  - `strip_punct` → remove all non-alphanumeric, non-whitespace chars (regex `[^\w\s]` → `""`)
  - `collapse_ws` → split-and-rejoin on whitespace (single space)
  - Description truncated to **first 200 chars** (post-normalization, not pre)
  - **Stemming**: optional, **off by default** — researcher to decide whether NLTK Porter stemming materially changes the result; if it does, report both with-stemming and without-stemming rates
- **Why aggressive**: Catches `Transformer.` vs `Transformer`, `multi-head attention` vs `Multi Head Attention`, etc. The spike's job is to measure *worst-case* dedup pressure; conservative recipes would under-count and leave the question half-answered.
- **Scope warning**: When `description` is missing or empty, fingerprint = `sha256(norm(label) + "|")` — degenerate but consistent. Researcher must call this out in artifact methodology.

### Genuine-collision classification — Cross-check vs semantically_similar_to edges
- **Method**: For each set of nodes sharing a fingerprint, query the graph for existing INFERRED `semantically_similar_to` edges between them. Compute:
  - **Raw collision rate** = (nodes in any collision set) / (total concept nodes)
  - **Residual collision rate** = (nodes in collision sets with NO sem-sim edge linking them) / (total concept nodes)
- **Decision rule** (replaces "AND genuine collisions"):
  - **Ship** if raw > 5% AND residual > 5% (existing sem-sim edges insufficient)
  - **Defer** if raw ≤ 5% OR residual ≤ 5% (sem-sim already collapses the cases that matter)
- **Why this method**: 100% deterministic, re-runnable by anyone with the same corpus, no LLM-judge cost, no manual-sample bias. Closes Q-2026-05-07-01's third measurement point ("Check whether INFERRED `semantically_similar_to` edges already cover this case adequately") cleanly.
- **Trade-off accepted**: This treats the absence of a sem-sim edge as evidence of distinctness even when the edge could have been inferred but wasn't. Acceptable for a measurement spike — false-positives only inflate the recommendation toward "ship", which the >5% gate then absorbs.

### Artifact location & format — Phase-scoped 73-SPIKE.md
- **Path**: `.planning/phases/73-dedup/73-SPIKE.md`
- **Required sections**:
  1. **Summary** — one-paragraph recommendation (Ship | Defer) with the two key numbers
  2. **Corpus** — exact paths, file counts, byte sizes, command invocations to reproduce
  3. **Method** — normalization formula (verbatim), classification method, sem-sim cross-check query
  4. **Results** — table with raw rate, residual rate, total concept nodes, total collisions, sem-sim coverage %
  5. **Recommendation** — Ship / Defer with rationale tied to the decision rule
  6. **Appendix: Collision sample** — first 20 collision sets (label + description excerpt + source_files) for human spot-check, even though classification is automated
- **Cross-link** (lightweight, optional): When the spike completes, the executor may flip Q-2026-05-07-01 status in `.planning/research/questions.md` to "Resolved — see .planning/phases/73-dedup/73-SPIKE.md", but the artifact itself stays canonical inside the phase directory. No duplication of data.

</decisions>

<deferred>
- **Implementation of node-level fingerprint dedup** in `_make_id()` / `build.py` — this is DEDUP-02..N, explicitly out of scope; only ships if this spike's recommendation is Ship.
- **Manual / LLM-judge classification of collisions** — considered, rejected for this phase in favor of deterministic sem-sim cross-check. If a future phase needs deeper semantic analysis of collisions, capture as new research question.
- **Embedding-based collision detection** — out of scope per project-level "Out of Scope" exclusions in REQUIREMENTS.md.
- **Multi-recipe comparison (conservative + standard + aggressive)** — considered as a normalization option, rejected to keep the spike timeboxed; aggressive recipe is sufficient for a Ship/Defer decision.
</deferred>

<code_context>
- **`_make_id()` in `graphify/extract.py`**: Current dedup is name-based (slug-from-label). The spike measures *what fraction of nodes this misses*.
- **`build.py` (3-level dedup)**: CLAUDE.md mentions "Node deduplication happens at three levels" — researcher should document the three levels in 73-SPIKE.md Method section so the recommendation is grounded.
- **`semantically_similar_to` edges**: INFERRED, with `confidence_score`. Produced during semantic extraction. The cross-check query needs to handle confidence_score thresholds — researcher to decide whether to count edges below e.g. 0.5 as "linking" or not.
- **Existing test fixtures** (`tests/fixtures/`) are NOT representative for this spike — too small, too contrived. The spike must use real external corpora.
- **No new graphify code ships this phase.** The fingerprint computation lives in a one-shot script (likely `scripts/dedup_spike.py` or inline in 73-SPIKE.md), not in `graphify/`.
</code_context>

<open_questions_for_research>
- Confirm exact corpus paths exist on this machine; if a candidate is missing, researcher proposes a substitute under `companion-util_repos/` siblings.
- Confirm whether NLTK is acceptable as a transient spike-script dependency (not a graphify package dep) for optional stemming, OR keep stemming off entirely. Default: off.
- Confirm the `confidence_score` threshold for counting a `semantically_similar_to` edge as "linking" two nodes (suggested default: any edge counts, regardless of score).
- Confirm spike-script location — `scripts/dedup_spike.py` (committed under repo) vs inline-in-artifact code blocks (no new file). Default: `scripts/dedup_spike.py` for reproducibility.
</open_questions_for_research>

<next_steps>
- `/clear` then `/gsd-plan-phase 73` to produce PLAN.md (researcher will run first, hit the open questions above, then planner will sequence execution).
- Plan should include: spike-script implementation, corpus run, results aggregation, artifact authoring, and Q-2026-05-07-01 status flip.
</next_steps>
