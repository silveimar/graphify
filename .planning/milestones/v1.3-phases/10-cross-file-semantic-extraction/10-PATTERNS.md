# Phase 10: Cross-File Semantic Extraction with Entity Deduplication - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/batch.py` | service | transform | `graphify/cluster.py` | role-match (grouping stage, optional heavy dep) |
| `graphify/dedup.py` | service | transform | `graphify/cluster.py` + `graphify/build.py` | role-match (pure function, dict in/out) |
| `graphify/validate.py` | utility | transform | `graphify/validate.py` (self — extension) | exact |
| `graphify/report.py` | utility | transform | `graphify/report.py` (self — new section) | exact |
| `graphify/serve.py` | middleware | request-response | `graphify/serve.py` (self — new thin layer) | exact |
| `graphify/__main__.py` | config | request-response | `graphify/__main__.py` (self — new flags) | exact |
| `pyproject.toml` | config | — | `pyproject.toml` (self — new `[dedup]` extra) | exact |
| `tests/test_batch.py` | test | — | `tests/test_cluster.py` | exact |
| `tests/test_dedup.py` | test | — | `tests/test_validate.py` + `tests/test_build.py` | role-match |
| `tests/test_validate.py` | test | — | `tests/test_validate.py` (self — extension) | exact |
| `tests/test_serve.py` | test | — | `tests/test_serve.py` (self — extension) | exact |

---

## Pattern Assignments

### `graphify/batch.py` (service, transform)

**Analog:** `graphify/cluster.py`

**Why this analog:** `cluster.py` is the direct peer: a pipeline-stage module that takes a NetworkX graph, applies an algorithm with an optional heavy dependency (graspologic), and returns a plain-dict result. `batch.py` follows the same structure — takes paths + ast_results, builds an import graph, returns `list[dict]` of `FileCluster` objects. Same module-level docstring, same `from __future__ import annotations`, same `_private` helper pattern, same stderr progress prints.

**Imports pattern** (`cluster.py` lines 1-8):
```python
"""Community detection on NetworkX graphs. Uses Leiden (graspologic) if available, falls back to Louvain (networkx). Splits oversized communities. Returns cohesion scores."""
from __future__ import annotations
import contextlib
import inspect
import io
import sys
import networkx as nx
```

**Optional-dep + lazy fallback pattern** (`cluster.py` lines 30-52):
```python
try:
    from graspologic.partition import leiden
    old_stderr = sys.stderr
    try:
        sys.stderr = io.StringIO()
        with _suppress_output():
            result = leiden(G)
    finally:
        sys.stderr = old_stderr
    return result
except ImportError:
    pass

# Fallback: networkx louvain (available since networkx 2.7).
kwargs: dict = {"seed": 42, "threshold": 1e-4}
if "max_level" in inspect.signature(nx.community.louvain_communities).parameters:
    kwargs["max_level"] = 10
communities = nx.community.louvain_communities(G, **kwargs)
return {node: cid for cid, nodes in enumerate(communities) for node in nodes}
```

**Public function shape** (`cluster.py` lines 59-74 — copy this signature pattern):
```python
def cluster(G: nx.Graph) -> dict[int, list[str]]:
    """Run Leiden community detection. Returns {community_id: [node_ids]}.
    ...
    """
    if G.number_of_nodes() == 0:
        return {}
    if G.is_directed():
        G = G.to_undirected()
    if G.number_of_edges() == 0:
        return {i: [n] for i, n in enumerate(sorted(G.nodes))}
```

**For `batch.py`, translate to:**
```python
def cluster_files(paths: list[Path], ast_results: list[dict],
                  token_budget: int = 50_000) -> list[dict]:
    """Group import-connected files into FileCluster dicts.
    Returns [] if paths is empty.
    Each cluster: {"files": [...], "token_estimate": int, "cluster_id": int}
    """
    if not paths:
        return []
    # build import graph, find connected components, split by dir cap + token budget
```

**Constants block** (`cluster.py` lines 55-56 — use SCREAMING_SNAKE for module-level tuning knobs):
```python
_MAX_COMMUNITY_FRACTION = 0.25
_MIN_SPLIT_SIZE = 10
```

**Splitting helper** (`cluster.py` lines 107-122 — model `_split_by_budget` on `_split_community`):
```python
def _split_community(G: nx.Graph, nodes: list[str]) -> list[list[str]]:
    """Run a second Leiden pass on a community subgraph to split it further."""
    subgraph = G.subgraph(nodes)
    if subgraph.number_of_edges() == 0:
        return [[n] for n in sorted(nodes)]
    try:
        sub_partition = _partition(subgraph)
        ...
    except Exception:
        return [sorted(nodes)]
```

---

### `graphify/dedup.py` (service, transform)

**Analog:** `graphify/cluster.py` (module structure) + `graphify/build.py` (extraction-dict mutation)

**Why this analog:** `cluster.py` provides the optional-dep guard pattern for `sentence-transformers`. `build.py` shows how to consume extraction dicts (nodes/edges lists) and the "preserve provenance via attribute dicts" approach.

**Module header + optional-dep guard** (copy from `cluster.py` lines 1-8, adapt for sentence-transformers):
```python
"""Post-extraction entity deduplication. Fuzzy + embedding merge of fragmented nodes."""
from __future__ import annotations
import difflib
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

_MODEL: "SentenceTransformer | None" = None
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
```

**stderr progress print pattern** (from `build.py` line 42 — prefix all output with `[graphify]`):
```python
print(f"[graphify] Extraction warning ({len(real_errors)} issues): {real_errors[0]}", file=sys.stderr)
```

**Extraction-dict consumption pattern** (`build.py` lines 44-66 — iterate nodes/edges, skip missing fields gracefully):
```python
G: nx.Graph = nx.DiGraph() if directed else nx.Graph()
for node in extraction.get("nodes", []):
    G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
node_set = set(G.nodes())
for edge in extraction.get("edges", []):
    ...
    src, tgt = edge["source"], edge["target"]
    if src not in node_set or tgt not in node_set:
        continue  # skip dangling edges — expected, not an error
    attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
    G.add_edge(src, tgt, **attrs)
```

**Public function shape** — pure function, plain dicts in/out, matching pipeline contract:
```python
def dedup(
    extraction: dict,
    *,
    fuzzy_threshold: float = 0.90,
    embed_threshold: float = 0.85,
    cross_type: bool = False,
    encoder=None,          # callable(list[str]) -> np.ndarray | None (for testability)
) -> tuple[dict, dict]:
    """Merge fuzzy-matched and embedding-similar nodes. Returns (dedup'd extraction, report dict).

    encoder: inject a mock encoder in tests to avoid loading 90MB model.
    If None, loads sentence-transformers/all-MiniLM-L6-v2 on first call.
    """
```

**Atomic file write pattern** (`cache.py` lines 70-76 — use for dedup_report.json write):
```python
tmp = entry.with_suffix(".tmp")
try:
    tmp.write_text(json.dumps(result), encoding="utf-8")
    os.replace(tmp, entry)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

**Corpus hash pattern** (`cache.py` lines 20-33 — extend for corpus-level cache key):
```python
def file_hash(path: Path) -> str:
    """SHA256 of file contents + resolved path."""
    h = hashlib.sha256()
    h.update(content)
    h.update(b"\x00")
    h.update(str(p.resolve()).encode())
    return h.hexdigest()
```
Corpus hash should be: `hashlib.sha256(json.dumps(sorted(file_hash(Path(p)) for p in paths)).encode()).hexdigest()`

---

### `graphify/validate.py` — extension (utility, transform)

**Analog:** `graphify/validate.py` (self — existing pattern to extend)

**Existing pattern to extend** (`validate.py` lines 26-37):
```python
for i, node in enumerate(data["nodes"]):
    if not isinstance(node, dict):
        errors.append(f"Node {i} must be an object")
        continue
    for field in REQUIRED_NODE_FIELDS:
        if field not in node:
            errors.append(f"Node {i} (id={node.get('id', '?')!r}) missing required field '{field}'")
    if "file_type" in node and node["file_type"] not in VALID_FILE_TYPES:
        errors.append(
            f"Node {i} (id={node.get('id', '?')!r}) has invalid file_type "
            f"'{node['file_type']}' - must be one of {sorted(VALID_FILE_TYPES)}"
        )
```

**Extension to add after the required-fields loop** (D-12 — new checks, same error-list return pattern):
```python
# D-12: source_file may be str OR list[str] after dedup
if "source_file" in node:
    sf = node["source_file"]
    if not isinstance(sf, (str, list)):
        errors.append(f"Node {i} (id={node.get('id', '?')!r}) 'source_file' must be str or list[str], got {type(sf).__name__}")
    elif isinstance(sf, list) and not all(isinstance(s, str) for s in sf):
        errors.append(f"Node {i} (id={node.get('id', '?')!r}) 'source_file' list must contain only strings")
# D-11: merged_from is optional; when present must be list[str]
if "merged_from" in node:
    mf = node["merged_from"]
    if not isinstance(mf, list) or not all(isinstance(m, str) for m in mf):
        errors.append(f"Node {i} (id={node.get('id', '?')!r}) 'merged_from' must be list[str]")
```

**Important:** `source_file` is in `REQUIRED_NODE_FIELDS` — the existing required-field check will still fire for nodes missing it entirely. The new isinstance check only runs when the field exists. Do not remove `source_file` from `REQUIRED_NODE_FIELDS`.

---

### `graphify/report.py` — extension (utility, transform)

**Analog:** `graphify/report.py` (self — new section at bottom of `generate()`)

**Existing section-append pattern** (`report.py` lines 163-200 — "Ambiguous Edges" and "Knowledge Gaps" sections):
```python
ambiguous = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("confidence") == "AMBIGUOUS"]
if ambiguous:
    lines += ["", "## Ambiguous Edges - Review These"]
    for u, v, d in ambiguous:
        ...
        lines += [
            f"- `{ul}` → `{vl}`  [AMBIGUOUS]",
            f"  {d.get('source_file', '')} · relation: {d.get('relation', 'unknown')}",
        ]
```

**Pattern for the new "Entity Dedup" section** — add `dedup_report: dict | None = None` to `generate()` signature and append before `return "\n".join(lines)`:
```python
if dedup_report and dedup_report.get("merges"):
    summary = dedup_report.get("summary", {})
    lines += [
        "",
        "## Entity Dedup",
        f"- {summary.get('merges', 0)} entities merged · "
        f"{summary.get('total_nodes_before', '?')} nodes → {summary.get('total_nodes_after', '?')} nodes",
    ]
    for merge in dedup_report["merges"][:10]:  # cap to 10 in report
        eliminated_labels = ", ".join(e.get("label", e.get("id", "?")) for e in merge.get("eliminated", []))
        lines.append(
            f"- `{merge['canonical_label']}` ← {eliminated_labels} "
            f"[fuzzy={merge.get('fuzzy_score', 0):.3f}, cos={merge.get('cosine_score', 0):.3f}]"
        )
    if len(dedup_report["merges"]) > 10:
        lines.append(f"  (+{len(dedup_report['merges']) - 10} more — see dedup_report.json)")
```

**_sanitize_md helper** (`report.py` lines 249-253 — apply to canonical_label and eliminated labels):
```python
def _sanitize_md(text: str) -> str:
    """Strip characters that could inject markdown structure from untrusted LLM output."""
    text = text.replace("`", "'").replace("<", "&lt;").replace(">", "&gt;")
    return text
```

---

### `graphify/serve.py` — extension (middleware, request-response)

**Analog:** `graphify/serve.py` (self — thin lookup layer at `serve()` startup)

**Sidecar state initialisation slot** (`serve.py` lines 962-975 — add dedup alias map next to existing sidecar state):
```python
G = _load_graph(graph_path)
communities = _communities_from_graph(G)
_graph_mtime = Path(graph_path).stat().st_mtime if Path(graph_path).exists() else 0.0
_branching_factor = _compute_branching_factor(G)
_out_dir = Path(graph_path).parent
_annotations: list[dict] = _compact_annotations(_out_dir / "annotations.jsonl")
_agent_edges: list[dict] = _load_agent_edges(_out_dir / "agent-edges.json")
_telemetry: dict = _load_telemetry(_out_dir / "telemetry.json")
_session_id = str(uuid.uuid4())
# ADD HERE (D-16):
# _alias_map: dict[str, str] = _load_dedup_report(_out_dir)
```

**Load helper pattern** (`serve.py` lines 81-88 — `_load_telemetry` is the exact template):
```python
def _load_telemetry(path: Path) -> dict:
    """Load telemetry.json as a dict. Returns default on missing or corrupt."""
    if not path.exists():
        return {"counters": {}, "threshold": 5}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"counters": {}, "threshold": 5}
```

**Translate to `_load_dedup_report`:**
```python
def _load_dedup_report(out_dir: Path) -> dict[str, str]:
    """Load alias_map from dedup_report.json. Returns {} if dedup was not run."""
    path = out_dir / "dedup_report.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("alias_map", {})  # {eliminated_id: canonical_id}
    except (json.JSONDecodeError, OSError):
        return {}
```

**Alias redirect injection point** (`serve.py` line 750 — at the top of `_run_query_graph`, after argument parsing, before `_score_nodes`):
```python
question = str(arguments.get("question", ""))
mode = str(arguments.get("mode", "bfs"))
depth = max(1, min(int(arguments.get("depth", 3)), 6))
budget = int(arguments.get("budget", arguments.get("token_budget", 2000)))
# ADD: resolve merged-away node IDs before scoring
# node_id = alias_map.get(node_id, node_id)  — passed from _tool_query_graph closure
```

**Atomic write pattern** (`serve.py` lines 91-100 — `_save_telemetry` using `os.replace`):
```python
def _save_telemetry(out_dir: Path, data: dict) -> None:
    """Atomically write telemetry.json to out_dir using os.replace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "telemetry.json"
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```

---

### `graphify/__main__.py` — extension (config, request-response)

**Analog:** `graphify/__main__.py` (self — existing `--obsidian` flag parsing block)

**Flag-parsing pattern** (`__main__.py` lines 988-1011 — manual `while i < len(args)` loop, no argparse for top-level commands):
```python
if cmd == "--obsidian":
    graph_path = "graphify-out/graph.json"
    obsidian_dir = "graphify-out/obsidian"
    dry_run = False
    force = False
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--graph" and i + 1 < len(args):
            graph_path = args[i + 1]; i += 2
        elif args[i].startswith("--graph="):
            graph_path = args[i].split("=", 1)[1]; i += 1
        elif args[i] == "--obsidian-dir" and i + 1 < len(args):
            obsidian_dir = args[i + 1]; i += 2
        elif args[i] == "--dry-run":
            dry_run = True; i += 1
        elif args[i] == "--force":
            force = True; i += 1
        else:
            print(f"error: unknown --obsidian option: {args[i]}", file=sys.stderr)
            sys.exit(2)
```

**Translate for `run` command flags** — new flags to add to the existing `run` command argument loop (D-14, D-15, D-17):
```python
# Within the run command's args loop:
elif args[i] == "--dedup":
    dedup = True; i += 1
elif args[i] == "--dedup-fuzzy-threshold" and i + 1 < len(args):
    dedup_fuzzy_threshold = float(args[i + 1]); i += 2
elif args[i].startswith("--dedup-fuzzy-threshold="):
    dedup_fuzzy_threshold = float(args[i].split("=", 1)[1]); i += 1
elif args[i] == "--dedup-embed-threshold" and i + 1 < len(args):
    dedup_embed_threshold = float(args[i + 1]); i += 2
elif args[i] == "--dedup-cross-type":
    dedup_cross_type = True; i += 1
elif args[i] == "--obsidian-dedup":
    obsidian_dedup = True; i += 1
elif args[i] == "--batch-token-budget" and i + 1 < len(args):
    batch_token_budget = int(args[i + 1]); i += 2
elif args[i].startswith("--batch-token-budget="):
    batch_token_budget = int(args[i].split("=", 1)[1]); i += 1
```

**Help text pattern** (`__main__.py` lines 910-914 — indented multi-line flags under command):
```python
print("  --obsidian              export an already-built graphify-out/graph.json to an Obsidian vault")
print("    --obsidian-dir <path>   output vault directory (default graphify-out/obsidian)")
```

**validate-profile error path** (`__main__.py` lines 963-978 — `sys.exit(2)` on bad args, `sys.exit(1)` on failure):
```python
if cmd == "--validate-profile":
    if len(sys.argv) < 3:
        print("Usage: graphify --validate-profile <vault-path>", file=sys.stderr)
        sys.exit(2)
    ...
    if result.errors:
        sys.exit(1)
```

---

### `pyproject.toml` — extension (config)

**Analog:** `pyproject.toml` (self — existing `[project.optional-dependencies]` block)

**Existing optional-extras pattern** (`pyproject.toml` lines 43-52):
```toml
[project.optional-dependencies]
mcp = ["mcp"]
neo4j = ["neo4j"]
pdf = ["pypdf", "html2text"]
watch = ["watchdog"]
leiden = ["graspologic"]
office = ["python-docx", "openpyxl"]
obsidian = ["PyYAML"]
video = ["faster-whisper", "yt-dlp"]
all = ["mcp", "neo4j", "pypdf", "html2text", "watchdog", "graspologic", "python-docx", "openpyxl", "PyYAML", "faster-whisper", "yt-dlp"]
```

**Add `dedup` line after `obsidian`, and extend `all`:**
```toml
dedup = ["sentence-transformers"]
all = [..., "sentence-transformers"]
```

Pattern: one line per extra, single-quoted dep strings, alphabetical within a group is conventional but not enforced. Add `"sentence-transformers"` to the `all` list.

---

### `tests/test_batch.py` (test)

**Analog:** `tests/test_cluster.py`

**Why this analog:** `test_cluster.py` is the direct peer — tests a pure-function pipeline stage that takes a graph, uses fixtures for input data, and makes structural assertions on the returned dict. `test_batch.py` follows the same shape.

**File header + fixture pattern** (`test_cluster.py` lines 1-11):
```python
import json
import sys
import networkx as nx
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, cohesion_score, score_all

FIXTURES = Path(__file__).parent / "fixtures"

def make_graph():
    return build_from_json(json.loads((FIXTURES / "extraction.json").read_text()))
```

**Translate for `test_batch.py`:**
```python
from __future__ import annotations
import json
from pathlib import Path
import networkx as nx
from graphify.batch import cluster_files, _build_import_graph, _topological_order

FIXTURES = Path(__file__).parent / "fixtures"

def _make_paths_and_results(tmp_path: Path) -> tuple[list[Path], list[dict]]:
    """Create stub files + extraction dicts with import edges for batch tests."""
    auth = tmp_path / "auth.py"; auth.write_text("# auth")
    models = tmp_path / "models.py"; models.write_text("# models")
    api = tmp_path / "api.py"; api.write_text("# api")
    paths = [auth, models, api]
    ast_results = [
        {"nodes": [], "edges": [{"source_file": str(auth), "target": str(models),
                                  "relation": "imports", "confidence": "EXTRACTED",
                                  "source": "auth", "target": "models"}]},
        ...
    ]
    return paths, ast_results
```

**Structural assertion style** (`test_cluster.py` lines 13-22 — assert type and coverage, not exact values):
```python
def test_cluster_returns_dict():
    G = make_graph()
    communities = cluster(G)
    assert isinstance(communities, dict)

def test_cluster_covers_all_nodes():
    G = make_graph()
    communities = cluster(G)
    all_nodes = {n for nodes in communities.values() for n in nodes}
    assert all_nodes == set(G.nodes)
```

**stdout suppression test** (`test_cluster.py` lines 56-66 — add same test for batch.py):
```python
def test_cluster_does_not_write_to_stdout(capsys):
    G = make_graph()
    cluster(G)
    captured = capsys.readouterr()
    assert captured.out == "", f"cluster() wrote to stdout: {captured.out!r}"
```

---

### `tests/test_dedup.py` (test)

**Analog:** `tests/test_validate.py` (inline fixture dict style) + `tests/test_build.py` (multi-extraction merge assertions)

**Why this analog:** `test_validate.py` shows how to write inline fixture dicts for schema tests — directly relevant to the D-12 extraction-dict schema tests in `test_dedup.py`. `test_build.py` shows how to assert on extraction-dict transformations.

**Inline fixture dict style** (`test_validate.py` lines 4-13):
```python
VALID = {
    "nodes": [
        {"id": "n1", "label": "Foo", "file_type": "code", "source_file": "foo.py"},
        {"id": "n2", "label": "Bar", "file_type": "document", "source_file": "bar.md"},
    ],
    "edges": [
        {"source": "n1", "target": "n2", "relation": "references",
         "confidence": "EXTRACTED", "source_file": "foo.py", "weight": 1.0},
    ],
}
```

**Multi-extraction merge assertion** (`test_build.py` lines 33-41):
```python
def test_build_merges_multiple_extractions():
    ext1 = {"nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
            "edges": [], "input_tokens": 0, "output_tokens": 0}
    ext2 = {"nodes": [{"id": "n2", "label": "B", "file_type": "document", "source_file": "b.md"}],
            "edges": [...], "input_tokens": 0, "output_tokens": 0}
    G = build([ext1, ext2])
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1
```

**Mocked encoder for CI** (from RESEARCH.md Pattern - no model download in tests):
```python
import numpy as np

def _fixed_encoder(labels: list[str]) -> np.ndarray:
    """Deterministic mock encoder — same label always produces same vector."""
    result = []
    for label in labels:
        rng = np.random.default_rng(abs(hash(label)) % (2**32))
        vec = rng.standard_normal(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        result.append(vec)
    return np.array(result)
```

**Error-list assertion style** (`test_validate.py` lines 15-24 — assert on specific field names in error strings):
```python
def test_valid_passes():
    assert validate_extraction(VALID) == []

def test_missing_nodes_key():
    errors = validate_extraction({"edges": []})
    assert any("nodes" in e for e in errors)
```

**Translate dedup test assertions:**
```python
def test_dedup_produces_report():
    extraction = {...}
    result_extraction, report = dedup(extraction, encoder=_fixed_encoder)
    assert "merges" in report
    assert "alias_map" in report
    assert isinstance(report["merges"], list)

def test_edge_weight_summed():
    extraction = {
        "nodes": [
            {"id": "n1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "Auth_Service", "file_type": "code", "source_file": "b.py"},
            {"id": "n3", "label": "handler", "file_type": "code", "source_file": "c.py"},
        ],
        "edges": [
            {"source": "n1", "target": "n3", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
            {"source": "n2", "target": "n3", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0},
        ],
    }
    result, _ = dedup(extraction, encoder=_fixed_encoder, fuzzy_threshold=0.85)
    # After merge, edge weight from canonical to handler should be 2.0 (sum)
    merged_edges = {(e["source"], e["target"]): e for e in result["edges"]}
    assert ...
```

---

### `tests/test_validate.py` — extension (test)

**Analog:** `tests/test_validate.py` (self — add new test functions at end of file)

**Extension pattern** — add two new test functions after `test_assert_valid_passes_silently` (line 87):
```python
def test_source_file_as_list():
    """D-12: source_file list[str] is valid after dedup."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": ["a.py", "b.py"], "merged_from": ["n2"]}],
        "edges": [],
    }
    assert validate_extraction(data) == []

def test_merged_from_accepted():
    """D-11: merged_from list[str] is optional; when present must be list[str]."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": "a.py", "merged_from": ["n2", "n3"]}],
        "edges": [],
    }
    assert validate_extraction(data) == []

def test_source_file_invalid_type():
    """D-12: source_file that is neither str nor list[str] must fail validation."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": 42}],
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("source_file" in e for e in errors)
```

---

### `tests/test_serve.py` — extension (test)

**Analog:** `tests/test_serve.py` (self — import new helper, add alias redirect test)

**Existing import block** (`test_serve.py` lines 1-36 — add `_load_dedup_report` to imports):
```python
from graphify.serve import (
    _communities_from_graph,
    _score_nodes,
    _bfs,
    ...
    _run_query_graph,
    QUERY_GRAPH_META_SENTINEL,
    # ADD:
    # _load_dedup_report,
)
```

**Test pattern** (modeled on `test_serve.py` lines 39-49 `_make_graph()` helper):
```python
def test_load_dedup_report_missing_returns_empty(tmp_path):
    """_load_dedup_report returns {} when file does not exist."""
    result = _load_dedup_report(tmp_path)
    assert result == {}

def test_load_dedup_report_reads_alias_map(tmp_path):
    """_load_dedup_report returns the alias_map dict from dedup_report.json."""
    report = {
        "version": "1",
        "alias_map": {"auth": "authentication_service"},
        "merges": [],
    }
    (tmp_path / "dedup_report.json").write_text(json.dumps(report))
    result = _load_dedup_report(tmp_path)
    assert result == {"auth": "authentication_service"}
```

---

## Shared Patterns

### Optional Heavy Dependency Guard
**Source:** `graphify/cluster.py` lines 30-52
**Apply to:** `graphify/batch.py` (sentence-transformers not needed, but pattern applies if future heavy dep), `graphify/dedup.py` (sentence-transformers)

```python
try:
    from graspologic.partition import leiden
    ...
except ImportError:
    pass
# fallback logic here
```

For `dedup.py`, no fallback exists for sentence-transformers when `--dedup` is active — raise `RuntimeError` with install hint instead of silent degradation (same pattern as `serve.py` lines 959-963):
```python
except ImportError as e:
    raise ImportError("mcp not installed. Run: pip install mcp") from e
```

### Atomic JSON File Write
**Source:** `graphify/cache.py` lines 70-76 and `graphify/serve.py` lines 91-100
**Apply to:** `graphify/dedup.py` writing `dedup_report.json` and `dedup_report.md`

```python
tmp = target.with_suffix(".tmp")
try:
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

### Stderr Progress Prints
**Source:** `graphify/build.py` line 42
**Apply to:** `graphify/batch.py` (cluster progress), `graphify/dedup.py` (model load, merge count)

```python
print(f"[graphify] ...", file=sys.stderr)
```

### Label Sanitization Before Output
**Source:** `graphify/security.py` lines 188-200 (`sanitize_label`)
**Apply to:** `graphify/dedup.py` — call `sanitize_label(canonical_label)` before writing canonical labels to `dedup_report.md` and before embedding in the `GRAPH_REPORT.md` "Entity Dedup" section

```python
from graphify.security import sanitize_label
# ...
label = sanitize_label(node.get("label", ""))
```

### `from __future__ import annotations` + module docstring
**Source:** Every module in `graphify/` (e.g., `cluster.py` lines 1-2, `build.py` lines 23-24)
**Apply to:** `graphify/batch.py` and `graphify/dedup.py` — both must start with module docstring then `from __future__ import annotations`

### Test Fixture Dict Pattern
**Source:** `tests/test_validate.py` lines 4-13, `tests/test_build.py` lines 33-41
**Apply to:** `tests/test_batch.py` and `tests/test_dedup.py` — use inline minimal dicts, not file fixtures, for unit tests. Only use `FIXTURES / "extraction.json"` when the real multi-file fixture is needed for integration assertions.

---

## No Analog Found

All files have analogs. No entries in this section.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | — |

---

## Metadata

**Analog search scope:** `graphify/` (all modules), `tests/` (all test files), `pyproject.toml`
**Files scanned:** 12 source files read in full (cluster.py, build.py, validate.py, cache.py, serve.py, report.py, security.py, __main__.py, pyproject.toml, test_cluster.py, test_validate.py, test_build.py, test_serve.py)
**Pattern extraction date:** 2026-04-16

---

## PATTERN MAPPING COMPLETE
