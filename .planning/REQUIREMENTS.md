# Requirements — Milestone v1.9 — Onboarding, Harness Portability & Vault CLI

Scoped from `/gsd-new-milestone` input and seeds `SEED-001`, `SEED-002`, `SEED-vault-root-aware-cli`. Phase numbering continues after v1.8 (Phase 38 → Phases 39–41).

---

## Tacit-to-explicit onboarding & elicitation

### ELIC-01 — Guided hybrid interview entry surface

**Goal:** Users can run a deterministic, testable elicitation interview (scripted backbone + optional deepening) from the canonical CLI path; platform skills delegate to that path without duplicating logic.

**Acceptance criteria:**

1. A documented primary CLI invocation (e.g. `graphify elicit …`) exercises the same library functions that any skill wrapper calls (per D-01).
2. The scripted backbone covers the SEED-001 dimensions: rhythms, decisions, dependencies, tacit knowledge, and friction, with explicit confirm-before-persist checkpoints.
3. Optional LLM deepening is gated (flag and/or env) and is not required for baseline tests (per D-03).

---

### ELIC-02 — Validated extraction-shaped graph input

**Goal:** Elicited answers become `nodes` / `edges` dicts that satisfy `graphify.validate.validate_extraction` before graph assembly.

**Acceptance criteria:**

1. For a representative fixture session, `validate_extraction(elicitation_dict)` returns no schema errors.
2. Elicitation-fed data reaches `build.build()` / `build.build_from_json()` only after validation (or with the same warning policy as other extraction merges for dangling edges).
3. Elicitation is integrated via a persisted sidecar (or bundle) merged in `build` with explicit ordering/dedup rules (per D-06).

---

### ELIC-03 — Harness-aligned artifacts (SOUL / HEARTBEAT / USER)

**Goal:** Outputs remain compatible with Phase 13 harness shapes: either direct markdown from elicitation state (fast path) or `export_claude_harness`-compatible snapshots under `graphify/harness_schemas/claude.yaml` when a graph bundle exists (per D-04).

**Acceptance criteria:**

1. When a graph JSON + sidecars exist, `graphify harness export` (or shared `export_claude_harness`) can consume elicitation-enriched data without ad-hoc template forks.
2. When no graph exists yet, elicitation can still emit SOUL/HEARTBEAT/USER-class files whose structure matches schema placeholders (filenames and section intent per `claude.yaml`).
3. Labels and paths pass through existing sanitization (`security.py` and harness annotation allow-lists as applicable).

---

### ELIC-04 — Idempotent re-run behavior

**Goal:** Re-running elicitation does not duplicate nodes/edges without an explicit merge, replace, or preview strategy.

**Acceptance criteria:**

1. Behavior is documented (README fragment, `docs/…`, or CLI `--help`) describing default merge vs overwrite vs preview.
2. At least one `tmp_path` test proves duplicate suppression or preview gating for a second run against the same target bundle.

---

### ELIC-05 — Path confinement

**Goal:** All writes from elicitation stay inside approved roots resolved the same way as the rest of the pipeline (`validate_graph_path` / `ResolvedOutput.artifacts_dir` patterns).

**Acceptance criteria:**

1. Attempted escape paths (e.g. `..` components, symlinks outside root where tests simulate) fail closed with clear errors.
2. Default artifact locations use vault-resolved `artifacts_dir` when `resolve_output()` applies (per D-05).

---

### ELIC-06 — Offline unit test coverage

**Goal:** Core state machine, validation, and merge behaviors are covered without network calls.

**Acceptance criteria:**

1. `tests/test_elicit.py` (or split per module) runs under `pytest` with no external API usage.
2. CI-matching commands (`pytest tests/… -q`) document the minimum elicitation test entrypoints in PLAN verification blocks.

---

### ELIC-07 — Discovery-first documentation

**Goal:** A dedicated doc explains when elicitation fits (empty/tiny corpus, onboarding) versus full corpus extraction (per D-02, D-08).

**Acceptance criteria:**

1. A non-README primary file (e.g. `docs/ELICITATION.md`) links from CLI help or top-level docs index where appropriate.
2. The doc states prerequisites (vault/profile if required), output locations, and how elicitation data joins the graph via sidecar merge.

---

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
