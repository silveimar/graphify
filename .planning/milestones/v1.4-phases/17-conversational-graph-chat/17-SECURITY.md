---
phase: 17
slug: conversational-graph-chat
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-22
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| MCP stdio (agent → server) | External agent invokes the `chat` tool via stdio transport | `query: str`, optional `session_id: str` — untrusted user input |
| Graph store (disk → memory) | `graphify-out/graph.json` + `dedup_report.json` loaded by `_reload_if_stale` | Node labels, source_files, community ids, alias map |
| Chat envelope (server → agent) | D-02 envelope returned via `QUERY_GRAPH_META_SENTINEL` | `text_body` (narrative), `meta.citations`, `meta.suggestions`, `meta.resolved_from_alias`, `meta.session_id` |
| Session store (in-process) | `_CHAT_SESSIONS: dict[str, deque]` — process-lifetime, no persistence | Prior-turn citations, narrative hash, monotonic `ts` |
| Slash command (Claude Code → MCP) | `/graphify-ask <question>` frontmatter invocation | `$ARGUMENTS` threaded verbatim into `query` |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-17-01 | Spoofing (fabricated citation) | composer output — `_validate_citations` in `graphify/serve.py` | mitigate | Sentence-level validator drops sentences whose label-tokens resolve to node_ids not in `cited_ids`; bounded re-validate loop (`_CHAT_VALIDATOR_MAX_PASSES = 3`); empty result → `status = "no_results"` + empty `text_body`. Verified at `graphify/serve.py:1019-1042` and applied at `graphify/serve.py:1325-1329`. Tests: `test_chat_validator_strips_uncited` (test_serve.py:2869). | closed |
| T-17-02 | Information Disclosure (query echo) | `_fuzzy_suggest` + no_results branch in `graphify/serve.py`; `graphify/commands/ask.md` renderer | mitigate | `_fuzzy_suggest` builds candidate pool from graph labels only (top-degree god-surrogates ∪ top-3 communities' first-5 members) and final-filters via `[s for s in suggestions if s in candidates]` so output cannot contain user tokens. `no_results` branch sets `narrative = ""` and `text_body = ""` without interpolating `query_raw`. `ask.md` renderer consumes `meta.suggestions` and forbids echoing unmatched query terms. Verified at `graphify/serve.py:1044-1073`, `1333-1337`, and `graphify/commands/ask.md:20-22`. Tests: `test_chat_suggestions_no_echo` (test_serve.py:2918), `test_chat_no_match_returns_suggestions` (test_serve.py:2899). | closed |
| T-17-03 | Spoofing / DoS | `_CHAT_SESSIONS` dict + `_tool_chat` / `_run_chat_core` in `graphify/serve.py` | mitigate | `_CHAT_SESSION_ID_MAX_LEN = 128` cap (serve.py:915); non-str or over-cap `session_id` coerced to `None` via silent-ignore (serve.py:1223-1224); no stderr logging of session_ids inside chat code path (grep of chat region 900-2020 → zero `print(..., file=sys.stderr)` hits referencing session/alias). TTL eviction uses `time.monotonic()` (WR-01, serve.py:1228). Tests: `test_chat_session_isolation` (test_serve.py:2838), `test_chat_ttl_eviction` (test_serve.py:2852). | closed |
| T-17-04 | DoS (unbounded payload) | `text_body` / `_truncate_to_token_cap` in `graphify/serve.py` | mitigate | `_truncate_to_token_cap(narrative, cap=500)` performs sentence-boundary truncation at 500 tokens × 4 chars/tok with `…` marker (serve.py:1075-1101). WR-02 word-boundary fallback for over-long first sentence. Applied at serve.py:1339. Tests: `test_chat_narrative_under_cap` (test_serve.py:2934), `test_chat_truncate_helper_unit` (test_serve.py:2959). | closed |
| T-17-05 | Information Disclosure (alias leak) | `_run_chat_core` alias threading in `graphify/serve.py` | mitigate | `_resolve_alias` closure applied to seed_ids BEFORE citation dicts are built (serve.py:1257) and again during citation construction (serve.py:1300-1310); `meta.resolved_from_alias` is forward-only (maps canonical → [aliases redirected], never enumerates unresolved aliases). WR-03 cycle guard on transitive resolution (serve.py:1234-1250). No stderr logging of canonical or alias IDs in chat region. Tests: `test_chat_alias_redirect_canonical` (test_serve.py:2974), `test_chat_no_alias_empty_redirect_map` (test_serve.py:3007). | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Threat Flags (from executor SUMMARY.md files)

- 17-01 SUMMARY `## Threat Flags`: None — surface matches plan's threat model (T-17-03 mitigation confirmed in-place).
- 17-02 SUMMARY `## Threat Flags`: None — T-17-01/T-17-02/T-17-04 mitigations confirmed in-place.
- 17-03 SUMMARY `## Threat Flags`: None — T-17-05 and T-17-02 mitigations confirmed in-place.

No unregistered flags.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-22 | 5 | 5 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-22
