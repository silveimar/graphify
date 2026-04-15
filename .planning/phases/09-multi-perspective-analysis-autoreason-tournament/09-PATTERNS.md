# Phase 9: Multi-Perspective Analysis with Autoreason Tournament - Pattern Map

**Mapped:** 2026-04-14
**Files analyzed:** 5 (2 Python lib additions, 1 skill.md section, 2 test files)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `graphify/analyze.py` (add `render_analysis_context()`) | utility | transform | `graphify/analyze.py::suggest_questions()` (same file, same pattern) | exact |
| `graphify/report.py` (add `render_analysis()`) | utility | transform | `graphify/report.py::generate()` (same file, same pattern) | exact |
| `graphify/skill.md` (add `## For /graphify analyze` section) | orchestrator | request-response + LLM calls | `graphify/skill.md` Step 3B + Step 4 blocks (same file) | exact |
| `tests/test_analyze.py` (add tests for `render_analysis_context`) | test | transform | `tests/test_analyze.py` existing tests | exact |
| `tests/test_report.py` (add tests for `render_analysis`) | test | transform | `tests/test_report.py` existing tests | exact |

---

## Pattern Assignments

### `graphify/analyze.py` — add `render_analysis_context()`

**Analog:** `graphify/analyze.py::suggest_questions()` (lines 335–454)

**Key facts:**
- `knowledge_gaps()` does NOT exist in `analyze.py` — gap logic lives inline in `report.py` (lines 134–160). RESEARCH.md's file list is slightly wrong on this. The new function still belongs in `analyze.py` as a serializer.
- `render_analysis_context()` is a pure transform: takes graph + mechanical analysis dicts → returns a compact string for LLM consumption. No networkx write, no side effects.

**Imports pattern** (`analyze.py` lines 1–4):
```python
"""Graph analysis: god nodes (most connected), surprising connections (cross-community), suggested questions."""
from __future__ import annotations
import networkx as nx
```

**Function signature and docstring pattern** (lines 335–345, `suggest_questions`):
```python
def suggest_questions(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    top_n: int = 7,
) -> list[dict]:
    """
    Generate questions the graph is uniquely positioned to answer.
    Based on: AMBIGUOUS edges, bridge nodes, underexplored god nodes, isolated nodes.
    Each question has a 'type', 'question', and 'why' field.
    """
```

**Copy this signature shape** for `render_analysis_context()`:
```python
def render_analysis_context(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    top_n_nodes: int = 20,
) -> str:
    """Serialize graph structure to a compact prompt-safe text block for tournament lens agents."""
```

**Lines-list builder pattern** (lines 346–383, `suggest_questions` internal):
```python
    lines = [...]
    for n in god_node_list[:top_n_nodes]:
        lines.append(f"  - {n['label']} ({n['edges']} connections)")
    # ... more appends ...
    return "\n".join(lines)
```
This is identical to `report.py::generate()` — build a `lines` list, `append()` per item, return `"\n".join(lines)`.

**Node attribute access pattern** (lines 53–55, `god_nodes`):
```python
result.append({
    "id": node_id,
    "label": G.nodes[node_id].get("label", node_id),
    "edges": deg,
})
```
Use `.get("label", node_id)` defensively — never direct attribute access.

**Private helper pattern** (lines 6–8, `_node_community_map`):
```python
def _node_community_map(communities: dict[int, list[str]]) -> dict[str, int]:
    """Invert communities dict: node_id -> community_id."""
    return {n: cid for cid, nodes in communities.items() for n in nodes}
```
Small, single-responsibility helpers with leading underscore. `render_analysis_context` may need `_node_community_map` if it annotates communities by node.

---

### `graphify/report.py` — add `render_analysis()`

**Analog:** `graphify/report.py::generate()` (lines 15–175) — the existing GRAPH_REPORT.md renderer. `render_analysis()` is structurally identical: takes structured dicts, builds a markdown string via `lines` list, returns it.

**Imports pattern** (`report.py` lines 1–5):
```python
# generate GRAPH_REPORT.md - the human-readable audit trail
from __future__ import annotations
import re
from datetime import date
import networkx as nx
```
New function will need `from datetime import date` (already present). No new imports needed.

**Function signature pattern** (lines 15–26):
```python
def generate(
    G: nx.Graph,
    communities: dict[int, list[str]],
    cohesion_scores: dict[int, float],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    detection_result: dict,
    token_cost: dict,
    root: str,
    suggested_questions: list[dict] | None = None,
) -> str:
    today = date.today().isoformat()
```

**Copy this signature shape** for `render_analysis()`:
```python
def render_analysis(
    lens_results: list[dict],
    root: str,
    lenses_run: list[str],
) -> str:
    """Render GRAPH_ANALYSIS.md from per-lens tournament result dicts."""
    today = date.today().isoformat()
```

Where each `lens_result` dict has shape:
`{lens, verdict, confidence, confidence_label, findings_text, voting_rationale, top_finding}`

**Header + lines-list builder pattern** (lines 39–43):
```python
    lines = [
        f"# Graph Report - {root}  ({today})",
        "",
        "## Corpus Check",
    ]
```

**Section append pattern** (lines 70–75):
```python
    lines += [
        "",
        "## God Nodes (most connected - your core abstractions)",
    ]
    for i, node in enumerate(god_node_list, 1):
        lines.append(f"{i}. `{node['label']}` - {node['edges']} edges")
```

**Conditional section pattern** (lines 78–95, surprising connections):
```python
    lines += ["", "## Surprising Connections (you probably didn't know these)"]
    if surprise_list:
        for s in surprise_list:
            # ... format each entry
    else:
        lines.append("- None detected - all connections are within the same source files.")
```
Apply same pattern for "Clean" lens verdict: always emit the section, show verdict + rationale instead of silence.

**Cross-module import pattern** (lines 108, 135):
```python
    from .analyze import _is_file_node as _ifn
    from .analyze import _is_file_node, _is_concept_node
```
Lazy relative import inside function body — used when importing at module top would create circular deps. `render_analysis()` has no cross-module deps so this is not needed, but the pattern is available if required.

**Return** (line 175):
```python
    return "\n".join(lines)
```

---

### `graphify/skill.md` — add `## For /graphify analyze` section

**Analog:** Entire skill.md, specifically:
- Step 3B subagent dispatch pattern (lines 237–304) — for understanding inline LLM call blocks
- Step 4 build+analyze+report block (lines 399–447) — for the `render_analysis()` call and `write_text()` output pattern

**Section header pattern** (matches all other sections):
```
## For /graphify analyze
```
Consistent with `## For /graphify add`, `## For --watch`, `## For git commit hook`.

**Inline python bash block pattern** (lines 399–447):
```bash
$(cat graphify-out/.graphify_python) -c "
import sys, json
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text())
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text())
# ... processing ...
Path('graphify-out/GRAPH_REPORT.md').write_text(report)
"
```
Tournament section uses the same `$(cat graphify-out/.graphify_python) -c "..."` wrapper with `Path(...).write_text(...)` for `GRAPH_ANALYSIS.md`.

**Analysis JSON reading pattern** (line 441):
```python
analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
Path('graphify-out/.graphify_analysis.json').write_text(json.dumps(analysis, indent=2))
```
Tournament section reads `.graphify_analysis.json` (already written by Step 4) via:
```python
analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text())
gods = analysis['gods']
surprises = analysis['surprises']
```

**Subagent prompt pattern** (lines 251–304) — for tournament LLM call blocks:
Each role (incumbent, adversary, synthesizer, judge) follows:
```
System: [Role description. Behavioral constraints. Output format.]

User: [GRAPH_CONTEXT_BLOCK]
      [Role-specific input (prior candidate text)]
      [Task instruction]
```
Key enforcement from line 255: `Output ONLY valid JSON...` equivalent is the judge's `"1st: [label] 2nd: [label] 3rd: [label]" — nothing else.`

**Error handling pattern** (lines 442–445):
```python
if G.number_of_nodes() == 0:
    print('ERROR: Graph is empty - extraction produced no nodes.')
    raise SystemExit(1)
```
Tournament section should check `.graphify_analysis.json` exists before reading; if absent, tell user to run `/graphify` first.

**Inline Borda count computation pattern** — pure Python dict/list manipulation, no imports beyond stdlib:
```python
# Standard Borda count — n=3 candidates: 1st=2pts, 2nd=1pt, 3rd=0pts
def borda_count(rankings):
    scores = {"A": 0, "B": 0, "AB": 0}
    for ranking in rankings:
        for pts, label in enumerate(reversed(ranking)):
            scores[label] += pts
    return scores
```
Written as inline python -c block, not as a library function (D-75: CLI stays utilities-only).

---

### `tests/test_analyze.py` — add tests for `render_analysis_context()`

**Analog:** `tests/test_analyze.py` existing tests (lines 1–232)

**File header pattern** (lines 1–9):
```python
"""Tests for analyze.py."""
import json
import networkx as nx
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.analyze import god_nodes, surprising_connections, _is_concept_node, graph_diff, _surprise_score, _file_category

FIXTURES = Path(__file__).parent / "fixtures"
```
Add `render_analysis_context` to the import line.

**Fixture graph pattern** (lines 12–13):
```python
def make_graph():
    return build_from_json(json.loads((FIXTURES / "extraction.json").read_text()))
```
Reuse `make_graph()` — it already exists. Build `communities` and `god_node_list` from it for test input.

**Test structure pattern** (lines 16–35):
```python
def test_god_nodes_returns_list():
    G = make_graph()
    result = god_nodes(G, top_n=3)
    assert isinstance(result, list)
    assert len(result) <= 3

def test_god_nodes_have_required_keys():
    G = make_graph()
    result = god_nodes(G, top_n=1)
    assert "id" in result[0]
    assert "label" in result[0]
    assert "edges" in result[0]
```
Pattern for `render_analysis_context` tests:
- `test_render_analysis_context_returns_str()` — assert isinstance(result, str)
- `test_render_analysis_context_contains_node_count()` — assert "nodes" in result or str(G.number_of_nodes()) in result
- `test_render_analysis_context_contains_god_nodes()` — assert a god node label appears in result
- `test_render_analysis_context_empty_surprises()` — pass empty surprise_list, assert no crash

**Manual graph construction pattern** (lines 63–80, `test_surprising_connections_single_file_uses_community_bridges`):
```python
G = nx.Graph()
for i in range(5):
    G.add_node(f"a{i}", label=f"A{i}", file_type="code", source_file="single.py",
               source_location=f"L{i}")
G.add_edge("a4", "b0", relation="references", confidence="INFERRED",
           source_file="single.py", weight=0.5)
```
Use for `render_analysis_context` tests that need minimal controlled graphs (e.g., testing empty communities edge case).

---

### `tests/test_report.py` — add tests for `render_analysis()`

**Analog:** `tests/test_report.py` existing tests (lines 1–63)

**File header pattern** (lines 1–8):
```python
import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate

FIXTURES = Path(__file__).parent / "fixtures"
```
Add `render_analysis` to the `from graphify.report import` line.

**`make_inputs()` helper pattern** (lines 10–20):
```python
def make_inputs():
    extraction = json.loads((FIXTURES / "extraction.json").read_text())
    G = build_from_json(extraction)
    communities = cluster(G)
    cohesion = score_all(G, communities)
    labels = {cid: f"Community {cid}" for cid in communities}
    gods = god_nodes(G)
    surprises = surprising_connections(G)
    detection = {"total_files": 4, "total_words": 62400, "needs_graph": True, "warning": None}
    tokens = {"input": extraction["input_tokens"], "output": extraction["output_tokens"]}
    return G, communities, cohesion, labels, gods, surprises, detection, tokens
```
Add a parallel `make_lens_results()` helper that returns a synthetic list of per-lens dicts for `render_analysis()` tests:
```python
def make_lens_results():
    return [
        {"lens": "security", "verdict": "Clean", "confidence": 1.0, "confidence_label": "high",
         "findings_text": "No issues found.", "voting_rationale": "3-0 unanimous for incumbent.", "top_finding": ""},
        {"lens": "architecture", "verdict": "Finding", "confidence": 0.67, "confidence_label": "medium",
         "findings_text": "God node X is overloaded.", "voting_rationale": "2-1 for synthesis.", "top_finding": "God node X is overloaded."},
    ]
```

**Assertion pattern** (lines 22–62):
```python
def test_report_contains_header():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "# Graph Report" in report
```
Copy this shape for `render_analysis()` tests:
- `test_analysis_contains_header()` — assert `"# Graph Analysis"` in result
- `test_analysis_contains_each_lens()` — assert `"## Security"` and `"## Architecture"` in result
- `test_analysis_clean_lens_shows_verdict()` — assert `"Clean"` in result for clean lens
- `test_analysis_clean_lens_shows_rationale()` — assert `"3-0 unanimous"` in result (voting rationale always shown, D-82)
- `test_analysis_all_lenses_always_appear()` — even clean lenses appear in output (D-83)
- `test_analysis_returns_str()` — assert isinstance(result, str)

---

## Shared Patterns

### `from __future__ import annotations` — first line of every module
**Source:** `analyze.py` line 2, `report.py` line 2
**Apply to:** `analyze.py` (already present), `report.py` (already present)
No new modules created — additions go into existing files. Both already have this import.

### lines-list builder → `"\n".join(lines)`
**Source:** `report.py::generate()` lines 39–175
**Apply to:** `render_analysis_context()` in `analyze.py`, `render_analysis()` in `report.py`
```python
lines = ["# Header", ""]
lines += ["## Section", ""]
lines.append(f"- item")
return "\n".join(lines)
```
This is the universal markdown rendering pattern in this codebase. Do not use f-string concatenation or templating.

### `.get()` defensive attribute access
**Source:** `analyze.py::god_nodes()` line 53, `report.py::generate()` lines 80–84
**Apply to:** All node/edge dict accesses
```python
G.nodes[node_id].get("label", node_id)   # node labels
d.get("confidence", "EXTRACTED")          # edge confidence
s.get("note", "")                         # optional fields
```
Never use direct dict key access on graph node/edge attributes — always `.get(key, default)`.

### `$(cat graphify-out/.graphify_python) -c "..."` bash block
**Source:** `skill.md` lines 401, 820, 1202
**Apply to:** All new skill.md Python execution blocks
```bash
$(cat graphify-out/.graphify_python) -c "
import json
from pathlib import Path
# ... code ...
Path('graphify-out/GRAPH_ANALYSIS.md').write_text(result)
"
```
Never use `python3` directly in skill.md bash blocks — always via the `.graphify_python` indirection.

### Output write pattern
**Source:** `skill.md` lines 424, 441, 485
**Apply to:** Writing `GRAPH_ANALYSIS.md`
```python
Path('graphify-out/GRAPH_ANALYSIS.md').write_text(analysis_md)
```
One `write_text()` call at the end of the assembly block. No intermediate file handles.

### Error guard pattern
**Source:** `skill.md` lines 442–445
**Apply to:** Tournament section preamble
```python
if not Path('graphify-out/.graphify_analysis.json').exists():
    print('ERROR: .graphify_analysis.json not found. Run /graphify first to build the graph.')
    raise SystemExit(1)
```

### Test fixture reuse — `make_graph()` and `FIXTURES`
**Source:** `tests/test_analyze.py` lines 9–13, `tests/test_report.py` lines 8–20
**Apply to:** New tests in both test files
Both test files already load from `tests/fixtures/extraction.json`. New tests append to existing files and reuse `make_graph()` / `make_inputs()` without creating new fixture files.

---

## No Analog Found

None. All five files have exact analogs within the same file or test file.

---

## Critical Correction from Research

RESEARCH.md states `knowledge_gaps()` is a function in `analyze.py`. **This is wrong.** Gap detection logic lives inline in `report.py::generate()` (lines 134–160), not in a named function in `analyze.py`. The `graphify/analyze.py` function list (confirmed by grep) is:
```
_node_community_map, _is_file_node, god_nodes, surprising_connections, _is_concept_node,
_file_category, _top_level_dir, _surprise_score, _cross_file_surprises,
_cross_community_surprises, suggest_questions, graph_diff
```
No `knowledge_gaps()`. This does not affect Phase 9 scope — the new `render_analysis_context()` function is a serializer, not a gap detector.

---

## Metadata

**Analog search scope:** `graphify/analyze.py`, `graphify/report.py`, `graphify/skill.md`, `tests/test_analyze.py`, `tests/test_report.py`
**Files scanned:** 5 source files read in full
**Pattern extraction date:** 2026-04-14
