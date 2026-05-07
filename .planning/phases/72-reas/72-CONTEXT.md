# Phase 72: REAS - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Document and concept nodes carry typed reasoning-relation edges (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) extracted by the existing semantic prompt; `analyze.py` produces a Contradictions and Supersession Chains section; `report.py` GRAPH_REPORT.md and `wiki.py` per-community articles render reasoning relations as a distinct subsection; Obsidian export preserves them as typed wikilinks distinguishable from structural relations.

</domain>

<decisions>
## Implementation Decisions

### 1. Extraction trigger & prompt shape (REAS-02)
- **D-01:** Extend the EXISTING semantic-extraction prompt for documents (md/txt/rst), papers (PDF), and rationales — single LLM pass per doc, no second classifier prompt and no signal-gating. Cheaper and keeps prompt evolution centralized.
- **D-02:** Prompt exemplars are FOCUSED: two worked examples — ADR supersession chain (ADR-0042 supersedes ADR-0028) and an ADR contradiction. The other three relations (`supports`, `evolved_into`, `depends_on`) get a one-line definition only. REAS-02 only mandates ADR examples for supersession and contradiction.
- **D-03:** Reasoning edges emit `confidence` (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`) and `confidence_score` per the CCONF v1.13 contract. Mirrors Phase 53's evidence/score rule: INFERRED requires `confidence_score ∈ [0.0, 1.0]`. Researcher to decide whether reasoning edges need an `evidence` field analogous to the Phase 53 `documents/tests/realizes/instantiates` rule, or if `confidence_score` alone is sufficient.

### 2. Cross-document edges & dangling targets
- **D-04:** **Two-pass build resolution.** First pass extracts all reasoning edges with raw target strings (id or label). Second pass resolves them against the now-complete node set after every doc has been extracted. Unresolved targets after pass 2 are dropped with a stderr warning (`[graphify] dangling reasoning edge ...`). No stub-node creation.
- **D-05:** **Both endpoints must be document-typed or concept-typed.** Reject reasoning relations if EITHER source OR target is a code-typed node. validate.py enforces; build.py honors. This is stricter than REAS-01's literal wording but semantically defensible — reasoning is about ideas/claims, not code artifacts.
- **D-06:** Validation pattern follows the existing `validate.py` shape: return error strings, do not raise. build.py decides whether to drop or fail. Match how the Phase 53 concept↔code rules behave today.

### 3. Interaction with Phase 71 temporal layer
- **D-07:** **`supersedes` auto-stamps `valid_until` on outbound edges of the superseded node.** When build.py lands a new `A supersedes B` edge, it iterates ALL outbound edges of B and stamps `valid_until` with the current run timestamp.
- **D-08:** Stamp scope is **all outbound edges** of B — both reasoning relations (`B supports X`) AND structural relations (`B references Y`). Maximal historical capture; once a node is superseded, all its outbound claims/relations become historical and surface in the wiki's `## Historical relations` subsection (Phase 71-05 already renders that section when `valid_until` is set).
- **D-09:** Stamp is one-shot at supersession-edge insertion time. If a future run produces a NEW supersedes (e.g., `A2 supersedes B`), no re-stamping needed — the edges are already historical. The `supersedes` edge itself follows Phase 71's normal stamping rules (valid_from on emission, valid_until on disappearance from re-runs).
- **D-10:** Stamping does NOT create new edges — it mutates `valid_until` on existing edges in graph.json. Idempotent: re-running with the same supersedes input is a no-op.

### 4. Contradictions & supersession-chain rendering (REAS-03 + REAS-04)
- **D-11:** **`analyze.py` Contradictions and Supersession Chains section is confidence-gated:** include only edges with `confidence_score >= 0.5`. EXTRACTED edges (no score) are always included. AMBIGUOUS edges and weak INFERRED edges (< 0.5) stay in the graph but are excluded from this report section. Cuts noise; aligns with CCONF v1.13 mid-confidence threshold spirit.
- **D-12:** Sorting: longest supersession chains first; contradiction pairs sorted by confidence_score descending. No top-N cap initially (revisit if reports get noisy).
- **D-13:** **`analyze.py` knowledge_gaps must NOT misclassify isolated reasoning-edge endpoints as gaps** (REAS-03 line). Add reasoning-relation predicate to the existing `isolated` reason filter at `analyze.py:495–504`.
- **D-14:** **`wiki.py` rendering: separate `## Reasoning Relations` subsection** in per-community articles, placed above the existing `## Relationships` section and above `## Historical relations`. Lists only the 5 reasoning relation types. Subsection omitted entirely when no reasoning edges exist for the community (mirrors the Phase 71-05 Historical relations omission rule).
- **D-15:** **Obsidian export rendering:** reasoning relations appear in note frontmatter as a YAML list `reasoning_relations: [{type, target, confidence_score}]`. Distinguishable from structural relations (which stay as inline wikilinks in the body). Researcher to verify export.py's existing Obsidian frontmatter shape and confirm this addition does not collide with vault-profile templates.
- **D-16:** **`report.py` GRAPH_REPORT.md** gets the new "Contradictions and Supersession Chains" section as a top-level addition; format follows existing section conventions (one short paragraph per chain/pair with source-node citations).

### Claude's Discretion
- Exact placement of the two-pass resolution logic in `build.py` (new helper vs inline in `build()`).
- Whether to share resolution code with the existing `dangling stdlib import` warning pattern.
- Whether the prompt-extension lives inline in the existing prompts in `prompts.py` or as a new appended block (researcher decision; coordinate with `PROMPT_VERSION` bump).
- Concrete YAML key naming in Obsidian frontmatter beyond `reasoning_relations` (e.g., per-target wikilink syntax).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 72 success criteria (REAS section)
- `.planning/REQUIREMENTS.md` — REAS-01 through REAS-04 definitions (lines 22–25)

### Phase 71 (preceding phase, schema layer)
- `.planning/phases/71-temp/71-CONTEXT.md` — Temporal Edge Validity decisions; D-04 backward-compat read pattern reused here
- `.planning/phases/71-temp/71-VERIFICATION.md` — verification status: passed
- `graphify/build.py` — `SCHEMA_VERSION` (already bumped to "2.0" in Phase 70.2/71); supersedes auto-stamp logic lands here
- `graphify/wiki.py` (lines 89–110) — existing `## Historical relations` rendering established by Phase 71-05; precedent for the new `## Reasoning Relations` subsection

### Validation and relation vocabulary
- `graphify/validate.py` — `KNOWN_EDGE_RELATIONS` (lines 14–43), `NEW_CONCEPT_CODE_RELATIONS` and Phase 53 evidence/confidence_score rules (lines 52–69, 178–214) — REAS-01 extension follows this pattern
- `docs/RELATIONS.md` — canonical relation vocabulary doc; the 5 new reasoning relations must be documented here as part of this phase

### Extraction
- `graphify/extract.py` — semantic-extraction paths for documents/papers/rationales (D-01 prompt extension)
- `graphify/prompts.py` (`PROMPT_VERSION` import in extract.py:17) — bump expected; ADR exemplar block added

### Analysis and rendering
- `graphify/analyze.py` (lines 495–504, 661–685) — `knowledge_gaps` isolated-node filter; D-13 needs reasoning-edge predicate
- `graphify/report.py` — GRAPH_REPORT.md generation; new top-level "Contradictions and Supersession Chains" section
- `graphify/export.py` — Obsidian export with vault profile; verify reasoning_relations frontmatter shape

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`, `STACK.md`, `CONVENTIONS.md` — existing structural maps consulted

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`validate.py:52–69` (Phase 53 NEW_CONCEPT_CODE_RELATIONS pattern)** — direct precedent for adding REAS-01: a frozenset of relation names plus per-relation confidence/evidence rules. The 5 reasoning relations slot in as a sibling frozenset (e.g., `REASONING_RELATIONS`).
- **`wiki.py:89–110` Historical-relations subsection (Phase 71-05)** — the exact rendering shape for D-14 `## Reasoning Relations` subsection, including the "omit when empty" rule.
- **Phase 65 schema_version read/write split (in `validate.py:231–258`)** — referenced by Phase 71 D-04. Same backward-compat philosophy: legacy graph.json without reasoning relations loads without error.
- **`extract.py:17` PROMPT_VERSION import** — bump signals re-extraction in cache invalidation.

### Established Patterns
- **Validation returns error list (`list[str]`), does not raise** (validate.py module-wide). REAS-01's "reject reasoning relations on code nodes" follows this — error appended to the list, build.py decides.
- **`KNOWN_EDGE_RELATIONS` is a single-source frozenset** consulted by `warn_unknown_relations`. The 5 new relations must be added there too, otherwise extractors produce stderr warnings.
- **Two-pass extraction-then-resolution is novel for graphify.** Existing extraction is one-pass per file. D-04 introduces a new build-layer pass; researcher should decide whether to land it as a new function in `build.py` or extend `build_from_json`.
- **CCONF v1.13 confidence_score contract** (per-edge float in [0.0, 1.0] for INFERRED) — REAS-02 and D-03 inherit this verbatim.

### Integration Points
- `validate.py` — add `REASONING_RELATIONS` frozenset; extend the per-edge validation loop to enforce node-type endpoint rule (D-05); update `KNOWN_EDGE_RELATIONS`.
- `extract.py` semantic prompt path — extend the existing prompt with the 5-relation taxonomy + ADR exemplars (D-01, D-02).
- `prompts.py` — bump `PROMPT_VERSION` so cache invalidates and re-extracts under the new prompt.
- `build.py` — two-pass target resolution (D-04); supersedes auto-stamp on outbound edges of B (D-07, D-08).
- `analyze.py` — new "Contradictions and Supersession Chains" producer (D-11, D-12); fix isolated-node filter to exclude reasoning-edge endpoints (D-13).
- `report.py` — new top-level GRAPH_REPORT.md section consuming analyze.py output (D-16).
- `wiki.py` — new `## Reasoning Relations` subsection above existing sections (D-14).
- `export.py` Obsidian path — `reasoning_relations` frontmatter list (D-15).
- `docs/RELATIONS.md` — document the 5 new relations.

</code_context>

<specifics>
## Specific Ideas

- ADR supersession chains are the primary motivating example throughout — keep prompt exemplars and report citations in that domain.
- `## Reasoning Relations` subsection in wiki articles must mirror the Phase 71-05 `## Historical relations` shape (omit when empty, render valid edges only).
- Frontmatter list shape `reasoning_relations: [{type, target, confidence_score}]` keeps Obsidian queryable via Dataview without colliding with body wikilinks.

</specifics>

<deferred>
## Deferred Ideas

- **Top-N caps on report sections** — only revisit if reports become noisy in practice. Default is unbounded with confidence gate.
- **Stub-node creation for unresolved reasoning targets** — rejected in favor of two-pass resolve + drop. If unresolved-edge volume becomes a real loss, reconsider in a follow-up.
- **Second-pass dedicated reasoning classifier prompt** — chosen single-pass extension instead. Revisit if extraction quality on reasoning relations is poor at v2.0 ship.
- **Signal-triggered (gated) extraction** — rejected; full pass keeps quality predictable.
- **`evidence` field for reasoning relations (analogous to Phase 53)** — researcher to evaluate; deferred until research signals it's needed.

</deferred>

---

*Phase: 72-REAS*
*Context gathered: 2026-05-07*
