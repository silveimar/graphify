# Phase 39: tacit-to-explicit-onboarding-elicitation - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **tacit-to-explicit onboarding and elicitation**: a guided interview/state machine that produces validated graph-relevant output and **SOUL / HEARTBEAT / USER**-class artifacts (aligned with existing harness export shapes), plus documentation for discovery-first workflows. Uses existing `validate`, `build`, and `security` layers. Does not own Phase 40 harness import defenses or Phase 41 vault CLI flags — only interfaces that must stay stable should be named early for those phases.

</domain>

<decisions>
## Implementation Decisions

### Entry surface
- **D-01:** **CLI is canonical** for behavior and tests; **skill** is a thin wrapper that invokes the same library/CLI path (not a divergent implementation).
- **D-02:** Elicitation should be **emphasized when the corpus is empty or tiny** (onboarding path), not as a constant parallel funnel for every full-corpus run.

### Interview engine
- **D-03:** **Hybrid interview:** a **deterministic scripted backbone** (predictable state machine, strong testability) plus an **optional LLM deepening** step (e.g. flag or env — exact wiring is planner discretion). No “LLM-only” mode for the baseline MVP unless explicitly added later.

### Output wiring (artifacts)
- **D-04:** Support **both** artifact paths where appropriate: **direct** rendering from elicitation state for early/MVP speed, and **reuse of existing harness export** (`harness export` + schemas) when a graph snapshot or merged state exists — shapes must stay compatible with **Phase 13 / `claude.yaml`** over time.
- **D-05:** Default output location: **vault-resolved** paths when vault context is available (profile / `ResolvedOutput` / v1.7 routing patterns), not “graphify-out only” as the sole story for Phase 39.

### Graph ingestion
- **D-06:** Elicited facts enter the pipeline via a **JSON sidecar (or equivalent persisted bundle)** merged into the graph in **`build`** with **explicit merge rules**, rather than only pretending elicitation came from `extract()` as normal file extraction. (Planner details schema for sidecar + merge stage; may still emit extraction-shaped dicts internally if helpful.)

### Requirements traceability & documentation
- **D-07:** Add **numbered ELIC requirements** to `.planning/REQUIREMENTS.md` **before or as the first concrete planning commitment** for Phase 39 — not “CONTEXT-only” without REQ IDs.
- **D-08:** Ship a **new dedicated documentation file** for discovery-first / elicitation workflows (path and name per planner; not “README-only” for this phase).

### Claude's Discretion
- Exact CLI spelling (`elicit` vs subcommand nesting), flag names for LLM deepening, sidecar filename/layout, and merge hook placement (module boundaries) are left to research + planner within the decisions above.
- Exact vault-relative paths under profile defaults — follow existing `ResolvedOutput` / export routing conventions unless CONTEXT is updated.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase & milestone
- `.planning/ROADMAP.md` — Phase 39 goal, v1.9 milestone, dependencies to Phase 40/41.
- `.planning/PROJECT.md` — v1.9 themes (SEED-001/002, onboarding).
- `.planning/STATE.md` — Current milestone position.

### Seeds & prior art (intent)
- `.planning/seeds/SEED-001-tacit-knowledge-elicitation-engine.md` — Interview layers (rhythms, decisions, dependencies, knowledge, friction), artifact vision.
- `.planning/seeds/SEED-002-harness-memory-export.md` — SOUL/HEARTBEAT/USER portability; dependency note on elicitation feeding export.

### Existing harness export (reuse targets)
- `graphify/harness_export.py` — Export pipeline from graph/sidecars.
- `graphify/harness_schemas/claude.yaml` — Block definitions / placeholders for harness markdown.
- `tests/test_harness_export.py` — Behavioral contracts for harness outputs.

### Recent phase contracts (vault/output discipline)
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-CONTEXT.md` — Vault safety, skill alignment, regression posture (carry-forward discipline).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`graphify harness export`** and **`harness_schemas/claude.yaml`** — Template and placeholder model for SOUL/HEARTBEAT/USER-shaped files; elicitation output should converge here when the graph path is used.
- **`validate.py` / `build.py` / `security.py`** — Validation and merge must stay confined and schema-safe; sidecar merge should reuse sanitization patterns.

### Established patterns
- **Deterministic + optional LLM** elsewhere in graphify — mirror “cheap core + optional semantic layer” for hybrid elicitation.
- **Vault-relative output** — v1.7 `ResolvedOutput` / profile-driven routing should drive default artifact placement when a vault is resolved.

### Integration points
- **CLI:** `graphify/__main__.py` command dispatch — new `elicit` (or grouped) entry.
- **Skill:** platform skill files — thin wrapper only per **D-01**.
- **Build pipeline:** merge elicitation sidecar after or alongside extraction merge in **`build`** (planner specifies ordering and dedup).

</code_context>

<specifics>
## Specific Ideas

- Onboarding emphasis when **corpus is empty or tiny** — docs and CLI help should reflect that path clearly.
- **Requirements-first:** ELIC IDs land in **REQUIREMENTS.md** before implementation momentum.

</specifics>

<deferred>
## Deferred Ideas

- Phase **40** — Multi-harness memory, inverse import, injection defenses (full scope).
- Phase **41** — `--vault` / multi-vault selector productization beyond what Phase 39 needs for routing defaults.
- Pure LLM-led interview without a scripted backbone — not chosen for MVP (**D-03**).

</deferred>

---

*Phase: 39-tacit-to-explicit-onboarding-elicitation*
*Context gathered: 2026-04-29*
