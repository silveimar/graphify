# Requirements — Milestone v1.9 — Onboarding, Harness Portability & Vault CLI

Scoped from `/gsd-new-milestone` input and seeds `SEED-001`, `SEED-002`, `SEED-vault-root-aware-cli`. Phase numbering continues after v1.8 (Phase 38 → Phases 39–41).

---

## Tacit-to-explicit onboarding & elicitation

- [ ] **ELIC-01**: User can complete a guided elicitation flow (CLI entrypoint and/or documented skill orchestration) structured around rhythms, decisions, dependencies, tacit knowledge, and friction, with confirm-before-save checkpoints.
- [ ] **ELIC-02**: Elicitation persists answers into extraction-compatible graph data (`nodes`/`edges`) that passes `validate.validate_extraction` before `build_graph()`.
- [ ] **ELIC-03**: Elicitation emits portable harness-facing artifacts (at minimum SOUL.md, HEARTBEAT.md, USER.md — paths configurable or profile-relative) using existing label/path sanitization.
- [ ] **ELIC-04**: Re-running elicitation against the same target does not spam duplicates without an explicit merge or preview strategy (documented behavior + tests).
- [ ] **ELIC-05**: All elicitation-written paths stay within approved output roots per `security.py` patterns.
- [ ] **ELIC-06**: Pure unit tests cover the elicitation flow core with fixtures (no network).
- [ ] **ELIC-07**: Project docs explain when to use elicitation versus corpus-based extraction.

## Multi-harness memory & inverse import

- [ ] **PORT-01**: Harness export supports at least one additional first-class target beyond existing Claude-oriented export (e.g. Codex/AGENTS-shaped bundles), with mappings documented in-repo.
- [ ] **PORT-02**: Canonical harness mapping artifacts live under version control (e.g. `graphify/harness_schemas/` YAML or Markdown tables) and are referenced by export/import code.
- [ ] **PORT-03**: `graphify import-harness` ingests supported harness memory files into validated extraction dicts suitable for `build_graph()` (no validation bypass).
- [ ] **PORT-04**: Fixture-based tests demonstrate export→import round-trip preservation within documented limits.
- [ ] **PORT-05**: Import enforces path confinement, size caps, and rejects traversal consistent with `security.py`.

## Prompt-injection & trust boundaries

- [ ] **SEC-01**: Imported harness content is normalized/sanitized against prompt-injection gadgets before influencing graph merge or template expansion (tests cover representative vectors).
- [ ] **SEC-02**: Exported harness bundles include provenance fields (run identity / timestamp / schema version) where they fit the format.
- [ ] **SEC-03**: MCP entry points for harness import/export use the same validation and sanitization as CLI.
- [ ] **SEC-04**: `SECURITY.md` documents harness import/export threats and mitigations for this release.

## Vault-root CLI surface

- [ ] **VCLI-01**: Explicit `--vault <path>` selects the Obsidian vault root with deterministic precedence relative to CWD detection (documented).
- [ ] **VCLI-02**: User can select among multiple discovered vaults via a documented mechanism (minimal selector — env, `--vault-list` file, or interactive prompt gated for CI).
- [ ] **VCLI-03**: `graphify doctor` reflects resolved `--vault`/selector choice consistently with output resolution.
- [ ] **VCLI-04**: Dry-run / preview paths show resolved vault + output + skip reasons aligned with v1.7–v1.8 behavior.
- [ ] **VCLI-05**: Unit tests cover `--vault` precedence and selector edge cases using `tmp_path` only.
- [ ] **VCLI-06**: README or CLI help summarizes vault selection for scripting users.

---

## Future / deferred

- Full parity with every external harness proprietary format — defer until demand; v1.9 ships documented extensions only.
- **Baseline test failures** (`tests/test_detect.py::test_detect_skips_dotfiles`, `tests/test_extract.py::test_collect_files_from_dir`) remain a **`/gsd-debug`** track unless promoted explicitly later.

## Out of scope (v1.9)

- Designing third-party Obsidian plugins or `.obsidian/graph.json` write-back (still per D-74 stance unless a future milestone reopens).
- Neo4j / non-Obsidian exporters.

---

## Traceability (requirement → phase)

| REQ-ID   | Phase | Title (abbrev) |
|----------|-------|----------------|
| ELIC-01–07 | 39 | Tacit-to-explicit onboarding & elicitation |
| PORT-01–05, SEC-01–04 | 40 | Multi-harness memory, inverse import, injection defenses |
| VCLI-01–06 | 41 | Explicit `--vault` & multi-vault selector |
