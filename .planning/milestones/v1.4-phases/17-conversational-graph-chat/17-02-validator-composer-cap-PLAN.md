---
phase: 17
plan: 02
type: execute
wave: 2
depends_on: [17-01]
files_modified:
  - graphify/serve.py
  - tests/test_serve.py
autonomous: true
requirements: [CHAT-03, CHAT-04, CHAT-05, CHAT-09]
requirements_addressed: [CHAT-03, CHAT-04, CHAT-05, CHAT-09]
threat_model:
  - id: T-17-01
    category: Spoofing (fabricated citations)
    component: "narrative composer + _validate_citations"
    disposition: mitigate
    mitigation: "Label-token validator (D-04) drops sentences whose token matches a real label not in citation set; re-validate loop bounded at 3 passes (Pitfall 7); empty cleaned → no_context envelope"
  - id: T-17-02
    category: Information Disclosure (query echo leak)
    component: "fuzzy-suggestion template + no_results envelope"
    disposition: mitigate
    mitigation: "`_fuzzy_suggest` returns strings ONLY from graph candidate pool (god-labels + top-community members); no_results text never interpolates `query` or unmatched tokens (Pitfall 1 / Phase 18 D-12)"
  - id: T-17-04
    category: Denial of Service (unbounded payload)
    component: "narrative composer output"
    disposition: mitigate
    mitigation: "500-token hard cap via sentence-boundary truncation (D-09); char/4 heuristic; trailing `…` marker; `meta.findings` remains complete for callers that re-render"
must_haves:
  truths:
    - "Composer produces a templated narrative grounded in traversal results (no LLM)"
    - "Validator strips uncited sentences; empty remainder collapses to no_context envelope"
    - "Empty-match queries receive fuzzy suggestions drawn from the graph — never echo the user's unmatched tokens"
    - "Narrative body is always ≤ 500 tokens (char/4 heuristic), truncated at sentence boundary with `…`"
  artifacts:
    - path: graphify/serve.py
      provides: "_compose_explore_narrative, _compose_connect_narrative, _compose_summarize_narrative, _build_label_token_index, _tokenize_narrative, _split_sentences, _validate_citations, _fuzzy_suggest, _truncate_to_token_cap"
      contains: "def _validate_citations("
  key_links:
    - from: "_run_chat_core"
      to: "_validate_citations"
      via: "post-compose filter before text_body assignment"
      pattern: "_validate_citations\\("
    - from: "_run_chat_core"
      to: "_truncate_to_token_cap"
      via: "final prep of text_body after validator"
      pattern: "_truncate_to_token_cap\\("
    - from: "_run_chat_core (no_results branch)"
      to: "_fuzzy_suggest"
      via: "empty scored-nodes → suggestion list"
      pattern: "_fuzzy_suggest\\("
---

<objective>
Replace Plan 17-01's stub `text_body = ""` with the real Stage-2 narrative composer, citation validator (D-04/D-05), fuzzy-suggestion fallback (CHAT-05 + echo guard), and 500-token sentence-boundary cap (D-09). Zero LLM calls are introduced — composition is pure template slot-fill over traversal results and enrichment overlay attrs.

**Purpose:** Deliver the content side of `chat`. After this plan, `chat` returns a real narrative with verified citations; fabrications are structurally impossible by the validator; empty-match queries return graph-grounded fuzzy suggestions without echoing unmatched tokens.

**Output:** Five new test cases green; `chat` produces human-readable prose with cited labels, or `no_context` envelope with suggestions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/phases/17-conversational-graph-chat/17-CONTEXT.md
@.planning/phases/17-conversational-graph-chat/17-RESEARCH.md
@.planning/phases/17-conversational-graph-chat/17-VALIDATION.md
@.planning/phases/17-conversational-graph-chat/17-01-core-dispatch-sessions-PLAN.md

<!-- Phase 15 enrichment overlay — citation source for Stage 2 -->
@.planning/phases/15-async-background-enrichment/15-CONTEXT.md

<!-- Phase 18 anti-echo precedent -->
@.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md

@graphify/serve.py
@tests/test_serve.py

<interfaces>
<!-- Already added by Plan 17-01 -->
def _run_chat_core(G, communities, alias_map, arguments) -> str: ...
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"

<!-- Enrichment attrs attached by _load_enrichment_overlay (serve.py:130) BEFORE _run_chat_core runs -->
G.nodes[nid].get("enriched_description")   # first sentence is Stage-2 input
G.nodes[nid].get("description")            # pre-enrichment description fallback
G.nodes[nid].get("community_summary")      # community prose (fanned to members)
G.graph.get("patterns")                    # list[dict] pattern payloads

<!-- Existing helper for label safety (serve.py) -->
from graphify.security import sanitize_label
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add composer + validator + fuzzy + cap helpers; wire into _run_chat_core</name>
  <files>graphify/serve.py</files>
  <read_first>
    - graphify/serve.py (read current `_run_chat_core` after Plan 17-01 — line it sits at; read serve.py:130-200 for enrichment overlay attrs; read serve.py:752 `_subgraph_to_text` token heuristic for precedent)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md §§ 5, 6, 7, 8 (validator mechanics, token cap, fuzzy, composition scaffolds — ALL verbatim starters)
    - .planning/phases/17-conversational-graph-chat/17-CONTEXT.md D-04, D-05, D-09 + Claude's Discretion (echo-leak guard)
    - .planning/phases/17-conversational-graph-chat/17-01-core-dispatch-sessions-PLAN.md (interface of current `_run_chat_core`)
    - .planning/phases/15-async-background-enrichment/15-CONTEXT.md §§ D-04, D-05 (enrichment attrs)
    - graphify/security.py (for `sanitize_label` signature — confirm already imported in serve.py; grep `from graphify.security import`)
  </read_first>
  <behavior>
    - Composer produces a non-empty templated string for each intent when traversal yields ≥1 cited node; string references at least one sanitized label from citations.
    - Validator drops sentences containing a label-token whose owning node_id is NOT in the citation set.
    - If validator yields empty narrative → `_run_chat_core` returns `no_context` envelope (`text_body == ""`, `meta["status"] == "no_results"`, `meta["suggestions"]` drawn from `_fuzzy_suggest`).
    - Token cap: any narrative with `len(chars) > 2000` (500 tokens × 4 chars/tok) truncated at sentence boundary; last kept sentence ends with `…`.
    - Fuzzy suggest never echoes the raw user query token — output strings are strictly subset of the candidate pool.
  </behavior>
  <action>
All edits happen in `graphify/serve.py`.

**1. Add helpers immediately AFTER the Plan 17-01 session block, BEFORE `_run_chat_core`:**

```python
# --- Phase 17 Stage-2 helpers (Plan 17-02) ---

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_CHAT_NARRATIVE_TOKEN_CAP = 500
_CHAT_VALIDATOR_MAX_PASSES = 3  # Pitfall 7 re-validate bound


def _tokenize_narrative(text: str) -> list[str]:
    """ASCII-only tokens, lowercased. Matches D-03 tokenizer shape."""
    return [t.lower() for t in _WORD_RE.findall(text)]


def _split_sentences(narrative: str) -> list[str]:
    """Regex sentence split. Safe because Phase 17 narratives are templated (no embedded 'e.g.')."""
    return [s.strip() for s in _SENTENCE_RE.split(narrative) if s.strip()]


def _build_label_token_index(G: nx.Graph) -> dict[str, set[str]]:
    """{label_token_lowercased: {node_id, ...}}. Skip tokens <= 2 chars (Pitfall 2 false-positive cap)."""
    index: dict[str, set[str]] = {}
    for nid, data in G.nodes(data=True):
        label = (data.get("label") or "").lower()
        for tok in _WORD_RE.findall(label):
            if len(tok) <= 2:
                continue
            index.setdefault(tok, set()).add(nid)
    return index


def _validate_citations(
    narrative: str,
    cited_ids: set[str],
    label_index: dict[str, set[str]],
) -> tuple[str, list[str]]:
    """D-04/D-05: strip sentences whose token matches a real label not in cited_ids. Bounded re-validate."""
    current = narrative
    all_dropped: list[str] = []
    for _ in range(_CHAT_VALIDATOR_MAX_PASSES):
        kept, dropped = [], []
        for sentence in _split_sentences(current):
            violated = False
            for tok in _tokenize_narrative(sentence):
                owners = label_index.get(tok)
                if owners and not (owners & cited_ids):
                    violated = True
                    break
            (dropped if violated else kept).append(sentence)
        all_dropped.extend(dropped)
        current = " ".join(kept)
        if not dropped or not kept:
            break
    return current, all_dropped


def _fuzzy_suggest(
    terms: list[str],
    G: nx.Graph,
    communities: dict[int, list[str]],
    k: int = 3,
) -> list[str]:
    """CHAT-05 candidate pool: top-degree (god-node surrogate) + top-3 communities' top members.
    Returns label strings ONLY from the graph — never echoes user tokens (Pitfall 1)."""
    import difflib
    if not G.nodes:
        return []
    degree_sorted = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
    god_labels = [sanitize_label(G.nodes[n].get("label", n)) for n in degree_sorted[:20]]
    top_comms = sorted(communities.items(), key=lambda kv: -len(kv[1]))[:3]
    comm_labels = [
        sanitize_label(G.nodes[nid].get("label", nid))
        for _, members in top_comms
        for nid in members[:5]
        if nid in G.nodes
    ]
    candidates = list(dict.fromkeys(god_labels + comm_labels))  # dedup preserving order
    suggestions: list[str] = []
    for term in terms[:3]:  # bound search
        matches = difflib.get_close_matches(term, candidates, n=k, cutoff=0.6)
        for m in matches:
            if m not in suggestions:
                suggestions.append(m)
    # Hard guard: return only strings from candidates (never from terms).
    return [s for s in suggestions if s in candidates][:k]


def _truncate_to_token_cap(narrative: str, cap: int = _CHAT_NARRATIVE_TOKEN_CAP) -> str:
    """D-09: sentence-boundary truncation at 500 tokens (chars/4 heuristic)."""
    char_cap = cap * 4
    if len(narrative) <= char_cap:
        return narrative
    sentences = _split_sentences(narrative)
    out: list[str] = []
    total = 0
    for s in sentences:
        if total + len(s) + 1 > char_cap:
            break
        out.append(s)
        total += len(s) + 1
    if not out:
        return narrative[:char_cap].rstrip() + "…"
    truncated = " ".join(out)
    if len(out) < len(sentences):
        truncated = truncated.rstrip(".!?") + "…"
    return truncated


def _first_enrichment_sentence(G: nx.Graph, nid: str) -> str | None:
    """Return first sentence of enriched_description or description, if present (Phase 15 D-04/D-05)."""
    desc = G.nodes[nid].get("enriched_description") or G.nodes[nid].get("description")
    if not desc:
        return None
    parts = _split_sentences(str(desc))
    return parts[0] if parts else None


def _compose_explore_narrative(
    G: nx.Graph, visited: set[str], edges: list[tuple], cited_ids: set[str],
) -> str:
    """Template slot-fill for explore intent. Zero LLM."""
    if not visited:
        return ""
    ranked = sorted(visited, key=lambda n: G.degree(n), reverse=True)[:3]
    labels = [sanitize_label(G.nodes[n].get("label", n)) for n in ranked if n in G.nodes]
    if not labels:
        return ""
    edge_count = sum(1 for u, v in edges if u in visited and v in visited)
    desc_line = ""
    for nid in ranked:
        if nid not in cited_ids:
            continue
        s = _first_enrichment_sentence(G, nid)
        if s:
            lbl = sanitize_label(G.nodes[nid].get("label", nid))
            # Lowercase first letter of s for grammatical flow.
            s_low = s[0].lower() + s[1:] if s else s
            desc_line = f" Notably, {lbl} {s_low}"
            break
    return (
        f"The query touches {', '.join(labels)} — "
        f"connected through {edge_count} edges in the current graph."
        f"{desc_line}"
    )


def _compose_connect_narrative(
    G: nx.Graph, visited: set[str], edges: list[tuple], cited_ids: set[str],
    status: str,
) -> str:
    """Template slot-fill for connect intent."""
    if status != "ok" or not visited:
        return ""
    ranked = sorted(visited, key=lambda n: G.degree(n), reverse=True)[:4]
    labels = [sanitize_label(G.nodes[n].get("label", n)) for n in ranked if n in G.nodes]
    if not labels:
        return ""
    hop_count = len(edges)
    return (
        f"A path links {labels[0]} to {labels[-1]} via "
        f"{', '.join(labels[1:-1]) if len(labels) > 2 else 'direct edges'} — "
        f"{hop_count} hops in the current graph."
    )


def _compose_summarize_narrative(
    G: nx.Graph, visited: set[str], communities: dict[int, list[str]], cited_ids: set[str],
) -> str:
    """Template slot-fill for summarize intent. Surfaces community_summary when present."""
    if not visited:
        return ""
    # Find community with the most visited members
    community_counts: dict[int, int] = {}
    for nid in visited:
        if nid not in G.nodes:
            continue
        cid = G.nodes[nid].get("community")
        if cid is not None:
            community_counts[int(cid)] = community_counts.get(int(cid), 0) + 1
    if not community_counts:
        return ""
    top_cid = max(community_counts, key=lambda k: community_counts[k])
    members = communities.get(top_cid, [])
    member_labels = [
        sanitize_label(G.nodes[m].get("label", m))
        for m in members[:5] if m in G.nodes
    ]
    # Surface community_summary from any cited member
    summary_line = ""
    for nid in visited:
        if nid in cited_ids and nid in G.nodes:
            cs = G.nodes[nid].get("community_summary")
            if cs:
                first = _split_sentences(str(cs))
                if first:
                    summary_line = f" {first[0]}"
                    break
    return (
        f"Community {top_cid} groups {', '.join(member_labels)}.{summary_line}"
    )
```

**2. Rewrite the Stage-2 block inside `_run_chat_core`** — replace the placeholder `text_body = ""` lines from Plan 17-01 with:

```python
    # --- Stage 2: compose narrative per intent ---
    cited_ids_set: set[str] = {c["node_id"] for c in citations}
    if intent == "connect":
        narrative = _compose_connect_narrative(G, visited, edges, cited_ids_set, status)
    elif intent == "summarize":
        narrative = _compose_summarize_narrative(G, visited, communities, cited_ids_set)
    else:
        narrative = _compose_explore_narrative(G, visited, edges, cited_ids_set)

    # --- Stage 2: citation validator (D-04/D-05) ---
    if narrative:
        label_index = _build_label_token_index(G)
        cleaned, _dropped = _validate_citations(narrative, cited_ids_set, label_index)
        narrative = cleaned

    # --- Stage 2: no_context fallback with fuzzy suggestions (CHAT-05 + echo guard) ---
    suggestions: list[str] = []
    if not narrative or status == "no_results":
        narrative = ""
        status = "no_results"
        suggestions = _fuzzy_suggest(terms, G, communities, k=3)

    # --- Stage 2: 500-token cap (D-09 / CHAT-09) ---
    text_body = _truncate_to_token_cap(narrative) if narrative else ""
```

Then, update the `meta` dict construction to use the updated `status` and include `suggestions`:

```python
    meta = {
        "status": status,
        "intent": intent,
        "citations": citations if status == "ok" else [],
        "findings": [],
        "suggestions": suggestions,  # graph-sourced only (T-17-02)
        "session_id": session_id,
        "resolved_from_alias": {},  # Plan 17-03 threads aliases
    }
```

Update the session-write guard so stale turns are not recorded on `no_results`:

```python
    if session_id is not None and status == "ok" and text_body:
        turn = {
            "query": query_raw,
            "citations": citations,
            "narrative_hash": hashlib.sha256(text_body.encode("utf-8")).hexdigest()[:16],
            "ts": now,
        }
        _CHAT_SESSIONS.setdefault(session_id, deque(maxlen=_CHAT_SESSION_MAXLEN)).append(turn)
```

If `import hashlib` is not already in `serve.py`, add it to the stdlib import block (grep first).

**Critical invariants:**
- `text_body` returned from `_run_chat_core` MUST be the sentence-boundary-truncated string (post-validator, post-cap). Do NOT emit the full composer output when it exceeds the cap.
- `suggestions` list entries MUST be substrings sourced only from graph node labels — enforced by `_fuzzy_suggest`'s final filter. Do NOT add `query_raw` or any token from `terms` to `suggestions` anywhere in the core.
- Validator re-validate loop is bounded at `_CHAT_VALIDATOR_MAX_PASSES = 3` — Pitfall 7 guard against pathological expansion.
  </action>
  <verify>
    <automated>pytest tests/test_serve.py -q -k chat</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def _validate_citations(" graphify/serve.py` returns exactly one hit.
    - `grep -n "def _truncate_to_token_cap(" graphify/serve.py` returns exactly one hit.
    - `grep -n "def _fuzzy_suggest(" graphify/serve.py` returns exactly one hit.
    - `grep -n "def _compose_explore_narrative(" graphify/serve.py` returns exactly one hit.
    - `grep -n "def _compose_connect_narrative(" graphify/serve.py` returns exactly one hit.
    - `grep -n "def _compose_summarize_narrative(" graphify/serve.py` returns exactly one hit.
    - `grep -n "_CHAT_NARRATIVE_TOKEN_CAP\\s*=\\s*500" graphify/serve.py` returns exactly one hit.
    - `grep -n "_CHAT_VALIDATOR_MAX_PASSES" graphify/serve.py` returns at least 2 hits (definition + loop).
    - `grep -nE "^(import|from)\\s+(anthropic|openai|langchain|llm)" graphify/serve.py` returns zero hits.
    - `python -c "from graphify.serve import _validate_citations, _fuzzy_suggest, _truncate_to_token_cap, _compose_explore_narrative"` exits 0.
    - Existing Plan 17-01 tests still green: `pytest tests/test_serve.py -q -k "chat_envelope_ok or chat_session_isolation or chat_ttl_eviction or chat_intent_connect_calls_bi_bfs or chat_tool_registered"` all pass.
  </acceptance_criteria>
  <done>
    All helpers exist with exact signatures; `_run_chat_core` composes real narrative, validates citations, truncates to 500 tokens, falls back to graph-sourced fuzzy suggestions on empty match; no LLM imports introduced.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add validator / fuzzy / cap test cases (extend tests/test_serve.py)</name>
  <files>tests/test_serve.py</files>
  <read_first>
    - tests/test_serve.py (Plan 17-01's extensions — fixture `_reset_chat_sessions`, `_make_graph()`, imports)
    - .planning/phases/17-conversational-graph-chat/17-VALIDATION.md (test IDs: test_chat_validator_strips_uncited, test_chat_no_match_returns_suggestions, test_chat_suggestions_no_echo, test_chat_narrative_under_cap)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md § 11 (test harness boilerplate)
  </read_first>
  <behavior>
    - `test_chat_validator_strips_uncited`: given a narrative containing a label-token for a node NOT in `cited_ids`, `_validate_citations` returns cleaned narrative without that sentence. Sentence containing only cited labels survives.
    - `test_chat_no_match_returns_suggestions`: query with no real terms (e.g., `"xyznonexistentblah"`) produces envelope with `meta["status"] == "no_results"`, `text_body == ""`, `meta["suggestions"]` is a non-empty list drawn from graph labels (all entries are labels of actual nodes in `_make_graph()`).
    - `test_chat_suggestions_no_echo`: for query `"xyznonexistent"`, every entry in `meta["suggestions"]` is NOT equal to `"xyznonexistent"` and does NOT contain the substring `"xyznonexistent"`. `text_body` does NOT contain the string `"xyznonexistent"` either.
    - `test_chat_narrative_under_cap`: synthesize a graph with long `enriched_description` attrs OR monkeypatch `_compose_explore_narrative` to return a 5000-char prose; assert `len(text_body) <= 2000` (500 tokens × 4 char/tok); assert ends with `"…"` when truncated.
  </behavior>
  <action>
**Extend `tests/test_serve.py`** — do NOT create a new file.

**1. Extend import block to include new helpers:**
```python
from graphify.serve import (
    # ... existing Plan 17-01 imports preserved ...
    _validate_citations,
    _fuzzy_suggest,
    _truncate_to_token_cap,
    _build_label_token_index,
    _compose_explore_narrative,
)
```

**2. Add 4 new test cases using the existing `_reset_chat_sessions` fixture:**

```python
def test_chat_validator_strips_uncited():
    """CHAT-04 D-04: sentence containing uncited label-token is dropped."""
    G = _make_graph()
    # Build index; pick one label that IS in the graph.
    label_index = _build_label_token_index(G)
    # Choose any node in G; its label-tokens are the "real labels".
    sample_nid = next(iter(G.nodes))
    sample_label = G.nodes[sample_nid].get("label", sample_nid)
    sample_token = next(iter(_WORD_RE.findall(sample_label.lower())), None)
    assert sample_token and len(sample_token) > 2, "fixture invariant: graph must have a >2-char label token"

    # Narrative: sentence 1 cites sample_nid (ok); sentence 2 uses sample_token but we pass an EMPTY cited set → violation.
    narrative = f"Totally unrelated sentence. The {sample_token} appears here."
    cleaned, dropped = _validate_citations(narrative, cited_ids=set(), label_index=label_index)
    # With empty cited_ids, any sentence containing sample_token must be dropped.
    assert sample_token not in cleaned.lower()
    assert len(dropped) >= 1

    # When cited_ids contains sample_nid, the sentence survives.
    cleaned2, _ = _validate_citations(narrative, cited_ids={sample_nid}, label_index=label_index)
    assert sample_token in cleaned2.lower()


# Needs top-of-file import; add `from graphify.serve import _WORD_RE` or use `re.findall(r"[A-Za-z0-9_]+", ...)` inline.


def test_chat_no_match_returns_suggestions(_reset_chat_sessions):
    """CHAT-05: empty-match query returns fuzzy suggestions from graph candidate pool."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(
        G, communities, {}, {"query": "xyznonexistentblah"}
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "no_results"
    assert text_body == ""
    # Suggestions must all be drawn from graph labels
    graph_labels = {G.nodes[n].get("label", n) for n in G.nodes}
    for s in meta["suggestions"]:
        assert s in graph_labels or any(s in lbl for lbl in graph_labels), \
            f"suggestion {s!r} is not sourced from graph labels"


def test_chat_suggestions_no_echo(_reset_chat_sessions):
    """CHAT-05 echo-leak guard (T-17-02 / Pitfall 1 / Phase 18 D-12)."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    leak_marker = "xyznonexistentblah"
    response = _run_chat_core(
        G, communities, {}, {"query": leak_marker}
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert leak_marker not in text_body
    assert leak_marker not in json.dumps(meta["suggestions"])
    for s in meta["suggestions"]:
        assert leak_marker not in s


def test_chat_narrative_under_cap(_reset_chat_sessions, monkeypatch):
    """CHAT-09 / D-09: 500-token cap enforced; overflow truncates at sentence boundary with `…`."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    # Force composer to emit a long narrative using only real cited labels.
    cited_label = next(iter(G.nodes[next(iter(G.nodes))].get("label", "").split()), "node")
    long_narrative = (
        f"The query touches {cited_label}. " * 200
    )  # >2000 chars, all tokens reference a real (cited) label
    def _fake_compose(G_, visited, edges, cited_ids):
        return long_narrative
    monkeypatch.setattr("graphify.serve._compose_explore_narrative", _fake_compose)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    text_body, _meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    assert len(text_body) <= 2000, f"text_body {len(text_body)} chars exceeds 500-token cap"
    # When truncation occurred (original > cap), expect ellipsis marker
    if len(long_narrative) > 2000:
        assert text_body.endswith("…") or text_body == "", \
            "truncated narrative must end with ellipsis (or be empty if validator stripped it)"


def test_chat_truncate_helper_unit():
    """Unit test for _truncate_to_token_cap — sentence boundary behavior."""
    short = "Hello world."
    assert _truncate_to_token_cap(short) == short
    # 2500 chars → must truncate and end with …
    long = ("This is a sentence. " * 200)
    out = _truncate_to_token_cap(long)
    assert len(out) <= 2000
    assert out.endswith("…")
```

For `test_chat_validator_strips_uncited`, add to the import block:
```python
import re as _re_for_tests  # local alias if _WORD_RE is not exported
```
OR export `_WORD_RE` by adding it to the import list (preferred — it's already module-level in serve.py).
  </action>
  <verify>
    <automated>pytest tests/test_serve.py -q -k "chat_validator_strips_uncited or chat_no_match_returns_suggestions or chat_suggestions_no_echo or chat_narrative_under_cap or chat_truncate_helper_unit"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_chat_validator_strips_uncited" tests/test_serve.py` == 1
    - `grep -c "def test_chat_no_match_returns_suggestions" tests/test_serve.py` == 1
    - `grep -c "def test_chat_suggestions_no_echo" tests/test_serve.py` == 1
    - `grep -c "def test_chat_narrative_under_cap" tests/test_serve.py` == 1
    - `grep -c "def test_chat_truncate_helper_unit" tests/test_serve.py` == 1
    - `pytest tests/test_serve.py::test_chat_validator_strips_uncited -x` exits 0
    - `pytest tests/test_serve.py::test_chat_no_match_returns_suggestions -x` exits 0
    - `pytest tests/test_serve.py::test_chat_suggestions_no_echo -x` exits 0
    - `pytest tests/test_serve.py::test_chat_narrative_under_cap -x` exits 0
    - `pytest tests/test_serve.py -q` passes full module (all Plan 17-01 tests still green).
    - `pytest tests/ -q` baseline suite (≥ 1369 tests per STATE) passes.
  </acceptance_criteria>
  <done>
    Five new tests exist and pass; Plan 17-01 tests still pass; full suite clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| composer → validator | Composer output is untrusted at validator entry (even though templated, belt-and-suspenders) |
| fuzzy suggest → envelope | Suggestion strings must originate ONLY from graph candidate pool |
| composer → narrative cap | Any composer output may exceed cap; truncation enforced at emission |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-17-01 | Spoofing (fabricated citation) | composer output | mitigate | `_validate_citations` drops sentences containing label-tokens for uncited nodes; re-validate loop bounded at 3 passes; empty result → no_context envelope |
| T-17-02 | Information Disclosure (query echo) | `_fuzzy_suggest` + no_results branch | mitigate | `_fuzzy_suggest` final-filter keeps only entries drawn from `candidates` (god-labels ∪ community members); no_results branch sets `text_body = ""` (never interpolates query) |
| T-17-04 | DoS (unbounded payload) | `text_body` | mitigate | `_truncate_to_token_cap` sentence-boundary truncation at 500 tokens × 4 chars/tok; `…` marker |
</threat_model>

<verification>
- `pytest tests/test_serve.py -q` — all chat tests (Plan 17-01 + 17-02) green
- `pytest tests/ -q` — baseline suite green (≥1369 pre-plan)
- `grep -nE "^(import|from)\s+(anthropic|openai|langchain)" graphify/serve.py` — zero hits (CHAT-03 invariant held)
- `grep -c "def _validate_citations\|def _fuzzy_suggest\|def _truncate_to_token_cap" graphify/serve.py` ≥ 3
</verification>

<success_criteria>
- `chat` produces a templated narrative grounded in traversal results for explore / connect / summarize intents
- Uncited phrases are structurally dropped by the validator; empty remainder collapses to `no_results` envelope
- Fuzzy suggestions drawn ONLY from graph labels; no echo of unmatched query tokens anywhere in envelope
- Narrative always ≤ 500 tokens (char/4); truncation at sentence boundary with `…`
- `meta.findings` complete (no cap), `text_body` capped — callers can re-render if they want full answer
- Zero LLM imports introduced
</success_criteria>

<output>
After completion, create `.planning/phases/17-conversational-graph-chat/17-02-SUMMARY.md`.
</output>
