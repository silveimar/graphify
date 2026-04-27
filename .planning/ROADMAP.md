# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- ✅ **v1.1 Context Persistence & Agent Memory** — Phases 6–8.2 (shipped 2026-04-13)
- ✅ **v1.2 Intelligent Analysis & Cross-File Extraction** — Phases 9, 9.1 (+ 9.1.1 gap closure) (shipped 2026-04-15)
- ✅ **v1.3 Intelligent Analysis Continuation** — Phases 9.2, 10, 11 (shipped 2026-04-17)
- ✅ **v1.4 Agent Discoverability & Obsidian Workflows** — Phases 12–18.2 (shipped 2026-04-22)
- ✅ **v1.5 Diagram Intelligence & Excalidraw Bridge** — Phases 19–22 (shipped 2026-04-27)
- 🔄 **v1.6 Hardening & Onboarding** — Phases 23–26 (planning 2026-04-27)

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

**Theme:** Make graphify viable for real production use on multi-source codebases — agents can query without blowing their token budget, extraction produces dramatically better graphs via entity deduplication, and humans get an interactive thinking partner via Obsidian slash commands. Priority order locked a → b → c during 2026-04-16 exploration: Phase 9.2 first (agent viability), Phase 10 second (graph quality), Phase 11 third (human UX).

**Origin:** Priority lock and scope decisions captured in `.planning/notes/april-2026-v1.3-priorities.md`. Research anchors: Your-GPUs-Just-Got-6x, Make-Knowledge-Graphs-Fast, Pied-Piper-Was-a-Documentary (cardinality estimation + bidirectional search signals for 9.2); Build-Agents-That-Never-Forget, Everything-Is-Connected, Cognee dedup patterns (entity fragmentation signals for 10); Obsidian-Claude-Codebook, Your-Harness-Your-Memory, memory-harness (static-to-interactive slash command pivot for 11). Phase 12 (Heterogeneous Extraction Routing) explicitly deferred to v1.4 — see Out of Scope in REQUIREMENTS.md.

**Phases:**

- [x] Phase 9.2: Progressive Graph Retrieval (3/3 plans, completed 2026-04-17)
- [x] Phase 10: Cross-File Semantic Extraction with Entity Deduplication (9/9 plans, completed 2026-04-17)
- [x] Phase 11: Narrative Mode as Interactive Slash Commands (7/7 plans, completed 2026-04-17)

**Totals:** 3 phases, 19 plans, 14/15 requirements satisfied (TOKEN-04 Bloom filter stretch deferred per D-09).

**Archives:**
- Full phase detail: `.planning/milestones/v1.3-ROADMAP.md`
- Requirements: `.planning/milestones/v1.3-REQUIREMENTS.md`

</details>

<details>
<summary>✅ v1.4 Agent Discoverability & Obsidian Workflows (Phases 12, 13, 14, 15, 16, 17, 18, 18.1, 18.2) — SHIPPED 2026-04-22</summary>

Agent discoverability via MCP capability manifest + harness-memory export (SEED-002), Obsidian workflow depth via vault-scoped thinking commands, and graph quality over time via heterogeneous routing, async enrichment, focus-aware zoom, grounded chat, and SPAR-Kit graph-argumentation. Phase 12 (Heterogeneous Extraction Routing) pulled forward from v1.3 deferral. Milestone audit passed after Phase 18.1 (Phase 13 verification artifact retrofill) and Phase 18.2 (MANIFEST-06 metadata closure + VALIDATION frontmatter refresh).

**Phases:**

- [x] Phase 12: Heterogeneous Extraction Routing — AST-complexity-classified routing to cheap/mid/expensive model classes with parallel fan-out, cost ceiling, model-isolated cache keys, `routing.json` sidecar. (6/6 plans, completed 2026-04-17)
- [x] Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export) — Static `server.json` + runtime `manifest.json`, MCP `capability_describe`, manifest-hash drift detection, `graphify harness export` producing SOUL/HEARTBEAT/USER triplet. (4/4 plans, 18/18 REQ-IDs, completed 2026-04-17; verification retrofitted via Phase 18.1)
- [x] Phase 14: Obsidian Thinking Commands — Vault-scoped `/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind` slash commands with `target:` frontmatter filtering + `propose_vault_note + approve` trust boundary. (6/6 plans, completed 2026-04-23)
- [x] Phase 15: Async Background Enrichment — Four-pass background enricher writing overlay-only `enrichment.json`; event-driven via `watch.py`; `fcntl.flock`-coordinated; snapshot-pinned for determinism. (6/6 plans, completed 2026-04-22)
- [x] Phase 16: Graph Argumentation Mode — `argue.py` SPAR-Kit-style `ArgumentPackage` + `argue_topic` MCP tool; `{claim, cites: [node_id]}` schema rejecting fabricated IDs; round cap 6; advisory-only `GRAPH_ARGUMENT.md`. (3/3 plans, completed 2026-04-23)
- [x] Phase 17: Conversational Graph Chat — Two-stage structurally-enforced `chat(query, session_id)` MCP tool; every claim cited; templated fuzzy suggestions on empty; `/graphify-ask` slash command. (3/3 plans, completed 2026-04-22)
- [x] Phase 18: Focus-Aware Graph Context — `get_focus_context(focus_hint)` MCP tool returning BFS ego-graph + community summary; codifies v1.3 CR-01 snapshot-root fix via `snapshot.py::root` → `project_root` rename. (4/4 plans, completed 2026-04-20)
- [x] Phase 18.1: v1.4 Gap Closure — Produced retrofitted `13-VERIFICATION.md`, `13-SECURITY.md`, `13-VALIDATION.md` for Phase 13's shipped 18 REQ-IDs. (commits `33f9f84`, `63d2480`, `1eda4be`)
- [x] Phase 18.2: v1.4 Gap Closure — Added `chat` + `get_focus_context` to `capability_tool_meta.yaml` closing MANIFEST-06; refreshed 15/18 VALIDATION frontmatter; audit re-stamped `passed`. (commits `59298c8`, `37aad87`, `012a90b`)

**Totals:** 9 phase directories (7 core + 2 gap closure), 32 plans, 72/86 P1+P2 requirements satisfied, 14 P2 carve-outs intentionally deferred. 155 files changed, +35,754 / −2,481 lines across 165 commits over 2026-04-17 → 2026-04-22.

**Deferred to v1.4.x / v1.5:**
- SEED-002 inverse-import (CLAUDE.md → graph) — requires quarantine + prompt-injection defenses (OQ-4)
- SEED-002 multi-harness schemas (codex.yaml, letta.yaml, honcho.yaml, AGENTS.md) — prove canonical on claude.yaml first (OQ-5)
- SEED-001 Tacit-to-Explicit Elicitation Engine — revisit if onboarding/discovery becomes the theme
- Phase 19 Vault Promotion Script Layer B — moved to v1.5 via scope reconciliation 2026-04-23 (commit `0f6304b`)

**Archives:**
- Full phase detail: `.planning/milestones/v1.4-ROADMAP.md`
- Requirements: `.planning/milestones/v1.4-REQUIREMENTS.md`
- Milestone audit: `.planning/milestones/v1.4-MILESTONE-AUDIT.md`
- Per-phase artifacts: `.planning/milestones/v1.4-phases/`

</details>

## Phase Details

### 🌱 Candidate Phase: ACE-Aligned Vocabulary, Linking & Naming

**Goal:** Replace graphify's hardcoded note-type vocabulary with an ACE-aligned,
profile-driven system. Emit full Ideaverse-compatible frontmatter (backlinks, collections,
rank, confidence tags) and enforce naming conventions across all vault output.

**Scope:**

- `project.yaml` — new `vocabulary:` section (note types, tags taxonomy, `diagrams:` with
  `x/Excalidraw/` folder map and per-template stencil/palette config)
- `profile.py` — parse and validate the `vocabulary:` section; expose typed dicts to all exporters
- `templates.py` — replace hardcoded `_NOTE_TYPES` frozenset with `vocab.note_types.keys()`
  loaded from profile; add `map`, `dot`, `work`, `question` built-in templates
- `mapping.py` — `classify()` driven by profile vocabulary rules; emit `rank` score to frontmatter
- `export.py` — emit full frontmatter: `up`, `related`, `down`, `collections`, `rank`,
  `created`, and confidence tags (`extracted`/`inferred`/`ambiguous`) on all promoted notes;
  all vault filenames use `safe_filename()` → `lowercase-hyphen` slugs with type prefix
- `seeds.py` (new) — generate `-seed.md` files in `x/Excalidraw/seeds/` from promoted Dots
  using `vocab.diagrams` template/stencil/palette config
- `builtin_templates/` — add `map-template.md`, `dot-template.md`, `work-template.md`,
  `question-template.md`; rename existing templates to `lowercase-hyphen-template` convention

**Naming conventions enforced (all output):**
- Tags: `lowercase-hyphen-separated`, no IDs/symbols/numbers
- Master Keys: `PascalCase`, max 4 words
- MD filenames: `lowercase-hyphen-separated` with type prefix
- Wikilinks: always with human-readable alias `[[filename|Human Readable Alias]]`
- Seeds: `name-seed.md` in `x/Excalidraw/seeds/`
- Diagrams: `name.excalidraw.md` in `x/Excalidraw/diagrams/`

**ACE folder targets:**
`Atlas/Maps`, `Atlas/Dots`, `Atlas/Dots/Things`, `Atlas/Dots/Statements`,
`Atlas/Dots/Questions`, `Atlas/Dots/People`, `Atlas/Sources`, `Efforts/Works`,
`x/Excalidraw/{annotations,cropped,diagrams,palettes,templates,seeds,scripts/downloaded,scripts/custom}`

**Design doc:** `.planning/notes/ace-vocabulary-naming-conventions.md`

**Entry point:** Run `/gsd-add-phase` to formally scope and plan this phase.

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

## v1.6 Hardening & Onboarding (Phases 23–26) — IN PLANNING

**Theme:** Close known stability gaps from v1.5 (dedup crash on `list[str]` source_file, manifest writers that overwrite siblings on subpath runs, persistence-block drift across platform skill variants) and produce the first end-to-end onboarding doc that lets a new user run the v1.5 diagram-intelligence pipeline from documentation alone — no source reading required.

**Origin:** Issue #4 surfaced the dedup `TypeError: unhashable type: 'list'` after v1.5 closed; manifest audit thread on 2026-04-27 confirmed multiple writers (`vault-manifest.json`, `seeds-manifest.json`, `routing.json`, MCP `manifest.json`) lack uniform read-merge-write semantics; SKILLMEM gap discovered when persistence contract present in working agent prompt did not survive `graphify install` round-trip.

**Phase independence:** All four phases are independent. No phase blocks another. Order is by risk priority (DEDUP first since it's a live crash) but execution can interleave.

### Phase 23: Dedup `source_file` List-Handling Fix
**Goal**: `graphify --dedup --dedup-cross-type` no longer crashes on extractions whose edges already carry `list[str]` `source_file` values; merged shape stays compatible with `export.py` consumers.
**Depends on**: —
**Requirements**: DEDUP-01, DEDUP-02, DEDUP-03
**Success Criteria** (what must be TRUE):
  1. `graphify --dedup --dedup-cross-type` completes on a fixture extraction whose edges already carry `list[str]` `source_file` values, with no `TypeError: unhashable type: 'list'`
  2. After dedup, an edge contributed by ≥2 sources has `source_file` equal to the sorted unique union of its inputs; an edge with exactly 1 contributor preserves the scalar shape
  3. `pytest tests/test_dedup.py -q` includes a regression case exercising the cross-type path on the list-shaped fixture and is green
  4. `export.py` consumers (HTML, JSON, GraphML, Obsidian) handle the merged `source_file` shape without raising
**Plans**: TBD

### Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening
**Goal**: All on-disk manifest writers in graphify use uniform read-merge-write semantics scoped by row identity, so subpath runs on a shared vault never erase sibling-subpath rows.
**Depends on**: —
**Requirements**: MANIFEST-09, MANIFEST-10, MANIFEST-11, MANIFEST-12
**Success Criteria** (what must be TRUE):
  1. Phase 24 ships an `AUDIT.md` (under `.planning/phases/24-*/`) enumerating every manifest writer in the codebase, its pre-v1.6 merge policy, and its post-fix policy
  2. `vault-manifest.json`, `seeds-manifest.json`, `routing.json`, and the MCP `manifest.json` all commit via `.tmp` + `os.replace` after read-merge-write keyed by row identity (path/id), not by run
  3. Two sequential runs against `vault/sub_a/` then `vault/sub_b/` produce a single manifest containing rows from both subpaths (regression test asserts both row sets present)
  4. `pytest tests/ -q` is green; subpath isolation regression test added under existing test conventions
**Plans**: TBD

### Phase 25: Mandatory Dual-Artifact Persistence in Skill Files
**Goal**: Every platform skill file emitted by `graphify install` carries the "Mandatory response persistence" contract verbatim (or platform-correct paraphrase), so interactive `query` / `path` / `explain` / `analyze` responses always write `graphify-out/memory/CMD_<TS>_<SLUG>.{graph,human}.md` regardless of which AI harness invokes the skill.
**Depends on**: —
**Requirements**: SKILLMEM-01, SKILLMEM-02, SKILLMEM-03, SKILLMEM-04
**Success Criteria** (what must be TRUE):
  1. Source `graphify/skill.md` contains a "Mandatory response persistence" section requiring dual-artifact writes for every interactive `query`/`path`/`explain`/`analyze` response
  2. All platform variants in `_PLATFORM_CONFIG` (claude, codex, opencode, openclaw, droid, trae, trae-cn, plus copilot/antigravity derivations — 8 entries total) carry the persistence contract verbatim or as a platform-correct paraphrase
  3. `graphify install <platform>` on a fresh install for each `_PLATFORM_CONFIG` entry emits a skill file containing the persistence canary string at its `skill_dst`
  4. A regression test in `tests/` grep-asserts the persistence canary in every emitted skill file across all `_PLATFORM_CONFIG[*].skill_dst` paths
**Plans**: TBD

### Phase 26: v1.5 Configuration Guide & Walkthrough Docs
**Goal**: A new user can configure and run the v1.5 pipeline (`vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → invoke skill) end-to-end on a sample vault using docs alone, including MCP tool integration.
**Depends on**: —
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A guide file exists at `CONFIGURING_V1_5.md` (or `docs/v1.5-configuration.md`) walking the full pipeline end-to-end on a sample vault: `vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → skill invocation
  2. The guide ships a complete example `.graphify/profile.yaml` with `diagram_types:` showing at least one custom type beyond the 6 built-ins, plus annotated frontmatter explaining D-06 gating and D-07 tiebreak
  3. The guide documents `list_diagram_seeds` and `get_diagram_seed` MCP tools — invocation shape, return schema, and `_resolve_alias` traversal-defense behavior — sufficient for an agent author to integrate without reading source
  4. `README.md` links to the guide via a "v1.5 Configuration" entry in the docs/getting-started area
**Plans**: TBD

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

| 23. Dedup `source_file` List-Handling Fix | v1.6 | 0/0 | Not started | — |
| 24. Manifest Writer Audit + Atomic Read-Merge-Write | v1.6 | 0/0 | Not started | — |
| 25. Mandatory Dual-Artifact Persistence in Skill Files | v1.6 | 0/0 | Not started | — |
| 26. v1.5 Configuration Guide & Walkthrough Docs | v1.6 | 0/0 | Not started | — |

---
*Last updated: 2026-04-27 — v1.6 Hardening & Onboarding scoped: 4 phases (23–26), 14 REQ-IDs across DEDUP/MANIFEST/SKILLMEM/DOCS, 14/14 mapped, all phases independent.*
