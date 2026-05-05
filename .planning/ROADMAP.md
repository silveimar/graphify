# graphify v1.13 — Concept Intelligence & Audit Closure: Roadmap

**Milestone:** v1.13
**Goal:** Promote concept↔code edges from a structural feature to a knowledge-reasoning tool (per-edge confidence, deterministic cross-repo federation, edge-level drift, parameterized vault queries), close the Option B vault-CWD seed, and resolve all v1.12 audit-deferred items.
**Granularity:** standard
**Total phases:** 6 (Phase 63 → Phase 68)
**Phase numbering:** continues from v1.12 (last phase 62.1).

## Phases

- [ ] **Phase 63: VOPT — Vault Option B Silent Reroute & `--explain-paths`** — Vault-CWD reroute to `.graphify-out/` with stderr breadcrumb and a path-resolver flag.
- [ ] **Phase 64: AUDIT-A — stderr Format Snapshot Lock & Sweep** — Freeze the `[graphify]` two-line stderr contract via snapshot test, then migrate one-line outliers.
- [ ] **Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version** — Load-bearing: per-edge LLM `confidence_score` + `evidence`, second cache namespace, schema-compat with legacy fixture, calibration self-check.
- [ ] **Phase 66: CFED — Cross-Repo Concept Federation (`federate.py`)** — Opt-in deterministic id-namespacing + multi-signal merge + provenance manifest + report section.
- [ ] **Phase 67: CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries** — Membership-Jaccard drift classification with snapshot retention, plus `concept_code_hops` parameter filters.
- [ ] **Phase 68: AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability** — Retroactive VALIDATION.md entries with re-run proofs, seed→milestone annotations across REQUIREMENTS.md and PROJECT.md.

## Phase Details

### Phase 63: VOPT — Vault Option B Silent Reroute & `--explain-paths`
**Goal**: Users running graphify from inside an Obsidian vault without a `.graphify/profile.yaml` get sane, vault-local output with an audible breadcrumb, and can introspect resolved paths without running the pipeline.
**Depends on**: Nothing (independent of CCONF/CFED/CDRIFT track)
**Requirements**: VOPT-01, VOPT-02, VOPT-03
**Success Criteria** (what must be TRUE):
  1. Running graphify from a vault CWD with `.obsidian/` and no `.graphify/profile.yaml` writes outputs under `.graphify-out/` inside the vault (not the legacy `graphify-out/`).
  2. Every Option B run emits exactly one `[graphify]` stderr breadcrumb explaining the reroute.
  3. `graphify --explain-paths` prints resolved output paths and active vault profile (if any) and exits without running the pipeline.
  4. Non-vault CWDs continue to use `default_graphify_artifacts_dir()` unchanged (no regressions on existing routing-audit tests).
**Plans**: TBD

### Phase 64: AUDIT-A — stderr Format Snapshot Lock & Sweep
**Goal**: The `[graphify] error:` + `  hint:` two-line stderr contract is locked by an automated snapshot test BEFORE any reformatting touches the codebase, so the 7 platform skills' regex parsers cannot silently break.
**Depends on**: Phase 63 (VOPT-02 emits a stderr line that must conform; lock contract first, then sweep)
**Requirements**: AUDIT-02
**Success Criteria** (what must be TRUE):
  1. A stderr-format snapshot test exists and passes against the current main, capturing the v1.12 two-line convention as the contract for the 7 platform skill files.
  2. After the snapshot lands, the remaining one-line stderr outliers (e.g., `__main__.py:~2745`) are migrated to the two-line convention with the snapshot still passing.
  3. Running `pytest tests/ -q` produces zero unexpected stderr-format diffs across the full suite.
  4. The 7 platform skill files' regex parsers are enumerated in a test fixture so future format changes have a documented contract surface.
**Plans**: TBD

### Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version
**Goal**: Every concept↔code INFERRED edge carries a per-edge LLM-derived `confidence_score` and `evidence`, persisted via a separate cache namespace that prompt-version bumps invalidate cleanly, with backward-compat reads of pre-v1.13 graphs.
**Depends on**: Phase 64 (stderr contract locked before extractor refactor that may emit new warning lines)
**Requirements**: CCONF-01, CCONF-02, CCONF-03, CCONF-04, CCONF-05
**Success Criteria** (what must be TRUE):
  1. Every concept↔code INFERRED edge produced by `extract.py` carries `confidence_score ∈ [0.0, 1.0]` and an `evidence` field; uniform `1.0` baseline is gone.
  2. Bumping `prompt_version` invalidates only confidence-cache entries; the existing `extract.py` file-hash cache is untouched and unchanged files still skip extraction.
  3. A frozen v1.10–v1.12 legacy graph fixture passes `validate.py` read validation; new writes require `schema_version`.
  4. `GRAPH_REPORT.md` contains a calibration self-check section that flags suspicious score distributions (e.g., >70% clustered in 0.85±0.05) on a synthetic skewed test corpus.
**Plans**: TBD

### Phase 66: CFED — Cross-Repo Concept Federation (`federate.py`)
**Goal**: A user can opt into deterministic cross-repo federation that merges concepts only on multi-signal evidence, namespaces all node IDs by repo, records per-merge provenance, and reports merges in `GRAPH_REPORT.md`.
**Depends on**: Phase 65 (federation tiebreakers consume per-edge `confidence_score`)
**Requirements**: CFED-01, CFED-02, CFED-03, CFED-04, CFED-05
**Success Criteria** (what must be TRUE):
  1. Federation runs only when an explicit CLI flag is passed; default behavior across all existing test runs is unchanged.
  2. A two-repo federation test where labels match but neighborhoods differ produces ZERO merges; only multi-signal agreement (label + shared neighborhood + source-path overlap) yields a merge.
  3. Merged concepts appear in a federation manifest under `graphify-out/` with per-repo provenance entries and the matching signals named.
  4. `federate.py` runs after `_normalize_concept_code_edges` in `build.py` and before `cluster.py`; no embeddings or LLM calls are introduced.
  5. `GRAPH_REPORT.md` gains a Federation section listing each merged concept and its provenance.
**Plans**: TBD

### Phase 67: CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries
**Goal**: Users can detect concept-edge drift between snapshots via stable community-membership Jaccard (never community names/IDs), and the MCP `concept_code_hops` query accepts parameter filters that operate over real per-edge confidence values.
**Depends on**: Phase 65 (per-edge confidence) + Phase 66 (federated cross-repo baseline as candidate snapshot)
**Requirements**: CDRIFT-01, CDRIFT-02, CDRIFT-03, CDRIFT-04, CQUERY-01, CQUERY-02
**Success Criteria** (what must be TRUE):
  1. With a prior snapshot present, `GRAPH_REPORT.md` contains a Drift section classifying each `implements`/`documents`/`tests` edge as `stable`, `community-renamed`, `community-resharded`, or `orphaned`; absent snapshot ⇒ section omitted entirely.
  2. Renaming a community deterministically (membership unchanged) yields drift status `community-renamed` for affected edges, NOT `orphaned` — proving the comparator anchors on membership Jaccard.
  3. Drift snapshots persist under `graphify-out/cache/snapshots/` and respect the count- or age-based retention policy chosen at planning time.
  4. `concept_code_hops(min_confidence=…, relations=[…], confidence_band=…)` filters BFS results accordingly, and callers omitting the new parameters receive results byte-identical to v1.12 behavior on a frozen fixture.
**Plans**: TBD

### Phase 68: AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability
**Goal**: Every v1.12 phase deferred from Nyquist sampling has a retroactive VALIDATION.md entry that re-runs and passes, and every shipped seed is annotated with the milestone(s) that consumed it.
**Depends on**: Phases 63–67 (audit sweep operates over the full v1.13 surface)
**Requirements**: AUDIT-01, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. v1.12 phases 59, 59.1, 60, 60.1, and 61 each have a retroactive VALIDATION.md entry citing the implementing SHA and the asserting test path.
  2. A closure script re-executes every cited test and reports green; the script is checked in and runnable from a clean checkout.
  3. REQUIREMENTS.md and PROJECT.md annotate each seed with its consuming milestone (SEED-001 → v1.9, SEED-002 → v1.4, SEED-vault-root-aware-cli → v1.12 + v1.13 closes Option B, SEED-bidirectional-concept-code-links → v1.10 / v1.11 / v1.13 closes remainder).
  4. The audit closure leaves no v1.12-deferred audit item open in MILESTONES.md.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 63. VOPT | 0/0 | Not started | - |
| 64. AUDIT-A | 0/0 | Not started | - |
| 65. CCONF | 0/0 | Not started | - |
| 66. CFED | 0/0 | Not started | - |
| 67. CDRIFT + CQUERY | 0/0 | Not started | - |
| 68. AUDIT-B | 0/0 | Not started | - |

## Coverage

All 22 v1.13 requirements mapped to exactly one phase:

| REQ-ID | Phase |
|--------|-------|
| CCONF-01..05 | 65 |
| CFED-01..05 | 66 |
| CDRIFT-01..04 | 67 |
| CQUERY-01..02 | 67 |
| VOPT-01..03 | 63 |
| AUDIT-01 | 68 |
| AUDIT-02 | 64 |
| AUDIT-03 | 68 |

Total: 22/22 — no orphans, no duplicates.

---
*Created: 2026-05-05 — graphify v1.13 roadmap.*
