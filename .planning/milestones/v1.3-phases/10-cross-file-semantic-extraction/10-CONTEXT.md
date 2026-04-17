# Phase 10: Cross-File Semantic Extraction with Entity Deduplication - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver production-quality graphs on multi-source corpora by (1) extracting import-connected or co-located file clusters as single LLM-batch units and (2) adding a post-extraction entity deduplication layer that merges fuzzy-matched and embedding-similar nodes into canonical entities with aggregated edges.

**In-scope:**
- Cluster-based batch extraction (GRAPH-01) — skill calls the LLM once per file cluster, not once per file
- Post-extraction dedup pipeline stage (GRAPH-02) — fuzzy + semantic similarity, conservative thresholds
- Canonical merging with edge re-routing, weight aggregation, and deterministic label selection (GRAPH-03)
- Cross-source ontology alignment as stretch (GRAPH-04) — enabled by the embedding layer

**Out-of-scope (belongs in other phases):**
- Narrative slash commands (Phase 11)
- Heterogeneous extraction routing by file complexity (Phase 12, v1.4)
- LLM-as-judge final confirmation pass on proposed merges — captured in Deferred Ideas

</domain>

<decisions>
## Implementation Decisions

### Similarity Stack (Dedup Signals)

- **D-01:** Dedup uses **fuzzy + local embeddings**. Fuzzy match via stdlib `difflib.SequenceMatcher.ratio()`; semantic match via `sentence-transformers` with `all-MiniLM-L6-v2` (~90MB, ~384-dim vectors). Added as a new optional extra `[dedup]` in `pyproject.toml`. Core install stays lean; `pip install -e '.[dedup]'` opts in.
- **D-02:** Threshold policy is **conservative / high-precision**: merge only when **fuzzy ratio ≥ 0.90 AND embedding cosine ≥ 0.85** (both signals must agree). Prefers false-negatives over false-positives. Every proposed merge is recorded in the dedup report even if it's rejected by a safety net rule (see D-13).
- **D-03:** Dedup runs as a **blocking pipeline stage after extraction and before `build_graph`**. New pipeline shape: `detect → extract → **dedup** → build_graph → cluster → analyze → report → export`. Fits the existing "pure function, plain dicts between stages" contract.
- **D-04:** Audit trail is emitted in **three forms**: `graphify-out/dedup_report.json` (machine-readable, MCP/test consumable), `graphify-out/dedup_report.md` (human diff of merged pairs with similarity scores), and a new **"Entity Dedup"** section appended to `GRAPH_REPORT.md`. Matches the existing html + json + report triad.

### Batch Clustering Heuristic (Cross-File Extraction)

- **D-05:** File grouping is **hybrid: import-graph connected components, capped by top-level directory**. Start from the cross-file import resolution that already runs in `extract.py._resolve_cross_file_imports`. Split any component that spans multiple top-level directories (e.g., `auth/` and `api/`) so batches stay coherent even across tightly-coupled projects.
- **D-06:** Clustering logic lives in a **new `graphify/batch.py` library module**, sibling of `extract.py`. The skill consumes it: after AST extraction completes, skill calls `batch.cluster_files(paths, ast_results)` → list of `FileCluster` dicts → one LLM semantic call per cluster. Keeps `extract.py` pure AST. Makes clustering independently unit-testable.
- **D-07:** Cluster size is bounded by a **token-budgeted soft cap** with default `--batch-token-budget=50000`. When an import-component would exceed the budget, split at the weakest import edge (lowest degree-centrality boundary node). Budget is exposed via CLI flag; skill reads it from run config.
- **D-08:** Files within a cluster are emitted in **import-topological order** (imported-first, importer-last) so the LLM sees foundational definitions before dependents. Cycles fall back to alphabetical order for determinism.

### Canonical Label & Merge Rules

- **D-09:** Canonical-label tie-break order: **longest label → most-connected (degree-centrality) → alphabetical**. `source_location` mtime is intentionally excluded because it makes canonical selection non-reproducible across developer machines / CI. Locked order guarantees two runs on the same corpus produce the same canonical.
- **D-10:** On edge collapse (both nodes had an edge to the same target with the same relation):
  - `weight` → **sum** across merged edges (spec requirement)
  - `confidence_score` → **max** across merged edges
  - `confidence` enum → **EXTRACTED > INFERRED > AMBIGUOUS** (higher-trust wins; prevents INFERRED from silently burying AST ground-truth)
  - `source_file` → **list of all contributing source files** (dedup'd)
- **D-11:** Provenance on every canonical node: `source_file` becomes a **list of all merged paths**; new `merged_from` field is a **list of eliminated node IDs**. Both fields are optional on nodes that were never merged (back-compat with existing `graph.json` consumers).
- **D-12:** `validate.py` schema is extended to accept `source_file: str | list[str]` and optional `merged_from: list[str]`. Existing single-file nodes remain valid.
- **D-13:** Safety net: **cross-`file_type` merges are blocked by default.** A code node and a document node with identical labels (`User` class vs "User" paragraph) will NOT merge unless `--dedup-cross-type` is passed. This is the gateway to GRAPH-04 stretch; when enabled, cross-type merges use embeddings only (fuzzy alone is too weak across code/prose).

### Opt-in & Defaults

- **D-14:** Dedup is **opt-in via `--dedup` CLI flag** on `graphify run`. Off by default. Zero-surprise rollout; existing users see identical graphs unless they opt in. Skill and docs recommend `--dedup` for multi-source corpora. May become default-on in a future minor version after observed stability.
- **D-15:** Vault / Obsidian runs require a **separate `--obsidian-dedup` flag**, even if core dedup becomes default-on later. Rationale: Phase 8's Obsidian adapter writes wikilinks keyed to node IDs; dedup renames change those IDs. When `--obsidian-dedup` is on, every canonical node emits a `legacy_aliases: [id1, id2, ...]` list consumed by `merge.py`/`mapping.py` to forward-map existing wikilinks in user notes.
- **D-16:** MCP `query_graph` **transparently redirects** merged-away IDs. If an agent queries `auth` and it merged into `authentication_service`, the response returns the canonical node annotated with `resolved_from_alias: "auth"` and `merged_from: [...]`. Old agent callsites don't break; the redirect is visible in telemetry. Implemented as a dict lookup against the dedup report loaded alongside `graph.json`.
- **D-17:** Configuration layering: **CLI flags + optional `.graphify/dedup.yaml`** at corpus root. Flags (`--dedup`, `--dedup-fuzzy-threshold`, `--dedup-embed-threshold`, `--dedup-cross-type`, `--obsidian-dedup`, `--batch-token-budget`) take precedence over the YAML file. The YAML mirrors the existing `.graphify/profile.yaml` pattern (Obsidian vault profile) so power users have one consistent config surface. Requires PyYAML — already an optional extra `[obsidian]`; reuse it rather than introduce new parsing.

### Claude's Discretion

- Exact structure of the `dedup_report.json` schema (version field, merge record shape, summary stats) — to be designed during planning with the goal of being stable across minor versions.
- HTML viz tooltip format when hovering a merged canonical node — show label, `merged_from` list, and similarity scores from the dedup report.
- Degree-centrality source for D-09's tie-breaker — pre-dedup undirected graph degree is fine; no need to precompute PageRank.
- Minimum cluster size below which batching is skipped (single-file "clusters" just go through per-file semantic extraction unchanged). Likely ≥2 files.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope & Motivation
- `.planning/ROADMAP.md` §"v1.3 Intelligent Analysis Continuation" → "Phase 10" (lines ~118–132) — the four success criteria that must be verifiable after execution
- `.planning/REQUIREMENTS.md` — GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04 (stretch) full text and traceability
- `.planning/notes/april-2026-v1.3-priorities.md` §"Phase 10 — Cross-File Semantic Extraction (EMPHASIZE ENTITY DEDUP)" — the rationale shift from "batch only" to "batch + dedup"
- `.planning/notes/april-research-gap-analysis.md` — the 5–50× entity fragmentation observation that motivated dedup prominence

### Existing Code That This Phase Extends or Interoperates With
- `graphify/build.py` — existing three-layer exact-ID dedup (per-file `seen_ids`, NetworkX `add_node` overwrite, skill-level `seen` set). Phase 10 adds a fourth layer on top, does NOT replace any of them.
- `graphify/extract.py` §"Main extract and collect_files" (~line 2631) — the pure-AST `extract()` that feeds dedup; especially `_resolve_cross_file_imports` which seeds the import graph for D-05 clustering
- `graphify/cache.py` — per-file SHA256 cache; dedup output must be cached separately with a key derived from the full corpus hash (single added file invalidates dedup, not per-file AST)
- `graphify/cluster.py` — Leiden community detection runs AFTER dedup; communities become more meaningful once fragmented entities collapse
- `graphify/validate.py` — extraction schema enforcement; new provenance fields (D-11, D-12) require schema update
- `graphify/security.py` — all `graphify-out/*` path confinement (dedup_report.{json,md}) + label sanitization invariants for canonical labels
- `graphify/serve.py` — MCP server; new alias-resolution layer (D-16) sits at query-response boundary alongside Phase 9.2's Layer 1/2/3 budget framing
- `graphify/merge.py` + `graphify/mapping.py` — Obsidian adapter; consumes D-15's `legacy_aliases` to forward-map wikilinks in user vaults
- `graphify/analyze.py` — god-node / surprising-connection analysis re-runs against the dedup'd graph; degree-centrality tie-breakers in D-09 use pre-dedup graph to avoid circularity

### Architectural Conventions
- `.planning/codebase/STACK.md` + `.planning/codebase/STRUCTURE.md` — module layout, optional-deps pattern (`[leiden]`, `[obsidian]`) that `[dedup]` follows
- `.planning/codebase/CONVENTIONS.md` — naming (snake_case modules, `_private` helpers), type hints, `from __future__ import annotations`
- `CLAUDE.md` §"Extraction output schema" — authoritative node/edge schema; D-11/D-12 extend it
- `CLAUDE.md` §"Adding a new language" — unrelated but precedent for "new module + dispatch registration" pattern the `batch.py` addition mirrors

### Prior Phase Artifacts Worth Scanning
- `.planning/phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md` — Phase 9.2 decisions about MCP response layering; D-16 alias resolution must interoperate
- `.planning/phases/09.2-progressive-graph-retrieval/09.2-VERIFICATION.md` — passed status; confirms the current serve.py surface is the integration point

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`graphify/build.py` three-layer dedup** — preserved; Phase 10 adds `dedup.py` as the fourth layer that runs on the combined extraction dict BEFORE `build_from_json()` is called
- **Optional extras pattern in `pyproject.toml`** — `[leiden]`, `[obsidian]`, `[pdf]` show the precedent; `[dedup] = ["sentence-transformers"]` follows it exactly
- **`cache.py` SHA256 file cache** — unchanged for AST; dedup's own cache is a separate file keyed on corpus hash
- **`cluster.py` graspologic ImportError fallback** — the pattern for "optional heavy dep with graceful degrade" transfers directly to sentence-transformers (when missing, `--dedup` errors with an actionable install hint)
- **`security.py` path confinement + label sanitization** — canonical labels pass through `sanitize_label()` already; no new security work beyond ensuring `dedup_report.json` stays under `graphify-out/`
- **`serve.py` Phase 9.2 budget-aware response layering** — D-16 alias resolution slots in at the same query-response translation layer

### Established Patterns
- **Pure-function stages + plain dicts between them** — `dedup.py` takes the combined extraction dict and returns a dedup'd extraction dict + a report dict; no shared state
- **Deterministic output** — Leiden uses `seed=42` for reproducibility; dedup's tie-break order (D-09) serves the same purpose
- **Progress prints to stderr with `[graphify]` prefix** — dedup long-running embedding step follows this
- **Test pattern: one `tests/test_<module>.py` per module, pure unit tests, no network, no FS outside `tmp_path`** — `tests/test_batch.py` and `tests/test_dedup.py` will follow. Embedding tests use a tiny mocked encoder rather than the real model to keep CI fast.

### Integration Points
- **`extract()` → `dedup()` → `build_from_json()`** — new pipeline edge; `dedup.py` imported by whatever orchestrates `run` (skill today, `__main__.py run` command for CLI use)
- **`batch.py` → skill's semantic extraction call** — batch returns cluster metadata; skill's loop changes from "per file" to "per cluster"
- **`dedup_report.json` ↔ `serve.py`** — MCP server loads the report alongside `graph.json` to answer merged-alias queries
- **`dedup.py` → `merge.py` (Obsidian)** — when `--obsidian-dedup` is set, `legacy_aliases` flows through the existing Obsidian note generator
- **`pyproject.toml [dedup]` extra** — `sentence-transformers` + any transitive deps; reuse `PyYAML` already in `[obsidian]` for `.graphify/dedup.yaml`

</code_context>

<specifics>
## Specific Ideas

- **Model pin: `sentence-transformers/all-MiniLM-L6-v2`** — 384-dim vectors, 80MB on disk, fast on CPU, widely benchmarked. Locked via config so users don't drift onto incompatible encoders.
- **Deterministic cosine threshold semantics** — cosine values can drift slightly between torch versions on different platforms. Round to 3 decimals before threshold comparison so CI across Python 3.10 / 3.12 and macOS / Linux produces identical merge decisions.
- **`legacy_aliases` field is wikilink-safe** — must be slug-format node IDs, not labels, so Obsidian note generation never has to re-slug during forward-mapping.
- **Corpus canonical example for GRAPH-04 stretch verification** — `auth.py` (function) + `docs.md` ("authentication" heading) + `tests/test_auth.py` (`AuthService` class reference) should collapse to one canonical node. This is the specific acceptance test in the ROADMAP success criteria.
- **Dedup report as MCP-queryable** — consider adding a small MCP tool `list_merged_entities(limit=N)` that surfaces top merges by source_file count. Lets agents introspect whether dedup is actually helping their queries.

</specifics>

<deferred>
## Deferred Ideas

- **LLM-as-judge final confirmation pass** — Cognee's pattern of asking the LLM to approve proposed merges before applying. Higher precision but adds per-run cost. Revisit after Phase 10 ships and real-world precision is measured.
- **Content-similarity clustering** (embed whole file contents, cluster by topical similarity, use as batch units). Rejected for this phase because it flips the dependency order — you'd need embeddings before extraction. Could complement D-05 in a future phase if hybrid clustering proves insufficient.
- **`rapidfuzz` performance swap** — drop-in faster replacement for `difflib` if profiling shows fuzzy matching dominating runtime on large corpora. Currently unnecessary; revisit only if measured.
- **Automatic threshold tuning** — calibrate `--dedup-fuzzy-threshold` and `--dedup-embed-threshold` per corpus by sampling node pairs and looking for the distribution knee. Power-user feature, not worth blocking Phase 10 on.
- **Ontology-aware alignment rules** (explicit code-to-doc mappings like `snake_case_function` ↔ "Natural Language Title") — could augment GRAPH-04 embeddings with rule-based transforms. Defer to a future phase once v1.3 embeddings are in production.
- **Incremental dedup on Phase 6 deltas** — when the graph is rebuilt incrementally (v1.1 delta machinery), only re-dedup affected subgraphs rather than the whole corpus. Performance optimization; rely on corpus-hash-keyed full re-dedup for Phase 10.

</deferred>

---

*Phase: 10-cross-file-semantic-extraction*
*Context gathered: 2026-04-16*
