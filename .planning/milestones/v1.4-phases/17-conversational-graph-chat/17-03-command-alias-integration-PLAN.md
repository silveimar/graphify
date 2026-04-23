---
phase: 17
plan: 03
type: execute
wave: 3
depends_on: [17-01, 17-02]
files_modified:
  - graphify/serve.py
  - graphify/commands/ask.md
  - tests/test_serve.py
  - tests/test_commands.py
autonomous: true
requirements: [CHAT-03, CHAT-06, CHAT-07]
requirements_addressed: [CHAT-03, CHAT-06, CHAT-07]
threat_model:
  - id: T-17-05
    category: Information Disclosure (alias leak)
    component: "_run_chat_core alias threading"
    disposition: mitigate
    mitigation: "`_resolve_alias` closure applied to EVERY node_id BEFORE it enters `meta.citations`; `meta.resolved_from_alias` is forward-only — lists canonical_id → [aliases redirected], does not enumerate aliases that WEREN'T redirected (per CONTEXT.md Clarification)"
  - id: T-17-02
    category: Information Disclosure (no_graph echo)
    component: "graphify/commands/ask.md slash renderer"
    disposition: mitigate
    mitigation: "ask.md renders only envelope fields; no_results branch emits generic 'Did you mean…' template sourced from meta.suggestions (which are graph-labels only per Plan 17-02)"
must_haves:
  truths:
    - "Every citation node_id emitted by `_run_chat_core` has been passed through `_resolve_alias` before entering `meta.citations`"
    - "When redirection occurs, `meta.resolved_from_alias` maps canonical_id → list of original aliases"
    - "`graphify/commands/ask.md` exists, has valid frontmatter matching connect.md convention, invokes the `chat` MCP tool"
    - "Zero-LLM architectural test passes — `serve.py` contains no import of anthropic / openai / LLM client"
  artifacts:
    - path: graphify/commands/ask.md
      provides: "/graphify-ask slash command wrapping the chat MCP tool"
      contains: "name: graphify-ask"
    - path: graphify/serve.py
      provides: "`_resolve_alias` closure inside `_run_chat_core`; `meta.resolved_from_alias` populated when redirects occur"
      contains: 'meta["resolved_from_alias"] ='
    - path: tests/test_serve.py
      provides: "test_chat_alias_redirect_canonical, test_serve_makes_zero_llm_calls"
      contains: "def test_chat_alias_redirect_canonical"
    - path: tests/test_commands.py
      provides: "test_ask_md_frontmatter"
      contains: "def test_ask_md_frontmatter"
  key_links:
    - from: "_run_chat_core"
      to: "_resolve_alias closure (pattern copied from _run_connect_topics:1245)"
      via: "maps every node_id BEFORE citation dict construction"
      pattern: "_resolve_alias\\(nid\\)"
    - from: "_run_chat_core"
      to: "meta.resolved_from_alias"
      via: "writes dict[canonical_id, list[original_alias]] at end of core if non-empty"
      pattern: 'meta\\["resolved_from_alias"\\]'
    - from: "graphify/commands/ask.md"
      to: "graphify chat MCP tool"
      via: "slash-command invocation template"
      pattern: "chat"
---

<objective>
Close the three remaining threads of Phase 17:
1. **CHAT-07 alias threading** — plumb `_resolve_alias` through every `node_id` in `_run_chat_core`'s citation list, following the verbatim closure pattern from `_run_connect_topics:1245`. Emit `meta.resolved_from_alias` (NOT `alias_redirects` — per CONTEXT.md clarification).
2. **CHAT-06 slash command** — ship `graphify/commands/ask.md` using the existing `connect.md` frontmatter convention (no `target:` field — per CONTEXT.md clarification).
3. **CHAT-03 zero-LLM architectural test** — grep-based unit test asserting `serve.py` never imports an LLM client.

**Purpose:** Deliver the remaining three REQ-IDs and close the Phase 17 success-criteria list.

**Output:** `chat` citations are canonical-post-dedup; `/graphify-ask` exists as a slash command; zero-LLM invariant is tested structurally.
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
@.planning/phases/17-conversational-graph-chat/17-02-validator-composer-cap-PLAN.md

<!-- Alias redirect origin (D-16) -->
@.planning/phases/10-dedup-merge/10-CONTEXT.md

@graphify/serve.py
@graphify/commands/connect.md
@graphify/commands/context.md
@graphify/commands/trace.md
@tests/test_serve.py

<interfaces>
<!-- Alias closure pattern from _run_connect_topics:1245 (RESEARCH.md §4) — copy VERBATIM -->
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

<!-- Existing convention (6+ hits in serve.py at 1016, 1091, 1276, 1300…): -->
meta["resolved_from_alias"] = _resolved_aliases  # ONLY when non-empty

<!-- connect.md frontmatter convention (CONTEXT.md clarification — NO target: field) -->
---
name: <name>
description: <short desc>
argument-hint: <args>
disable-model-invocation: true
---
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Thread _resolve_alias through _run_chat_core citations + emit meta.resolved_from_alias</name>
  <files>graphify/serve.py, tests/test_serve.py</files>
  <read_first>
    - graphify/serve.py lines 1245-1310 (`_resolve_alias` closure in `_run_connect_topics` — copy verbatim)
    - graphify/serve.py lines 1016, 1091, 1276, 1300 (`resolved_from_alias` usage precedent — 6+ hits)
    - graphify/serve.py current `_run_chat_core` after Plans 17-01/17-02 (citations dict construction is where alias threading lands)
    - .planning/phases/17-conversational-graph-chat/17-CONTEXT.md — Clarifications section (D-08 → `resolved_from_alias`)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md §§ 4, 13 P3 (alias redirect — timing matters; apply BEFORE citations built)
  </read_first>
  <behavior>
    - Given `alias_map = {"alias_nid": "canonical_nid"}` and a visited set containing `"alias_nid"`, every `meta.citations[i].node_id` equals `"canonical_nid"` (never `"alias_nid"`).
    - `meta.resolved_from_alias` contains `{"canonical_nid": ["alias_nid"]}`.
    - Given `alias_map = None` (or empty), `meta.resolved_from_alias` is absent OR is the empty dict `{}`.
    - When no redirection occurs (alias_map non-empty but no visited node matches any alias), `meta.resolved_from_alias == {}`.
  </behavior>
  <action>
**1. Inside `_run_chat_core` (graphify/serve.py)**, near the top of the function BEFORE any citation dict is built, insert the verbatim closure from `_run_connect_topics:1245`:

```python
    # --- Phase 17 CHAT-07 / D-16: alias redirect closure (verbatim copy of _run_connect_topics:1245) ---
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

**2. Apply `_resolve_alias` at 2 points (Pitfall 3 — apply BEFORE citations are built, not after):**

**Point A — right after `_score_nodes`:**
```python
    scored = _score_nodes(G, terms) if terms else []
    seed_ids = [_resolve_alias(nid) for _, nid in scored[:5]]
```

**Point B — citation construction (replace the existing `citations = [...]` from Plan 17-01):**
```python
    citations = [
        {"node_id": _resolve_alias(nid),
         "label": G.nodes[nid].get("label", nid) if nid in G.nodes else nid,
         "source_file": G.nodes[nid].get("source_file", "") if nid in G.nodes else ""}
        for nid in list(visited)[:20]
    ]
    cited_ids_set: set[str] = {c["node_id"] for c in citations}
```

**3. Populate `meta["resolved_from_alias"]` at the very end (replace the empty `{}` placeholder from Plans 17-01 / 17-02):**
```python
    meta = {
        "status": status,
        "intent": intent,
        "citations": citations if status == "ok" else [],
        "findings": [],
        "suggestions": suggestions,
        "session_id": session_id,
        "resolved_from_alias": _resolved_aliases,  # CHAT-07 / T-17-05
    }
```

The invariant `meta["resolved_from_alias"]` is:
- `{}` when no redirect occurred
- `{canonical_id: [original_alias, ...]}` when redirects occurred

Do NOT emit a different key name — the existing convention across 6+ serve.py cores is `resolved_from_alias`. The orchestrator planning context and CONTEXT.md Clarifications both confirm this.

**4. Extend `tests/test_serve.py` with two cases:**

```python
def test_chat_alias_redirect_canonical(_reset_chat_sessions):
    """CHAT-07 / D-16 / T-17-05: node_ids in citations are canonical, not aliases."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    # Pick a real node and invent an alias that maps to it.
    real_nid = next(iter(G.nodes))
    real_label = G.nodes[real_nid].get("label", real_nid)
    alias_map = {f"alias_of_{real_nid}": real_nid}

    # The alias node does NOT exist in G; but scored_nodes may surface it if we seed the query with the alias id directly.
    # Simpler: verify via a direct call where we force visited to include the alias.
    # Use a query that should hit the real node via label.
    # Craft a query containing the label so _score_nodes returns the real node; then force-add the alias via monkeypatch.
    import graphify.serve as _svc
    original_score = _svc._score_nodes
    def _alias_aware_score(G_, terms_):
        base = original_score(G_, terms_)
        # prepend alias tuple so alias appears in seed_ids before resolution
        return [(10.0, f"alias_of_{real_nid}")] + base
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr("graphify.serve._score_nodes", _alias_aware_score)
        response = _run_chat_core(
            G, communities, alias_map,
            {"query": f"tell me about {real_label}"}
        )
    finally:
        monkeypatch.undo()
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    # No citation node_id should equal the alias
    alias_id = f"alias_of_{real_nid}"
    citation_ids = [c["node_id"] for c in meta["citations"]]
    assert alias_id not in citation_ids, "alias leaked through to meta.citations"
    # resolved_from_alias should document the redirect
    assert real_nid in meta["resolved_from_alias"]
    assert alias_id in meta["resolved_from_alias"][real_nid]


def test_chat_no_alias_empty_redirect_map(_reset_chat_sessions):
    """When alias_map has no applicable redirects, meta.resolved_from_alias is empty dict."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(
        G, communities, {}, {"query": "what is extract?"}
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["resolved_from_alias"] == {}
```

Use `pytest.MonkeyPatch()` context manager OR refactor to `monkeypatch` fixture parameter — whichever pattern is already used in the file (grep `def test_chat_intent_connect_calls_bi_bfs` to see the pattern).
  </action>
  <verify>
    <automated>pytest tests/test_serve.py -q -k "chat_alias_redirect_canonical or chat_no_alias_empty_redirect_map"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def _resolve_alias(" graphify/serve.py` returns ≥ 2 hits (Plan 17-03 adds one inside `_run_chat_core`; prior hits from `_run_connect_topics` / `_run_query_graph` remain).
    - `grep -n '_resolved_aliases' graphify/serve.py` shows new hits inside `_run_chat_core` (minimum 2 — declaration + `meta["resolved_from_alias"] = _resolved_aliases`).
    - `grep -n 'meta\["resolved_from_alias"\]' graphify/serve.py` includes a hit inside `_run_chat_core`'s meta construction block.
    - `grep -n "alias_redirects" graphify/serve.py` returns zero hits (per CONTEXT.md Clarification — wrong key name).
    - `pytest tests/test_serve.py::test_chat_alias_redirect_canonical -x` exits 0.
    - `pytest tests/test_serve.py::test_chat_no_alias_empty_redirect_map -x` exits 0.
    - All prior chat tests (Plans 17-01/17-02) still pass: `pytest tests/test_serve.py -q -k chat` green.
  </acceptance_criteria>
  <done>
    Alias closure copied verbatim, applied at `_score_nodes` output and citation-build point; `meta.resolved_from_alias` emitted; two alias tests pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Ship graphify/commands/ask.md + frontmatter test + zero-LLM arch test</name>
  <files>graphify/commands/ask.md, tests/test_commands.py, tests/test_serve.py</files>
  <read_first>
    - graphify/commands/connect.md (verbatim frontmatter convention — name, description, argument-hint, disable-model-invocation: true)
    - graphify/commands/context.md (secondary reference)
    - graphify/commands/trace.md (secondary reference)
    - tests/test_commands.py (if exists — otherwise will be created; grep `ls tests/test_commands.py`)
    - .planning/phases/17-conversational-graph-chat/17-RESEARCH.md § 10 (verbatim ask.md body template)
    - .planning/phases/17-conversational-graph-chat/17-CONTEXT.md Clarifications (no `target:` field)
  </read_first>
  <behavior>
    - `graphify/commands/ask.md` file exists.
    - Frontmatter parses cleanly with the YAML delimiters `---` and contains keys: `name`, `description`, `argument-hint`, `disable-model-invocation` (value `true`).
    - Frontmatter does NOT contain `target:` key (per CONTEXT.md Clarification).
    - Body references the `chat` MCP tool and passes `query: "$ARGUMENTS"`.
    - `test_serve_makes_zero_llm_calls`: reads `graphify/serve.py` source; asserts none of `import anthropic`, `from anthropic`, `import openai`, `from openai`, `from graphify.llm`, `import graphify.llm`, `import langchain`, `from langchain` appear.
  </behavior>
  <action>
**1. Create `graphify/commands/ask.md`** verbatim from RESEARCH.md §10, adapted per CONTEXT.md Clarification (no `target:` field):

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

If `meta.resolved_from_alias` is non-empty, append a small note:
> _Note: some cited IDs were redirected from merged aliases; the canonical IDs shown are the current graph's node IDs._

Keep total output under 500 tokens (the tool already caps narrative; do not expand).
```

**2. Create or extend `tests/test_commands.py`:**

First check if it exists:
```bash
ls tests/test_commands.py 2>/dev/null
```

If it exists, APPEND the frontmatter test. If NOT, create a new file. Note: CLAUDE.md says "one test file per module" — `graphify/commands/` is a directory of command files, not a Python module; a single `tests/test_commands.py` exercising all command frontmatter is the established convention (grep to confirm; if no such file and no precedent, create it).

```python
"""Tests for graphify/commands/*.md slash-command frontmatter."""
from __future__ import annotations
from pathlib import Path
import re


def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path} missing YAML frontmatter"
    block = m.group(1)
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def test_ask_md_frontmatter():
    """CHAT-06: /graphify-ask command file exists with connect.md-style frontmatter."""
    path = Path("graphify/commands/ask.md")
    assert path.exists(), "graphify/commands/ask.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-ask"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    # Per CONTEXT.md Clarification: no `target:` field
    assert "target" not in fm, "ask.md must NOT have a target: field per CONTEXT.md Clarification"
    # Body must reference the chat MCP tool
    body = path.read_text()
    assert "chat" in body, "ask.md body must invoke the chat MCP tool"
    assert "$ARGUMENTS" in body, "ask.md must pass $ARGUMENTS to query"
```

**3. Append the zero-LLM architectural test to `tests/test_serve.py`:**

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

Place it in the chat test cluster (near the other `test_chat_*` cases) for locality — even though its test name doesn't match `chat_*`, the regression it guards is Phase 17's architectural invariant.
  </action>
  <verify>
    <automated>pytest tests/test_commands.py::test_ask_md_frontmatter tests/test_serve.py::test_serve_makes_zero_llm_calls -x</automated>
  </verify>
  <acceptance_criteria>
    - `test -f graphify/commands/ask.md` exits 0.
    - `head -1 graphify/commands/ask.md` prints `---`.
    - `grep -c "^name: graphify-ask$" graphify/commands/ask.md` == 1.
    - `grep -c "^disable-model-invocation: true$" graphify/commands/ask.md` == 1.
    - `grep -c "^target:" graphify/commands/ask.md` == 0 (per CONTEXT.md Clarification).
    - `grep -c "chat" graphify/commands/ask.md` ≥ 1 (body invokes chat tool).
    - `grep -c "\$ARGUMENTS" graphify/commands/ask.md` ≥ 1.
    - `pytest tests/test_commands.py::test_ask_md_frontmatter -x` exits 0.
    - `pytest tests/test_serve.py::test_serve_makes_zero_llm_calls -x` exits 0.
    - `grep -c "def test_serve_makes_zero_llm_calls" tests/test_serve.py` == 1.
    - `pytest tests/ -q` full baseline suite (≥ 1369 tests) passes.
  </acceptance_criteria>
  <done>
    `graphify/commands/ask.md` shipped with correct frontmatter (no `target:`); two new tests pass; zero-LLM invariant structurally enforced.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| dedup writer → `_alias_map` | alias map is written by dedup_report; consumed by every tool core via `_maybe_reload_dedup` |
| `_run_chat_core` → caller | `meta.resolved_from_alias` is forward-only — never enumerates aliases that were NOT redirected |
| `ask.md` renderer → user | renderer uses only `meta` fields; never echoes unmatched query tokens |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-17-05 | Information Disclosure (alias leak) | `_run_chat_core` alias threading | mitigate | `_resolve_alias` applied BEFORE citations built (Pitfall 3 timing); `meta.resolved_from_alias` is forward-only (lists aliases that WERE redirected, not those that WEREN'T); no stderr logging of either canonical or alias IDs |
| T-17-02 | Information Disclosure (no_graph echo) | `ask.md` renderer | mitigate | Static `no_graph` verbatim text; no_results branch renders ONLY `meta.suggestions` (graph-sourced per Plan 17-02); never interpolates user query |
</threat_model>

<verification>
- `pytest tests/ -q` — full baseline suite green (≥ 1369 tests + new Phase 17 tests)
- `pytest tests/test_serve.py -q -k chat` — all chat cases green (Plans 17-01/02/03 combined)
- `pytest tests/test_commands.py::test_ask_md_frontmatter -x` — green
- `pytest tests/test_serve.py::test_serve_makes_zero_llm_calls -x` — green
- `grep -c "alias_redirects" graphify/serve.py` → 0 (wrong key name, confirmed absent)
- `grep -c "resolved_from_alias" graphify/serve.py` → strictly greater than pre-Phase-17 baseline
</verification>

<success_criteria>
- Every citation node_id is canonical-post-dedup; aliases never leak into `meta.citations`
- `meta.resolved_from_alias` populated when redirects occur; empty dict when not
- `graphify/commands/ask.md` ships with `connect.md`-shape frontmatter (no `target:`); invokes `chat` MCP tool
- `test_serve_makes_zero_llm_calls` passes — structural enforcement of CHAT-03 invariant
- All 12 P1 CHAT REQs (CHAT-01..09) covered by at least one passing test across Plans 17-01/02/03
- Full baseline test suite remains green
</success_criteria>

<output>
After completion, create `.planning/phases/17-conversational-graph-chat/17-03-SUMMARY.md`.

**Phase 17 is shipped** when this plan's SUMMARY is committed. Proceed with `/gsd-verify-work` per normal workflow.
</output>
