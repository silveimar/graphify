# Phase 65: CCONF — Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 13 (5 modified Python modules, 1 new module, 4 new/extended tests, 2 fixtures, 1 skill family)
**Analogs found:** 12 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/prompts.py` (NEW) | config / constants | static-load | `graphify/security.py` (constants module pattern) | role-match |
| `graphify/cache.py` (MODIFIED — confidence helpers) | cache / persistence | file-I/O | `graphify/cache.py` self (extract-cache helpers) | exact |
| `graphify/extract.py` (MODIFIED — scored emission at 3 sites) | extractor | transform / batch | `graphify/extract.py:585-600` (existing edge dict construction) | exact |
| `graphify/validate.py` (MODIFIED — schema_version semantics) | validator | request-response | `graphify/validate.py:117-227` (`validate_extraction`) | exact |
| `graphify/export.py` (MODIFIED — emit `schema_version`) | serializer | transform | `graphify/export.py:to_json` (back-fill `confidence_score`) | exact |
| `graphify/report.py` (MODIFIED — calibration histogram) | reporter | read-only aggregate | `graphify/report.py:80-100` (`inf_avg` block) | exact |
| `graphify/skill.md` + 6 platform variants (MODIFIED) | orchestrator prompt | event-driven | existing semantic-extraction skill section | role-match |
| `tests/test_confidence_cache.py` (NEW) | test | unit | `tests/test_cache.py` | exact |
| `tests/test_extract_confidence.py` (NEW or extend) | test | unit | `tests/test_extract.py` | role-match |
| `tests/test_report_calibration.py` (NEW) | test | unit | `tests/test_report.py` (if exists) | role-match |
| `tests/test_validate.py` (EXTEND — schema_version) | test | unit | `tests/test_validate.py` self | exact |
| `tests/fixtures/legacy_v1_12_graph.json` (NEW) | fixture | static | none — captured from real v1.12 run | no analog |
| `tests/fixtures/skewed_distribution.json` (NEW) | fixture | static | `tests/fixtures/stderr_contract.txt` (frozen-fixture pattern) | role-match |

## Pattern Assignments

### `graphify/prompts.py` (NEW — constants module)

**Analog:** `graphify/security.py` (module-level constants + sanitize helpers)

**Module skeleton pattern** (mirrors `cache.py:1-7` and `security.py` constants):
```python
# scoring prompt + version constant for confidence cache key composition
from __future__ import annotations

PROMPT_VERSION = "1.13.0"

SCORING_PROMPT_TEMPLATE = """\
... <planner-authored prompt body, free text> ...
"""
```

Bumped in same commit as any prompt edit; imported by `cache.py` (new helpers) and the scoring wrapper in `extract.py`.

---

### `graphify/cache.py` (MODIFIED — confidence-cache helpers, per Open Question Q6 recommendation)

**Analog:** `graphify/cache.py` self — mirror existing `_inner_hash` / `_sanitize_model_id` / `_cache_key_string` / `_cache_json_filename` / `load_cached` / `save_cached` shape into a parallel `confidence_*` family.

**Sanitization pattern** (lines 32-41, copy verbatim shape for `_sanitize_prompt_version`):
```python
def _sanitize_model_id(model_id: str) -> str:
    """Reject path-like model_id values (cache poisoning / traversal)."""
    if ".." in model_id or "/" in model_id or "\\" in model_id:
        raise ValueError("model_id must not contain path segments or '..'")
    if not model_id:
        return ""
    if len(model_id) > 512:
        raise ValueError("model_id too long")
    return model_id
```

**Filename safety pattern** (lines 50-54, reuse for confidence cache):
```python
def _cache_json_filename(key: str) -> str:
    """Map logical cache key to a filesystem-safe .json basename (no ':' on Windows)."""
    if ":" not in key:
        return f"{key}.json"
    return f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"
```

**Cache directory pattern** (lines 69-73):
```python
def cache_dir(root: Path = Path(".")) -> Path:
    """Returns graphify-out/cache/ - creates it if needed."""
    d = Path(root) / "graphify-out" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d
```
New `confidence_cache_dir` returns `graphify-out/cache/confidence/` (D-65.04).

**Load pattern** (lines 76-90):
```python
def load_cached(path: Path, root: Path = Path("."), *, model_id: str = "") -> dict | None:
    try:
        key = file_hash(path, model_id=model_id)
    except ValueError:
        return None
    except OSError:
        return None
    entry = cache_dir(root) / _cache_json_filename(key)
    if not entry.exists():
        return None
    try:
        return json.loads(entry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
```

**Atomic-write pattern** (lines 96-104, reuse for confidence save):
```python
def save_cached(path: Path, result: dict, root: Path = Path("."), *, model_id: str = "") -> None:
    key = file_hash(path, model_id=model_id)
    entry = cache_dir(root) / _cache_json_filename(key)
    tmp = entry.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result), encoding="utf-8")
        os.replace(tmp, entry)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```

**New key-derivation pattern** (Phase 65 — composite three-dimensional key per D-65.05):
```python
def _confidence_cache_key(prompt_version: str, model_id: str, file_hash_str: str) -> str:
    _sanitize_model_id(model_id)
    _sanitize_prompt_version(prompt_version)  # NEW — mirrors _sanitize_model_id rules
    blob = f"{prompt_version}\x00{model_id}\x00{file_hash_str}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

---

### `graphify/extract.py` (MODIFIED — three INFERRED-emission sites)

**Analog:** `graphify/extract.py` itself at lines 585-600, 1208-1232, 2248-2256.

**Existing edge-dict shape to upgrade** (lines 591-600 — currently bakes `confidence_score: 1.0`):
```python
edges.append({
    "source": file_nid,
    "target": module_name,
    "relation": "imports",
    "confidence": "EXTRACTED",
    "confidence_score": 1.0,        # <-- Phase 65: replace at INFERRED sites
    "source_file": str_path,
    "source_location": str(node.start_point[0] + 1),
    "weight": 1.0,
})
```

**The `uses` site** (lines 2252-2260 — currently emits no `confidence_score` at all):
```python
new_edges.append({
    "source": src_class_nid,
    "target": tgt_nid,
    "relation": "uses",
    "confidence": "INFERRED",
    "source_file": str_path,
    "source_location": f"L{line}",
    "weight": 0.8,
})
# Phase 65: must add `confidence_score` + `evidence` per scored result
```

**Scoring wrapper pattern (NEW — at concept emission per D-65.02):**
```python
from .security import sanitize_label
from .prompts import PROMPT_VERSION

_MAX_EVIDENCE_LEN = 280

def _finalize_evidence(raw: str) -> str:
    truncated = raw[:_MAX_EVIDENCE_LEN]
    return sanitize_label(truncated)

# Call site (conceptual — per-source-file batch, D-65.03):
scored = score_concept_code_edges_for_file(path, candidate_edges)  # → [(score, evidence), ...]
for edge, (score, evidence) in zip(candidate_edges, scored):
    edge["confidence_score"] = score
    edge["evidence"] = _finalize_evidence(evidence)
```

Note (per Open Question Q1): the actual Claude API call is dispatched by the **skill orchestrator**, not Python. The Python helper exposes the request/response shape and writes results into `save_confidence_cache(...)`.

---

### `graphify/validate.py` (MODIFIED — `schema_version` read/write split)

**Analog:** `graphify/validate.py:117-227` (`validate_extraction`).

**Existing entry shape** (lines 117-122):
```python
def validate_extraction(data: dict) -> list[str]:
    """Validate an extraction JSON dict against the graphify schema.
    Returns a list of error strings - empty list means valid."""
    if not isinstance(data, dict):
        return ["Extraction must be a JSON object"]
    errors: list[str] = []
```

**Existing required-field iteration pattern** (lines 167-177 — copy shape for `schema_version` write rule):
```python
for i, edge in enumerate(edge_list):
    if not isinstance(edge, dict):
        errors.append(f"Edge {i} must be an object")
        continue
    for field in REQUIRED_EDGE_FIELDS:
        if field not in edge:
            errors.append(f"Edge {i} missing required field '{field}'")
```

**Phase 53 conditional-rule pattern** (lines 184-211 — template for the read/write `schema_version` branch):
```python
rel = edge.get("relation")
conf = edge.get("confidence")
if rel in NEW_CONCEPT_CODE_RELATIONS:
    if conf == "EXTRACTED":
        ev = edge.get("evidence")
        if not isinstance(ev, str) or not ev:
            errors.append(...)
    elif conf == "INFERRED":
        raw = edge.get("confidence_score")
        ...
        if score is None or not (0.0 <= score <= 1.0):
            errors.append(...)
```

**New entry-point pattern (Open Question Q5 recommendation):**
```python
def validate_extraction_for_read(data: dict) -> list[str]:
    return validate_extraction(data)  # schema_version absent → OK

def validate_extraction_for_write(data: dict) -> list[str]:
    errors = validate_extraction(data)
    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv:
        errors.append("Missing required key 'schema_version' (write-mode)")
    return errors
```

---

### `graphify/export.py` (MODIFIED — emit `schema_version` in `to_json`)

**Analog:** `graphify/export.py:to_json` (lines 313-340).

**Existing back-fill pattern to extend** (lines 314-330):
```python
def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str) -> None:
    node_community = _node_community_map(communities)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)
    for node in data["nodes"]:
        node["community"] = node_community.get(node["id"])
    for link in data["links"]:
        if "confidence_score" not in link:
            conf = link.get("confidence", "EXTRACTED")
            link["confidence_score"] = _CONFIDENCE_SCORE_DEFAULTS.get(conf, 1.0)
    data["hyperedges"] = getattr(G, "graph", {}).get("hyperedges", [])
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
```

**Phase 65 insertion** (one line after `node_link_data`, mirrors how `hyperedges` is sourced from `G.graph`):
```python
data["schema_version"] = G.graph.get("schema_version", "1.13")
```

---

### `graphify/report.py` (MODIFIED — calibration histogram + flag rules)

**Analog:** `graphify/report.py` lines ~85-100 (`inf_avg` aggregation).

**Existing aggregation pattern** (the natural extension point):
```python
inf_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("confidence") == "INFERRED"]
inf_scores = [d.get("confidence_score", 0.5) for _, _, d in inf_edges]
inf_avg = round(sum(inf_scores) / len(inf_scores), 2) if inf_scores else None
```

**Phase 65 additions (constants + helpers — D-65.11 named constants in `report.py`):**
```python
_CALIBRATION_MIN_EDGES = 10
_CALIBRATION_MODE_COLLAPSE_THRESHOLD = 0.70
_CALIBRATION_REFUSAL_THRESHOLD = 0.50
_CALIBRATION_NEGATIVE_FLOOR = 0.05

def _calibration_histogram(inf_scores: list[float]) -> list[int]:
    bins = [0] * 10
    for s in inf_scores:
        idx = min(9, max(0, int(s * 10)))
        bins[idx] += 1
    return bins
```

**Existing line-append rendering pattern** (lines 100-115 — copy shape for new `## Calibration` section):
```python
lines += [
    "",
    "## Summary",
    f"- {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities detected",
    ...
]
```

---

### `graphify/output.py` stderr contract (carry-forward, applies to any new emitter)

**Analog:** `graphify/output.py:_emit_vault_error` (line 85) and `_emit_vault_info` (line 119).

**Locked two-line pattern** (lines 98-99 / 126-127):
```python
print(f"[graphify] error: {msg}", file=sys.stderr)
print(f"  hint: {hint}", file=sys.stderr)
```
```python
print(f"[graphify] info: {msg}", file=sys.stderr)
print(f"  hint: {hint}", file=sys.stderr)
```

Apply to any new Phase 65 emission ("schema_version missing — read-validating as legacy", "confidence scoring fell back due to LLM error"). Snapshot lock = `tests/fixtures/stderr_contract.txt`.

---

### `tests/test_confidence_cache.py` (NEW)

**Analog:** `tests/test_cache.py` (lines 1-40).

**Imports + fixture pattern** (verbatim shape):
```python
"""Tests for graphify/cache.py."""
import pytest
from pathlib import Path
from graphify.cache import (
    file_hash, cache_dir, load_cached, save_cached, ...
)

@pytest.fixture
def tmp_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world")
    return f

@pytest.fixture
def cache_root(tmp_path):
    return tmp_path
```

**Determinism assertion pattern** (lines 28-34 — template for `test_prompt_version_invalidation`):
```python
def test_file_hash_consistent(tmp_file):
    h1 = file_hash(tmp_file)
    h2 = file_hash(tmp_file)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 64
```

---

### `tests/test_validate.py` (EXTEND — `schema_version` read/write split)

**Analog:** existing `validate_extraction` test cases.

Use the same `errors == []` / `errors != []` shape established by `validate_extraction(data) -> list[str]` semantics. Add fixture: `legacy_v1_12_graph.json` loaded via `json.loads(Path(...).read_text())`, then assert `validate_extraction_for_read(data) == []` and `validate_extraction_for_write(data)` reports the missing `schema_version`.

---

### `tests/fixtures/skewed_distribution.json` (NEW)

**Shape (per RESEARCH §"Skewed corpus fixture shape"):** 4 nodes (2 code, 2 rationale), 10 INFERRED `documents` edges with `confidence_score` clustered in 0.85±0.05 to push >70% into the [0.8, 0.9) bin. `schema_version: "1.13"` set.

---

## Shared Patterns

### Atomic file write
**Source:** `graphify/cache.py:96-104` (`save_cached`)
**Apply to:** confidence cache `save_confidence(...)`, frozen fixture writes (test scaffolding only)
```python
tmp = entry.with_suffix(".tmp")
try:
    tmp.write_text(json.dumps(result), encoding="utf-8")
    os.replace(tmp, entry)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

### Path-traversal sanitization for cache key components
**Source:** `graphify/cache.py:32-41` (`_sanitize_model_id`)
**Apply to:** new `_sanitize_prompt_version` in confidence-cache helpers
```python
if ".." in s or "/" in s or "\\" in s:
    raise ValueError("must not contain path segments or '..'")
if len(s) > 512:
    raise ValueError("too long")
```

### Filesystem-safe key→filename mapping
**Source:** `graphify/cache.py:50-54` (`_cache_json_filename`)
**Apply to:** all on-disk artifact filenames containing `:` or composite tokens — confidence cache included.

### Evidence / label sanitization
**Source:** `graphify/security.py:183-197` (`sanitize_label`)
**Apply to:** Phase 65 `evidence` field, capped at 280 chars (one bump above `_MAX_LABEL_LEN = 256`).
```python
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
def sanitize_label(text: str) -> str:
    text = _CONTROL_CHAR_RE.sub("", text)
    if len(text) > _MAX_LABEL_LEN:
        text = text[:_MAX_LABEL_LEN]
    return text
```

### Stderr two-line contract (Phase 64 carry-forward)
**Source:** `graphify/output.py:_emit_vault_error` (line 85) / `_emit_vault_info` (line 119)
**Apply to:** Every new Phase 65 stderr emission. Locked by snapshot test `tests/fixtures/stderr_contract.txt`.

### Validator return-list convention (errors as list[str])
**Source:** `graphify/validate.py:117-227`
**Apply to:** new `validate_extraction_for_read` / `validate_extraction_for_write`. Empty list = valid; never raise from validator (callers use `assert_valid` to convert to exception).

### Defaults map for confidence_score back-fill
**Source:** `graphify/export.py:_CONFIDENCE_SCORE_DEFAULTS` (line ~300)
**Apply to:** Use the existing map; do NOT introduce a parallel default dict.
```python
_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}
```

### `graph.json` round-trip via `G.graph` attr
**Source:** `graphify/export.py:to_json` (uses `G.graph["hyperedges"]`)
**Apply to:** `schema_version` storage — write as `G.graph["schema_version"] = "1.13"`, emit at top-level JSON via `data["schema_version"] = G.graph.get("schema_version", "1.13")`. NetworkX `node_link_data` / `node_link_graph` round-trips `G.graph` cleanly.

### `from __future__ import annotations` first
**Source:** every Python module in `graphify/`
**Apply to:** new `prompts.py`, all new test files.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/fixtures/legacy_v1_12_graph.json` | fixture | static | D-65.09 mandates capture from a real v1.12 commit run — no in-tree analog; produced by a one-shot `git checkout v1.12 && graphify run …` against a small corpus, then committed verbatim. |

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `tests/fixtures/`
**Files scanned:** `cache.py`, `validate.py`, `extract.py` (3 emission sites), `export.py:to_json`, `report.py` (inf_avg block), `security.py` (sanitize_label), `output.py` (stderr emitters), `tests/test_cache.py` (head)
**Pattern extraction date:** 2026-05-06
