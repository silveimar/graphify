# Phase 17: Conversational Graph Chat — Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a new MCP tool `chat(query: str, session_id: str | None = None)` on `serve.py` that answers NL questions about the codebase with a **graph-grounded narrative** where every claim traces back to a real node. The pipeline is two-stage and structurally enforced: Stage 1 translates the query into a deterministic sequence of calls against existing traversal primitives (`_score_nodes`, `_bfs`, `_dfs`, `_bidirectional_bfs`, `_get_community`, `_connect_topics`); Stage 2 composes a structured narrative packet from those results. **`serve.py` makes zero LLM calls** — the skill or calling agent renders the final human-facing text. Also ships `/graphify-ask` as a `target: both` command file that wraps the MCP tool.

Scope: new `_run_chat_core` dispatcher + MCP wrapper in `serve.py`; intent classifier + entity-term extractor; citation validator; session history store; templated narrative composition; `graphify/commands/ask.md`; D-16 alias redirect threaded through `meta.citations`. Out of scope: LLM reasoning in serve.py; cross-session memory; save-chat-as-vault-note (CHAT-11 P2); chat→argue handoff (CHAT-12 P2); auto-suggest follow-ups from surprising-connections (CHAT-10 P2 — belongs as a post-v1 enhancement).

Twelve REQ-IDs are scoped: CHAT-01..09 (P1) + CHAT-10..12 (P2).

</domain>

<decisions>
## Implementation Decisions

### Stage 1 — Intent & entity extraction

- **D-01:** **Deterministic pipeline inside `_run_chat_core`.** No LLM, no agent-supplied plan. The core function classifies intent from the query string via keyword/regex rules and dispatches a fixed primitive sequence per intent. This is the only reading of CHAT-02 + CHAT-03 that keeps `serve.py` free of LLM calls while still letting `chat` be a single-shot MCP tool (CHAT-01). Honors D-18 (compose, don't plumb) — no new traversal algorithms.

- **D-02:** **Three intents in v1: `explore`, `connect`, `summarize`.** Pipelines:
  - `explore` (default / fallback) — `_score_nodes(terms) → _bfs(top_seeds, depth=2) → _get_community(subgraph)` when `include_community` signals ("about", "overview") are present.
  - `connect` — triggered by two distinct entity groups + connector verbs (`connect`, `relate`, `between`, `from … to`, `path`). Runs `_score_nodes(A) + _score_nodes(B) → _bidirectional_bfs(A_ids, B_ids, depth=3)`.
  - `summarize` — triggered by "what's in", "overview of", "summarize <module>". Runs `_score_nodes(terms) → _get_community(seed_ids)` — skips BFS expansion.
  Five-intent variants (compare/trace) deferred to v1.5 if real user queries demand them.

- **D-03:** **Entity terms extracted via tokenize + stopword filter.** Lowercase, split on whitespace/punctuation, drop a built-in stopword list that includes English function words AND intent verbs (`what`, `how`, `is`, `the`, `between`, `connect`, `relate`, `show`, `explain`, `tell`, `me`, `about`…). Remaining tokens → `_score_nodes`. Multi-word labels rely on `_score_nodes`'s existing partial-match scoring. No new NLP deps, no spacy.

### Stage 2 — Narrative composition & validation

- **D-04:** **Citation validator is label-token match against the citation set.** Tokenize the composed narrative on word boundaries; for every token, check if it is a substring of any node label in the graph. If yes **and** the owning node_id is not in the turn's citation list → the sentence is flagged as a fabrication. Bounded false-positive rate because we only consider tokens that actually match *some* real label.

- **D-05:** **On validator violation: strip violating sentences, re-validate remainder.** Split narrative on sentence boundaries; drop any sentence containing an uncited label token; re-run validator on the remainder. If non-empty → return as `text_body`. If empty → return the `no_context` envelope (empty `text_body`, templated fuzzy suggestions via CHAT-05, `meta.status = "no_results"`). Preserves partial value without ever emitting a fabricated claim (CHAT-04 mitigation).

### Session history (CHAT-08)

- **D-06:** **Module-level `_SESSIONS: dict[str, deque]` — 10-turn cap, 30-min idle TTL, process-lifetime only.** Each entry stores `{query, citations: [{node_id, label, source_file}], narrative_hash, ts}`. Cap enforced by `deque(maxlen=10)`. TTL enforced lazily on access (next call evicts entries older than 1800s). No disk persistence, no new deps. Acceptable loss on serve.py restart because MCP stdio sessions already die with the server.

- **D-07:** **History feeds Stage 1 via pronoun/follow-up detection.** If the current query matches a follow-up regex — patterns: `^(and|but|what about|tell me more|more|why|how come)\b`, `\bit\b`, `\bthat\b` at sentence start — prepend the prior turn's cited `node_ids` to the extracted entity terms before calling `_score_nodes`. Otherwise history is write-only. Deterministic, no NLU, covers the realistic "and what else?" case.

### Envelope & shape

- **D-08:** **D-02 envelope: prose in `text_body`, structured packet in `meta`.** `text_body` is pre-rendered templated sentences with slot-filled cited labels — readable verbatim by humans and agents without a renderer. `meta` carries `{citations: [...], findings: [...], suggestions: [...], session_id, alias_redirects: [...], intent, status}`. Matches Phase 18's precedent (text_body is real content, not JSON). Callers that want rich rendering re-render from `meta.findings`.

- **D-09:** **500-token cap (CHAT-09) enforced via sentence-boundary truncation.** Estimate tokens via cheap char/4 heuristic (same as other `serve.py` tools). Drop trailing sentences until under cap; append `…` marker to the last kept sentence. `meta.findings` remains complete so callers can re-render the full answer. Matches how existing tools handle subgraph budget.

### Claude's Discretion

Decisions not locked in this phase — planner/executor has flexibility within the patterns below. These were explicitly left to discretion; they're tactical and reversible.

- **Fuzzy suggestion source (CHAT-05).** Default plan: `difflib.get_close_matches(term, candidates, n=3, cutoff=0.6)` where `candidates` = union of god-node labels (top-degree nodes) + top-community member labels. Stdlib only; no new dep. Planner may swap for a trigram index if profiling shows latency issues on large graphs.

- **`/graphify-ask` slash command surface.** Default plan: single-shot per invocation. Each `/graphify-ask <question>` call generates a fresh `session_id` (UUID4) — no cross-invocation history in the slash-command wrapper. The `chat` MCP tool itself still respects `session_id` for agents that DO want multi-turn history. Revisit in v1.5 if user feedback asks for conversational chains in the slash command.

- **Empty-result suggestion template text.** Planner picks the exact wording for "did you mean X, Y?" templates and the no-context message — must not mention unmatched terms back to the caller (Pitfall 6 echo-leak avoidance — do NOT reflect raw query tokens that didn't match any label, since that distinguishes spoofed queries from typoed real queries).

### Folded Todos

No pending todos matched Phase 17 (todo.match-phase returned 0).

### Clarifications (2026-04-22, post-research)

Two points from D-08 were refined against codebase evidence surfaced by the researcher:

- **D-08 correction:** the citation-alias meta key is **`resolved_from_alias`** (matches existing convention in `serve.py` at lines 1016, 1091, 1276, 1300 and 6+ other tools) — NOT `alias_redirects` as originally written. Every `meta` returned by `_run_chat_core` must use `meta["resolved_from_alias"] = {canonical_id: [original_alias, ...]}`.
- **CHAT-06 correction:** `graphify/commands/ask.md` uses the **existing command-file frontmatter convention** (same shape as `connect.md` / `trace.md` — `description:` + `disable-model-invocation: true` + `allowed-tools:` list). The `target: both` field from the earlier CONTEXT.md draft is dropped — no existing command file has it and introducing it unilaterally would create a second convention.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Envelope & MCP contract (D-02, carried forward)
- `.planning/milestones/v1.3-phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md` — origin of the D-02 envelope shape (`text_body + "\n---GRAPHIFY-META---\n" + json.dumps(meta)`). `chat` MUST match.
- `.planning/phases/13-agent-capability-manifest/13-CONTEXT.md` §§ D-02 — capability_describe uses the same envelope; set the precedent for hash-extended meta.
- `.planning/phases/15-async-background-enrichment/15-CONTEXT.md` §§ D-04, D-05 — enrichment overlay shape; the description/pattern/community fields on nodes come from this file and are a Stage 2 input (findings can cite enrichment-derived attrs).
- `.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md` §§ D-07, D-09, D-12 — silent-ignore on path violations, `text_body = ""` for no-context, no echo of unmatched input. Pattern is load-bearing for CHAT-05's fuzzy-suggestion template (see Claude's Discretion note on echo-leak avoidance).

### Alias redirect (D-16)
- `.planning/ROADMAP.md` §§ "Milestone-level invariants" — D-16 alias redirect requirement for every public ID.
- `graphify/serve.py` §§ `_resolve_alias` — canonical resolver. CHAT-07 requires threading this through every citation before it leaves `_run_chat_core`.

### Existing primitives (D-18 compose-don't-plumb)
- `graphify/serve.py:535 _score_nodes(G, terms)` — term-to-node_id ranking. Stage 1 entity resolver.
- `graphify/serve.py:546 _bfs(G, start_nodes, depth)` — bounded BFS. `explore` intent.
- `graphify/serve.py:562 _bidirectional_bfs(...)` — two-seed path-find. `connect` intent.
- `graphify/serve.py:685 _dfs(G, start_nodes, depth)` — reserved; not currently dispatched by any intent but kept in the primitive whitelist per CHAT-02.
- `graphify/serve.py:1212 _run_connect_topics(...)` — reference implementation for "two named entities" composition; Stage 1's `connect` pipeline mirrors this shape.
- `graphify/serve.py:1804 _run_get_focus_context_core(...)` — reference for D-02 envelope composition + silent-ignore + budget clamp pattern; `_run_chat_core` follows the same skeleton.
- `graphify/serve.py:130 _load_enrichment_overlay(G, out_dir)` — merges Phase 15 enrichment onto graph at read time. `chat` benefits because node descriptions / community summaries are already attributes on G by the time `_run_chat_core` runs — no new loading code required.
- `graphify/serve.py:504 _load_graph(...)` — standard graph loader. Mock-safe; do not call inside `_load_enrichment_overlay`'s post-load path (Phase 15 D-08 invariant).

### Security
- `graphify/security.py::validate_graph_path(path, base=project_root)` — path confinement. Chat doesn't take file paths directly, but if `query` ever gets routed through `focus_hint` (CHAT-01's signature allows a future extension), this gate applies.

### Command surface
- `graphify/commands/context.md`, `graphify/commands/connect.md`, `graphify/commands/trace.md` — existing `target: both` slash-command precedents. `/graphify-ask` follows the same frontmatter shape (CHAT-06).

### Requirements spine
- `.planning/REQUIREMENTS.md` §§ "Conversational Graph Chat (Phase 17)" (lines 100–112) — all 12 CHAT REQ-IDs.
- `.planning/ROADMAP.md` §§ "Phase 17" — goal, dependencies, 5 success criteria (narrative + citations, uncited-phrase rejection, fuzzy suggestions, zero-LLM architectural test, alias redirect).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **All six traversal primitives** already exist in `graphify/serve.py` (lines 535, 546, 562, 685, 1212, plus `_get_community` helper). Zero new graph algorithms needed.
- **D-02 envelope composition** is implemented in ≥6 MCP tool cores; `_run_chat_core` is a parallel addition, not a new pattern (`QUERY_GRAPH_META_SENTINEL`, `_subgraph_to_text`, budget clamp).
- **Enrichment overlay** (`_load_enrichment_overlay`, shipped Phase 15) already attaches `description`, `patterns`, `community_summary` attrs to nodes. Stage 2 findings can surface these as citations without any new I/O.
- **Alias resolver** (`_resolve_alias`) is the canonical D-16 plumb; call it on every `node_id` in `meta.citations` before returning.
- **Template slash-command files** under `graphify/commands/` (`connect.md`, `context.md`, `trace.md`, etc.) — `/graphify-ask` follows the same `target: both` frontmatter shape.

### Established Patterns
- **Pure dispatch cores + MCP wrapper** — every MCP tool has `_run_<name>_core(...)` that returns the envelope string, plus a runtime wrapper at the bottom. `_run_chat_core` follows the same shape, making it testable without the `mcp` package.
- **Budget clamp** — `max(50, min(budget, 100000))`. `chat` may not take `budget` directly (CHAT-09 fixes the narrative cap at 500 tokens), but the structured `meta.findings` inherits the standard clamp for any subgraph payloads.
- **Silent-ignore on input violations** — caught `ValueError` maps to empty-envelope return, never re-raised. Applies to malformed `session_id` inputs too.

### Integration Points
- **`serve.py` tool registry** — add `chat` to the MCP tool list (same pattern as `get_focus_context` / `capability_describe`).
- **`tests/test_serve.py`** — already exercises D-02 envelopes. Add `test_chat_*` cases following the existing shape.
- **`graphify/commands/ask.md`** — new file; mirror `connect.md`'s frontmatter and body.

</code_context>

<specifics>
## Specific Ideas

- **Intent verbs in stopword list** (D-03): confirm the list includes `what, how, is, the, a, an, between, connect, relate, show, explain, tell, me, about, of, in, for, with, and, or, but, to, from, across, among` — planner may expand. Keep it ASCII-only; don't bring locale into stopwording.
- **Follow-up regex anchors** (D-07): match at *start* of query (`^`) or after a leading connector, not anywhere in the query. Otherwise "describe the component that logger calls" triggers on embedded "that".
- **Sentence splitter** (D-05, D-09): stdlib only — a lightweight regex split on `[.!?]+\s+` is sufficient for templated prose we control. Don't pull in nltk/spacy.
- **No-context template must not echo** (see CHAT-05 Claude's Discretion): when fuzzy suggestions fire, return only candidate labels that DO exist in the graph; never echo unmatched query tokens back. Matches Phase 18 D-12 anti-leak stance.

</specifics>

<deferred>
## Deferred Ideas

- **Five-intent taxonomy** (`compare`, `trace` on top of `explore` / `connect` / `summarize`) — revisit in v1.5 if real queries justify the extra surface.
- **Spacy/nltk-backed entity extraction** — rejected for v1 (adds heavy dep). Revisit only if tokenize+stopword precision fails in dogfooding.
- **Persistent session history (disk or SQLite)** — rejected for v1. Process-lifetime + TTL is acceptable because MCP stdio sessions die with the server anyway.
- **Cross-session chat memory** — explicitly out of scope per ROADMAP "Explicit out-of-scope" list (privacy default).
- **Chat-to-argue handoff (CHAT-12 P2)** — Phase 16 interaction; deferred to that phase's context.
- **Save-chat-as-vault-note (CHAT-11 P2)** — requires `propose_vault_note` round-trip; belongs with the Phase 14 Obsidian commands work.
- **Auto-suggest follow-ups from surprising connections (CHAT-10 P2)** — hook exists via `meta.suggestions`, but the surprising-connections analyzer integration is a separable enhancement.
- **Trigram / full-text index for fuzzy suggestions** — `difflib` default is fine; swap only if profiling on large graphs (>10k nodes) shows latency issues.

### Reviewed Todos (not folded)

None — `todo.match-phase` returned 0 matches for Phase 17.

</deferred>

---

*Phase: 17-conversational-graph-chat*
*Context gathered: 2026-04-22*
