# Phase 16: Graph Argumentation Mode — Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

User poses a decision-shaped question about the codebase. Graphify runs a structurally-enforced multi-perspective debate grounded in the knowledge graph, producing `graphify-out/GRAPH_ARGUMENT.md` — an advisory-only transcript where every persona claim cites a real `node_id` from the graph. Zero LLM calls in the Python substrate; all LLM orchestration in `skill.md`. Phase 16 never invokes Phase 17 `chat` (Pitfall 18 recursion guard).

In scope: `graphify/argue.py` substrate (populate, ArgumentPackage, PerspectiveSeed, NodeCitation, validate_turn), `argue_topic` MCP tool, skill.md SPAR-Kit orchestration, `/graphify-argue` command file, Phase 9 blind-label harness reuse.

Out of scope: auto-applying argument outputs to code or graph; cross-session argument memory; `chat → argue` composition; Phase 16 → Phase 17 chaining.

</domain>

<decisions>
## Implementation Decisions

### Persona Roster (ARGUE-01, ARGUE-02)
- **D-01:** **Reuse Phase 9's four lenses verbatim as PerspectiveSeeds: `security`, `architecture`, `complexity`, `onboarding`.** Each lens has existing focus bullets at `graphify/skill.md:1433`. No new persona authoring. Fixed roster — no per-call variation in v1. `ArgumentPackage.perspectives` is always `[PerspectiveSeed(lens=L) for L in [security, architecture, complexity, onboarding]]`. CLI flag `--lenses` (subset) deferred to v1.4.x backlog; default is all 4.

### Scope → Subgraph Mapping (ARGUE-01 `scope`, `budget`)
- **D-02:** **Default `scope="topic"` resolves via tokenize + `_score_nodes` + `nx.ego_graph(depth=2)`.** Tokenize topic string (reuse Phase 17's CHAT-02 stopword + tokenizer pattern — `_run_chat_core` extraction in `serve.py`), call `_score_nodes` to find top-k seeds, then build the evidence subgraph as the union of depth-2 ego-graphs over the seeds. `budget` caps total nodes in the returned subgraph (same clamp as existing MCP tools: `max(50, min(budget, 100000))`).
- **D-03:** **`scope="subgraph"` accepts explicit `node_ids`; `scope="community"` accepts a single `community_id` → `_get_community(community_id)`.** These are power-user entry points; the default path (`topic`) is what `/graphify-argue <question>` drives.

### Round Structure (ARGUE-08, ARGUE-03)
- **D-04:** **All 4 personas per round, synchronous barrier.** Each round = 4 LLM calls (one per persona, in parallel). Round N+1 sees all round-N validated claims. Worst case: 4 personas × 6 rounds = 24 LLM calls — parity with existing `/graphify analyze` tournament budget users already accept. Temperature ≤ 0.4 enforced at prompt-call level in skill.md.
- **D-05:** **Blind-label harness reshuffled per round.** Shuffle A/B/C/D persona labels at the start of each round (not per turn — simpler wiring, still preserves the Phase 9 bias guarantee because judges never see stable persona→label mapping across rounds). Reuses the same shuffling code pattern as `skill.md:1511` (tournament judge rotation).

### Stop Condition (ARGUE-08 `dissent`/`inconclusive` valid)
- **D-06:** **Cite-overlap convergence + hard cap=6.** After each round, compute Jaccard overlap of cited `node_id` sets across the 4 personas. Halt early with:
  - `verdict="consensus"` when overlap ≥ 0.7 for 2 consecutive rounds
  - `verdict="dissent"` when overlap < 0.2 for 3 consecutive rounds
  - `verdict="inconclusive"` when cap=6 reached without either condition firing
- **D-07:** **No synthesis step that invents agreement.** Consensus is *detected* from independent cite overlap, never produced by a "synthesizer persona" that merges claims. This literal-reads ARGUE-08's "no consensus-forcing" constraint.

### Fabrication Handler (ARGUE-05)
- **D-08:** **Validator is a pure function in `argue.py`: `validate_turn(turn: dict, G: nx.Graph) -> list[str]`.** Returns list of `node_id`s in `turn["cites"]` that are not in `G.nodes`. Zero LLM calls (honors ARGUE-03). Unit-testable without skill. Skill.md imports and calls it after each persona turn.
- **D-09:** **On violation: hard-reject the turn, re-prompt the same persona once** with the list of invalid node_ids and a "cite only from the provided subgraph" reminder. Max 1 retry. If the retry is still invalid → the persona's turn for that round becomes `{claim: "[NO VALID CLAIM]", cites: []}` (recorded as abstention in the transcript). An abstention does NOT halt the debate and does NOT count toward early-stop overlap (abstentions are dropped from the Jaccard numerator/denominator for that round).
- **D-10:** **Validator operates on the `cites` list, NOT on claim prose.** Unlike Phase 17's narrative-level label-token check (which strips sentences), Phase 16's `{claim, cites:[...]}` schema makes the atomic unit explicit — a claim either has valid cites or it doesn't. No partial stripping.

### Transcript Format (ARGUE-09)
- **D-11:** **Per-round chronological layout.** `## Round 1`, `## Round 2`, … with 4 persona sub-sections per round (`### Security`, `### Architecture`, `### Complexity`, `### Onboarding`). Each persona sub-section contains that persona's bulleted claim(s) for the round with inline cites.
- **D-12:** **Final `## Verdict` section at the end** carries: `verdict` field (`consensus | dissent | inconclusive`), the per-round cite-overlap Jaccard trajectory (e.g., `0.15 → 0.28 → 0.55 → 0.78 → 0.82`), the advisory disclaimer ("This transcript is advisory only — no code or graph mutations result from this run"), and the full list of cited node_ids with labels.
- **D-13:** **Inline cite style `[node_id:label]`.** Example: "The auth layer couples to logger setup [n_logger_setup:LoggerSetup] and token store [n_token_store:TokenStore]." Greppable, readable verbatim, fabrication-auditable at the claim site, and matches Phase 17's validator granularity. Alias redirects (D-16) apply before the cite is rendered — `[canonical_id:label]` always uses the canonical id.

### Envelope & MCP Contract (inherited from Phase 17 D-02, ARGUE-04)
- **D-14:** **`argue_topic` returns a D-02 envelope.** `text_body` = a human-readable summary (verdict + cite-overlap trajectory + path to `GRAPH_ARGUMENT.md`). `meta` = `{verdict, rounds_run, argument_package: <serialized ArgumentPackage>, citations: [...], resolved_from_alias: {...}, output_path: "graphify-out/GRAPH_ARGUMENT.md"}`. Budget clamp = existing `max(50, min(budget, 100000))`.
- **D-15:** **`composable_from: []` in the manifest for `argue_topic` (ARGUE-07).** Manifest generator (Phase 13) must emit this exact value — future Wave B regen passes must not overwrite it. Planner owns adding a manifest-level test that asserts `argue_topic.composable_from == []`. This is the recursion guard.
- **D-16:** **Alias redirects threaded through every citation.** Call `_resolve_alias(node_id)` on every cite in every persona turn before writing to transcript or returning in `meta.citations`. Include `meta.resolved_from_alias = {canonical_id: [original_alias, ...]}` matching the Phase 17 convention (NOT `alias_redirects` — that was a draft miss).

### Claude's Discretion
- **Focus-bullet wording for each lens persona.** Planner reuses Phase 9's lens focus bullets verbatim (`skill.md:1433`) with minor prompt-framing changes to shift from "analyze and output" to "argue a position on THIS question citing THIS subgraph." Exact prose is planner's call.
- **Jaccard threshold tuning.** Thresholds 0.7 (consensus) and 0.2 (dissent) are the starting values from D-06. Planner may propose ±0.1 adjustments if the blind-harness regression test (ARGUE-06 SC4) shows they trigger too eagerly or too rarely on the Phase 9 bias suite. Lock the final values before shipping.
- **Output-file overwrite behavior for `GRAPH_ARGUMENT.md`.** Default plan: overwrite on each `/graphify-argue` invocation (matches how `GRAPH_ANALYSIS.md` behaves). Planner may swap to timestamped filenames (`GRAPH_ARGUMENT-<topic-slug>.md`) if UAT says users want argument history preserved.
- **SPAR-Kit INTERROGATE step (ARGUE-11 P2).** Deferred to v1.4.x backlog — not planned in this phase. If activated, it inserts between round N and round N+1 as an optional persona cross-examination turn (+40% synthesis quality per protocol docs).

### Folded Todos
None — no pending todos matched Phase 16 scope at discussion time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 16 requirements spine
- `.planning/REQUIREMENTS.md` §Graph Argumentation — ARGUE-01..ARGUE-13 — defines `argue.py`, `ArgumentPackage`, `argue_topic`, blind-harness reuse, fabrication validator, round cap, SPAR-Kit steps, output contract.
- `.planning/ROADMAP.md` §Phase 16 — goal, cross-phase rule (no Phase 17 invocation), success criteria, manifest `composable_from: []`.

### Phase 17 precedents (inherit-or-mirror)
- `.planning/phases/17-conversational-graph-chat/17-CONTEXT.md` D-02, D-08, D-16 — D-02 envelope shape, `meta.resolved_from_alias` key name (NOT `alias_redirects`), alias-resolution threading pattern.
- `.planning/phases/17-conversational-graph-chat/17-01-core-dispatch-sessions-PLAN.md` — Entity/term tokenizer + `_score_nodes` seed pattern reused for D-02 topic→subgraph mapping.
- `.planning/phases/17-conversational-graph-chat/17-03-command-alias-integration-PLAN.md` — `graphify/commands/ask.md` frontmatter shape; `/graphify-argue` command file mirrors it (`description:`, `disable-model-invocation: true`, `allowed-tools:` list — NO `target:` field).

### Phase 9 blind-label harness (ARGUE-06 reuse)
- `graphify/skill.md:1388` — Blind-label anti-pattern note ("Never label candidates as incumbent/adversary/synthesis in judge prompts").
- `graphify/skill.md:1511` — Shuffled A/B/AB-to-Analysis rotation per judge; exact shuffling pattern Phase 16 reuses per-round (D-05).
- `graphify/skill.md:1433` — Lens focus bullet substitution for security/architecture/complexity/onboarding; same text fed to Phase 16 personas with prompt-framing tweak.
- `graphify/analyze.py:501` `render_analysis_context` — Serializes graph structure into a prompt-safe text block; reused by skill.md to build the `{GRAPH_CONTEXT}` block fed to each persona.

### Existing primitives (D-18 compose-don't-plumb)
- `graphify/serve.py` `_bidirectional_bfs`, `_score_nodes`, `_get_community`, `_connect_topics`, `_resolve_alias` — all scope-resolution and citation paths reuse these; zero new traversal algorithms.
- `graphify/serve.py` `QUERY_GRAPH_META_SENTINEL`, `_subgraph_to_text`, budget clamp — D-02 envelope composition pattern for `argue_topic`.
- `graphify/serve.py` enrichment overlay (`_load_enrichment_overlay`, Phase 15) — persona claims may surface `description`/`patterns`/`community_summary` attrs as citable evidence without new I/O.

### Security
- `graphify/security.py` `validate_graph_path`, `sanitize_label`, `validate_graph_path(base=project_root)` — every emitted label in transcript must pass `sanitize_label`; output path must confine to `graphify-out/` (Phase 18 sentinel inherited).

### Manifest & capability surface
- `graphify/capability_manifest.schema.json` — `composable_from` field schema (Phase 13 Wave A).
- `graphify/capability_tool_meta.yaml` — add `argue_topic` entry with `composable_from: []` explicit.
- Phase 13 manifest regeneration (Wave B) — `argue_topic` manifest entry survives regen; planner adds a regression test.

### Pitfalls index
- `.planning/PITFALLS.md` Pitfall 4 (fabrication) — validator MUST reject unknown cites (ARGUE-05).
- `.planning/PITFALLS.md` Pitfall 6 (echo-leak) — fuzzy suggestion / no-context templates must not echo unmatched tokens (inherited from Phase 17; applies to any argue_topic no-result pathway).
- `.planning/PITFALLS.md` Pitfall 18 (recursion) — `composable_from: []` enforcement (ARGUE-07, D-15).
- `.planning/PITFALLS.md` Pitfall 20 (snapshot double-nesting) — output-path sentinel guard inherited from Phase 18.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **All graph traversal primitives** already live in `graphify/serve.py` — `_score_nodes`, `_bidirectional_bfs`, `_get_community`, `_connect_topics`, `_resolve_alias`. Zero new algorithms needed.
- **Phase 9 tournament harness in `skill.md:1388-1600`** — blind A/B labeling, shuffled assignment per judge, Borda scoring. Phase 16 reuses the shuffling machinery verbatim; the "judge" role is replaced by the mechanical cite-overlap detector (D-06) rather than an LLM panel.
- **`graphify/analyze.py::render_analysis_context` (line 501)** — already serializes graph structure into prompt-safe text blocks for lens agents. Reused verbatim to build the `{EVIDENCE_SUBGRAPH}` block each persona receives.
- **D-02 envelope composition pattern** — implemented in ≥6 MCP tool cores in `serve.py` (`QUERY_GRAPH_META_SENTINEL`, budget clamp). `argue_topic` is a parallel addition, not a new pattern.
- **Command-file template** — `graphify/commands/connect.md`, `ask.md` (Phase 17). `/graphify-argue` mirrors these.

### Established Patterns
- **Pure substrate + skill orchestration split** — Phase 9 precedent (`analyze.py` helpers + skill.md tournament loop). Phase 16 follows the same split: `argue.py` = substrate (populate, ArgumentPackage, PerspectiveSeed, NodeCitation, validate_turn, compute_overlap); `skill.md` = LLM rounds + retry + verdict emission.
- **Pure dispatch cores + MCP wrapper** — `_run_argue_topic_core(...)` returns the envelope; thin `@tool` wrapper at the bottom of `serve.py` registers it. Testable without `mcp` package.
- **Silent-ignore on input violations** — `ValueError` on malformed topic/scope → empty envelope, never re-raised.
- **Budget clamp** — `max(50, min(budget, 100000))` for subgraph node count.

### Integration Points
- **`serve.py` tool registry** — register `argue_topic` alongside `chat` / `get_focus_context` / `capability_describe`.
- **`tests/test_serve.py`** — add `test_argue_*` cases; follow Phase 17 shape (envelope assertions, alias threading, D-02 meta keys).
- **`tests/test_argue.py`** (new) — pure-substrate unit tests for `populate`, `validate_turn`, cite-overlap Jaccard computation. No LLM, no `mcp` import.
- **`graphify/commands/argue.md`** — new command file; mirror `ask.md` frontmatter.
- **Phase 13 manifest** — `argue_topic` entry with `composable_from: []`; regen-safe assertion lives in `tests/test_capability_manifest.py`.
- **`graphify/capability_tool_meta.yaml`** — authoritative source for manifest generator input.

</code_context>

<specifics>
## Specific Ideas

- **Lens focus bullets** reused from `skill.md:1433` verbatim; prompt-framing changes from "analyze and output" to "argue a position on the user's question, citing only `node_id`s from the provided subgraph."
- **Jaccard starting thresholds** are 0.7 (consensus, 2 consecutive rounds) and 0.2 (dissent, 3 consecutive rounds). Planner validates with Phase 9 regression suite before locking.
- **Cite format `[node_id:label]`** — label sanitized via `security.py::sanitize_label` before emission.
- **Alias meta key is `resolved_from_alias`** (canonical convention, matches `serve.py` lines 1016, 1091, 1276, 1300) — NOT `alias_redirects`.
- **Command file frontmatter** mirrors `ask.md`: `description:`, `disable-model-invocation: true`, `allowed-tools:` list — no `target:` field.
- **Temperature ≤ 0.4** enforced at every LLM call in skill.md persona prompts.
- **`argue_topic` must NOT call `chat`** — manifest `composable_from: []` + regression test in `tests/test_capability_manifest.py`.

</specifics>

<deferred>
## Deferred Ideas

- **SPAR-Kit INTERROGATE step (ARGUE-11 P2)** — optional cross-examination turn between rounds. Defer to v1.4.x backlog; re-enable via `--interrogate` flag when activated.
- **Persona memory across rounds (ARGUE-12 P2)** — personas retain their own prior claims for consistency. Substrate work fits in `PerspectiveSeed`; defer scoring/enforcement to backlog.
- **Clash/rumble/domain intensity scoring (ARGUE-13 P2)** — conflict-density annotations on transcript. Defer to backlog; no impact on v1 verdict engine.
- **User-selectable lens subset (`--lenses` CLI flag)** — mentioned in presentation but rejected for v1 to keep the default deterministic. Easy to add in v1.4.x if dogfooding calls for it.
- **Timestamped `GRAPH_ARGUMENT-<topic-slug>.md` output** — default v1 is single-file overwrite (matches `GRAPH_ANALYSIS.md`). Revisit if UAT wants argument history preserved.
- **Five-persona or custom-roster debates** — rejected for v1; fixed 4 lenses keep the blind-harness wiring trivial.
- **Chat-to-argue handoff (CHAT-12, cross-phase)** — lives in Phase 17's backlog, not here. Would let `chat` suggest `/graphify-argue` for decision-shaped queries, but direct invocation between the two tools remains prohibited by `composable_from: []`.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 16 scope at discussion time.

</deferred>

---

*Phase: 16-graph-argumentation-mode*
*Context gathered: 2026-04-22*
