# Phase 17: Conversational Graph Chat — Research

**Researched:** 2026-04-22
**Domain:** MCP tool composition over existing graphify traversal primitives (zero LLM in `serve.py`)
**Confidence:** HIGH (all claims grep-verified against `serve.py@HEAD`, commit ce93793)

## Summary

Phase 17 ships `chat(query, session_id=None)` — a deterministic MCP tool that dispatches existing primitives (D-02 intents) and composes a D-08 narrative envelope with citation validation. All architecture questions are locked in CONTEXT.md. This research answers **"what do I paste into the new code"** — exact signatures, verbatim idioms, test fixture patterns, and a `graphify/commands/ask.md` template.

**Primary recommendation:** Model `_run_chat_core` after `_run_get_focus_context_core` (serve.py:1804) — same shape (pure dispatch core + MCP wrapper), same envelope idiom, same silent-ignore invariant. Reuse `_make_graph()` test fixture from `tests/test_serve.py:50` for `test_chat_*`. Wave structure: 3 plans (pipeline+sessions / validator+fuzzy / command+alias+integration).

<user_constraints>
## User Constraints (from 17-CONTEXT.md)

### Locked Decisions

- **D-01** Deterministic pipeline inside `_run_chat_core`. No LLM, no agent-supplied plan. Core classifies intent via keyword/regex and dispatches a fixed primitive sequence. Honors D-18 compose-don't-plumb.
- **D-02** Three intents in v1:
  - `explore` (default/fallback) — `_score_nodes(terms) → _bfs(top_seeds, depth=2) → _get_community(subgraph)` when `include_community` signals present (`about`, `overview`).
  - `connect` — two entity groups + connector verbs (`connect`, `relate`, `between`, `from…to`, `path`). Runs `_score_nodes(A) + _score_nodes(B) → _bidirectional_bfs(A_ids, B_ids, depth=3)`.
  - `summarize` — `what's in`, `overview of`, `summarize <module>`. Runs `_score_nodes(terms) → _get_community(seed_ids)` (skips BFS).
- **D-03** Entity terms: lowercase tokenize + stopword filter including intent verbs (`what, how, is, the, between, connect, relate, show, explain, tell, me, about, of, in, for, with, and, or, but, to, from, across, among` — planner may extend; ASCII-only).
- **D-04** Citation validator: label-token match. For every token in narrative, if token is substring of a real node label AND owning `node_id` not in turn citation list → sentence flagged.
- **D-05** On violation: split on `[.!?]+\s+`, drop violating sentences, re-validate remainder. If non-empty → `text_body`. If empty → no_context envelope.
- **D-06** `_SESSIONS: dict[str, deque(maxlen=10)]`, 30-min (1800s) idle TTL evicted lazily on access. Entry = `{query, citations: [{node_id, label, source_file}], narrative_hash, ts}`. Process-lifetime, no disk.
- **D-07** Follow-up regex: `^(and|but|what about|tell me more|more|why|how come)\b` OR `\bit\b`/`\bthat\b` at sentence start. Match anchored to START of query. Prepend prior turn's cited `node_ids` to current entity terms before `_score_nodes`.
- **D-08** Envelope: prose in `text_body`, structured packet in `meta = {citations, findings, suggestions, session_id, alias_redirects, intent, status}`.
- **D-09** 500-token cap via sentence-boundary truncation. `chars/4` heuristic. Drop trailing sentences until under cap; append `…` to last kept sentence. `meta.findings` stays complete.

### Claude's Discretion

- Fuzzy suggestion source (CHAT-05): default `difflib.get_close_matches(term, candidates, n=3, cutoff=0.6)` where candidates = god-node labels ∪ top-community member labels. Stdlib only.
- `/graphify-ask`: single-shot per invocation. Fresh UUID4 `session_id` per slash-call. Multi-turn history reserved for direct MCP callers.
- Empty-result suggestion wording: planner chooses. **MUST NOT echo unmatched query tokens** (Phase 18 D-12 anti-leak).

### Deferred Ideas (OUT OF SCOPE)

- Five-intent taxonomy (`compare`, `trace`). Spacy/nltk entity extraction. Persistent session history. Cross-session memory. Chat-to-argue handoff (CHAT-12 P2). Save-chat-as-vault-note (CHAT-11 P2). Auto-suggest follow-ups from surprising connections (CHAT-10 P2). Trigram fuzzy index.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | MCP tool `chat(query, session_id=None)` + two-stage pipeline | §§ Primitive Signatures, Envelope Idiom, MCP Registration |
| CHAT-02 | Stage 1 primitive dispatch (`_score_nodes`/`_bfs`/`_dfs`/`_bidirectional_bfs`/`_get_community`/`_connect_topics`) | §§ Primitive Signatures (exact return shapes) |
| CHAT-03 | Stage 2 no-LLM composition | §§ Narrative Composition Scaffold |
| CHAT-04 | Citation validator | §§ Citation Validator Mechanics |
| CHAT-05 | Fuzzy suggestions on empty results | §§ Fuzzy Suggestions (difflib pattern + echo guard) |
| CHAT-06 | `/graphify-ask` command file | §§ Slash-Command Template (verbatim frontmatter) |
| CHAT-07 | D-16 alias redirect threaded through citations | §§ Alias Redirect Threading (verbatim `_resolve_alias` closure) |
| CHAT-08 | Session history, no cross-session memory | §§ Session History Implementation |
| CHAT-09 | D-02 envelope + 500-tok cap | §§ Envelope Idiom, Token Cap Algorithm |
| CHAT-10 P2 | Follow-up suggestions | Deferred per CONTEXT |
| CHAT-11 P2 | Save-chat-as-vault-note | Deferred per CONTEXT |
| CHAT-12 P2 | Chat-to-argue handoff | Deferred per CONTEXT |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Intent classification + entity extraction | `_run_chat_core` (Stage 1) | — | Deterministic keyword/regex dispatch; no LLM |
| Graph traversal | existing primitives at `serve.py:535,546,562,685,1212` | — | D-18 compose-don't-plumb |
| Narrative composition + citation validation | `_run_chat_core` (Stage 2) | — | Template slot-fill over tool results |
| Session history | module-level `_SESSIONS` in `serve.py` | — | Process-lifetime, lazy TTL; no I/O |
| Human-facing renderer | skill / calling agent | — | CHAT-03: serve.py makes zero LLM calls |
| D-16 alias resolution | inline `_resolve_alias` closure in `_run_chat_core` | `_alias_map` loaded by `_maybe_reload_dedup()` (serve.py:2057) | Copy idiom from `_run_query_graph:956` / `_run_connect_topics:1245` |

## Project Constraints (from ./CLAUDE.md)

- Python 3.10+ (CI runs 3.10 and 3.12). No `collections.deque` features newer than 3.9.
- `from __future__ import annotations` as first import.
- Type hints on all public functions; `dict[...]` / `str | None` style.
- Pure unit tests: no network, no filesystem side effects outside `tmp_path`.
- No linter / no formatter configured. 4-space indent, PEP-8 spirit.
- Imports: stdlib → third-party → local. Absolute: `from graphify.x import y`.
- Warnings/errors to stderr via `print(..., file=sys.stderr)` prefixed `[graphify]`.
- All external input passes through `graphify/security.py`. Label sanitization via `sanitize_label()` already used by `_run_connect_topics` and `_run_get_focus_context_core`.
- One test file per module (`tests/test_serve.py` already exists — extend, don't add new file).

---

## 1. Primitive Signatures (verbatim from serve.py@HEAD)

Planner: paste these signatures as-is into `read_first` and task acceptance criteria. Line numbers are anchors for the task's `files_modified`.

### `_score_nodes` — serve.py:535
```python
def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    # Scores = sum(1 per term substring-in-label) + sum(0.5 per term substring-in-source_file)
    # Returns sorted([(score, node_id), ...], reverse=True). Nodes with score 0 omitted.
```
**Return shape:** `list[tuple[float, str]]` — **NOT** `list[str]`. Stage 1 pulls `start_nodes = [nid for _, nid in scored[:N]]` (see `_run_query_graph:1000`).
**Term preprocessing idiom (reference: `_run_query_graph:999`):** `terms = [t.lower() for t in question.split() if len(t) > 2]`. Phase 17 must replace this with D-03's stopword filter before calling.

### `_bfs` — serve.py:546
```python
def _bfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    # Returns (visited, edges_seen). edges_seen is list of (u, v) parent→child tuples.
```
**Return shape:** `tuple[set[str], list[tuple[str, str]]]`. Feed directly to `_subgraph_to_text` or consume `visited` for citation set.

### `_bidirectional_bfs` — serve.py:562
```python
def _bidirectional_bfs(
    G: nx.Graph,
    start_nodes: list[str],
    target_nodes: list[str],
    depth: int,        # combined hop budget (forward + reverse)
    max_visited: int,  # REQUIRED — no default
) -> tuple[set[str], list[tuple], str]:
    # Returns (visited, edges_seen, status)
    # status ∈ {"ok", "frontiers_disjoint", "budget_exhausted"}
```
**Gotcha:** `max_visited` is **required**. `_run_query_graph` passes it as `max(100, min(5000, budget * 2))`-shaped clamp (grep `max_visited` near line 1040). Pick a Stage-1-appropriate value (e.g., `1000`).

### `_dfs` — serve.py:685
```python
def _dfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    # Same return shape as _bfs. Reserved in whitelist; no D-02 intent dispatches it in v1.
```
Include in allow-list per CHAT-02 but no code path invokes it.

### `_get_community` / `_communities_from_graph` — serve.py:525 / runtime
No dedicated `_get_community(subgraph)` function exists. The existing pattern is: `communities` dict is already computed by `_communities_from_graph(G) -> dict[int, list[str]]` (serve.py:525) at serve() startup and passed into every core. For the `explore`/`summarize` intents:

```python
# Map each seed node to its community id, then fetch member labels:
community_ids = {G.nodes[nid].get("community") for nid in seed_ids if nid in G.nodes}
community_ids.discard(None)
for cid in community_ids:
    members = communities.get(int(cid), [])
```

**Signature planner must use in `_run_chat_core`:**
```python
def _run_chat_core(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str] | None,
    arguments: dict,  # {"query": str, "session_id": str | None}
) -> str:
```
Match the 4-arg shape of `_run_connect_topics(G, communities, alias_map, arguments)` at serve.py:1212.

### `_subgraph_to_text` — serve.py:752
```python
def _subgraph_to_text(
    G: nx.Graph, nodes: set[str], edges: list[tuple],
    token_budget: int = 2000, layer: int = 3,
) -> str:
```
**Char budget:** `char_budget = token_budget * 3`. Every label goes through `sanitize_label()`. **Phase 17 probably does NOT call this directly** — Stage 2 composes prose, not `NODE/EDGE` lines. Use it only if `meta.findings` wants a raw subgraph snippet.

### `_find_node` — serve.py:805 (approx, grep to confirm)
```python
def _find_node(G: nx.Graph, label: str) -> list[str]:
    # Case-insensitive substring match on label OR exact match on node id.
```
Used by `_run_connect_topics` to resolve user-supplied topic strings. Phase 17 may reuse for the `connect` intent after `_score_nodes` produces candidate groups.

---

## 2. D-02 Envelope Idiom (verbatim)

### Sentinel — serve.py:901
```python
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"
```
Import it from `graphify.serve` in tests: already re-exported at serve.py:46 (tests import it directly, see `tests/test_serve.py:46`).

### Budget clamp idiom (used in EVERY core)
```python
budget = int(arguments.get("budget", 2000))
budget = max(50, min(budget, 100000))
```
Appears at serve.py:940, 1136, 1225, 1403, 1581, 1682, 1826. Chat's narrative cap is fixed at 500 tokens (CHAT-09), so this clamp is for `meta.findings` subgraph snippets only — `budget_used` reporting uses `min(len(text_body) // 3, budget)`.

### Envelope composition (success path)
```python
return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

### Envelope composition (empty/error path)
```python
return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```
Note the **leading `""`** is intentional for symmetry — every core uses it (grep `'"" + QUERY_GRAPH_META_SENTINEL'`).

### Manifest hash — automatic at wrapper layer
**Do NOT manually add `manifest_content_hash` inside `_run_chat_core`.** The `_merge_manifest_meta` wrapper at serve.py:2104 parses the envelope, injects `meta["manifest_content_hash"]`, and re-serializes. If your core returns a sentinel-less text (rare), the wrapper wraps it with a synthetic `{"status":"ok","manifest_content_hash":...}`. Ensure `_run_chat_core` ALWAYS emits the sentinel so the parse path is taken.

---

## 3. Session History Implementation (D-06, D-07)

### Module-level state placement
Add near line 901 (sentinel vicinity), grouped with the other module-level MCP state:

```python
from __future__ import annotations
from collections import deque  # ADD — not currently imported in serve.py
import time

# Phase 17 D-06: conversational session store. Process-lifetime; evicted lazily.
_CHAT_SESSIONS: dict[str, deque] = {}
_CHAT_SESSION_TTL_SECONDS = 1800  # 30 min
_CHAT_SESSION_MAXLEN = 10
```

### Concurrency note
The MCP stdio server is **single-threaded async** (serve.py:2524 `async def call_tool`). Handler calls are serialized by the asyncio event loop; **no lock needed** on `_CHAT_SESSIONS`. Confirmed via grep: no `threading.Lock`, no `asyncio.Lock` on any other module-level dict in serve.py (e.g., `_FOCUS_DEBOUNCE_CACHE` at serve.py:1918 area is lock-free). [VERIFIED: grep-scan of serve.py]

### TTL eviction (lazy-on-access)
```python
def _chat_evict_stale(now: float) -> None:
    """Drop any session whose newest turn is older than TTL. Called at start of every chat call."""
    stale = [sid for sid, turns in _CHAT_SESSIONS.items()
             if not turns or (now - turns[-1]["ts"] > _CHAT_SESSION_TTL_SECONDS)]
    for sid in stale:
        del _CHAT_SESSIONS[sid]
```

### Pitfall: `session_id=None`
D-06 keys sessions by `str`. A `None` session_id must **skip writing to history entirely** (otherwise all nil-session callers share one giant deque, violating CHAT-08 "scoped per session_id"). Guard:
```python
if session_id is not None:
    _CHAT_SESSIONS.setdefault(session_id, deque(maxlen=_CHAT_SESSION_MAXLEN)).append(turn)
```

### Follow-up seed augmentation (D-07)
```python
import re
_FOLLOWUP_RE = re.compile(r"^(and|but|what about|tell me more|more|why|how come)\b", re.IGNORECASE)
_PRONOUN_RE = re.compile(r"^(it|that)\b", re.IGNORECASE)  # anchored at START only (see D-07 pitfall)

def _augment_terms_from_history(session_id: str | None, query: str, terms: list[str]) -> list[str]:
    if session_id is None or session_id not in _CHAT_SESSIONS:
        return terms
    if not (_FOLLOWUP_RE.match(query.strip()) or _PRONOUN_RE.match(query.strip())):
        return terms
    prior = _CHAT_SESSIONS[session_id]
    if not prior:
        return terms
    last_turn = prior[-1]
    prior_node_ids = [c["node_id"] for c in last_turn.get("citations", [])]
    return prior_node_ids + terms  # D-07: prepend, so history-derived seeds rank ahead
```

**Pitfall:** Do NOT match the follow-up regex anywhere in the query — "describe the component that logger calls" contains "that" but is NOT a pronoun-followup. CONTEXT.md D-07 + Specifics note explicitly anchor on `^` or after a leading connector.

---

## 4. Alias Redirect Threading (CHAT-07, D-16)

Copy the closure from `_run_connect_topics:1245` verbatim. Every `node_id` emitted into `meta.citations` must pass through it.

```python
_resolved_aliases: dict[str, list[str]] = {}
_effective_alias_map: dict[str, str] = alias_map or {}

def _resolve_alias(node_id: str) -> str:
    canonical = _effective_alias_map.get(node_id)
    if canonical and canonical != node_id:
        aliases = _resolved_aliases.setdefault(canonical, [])
        if node_id not in aliases:
            aliases.append(node_id)
        return canonical
    return node_id
```

**Where to apply** (per Phase 10 D-16 pattern):
1. After `_score_nodes` returns → map each `nid` through `_resolve_alias` before consuming.
2. Before building each citation entry → `citations.append({"node_id": _resolve_alias(nid), ...})`.
3. At the end of `_run_chat_core`, if `_resolved_aliases` is non-empty: `meta["alias_redirects"] = _resolved_aliases` (schema per D-08 envelope spec; prior phases use `meta["resolved_from_alias"]` — planner must reconcile: CONTEXT.md calls the field `alias_redirects`, existing code uses `resolved_from_alias`. **Recommend D-08's `alias_redirects` name** — this is a NEW field on a new tool, not a rename).

**Wrapper wiring:** `_alias_map` is loaded per-call by `_maybe_reload_dedup()` at serve.py:2054. The new `_tool_chat(arguments)` wrapper must call `_maybe_reload_dedup()` and pass `_alias_map` into `_run_chat_core`. See `_tool_query_graph:2118` for the full pattern.

---

## 5. Citation Validator Mechanics (CHAT-04, D-04, D-05)

### Tokenizer
Phase 17 controls the narrative text (it's templated), so a regex split is safe:
```python
import re
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")

def _tokenize_narrative(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]
```
Avoid `\w+` if you want to exclude non-ASCII — `[A-Za-z0-9_]+` matches the ASCII-only stopword constraint in CONTEXT.md Specifics.

### Real-labels lookup
Build ONCE per call (O(|V|)), not per-sentence:
```python
def _build_label_token_index(G: nx.Graph) -> dict[str, set[str]]:
    """Returns {label_token_lowercased: {node_id, ...}}. Multi-word labels contribute each token."""
    index: dict[str, set[str]] = {}
    for nid, data in G.nodes(data=True):
        label = (data.get("label") or "").lower()
        for tok in _WORD_RE.findall(label):
            if len(tok) <= 2:  # skip "a", "is", "of" — reduces false positives
                continue
            index.setdefault(tok, set()).add(nid)
    return index
```
**False-positive cap:** The `len(tok) <= 2` skip rule is critical. Without it, a node labeled "Layer A" contributes the token "a" and every narrative sentence gets flagged. [ASSUMED — planner should stress-test in Wave 3]

### Sentence splitter (D-05)
```python
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

def _split_sentences(narrative: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(narrative) if s.strip()]
```
Use lookbehind so the punctuation stays on the preceding sentence (we re-join with spaces). Safe because Phase 17 generates the prose from templates — no embedded abbreviations like "e.g.".

### Validator core
```python
def _validate_citations(
    narrative: str,
    cited_ids: set[str],
    label_index: dict[str, set[str]],
) -> tuple[str, list[str]]:
    """Returns (cleaned_narrative, dropped_sentences). Empty cleaned_narrative → caller falls back to no_context."""
    kept, dropped = [], []
    for sentence in _split_sentences(narrative):
        violated = False
        for tok in _tokenize_narrative(sentence):
            owners = label_index.get(tok)
            if owners and not (owners & cited_ids):
                violated = True
                break
        (dropped if violated else kept).append(sentence)
    return " ".join(kept), dropped
```
D-05 re-validate: after first drop, re-run validator on `" ".join(kept)` to catch sentences whose violating claim was only legitimized by a now-dropped neighbor. Practical implementation: loop until `dropped` is empty OR `kept` is empty.

---

## 6. 500-Token Cap (CHAT-09, D-09)

```python
_CHAT_NARRATIVE_TOKEN_CAP = 500

def _truncate_to_token_cap(narrative: str, cap: int = _CHAT_NARRATIVE_TOKEN_CAP) -> str:
    # chars/4 heuristic matches the existing serve.py idiom (see _run_get_focus_context_core:1876 uses *3; char/4 is documented in CONTEXT.md D-09).
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
        # Fallback: single-sentence narrative already over cap — hard-slice.
        return narrative[:char_cap] + "…"
    truncated = " ".join(out)
    if len(out) < len(sentences):
        truncated = truncated.rstrip(".!?") + "…"
    return truncated
```

**Discrepancy note:** Existing cores use `chars/3` (serve.py:1876 `char_budget = budget * 3`) not `chars/4`. CONTEXT.md D-09 says `char/4`. Either works (both approximate GPT tokenization); recommend `/4` per CONTEXT.md. [CITED: 17-CONTEXT.md D-09]

---

## 7. Fuzzy Suggestions (CHAT-05)

```python
import difflib

def _fuzzy_suggest(term: str, G: nx.Graph, communities: dict[int, list[str]], k: int = 3) -> list[str]:
    # Candidate pool: top-degree nodes (god-node surrogate) + top-3 communities' members.
    degree_sorted = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
    god_labels = [G.nodes[n].get("label", n) for n in degree_sorted[:20]]
    top_comms = sorted(communities.items(), key=lambda kv: -len(kv[1]))[:3]
    comm_labels = [G.nodes[nid].get("label", nid) for _, members in top_comms for nid in members[:5]]
    candidates = list(dict.fromkeys(god_labels + comm_labels))  # preserve order, dedup
    return difflib.get_close_matches(term, candidates, n=k, cutoff=0.6)
```

**Echo-leak guard (Phase 18 D-12 precedent):** `meta.suggestions` and any template prose must include ONLY strings from `candidates` — never reflect the user's unmatched token back. The template must NOT say `"no match for 'xyz'; did you mean…"` — just `"Did you mean: A, B, C?"`. If `_fuzzy_suggest` returns `[]`, fall back to a generic "No matching nodes in this graph." Do not echo the term.

---

## 8. Narrative Composition Scaffold

Zero LLM. Pure template slot-fill. Example `explore` intent:

```python
def _compose_explore_narrative(G, visited: set[str], edges: list[tuple], cited_ids: set[str]) -> str:
    # Pull top-3 by degree within visited; cite each.
    ranked = sorted(visited, key=lambda n: G.degree(n), reverse=True)[:3]
    labels = [sanitize_label(G.nodes[n].get("label", n)) for n in ranked]
    edge_count = sum(1 for u, v in edges if u in visited and v in visited)
    # Enrichment overlay: if node has enriched_description, surface first sentence.
    desc_line = ""
    for nid in ranked:
        d = G.nodes[nid].get("enriched_description") or G.nodes[nid].get("description")
        if d:
            first = _split_sentences(d)[:1]
            if first:
                desc_line = f" Notably, {sanitize_label(G.nodes[nid]['label'])} {first[0][0].lower()}{first[0][1:]}"
                break
    return (
        f"The query touches {', '.join(labels)} — connected through {edge_count} edges in the current graph."
        f"{desc_line}"
    )
```

**Enrichment as citation source (Phase 15 D-04/D-05):** By the time `_run_chat_core` runs, `_load_enrichment_overlay` (serve.py:130) has already attached:
- `G.nodes[nid]["enriched_description"]` — human-readable description
- `G.nodes[nid]["community_summary"]` — community prose (fanned out to each member)
- `G.nodes[nid]["staleness_override"]` — staleness label
- `G.graph["patterns"]` — list of pattern dicts

Stage 2 may surface these in `text_body` / `meta.findings` **without any I/O**. [VERIFIED: serve.py:130-200]

---

## 9. MCP Registration

### `graphify/mcp_tool_registry.py` — add entry
Model after `connect_topics` (line 214) and `get_focus_context` (line 231):

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

### `graphify/serve.py` — wrapper + dispatch table

**Wrapper** (near serve.py:2311 `_tool_connect_topics`):
```python
def _tool_chat(arguments: dict) -> str:
    _reload_if_stale()
    if not Path(graph_path).exists():
        meta = {"status": "no_graph", "citations": [], "findings": [],
                "suggestions": [], "session_id": None, "intent": None}
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    return _run_chat_core(G, communities, _alias_map, arguments)
```

**Dispatch table** (serve.py:2484):
```python
"chat": _tool_chat,
```
(Add alongside existing 20 entries.)

---

## 10. Slash-Command Template — `graphify/commands/ask.md`

**Frontmatter discrepancy:** CONTEXT.md references `target: both` but **no existing command file in `graphify/commands/` uses a `target:` field** [VERIFIED: grep across 7 .md files, zero hits]. The actual frontmatter convention is:

```
---
name: <name>
description: <short desc>
argument-hint: <args>            # optional
disable-model-invocation: true
---
```

Recommend planner file `ask.md` as:

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
- (omit `session_id` — slash-command is single-shot; the MCP tool will generate/accept one if the agent wants multi-turn)

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `no_results`:** render the fuzzy suggestions from `meta.suggestions` as "Did you mean: A, B, C?". Do NOT echo the original query's unmatched terms back.

**If `status` is `ok`:** render `text_body` verbatim (it is already token-capped and cited). Do NOT re-summarize. After the body, list the citations inline:
> **Cited nodes:** [label1](source_file1), [label2](source_file2), …

Keep total output under 500 tokens (the tool already caps narrative; do not expand).
```

Clarify with user before shipping if CONTEXT.md's `target: both` is a requirement from a NEW convention planned for Phase 17 vs. a mis-specification. [ASSUMED]

---

## 11. Test Harness Patterns (`tests/test_serve.py`)

### Import pattern (add `_run_chat_core` to existing block at line 42)
```python
from graphify.serve import (
    ...,
    _run_chat_core,
    _CHAT_SESSIONS,  # for test isolation
    QUERY_GRAPH_META_SENTINEL,
)
```

### Reusable fixture — already exists at line 50
```python
def _make_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", ...)
    # 5 nodes, 3 edges, 3 communities. Use for chat happy-path tests.
```

### Envelope assertion boilerplate (from serve tests)
```python
def test_chat_envelope_ok():
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    assert QUERY_GRAPH_META_SENTINEL in response
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "ok"
    assert meta["intent"] in ("explore", "connect", "summarize")
    assert len(meta["citations"]) >= 1
    # Every cited node_id must be real:
    assert all(c["node_id"] in G.nodes for c in meta["citations"])
```

### Session isolation fixture — add to tests
```python
import pytest
from graphify.serve import _CHAT_SESSIONS

@pytest.fixture(autouse=True)
def _reset_chat_sessions():
    _CHAT_SESSIONS.clear()
    yield
    _CHAT_SESSIONS.clear()
```
Scope this ONLY to chat tests (not autouse at module level — other tests don't need it). Use a marker or a class-scoped fixture.

### Pattern for zero-LLM architectural test (SC4)
```python
def test_serve_makes_zero_llm_calls():
    """CHAT-03 SC4: serve.py source must not import LLM clients."""
    import pathlib
    src = pathlib.Path("graphify/serve.py").read_text()
    forbidden = ("import anthropic", "from anthropic", "import openai", "from openai",
                 "from graphify.llm", "import graphify.llm")
    for needle in forbidden:
        assert needle not in src, f"serve.py introduced LLM dependency: {needle}"
```

---

## 12. Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entity resolution | Fuzzy matcher | `_score_nodes` (serve.py:535) | Already handles partial label + source_file scoring |
| BFS/traversal | New walker | `_bfs` / `_bidirectional_bfs` / `_dfs` | D-18; already tested; `_bidirectional_bfs` returns status string for disjoint handling |
| Alias resolution | New resolver | `_resolve_alias` closure from `_run_connect_topics:1245` | Verbatim copy; fed by `_alias_map` from `_maybe_reload_dedup()` |
| Envelope emit | New format | `text_body + SENTINEL + json.dumps(meta)` | Manifest-hash wrapper depends on exact shape |
| Fuzzy suggestions | Trigram index, rapidfuzz | `difflib.get_close_matches` | Stdlib; acceptable perf < 10k nodes |
| Session store | SQLite, disk | Module-level `dict[str, deque]` + lazy TTL | D-06 process-lifetime |
| Sentence split | nltk/spacy | `re.split(r"(?<=[.!?])\s+", ...)` | Templated prose; no abbreviations |
| Token count | tiktoken | `chars/4` heuristic | Matches existing serve.py cores |

---

## 13. Common Pitfalls

### P1: Echo leak in fuzzy suggestions
**Symptom:** Template includes the unmatched user term ("no match for 'xyz'"). **Why bad:** Phase 18 D-12 — distinguishes typoed-real from crafted-spoof queries. **Fix:** Emit only strings from the candidate pool; use generic "No matching nodes." on empty result.

### P2: Label-token false positives (short tokens)
**Symptom:** Validator flags every sentence because a node is labeled "Layer A" and "a" appears everywhere. **Fix:** `if len(tok) <= 2: continue` in both tokenizer and label-index builder. [ASSUMED — tune cutoff during dogfooding]

### P3: Alias redirect applied too late
**Symptom:** `meta.citations[i].node_id == "auth"` (merged-away) instead of `"authentication_service"`. **Fix:** Apply `_resolve_alias` on every `nid` BEFORE it enters `citations` — NOT after. See `_run_query_graph:977` pattern (resolution happens on input arguments AND on emitted IDs).

### P4: Follow-up regex matches mid-query "that"
**Symptom:** "describe the component that logger calls" triggers pronoun-followup seed augmentation. **Fix:** Anchor all follow-up patterns with `^` — never `\bthat\b` unqualified (CONTEXT.md D-07 + Specifics).

### P5: `session_id=None` collects a global deque
**Symptom:** All anonymous callers share history. **Fix:** Skip write path when `session_id is None`; only read history when session_id in _CHAT_SESSIONS.

### P6: Sentence splitter eats abbreviations
**Symptom:** "e.g., the module" splits at "e." — not a real sentence boundary. **Mitigation:** Phase 17's narrative is templated; **do not insert "e.g.", "i.e.", "Dr.", etc. in templates.** Lint this convention in code review.

### P7: Validator's re-validate pass blows up
**Symptom:** Infinite loop when dropping a sentence enables another. **Fix:** Bound re-validate to a max of 3 passes, then force `no_context` if still violating. Belt + suspenders for D-05.

### P8: `_bidirectional_bfs` called without `max_visited`
**Symptom:** TypeError at runtime (no default). **Fix:** Pass a sane cap, e.g., `max_visited=1000`. See `_run_query_graph` invocation near line 1035.

### P9: Forgetting `_maybe_reload_dedup()` in wrapper
**Symptom:** `_alias_map` is stale after a dedup_report rewrite. **Fix:** Call `_maybe_reload_dedup()` at top of `_tool_chat`, before passing `_alias_map`. [VERIFIED: pattern used at serve.py:2056]

### P10: Not emitting sentinel on early returns
**Symptom:** `_merge_manifest_meta` wrapper synthesizes a fake envelope, hiding real error. **Fix:** Every return path from `_run_chat_core` must be `"" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta)` — even errors.

---

## 14. Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥ 7 (already in `[dev]` extras via `pyproject.toml`) |
| Config file | `pyproject.toml` (no `pytest.ini`) |
| Quick run command | `pytest tests/test_serve.py -q -k chat` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | `chat` tool registered in MCP registry | unit | `pytest tests/test_serve.py::test_chat_tool_registered -x` | ❌ Wave 1 |
| CHAT-02 | Intent dispatch invokes correct primitive | unit (with spy/patch) | `pytest tests/test_serve.py::test_chat_intent_connect_calls_bi_bfs -x` | ❌ Wave 1 |
| CHAT-03 | Zero-LLM architectural test | unit (grep) | `pytest tests/test_serve.py::test_serve_makes_zero_llm_calls -x` | ❌ Wave 3 |
| CHAT-04 | Uncited phrase rejected | unit | `pytest tests/test_serve.py::test_chat_validator_strips_uncited -x` | ❌ Wave 2 |
| CHAT-05 | Fuzzy suggestions on empty | unit | `pytest tests/test_serve.py::test_chat_no_match_returns_suggestions -x` | ❌ Wave 2 |
| CHAT-05 | No echo of unmatched token | unit | `pytest tests/test_serve.py::test_chat_suggestions_no_echo -x` | ❌ Wave 2 |
| CHAT-06 | `/graphify-ask` file exists and is valid | unit | `pytest tests/test_commands.py::test_ask_md_frontmatter -x` (extend if exists) | ❌ Wave 3 |
| CHAT-07 | Alias redirect threaded | unit | `pytest tests/test_serve.py::test_chat_alias_redirect_canonical -x` | ❌ Wave 3 |
| CHAT-08 | Session history scoped + TTL | unit | `pytest tests/test_serve.py::test_chat_session_isolation -x` + `test_chat_ttl_eviction -x` | ❌ Wave 1 |
| CHAT-09 | 500-tok cap enforced | unit | `pytest tests/test_serve.py::test_chat_narrative_under_cap -x` | ❌ Wave 2 |
| CHAT-09 | D-02 envelope structural | unit | `pytest tests/test_serve.py::test_chat_envelope_ok -x` | ❌ Wave 1 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_serve.py -q -k chat` (< 3s).
- **Per wave merge:** `pytest tests/test_serve.py -q` (full serve suite, < 15s).
- **Phase gate:** `pytest tests/ -q` (full suite, 1329+ tests).

### Wave 0 Gaps
- [ ] `tests/test_serve.py` extensions — no new file; all chat tests extend existing module.
- [ ] Session-isolation fixture (class-scoped or explicit `_CHAT_SESSIONS.clear()` per test).
- No framework install needed — pytest already used.

---

## 15. Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MCP stdio runs under caller's process; no auth layer in serve.py |
| V3 Session Management | partial | `_CHAT_SESSIONS` is process-local; session_id supplied by caller (no server-issued tokens). Treat session_id as untrusted string — sanitize length and chars. |
| V4 Access Control | no | All graph data is already public to the MCP caller |
| V5 Input Validation | **yes** | `query` + `session_id` both untrusted strings — sanitize, length-cap |
| V6 Cryptography | no | No secrets, no tokens |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| session_id DOS (huge id, fills dict) | Denial of Service | Validate `len(session_id) <= 128`, reject or truncate |
| Query injection into label_index / fabrication | Spoofing | Label-token validator (D-04) — sentences with tokens matching real labels but uncited get dropped |
| Echo-leak via unmatched term (info-disclosure distinguisher) | Information Disclosure | Phase 18 D-12 — never reflect unmatched query tokens |
| Control chars in query → log injection | Tampering | `sanitize_label(query)` at entry (existing helper) — strips `\x00-\x1f\x7f` and caps at 256 chars |

---

## 16. Estimated Plan Count & Wave Structure

**Recommendation: 3 plans.** Phase 17 is meaningfully smaller than Phase 18 (which shipped 4 plans across 9 REQs) — it has no snapshot sentinel overhead and reuses primitives already shipped.

| Plan | Scope | REQ-IDs | Est. Size |
|------|-------|---------|-----------|
| **17-01 — Core dispatch + sessions** | `_run_chat_core` shell, intent classifier, D-02/D-03/D-06/D-07 primitives-wiring, `_tool_chat`, `mcp_tool_registry` entry, `_CHAT_SESSIONS` + TTL + follow-up augmentation. Smoke tests for each intent. | CHAT-01, CHAT-02, CHAT-08 | Large |
| **17-02 — Validator + narrative composition + cap** | Citation validator (D-04/D-05), label-token index, sentence splitter, fuzzy suggestions (CHAT-05 with echo guard), 500-tok cap (D-09), template scaffolds for the 3 intents. | CHAT-03, CHAT-04, CHAT-05, CHAT-09 | Large |
| **17-03 — Command file + alias + integration** | `graphify/commands/ask.md`, alias redirect threading through all citations (CHAT-07), zero-LLM architectural test, enrichment-overlay surfacing in findings, full-envelope integration tests. | CHAT-06, CHAT-07 | Medium |

**Why not 4+?** Sessions (D-06) is small enough to fold into Plan 1. Alias threading (CHAT-07) is a ~20-line closure — folds into Plan 3's integration work. P2 REQs (10/11/12) are explicitly deferred in CONTEXT.md.

**Why not 2?** Plan 17-02's validator + composer together are too large (~300 LOC + 8-10 tests) to merge with Plan 17-01's dispatch shell without a wave becoming unreviewable.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `len(tok) <= 2` threshold adequate for false-positive suppression in validator | §5 Citation Validator | Too-lax → fabrications pass; too-strict → valid 3-letter labels (e.g. "API") never cited. Tune in Wave 3 dogfooding. |
| A2 | CONTEXT.md's `alias_redirects` meta key should be used vs existing convention `resolved_from_alias` | §4 Alias Redirect | If planner picks wrong name, downstream consumers / skill renderers break |
| A3 | CONTEXT.md's `target: both` frontmatter field is a spec error — existing commands don't use it | §10 Slash-Command Template | If `target: both` is a NEW convention being introduced in Phase 17, `ask.md` will ship without it |
| A4 | `chars/4` token heuristic per D-09 is correct; existing code uses `chars/3` | §6 Token Cap | Narrative overflow or underflow by ~25% — cosmetic only |
| A5 | `_bidirectional_bfs` `max_visited=1000` is a safe default for chat | §1 / §13 P8 | Too-low: "budget_exhausted" status more often than desired |
| A6 | Re-validate pass bound at 3 iterations prevents pathological loops | §5 / §13 P7 | If a legit narrative needs more iterations, it collapses to no_context |

---

## Open Questions

1. **`meta.alias_redirects` vs `meta.resolved_from_alias`?**
   - What we know: CONTEXT.md D-08 calls the field `alias_redirects`. Every existing core uses `resolved_from_alias` (grep confirms 3 instances in `_run_connect_topics`, `_run_query_graph`, `_run_entity_trace`).
   - What's unclear: Is this a rename across the board, or is chat inventing a new name?
   - Recommendation: Planner flag to user in discussion; default to `resolved_from_alias` (consistency wins) unless user confirms the rename.

2. **`target: both` frontmatter?**
   - What we know: Not present in any of 7 existing command `.md` files.
   - Recommendation: Plan 17-03 planner should confirm with user. If ambiguous, ship without it (matches precedent) and document the gap.

3. **`_get_community` primitive reference**
   - What we know: No standalone `_get_community(subgraph)` function exists. The `communities` dict (from `_communities_from_graph`) is already passed into every core.
   - Recommendation: Plan 17-01 uses the dict-based pattern (§1). CHAT-02's mention of `_get_community` is satisfied by consuming `communities[cid]`.

---

## Environment Availability

Purely code-internal phase — no external tools, no services, no new runtime deps.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | Tests | ✓ | in `[dev]` extras | — |
| networkx | All | ✓ | already pinned | — |
| `collections.deque` | `_CHAT_SESSIONS` | ✓ | stdlib (Python 3.10+) | — |
| `difflib` | Fuzzy suggestions | ✓ | stdlib | — |
| `re` | Validator / follow-up | ✓ | stdlib | — |

No new dependencies required.

---

## Sources

### Primary (HIGH confidence)
- `graphify/serve.py@HEAD` lines 46, 130, 504, 525, 535, 546, 562, 685, 752, 901, 904–1092, 1136, 1212, 1245, 1382, 1564, 1665, 1804–1915, 2016, 2054, 2100, 2118, 2311, 2341, 2484, 2524
- `graphify/mcp_tool_registry.py` lines 214, 231 (Tool definitions)
- `graphify/security.py` line 144 (`validate_graph_path`), `sanitize_label`
- `graphify/commands/context.md`, `connect.md`, `trace.md` (frontmatter reference)
- `tests/test_serve.py` lines 30, 46, 50, 1140, 2226, 2302–2360 (fixtures + envelope assertions)
- `.planning/phases/17-conversational-graph-chat/17-CONTEXT.md` (all 9 decisions)
- `.planning/REQUIREMENTS.md` lines 100–112 (CHAT REQ-IDs)
- `.planning/ROADMAP.md` lines 223–233 (Phase 17 success criteria)

### Secondary (MEDIUM)
- `.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md` (D-12 no-echo precedent)
- `.planning/phases/15-async-background-enrichment/15-CONTEXT.md` (enrichment attributes)

### Tertiary (LOW — training data only)
- None needed; all claims grep-verified against current source.

---

## Metadata

**Confidence breakdown:**
- Primitive signatures: HIGH — grep-verified line by line.
- Envelope idiom: HIGH — identical pattern appears in 8+ existing cores.
- Session history pattern: MEDIUM — derives from CONTEXT.md D-06; no existing session-store pattern in serve.py to mimic (the `_FOCUS_DEBOUNCE_CACHE` is shape-similar but purpose-different).
- Validator false-positive threshold: LOW (assumed) — needs dogfooding tuning.
- Command frontmatter `target: both`: LOW — contradicts current codebase convention.

**Research date:** 2026-04-22
**Valid until:** 2026-05-06 (14 days — serve.py is under active development; re-verify line anchors if not started within window)
