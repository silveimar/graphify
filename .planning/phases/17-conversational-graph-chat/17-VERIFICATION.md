---
phase: 17-conversational-graph-chat
verified: 2026-04-22T21:55:00Z
status: passed
score: 5/5 success criteria verified; CHAT-01..09 (P1) delivered; CHAT-10/11/12 (P2) correctly deferred
overrides_applied: 0
re_verification: null
test_count: 1384
test_pass_rate: 1384/1384
chat_tests: 13 (12 test_chat_* + test_serve_makes_zero_llm_calls) + test_ask_md_frontmatter
---

# Phase 17: Conversational Graph Chat — Verification Report

**Phase Goal:** User asks a natural-language question about the codebase and receives a graph-grounded narrative answer where every claim traces back to a real node — no fabricated entities, no hallucinated connections.

**Verified:** 2026-04-22T21:55:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `/graphify-ask "..."` returns narrative + `meta.citations: [{node_id, label, source_file}]` resolving claims to real nodes | VERIFIED | `graphify/commands/ask.md` exists (29 lines) delegating to `chat` MCP tool; `_run_chat_core` (serve.py:1190) builds `citations` dict with node_id/label/source_file from `G.nodes[nid]` at serve.py:1276-1284; `test_chat_envelope_ok` (tests/test_serve.py:2809) asserts shape |
| 2 | Post-process grep finds no uncited node IDs/labels — uncited phrases rejected before response leaves `_run_chat` | VERIFIED | `_validate_citations` (serve.py:1019) drops sentences containing label-tokens owned by nodes absent from `cited_ids`; bounded at `_CHAT_VALIDATOR_MAX_PASSES=3` (serve.py:994); `test_chat_validator_strips_uncited` (tests/test_serve.py:2869) pins behavior |
| 3 | Entity not in graph returns templated fuzzy suggestions; handler never fabricates node names | VERIFIED | `_fuzzy_suggest` (serve.py:1044) draws candidates from top-20-degree + top-3-communities' top-5 members using `difflib.get_close_matches(cutoff=0.6, k=3)`; final filter restricts to candidate pool (T-17-02 anti-echo); `test_chat_no_match_returns_suggestions` + `test_chat_suggestions_no_echo` (tests/test_serve.py:2899, 2918) pin behavior |
| 4 | Architectural test asserts `serve.py` makes zero LLM calls | VERIFIED | `test_serve_makes_zero_llm_calls` (tests/test_serve.py:3019) greps serve.py source for forbidden imports; live grep confirms: `grep -cE "^(import\|from)\s+(anthropic\|openai\|langchain\|litellm\|graphify\.llm)" graphify/serve.py` → 0 hits |
| 5 | D-16 alias redirect threaded through every citation — merged nodes resolve to canonical IDs | VERIFIED | `_resolve_alias` closure (serve.py:1227-1234) applied at seed construction (L1243) and citation construction (L1277); `meta.resolved_from_alias` populated via `_resolved_aliases` accumulator (serve.py:1224); `test_chat_alias_redirect_canonical` + `test_chat_no_alias_empty_redirect_map` (tests/test_serve.py:2974, 3007) pin behavior |

**Score:** 5/5 ROADMAP success criteria verified.

### REQ-ID Coverage (P1: CHAT-01..09)

| REQ | Status | Evidence |
|-----|--------|----------|
| CHAT-01 | DELIVERED | `chat` MCP tool registered at `graphify/mcp_tool_registry.py:214` (`name="chat"`), dispatched at `serve.py:2951` (`"chat": _tool_chat`); wrapper at `serve.py:2743`; two-stage pipeline `_run_chat_core` at `serve.py:1190`. Test: `test_chat_tool_registered` (tests/test_serve.py:2792) |
| CHAT-02 | DELIVERED | Stage-1 dispatch calls `_score_nodes`, `_bfs`, `_bidirectional_bfs`, and `_get_community`-equivalent community lookup per intent (serve.py:1242-1272). `_dfs` remains in primitive whitelist per CHAT-02 but is not currently dispatched (documented in CONTEXT.md). Test: `test_chat_intent_connect_calls_bi_bfs` (tests/test_serve.py:2823) |
| CHAT-03 | DELIVERED | Zero LLM imports (`anthropic`, `openai`, `langchain`, `litellm`, `graphify.llm`) — verified by `test_serve_makes_zero_llm_calls` (tests/test_serve.py:3019) AND confirmed by live source grep (0 hits). Composer is pure template slot-fill at `_compose_{explore,connect,summarize}_narrative` (serve.py:1105, 1134, 1153) |
| CHAT-04 | DELIVERED | `_validate_citations` (serve.py:1019) enforces citation-grounding via label-token index (`_build_label_token_index`, serve.py:1007); bounded re-validate loop at 3 passes (`_CHAT_VALIDATOR_MAX_PASSES=3`, serve.py:994). Test: `test_chat_validator_strips_uncited` (tests/test_serve.py:2869) |
| CHAT-05 | DELIVERED | `_fuzzy_suggest` (serve.py:1044) with candidate-pool-restricted output (T-17-02 anti-echo). Emits `status=no_results` with `text_body=""` when no match. Tests: `test_chat_no_match_returns_suggestions`, `test_chat_suggestions_no_echo` (tests/test_serve.py:2899, 2918) |
| CHAT-06 | DELIVERED | `graphify/commands/ask.md` (29 lines) with correct frontmatter: `name: graphify-ask`, `description:`, `argument-hint:`, `disable-model-invocation: true` — matches `connect.md`/`trace.md` convention. No `target:` field per CONTEXT.md Clarification. Test: `test_ask_md_frontmatter` (tests/test_commands.py:195) |
| CHAT-07 | DELIVERED | `_resolve_alias` closure threaded at TWO points — seed construction (serve.py:1243) and citation construction (serve.py:1277). `meta.resolved_from_alias` emitted as populated accumulator (serve.py:1314). Uses canonical `resolved_from_alias` key (0 hits for wrong `alias_redirects` key). Tests: `test_chat_alias_redirect_canonical`, `test_chat_no_alias_empty_redirect_map` (tests/test_serve.py:2974, 3007) |
| CHAT-08 | DELIVERED | `_CHAT_SESSIONS: dict[str, deque]` (serve.py:912) with `maxlen=10` (`_CHAT_SESSION_MAXLEN`, serve.py:914); TTL=1800s (`_CHAT_SESSION_TTL_SECONDS`, serve.py:913); lazy eviction via `_chat_evict_stale` (serve.py:944) called on every invocation. Session-id cap at 128 chars + silent-ignore on malformed (T-17-03). Tests: `test_chat_session_isolation`, `test_chat_ttl_eviction` (tests/test_serve.py:2838, 2852) |
| CHAT-09 | DELIVERED | `_CHAT_NARRATIVE_TOKEN_CAP=500` (serve.py:993); `_truncate_to_token_cap` (serve.py:1075) does sentence-boundary truncation via `_SENTENCE_RE` with ellipsis marker. D-02 envelope `text_body + SENTINEL + json.dumps(meta)` on every return path. Tests: `test_chat_narrative_under_cap`, `test_chat_truncate_helper_unit`, `test_chat_envelope_ok` (tests/test_serve.py:2934, 2959, 2809) |

### P2 REQ-ID Coverage (CHAT-10/11/12) — Correctly Deferred

| REQ | Status | Note |
|-----|--------|------|
| CHAT-10 | DEFERRED (P2) | Auto-suggest follow-ups from surprising-connections — `meta.suggestions` hook exists but the surprising-connections integration is a separable enhancement per CONTEXT.md `<deferred>`. ROADMAP marks `[ ]` unchecked as expected. |
| CHAT-11 | DEFERRED (P2) | Save-chat-as-vault-note via `propose_vault_note` round-trip — requires Phase 14 Obsidian commands work. |
| CHAT-12 | DEFERRED (P2) | Chat-to-argue handoff — Phase 16 interaction. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/serve.py::_run_chat_core` | Pure-dispatch core | VERIFIED | 4-arg signature `(G, communities, alias_map, arguments)` at L1190; D-02 envelope on every return path |
| `graphify/serve.py::_tool_chat` | MCP wrapper | VERIFIED | Closure inside `serve()` at L2743 |
| `graphify/mcp_tool_registry.py` | Registry entry | VERIFIED | `types.Tool(name="chat", ...)` at L214 |
| `graphify/commands/ask.md` | Slash command | VERIFIED | 29 lines, correct frontmatter convention |
| `tests/test_serve.py` (test_chat_*) | Chat tests | VERIFIED | 12 `test_chat_*` tests + `test_serve_makes_zero_llm_calls` |
| `tests/test_commands.py::test_ask_md_frontmatter` | Frontmatter test | VERIFIED | L195 |
| `server.json` `_meta.manifest_content_hash` | Refreshed for new tool | VERIFIED | Updated to `ce1d730e…`; `test_validate_cli_zero` passes |

### Key Link Verification (Data Flow)

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_tool_chat` | `_run_chat_core` | Direct call after `_reload_if_stale` | WIRED | serve.py:2743+ |
| `chat` tool → MCP registry | `build_mcp_tools()` | `types.Tool(name="chat", ...)` at mcp_tool_registry.py:214 | WIRED | Verified by `test_chat_tool_registered` |
| Query → intent → primitives | `_classify_intent` → `_score_nodes`/`_bfs`/`_bidirectional_bfs`/community lookup | serve.py:1237-1272 | WIRED | Verified by `test_chat_intent_connect_calls_bi_bfs` |
| Traversal → citations | `visited` set → `_resolve_alias` → citation dict | serve.py:1276-1284 | WIRED | Canonical-post-alias IDs verified by `test_chat_alias_redirect_canonical` |
| Citations → validator → cap | `_validate_citations` → `_truncate_to_token_cap` → `text_body` | serve.py:1295-1305 | WIRED | Verified by `test_chat_validator_strips_uncited`, `test_chat_narrative_under_cap` |
| `text_body + SENTINEL + meta` | D-02 envelope | `QUERY_GRAPH_META_SENTINEL + json.dumps(meta)` | WIRED | Matches Phase 09.2 precedent |
| Session history → follow-up terms | `_augment_terms_from_history` → prior citations prepend | serve.py:972-987 | WIRED | Verified by `test_chat_session_isolation` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `pytest tests/ -q` | `1384 passed, 2 warnings in 42.81s` | PASS |
| Zero LLM imports in serve.py | `grep -cE "^(import\|from)\s+(anthropic\|openai\|langchain\|litellm\|graphify\.llm)" graphify/serve.py` | `0` | PASS |
| Chat tool registered | `grep -n 'name="chat"' graphify/mcp_tool_registry.py` | `214:            name="chat",` | PASS |
| Dispatch wired | `grep -n '"chat":' graphify/serve.py` | `2951:        "chat": _tool_chat,` | PASS |
| `resolved_from_alias` used (not wrong `alias_redirects`) | `grep -c "alias_redirects" graphify/serve.py` vs. `grep -c "resolved_from_alias" graphify/serve.py` | 0 vs. 15 | PASS |
| `_CHAT_NARRATIVE_TOKEN_CAP` = 500 | `grep -nE "_CHAT_NARRATIVE_TOKEN_CAP\s*=\s*500"` | `993` | PASS |
| `_CHAT_VALIDATOR_MAX_PASSES` bounded | `grep -c _CHAT_VALIDATOR_MAX_PASSES` | 2 (def + loop) | PASS |
| `ask.md` exists | `test -f graphify/commands/ask.md` | exists | PASS |

### Requirements Coverage

All 9 P1 REQs (CHAT-01..09) have at least one automated test pinning behavior. 3 P2 REQs (CHAT-10..12) correctly deferred per ROADMAP and CONTEXT.md `<deferred>` section.

### Anti-Patterns Found

None blocking. Review surfaced 4 non-blocking warnings (WR-01..WR-04) in 17-REVIEW.md — all logged, none violate the phase goal:

- **WR-01** (wall-clock TTL): Edge case only affects sleep/resume on dev laptops; not a goal regression. Informational.
- **WR-02** (truncate-fallback mid-sentence cut): Only fires when a single sentence exceeds 2000 chars; composer templates are short-sentence; no contract violation for shipped tests.
- **WR-03** (single-hop alias resolution): Speculative; requires a malformed dedup_report.json with chained entries. No such artifact exists. Not a current-state goal failure.
- **WR-04** (citations with nodes absent from `G.nodes`): Guarded by fallback; worst case is `source_file=""` — the grep-based validator does not fabricate claims. No goal-level failure.

Two stale docstrings (IN-01, IN-02) reference the "Stage 1 shell — stubbed" language after Plan 17-02 filled the stubs. Cosmetic only — does not affect behavior or the phase goal.

### Human Verification Required

None. All phase behaviors have automated unit coverage. 17-VALIDATION.md identifies two manual-only verifications (end-to-end MCP roundtrip and live `/graphify-ask` slash-command in a Claude Code session), but these test the host runtime surface, not graphify's code — and are documented as expected manual verifications in the validation plan, not gaps.

### Gaps Summary

**No gaps blocking goal achievement.** The phase delivers:

1. A deterministic `chat(query, session_id)` MCP tool that answers NL questions with graph-grounded narratives.
2. Zero LLM calls in `serve.py` — structurally enforced by `test_serve_makes_zero_llm_calls`.
3. Citation grounding with label-token validator + bounded re-validate loop.
4. Fuzzy fallback with anti-echo guard.
5. Canonical-alias threading via `_resolve_alias` at both seed and citation points.
6. Session store with bounded memory (deque maxlen + TTL eviction).
7. 500-token sentence-boundary cap.
8. `/graphify-ask` slash command using the established command-file convention.

All 5 ROADMAP success criteria verified with concrete file:line evidence and passing tests. 1384/1384 tests green.

**Recommendation:** Ready to close Phase 17. Proceed to next milestone-order phase (Phase 16 per build order `12→18→13A→15→17→16→14→13B+SEED-002`). Consider filing the 4 non-blocking review warnings (WR-01..WR-04) as v1.4.x backlog items.

---

_Verified: 2026-04-22T21:55:00Z_
_Verifier: Claude (gsd-verifier)_
