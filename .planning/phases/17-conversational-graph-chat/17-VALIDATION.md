---
phase: 17
slug: conversational-graph-chat
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `17-RESEARCH.md` § 14 "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥ 7 (already in `[dev]` extras via `pyproject.toml`) |
| **Config file** | `pyproject.toml` (no `pytest.ini`) |
| **Quick run command** | `pytest tests/test_serve.py -q -k chat` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick ~3s / full ~45s (baseline 1370 tests post Phase 15) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_serve.py -q -k chat`
- **After every plan wave:** Run `pytest tests/test_serve.py -q`
- **Before `/gsd-verify-work`:** Full suite `pytest tests/ -q` must be green
- **Max feedback latency:** 15 seconds (per-wave merge)

---

## Per-Task Verification Map

*Task IDs are placeholders until the planner assigns them. The Req → Test mapping below is load-bearing; planner MUST reference it when writing `acceptance_criteria` blocks.*

| Req ID | Plan (expected) | Wave | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|--------|-----------------|------|-----------------|-----------|-------------------|-------------|--------|
| CHAT-01 | 17-01 | 1 | `chat` tool registered in MCP registry | unit | `pytest tests/test_serve.py::test_chat_tool_registered -x` | ❌ W0 | ⬜ pending |
| CHAT-02 | 17-01 | 1 | Intent dispatch invokes correct primitive (explore/connect/summarize) | unit (spy/patch) | `pytest tests/test_serve.py::test_chat_intent_connect_calls_bi_bfs -x` | ❌ W0 | ⬜ pending |
| CHAT-03 | 17-03 | 3 | Zero-LLM architectural test — grep serve.py for LLM-client imports | unit (grep-based) | `pytest tests/test_serve.py::test_serve_makes_zero_llm_calls -x` | ❌ W0 | ⬜ pending |
| CHAT-04 | 17-02 | 2 | Uncited phrase rejected — strip violating sentence, re-validate | unit | `pytest tests/test_serve.py::test_chat_validator_strips_uncited -x` | ❌ W0 | ⬜ pending |
| CHAT-05 | 17-02 | 2 | Fuzzy suggestions returned on empty-match queries | unit | `pytest tests/test_serve.py::test_chat_no_match_returns_suggestions -x` | ❌ W0 | ⬜ pending |
| CHAT-05 | 17-02 | 2 | No echo of unmatched tokens in suggestion template (anti-leak) | unit | `pytest tests/test_serve.py::test_chat_suggestions_no_echo -x` | ❌ W0 | ⬜ pending |
| CHAT-06 | 17-03 | 3 | `graphify/commands/ask.md` exists with valid frontmatter | unit | `pytest tests/test_commands.py::test_ask_md_frontmatter -x` (extend if file exists, else new) | ❌ W0 | ⬜ pending |
| CHAT-07 | 17-03 | 3 | Alias redirect threaded — `meta.resolved_from_alias` populated | unit | `pytest tests/test_serve.py::test_chat_alias_redirect_canonical -x` | ❌ W0 | ⬜ pending |
| CHAT-08 | 17-01 | 1 | Session scoping + deque cap (10) + 30-min TTL eviction | unit | `pytest tests/test_serve.py::test_chat_session_isolation -x` + `::test_chat_ttl_eviction -x` | ❌ W0 | ⬜ pending |
| CHAT-09 | 17-02 | 2 | 500-token narrative cap enforced; overflow truncates at sentence boundary with `…` | unit | `pytest tests/test_serve.py::test_chat_narrative_under_cap -x` | ❌ W0 | ⬜ pending |
| CHAT-09 | 17-01 | 1 | D-02 envelope structural (`text_body + SENTINEL + json.dumps(meta)`) | unit | `pytest tests/test_serve.py::test_chat_envelope_ok -x` | ❌ W0 | ⬜ pending |

*P2 REQs (CHAT-10/11/12) are explicitly deferred per ROADMAP — no validation rows required.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Extend `tests/test_serve.py` — all `test_chat_*` cases live in the existing module (no new test file per CLAUDE.md convention: "One test file per module").
- [ ] Session-isolation fixture — either class-scoped or explicit `_CHAT_SESSIONS.clear()` between tests.
- [ ] Graph fixture reuse — `_make_graph()` helper at `tests/test_serve.py:50` is the canonical fixture. Extend, don't replace.
- [ ] No framework install needed — pytest already present via `pyproject.toml` `[dev]` extras.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end MCP roundtrip with real `mcp` server | CHAT-01 surface | The MCP stdio runtime is not exercised by unit tests (cores are called directly) | Start `graphify serve` in stdio mode; send a `chat` tool-call from a test client or Claude Code session; confirm envelope parses and citations resolve |
| `/graphify-ask` slash command invocation in a real Claude Code session | CHAT-06 surface | Slash-command discovery happens inside the host runtime, not in graphify's test suite | In a Claude Code session with graphify installed, run `/graphify-ask "what does _score_nodes do?"`; confirm narrative arrives with citations |

*All other phase behaviors have automated unit coverage.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify commands or are listed under Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (new `test_chat_*` cases + session-isolation fixture)
- [ ] No watch-mode flags in CI commands
- [ ] Feedback latency < 15s per wave
- [ ] `nyquist_compliant: true` set in frontmatter after final pass

**Approval:** pending
