# Phase 71: TEMP — Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 12 (2 new modules, 8 modified, 2 new test fixtures, 1 new test module)
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/temporal.py` (NEW) | utility | transform | `graphify/security.py` + `graphify/cache.py` | role-match (stdlib-only utility) |
| `graphify/temporal_config.yaml` (NEW) | config | n/a | (no analog — first YAML config) | none |
| `graphify/build.py` (MOD) | service | transform | self (Phase 65 SCHEMA_VERSION pattern) | exact (extending) |
| `graphify/validate.py` (MOD) | service | transform | self (Phase 65 read/write split lines 231–258) | exact (extending) |
| `graphify/analyze.py` (MOD) | service | transform | self (existing edge-iter sites 76/246/336/408) | exact (extending) |
| `graphify/export.py` (MOD) | service | transform | self (lines 1098–1112 None-sanitization) | exact (extending) |
| `graphify/report.py` (MOD) | service | transform | self (existing section renderer) | exact (extending) |
| `graphify/wiki.py` (MOD) | service | transform | self (`_community_article`) | exact (extending) |
| `graphify/__main__.py` (MOD) | controller | request-response | self (~line 1962 prior-graph load path) | exact (extending) |
| `graphify/cache.py` | utility | n/a (verify only) | n/a — confirmed unchanged | none |
| `tests/test_temporal.py` (NEW) | test | n/a | `tests/test_validate.py` | role-match |
| `tests/fixtures/graph_legacy_v113.json`, `graph_temporal_v20.json` (NEW) | test fixture | n/a | existing `tests/fixtures/*.json` | role-match |
| `tests/conftest.py` (EXTEND) | test config | n/a | existing conftest | exact (extending) |

## Pattern Assignments

### `graphify/temporal.py` (NEW utility module)

**Analogs:** `graphify/security.py` (input validation utility, fail-loud), `graphify/cache.py` (stdlib-only helper module, hashable transforms).

**Imports pattern (mirror `security.py` / `cache.py`):**
```python
from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
```

**Run-clock helper (RESEARCH.md Pattern 3 — verbatim):**
```python
def run_now_iso() -> str:
    """Return ISO-8601 UTC timestamp for the current run.
    Tests may pin via GRAPHIFY_RUN_TS env var or monkeypatch run_now_iso directly.
    """
    pinned = os.environ.get("GRAPHIFY_RUN_TS")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()
```

**PyYAML-guarded loader (RESEARCH.md Pattern 4 — verbatim, mirrors optional-import pattern in `cluster.py` graspologic→Louvain fallback):**
```python
def load_decay_config(path: Path | None = None) -> dict:
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
    if "default" not in loaded:
        loaded["default"] = defaults["default"]
    return loaded
```

**Decay computation (RESEARCH.md verbatim):**
```python
def compute_decay_weight(*, relation: str, valid_from: str, run_now: str, config: dict) -> float:
    cfg = config.get(relation, config["default"])
    if cfg["function"] != "exponential":
        return 1.0
    age_days = (datetime.fromisoformat(run_now) - datetime.fromisoformat(valid_from)).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    half_life = float(cfg["half_life_days"])
    floor = float(cfg["floor"])
    return max(floor, 0.5 ** (age_days / half_life))
```

**Supersession helper (`stamp_supersessions`):** New helper. No direct analog — reads prior `graph.json` via `nx.readwrite.json_graph.node_link_graph` (same mechanism `__main__.py:1962` uses for `query` / `--obsidian` re-load). Returns merged edge list with `valid_until` stamped on missing prior-INFERRED tuples.

---

### `graphify/build.py` (MODIFIED)

**Analog:** Self — Phase 65 SCHEMA_VERSION pattern at line 37 + Phase 70.2 in-memory stamping at lines 304–307.

**Bump pattern (one-line, exact precedent):**
```python
# graphify/build.py:37 — was "1.13", bump to:
SCHEMA_VERSION = "2.0"
```

**Stamp pattern (mirror Phase 70.2-02 — stamping happens INSIDE `build_from_json`, not in a wrapper):**
```python
# Inside build_from_json, after _normalize_concept_code_edges, BEFORE validate_extraction_for_write
from .temporal import run_now_iso, load_decay_config, compute_decay_weight, stamp_supersessions

run_now = run_now_iso()
decay_cfg = load_decay_config()

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

extraction["edges"] = stamp_supersessions(
    new_edges=extraction["edges"],
    prior_graph_path=Path(target_dir or Path.cwd()) / "graphify-out" / "graph.json",
    run_now=run_now,
)
```

**Critical invariant (Pitfall 3):** Compute `run_now` ONCE per build run; pass it down. Never call `run_now_iso()` inside loops.

---

### `graphify/validate.py` (MODIFIED — extend lines 231–258)

**Analog:** Self — Phase 65 CCONF-05 read/write split, EXACT precedent.

**Existing pattern to extend (RESEARCH.md verbatim, lines 231–258):**
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

**Phase 71 extension — append inside `validate_extraction_for_write` (do NOT add to `REQUIRED_EDGE_FIELDS`):**
```python
edge_list = data.get("edges", []) if isinstance(data, dict) else []
for i, edge in enumerate(edge_list):
    if not isinstance(edge, dict):
        continue
    if "valid_from" not in edge:
        errors.append(f"Edge {i} missing required field 'valid_from' (write-mode)")
    dw = edge.get("decay_weight")
    if not isinstance(dw, (int, float)) or not (0.0 <= float(dw) <= 1.0):
        errors.append(f"Edge {i} 'decay_weight' must be float in [0.0, 1.0] (write-mode)")
    # valid_until: None OR ISO string — both OK; no error
```

**Anti-pattern to AVOID:** Adding `valid_from` to `REQUIRED_EDGE_FIELDS` — this would break read-mode legacy compat.

---

### `graphify/analyze.py` (MODIFIED — 4 edge-iter sites)

**Analog:** Self — existing `for u, v, data in G.edges(data=True)` loops at lines 246, 336, 408, plus `god_nodes` at 76.

**Filter pattern (one-line per site):**
```python
for u, v, data in G.edges(data=True):
    if data.get("valid_until") is not None:
        continue
    # ... existing logic
```

**god_nodes special case (line 76 — uses `G.degree()`):**
```python
# Use edge_subgraph view to filter superseded edges, then degree()
G_current = G.edge_subgraph(
    (u, v) for u, v, d in G.edges(data=True) if d.get("valid_until") is None
)
# then call .degree() on G_current
```

---

### `graphify/export.py` (MODIFIED)

**Analog:** Self — `to_graphml` at lines 1098–1112 already does `H = G.copy()` for sanitization (this is the exact extension point for None-handling).

**`to_json` (lines 318–340):** No edge-loop changes needed — `nx.readwrite.json_graph.node_link_data` preserves arbitrary edge attrs. `SCHEMA_VERSION` stamp at line 334 propagates the 1.13→2.0 bump automatically.

**`to_graphml` extension (sanitize None-valued temporal attrs):**
```python
H = G.copy()
for u, v, data in H.edges(data=True):
    if data.get("valid_until") is None:
        # GraphML writer rejects None — drop the attr
        H.edges[u, v].pop("valid_until", None)
nx.write_graphml(H, output_path)
```

**`to_cypher` (lines 354–367):** Quote ISO timestamp strings (existing string-quoting pattern handles this; verify `valid_until=None` renders as Cypher `null`).

**`to_obsidian` (lines 553–820):** No edge-frontmatter changes (renders nodes, not edges, in frontmatter). Historical relations rendering belongs to `wiki.py`, not here.

---

### `graphify/wiki.py` (MODIFIED)

**Analog:** Self — `_community_article` edge-enumeration loop.

**Extension pattern:** Add second pass filtering `data.get("valid_until") is not None`. Render under new `## Historical relations` heading at the bottom of each community article. **Omit the heading entirely when the filtered list is empty.**

```python
historical = [(nbr, data) for nbr, data in edges_iter if data.get("valid_until") is not None]
if historical:
    md.append("\n## Historical relations\n")
    for nbr, data in historical:
        md.append(f"- [[{nbr}]] (until {data['valid_until']})")
```

---

### `graphify/report.py` (MODIFIED)

**Analog:** Self — existing section renderer pattern.

**Extension pattern (minimal per locked decision: counts only):**
```python
total = G.number_of_edges()
superseded = sum(1 for _, _, d in G.edges(data=True) if d.get("valid_until") is not None)
current = total - superseded
pct = (superseded / total * 100.0) if total else 0.0
md.append(f"\n## Temporal Health\n\n"
          f"- Currently valid edges: {current}\n"
          f"- Superseded edges: {superseded}\n"
          f"- Superseded share: {pct:.1f}%\n")
```

---

### `graphify/__main__.py` (MODIFIED — around line 1962)

**Analog:** Self — existing prior-graph load path used by `query` / `--obsidian`.

**Pattern to mirror:** Same `nx.readwrite.json_graph.node_link_graph` load and same `ResolvedOutput`-based path resolution as `to_json`. Supersession diff in `build.py` reuses this path resolution to avoid Pitfall 1 (vault vs default mode mismatch).

---

### `graphify/cache.py` (UNCHANGED — verify only)

**Verification claim (RESEARCH.md):** `cache.py` saves per-file extraction dicts BEFORE temporal stamping (which happens at build time). Existing cache files replay through `build_from_json` and get stamped on the fly. **No cache invalidation needed.**

---

### `tests/test_temporal.py` (NEW)

**Analog:** `tests/test_validate.py` (pure unit tests of stdlib-only helper module) and `tests/test_extract.py` (monkeypatch fixture usage).

**Pattern to mirror:**
```python
from __future__ import annotations
import pytest
from graphify import temporal

def test_run_now_iso_env_override(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_RUN_TS", "2026-01-01T00:00:00+00:00")
    assert temporal.run_now_iso() == "2026-01-01T00:00:00+00:00"

def test_extracted_no_decay():
    # decay_weight always 1.0 for EXTRACTED, regardless of age
    ...

def test_inferred_exponential_decay():
    cfg = {"default": {"function": "exponential", "half_life_days": 30, "floor": 0.1}}
    w = temporal.compute_decay_weight(
        relation="references",
        valid_from="2026-04-07T00:00:00+00:00",
        run_now="2026-05-07T00:00:00+00:00",
        config=cfg,
    )
    assert 0.49 <= w <= 0.51  # ~30d => ~0.5

def test_decay_floor():
    ...

def test_decay_config_no_yaml(monkeypatch):
    # Simulate ImportError on `import yaml`
    ...
```

**Constraints (CLAUDE.md):** pure unit tests, no network, no FS side-effects outside `tmp_path`.

---

### `tests/fixtures/graph_legacy_v113.json`, `graph_temporal_v20.json` (NEW)

**Analog:** Existing `tests/fixtures/*.json` from prior phases.

**Patterns:**
- `graph_legacy_v113.json`: edges with `confidence` but NO `valid_from`/`valid_until`/`decay_weight`; `schema_version: "1.13"` at top level. Used by `test_legacy_graph_loads`.
- `graph_temporal_v20.json`: full schema-2.0 fixture with `valid_from`, mixed `valid_until` (some null, some ISO), `decay_weight` ∈ [0.1, 1.0]. Used by supersession round-trip tests.

---

### `tests/conftest.py` (EXTEND)

**Analog:** Existing conftest fixtures.

**Extension (optional — RESEARCH.md says existing `tmp_path` suffices):** A clock-pinning fixture if multiple test modules need the same pinned timestamp:
```python
@pytest.fixture
def pinned_run_ts(monkeypatch):
    ts = "2026-05-07T12:00:00+00:00"
    monkeypatch.setenv("GRAPHIFY_RUN_TS", ts)
    return ts
```

---

## Shared Patterns

### Schema-version single-source-of-truth (Phase 65 + 70.2 precedent)
**Source:** `graphify/build.py:37` (constant) + `build.py:304–307` (in-memory stamp) + `export.py:331–334` (import-and-restamp).
**Apply to:** `build.py` (bump constant), every test that constructs a graph (assert `G.graph["schema_version"] == "2.0"`).
**Anti-pattern (Pitfall 3):** Never add a code path that bypasses `build_from_json` — stamping must happen INSIDE that function.

### Read-tolerant / write-strict validators (Phase 65 CCONF-05 precedent)
**Source:** `graphify/validate.py:231–258`.
**Apply to:** Every new optional-on-read / required-on-write field (Phase 71: `valid_from`, `decay_weight`).

### Optional-dependency guard (existing precedent: graspologic in `cluster.py`, neo4j in `export.py`)
**Source:** Try/except `ImportError` with in-code fallback.
**Apply to:** PyYAML in `temporal.load_decay_config`.

### Run-scoped clock (NEW — Phase 71 establishes precedent)
**Source:** `graphify/temporal.run_now_iso()`.
**Apply to:** Any future feature needing per-run timestamps. Always compute once at top of pipeline; never inside loops.

### Edge-attribute round-trip (existing `confidence_score` precedent — Assumption A5)
**Source:** Implicit in `nx.readwrite.json_graph.node_link_data` — preserves arbitrary attrs.
**Apply to:** All new edge attrs in Phase 71. Only special handling needed: `to_graphml` rejects `None` → sanitize.

### Path confinement for prior-graph load
**Source:** `__main__.py:1962` + `ResolvedOutput` resolution mirrored from `to_json` write path.
**Apply to:** `stamp_supersessions` prior-graph load. Avoids Pitfall 1 (vault vs default mismatch).

### stderr-format test discipline (Pitfall 2 — Phase 64 audit lesson)
**Apply to:** `test_validate.py` — assert exact new error strings, do not rely on regex over generic stderr.

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `graphify/temporal_config.yaml` | config | First YAML config in the package; `pyproject.toml` `[tool.setuptools.package-data]` must list it: `"graphify": ["temporal_config.yaml"]`. |
| `stamp_supersessions` helper | utility (diff) | No prior run-scoped diff helper exists in tree; design is novel but composes existing primitives (`json_graph.node_link_graph`, dict tuple-key lookup). |

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `pyproject.toml`.
**Files scanned:** validate.py, build.py, export.py, analyze.py, cache.py, security.py, cluster.py, wiki.py, report.py, tests/test_validate.py, tests/test_extract.py.
**Pattern extraction date:** 2026-05-07
**Verification source:** RESEARCH.md verified file:line citations (build.py:37, validate.py:231–258, export.py:1098–1112, analyze.py:76/246/336/408, __main__.py:1962). Re-reads suppressed by hook (only line 1 returned); RESEARCH.md verbatim excerpts used as ground truth.
