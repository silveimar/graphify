# Requirements: graphify

**Defined:** 2026-04-15
**Core Value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile — extended in v1.2 with multi-perspective analysis and usage-weighted graph self-improvement

**Archives:**
- v1.0 — `.planning/milestones/v1.0-REQUIREMENTS.md`
- v1.1 — `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.2 Requirements — Intelligent Analysis & Cross-File Extraction

**Status:** SHIPPED 2026-04-15 (narrow scope: phases 9 + 9.1)
**Source:** Derived from ROADMAP.md phase bullets and registered post-hoc per `.planning/v1.2-MILESTONE-AUDIT.md`. Milestone was never formally instantiated via `/gsd-new-milestone`; this catalog closes that gap.

**Narrow-scope decision:** v1.2 concludes at phases 9 and 9.1. ROADMAP.md phases 9.2, 10, 11, 12 have been moved to v1.3 (see Phase 9.1.1 scope reconciliation).

### Multi-Perspective Graph Analysis with Autoreason Tournament

- [x] **v1.2-REQ-09-A**: Configurable analysis lenses (security, architecture, complexity, onboarding) with autoreason tournament (A/B/AB/Borda) — Phase 09 — `skill.md:1324-1545 → analyze.py:456 → report.py:256`
- [x] **v1.2-REQ-09-B**: "No finding" competes as first-class Borda option — Phase 09 — `skill.md:1502 tournament_failed + :1526 "no issues found" → Clean verdict`
- [x] **v1.2-REQ-09-C**: Tournament output in GRAPH_ANALYSIS.md separate from GRAPH_REPORT.md (D-80) — Phase 09 — `skill.md:1546 writes GRAPH_ANALYSIS.md; generate()/GRAPH_REPORT.md never overlaps`

### Query Telemetry & Usage-Weighted Edges

- [x] **v1.2-REQ-09.1-A**: Per-edge traversal counters via MCP query telemetry — Phase 09.1 — `serve.py:630 _tool_query_graph → :642 _record_traversal → :643 _save_telemetry`
- [x] **v1.2-REQ-09.1-B**: Strengthen hot paths, decay unused ones — Phase 09.1 — `serve.py:110 _edge_weight = 1.0+log(n) clamped; skill.md:439,999 _decay_telemetry(0.8)`
- [x] **v1.2-REQ-09.1-C**: 2-hop A→C derived edge with INFERRED confidence after N traversals — Phase 09.1 — `serve.py:644 _check_derived_edges → :163 INFERRED, :164 score 0.7, :166 via:b → :173 _save_agent_edges`
- [x] **v1.2-REQ-09.1-D**: Hot/cold paths surfaced in GRAPH_REPORT.md — Phase 09.1 — `skill.md:429 loads telemetry → :433 generate(usage_data=) → report.py:16 _compute_hot_cold → :219 "## Usage Patterns"`

### Milestone v1.2 Lifecycle Cleanup (Phase 9.1.1)

Gap-closure requirements identified by `/gsd-audit-milestone` on 2026-04-16 and tracked by Phase 9.1.1. All three are planning-artifact work — no graphify code touched.

- [x] **v1.2-REQ-9.1.1-A**: Generate missing `09.1-VERIFICATION.md` goal-backward report from existing UAT/VALIDATION/SECURITY evidence — Phase 09.1.1 Plan 01 — `.planning/phases/09.1-query-telemetry-usage-weighted-edges/09.1-VERIFICATION.md`
- [x] **v1.2-REQ-9.1.1-B**: Create project-level `.planning/REQUIREMENTS.md` registering the 7 derived v1.2 REQ-IDs with phase traceability — Phase 09.1.1 Plan 02 — `.planning/REQUIREMENTS.md`
- [x] **v1.2-REQ-9.1.1-C**: Reconcile v1.2 scope contradictions across `ROADMAP.md`, `STATE.md`, and `PROJECT.md` to the narrow-scope shape (phases 9 + 9.1 only); move phases 9.2, 10, 11, 12 into the v1.3 section — Phase 09.1.1 Plan 03 — `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/PROJECT.md`

## Traceability Matrix (v1.2)

| REQ ID | Description | Assigned Phase | Integration Path | Status |
|--------|-------------|----------------|------------------|--------|
| v1.2-REQ-09-A | Configurable analysis lenses with autoreason tournament (A/B/AB/Borda) | Phase 09 | skill.md:1324-1545 → analyze.py:456 → report.py:256 | satisfied |
| v1.2-REQ-09-B | "No finding" competes as first-class Borda option | Phase 09 | skill.md:1502 + :1526 → Clean verdict | satisfied |
| v1.2-REQ-09-C | GRAPH_ANALYSIS.md separate from GRAPH_REPORT.md (D-80) | Phase 09 | skill.md:1546 writes GRAPH_ANALYSIS.md; no overlap with GRAPH_REPORT.md | satisfied |
| v1.2-REQ-09.1-A | Per-edge traversal counters via MCP query telemetry | Phase 09.1 | serve.py:630 → :642 → :643 | satisfied |
| v1.2-REQ-09.1-B | Strengthen hot paths, decay unused | Phase 09.1 | serve.py:110; skill.md:439, 999 | satisfied |
| v1.2-REQ-09.1-C | 2-hop A→C derived edge with INFERRED confidence | Phase 09.1 | serve.py:644 → :163/:164/:166/:173 | satisfied |
| v1.2-REQ-09.1-D | Hot/cold paths surfaced in GRAPH_REPORT.md | Phase 09.1 | skill.md:429/:433 → report.py:16 → :219 | satisfied |
| v1.2-REQ-9.1.1-A | Generate missing 09.1-VERIFICATION.md | Phase 09.1.1 | .planning/phases/09.1-.../09.1-VERIFICATION.md | satisfied |
| v1.2-REQ-9.1.1-B | Create project-level REQUIREMENTS.md | Phase 09.1.1 | .planning/REQUIREMENTS.md | satisfied |
| v1.2-REQ-9.1.1-C | Reconcile v1.2 scope across ROADMAP/STATE/PROJECT | Phase 09.1.1 | .planning/ROADMAP.md, STATE.md, PROJECT.md | satisfied |

**Totals:** 10/10 in-scope requirements satisfied (7 derived v1.2 from phases 9 + 9.1, plus 3 gap-closure REQ-IDs from phase 9.1.1).

## Deferred to v1.3 (and beyond)

Requirements originally listed under v1.2 in ROADMAP.md but moved out during the narrow-scope reconciliation. See `.planning/ROADMAP.md` v1.3 section for the new home.

- [ ] **v1.3-REQ-09.2** (Progressive Graph Retrieval): Token-aware 3-layer MCP responses — Phase 9.2
- [ ] **v1.3-REQ-10** (Cross-File Semantic Extraction): Cluster-batched extraction for cross-file relationship capture — Phase 10
- [ ] **v1.3-REQ-11** (Narrative Mode): Codebase walkthrough generation — Phase 11
- [ ] **v1.3-REQ-12** (Heterogeneous Extraction Routing): Complexity-based model routing — Phase 12

These carry over placeholder REQ-IDs that will be refined when `/gsd-new-milestone v1.3` instantiates the milestone.

## Carried forward from v1.0 / v1.1 (still deferred)

Template-engine extensions and config-composition features deferred at v1.0 exit, still not in scope for any shipped milestone:

- [ ] **TMPL-01**: Conditional template sections (`{{#if_god_node}}...{{/if}}` guards)
- [ ] **TMPL-02**: Loop blocks for connections in templates (`{{#connections}}...{{/connections}}`)
- [ ] **TMPL-03**: Custom Dataview query templates per note type in profile
- [ ] **CFG-02**: Profile includes/extends mechanism (compose profiles from fragments)
- [ ] **CFG-03**: Per-community template overrides

---

*Last updated: 2026-04-15 — v1.2 requirements registered post-hoc during Phase 9.1.1 milestone audit gap closure. Next update: `/gsd-complete-milestone v1.2` will archive this block to `.planning/milestones/v1.2-REQUIREMENTS.md` and reset active requirements to whatever `/gsd-new-milestone v1.3` produces.*
