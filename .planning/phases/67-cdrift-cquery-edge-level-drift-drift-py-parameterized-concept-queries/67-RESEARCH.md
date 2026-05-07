# Phase 67: CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries - Research

**Researched:** 2026-05-06
**Domain:** Snapshot persistence + community-membership Jaccard drift classification + MCP BFS filter parameters
**Confidence:** HIGH (codebase-internal patterns; all references verified by direct read)

## Summary

Phase 67 ships two backward-compatible features on top of well-established graphify infrastructure. Most of the substrate already exists: `graphify/snapshot.py` (Phase 11) provides atomic snapshot save/load/FIFO-prune, `graphify/delta.py` already computes per-node community migrations, and `graphify/federate.py::write_manifest` (Phase 66) is the canonical atomic-write reference. The two genuine deliverables are (1) a new `drift.py` that converts existing snapshot/delta primitives into **edge-level** drift classifications using community-membership **set Jaccard** at threshold 0.7, and (2) three new optional kwargs on `_run_concept_code_hops` that filter BFS results without mutating the v1.12 path.

The most consequential research findings are two pre-existing collisions the planner MUST resolve before writing PLAN.md:

1. **Snapshot path collision.** `graphify/snapshot.py` already writes to `graphify-out/snapshots/` (eight call-sites, including `enrich.py` and `serve.py::_run_drift_nodes`). CONTEXT.md D-01 specifies `graphify-out/cache/snapshots/`. These cannot both be true. **Recommendation:** Reuse the existing `graphify-out/snapshots/` directory and the existing `snapshot.save_snapshot` / `list_snapshots` / `load_snapshot` API rather than duplicating. The CONTEXT decision should be re-confirmed by the user — but the cost of a parallel directory is high (broken Phase 11 `_run_drift_nodes`, two sources of truth, retention races).
2. **Symbol collision on `drift`.** `serve.py` already exposes `_tool_drift_nodes` and `_run_drift_nodes` (Phase 11 SLASH-04 — per-node trend vectors over the snapshot chain). Phase 67 introduces edge-level drift classification on a single before/after pair. They are different signals. **Recommendation:** Name the new module `graphify/drift.py` (per CONTEXT) but namespace public functions to avoid confusion: `compute_edge_drift`, `classify_edges`, `match_communities_jaccard`. Keep Phase 11 behavior intact.

**Primary recommendation:** Reuse `graphify/snapshot.py` verbatim for snapshot lifecycle (D-01..D-03 already shipped); confine `drift.py` to pure analysis (Jaccard + edge classification) plus a pure renderer; add three optional kwargs to `_run_concept_code_hops` with strict `None`-default short-circuit so the v1.12 byte-identity contract holds.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Auto-snapshot on every successful `graphify run`; write to `graphify-out/cache/snapshots/`. Zero-friction; no opt-in flag. *(See collision flag above — recommend deferring to existing `graphify-out/snapshots/` per Phase 11.)*
- **D-02:** FIFO retention by mtime, keep last 10. No age-based policy.
- **D-03:** Snapshot writes use atomic `fsync + os.replace` (Phase 66 `federate.write_manifest` pattern).
- **D-04:** Set Jaccard on community membership (node-id sets); threshold **0.7 hardcoded**. ≥0.7 = `community-renamed`; <0.7 = `community-resharded`; missing endpoints = `orphaned`; otherwise `stable`.
- **D-05:** Threshold is a single hardcoded module-level constant in `drift.py`.
- **D-06:** Drift section sits AFTER Federation section in `GRAPH_REPORT.md` (Communities → Federation → Drift).
- **D-07:** 4-row summary table (`stable` / `community-renamed` / `community-resharded` / `orphaned` with edge counts) + per-class top-N=10 listing of `source → target` + relation for the three non-`stable` classes.
- **D-08:** When snapshot exists but current graph has zero `implements`/`documents`/`tests` edges, render `0/0/0/0` table with a "no drift edges to classify" note. Predictable section presence.
- **D-09:** When NO prior snapshot exists, omit the Drift section entirely (no header, no table).
- **D-10:** `confidence_band` enum = `"high"` (≥0.8) / `"medium"` (0.5 ≤ x < 0.8) / `"low"` (<0.5). To be sanity-checked against Phase 65 distribution. **Researcher recommendation: keep these cutpoints as-is — see Question 1 below.**
- **D-11:** `min_confidence` AND `confidence_band` → both must pass (AND semantics). Either may be `None` independently.
- **D-12:** `relations` whitelist. `None` = all relations traverse. `[]` = explicit zero-results (NOT silently "all").
- **D-13:** All three CQUERY params optional, default `None`; all-`None` BFS path MUST be byte-identical to v1.12 (CQUERY-02). Validation reuses `_validate_relations_arg` pattern at `serve.py:2246`.
- **D-14:** Frozen-fixture regression test: deep-equal JSON match against checked-in golden output.

### Claude's Discretion

- Internal data structures inside `drift.py` (snapshot file format, in-memory dataclasses). Constraint: atomic-write + JSON-serializable.
- Renderer location (`report.py` extend-in-place vs `drift_report.py` helper). Planner decides based on `report.py` size.
- Top-N=10 fixed in code as a small constant (no config knob).

### Deferred Ideas (OUT OF SCOPE)

- Coverage-lens query (D-3) — depends on CQUERY shipping first.
- Drift exposure via MCP / CLI subcommand.
- Age-based snapshot retention.
- User-tunable Jaccard threshold (env var / CLI flag).
- HTML viz of drift.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CDRIFT-01 | Drift compares snapshots via community-membership Jaccard, never names/IDs | §"Architecture Patterns: Jaccard matching"; existing `delta.py:32-41` shows membership map idiom |
| CDRIFT-02 | Each `implements`/`documents`/`tests` edge classified `stable`/`community-renamed`/`community-resharded`/`orphaned` | §"drift.py public API surface" — `classify_edges` semantics |
| CDRIFT-03 | GRAPH_REPORT.md gains Drift section when prior snapshot exists; absent ⇒ omit | §"report.py extension shape" — Federation pattern (lines 269-289) is direct template |
| CDRIFT-04 | Snapshots persist under `graphify-out/cache/snapshots/` w/ retention | **Collision flagged** — existing `graphify-out/snapshots/` already does this; reuse |
| CQUERY-01 | MCP `concept_code_hops` accepts `min_confidence`, `relations`, `confidence_band` | §"CQUERY filter integration point" — predicate at `serve.py:2326` (inside `_concept_code_hop_kind`) or post-classify in `_concept_code_hop_allowed` |
| CQUERY-02 | All-`None` call byte-identical to v1.12 | §"Frozen fixture" — `tests/fixtures/legacy_v1_12_graph.json` exists; needs golden output JSON committed |

---

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**, tested on 3.10 and 3.12.
- **Pure unit tests** in `tmp_path` only — no network, no fs side effects elsewhere.
- **Type hints** on all functions; `from __future__ import annotations` as first import.
- **Naming:** lowercase_with_underscores for files/functions/vars; private helpers `_underscore_prefixed`.
- **Stderr contract (Phase 64 AUDIT-02):** two-line `[graphify] error: <msg>\n  hint: <actionable>`.
- **All paths confined** to `graphify-out/` via `graphify/security.py` helpers.
- **One test file per module:** expect new `tests/test_drift.py`; extend `tests/test_serve.py` (or `tests/test_concept_code_hops.py`) and `tests/test_report*.py`.
- **No new required dependencies.**
- **GSD workflow:** All edits go through GSD commands; this phase uses TDD mode (see config: `tdd_mode: true`).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Snapshot persistence (write/list/load/prune) | `graphify/snapshot.py` (existing) | — | Already implements D-01..D-03 atomic write + FIFO prune |
| Snapshot file format (graph + community map) | `graphify/snapshot.py` (existing) | — | `node_link_data` + `{communities, metadata}` already defined |
| Community matching (Jaccard) | `graphify/drift.py` (NEW) | — | Pure math; no I/O; depends on community map only |
| Edge classification | `graphify/drift.py` (NEW) | — | Pure: takes (current G, prev snapshot) → DriftSummary |
| Drift section rendering | `graphify/report.py::generate` | — | Federation pattern (in-place kwarg) per CONTEXT D-06 |
| Pipeline wiring (auto-snapshot + drift compute) | `graphify/__main__.py::run` | — | Mirrors how `report.generate(federation_manifest=...)` is wired |
| CQUERY param validation | `graphify/serve.py` (next to `_validate_relations_arg`) | — | Same module, same idiom, same stderr error shape |
| CQUERY BFS filtering | `graphify/serve.py::_concept_code_hop_kind` (extend) or `_bfs_concept_code_from` (extend) | — | Predicate must short-circuit when all three are None |
| Frozen-fixture regression test | `tests/test_concept_code_hops_v112_compat.py` (NEW) | `tests/fixtures/legacy_v1_12_graph.json` (exists) + new golden JSON | One file per regression invariant |

---

## Standard Stack

### Core (already in tree, reuse)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | unpinned | Graph data structure | Project-wide primary abstraction `[VERIFIED: pyproject.toml]` |
| stdlib `json` | 3.10+ | Snapshot serialization | Already used by `snapshot.py:99` and `federate.py:381` `[VERIFIED: codebase grep]` |
| stdlib `os.replace` + `fsync` | 3.10+ | Atomic write | Reference pattern in `federate.py:417-426` `[VERIFIED]` |
| `networkx.readwrite.json_graph` | bundled | node_link_data round-trip | Already used by `snapshot.py:96` and `export.py` `[VERIFIED]` |

**No new dependencies required.** This phase is stdlib + existing modules only.

### Reusable Code (DO NOT REIMPLEMENT)

| Existing | Location | Reuse For |
|----------|----------|-----------|
| `save_snapshot(G, communities, project_root, cap=10)` | `snapshot.py:65` | CDRIFT-04 — already does atomic write + FIFO prune at cap=10 |
| `list_snapshots(project_root)` | `snapshot.py:48` | Locating prior snapshot for drift compute |
| `load_snapshot(path)` | `snapshot.py:172` | Hydrating prior snapshot back into `(G, communities, metadata)` |
| `auto_snapshot_and_delta(...)` | `snapshot.py:127` | Pattern — but emits GRAPH_DELTA.md (Phase 11), NOT GRAPH_REPORT drift section |
| `compute_delta(G_old, c_old, G_new, c_new)` | `delta.py:9` | Per-node migrations dict — partial overlap with drift but DOES NOT classify edges by Jaccard |
| `write_manifest` atomic pattern | `federate.py:399-432` | Reference if a parallel snapshot path is ever needed |
| `_validate_relations_arg` | `serve.py:2246` | Idiom for new `_validate_min_confidence_arg` and `_validate_confidence_band_arg` |
| `_concept_code_hop_kind` / `_concept_code_hop_allowed` | `serve.py:2204` / `serve.py:2230` | Predicate functions where filters short-circuit |
| `tests/fixtures/legacy_v1_12_graph.json` | exists | CQUERY-02 frozen fixture (already commits with v1.12 schema; 85 lines) |

---

## Architecture Patterns

### System Architecture Diagram (Phase 67 additions only)

```
graphify run pipeline
  │
  ├─ build_graph()       (existing)
  ├─ federate()          (Phase 66, existing)
  ├─ cluster()           (existing → produces communities map)
  ├─ analyze()           (existing)
  │
  ├─ NEW: drift.compute_edge_drift(G_current, snapshot_path_or_None)
  │      │
  │      ├─ load_snapshot(prev) → (G_prev, communities_prev)
  │      ├─ match_communities_jaccard(communities_prev, communities_current)
  │      │     → {prev_cid: matched_curr_cid_or_None}
  │      └─ classify_edges(G_current, communities_prev, match_map)
  │            → DriftSummary {stable, community_renamed,
  │                           community_resharded, orphaned}
  │
  ├─ report.generate(..., drift_summary=summary_or_None)
  │      └─ if drift_summary: render Drift section after Federation (D-06)
  │
  └─ NEW: drift.write_snapshot(G_current, communities_current)
          ├─ uses existing snapshot.save_snapshot (cap=10)
          └─ atomic fsync + os.replace (already in save_snapshot:108-114)

  Note: write_snapshot AFTER report.generate so the just-written snapshot
        does NOT influence the report it accompanies.
```

```
MCP concept_code_hops call
  │
  ├─ _validate_relations_arg(arguments.get("relations"))   (existing)
  ├─ NEW: _validate_min_confidence_arg(arguments.get("min_confidence"))
  ├─ NEW: _validate_confidence_band_arg(arguments.get("confidence_band"))
  │
  ├─ if all three are None → behave EXACTLY as v1.12 (no predicate cost)
  │   else → compose composite predicate
  │
  └─ _bfs_concept_code_from(G, ..., extra_predicate=composite_or_None)
        └─ at hop-classification step (_concept_code_hop_kind), if predicate
           is not None and predicate(edge_data) is False → return None
           (effectively the same short-circuit as `rel not in relations`)
```

### Recommended Project Structure

```
graphify/
├── snapshot.py        # EXISTING — reuse save_snapshot/load_snapshot/list_snapshots
├── delta.py           # EXISTING — node-level migrations (Phase 11); leave intact
├── drift.py           # NEW — edge-level Jaccard classification + write_snapshot wrapper
├── report.py          # EXTEND — add drift_summary kwarg to generate()
├── serve.py           # EXTEND — add 2 new validators + thread params into BFS
└── __main__.py        # EXTEND — pipeline wires drift compute → report → snapshot write

tests/
├── test_drift.py                          # NEW — pure unit tests for Jaccard + classification
├── test_concept_code_hops_v112_compat.py  # NEW — frozen-fixture byte-identity (CQUERY-02)
├── test_concept_code_hops.py              # EXTEND — new param validators + filter behavior
├── test_report.py                         # EXTEND — drift section rendering
└── fixtures/
    ├── legacy_v1_12_graph.json            # EXISTS — input for CQUERY-02
    └── legacy_v1_12_concept_code_hops_golden.json  # NEW — committed expected JSON output
```

### Pattern 1: Atomic write (already in snapshot.py)

```python
# Source: graphify/snapshot.py:108-114 (and graphify/federate.py:417-426 for fsync flavor)
tmp = target.with_suffix(".tmp")
try:
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, target)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

`federate.py:417-426` adds explicit `fh.flush(); os.fsync(fh.fileno())` before `os.replace` — this is the pattern CONTEXT D-03 calls out. `snapshot.save_snapshot` does NOT currently fsync. **Recommendation:** if reusing `save_snapshot`, add the fsync line for D-03 compliance, or wrap with a thin `drift.write_snapshot` that calls `save_snapshot` and is willing to be slightly redundant. Either is fine.

### Pattern 2: Federation section as direct template for Drift section

```python
# Source: graphify/report.py:269-289
if federation_manifest:
    lines += ["", "## Federation"]
    lines.append("| Merged Concept | Repos | Jaccard | ... |")
    lines.append("|---|---|---|---|---|")
    for entry in federation_manifest:
        ...
```

Drift section follows EXACTLY this shape, gated by `if drift_summary is not None`. Per D-09, `None` means no prior snapshot ⇒ no header. Per D-08, an empty (all-zeros) summary still renders.

### Pattern 3: BFS filter short-circuit (key for byte-identity)

The v1.12 path goes through `_concept_code_hop_kind` (serve.py:2204). The new filter must compose into this without changing return shape on the all-`None` path. Two options:

- **Option A (recommended):** add `extra_predicate: Callable | None = None` parameter to `_bfs_concept_code_from` and `_concept_code_hop_allowed`. When all three new args are `None`, predicate is `None` and the existing code path is structurally unchanged.
- **Option B:** add params to `_concept_code_hop_kind` and check inline. More invasive; harder to prove byte-identity.

**Decision: Option A.** This keeps the v1.12 codepath untouched at the byte level — only the function signature gains a defaulted kwarg. The `meta` dict produced for the response includes the new fields conditionally (omit when `None`) so JSON output is identical.

### Anti-Patterns to Avoid

- **Reimplementing `save_snapshot`** — `graphify/snapshot.py` already exists and is exercised by Phase 11 `_run_drift_nodes`. A second snapshot directory will diverge silently.
- **Putting Jaccard logic inside `delta.py`** — `delta.py` is node-level (Phase 11). Drift is edge-level. Separate module keeps responsibilities clean.
- **Adding new keys to `meta` envelope on the all-`None` CQUERY path** — breaks byte-identity. Conditionally include only when the corresponding param is non-`None`.
- **Treating empty `relations=[]` as "all relations"** — D-12 explicitly forbids this. The existing `_validate_relations_arg` errors on empty list with `"must not be empty; omit the parameter"` (serve.py:2266). The CQUERY semantics REVERSE this for the new `relations` kwarg per D-12: `[]` is valid and means "zero results". This is a behavior diff between the legacy validator and the new one. **Plan must NOT reuse `_validate_relations_arg` verbatim** — it must factor a new validator with `[]`-allowed semantics, OR re-spec D-12 to error on `[]` for consistency. Flag for planner/discuss.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Snapshot persistence | New writer in `drift.py` | `snapshot.save_snapshot` | Already atomic, FIFO-prunes, exercised by tests |
| Snapshot loading | Custom JSON parse | `snapshot.load_snapshot` | Handles networkx node_link_graph fallback for both `edges=` and legacy `links` shapes |
| Snapshot list | `glob` | `snapshot.list_snapshots` | Same mtime-sort + ProjectRoot guard against `graphify-out/graphify-out/` regression |
| Set Jaccard | Custom math | Inline `len(a & b) / len(a | b)` with `if union else 0.0` guard | One-liner; `federate.py:131-135` is the in-tree precedent |
| Atomic file write | Naive `open + write` | `tmp + os.replace` | `federate.py:417-426` is the canonical reference |
| Concept-code BFS | New BFS | `_bfs_concept_code_from` (serve.py:2290) | Already factored as pure helper; just add predicate kwarg |

---

## Runtime State Inventory

> Phase 67 is greenfield (new module + extensions to existing). No rename/refactor. **Skipped.**

---

## Common Pitfalls

### Pitfall 1: Empty-community Jaccard division-by-zero
**What goes wrong:** A community in either snapshot may have zero nodes after the `implements`/`documents`/`tests`-only filter (or pathologically after community split).
**Why it happens:** `0 / 0` raises `ZeroDivisionError`; `set() | set() = set()` so `len(union) == 0`.
**How to avoid:** Guard `if not union: return 0.0` (or treat as no-match). `federate.py:131-135` already does this.
**Warning sign:** Any code shaped `len(a & b) / len(a | b)` without an `if not union` guard.

### Pitfall 2: Phase 11 / Phase 67 snapshot directory split
**What goes wrong:** If Phase 67 writes to `graphify-out/cache/snapshots/` while Phase 11 reads from `graphify-out/snapshots/`, the `_run_drift_nodes` MCP tool silently sees only stale data.
**Why it happens:** CONTEXT D-01 specifies the new path without acknowledging the existing one.
**How to avoid:** Reuse `graphify-out/snapshots/`. If user insists on `cache/snapshots/`, migrate Phase 11 reader in the same commit.
**Warning sign:** Two `*.json` directories under `graphify-out/`, both holding NetworkX dumps.

### Pitfall 3: Byte-identity drift on `meta` envelope
**What goes wrong:** Adding `"min_confidence": null, "relations": null, "confidence_band": null` to the response `meta` dict on the all-`None` path changes the JSON byte-for-byte.
**Why it happens:** Default `json.dumps` includes None keys.
**How to avoid:** Conditionally `meta[k] = v` only when `v is not None`. The existing code already does this for `resolved_from_alias` (serve.py:2496) — same idiom.
**Warning sign:** The frozen-fixture deep-equal test fails on a diff that includes new keys with `null` values.

### Pitfall 4: `relations=[]` semantic conflict
**What goes wrong:** The existing `_validate_relations_arg` errors on empty list with stderr message; D-12 wants `[]` to mean "zero results" (no traversal).
**Why it happens:** Two different validators with different contracts share a parameter name.
**How to avoid:** Factor a new `_validate_cquery_relations_arg` (or rename the new param) that accepts `[]`. Decide explicitly which validator the MCP entry point uses. Flag for plan-checker.
**Warning sign:** Two functions named `_validate_relations_*` with conflicting empty-list rules.

### Pitfall 5: Drift compute reads the snapshot it just wrote
**What goes wrong:** If `drift.write_snapshot` runs before `drift.compute_edge_drift`, the "previous" snapshot IS the current graph and drift is always all-`stable`.
**Why it happens:** Pipeline ordering bug.
**How to avoid:** **Compute drift BEFORE writing the new snapshot.** The CONTEXT integration-points note (`__main__.py::run`) already calls this out: "call `drift.write_snapshot(...)` after `report.generate(...)`".
**Warning sign:** `list_snapshots` returns 1 result before drift compute on first run after Phase 67 ships → ALWAYS treat `len(prev_snaps) >= 1` (where the most recent is from a prior run, not the current one).

### Pitfall 6: Snapshot path collision with `_run_drift_nodes`
**What goes wrong:** Per Pitfall 2 — Phase 11's MCP tool stops working if path moves.
**How to avoid:** See §Pitfall 2 mitigation.

---

## Specific Research Questions Answered

### Q1. Confidence-band cutpoint sanity check (D-10 contingent)

**Recommendation: KEEP cutpoints `high ≥ 0.8`, `medium 0.5–0.8`, `low < 0.5`.**

Evidence from in-tree analysis:

- `graphify/export.py:302` defines `_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}`. So:
  - All `EXTRACTED` edges land at exactly `1.0` → solidly in `high`.
  - All `INFERRED` edges default to exactly `0.5` → first integer of `medium` (boundary inclusive on `0.5`).
  - All `AMBIGUOUS` edges default to `0.2` → solidly in `low`.
- Phase 65 calibration histogram (`report.py:18-25`) uses 10 bins over [0.0, 1.0] with `int(s * 10)`. The proposed cutpoints align with bin edges 5 and 8 — natural interpretive breakpoints, not arbitrary.
- Phase 65 calibration thresholds (`report.py`) treat `s < 0.5` as "negative" (`no_negatives` flag) — confirming `0.5` as the canonical low/non-low boundary.
- Phase 65 also flags "refusal" for scores `== 0.5` (model hedging). Cutpoint `medium ≥ 0.5` correctly captures the hedge zone.

**Cutpoints are coherent with the rest of the codebase. No revision needed.**
`[VERIFIED: graphify/export.py:302, graphify/report.py:18-25, graphify/extract.py:629]`

### Q2. Snapshot filename shape

**Recommendation: ISO timestamp, sortable, exactly the existing `snapshot.py:87` pattern.**

```
graphify-out/snapshots/2026-05-06T14-23-05.json
graphify-out/snapshots/2026-05-06T14-23-05_optional-name.json
```

Rationale:
- Already shipped: `snapshot.save_snapshot` produces exactly this shape (`snapshot.py:87`).
- mtime sort and lexicographic sort agree (timestamp is ISO-8601 fixed-width-numeric prefix).
- Manifest hash filename would be **ambiguous for FIFO mtime eviction** — same content twice in a row produces same hash, collides with itself, FIFO logic gets confused.
- A timestamp encodes "when" (which is what FIFO retention actually needs). Manifest hash encodes "what", which is irrelevant to retention policy.
`[VERIFIED: graphify/snapshot.py:87]`

### Q3. Snapshot file format

**Recommendation: REUSE the existing `snapshot.save_snapshot` payload format.** It already includes everything drift needs:

```json
{
  "graph": <node_link_data>,
  "communities": {"<cid>": [<node_id>, ...], ...},
  "metadata": {"timestamp": "...", "node_count": N, "edge_count": M}
}
```

Drift requires:
- **Node → community map** ⇒ derived from `payload["communities"]` (already there).
- **Edge endpoints + relation** for `implements`/`documents`/`tests` classification ⇒ derived from `payload["graph"]["links"]` (already there).
- **No edge confidence_score needed** for drift classification — drift is structural, not confidence-weighted.

`load_snapshot` (snapshot.py:172) already returns `(G, communities, metadata)`. Drift uses all three.
`[VERIFIED: graphify/snapshot.py:88-105 (write); 172-198 (read)]`

### Q4. drift.py public API surface

```python
# graphify/drift.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import networkx as nx

_JACCARD_THRESHOLD: float = 0.7   # D-04, D-05
_DRIFT_RELATIONS: frozenset[str] = frozenset({"implements", "documents", "tests"})  # CDRIFT-02
_TOP_N: int = 10  # D-07

@dataclass(frozen=True)
class DriftSummary:
    stable: list[tuple[str, str, str]]            # (src, tgt, relation)
    community_renamed: list[tuple[str, str, str]]
    community_resharded: list[tuple[str, str, str]]
    orphaned: list[tuple[str, str, str]]

def match_communities_jaccard(
    communities_prev: dict[int, list[str]],
    communities_curr: dict[int, list[str]],
    threshold: float = _JACCARD_THRESHOLD,
) -> dict[int, int | None]: ...
    """For each prev community, the current community with which it has the
    largest Jaccard ≥ threshold (or None if none match). Pure."""

def classify_edges(
    G_current: nx.Graph,
    communities_prev: dict[int, list[str]],
    communities_curr: dict[int, list[str]],
    match_map: dict[int, int | None],
) -> DriftSummary: ...
    """Walk each implements/documents/tests edge in G_current and classify."""

def compute_edge_drift(
    G_current: nx.Graph,
    communities_curr: dict[int, list[str]],
    project_root: Path = Path("."),
) -> DriftSummary | None: ...
    """High-level: list_snapshots → load latest → match → classify.
    Returns None when no prior snapshot exists (CDRIFT-03 / D-09)."""

def write_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    project_root: Path = Path("."),
    cap: int = 10,
) -> Path: ...
    """Thin wrapper over snapshot.save_snapshot with explicit fsync per D-03."""
```

**Confirmed/revised vs original question:**
- ✅ `write_snapshot` — kept; thin wrapper (don't duplicate atomic write logic).
- ❌ `load_latest_snapshot` — **NOT exposed publicly** in drift.py; reuse `snapshot.list_snapshots` + `snapshot.load_snapshot` in `compute_edge_drift`.
- ✅ `compute_drift` → **renamed `compute_edge_drift`** to disambiguate from Phase 11 `_run_drift_nodes` semantics.
- ❌ `evict_old_snapshots` — already done by `save_snapshot(cap=10)`. Don't expose separately.
- ➕ Added `match_communities_jaccard` and `classify_edges` as public testable units (TDD-eligible math).

### Q5. report.py extension shape

**Read on disk:** `graphify/report.py` is **521 lines** post-Phase 66. The Federation section is 21 lines (`report.py:269-289`).

**Recommendation: EXTEND `generate()` in place — same pattern as Federation.**

Rationale:
- 521 lines is comfortably within the existing module's footprint (extract.py is 2719 lines and still in one file).
- Federation section template fits in ~25 lines; Drift section will be similar shape.
- Adding `_render_drift_section` as a module-level helper IS still acceptable — keep it private (underscore prefix), mirror federation if/when planner judges. No decision blocker.

Concrete change shape:

```python
# graphify/report.py::generate(...)
def generate(
    ...,
    federation_manifest: list[dict] | None = None,
    drift_summary: "DriftSummary | None" = None,   # NEW (forward-ref to drift.DriftSummary)
) -> str:
    ...
    # AFTER Federation block (line ~289), BEFORE "Ambiguous Edges" (line ~290):
    if drift_summary is not None:
        lines += _render_drift_section(drift_summary)
```

`_render_drift_section` is pure, returns `list[str]`, easy to unit-test.

### Q6. CQUERY filter integration point

**Exact line where filters short-circuit:** Inside `_concept_code_hop_kind` at `serve.py:2204` is too early (it doesn't see edge-level confidence). Inside `_concept_code_hop_allowed` at `serve.py:2230` is correct — it already receives edge data and the `relations` filter set.

**Recommended integration:**
1. Add `extra_predicate: Callable[[dict], bool] | None = None` kwarg to `_bfs_concept_code_from` (`serve.py:2290`).
2. Inside the BFS loop, after `_concept_code_hop_allowed(...)` returns non-None and BEFORE incrementing `traversals`, evaluate `if extra_predicate is not None and not extra_predicate(G.edges[u, v]): continue`.
3. Build `extra_predicate` in `_run_concept_code_hops`:
   ```python
   if min_conf is None and band is None:
       extra_predicate = None  # byte-identity preserved
   else:
       def extra_predicate(ed: dict) -> bool:
           score = ed.get("confidence_score", _CONFIDENCE_SCORE_DEFAULTS.get(ed.get("confidence", "EXTRACTED"), 1.0))
           if min_conf is not None and score < min_conf: return False
           if band is not None and not _band_match(score, band): return False
           return True
   ```
4. The `relations` arg already exists; CQUERY-01 only changes its default semantics from `frozenset({"implements"})` to `frozenset(_ALLOWED_CONCEPT_CODE_RELATIONS)` when `None`. **D-12 conflict from Pitfall 4 must be resolved here.**

**Byte-identity contract:** when `min_confidence is None and confidence_band is None and relations is None`, `extra_predicate` is `None`, the `requested_relations` is the same `frozenset({"implements"})` as v1.12 → BFS path is structurally unchanged.

`[VERIFIED: graphify/serve.py:2230, 2290-2330]`

### Q7. Frozen fixture for CQUERY-02

**Fixture (input) already exists:** `tests/fixtures/legacy_v1_12_graph.json` (85 lines, v1.12-shaped: includes `community` per node, no `confidence_score` on nodes). ✅

**Golden output to commit:** `tests/fixtures/legacy_v1_12_concept_code_hops_golden.json`

Required schema fields the fixture+golden must include for stability across Phase 65 cache split:

| Source | Field | Reason |
|--------|-------|--------|
| Fixture nodes | `id`, `label`, `file_type`, `source_file`, `source_location`, `community` | v1.12 minimum schema |
| Fixture edges | `source`, `target`, `relation`, `confidence`, `source_file` | required by `validate.py` |
| Fixture edges (only some) | `confidence_score` | OPTIONAL in v1.12 — fixture should NOT include it on most edges so the golden test asserts the v1.12-no-score path is byte-identical |
| Golden output | full `text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta)` string | The function returns this exact byte sequence; deep-equal compares the parsed JSON portion separately |

**Test pattern:**

```python
def test_concept_code_hops_v112_byte_identity():
    G = _load_fixture("legacy_v1_12_graph.json")
    result = _run_concept_code_hops(G, alias_map={}, arguments={"entity": "Transformer"})
    text, _, meta_json = result.partition(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(meta_json)
    expected = json.loads((FIXTURES / "legacy_v1_12_concept_code_hops_golden.json").read_text())
    assert text == expected["text"]
    assert meta == expected["meta"]   # deep-equal, not subset
```

**The fixture and golden MUST NOT carry `cache_version` or `schema_version` keys** — those are pipeline artifacts (Phase 65), not graph fields. Including them would couple the regression test to the cache layer and force re-snapshotting on every Phase 65+ schema bump.

### Q8. Validation Architecture — see dedicated section below.

### Q9. Stderr/error paths

All messages follow Phase 64 two-line contract: `[graphify] error: <msg>\n  hint: <actionable>`.

| Failure mode | Where raised | Two-line message |
|--------------|--------------|-------------------|
| Snapshot read corruption (truncated/invalid JSON) | `drift.compute_edge_drift` (catches `ValueError` from `load_snapshot`) | `[graphify] error: drift snapshot is corrupt: <path>\n  hint: delete the file (graphify-out/snapshots/) or rerun \`graphify run\` to regenerate` |
| Snapshot missing required keys | `load_snapshot` already raises (`snapshot.py:184`) | reuse existing message; ensure two-line format applied at call-site if not already |
| Jaccard divide-by-zero (empty union) | `match_communities_jaccard` | **NOT a stderr error** — guard returns `0.0`, classification still proceeds |
| Invalid `confidence_band` string | `_validate_confidence_band_arg` | `[graphify] error: confidence_band must be one of {'high','medium','low'}; got <repr>\n  hint: omit the parameter to disable band filtering` |
| Invalid `min_confidence` (not numeric or out of [0,1]) | `_validate_min_confidence_arg` | `[graphify] error: min_confidence must be a float in [0.0, 1.0]; got <repr>\n  hint: omit the parameter or pass a value like 0.7` |
| Invalid `relations` (non-list, non-string item) | new validator | `[graphify] error: relations must be a list of strings; got <type>\n  hint: pass e.g. ['implements','documents'] or omit the parameter` |
| Snapshot write failure (disk full / permission) | `snapshot.save_snapshot` already raises after `tmp.unlink` | wrap in `__main__.py` to emit two-line stderr but DO NOT abort the run (drift is best-effort) |

CQUERY validator errors flow through the existing MCP envelope (status="error" meta + sentinel). They do NOT print to stderr; the two-line contract there is **embedded in the `error` meta string** because MCP runs over stdio and stderr is reserved for server-level logs. Confirmed pattern at `serve.py:2353-2363`.

### Q10. TDD eligibility per task

| Work unit | TDD-eligible? | Rationale |
|-----------|---------------|-----------|
| `match_communities_jaccard` | ✅ YES | Pure math; trivial fixtures (small dicts); easy red→green |
| `classify_edges` | ✅ YES | Pure; takes (G, prev_communities, curr_communities, match_map); deterministic |
| `compute_edge_drift` (orchestrator) | ✅ YES | Pure given a `tmp_path` and seeded snapshots |
| `write_snapshot` thin wrapper | ✅ YES | Atomic-write contract is testable (write twice → verify FIFO) |
| `_validate_min_confidence_arg` | ✅ YES | Trivial input/output validator |
| `_validate_confidence_band_arg` | ✅ YES | Trivial input/output validator |
| BFS predicate composition (Option A) | ✅ YES | Pure function over edge-data dict |
| CQUERY-02 frozen-fixture regression | ✅ YES | One-shot deep-equal; build red test first by deliberately omitting predicate-`None` short-circuit |
| `_render_drift_section` (or in-place block) | ⚠️ STANDARD | String-rendering, snapshot-test-friendly but TDD overhead modest |
| MCP tool input-schema dict update | ❌ STANDARD (config-shaped) | Static declaration; tested indirectly via integration test |
| Pipeline wiring in `__main__.py::run` | ❌ STANDARD | Integration; covered by an end-to-end smoke test under `tmp_path` |

---

## Code Examples

### Example 1: Set Jaccard with empty-union guard (in-tree precedent)

```python
# Source: graphify/federate.py:131-135 (Phase 66, verified)
def _jaccard_ok(local_nbrs: set[str], peer_nbrs: set[str]) -> tuple[bool, float]:
    union = local_nbrs | peer_nbrs
    if not union:
        return False, 0.0
    j = len(local_nbrs & peer_nbrs) / len(union)
    return j >= _JACCARD_THRESHOLD, j
```

Phase 67 use:
```python
def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)
```

### Example 2: Atomic snapshot write (already shipped)

```python
# Source: graphify/snapshot.py:108-114 (verified)
tmp = target.with_suffix(".tmp")
try:
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, target)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

For D-03 fsync compliance (mirror `federate.py:417-426`):
```python
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, indent=2))
    fh.flush()
    os.fsync(fh.fileno())
os.replace(tmp, target)
```

### Example 3: BFS predicate short-circuit (sketch)

```python
# graphify/serve.py — extension to _bfs_concept_code_from
def _bfs_concept_code_from(
    G, start_id, max_hops, direction, relations,
    *, extra_predicate=None,   # NEW kwarg, default None preserves v1.12 path
):
    ...
    while queue:
        u = queue.popleft()
        ...
        for v in G.neighbors(u):
            ...
            allowed = _concept_code_hop_allowed(G, u, v, direction, relations)
            if allowed is None:
                continue
            if extra_predicate is not None:
                ed = G.edges[u, v]
                if not extra_predicate(ed):
                    continue
            ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled NX serialization | `networkx.json_graph.node_link_data` w/ `edges="links"` fallback | `snapshot.py:96-100` | Stable across NetworkX versions |
| One-line `[graphify]` stderr | Two-line `[graphify] error: + hint:` | Phase 64 AUDIT-02 | All new errors must follow |
| Inline confidence handling | `_CONFIDENCE_SCORE_DEFAULTS` + per-edge `confidence_score` | Phase 65 | CQUERY band filter reads this |
| Federation kwarg-on-`generate()` | (current) | Phase 66 | Direct template for Drift kwarg |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reusing `graphify-out/snapshots/` (vs CONTEXT-specified `graphify-out/cache/snapshots/`) is preferable | §Summary; Pitfall 2 | If user insists on `cache/snapshots/`, Phase 11 `_run_drift_nodes` breaks unless migrated in same commit. Confirm in plan-check or with user. `[ASSUMED]` |
| A2 | `relations=[]` should be allowed (D-12) and yield zero results despite existing `_validate_relations_arg` rejecting `[]` | §Pitfall 4; Q6 | If reuse-validator-verbatim wins, D-12 must be re-spec'd to error on `[]`. `[ASSUMED]` |
| A3 | Confidence cutpoints `0.8`/`0.5` align with codebase distribution | Q1 | Verified against `_CONFIDENCE_SCORE_DEFAULTS` and Phase 65 calibration thresholds — `[VERIFIED]` |
| A4 | `report.py` 521 LOC is small enough to extend in place vs factor `drift_report.py` | Q5 | Subjective; planner discretion confirmed by CONTEXT | `[ASSUMED]` |
| A5 | Drift compute MUST run BEFORE write_snapshot in pipeline | Pitfall 5; Architecture diagram | If reversed, drift is always all-`stable` on every run → silent regression `[CITED: CONTEXT.md "Integration Points"]` |
| A6 | `confidence_score` field is reliably present on Phase 65+ edges; default to `_CONFIDENCE_SCORE_DEFAULTS` lookup when missing | Q6 BFS predicate | If older graphs lack the field entirely (e.g., loaded snapshots from before Phase 65), the band filter falls back to ladder defaults — confirmed at `export.py:325-327` `[VERIFIED]` |

---

## Open Questions

1. **Snapshot path (`graphify-out/snapshots/` vs `graphify-out/cache/snapshots/`)**
   - What we know: existing infrastructure uses `graphify-out/snapshots/`; CONTEXT D-01 says `cache/snapshots/`.
   - What's unclear: was the CONTEXT decision made aware of Phase 11's existing path?
   - Recommendation: planner OR plan-check must confirm with user before locking. Default to existing path.

2. **`relations=[]` semantics**
   - What we know: D-12 says `[]` = zero-results; existing validator says `[]` = error.
   - What's unclear: should the new CQUERY entry use a forked validator with new semantics, or should D-12 be updated to align with existing validator?
   - Recommendation: factor a new validator (`_validate_cquery_relations_arg`) so each entry point keeps its own contract; flag in plan-check.

---

## Environment Availability

> Phase 67 is code-only — no new external dependencies. **Skipped (no external dependencies identified).**

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard, configured via pyproject.toml) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_drift.py tests/test_concept_code_hops_v112_compat.py -x` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CDRIFT-01 | Jaccard matching never references community names/IDs | unit | `pytest tests/test_drift.py::test_jaccard_renamed_communities -x` | ❌ Wave 0 |
| CDRIFT-01 | Jaccard guards empty-union | unit | `pytest tests/test_drift.py::test_jaccard_empty_union_guard -x` | ❌ Wave 0 |
| CDRIFT-02 | Edge classifier produces all four classes | unit | `pytest tests/test_drift.py::test_classify_edges_all_four_classes -x` | ❌ Wave 0 |
| CDRIFT-02 | Orphaned edges (endpoints disappear) | unit | `pytest tests/test_drift.py::test_classify_orphaned -x` | ❌ Wave 0 |
| CDRIFT-02 | community-renamed (Jaccard ≥ 0.7) | unit | `pytest tests/test_drift.py::test_classify_community_renamed_at_threshold -x` | ❌ Wave 0 |
| CDRIFT-02 | community-resharded (Jaccard < 0.7) | unit | `pytest tests/test_drift.py::test_classify_community_resharded_below_threshold -x` | ❌ Wave 0 |
| CDRIFT-03 | Drift section present when prior snapshot exists | integration | `pytest tests/test_report.py::test_drift_section_emitted_with_prior_snapshot -x` | ❌ Wave 0 |
| CDRIFT-03 | Drift section omitted when no prior snapshot | integration | `pytest tests/test_report.py::test_drift_section_omitted_no_prior -x` | ❌ Wave 0 |
| CDRIFT-03 | D-08 zero-edge case still renders 0/0/0/0 | integration | `pytest tests/test_report.py::test_drift_section_zero_edges_renders -x` | ❌ Wave 0 |
| CDRIFT-04 | FIFO retention at cap=10 | unit | `pytest tests/test_drift.py::test_write_snapshot_fifo_cap10 -x` | ❌ Wave 0 |
| CDRIFT-04 | Atomic write (no partial files on crash) | unit | `pytest tests/test_drift.py::test_write_snapshot_atomic -x` | ❌ Wave 0 |
| CQUERY-01 | `min_confidence` filters edges below threshold | unit | `pytest tests/test_concept_code_hops.py::test_min_confidence_filter -x` | ✅ extends existing |
| CQUERY-01 | `relations` whitelist (None=all, []=zero, list=subset) | unit | `pytest tests/test_concept_code_hops.py::test_relations_whitelist_three_modes -x` | ✅ extends existing |
| CQUERY-01 | `confidence_band` enum (high/medium/low) | unit | `pytest tests/test_concept_code_hops.py::test_confidence_band_enum -x` | ✅ extends existing |
| CQUERY-01 | AND semantics: both `min_confidence` and `confidence_band` must pass | unit | `pytest tests/test_concept_code_hops.py::test_min_conf_and_band_and_semantics -x` | ✅ extends existing |
| CQUERY-01 | Invalid `confidence_band` returns error envelope w/ two-line message | unit | `pytest tests/test_concept_code_hops.py::test_invalid_band_error_envelope -x` | ✅ extends existing |
| CQUERY-02 | Frozen fixture deep-equal with v1.12 golden | regression | `pytest tests/test_concept_code_hops_v112_compat.py::test_byte_identity_v112 -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_drift.py tests/test_concept_code_hops_v112_compat.py tests/test_concept_code_hops.py -x` (~5 sec)
- **Per wave merge:** `pytest tests/test_drift.py tests/test_concept_code_hops*.py tests/test_report.py tests/test_serve.py -q` (~20 sec)
- **Phase gate:** `pytest tests/ -q` (full suite) green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_drift.py` — covers CDRIFT-01..04 (NEW)
- [ ] `tests/test_concept_code_hops_v112_compat.py` — covers CQUERY-02 (NEW)
- [ ] `tests/fixtures/legacy_v1_12_concept_code_hops_golden.json` — golden output for CQUERY-02 (NEW)
- [ ] Drift-section assertions in `tests/test_report.py` — extending existing file (CDRIFT-03)
- [ ] CQUERY param tests in `tests/test_concept_code_hops.py` if it exists, else extend `tests/test_serve.py` (CQUERY-01)
- *(Framework install: pytest is already a project dependency — no install step needed)*

---

## Sources

### Primary (HIGH confidence — direct codebase verification)
- `graphify/snapshot.py` lines 1-198 — existing snapshot save/load/list with FIFO cap and ProjectRoot guard
- `graphify/federate.py` lines 131-135 (Jaccard guard), 399-432 (atomic write w/ fsync)
- `graphify/report.py` lines 117-160 (generate signature), 269-289 (Federation section template)
- `graphify/serve.py` lines 2200-2207 (allowed relations), 2230-2260 (hop allowed), 2246-2280 (validator), 2290-2334 (BFS), 2345-2500 (run_concept_code_hops), 3553-3566 (MCP entry)
- `graphify/delta.py` lines 9-67 — node-level migration computation (Phase 11)
- `graphify/export.py` line 302 — `_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}`
- `tests/fixtures/legacy_v1_12_graph.json` — exists, 85 lines, v1.12-shaped
- `.planning/phases/67-.../67-CONTEXT.md` — locked decisions D-01..D-14

### Secondary (MEDIUM confidence — referenced but not exhaustively traced)
- Phase 65 confidence_score contract (referenced in CONTEXT canonical_refs, partially verified via `report.py:18-25` calibration histogram)
- Phase 64 stderr two-line contract (referenced in CONTEXT; verified via `federate.py:170-173` error message shape)

### Tertiary (LOW confidence — none)
- N/A — all claims grounded in directly-read source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every reusable module verified by direct read
- Architecture: HIGH — all integration points exist and were inspected
- Pitfalls: HIGH — Pitfall 2 (snapshot path) and Pitfall 4 (`relations=[]`) are codebase-grounded, not speculative
- Confidence cutpoints (D-10): HIGH — verified against `_CONFIDENCE_SCORE_DEFAULTS` and calibration thresholds

**Research date:** 2026-05-06
**Valid until:** 2026-06-05 (30 days; stable internal codebase)
