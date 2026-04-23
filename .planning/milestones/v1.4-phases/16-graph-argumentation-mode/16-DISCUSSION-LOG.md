# Phase 16: Graph Argumentation Mode — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 16-graph-argumentation-mode
**Areas discussed:** Persona roster + scope→subgraph, Round structure + stop, Fabrication handler, Transcript + verdict

---

## Persona roster + scope→subgraph mapping

### Q1: Persona roster

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Phase 9 lenses | security / architecture / complexity / onboarding — same 4 lenses as analyze tournament; focus bullets exist at skill.md:1433; max reuse of Phase 9 blind-label harness; fixed roster | ✓ |
| Fixed 3-role debate | Advocate / Skeptic / Synthesizer — classic SPAR-Kit triad; 3×6=18 LLM calls; debate-native framing; requires new focus bullets | |
| User-selectable lens menu | ARGUE-10 takes --lenses flag (subset of Phase 9 lenses); default=all 4; mirrors `/graphify analyze for security` | |

**User's choice:** Reuse Phase 9 lenses (Recommended)
**Notes:** Maximum substrate reuse; deterministic default roster; CLI `--lenses` deferred to v1.4.x backlog.

### Q2: Default scope mapping

| Option | Description | Selected |
|--------|-------------|----------|
| topic → BFS ego | Tokenize + _score_nodes → top-k seeds → nx.ego_graph(depth=2); reuses Phase 17 CHAT-02 pattern; budget caps node count | ✓ |
| topic → dominant community | Resolve seeds + return majority community via _get_community; broader context but weaker for cross-community topics | |
| topic → connect_topics bridge | Split topic into two clusters (connectors like "vs", "and"); _connect_topics bridge; only suits comparison queries | |

**User's choice:** topic → BFS ego (Recommended)
**Notes:** Uniform default for arbitrary decision queries; `scope="community"` and `scope="subgraph"` remain available as power-user paths.

---

## Round structure + stop condition

### Q1: Round shape

| Option | Description | Selected |
|--------|-------------|----------|
| All 4 personas per round | Synchronous barrier; each round = 4 parallel LLM calls; worst case 4×6=24 calls; simple blind-harness wiring (shuffle per round) | ✓ |
| One persona per turn | Rotating turn order; 6 cap = 6 total turns; cheapest (6 calls) but asymmetric persona exposure | |
| Tournament per round | Phase 9 shape (incumbent/adversary/synthesis + 3 judges) chained across rounds; ≤36 calls; expensive; loses multi-voice feel | |

**User's choice:** All 4 personas per round (Recommended)

### Q2: Stop condition

| Option | Description | Selected |
|--------|-------------|----------|
| Cite-overlap convergence + cap | Jaccard ≥0.7×2 rounds → consensus; <0.2×3 rounds → dissent; else cap=6 → inconclusive; mechanical detection, no synthesis persona | ✓ |
| Always run to cap=6 | No early stop; verdict computed post-hoc from final overlap; most predictable cost | |
| Judge-panel verdict per round | Phase 9-style judges vote (continue/consensus/dissent/inconclusive); adds judge calls; persona-scored verdict | |

**User's choice:** Cite-overlap convergence + cap (Recommended)
**Notes:** Consensus is *detected*, not *produced* — honors ARGUE-08 "no consensus-forcing" literally. Jaccard thresholds are starting values; Planner may adjust ±0.1 after blind-harness regression test.

---

## Fabrication handler

### Q1: Validator site

| Option | Description | Selected |
|--------|-------------|----------|
| Substrate: argue.py | Pure `validate_turn(turn, G) -> list[str]`; zero LLM; unit-testable; skill.md imports and calls it after each turn | ✓ |
| Skill-side only | Validation entirely in skill.md prose; no Python helper; harder to test in blind-harness regression suite | |

**User's choice:** Substrate: argue.py (Recommended)

### Q2: Violation action

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-reject + re-prompt once | Drop the turn; re-prompt with invalid node_ids + reminder; max 1 retry; second failure → `{claim:'[NO VALID CLAIM]', cites:[]}` abstention, does not halt debate | ✓ |
| Strip invalid cites, keep claim | Remove fabricated node_ids from cites list; keep claim if ≥1 valid cite remains; no re-prompt; risk of label-level fabrication leak | |
| Hard-reject + retry twice | Same as recommended but max 2 retries; worst-case ≈+8 extra LLM calls across the debate | |

**User's choice:** Hard-reject + re-prompt once (Recommended)
**Notes:** Abstentions are dropped from Jaccard numerator/denominator for that round — they don't spuriously count as disagreement.

---

## Transcript + verdict

### Q1: Transcript shape

| Option | Description | Selected |
|--------|-------------|----------|
| Per-round chronological | `## Round 1/2/...` with 4 persona sub-sections per round; `## Verdict` at end with cite-overlap trajectory; convergence visible | ✓ |
| Per-lens sections (Phase 9 shape) | `## Security / Architecture / ...` with that persona's claims across all rounds; loses round-over-round debate flow | |
| Hybrid: Verdict up top | `## Verdict` first (bottom-line), then compact round×persona transcript table | |

**User's choice:** Per-round chronological (Recommended)

### Q2: Cite style

| Option | Description | Selected |
|--------|-------------|----------|
| Inline `[node_id:label]` | Cites anchored at claim site; greppable for audit; matches Phase 17 validator granularity; label sanitized via security.py | ✓ |
| Footnote refs `[^1]` | Markdown footnote style with numbered list at section end; lower inline noise but harder to spot-check fabrications | |
| Trailing cite block per claim | Claim text clean, followed by `cites: [n_a, n_b]` on next line; compromise; drift risk if author edits one without the other | |

**User's choice:** Inline `[node_id:label]` (Recommended)

---

## Claude's Discretion

- Exact persona prompt wording (reused from Phase 9 lens focus bullets with debate-framing tweak).
- Final Jaccard threshold values (0.7 / 0.2 are starting points; validated via Phase 9 regression suite).
- `GRAPH_ARGUMENT.md` overwrite vs timestamped filename (default: overwrite).
- SPAR-Kit INTERROGATE step (ARGUE-11 P2) — deferred.

## Deferred Ideas

- ARGUE-11 INTERROGATE step, ARGUE-12 persona memory, ARGUE-13 conflict-density scoring (all P2).
- `--lenses` CLI subset flag.
- Timestamped argument history (`GRAPH_ARGUMENT-<slug>.md`).
- Five-persona / custom-roster debates.
- `chat → argue` handoff (cross-phase; lives in Phase 17 backlog).
