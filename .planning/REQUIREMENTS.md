# Requirements: Milestone v1.10 — Stability, Baselines & Concept↔Code MVP

**Project:** graphify — Ideaverse Integration (configurable vault adapter)  
**Source context:** `.planning/PROJECT.md`, carryovers from v1.9 close (`STATE.md`), **SEED-bidirectional-concept-code-links** (scoped MVP, not full seed vision unless phased).

## v1.10 — Hygiene & baseline correctness

- [ ] **HYG-01:** Quick-task **`260427-rc7-fix-detect-self-ingestion`** is implemented: detect no longer mis-handles self-ingestion scenarios covered by the task; regression tests prove the fix. Includes **`graphify/corpus_prune`** shared pruning/manifest **`prior_files`** (default-root **`graphify-out`** manifest when `resolved is None`), manifest skip summary **stderr**, **`collect_files(..., resolved=)`** parity with **`detect()`**, optional **`corpus.dot_graphify`** profile policy for **`.graphify/`** corpus paths (YAML/profile hard-excluded), and **`doctor --dot-graphify-track`** / **`--apply-dot-graphify-track`** plus vault **`auto_track_discoveries`** write-back.
- [ ] **HYG-02:** `tests/test_detect.py::test_detect_skips_dotfiles` passes **or** the contract is intentionally revised with tests and docs updated (no silent behavior drift).
- [ ] **HYG-03:** `tests/test_extract.py::test_collect_files_from_dir` passes **or** collect-files semantics are explicitly reconciled with documented expectations and tests.
- [x] **HYG-04:** Diagnostics and agent/doctor prompts **do not** ask for `.graphifyignore` entries that duplicate coverage: if nested `graphify-out` paths are already excluded by effective ignore patterns (same semantics as `detect` / `collect_files`), no boilerplate “add `graphify-out/**`” fix — Phase 48 (2026-04-30).
- [x] **HYG-05:** New runs use the **canonical** `ResolvedOutput.artifacts_dir` / per-run output root and **do not** sprawl additional nested `graphify-out/` trees under corpus subtrees when configured; behavior documented with regression tests — Phase 48 (2026-04-30).

## v1.10 — Concept↔code graph MVP (SEED-bidirectional scope)

- [x] **CCODE-01:** **Schema:** New edge relation type(s) for concept↔code linkage are accepted by `validate.py` and documented (confidence semantics align with EXTRACTED / INFERRED / AMBIGUOUS). — Phase 46 (2026-04-30)
- [x] **CCODE-02:** **Build:** Concept↔code edges merge into the NetworkX graph deterministically and survive `graph.json` export/import assumptions used elsewhere (fixture-backed tests). — Phase 46 (2026-04-30)
- [ ] **CCODE-03:** **MCP:** At least one MCP tool or structured query path lists or traverses concept↔implementation edges; capability/manifest/skill docs updated if surface area changes.
- [ ] **CCODE-04:** **Trace:** `/trace` (slash) **or** `entity_trace` MCP uses typed concept↔code hops in at least one golden-path scenario with automated coverage.
- [x] **CCODE-05:** **Security:** All new labels/paths pass through existing sanitization patterns (`security.py`); no injection regressions in templates or MCP payloads. — Phase 46 (2026-04-30)

## v1.10 — CLI version & provenance (Phase 49)

- [x] **CLI-VER-01:** `graphify --version` and `graphify -V` print a single stdout line (`graphify <version>`) and exit **0** without running skill-version sidecar checks; `graphify.version.package_version()` is the single runtime reader for the `graphifyy` distribution version (with tests). — Phase 49 (2026-04-30)
- [x] **CLI-VER-02:** Successful non-install / non-subcommand-install CLI exits emit one stderr line `[graphify] version <version>`; skill `.graphify_version` mismatch warnings use directional copy (older vs newer stamp). — Phase 49 (2026-04-30)

## Future (not v1.10)

- Full multi-repo concept identity federation, autoreason predicates over “is implementation of,” and rich drift graphs — **defer** unless pulled into a later milestone explicitly.

## Out of scope (v1.10)

- Rewriting Obsidian frontmatter export beyond what is needed to emit/consume the new edge type(s).
- Neo4j or non-Obsidian exporters for concept↔code (same as project-wide Obsidian focus).

## Traceability

| REQ-ID | Phase | Plan / notes |
|--------|-------|--------------|
| HYG-01 | **45** | Quick task `260427-rc7-fix-detect-self-ingestion`; `corpus_prune`; manifest stderr; default-root manifest; `collect_files(resolved=)`; profile **`corpus.dot_graphify`** + doctor tracked_paths UX |
| HYG-02 | **45** | `test_detect_skips_dotfiles` fix or intentional contract change + docs |
| HYG-03 | **45** | `test_collect_files_from_dir` fix or reconciled semantics + docs |
| HYG-04 | **48** | Duplicate-suppression for graphifyignore hints vs effective patterns (`doctor` + shared predicate) |
| HYG-05 | **48** | Canonical output root; no nested `graphify-out` sprawl; tests + docs |
| CCODE-01 | **46** | `validate.py` + docs for relation type(s); confidence aligns with EXTRACTED/INFERRED/AMBIGUOUS |
| CCODE-02 | **46** | Deterministic merge + `graph.json` fixture round-trip parity |
| CCODE-05 | **46** | `security.py` for new labels/paths; MCP/template injection regressions |
| CCODE-03 | **47** | MCP listing/traversal; manifest/skill docs if surface changes |
| CCODE-04 | **47** | `/trace` or `entity_trace` golden-path + automated coverage |
| CLI-VER-01 | **49** | `--version` / `-V`; `graphify.version`; subprocess tests |
| CLI-VER-02 | **49** | Success footer; directional skill stamp warnings |
