# Requirements: Milestone v1.10 — Stability, Baselines & Concept↔Code MVP

**Project:** graphify — Ideaverse Integration (configurable vault adapter)  
**Source context:** `.planning/PROJECT.md`, carryovers from v1.9 close (`STATE.md`), **SEED-bidirectional-concept-code-links** (scoped MVP, not full seed vision unless phased).

## v1.10 — Hygiene & baseline correctness

- [ ] **HYG-01:** Quick-task **`260427-rc7-fix-detect-self-ingestion`** is implemented: detect no longer mis-handles self-ingestion scenarios covered by the task; regression tests prove the fix.
- [ ] **HYG-02:** `tests/test_detect.py::test_detect_skips_dotfiles` passes **or** the contract is intentionally revised with tests and docs updated (no silent behavior drift).
- [ ] **HYG-03:** `tests/test_extract.py::test_collect_files_from_dir` passes **or** collect-files semantics are explicitly reconciled with documented expectations and tests.

## v1.10 — Concept↔code graph MVP (SEED-bidirectional scope)

- [ ] **CCODE-01:** **Schema:** New edge relation type(s) for concept↔code linkage are accepted by `validate.py` and documented (confidence semantics align with EXTRACTED / INFERRED / AMBIGUOUS).
- [ ] **CCODE-02:** **Build:** Concept↔code edges merge into the NetworkX graph deterministically and survive `graph.json` export/import assumptions used elsewhere (fixture-backed tests).
- [ ] **CCODE-03:** **MCP:** At least one MCP tool or structured query path lists or traverses concept↔implementation edges; capability/manifest/skill docs updated if surface area changes.
- [ ] **CCODE-04:** **Trace:** `/trace` (slash) **or** `entity_trace` MCP uses typed concept↔code hops in at least one golden-path scenario with automated coverage.
- [ ] **CCODE-05:** **Security:** All new labels/paths pass through existing sanitization patterns (`security.py`); no injection regressions in templates or MCP payloads.

## Future (not v1.10)

- Full multi-repo concept identity federation, autoreason predicates over “is implementation of,” and rich drift graphs — **defer** unless pulled into a later milestone explicitly.

## Out of scope (v1.10)

- Rewriting Obsidian frontmatter export beyond what is needed to emit/consume the new edge type(s).
- Neo4j or non-Obsidian exporters for concept↔code (same as project-wide Obsidian focus).

## Traceability

| REQ-ID | Phase | Plan / notes |
|--------|-------|--------------|
| HYG-01 — | — | Set by roadmap (`/gsd-plan-phase`) |
| HYG-02 — | — | |
| HYG-03 — | — | |
| CCODE-01 — | — | |
| CCODE-02 — | — | |
| CCODE-03 — | — | |
| CCODE-04 — | — | |
| CCODE-05 — | — | |
