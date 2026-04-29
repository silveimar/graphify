# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- ✅ **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9, 9.1 (+ 9.1.1 gap closure) (shipped 2026-04-15)
- ✅ **v1.3 Intelligent Analysis Continuation** — Phases 9.2, 10, 11 (shipped 2026-04-17)
- ✅ **v1.4 Agent Discoverability & Obsidian Workflows** — Phases 12–18.2 (shipped 2026-04-22)
- ✅ **v1.5 Diagram Intelligence & Excalidraw Bridge** — Phases 19–22 (shipped 2026-04-27)
- ✅ **v1.6 Hardening & Onboarding** — Phases 23–26 (shipped 2026-04-27)
- ✅ **v1.7 Vault Adapter UX & Template Polish** — Phases 27–31 (shipped 2026-04-28)
- 🚧 **v1.8 Output Taxonomy & Cluster Quality** — Phases 32–36 (planned)

## Phases

<details>
<summary>✅ v1.0 Ideaverse Integration — Configurable Vault Adapter (Phases 1–5) — SHIPPED 2026-04-11</summary>

Configurable output adapter replacing the monolithic `to_obsidian()` with a four-component vault-driven pipeline: profile loading → template rendering → mapping classification → safe merge → CLI wiring. Reads a `.graphify/profile.yaml` from the target vault, falls back to a built-in Ideaverse ACE default when absent, and supports `graphify --obsidian [--dry-run]` plus `graphify --validate-profile` as direct CLI entry points.

**Phases:**

- [x] Phase 1: Foundation — Profile loader, filename safety utilities, and security primitives; FIX-01..05 bug fixes (2/2 plans, completed 2026-04-11)
- [x] Phase 2: Template Engine — Note rendering via `string.Template` with 6 built-in templates (MOC, Thing, Statement, Person, Source, Community Overview) (4/4 plans, completed 2026-04-11)
- [x] Phase 3: Mapping Engine — Topology + attribute classification of nodes into note types and folder placements (4/4 plans, completed 2026-04-11)
- [x] Phase 4: Merge Engine — Safe frontmatter round-trip with `preserve_fields`, field-order preservation, and configurable merge strategies (6/6 plans, completed 2026-04-11)
- [x] Phase 5: Integration & CLI — Wire all four modules into refactored `to_obsidian()`; add `--dry-run` and `--validate-profile` CLI flags (6/6 plans including 05-06 gap-closure, completed 2026-04-11)

**Totals:** 5 phases, 22 plans, 31/31 in-scope requirements satisfied, 2 requirements de-scoped via D-74 (OBS-01/OBS-02).

**Archives:**
- Full phase detail: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v1.1 Context Persistence & Agent Memory (Phases 6–8.2) — SHIPPED 2026-04-13</summary>

Persistent, evolving context layer — graphify is no longer a one-shot graph builder. Agents can read AND write to the knowledge graph across sessions, users see how their corpus changes over time, and Obsidian vault notes survive round-trip re-runs with user content preservation. 25/25 requirements satisfied.

**Phases:**

- [x] Phase 6: Graph Delta Analysis & Staleness (3/3 plans, completed 2026-04-12)
- [x] Phase 7: MCP Write-Back with Peer Modeling (3/3 plans, completed 2026-04-13)
- [x] Phase 8: Obsidian Round-Trip Awareness (3/3 plans, completed 2026-04-13)
- [x] Phase 8.1: Approve & Pipeline Wiring (2/2 plans, completed 2026-04-13)
- [x] Phase 8.2: MCP Query Enhancements (1/1 plan, completed 2026-04-13)

**Totals:** 5 phases, 12 plans, 25/25 requirements satisfied, ~117 commits over 2 days.

**Archives:**
- Full phase detail: `.planning/milestones/v1.1-ROADMAP.md`
- Requirements: `.planning/milestones/v1.1-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.1-MILESTONE-AUDIT.md`

</details>

**Carried forward from v1.0/v1.1 scope** (deferred to v1.2+):

- Conditional template sections (`{{#if_god_node}}...{{/if}}` guards) — TMPL-01
- Loop blocks for template connections (`{{#connections}}...{{/connections}}`) — TMPL-02
- Custom Dataview query templates per note type in profile — TMPL-03
- Profile includes/extends mechanism (compose profiles from fragments) — CFG-02
- Per-community template overrides — CFG-03

---

<details>
<summary>✅ v1.2 Intelligent Analysis & Cross-File Extraction (Phases 9, 9.1, 9.1.1) — SHIPPED 2026-04-15</summary>

LLM-assisted multi-perspective graph analysis via autoreason tournament (4 lenses × 4 rounds), query telemetry with usage-weighted edges and 2-hop derived edges, and lifecycle cleanup ensuring retroactive audit compliance.

**Phases:**

- [x] Phase 9: Multi-Perspective Graph Analysis (Autoreason Tournament) — 4 lenses (security, architecture, complexity, onboarding) × 4 tournament rounds (A/B/AB/blind-Borda) with "no finding" as first-class option (3/3 plans, completed 2026-04-14)
- [x] Phase 9.1: Query Telemetry & Usage-Weighted Edges — Per-edge MCP traversal counters, hot-path strengthening, decay of unused edges, 2-hop derived edges with INFERRED confidence, hot/cold paths surfaced in GRAPH_REPORT.md (3/3 plans, completed 2026-04-15)
- [x] Phase 9.1.1: Milestone v1.2 Lifecycle Cleanup — Retroactive 09.1-VERIFICATION.md, project-level REQUIREMENTS.md with traceability, narrow-scope reconciliation across ROADMAP/STATE/PROJECT. Planning-only gap closure (3/3 plans, completed 2026-04-15)

**Totals:** 3 phases, 9 plans, 10/10 requirements satisfied, milestone audit: passed.

**Archives:**
- Full phase detail: `.planning/milestones/v1.2-ROADMAP.md`
- Requirements: `.planning/milestones/v1.2-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.2-MILESTONE-AUDIT.md`

</details>

---

<details>
<summary>✅ v1.3 Intelligent Analysis Continuation (Phases 9.2, 10, 11) — SHIPPED 2026-04-17</summary>

Cross-file semantic extraction with entity dedup, progressive graph retrieval, and narrative-mode slash commands.

</details>

---

<details>
<summary>✅ v1.4 Agent Discoverability & Obsidian Workflows (Phases 12–18.2) — SHIPPED 2026-04-22</summary>

Heterogeneous routing, agent capability manifest, Obsidian thinking commands, async enrichment, argumentation, chat, focus, and gap-closure phases.

</details>

---

<details>
<summary>✅ v1.5 Diagram Intelligence & Excalidraw Bridge (Phases 19–22) — SHIPPED 2026-04-27</summary>

Turn graphify's knowledge graph into a diagram generation pipeline. Vault-promotion script writing 7-folder Ideaverse Pro 2.5 notes, diagram seed engine with auto-tagging + MCP `list_diagram_seeds`/`get_diagram_seed` pair, profile `diagram_types:` schema with 6 built-in defaults + `--init-diagram-templates` Excalidraw stubs (compress=false one-way door), and a deployable `excalidraw-diagram` skill with pure-Python fallback.

**Phases:**

- [x] Phase 19: Vault Promotion Script (Layer B) — `graphify vault-promote` CLI; 7-folder classifier; SHA-256 manifest; D-13 overwrite-self-skip-foreign; profile write-back; 3-layer taxonomy merge (4/4 plans, completed 2026-04-23)
- [x] Phase 20: Diagram Seed Engine — `analyze.py` auto-tagging; `seed.py` orchestrator with D-05 layout heuristic + Jaccard dedup + max-20 cap; `--diagram-seeds` CLI; MANIFEST-05 atomic MCP pair (3/3 plans, completed 2026-04-23)
- [x] Phase 21: Profile Extension & Template Bootstrap — `diagram_types:` schema + 6 built-in defaults; `--init-diagram-templates` writing `compress: false` Excalidraw stubs; lzstring-import denylist (2/2 plans, completed 2026-04-23)
- [x] Phase 22: Excalidraw Skill & Vault Bridge — `excalidraw-diagram` skill with 7-step pipeline; `graphify install excalidraw`; pure-Python `.excalidraw.md` fallback (2/2 plans, completed 2026-04-27)

**Totals:** 4 phases, 11 plans, 34/34 requirements (VAULT-01..07, SEED-01..11, PROF-01..04, TMPL-01..06, SKILL-01..06). All 4 phases Nyquist-compliant. End-to-end flow verified across 7 cross-phase wires.

**Archives:**
- Full phase detail: `.planning/milestones/v1.5-ROADMAP.md`
- Requirements: `.planning/milestones/v1.5-REQUIREMENTS.md`
- Audit: `.planning/milestones/v1.5-MILESTONE-AUDIT.md`

</details>


---

<details>
<summary>✅ v1.6 Hardening & Onboarding (Phases 23–26) — SHIPPED 2026-04-27</summary>

**Theme:** Close known stability gaps from v1.5 (dedup crash on `list[str]` source_file, manifest writers that overwrite siblings on subpath runs, persistence-block drift across platform skill variants) and produce the first end-to-end onboarding doc that lets a new user run the v1.5 diagram-intelligence pipeline from documentation alone — no source reading required.

- [x] Phase 23: Dedup `source_file` List-Handling Fix (1/1 plan) — completed 2026-04-27
- [x] Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening (2/2 plans) — completed 2026-04-27
- [x] Phase 25: Mandatory Dual-Artifact Persistence in Skill Files (1/1 plan) — completed 2026-04-27
- [x] Phase 26: v1.5 Configuration Guide & Walkthrough Docs (1/1 plan) — completed 2026-04-27

Full details: [.planning/milestones/v1.6-ROADMAP.md](milestones/v1.6-ROADMAP.md)

</details>

---

<details>
<summary>✅ v1.7 Vault Adapter UX & Template Polish (Phases 27–31) — SHIPPED 2026-04-28</summary>

**Theme:** Make graphify safe and ergonomic to run from inside an Obsidian vault. Profile-driven output placement, vault-CWD detection with auto-adopt (SEED-vault-root-aware-cli Option C), hardened self-ingestion defenses, onboarding diagnostics — and close out the long-deferred template/profile composition backlog from v1.0.

**Phases:**

- [x] Phase 27: Vault Detection & Profile-Driven Output Routing (3/3 plans, completed 2026-04-28)
- [x] Phase 28: Self-Ingestion Hardening (3/3 plans, completed 2026-04-28)
- [x] Phase 29: Doctor Diagnostics & Dry-Run Preview (3/3 plans, completed 2026-04-28)
- [x] Phase 30: Profile Composition (3/3 plans, completed 2026-04-28)
- [x] Phase 31: Template Engine Extensions (2/2 plans, completed 2026-04-28)

**Totals:** 5 phases, 14 plans, 13/13 requirements satisfied (VAULT-08..15, TMPL-01..03, CFG-02..03), 5/5 Nyquist ratified.

**Archives:**
- Full phase detail: `.planning/milestones/v1.7-ROADMAP.md`
- Requirements: `.planning/milestones/v1.7-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.7-MILESTONE-AUDIT.md`

## Phase Details (archived — see milestones/v1.7-ROADMAP.md for full text)

### Phase 27: Vault Detection & Profile-Driven Output Routing
**Goal:** When graphify runs from inside an Obsidian vault, it recognizes the vault and routes output to a profile-declared destination instead of dumping `graphify-out/` into the vault root.
**Depends on:** Nothing (foundation for v1.7)
**Requirements:** VAULT-08, VAULT-09, VAULT-10
**Success Criteria** (what must be TRUE):
  1. Running `graphify` from a directory containing `.obsidian/` is detected as a vault and reported in CLI output
  2. When the vault has `.graphify/profile.yaml`, graphify auto-adopts profile-driven placement (Option C) — CWD is treated as both input corpus and output target without an explicit flag
  3. The profile's output destination field (vault-relative path, absolute path, or sibling-of-vault) determines where notes are written
  4. The CLI `--output` flag overrides the profile's declared destination and the precedence is shown in stderr when both are present
**Plans:** 3 plans
Plans:
- [ ] 27-01-PLAN.md — Profile schema extension: output: block + validate_sibling_path() (VAULT-10 schema half)
- [ ] 27-02-PLAN.md — graphify/output.py: ResolvedOutput, is_obsidian_vault, resolve_output (VAULT-08, VAULT-09)
- [ ] 27-03-PLAN.md — CLI wiring: --output flag in run + --obsidian, run_corpus out_dir kwarg, integration tests (VAULT-08, VAULT-09, VAULT-10)

### Phase 28: Self-Ingestion Hardening
**Goal:** Re-running graphify inside a vault never re-ingests its own previous output, even across profile changes or unconventional output paths.
**Depends on:** Phase 27 (requires resolved profile output destination)
**Requirements:** VAULT-11, VAULT-12, VAULT-13
**Success Criteria** (what must be TRUE):
  1. `detect.py` prunes the profile's resolved output destination plus any declared exclusion globs from the input scan
  2. Paths matching `**/graphify-out/**` at any nesting depth are refused as ingestion candidates and prior nesting is reported as a warning to the user
  3. The current run's manifest records every output path it wrote, and a subsequent run reads that manifest and skips those paths even when the profile output destination has changed since
  4. A user who renames their output directory in `profile.yaml` between two runs does not see the previous run's notes re-ingested as "documents"
**Plans:** 3/3 plans complete
Plans:
- [x] 28-01-PLAN.md — Profile schema + ResolvedOutput.exclude_globs (VAULT-11 schema)
- [x] 28-02-PLAN.md — detect.py nesting guard + exclude_globs application + pipeline threading (VAULT-11 detect-side, VAULT-12)
- [x] 28-03-PLAN.md — output-manifest.json read/write + cross-run renamed-output recovery (VAULT-13)

### Phase 29: Doctor Diagnostics & Dry-Run Preview
**Goal:** A new user can diagnose vault adapter misconfiguration and preview vault-aware behavior before any files are written.
**Depends on:** Phase 27, Phase 28 (consumes resolved detection state, output destination, and ignore-list)
**Requirements:** VAULT-14, VAULT-15
**Success Criteria** (what must be TRUE):
  1. `graphify doctor` prints vault detection status, profile validation result, resolved output destination, and the active ignore-list in a single human-readable report
  2. `graphify doctor` exits non-zero when the profile is invalid, the output destination is unresolvable, or the configuration would cause self-ingestion
  3. `graphify --dry-run` (and/or `graphify doctor --dry-run`) shows which input files would be ingested, which would be skipped, and which output files would be written — all without touching disk
  4. The doctor report ends with concrete, actionable "recommended fixes" lines for each detected misconfiguration
**Plans:** 3 plans
Plans:
- [ ] 29-01-PLAN.md — graphify/doctor.py module: DoctorReport, run_doctor (non-dry-run), format_report, _FIX_HINTS + 12 unit tests (VAULT-14)
- [ ] 29-02-PLAN.md — graphify/detect.py additive skipped[reason] return key + 2 backcompat tests (VAULT-15)
- [ ] 29-03-PLAN.md — doctor.py dry-run preview branch + __main__.py doctor subcommand wiring + 7 tests (VAULT-14, VAULT-15)

### Phase 30: Profile Composition
**Goal:** Users can compose profiles from fragments and override templates per community without duplicating profile content, with deterministic merge order and cycle detection.
**Depends on:** Nothing (independent surface from VAULT-* phases)
**Requirements:** CFG-02, CFG-03
**Success Criteria** (what must be TRUE):
  1. A profile with `extends:` or `includes:` resolves into a single composed profile via deterministic merge order, and cycles are detected and reported as a clear error rather than infinite-looping
  2. A profile field maps community ID/label patterns to custom templates, and the first matching pattern wins (consistent with the v1.0 mapping engine precedence)
  3. Running `graphify --validate-profile` against a composed profile reports the merge chain and the resolved per-community template assignments
  4. Removing an `extends:` reference and re-validating shows exactly which fields were lost — no silent drops
**Plans:** 3/3 plans complete
Plans:
- [x] 30-01-PLAN.md — [wave 1] Resolver + schema (extends/includes, cycle detection, depth cap, path confinement, _deep_merge_with_provenance, refactor load_profile, extend validate_profile + PreflightResult)
- [x] 30-02-PLAN.md — [wave 2, depends on 01] community_templates runtime dispatch in _render_moc_like (fnmatchcase, first-match-wins, MOC-only scope, fallback on failure)
- [x] 30-03-PLAN.md — [wave 3, depends on 01+02] Extend --validate-profile output: Merge chain + Field provenance + Resolved community templates sections (uses Plan 02 fixture; serial appends to test_profile_composition.py)

### Phase 31: Template Engine Extensions
**Goal:** Markdown templates can express conditional sections, iterate over connections, and inject per-note-type Dataview queries — without leaving the `string.Template` block-parser surface or adding new required dependencies.
**Depends on:** Phase 30 (per-community templates from CFG-03 are the natural delivery vehicle for TMPL-03's per-note-type Dataview queries)
**Requirements:** TMPL-01, TMPL-02, TMPL-03
**Success Criteria** (what must be TRUE):
  1. A template containing `{{#if_god_node}}...{{/if}}` renders the guarded section only when the node attribute predicate is true and omits it cleanly otherwise
  2. A template containing `{{#connections}}...{{/connections}}` iterates over each connection with per-iteration variable scope; nested loops are either supported or rejected with a clear error
  3. A profile field declaring per-note-type Dataview query strings produces notes whose Dataview block content matches the profile-declared query at render time
  4. All three template features are sanitized — node labels containing template syntax (`{{`, `}}`, `#`) cannot inject conditional logic or break out of loops
**Plans:** 2 plans
Plans:
- [ ] 31-01-PLAN.md — [wave 1] Block engine: `{{#if_X}}` conditionals (TMPL-01) + `{{#connections}}` loops (TMPL-02) + sanitization hardening (T-31-01); _BlockTemplate subclass + _PREDICATE_CATALOG (4 entries) + _expand_blocks pre-processor + extended validate_template
- [ ] 31-02-PLAN.md — [wave 1] Per-note-type Dataview queries (TMPL-03): new top-level `dataview_queries` profile key whitelisted against _KNOWN_NOTE_TYPES (6 entries); _build_dataview_block per-note-type lookup with legacy moc_query fallback; --validate-profile provenance per D-14

</details>

---

### 🚧 v1.8 Output Taxonomy & Cluster Quality (Planned)

**Milestone Goal:** Make graphify's vault output legible at a glance and give the real `work-vault` → `ls-vault` workflow a safe, step-by-step migration path.

- [x] **Phase 32: Profile Contract & Defaults** - Lock the v1.8 default taxonomy, profile keys, validation, and compatibility behavior. (completed 2026-04-29)
- [x] **Phase 33: Naming & Repo Identity Helpers** - Resolve stable concept names and repo identities before rendering or manifest writes depend on them. (completed 2026-04-29)
- [x] **Phase 34: Mapping, Cluster Quality & Note Classes** - Apply MOC-only community semantics, the cluster-quality floor, and CODE-vs-concept note classes. (completed 2026-04-29)
- [ ] **Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility** - Render the new taxonomy, expose repo identity in outputs, and make migration effects previewable.
- [ ] **Phase 36: Migration Guide, Skill Alignment & Regression Sweep** - Document the real vault migration path and verify CLI, skill, security, and tests stay aligned.

## Phase Details

### Phase 32: Profile Contract & Defaults
**Goal:** Users get a stable v1.8 default vault taxonomy and actionable profile validation before downstream export behavior changes.
**Depends on:** Phase 31 (v1.7 template/profile foundation)
**Requirements:** TAX-01, TAX-02, TAX-03, TAX-04, COMM-03, CLUST-01, CLUST-04
**Success Criteria** (what must be TRUE):
  1. User can run graphify with no vault profile and see generated notes routed into a Graphify-owned default subtree, including concept MOCs under `Atlas/Sources/Graphify/MOCs/`
  2. Valid v1.8 user-authored vault profiles override folder placement through `taxonomy:`, while invalid or missing v1.8 keys fail validation
  3. User can validate a v1.8 profile and receive actionable errors or warnings for unsupported taxonomy keys, invalid folder mappings, or hard-deprecated community overview output
  4. User can set `mapping.min_community_size` to control standalone MOC generation, and `mapping.moc_threshold` is invalid immediately
**Plans:** 4/4 plans complete
Plans:
- [x] 32-01-PLAN.md — Reconcile v1.8 planning contract
- [x] 32-02-PLAN.md — Add profile taxonomy defaults and validation
- [x] 32-03-PLAN.md — Consume taxonomy in mapping/export paths
- [x] 32-04-PLAN.md — Share preflight findings with doctor

### Phase 33: Naming & Repo Identity Helpers
**Goal:** Users get stable human-readable concept names and deterministic repo identity resolution that downstream note paths can trust.
**Depends on:** Phase 32
**Requirements:** NAME-01, NAME-02, NAME-03, NAME-04, NAME-05, REPO-01, REPO-02, REPO-03
**Success Criteria** (what must be TRUE):
  1. User can provide repo identity through a CLI flag, through `profile.yaml`, or by deterministic fallback, and graphify reports which source won
  2. User receives cached LLM concept MOC titles when concept naming is enabled, with deterministic fallback names when LLM naming is unavailable, disabled by budget, or rejected
  3. User can rerun graphify on an unchanged community and keep the same concept MOC filename across runs
  4. User can inspect concept naming provenance, and unsafe generated labels are sanitized for filenames, tags, wikilinks, Dataview, and frontmatter
**Plans:** 4/4 plans complete
Plans:
**Wave 1**
- [x] 33-01-PLAN.md — Wave 0 validation scaffold for repo identity, concept naming, provenance, and sink safety
- [x] 33-02-PLAN.md — Repo identity resolver plus profile schema/default controls

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 33-03-PLAN.md — Stable concept naming helper with cache, fallback, provenance, and unsafe-title rejection

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 33-04-PLAN.md — CLI and Obsidian export wiring for repo identity and concept MOC names

### Phase 34: Mapping, Cluster Quality & Note Classes
**Goal:** Users see clean MOC-only community output, low-quality clusters handled predictably, and code-derived hubs separated from concept MOCs.
**Depends on:** Phase 33
**Requirements:** COMM-01, CLUST-02, CLUST-03, GOD-01, GOD-02, GOD-03, GOD-04
**Success Criteria** (what must be TRUE):
  1. User receives MOC-only community output by default with no generated `_COMMUNITY_*` overview notes
  2. User sees isolate communities omitted from standalone MOC generation while their nodes remain available in graph data and non-community exports
  3. User sees tiny connected communities below the configured floor routed deterministically into an `_Unclassified` MOC
  4. User sees code-derived god nodes exported as collision-safe `CODE_<repo>_<node>` notes with bidirectional navigation to their related concept MOCs
**Plans:** 4/4 plans complete
Plans:
- [x] 34-01-PLAN.md — Establish profile/template note-class contract and default cluster floor
- [x] 34-02-PLAN.md — Emit mapping routing metadata, CODE eligibility, and CODE member context
- [x] 34-03-PLAN.md — Add deterministic CODE filename identity and MOC-only export dispatch
- [x] 34-04-PLAN.md — Wire CODE/concept bidirectional rendering and phase verification

### Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility
**Goal:** Users can preview and run the new export/migration path without silent overwrites, hidden legacy artifacts, or repo identity drift.
**Depends on:** Phase 34
**Requirements:** COMM-02, REPO-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-06
**Success Criteria** (what must be TRUE):
  1. User sees the resolved repo identity recorded consistently in CODE note filenames, frontmatter, tags, and output manifests
  2. User can run an automated migration command for the real `work-vault` to `ls-vault` update path and preview its effects in dry-run mode before vault writes
  3. User sees old managed paths mapped to new Graphify-owned paths when note identity can be matched, with legacy `_COMMUNITY_*` files surfaced as migration candidates or orphans
  4. User can review CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, and ORPHAN outcomes before committing, and migration never automatically deletes legacy vault notes
**Plans:** TBD

### Phase 36: Migration Guide, Skill Alignment & Regression Sweep
**Goal:** Users and maintainers can trust the v1.8 behavior because docs, skill files, tests, and security checks all describe and verify the same export contract.
**Depends on:** Phase 35
**Requirements:** MIG-05, VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. User receives a Markdown migration guide covering backup, validation, dry-run, migration command, review, cleanup, rollback, and rerun steps for the `work-vault` → `ls-vault` workflow
  2. Maintainer can confirm skill files and CLI docs use the same v1.8 Obsidian export behavior
  3. Maintainer can verify v1.8 behavior with pure unit tests that use `tmp_path` and perform no network calls
  4. Maintainer can confirm all new path, template, profile, LLM-label, and repo-identity inputs pass through existing security and sanitization helpers
**Plans:** TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-04-11 |
| 2. Template Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 3. Mapping Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 4. Merge Engine | v1.0 | 6/6 | Complete | 2026-04-11 |
| 5. Integration & CLI | v1.0 | 6/6 | Complete | 2026-04-11 |
| 6. Graph Delta Analysis & Staleness | v1.1 | 3/3 | Complete | 2026-04-12 |
| 7. MCP Write-Back with Peer Modeling | v1.1 | 3/3 | Complete | 2026-04-13 |
| 8. Obsidian Round-Trip Awareness | v1.1 | 3/3 | Complete | 2026-04-13 |
| 8.1 Approve & Pipeline Wiring | v1.1 | 2/2 | Complete | 2026-04-13 |
| 8.2 MCP Query Enhancements | v1.1 | 1/1 | Complete | 2026-04-13 |
| 9. Multi-Perspective Analysis (Autoreason Tournament) | v1.2 | 3/3 | Complete   | 2026-04-14 |
| 9.1 Query Telemetry & Usage-Weighted Edges | v1.2 | 3/3 | Complete | 2026-04-15 |
| 9.1.1 Milestone v1.2 Lifecycle Cleanup | v1.2 | 3/3 | Complete | 2026-04-15 |
| 9.2 Progressive Graph Retrieval | v1.3 | 3/3 | Complete | 2026-04-17 |
| 10. Cross-File Semantic Extraction with Entity Deduplication | v1.3 | 9/9 | Complete   | 2026-04-17 |
| 11. Narrative Mode as Interactive Slash Commands | v1.3 | 7/7 | Complete   | 2026-04-17 |
| 12. Heterogeneous Extraction Routing | v1.4 | 6/6 | Complete | 2026-04-17 |
| 13. Agent Capability Manifest (+ SEED-002 Harness Export) | v1.4 | 4/4 | Complete | 2026-04-17 |
| 14. Obsidian Thinking Commands | v1.4 | 6/6 | Complete   | 2026-04-23 |
| 15. Async Background Enrichment | v1.4 | 6/6 | Complete    | 2026-04-22 |
| 16. Graph Argumentation Mode | v1.4 | 3/3 | Complete   | 2026-04-23 |
| 17. Conversational Graph Chat | v1.4 | 3/3 | Complete   | 2026-04-22 |
| 18. Focus-Aware Graph Context | v1.4 | 4/4 | Complete | 2026-04-20 |
| 18.1 v1.4 Gap Closure — Phase 13 Verification Artifacts | v1.4 | 3/3 | Complete | 2026-04-22 |
| 18.2 v1.4 Gap Closure — Manifest Metadata + Tech Debt Cleanup | v1.4 | 3/3 | Complete | 2026-04-22 |
| 19. Vault Promotion Script (Layer B) | v1.5 | 4/4 | Complete | 2026-04-23 |
| 20. Diagram Seed Engine | v1.5 | 3/3 | Complete | 2026-04-23 |
| 21. Profile Extension & Template Bootstrap | v1.5 | 2/2 | Complete | 2026-04-23 |
| 22. Excalidraw Skill & Vault Bridge | v1.5 | 2/2 | Complete | 2026-04-27 |
| 23. Dedup `source_file` List-Handling Fix | v1.6 | 1/1 | Complete   | 2026-04-27 |
| 24. Manifest Writer Audit + Atomic Read-Merge-Write | v1.6 | 2/2 | Complete    | 2026-04-27 |
| 25. Mandatory Dual-Artifact Persistence in Skill Files | v1.6 | 1/1 | Complete    | 2026-04-27 |
| 26. v1.5 Configuration Guide & Walkthrough Docs | v1.6 | 1/1 | Complete   | 2026-04-27 |
| 27. Vault Detection & Profile-Driven Output Routing | v1.7 | 3/3 | Complete | 2026-04-28 |
| 28. Self-Ingestion Hardening | v1.7 | 3/3 | Complete | 2026-04-28 |
| 29. Doctor Diagnostics & Dry-Run Preview | v1.7 | 3/3 | Complete | 2026-04-28 |
| 30. Profile Composition | v1.7 | 3/3 | Complete | 2026-04-28 |
| 31. Template Engine Extensions | v1.7 | 2/2 | Complete | 2026-04-28 |
| 32. Profile Contract & Defaults | v1.8 | 4/4 | Complete    | 2026-04-29 |
| 33. Naming & Repo Identity Helpers | v1.8 | 4/4 | Complete    | 2026-04-29 |
| 34. Mapping, Cluster Quality & Note Classes | v1.8 | 4/4 | Complete   | 2026-04-29 |
| 35. Templates, Export Plumbing & Dry-Run/Migration Visibility | v1.8 | 0/TBD | Not started | - |
| 36. Migration Guide, Skill Alignment & Regression Sweep | v1.8 | 0/TBD | Not started | - |

---
*Last updated: 2026-04-28 — v1.8 Output Taxonomy & Cluster Quality planned: 5 phases (32–36), 33/33 requirements mapped, standard granularity.*
