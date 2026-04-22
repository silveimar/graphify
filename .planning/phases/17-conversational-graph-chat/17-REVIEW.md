---
phase: 17-conversational-graph-chat
reviewed: 2026-04-22T21:46:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - graphify/serve.py
  - graphify/mcp_tool_registry.py
  - graphify/commands/ask.md
  - tests/test_serve.py
  - tests/test_commands.py
  - server.json
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-04-22T21:46:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 17 (Conversational Graph Chat) wires a deterministic, zero-LLM `chat` MCP
tool into `serve.py`, backed by a session store, intent classifier, narrative
composer, citation validator (D-04/D-05), fuzzy-suggestion fallback, alias
threading (CHAT-07/D-16), 500-token cap (D-09), and the `/graphify-ask` slash
command.

**Key invariants are upheld:**
- **CHAT-03 zero-LLM**: verified — no `anthropic`, `openai`, `langchain`,
  `litellm`, or `graphify.llm` imports anywhere in `serve.py` (regression test
  `test_serve_makes_zero_llm_calls` pins this).
- **Citation validator convergence**: bounded at `_CHAT_VALIDATOR_MAX_PASSES = 3`
  with early break on `not dropped or not kept` — cannot run unbounded.
- **Session TTL**: `_chat_evict_stale` runs on every `_run_chat_core` call and
  drops sessions whose newest turn exceeds `_CHAT_SESSION_TTL_SECONDS` (1800 s).
  Combined with `deque(maxlen=_CHAT_SESSION_MAXLEN=10)`, per-session memory is
  bounded; total sessions grow only for the TTL window.
- **500-token cap**: `_truncate_to_token_cap` uses `_split_sentences` (sentence
  boundaries via `_SENTENCE_RE`) and only mid-sentence-truncates when a single
  sentence exceeds the char cap.

Findings below document a handful of correctness and robustness issues plus
style/maintenance items — none are critical or security-relevant.

## Warnings

### WR-01: TTL eviction uses wall clock; jumps backwards silently evict healthy sessions

**File:** `graphify/serve.py:944-950`
**Issue:** `_chat_evict_stale` compares `now - turns[-1]["ts"]` where `now` and
`ts` both come from `time.time()`. If the system clock jumps *backwards*
(NTP slew, VM suspend/resume), `now - ts` becomes negative and eviction is
skipped — benign. However, if the clock jumps *forward* by > TTL (common after
laptop sleep/resume on macOS dev boxes, or in containers with skewed host
clocks), every active session is evicted on the next call even though no real
idle time has passed. Because session writes also stamp `ts = now` from the same
clock, the user's very next turn silently loses its conversational context.
**Fix:** Use `time.monotonic()` for the session store — it is not affected by
clock adjustments and is the correct primitive for elapsed-time checks:
```python
now = time.monotonic()   # in _run_chat_core + _chat_evict_stale
turn = {..., "ts": now}  # keep symmetric
```
A wall-clock timestamp (for display) can be kept as a separate `"created_at"`
field if ever needed.

### WR-02: `_truncate_to_token_cap` can mid-sentence-truncate even when sentence-split would work

**File:** `graphify/serve.py:1075-1092`
**Issue:** When the very first sentence is longer than `char_cap` (2000 chars),
the loop exits with `out == []` and falls through to a hard character slice:
`narrative[:char_cap].rstrip() + "…"`. The docstring says "sentence-boundary
truncation at 500 tokens" but this branch violates that contract mid-sentence.
For Phase 17 this is unlikely to fire because composer templates produce short
sentences, but `_compose_summarize_narrative` surfaces user-authored
`community_summary` content (via `_first_enrichment_sentence`), which could
legitimately contain one very long sentence.
**Fix:** When `out == []`, prefer a word-boundary cut over a raw character cut:
```python
if not out:
    head = sentences[0] if sentences else narrative
    # word-boundary trim
    trimmed = head[:char_cap].rsplit(" ", 1)[0].rstrip(".!?,; ")
    return trimmed + "…"
```
Also consider making the mid-sentence path explicit in the docstring so future
callers are not surprised.

### WR-03: `_resolved_aliases` keyed by canonical can double-resolve when canonical is itself a key in alias_map

**File:** `graphify/serve.py:1227-1234`
**Issue:** `_resolve_alias` does a single-hop lookup:
```python
canonical = _effective_alias_map.get(node_id)
if canonical and canonical != node_id: ...
```
`_load_dedup_report` returns `{eliminated_id: canonical_id}` pairs directly
without transitive-closure compression. If `dedup_report.json` ever contains
chained entries (`{"a": "b", "b": "c"}` — possible when two dedup runs are
concatenated or when the writer does not close transitively), `_resolve_alias`
returns `"b"` instead of `"c"`, so citations point at an intermediate alias that
may not even exist in `G.nodes`. The envelope will then carry `label=nid`
(fallback) and `source_file=""`, producing a broken citation the validator
cannot catch (its label-token index is built from `G.nodes`).
**Fix:** Either (a) trust the dedup writer to produce closed maps and add a
loud `validate` step on load, or (b) resolve transitively with a cycle guard:
```python
def _resolve_alias(node_id: str) -> str:
    seen = set()
    current = node_id
    while current in _effective_alias_map and current not in seen:
        seen.add(current)
        nxt = _effective_alias_map[current]
        if nxt == current:
            break
        current = nxt
    if current != node_id:
        _resolved_aliases.setdefault(current, []).append(node_id)
    return current
```
Option (b) is cheap and defensive.

### WR-04: Citations list can contain nodes absent from `G.nodes`; validator silently ignores them

**File:** `graphify/serve.py:1276-1284`
**Issue:** The citation list comprehension guards every field with
`if nid in G.nodes else ...` fallback:
```python
"label": G.nodes[nid].get("label", nid) if nid in G.nodes else nid,
"source_file": G.nodes[nid].get("source_file", "") if nid in G.nodes else "",
```
This means a citation referring to a node *not* in the current graph is emitted
with `label == nid` and empty `source_file`. This can happen when (i)
`_bidirectional_bfs` returns visited ids that include alias ids later resolved
to canonical ids not present in `G.nodes`, or (ii) WR-03's single-hop alias
bug lands. The `_run_chat_core` contract says "every claim cites a real node"
(mcp_tool_registry.py:217), but the emitted envelope can contradict that
contract with a synthetic citation that has no `source_file`.
**Fix:** Filter citations to real graph nodes before emit:
```python
citations = [
    {"node_id": nid, "label": G.nodes[nid].get("label", nid),
     "source_file": G.nodes[nid].get("source_file", "")}
    for nid in (_resolve_alias(n) for n in list(visited)[:20])
    if nid in G.nodes
]
```
If citations shrinks to zero after filtering, downgrade `status` to
`no_results` so the `/graphify-ask` template renders the fuzzy fallback.

## Info

### IN-01: Stale docstring in `_run_chat_core` — "Stage 1 shell — stubbed"

**File:** `graphify/serve.py:1196-1200`
**Issue:** The docstring says "Stage 1 shell — narrative composition and
citation validation are stubbed here (text_body=""). Plan 17-02 wires the real
composer + validator + cap." Plan 17-02 has already been merged (per memory
entry "Phase 17 Stage-2 Narrative Helpers Inserted", 2026-04-22 4:32p) and the
composer/validator/cap are all live in this function.
**Fix:** Drop the stub reference:
```python
"""Phase 17: deterministic chat tool. Zero LLM. D-02 envelope.

Composes a templated narrative per intent (explore/connect/summarize),
validates citations against the graph label index (D-04/D-05), falls
back to fuzzy suggestions on no-match (CHAT-05), and caps at 500 tokens.
"""
```

### IN-02: Similar stale "Stage 1 shell" reference in `_tool_chat`

**File:** `graphify/serve.py:2744-2748`
**Issue:** `_tool_chat.__doc__` also says "Stage 1 shell ... Plan 17-02 wires
the real narrative composer..." — same staleness as IN-01.
**Fix:** Update to reflect the shipped feature surface.

### IN-03: `_build_label_token_index(G)` rebuilds on every call, O(nodes·avg_label_tokens)

**File:** `graphify/serve.py:1009-1017` (called from `_run_chat_core:1297`)
**Issue:** The label token index is rebuilt from scratch on every chat turn.
For typical graphifyy runs (a few thousand nodes) this is fast, but it is
noticeably redundant given `G` is already bound at module scope in `serve()`.
Performance is out of v1 scope, but this also means the index does not pick up
a graph reload from `_reload_if_stale` unless rebuilt — which it fortunately is,
because it is local. Log note only; no fix required. If someone later memoizes
this via `functools.lru_cache` keyed on `id(G)`, they must remember to bust the
cache on reload.

### IN-04: `_FOLLOWUP_RE` matches `more` but not `more about` correctly when followed by punctuation

**File:** `graphify/serve.py:940`
**Issue:** `_FOLLOWUP_RE = re.compile(r"^(and|but|what about|tell me more|more|why|how come)\b", re.IGNORECASE)`. The alternation puts `tell me more` before `more`, but Python regex alternation is left-to-right only within the `^` anchor — both match, so this is fine. However, `what about` as a follow-up trigger also overlaps with `_SUMMARIZE_TRIGGERS_RE`'s "what's in" path and with `_EXPLORE_COMMUNITY_HINTS_RE`'s "about" hint. The *intent* classifier still runs *after* `_augment_terms_from_history`, so a follow-up like `what about extract?` first pulls prior citations (correct), then reclassifies as "explore" (community hint triggers), which is fine for current tests. Note for future maintainers: the three regex sets are not mutually exclusive, and order dependence lives in `_classify_intent`.
**Fix:** None required — document the order dependence in a brief comment:
```python
# NOTE: intent regexes are not mutually exclusive; classification is
# order-sensitive (summarize > connect > explore). Any new trigger must be
# ordered accordingly.
```

### IN-05: `test_chat_narrative_under_cap` uses `G.nodes["n1"]` which assumes fixture shape

**File:** `tests/test_serve.py:2914`
**Issue:** The test hard-codes `G.nodes["n1"]` to pull a sample label. If
`_make_graph` ever changes its default node naming (e.g. to match real
tree-sitter ids), the test breaks with `KeyError`, not an assertion message.
**Fix:** Use `next(iter(G.nodes))` or pick the highest-degree node explicitly,
matching the pattern used in `test_chat_validator_strips_uncited`.

---

_Reviewed: 2026-04-22T21:46:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
