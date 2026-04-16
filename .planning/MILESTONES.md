# Milestones

## v1.2 Intelligent Analysis & Cross-File Extraction (Shipped: 2026-04-15)

**Delivered:** LLM-assisted multi-perspective graph analysis via autoreason tournament (A/B/AB/blind-Borda rounds across 4 lenses), per-edge MCP query telemetry with hot-path strengthening and decay of unused edges, 2-hop A→C derived edges with INFERRED confidence, and hot/cold paths surfaced in `GRAPH_REPORT.md`. Analysis output is scoped to a dedicated `GRAPH_ANALYSIS.md` file — `GRAPH_REPORT.md` remains the mechanical metrics artifact (D-80 separation).

**Phases completed:** 3 phases (09, 09.1, 09.1.1), 9 plans
**Timeline:** 2026-04-14 → 2026-04-15 (2 days of code + 1 day of retroactive lifecycle cleanup 2026-04-15/16)
**Codebase delta:** 6 code files changed, +1083 / −6 lines (9.1.1 was planning-only, zero code delta)
**Test suite:** 1023 passing (up from 1000 at v1.1), no regressions
**Requirements:** 10/10 satisfied
**Audit:** Passed (10/10 REQ-IDs, 5/5 integration links WIRED, 3/3 E2E flows COMPLETE) — see `.planning/milestones/v1.2-MILESTONE-AUDIT.md`

### Key Accomplishments

1. **Autoreason Tournament Analysis** (Phase 9) — `render_analysis_context()` in `analyze.py` serializes the graph (nodes, edges, communities, god nodes, surprising connections) for tournament LLM prompts. `render_analysis()` in `report.py` produces the final `GRAPH_ANALYSIS.md` with per-lens sections, cross-lens synthesis (convergences + tensions), overall verdict, and tournament rationale (A/B/AB Borda scores). Tournament orchestration lives in `skill.md` (~260 lines, 6-step protocol A1–A6) with 4 independent lenses × 4 rounds × blind judges. "No finding" competes as a first-class Borda option — prevents hallucinated problems on clean graphs. 23 new tests (9 for context, 14 for report).

2. **Query Telemetry & Usage-Weighted Edges** (Phase 9.1) — `serve.py` records every MCP traversal to a `telemetry.json` sidecar with atomic `os.replace()` writes. Per-edge traversal counters feed a weight formula with exponential decay of unused edges. After N traversals of A→B→C, a direct A→C derived edge is proposed with `confidence=INFERRED`, `confidence_score=0.7`, and a `via` field naming the intermediate node. Neighbor-identity skip in `_check_derived_edges` prevents self-loops when `neighbor == a`. `report.py` emits a new "Usage Patterns" section with hot/cold paths classified via percentile thresholds.

3. **Pipeline Integration** (Phase 9.1, Plan 3) — Telemetry decay fires on every rebuild; usage data flows into all three `generate()` call sites and both rebuild points in `skill.md`. The graph's `agent-edges.json` and `annotations.jsonl` sidecars use the same atomic-write pattern as telemetry — no partial-write corruption possible mid-query.

4. **Retroactive Milestone Lifecycle Cleanup** (Phase 9.1.1) — Planning-only phase that closed three structural gaps found by `/gsd-audit-milestone`: (a) generated retroactive `09.1-VERIFICATION.md` from existing UAT/VALIDATION/SECURITY evidence, (b) created project-level `.planning/REQUIREMENTS.md` with 10 v1.2 REQ-IDs and a full traceability matrix back to file:line anchors, (c) reconciled scope contradictions across `ROADMAP.md` / `STATE.md` / `PROJECT.md` into a consistent narrow-v1.2 narrative, moving phases 9.2/10/11/12 into a new v1.3 milestone and renaming the old v1.3 → v1.4. Zero code changes; audit status upgraded `gaps_found → passed`.

### Architectural Decisions Locked

- **D-80: GRAPH_ANALYSIS.md is separate from GRAPH_REPORT.md** — tournament output never mutates the mechanical metrics artifact. Verified behaviorally in 09-HUMAN-UAT.md.
- **D-83: Every lens always appears as a section** — `report.py` iterates all lens_results with no filtering, so Clean verdicts (e.g., "3-0 unanimous for incumbent") are visible rather than silently omitted.
- **Blind Borda judges** — judge prompts use shuffled neutral labels (Analysis-1/2/3) with no role identity disclosed; shuffle rotation enforced across 3 judges.
- **Telemetry atomicity** — `telemetry.json`, `agent-edges.json`, and `annotations.jsonl` use `os.replace()` for all writes; no torn reads during concurrent MCP queries.
- **Narrow-scope milestone policy** — v1.2 closed when 2/6 originally-planned phases completed the intent. Remaining scope queued into v1.3 with clear origin anchoring rather than leaving v1.2 open indefinitely.

### Known Gaps / Deferred

- 09.1-SECURITY.md lacks structured YAML frontmatter (no `threats_total`/`threats_open` fields) — all 7 threats marked CLOSED in the table body but grep-based frontmatter extraction returns empty. Non-blocking tech debt.
- v1.2 was never formally instantiated via `/gsd-new-milestone`; REQUIREMENTS.md was created post-hoc by Phase 9.1.1, so SUMMARY.md files for 09 and 09.1 predate it and have no `requirements_completed` frontmatter. Non-blocking; audit accepted as documented.
- Remaining v1.2-origin scope (Progressive Graph Retrieval, Cross-File Semantic Extraction, Narrative Mode, Heterogeneous Extraction Routing) carried forward to v1.3.

### Archives

- `.planning/milestones/v1.2-ROADMAP.md` — full phase detail with plan breakdowns
- `.planning/milestones/v1.2-REQUIREMENTS.md` — 10 v1.2 REQ-IDs with traceability table (file:line evidence)
- `.planning/milestones/v1.2-MILESTONE-AUDIT.md` — final audit report (passed)

---

## v1.1 Context Persistence & Agent Memory (Shipped: 2026-04-13)

**Delivered:** Persistent, evolving context layer — graphify is no longer a one-shot graph builder. Agents can read AND write to the knowledge graph across sessions, users see how their corpus changes over time, and Obsidian vault notes survive round-trip re-runs with user content preservation.

**Phases completed:** 5 phases (6–8.2), 12 plans, ~117 commits
**Timeline:** 2026-04-12 → 2026-04-13 (2 days)
**Codebase delta:** 13,520 LOC across 26 Python modules (`graphify/`) — 3,663 insertions across 13 files
**Test suite:** 1,000 passing (up from 872 at v1.0)
**Requirements:** 25/25 satisfied
**Audit:** Passed (25/25 requirements, 5/5 phases, 25/25 integration, 3/3 flows)

### Key Accomplishments

1. **Graph Delta Analysis & Staleness** (Phase 6) — `snapshot.py` and `delta.py` modules deliver run-over-run comparison with `GRAPH_DELTA.md` output, snapshot persistence with FIFO retention, per-node provenance metadata (`extracted_at`, `source_hash`, `source_mtime`), three-state staleness classification (FRESH/STALE/GHOST), and community migration tracking. `graphify snapshot` CLI subcommand with `--name/--cap/--from/--to/--delta` flags.

2. **MCP Write-Back with Peer Modeling** (Phase 7) — 5 new MCP tools (`annotate_node`, `flag_node`, `add_edge`, `propose_vault_note`, `get_annotations`) with JSONL/JSON sidecar persistence, peer identity tracking (`peer_id`, `session_id`, `timestamp`), mtime-based graph reload, and startup compaction. `graph.json` is never mutated by agent tools.

3. **Human-in-the-Loop Proposals** (Phase 7, Plan 3) — `graphify approve` CLI subcommand for listing, approving, rejecting, and batch-processing agent-proposed vault notes. Proposals stage to `graphify-out/proposals/` with UUID4 filenames; vault is untouched until explicit approval.

4. **Obsidian Round-Trip Awareness** (Phase 8) — Content-hash manifest (`vault-manifest.json`) tracks what graphify wrote per note. On re-run, user-modified notes receive `SKIP_PRESERVE`. User sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) provide inviolable preservation zones that survive even REPLACE strategy and `--force` mode. Dry-run enhanced with source annotations and summary preamble.

5. **Pipeline Integration & MCP Enhancements** (Phases 8.1–8.2) — Auto-snapshot and auto-delta on every `/graphify` run (skill.md wiring). Approve path threaded through vault manifest for user-modified detection. MCP `get_node` surfaces provenance fields and staleness classification. New `get_agent_edges` query tool with peer/session/node filtering.

### Architectural Decisions Locked

- peer_id defaults to `"anonymous"` — never derived from environment variables (security: prevents machine identity leaking into committed annotation files)
- `graph.json` is read-only pipeline ground truth — all agent state lives in JSONL/JSON sidecars
- Proposal filenames are server-generated UUID4 — never derived from agent-supplied input
- Content-hash manifest uses content-only SHA256 (no path) to avoid macOS symlink mismatch
- User sentinel blocks are inviolable even for REPLACE strategy — user content always wins
- Multiple USER_START/END pairs per note supported

### Known Gaps / Deferred

- **WIRING-01** (low): `_approve_and_write_proposal` hardcodes manifest path to `Path('graphify-out')` — doesn't respect `--out-dir` override
- 6 human verification items pending (real vault E2E tests for Phases 8 and 8.1)
- Template engine extensions (TMPL-01/02/03, CFG-02/03) deferred to v1.2+

### Archives

- `.planning/milestones/v1.1-ROADMAP.md` — full phase detail with success criteria and plan descriptions
- `.planning/milestones/v1.1-REQUIREMENTS.md` — 25 v1.1 requirements with traceability table
- `.planning/milestones/v1.1-MILESTONE-AUDIT.md` — audit report with integration verification

---

## v1.0 Ideaverse Integration — Configurable Vault Adapter (Shipped: 2026-04-11)

**Delivered:** Configurable output adapter that injects graphify knowledge graphs into any Obsidian vault framework via a declarative `.graphify/profile.yaml`. Replaces the monolithic `to_obsidian()` with a four-component pipeline (profile → mapping → templates → merge) and wires it behind two new CLI entry points. Backward-compatible when no vault profile exists (default profile emits Ideaverse ACE Atlas/ layout).

**Phases completed:** 5 phases, 22 plans, ~172 commits
**Timeline:** 2026-04-09 → 2026-04-11 (2 days)
**Codebase delta:** 11,620 LOC across 24 Python modules (`graphify/`) + 10,500 LOC across 33 test files (`tests/`)
**Test suite:** 872 passing (up from pre-milestone baseline)
**Requirements:** 31/33 satisfied (2 de-scoped via D-74 — see Out of Scope in archived requirements)

### Key Accomplishments

1. **Configurable vault profile system** (Phase 1: Foundation) — `.graphify/profile.yaml` discovery, deep-merge over built-in defaults, schema validation with actionable errors, path-traversal guard (`validate_vault_path`). Standalone `profile.py` module with no `export.py` coupling (D-16). Ships `_DEFAULT_PROFILE` constant producing Ideaverse ACE Atlas/ layout.

2. **Safety helpers + pre-existing bug fixes** (Phase 1 Plan 2) — `safe_filename` with NFC normalization (FIX-04) and 200-char length cap (FIX-05), `safe_tag` handling slashes / plus signs / digit-at-start (FIX-03), `safe_frontmatter_value` neutralizing YAML injection (FIX-01), and deterministic filename deduplication sorted on `(source_file, label)` (FIX-02). PyYAML added as optional `obsidian` extra.

3. **Template engine with placeholder substitution** (Phase 2: Template Engine) — `graphify/templates.py` delivers 6 built-in note types (MOC, Thing, Statement, Person, Source, Community Overview) via `string.Template.safe_substitute` with KNOWN_VARS + two-phase Dataview wrap. User template overrides in `.graphify/templates/` with built-in fallback on error. Wayfinder navigation callouts. Configurable filename conventions.

4. **Mapping engine with dual-evaluation classification** (Phase 3: Mapping Engine) — `graphify/mapping.py` classifies every graph node into exactly one note type via first-match-wins precedence: attribute rules (`compile_rules` + `_match_when`) override topology fallbacks (god nodes → Things, communities above threshold → MOCs, source files → Sources, default → Statements). Configurable community-to-MOC threshold; below-threshold communities collapse into sub-community callouts. Source-file extension routing.

5. **Merge engine with field-level policies** (Phase 4: Merge Engine) — `graphify/merge.py` delivers a pure `compute_merge_plan` (CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN actions) and atomic `apply_merge_plan` (`.tmp` + fsync + `os.replace`). 14-key built-in field-policy table (D-64), hand-rolled YAML frontmatter reader as strict inverse of `_dump_frontmatter`, D-67 sentinel block protection for graphify-owned body regions, content-hash skip for idempotent re-runs, D-72 orphan preservation. Four configurable merge strategies (`update` / `skip` / `replace`). 28/28 must-haves verified.

6. **Integration & CLI** (Phase 5: Integration & CLI) — Refactored `to_obsidian()` in `graphify/export.py` orchestrates the four-module pipeline behind a single entry point. `graphify --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run]` and `graphify --validate-profile <vault-path>` land in `__main__.py:691-740`. `validate_profile_preflight` runs a four-layer preflight (schema → templates → dead-rules → path-safety). `format_merge_plan` + `split_rendered_note` public helpers support dry-run formatting. All 9 skill platform variants updated with the new pipeline patterns.

### Architectural Decisions Locked

- **D-73** — CLI is utilities-only; the skill is the pipeline driver. `graphify --obsidian` and `graphify --validate-profile` exist as direct utility entry points, but the full detect→extract→build→cluster→analyze→report→export pipeline runs via the skill (`graphify/skill.md`), not via a single CLI verb. Avoids rebuilding agent orchestration in Python.
- **D-74** — De-scope `.obsidian/graph.json` generation from `to_obsidian()` — the library entry point is a notes pipeline, not a vault-config-file manager. OBS-01 and OBS-02 moved to Out of Scope. The underlying `safe_tag()` invariant (slug form `community/<slug>`) remains and is anchored by `tests/test_profile.py::test_obs01_obs02_safe_tag_regression_anchor`.

Other locked decisions (D-01..D-72) are recorded in the archived phase contexts and in `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.

### Verification

- All 5 phases have passing VERIFICATION.md artifacts (Phase 01 was retroactive to close the audit's evidence gap — commit `ffdb076`)
- 12/12 cross-phase integration key-links WIRED (verified by `gsd-integration-checker`)
- 5/5 primary user flows traced end-to-end (2 of them additionally live-verified against a 3-node graph fixture)
- Milestone audit run #2: `status: passed` — see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

### Known Gaps / Deferred

- **OBS-01, OBS-02** — `.obsidian/graph.json` read-merge-write management. Deliberately de-scoped via D-74. Revisit if a future release needs plugin-side graph.json management.
- **SUMMARY.md frontmatter schema drift** — Phases 2/3/5 used inconsistent field names (`requirements-completed`, `requirements`, `requirements_closed`) or omitted the field. Non-blocking; future housekeeping.
- **Nyquist validation artifacts** — Only Phase 1 has `VALIDATION.md`. Phases 2-5 shipped without Nyquist coverage. Advisory only per workflow config.

### Archives

- `.planning/milestones/v1.0-ROADMAP.md` — full phase detail (success criteria, plan descriptions, requirements mapping)
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 33 v1 requirements with traceability table + Out of Scope for D-74 items
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — audit runs 1 and 2, integration trace, 3-source cross-reference

---
