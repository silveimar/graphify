# Phase 71: TEMP — Temporal Edge Validity — Research

**Researched:** 2026-05-07
**Domain:** Graph schema evolution / temporal metadata on edges
**Confidence:** HIGH for code-path mechanics (verified in repo), MEDIUM for decay-defaults tuning (no empirical data yet)

## Summary

Phase 71 adds three optional, additive edge attributes — `valid_from` (ISO-8601 UTC string), `valid_until` (string or `null`), and `decay_weight` (float in [0.0, 1.0]) — to every edge produced by `build.py`. Backward-compatibility is achieved by mirroring the read/write split that Phase 65 (CCONF-05) introduced for `schema_version` in `graphify/validate.py:231–258`: a write-mode validator demands the new fields on fresh writes; a read-mode validator tolerates their absence on legacy graphs. The single-source-of-truth `SCHEMA_VERSION` constant in `graphify/build.py:37` (currently `"1.13"`) bumps to `"2.0"`.

Supersession runs as a run-scoped diff over the existing on-disk `graphify-out/graph.json`: the build constructs the new edge set, loads the prior graph if present, and stamps `valid_until` on prior-INFERRED `(source, target, relation)` tuples that are absent from the new run. Superseded edges are appended back into the in-memory graph (history retained) and persisted via the normal `to_json` path. `analyze.py` adds a "currently valid" predicate (`d.get("valid_until") is None`) at the four edge-iteration sites.

Decay configuration loads from a new `graphify/temporal_config.yaml` shipped inside the package. PyYAML availability is guarded — when missing, in-code defaults take over so the core install (no `[routing]` extra) keeps working.

**Primary recommendation:** Implement TEMP-01 (schema fields + version bump) first as a Wave 0 foundation; TEMP-02 (decay) and TEMP-03 (supersession) can then layer on top in parallel. TEMP-04 (rendering) is last and depends on the prior three.

## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Timestamp format & source (TEMP-01):** ISO-8601 UTC wall-clock string per edge, e.g. `"2026-05-07T11:54:00+00:00"`. Single `datetime.now(timezone.utc).isoformat()` value evaluated **once per build run** and stamped on every edge. `valid_until` is `null` for currently-valid edges and the same ISO string when superseded.
2. **Decay config & shape (TEMP-02):** YAML at `graphify/temporal_config.yaml`. Per-relation entries `{function: exponential, half_life_days: <int>, floor: <float>}` with a `default:` fallback. Default function: exponential half-life `weight = max(floor, 0.5 ** (age_days / half_life_days))` with `half_life_days: 30`, `floor: 0.1`. EXTRACTED edges always `decay_weight = 1.0`.
3. **Decay loading:** PyYAML guarded — if unavailable OR file missing, fall back to in-code defaults so the core install works without the `[routing]` extra.
4. **Supersession match key (TEMP-03):** Global `(source, target, relation)` tuple across the entire run. Only previously-INFERRED edges are subject to supersession (EXTRACTED edges are not stamped).
5. **File-deletion rule (TEMP-03):** When a `source_file` is removed from the corpus, edges originally attributed to that file are stamped `valid_until` UNLESS the same `(source, target, relation)` is produced by another file in the current run (global rule wins).
6. **Persistence (TEMP-03):** Superseded edges remain in graph.json for history.
7. **Scoring exclusion (TEMP-03):** `analyze.py` god-node and surprising-connection scoring excludes edges with `valid_until != null` by default.
8. **Backward-compat (cross-cutting):** Read-tolerant, write-strict, mirroring Phase 65. Bump `SCHEMA_VERSION` from `"1.13"` to `"2.0"` in `graphify/build.py:37`.
9. **Migration:** Out of scope. Lazy on-read tolerance is sufficient.
10. **Temporal Health rendering (TEMP-04):** Minimal — counts only (currently-valid count, superseded count, % superseded). One short paragraph in GRAPH_REPORT.md.
11. **Wiki rendering (TEMP-04):** Per-community articles get a separate `## Historical relations` subsection at the bottom (omitted when empty), each entry annotated with `valid_until` date.

### Claude's Discretion

- Test-time clock injection mechanism (env var vs injectable arg vs monkeypatch fixture). **Researcher recommendation below: env-var override `GRAPHIFY_RUN_TS` + module-level `_now_iso()` helper that monkeypatch can target.**
- Exact `analyze.py` filter predicate locations.
- Per-relation default `half_life_days` tuning.
- Whether `cache.py` already supports the run-scoped edge-set diff.

### Deferred Ideas (OUT OF SCOPE)

- Decay-weight histogram, supersession timeline, top-N decayed relations table in GRAPH_REPORT.md (richer Temporal Health views).
- Explicit `graphify migrate` CLI command.
- Promoting PyYAML from `[routing]` extra to a core dependency.
- Per-relation half-life tuning by relation type beyond a single default (researcher may emit multiple defaults if obvious; otherwise leave as backlog).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEMP-01 | Edges carry `valid_from` and optional `valid_until` (null=currently valid); emitted via `validate.py`, persisted in `graph.json` | §Schema design, §Backward-compat read paths, §schema_version migration |
| TEMP-02 | `decay_weight` float ∈ [0,1]; EXTRACTED=1.0; INFERRED decays per-relation by `valid_from` age, configurable | §Decay function, §temporal_config.yaml shape, §PyYAML guard pattern |
| TEMP-03 | Re-run supersession: missing prior-INFERRED tuples → stamp `valid_until`; persist; exclude from scoring | §Supersession algorithm, §analyze.py predicate sites |
| TEMP-04 | Temporal Health subsection in `report.py`; historical-relations subsection in `wiki.py` | §Rendering hooks |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stamp `valid_from` on new edges | `build.py` | `extract.py` (origination) | Single run-clock per build → one stamp site |
| Stamp `valid_until` on superseded | `build.py` (new helper) | `cache.py` (priors source) | Diff is a build-time concern; cache only supplies prior set |
| Compute `decay_weight` | `build.py` (new helper) | `temporal_config.yaml` | Pure function of (relation, age_days, run_now); applied once at build |
| Validate temporal fields | `validate.py` | — | Schema checks live in one module by convention |
| Filter superseded for scoring | `analyze.py` | — | Owner of god-node / surprising-connection logic |
| Render Temporal Health | `report.py` + `wiki.py` | — | Existing rendering owners |
| Persist temporal fields | `export.py` (`to_json`, `to_graphml`, `to_cypher`, `to_obsidian`) | — | Per-format round-trip |

## Standard Stack

### Core (already in tree)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `datetime` (stdlib) | 3.10+ | `datetime.now(timezone.utc).isoformat()` for ISO-8601 timestamps | Stdlib — no new dep |
| `networkx` | unpinned | Edge attribute storage; `nx.Graph.edges(data=True)` already iterates attrs | Already core |
| `PyYAML` | optional `[routing]` | Parse `temporal_config.yaml` | Already optional in pyproject; **stay optional** per locked decision |

[VERIFIED: pyproject.toml; graphify/build.py:37; graphify/validate.py:231–258]

### New module (no new package)
| File | Purpose |
|------|---------|
| `graphify/temporal.py` | New module: `run_now_iso()`, `load_decay_config()`, `compute_decay_weight()`, `stamp_supersessions()`. Keeps `build.py` lean. |
| `graphify/temporal_config.yaml` | Package-shipped YAML with default decay params. Add to `pyproject.toml` `package-data` so `pip install` ships it. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ISO-8601 string | epoch int | int saves bytes but loses human readability and round-trips poorly through GraphML/Cypher; ISO is standard. [CITED: ISO-8601 is the de-facto JSON timestamp format] |
| YAML config | TOML in pyproject | TOML avoids PyYAML guard but mixes user-runtime config with package metadata — locked decision rejects this. |
| Inline in `build.py` | Separate `temporal.py` | Build is already 352 lines; new module aligns with project convention "one stage = one module". |

**Installation:** No new dependencies. Verify shipped YAML:
```bash
pip install -e ".[all]"
python -c "from importlib.resources import files; print(files('graphify').joinpath('temporal_config.yaml').read_text())"
```

**Version verification:** No external packages added. PyYAML is already at `pyproject.toml`'s `[routing]` extra (no version pin observed). [VERIFIED: pyproject.toml read]

## Architecture Patterns

### System Architecture Diagram

```
extract.py (per-file)         cache.py (load_cached)
       │                              │
       └──────► combined dict ◄───────┘
                       │
                       ▼
            build_from_json(extraction)
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
   _normalize_      stamp_      compute_
   concept_code   temporal_     decay_weights
   _edges()       fields()      (per edge)
   (existing)     (NEW)         (NEW)
            │          │          │
            └──────────┼──────────┘
                       ▼
            stamp_supersessions(             load prior graph.json (if exists)
              new_edges, prior_edges,  ◄──── via networkx.readwrite.json_graph.node_link_graph
              run_now)
                       │
                       ▼
            validate_extraction_for_write(data)
                       │
                       ▼
            nx.Graph G with G.graph["schema_version"]="2.0"
                       │
            ┌──────────┼──────────────┬──────────┐
            ▼          ▼              ▼          ▼
        analyze.py  report.py     wiki.py   export.py
        (filter     (Temporal    (Historical (round-trip
         valid_     Health)       relations) temporal
         until)                              fields)
```

### Recommended Project Structure
```
graphify/
├── temporal.py              # NEW: run-clock, decay, supersession helpers
├── temporal_config.yaml     # NEW: per-relation decay params
├── build.py                 # MODIFIED: SCHEMA_VERSION 1.13→2.0; call temporal hooks
├── validate.py              # MODIFIED: tolerate temporal fields read-mode; require write-mode
├── analyze.py               # MODIFIED: filter d.get("valid_until") is None at 4 sites
├── report.py                # MODIFIED: add ## Temporal Health subsection
├── wiki.py                  # MODIFIED: add ## Historical relations subsection
├── export.py                # MODIFIED: temporal fields round-trip in to_json/graphml/cypher/obsidian
└── cache.py                 # UNCHANGED — supersession reads graph.json, not cache files
tests/
├── test_temporal.py         # NEW: pure unit tests for run_now_iso, decay, supersession
├── test_validate.py         # MODIFIED: read/write split for temporal fields
└── test_build.py / test_export.py / test_analyze.py / test_report.py / test_wiki.py — augmented
```

### Pattern 1: schema_version read/write split (Phase 65 precedent)

**What:** Two validators — `validate_extraction_for_read` (tolerant) and `validate_extraction_for_write` (strict). Both delegate to the shared `validate_extraction()` for non-versioned checks; the write variant adds the version requirement.

**When to use:** Any new schema field that must be additive on read but mandatory on write.

**Existing example to mirror** [VERIFIED: graphify/validate.py:231–258]:
```python
def validate_extraction_for_read(data: dict) -> list[str]:
    """Read-mode: schema_version absent is OK (pre-1.13 legacy graphs)."""
    return validate_extraction(data)

def validate_extraction_for_write(data: dict) -> list[str]:
    """Write-mode: schema_version REQUIRED (every new graph must be stamped)."""
    errors = validate_extraction(data)
    if not isinstance(data, dict):
        return errors
    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv:
        errors.append("Missing required key 'schema_version' (write-mode)")
    return errors
```

**Phase 71 extension:** Inside `validate_extraction()` itself, treat `valid_from`, `valid_until`, `decay_weight` as **additive optional** edge fields (do NOT add to `REQUIRED_EDGE_FIELDS`). Inside `validate_extraction_for_write`, append:
```python
for i, edge in enumerate(edge_list):
    if "valid_from" not in edge:
        errors.append(f"Edge {i} missing required field 'valid_from' (write-mode)")
    # valid_until may be null OR ISO string — both OK
    # decay_weight: float [0,1]; 1.0 default for EXTRACTED, computed for INFERRED
    dw = edge.get("decay_weight")
    if not isinstance(dw, (int, float)) or not (0.0 <= float(dw) <= 1.0):
        errors.append(f"Edge {i} 'decay_weight' must be float in [0.0, 1.0] (write-mode)")
```

### Pattern 2: SCHEMA_VERSION single-source-of-truth (Phase 70.2-02 precedent)

[VERIFIED: graphify/build.py:36–38] The constant lives in `build.py`. `export.py:331–334` imports it. Bumping is one-line: `SCHEMA_VERSION = "2.0"`. The MCP server, query tooling, and downstream callers see the version through `G.graph["schema_version"]` stamped at lines 304–307 of `build.py` (build_from_json) and again at the top-level `build()` boundary.

### Pattern 3: Run-scoped clock injection

**Recommended hook (Claude's discretion):** Module-level `_now_iso()` helper in `graphify/temporal.py` plus an env-var override:

```python
# graphify/temporal.py
import os
from datetime import datetime, timezone

def run_now_iso() -> str:
    """Return ISO-8601 UTC timestamp for the current run.
    Tests may pin via GRAPHIFY_RUN_TS env var or monkeypatch run_now_iso directly.
    """
    pinned = os.environ.get("GRAPHIFY_RUN_TS")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()
```

This works in both `pytest`'s `monkeypatch.setenv` style and direct `monkeypatch.setattr("graphify.temporal.run_now_iso", lambda: "2026-01-01T00:00:00+00:00")`. **Call once at the top of `build_from_json` and pass the value down to stamping helpers** — do not call inside loops.

### Pattern 4: PyYAML guard

[VERIFIED: existing pattern in pyproject.toml — PyYAML in `[routing]` extra]
```python
def load_decay_config(path: Path | None = None) -> dict:
    """Load temporal_config.yaml; fall back to in-code defaults on missing/import-error."""
    defaults = {"default": {"function": "exponential", "half_life_days": 30, "floor": 0.1}}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return defaults
    cfg_path = path or files("graphify").joinpath("temporal_config.yaml")
    try:
        text = cfg_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return defaults
    try:
        loaded = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return defaults
    # Merge so 'default' is always present
    if "default" not in loaded:
        loaded["default"] = defaults["default"]
    return loaded
```

### Anti-Patterns to Avoid

- **Stamping `valid_from` per-edge with a fresh `datetime.now()` call:** introduces test flakiness and breaks "all edges stamped with same run timestamp" invariant. Compute once.
- **Storing `valid_from` as Python `datetime` in node attrs:** GraphML and JSON serialization will fail. Always use ISO strings end-to-end.
- **Adding temporal fields to `REQUIRED_EDGE_FIELDS`:** breaks read-mode legacy compat. Use the write-mode validator instead.
- **Dropping superseded edges from the graph:** TEMP-03 explicitly requires history retention.
- **Calling `compute_decay_weight()` in `analyze.py` / `report.py`:** decay must be computed once at build time and persisted; readers should trust the value.
- **Using `time.time()` or naive `datetime.utcnow()`:** the latter is deprecated in 3.12; use `datetime.now(timezone.utc)`. [CITED: PEP 615/python.org docs]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO-8601 formatting | Custom `f"{y}-{m}-{d}T..."` | `datetime.now(timezone.utc).isoformat()` | Stdlib handles offsets, sub-seconds, leap behavior |
| YAML parsing | Manual `:` splitter | `yaml.safe_load()` (guarded) | Avoid injection / arbitrary-tag bugs |
| Graph round-trip | Custom JSON walker | Existing `json_graph.node_link_data` (already used in `to_json`) | NetworkX preserves arbitrary edge attrs as-is |
| Run-scoped diff | New cache structure | Read prior `graphify-out/graph.json` via `nx.readwrite.json_graph.node_link_graph` | Simpler; matches `query` and `--obsidian` re-load pattern (`__main__.py:1962`) |

**Key insight:** `cache.py` indexes per-file extraction outputs, NOT per-run edge sets. Trying to compute global `(source, target, relation)` supersession from cache files would require reconstructing the full prior edge set anyway. **Just load the prior `graph.json`** — that's what `query` and `--obsidian` already do.

## Runtime State Inventory

> Phase 71 is additive schema work, not a rename. State inventory is light but tracked.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing `graphify-out/graph.json` files in user repos lack temporal fields. | Read-tolerance handles them. No data migration. (Optional `migrate` CLI is deferred per locked decision.) |
| Live service config | None. graphify is a CLI library; no running services. | None. |
| OS-registered state | None. | None — verified by absence of OS-level integration. |
| Secrets/env vars | New `GRAPHIFY_RUN_TS` env var (test-only override). Not a secret. | Document in CLAUDE.md / README. |
| Build artifacts | None. `temporal_config.yaml` ships in package; ensure `pyproject.toml` `[tool.setuptools.package-data]` lists it. | Add `"graphify": ["temporal_config.yaml"]` to package-data and reinstall after first build. |

**Cache compatibility note:** `cache.py` saves per-file extraction dicts (`{"nodes": [...], "edges": [...]}`) keyed by file SHA. **These cache files contain edges WITHOUT temporal fields** because temporal stamping happens at build time, not extraction time. After Phase 71 ships, existing cache files will replay through `build_from_json` and the build-time stamper will add `valid_from`/`decay_weight` on the fly. **No cache invalidation required.** [VERIFIED: graphify/cache.py — saves are pre-build-time]

## Common Pitfalls

### Pitfall 1: Forgetting to seed the supersession diff on a fresh run

**What goes wrong:** First run after upgrade has no prior `graph.json` ⇒ all edges look "new" ⇒ no supersession; correct. Second run with deleted file expects to find priors; if path resolution differs from the write path, the diff sees an empty prior set and silently skips supersession.

**How to avoid:** Use the same path resolution as `to_json` (i.e., the resolved output dir from `ResolvedOutput`). Test with both default and vault output modes.

### Pitfall 2: stderr-format regex in tests (v1.13 audit blind spot)

**What goes wrong:** `validate.py` adds new error strings; existing tests grep stderr for known prefixes. New errors land but the regex doesn't catch them. From STATE.md: prior phase audits flagged stderr-format snapshot drift (Phase 64).

**How to avoid:** Add explicit assertions for each new error message in `test_validate.py` (positive AND negative). Don't rely on a generic stderr regex.

### Pitfall 3: In-memory schema_version gap (Phase 70.2 audit)

**What goes wrong:** STATE.md observation 6614 — earlier code called `build_from_json` and never went through `export.to_json`, so `schema_version` was missing from in-memory graphs. Phase 70.2-02 fixed this by stamping at `build_from_json`/`build`. Phase 71 must NOT re-introduce the gap by adding a new code path that bypasses `build_from_json`.

**How to avoid:** All temporal field stamping must occur INSIDE `build_from_json`, not in a wrapper layered on top. Verify by asserting `G.graph["schema_version"] == "2.0"` in every test that constructs a graph.

### Pitfall 4: NetworkX edge-attr round-trip with `null` JSON values

**What goes wrong:** `valid_until: null` round-trips through `node_link_data` correctly, but `nx.write_graphml()` does not accept Python `None` as an attribute value — it raises `nx.NetworkXError`.

**How to avoid:** In `to_graphml`, transform `None` → empty string OR drop the attr from the graphml writer's view (using `H.copy()` and removing keys). [VERIFIED: graphify/export.py:1098-1112 already does `H = G.copy()`; extend that block to sanitize `valid_until=None` and any other None-valued temporal attrs before `nx.write_graphml`]

### Pitfall 5: Deterministic edge sort vs. timestamp tie-breaks

**What goes wrong:** `_normalize_concept_code_edges` sorts edges by `(source, target, relation)` for determinism. If two edges share the tuple but one is currently-valid and another superseded, the sort key alone can't disambiguate which one wins through `_merge_edge_fields`.

**How to avoid:** Make `_merge_edge_fields` aware that one of the merged edges may carry `valid_until != null` — preserve the **earliest** `valid_from` and the **latest** `valid_until` (or `None` if any input is current). Add a unit test for merge with mixed temporal status.

### Pitfall 6: Decay weight for AMBIGUOUS edges

**Locked decisions specify EXTRACTED=1.0, INFERRED decays.** AMBIGUOUS is unspecified. Default to: same decay as INFERRED (don't treat AMBIGUOUS as fresh-forever). Document in TEMP-02 plan.

## Code Examples

### Stamping temporal fields at build time
```python
# graphify/build.py — inside build_from_json, after _normalize_concept_code_edges
from .temporal import run_now_iso, load_decay_config, compute_decay_weight, stamp_supersessions

run_now = run_now_iso()
decay_cfg = load_decay_config()

# 1. Stamp valid_from / decay_weight on every new edge
for e in extraction["edges"]:
    e.setdefault("valid_from", run_now)
    e.setdefault("valid_until", None)
    if "decay_weight" not in e:
        if e.get("confidence") == "EXTRACTED":
            e["decay_weight"] = 1.0
        else:
            e["decay_weight"] = compute_decay_weight(
                relation=e.get("relation", ""),
                valid_from=e["valid_from"],
                run_now=run_now,
                config=decay_cfg,
            )

# 2. Supersession diff against prior on-disk graph
prior_path = Path(target_dir or Path.cwd()) / "graphify-out" / "graph.json"
extraction["edges"] = stamp_supersessions(
    new_edges=extraction["edges"],
    prior_graph_path=prior_path,
    run_now=run_now,
)
```

### Decay computation
```python
# graphify/temporal.py
from datetime import datetime

def compute_decay_weight(*, relation: str, valid_from: str, run_now: str, config: dict) -> float:
    cfg = config.get(relation, config["default"])
    if cfg["function"] != "exponential":
        return 1.0  # unknown function — fail open
    age_days = (datetime.fromisoformat(run_now) - datetime.fromisoformat(valid_from)).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    half_life = float(cfg["half_life_days"])
    floor = float(cfg["floor"])
    return max(floor, 0.5 ** (age_days / half_life))
```

### analyze.py filter sites

[VERIFIED: graphify/analyze.py — 4 edge-iteration sites]
- **Line 246** (`for u, v, data in G.edges(data=True)` inside `surprising_connections`): add `if data.get("valid_until") is not None: continue`
- **Line 336** (`for u, v, data in G.edges(data=True)` second cross-community pass): same filter
- **Line 408** (`for u, v, data in G.edges(data=True)` knowledge-gap analysis): same filter
- **`god_nodes` at line 76**: uses `G.degree()` which counts ALL edges. Need to compute degree manually over current-only edges OR use a subgraph view: `G_current = G.edge_subgraph((u,v) for u,v,d in G.edges(data=True) if d.get("valid_until") is None)`. **Use the subgraph approach** — it's one line and reuses NetworkX semantics.

### Persistence: to_json (already correct via NetworkX)
[VERIFIED: graphify/export.py:318–340] `nx.readwrite.json_graph.node_link_data(G, edges="links")` serializes ALL edge attrs including new ones. **No changes needed in to_json's edge loop**, only the schema_version stamp at line 334 already imports SCHEMA_VERSION from build.py — bump propagates automatically.

### Persistence: to_graphml
```python
# graphify/export.py — to_graphml, before nx.write_graphml
H = G.copy()
for u, v, data in H.edges(data=True):
    if data.get("valid_until") is None:
        # GraphML writer rejects None — sanitize
        del H.edges[u, v]["valid_until"]  # or set to ""
nx.write_graphml(H, output_path)
```

### Persistence: to_obsidian frontmatter
[VERIFIED: graphify/export.py:553–820 — to_obsidian renders nodes, not edges, into frontmatter] Edges in Obsidian appear as wikilinks in body. No frontmatter changes needed; **but** the `## Historical relations` subsection (TEMP-04) is added to community articles by `wiki.py`, separate from `to_obsidian`. Confirm whether the user runs `--obsidian` or the wiki path: both should render historical relations consistently.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecated naive utcnow | Use timezone-aware everywhere |
| Edges have only structural attrs | Edges carry temporal validity | Phase 71 (this) | Schema 2.0 |
| `schema_version` optional | required on write, optional on read | Phase 65 | Pattern reused here |

**Deprecated/outdated:**
- `datetime.utcnow()` — replaced everywhere with `datetime.now(timezone.utc)`. [CITED: docs.python.org datetime module]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `nx.write_graphml` rejects `None` attribute values | Pitfall 4 | LOW — easy to confirm with a 3-line test; if wrong, just skip the sanitization |
| A2 | Default `half_life_days: 30` is reasonable | Decisions §2 | MEDIUM — no empirical data; users may need to tune. Backlog already covers tuning. |
| A3 | Loading prior `graph.json` once per build is acceptable performance | Pattern 4 / Pitfall 1 | LOW — graph.json sizes are small (KB-MB); same load already happens in `query` / `--obsidian` paths |
| A4 | AMBIGUOUS edges should decay like INFERRED | Pitfall 6 | LOW — locked decisions are silent; documenting choice is sufficient |
| A5 | NetworkX preserves arbitrary edge attrs through `node_link_data` round-trip | Code Examples / Persistence | HIGH if wrong — but VERIFIED by inspection of existing `confidence_score` round-trip (export.py:326–329); same mechanism extends |

## Open Questions

1. **Per-relation half-life defaults beyond a single global default?**
   - What we know: locked decisions specify exponential half-life, default 30d, floor 0.1.
   - What's unclear: whether `semantically_similar_to` (LLM-derived, more volatile) should decay faster than `references` (mechanical doc-link, more stable).
   - Recommendation: Ship a single `default:` entry plus a stub `semantically_similar_to: {half_life_days: 14}` and document for follow-up tuning. Backlog item already exists.

2. **Vault-output supersession path:**
   - When user runs with `--obsidian` against a vault, does the prior `graph.json` live in the vault subdir or in the cwd `graphify-out/`?
   - Recommendation: Use `ResolvedOutput.source` to choose the prior-graph path identically to where `to_json` will write the new one. Add a test for both default and vault modes.

3. **Wiki rendering depends on per-community edge enumeration:**
   - `wiki.py:_community_article` iterates `G.edges[nid, neighbor]` for each node in the community. To render `## Historical relations`, a second pass is needed filtering `valid_until != None`.
   - Recommendation: Pass `historical_only=True` flag to `_community_article` (or split into two helpers). Trivial; mention in plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `datetime` | run-clock, decay age | ✓ | stdlib 3.10+ | — |
| Python `pathlib` | prior-graph load | ✓ | stdlib | — |
| NetworkX | graph manipulation | ✓ | already core | — |
| PyYAML | temporal_config.yaml parsing | ✗ in core / ✓ with `[routing]` | — | In-code defaults dict |
| `importlib.resources` | locating shipped YAML | ✓ | stdlib 3.10+ | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** PyYAML — falls back to in-code defaults per locked decision.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | none observed at root; pytest auto-discovers `tests/test_*.py` |
| Quick run command | `pytest tests/test_temporal.py tests/test_validate.py tests/test_build.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEMP-01 | New edges carry `valid_from` ISO-8601 string | unit | `pytest tests/test_build.py::test_build_stamps_valid_from -x` | ❌ Wave 0 |
| TEMP-01 | `valid_until` defaults to `None` for new edges | unit | `pytest tests/test_build.py::test_build_valid_until_none -x` | ❌ Wave 0 |
| TEMP-01 | Legacy graph.json without temporal fields loads without error | unit | `pytest tests/test_validate.py::test_legacy_graph_loads -x` | ❌ Wave 0 |
| TEMP-01 | Write-mode validator rejects edge missing `valid_from` | unit | `pytest tests/test_validate.py::test_write_requires_valid_from -x` | ❌ Wave 0 |
| TEMP-01 | `SCHEMA_VERSION == "2.0"` stamped on `G.graph` | unit | `pytest tests/test_build.py::test_schema_version_2_0 -x` | ❌ Wave 0 |
| TEMP-02 | EXTRACTED edges have `decay_weight == 1.0` regardless of age | unit | `pytest tests/test_temporal.py::test_extracted_no_decay -x` | ❌ Wave 0 |
| TEMP-02 | INFERRED edges decay per exponential half-life | unit | `pytest tests/test_temporal.py::test_inferred_exponential_decay -x` | ❌ Wave 0 |
| TEMP-02 | Decay floor respected | unit | `pytest tests/test_temporal.py::test_decay_floor -x` | ❌ Wave 0 |
| TEMP-02 | Missing PyYAML → in-code defaults | unit | `pytest tests/test_temporal.py::test_decay_config_no_yaml -x` | ❌ Wave 0 |
| TEMP-03 | Re-run stamps `valid_until` on missing prior INFERRED edge | unit | `pytest tests/test_temporal.py::test_supersession_inferred -x` | ❌ Wave 0 |
| TEMP-03 | Same tuple from another file → no supersession | unit | `pytest tests/test_temporal.py::test_supersession_global_rule -x` | ❌ Wave 0 |
| TEMP-03 | Superseded edges excluded from `god_nodes` | unit | `pytest tests/test_analyze.py::test_god_nodes_excludes_superseded -x` | ❌ Wave 0 |
| TEMP-03 | Superseded edges excluded from `surprising_connections` | unit | `pytest tests/test_analyze.py::test_surprising_excludes_superseded -x` | ❌ Wave 0 |
| TEMP-04 | GRAPH_REPORT.md contains "Temporal Health" subsection | unit | `pytest tests/test_report.py::test_temporal_health_section -x` | ❌ Wave 0 |
| TEMP-04 | Wiki community article renders "Historical relations" | unit | `pytest tests/test_wiki.py::test_historical_relations_section -x` | ❌ Wave 0 |
| TEMP-04 | Wiki omits historical subsection when empty | unit | `pytest tests/test_wiki.py::test_no_historical_when_empty -x` | ❌ Wave 0 |
| Round-trip | `to_json` preserves temporal fields | integration | `pytest tests/test_export.py::test_json_temporal_roundtrip -x` | ❌ Wave 0 |
| Round-trip | `to_graphml` handles `valid_until=None` | integration | `pytest tests/test_export.py::test_graphml_none_sanitized -x` | ❌ Wave 0 |
| Round-trip | `to_cypher` quotes ISO timestamps | integration | `pytest tests/test_export.py::test_cypher_temporal -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_temporal.py tests/test_validate.py -x -q` (~3s)
- **Per wave merge:** `pytest tests/test_build.py tests/test_validate.py tests/test_temporal.py tests/test_analyze.py tests/test_report.py tests/test_wiki.py tests/test_export.py -q`
- **Phase gate:** `pytest tests/ -q` must be green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_temporal.py` — NEW. Covers `run_now_iso`, `load_decay_config`, `compute_decay_weight`, `stamp_supersessions`. Pure unit tests with `monkeypatch` for clock pinning.
- [ ] No new conftest needed — existing `tmp_path` fixtures suffice.
- [ ] No framework install needed — pytest already in `[all]` extras.
- [ ] Verify `temporal_config.yaml` is included in `pyproject.toml` `package-data` so `tests/test_temporal.py::test_decay_config_loads_shipped` finds it.

## Security Domain

`security_enforcement` is enabled by default (no opt-out observed in config). Phase 71 is low surface-area for security:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — local CLI |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | `validate.py` extended for temporal fields; `yaml.safe_load` for config; `datetime.fromisoformat` rejects malformed strings |
| V6 Cryptography | no | n/a |

### Known Threat Patterns for graphify temporal layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious `temporal_config.yaml` (if user replaces shipped file) | Tampering | Use `yaml.safe_load` (NEVER `yaml.load`); the file is package-shipped, not user-configurable in v1 — document this in CLAUDE.md |
| `valid_from` with timezone-naive ISO string | Input Validation | `datetime.fromisoformat(...)` raises `ValueError` on malformed input; catch and treat edge as legacy (decay_weight=1.0) |
| `GRAPHIFY_RUN_TS` env var injected with non-ISO value | Input Validation | Validate before use; on failure, fall back to real `datetime.now()` and warn to stderr |
| Path confinement for prior `graph.json` load | Tampering | Use the same `ResolvedOutput` mechanism as `to_json` — already path-confined to `graphify-out/` per `security.py` |

## Project Constraints (from CLAUDE.md)

These directives bind Phase 71 plans:

- **Python 3.10+** — `datetime.now(timezone.utc)` is OK; no PEP 615 `zoneinfo` dependency needed for UTC.
- **No new required dependencies** — PyYAML stays optional; in-code defaults cover the no-PyYAML path.
- **Backward compatible** — graph.json without temporal fields must load. Mirrors locked decision.
- **Existing test patterns** — pure unit tests, no network, no FS side-effects outside `tmp_path`.
- **Security** — paths confined to output dir; sanitize template inputs (relevant for wiki / obsidian rendering of historical relations — escape `valid_until` strings).
- **PyPI package name `graphifyy`** — irrelevant for this phase but noted.
- **After modifying code, run `_rebuild_code` to refresh the graph** — applies to dev workflow, not the deliverable.
- **GSD workflow enforcement** — all edits must go through GSD commands.

## Sources

### Primary (HIGH confidence)
- `graphify/build.py` (full read) — SCHEMA_VERSION location, edge merge semantics, build_from_json control flow
- `graphify/validate.py` (full read) — read/write split pattern (lines 231–258), schema fields, error format
- `graphify/cache.py` (full read) — confirmed cache is per-file extraction, not run-scoped edge sets
- `graphify/export.py` (grep + targeted reads) — to_json schema_version stamp at line 334; to_graphml at 1098–1112; to_cypher at 354–367
- `graphify/analyze.py` (grep) — edge-iteration sites at lines 246, 336, 408; god_nodes at 76
- `graphify/report.py` (grep) — section structure for Temporal Health placement
- `graphify/wiki.py` (grep) — `_community_article` edge enumeration for Historical relations placement
- `.planning/REQUIREMENTS.md` (lines 13–18, 61–64) — TEMP-01..04 verbatim
- `.planning/ROADMAP.md` (lines 27–46) — Phase 71 success criteria
- `.planning/phases/71-temp/71-CONTEXT.md` — locked decisions
- `.planning/phases/71-temp/71-DISCUSSION-LOG.md` — decision provenance

### Secondary (MEDIUM confidence)
- STATE.md observations 6190, 6377, 6614, 6679, 6747 — Phase 65/70.2 precedent and v1.13 audit findings (referenced in pitfalls)

### Tertiary (LOW confidence)
- Default `half_life_days: 30` — locked from CONTEXT.md, but no empirical tuning data; flagged in Open Questions and Assumptions Log A2.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in tree; no version research needed
- Architecture: HIGH — patterns directly inherited from Phase 65 / 70.2 precedent (cited file/line)
- Pitfalls: HIGH — derived from documented v1.13 audit findings in STATE.md (stderr-format snapshot, in-memory schema_version) plus NetworkX behavior
- Decay defaults: MEDIUM — locked but unverified empirically (Assumption A2)
- Round-trip behavior: MEDIUM — extends pattern verified for `confidence_score` round-trip (Assumption A5)

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30-day estimate; underlying NetworkX/Python behavior is stable)
