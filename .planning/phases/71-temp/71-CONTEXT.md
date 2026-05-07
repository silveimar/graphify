# Phase 71 CONTEXT — TEMP: Temporal Edge Validity

**Date:** 2026-05-07
**Milestone:** v2.0 Graph Schema Deepening
**Requirements:** TEMP-01, TEMP-02, TEMP-03, TEMP-04

<domain>
Edges carry complete temporal metadata (`valid_from`, `valid_until`, `decay_weight`); supersession stamps `valid_until` instead of silently dropping edges; `report.py` and `wiki.py` surface temporal health.
</domain>

<canonical_refs>
- `.planning/ROADMAP.md` — Phase 71 success criteria (lines 37–46)
- `.planning/REQUIREMENTS.md` — TEMP-01..TEMP-04 definitions (lines 15–18)
- `graphify/build.py` — `SCHEMA_VERSION = "1.13"` constant (line 37); to bump to `"2.0"`
- `graphify/validate.py` — Phase 65 read/write split precedent (lines 231–258); pattern to mirror for temporal fields
- `graphify/cache.py` — supersession detection integration point (re-run path)
- `graphify/export.py` — `schema_version` write path (line 331); JSON output of edges
- `graphify/report.py` — GRAPH_REPORT.md generation; Temporal Health subsection lands here
- `graphify/wiki.py` — per-community articles; Historical relations subsection lands here
- `.planning/codebase/ARCHITECTURE.md`, `STACK.md`, `CONVENTIONS.md` — existing structural maps consulted
</canonical_refs>

<prior_decisions>
- **Phase 65 (CCONF-05):** `schema_version` read/write split — read-mode tolerant of missing key, write-mode strict. Phase 71 mirrors this pattern for temporal fields.
- **Phase 70.2-02:** SCHEMA_VERSION single-source-of-truth lives in `build.py`. Bump touches one constant.
- **PyYAML** is currently in the optional `routing` extra (per CLAUDE.md / pyproject.toml). Phase 71 introduces a YAML config; planner must decide whether to promote PyYAML to a core dep or guard YAML loading behind try/except (preferred: guard, with sensible code defaults if config absent).
</prior_decisions>

<decisions>

### 1. Timestamp source & format (TEMP-01)
- **Format:** ISO8601 UTC wall-clock string per edge (e.g., `"2026-05-07T11:54:00+00:00"`).
- **Source:** `datetime.now(timezone.utc).isoformat()` evaluated once per build run; same value stamped on every edge produced or revalidated in that run.
- **Test determinism:** Provide an injectable clock or env-var override (e.g., `GRAPHIFY_RUN_TS`) so tests pin time deterministically. Researcher to pick the cleanest hook (function arg vs env var).
- **`valid_until`:** `null` for currently-valid edges; ISO8601 UTC string when superseded.

### 2. Decay function & config (TEMP-02)
- **Config file:** `graphify/temporal_config.yaml` (new file, package-shipped).
- **Schema (per relation):** `{function: exponential, half_life_days: <int>, floor: <float>}`. A `default:` entry covers unspecified relations.
- **Default function:** **Exponential half-life** — `weight = max(floor, 0.5 ** (age_days / half_life_days))`.
- **Default parameters:** `half_life_days: 30`, `floor: 0.1` (researcher may revise based on relation-type sensitivity research).
- **EXTRACTED edges:** always `decay_weight = 1.0`, regardless of age (TEMP-02 requirement).
- **Loading:** Config loaded once at build time. If PyYAML unavailable OR file missing, fall back to in-code defaults so core install still works without the `routing` extra.

### 3. Supersession detection (TEMP-03)
- **Match key:** Global `(source, target, relation)` tuple across the entire run.
- **Rule:** If a previously-INFERRED edge with this tuple is NOT produced by any source in the current run → stamp `valid_until` with the current run timestamp.
- **File deletion:** When a `source_file` is removed from the corpus, edges originally attributed to that file are stamped `valid_until` **unless** the same `(source, target, relation)` tuple is produced by another file in the current run (global rule wins).
- **Persistence:** Superseded edges remain on-disk in graph.json for history.
- **Scoring exclusion:** `analyze.py` god-node and surprising-connection scoring excludes edges with `valid_until != null` by default. Researcher to confirm exact predicate location(s).

### 4. Backward compatibility (cross-cutting)
- **Approach:** Read-tolerant, write-strict, mirroring Phase 65.
  - Read: missing `valid_from`/`valid_until`/`decay_weight` → treat as legacy; default `decay_weight` to `1.0`, `valid_from`/`valid_until` to `None`. No error.
  - Write: every new graph.json stamps all three fields on every edge.
- **SCHEMA_VERSION:** Bump from `"1.13"` to `"2.0"` in `graphify/build.py:37` as part of this phase.
- **Migration command:** Not in scope for Phase 71. Lazy on-read tolerance is sufficient for v2.0 ship; an explicit `graphify migrate` command is deferred (candidate for Phase 75 PKG or backlog).

### 5. Temporal Health rendering (TEMP-04)

**`report.py` — GRAPH_REPORT.md "Temporal Health" subsection (minimal):**
- Currently-valid edge count
- Superseded edge count (`valid_until != null`)
- Percentage superseded
- One short paragraph; no histogram, no timeline. (Richer rendering deferred to backlog.)

**`wiki.py` — per-community articles:**
- Currently-valid edges render in the main body as today.
- Superseded edges render in a separate `## Historical relations` subsection at the bottom of the article, each annotated with the `valid_until` date.
- Subsection omitted entirely when no superseded edges exist for the community.

</decisions>

<deferred>
- Decay-weight histogram, supersession timeline, top-N decayed relations table in GRAPH_REPORT.md (richer Temporal Health views) — backlog.
- Explicit `graphify migrate` CLI command for one-shot rewrite of pre-v2.0 graphs — candidate for Phase 75 PKG or backlog.
- Promoting PyYAML from `[routing]` extra to a core dependency — let researcher decide whether the temporal-config fallback (in-code defaults) is sufficient or whether YAML should be required.
</deferred>

<open_questions_for_researcher>
- Best test-time clock-injection pattern given existing `build.py` / `cache.py` shape (env var vs. injectable arg vs. monkeypatch fixture).
- Exact predicate location(s) in `analyze.py` where currently-valid filtering must be applied (god nodes, surprising connections).
- Whether per-relation `half_life_days` defaults should differ by relation type based on existing graph behavior (e.g., `semantically_similar_to` vs `references`).
- Whether `cache.py` already tracks per-file invalidation in a way that simplifies global supersession matching, or whether a new run-scoped edge-set diff is required.
</open_questions_for_researcher>

<scope_boundary>
Phase 71 delivers temporal fields, decay config, supersession stamping, SCHEMA_VERSION bump to 2.0, and minimal Temporal Health rendering. It does NOT deliver: typed reasoning relations (Phase 72 REAS), node-level dedup (Phase 73 DEDUP), vault-cwd bug fix (Phase 74 VBUG), or the v2.0 release packaging (Phase 75 PKG).
</scope_boundary>
