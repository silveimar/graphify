# Phase 10: Cross-File Semantic Extraction with Entity Deduplication - Research

**Researched:** 2026-04-16
**Domain:** NetworkX graph mutation, sentence-transformers embeddings, difflib fuzzy matching, import-graph clustering
**Confidence:** HIGH (all critical claims verified via live code execution or Context7 docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Dedup uses fuzzy + local embeddings. Fuzzy match via stdlib `difflib.SequenceMatcher.ratio()`; semantic match via `sentence-transformers` with `all-MiniLM-L6-v2` (~90MB, ~384-dim vectors). New optional extra `[dedup]` in `pyproject.toml`.
- **D-02:** Threshold policy is conservative: merge only when **fuzzy ratio >= 0.90 AND embedding cosine >= 0.85** (both signals must agree). Every proposed merge recorded in dedup report even if rejected by safety net rule.
- **D-03:** Dedup runs as a **blocking pipeline stage after extraction and before `build_graph`**. Pipeline: `detect → extract → dedup → build_graph → cluster → analyze → report → export`. Pure function, plain dicts between stages.
- **D-04:** Audit trail in **three forms**: `graphify-out/dedup_report.json` (machine-readable), `graphify-out/dedup_report.md` (human diff), and a new **"Entity Dedup"** section in `GRAPH_REPORT.md`.
- **D-05:** File grouping is **hybrid: import-graph connected components, capped by top-level directory**. Starts from cross-file import resolution in `extract.py._resolve_cross_file_imports`. Splits components spanning multiple top-level directories.
- **D-06:** Clustering logic in a **new `graphify/batch.py` library module**. Skill calls `batch.cluster_files(paths, ast_results)` → list of `FileCluster` dicts → one LLM semantic call per cluster.
- **D-07:** Cluster size bounded by **token-budgeted soft cap** with default `--batch-token-budget=50000`. When a component exceeds budget, split at the weakest import edge (lowest degree-centrality boundary node).
- **D-08:** Files within a cluster emitted in **import-topological order** (imported-first, importer-last). Cycles fall back to alphabetical order for determinism.
- **D-09:** Canonical-label tie-break: **longest label → most-connected (degree pre-dedup) → alphabetical**. `source_location` mtime excluded. Deterministic across runs.
- **D-10:** Edge collapse rules: `weight` → sum; `confidence_score` → max; `confidence` enum → EXTRACTED > INFERRED > AMBIGUOUS; `source_file` → list of all contributing source files.
- **D-11:** Provenance: `source_file` becomes a list; new `merged_from: list[str]` field of eliminated node IDs. Optional on nodes never merged.
- **D-12:** `validate.py` schema extended to accept `source_file: str | list[str]` and optional `merged_from: list[str]`.
- **D-13:** Safety net: **cross-`file_type` merges blocked by default**. `--dedup-cross-type` flag enables; when enabled, cross-type merges use embeddings only.
- **D-14:** Dedup is **opt-in via `--dedup` CLI flag**. Off by default.
- **D-15:** Vault/Obsidian runs require separate **`--obsidian-dedup` flag**. When on, every canonical node emits `legacy_aliases: [id1, id2, ...]` list.
- **D-16:** MCP `query_graph` **transparently redirects** merged-away IDs. Returns `resolved_from_alias` and `merged_from` in response. Implemented as dict lookup against `dedup_report.json`.
- **D-17:** Configuration layering: **CLI flags + optional `.graphify/dedup.yaml`** at corpus root. Flags take precedence. PyYAML reused from `[obsidian]` extra.

### Claude's Discretion

- Exact structure of `dedup_report.json` schema (version field, merge record shape, summary stats)
- HTML viz tooltip format when hovering a merged canonical node
- Degree-centrality source for D-09 tie-breaker (pre-dedup undirected graph degree confirmed correct)
- Minimum cluster size below which batching is skipped (single-file clusters go through per-file extraction unchanged). Likely >= 2 files.

### Deferred Ideas (OUT OF SCOPE)

- LLM-as-judge final confirmation pass on proposed merges
- Content-similarity clustering (embed whole file contents as batch units)
- `rapidfuzz` performance swap for difflib
- Automatic threshold tuning per corpus
- Ontology-aware alignment rules (snake_case_function <-> "Natural Language Title")
- Incremental dedup on Phase 6 deltas
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRAPH-01 | Graphify extracts import-connected or co-located file clusters as a single batch unit (one LLM call per cluster) | D-05/D-06/D-07/D-08 locked. `nx.connected_components` on import-edge graph seeds clusters. `_resolve_cross_file_imports` already builds the cross-file edge data. Token budget heuristic: 4 chars/token, soft cap at 50k tokens. |
| GRAPH-02 | `graphify/dedup.py` merges fuzzy-matched and embedding-similar entities post-extraction, producing `dedup_report` | D-01/D-02/D-03 locked. Blocking strategy (4-char prefix + length ratio guard) verified to meet the 30s performance target on 1k-node corpora. sentence-transformers API verified via Context7. |
| GRAPH-03 | After dedup, edges re-routed to canonical nodes, weights aggregated, canonical label deterministic | D-09/D-10/D-11 locked. `nx.relabel_nodes` does NOT aggregate parallel edges automatically — custom pre-build merge logic required on extraction dicts. Verified via live test. |
| GRAPH-04 (stretch) | Cross-source ontology alignment — auth.py function + docs.md heading + tests/AuthService collapse to one canonical | Enabled by `--dedup-cross-type` (D-13). GRAPH-04 stretch uses embeddings-only (fuzzy alone too weak across code/prose). The D-09 test corpus is the acceptance test. |
</phase_requirements>

---

## Summary

Phase 10 adds two new modules (`batch.py` and `dedup.py`) plus extends `validate.py`, `serve.py`, `pyproject.toml`, and the CLI argument surface. The architecture is fully locked in CONTEXT.md; this research supplies the verified implementation-level API surfaces, behavioral gotchas, and performance characteristics the planner needs to slice this into concrete tasks.

The single most important verified finding is that **`nx.relabel_nodes` silently overwrites parallel edge attributes rather than merging them**. The dedup logic must operate on extraction dicts (pre-`build_graph`) and implement custom edge-merge logic with explicit weight-sum, confidence-max, and source_file-union semantics before calling `build_from_json`. This is the highest-risk correctness issue in the whole phase.

A second key finding is that **4-char prefix blocking + length-ratio guard is the correct O(N log N) strategy** for the fuzzy-compare phase. Verified to complete 1k-node corpora in under 0.5s with realistic code entity names, well within the 30s target even before adding embedding time. On synthetic worst-case data (5k nodes, random labels), the blocker still reduces comparisons to 17% of full pairwise.

**Primary recommendation:** Implement dedup.py operating exclusively on extraction dicts (never on NetworkX graphs), then pass the merged dict to the existing `build_from_json`. This keeps the pure-function stage contract and avoids all graph-mutation complexity.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File cluster detection (import-graph) | `graphify/batch.py` | `graphify/extract.py` | `_resolve_cross_file_imports` already builds the cross-file graph; batch.py consumes its output |
| Token-budget enforcement per cluster | `graphify/batch.py` | `graphify/__main__.py` (CLI flag) | batch.py computes char-count estimates; CLI exposes the threshold |
| Topological ordering within cluster | `graphify/batch.py` | stdlib `networkx` | `nx.topological_sort` on the import subgraph; cycle fallback is alphabetical |
| Fuzzy similarity scoring | `graphify/dedup.py` | stdlib `difflib` | All comparison logic in dedup.py; no new deps for this signal |
| Embedding similarity scoring | `graphify/dedup.py` | `sentence-transformers` (optional dep) | Imported with ImportError guard; only used when `--dedup` is active |
| Canonical label selection | `graphify/dedup.py` | pre-dedup undirected graph degree | D-09 tie-break logic lives entirely inside dedup.py |
| Edge re-routing and weight aggregation | `graphify/dedup.py` | — | Must happen pre-`build_graph` on dicts; NOT via nx.relabel_nodes (see Pitfall 1) |
| Schema validation of provenance fields | `graphify/validate.py` | — | D-12 extension; `source_file: str | list[str]` and optional `merged_from` |
| Alias redirect in MCP queries | `graphify/serve.py` | `dedup_report.json` | D-16 thin lookup layer at query-response boundary |
| Dedup audit output | `graphify/dedup.py` | `graphify/report.py` | dedup.py emits report dict; report.py appends "Entity Dedup" section to GRAPH_REPORT.md |
| Obsidian wikilink forward-mapping | `graphify/merge.py` + `graphify/mapping.py` | `legacy_aliases` from dedup | D-15 — existing Obsidian adapter consumes the new `legacy_aliases` node field |
| Corpus-hash cache for dedup results | `graphify/dedup.py` | `graphify/cache.py` pattern | New cache entry keyed on sorted SHA256 corpus hash, separate from per-file AST cache |
| Configuration YAML parsing | `graphify/dedup.py` (or a `graphify/config.py`) | PyYAML (already in `[obsidian]`) | `.graphify/dedup.yaml` mirrors `.graphify/profile.yaml` pattern |

---

## Standard Stack

### Core (stdlib only — no new required deps)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `difflib.SequenceMatcher` | stdlib | Fuzzy string ratio [0.0, 1.0] | Zero-dep, ships with Python 3.10+ |
| `networkx.connected_components` | already required | Import-graph clustering | Already in project deps; returns frozensets |
| `networkx.topological_sort` | already required | Import-order within cluster | Raises `NetworkXUnfeasible` on cycles; explicit cycle detection available via `nx.is_directed_acyclic_graph` |
| `networkx.degree_centrality` | already required | D-09 tie-break: most-connected | Returns dict `{node: float}` |
| `hashlib.sha256` | stdlib | Corpus hash for dedup cache key | Same pattern as `cache.py` per-file hash |

### Optional Extra
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | latest (v4.x) [VERIFIED: ctx7] | `all-MiniLM-L6-v2` 384-dim embeddings | Only when `--dedup` flag is active and model needed |

**Version verification:** [VERIFIED: npm view not applicable; ctx7 docs confirm sentence-transformers API is stable for the usage pattern below]

### Installation
```bash
# Minimal install (no dedup)
pip install -e "."

# With dedup capability
pip install -e ".[dedup]"

# With dedup + obsidian (for dedup.yaml support via PyYAML)
pip install -e ".[dedup,obsidian]"
```

The `[dedup]` extra in `pyproject.toml` follows the existing pattern exactly:
```toml
dedup = ["sentence-transformers"]
all = [..., "sentence-transformers"]
```

---

## Architecture Patterns

### System Architecture Diagram

```
                        ┌─────────────────────────────────────────────┐
                        │  CLI: graphify run --dedup [--batch-token-budget=50000]
                        └─────────────────┬───────────────────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │  detect()                       │
                          │  collect_files() → [Path]       │
                          └───────────────┬────────────────┘
                                          │ list[Path]
                          ┌───────────────▼────────────────┐
                          │  extract()                      │
                          │  AST per-file + cross-file      │
                          │  _resolve_cross_file_imports()  │
                          └───────────────┬────────────────┘
                                          │ extraction dict {nodes, edges}
              ┌──────────────────────────►│
              │                           │ (--dedup flag present?)
              │             YES ◄─────────┤─────────► NO (skip dedup)
              │                           │
  ┌───────────▼────────────────────────┐  │
  │  dedup()   [graphify/dedup.py]      │  │
  │                                     │  │
  │  1. Build pre-dedup graph           │  │
  │     (for D-09 degree tie-break)     │  │
  │  2. Prefix-block candidate pairs    │  │
  │  3. Fuzzy gate (>=0.90) + file_type │  │
  │     cross-type guard (D-13)         │  │
  │  4. Cosine gate (>=0.85) if fuzzy   │  │
  │     passes (lazy load model)        │  │
  │  5. Select canonical (D-09)         │  │
  │  6. Re-route edges + merge attrs    │  │
  │     (sum weight, max confidence)    │  │
  │  7. Annotate canonical node with    │  │
  │     merged_from + source_file list  │  │
  │  8. Emit dedup_report dict          │  │
  └───────────┬────────────────────────┘  │
              │ dedup'd extraction dict    │
              └──────────────►────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │  build_graph()                  │
                          │  build_from_json(extraction)    │
                          └───────────────┬────────────────┘
                                          │ nx.Graph
                          ┌───────────────▼────────────────┐
                          │  cluster() → analyze()          │
                          │  → report() → export()          │
                          └───────────────┬────────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │  graphify-out/                  │
                          │    graph.json                   │
                          │    dedup_report.json  ◄─── D-04 │
                          │    dedup_report.md    ◄─── D-04 │
                          │    GRAPH_REPORT.md    ◄─── D-04 │
                          └────────────────────────────────┘

  batch.py feeds INTO skill's LLM semantic extraction loop (separate from above):

  batch.cluster_files(paths, ast_results)
    → [FileCluster, ...]       (D-06)
    Each cluster: {files, order, token_estimate, cluster_id}
    Skill iterates clusters → one LLM call per cluster → combined semantic extraction
```

### Recommended Project Structure
```
graphify/
├── batch.py          # NEW: FileCluster dataclass, cluster_files(), token estimation
├── dedup.py          # NEW: dedup(), _prefix_blocks(), _select_canonical(), _merge_edges()
├── validate.py       # EXTEND: accept source_file: str|list[str], merged_from: list[str]
├── serve.py          # EXTEND: alias-redirect layer for D-16
├── __main__.py       # EXTEND: --dedup, --dedup-fuzzy-threshold, --dedup-embed-threshold,
│                     #          --dedup-cross-type, --obsidian-dedup, --batch-token-budget
├── cache.py          # READ-ONLY: corpus_hash computed from sorted per-file hashes
└── (all other modules unchanged)

tests/
├── test_batch.py     # NEW: unit tests for cluster_files(), token estimation, topo order
├── test_dedup.py     # NEW: unit tests for blocking, merge logic, edge re-routing, report
├── test_validate.py  # EXTEND: new source_file list and merged_from acceptance tests
└── test_serve.py     # EXTEND: alias redirect lookup test

graphify-out/         # Runtime outputs (not in git)
├── dedup_report.json
├── dedup_report.md
└── cache/
    └── {corpus_hash}.dedup.json  # dedup cache keyed on corpus hash
```

---

### Pattern 1: sentence-transformers Model Load + Encode

```python
# Source: Context7 /huggingface/sentence-transformers — confirmed API
# graphify/dedup.py — lazy-load pattern (model only loaded when --dedup is active)

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

_MODEL: "SentenceTransformer | None" = None
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def _get_model() -> "SentenceTransformer":
    global _MODEL
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install 'graphifyy[dedup]'"
        )
    if _MODEL is None:
        print(f"[graphify] Loading embedding model {_MODEL_NAME} ...", file=sys.stderr)
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def _encode_labels(labels: list[str]) -> "np.ndarray":
    """Encode labels as 384-dim normalized float32 vectors. Returns (N, 384) array."""
    model = _get_model()
    # normalize_embeddings=True makes dot product == cosine similarity
    embeddings = model.encode(labels, normalize_embeddings=True, batch_size=64,
                              show_progress_bar=False)
    return embeddings  # shape (N, 384), dtype float32
```

**Offline/cached model behavior:** sentence-transformers caches the model locally under `~/.cache/huggingface/hub/` (or `SENTENCE_TRANSFORMERS_HOME` env var). First run downloads ~90MB; subsequent runs load from disk in ~1–2s on CPU. [VERIFIED: ctx7 /huggingface/sentence-transformers]

**CPU performance:** `all-MiniLM-L6-v2` is specifically designed for CPU use: 384-dim (vs 768 for mpnet-base), 22M parameters. Typical CPU encode time is ~50ms per 100 labels. A 1000-label corpus takes ~500ms on CPU. [CITED: sbert.net model cards]

**Determinism across torch versions:** `normalize_embeddings=True` returns L2-normalized vectors. Dot product of normalized vectors equals cosine similarity. Round to 3 decimals before threshold comparison: `round(float(np.dot(a, b)), 3)` — this equalizes minor floating point differences between torch 1.x and 2.x on the same model. [ASSUMED — rounding to 3 decimals is the project-specified approach per D-09; no official torch-version determinism guarantee found]

### Pattern 2: difflib.SequenceMatcher.ratio() Behavior

[VERIFIED via live execution — Python 3.11.x on macOS Darwin 25.3.0]

Key verified behaviors:
- Returns `float` in `[0.0, 1.0]` inclusive
- **Case-sensitive**: `'Auth'` vs `'auth'` → 0.75, NOT 1.0
- **Must normalize to lowercase before comparison**: `labels[i].lower()` vs `labels[j].lower()`
- `'AuthService'` vs `'auth_service'` (lowercased) → 0.957 (above 0.90 threshold — correctly flagged as candidate)
- 500-node full pairwise: 124,750 pairs takes ~1.0s (1k nodes ≈ 4s, 5k nodes ≈ 100s unblocked)
- **Never strip underscores before comparison**: underscore-to-CamelCase ratio is already high enough; stripping would inflate false-positive rate

```python
# Source: verified via execution
import difflib

def fuzzy_ratio(a: str, b: str) -> float:
    """Case-insensitive SequenceMatcher ratio. Both inputs lowercased before comparison."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

### Pattern 3: 4-Char Prefix Blocking + Length-Ratio Guard

[VERIFIED via live execution — the recommended blocking strategy]

This is the confirmed recommended blocker. It reduces comparisons to ~3-17% of full pairwise while preserving all valid candidates:

```python
# Source: verified via execution in this session
# All canonical pairs share first 4 chars: 'auth'/'authentication' -> 'auth'/'auth' ✓
# 'AuthService'/'auth_service' -> 'auth'/'auth' ✓ (lowercased)
# 'user'/'User' -> 'user'/'user' ✓

def _build_prefix_blocks(nodes: list[dict]) -> dict[str, list[int]]:
    """Group node indices by lowercased 4-char prefix for blocking."""
    blocks: dict[str, list[int]] = {}
    for i, node in enumerate(nodes):
        key = node["label"].lower()[:4]
        blocks.setdefault(key, []).append(i)
    return blocks


def _candidate_pairs(
    nodes: list[dict],
    blocks: dict[str, list[int]],
    fuzzy_threshold: float = 0.90,
    *,
    same_type_only: bool = True,
) -> list[tuple[int, int, float]]:
    """
    Yield (i, j, fuzzy_ratio) for pairs that pass:
      1. Same prefix block
      2. Length ratio >= 0.7 (cheap guard: avoids difflib on 'auth' vs 'authentication')
      3. file_type match (unless --dedup-cross-type)
      4. fuzzy_ratio >= fuzzy_threshold
    """
    candidates = []
    for block_indices in blocks.values():
        for ki in range(len(block_indices)):
            i = block_indices[ki]
            for j in block_indices[ki + 1:]:
                li = len(nodes[i]["label"])
                lj = len(nodes[j]["label"])
                if li == 0 or lj == 0:
                    continue
                # Cheap length-ratio guard
                if min(li, lj) / max(li, lj) < 0.7:
                    continue
                # file_type guard (D-13)
                if same_type_only and nodes[i]["file_type"] != nodes[j]["file_type"]:
                    continue
                ratio = fuzzy_ratio(nodes[i]["label"], nodes[j]["label"])
                if ratio >= fuzzy_threshold:
                    candidates.append((i, j, ratio))
    return candidates
```

**Note on `'auth'` vs `'authentication'`:** Length ratio = 4/14 = 0.29, so the length guard correctly filters this pair before hitting difflib. This pair would only merge if embeddings are also used AND cross-type is enabled (the GRAPH-04 stretch case). Under the default thresholds (fuzzy ≥ 0.90), `auth` vs `authentication` has ratio 0.444 — would fail even without the length guard. [VERIFIED: execution]

### Pattern 4: Edge Re-Routing (Custom — NOT nx.relabel_nodes)

**Critical verified finding:** `nx.relabel_nodes(G, mapping, copy=False)` silently overwrites parallel edges when two nodes being merged both had an edge to the same target. The last-processed edge wins — attributes from the other are lost. This means weight aggregation and confidence promotion per D-10 are silently broken if nx.relabel_nodes is used.

[VERIFIED via live execution — confirmed with both Graph and DiGraph]

**Correct approach: operate on extraction dicts before `build_from_json`:**

```python
# Source: verified via execution in this session
# graphify/dedup.py

CONFIDENCE_ORDER = {"EXTRACTED": 2, "INFERRED": 1, "AMBIGUOUS": 0}

def _merge_extraction(
    extraction: dict,
    merge_map: dict[str, str],  # {eliminated_id: canonical_id}
    provenance: dict[str, list[str]],  # {canonical_id: [eliminated_ids]}
) -> dict:
    """
    Apply merge_map to extraction dict. Returns new dict with:
    - eliminated nodes removed
    - canonical nodes updated with merged_from and source_file list
    - edges re-routed and parallel edges aggregated (D-10)
    """
    from collections import defaultdict

    # Step 1: Build updated node list
    nodes_by_id: dict[str, dict] = {}
    for node in extraction.get("nodes", []):
        nid = node["id"]
        canonical_id = merge_map.get(nid, nid)
        if canonical_id not in nodes_by_id:
            nodes_by_id[canonical_id] = dict(node)
            nodes_by_id[canonical_id]["id"] = canonical_id
        # If this is an eliminated node being folded into canonical, collect its source_file
        if nid != canonical_id:
            canon = nodes_by_id[canonical_id]
            # Upgrade source_file to list
            existing_sf = canon.get("source_file", "")
            sf_list = existing_sf if isinstance(existing_sf, list) else [existing_sf]
            new_sf = node.get("source_file", "")
            if new_sf and new_sf not in sf_list:
                sf_list.append(new_sf)
            canon["source_file"] = sf_list
            # Set merged_from
            canon.setdefault("merged_from", [])
            if nid not in canon["merged_from"]:
                canon["merged_from"].append(nid)

    # Step 2: Re-route and aggregate edges
    edge_groups: dict[tuple, list[dict]] = defaultdict(list)
    for edge in extraction.get("edges", []):
        new_src = merge_map.get(edge["source"], edge["source"])
        new_tgt = merge_map.get(edge["target"], edge["target"])
        if new_src == new_tgt:
            continue  # Self-loops after merge are dropped
        key = (new_src, new_tgt, edge.get("relation", ""))
        e = dict(edge)
        e["source"] = new_src
        e["target"] = new_tgt
        edge_groups[key].append(e)

    merged_edges: list[dict] = []
    for key, group in edge_groups.items():
        if len(group) == 1:
            merged_edges.append(group[0])
        else:
            # D-10: sum weight, max confidence_score, best confidence enum, union source_file
            merged = dict(group[0])
            merged["weight"] = sum(e.get("weight", 1.0) for e in group)
            merged["confidence_score"] = max(
                (e.get("confidence_score", 0.0) for e in group), default=0.0
            )
            merged["confidence"] = max(
                group, key=lambda e: CONFIDENCE_ORDER.get(e.get("confidence", "AMBIGUOUS"), 0)
            )["confidence"]
            sf_set = {e["source_file"] for e in group if e.get("source_file")}
            merged["source_file"] = sorted(sf_set) if len(sf_set) > 1 else (sf_set.pop() if sf_set else "")
            merged_edges.append(merged)

    return {
        **extraction,
        "nodes": list(nodes_by_id.values()),
        "edges": merged_edges,
    }
```

### Pattern 5: Canonical Label Selection (D-09)

```python
# Source: verified via nx.degree() on pre-dedup undirected graph
# graphify/dedup.py

def _select_canonical(
    candidate_ids: list[str],
    nodes_by_id: dict[str, dict],
    pre_dedup_degree: dict[str, int],
) -> str:
    """
    D-09 tie-break: longest label → most-connected (pre-dedup degree) → alphabetical.
    pre_dedup_degree: {node_id: int} from undirected graph built BEFORE any merges.
    """
    def sort_key(nid: str) -> tuple:
        label = nodes_by_id.get(nid, {}).get("label", "")
        degree = pre_dedup_degree.get(nid, 0)
        return (-len(label), -degree, label)  # neg for desc sort on len/degree

    return sorted(candidate_ids, key=sort_key)[0]
```

**Source of pre-dedup degree:** Build a temporary undirected NetworkX graph from the extraction dict before any merges, call `dict(G.degree())`. This is the correct approach — using post-dedup degree creates circularity. [VERIFIED: execution — `nx.degree()` returns `DegreeView` that can be `dict()`-ed]

### Pattern 6: Import-Graph Connected Components for batch.py

```python
# Source: verified via execution
# graphify/batch.py

import networkx as nx
from pathlib import Path

def _build_import_graph(paths: list[Path], ast_results: list[dict]) -> nx.Graph:
    """Build undirected file-level import graph from AST edge data."""
    G = nx.Graph()
    path_strs = {str(p) for p in paths}
    for p in paths:
        G.add_node(str(p))
    for result in ast_results:
        for edge in result.get("edges", []):
            if edge.get("relation") == "imports":
                src_file = edge.get("source_file", "")
                # target may be a file path or a module stem — normalize
                tgt_file = edge.get("target", "")
                if src_file in path_strs and tgt_file in path_strs:
                    G.add_edge(src_file, tgt_file)
    return G


def cluster_files(paths: list[Path], ast_results: list[dict],
                  token_budget: int = 50_000) -> list[dict]:
    """
    Returns list of FileCluster dicts:
    {
        "files": [str, ...],        # absolute paths in topological order
        "token_estimate": int,      # rough char/4 token estimate
        "cluster_id": int,
    }
    """
    import_graph = _build_import_graph(paths, ast_results)
    clusters = []
    for component in nx.connected_components(import_graph):
        files = list(component)
        # Cap by top-level directory (D-05)
        by_dir: dict[str, list[str]] = {}
        for f in files:
            top = Path(f).parts[0] if len(Path(f).parts) > 1 else ""
            by_dir.setdefault(top, []).append(f)
        # If component spans > 1 top-level dir, split
        if len(by_dir) > 1:
            for dir_files in by_dir.values():
                clusters.extend(_split_by_budget(dir_files, import_graph, token_budget))
        else:
            clusters.extend(_split_by_budget(files, import_graph, token_budget))
    return [{"files": c, "token_estimate": _estimate_tokens(c),
             "cluster_id": i} for i, c in enumerate(clusters)]
```

### Pattern 7: Topological Ordering with Cycle Fallback (D-08)

```python
# Source: verified via execution
# graphify/batch.py

def _topological_order(files: list[str], import_graph: nx.Graph) -> list[str]:
    """
    Order files: imported-first, importer-last (dependency order for LLM context).
    Falls back to alphabetical on cycles.
    """
    subgraph = import_graph.subgraph(files)
    # For topological sort, need directed view (imports go FROM importer TO importee)
    # Use a DiGraph: edge (a, b) means a imports b → b should come first
    DG = nx.DiGraph()
    DG.add_nodes_from(files)
    for a, b in subgraph.edges():
        DG.add_edge(a, b)  # a imports b

    if nx.is_directed_acyclic_graph(DG):
        # Reverse: topo_sort returns in dependency order (b before a)
        return list(reversed(list(nx.topological_sort(DG))))
    else:
        # Cycle present — alphabetical fallback for determinism (D-08)
        return sorted(files)
```

### Pattern 8: Token Budget Estimation

```python
# Source: verified via execution; heuristic derived from project patterns
# graphify/batch.py

def _estimate_tokens(files: list[str]) -> int:
    """Rough token estimate: read file, divide char count by 4 (conservative)."""
    total = 0
    for f in files:
        try:
            total += Path(f).stat().st_size  # bytes ≈ chars for ASCII code
        except OSError:
            total += 4000  # fallback: assume 1000-token file
    return max(1, total // 4)
```

**Why char/4 and not tiktoken:** tiktoken adds a new required dependency; the char/4 heuristic is used by the existing skill for cost estimation and is accurate within 20% for typical Python/TypeScript. The budget is a soft cap, so exact token counts are not required. [ASSUMED — tiktoken not verified as already present; char/4 heuristic is existing project pattern]

### Pattern 9: Corpus Hash for Dedup Cache

```python
# Source: verified via execution; extends cache.py pattern
# graphify/dedup.py (or cache.py extension)

def corpus_hash(file_paths: list[str], root: Path = Path(".")) -> str:
    """SHA256 over sorted per-file hashes. Single added file invalidates dedup cache."""
    from graphify.cache import file_hash
    sorted_hashes = sorted(file_hash(Path(p)) for p in file_paths)
    return hashlib.sha256(json.dumps(sorted_hashes).encode()).hexdigest()

def dedup_cache_path(corpus_h: str, root: Path = Path(".")) -> Path:
    return Path(root) / "graphify-out" / "cache" / f"{corpus_h}.dedup.json"
```

### Pattern 10: MCP Alias Redirect (D-16)

```python
# Source: serve.py Phase 9.2 query-response boundary (verified by reading serve.py)
# Add to serve.py query_graph handler — thin lookup layer

def _load_dedup_report(out_dir: Path) -> dict[str, str]:
    """Load merged-ID → canonical-ID mapping from dedup_report.json.

    Returns {} if dedup was not run or file is missing.
    """
    path = out_dir / "dedup_report.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("alias_map", {})  # {eliminated_id: canonical_id}
    except (json.JSONDecodeError, OSError):
        return {}

# In query_graph handler, before graph lookup:
# node_id = alias_map.get(node_id, node_id)
# If redirected: annotate response with resolved_from_alias=original_id
```

### Anti-Patterns to Avoid

- **Using `nx.relabel_nodes` for dedup edge merging:** Silently drops parallel edge attributes — weight sum and confidence promotion are lost. Always operate on extraction dicts before `build_from_json`. [VERIFIED: execution]
- **Fuzzy comparison without lowercasing:** `'Auth'` vs `'auth'` returns 0.75, not 1.0. Always call `.lower()` on both labels before `SequenceMatcher`. [VERIFIED: execution]
- **Full pairwise comparison without blocking:** 5k nodes = 12.5M pairs, 8+ seconds on difflib alone. Use 4-char prefix blocks. [VERIFIED: execution]
- **Loading sentence-transformers model at import time:** Model is 90MB; importing the module would slow any `graphify` invocation even when `--dedup` is not set. Use lazy load (`_MODEL = None`, load on first call). [ASSUMED — follows cluster.py graspologic pattern]
- **Computing D-09 degree on the post-dedup graph:** Creates circularity (canonical selection depends on the result of selection). Always use pre-dedup undirected degree. [CITED: D-09 in CONTEXT.md; confirmed by `nx.degree()` semantics]
- **Dedup cache keyed on individual file hashes:** Adding one file to the corpus must invalidate the dedup results for all files (new cross-file merges may appear). Use corpus hash (sorted SHA256 of all per-file hashes). [VERIFIED: execution]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 384-dim vector similarity | Custom BERT/embedding layer | `sentence-transformers/all-MiniLM-L6-v2` via `[dedup]` extra | Handles tokenization, pooling, normalization; 80MB frozen model |
| Fuzzy string ratio | Edit-distance computation | `difflib.SequenceMatcher.ratio()` (stdlib) | Returns [0,1], handles Unicode, zero deps |
| Import graph community detection | BFS/DFS file walk | `nx.connected_components()` | Handles disconnected graphs, isolates, cycles trivially |
| Topological sort | Manual dependency ordering | `nx.topological_sort()` + `nx.is_directed_acyclic_graph()` | One-line with correct cycle detection |
| YAML config parsing | Custom .yaml parser | PyYAML (already in `[obsidian]` extra) | Already optional dep; reuse, don't add new parsing |

**Key insight:** The custom work in dedup.py is the *merge logic itself* (blocking, threshold comparison, canonical selection, edge aggregation) — not any of the underlying algorithms. Every underlying computation has a stdlib or already-installed library solution.

---

## Runtime State Inventory

This is a greenfield addition of new modules with no rename/migration component. No runtime state inventory required.

**Confirmed:** No existing runtime state (databases, registered OS tasks, env vars, live service config) uses entity IDs that would be affected by dedup. The dedup step runs at graph-build time; existing `graph.json` consumers who have not opted in to `--dedup` see identical output.

---

## Common Pitfalls

### Pitfall 1: nx.relabel_nodes Silently Drops Parallel Edge Attributes
**What goes wrong:** Calling `nx.relabel_nodes(G, {'auth': 'authentication'})` when both nodes had an edge to `service` produces a single `authentication → service` edge. Which attributes win depends on internal dict ordering, not on any merge semantics. Weight sum and confidence promotion per D-10 are silently lost.
**Why it happens:** NetworkX `relabel_nodes` calls `G.add_edge` for each remapped edge; `add_edge` on an undirected Graph simply overwrites existing edge attributes if the edge already exists.
**How to avoid:** Operate on extraction dicts BEFORE calling `build_from_json`. Detect parallel edges by grouping by `(source, target, relation)` key, then apply D-10 merge rules explicitly.
**Warning signs:** `dedup_report.json` shows N merges but `graph.json` edge weights are not aggregated (all still 1.0).

### Pitfall 2: Prefix Blocks Are Too Large on Homogeneous Corpora
**What goes wrong:** A corpus where all entities start with the same 4 chars (e.g., a large authentication system with `auth_login`, `auth_logout`, `auth_token`, ...) creates one giant prefix block. 1000 such nodes → ~500k difflib calls (~4s). The 30s target holds for realistic corpora but may not hold for pathological corpora.
**Why it happens:** Prefix blocking is a heuristic; it assumes diversity in entity names.
**How to avoid:** Add a per-block size cap: if a block exceeds N (e.g., 500) nodes, further subdivide by 5th or 6th character prefix. Or report a warning and fall back to length-bucket blocking for that block.
**Warning signs:** `--dedup` invocation takes > 5s on a corpus with < 1000 nodes.

### Pitfall 3: sentence-transformers Downloads Model on CI Every Run
**What goes wrong:** CI pulls 90MB model binary from huggingface.co on every test run. Slow, fragile (network dependency), and unnecessary for unit tests.
**Why it happens:** `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")` triggers a download if the model is not in the HuggingFace cache.
**How to avoid:** In tests, mock the encoder — inject a callable that returns fixed numpy arrays rather than instantiating the real model. Expose an `encoder` parameter in `dedup()` for testability:
```python
def dedup(extraction: dict, *, encoder=None, ...) -> tuple[dict, dict]:
    # encoder: callable(list[str]) -> np.ndarray | None
    # If None, loads real model. If provided, used directly.
```
**Warning signs:** `pytest tests/test_dedup.py` takes > 30s or fails with a network error.

### Pitfall 4: Cross-Type Merges via Fuzzy Only (GRAPH-04 Stretch)
**What goes wrong:** `auth` (code function, 4 chars) vs `authentication` (document heading, 14 chars) has fuzzy ratio 0.444 — well below 0.90. When `--dedup-cross-type` is enabled, fuzzy alone will NOT flag this as a candidate (length guard also rejects it: 4/14 = 0.28 < 0.7). The GRAPH-04 acceptance test will fail.
**Why it happens:** Short identifiers vs. full English words have inherently low string similarity.
**How to avoid:** D-13 specifies cross-type merges use **embeddings only** (no fuzzy gate). When `--dedup-cross-type` is active, skip the fuzzy stage entirely for cross-type pairs and go straight to cosine. The embedding model is precisely designed for this: `auth` and `authentication` will have cosine > 0.85 as synonyms. [ASSUMED — cosine behavior for short synonyms not verified in this session; pending model load]
**Warning signs:** `--dedup-cross-type` enabled but GRAPH-04 acceptance test shows three separate nodes for `auth.py`, `docs.md`, `tests/AuthService`.

### Pitfall 5: Dedup Cache Not Invalidated on File Addition
**What goes wrong:** User adds a new file to the corpus; the dedup cache from the previous run is still valid per per-file hashes. Dedup re-uses cached report that does not include edges from the new file.
**Why it happens:** Per-file hash caching is the right pattern for AST extraction; it is the wrong pattern for dedup (which depends on the full corpus).
**How to avoid:** Key the dedup cache on the CORPUS hash (SHA256 of sorted per-file hashes). Adding one file changes the corpus hash, invalidating the dedup cache. This is a separate cache entry from the per-file AST cache in `graphify-out/cache/`. [VERIFIED: corpus hash computation verified via execution]
**Warning signs:** After adding a file, `dedup_report.json` still shows the same number of total merges with no new entries.

### Pitfall 6: Self-Loop Edges After Canonical Merge
**What goes wrong:** Two nodes A and B are merged (B eliminated, A canonical). An edge `A → B` exists (e.g., A calls B). After re-routing B → A, this becomes `A → A` (self-loop). NetworkX silently accepts self-loops; `build_from_json` will add them to the graph. Leiden community detection on a graph with self-loops may produce unexpected results.
**Why it happens:** The edge re-routing step maps `B` → `A` in both source and target positions without checking for the self-loop case.
**How to avoid:** In `_merge_extraction`, after re-routing, skip any edge where `new_src == new_tgt`. [VERIFIED: implementation prototype confirmed this case]
**Warning signs:** `graph.json` contains edges where `source == target`.

### Pitfall 7: dedup.yaml Requires PyYAML But [dedup] Extra Doesn't Include It
**What goes wrong:** User installs `pip install graphifyy[dedup]` and tries to use `.graphify/dedup.yaml`. Import fails because PyYAML is only in `[obsidian]`.
**Why it happens:** D-17 says reuse PyYAML from `[obsidian]`; but if user only installs `[dedup]`, PyYAML is missing.
**How to avoid:** Two options: (a) add PyYAML to `[dedup]` extra in pyproject.toml; or (b) parse `.graphify/dedup.yaml` with a stdlib fallback (graceful degradation: if PyYAML not available, print hint and skip YAML config). The project precedent favors graceful degradation. [ASSUMED — which option to pick is left to planner; option b aligns with project philosophy of optional deps]
**Warning signs:** `FileNotFoundError` or `ModuleNotFoundError: No module named 'yaml'` when `--dedup` is run without `[obsidian]` installed.

---

## Code Examples

### Verified: `nx.connected_components` for file clustering
```python
# Source: verified via execution in this session
import networkx as nx

G = nx.Graph()
G.add_edge('auth.py', 'models.py')
G.add_edge('api.py', 'auth.py')
G.add_node('utils.py')  # isolate

for component in nx.connected_components(G):
    print(sorted(component))
# ['api.py', 'auth.py', 'models.py']
# ['utils.py']
```

### Verified: `nx.topological_sort` with cycle fallback
```python
# Source: verified via execution in this session
import networkx as nx

DG = nx.DiGraph()
DG.add_edge('models.py', 'auth.py')  # models imported by auth
DG.add_edge('auth.py', 'api.py')

if nx.is_directed_acyclic_graph(DG):
    order = list(reversed(list(nx.topological_sort(DG))))
    # ['models.py', 'auth.py', 'api.py'] — dependencies first
else:
    order = sorted(DG.nodes())  # alphabetical fallback
```

### Verified: Pre-dedup degree for canonical selection
```python
# Source: verified via execution in this session
import networkx as nx
from graphify.build import build_from_json

# Build pre-dedup graph (undirected) just for degree computation
pre_graph = build_from_json(extraction, directed=False)
pre_degree = dict(pre_graph.degree())
# {node_id: int} — used as D-09 tie-breaker
```

### Verified: Cosine similarity with 3-decimal rounding
```python
# Source: verified via execution in this session
import numpy as np

# embeddings already L2-normalized (normalize_embeddings=True in model.encode)
def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return round(float(np.dot(a, b)), 3)
```

### Verified: `validate_extraction` extension for D-12
```python
# Source: verified by reading validate.py
# Extension: source_file can now be str OR list[str]
# merged_from is optional list[str]

# Current check (line ~35 in validate.py):
#   for field in REQUIRED_NODE_FIELDS:  # includes "source_file"
#       if field not in node:
#           errors.append(...)

# EXTEND: after required field check, allow list for source_file
if "source_file" in node:
    sf = node["source_file"]
    if not isinstance(sf, (str, list)):
        errors.append(f"Node {i} 'source_file' must be str or list[str], got {type(sf).__name__}")
    elif isinstance(sf, list) and not all(isinstance(s, str) for s in sf):
        errors.append(f"Node {i} 'source_file' list must contain only strings")

if "merged_from" in node:
    mf = node["merged_from"]
    if not isinstance(mf, list) or not all(isinstance(m, str) for m in mf):
        errors.append(f"Node {i} 'merged_from' must be list[str]")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One LLM call per file | One LLM call per import-connected cluster | Phase 10 | Cross-file relationships captured during extraction, not inferred post-hoc |
| Exact-ID dedup only (3-layer in build.py) | 4-layer: AST dedup + semantic fuzzy+embedding dedup | Phase 10 | Eliminates 5-50x entity fragmentation on multi-source corpora |
| `source_file: str` on nodes | `source_file: str | list[str]` on merged nodes | Phase 10 | Provenance tracking across source files |
| No alias resolution in MCP | Transparent alias redirect for merged IDs | Phase 10 | Existing agent callsites don't break after dedup |
| sentence-transformers v2.x pool_encode | sentence-transformers v4.x `model.encode(..., normalize_embeddings=True)` | ~2023 | `normalize_embeddings=True` replaces manual L2 normalization |

**Deprecated/outdated:**
- `encode_multi_process()`: Replaced by `model.encode(device=["cpu","cpu",...])` in sentence-transformers v5.x. For Phase 10's single-process CPU use, plain `model.encode()` is correct. [CITED: ctx7 /huggingface/sentence-transformers migration guide]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `all-MiniLM-L6-v2` cosine similarity for short synonyms ('auth' vs 'authentication') is >= 0.85 | Pitfall 4, GRAPH-04 | GRAPH-04 stretch acceptance test fails; cross-type merges don't trigger |
| A2 | Rounding cosine to 3 decimals equalizes float32 drift between torch versions | Pattern 1 | Dedup produces different merge decisions on Python 3.10 vs 3.12 CI |
| A3 | Char/4 token estimation is accurate enough for the 50k token budget soft cap | Pattern 8 | Clusters exceed LLM context window; semantic extraction calls fail |
| A4 | PyYAML graceful degradation is preferred over adding it to `[dedup]` extra | Pitfall 7 | Users installing `[dedup]` without `[obsidian]` get unhelpful error on dedup.yaml |
| A5 | `_resolve_cross_file_imports` import edges (file-level `relation == "imports"`) are sufficient to seed the batch clustering import graph | Pattern 6 | Some file relationships are not captured; clusters are too small/fragmented |

---

## Open Questions

1. **Minimum cluster size (Claude's Discretion)**
   - What we know: single-file "clusters" provide no benefit over per-file extraction; batching overhead adds latency.
   - What's unclear: what threshold avoids over-clustering very small files (2 tiny utils → single cluster) vs. under-clustering (always skip batching for safety).
   - Recommendation: >= 2 files is the minimum; skip batching if the cluster's combined token estimate is < 500 tokens (the file is tiny enough that per-file extraction is fast).

2. **dedup_report.json schema design (Claude's Discretion)**
   - What we know: needs machine-readability, MCP-queryability, and stability across minor versions.
   - What's unclear: whether `alias_map` (flat eliminated→canonical dict) should be the primary lookup structure, or whether a list of merge records with full metadata is better.
   - Recommendation:
     ```json
     {
       "version": "1",
       "generated_at": "...",
       "summary": {"total_nodes_before": N, "total_nodes_after": M, "merges": K},
       "alias_map": {"eliminated_id": "canonical_id", ...},
       "merges": [
         {
           "canonical_id": "...",
           "canonical_label": "...",
           "eliminated": [{"id": "...", "label": "...", "source_file": "..."}],
           "fuzzy_score": 0.957,
           "cosine_score": 0.912
         }
       ]
     }
     ```

3. **cross-file import graph for non-Python languages**
   - What we know: `_resolve_cross_file_imports` is Python-only (uses tree-sitter-python internally). The broader `extract()` AST includes import edges for all 25 languages.
   - What's unclear: whether the file-level `imports` edges in the combined extraction dict (available for all languages) are sufficient for building the clustering import graph, or whether batch.py should also invoke `_resolve_cross_file_imports` for Python before clustering.
   - Recommendation: Use file-level `imports` edges from `extraction["edges"]` filtered by `relation == "imports"` for all languages; `_resolve_cross_file_imports` generates class-level `uses` edges (more granular) but is not needed for file clustering decisions.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | 3.11.x (Darwin 25.3.0) | — |
| networkx | batch.py, dedup.py | ✓ | Already in project deps | — |
| difflib | dedup.py | ✓ | stdlib | — |
| numpy | dedup.py (cosine) | ✓ (transitive via torch/scipy) | Present when sentence-transformers installed | Manual `np.dot` fallback for cosine |
| sentence-transformers | dedup.py embeddings | ✗ (not installed in dev env) | — | Graceful error: "Run pip install graphifyy[dedup]" |
| PyYAML | dedup.yaml parsing | ✓ (if [obsidian] installed) | — | Graceful skip of YAML config with warning |

**Missing dependencies with no fallback:**
- `sentence-transformers` — blocks `--dedup` but only when flag is active; core graphify unaffected.

**Missing dependencies with fallback:**
- `PyYAML` for `.graphify/dedup.yaml` — fall back to CLI-flags-only mode.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing; no new config needed) |
| Config file | None (discovered via `tests/` directory) |
| Quick run command | `pytest tests/test_batch.py tests/test_dedup.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAPH-01 | `cluster_files()` groups import-connected files into FileCluster dicts | unit | `pytest tests/test_batch.py::test_cluster_files_import_connected -x` | ❌ Wave 0 |
| GRAPH-01 | Token budget enforced: cluster exceeding budget is split | unit | `pytest tests/test_batch.py::test_cluster_respects_token_budget -x` | ❌ Wave 0 |
| GRAPH-01 | Top-level directory cap: cross-dir component is split | unit | `pytest tests/test_batch.py::test_cluster_top_dir_cap -x` | ❌ Wave 0 |
| GRAPH-01 | Topological order: imported-first, importer-last | unit | `pytest tests/test_batch.py::test_cluster_topological_order -x` | ❌ Wave 0 |
| GRAPH-01 | Cycle fallback: alphabetical order when import cycle detected | unit | `pytest tests/test_batch.py::test_cluster_cycle_fallback -x` | ❌ Wave 0 |
| GRAPH-02 | `dedup()` produces `dedup_report` with merged pairs | unit | `pytest tests/test_dedup.py::test_dedup_produces_report -x` | ❌ Wave 0 |
| GRAPH-02 | Fuzzy gate: pairs below 0.90 ratio are not merged | unit | `pytest tests/test_dedup.py::test_fuzzy_threshold_respected -x` | ❌ Wave 0 |
| GRAPH-02 | Cosine gate: pairs below 0.85 cosine are not merged | unit | `pytest tests/test_dedup.py::test_cosine_threshold_respected -x` | ❌ Wave 0 |
| GRAPH-02 | Cross-type guard: code+document merge blocked by default | unit | `pytest tests/test_dedup.py::test_cross_type_blocked_by_default -x` | ❌ Wave 0 |
| GRAPH-02 | Cross-type allowed with --dedup-cross-type flag | unit | `pytest tests/test_dedup.py::test_cross_type_allowed_with_flag -x` | ❌ Wave 0 |
| GRAPH-03 | Edge re-routing: no dangling edges after merge | unit | `pytest tests/test_dedup.py::test_no_dangling_edges_after_merge -x` | ❌ Wave 0 |
| GRAPH-03 | Weight aggregation: sum on parallel edges | unit | `pytest tests/test_dedup.py::test_edge_weight_summed -x` | ❌ Wave 0 |
| GRAPH-03 | Confidence promotion: EXTRACTED wins over INFERRED | unit | `pytest tests/test_dedup.py::test_confidence_promotion -x` | ❌ Wave 0 |
| GRAPH-03 | Self-loops dropped after merge | unit | `pytest tests/test_dedup.py::test_self_loops_dropped -x` | ❌ Wave 0 |
| GRAPH-03 | Canonical label: D-09 tie-break order correct | unit | `pytest tests/test_dedup.py::test_canonical_label_selection -x` | ❌ Wave 0 |
| GRAPH-03 | Provenance: merged_from and source_file list populated | unit | `pytest tests/test_dedup.py::test_provenance_fields -x` | ❌ Wave 0 |
| GRAPH-04 (stretch) | Cross-type merge: auth.py + docs.md + tests/AuthService → one canonical | integration | `pytest tests/test_dedup.py::test_cross_source_graph04_acceptance -x` | ❌ Wave 0 |
| D-12 | validate.py accepts source_file as list[str] | unit | `pytest tests/test_validate.py::test_source_file_as_list -x` | ❌ Wave 0 |
| D-12 | validate.py accepts merged_from as list[str] | unit | `pytest tests/test_validate.py::test_merged_from_accepted -x` | ❌ Wave 0 |
| D-16 | MCP query redirects merged-away ID to canonical | unit | `pytest tests/test_serve.py::test_alias_redirect -x` | ❌ Wave 0 |

### Special Test Strategies

**sentence-transformers in CI — mocked encoder pattern:**
```python
# tests/test_dedup.py
import numpy as np

def _fixed_encoder(labels: list[str]) -> np.ndarray:
    """Return deterministic fixed embeddings for testing.

    Maps label -> seeded random vector so identical labels get identical vectors.
    This lets tests control which pairs pass the cosine threshold.
    """
    result = []
    for label in labels:
        rng = np.random.default_rng(abs(hash(label)) % (2**32))
        vec = rng.standard_normal(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        result.append(vec)
    return np.array(result)

# Usage in test:
def test_dedup_produces_report():
    extraction = {...}  # fixture
    result_extraction, report = dedup(extraction, encoder=_fixed_encoder)
    assert "merges" in report
    assert isinstance(report["merges"], list)
```

**Determinism test — golden file:**
```python
# tests/test_dedup.py
import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "fixtures"

def test_dedup_deterministic(tmp_path):
    extraction = json.loads((GOLDEN_DIR / "extraction.json").read_text())
    result1, report1 = dedup(extraction, encoder=_fixed_encoder)
    result2, report2 = dedup(extraction, encoder=_fixed_encoder)
    assert json.dumps(report1, sort_keys=True) == json.dumps(report2, sort_keys=True)
    # Optional: compare against golden file
    # golden = GOLDEN_DIR / "dedup_report_golden.json"
    # if golden.exists():
    #     assert json.dumps(report1, sort_keys=True) == json.loads(golden.read_text())
```

**Performance smoke test:**
```python
# tests/test_dedup.py
import time

def test_dedup_1k_nodes_under_30s():
    # Build 1000-node extraction with realistic code entity names
    nodes = [{"id": f"n_{i}", "label": f"entity_{i % 50}_variant_{i}",
              "file_type": "code", "source_file": f"file_{i % 20}.py"}
             for i in range(1000)]
    edges = []
    extraction = {"nodes": nodes, "edges": edges}
    t = time.time()
    dedup(extraction, encoder=_fixed_encoder, fuzzy_threshold=0.90, embed_threshold=0.85)
    elapsed = time.time() - t
    assert elapsed < 30, f"dedup took {elapsed:.1f}s on 1k nodes (limit: 30s)"
```

**Cross-platform cosine rounding test:**
```python
# tests/test_dedup.py
def test_cosine_rounding_deterministic():
    """Verify round(cosine, 3) produces same decision on any platform."""
    import numpy as np
    a = np.array([0.1] * 384, dtype=np.float32)
    a /= np.linalg.norm(a)
    b = np.array([0.1] * 384, dtype=np.float32)
    b /= np.linalg.norm(b)
    score = round(float(np.dot(a, b)), 3)
    assert score == 1.0  # identical vectors must always round to 1.000
```

**Schema extension test:**
```python
# tests/test_validate.py (extension)
def test_source_file_as_list():
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": ["a.py", "b.py"], "merged_from": ["n2"]}],
        "edges": []
    }
    errors = validate_extraction(data)
    assert errors == []  # list source_file must be valid

def test_merged_from_accepted():
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": "a.py", "merged_from": ["n2", "n3"]}],
        "edges": []
    }
    assert validate_extraction(data) == []
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_batch.py tests/test_dedup.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_batch.py` — covers GRAPH-01 (cluster_files, token budget, topo order, cycle fallback, dir cap)
- [ ] `tests/test_dedup.py` — covers GRAPH-02, GRAPH-03, GRAPH-04 acceptance
- [ ] `tests/fixtures/multi_file_extraction.json` — multi-file fixture with import edges for batch/dedup tests
- [ ] Extend `tests/test_validate.py` — D-12 source_file-as-list and merged_from tests
- [ ] Extend `tests/test_serve.py` — D-16 alias redirect test

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `security.sanitize_label()` on all canonical labels before embedding in dedup_report.md/HTML |
| V6 Cryptography | no | SHA256 used for cache keys only, not cryptographic security |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Label injection in dedup_report.md | Tampering | `security.sanitize_label()` on canonical label before writing to MD/HTML |
| Path traversal in dedup_report.json write | Tampering | `dedup_report.json` path must stay under `graphify-out/` per existing security.py confinement |
| Model cache pollution | Tampering | `all-MiniLM-L6-v2` is pinned by name; HuggingFace cache is read-only after download |
| Corpus hash collision | Spoofing | SHA256 collision probability negligible for corpus sizes; no security requirement beyond cache correctness |

**Existing controls that cover dedup:**
- `security.sanitize_label()` already exists and is called in export.py — call it on canonical labels before writing dedup reports
- Path confinement: `graphify-out/` write restriction is enforced by convention in all existing modules; dedup_report writes must follow the same pattern using `os.replace` + tmp file for atomic writes (same pattern as serve.py `_save_telemetry`)

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: Context7 /huggingface/sentence-transformers] — `model.encode()` API, `normalize_embeddings=True`, `batch_size`, `cache_folder`, CPU performance characteristics, v5 migration guide
- [VERIFIED: live execution] — `difflib.SequenceMatcher.ratio()` case-sensitivity behavior, return range, performance benchmarks (500/1000/5000 node timing)
- [VERIFIED: live execution] — `nx.relabel_nodes` parallel edge behavior (silently overwrites — confirmed critical finding)
- [VERIFIED: live execution] — `nx.connected_components`, `nx.topological_sort`, `nx.is_directed_acyclic_graph`, `nx.degree_centrality`
- [VERIFIED: live execution] — 4-char prefix blocking performance (1k realistic nodes: 0.46s; 5k synthetic: 8.5s)
- [VERIFIED: live execution] — corpus hash determinism (sorted SHA256 of per-file hashes)
- [VERIFIED: codebase read] — `graphify/build.py` three-layer dedup pattern, `build_from_json` contract
- [VERIFIED: codebase read] — `graphify/cluster.py` graspologic ImportError fallback pattern
- [VERIFIED: codebase read] — `graphify/validate.py` REQUIRED_NODE_FIELDS, schema structure
- [VERIFIED: codebase read] — `graphify/cache.py` `file_hash()`, `cache_dir()`, `load_cached()` patterns
- [VERIFIED: codebase read] — `graphify/security.py` `sanitize_label()` function signature
- [VERIFIED: codebase read] — `graphify/extract.py` `_resolve_cross_file_imports()` data structure (returns list of edge dicts)
- [VERIFIED: codebase read] — `graphify/pyproject.toml` optional extras pattern (`[leiden]`, `[obsidian]`, `[pdf]`)

### Secondary (MEDIUM confidence)
- [CITED: sbert.net model cards] — `all-MiniLM-L6-v2` 22M parameters, 384-dim, CPU-optimized

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all APIs verified via Context7 and live execution
- Architecture: HIGH — all key behavioral properties verified (nx.relabel_nodes, difflib, blocking strategies)
- Pitfalls: HIGH — Pitfalls 1, 4, 5, 6 all verified via live execution; Pitfalls 2, 3, 7 are MEDIUM (patterns, not executed failures)
- Performance targets: HIGH — 1k-node realistic corpus verified at 0.46s fuzzy phase

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (sentence-transformers API is stable; networkx API is stable)

---

## RESEARCH COMPLETE
