# Requirements: Milestone v1.11

**Project:** graphify — Ideaverse Integration (configurable vault adapter)  
**Milestone:** v1.11 — Templates, Graph Semantics & Vault Depth  
**Research:** `.planning/research/SUMMARY.md` (2026-04-30)

## v1.11 Requirements

### Templates & profile presentation (TMPL)

- [ ] **TMPL-01**: Users can author **conditional template sections** in `.graphify/templates/` (profile-controlled predicates such as note type / god-node / simple flags) with expansion occurring **before** `${}` substitution; outputs pass through existing sanitization sinks.
- [ ] **TMPL-02**: Users can iterate **outbound/inbound connections** via a **`{{#connections}}…{{/connections}}`** (or equivalent documented block) with deterministic ordering and sanitized labels/targets.
- [ ] **TMPL-03**: Profile may declare **per-note-type Dataview query templates** validated at `validate_profile_preflight` time (schema + dead-rule checks).

### Profile overrides (CFG)

- [ ] **CFG-01**: Composed profiles support **scoped template overrides** (e.g., per-community or per-mapping-rule path documented in schema) without breaking `extends:` / `includes:` merge semantics from v1.7.
- [ ] **CFG-02**: Deterministic **validation errors** when override precedence is ambiguous (collision matrix documented in tests).

### Concept ↔ code graph semantics (CGRAPH)

- [ ] **CGRAPH-01**: `validate_extraction` accepts **new relation value(s)** for concept↔implementation edges with required fields and confidence rules aligned to existing edge schema.
- [ ] **CGRAPH-02**: `build` / merge preserves **concept↔code** edges with deterministic dedupe and stable IDs alongside existing structural edges.
- [ ] **CGRAPH-03**: MCP exposes **typed concept↔code hop/query** behavior consistent with v1.10 **`concept_code_hops`** and slash **`/trace`** expectations (documented mapping table in verification).
- [ ] **CGRAPH-04**: Obsidian **CODE / concept MOC** export does not contradict graph-level concept↔code edges (single source of truth from the graph).

### Elicitation & harness (ELIC / HARN)

- [ ] **ELIC-01**: At least **one additional scripted elicitation → extraction** scenario is covered by unit tests versus the v1.9 baseline (failure modes + happy path artifact shape).
- [ ] **ELIC-02**: `docs/ELICITATION.md` (or successor) states **trust boundaries**, artifact locations, and non-goals for this milestone.
- [ ] **HARN-01**: Harness export adds **documented canonical mapping + tests** for one incremental capability (e.g., additional target formatting **or** inverse-import remains off-default with explicit guard tests if touched).
- [ ] **HARN-02**: Any **import** entrypoint remains **off by default** and cannot write vault paths without explicit user-approved CLI/MCP semantics.

### Vault CLI & hygiene (VAUX / HYG)

- [ ] **VAUX-01**: **`--vault` / discovery** behavior matches **`graphify doctor`** reporting for equivalent inputs (golden tests or structured parity assertions).
- [ ] **VAUX-02**: Vault-related CLI failures produce **actionable messages** covered by pytest (unknown vault, ambiguous selection, dry-run mismatch).
- [ ] **HYG-01**: v1.10-close **quick-task / registry hygiene** item (`260427-rc7-fix-detect-self-ingestion` or successor slug) is **resolved or formally waived** with evidence in-planning (VERIFICATION note).

## Future (deferred past v1.11)

- Full **multi-harness inverse-import** parity across all platforms  
- **Bloom / TOKEN-04** performance caches (v1.3 deferral)  
- **Obsidian plugin** or `.obsidian/graph.json` writer inside `to_obsidian()` (D-74 still stands unless explicitly re-opened)

## Out of scope

- Replacing **`string.Template`** with Jinja2 or adding templating as a required dependency  
- Non-Obsidian export formats as mandatory work  
- Network calls in default CI tests  

## Traceability

| REQ-ID | Phase | Plan / notes |
|--------|-------|----------------|
| — | — | *(filled when ROADMAP.md is created)* |
