# Phase 16: Graph Argumentation Mode — Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 7 (new/modified)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `graphify/argue.py` | substrate / utility | request-response (pure transform) | `graphify/enrich.py` (dataclass + pure-function pattern) | role-match |
| `graphify/serve.py` (extend) | MCP tool dispatch | request-response | `graphify/serve.py` `_run_chat_core` + `_tool_chat` (same file) | exact |
| `graphify/mcp_tool_registry.py` (extend) | manifest / config | config | `graphify/mcp_tool_registry.py` `chat` Tool entry (same file) | exact |
| `graphify/capability_tool_meta.yaml` (extend) | manifest / config | config | existing `entity_trace` entry (same file, `composable_from: []`) | exact |
| `graphify/commands/argue.md` | command file | request-response | `graphify/commands/ask.md` | exact |
| `tests/test_argue.py` | test | CRUD (unit assertions) | `tests/test_serve.py` `test_chat_*` section | role-match |
| `tests/test_serve.py` (extend) | test | CRUD (unit assertions) | same file `test_chat_*` block (lines 2792–3034) | exact |

---

## Pattern Assignments

---

### `graphify/argue.py` (substrate, request-response / pure transform)

**Analog:** `graphify/enrich.py`

**Imports pattern** (`enrich.py` lines 1–19):
```python
from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graphify.security import validate_graph_path
from graphify.snapshot import list_snapshots
```
For `argue.py` the relevant subset is:
```python
from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx
```

**Dataclass pattern** (`enrich.py` lines 42–51):
```python
@dataclass
class EnrichmentResult:
    """Aggregated outcome of one enrichment run (all passes)."""

    snapshot_id: str
    passes_run: list[str] = field(default_factory=list)
    passes_skipped: list[str] = field(default_factory=list)
    passes_failed: list[str] = field(default_factory=list)
    tokens_used: int = 0
    llm_calls: int = 0
    dry_run: bool = False
    aborted: bool = False  # True if SIGTERM received mid-run
```
Apply the same `@dataclass` + `field(default_factory=list)` convention for:
- `NodeCitation(node_id: str, label: str, source_file: str)`
- `PerspectiveSeed(lens: str)`
- `ArgumentPackage(subgraph: nx.Graph, perspectives: list[PerspectiveSeed] = field(default_factory=list), evidence: list[NodeCitation] = field(default_factory=list))`

**Core function signature pattern** (`enrich.py` — `run_enrichment` style; `serve.py` line 1197 for zero-LLM pure dispatch):
```python
def populate(
    G: nx.Graph,
    topic: str,
    *,
    scope: str = "topic",
    budget: int = 2000,
    node_ids: list[str] | None = None,
    community_id: int | None = None,
) -> ArgumentPackage:
    ...
```

**Scope dispatch pattern** — mirrors `_run_chat_core` at `serve.py` lines 1252–1258:
```python
terms = _extract_entity_terms(query_raw)
...
scored = _score_nodes(G, terms) if terms else []
seed_ids = [_resolve_alias(nid) for _, nid in scored[:5]]
```
For `argue.py` `populate(scope="topic")`:
```python
terms = _extract_entity_terms(topic)
scored = _score_nodes(G, terms)
seed_ids = [nid for _, nid in scored[:5]]
```

**Budget clamp pattern** — used identically across ≥6 tool cores in `serve.py`:
```python
budget = max(50, min(budget, 100000))
```

**validate_turn pure function** — zero LLM, returns error list (mirrors `validate.py::validate_extraction` which returns `list[str]`):
```python
def validate_turn(turn: dict, G: nx.Graph) -> list[str]:
    """Return list of node_ids in turn['cites'] that are not in G.nodes.

    Empty return = valid turn. Zero LLM calls.
    """
    return [nid for nid in turn.get("cites", []) if nid not in G.nodes]
```

**Error handling pattern** — silent fallback on bad input (mirrors all MCP cores):
```python
if not isinstance(topic, str) or not topic.strip():
    return ArgumentPackage(subgraph=nx.Graph(), perspectives=[], evidence=[])
```

---

### `graphify/serve.py` — `_run_argue_topic_core` + `_tool_argue_topic` (extend)

**Analog:** `graphify/serve.py` `_run_chat_core` (lines 1197–1354) and `_tool_chat` (lines 2764–2782)

**Core dispatch function signature** (`serve.py` lines 1197–1202):
```python
def _run_chat_core(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str] | None,
    arguments: dict,
) -> str:
    """Phase 17: deterministic chat tool. Zero LLM. D-02 envelope."""
```
Copy this exact signature for `_run_argue_topic_core`, replacing docstring.

**Empty-input early return** (`serve.py` lines 1210–1224):
```python
query_raw = arguments.get("query", "")
...
if not isinstance(query_raw, str) or not query_raw.strip():
    meta = {
        "status": "no_results",
        "citations": [],
        "findings": [],
        "suggestions": [],
        "session_id": None,
        "intent": None,
        "resolved_from_alias": {},
    }
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```
For `argue_topic` the empty-input meta shape is:
```python
meta = {
    "status": "no_results",
    "citations": [],
    "verdict": None,
    "rounds_run": 0,
    "argument_package": {},
    "resolved_from_alias": {},
    "output_path": "graphify-out/GRAPH_ARGUMENT.md",
}
return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**`_resolve_alias` closure** (`serve.py` lines 1234–1250) — copy verbatim:
```python
_resolved_aliases: dict[str, list[str]] = {}
_effective_alias_map: dict[str, str] = alias_map or {}

def _resolve_alias(node_id: str) -> str:
    seen: set[str] = set()
    current = node_id
    while current in _effective_alias_map and current not in seen:
        seen.add(current)
        nxt = _effective_alias_map[current]
        if nxt == current:
            break
        current = nxt
    if current != node_id:
        aliases = _resolved_aliases.setdefault(current, [])
        if node_id not in aliases:
            aliases.append(node_id)
    return current
```

**D-02 envelope return** (`serve.py` line 1354):
```python
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```
`meta` for `argue_topic` must contain exactly:
`{verdict, rounds_run, argument_package, citations, resolved_from_alias, output_path}`
Key name `resolved_from_alias` — NOT `alias_redirects` (verified at `serve.py:1016, 1091, 1276, 1300`).

**`_tool_argue_topic` handler** — copy pattern from `_tool_chat` (`serve.py` lines 2764–2782):
```python
def _tool_argue_topic(arguments: dict) -> str:
    """Phase 16 ARGUE-01: multi-persona graph debate. Deterministic, zero LLM."""
    _reload_if_stale()
    if not Path(graph_path).exists():
        meta: dict = {
            "status": "no_graph",
            "citations": [],
            "verdict": None,
            "rounds_run": 0,
            "argument_package": {},
            "resolved_from_alias": {},
            "output_path": "graphify-out/GRAPH_ARGUMENT.md",
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    return _run_argue_topic_core(G, communities, _alias_map, arguments)
```

**`_handlers` dict extension** (`serve.py` lines 2957–2979) — add one entry:
```python
_handlers = {
    ...
    "chat": _tool_chat,
    ...
    "argue_topic": _tool_argue_topic,   # NEW Phase 16
}
```
The dict size must equal `len(build_mcp_tools())` — the `RuntimeError` at line 2981 enforces this:
```python
if {t.name for t in _reg_tools} != set(_handlers.keys()):
    raise RuntimeError("MCP tool registry and _handlers keys must match (MANIFEST-05)")
```

---

### `graphify/mcp_tool_registry.py` — `argue_topic` Tool entry (extend)

**Analog:** `chat` Tool entry (`mcp_tool_registry.py` lines 213–229) and `get_focus_context` entry (lines 248–281) for the richer `inputSchema` with optional parameters.

**`chat` tool definition** (`mcp_tool_registry.py` lines 213–229):
```python
types.Tool(
    name="chat",
    description=(
        "Answer a natural-language question about the codebase with a graph-grounded "
        "narrative. Every claim cites a real node (node_id, label, source_file). "
        "Empty results return fuzzy suggestions. Deterministic, zero LLM in serve.py. "
        "Used by the /graphify-ask slash command."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "session_id": {"type": "string"},
        },
        "required": ["query"],
    },
),
```
Apply the same `types.Tool(name=..., description=..., inputSchema={...})` shape for `argue_topic`.
The `inputSchema` must include:
- `"topic"` (required string) — the decision question
- `"scope"` (optional enum `["topic", "subgraph", "community"]`, default `"topic"`)
- `"budget"` (optional integer, default 2000, min 50, max 100000)
- `"node_ids"` (optional array of strings — `scope="subgraph"` only)
- `"community_id"` (optional integer — `scope="community"` only)

**`build_mcp_tools()` return list** (`mcp_tool_registry.py` line 57) — append `argue_topic` Tool to the list returned by this function. The function docstring states: "Return MCP Tool list — must match serve._handlers keys (MANIFEST-05)."

---

### `graphify/capability_tool_meta.yaml` — `argue_topic` entry (extend)

**Analog:** `entity_trace` entry and `newly_formed_clusters` entry in `capability_tool_meta.yaml` (lines 72–91) — both have `composable_from: []`.

**`entity_trace` and `drift_nodes` entry pattern** (`capability_tool_meta.yaml` lines 72–91):
```yaml
entity_trace:
  cost_class: expensive
  deterministic: false
  cacheable_until: graph_mtime
  composable_from: []
drift_nodes:
  cost_class: expensive
  deterministic: false
  cacheable_until: graph_mtime
  composable_from: []
```
Apply the identical shape for `argue_topic`:
```yaml
argue_topic:
  cost_class: expensive
  deterministic: false
  cacheable_until: graph_mtime
  composable_from: []   # HARD CONSTRAINT — recursion guard (ARGUE-07, D-15)
```
`composable_from: []` is MANDATORY — not a default. The regression test in `tests/test_capability.py` must assert `argue_topic.composable_from == []` explicitly.

---

### `graphify/commands/argue.md` (new command file)

**Analog:** `graphify/commands/ask.md` (all 29 lines — exact template)

**Full `ask.md` content** (`graphify/commands/ask.md` lines 1–29):
```markdown
---
name: graphify-ask
description: Ask a natural-language question about the codebase and receive a graph-grounded narrative answer with citations.
argument-hint: <question>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `chat` with:
- `query`: "$ARGUMENTS"
- (omit `session_id` — slash-command is single-shot; ...)

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim: ...

**If `status` is `no_results`:** render the fuzzy suggestions from `meta.suggestions` ...

**If `status` is `ok`:** render `text_body` verbatim ...

If `meta.resolved_from_alias` is non-empty, append a small note: ...

Keep total output under 500 tokens ...
```

For `argue.md` mirror the frontmatter fields exactly:
```markdown
---
name: graphify-argue
description: Run a structurally-enforced multi-perspective graph debate on a decision question.
argument-hint: <decision question>
disable-model-invocation: true
---
```
Constraints (verified from `test_commands.py:test_ask_md_frontmatter`):
- No `target:` field
- `disable-model-invocation: true` required
- Body must reference `argue_topic` MCP tool (not `chat`)
- Body must include `$ARGUMENTS`
- Meta status handling: `no_graph`, `no_results`, `ok`; meta key `resolved_from_alias` (not `alias_redirects`)

---

### `tests/test_argue.py` (new test file)

**Analog:** `tests/test_serve.py` `test_chat_*` block (lines 2792–3034) — pure unit tests for `_run_chat_core`

**Import block pattern** (`tests/test_serve.py` lines 1–60):
```python
from __future__ import annotations

import json
import pytest
...
from graphify.serve import (
    _run_chat_core,
    ...
    QUERY_GRAPH_META_SENTINEL,
)
```
For `test_argue.py`:
```python
from __future__ import annotations

import networkx as nx
import pytest

from graphify.argue import (
    ArgumentPackage,
    PerspectiveSeed,
    NodeCitation,
    populate,
    validate_turn,
    compute_overlap,
)
```

**Graph fixture pattern** — `_make_graph()` helper used throughout `test_serve.py`:
```python
def _make_graph() -> nx.Graph:
    G = nx.DiGraph()
    G.add_node("n_extract", label="extract", source_file="graphify/extract.py", ...)
    G.add_node("n_build", label="build", source_file="graphify/build.py", ...)
    G.add_edge("n_extract", "n_build", relation="imports", confidence="EXTRACTED", ...)
    return G
```
Define a minimal `_make_argue_graph()` for `test_argue.py` with 5–10 nodes.

**Zero-LLM grep test pattern** (`tests/test_serve.py` lines 3019–3034):
```python
def test_serve_makes_zero_llm_calls():
    """CHAT-03 SC4: serve.py source must not import any LLM client."""
    from pathlib import Path
    src = Path("graphify/serve.py").read_text()
    forbidden = (
        "import anthropic",
        "from anthropic",
        "import openai",
        "from openai",
        "from graphify.llm",
        "import graphify.llm",
        "import langchain",
        "from langchain",
    )
    for needle in forbidden:
        assert needle not in src, f"serve.py introduced LLM dependency: {needle!r}"
```
Copy this pattern for `test_argue_zero_llm_calls` — scan `graphify/argue.py` with the same `forbidden` tuple.

**Envelope assertion pattern** (`tests/test_serve.py` lines 2809–2821):
```python
def test_chat_envelope_ok(_reset_chat_sessions):
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    assert QUERY_GRAPH_META_SENTINEL in response
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["intent"] in ("explore", "connect", "summarize")
    assert "resolved_from_alias" in meta
    assert "citations" in meta and isinstance(meta["citations"], list)
```
For `test_argue.py` unit tests, call `populate()` directly (no sentinel — `argue.py` is pure substrate, not returning an envelope). The sentinel envelope tests belong in `tests/test_serve.py::test_argue_topic_*`.

**Key test cases to write** (from RESEARCH.md validation map):
- `test_argument_package_fields` — assert `ArgumentPackage` has `subgraph`, `perspectives`, `evidence`
- `test_four_perspectives` — `len(pkg.perspectives) == 4` and lens names are `["security","architecture","complexity","onboarding"]`
- `test_populate_returns_argument_package` — `populate(G, "extract")` returns `ArgumentPackage` with non-empty subgraph
- `test_populate_scope_subgraph` — `populate(G, "", scope="subgraph", node_ids=["n_extract"])` includes that node
- `test_populate_scope_community` — `populate(G, "", scope="community", community_id=0, communities={0: ["n_extract"]})` includes community members
- `test_validate_turn_valid` — `validate_turn({"cites": ["n_extract"]}, G)` returns `[]`
- `test_validate_turn_fabricated` — `validate_turn({"cites": ["n_fake"]}, G)` returns `["n_fake"]`
- `test_compute_overlap_jaccard` — exact Jaccard with known sets
- `test_compute_overlap_drops_abstentions` — empty sets excluded from computation
- `test_argue_zero_llm_calls` — grep `graphify/argue.py` for forbidden imports
- `test_blind_label_harness_intact` — grep `graphify/skill.md` for shuffle pattern at ~line 1511

---

### `tests/test_serve.py` — `test_argue_*` extensions (extend)

**Analog:** same file, `test_chat_*` block (lines 2792–3034)

**Tool registration pattern** (`test_serve.py` lines 2792–2807):
```python
def test_chat_tool_registered():
    """CHAT-01 registry surface: chat tool discoverable via build_mcp_tools()."""
    from graphify import mcp_tool_registry
    tools = (
        getattr(mcp_tool_registry, "TOOLS", None)
        or getattr(mcp_tool_registry, "tools", None)
        or mcp_tool_registry.build_mcp_tools()
    )
    assert tools is not None
    chat_tool = next((t for t in tools if getattr(t, "name", None) == "chat"), None)
    assert chat_tool is not None, "chat tool missing from registry"
    schema = chat_tool.inputSchema
    assert "query" in schema["required"]
```
Copy for `test_argue_topic_tool_registered` — assert `name == "argue_topic"`, `"topic"` in `required`.

**Alias redirect pattern** (`test_serve.py` lines 2974–3006):
```python
def test_chat_alias_redirect_canonical(_reset_chat_sessions, monkeypatch):
    ...
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["resolved_from_alias"] == {"authentication_service": ["auth"]}
```
Copy for `test_argue_topic_alias_redirect` — assert `meta["resolved_from_alias"]` populated.

**Anti-chat-invocation test** — new pattern (no existing analog; derive from zero-LLM grep pattern):
```python
def test_argue_does_not_invoke_chat():
    """ARGUE-03: _run_argue_topic_core must not call _run_chat_core."""
    from pathlib import Path
    src = Path("graphify/serve.py").read_text()
    # Find the _run_argue_topic_core function body
    start = src.find("def _run_argue_topic_core")
    assert start != -1, "_run_argue_topic_core not yet defined"
    end = src.find("\ndef _", start + 1)
    body = src[start:end] if end != -1 else src[start:]
    assert "_run_chat_core" not in body, "_run_argue_topic_core must not invoke _run_chat_core"
```

**Key test cases to add to `tests/test_serve.py`** (from RESEARCH.md validation map):
- `test_argue_topic_tool_registered` — tool discoverable, `"topic"` required
- `test_argue_topic_envelope_ok` — `_run_argue_topic_core` emits sentinel, has all required meta keys
- `test_argue_topic_alias_redirect` — `resolved_from_alias` populated on redirect
- `test_argue_topic_output_path` — `meta["output_path"] == "graphify-out/GRAPH_ARGUMENT.md"`
- `test_argue_does_not_invoke_chat` — grep-based isolation check

---

### `tests/test_capability.py` and `tests/test_commands.py` — extensions

**`tests/test_capability.py` — add `test_argue_topic_not_composable`**

**Analog:** `test_manifest_tool_names_match_registry` (`test_capability.py` lines 30–37) for manifest access pattern:
```python
def test_manifest_tool_names_match_registry() -> None:
    from graphify.mcp_tool_registry import build_mcp_tools
    m = build_manifest_dict()
    reg = {t.name for t in build_mcp_tools()}
    man = {t["name"] for t in m["CAPABILITY_TOOLS"]}
    assert reg == man
```
New test:
```python
def test_argue_topic_not_composable() -> None:
    """ARGUE-07 D-15: argue_topic.composable_from must be [] — recursion guard."""
    m = build_manifest_dict()
    tool = next((t for t in m["CAPABILITY_TOOLS"] if t["name"] == "argue_topic"), None)
    assert tool is not None, "argue_topic missing from manifest"
    assert tool.get("composable_from") == [], (
        "argue_topic.composable_from must be [] to prevent Phase 17 chat recursion"
    )
```

**`tests/test_commands.py` — add `test_argue_md_frontmatter`**

**Analog:** `test_ask_md_frontmatter` (`test_commands.py` lines 195–209) — exact template:
```python
def test_ask_md_frontmatter():
    """CHAT-06: /graphify-ask command file exists with connect.md-style frontmatter."""
    path = _commands_dir() / "ask.md"
    assert path.exists(), "graphify/commands/ask.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-ask"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    assert "target" not in fm, "ask.md must NOT have a target: field"
    body = path.read_text()
    assert "chat" in body, "ask.md body must invoke the chat MCP tool"
    assert "$ARGUMENTS" in body, "ask.md must pass $ARGUMENTS to query"
```
New test:
```python
def test_argue_md_frontmatter():
    """ARGUE-10: /graphify-argue command file exists with ask.md-style frontmatter."""
    path = _commands_dir() / "argue.md"
    assert path.exists(), "graphify/commands/argue.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-argue"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    assert "target" not in fm, "argue.md must NOT have a target: field"
    body = path.read_text()
    assert "argue_topic" in body, "argue.md body must invoke the argue_topic MCP tool"
    assert "$ARGUMENTS" in body, "argue.md must pass $ARGUMENTS to topic"
```

---

## Shared Patterns

### D-02 Envelope Format
**Source:** `graphify/serve.py` line 903 + line 1354
**Apply to:** `_run_argue_topic_core` in `serve.py`
```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
# ...
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```
The sentinel string is the file-level constant at `serve.py:903`. Every tool core uses the identical `text_body + SENTINEL + json.dumps(meta)` pattern — do not invent a new format.

### `resolved_from_alias` Meta Key
**Source:** `graphify/serve.py` lines 1016, 1091, 1276, 1300 (all uses in existing tool cores)
**Apply to:** `_run_argue_topic_core` meta dict
The key is `resolved_from_alias` — the draft name `alias_redirects` must NOT appear anywhere in Phase 16 code.

### Budget Clamp
**Source:** all MCP tool cores in `serve.py` (≥6 occurrences)
**Apply to:** `argue.py::populate()` and `_run_argue_topic_core`
```python
budget = max(50, min(budget, 100000))
```

### Label Sanitization
**Source:** `graphify/security.py` `sanitize_label` (line 188)
**Apply to:** Every persona claim label and every node label emitted into `GRAPH_ARGUMENT.md`
```python
from graphify.security import sanitize_label
# ...
safe_label = sanitize_label(raw_label)
```

### `from __future__ import annotations`
**Source:** All graphify modules
**Apply to:** `graphify/argue.py` — must be first import per `CLAUDE.md` conventions.

### Silent-ignore on malformed input
**Source:** `serve.py` `_run_chat_core` lines 1210–1224
**Apply to:** `_run_argue_topic_core` — invalid/empty `topic` returns empty envelope, never raises.

---

## No Analog Found

All files in this phase have close analogs. No files are greenfield without a matching pattern.

---

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `graphify/commands/`
**Files scanned:** 7 source files read directly
**Pattern extraction date:** 2026-04-22
