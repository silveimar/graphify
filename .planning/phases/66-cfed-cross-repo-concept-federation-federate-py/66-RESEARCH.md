# Phase 66: CFED — Cross-Repo Concept Federation - Research

**Researched:** 2026-05-06
**Domain:** Build-pipeline graph merge (id-namespacing + multi-signal AND gate)
**Confidence:** HIGH (all decisions locked in CONTEXT; remaining work is mechanical wiring against verified call sites)

## Summary

Phase 66 introduces a new `graphify/federate.py` module called from `build_from_json` in `build.py` between `_normalize_concept_code_edges` and graph assembly. It namespaces every node id with `{repo}::` (local + each peer), reads each peer's prior `graph.json` (canonical name — see Open Question #1), runs an AND gate (label match + 1-hop label-Jaccard ≥ 0.5 + ≥1 shared source basename) to merge concept nodes, and emits a `federation-manifest.json` artifact plus a Federation section in `GRAPH_REPORT.md`. The whole feature is opt-in via repeatable `--federate-with PATH` and disabled by default.

All 12 architectural questions from the orchestrator have been answered against the live codebase — the only open question is artifact name (`graph.json` vs `export.json`) which the planner must resolve in Wave 0.

**Primary recommendation:** Implement as a single function `federate(graph: nx.Graph, peers: list[Path], *, repo_label: str) -> tuple[nx.Graph, dict]` returning `(merged_graph, manifest_payload)`. Call it from `build_from_json` AFTER `_normalize_concept_code_edges` returns and BEFORE the `nx.Graph` is constructed, by namespacing the in-memory `nodes`/`edges` dict lists. Thread `--federate-with` through CLI → `run_corpus` → `build_from_json` via a new optional kwarg. Manifest writer uses `default_graphify_artifacts_dir(target, resolved=resolved)` from `graphify/output.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-66.1 — CLI invocation**
- Repeatable `--federate-with PATH` on `graphify run`. PATH points at a peer repo's `graphify-out/` directory.
- Default behavior unchanged when flag absent (CFED-01).
- No new config file (`.graphify/federate.yaml` rejected).

**D-66.2 — Peer artifact**
- Federation reads each peer's existing `graphify-out/export.json` (per CONTEXT — but see Open Question #1: actual file is `graph.json`).
- No new producer-side artifact, no peer re-extraction.
- If peer artifact missing/unreadable → two-line stderr per Phase 64 contract.

**D-66.3 — Repo namespace label**
- `{repo}` = `basename(parent_of_PATH)` of `--federate-with` arg.
- Local repo = basename of current run's project root.
- Collision policy: hard-fail with two-line stderr; no implicit suffixing.
- Alias syntax (`PATH=ALIAS`) deferred.

**D-66.4 — Multi-signal merge gate (AND of all three)**
1. Label: case-folded exact match.
2. Neighborhood Jaccard ≥ 0.5 over 1-hop neighbor labels (case-folded, label-based not id-based).
3. Source-path overlap: ≥1 shared `source_file` basename.
- Tiebreaker (T-66.4): higher mean Phase 65 `confidence_score` across contributing INFERRED edges. Otherwise unused.

**D-66.5 — Manifest**
- Path: `{vault_aware_artifacts_dir}/federation-manifest.json` via `default_graphify_artifacts_dir()`.
- Format: stdlib `json`, no new deps.
- Lifecycle: rewritten each run.
- Schema: full provenance per merged-concept entry; `tiebreaker_score` only when fired.

**D-66.6 — GRAPH_REPORT.md Federation section**
- Placement: after Communities, before Calibration.
- Markdown table: Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker.
- Zero merges → section omitted.

**D-66.7 — Pipeline placement & invariants**
- New module `graphify/federate.py` exposing single entrypoint.
- Called from `build.py` after `_normalize_concept_code_edges`, before cluster.
- Preserves Phase 53 concept↔code edge contract.
- All ids namespaced before federation runs; canonical merged id = lex-min across namespaced contributing ids.

### Claude's Discretion
*(None enumerated; constraints are tight.)*

### Deferred Ideas (OUT OF SCOPE)
- `--federate-with PATH=ALIAS` syntax for explicit namespace overrides.
- Append-only `federation-history.jsonl` (deferred to Phase 67 CDRIFT).
- `.graphify/federate.yaml` declarative manifest.
- Hard floor on `confidence_score` for low-confidence neighbors.
- Auto-derivation of repo label from peer's PROJECT.md / pyproject metadata.
- Bullet/verbose Federation rendering for small-N.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFED-01 | Default-off; `--federate-with` flag activates federation | Argparse plumbing in `__main__.py:3083` (cmd=="run"); add `action="append"` parser inside the existing parse-loop; thread through `run_corpus`/`build_from_json`. Backward compat verified by every existing `build_from_json` test in `tests/test_build.py` (no kwarg passed → no federation runs). |
| CFED-02 | Deterministic, no embeddings, no LLM | All gate signals are pure-stdlib: case-folded string equals, set-Jaccard, basename comparison via `pathlib.PurePosixPath.name`. Tiebreaker is `statistics.mean()` over Phase 65 `confidence_score` floats. Lex-min canonical id is `min(ids)`. No new deps. |
| CFED-03 | ID-namespacing + multi-signal AND merge | Namespacing pattern: rewrite `node["id"]` → `f"{repo}::{old_id}"` and rewrite every edge's `source`/`target` in lock-step BEFORE constructing `nx.Graph`. Operates on the dict lists `extraction["nodes"]` / `extraction["edges"]` already mutated by `_normalize_concept_code_edges`. AND gate over candidate pairs (one local concept × one peer concept matching by case-folded label). |
| CFED-04 | Provenance manifest at vault-aware path | `default_graphify_artifacts_dir(target, resolved=resolved)` in `graphify/output.py:54` is the canonical resolver. Phase 63 Option B routes vault CWDs to `<vault>/.graphify-out/`. Phase 48 HYG-05 routes non-vault to cwd-relative `graphify-out/`. Schema documented in CONTEXT D-66.5. Use `json.dumps(payload, indent=2, sort_keys=True)` + `os.replace` atomic write (mirror `_write_repo_identity_sidecar` in export.py:308). |
| CFED-05 | Federation section in GRAPH_REPORT.md (omit on zero merges) | Splice in `report.py` between line 252 (`## Communities` block ends after community loop) and line 175 (`## Calibration` — but Calibration currently appears BEFORE Communities; see Pitfall #2). Pattern matches calibration's "skipped on insufficient data" approach: `if not merges: pass` (no `## Federation` line emitted). |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI flag parsing (`--federate-with PATH`, repeatable) | CLI / `__main__.py` | — | Single dispatch site at `cmd == "run"` (line 3083). |
| Peer artifact loading (`graph.json` JSON parse) | `federate.py` | — | New module owns peer I/O; `validate_extraction_for_read` from `validate.py` reused. |
| ID-namespacing of local + peer dicts | `federate.py` | — | Operates on plain dict lists (pre-`nx.Graph`). |
| Merge candidate scoring & AND gate | `federate.py` | — | Pure functions; no external state. |
| Tiebreaker (mean confidence_score) | `federate.py` | — | Reads Phase 65 edge attribute; no Phase 65 code modified. |
| Manifest write | `federate.py` | `output.py` (resolver) | Atomic JSON dump under vault-aware artifacts dir. |
| Graph mutation hand-off | `build.py` | `federate.py` | `build_from_json` calls federate then constructs `nx.Graph` from rewritten dicts. |
| Report section render | `report.py` | — | Reads `federation-manifest.json` from artifacts_dir if present; otherwise omits. |
| Stderr breadcrumbs (load failures, collisions) | `output.py` helpers (`_emit_vault_error` pattern) | `federate.py` | Reuse two-line `[graphify] error: ... / hint: ...` shape (Phase 64 contract). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `networkx` | (no pin, latest stable) | Graph data structure | Already the project's primary graph abstraction; `relabel_nodes` is the documented API for id rewrites. [VERIFIED: graphify/build.py:21] |
| `json` (stdlib) | 3.10+ | Read peer artifact, write manifest | CONTEXT D-66.5 explicitly requires stdlib only. [VERIFIED: CONTEXT.md] |
| `pathlib` (stdlib) | 3.10+ | Path resolution, basename extraction | Already used everywhere in graphify. [VERIFIED: codebase] |
| `statistics` (stdlib) | 3.10+ | `mean()` for tiebreaker score | Standard for arithmetic mean of small float lists. [ASSUMED — could also use sum/len; trivial] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `graphify.output.default_graphify_artifacts_dir` | internal | Vault-aware artifacts path | ALWAYS for manifest write. [VERIFIED: graphify/output.py:54] |
| `graphify.validate.validate_extraction_for_read` | internal | Peer artifact schema check | Run BEFORE namespacing peer nodes. [VERIFIED: graphify/validate.py:233] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `nx.relabel_nodes(G, mapping)` | Rewrite dict lists pre-construction | Dict-list rewrite is simpler — federate runs BEFORE `nx.Graph` exists in `build_from_json`. Avoids `relabel_nodes` edge-attribute corner cases. [VERIFIED: build.py:215-260 — graph constructed AFTER normalize] |
| Single peer at a time | Process all peers in one pass | Single-pass needed for transitive merges (concept appearing in repo A and B both merge into local). |

**No new packages installed** — pyproject.toml unchanged.

**Version verification:** Not applicable; no new dependencies.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌────────────────────────────┐
                    │ CLI: graphify run          │
                    │   --federate-with peer1/   │
                    │   --federate-with peer2/   │
                    └──────────────┬─────────────┘
                                   │ (list of paths)
                                   ▼
                    ┌────────────────────────────┐
                    │ run_corpus / skill         │
                    │   detect → extract         │
                    └──────────────┬─────────────┘
                                   │ (extraction dict)
                                   ▼
                    ┌────────────────────────────┐
                    │ build_from_json(extraction,│
                    │   federate_with=[...])     │
                    │                            │
                    │ 1. _normalize_concept_code │
                    │    _edges(nodes, edges)    │
                    │ 2. ── NEW STEP ──          │
                    │    federate(nodes, edges,  │
                    │      peers, repo_label)    │
                    │      ├─ namespace local ids│
                    │      ├─ load peers (json)  │
                    │      ├─ namespace peer ids │
                    │      ├─ merge by AND gate  │
                    │      ├─ rewrite edges      │
                    │      └─ write manifest     │
                    │ 3. validate_extraction     │
                    │ 4. build nx.Graph          │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌────────────────────────────┐
                    │ cluster.py (Leiden)        │
                    │   sees post-federation G   │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌────────────────────────────┐
                    │ report.py                  │
                    │   reads federation-        │
                    │   manifest.json,           │
                    │   renders Federation §     │
                    │   between Communities and  │
                    │   Calibration              │
                    └────────────────────────────┘
```

### Recommended Project Structure
```
graphify/
├── federate.py          # NEW — single new module (federate, _load_peer, _gate, _merge, _write_manifest)
├── build.py             # MODIFIED — accept federate_with kwarg, call federate after _normalize
├── __main__.py          # MODIFIED — argparse for --federate-with action="append"
├── pipeline.py          # MODIFIED (maybe) — pass federate_with through to build
├── report.py            # MODIFIED — render Federation section between Communities and Calibration
├── output.py            # UNCHANGED — already provides default_graphify_artifacts_dir
└── validate.py          # UNCHANGED — peer ingest reuses validate_extraction_for_read

tests/
├── test_federate.py     # NEW — unit tests for gate, namespace, merge, manifest, tiebreaker
├── fixtures/
│   ├── peer_match/      # NEW — peer graph.json that merges (full multi-signal agreement)
│   └── peer_nomerge/    # NEW — peer graph.json with label match but neighborhood divergence
```

### Pattern 1: ID-namespace via dict-list rewrite (BEFORE nx.Graph construction)
**What:** Rewrite `node["id"]` and every `edge["source"]`/`edge["target"]` in the in-memory dicts before `build_from_json` constructs the `nx.Graph`. Avoids `nx.relabel_nodes` and its edge-attribute pitfalls.
**When to use:** Always — federation runs at line ~215 of `build.py`, before `G = nx.Graph()`.
**Example:**
```python
# Source: graphify/build.py:213-215 (insertion point)
nodes_for_norm = [n for n in extraction["nodes"] if isinstance(n, dict)]
_normalize_concept_code_edges(nodes_for_norm, extraction["edges"])
# >>> NEW: federation hook here <<<
if federate_with:
    from graphify.federate import federate_extraction
    federate_extraction(extraction, federate_with, repo_label, artifacts_dir)
errors = validate_extraction(extraction)
```

### Pattern 2: Two-line stderr (Phase 64 contract)
**What:** Every error path emits exactly two lines: `[graphify] error: <msg>` then `  hint: <hint>`. Info path uses `info:` prefix.
**Example:**
```python
# Source: graphify/output.py:101 (_emit_vault_error)
print(f"[graphify] error: {msg}", file=sys.stderr)
print(f"  hint: {hint}", file=sys.stderr)
```
For federation, expose a thin helper in `federate.py` (do NOT reuse `_emit_vault_error` directly — it raises SystemExit; federate may want to error without vault-specific exit codes). Pattern:
```python
def _emit_federate_error(msg: str, hint: str) -> SystemExit:
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(1)
```

### Pattern 3: Atomic JSON manifest write
**What:** Write to `.tmp` sibling, fsync, then `os.replace`. Mirrors export.py's `_write_repo_identity_sidecar`.
**Example:**
```python
# Source: graphify/export.py:308-326
tmp = manifest_path.with_suffix(".json.tmp")
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, indent=2, sort_keys=True))
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
os.replace(tmp, manifest_path)
```

### Pattern 4: Section omission on empty (calibration precedent)
**What:** Calibration (Phase 65) section ALWAYS renders but says "skipped — insufficient INFERRED edges" on empty. Federation diverges: CONTEXT D-66.6 mandates **complete omission** on zero merges. Don't add the `## Federation` header at all.
**Example:**
```python
# Source: report.py — pattern adapted from calibration
manifest_path = artifacts_dir / "federation-manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    merges = manifest.get("merges", [])
    if merges:
        lines += ["", "## Federation", ""]
        lines += ["| Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker |",
                  "|---|---|---|---|---|"]
        for m in merges:
            lines.append(f"| {m['merged_id']} | {', '.join(c['repo'] for c in m['contributing'])} "
                         f"| {m['signals']['neighborhood_jaccard']:.2f} "
                         f"| {', '.join(m['signals']['shared_basenames'])} "
                         f"| {m.get('tiebreaker_score', '—')} |")
```

### Anti-Patterns to Avoid
- **`nx.relabel_nodes(G, mapping, copy=False)` on the partially-built graph:** would force federation to run AFTER `build_from_json` finishes, creating a two-pass flow. Stay in dict-land; relabel before construction.
- **Embedding repo-label in the original `id` (single-string concat without separator):** breaks reverse-mapping. Always use `::` (double-colon) — collision-free with existing graphify ids per `_make_id` slug rules (alphanumeric + underscore only).
- **Reading peer's `extraction.json` instead of `graph.json`:** `extraction.json` is pre-normalize, lacks community labels. CONTEXT says `export.json` but the actual canonical artifact written by `to_json` is `graphify-out/graph.json` (see Open Question #1 for resolution).
- **Iterating peers in CLI-supplied order for non-deterministic outputs:** sort peers by repo-label before merging; ensures lex-min canonical id is reproducible.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation of peer graph.json | Custom field check | `graphify.validate.validate_extraction_for_read(data)` | Already covers required fields + dangling edge tolerance + Phase 53 evidence rules. [VERIFIED: validate.py:233] |
| Vault-aware artifacts path | Hardcoded `Path("graphify-out")` | `graphify.output.default_graphify_artifacts_dir(target, resolved=resolved)` | Phase 63 Option B silent reroute will break otherwise. [VERIFIED: output.py:54] |
| Two-line stderr formatting | Custom `print` calls | Mirror `_emit_vault_error` shape | Phase 64 snapshot test will fail any deviation. [VERIFIED: tests/test_stderr_contract.py] |
| Atomic file write | `open + write + close` | Tmp + fsync + os.replace | Half-written manifest on crash corrupts subsequent runs. Pattern in export.py:308. [VERIFIED] |
| Repo label slugging | Custom regex | `Path(peer_path).resolve().parent.name` | Stdlib basename is sufficient per D-66.3. |

**Key insight:** Every adjacent concern (validation, paths, stderr, atomic IO) already has a battle-tested utility in graphify. The federation module should be a thin orchestrator over these.

## Runtime State Inventory

> Phase 66 is greenfield code addition (new module, new artifact, new CLI flag). No rename/refactor — section omitted per template guidance. The existing build pipeline behavior is unchanged when `--federate-with` is absent.

## Common Pitfalls

### Pitfall 1: Build pipeline call site is `build_from_json`, NOT `run_corpus`
**What goes wrong:** Plumbing `--federate-with` only as far as `run_corpus` (in `pipeline.py`) means federation never runs.
**Why it happens:** `graphify run` ends at extraction. `build_from_json` is called by the **skill orchestration** (and by `--obsidian` re-build path) — not by the `run` CLI command directly.
**How to avoid:** The CLI flag must reach `build_from_json` via two paths: (a) skill orchestration reads the flag from a sidecar / env / re-parsed argv, OR (b) plan adopts a simpler model: the `run` command stops at extraction and `--federate-with` is wired into a **separate** build invocation (likely the skill's `build_from_json` call). **Planner decision needed** — see Open Question #2.
**Warning signs:** All federation tests pass for `build_from_json` direct calls but the CLI integration test silently skips federation.

### Pitfall 2: report.py section ordering — Calibration appears BEFORE Communities, not after
**What goes wrong:** CONTEXT D-66.6 says "after Communities, before Calibration" but in current `report.py`:
- Line 175: `## Calibration`
- Line 208: `## Community Hubs (Navigation)`
- Line 252: `## Communities`
**Why it happens:** Phase 65 added Calibration high in the report (right after Summary), not at the end.
**How to avoid:** Either (a) move Calibration section per CONTEXT D-66.6, or (b) interpret "after Communities, before Calibration" as **render order in the file** — which means inserting Federation **between line 252 (Communities) and the end of the report**, NOT before line 175 Calibration. **Planner must clarify with user** in plan-time discuss step. Recommendation: insert Federation immediately after the Communities block (after line ~268) since Calibration is already above Communities; keep Calibration where it is.
**Warning signs:** Section ordering test fails OR user objects to Federation appearing after report's analytical sections.

### Pitfall 3: Edges to namespaced ids that don't exist post-merge
**What goes wrong:** When two concepts merge into a single canonical id, edges from peer that pointed to the old peer id become dangling.
**Why it happens:** Peer's `graph.json` references `peer::concept_x`; after merge the canonical id is `local::concept_x` (lex-min). The edge `peer::other → peer::concept_x` must be rewritten to `peer::other → local::concept_x`.
**How to avoid:** Build a `merge_map: dict[old_id, canonical_id]` and apply to ALL edges (peer + local) after merge gate runs. `validate_extraction` will silently drop unknown-target edges (per build.py:240, line "Edge does not match any node id" is a tolerated warning) — masking bugs.
**Warning signs:** Edge counts in manifest don't add up to local + peer edges minus internal-peer-edges removed by deduplication.

### Pitfall 4: `confidence_score` default for EXTRACTED edges
**What goes wrong:** Tiebreaker computes `mean(confidence_score)` over INFERRED edges only — but EXTRACTED edges have a default of 1.0 (per `_CONFIDENCE_SCORE_DEFAULTS` in export.py:286). Including them inflates the mean.
**Why it happens:** Phase 65 stamps all edges with `confidence_score`, but only INFERRED edges have meaningful values; EXTRACTED is always 1.0.
**How to avoid:** Filter to `confidence == "INFERRED"` BEFORE computing tiebreaker mean. CONTEXT D-66.4 says "across the contributing INFERRED edges" — honor strictly. If no INFERRED edges exist between the candidate concept and its neighbors, `tiebreaker_score` is omitted (per D-66.5 schema).
**Warning signs:** Tiebreaker fires on EXTRACTED-only neighborhoods (logically impossible — they're all 1.0).

### Pitfall 5: Peer artifact filename — `graph.json` vs `export.json`
**What goes wrong:** CONTEXT D-66.2 says "graphify-out/export.json" — but the canonical artifact written by `graphify.export.to_json` is `graphify-out/graph.json` (line 290, 652, 893 of __main__.py confirm this is the expected artifact name).
**Why it happens:** CONTEXT may have used "export.json" as a generic name for "the JSON written by export.py".
**How to avoid:** Plan adopts `graph.json` as the file read from peer. Document in PLAN that this resolves CONTEXT D-66.2 ambiguity.
**Warning signs:** Tests pass against fixture named `export.json` but real-world peers have `graph.json`.

### Pitfall 6: Cache invalidation
**What goes wrong:** `graphify/cache.py` keys on file SHA. Federation merges concepts post-extraction → does NOT alter any cached artifact. Peer changes between local runs (peer re-runs `graphify run`) → manifest is stale.
**Why it happens:** Federation manifest is rewritten each run (D-66.5), but peer's `graph.json` mtime is not part of any cache key.
**How to avoid:** Manifest is rewritten unconditionally each run; no cache layer involved. Document this in PLAN. (Phase 67 CDRIFT will likely tackle staleness via append-only history.)
**Warning signs:** N/A this phase.

### Pitfall 7: Cluster.py / Leiden determinism with namespaced ids
**What goes wrong:** Leiden's seed-based determinism (seed=42 per project notes) hashes node ids. Renaming `n_transformer` → `local::n_transformer` changes hash → potentially shifts community partitions for existing single-repo runs that DON'T pass `--federate-with`.
**Why it happens:** When `--federate-with` is absent, federation must NOT touch ids. Otherwise CFED-01 (default-off) is violated and existing test fixtures break.
**How to avoid:** `if not federate_with: skip federation entirely` — no namespacing, no manifest write. Existing test_build.py tests must pass unchanged.
**Warning signs:** test_build.py `test_nodes_have_label` checking `G.nodes["n_transformer"]` fails because id became `local::n_transformer`.

## Code Examples

### Namespacing extraction in-place
```python
# graphify/federate.py — sketch
def _namespace_extraction(extraction: dict, repo_label: str) -> None:
    """Rewrite node ids and edge endpoints in-place with `{repo}::` prefix."""
    prefix = f"{repo_label}::"
    for n in extraction["nodes"]:
        if isinstance(n, dict) and "id" in n:
            n["id"] = prefix + n["id"]
    for e in extraction["edges"]:
        if "source" in e:
            e["source"] = prefix + e["source"]
        if "target" in e:
            e["target"] = prefix + e["target"]
```

### Multi-signal AND gate
```python
def _gate(local_concept: dict, peer_concept: dict,
          local_neighbors: set[str], peer_neighbors: set[str]) -> tuple[bool, dict]:
    """Returns (passes, signals). All three signals must pass."""
    # Signal 1: case-folded label match
    label_l = local_concept.get("label", "").casefold()
    label_p = peer_concept.get("label", "").casefold()
    if not label_l or label_l != label_p:
        return False, {}
    # Signal 2: neighborhood Jaccard
    nbrs_l = {x.casefold() for x in local_neighbors}
    nbrs_p = {x.casefold() for x in peer_neighbors}
    if not nbrs_l or not nbrs_p:
        return False, {}
    inter = len(nbrs_l & nbrs_p)
    union = len(nbrs_l | nbrs_p)
    jaccard = inter / union if union else 0.0
    if jaccard < 0.5:
        return False, {}
    # Signal 3: shared source basenames
    bn_l = {Path(s).name for s in _split_sources(local_concept.get("source_file"))}
    bn_p = {Path(s).name for s in _split_sources(peer_concept.get("source_file"))}
    shared = bn_l & bn_p
    if not shared:
        return False, {}
    return True, {
        "label_match": local_concept["label"],
        "neighborhood_jaccard": round(jaccard, 4),
        "shared_basenames": sorted(shared),
    }
```

### Two-repo fixture (merge case)
```python
# tests/fixtures/peer_match/graph.json
{
  "schema_version": "1.13",
  "nodes": [
    {"id": "concept_attn", "label": "attention mechanism", "file_type": "document",
     "source_file": "paper.md"},
    {"id": "n_attention", "label": "MultiHeadAttention", "file_type": "code",
     "source_file": "model.py"}
  ],
  "links": [
    {"source": "n_attention", "target": "concept_attn", "relation": "implements",
     "confidence": "INFERRED", "confidence_score": 0.85, "source_file": "model.py"}
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pre-Phase 53: concept↔code edges merged opposite directions | Phase 53 D-53.05: only `implements/implemented_by` collapses; new four relations don't | Phase 53 (May 2026) | Federation must not violate this — namespaced edges keep their direction. |
| Pre-Phase 65: edges had no `confidence_score` | Phase 65 CCONF: every INFERRED concept↔code edge carries `confidence_score ∈ [0.0, 1.0]` | Phase 65 (May 2026) | Federation tiebreaker depends on this attribute; must filter to INFERRED. |
| Pre-Phase 63: outputs always under `<target>/graphify-out/` | Phase 63 VOPT Option B: vault CWD reroutes to `<vault>/.graphify-out/` | Phase 63 (May 2026) | Manifest path MUST go through `default_graphify_artifacts_dir`. |
| Pre-Phase 64: stderr format ad-hoc | Phase 64 AUDIT-A: locked two-line `[graphify] error/info: ... / hint: ...` | Phase 64 (May 2026) | Federation breadcrumbs must conform; snapshot test will catch deviations. |

**Deprecated/outdated:** None directly affected.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Peer artifact name is `graph.json`, not `export.json` (CONTEXT D-66.2) | Pitfall 5, Code Examples | Tests use wrong fixture name; real peers won't match. **Resolve in Wave 0.** |
| A2 | `build_from_json` is the right insertion point (CLI `run` only does extract; build happens in skill) | Pitfall 1 | If federation must trigger from CLI `run`, plumbing changes are larger. **Resolve in Wave 0.** |
| A3 | Federation section appears AFTER Communities and AFTER Calibration in render order (since Calibration is currently above Communities) | Pitfall 2 | User may want Calibration moved or Federation moved. |
| A4 | `statistics.mean()` is acceptable for tiebreaker (no clarification on rounding) | Stack table | Trivial — adopt 4-decimal rounding to match Jaccard precision. |
| A5 | `validate_extraction_for_read` should run on peer artifact before namespacing | Don't Hand-Roll | If peer artifact is partially malformed (legacy schema), strict validation may reject. Use `_for_read` (legacy-tolerant) not `_for_write`. |

## Open Questions

1. **Peer artifact filename: `graph.json` or `export.json`?**
   - What we know: `graphify.export.to_json` writes `graphify-out/graph.json` (verified across `__main__.py:290, 652, 893, 1366, etc.`). CONTEXT D-66.2 says `export.json`.
   - What's unclear: Is CONTEXT using "export.json" loosely?
   - Recommendation: Plan should adopt `graph.json` and call out this resolution at top of PLAN.md.

2. **Federation flag: passed to `run_corpus` (extract-only) or only to `build_from_json` (skill-driven)?**
   - What we know: `cmd == "run"` calls `run_corpus` which only does detect+extract. The `build_from_json` step is invoked by the skill orchestrator (or by `--obsidian` rebuild path).
   - What's unclear: Should `--federate-with` short-circuit if `graphify run` doesn't reach `build_from_json`?
   - Recommendation: Persist the federation flag list to a sidecar (`graphify-out/.federate-pending.json`) during `run_corpus`; have the skill read it during build. OR simpler: error loudly if `--federate-with` is passed to `run` without the skill orchestrator wired up. Resolve with user during planning.

3. **Section placement in `report.py`:** see Pitfall 2.

4. **Should `federation-manifest.json` include unmerged candidates (rejected by gate) for explainability?**
   - CONTEXT D-66.5 schema is silent. Recommendation: NO — keep manifest tight; rejected candidates can be derived from per-run logs. Defer to Phase 67 CDRIFT if needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core | ✓ | 3.10+ (CI: 3.10, 3.12) | — |
| networkx | Build pipeline | ✓ | already installed | — |
| stdlib `json`, `pathlib`, `statistics` | All federation logic | ✓ | bundled | — |
| pytest | Tests | ✓ | already installed | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`tests/conftest.py` already configured) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_federate.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFED-01 | Default-off: build_from_json without `federate_with` kwarg behaves identically to today | unit | `pytest tests/test_build.py -x` (existing fixtures must still pass) | ✅ |
| CFED-01 | `--federate-with` flag parses repeatable | unit | `pytest tests/test_federate.py::test_cli_repeatable -x` | ❌ Wave 0 |
| CFED-02 | Determinism: two runs with same inputs produce byte-identical manifest | unit | `pytest tests/test_federate.py::test_manifest_deterministic -x` | ❌ Wave 0 |
| CFED-02 | No new imports outside stdlib + networkx | unit | `pytest tests/test_federate.py::test_no_new_deps -x` (AST-scan federate.py) | ❌ Wave 0 |
| CFED-03 | Namespacing: all node ids gain `{repo}::` prefix; edges rewritten | unit | `pytest tests/test_federate.py::test_namespace -x` | ❌ Wave 0 |
| CFED-03 | AND gate: all-three-signals passes → merge | unit | `pytest tests/test_federate.py::test_gate_all_pass -x` | ❌ Wave 0 |
| CFED-03 | AND gate: any single signal fails → no merge | unit (3 cases) | `pytest tests/test_federate.py::test_gate_label_fail tests/test_federate.py::test_gate_jaccard_fail tests/test_federate.py::test_gate_basename_fail -x` | ❌ Wave 0 |
| CFED-03 | Tiebreaker: ties on Jaccard resolved by mean INFERRED confidence_score | unit | `pytest tests/test_federate.py::test_tiebreaker -x` | ❌ Wave 0 |
| CFED-03 | Canonical merged id = lex-min across contributing namespaced ids | unit | `pytest tests/test_federate.py::test_canonical_id -x` | ❌ Wave 0 |
| CFED-03 | Repo basename collision → hard error two-line stderr | unit | `pytest tests/test_federate.py::test_collision_error -x` | ❌ Wave 0 |
| CFED-04 | Manifest written to `default_graphify_artifacts_dir(...)` not hardcoded | unit | `pytest tests/test_federate.py::test_manifest_vault_aware -x` | ❌ Wave 0 |
| CFED-04 | Manifest schema matches D-66.5 (provenance, signals, optional tiebreaker_score) | unit | `pytest tests/test_federate.py::test_manifest_schema -x` | ❌ Wave 0 |
| CFED-04 | Atomic write (no partial manifest on simulated crash) | unit | `pytest tests/test_federate.py::test_manifest_atomic -x` | ❌ Wave 0 |
| CFED-05 | Federation section renders when manifest has merges | unit | `pytest tests/test_federate.py::test_report_renders_section -x` | ❌ Wave 0 |
| CFED-05 | Federation section omitted entirely on zero merges | unit | `pytest tests/test_federate.py::test_report_omits_on_zero -x` | ❌ Wave 0 |
| CFED-05 | Stderr breadcrumb on missing peer artifact conforms to Phase 64 contract | unit | `pytest tests/test_stderr_contract.py -x` (extend existing snapshot) | ✅ (extend) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_federate.py tests/test_build.py -q` (~5s)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_federate.py` — main test module covering all CFED-01..05 cases
- [ ] `tests/fixtures/peer_match/graph.json` — peer artifact that achieves all three gate signals (full merge)
- [ ] `tests/fixtures/peer_nomerge/graph.json` — peer with label match but neighborhood Jaccard < 0.5 (zero-merge case)
- [ ] `tests/fixtures/peer_collision_a/graph.json` and `peer_collision_b/graph.json` — same basename for collision test
- [ ] Extend `tests/test_stderr_contract.py` fixture with federation error breadcrumbs
- [ ] Extend `tests/test_report_calibration.py` style helpers for Federation section assertions (or add to `tests/test_federate.py`)

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** required (CI: 3.10 and 3.12) — federation code must use `from __future__ import annotations` and `dict[...]` style hints (not `Dict[...]`). [VERIFIED: graphify/build.py:24]
- **No new required dependencies** — federation may not add anything to `pyproject.toml` (stdlib + networkx only). [VERIFIED: CLAUDE.md "No new required dependencies"]
- **No formatter/linter configured** — match existing 4-space, no inline comments, docstrings on public functions style.
- **All external input through `security.py`** — peer PATH must be resolved with `Path(p).resolve()`; no SSRF/path-escape vector since federation reads only local filesystem (no URLs). Still, treat peer paths as untrusted: do not follow symlinks blindly.
- **Tests:** pure unit, no network, no fs side effects outside `tmp_path`.
- **PyPI package name `graphifyy`; CLI `graphify`** — internal references use `graphify`.
- **GSD workflow enforced** — file edits must be inside an active GSD command (this research is part of one).

## Sources

### Primary (HIGH confidence)
- `graphify/build.py` (full read, 307 lines) — confirmed insertion point at line ~215
- `graphify/output.py` (full read, ~250 lines) — `default_graphify_artifacts_dir` resolver at line 54
- `graphify/validate.py` (full read, 259 lines) — `validate_extraction_for_read` at line 233; required field sets
- `graphify/security.py` (full read) — atomic write pattern not present here, but `validate_graph_path` shows path-confinement idiom
- `graphify/report.py` (key sections, lines 145-265) — section ordering: Calibration at L175, Communities at L252
- `graphify/__main__.py` (key sections, lines 3083-3210) — `run` command argparse
- `graphify/pipeline.py` (full read) — `run_corpus` does NOT call `build_from_json`
- `graphify/export.py` (key sections, lines 285-340) — `to_json` writes `graph.json` via `node_link_data`; `_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}` at line 285; atomic write pattern at line 308
- `tests/test_build.py` (top, lines 1-50) — fixture pattern with `tests/fixtures/extraction.json`
- `tests/test_report_calibration.py` (top, lines 1-50) — calibration test pattern (templates federation tests)
- `tests/fixtures/extraction.json` — minimal 4-node fixture model
- `.planning/phases/66-cfed-cross-repo-concept-federation-federate-py/66-CONTEXT.md` (full read, 128 lines)

### Secondary (MEDIUM confidence)
- networkx documentation on `relabel_nodes` (training knowledge — verified semantics: `mapping` dict, `copy=True` default, edge attributes preserved)
- Phase 64 stderr contract test (`tests/test_stderr_contract.py`) — confirmed exists; format locked

### Tertiary (LOW confidence)
- None — every claim traces to a file read this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is stdlib or already-installed graphify modules.
- Architecture: HIGH — insertion point in build.py:215 is unambiguous; vault-aware path resolver verified.
- Pitfalls: HIGH — Pitfalls 1 and 2 (CLI plumbing, section ordering) are derived from direct file reads showing CONTEXT mismatches with current code.

**Research date:** 2026-05-06
**Valid until:** 2026-06-05 (30 days — graphify codebase is stable; only Phase 67 CDRIFT could affect manifest schema if it lands first.)

## RESEARCH COMPLETE
