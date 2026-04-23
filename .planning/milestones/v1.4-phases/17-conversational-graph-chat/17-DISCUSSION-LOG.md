# Phase 17: Conversational Graph Chat — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `17-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 17-conversational-graph-chat
**Areas discussed:** Stage 1 architecture, Citation validator, Session history semantics, Narrative packet shape

---

## Stage 1 architecture

### Q1 — How should Stage 1 map an NL query to the primitive sequence?

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic pipeline in serve.py (Recommended) | Keyword/regex intent classifier dispatches a fixed primitive sequence per intent; zero LLM in serve.py | ✓ |
| Agent-supplied plan | `chat(query, session_id, plan)` — skill builds the plan, serve.py executes | |
| Single-primitive dispatch | Classify to exactly one primitive; fails on "connect X and Y" | |
| Hybrid with optional intent_hint | Deterministic pipeline + optional agent override | |

**User's choice:** Deterministic pipeline in serve.py
**Notes:** Resolves the CHAT-02/CHAT-03 tension cleanly; single MCP tool surface per CHAT-01.

### Q2 — How many intent buckets should the Stage 1 classifier support in v1?

| Option | Description | Selected |
|--------|-------------|----------|
| Three core intents (Recommended) | explore / connect / summarize | ✓ |
| Five intents | + compare + trace | |
| Two intents | connect vs explore | |
| One intent, branching on entity count | Single pipeline with BFS/bidirectional switch | |

**User's choice:** Three core intents
**Notes:** Covers ~90% of realistic queries; compare/trace deferred to v1.5.

### Q3 — How should Stage 1 extract candidate entity terms from the NL query?

| Option | Description | Selected |
|--------|-------------|----------|
| Tokenize + stopword filter (Recommended) | Lowercase, split, drop stopwords + intent verbs | ✓ |
| Regex noun-phrase heuristic | Capture quoted / camelCase / snake_case spans verbatim | |
| Pass whole query to _score_nodes | Don't extract; let _score_nodes handle everything | |
| Caller supplies entities | Skill extracts terms; serve.py just consumes | |

**User's choice:** Tokenize + stopword filter
**Notes:** No new deps; relies on `_score_nodes`'s existing partial-match for multi-word labels.

---

## Citation validator

### Q1 — What's the grep-validator rule for catching fabricated node references?

| Option | Description | Selected |
|--------|-------------|----------|
| Label-token match against citation set (Recommended) | Flag tokens that match some real label but aren't cited | ✓ |
| Strict node_id only | Grep for snake_case slugs only; rarely fires | |
| Whitelist-only narrative | Template-only prose, no free text | |
| Hybrid: template spine + label validator | Templates for skeleton, validator for connective tissue | |

**User's choice:** Label-token match against citation set
**Notes:** Bounded false-positive rate; only considers tokens that match real labels.

### Q2 — What does `_run_chat_core` do when the validator rejects the narrative?

| Option | Description | Selected |
|--------|-------------|----------|
| Strip violating sentences, return remainder (Recommended) | Drop sentences with uncited labels; re-validate; empty → no_context | ✓ |
| Hard reject — return empty envelope | Any violation → full empty envelope | |
| Replace uncited tokens with [redacted] | Mask tokens in place | |
| Return with error flag in meta | Emit as-is + `meta.citation_violations` | |

**User's choice:** Strip violating sentences, return remainder
**Notes:** Preserves partial value without ever emitting a fabricated claim.

---

## Session history semantics

### Q1 — Where does session state live, and for how long?

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory dict, 10-turn cap, 30-min TTL (Recommended) | `_SESSIONS: dict[str, deque]`; process-lifetime only | ✓ |
| In-memory, no cap, no TTL | Grows unbounded | |
| Persisted to chat_sessions.json | Disk I/O per turn; survives restart | |
| Stateless — session_id ignored | Rejects CHAT-08 | |

**User's choice:** In-memory dict, 10-turn cap, 30-min TTL
**Notes:** MCP stdio sessions die with the server anyway; disk persistence over-scoped for v1.

### Q2 — What does stored history do for the NEXT chat turn in the same session?

| Option | Description | Selected |
|--------|-------------|----------|
| Seed augmentation on pronoun/follow-up queries (Recommended) | Regex-matched follow-ups prepend prior cited node_ids to seeds | ✓ |
| Always merge prior citations as seeds | Every turn auto-carries context | |
| Store only; never read in Stage 1 | Write-only for this phase | |
| Return prior turn in meta only | Push coherence to the caller | |

**User's choice:** Seed augmentation on pronoun/follow-up queries
**Notes:** Deterministic; handles "and what else?" without bleeding context into unrelated follow-ups.

---

## Narrative packet shape

### Q1 — What exactly does `_run_chat_core` return as the D-02 envelope contents?

| Option | Description | Selected |
|--------|-------------|----------|
| Compact prose in text_body, structured packet in meta (Recommended) | Templated slot-filled sentences + {citations, findings, suggestions} in meta | ✓ |
| JSON packet as text_body, meta holds provenance only | Forces rendering on caller | |
| Empty text_body, everything in meta | Maximally strict; unreadable without renderer | |
| Prose in text_body; no structured packet at all | Simpler but loses P2 hook surface | |

**User's choice:** Compact prose in text_body, structured packet in meta
**Notes:** Matches Phase 18 precedent; dual-usable by callers with or without a renderer.

### Q2 — When the templated prose would exceed 500 tokens, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate text_body at sentence boundary, full packet stays in meta (Recommended) | Drop trailing sentences with `…` marker | ✓ |
| Return "too broad" envelope and abort | Strict cap; no partial answer | |
| Compress by dropping lowest-confidence findings | Requires scoring pass; complexity > value | |
| Raise cap — reinterpret CHAT-09 as advisory | Rejects the REQ | |

**User's choice:** Truncate text_body at sentence boundary, full packet stays in meta
**Notes:** Matches existing MCP-tool subgraph-budget behavior; `meta.findings` remains complete for re-render.

---

## Claude's Discretion

- **Fuzzy suggestion source (CHAT-05):** `difflib.get_close_matches` over god-node + top-community labels, cutoff 0.6. Stdlib only.
- **`/graphify-ask` slash command:** single-shot per invocation; fresh UUID session_id per call. Multi-turn reserved for direct MCP tool usage.
- **Empty-result suggestion template wording:** planner chooses; must NOT echo unmatched query tokens (Pitfall 6 anti-leak).

## Deferred Ideas

- Five-intent taxonomy (compare, trace)
- Spacy/nltk entity extraction
- Persistent session history (disk / SQLite)
- Cross-session chat memory (out-of-scope per ROADMAP)
- Chat-to-argue handoff (CHAT-12 P2, Phase 16 interaction)
- Save-chat-as-vault-note (CHAT-11 P2, Phase 14 interaction)
- Auto-suggest follow-ups from surprising connections (CHAT-10 P2)
- Trigram / full-text index for fuzzy suggestions
