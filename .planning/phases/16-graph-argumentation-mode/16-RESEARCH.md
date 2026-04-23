---
phase: 16
slug: graph-argumentation-mode
status: research-complete
researched: 2026-04-22
confidence: HIGH
---

# Phase 16: Graph Argumentation Mode — Research

**Researched:** 2026-04-22
**Domain:** Debate orchestration substrate / multi-persona argumentation grounded in knowledge graph
**Confidence:** HIGH

---

## Summary

Phase 16 adds a SPAR-Kit-style multi-persona debate substrate to graphify. The user poses a
decision-shaped question; graphify builds an evidence subgraph, seeds four fixed lenses
(security / architecture / complexity / onboarding from Phase 9), runs up to 6 rounds of
structured LLM debate inside `skill.md`, and writes `graphify-out/GRAPH_ARGUMENT.md` — an
advisory-only transcript where every persona claim cites a verified `node_id` from the graph.

All Python substrate code (`graphify/argue.py`) is zero-LLM; LLM orchestration lives exclusively
in `skill.md`. This mirrors the exact precedent set by Phase 9 (`analyze.py` + skill.md
tournament loop). The fabrication validator (`validate_turn`) is a pure function testable without
any LLM or MCP runtime, enabling strong unit-test coverage of the anti-hallucination guarantee.

The MCP tool `argue_topic` returns a D-02 envelope identical in shape to `chat` and
`get_focus_context`, composed from existing `serve.py` primitives. A single new command file
`graphify/commands/argue.md` provides the `/graphify-argue` slash command. The manifest entry
`argue_topic.composable_from: []` is the recursion guard against Phase 17 `chat` invocation.

**Primary recommendation:** Implement in three waves — (1) `argue.py` substrate + `ArgumentPackage`
dataclasses + `validate_turn`, (2) `argue_topic` MCP tool + `serve.py` dispatch + manifest entry,
(3) `skill.md` SPAR-Kit debate orchestration + `/graphify-argue` command file.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Persona roster:** Reuse Phase 9's four lenses verbatim as PerspectiveSeeds:
`security`, `architecture`, `complexity`, `onboarding`. Focus bullets live at
`graphify/skill.md:1433`. Fixed roster for v1 — no per-call variation. `ArgumentPackage.perspectives`
is always `[PerspectiveSeed(lens=L) for L in ["security", "architecture", "complexity", "onboarding"]]`.
`--lenses` subset flag deferred to v1.4.x backlog.

**D-02 — scope="topic" resolution:** Default resolves via `_extract_entity_terms` + `_score_nodes`
+ `nx.ego_graph(depth=2)`. Budget caps total nodes (clamp `max(50, min(budget, 100000))`).

**D-03 — scope="subgraph" / scope="community":** Accept explicit `node_ids` or `community_id`
→ `_get_community(community_id)`. Power-user paths.

**D-04 — All 4 personas per round, synchronous barrier.** 4 parallel LLM calls per round.
Round N+1 sees all round-N validated claims. Worst case: 4 × 6 = 24 LLM calls.
Temperature ≤ 0.4 enforced at prompt-call level in skill.md.

**D-05 — Blind-label harness reshuffled per round.** Shuffle A/B/C/D persona labels at round
start (not per turn). Reuses shuffling code pattern at `skill.md:1511`.

**D-06 — Cite-overlap convergence + hard cap=6:**
- `verdict="consensus"` when Jaccard overlap ≥ 0.7 for 2 consecutive rounds
- `verdict="dissent"` when overlap < 0.2 for 3 consecutive rounds
- `verdict="inconclusive"` when cap=6 reached without either condition firing

**D-07 — No synthesis step that invents agreement.** Consensus is detected from independent
cite overlap, never produced by a synthesizer persona.

**D-08 — `validate_turn` is a pure function in `argue.py`:** `validate_turn(turn: dict, G: nx.Graph) -> list[str]`.
Returns list of `node_id`s in `turn["cites"]` not in `G.nodes`. Zero LLM calls.

**D-09 — On violation: hard-reject + re-prompt once.** Max 1 retry. If still invalid →
`{claim: "[NO VALID CLAIM]", cites: []}` abstention. Abstentions dropped from Jaccard
numerator/denominator for that round.

**D-10 — Validator operates on `cites` list, not on claim prose.** Atomic unit: a claim either
has valid cites or it doesn't.

**D-11 — Per-round chronological transcript layout.** `## Round 1`, `## Round 2`, … with 4 persona
sub-sections per round (`### Security`, `### Architecture`, `### Complexity`, `### Onboarding`).

**D-12 — Final `## Verdict` section** with: verdict field, per-round cite-overlap Jaccard
trajectory, advisory disclaimer, full list of cited node_ids with labels.

**D-13 — Inline cite style `[node_id:label]`.** Label sanitized via `security.py::sanitize_label`.
Alias redirects applied before rendering — `[canonical_id:label]` always uses canonical.

**D-14 — `argue_topic` returns a D-02 envelope.** `text_body` = human-readable summary. `meta` =
`{verdict, rounds_run, argument_package: <serialized ArgumentPackage>, citations: [...],
resolved_from_alias: {...}, output_path: "graphify-out/GRAPH_ARGUMENT.md"}`.

**D-15 — `composable_from: []` in manifest for `argue_topic`.** Planner adds regression test
asserting `argue_topic.composable_from == []` in `tests/test_capability_manifest.py`.

**D-16 — Alias redirects threaded through every citation.** Call `_resolve_alias(node_id)` on
every cite before writing to transcript or returning in `meta.citations`. Use key
`meta.resolved_from_alias` (NOT `alias_redirects`).

### Claude's Discretion

- Exact persona prompt wording (reuse Phase 9 lens focus bullets from `skill.md:1433` with
  debate-framing tweak: "argue a position on THIS question citing THIS subgraph").
- Final Jaccard threshold values (0.7 / 0.2 starting points; validated via Phase 9 regression suite).
- `GRAPH_ARGUMENT.md` overwrite vs timestamped filename (default: overwrite).
- SPAR-Kit INTERROGATE step (ARGUE-11 P2) — deferred to v1.4.x.

### Deferred Ideas (OUT OF SCOPE)

- SPAR-Kit INTERROGATE step (ARGUE-11 P2) — optional cross-examination turn between rounds.
- Persona memory across rounds (ARGUE-12 P2).
- Clash/rumble/domain intensity scoring (ARGUE-13 P2).
- `--lenses` CLI subset flag.
- Timestamped `GRAPH_ARGUMENT-<topic-slug>.md` output.
- Five-persona / custom-roster debates.
- Chat-to-argue handoff (CHAT-12, cross-phase — lives in Phase 17 backlog).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARGUE-01 | New module `graphify/argue.py` — substrate only. Exposes `populate(G, topic|subgraph, *, scope: "topic"|"subgraph"|"community", budget: int) -> ArgumentPackage` | Confirmed: module does not exist yet. Pattern mirrors `enrich.py` dataclass structure. |
| ARGUE-02 | `ArgumentPackage` dataclass fields: `subgraph: nx.Graph`, `perspectives: list[PerspectiveSeed]`, `evidence: list[NodeCitation]` | Confirmed: `@dataclass` pattern established in `enrich.py`. |
| ARGUE-03 | LLM orchestration in `skill.md` only; `argue.py` zero LLM calls — parallels Phase 9 structure | Confirmed: `test_serve_makes_zero_llm_calls` pattern can be extended to `argue.py`. |
| ARGUE-04 | New MCP tool `argue_topic(topic, scope, budget)` returns `ArgumentPackage` serialized into D-02 envelope | Confirmed: pattern is identical to `_run_chat_core`. |
| ARGUE-05 | Mandatory `{claim, cites: [node_id]}` schema; validator rejects unknown cites as `[FABRICATED]` and re-prompts | Confirmed: `validate_turn(turn, G) -> list[str]` pure function, unit-testable. |
| ARGUE-06 | Phase 9 blind-label harness reused as-is — shuffled A/B labels, stripped persona phrases, rotating judge identity | Confirmed: harness at `skill.md:1388–1550`. Shuffle pattern at `skill.md:1511`. |
| ARGUE-07 | Manifest declares `composable_from: []` for `argue_topic` — Phase 16 MUST NOT invoke Phase 17 chat | Confirmed: `capability_tool_meta.yaml` + `build_mcp_tools()` + assertion in `test_capability.py`. |
| ARGUE-08 | Round cap = 6; debate temperature ≤ 0.4; `dissent` and `inconclusive` are valid outputs (no consensus-forcing) | Confirmed: Jaccard overlap detector in pure Python, no LLM judge needed. |
| ARGUE-09 | Output written to `graphify-out/GRAPH_ARGUMENT.md`; advisory only — never auto-applies changes | Confirmed: GRAPH_ANALYSIS.md precedent at `skill.md:1607`. |
| ARGUE-10 | `/graphify-argue <question>` command file invokes `argue_topic` via MCP | Confirmed: `graphify/commands/ask.md` is the template; `test_commands.py::test_ask_md_frontmatter` is the test template. |
| ARGUE-11 [P2] | SPAR-Kit INTERROGATE step — deferred | Out of scope. |
| ARGUE-12 [P2] | Persona memory across rounds — deferred | Out of scope. |
| ARGUE-13 [P2] | Clash/rumble/domain intensity scoring — deferred | Out of scope. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Evidence subgraph construction | Python substrate (`argue.py`) | `serve.py` primitives | `populate()` composes existing `_score_nodes`, `_bfs`, `_get_community` — zero new traversal logic |
| Fabrication validation | Python substrate (`argue.py`) | None | Pure function `validate_turn(turn, G) -> list[str]`; zero LLM; unit-testable in isolation |
| LLM persona debate orchestration | Skill (`skill.md`) | None | D-73 / ARGUE-03 — LLM lives in skill only |
| Blind-label anti-bias harness | Skill (`skill.md`) | None | Phase 9 precedent; shuffle machinery at skill.md:1511 |
| MCP surface for `argue_topic` | `serve.py` + `mcp_tool_registry.py` | `argue.py` (substrate) | Thin `@tool` wrapper over `_run_argue_topic_core` — same pattern as `_tool_chat` |
| Manifest recursion guard | `capability_tool_meta.yaml` | `tests/test_capability.py` | `composable_from: []` declared at rest; regression test asserts it |
| Advisory-only output file | Skill (`skill.md`) | None | GRAPH_ARGUMENT.md written at end of debate via Python snippet in skill.md |
| Citation alias threading | `argue.py` populate + serve.py wrapper | None | `_resolve_alias` closure per D-16; same pattern as chat |
| Label sanitization | `security.py::sanitize_label` | None | All persona labels / cite labels pass through before transcript |
| Slash command routing | `graphify/commands/argue.md` | None | Mirrors ask.md frontmatter shape |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | 3.4.2 [VERIFIED: pip show] | Graph representation, `nx.ego_graph`, subgraph extraction | Project backbone |
| Python dataclasses | stdlib | `ArgumentPackage`, `PerspectiveSeed`, `NodeCitation` | Pattern from `enrich.py::EnrichmentResult` |
| Python `__future__` annotations | stdlib | Forward-compat type hints | Required by all modules per CLAUDE.md |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 [VERIFIED: pip show] | Unit tests for `argue.py` + serve.py argue extensions | All tests |
| json | stdlib | Serialize `ArgumentPackage` into D-02 envelope `meta` | In `_run_argue_topic_core` |

### No new required dependencies
The entire Phase 16 Python substrate uses only libraries already present in the project.
[VERIFIED: reviewed imports of `enrich.py`, `serve.py`, `analyze.py` — all use networkx + stdlib]

---

## Architecture Patterns

### System Architecture Diagram

```
User question: "/graphify-argue <question>"
        |
        v
[graphify/commands/argue.md]  ← slash command (no model invocation)
        |  calls MCP tool argue_topic(topic, scope, budget)
        v
[serve.py :: _run_argue_topic_core]
        |  calls
        v
[argue.py :: populate(G, topic, scope, budget)]
        |
        +-- _extract_entity_terms(topic)  → terms
        +-- _score_nodes(G, terms)         → seeds
        +-- _bfs(G, seeds, depth=2)        → evidence subgraph
        |
        v
  ArgumentPackage {
    subgraph: nx.Graph (≤budget nodes),
    perspectives: [PerspectiveSeed(lens) × 4],
    evidence: [NodeCitation(node_id, label, source_file)]
  }
        |
        v  (returned to skill.md via MCP envelope)
[skill.md :: SPAR-Kit debate loop]
        |
        for round in 1..6:
          shuffle A/B/C/D labels  ← Phase 9 blind-harness
          for each persona:
            LLM call (temp≤0.4)  → {claim, cites:[node_id]}
            validate_turn(turn, G)  ← argue.py (zero LLM)
            if invalid: re-prompt once; else abstain
          compute Jaccard overlap across 4 persona cite sets
          early-stop on consensus (≥0.7 × 2 rounds)
            or dissent (<0.2 × 3 rounds)
        |
        v
[GRAPH_ARGUMENT.md written to graphify-out/]
        |
        v
D-02 envelope returned:
  text_body = summary (verdict + trajectory + path)
  meta = {verdict, rounds_run, argument_package, citations,
          resolved_from_alias, output_path}
```

### Recommended Project Structure
```
graphify/
├── argue.py              # NEW — zero-LLM substrate
│                         #   populate(), ArgumentPackage, PerspectiveSeed,
│                         #   NodeCitation, validate_turn, compute_overlap
├── serve.py              # EXTEND — _run_argue_topic_core, _tool_argue_topic
├── mcp_tool_registry.py  # EXTEND — add argue_topic Tool entry
├── capability_tool_meta.yaml  # EXTEND — add argue_topic with composable_from: []
├── commands/
│   └── argue.md          # NEW — /graphify-argue slash command
└── skill.md              # EXTEND — /graphify-argue SPAR-Kit orchestration block

tests/
├── test_argue.py          # NEW — pure substrate unit tests
└── test_serve.py          # EXTEND — test_argue_* envelope/alias tests
```

### Pattern 1: argue.py Dataclass Structure (mirrors enrich.py)

```python
# Source: graphify/enrich.py (EnrichmentResult pattern) [VERIFIED: file read]
from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx


@dataclass
class NodeCitation:
    node_id: str
    label: str
    source_file: str


@dataclass
class PerspectiveSeed:
    lens: str  # "security" | "architecture" | "complexity" | "onboarding"


@dataclass
class ArgumentPackage:
    subgraph: nx.Graph
    perspectives: list[PerspectiveSeed] = field(default_factory=list)
    evidence: list[NodeCitation] = field(default_factory=list)


def populate(
    G: nx.Graph,
    topic: str,
    *,
    scope: str = "topic",
    budget: int = 2000,
    node_ids: list[str] | None = None,
    community_id: int | None = None,
) -> ArgumentPackage:
    ...


def validate_turn(turn: dict, G: nx.Graph) -> list[str]:
    """Return list of node_ids in turn['cites'] not present in G.nodes.
    Empty list = valid. Zero LLM calls."""
    return [nid for nid in turn.get("cites", []) if nid not in G.nodes]


def compute_overlap(cite_sets: list[set[str]]) -> float:
    """Jaccard overlap across 4 persona cite sets for convergence detection."""
    if not cite_sets or all(len(s) == 0 for s in cite_sets):
        return 0.0
    union: set[str] = set()
    intersection: set[str] | None = None
    for s in cite_sets:
        union |= s
        intersection = s if intersection is None else intersection & s
    if not union:
        return 0.0
    return len(intersection) / len(union)  # type: ignore[arg-type]
```

### Pattern 2: _run_argue_topic_core (mirrors _run_chat_core)

```python
# Source: graphify/serve.py::_run_chat_core (lines 1197–1354) [VERIFIED: file read]
# Key structural pattern:
def _run_argue_topic_core(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str] | None,
    arguments: dict,
) -> str:
    """Phase 16: deterministic argue_topic substrate. Zero LLM. D-02 envelope."""
    topic = arguments.get("topic", "")
    if not isinstance(topic, str) or not topic.strip():
        meta = {"status": "no_results", "citations": [], "verdict": None,
                "rounds_run": 0, "argument_package": {}, "resolved_from_alias": {},
                "output_path": "graphify-out/GRAPH_ARGUMENT.md"}
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
    # ... populate ArgumentPackage, build text_body summary ...
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
```

### Pattern 3: MCP Tool Registration (mirrors chat in mcp_tool_registry.py)

```python
# Source: graphify/mcp_tool_registry.py (lines 57–341) [VERIFIED: file read]
types.Tool(
    name="argue_topic",
    description=(
        "Run a structurally-enforced multi-perspective debate about a decision "
        "grounded in the knowledge graph. Every persona claim cites a real node_id. "
        "Produces graphify-out/GRAPH_ARGUMENT.md. Advisory only — never mutates code or graph. "
        "Used by the /graphify-argue slash command."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Decision question to debate"},
            "scope": {
                "type": "string",
                "enum": ["topic", "subgraph", "community"],
                "default": "topic",
            },
            "budget": {"type": "integer", "default": 2000, "minimum": 50, "maximum": 100000},
            "node_ids": {
                "type": "array", "items": {"type": "string"},
                "description": "Explicit node IDs (scope='subgraph' only)",
            },
            "community_id": {
                "type": "integer",
                "description": "Community ID (scope='community' only)",
            },
        },
        "required": ["topic"],
    },
)
```

### Pattern 4: capability_tool_meta.yaml entry

```yaml
# Source: graphify/capability_tool_meta.yaml (existing pattern) [VERIFIED: file read]
argue_topic:
  cost_class: expensive
  deterministic: false
  cacheable_until: graph_mtime
  composable_from: []   # HARD CONSTRAINT — recursion guard (ARGUE-07, D-15)
```

### Pattern 5: argue.md command file (mirrors ask.md)

```markdown
---
name: graphify-argue
description: Run a structurally-enforced multi-perspective graph debate on a decision question.
argument-hint: <decision question>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `argue_topic` with:
- `topic`: "$ARGUMENTS"
- `scope`: "topic"

Parse the D-02 envelope ...
```
[VERIFIED: `graphify/commands/ask.md` read — no `target:` field, `disable-model-invocation: true`]

### Pattern 6: Phase 9 blind-label harness reuse (skill.md:1511)

```
# Source: graphify/skill.md:1511 [VERIFIED: file read]
# Existing rotation per judge:
# Judge 1: Analysis-1=A, Analysis-2=B, Analysis-3=AB
# Judge 2: Analysis-1=B, Analysis-2=AB, Analysis-3=A
# Judge 3: Analysis-1=AB, Analysis-2=A, Analysis-3=B

# Phase 16 adaptation: per-round shuffle of 4 persona labels (A/B/C/D)
# assigned to security/architecture/complexity/onboarding at round start.
# Same principle: judge (here: Jaccard detector) never sees stable persona→label mapping.
```

### Anti-Patterns to Avoid

- **Calling `chat` from `argue_topic`:** Forbidden by `composable_from: []` + Pitfall 18 recursion guard.
- **LLM calls in `argue.py`:** Violates ARGUE-03 and D-73. `argue.py` is pure Python + NetworkX.
- **Inventing consensus via a synthesizer persona:** D-07 forbids this. Consensus is *detected* from Jaccard overlap, never produced.
- **Stripping invalid cites from claims instead of rejecting the turn:** D-10 uses the atomic `{claim, cites}` unit. Partial stripping (Phase 17's approach) does not apply here.
- **Logging `topic` to stderr:** Pitfall 6 echo-leak guard — no unmatched input tokens echoed back.
- **`meta` key `alias_redirects` instead of `resolved_from_alias`:** Phase 17 canonical naming is `resolved_from_alias`. Using the wrong key would break downstream parsers.
- **Mutating `graph.json` or source files:** ARGUE-09 — output is strictly `graphify-out/GRAPH_ARGUMENT.md` (advisory only).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Topic → graph seed resolution | Custom tokenizer | `_extract_entity_terms` + `_score_nodes` in `serve.py` (lines 954, 537) | Already handles stopwords, ASCII normalization, score ranking |
| BFS depth-2 ego-graph traversal | Custom graph walk | `_bfs(G, seed_ids, depth=2)` in `serve.py` | Established, tested, uniform contract |
| Community member lookup | Custom dict iteration | `communities.get(cid, [])` pattern (already exposed via `_tool_get_community`) | Available in serve.py closure; no new code |
| Alias resolution | Custom redirect loop | `_resolve_alias` closure pattern in `serve.py` (lines 1234, 1409, 1698, 1873) — copy verbatim | Handles cycles, transitive chains, updates `_resolved_aliases` dict |
| Graph serialization to text block | Custom serializer | `render_analysis_context` in `analyze.py` (line 501) | Already produces prompt-safe compact text for lens agents |
| Label sanitization | Custom HTML-escape | `security.py::sanitize_label` (line 188) | Strips control chars, caps at 256 chars |
| Budget clamping | Custom clamp | `max(50, min(budget, 100000))` — existing one-liner across all MCP tools | Used in ≥6 tool cores |
| D-02 envelope format | New envelope | `text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta)` — existing constant | `QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"` at serve.py:903 |

**Key insight:** argue.py's populate() is almost entirely composition of serve.py primitives that already exist. The only genuinely new code is the Jaccard overlap computation and the `validate_turn` pure function.

---

## Common Pitfalls

### Pitfall 1: chat Invocation from argue_topic (Pitfall 18)
**What goes wrong:** `argue_topic` calls `chat` MCP tool, creating non-determinism + potential infinite loop.
**Why it happens:** Developer sees chat as the "query the graph" primitive.
**How to avoid:** `composable_from: []` in manifest. Regression test in `tests/test_capability.py` asserts this. `_run_argue_topic_core` must never import or call `_run_chat_core`.
**Warning signs:** `"chat"` appearing in `argue.py` or `_run_argue_topic_core`.

### Pitfall 2: Fabricated node_id leaking into transcript (Pitfall 4)
**What goes wrong:** Persona invents a node_id that sounds plausible but doesn't exist in `G.nodes`. Transcript cites phantom node.
**Why it happens:** LLM has seen similar node names and completes them from training data.
**How to avoid:** `validate_turn(turn, G)` runs after EVERY persona turn, before the claim enters the transcript. Invalid cites → re-prompt once → abstain if still invalid. The abstained turn contains `"[NO VALID CLAIM]"` as claim and empty cites list.
**Warning signs:** Node IDs in transcript not present in `G.nodes`.

### Pitfall 3: Consensus-forcing via synthesizer persona
**What goes wrong:** A fourth "synthesizer" role merges the three personas' claims into a fake unified verdict.
**Why it happens:** Classic SPAR-Kit adds a synthesizer; Phase 16 deliberately omits it per D-07.
**How to avoid:** No synthesizer persona in the 4-persona roster. Consensus is detected mechanically by Jaccard overlap ≥ 0.7 for 2 consecutive rounds.
**Warning signs:** Any persona named "Synthesizer" or "Consensus" in the debate loop.

### Pitfall 4: `alias_redirects` key instead of `resolved_from_alias`
**What goes wrong:** Parser downstream expects `meta.resolved_from_alias` (Phase 17 canonical) but finds `meta.alias_redirects` (discussion-phase draft name).
**Why it happens:** Discussion log used `alias_redirects` early; CONTEXT.md locks the canonical name.
**How to avoid:** Key must be `resolved_from_alias` (verified at `serve.py:1016, 1091, 1276, 1300`).
**Warning signs:** `alias_redirects` appearing in `_run_argue_topic_core` or `argue.md`.

### Pitfall 5: LLM import sneaking into argue.py
**What goes wrong:** `argue.py` gains an import of `anthropic` or `openai`, breaking ARGUE-03.
**Why it happens:** Developer adds LLM call for "smarter" overlap detection.
**How to avoid:** Extend `test_serve_makes_zero_llm_calls` to also scan `argue.py`. The grep-based test already checks `serve.py`; copy the pattern for `argue.py`.
**Warning signs:** Any `from graphify.llm` or `import anthropic` in argue.py.

### Pitfall 6: Abstentions counted in Jaccard overlap
**What goes wrong:** Round with 1-2 abstentions has only 2-3 persona cite sets. Empty set intersection pulls Jaccard toward 0, triggering false dissent.
**Why it happens:** Naive Jaccard includes empty sets.
**How to avoid:** `compute_overlap` must DROP turns where `cites == []` (abstentions) from both numerator and denominator before computing Jaccard. Documented in D-09.
**Warning signs:** Early `verdict="dissent"` on rounds where most personas agreed.

### Pitfall 7: `GRAPH_ARGUMENT.md` path escaping graphify-out/
**What goes wrong:** Output file written to a path outside `graphify-out/`, violating ARGUE-09 confinement.
**Why it happens:** skill.md has full write access; path could be parameterized via a user argument.
**How to avoid:** Hardcode `output_path = "graphify-out/GRAPH_ARGUMENT.md"` in both `_run_argue_topic_core` and skill.md. `validate_graph_path` in security.py can verify at write time.

### Pitfall 8: Round-cap bypass via off-by-one
**What goes wrong:** Loop runs 7 rounds instead of 6.
**Why it happens:** `for round in range(1, 7)` vs `for round in range(7)`.
**How to avoid:** Unit test asserts `ArgumentPackage.rounds_run <= 6` when no early-stop fires.

---

## Code Examples

### validate_turn (core fabrication guard)
```python
# Source: derived from D-08 / D-10 in CONTEXT.md; mirrors _validate_citations in serve.py
# [VERIFIED: design confirmed by reading serve.py:1019-1042]
def validate_turn(turn: dict, G: nx.Graph) -> list[str]:
    """Return list of node_ids in turn['cites'] that are not in G.nodes.

    Empty return = valid turn. Caller (skill.md) uses non-empty return to re-prompt.
    Zero LLM calls. Unit-testable without mcp package.
    """
    return [nid for nid in turn.get("cites", []) if nid not in G.nodes]
```

### compute_overlap (Jaccard for stop condition)
```python
# Source: D-06 in CONTEXT.md
# [VERIFIED: design; pure math]
def compute_overlap(cite_sets: list[set[str]]) -> float:
    """Jaccard overlap across 4 persona cite sets.

    Abstentions (empty sets) are excluded from computation before calling.
    """
    non_empty = [s for s in cite_sets if s]
    if len(non_empty) < 2:
        return 0.0  # cannot compute overlap with fewer than 2 non-absent personas
    union: set[str] = set()
    intersection = non_empty[0].copy()
    for s in non_empty[1:]:
        union |= s
        intersection &= s
    union |= non_empty[0]
    return len(intersection) / len(union) if union else 0.0
```

### populate() scope dispatch
```python
# Source: D-02, D-03 in CONTEXT.md; _run_chat_core scope dispatch at serve.py:1256-1282
# [VERIFIED: verified serve.py pattern]
def populate(
    G: nx.Graph,
    topic: str,
    *,
    scope: str = "topic",
    budget: int = 2000,
    node_ids: list[str] | None = None,
    community_id: int | None = None,
) -> ArgumentPackage:
    from graphify.serve import _extract_entity_terms, _score_nodes, _bfs
    budget = max(50, min(budget, 100000))

    if scope == "subgraph" and node_ids:
        seed_ids = [nid for nid in node_ids if nid in G.nodes]
    elif scope == "community" and community_id is not None:
        from graphify.serve import _communities_from_graph
        communities = _communities_from_graph(G)
        seed_ids = communities.get(community_id, [])
    else:  # "topic" (default)
        terms = _extract_entity_terms(topic)
        scored = _score_nodes(G, terms)
        seed_ids = [nid for _, nid in scored[:5]]

    if not seed_ids:
        subG = G.__class__()
    else:
        visited, _ = _bfs(G, seed_ids, depth=2)
        nodes_list = list(visited)[:budget]
        subG = G.subgraph(nodes_list).copy()

    perspectives = [
        PerspectiveSeed(lens=l)
        for l in ["security", "architecture", "complexity", "onboarding"]
    ]
    evidence = [
        NodeCitation(
            node_id=nid,
            label=G.nodes[nid].get("label", nid),
            source_file=G.nodes[nid].get("source_file", ""),
        )
        for nid in subG.nodes if nid in G.nodes
    ]
    return ArgumentPackage(subgraph=subG, perspectives=perspectives, evidence=evidence)
```

### _resolve_alias closure (copy verbatim from _run_chat_core)
```python
# Source: graphify/serve.py:1234-1250 [VERIFIED: file read]
# Copy this closure verbatim into _run_argue_topic_core.
_resolved_aliases: dict[str, list[str]] = {}
_effective_alias_map: dict[str, str] = alias_map or {}

def _resolve_alias(node_id: str) -> str:
    seen: set[str] = set()
    current = node_id
    while current in _effective_alias_map and current not in seen:
        seen.add(current)
        nxt = _effective_alias_map[current]
        if nxt == current:
            break
        current = nxt
    if current != node_id:
        aliases = _resolved_aliases.setdefault(current, [])
        if node_id not in aliases:
            aliases.append(node_id)
    return current
```

### argue.md frontmatter (mirrors ask.md exactly)
```markdown
# Source: graphify/commands/ask.md [VERIFIED: file read]
---
name: graphify-argue
description: Run a structurally-enforced multi-perspective graph debate on a decision question.
argument-hint: <decision question>
disable-model-invocation: true
---
```
Note: No `target:` field (confirmed by test_commands.py:test_ask_md_frontmatter assertion).

### SPAR-Kit skill.md block structure (debate orchestration)
```
# Source: graphify/skill.md:1388-1607 (Phase 9 tournament pattern) [VERIFIED: file read]
# Phase 16 skill block pattern:
For /graphify-argue <question>:
  Step B1 — call argue_topic via MCP → ArgumentPackage (serialize subgraph + evidence)
  Step B2 — render_analysis_context(subgraph, ...) → {EVIDENCE_SUBGRAPH} text block
  Step B3 — for round in 1..6:
    shuffle A/B/C/D labels (reuse skill.md:1511 rotation)
    for each persona (security/architecture/complexity/onboarding):
      LLM call temp=0.4 with focus bullets from skill.md:1433
      validate_turn(turn, subgraph_G) via Python
      if invalid: re-prompt once with invalid node_ids
      if still invalid: abstain
    compute Jaccard overlap across non-abstain cite sets
    check early-stop conditions (D-06)
  Step B4 — write GRAPH_ARGUMENT.md per D-11/D-12 format
  Step B5 — report verdict to user
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 9 tournament: incumbent/adversary/synthesis + 3 judges | Phase 16: 4 fixed lens personas with cite-overlap convergence (no judges) | Phase 16 decision | Removes judge LLM calls (saves 3×6=18 calls); convergence is mechanical via Jaccard |
| Phase 17 narrative-level citation validator (sentence stripping) | Phase 16 atomic `{claim, cites}` schema with turn-level hard-reject | Phase 16 decision | Stricter; no partial claims survive; re-prompt enforces full validity |

**Not applicable (greenfield phase):** No runtime state inventory needed — `argue.py` does not exist yet, no stored data to migrate.

---

## Phase 9 Blind-Label Harness — Reuse Map

| Component | Location in skill.md | Phase 16 Reuse |
|-----------|----------------------|----------------|
| Anti-pattern note (never label incumbent/adversary in judge prompts) | line 1388-1389 | Apply to Phase 16: never identify personas by role name in Jaccard computation |
| Lens focus bullet definitions (security/architecture/complexity/onboarding) | line 1433 | Copy verbatim; add debate-framing wrapper: "argue a position on THIS question citing only node_ids from the provided subgraph" |
| Shuffled A/B rotation per judge | line 1511 | Adapt: shuffle A/B/C/D persona labels per round (not per judge) — simpler wiring, same bias guarantee |
| Tournament runs 4 rounds (incumbent + adversary + synthesis + judges) | line ~1420 | Replace with: 4 personas × ≤6 rounds; Jaccard replaces judge panel |
| `render_analysis_context` for GRAPH_CONTEXT block | `analyze.py:501` | Reuse verbatim to build `{EVIDENCE_SUBGRAPH}` block for each persona prompt |

---

## MCP Tool Registration — Integration Checklist

Adding `argue_topic` requires touching exactly these files in this order:

1. **`graphify/argue.py`** (new) — `populate`, `ArgumentPackage`, `PerspectiveSeed`, `NodeCitation`, `validate_turn`, `compute_overlap`
2. **`graphify/serve.py`** — add `_run_argue_topic_core`, `_tool_argue_topic`; add `"argue_topic": _tool_argue_topic` to `_handlers` dict
3. **`graphify/mcp_tool_registry.py`** — add `types.Tool(name="argue_topic", ...)` to `build_mcp_tools()` return list
4. **`graphify/capability_tool_meta.yaml`** — add `argue_topic:` block with `composable_from: []`
5. **`graphify/commands/argue.md`** (new) — slash command file
6. **`graphify/skill.md`** — add `/graphify-argue` section after `/graphify analyze` section

The `_handlers` dict key count must equal `build_mcp_tools()` length — `MANIFEST-05` assertion in serve.py line 2981 will fail if they diverge.

---

## Threat Model

| Threat | STRIDE | Affected Component | Mitigation |
|--------|--------|-------------------|------------|
| Persona claims fabricated node_ids | Spoofing (fabrication) | `skill.md` → LLM persona output | `validate_turn(turn, G)` pure validator; re-prompt once; abstain on second failure; `[FABRICATED]` tag in transcript |
| Prompt injection via topic string | Tampering | `argue_topic` tool input | `_extract_entity_terms` tokenizes to `[A-Za-z0-9_]+` — no shell/prompt special chars survive |
| Prompt injection via persona names/labels | Tampering | Transcript rendering | `sanitize_label(text)` strips control chars; `sanitize_label_md` for markdown context |
| Node-ID injection in `node_ids` argument | Tampering | `populate(scope="subgraph")` | Validate `nid in G.nodes` before accepting; unknown node_ids silently dropped |
| Fabricated-cite bypass (retry with same invalid cites) | Spoofing | `skill.md` retry path | Max 1 retry; second failure → abstention, never accepted |
| Round-cap bypass via malformed stop signals | DoS | `skill.md` debate loop | Hard cap=6 enforced in Python before any stop-condition check |
| Token-budget exhaustion via large subgraph | DoS | `populate()` | Budget clamp `max(50, min(budget, 100000))`; node list sliced to `[:budget]` before subgraph construction |
| `argue_topic → chat` recursion | Elevation of Privilege | MCP tool manifest | `composable_from: []`; regression test in `test_capability.py` |
| `GRAPH_ARGUMENT.md` path traversal | Information Disclosure | `skill.md` output write | Hardcode output path; `validate_graph_path(base=project_root)` at write time |
| Session-state bleed between debates | Information Disclosure | In-process state | `argue_topic` is stateless (no session dict); each invocation starts fresh |

---

## Open Questions (RESOLVED)

1. **`render_analysis_context` signature vs. subgraph-only context**
   - What we know: `render_analysis_context(G, communities, community_labels, god_node_list, surprise_list)` takes full-graph artifacts (god nodes, surprises, community labels) — not just a subgraph.
   - What's unclear: For a debate-scoped subgraph, should the planner pre-compute god nodes / surprises on the subgraph only, or pass full-graph analytics and rely on subgraph node filtering in the prompt?
   - **RESOLVED:** Compute god nodes + surprises on the subgraph (`analyze.god_nodes(subG)`, `analyze.surprise_connections(subG)`) — debate stays scoped. Adopted in 16-03 Task 2 action.

2. **`ArgumentPackage` JSON serialization of `subgraph: nx.Graph`**
   - What we know: `nx.node_link_data(G)` produces a dict serializable to JSON; used in `serve.py` graph loading.
   - What's unclear: Whether to serialize the full subgraph into `meta.argument_package` or only the subgraph node/edge IDs.
   - **RESOLVED:** Serialize only `{nodes: [{id, label, source_file}], edge_count: N}` summary — the full graph is already in `graph.json`. Adopted in 16-02 Task 2 behavior.

3. **`test_commands.py` extension for argue.md**
   - What we know: `test_commands.py` covers `CORE_COMMANDS` and has explicit tests for `ask.md` (Phase 17).
   - What's unclear: Whether to add `argue` to `CORE_COMMANDS` dict or add a dedicated `test_argue_md_frontmatter` function following the `test_ask_md_frontmatter` pattern.
   - **RESOLVED:** Add a dedicated `test_argue_md_frontmatter` function modeled exactly on `test_ask_md_frontmatter` (lines 195-209 of `tests/test_commands.py`). Adopted in 16-03 Task 1.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 16 is code-only with no external dependencies beyond those already required by the project.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (already in `[dev]` extras via `pyproject.toml`) |
| Config file | `pyproject.toml` (no `pytest.ini`) |
| Quick run command | `pytest tests/test_argue.py tests/test_serve.py -q -k argue` |
| Full suite command | `pytest tests/ -q` |
| Estimated runtime | quick ~4s / full ~50s |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARGUE-01 | `populate()` returns `ArgumentPackage` with non-empty subgraph for known topic | unit | `pytest tests/test_argue.py::test_populate_returns_argument_package -x` | ❌ Wave 0 |
| ARGUE-01 | `populate(scope="subgraph")` accepts explicit `node_ids` | unit | `pytest tests/test_argue.py::test_populate_scope_subgraph -x` | ❌ Wave 0 |
| ARGUE-01 | `populate(scope="community")` returns community member nodes | unit | `pytest tests/test_argue.py::test_populate_scope_community -x` | ❌ Wave 0 |
| ARGUE-02 | `ArgumentPackage` has `subgraph`, `perspectives`, `evidence` fields with correct types | unit | `pytest tests/test_argue.py::test_argument_package_fields -x` | ❌ Wave 0 |
| ARGUE-02 | `perspectives` always contains exactly 4 lenses | unit | `pytest tests/test_argue.py::test_four_perspectives -x` | ❌ Wave 0 |
| ARGUE-03 | `argue.py` source contains zero LLM imports | unit (grep) | `pytest tests/test_argue.py::test_argue_zero_llm_calls -x` | ❌ Wave 0 |
| ARGUE-03 | `_run_argue_topic_core` source does not import or call `_run_chat_core` | unit (grep) | `pytest tests/test_serve.py::test_argue_does_not_invoke_chat -x` | ❌ Wave 0 |
| ARGUE-04 | `argue_topic` tool registered in MCP registry | unit | `pytest tests/test_serve.py::test_argue_topic_tool_registered -x` | ❌ Wave 0 |
| ARGUE-04 | `_run_argue_topic_core` emits valid D-02 envelope (sentinel present, meta keys correct) | unit | `pytest tests/test_serve.py::test_argue_topic_envelope_ok -x` | ❌ Wave 0 |
| ARGUE-04 | `meta.resolved_from_alias` populated when aliases redirected | unit | `pytest tests/test_serve.py::test_argue_topic_alias_redirect -x` | ❌ Wave 0 |
| ARGUE-05 | `validate_turn` returns empty list for all-valid cites | unit | `pytest tests/test_argue.py::test_validate_turn_valid -x` | ❌ Wave 0 |
| ARGUE-05 | `validate_turn` returns list of unknown node_ids when cites contain fabricated IDs | unit | `pytest tests/test_argue.py::test_validate_turn_fabricated -x` | ❌ Wave 0 |
| ARGUE-06 | Phase 9 blind-label regression: skill.md contains shuffled-label pattern at line ~1511 | unit (grep) | `pytest tests/test_argue.py::test_blind_label_harness_intact -x` | ❌ Wave 0 |
| ARGUE-07 | `argue_topic.composable_from == []` in capability manifest | unit | `pytest tests/test_capability.py::test_argue_topic_not_composable -x` | ❌ Wave 0 |
| ARGUE-08 | `compute_overlap` returns correct Jaccard for sample cite sets | unit | `pytest tests/test_argue.py::test_compute_overlap_jaccard -x` | ❌ Wave 0 |
| ARGUE-08 | `compute_overlap` drops abstentions (empty cite sets) from computation | unit | `pytest tests/test_argue.py::test_compute_overlap_drops_abstentions -x` | ❌ Wave 0 |
| ARGUE-09 | `_run_argue_topic_core` meta includes `output_path: "graphify-out/GRAPH_ARGUMENT.md"` | unit | `pytest tests/test_serve.py::test_argue_topic_output_path -x` | ❌ Wave 0 |
| ARGUE-10 | `graphify/commands/argue.md` exists with correct frontmatter | unit | `pytest tests/test_commands.py::test_argue_md_frontmatter -x` | ❌ Wave 0 |
| ARGUE-10 | `argue.md` body references `argue_topic` MCP tool | unit | `pytest tests/test_commands.py::test_argue_md_frontmatter -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_argue.py tests/test_serve.py -q -k argue`
- **Per wave merge:** `pytest tests/test_argue.py tests/test_serve.py -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_argue.py` — new file; covers ARGUE-01 through ARGUE-08 substrate tests
- [ ] `tests/test_serve.py` — extend with `test_argue_*` functions (≥5 cases)
- [ ] `tests/test_commands.py` — add `test_argue_md_frontmatter` function
- [ ] `tests/test_capability.py` — add `test_argue_topic_not_composable` assertion

**No framework install needed** — pytest already present.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth in MCP stdio |
| V3 Session Management | no | `argue_topic` is stateless (no session dict) |
| V4 Access Control | no | Output confined to `graphify-out/` |
| V5 Input Validation | yes | `_extract_entity_terms` tokenizer; `validate_turn`; `sanitize_label` on all transcript labels |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for Phase 16 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fabricated node_id in LLM persona output | Spoofing | `validate_turn(turn, G)` pure validator; re-prompt once; abstain |
| Prompt injection via `topic` input | Tampering | `_extract_entity_terms` → `re.findall(r"[A-Za-z0-9_]+", topic.lower())` strips all special chars |
| Transcript label injection (persona names, node labels) | Tampering | `sanitize_label` + `sanitize_label_md` on all emitted labels |
| Path traversal via `output_path` | Information Disclosure | Hardcoded `graphify-out/GRAPH_ARGUMENT.md`; `validate_graph_path(base=project_root)` |
| Round-cap bypass | DoS | Hard cap=6 in Python before stop-condition checks |
| Token budget exhaustion | DoS | `max(50, min(budget, 100000))` clamp; `nodes_list[:budget]` slice |
| Recursion via `argue_topic → chat` | Elevation | `composable_from: []` + regression test |

---

## Assumptions Log

> All claims in this research were verified or cited from source files read in this session.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `render_analysis_context` in `analyze.py:501` accepts `(G, communities, community_labels, god_node_list, surprise_list)` — correct signature for reuse in Phase 16 evidence block | Code Examples | Planner would need to adapt the call signature; low risk |
| A2 | `_communities_from_graph(G)` is importable from `graphify.serve` for use in `argue.py::populate(scope="community")` | Code Examples | Need to verify import path if argue.py imports it directly vs. gets communities passed in |

**Recommendation on A2:** Pass `communities` dict into `populate()` as an argument rather than importing `_communities_from_graph` from serve — keeps argue.py decoupled from serve.py's internal state.

---

## Sources

### Primary (HIGH confidence)
- `graphify/serve.py` (read directly) — `_score_nodes`, `_bfs`, `_bidirectional_bfs`, `_extract_entity_terms`, `_run_chat_core`, `QUERY_GRAPH_META_SENTINEL`, `_resolve_alias` pattern, `_tool_chat` handler, `_handlers` dict, `build_mcp_tools()` import
- `graphify/mcp_tool_registry.py` (read directly) — `build_mcp_tools()`, `tool_names_ordered()`, complete tool schema patterns
- `graphify/capability_tool_meta.yaml` (read directly) — `composable_from` field structure for all existing tools
- `graphify/capability_manifest.schema.json` (read directly) — `composable_from` schema definition
- `graphify/analyze.py` (read directly) — `render_analysis_context` signature (line 501)
- `graphify/enrich.py` (read directly) — `@dataclass EnrichmentResult` pattern (lines 42–50)
- `graphify/security.py` (read directly) — `sanitize_label`, `validate_graph_path` signatures (lines 144, 188)
- `graphify/skill.md` (read directly) — blind-label harness (lines 1388–1550), lens focus bullets (line 1433), shuffle rotation (line 1511), GRAPH_ANALYSIS.md write pattern (line 1607)
- `graphify/commands/ask.md` (read directly) — slash command frontmatter shape (no `target:` field)
- `tests/test_serve.py` (read directly) — `test_serve_makes_zero_llm_calls`, `test_chat_*` pattern, `_run_chat_core` import style
- `tests/test_commands.py` (read directly) — `test_ask_md_frontmatter` pattern (lines 195–209)
- `.planning/phases/16-graph-argumentation-mode/16-CONTEXT.md` (read directly) — all locked decisions D-01..D-16

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` ARGUE-01..ARGUE-10 (read directly) — requirement spine
- `.planning/ROADMAP.md` §Phase 16 (read directly) — cross-phase rule, success criteria
- `.planning/phases/17-conversational-graph-chat/17-VALIDATION.md` (read directly) — validation architecture template
- `.planning/phases/17-conversational-graph-chat/17-SECURITY.md` (read directly) — threat register pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via `pip show` and source reading
- Architecture: HIGH — all integration points verified in existing source files
- Pitfalls: HIGH — derived from reading locked CONTEXT.md decisions + Phase 17 precedents
- Validation: HIGH — test patterns verified from existing test_serve.py + test_commands.py

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable stack)
