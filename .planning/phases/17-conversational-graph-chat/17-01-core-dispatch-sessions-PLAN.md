---
phase: 17
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/serve.py
  - graphify/mcp_tool_registry.py
  - tests/test_serve.py
autonomous: true
requirements: [CHAT-01, CHAT-02, CHAT-08]
requirements_addressed: [CHAT-01, CHAT-02, CHAT-08]
threat_model:
  - id: T-17-03
    category: Spoofing / DoS
    component: "_CHAT_SESSIONS dict + _tool_chat wrapper"
    disposition: mitigate
    mitigation: "len(session_id) <= 128 cap before write; session_id=None skips write path (Pitfall 5); no stderr logging of session_id values"
must_haves:
  truths:
    - "`chat` tool is registered in MCP tool registry and dispatchable"
    - "Stage 1 dispatches the correct primitive per intent (explore→_bfs, connect→_bidirectional_bfs, summarize→_get_community via communities dict)"
    - "Session history is scoped per session_id with 10-turn cap and 30-min idle TTL"
    - "session_id=None never writes to shared state"
    - "Every return path from _run_chat_core emits the D-02 sentinel envelope"
  artifacts:
    - path: graphify/serve.py
      provides: "_run_chat_core, _tool_chat, _CHAT_SESSIONS, _chat_evict_stale, _augment_terms_from_history, _classify_intent, _extract_entity_terms"
      contains: "def _run_chat_core("
    - path: graphify/mcp_tool_registry.py
      provides: "chat Tool entry in tool list"
      contains: 'name="chat"'
    - path: tests/test_serve.py
      provides: "test_chat_tool_registered, test_chat_envelope_ok, test_chat_intent_connect_calls_bi_bfs, test_chat_session_isolation, test_chat_ttl_eviction"
  key_links:
    - from: "graphify/serve.py::_tool_chat"
      to: "graphify/serve.py::_run_chat_core"
      via: "direct call after _maybe_reload_dedup() / graph existence check"
      pattern: "_run_chat_core\\(G, communities, _alias_map, arguments\\)"
    - from: "graphify/serve.py dispatch table"
      to: "_tool_chat"
      via: "\"chat\": _tool_chat entry"
      pattern: '"chat":\\s*_tool_chat'
---

<objective>
Ship the Stage-1 shell of the `chat` MCP tool: deterministic intent classifier, entity-term extractor (D-03 tokenize + stopwords), primitive dispatcher (D-02 three intents), session history (D-06 deque-per-session + lazy TTL), follow-up seed augmentation (D-07), and a D-02 envelope skeleton. Narrative composition and citation validation are stubbed in this plan (plain `text_body = ""` or minimal templated line); Plan 17-02 wires the real composer + validator + cap.

**Purpose:** Lock the structural pieces — tool registration, core signature, sessions, dispatch — so Plan 17-02 can focus on composition/validation without touching the shell.

**Output:** `chat` is reachable over MCP, returns a valid D-02 envelope, runs the right primitive for each intent, respects session isolation. Five new pytest cases pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/17-conversational-graph-chat/17-CONTEXT.md
@.planning/phases/17-conversational-graph-chat/17-RESEARCH.md
@.planning/phases/17-conversational-graph-chat/17-VALIDATION.md

<!-- Prior-phase envelope precedents carried forward -->
@.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md
@.planning/milestones/v1.3-phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md

<!-- Reference implementations to mirror verbatim -->
@graphify/serve.py
@graphify/mcp_tool_registry.py
@tests/test_serve.py

<interfaces>
<!-- Verbatim from serve.py@HEAD (RESEARCH.md §1) -->
<!-- Stage 1 entity resolver -->
def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    # Returns sorted([(score, node_id), ...], reverse=True). Nodes with score 0 omitted.

<!-- Explore intent traversal -->
def _bfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:

<!-- Connect intent traversal (max_visited is REQUIRED, no default) -->
def _bidirectional_bfs(
    G: nx.Graph,
    start_nodes: list[str],
    target_nodes: list[str],
    depth: int,
    max_visited: int,
) -> tuple[set[str], list[tuple], str]:
    # status ∈ {"ok", "frontiers_disjoint", "budget_exhausted"}

<!-- Reserved for whitelist (no intent dispatches it in v1 per CHAT-02) -->
def _dfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:

<!-- Sentinel + envelope idiom (serve.py:901) -->
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"

<!-- Mandatory core signature to match _run_connect_topics shape (serve.py:1212) -->
def _run_chat_core(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str] | None,
    arguments: dict,  # {"query": str, "session_id": str | None}
) -> str:
    ...

<!-- Envelope emission (MUST be used on every return path) -->
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _run_chat_core shell + intent classifier + entity terms + sessions + _tool_chat wrapper + registry entry</name>
  <files>graphify/serve.py, graphify/mcp_tool_registry.py</files>
  <read_first>
    - graphify/serve.py (read lines 40-60 for import block, 525-700 for primitives, 900-910 for sentinel, 1212-1300 for _run_connect_topics reference shape, 1804-1915 for _run_get_focus_context_core reference, 2050-2130 for _maybe_reload_dedup + _merge_manifest_meta + wrapper pattern, 2311-2360 for _tool_* wrappers, 2484-2524 for dispatch table)
    - graphify/mcp_tool_registry.py (read in full — short file; add new Tool entry alongside connect_topics/get_focus_context)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md §§ 1, 2, 3, 9 (signatures, envelope, sessions, registration)
    - .planning/phases/17-conversational-graph-chat/17-CONTEXT.md D-01, D-02, D-03, D-06, D-07
  </read_first>
  <behavior>
    - Test 1 (test_chat_tool_registered): `from graphify.mcp_tool_registry import TOOLS` (or equivalent) — list contains a Tool with `name == "chat"` and inputSchema requires `query`.
    - Test 2 (test_chat_envelope_ok): `_run_chat_core(G, communities, {}, {"query": "what is extract?"})` returns a string containing `QUERY_GRAPH_META_SENTINEL`; splitting on sentinel yields two parts; `json.loads(part2)` parses; `meta["intent"] in ("explore","connect","summarize")`; `meta["status"] in ("ok","no_results")`; `meta["session_id"]` is None.
    - Test 3 (test_chat_intent_connect_calls_bi_bfs): query `"how does extract connect to build"` — monkeypatch `_bidirectional_bfs` to a spy; assert spy called exactly once; `meta["intent"] == "connect"`.
    - Test 4 (test_chat_session_isolation): Two calls with distinct `session_id="s1"` then `"s2"`; `len(_CHAT_SESSIONS["s1"]) == 1`, `len(_CHAT_SESSIONS["s2"]) == 1`; a third call with `session_id=None` does NOT create an entry under any key.
    - Test 5 (test_chat_ttl_eviction): Seed `_CHAT_SESSIONS["old"]` with a turn whose `ts = time.time() - 2000` (>1800s); next `_run_chat_core` call with any session_id purges `"old"`; assert `"old" not in _CHAT_SESSIONS` after call.
  </behavior>
  <action>
Add to `graphify/serve.py`, in this order:

**1. Imports (if missing — verify first with grep before adding):**
```python
from collections import deque
import time
import uuid
```
Place after existing `import re` / stdlib block. Do NOT re-add if already present.

**2. Module-level state (place near the sentinel at serve.py:901 vicinity):**
```python
# Phase 17 D-06: conversational session store. Process-lifetime; evicted lazily.
_CHAT_SESSIONS: dict[str, deque] = {}
_CHAT_SESSION_TTL_SECONDS = 1800  # 30 min
_CHAT_SESSION_MAXLEN = 10
_CHAT_SESSION_ID_MAX_LEN = 128  # T-17-03 cap

# D-03 stopwords (intent verbs + common English function words; ASCII-only)
_CHAT_STOPWORDS: frozenset[str] = frozenset({
    "what", "how", "is", "are", "was", "were", "be", "been", "being",
    "the", "a", "an", "this", "that", "these", "those", "it",
    "between", "connect", "connects", "relate", "relates", "show", "explain",
    "tell", "me", "about", "of", "in", "for", "with", "and", "or", "but",
    "to", "from", "across", "among", "on", "at", "by", "as", "do", "does",
    "did", "can", "could", "would", "should", "which", "who", "whom", "why",
    "when", "where", "there", "here", "summarize", "overview",
})

# D-02 intent trigger patterns
_CONNECT_VERBS_RE = re.compile(r"\b(connect|connects|relate|relates|between|path|from\s+.+\s+to)\b", re.IGNORECASE)
_SUMMARIZE_TRIGGERS_RE = re.compile(r"\b(what'?s in|overview of|summarize)\b", re.IGNORECASE)
_EXPLORE_COMMUNITY_HINTS_RE = re.compile(r"\b(about|overview)\b", re.IGNORECASE)

# D-07 follow-up detectors (anchored at START of query only — Pitfall 4)
_FOLLOWUP_RE = re.compile(r"^(and|but|what about|tell me more|more|why|how come)\b", re.IGNORECASE)
_PRONOUN_RE = re.compile(r"^(it|that)\b", re.IGNORECASE)
```

**3. Helper functions (add immediately after the state block):**
```python
def _chat_evict_stale(now: float) -> None:
    """Lazy TTL eviction. Drop sessions whose newest turn is older than TTL."""
    stale = [sid for sid, turns in _CHAT_SESSIONS.items()
             if not turns or (now - turns[-1]["ts"] > _CHAT_SESSION_TTL_SECONDS)]
    for sid in stale:
        del _CHAT_SESSIONS[sid]


def _extract_entity_terms(query: str) -> list[str]:
    """D-03: lowercase tokenize + stopword filter. ASCII-only; drop tokens <=2 chars or in stopword list."""
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    return [t for t in tokens if len(t) > 2 and t not in _CHAT_STOPWORDS]


def _classify_intent(query: str, terms: list[str]) -> str:
    """D-02: return one of 'explore', 'connect', 'summarize'. Order-sensitive."""
    if _SUMMARIZE_TRIGGERS_RE.search(query):
        return "summarize"
    if _CONNECT_VERBS_RE.search(query):
        return "connect"
    return "explore"


def _augment_terms_from_history(session_id: str | None, query: str, terms: list[str]) -> list[str]:
    """D-07: if query is a follow-up, prepend prior turn's cited node_ids to terms."""
    if session_id is None or session_id not in _CHAT_SESSIONS:
        return terms
    q = query.strip()
    if not (_FOLLOWUP_RE.match(q) or _PRONOUN_RE.match(q)):
        return terms
    prior = _CHAT_SESSIONS[session_id]
    if not prior:
        return terms
    last_turn = prior[-1]
    prior_node_ids = [c["node_id"] for c in last_turn.get("citations", [])]
    return prior_node_ids + terms
```

**4. Core dispatcher (`_run_chat_core`) — place adjacent to `_run_connect_topics` (near serve.py:1212) OR near `_run_get_focus_context_core` (serve.py:1804). Match 4-arg signature:**
```python
def _run_chat_core(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str] | None,
    arguments: dict,
) -> str:
    """Phase 17: deterministic chat tool. Zero LLM. D-02 envelope."""
    # --- Input validation (T-17-03 + silent-ignore) ---
    query_raw = arguments.get("query", "")
    session_id = arguments.get("session_id")
    if not isinstance(query_raw, str) or not query_raw.strip():
        meta = {"status": "no_results", "citations": [], "findings": [],
                "suggestions": [], "session_id": None, "intent": None,
                "resolved_from_alias": {}}
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    if session_id is not None:
        if not isinstance(session_id, str) or len(session_id) > _CHAT_SESSION_ID_MAX_LEN:
            session_id = None  # silent-ignore malformed (Pitfall 5 + T-17-03)

    # --- Lazy TTL eviction ---
    now = time.time()
    _chat_evict_stale(now)

    # --- Stage 1: entity terms + intent + history augmentation ---
    terms = _extract_entity_terms(query_raw)
    terms = _augment_terms_from_history(session_id, query_raw, terms)
    intent = _classify_intent(query_raw, terms)

    # --- Stage 1: primitive dispatch (D-02 three intents) ---
    # Placeholder body — Plan 17-02 replaces narrative composition + citation validation + cap.
    scored = _score_nodes(G, terms) if terms else []
    seed_ids = [nid for _, nid in scored[:5]]
    visited: set[str] = set(seed_ids)
    edges: list[tuple] = []
    status = "ok" if seed_ids else "no_results"

    if intent == "connect" and len(seed_ids) >= 2:
        # Split seeds into two groups by score bucket
        mid = len(seed_ids) // 2 or 1
        a_ids, b_ids = seed_ids[:mid], seed_ids[mid:]
        visited, edges, bi_status = _bidirectional_bfs(
            G, a_ids, b_ids, depth=3, max_visited=1000,
        )
        if bi_status != "ok":
            status = "no_results"
    elif intent == "summarize":
        # Skip BFS; use community membership only
        community_ids = {G.nodes[nid].get("community") for nid in seed_ids if nid in G.nodes}
        community_ids.discard(None)
        for cid in community_ids:
            members = communities.get(int(cid), [])
            visited.update(members)
    else:  # explore (default/fallback)
        if seed_ids:
            visited, edges = _bfs(G, seed_ids, depth=2)
            if _EXPLORE_COMMUNITY_HINTS_RE.search(query_raw):
                community_ids = {G.nodes[nid].get("community") for nid in seed_ids if nid in G.nodes}
                community_ids.discard(None)
                for cid in community_ids:
                    members = communities.get(int(cid), [])
                    visited.update(members)

    # --- Stage 2 shell (Plan 17-02 replaces with real composer + validator + cap) ---
    citations = [
        {"node_id": nid,
         "label": G.nodes[nid].get("label", nid),
         "source_file": G.nodes[nid].get("source_file", "")}
        for nid in list(visited)[:20]
    ]
    text_body = ""  # Plan 17-02 populates
    meta = {
        "status": status,
        "intent": intent,
        "citations": citations,
        "findings": [],
        "suggestions": [],
        "session_id": session_id,
        "resolved_from_alias": {},  # Plan 17-03 threads aliases
    }

    # --- D-06 session write (skip if session_id is None — Pitfall 5) ---
    if session_id is not None and status == "ok":
        turn = {
            "query": query_raw,
            "citations": citations,
            "narrative_hash": "",  # Plan 17-02 fills after composition
            "ts": now,
        }
        _CHAT_SESSIONS.setdefault(session_id, deque(maxlen=_CHAT_SESSION_MAXLEN)).append(turn)

    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

**5. MCP wrapper `_tool_chat` — add near other `_tool_*` wrappers (serve.py:2311 vicinity). Mirror `_tool_connect_topics` exactly:**
```python
def _tool_chat(arguments: dict) -> str:
    _maybe_reload_dedup()
    if not Path(graph_path).exists():
        meta = {"status": "no_graph", "citations": [], "findings": [],
                "suggestions": [], "session_id": None, "intent": None,
                "resolved_from_alias": {}}
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    return _run_chat_core(G, communities, _alias_map, arguments)
```

**6. Dispatch table — add `"chat": _tool_chat,` to the tool dispatch dict at serve.py:2484 (grep for existing `"connect_topics": _tool_connect_topics,` to find it).**

**7. `graphify/mcp_tool_registry.py` — add the Tool entry alongside `connect_topics` (line 214) / `get_focus_context` (line 231) — use the verbatim block from RESEARCH.md §9:**
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

**DO NOT** set `manifest_content_hash` anywhere in `_run_chat_core` — `_merge_manifest_meta` wrapper at serve.py:2104 injects it automatically (RESEARCH.md §2 / §12).
  </action>
  <verify>
    <automated>pytest tests/test_serve.py -q -k chat</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def _run_chat_core(" graphify/serve.py` returns exactly one hit with signature `(G, communities, alias_map, arguments)` (4 args matching `_run_connect_topics`).
    - `grep -n "_CHAT_SESSIONS" graphify/serve.py` returns at least 4 hits (definition, eviction, session write, test import target).
    - `grep -n "QUERY_GRAPH_META_SENTINEL" graphify/serve.py | grep -E "chat|_run_chat_core"` shows sentinel used in every return path from `_run_chat_core` (minimum 2 — empty-query return + happy-path return).
    - `grep -n '"chat":' graphify/serve.py` returns one hit in the dispatch table.
    - `grep -n 'name="chat"' graphify/mcp_tool_registry.py` returns exactly one hit.
    - `grep -c 'resolved_from_alias' graphify/serve.py` is strictly greater than the pre-plan baseline (new key usage in `_run_chat_core` return paths).
    - `grep -n "manifest_content_hash" graphify/serve.py` shows NO new assignment inside `_run_chat_core` (still only the existing `_merge_manifest_meta` wrapper hit).
    - `grep -n "\\balias_redirects\\b" graphify/serve.py` returns zero hits inside `_run_chat_core` (per CONTEXT.md clarification — field name is `resolved_from_alias`).
    - `python -c "from graphify.serve import _run_chat_core, _CHAT_SESSIONS, _classify_intent, _extract_entity_terms, _chat_evict_stale"` exits 0.
    - No new top-level imports of `anthropic`, `openai`, or any LLM client: `grep -E "^(import|from)\\s+(anthropic|openai)" graphify/serve.py` returns zero lines.
  </acceptance_criteria>
  <done>
    All five behaviors in `<behavior>` pass. Stage-1 dispatch selects the correct primitive for each intent. Sessions scoped, TTL-evicted. Envelope always emits sentinel. Narrative body is empty placeholder (Plan 17-02 fills).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add test_chat_* cases to tests/test_serve.py (extend — do not create new file)</name>
  <files>tests/test_serve.py</files>
  <read_first>
    - tests/test_serve.py (read lines 1-60 for imports + `_make_graph()` fixture at line 50; read lines 1140, 2226, 2302-2360 for existing envelope-assertion patterns and `_communities_from_graph` usage)
    - .planning/phases/17-conversational-graph-chat/17-VALIDATION.md (per-REQ test map)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md §§ 11 (test harness patterns — verbatim boilerplate)
    - .planning/phases/17-conversational-graph-chat/17-CONTEXT.md D-06 (sessions), D-07 (follow-ups)
  </read_first>
  <behavior>
    - `test_chat_tool_registered`: imports the registry list and asserts one Tool has `name=="chat"` with `query` in required inputSchema props.
    - `test_chat_envelope_ok`: `_run_chat_core(_make_graph(), _communities_from_graph(_make_graph()), {}, {"query": "what is extract?"})` — envelope parses; `meta["intent"] in ("explore","connect","summarize")`; `meta["session_id"] is None`; `"resolved_from_alias" in meta`.
    - `test_chat_intent_connect_calls_bi_bfs`: monkeypatch `graphify.serve._bidirectional_bfs` with `MagicMock(return_value=(set(), [], "ok"))`; invoke with query `"how does extract connect to build"`; assert `mock.called is True`; assert `meta["intent"] == "connect"`.
    - `test_chat_session_isolation`: call twice with `session_id="s1"` and `session_id="s2"`; assert `len(_CHAT_SESSIONS["s1"]) >= 1`, `len(_CHAT_SESSIONS["s2"]) >= 1`; call once with `session_id=None` and assert `None not in _CHAT_SESSIONS` (no key `None` and no key created). All after `_CHAT_SESSIONS.clear()` at test start.
    - `test_chat_ttl_eviction`: seed `_CHAT_SESSIONS["old"] = deque([{"query":"x","citations":[],"narrative_hash":"","ts":time.time()-2000}], maxlen=10)`; invoke core once with any valid query + `session_id="fresh"`; assert `"old" not in _CHAT_SESSIONS`.
  </behavior>
  <action>
**Extend `tests/test_serve.py`** — do NOT create a new test file (CLAUDE.md convention: one test file per module).

**1. Extend import block (near line 42):**
```python
from graphify.serve import (
    # ... existing imports preserved ...
    _run_chat_core,
    _CHAT_SESSIONS,
    _classify_intent,
    _extract_entity_terms,
    QUERY_GRAPH_META_SENTINEL,
)
from collections import deque
import time
from unittest.mock import MagicMock
import pytest
```

**2. Add a session-reset fixture (class-scoped — not autouse at module level; only chat tests use it):**
```python
@pytest.fixture
def _reset_chat_sessions():
    _CHAT_SESSIONS.clear()
    yield
    _CHAT_SESSIONS.clear()
```

**3. Add the five test cases.** Reuse `_make_graph()` at line 50 — do NOT replace it. Reuse `_communities_from_graph` (already imported). Exact test bodies:

```python
def test_chat_tool_registered():
    """CHAT-01 registry surface."""
    from graphify import mcp_tool_registry
    # Find the exported tool list — registry exposes a module-level TOOLS/list (grep to confirm name).
    tools = getattr(mcp_tool_registry, "TOOLS", None) or getattr(mcp_tool_registry, "tools", None)
    assert tools is not None, "mcp_tool_registry must expose a tool list"
    chat_tool = next((t for t in tools if getattr(t, "name", None) == "chat"), None)
    assert chat_tool is not None, "chat tool missing from registry"
    schema = chat_tool.inputSchema
    assert "query" in schema["required"]
    assert "query" in schema["properties"]
    assert "session_id" in schema["properties"]


def test_chat_envelope_ok(_reset_chat_sessions):
    """CHAT-01 / CHAT-09 D-02 envelope shape."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    assert QUERY_GRAPH_META_SENTINEL in response
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["intent"] in ("explore", "connect", "summarize")
    assert meta["session_id"] is None
    assert "resolved_from_alias" in meta
    assert "citations" in meta and isinstance(meta["citations"], list)


def test_chat_intent_connect_calls_bi_bfs(_reset_chat_sessions, monkeypatch):
    """CHAT-02 connect intent dispatches _bidirectional_bfs."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    spy = MagicMock(return_value=(set(G.nodes), [], "ok"))
    monkeypatch.setattr("graphify.serve._bidirectional_bfs", spy)
    response = _run_chat_core(
        G, communities, {}, {"query": "how does extract connect to build"}
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["intent"] == "connect"
    # Spy called if at least 2 seeds were scored; else connect falls through.
    # The fixture graph should have 2+ scored seeds for the terms "extract","build".
    assert spy.called, "connect intent must invoke _bidirectional_bfs when 2+ seeds resolve"


def test_chat_session_isolation(_reset_chat_sessions):
    """CHAT-08 session_id scoping + session_id=None no-write."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "s1"})
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "s2"})
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": None})
    assert "s1" in _CHAT_SESSIONS
    assert "s2" in _CHAT_SESSIONS
    assert None not in _CHAT_SESSIONS
    assert len(_CHAT_SESSIONS["s1"]) >= 1
    assert len(_CHAT_SESSIONS["s2"]) >= 1


def test_chat_ttl_eviction(_reset_chat_sessions):
    """CHAT-08 30-min idle TTL evicts stale sessions lazily."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    # Seed a stale session directly.
    _CHAT_SESSIONS["old"] = deque(
        [{"query": "x", "citations": [], "narrative_hash": "", "ts": time.time() - 2000}],
        maxlen=10,
    )
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "fresh"})
    assert "old" not in _CHAT_SESSIONS, "stale session should have been evicted"
```

**Guard against registry import mismatch:** If `mcp_tool_registry` exports a different symbol name (not `TOOLS` or `tools`), `grep -n "^TOOLS\|^tools" graphify/mcp_tool_registry.py` — update the fixture's `getattr` chain accordingly. Do NOT change the registry module itself to satisfy the test.
  </action>
  <verify>
    <automated>pytest tests/test_serve.py -q -k "chat_tool_registered or chat_envelope_ok or chat_intent_connect_calls_bi_bfs or chat_session_isolation or chat_ttl_eviction"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_chat_" tests/test_serve.py` returns at least 5.
    - `pytest tests/test_serve.py::test_chat_tool_registered -x` exits 0.
    - `pytest tests/test_serve.py::test_chat_envelope_ok -x` exits 0.
    - `pytest tests/test_serve.py::test_chat_intent_connect_calls_bi_bfs -x` exits 0.
    - `pytest tests/test_serve.py::test_chat_session_isolation -x` exits 0.
    - `pytest tests/test_serve.py::test_chat_ttl_eviction -x` exits 0.
    - `pytest tests/test_serve.py -q` passes full module (no regressions against existing tests).
    - `grep -c "^def test_" tests/test_serve.py` > baseline pre-plan (new tests added, none removed).
    - No new test file created: `ls tests/test_chat*.py 2>&1 | grep -c "No such"` returns 1 (or equivalent — confirm no `tests/test_chat.py` exists).
  </acceptance_criteria>
  <done>
    Five `test_chat_*` cases exist in `tests/test_serve.py`, all pass, session-reset fixture is scoped per-test (not autouse module-wide), full `tests/test_serve.py` suite green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP caller → `_tool_chat` | `query` and `session_id` are untrusted strings |
| `_tool_chat` → `_run_chat_core` | arguments dict passed through; both values treated as untrusted |
| `_CHAT_SESSIONS` dict | process-local state; session_id is the only scoping key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-17-03 | Spoofing / DoS | `_CHAT_SESSIONS` dict + `_tool_chat` | mitigate | Cap `len(session_id) <= 128` via `_CHAT_SESSION_ID_MAX_LEN`; coerce over-cap or non-str to `None` (silent-ignore); do NOT `print(..., file=sys.stderr)` session_ids anywhere (enforced by grep in acceptance) |
</threat_model>

<verification>
- `pytest tests/test_serve.py -q` passes — no regressions to existing tests
- `pytest tests/test_serve.py -q -k chat` passes all 5 new cases
- `grep -n "def _run_chat_core(" graphify/serve.py` exactly one hit
- `grep -n '"chat":' graphify/serve.py` exactly one hit (dispatch table)
- `grep -n 'name="chat"' graphify/mcp_tool_registry.py` exactly one hit
- `grep -n "alias_redirects" graphify/serve.py` zero hits (per CONTEXT.md clarification — use `resolved_from_alias`)
</verification>

<success_criteria>
- `chat` is a registered MCP tool discoverable at server startup
- `_run_chat_core` dispatches the correct primitive per intent (explore→_bfs, connect→_bidirectional_bfs, summarize→communities dict); `_dfs` remains in allow-list, no v1 dispatch
- Every return path emits the D-02 sentinel envelope
- Session history is scoped per `session_id`; `session_id=None` never writes to shared state; 30-min TTL evicted on access
- All 5 test_chat_* cases pass; full `tests/test_serve.py` suite green
- No LLM-client imports introduced to `serve.py`
</success_criteria>

<output>
After completion, create `.planning/phases/17-conversational-graph-chat/17-01-SUMMARY.md`.
</output>
