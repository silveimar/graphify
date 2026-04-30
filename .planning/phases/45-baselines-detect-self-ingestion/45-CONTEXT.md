# Phase 45: Baselines & Detect Self-Ingestion - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

**Roadmap baseline:** CI/hygiene for detect + collect-files + self-ingestion (**HYG-01..03**), quick task **`260427-rc7-fix-detect-self-ingestion`**.

**Expanded scope (locked in discuss-phase):** `.graphify/` corpus policy with profile-driven include/exclude, hard exclusion of YAML/profile/config artifacts from ingestion, **profile persistence** so `.graphify` metadata stays in sync after detect (CLI/`doctor`/detect-side updates — planner chooses wiring). Planner MUST reconcile this expansion with `.planning/ROADMAP.md` Phase 45 wording and `.planning/REQUIREMENTS.md` if new REQ IDs are needed.

</domain>

<decisions>
## Implementation Decisions

### Self-ingestion & manifest (HYG-01)

- **D-45.01:** When files are skipped due to **`output-manifest.json`** (`prior_files`), emit a **one-line stderr summary** (count + pointer to doctor/dry-run for detail), instead of purely silent skips.
- **D-45.02:** Load **manifest-based skips from default `graphify-out`** under the corpus root when **`resolved` is None**, not only when profile **`ResolvedOutput`** is present — stronger cross-run protection for non-vault runs.
- **D-45.03:** **Always skip** any path ever recorded in the output manifest (even after profile output destination changes). Accept tradeoff: legitimate reuse of old output folders may hide files until manifest/manually cleared — document for operators.

### `.graphify/` corpus & profile sync

- **D-45.04:** Add a **root-level profile section** (under `.graphify` / vault adapter config) for **include/exclude globs or paths** governing what under `.graphify/` may enter the corpus.
- **D-45.05:** **Always exclude** ingestion of YAML profile files and standard config filenames (exact list planner defines; minimum: `profile.yaml` and obvious config stubs).
- **D-45.06:** After detect observes **new eligible files** under `.graphify/` (per include rules), **update the profile section** that tracks discovered paths — user-facing option to **apply updates vs ignore** and optional **auto-update** behavior (full Phase 45 deliverable per user).

### Dotfiles / path contracts (HYG-02)

- **D-45.07:** Tests evolve to **dual guarantees**: **pathlib/part-based** hidden and canonical checks aligned with walk semantics **plus** documented **POSIX-relative string contract** for serialized paths used in graphs/manifests.

### `collect_files` vs `detect` parity (HYG-03)

- **D-45.08:** Introduce a **shared corpus-eligibility primitive** (single source of truth for skip/prune/manifest/graphifyignore/nested-output behavior) consumed by **`detect()`** and **`collect_files()`** so extraction cannot diverge from discovery rules when given equivalent roots/`resolved`.

### Regression surface

- **D-45.09:** **Hybrid testing**: keep detailed edge cases as **`tmp_path`** tests; add **one golden fixture vault** (mini vault with `.graphify/`, manifests, nested outputs) for integration smoke.

### Claude's Discretion

- Exact stderr wording for D-45.01; schema field names for `.graphify` include/exclude; manifest retention/`_OUTPUT_MANIFEST_MAX_RUNS` interaction with D-45.03 (ensure behavior is coherent); placement of shared walker module (`detect.py` vs new internal module).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning & requirements

- `.planning/ROADMAP.md` — Phase 45 goal, success criteria, milestone v1.10 context (**may need amendment** for expanded `.graphify`/profile-sync scope).
- `.planning/REQUIREMENTS.md` — **HYG-01**, **HYG-02**, **HYG-03** (+ any new IDs if scope is formally tracked).
- `.planning/PROJECT.md` — v1.10 milestone narrative.
- `.planning/STATE.md` — baseline test pointers (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`).

### Code (implementation anchors)

- `graphify/detect.py` — `detect()`, `_SELF_OUTPUT_DIRS`, `_load_output_manifest`, nesting/manifest/`skipped` telemetry, memory tree inclusion.
- `graphify/extract.py` — `collect_files()`, extension lists, `.graphifyignore`.
- `graphify/doctor.py` — `_compute_would_self_ingest`, ignore-list construction (alignment with user-visible warnings).
- `graphify/output.py` — `ResolvedOutput`, artifacts anchor for manifests.

### Patterns

- `.planning/codebase/TESTING.md` — pytest conventions, fixture layout.
- `.planning/codebase/ARCHITECTURE.md` — pipeline stages and data flow.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`detect()`** already implements nested-output pruning, manifest prior-files skip, **`skipped`** buckets (`noise-dir`, `exclude-glob`, `nesting`, `manifest`), and **`graphify-out/memory/`** allow-list.
- **`collect_files`** already respects **`.graphifyignore`** and hidden path skips but **not** `resolved`/nested-output/manifest — shared walker closes this gap per **D-45.08**.
- **`doctor`** already reasons about self-ingestion (`_compute_would_self_ingest`) — align messaging with new manifest stderr summary (**D-45.01**).

### Established Patterns

- Manifest IO: **`output-manifest.json`** under **`artifacts_dir`**; versioning and max runs constants in **`detect.py`**.
- Phase 28/29 skip telemetry: **`skipped`** dict + overflow caps — extend consistently when adding stderr summaries.

### Integration Points

- CLI **`run_corpus`** path resolves **`resolved`** before **`detect()`** — **`collect_files`** call sites must thread **`resolved`** when shared walker requires it.
- Profile loader **`graphify/profile.py`** — schema extension for `.graphify` include/exclude + persistence (**D-45.04..06**).

</code_context>

<specifics>
## Specific Ideas

- User intent: `.graphify/` is partly **configuration**, partly optional **content**; YAML/profile files never treated as corpus documents; operators can **opt in** markdown or other files via profile rules and keep profile metadata updated after detection.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 46+:** Typed concept↔code edges (**CCODE-*** — explicitly out of Phase 45 scope except avoiding contradictory detect contracts).

---

*Phase: 45-Baselines & Detect Self-Ingestion*
*Context gathered: 2026-04-30*
