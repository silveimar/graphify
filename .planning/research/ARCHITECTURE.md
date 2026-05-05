# Architecture Patterns — graphify v1.13 Concept Intelligence & Audit Closure

**Domain:** Knowledge-graph CLI / pipeline integration
**Researched:** 2026-05-05
**Confidence:** HIGH (grounded in observed v1.12 source state, prior-phase observations 4107, 4384, 4426, 4794, 5133, 5231, 5334)

---

## Recommended Architecture

v1.13 is **additive over the existing 7-stage pipeline** — no stage is removed or reordered. Three net-new capabilities slot in as follows:

```
detect → extract → [E1: per-edge confidence enrichment] → build_graph → [B1: federation merge] → cluster → analyze → report → export
                          ▲                                       ▲
                          │ separate cache namespace              │ uses confidence as tiebreaker
                          │                                       │
                                                                  └─ snapshots/ ──► drift detector (analyze-adjacent, query-time in serve.py)

__main__.py VCWD gate (1500–1593) ──► [V1: silent reroute branch] ──► default_graphify_artifacts_dir()
serve.py concept_code_hops ──► [S1: parameterized signature, MCP-visible]
```

### Component Boundaries — net new vs. modified

| # | Capability | New module? | Modified file(s) | Stage |
|---|-----------|-------------|------------------|-------|
| E1 | Per-edge LLM confidence scoring | **No** — extension inside `extract.py` (or thin `graphify/confidence.py` helper) | `extract.py`, `cache.py` (new namespace), `validate.py` (loosen confidence_score range) | extract |
| B1 | Cross-repo concept identity federation | **Yes** — `graphify/federate.py` (recommended) | `build.py` (calls federate after `_normalize_concept_code_edges`), `__main__.py` (multi-corpus arg) | build |
| D1 | Edge drift detection | **Yes** — `graphify/drift.py` (recommended) | `analyze.py` (optional summary section), `serve.py` (`_run_drift_nodes` already stub), `report.py` (drift block) | analyze + serve |
| S1 | Parameterized `concept_code_hops` | **No** | `serve.py` only | serve (query-time) |
| V1 | Vault Option B silent reroute | **No** | `__main__.py` (VCWD gate ~1522–1593), comment-only touch in `default_graphify_artifacts_dir()` | CLI dispatch |

---

## 1. Integration Points (specific anchors)

### E1 — Per-edge confidence scoring
- **Where:** Run as a *post-extraction enrichment pass* inside `extract()` dispatch in `extract.py`, **after** language-specific extractors return `{nodes, edges}` but **before** the dict is handed to `build_from_json()`. Keep it a separate function (`enrich_edge_confidence(extraction, llm_client) -> extraction`) so it is testable and skippable via `--no-confidence-score`.
- **Why not in-line per extractor:** would force every tree-sitter extractor to take an LLM client. Post-pass keeps EXTRACTED edges deterministic and pure.
- **Schema impact:** `validate.py` already accepts `confidence_score: float`. v1.13 promotes it from optional-on-INFERRED to optional-on-all-edges. Confidence enum (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`) unchanged.

### B1 — Federation
- **Where:** New `graphify/federate.py` invoked from `build.py` *immediately after* `_normalize_concept_code_edges` (which Phase 53 added; obs 4107). Federation merges concept nodes whose `id` matches across repos but whose `repo_identity` differs.
- **Single-corpus multi-repo:** federation is in-process; one `nx.Graph` already.
- **Cross-corpus runs:** federation accepts a list of pre-built graphs (`federate_graphs([G1, G2, ...]) -> G`). CLI exposes `graphify federate --corpus a/ --corpus b/`.
- **Why not query-time in `serve.py`:** dedupe must run before cluster.py — Leiden treats unmerged duplicates as separate communities, polluting cohesion scores and god-node ranking (`analyze.py:169` cross-repo logic).

### D1 — Drift detection
- **Snapshot location:** `graphify-out/snapshots/<ISO-timestamp>/graph.json` (uses existing `graphify-out/` confinement from `security.py`). One snapshot per `graphify run` when `--snapshot` flag set; pruned by count, not LRU (deterministic).
- **Emit point:** end of `export.py` (after canonical `graph.json` written). New helper `export.write_snapshot(graph, out_dir)`.
- **Compare point:** `drift.py` reads the two most recent snapshots and emits `drift.json` (added/removed/confidence-shifted edges). Called from `analyze.py` if `snapshots/` has ≥2 entries; otherwise no-op.
- **Serve hook:** `serve.py:_run_drift_nodes` already a stub — wire it to load `drift.json`, no graph mutation.

### S1 — Parameterized `concept_code_hops`
- **Pure refactor in `serve.py`** with **MCP-visible signature change** (added optional params: `max_hops`, `min_confidence`, `relation_filter`). Defaults preserve v1.12 behavior. MCP tool schema in serve.py needs JSON Schema update — that *is* a client-visible contract change, but additive.

### V1 — Vault Option B silent reroute
- **Where:** in `__main__.py` VCWD dispatch (~lines 1522–1593, the auto-adopt gate that sets `lv_vault = Path.cwd()` per obs 5133). Add a branch *before* the gate fires: when CWD is a vault but the user explicitly passes `--no-vault-route`, silently fall through to `default_graphify_artifacts_dir()`. No filesystem change in `default_graphify_artifacts_dir()` itself — just a docstring note.
- **Phase 62.1 lesson (obs 5334):** `argparse required=True` on `--vault` previously bypassed the gate. V1 must run the reroute decision **before** argparse coerces missing `--vault` into a default — i.e. in the dispatch wrapper, not the subparser.

---

## 2. Build Order (dependency-driven)

Recommended sequencing for the roadmapper:

1. **S1 (concept_code_hops parameterization)** — zero deps; warm-up phase, lands the MCP schema bump early so clients pin against final shape.
2. **V1 (vault silent reroute)** — independent CLI surgery; closes a pre-existing audit item (obs 5334) before adding new surface area.
3. **E1 (per-edge confidence)** — must precede B1 because federation uses confidence as a dedupe tiebreaker (higher-confidence concept↔code edge wins on merge collision). Also unblocks D1's "confidence-shifted" drift class.
4. **B1 (federation)** — depends on E1 confidence scores; depends on cluster.py being unchanged (we want federation *before* clustering).
5. **D1 (drift detection)** — depends on at least one prior snapshot; in practice depends on E1 (drift wants confidence deltas, not just topology deltas) and B1 (federated IDs are stable across runs; without federation, drift would flag legitimate cross-repo merges as churn).

Critical path: **E1 → B1 → D1**. S1 and V1 parallelizable from day one.

---

## 3. Suggested New Files

### `graphify/federate.py` — **YES, create**
- **For:** federation has its own dedupe rules (concept-id collision handling, `repo_identity` precedence, confidence tiebreak), distinct from `build.py`'s three-layer dedup (obs 704). Hiding it in `build.py` would push that file past its current scope and obscure cross-repo semantics.
- **Public API:** `federate_graph(graph: nx.Graph) -> nx.Graph`, `federate_extractions(extractions: list[dict]) -> dict`.

### `graphify/drift.py` — **YES, create**
- **For:** drift is fundamentally a temporal concern; mixing it into `analyze.py` (which is single-snapshot god-node/community analysis) muddies that module's invariants. Drift also owns its own JSON schema (`drift.json`) — module-per-schema is the established pattern (cf. `validate.py`, `report.py`).
- **Public API:** `compute_drift(prev_path, curr_path) -> dict`, `write_drift(out_dir, drift)`.

### `graphify/confidence.py` — **OPTIONAL, lean toward yes**
- **Argument for:** keeps the LLM enrichment loop, prompt template, and JSON-mode parsing out of the already-2700-line `extract.py`.
- **Argument against:** if the implementation is <100 lines and reuses `extract.py`'s existing LLM client plumbing, inline is fine.
- **Recommendation:** start inline; extract to `confidence.py` if the function exceeds ~150 lines or grows a second prompt variant.

---

## 4. Cache Implications

The existing semantic cache (`cache.py`) keys on **file SHA256** and stores the full `{nodes, edges}` extraction dict in `graphify-out/cache/`. Per-edge confidence scoring naively invalidates every cache entry on first v1.13 run.

**Recommended: separate cache namespace.**

- New namespace `graphify-out/cache/confidence/` keyed by **edge fingerprint** (`sha256(source|relation|target|source_file|source_location)`), not file hash.
- Extraction cache (`graphify-out/cache/extract/`) stays file-hash keyed and remains valid across the v1.12→v1.13 boundary.
- Enrichment pipeline: extract → load extract-cache → for each edge, look up confidence-cache → only LLM-call edges with no entry.
- **Migration:** old `cache/*.json` files get auto-moved into `cache/extract/` on first v1.13 run (one-shot in `cache.py`, idempotent). LOG a `[graphify]` notice once.

**Federation cache:** none needed — federation is fast graph ops over already-built graphs. Avoid premature caching.

**Drift cache:** the snapshots themselves *are* the cache. No extra layer.

---

## 5. Backward Compatibility

| Artifact | Change | Compat class |
|---------|--------|--------------|
| `graph.json` | Adds optional `confidence_score` on EXTRACTED edges; adds optional `repo_identity_canonical` on federated nodes | **Additive** — v1.12 readers ignore unknown fields |
| `cluster.json` | Federation may *reduce* node count (merged duplicates), shifting community ids | **Semantic break, not schema break** — flag in CHANGELOG; `cluster.py` already re-indexes by size desc (deterministic w/ seed=42, obs 4794) |
| `GRAPH_REPORT.md` | New "Drift" and "Federation" sections appended | **Additive** |
| Cypher dump (`export.py`) | Optional `confidence_score` property on rels; federated nodes carry `:Federated` label | **Additive** — Cypher MERGE-by-id semantics unchanged |
| `obsidian/` vault | No change in v1.13 (vault adapter is v1.10/v1.12 territory; v1.13 doesn't touch it except via V1) | **None** |
| MCP `concept_code_hops` | New optional params; tool schema bump | **Additive at protocol** — but `mcp/server.json` manifest hash changes; bump per CLAUDE.md release ritual |
| Cache directory layout | One-shot migration into `cache/extract/` and `cache/confidence/` | **Migrated, not broken** — old runs work; first v1.13 run reorganizes |
| `default_graphify_artifacts_dir()` | Behavior unchanged; comment update only | **None** |
| VCWD gate | New silent-reroute branch only fires under explicit `--no-vault-route` | **None for default flows** |

No v1.12 artifact becomes unreadable. No fixture-based test in `tests/` should break from schema (E1/B1 add fields) or dispatch (V1 is opt-in flag) changes.

---

## Patterns to Follow

### Pattern: Pure-function pipeline stages (preserve)
**What:** stages communicate via dicts/`nx.Graph`; no shared state; results are cacheable.
**Apply to v1.13:** `enrich_edge_confidence`, `federate_graph`, `compute_drift` all take inputs, return outputs, write nothing outside `graphify-out/`.

### Pattern: Optional dependency degradation
**What:** `cluster.py` falls back Leiden→Louvain on ImportError (obs 704).
**Apply:** confidence enrichment must degrade if no LLM key — emit `EXTRACTED` edges with `confidence_score=None`, log once. Federation runs without LLM. Drift runs without LLM.

### Pattern: Module-per-schema
**What:** `validate.py` owns extraction schema; `report.py` owns markdown schema.
**Apply:** `drift.py` owns `drift.json` schema; `federate.py` owns federation merge log schema.

---

## Anti-Patterns to Avoid

### Anti-pattern: Federation in `serve.py` (query-time only)
**Why bad:** Leiden runs over un-federated graph → polluted communities → cascades into `analyze.py` god-node ranking and `report.py` cohesion. Recompute on every query is expensive.
**Instead:** federate at build, after `_normalize_concept_code_edges`, before `cluster()`.

### Anti-pattern: Per-edge LLM scoring inside each tree-sitter extractor
**Why bad:** breaks determinism of EXTRACTED edges (obs 4794 confirms `_partition` determinism — preserve that property upstream too); forces every language extractor to take an LLM client.
**Instead:** post-pass in `extract()` dispatcher; cache per-edge.

### Anti-pattern: Reusing the file-hash cache for confidence scores
**Why bad:** any edit to a file invalidates confidence on every edge in that file, even unaffected ones.
**Instead:** edge-fingerprint cache namespace.

### Anti-pattern: Drift via in-memory diff during `graphify run`
**Why bad:** requires holding two graphs in RAM; couples drift to run-time; no audit trail.
**Instead:** snapshot to disk, compare two snapshots on demand. Idempotent, replayable.

### Anti-pattern: V1 silent reroute applied after argparse coercion
**Why bad:** Phase 62.1 (obs 5334) showed `required=True` bypasses gates that run after parser dispatch.
**Instead:** decide reroute in the dispatch wrapper before subparser kicks in.

---

## Scalability Considerations

| Concern | Single repo | Multi-repo (5–10) | Mega-corpus (50+) |
|--------|-------------|-------------------|-------------------|
| Confidence enrichment | LLM cost ~ #edges; cache hit rate >95% on re-run | Same per-repo; parallelizable across repos | Batch into single LLM request (16–32 edges/call) |
| Federation | No-op (nothing to merge) | O(n log n) over merged concept set | Consider `repo_identity`-bucketed pre-pass to bound comparisons |
| Drift | 2 snapshots, fast | Same — snapshots are per-corpus | Per-repo drift, then aggregated |
| Snapshot disk | ~MB/run | ~MB/run/repo | Add retention pruning (already recommended) |

---

## Sources

- v1.12 source state (build.py, serve.py, __main__.py, validate.py, cache.py, security.py) — HIGH
- Prior observations: 704 (build dedup), 4107 (Phase 53 concept↔code), 4384 (harness baseline), 4426 (build_from_json edge-skip), 4794 (`_partition` determinism), 5133 (VCWD auto-adopt), 5211 (exit-code constants), 5231 (auto-adopt scope), 5334 (Phase 62.1 argparse bypass), 5379 (seed audit) — HIGH
- CLAUDE.md Architecture section (pipeline, key modules, schema) — HIGH
- Milestone context block from orchestrator — HIGH
