# graphify Roadmap

## Shipped Milestones

- **v1.13 — Concept Intelligence & Audit Closure** (2026-05-07): Per-edge LLM confidence, cross-repo federation, edge-level drift, parameterized concept queries, vault profile-driven writes, vault↔input reverse-sync, audit hygiene. 10 phases, 41 plans, 28/28 requirements. → [`.planning/milestones/v1.13-ROADMAP.md`](milestones/v1.13-ROADMAP.md)
- v1.12 — Vault Awareness, Pipeline Integration & Error Hygiene (2026-05-04). → [`.planning/milestones/v1.12-ROADMAP.md`](milestones/v1.12-ROADMAP.md)
- Earlier milestones: see `.planning/milestones/`.

## Active Milestone

**v2.0 — Graph Schema Deepening** (started 2026-05-07)

Major-version schema upgrade adding temporal edge validity and reasoning-relation edge types, with a measurement-gated dedup spike, a carried-over vault-cwd-gate argparse fix, and a coordinated 2.0.0 PyPI version bump. Backward-compatible read of legacy graph.json fixtures preserved throughout (CCONF schema_version precedent from v1.13 Phase 65).

**Hard non-goals:** No embeddings; no Postgres backend; no OB1 integration.

**Phase numbering:** Continues from v1.13 Phase 70.2. Phases 71–75.

---

## Phases

**Phase Numbering:**
- Integer phases (71–75): Planned milestone work
- Decimal phases: Urgent insertions only (via /gsd-insert-phase)

- [x] **Phase 71: TEMP** - Temporal edge validity columns: valid_from, valid_until, decay_weight, supersession stamping, and report/wiki temporal-health rendering (completed 2026-05-07)
- [x] **Phase 72: REAS** - Reasoning-relation edge types, classifier prompts, contradiction/supersession analysis, and full render pipeline (completed 2026-05-07)
- [x] **Phase 73: DEDUP** - Measurement-only dedup spike: near-duplicate concept-node rate survey and ship/defer recommendation (completed 2026-05-08)
- [x] **Phase 74: VBUG** - Vault-cwd-gate argparse-required fix and regression test coverage (completed 2026-05-08)
- [ ] **Phase 75: PKG** - Coordinated graphifyy 2.0.0 PyPI version bump, mcp/server.json sync, skill-stamp refresh, and full test sweep

---

## Phase Details

### Phase 71: TEMP
**Goal**: Edges carry complete temporal metadata — valid_from, valid_until, decay_weight — and the graph surface makes temporal health visible to users
**Depends on**: Nothing (first schema phase of v2.0)
**Requirements**: TEMP-01, TEMP-02, TEMP-03, TEMP-04
**Success Criteria** (what must be TRUE):
  1. A freshly-built graph.json contains valid_from on every edge and valid_until: null on all currently-valid edges; legacy graph.json files without these fields load without error (backward-compat, schema_version precedent from Phase 65)
  2. INFERRED edges have a decay_weight < 1.0 after the configured age threshold; EXTRACTED edges always show decay_weight 1.0; the per-relation decay config is readable and documented
  3. Re-running graphify against a corpus where a previously-INFERRED edge is no longer produced stamps that edge's valid_until rather than dropping it silently; the edge is excluded from god-node and surprising-connection scoring by default
  4. GRAPH_REPORT.md contains a "Temporal Health" sub-section showing counts of currently-valid vs superseded edges and the decay-weight distribution; wiki per-community articles mark edges with valid_until set as historical context rather than current relations
**Plans**: 5 plans
- [x] 71-01-PLAN.md — Temporal columns on edges (valid_from, valid_until) + read/write validator split
- [x] 71-02-PLAN.md — temporal_config.yaml + compute_decay_weight + per-relation override
- [x] 71-03-PLAN.md — stamp_supersessions (INFERRED-only, global tuple, history retained)
- [x] 71-04-PLAN.md — analyze.py 4-site valid_until filter (god_nodes, surprises, suggestions)
- [x] 71-05-PLAN.md — Temporal Health in GRAPH_REPORT.md + Historical relations in wiki

### Phase 72: REAS
**Goal**: Documents and concept nodes carry typed reasoning-relation edges extracted by classifier prompts, with full contradiction/supersession analysis and render pipeline
**Depends on**: Phase 71 (schema migration shape established)
**Requirements**: REAS-01, REAS-02, REAS-03, REAS-04
**Success Criteria** (what must be TRUE):
  1. validate.py accepts the five reasoning relations (supports, contradicts, supersedes, evolved_into, depends_on) on document/concept nodes and rejects them on code nodes; legacy graph.json files without reasoning relations load without error
  2. Running graphify on a corpus containing ADRs or markdown docs with explicit agreement/disagreement language produces reasoning-relation edges with confidence and confidence_score populated by the updated extraction prompts, including explicit examples for ADR supersession and contradiction detection
  3. GRAPH_REPORT.md contains a "Contradictions and Supersession Chains" section listing detected pairs and chains (longest first) with source citations and confidence scores; isolated reasoning-edge nodes do not appear in the knowledge gaps list
  4. Obsidian export preserves reasoning relations as typed wikilinks distinguishable from structural relations in note frontmatter; wiki articles render supersession chains (e.g. "ADR-0042 supersedes ADR-0028 (confidence 0.91)") as first-class inline relations
**Plans**: 4 plans
- [x] 72-01-PLAN.md — validate.py REASONING_RELATIONS frozenset + endpoint type rule + docs/RELATIONS.md taxonomy section
- [x] 72-02-PLAN.md — Skill prompt extension across all 10 skill*.md files + PROMPT_VERSION bump + drift gate
- [x] 72-03-PLAN.md — build.py two-pass reasoning-target resolver + supersedes outbound auto-stamp
- [x] 72-04-PLAN.md — analyze.py contradictions_and_chains + knowledge_gaps fix + report/wiki/Obsidian rendering

### Phase 73: DEDUP
**Goal**: A concrete, data-backed ship/defer recommendation on content-fingerprint dedup exits as the deliverable — no implementation ships unless the spike clears the threshold
**Depends on**: Nothing (independent measurement spike; can run in parallel with Phase 72)
**Requirements**: DEDUP-01
**Success Criteria** (what must be TRUE):
  1. A spike artifact reports the near-duplicate concept-node rate from running graphify against a representative multi-source corpus (at least one code repo + one doc-heavy directory + one PDF/paper set) using SHA-256 fingerprinting of normalized labels and descriptions
  2. The artifact contains a clear ship recommendation (if measured duplicate rate > 5% AND collisions are confirmed genuine) or a defer recommendation with the measured rate and rationale; DEDUP-02..N remain explicitly in the future backlog either way
**Plans**: TBD

### Phase 74: VBUG
**Goal**: Running any gated graphify command from a vault CWD without --vault succeeds — no argparse exit-2, auto-adopt notice prints correctly, and regression tests prevent recurrence
**Depends on**: Nothing (independent bug fix; can run in parallel with Phase 72 or 73)
**Requirements**: VBUG-01, VBUG-02
**Success Criteria** (what must be TRUE):
  1. `graphify update-vault` (and every other command sharing _check_vault_cwd_gate with required=True) completes without exit code 2 when invoked from a vault CWD with no --vault flag; the auto-adopt notice is printed to stderr
  2. `tests/test_vault_cwd_gate.py` exercises every gated subcommand from a fixture vault CWD without --vault and all assertions pass on both Python 3.10 and 3.12
  3. The debug session file `.planning/debug/vault-cwd-gate-argparse-required.md` status field reads resolved with the fix-phase reference recorded
**Plans**: 2 plans
Plans:
**Wave 1**
- [ ] 74-01-PLAN.md — Flip update-vault and vault-promote --vault to required=False with tightened post-parse guard (VBUG-01)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 74-02-PLAN.md — Create tests/test_vault_cwd_gate.py with 15-branch parametrized coverage and resolve debug session (VBUG-02)

### Phase 75: PKG
**Goal**: graphifyy 2.0.0 ships with a coherent version stamp across pyproject.toml, mcp/server.json, and all platform SKILL.md files, with the full test suite green on Python 3.10 and 3.12
**Depends on**: Phase 71, Phase 72, Phase 73, Phase 74 (all schema and fix work must land before the version bump)
**Requirements**: PKG-01, PKG-02
**Success Criteria** (what must be TRUE):
  1. `graphify --version` reports 2.0.0; `python scripts/bump_version.py 2.0.0` and `pip install -e ".[mcp,pdf,watch]"` both complete without error; pyproject.toml version field reads 2.0.0
  2. `python scripts/sync_mcp_server_json.py` produces an updated mcp/server.json with graphify_version = 2.0.0 in the manifest hash; `graphify install` writes a fresh .graphify_version stamp next to each platform SKILL.md
  3. Full pytest suite is green on Python 3.10 AND Python 3.12 after the version bump; no regressions introduced by the schema changes in Phases 71 or 72
**Plans**: TBD

---

## Progress

**Execution Order:**
Phases 73 and 74 are independent and can run in parallel with Phase 72. Phase 75 must be last.

Recommended sequence: 71 → 72 (depends on 71) with 73 and 74 running in parallel → 75

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 71. TEMP | 5/5 | Complete    | 2026-05-07 |
| 72. REAS | 4/4 | Complete    | 2026-05-08 |
| 73. DEDUP | 2/2 | Complete   | 2026-05-08 |
| 74. VBUG | 0/TBD | Not started | - |
| 75. PKG | 0/TBD | Not started | - |
