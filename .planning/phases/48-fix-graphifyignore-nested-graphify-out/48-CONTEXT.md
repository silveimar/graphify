# Phase 48: fix-graphifyignore-nested-graphify-out - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

**Roadmap baseline:** `.graphifyignore` patterns must **match how nested `graphify-out/` paths are surfaced** so graphify **stops prompting** to add ignores that are **already declared**. Runs must **not sprawl** additional nested `graphify-out/` trees under arbitrary corpus subtrees when a **canonical per-run output root** exists (`ResolvedOutput.artifacts_dir` / default top-level `graphify-out/`), with **regression tests** and documented behavior.

**Depends on:** Phase 45 (detect / corpus eligibility semantics, shared walker / `collect_files` parity — **D-45.08**).

**Explicitly later:** Phase 49 (CLI `--version` / package vs skill version echo); Phase 47 (MCP/trace — already notes Phase 48 as deferral).

</domain>

<decisions>
## Implementation Decisions

### Ignore diagnostics vs declared patterns

- **D-48.01:** If a path is **already excluded** by effective `.graphifyignore` + profile `exclude_globs` semantics (same rules as **`_is_ignored` / shared corpus eligibility**), **do not** recommend appending duplicate patterns (e.g. skill or doctor text suggesting `graphify-out/**` when `**/graphify-out/**` or equivalent already covers nested outputs). Hints appear only when ingestion would still occur without a change.
- **D-48.02:** **Equivalence class for "covers nested output":** matching must honor **gitignore-style** patterns already documented in **`detect._load_graphifyignore`** / **`_is_ignored`** (root-relative, segment, basename). Do not require one canonical spelling in `.graphifyignore` if several spellings already exclude the tree.

### Canonical output root

- **D-48.03:** **All new artifact writes** use the resolved canonical output root (`ResolvedOutput.artifacts_dir` / notes dir contract). **Do not** create or rely on **new** nested `graphify-out/` directories under raw corpus subtrees when configuration provides a single canonical root; planner locates call sites (CLI `run_corpus`, exporters, manifest writers).
- **D-48.04:** **On-disk legacy** nested `graphify-out/` trees: **warn + document** only — **no automatic deletion** of user data; doctor or stderr may surface coexistence with canonical root (planner chooses UX).

### Shared primitive & tests

- **D-48.05:** Extend the **Phase 45 shared corpus-eligibility / ignore alignment** so **detect**, **`collect_files`**, **`doctor`** (`_compute_would_self_ingest`, ignore-list / fix hints), and any **agent-facing prompts** share predicates for “nested output excluded” vs “still ingestible” (**D-45.08** family — avoid divergent heuristics).
- **D-48.06:** **Regression tests** (pytest, `tmp_path`): (1) fixture with `.graphifyignore` already excluding nested graphify output — assert **no** duplicate-ignore recommendation / stable diagnostics; (2) fixture or trace asserting **no new nested** `graphify-out/` sprawl under configured canonical root; (3) document expected behavior in **`CLAUDE.md`** or **`docs/`** as appropriate (planner picks minimal doc touchpoints).

### Requirements traceability

- **D-48.07:** Map roadmap success criteria to **explicit REQ rows** in **`.planning/REQUIREMENTS.md`** (new IDs — planner proposes, e.g. output hygiene bucket) and reference them from PLAN frontmatter.

### Claude's Discretion

- Module placement for shared predicates (`corpus_prune.py` vs `detect.py` vs small new helper).
- Exact stderr / doctor line wording; caps on how many example paths to show.
- Whether to add a one-time migration note in **`graphify/skill*.md`** vs docs-only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning & milestone

- `.planning/ROADMAP.md` — Phase 48 goal, success criteria, Depends on Phase 45.
- `.planning/REQUIREMENTS.md` — **HYG-01..03** (Phase 45); new rows for Phase 48 per **D-48.07**.
- `.planning/PROJECT.md` — v1.10 stability / hygiene narrative.
- `.planning/phases/45-baselines-detect-self-ingestion/45-CONTEXT.md` — **D-45.01–09**, especially **D-45.08** shared walker / parity.
- `.planning/phases/47-mcp-trace-integration/47-CONTEXT.md` — explicitly defers `.graphifyignore` / nested output to Phase 48.

### Code (anchors)

- `graphify/detect.py` — `_load_graphifyignore`, `_is_ignored`, `detect()`, nested output pruning, `build_prior_files`, `skipped` telemetry.
- `graphify/extract.py` — `collect_files(..., resolved=)`.
- `graphify/corpus_prune.py` — `dir_prune_reason`, shared prune/ignore helpers.
- `graphify/doctor.py` — `_compute_would_self_ingest`, `_build_ignore_list`, fix-hint strings, `would_self_ingest` reporting.
- `graphify/output.py` — `resolve_output`, `ResolvedOutput`, `artifacts_dir`.
- `graphify/__main__.py` — corpus run / output resolution wiring.

### Conventions

- `.planning/codebase/ARCHITECTURE.md` — pipeline stages.
- `.planning/codebase/TESTING.md` — pytest / fixture conventions.
- `CLAUDE.md` — build/test commands if doc updates reference CI.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`detect._is_ignored` / `_load_graphifyignore`** — authoritative glob matching today; Phase 48 should not fork a second matching engine for “already ignored?” checks.
- **`corpus_prune.dir_prune_reason`** — directory-level prune reasons; may compose with ignore-aware “nested output” checks.
- **`doctor._build_ignore_list` + `_compute_would_self_ingest`** — where user-visible ignore/self-ingest guidance is built; align with detect/extract.
- **`ResolvedOutput`** — canonical artifact/note destinations for consolidation behavior.

### Established patterns

- **`skipped`** buckets and stderr summaries (Phase 28/29/45) — extend consistently if new diagnostic lines are added.
- **Phase 45 `collect_files` / `detect` parity** — any new rule for ignores or nested output must apply in both paths.

### Integration points

- CLI paths that call **`resolve_output`** then **`detect()`** / **`collect_files`** — thread consistent `resolved` and shared predicates.
- **Skill / harness** strings that suggest `.graphifyignore` edits — must call the same “already covered” logic as doctor where feasible.

</code_context>

<specifics>
## Specific Ideas

- Roadmap examples: patterns like `**/graphify-out/**` must satisfy success criterion 1 without redundant prompts.
- Success criterion 2: single canonical output directory configuration prevents sprawl; tests should lock the contract.

</specifics>

<deferred>
## Deferred Ideas

- **None** — discussion stayed within Phase 48 scope.

</deferred>

---

*Phase: 48-fix-graphifyignore-nested-graphify-out*
*Context gathered: 2026-04-30*
