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
- ✅ **v1.8 Output Taxonomy & Cluster Quality** — Phases 32–38 (shipped 2026-04-29)
- ✅ **v1.9 Onboarding, Harness Portability & Vault CLI** — Phases 39–44 (shipped 2026-04-30)
- ✅ **v1.10 Stability, Baselines & Concept↔Code MVP** — Phases 45–52 (shipped 2026-05-01)
- 🔷 **v1.11 Templates, Graph Semantics & Vault Depth** — Phases 53–58 *(active — planning/execution)*

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

<details>
<summary>✅ v1.8 Output Taxonomy & Cluster Quality (Phases 32–38) — SHIPPED 2026-04-29</summary>

Make vault output legible at a glance and deliver a safe `work-vault` → `ls-vault` migration path: Graphify-owned default taxonomy, MOC-only community output, cluster-quality floor, repo identity and concept naming, CODE vs concept note classes, preview-first migration/update vault, platform skill alignment, Nyquist validation metadata ratification, and Phase 38 docs-only dormant-seed and quick-task lifecycle reconciliation.

**Totals:** 7 phases (32–38), 25 plans, 33/33 requirements satisfied.

**Archives:**

- Full phase detail: `.planning/milestones/v1.8-ROADMAP.md`
- Requirements: `.planning/milestones/v1.8-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.8-MILESTONE-AUDIT.md`

</details>

---

<details>
<summary>✅ v1.9 Onboarding, Harness Portability & Vault CLI (Phases 39–44) — SHIPPED 2026-04-30</summary>

Activate **SEED-001** (tacit-to-explicit elicitation), **SEED-002** (multi-harness memory + inverse import, with injection defenses), and complete **SEED-vault-root-aware-cli** (explicit `--vault`, multi-vault selector) on top of v1.7 vault detection.

**Phases:**

- [x] **Phase 39: Tacit-to-Explicit Onboarding & Elicitation** — Guided interview/state machine → validated extraction → SOUL/HEARTBEAT/USER artifacts; docs for discovery-first workflows. **Requirements:** ELIC-01–ELIC-07. **Depends on:** None within milestone (uses existing `validate`/`build`/`security`).
- [x] **Phase 40: Multi-Harness Memory, Inverse Import & Injection Defenses** — Extend harness export/import, canonical schemas, MCP parity, SECURITY.md threats; sanitize imported harness content. **Requirements:** PORT-01–PORT-05, SEC-01–SEC-04. **Depends on:** Phase 39 recommended for coherent artifact story (SOUL/HEARTBEAT provenance); can proceed in parallel if interfaces are frozen early.
- [x] **Phase 41: Vault CLI — `--vault` & Multi-Vault Selector** — Deterministic vault root flag, discovery/selection UX, `doctor` + dry-run alignment. **Requirements:** VCLI-01–VCLI-06. **Depends on:** v1.7 `ResolvedOutput` / vault detection (shipped).
- [x] **Phase 42: Milestone gap — Doctor profile preflight vs pinned vault** — Closes **VCLI-03** audit gap: `validate_profile_preflight` must use the same vault root as resolved profile paths when `--vault` / env / list pins apply (see `.planning/v1.9-MILESTONE-AUDIT.md`). **Gap closure** — not greenfield scope.
- [x] **Phase 43: Milestone gap — Elicitation ↔ `run` pipeline (ELIC-02)** — Merge sidecar at `build()` callers (`update-vault`, `watch`); document extract-only `run`; tests for ELIC-02. **Gap closure (shipped).**
- [x] **Phase 44: Milestone gap — Verification & Nyquist artifacts (TRACE-01)** — `39`/`40`/`41`-VERIFICATION.md + **`38-02-SUMMARY.md`**; REQUIREMENTS + audit updated. **Gap closure (shipped).**

**Success criteria (milestone):**

1. A user with no corpus can run elicitation and obtain graph + harness artifacts without manual YAML authoring.
2. Harness import/export paths share validation with CLI and resist injection gadgets covered by tests.
3. Scripts can pin vault context with `--vault` and multi-root environments can select a vault without fragile `cd`.
4. **Gap closure:** Doctor validates the **pinned** vault profile; ELIC-02 has an explicit, tested story; GSD verification artifacts exist for shipped v1.9 phases.

**Totals:** 6 phases (39–44); 22+ requirements mapped; gap phases close `.planning/v1.9-MILESTONE-AUDIT.md` items.

</details>

<details>
<summary>Phase 39: Tacit-to-Explicit Onboarding &amp; Elicitation — PLANNING</summary>

**Goal:** Guided interview/state machine → validated extraction → SOUL/HEARTBEAT/USER artifacts; docs for discovery-first workflows. **Requirements:** ELIC-01–ELIC-07. **Context:** `.planning/phases/39-tacit-to-explicit-onboarding-elicitation/39-CONTEXT.md` (D-01..D-08).

**Plans:** 5 plans in 4 waves

Plans:
- [ ] `39-01-PLAN.md` — [wave 1] Library core: hybrid scripted elicitation, sidecar persistence, validation tests (ELIC-01/02/04/05/06; D-03, D-06)
- [ ] `39-02-PLAN.md` — [wave 2] `build()` merge for elicitation sidecar with explicit ordering + tests (ELIC-02/04/05; D-06)
- [ ] `39-03-PLAN.md` — [wave 3] Harness-aligned direct + `export_claude_harness` integration (ELIC-03/05; D-04)
- [ ] `39-04-PLAN.md` — [wave 3] Canonical `graphify elicit` CLI + skill thin wrappers + `resolve_output` (ELIC-01/02/05/06; D-01/D-02/D-05)
- [ ] `39-05-PLAN.md` — [wave 4] `docs/ELICITATION.md` + README pointer (ELIC-07; D-08)

**Artifacts:** `39-RESEARCH.md`, `39-PATTERNS.md` in phase directory.

</details>

<details>
<summary>Phase 40: Multi-Harness Memory, Inverse Import &amp; Injection Defenses — PLANNING</summary>

**Goal:** Canonical **JSON harness interchange**, **`import-harness`** into validated extraction dicts, **layered sanitization**, **MCP–CLI parity**, and **SECURITY.md** harness I/O subsection. **Requirements:** PORT-01–PORT-05, SEC-01–SEC-04. **Context:** `.planning/phases/40-multi-harness-memory-inverse-import-injection-defenses/40-CONTEXT.md` (D-01..D-07). **Phase 39** elicitation/harness contracts must not break without migration note.

**Plans:** 5 plans in 4 waves

Plans:
- [ ] `40-01-PLAN.md` — [wave 1] Interchange v1 schema + `harness_interchange` export + CLI wire + tests (PORT-01, PORT-02, SEC-02; D-01)
- [ ] `40-02-PLAN.md` — [wave 2, depends on 01] `harness_import` library + `security` sanitization + tests (PORT-03, PORT-05, SEC-01)
- [ ] `40-03-PLAN.md` — [wave 3, depends on 02] `graphify import-harness` CLI + integration tests (PORT-03, PORT-05; D-02, D-03)
- [ ] `40-04-PLAN.md` — [wave 3, depends on 02] MCP tools + `SECURITY.md` harness subsection + tests (SEC-03, SEC-04; D-05, D-07)
- [ ] `40-05-PLAN.md` — [wave 4, depends on 01+03+04] Export→import semantic round-trip tests + documented limits (PORT-04; D-06)

**Artifacts:** `40-RESEARCH.md`, `40-PATTERNS.md` in phase directory.

</details>

<details>
<summary>Phase 41: Vault CLI — explicit vault flag &amp; Multi-Vault Selector — PLANNING</summary>

**Goal:** Deterministic **`--vault &lt;path&gt;`** vault root selection, **multi-vault discovery/selection** UX suitable for scripts and CI, and alignment of **`doctor`**, **dry-run**, and **preview** messaging with resolved vault + output from v1.7–v1.8. **Requirements:** VCLI-01–VCLI-06. **Depends on:** v1.7 `ResolvedOutput` / vault detection (shipped); **Phase 40** does not deliver vault selector surface.

**Plans:** TBD after research/plan-phase.

**Artifacts:** `41-RESEARCH.md`, `41-PATTERNS.md`, `41-CONTEXT.md` in phase directory.

</details>

<details>
<summary>Phase 42: Milestone gap — Doctor profile preflight vs pinned vault — GAP CLOSURE</summary>

**Goal:** When `run_doctor(..., resolved_output=…)` supplies a pinned vault, **`validate_profile_preflight`** runs against **that** vault root (not shell CWD). Restores **VCLI-03** parity with **Phase 41** intent. **Source:** `.planning/v1.9-MILESTONE-AUDIT.md` (integration: doctor → `validate_profile_preflight`).

**Requirements:** **VCLI-03** (completion). **Depends on:** Phase 41 shipped code paths.

**Plans:** `42-01-PLAN.md` (1/1 executed)

**Artifacts:** `42-CONTEXT.md`, `42-01-SUMMARY.md`, `42-VERIFICATION.md` in phase directory.

</details>

<details>
<summary>Phase 43: Milestone gap — Elicitation ↔ run pipeline (ELIC-02) — GAP CLOSURE</summary>

**Goal:** Close **ELIC-02** audit partial: explicit product decision + implementation and/or documentation so elicitation-shaped extraction joins **`build`** on the path users expect (`graphify run` vs skill-only). **Source:** `.planning/v1.9-MILESTONE-AUDIT.md`.

**Requirements:** **ELIC-02** (completion), **ELIC-07** (docs). **Depends on:** Phase 39 deliverables (library + sidecar).

**Plans:** 3 plans in 2 waves

Plans:
- [x] `43-01-PLAN.md` — [wave 1] `run_update_vault`: merge `elicitation.json` before `build()` + migration tests (ELIC-02)
- [x] `43-02-PLAN.md` — [wave 1] `watch._rebuild_code`: merge sidecar before `build()` + watch tests (ELIC-02)
- [x] `43-03-PLAN.md` — [wave 2, depends on 01+02] `docs/ELICITATION.md` + `run` CLI help — merge surfaces vs extract-only `run` (ELIC-07)

**Artifacts:** `43-CONTEXT.md`, `43-RESEARCH.md`, `43-*-PLAN.md`, `43-*-SUMMARY.md`, `43-VERIFICATION.md` in phase directory.

</details>

<details>
<summary>Phase 44: Milestone gap — Verification &amp; Nyquist artifacts (TRACE-01) — GAP CLOSURE</summary>

**Goal:** Persist GSD **`*-VERIFICATION.md`** for phases **39–41** minimum; add **`*-VALIDATION.md`** where Nyquist policy applies; resolve **38-02** plan/summary debt if still outstanding. Closes **TRACE-01** from audit. **Source:** `.planning/v1.9-MILESTONE-AUDIT.md`.

**Requirements:** Process / traceability (maps to milestone audit gates). **Depends on:** none (docs-only + optional `/gsd-validate-phase`).

**Plans:** 4 plans in 2 waves

Plans:
- [x] `44-01-PLAN.md` — [wave 1] `39-VERIFICATION.md` (ELIC-01–07, TRACE-01)
- [x] `44-02-PLAN.md` — [wave 1] `40-VERIFICATION.md` (PORT/SEC, TRACE-01)
- [x] `44-03-PLAN.md` — [wave 1] `41-VERIFICATION.md` (VCLI, TRACE-01)
- [x] `44-04-PLAN.md` — [wave 2, depends on 01–03] `38-02-SUMMARY.md` + REQUIREMENTS + `v1.9-MILESTONE-AUDIT.md` TRACE-01 hygiene

**Artifacts:** `44-CONTEXT.md`, `44-RESEARCH.md`, `44-*-PLAN.md`, `44-*-SUMMARY.md`, `44-VERIFICATION.md` in phase directory.

</details>

<details>
<summary>✅ v1.10 Stability, Baselines & Concept↔Code MVP (Phases 45–52) — SHIPPED 2026-05-01</summary>

**Themes:** Detect/collect-files/**`corpus_prune`** baselines and manifest parity (**HYG-01..03**); concept↔code schema, merge, sanitization (**CCODE-01/02/05**); MCP **`concept_code_hops`** + trace/doc reconciliation (**CCODE-03/04**); **`.graphifyignore`** / canonical **`graphify-out`** (**HYG-04/05**); CLI **`--version`** / skill stamp (**CLI-VER-01/02**). Gap closures **50–52** delivered formal **`*-VERIFICATION.md`** artifacts and REQ sign-off.

**Totals:** 8 phase tracks (45–49 plus gap **50–52**); **13/13** requirements satisfied.

**Archives:** `.planning/milestones/v1.10-ROADMAP.md`, `.planning/milestones/v1.10-REQUIREMENTS.md`, `.planning/milestones/v1.10-MILESTONE-AUDIT.md`

</details>

<details open>
<summary>🔷 v1.11 Templates, Graph Semantics & Vault Depth (Phases 53–58) — ACTIVE</summary>

Typed **concept↔code** edges, **template** conditionals/loops/Dataview hooks, **profile overrides**, **elicitation/harness** increments, **vault CLI** parity, and **hygiene** closures. Phase numbering continues after v1.10 (**53+**).

| Phase | Goal | Requirements | Success criteria (observable) |
|-------|------|--------------|------------------------------|
| **53** — Concept↔code **schema & build** | New relation values validated; deterministic merge in `build` | **CGRAPH-01**, **CGRAPH-02** | `validate_extraction` rejects malformed edges; golden graph shows stable merged concept↔code edges in `pytest` |
| **54** — **MCP / trace / export** parity | Same semantic edges across MCP, slash trace, and Obsidian export | **CGRAPH-03**, **CGRAPH-04** | Documented mapping table + automated golden-path for MCP/traces; export tests cannot contradict graph edges |
| **55** — Template **conditionals & loops** | Block syntax before `${}` substitution | **TMPL-01**, **TMPL-02** | Fixture vault templates render with conditionals + `#connections`; sanitization regression tests |
| **56** — **Dataview** templates & **override** rules | Per-note-type Dataview + scoped overrides | **TMPL-03**, **CFG-01**, **CFG-02** | `validate_profile_preflight` errors on invalid queries; collision matrix tests for override precedence |
| **57** — **Elicitation & harness** | Measurable uplift vs v1.9 with explicit trust boundaries | **ELIC-01**, **ELIC-02**, **HARN-01**, **HARN-02** | New elicitation scenario tests; docs updated; harness import remains **off-default** with guard tests if touched |
| **58** — **Vault CLI & hygiene** | Doctor parity + registry closure | **VAUX-01**, **VAUX-02**, **HYG-01** | CLI/doctor parity tests; quick-task / waiver recorded with evidence |

**Totals:** 6 phases — **18/18** REQ-IDs mapped (**100% coverage**).

**Depends-on hints:** **53 → 54** (surface only after schema/build); **55 → 56** (blocks stable before Dataview complexity); **57** and **58** can partially parallelize after **53** lands.

**Plans:** create under `.planning/phases/5[3-8]-*/` during `/gsd-plan-phase`.

</details>

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
| 34. Mapping, Cluster Quality & Note Classes | v1.8 | 5/5 | Complete   | 2026-04-29 |
| 35. Templates, Export Plumbing & Dry-Run/Migration Visibility | v1.8 | 3/3 | Complete    | 2026-04-29 |
| 36. Migration Guide, Skill Alignment & Regression Sweep | v1.8 | 5/5 | Complete    | 2026-04-29 |
| 37. Validation Metadata Ratification | v1.8 | 2/2 | Complete   | 2026-04-29 |
| 38. Dormant seeds & quick-task reconciliation | v1.8 | 2/2 | Complete | 2026-04-29 |
| 39. Tacit-to-Explicit Onboarding & Elicitation | v1.9 | 5/5 | Complete | 2026-04-30 |
| 40. Multi-Harness Memory, Inverse Import & Injection Defenses | v1.9 | 5/5 | Complete | 2026-04-30 |
| 41. Vault CLI — `--vault` & Multi-Vault Selector | v1.9 | 4/4 | Complete | 2026-04-30 |
| 42. Doctor preflight vs pinned vault (gap closure) | v1.9 | 1/1 | Complete | 2026-04-30 |
| 43. Elicitation ↔ run pipeline ELIC-02 (gap closure) | v1.9 | 3/3 | Complete | 2026-04-30 |
| 44. Verification / Nyquist artifacts TRACE-01 (gap closure) | v1.9 | 4/4 | Complete | 2026-04-30 |
| 45. Baselines & Detect Self-Ingestion | v1.10 | 3/3 | Complete | 2026-04-30 |
| 46. Concept↔Code Schema, Build Merge & Security | v1.10 | 3/3 | Complete | 2026-04-30 |
| 47. MCP & Trace Integration | v1.10 | 2/2 | Complete | 2026-05-01 |
| 48. Graphifyignore & nested graphify-out consolidation | v1.10 | 2/2 | Complete | 2026-04-30 |
| 49. CLI `--version`, stderr version line, skill/package stamp | v1.10 | 1/1 | Complete | 2026-05-01 |
| 50. v1.10 gap — Baselines verification | v1.10 | 1/1 | Complete    | 2026-05-01 |
| 51. v1.10 gap — MCP & trace REQ sign-off | v1.10 | 1/1 | Complete    | 2026-05-01 |
| 52. v1.10 gap — Phase 48 verification artifact | v1.10 | 1/1 | Complete    | 2026-05-01 |
| 53. Concept↔code schema & build merge | v1.11 | 0/? | Not started | — |
| 54. MCP, trace & Obsidian parity | v1.11 | 0/? | Not started | — |
| 55. Template conditionals & connection loops | v1.11 | 0/? | Not started | — |
| 56. Dataview templates & profile overrides | v1.11 | 0/? | Not started | — |
| 57. Elicitation & harness increment | v1.11 | 0/? | Not started | — |
| 58. Vault CLI parity & hygiene | v1.11 | 0/? | Not started | — |

### Phase 47: MCP & Trace Integration

**Goal:** Agents and narrative commands can **find and walk** typed concept↔implementation links through **MCP** and **`/trace` or `entity_trace`**, with documentation updated when capability surfaces change.
**Depends on:** Phase 46 (typed edges live in validated graph artifacts).
**Requirements:** **CCODE-03**, **CCODE-04**.

**Success Criteria** (what must be TRUE):

1. At least one MCP tool or structured graph-query path exposes or traverses concept↔implementation edges; **manifest/capability** and skill docs reflect any new tools or parameters (**CCODE-03**).
2. **`/trace`** (slash workflow) **or** **`entity_trace`** MCP follows concept↔code hops in **at least one golden-path scenario** backed by automated tests (**CCODE-04**).

**Plans:** `.planning/phases/47-mcp-trace-integration/` — `47-01-PLAN.md` (wave 1: MCP `concept_code_hops` + tests), `47-02-PLAN.md` (wave 2: docs, `server.json`, skills).

**UI hint**: yes — slash **`/trace`** command surface ties to conversational UX workflows.

### Phase 49: add --version flag to graphify command, and also print current version on each command result, Fix skill vs package version validations (graphify update-vault warning: skill is from graphify 0.4.7, package is 1.0.0)

**Goal:** CLI `--version` / `-V`, stderr `[graphify] version` on successful non-install commands, directional skill-stamp warnings, `graphify.version.package_version()` as single metadata reader.
**Requirements:** **CLI-VER-01**, **CLI-VER-02**
**Depends on:** Phase 48
**Plans:** 1 plan (wave 1)

Plans:
- [x] `49-01-PLAN.md` — `graphify.version`, CLI flags, `_cli_exit` footer, skill stamp copy, tests (`test_main_cli` / `test_main_flags`)

---
*Last updated: 2026-04-30 — **v1.11** phases **53–58** added (active); v1.10 narrative archived under `.planning/milestones/v1.10-ROADMAP.md`.*
