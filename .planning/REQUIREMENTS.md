# graphify v1.13 — Concept Intelligence & Audit Closure: Requirements

**Milestone:** v1.13
**Goal:** Promote concept↔code edges from a structural feature to a knowledge-reasoning tool (cross-repo identity, semantic confidence, drift detection, parameterized queries), close the remaining vault-CWD seed bullet, and resolve all v1.12 audit-deferred items.
**Phase numbering:** continues from v1.12 (last phase 62.1) → starts at **Phase 63**.
**Source seeds:** SEED-bidirectional-concept-code-links (35% remaining), SEED-vault-root-aware-cli (20% remaining — Option B).

---

## v1.13 Requirements

### CCONF — Per-Edge Concept Confidence
- [ ] **CCONF-01**: Concept↔code edges emit per-edge `confidence_score ∈ [0.0, 1.0]` from LLM scoring (replaces uniform `1.0` baseline shipped in v1.10–v1.12).
- [ ] **CCONF-02**: INFERRED edges include an `evidence` field carrying the textual basis for the assigned score.
- [ ] **CCONF-03**: Confidence cache lives in a separate namespace keyed on `prompt_version + model + edge_signature` (independent from the existing `extract.py` file-hash cache); bumping `prompt_version` invalidates only confidence entries.
- [ ] **CCONF-04**: GRAPH_REPORT.md gains a calibration self-check section that flags suspicious score distributions (e.g., >70% of scores clustered in 0.85±0.05).
- [ ] **CCONF-05**: `validate.py` enforces "optional on read, required on write" with a new `schema_version` field; a frozen v1.10–v1.12 legacy fixture must pass read validation in `tests/`.

### CFED — Cross-Repo Concept Federation
- [ ] **CFED-01**: User can opt into cross-repo federation via an explicit CLI flag; default behaviour is off (federation never runs without consent).
- [ ] **CFED-02**: Federation is deterministic — namespaces all node IDs as `{repo}::{id}`; merges only when multi-signal evidence (label + shared neighborhood + source-path overlap) all agree. No embeddings, no LLM arbitration.
- [ ] **CFED-03**: A federation manifest records per-repo provenance for every merged concept (which repos contributed, which signals matched).
- [ ] **CFED-04**: `graphify/federate.py` runs as a build-time merge step after `_normalize_concept_code_edges` in `build.py` and before `cluster.py`.
- [ ] **CFED-05**: GRAPH_REPORT.md gains a Federation section listing merged concepts with their provenance entries.

### CDRIFT — Edge-Level Concept Drift
- [ ] **CDRIFT-01**: Drift detection compares snapshots via community-membership **Jaccard similarity**, never via community names or IDs (which rename for benign reasons even with stable membership).
- [ ] **CDRIFT-02**: Each `implements` / `documents` / `tests` edge is classified across snapshots as one of: `stable` / `community-renamed` / `community-resharded` / `orphaned`.
- [ ] **CDRIFT-03**: GRAPH_REPORT.md gains a Drift section when a prior snapshot exists; absent snapshot ⇒ section omitted (no spurious output).
- [ ] **CDRIFT-04**: Drift snapshots persist under `graphify-out/cache/snapshots/` with a count- or age-based retention policy decided at planning time.

### CQUERY — Parameterized Concept Queries
- [ ] **CQUERY-01**: MCP `concept_code_hops` accepts `min_confidence`, `relations`, and `confidence_band` parameters and applies them as filters on the BFS traversal.
- [ ] **CQUERY-02**: Backward compatibility — callers that omit the new parameters receive results identical to the v1.12 implementation.

### VOPT — Vault Option B Silent Reroute
- [ ] **VOPT-01**: When CWD is an Obsidian vault (`.obsidian/` present) but no `.graphify/profile.yaml` exists, output reroutes silently to a hidden `.graphify-out/` inside the vault.
- [ ] **VOPT-02**: An unconditional one-line `[graphify]` stderr breadcrumb explains the reroute on every run that uses Option B.
- [ ] **VOPT-03**: A new `--explain-paths` flag dumps the resolved output paths (and active vault profile, if any) without running the pipeline.

### AUDIT — v1.12 Audit Closure
- [ ] **AUDIT-01**: Nyquist VALIDATION.md gap-fill for v1.12 phases 59, 59.1, 60, 60.1, 61 — each retroactive entry cites the implementing SHA and the asserting test path; the closure script re-runs the cited tests to prove they still pass.
- [ ] **AUDIT-02**: Project-wide `[graphify]` stderr two-line format sweep migrates remaining one-line outliers (e.g. `__main__.py:~2745`) to the v1.12 `[graphify] error:` + `  hint:` convention. A stderr-format snapshot test is introduced **before** any reformatting to lock the contract for the 7 platform skill files that regex-parse stderr.
- [ ] **AUDIT-03**: Retroactive seed-SHA traceability — REQUIREMENTS.md and PROJECT.md are annotated with the milestone that consumed each seed (SEED-001 → v1.9, SEED-002 → v1.4, SEED-vault-root-aware-cli → v1.12 + v1.13 closes Option B, SEED-bidirectional-concept-code-links → v1.10 / v1.11 / v1.13 closes remainder).

---

## Future Requirements (deferred past v1.13)

- **D-3 Coverage lens query** — surface "concept coverage" (% of concepts with implements edges above confidence threshold). Depends on CQUERY shipping and being exercised in anger to learn the right shape.
- **D-5 Federated Obsidian frontmatter** — extend MOC↔CODE bidirectional links in the vault to reflect federated identity. Wait for CFED to prove its merge rules are trusted before extending into the vault surface.
- **Federation alias / override file** — manual override list for cases where exact-label + multi-signal heuristics produce false negatives. Only if real-world federation reveals this gap.

---

## Out of Scope (explicit exclusions)

- **Embedding-based similarity matching** for federation or concept identity — anti-feature; violates the deterministic + auditable + zero-new-deps stance. Adds ~800MB of torch weight and breaks the "no system deps" promise.
- **Auto-merge across repos without multi-signal evidence** — false-merges across repos are unrecoverable; deterministic guard rails (CFED-02) are non-negotiable.
- **Drift remediation / auto-fix** — v1.13 surfaces drift as a read-only signal in GRAPH_REPORT.md; auto-rewriting orphaned edges is out of scope and likely belongs to a vault-side workflow rather than graphify itself.
- **LLM-based federation arbitration** — federation decisions are deterministic by design; LLM-as-judge for merging concepts is non-reproducible and not auditable.
- **Cross-vault profile inheritance** — the vault profile system stays per-vault.
- **Real-time drift watcher / watch-mode integration** — drift is a batch-time signal in v1.13. A watch-mode integration is deferred until users hit a clear pain point.
- **Concept-edge schema breaking changes** — already shipped in v1.10/v1.11; CCONF-05 enforces backward-compat.
- **New language extractors** — orthogonal to v1.13's theme.

---

## Traceability

*Filled in by the roadmapper once phases are derived. Each REQ-ID below maps to the phase that delivers it.*

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| CCONF-01 | Phase 65 | |
| CCONF-02 | Phase 65 | |
| CCONF-03 | Phase 65 | |
| CCONF-04 | Phase 65 | |
| CCONF-05 | Phase 65 | |
| CFED-01 | Phase 66 | |
| CFED-02 | Phase 66 | |
| CFED-03 | Phase 66 | |
| CFED-04 | Phase 66 | |
| CFED-05 | Phase 66 | |
| CDRIFT-01 | Phase 67 | |
| CDRIFT-02 | Phase 67 | |
| CDRIFT-03 | Phase 67 | |
| CDRIFT-04 | Phase 67 | |
| CQUERY-01 | Phase 67 | |
| CQUERY-02 | Phase 67 | |
| VOPT-01 | Phase 63 | |
| VOPT-02 | Phase 63 | |
| VOPT-03 | Phase 63 | |
| AUDIT-01 | Phase 68 | |
| AUDIT-02 | Phase 64 | |
| AUDIT-03 | Phase 68 | |

---

*Created: 2026-05-05 — graphify v1.13 milestone init.*
