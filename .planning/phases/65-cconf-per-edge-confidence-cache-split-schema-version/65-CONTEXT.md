# Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the uniform `confidence_score: 1.0` baseline on concept↔code INFERRED edges with real per-edge LLM-derived scores plus an `evidence` field, persist them in a *second* cache namespace keyed on `prompt_version + model + file_hash` (independent of the existing `graphify/cache.py` file-hash extract cache), introduce a `schema_version` field that is optional-on-read / required-on-write so frozen v1.10–v1.12 graphs still pass `validate.py`, and add a calibration self-check section to `GRAPH_REPORT.md` that flags suspicious score distributions.

Order is load-bearing: schema_version + legacy fixture lands first (read-validation contract), then the confidence cache + scoring path, then the calibration self-check (consumes scored output). All scoring stays inside `extract.py` at concept emission — `_normalize_concept_code_edges` in `build.py` and the rest of the pipeline are untouched.

New capabilities (federation, drift, parameterized confidence queries) are explicitly out of scope; they belong to Phases 66–67 and consume the per-edge scores produced here.
</domain>

<decisions>
## Implementation Decisions

### Scoring source & integration point

- **D-65.01 — Real Claude LLM scoring.** Per-edge `confidence_score` and `evidence` are produced by an actual Claude API call. CCONF-01's "LLM-derived" wording is taken literally; no heuristic floor and no deferred-LLM stub. Reuses the existing semantic-extraction Claude integration in `extract.py`.
- **D-65.02 — Score at concept emission inside `extract.py`.** Scoring happens at the moment each concept↔code edge is created during semantic extraction, while concept text and the relevant code snippet are still in scope. `_normalize_concept_code_edges` in `build.py` stays untouched (Phase 53 D-53.02/06 invariants preserved).
- **D-65.03 — Batched per source file.** All concept↔code edges originating in one source file are scored in a single LLM call. The batching granularity matches the cache key (file-hash already pins source content), minimizes request count, and aligns with the existing per-file cache architecture in `cache.py`.

### Confidence cache shape & key

- **D-65.04 — Layout: `graphify-out/cache/confidence/<sha>.json`.** Sibling subdirectory next to the existing flat extract cache files. Visually separates namespaces, allows `rm -rf graphify-out/cache/confidence/` for a clean prompt-version reset, and prevents key collisions. The existing `graphify-out/cache/<sha>.json` extract cache is unchanged.
- **D-65.05 — Cache key = `sha256(prompt_version || model || file_hash)`.** File-level batching makes this the natural key composition. Bumping `prompt_version` invalidates only confidence entries; bumping `model` invalidates only confidence entries; the existing extract cache remains valid through both. Satisfies CCONF-03 verbatim.
- **D-65.06 — `prompt_version` lives in a new `graphify/prompts.py`.** Module-level constant, single source of truth, imported by `extract.py` and the new confidence cache module. Bumped by code change in the same commit as any prompt edit. Mirrors how `model_id` is handled in `cache.py`. The same module is the home for the scoring prompt template itself.

### schema_version + legacy fixture

- **D-65.07 — Storage: top-level JSON key in `graph.json` AND `nx.Graph.graph` attr.** Round-trips cleanly through `export.py` and stays attached on the in-memory NetworkX graph for downstream stages. Single source of truth on read.
- **D-65.08 — Value format: semver-shaped string `"1.13"`.** Aligns with the package version scheme in `pyproject.toml`. Read-validation accepts a missing/absent `schema_version` as "pre-1.13" and proceeds; write-validation requires it. CCONF-05's "optional on read, required on write" rule is implemented as two `validate.py` entry points (or one entry point with a `mode` parameter — planner's call).
- **D-65.09 — Legacy fixture: frozen real `graph.json` from a v1.12 sample run.** Run graphify on a small fixture corpus on a known-good v1.12 commit, capture the resulting `graph.json` verbatim, and check it in under `tests/fixtures/`. Authentic backward-compat proof — hand-crafted minimal fixtures can drift from what v1.10–v1.12 actually wrote and would defeat the purpose.

### Calibration self-check

- **D-65.10 — Histogram with multiple flag rules.** Compute a 10-bin histogram of `confidence_score` across all INFERRED concept↔code edges. Flag rules:
  1. **Mode-collapse:** any single bin holds >70% of total mass (the roadmap example, generalized to any bin not just 0.85±0.05).
  2. **Refusal-to-decide:** >50% of scores at exactly 0.5.
  3. **No-negatives:** <5% of edges score below 0.5.
  Each fired rule is reported with its observed value and threshold. The histogram itself is rendered in the `GRAPH_REPORT.md` calibration section regardless of whether any rule fires.
- **D-65.11 — Thresholds hardcoded as constants in `report.py`.** No new config surface; thresholds tunable via code if real-corpus runs show the rules are too tight/loose. Constants are named (e.g., `_CALIBRATION_MODE_COLLAPSE_THRESHOLD = 0.70`) so meaning stays self-documenting.

### Evidence field shape

- **D-65.12 — Free-text excerpt, char-capped, sanitized.** LLM returns a short justification string per edge. Stored as `edge["evidence"]: str`. Hard cap at 280 chars (matches the spirit of `security.py` label cap of 256 with a small bump for prose). Sanitization passes through the same control-char strip / HTML-escape used for labels in `security.py` so wiki/HTML rendering is safe out of the box.
- **D-65.13 — Skewed corpus test = hand-built fixture + stubbed scorer.** `tests/` ships a tiny `graph.json` where every concept↔code edge has `confidence_score` in 0.85±0.05; the scorer is monkeypatched to return those scores deterministically. Test asserts the mode-collapse flag fires. No LLM calls in tests — preserves the "no network calls" pure-unit-test convention from CLAUDE.md.

### Stderr contract conformance (carried forward from Phase 64)

- **D-65.14 — Any new warnings/errors emitted by the scoring path or schema_version validation MUST conform to the locked `[graphify] {error|info}: …` + `  hint: …` two-line contract.** Snapshot test from Phase 64 D-01 (`tests/fixtures/stderr_contract.txt`) is the gate; the round-trip skill regex test from Phase 64 D-03 is the secondary check.

### Claude's discretion (left to research / planning)

- Exact prompt template wording for the scoring call — language choice (e.g., "Score this edge from 0–1 and justify in <280 chars") is a research deliverable, not a context lock.
- Whether `validate.py` exposes one entry point with a `mode={"read","write"}` parameter or two separate functions (`validate_for_read` / `validate_for_write`).
- The small fixture corpus used to generate the frozen v1.12 `graph.json` — pick something already represented in `tests/fixtures/` if possible.
- Whether the calibration histogram is rendered as ASCII bars, a markdown table, or both in `GRAPH_REPORT.md`.
- Concurrency/retry behavior for the LLM scoring call (existing semantic extraction patterns govern; planner inherits whatever is already in place in `extract.py`).
- Cache file format details inside `graphify-out/cache/confidence/<sha>.json` (likely mirror the existing extract cache JSON shape).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & success criteria
- `.planning/ROADMAP.md` §"Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version" — goal, depends-on (Phase 64), 4 success criteria, requirements CCONF-01..05.
- `.planning/REQUIREMENTS.md` §CCONF — definitive requirement text for CCONF-01..05.
- `.planning/PROJECT.md` §"Current Milestone: v1.13 Concept Intelligence & Audit Closure" — milestone framing and seed-traceability for SEED-bidirectional-concept-code-links remaining 35%.

### Phase 64 contract (mandatory carry-forward)
- `.planning/phases/64-audit-a-stderr-format-snapshot-lock-sweep/64-CONTEXT.md` — D-04 stderr prefix policy (`error:` / `info:` only).
- `tests/fixtures/stderr_contract.txt` — locked stderr contract; any new emitter in this phase must conform.
- `graphify/output.py` `emit_option_b_breadcrumb`, `_emit_vault_error` — canonical two-line emitter shapes.

### Concept↔code edge invariants (Phase 53 carry-forward)
- `graphify/build.py` `_normalize_concept_code_edges` (line 116) — orient/merge step for the five concept↔code relations; Phase 65 must NOT bypass or relocate this.
- `graphify/build.py` lines 34–39 (Phase 53 D-53.02 comment) — concept↔code orientation invariants.

### Existing cache architecture (must NOT touch)
- `graphify/cache.py` — `_sanitize_model_id`, `_cache_key_string`. New confidence cache module mirrors these patterns but lives in a separate namespace per D-65.04/05.

### Validation contract (modified by this phase)
- `graphify/validate.py` — `REQUIRED_EDGE_FIELDS` (line 10), confidence/confidence_score validation (lines 178–210). CCONF-05 adds `schema_version` semantics here.

### Today's INFERRED edge sites (the surface to upgrade)
- `graphify/extract.py` lines ~596, 1211–1231, 2252 — current `confidence_score: 1.0` baked-in baseline emissions for concept↔code and INFERRED edges.

### Security & sanitization (for evidence field)
- `graphify/security.py` — label sanitization patterns (HTML-escape, control-char strip, length cap). Evidence field reuses these per D-65.12.

### Codebase orientation (already-built maps)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/STRUCTURE.md` — pipeline shape, naming patterns, module boundaries.
</canonical_refs>

<code_context>
## Reusable Assets & Patterns

- **Existing extract cache module (`graphify/cache.py`, 186 lines):** `_sanitize_model_id`, `_cache_key_string`, JSON-on-disk format. New confidence cache module copies these patterns into a sibling module / sibling subdirectory.
- **Existing semantic extraction Claude call path in `extract.py`:** scoring reuses whatever Claude integration the semantic concept extractor already calls — no second client surface introduced.
- **`security.py` sanitization:** evidence string passes through the same control-char strip / HTML-escape / length cap used for node labels.
- **Phase 64 stderr contract + fixtures:** any new warning emitted (e.g., "scoring fell back due to LLM error", "schema_version missing — read-validating as legacy") conforms to two-line format and is added to the snapshot.
- **Phase 53 `_normalize_concept_code_edges`:** treated as immutable. Scoring is upstream of normalization; merged duplicate edges inherit max(score) or first-seen score per planner decision.
- **`tests/fixtures/` convention:** legacy v1.12 graph.json and skewed-distribution graph.json both go here; pure-unit-test convention preserved (no network in tests).
</code_context>

<deferred>
## Deferred Ideas

None surfaced during discussion. (Federation tiebreakers using `confidence_score` → Phase 66 by roadmap; drift edge filters using `confidence_score` → Phase 67 by roadmap. Both already scoped.)
</deferred>
