# Phase 9: Multi-Perspective Analysis with Autoreason Tournament - Research

**Researched:** 2026-04-14
**Domain:** LLM-orchestrated tournament-based graph analysis in skill.md
**Confidence:** HIGH

## Summary

Phase 9 upgrades graphify's analysis output from purely mechanical graph metrics (degree counting, betweenness centrality, cross-community edges) to LLM-assisted multi-perspective interpretation using the autoreason tournament protocol. The work lives almost entirely in `skill.md` — the Python library stays untouched, and `analyze.py` stays a pure-Python utility for feeding mechanical context into the tournament.

The autoreason tournament structure is well-established and verified: per iteration it produces three candidates (incumbent A, adversarial revision B, synthesis AB) judged by fresh agents via blind Borda count. The key design invariant is that "do nothing" (the unchanged incumbent) is always option A — this prevents hallucinated findings in clean graphs. Convergence happens when the incumbent wins two consecutive rounds; the project scopes to a single tournament pass per lens (one run to completion, no convergence loop), which is a valid subset of the full protocol.

The knowledge graph produced by graphify's pipeline is the unique differentiator: all lenses reason over the same structured graph data (god_nodes, surprising_connections, community structure) rather than raw text, giving each lens a stable, machine-readable "cognitive map" that humans and LLMs can both interrogate.

**Primary recommendation:** Implement each tournament round as an embedded LLM call block inside skill.md, following exactly the pattern established in Step 3B for semantic extraction subagents. Four lenses run independently (optionally parallelized), each producing its own A/B/AB/verdict chain. The Python layer contributes only a `render_analysis()` function that writes the final `GRAPH_ANALYSIS.md` from the structured dict the skill assembles.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tournament Orchestration**
- D-75: Tournament runs in skill orchestration (skill.md), not in Python library code. `analyze.py` stays pure Python for mechanical metrics. Tournament rounds use embedded LLM calls in the skill.
- D-76: Tournament protocol: (1) lens produces incumbent analysis A, (2) adversarial agent generates competing revision B, (3) synthesis agent merges AB, (4) fresh blind judges score A/B/AB via Borda count with no shared context.

**Lens Configuration**
- D-77: Ship 4 built-in lenses: security, architecture, complexity, onboarding. All 4 run by default.
- D-78: User selects subset via skill prompt. No config file needed.
- D-79: Custom user-defined lenses deferred to v1.3.

**Output Shape**
- D-80: Tournament produces `GRAPH_ANALYSIS.md` in `graphify-out/`. `GRAPH_REPORT.md` is untouched.
- D-81: `GRAPH_ANALYSIS.md` contains: per-lens findings with verdicts, convergences, tensions, top insight per lens, overall verdict.
- D-82: When "do nothing" wins Borda for a lens, emit explicit "Clean" verdict with confidence score and voting rationale showing why the adversarial revision was rejected.
- D-83: Every lens always appears in output — clean lenses show verdict, not silence.

### Claude's Discretion
- Tournament round prompts (system prompts for incumbent/adversary/synthesizer/judge roles) — design for maximum separation and minimal context leakage
- Number of judges per Borda round (2-3 is typical in autoreason)
- How mechanical metrics from `analyze.py` feed into lens analysis (as context, not as findings to defend)

### Deferred Ideas (OUT OF SCOPE)
- Custom user-defined lenses via `.graphify/profile.yaml` — v1.3 scope
- Structured JSON output (`analysis.json`) for MCP consumption — Phase 9.2 scope
- Per-lens MCP tools (`get_security_findings`, etc.) — v1.3 scope
- Graph argumentation mode (Phase 16)
</user_constraints>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Mechanical graph metrics (god_nodes, surprises, gaps) | Python library (analyze.py) | — | Pure Python, deterministic, no LLM. Feeds tournament as context. |
| Tournament round orchestration | skill.md (LLM orchestration) | — | D-75 locked. Skill drives all LLM calls. Library is utilities-only. |
| Graph context serialization for prompts | skill.md (inline bash/python) | analyze.py helpers | skill.md reads `.graphify_analysis.json` and serializes relevant subsets per lens |
| Lens-specific incumbent analysis (A) | skill.md (embedded LLM call) | — | Each lens is a separate prompt block in the skill |
| Adversarial revision (B) | skill.md (embedded LLM call, fresh context) | — | Separate agent call with no shared state from incumbent |
| Synthesis (AB) | skill.md (embedded LLM call, fresh context) | — | Synthesizer sees A+B text only, not prior reasoning |
| Blind Borda judge scoring | skill.md (embedded LLM calls, 2-3 judges) | — | Each judge receives A, B, AB in randomized order with no role labels |
| GRAPH_ANALYSIS.md rendering | Python library (new analyze.py function or report.py extension) | skill.md | Skill assembles structured dict, Python renders markdown cleanly |
| Lens selection from user prompt | skill.md (intent parsing) | — | "analyze for security and architecture" → filter to those 2 lenses |
| Output file write | skill.md (bash write) | — | Follows existing pattern: bash block writes to `graphify-out/` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.10+ | Tournament result aggregation, Borda score computation | No new deps; project constraint (no new required deps) |
| networkx | pinned in pyproject.toml | Graph serialization for lens context | Already present pipeline dep |
| json (stdlib) | 3.10+ | Tournament output serialization | Consistent with `.graphify_analysis.json` pattern |

[VERIFIED: codebase grep] No new pip dependencies are introduced. The tournament is pure prompt engineering inside skill.md.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | 3.10+ | Writing GRAPH_ANALYSIS.md to graphify-out/ | Follows existing report.py + skill.md pattern |
| datetime (stdlib) | 3.10+ | Timestamping GRAPH_ANALYSIS.md header | Matches report.py header pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline LLM calls in skill.md | Parallel subagents per lens | Subagents add write-to-disk requirement; lenses are fast enough inline. Reserve subagents for extraction workloads. |
| Python-side tournament logic | Full skill.md orchestration | D-75 locked — CLI stays utilities-only. |
| Single pass per lens | Full convergence loop (incumbent wins 2x) | Convergence loop correct per autoreason paper, but single pass is valid for Phase 9 scope. Convergence can be Phase 9.x. |

**Installation:** No new packages. `pip install -e ".[all]"` remains unchanged.

---

## Architecture Patterns

### System Architecture Diagram

```
User: /graphify analyze [--lenses security,architecture]
          |
          v
     skill.md: parse lens selection
     (default: all 4 lenses)
          |
          v
     Read .graphify_analysis.json      Read graphify-out/graph.json
     (god_nodes, surprises, communities,  (full graph structure)
      cohesion scores)
          |
          +--[serialize graph summary]--+
          |                             |
          v                             |
     [Lens context block]               |
     For each selected lens:            |
       - filter relevant graph data <---+
       - serialize to prompt-safe text
          |
          v
     [Round 1: Incumbent Analysis A]
     Fresh LLM call per lens
     System: "You are a {lens} expert..."
     Input: graph context + lens prompt
     Output: structured findings text (A)
          |
          v
     [Round 2: Adversarial Revision B]
     Fresh LLM call per lens (no context from A call)
     System: "You are a devil's advocate critic..."
     Input: graph context + incumbent text A
     Output: challenged/revised findings (B)
          |
          v
     [Round 3: Synthesis AB]
     Fresh LLM call per lens
     System: "You are a neutral synthesizer..."
     Input: graph context + A text + B text
     Output: merged findings (AB)
          |
          v
     [Round 4: Blind Borda Judges (2-3 calls)]
     Fresh LLM calls, no role labels on A/B/AB
     System: "Rank these 3 analyses 1st/2nd/3rd..."
     Input: shuffled {analysis_1, analysis_2, analysis_3}
     Output: ranking
          |
          v
     [skill.md: compute Borda scores]
     Tally rankings, determine winner
     If winner is original incumbent with no issues → verdict = "Clean"
          |
          v
     [Assemble per-lens result dict]
     {lens, winner, confidence, findings, voting_rationale}
          |
          v
     [All lenses complete]
          |
          v
     [Cross-lens synthesis]
     skill.md: identify convergences and tensions across lenses
          |
          v
     [Python: render_analysis()]          ← NEW function in report.py or analyze.py
     Input: list of per-lens result dicts
     Output: GRAPH_ANALYSIS.md markdown
          |
          v
     graphify-out/GRAPH_ANALYSIS.md  (NEW)
     graphify-out/GRAPH_REPORT.md   (unchanged)
```

### Recommended Project Structure

New additions are minimal:

```
graphify/
├── analyze.py       # Add render_analysis_context() to serialize graph data for prompts
├── report.py        # Add render_analysis() to write GRAPH_ANALYSIS.md from dicts
└── skill.md         # Add new section: "For /graphify analyze" (tournament orchestration)

graphify-out/
├── GRAPH_REPORT.md           # unchanged (mechanical metrics)
├── GRAPH_ANALYSIS.md         # NEW (tournament output, opt-in)
└── .graphify_analysis.json   # unchanged (mechanical metrics cache)
```

### Pattern 1: Graph Context Serialization for Lens Prompts

**What:** Serialize the mechanical analysis output from `analyze.py` into a compact, prompt-safe text block that each lens agent receives as its "cognitive map."

**When to use:** Before every incumbent, adversary, synthesizer, and judge call. All roles get the same graph context — roles differ by system prompt and what other text they also receive.

**Example:**

```python
# Source: graphify/analyze.py (new helper, follows existing dict patterns)
def render_analysis_context(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    top_n_nodes: int = 20,
) -> str:
    """Serialize graph structure to a compact prompt-safe text block."""
    lines = [
        f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities",
        "",
        "Most-connected entities (god nodes):",
    ]
    for n in god_node_list[:top_n_nodes]:
        lines.append(f"  - {n['label']} ({n['edges']} connections)")
    lines += ["", "Surprising cross-file connections:"]
    for s in surprise_list:
        lines.append(f"  - {s['source']} --{s['relation']}--> {s['target']} [{s['confidence']}]: {s.get('why','')}")
    lines += ["", "Communities:"]
    for cid, nodes in communities.items():
        label = community_labels.get(cid, f"Community {cid}")
        sample = [G.nodes[n].get("label", n) for n in nodes[:5]]
        lines.append(f"  - {label}: {', '.join(sample)}{' ...' if len(nodes) > 5 else ''}")
    return "\n".join(lines)
```

### Pattern 2: Borda Count Computation

**What:** Collect 2-3 judge rankings and aggregate into Borda scores. Candidates are labeled by position (1st/2nd/3rd) not by A/B/AB — judge blindness is enforced by shuffling before presenting and unshuffling after scoring.

**When to use:** After collecting all judge outputs in skill.md.

**Example (Python inline block in skill.md):**

```python
# Source: [ASSUMED] — standard Borda count algorithm
# Run inline as python -c block in skill.md, following existing bash+python pattern

def borda_count(judge_rankings: list[list[str]], candidates: list[str]) -> dict[str, int]:
    """
    judge_rankings: list of rankings from each judge,
                    e.g. [["AB", "A", "B"], ["A", "AB", "B"]]
    candidates: the 3 candidate labels ["A", "B", "AB"]
    Returns: {candidate: score} — higher is better.
    n_candidates=3 → points: 1st=2, 2nd=1, 3rd=0
    """
    n = len(candidates)
    scores: dict[str, int] = {c: 0 for c in candidates}
    for ranking in judge_rankings:
        for rank, candidate in enumerate(ranking):
            scores[candidate] += (n - 1 - rank)
    return scores
```

**Clean verdict rule:** If candidate "A" (the original incumbent with no issues) wins Borda, emit verdict `"Clean"` with confidence = judge agreement ratio. Include the voting tally in `voting_rationale`.

### Pattern 3: Lens System Prompt Design

**What:** Each role (incumbent analyst, adversary, synthesizer, judge) gets a distinct system prompt that enforces role separation.

**When to use:** Each LLM call in the tournament.

**Incumbent analyst prompt structure (per lens):**

```
System: You are a {LENS} expert analyzing a software knowledge graph.
        Respond ONLY with your findings. Do not ask for more information.
        If you find no issues, say so explicitly — "no issues found" is a valid and important verdict.
        Format: list findings under headers. Include a confidence level (high/medium/low) per finding.

User: [GRAPH_CONTEXT_BLOCK]
      Analyze this graph from a {LENS} perspective. Focus on:
      {LENS_FOCUS_BULLETS}
```

**Adversary prompt structure:**

```
System: You are a rigorous devil's advocate reviewing an analysis.
        Your job: find what the analyst missed, overstated, or got wrong.
        You may also argue "the analysis is correct and complete" — do nothing is a valid position.
        Do not reference the original analyst by name.

User: [GRAPH_CONTEXT_BLOCK]
      Here is an analysis from a {LENS} perspective:
      [INCUMBENT_A_TEXT]

      Challenge this analysis. What did it miss? What did it overstate?
      Produce your own revised analysis.
```

**Synthesizer prompt structure:**

```
System: You are a neutral synthesizer. Merge two analyses into the best possible combined view.
        Preserve strong findings from both. Discard overclaims. Resolve contradictions explicitly.

User: [GRAPH_CONTEXT_BLOCK]
      Analysis 1: [INCUMBENT_A_TEXT]
      Analysis 2: [ADVERSARY_B_TEXT]
      Produce a merged analysis.
```

**Judge prompt structure (blind):**

```
System: You are an impartial evaluator. Rank the three analyses below from best (1st) to worst (3rd).
        Criteria: accuracy, completeness, absence of overclaims, actionability.
        Output format: "1st: [label] 2nd: [label] 3rd: [label]" — nothing else.
        The labels are Analysis-1, Analysis-2, Analysis-3. Do NOT know which role produced each.

User: [GRAPH_CONTEXT_BLOCK]
      Analysis-1: [SHUFFLED_TEXT]
      Analysis-2: [SHUFFLED_TEXT]
      Analysis-3: [SHUFFLED_TEXT]
      Rank them.
```

### Pattern 4: GRAPH_ANALYSIS.md Structure

**What:** Output format for the final file (D-80, D-81, D-82, D-83).

**Example structure:**

```markdown
# Graph Analysis - {root} ({date})

> Multi-perspective analysis using autoreason tournament protocol.
> Lenses run: security, architecture, complexity, onboarding

## Overall Verdict

[1-2 sentence cross-lens synthesis — convergences dominate, key tensions flagged]

## Security

**Verdict:** [Finding summary | Clean]
**Confidence:** [high | medium | low] (judges: 3-0 unanimous | 2-1 split | ...)

### Top Finding
[The single most important insight from this lens]

### Full Analysis
[Winner text (A, B, or AB)]

### Tournament Rationale
- Incumbent (A): [brief characterization]
- Adversary (B): [brief characterization]
- Synthesis (AB): [brief characterization]
- Judges voted: A={score}, B={score}, AB={score}
- Winner: [candidate] — [why it won in 1 sentence]

---

## Architecture

[same structure]

---

## Complexity

[same structure]

---

## Onboarding

[same structure]

---

## Cross-Lens Synthesis

### Convergences (all lenses agree)
- [finding agreed across 3+ lenses]

### Tensions (lenses disagree)
- Security vs Architecture: [description of disagreement]
```

### Anti-Patterns to Avoid

- **Shared context across rounds:** Never pass the incumbent call's full conversation history to the adversary. The adversary receives only the incumbent text as user-message content — not the system prompt or reasoning trace of the incumbent agent. Context leakage collapses the tournament into self-confirmation.
- **Judge identity disclosure:** Never label candidates as "incumbent", "adversary", "synthesis" in the judge prompt. Shuffle order + use neutral labels (Analysis-1/2/3). Unmap after all judges respond.
- **Incumbent with issues as "clean":** The "clean" verdict is only when the incumbent explicitly states "no issues found" AND it wins the Borda vote. An incumbent that finds minor issues but beats the alternatives is not "clean" — it is a "found issues" verdict with the incumbent as best analysis.
- **Silencing clean lenses:** D-83 requires every lens to appear even when clean. Never omit a lens section from GRAPH_ANALYSIS.md.
- **LLM calls inside analyze.py:** D-75 prohibits this. Any new functions in analyze.py must be pure Python.
- **Writing GRAPH_ANALYSIS.md from skill.md directly as a heredoc:** Use `report.py` render function or equivalent — keeps markdown formatting testable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-agent parallelism | Custom async orchestration | Agent tool multi-call in single message (existing skill.md pattern) | Same pattern used in Step 3B — battle-tested for this codebase |
| Borda count | Complex voting library | 5-line Python inline block | Standard algorithm, trivial implementation |
| Prompt templating | Jinja2 or similar | Python f-string substitution | Project constraint: no Jinja2. Existing skill.md uses direct string substitution throughout. |
| Markdown rendering | Template library | String joining with `"\n".join(lines)` | Matches existing `report.py` pattern exactly |
| Role separation | Shared conversation object | Fresh independent LLM calls per role | This IS the autoreason pattern — shared context defeats the tournament |

**Key insight:** The entire Phase 9 implementation is prompt engineering + a markdown renderer. No new algorithms, no new infrastructure, no new dependencies. The complexity is in designing prompts that maintain role separation and produce consistently structured output.

---

## Common Pitfalls

### Pitfall 1: Context Leakage Between Tournament Rounds
**What goes wrong:** The adversary receives the incumbent's system prompt or reasoning, causing it to argue within the incumbent's frame rather than genuinely challenging it.
**Why it happens:** Reusing a conversation object or passing the full message history forward.
**How to avoid:** Each round is a fresh, independent LLM call. The adversary receives ONLY: the graph context block (constant across all roles) + the incumbent's output text (A) as user message content. Nothing else from the incumbent call leaks in.
**Warning signs:** Adversary finds exactly the same issues as incumbent but "stronger." Adversary fails to identify any finding the incumbent missed.

### Pitfall 2: Judge Ranking Format Fragility
**What goes wrong:** Judges return free-text rankings ("I think the first analysis is best because...") instead of the required terse format ("1st: Analysis-2 2nd: Analysis-1 3rd: Analysis-3").
**Why it happens:** Judge system prompt is too permissive or doesn't enforce output format strictly.
**How to avoid:** Include an explicit OUTPUT FORMAT block in the judge system prompt. Parse with a regex that handles variations (e.g., "1. Analysis-2"). If parsing fails, re-prompt once. If still fails, mark that judge's vote as invalid and note in voting_rationale.
**Warning signs:** Skill hangs trying to parse judge output. Borda scores are all 0.

### Pitfall 3: Lens Prompt Too Generic
**What goes wrong:** The "security" lens produces the same findings as the "architecture" lens because both prompts reduce to "analyze the graph."
**Why it happens:** Lens-specific focus bullets are vague or absent.
**How to avoid:** Each lens prompt includes 4-6 concrete focus bullets specific to that lens perspective. Security focuses on: authentication boundaries, credential-adjacent nodes, privilege escalation paths, external interface exposure. Architecture focuses on: god nodes (coupling risk), community boundaries (separation of concerns), cross-layer dependencies, missing abstraction layers.
**Warning signs:** Convergence section contains every finding (all 4 lenses agree on everything) — means the lenses aren't actually distinct perspectives.

### Pitfall 4: Clean Verdict Suppressed for Boring Graphs
**What goes wrong:** skill.md skips writing the Clean verdict because "nothing interesting to say," violating D-83.
**Why it happens:** Conditional logic that omits a lens section when no issues found.
**How to avoid:** Always write the lens section. The Clean verdict with voting rationale ("adversary proposed X but judges rejected it 2-1 as overclaiming") is the output, not silence. This is the point: "we checked, here's proof we checked."
**Warning signs:** GRAPH_ANALYSIS.md has fewer than N lens sections when N lenses were requested.

### Pitfall 5: Graph Context Block Too Large
**What goes wrong:** Graph context serialization dumps all 500+ nodes into each prompt, exceeding context or degrading analysis quality.
**Why it happens:** `render_analysis_context()` not capping node counts.
**How to avoid:** Cap god_nodes at top 20, surprising_connections at top 10, communities at all but show only 5 node labels per community. Total context block should be <1000 tokens for medium graphs.
**Warning signs:** LLM calls time out. Lens findings are generic rather than referencing specific nodes by name.

### Pitfall 6: Mechanical Metrics Mistaken for Findings
**What goes wrong:** Incumbent prompt includes god_node list as "issues to address," causing incumbent to reflexively flag high-degree nodes as architectural problems.
**Why it happens:** Graph context framing uses words like "problems" or "issues."
**How to avoid:** Frame mechanical metrics as neutral context: "Here is the graph structure. God nodes are highly-connected entities — they may or may not be architectural concerns; that is for you to determine." Claude's Discretion confirms: mechanical metrics feed tournament as context, not as findings to defend.
**Warning signs:** Every incumbent analysis lists all god nodes as coupling risks regardless of lens.

---

## Code Examples

### New Function: render_analysis_context() in analyze.py

```python
# Source: [ASSUMED] — follows analyze.py patterns exactly
def render_analysis_context(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    top_n_nodes: int = 20,
    top_n_surprises: int = 10,
) -> str:
    """
    Serialize graph structure to a compact, prompt-safe text block.
    Used as the constant graph context fed to all tournament roles.
    Caps output to stay within ~800 tokens for medium graphs.
    """
    lines = [
        f"## Graph Structure",
        f"{G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities",
        "",
        "### Most Connected Entities",
    ]
    for n in god_node_list[:top_n_nodes]:
        lines.append(f"- {n['label']} ({n['edges']} connections)")

    lines += ["", "### Surprising Cross-File Connections"]
    for s in surprise_list[:top_n_surprises]:
        why = s.get("why", "")
        lines.append(
            f"- {s['source']} --{s['relation']}--> {s['target']} "
            f"[{s['confidence']}]{': ' + why if why else ''}"
        )

    lines += ["", "### Communities"]
    for cid, nodes in communities.items():
        label = community_labels.get(cid, f"Community {cid}")
        real_labels = [G.nodes[n].get("label", n) for n in nodes[:5]]
        suffix = f" (+{len(nodes)-5} more)" if len(nodes) > 5 else ""
        lines.append(f"- {label}: {', '.join(real_labels)}{suffix}")

    return "\n".join(lines)
```

### New Function: render_analysis() in report.py

```python
# Source: [ASSUMED] — follows report.py generate() pattern exactly
def render_analysis(
    lens_results: list[dict],
    root: str,
) -> str:
    """
    Render GRAPH_ANALYSIS.md from structured per-lens tournament results.

    Each lens_result dict:
    {
      "lens": "security",
      "verdict": "Clean" | "Found issues",
      "confidence": "high" | "medium" | "low",
      "judge_votes": {"A": 2, "B": 0, "AB": 4},  # Borda scores
      "winner": "AB",
      "top_finding": "...",
      "full_analysis": "...",          # winner text
      "candidate_a": "...",            # incumbent text
      "candidate_b": "...",            # adversary text
      "candidate_ab": "...",           # synthesis text
    }
    """
    from datetime import date
    today = date.today().isoformat()
    lines = [
        f"# Graph Analysis - {root}  ({today})",
        "",
        "> Multi-perspective analysis using autoreason tournament protocol.",
        f"> Lenses: {', '.join(r['lens'] for r in lens_results)}",
        "",
        "## Overall Verdict",
        "",
        "[Cross-lens synthesis — written by skill.md before calling render_analysis()]",
        "",
    ]
    for result in lens_results:
        lens = result["lens"].title()
        verdict = result["verdict"]
        conf = result["confidence"]
        votes = result["judge_votes"]
        winner = result["winner"]
        lines += [
            f"## {lens}",
            "",
            f"**Verdict:** {verdict}  ",
            f"**Confidence:** {conf} (A={votes.get('A',0)}, B={votes.get('B',0)}, AB={votes.get('AB',0)})",
            "",
        ]
        if result.get("top_finding"):
            lines += ["### Top Finding", "", result["top_finding"], ""]
        lines += [
            "### Full Analysis",
            "",
            result.get("full_analysis", ""),
            "",
            "### Tournament Rationale",
            f"- Winner: **{winner}** (Borda: A={votes.get('A',0)}, B={votes.get('B',0)}, AB={votes.get('AB',0)})",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)
```

### skill.md Trigger Block Structure

```
## For /graphify analyze

Trigger: user says "/graphify analyze", "/graphify analyze --lenses security,architecture",
         or explicitly requests multi-perspective analysis after a /graphify run.

Step 1 - Check graph exists (same guard pattern as /graphify query)
Step 2 - Parse requested lenses (default: all 4)
Step 3 - Load graph context
Step 4 - For each lens: run tournament (4 rounds of LLM calls)
Step 5 - Compute Borda scores in Python inline block
Step 6 - Assemble cross-lens convergences and tensions (LLM call or inline reasoning)
Step 7 - Call render_analysis() Python function
Step 8 - Write graphify-out/GRAPH_ANALYSIS.md
Step 9 - Print summary to user
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM council (all models see each other) | Blind Borda tournament (fresh agents, no shared context) | NousResearch autoreason, 2025 | Eliminates prompt bias and scope creep in multi-agent analysis |
| Binary critique (find issues or not) | Three-way tournament (A vs B vs AB) | Autoreason paper | AB synthesis captures best of both without forcing binary choice |
| Silence when graph is clean | Explicit "Clean" verdict with voting rationale | D-82/D-83 decision | Auditable signal: "we checked and it's fine" |
| Single monolithic analysis | Per-lens analysis with independent tournaments | Phase 9 | Users get perspective-specific findings, not averaged noise |

**Key insight from autoreason research:** The incumbent winning without changes ("do nothing") happens more often than expected on clean corpora — this is a feature, not a bug. The voting rationale showing a rejected adversarial revision provides more signal than silence would.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Single tournament pass per lens (no convergence loop) is the correct Phase 9 scope | Architecture | If full convergence is required, token cost is 2-3x higher and must be budgeted |
| A2 | 2-3 judges per Borda round is sufficient for reliable voting | Standard Stack / Patterns | 1 judge = no majority; 7 judges = faster convergence (per autoreason paper) but 3x token cost |
| A3 | Graph context block of 20 god nodes + 10 surprises + all communities stays under 1000 tokens for typical corpora | Common Pitfalls | If larger graphs overflow, `render_analysis_context()` needs dynamic token budgeting |
| A4 | `render_analysis()` belongs in `report.py` (extension) rather than a new `analyze_report.py` | Architecture | Minor: only affects file organization, not behavior |
| A5 | Lenses run sequentially in skill.md (not as parallel subagents) | Architecture Patterns | If token cost makes sequential too slow, parallelizing via subagents adds complexity (must write results to disk, merge pattern) |
| A6 | The "Clean" incumbent is the one produced when the analyst explicitly states "no issues found" AND wins Borda | Pattern 2 | If incumbent finds minor issues and wins Borda, verdict should be "Found issues (minor)" not "Clean" |

---

## Open Questions

1. **Parallel vs sequential lens execution**
   - What we know: skill.md already parallelizes via Agent tool multi-call in Step 3B
   - What's unclear: Whether lens tournaments should also parallelize (4 tournaments × 4 rounds = 16 LLM calls; parallel saves wall time at same token cost)
   - Recommendation (Claude's Discretion): Start sequential for simplicity. Each tournament is ~4 calls; total for 4 lenses is 16-20 calls. If wall time exceeds 60s, add parallelism in a follow-up. Subagent pattern requires writing partial results to disk which adds complexity.

2. **How "no issues found" is detected in incumbent output**
   - What we know: The incumbent is instructed that "no issues found" is a valid response
   - What's unclear: Whether this is keyword-matched or requires another LLM call to classify
   - Recommendation: Include a structured marker in the incumbent output format: first line must be either `VERDICT: ISSUES FOUND` or `VERDICT: CLEAN`. Regex-parse this — no additional LLM call needed.

3. **Overall verdict (cross-lens synthesis) — LLM call or rule-based?**
   - What we know: D-81 requires convergences and tensions across lenses
   - What's unclear: Whether a 5th LLM call synthesizes cross-lens, or skill.md inlines rule-based convergence detection
   - Recommendation (Claude's Discretion): One additional LLM call with all lens winners as input produces better prose than rule-based string matching. Token cost is low (single call on short inputs).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All pipeline stages | ✓ | 3.10.19 | — |
| pytest | Test suite | ✓ | 9.0.3 | — |
| pip | Package management | ✓ | 26.0.1 | — |
| graphify (library) | Tournament context loading | Must be installed per project | — | `pip install graphifyy` |

No new external dependencies for Phase 9. Environment is sufficient. [VERIFIED: bash command]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml (no separate pytest.ini) |
| Quick run command | `pytest tests/test_analyze.py tests/test_report.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

Phase 9 has no formal requirement IDs, but the implemented behaviors map as follows:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `render_analysis_context()` serializes god_nodes, surprises, communities to text | unit | `pytest tests/test_analyze.py::test_render_analysis_context -x` | ❌ Wave 0 |
| `render_analysis_context()` caps output (top_n_nodes, top_n_surprises) | unit | `pytest tests/test_analyze.py::test_render_analysis_context_caps -x` | ❌ Wave 0 |
| `render_analysis()` writes all 4 lens sections even when verdict is Clean | unit | `pytest tests/test_report.py::test_render_analysis_all_lenses_present -x` | ❌ Wave 0 |
| `render_analysis()` writes Clean verdict with voting rationale | unit | `pytest tests/test_report.py::test_render_analysis_clean_verdict -x` | ❌ Wave 0 |
| Borda count correctly aggregates 3 judge rankings | unit | `pytest tests/test_analyze.py::test_borda_count -x` | ❌ Wave 0 |
| skill.md tournament section present for /graphify analyze trigger | manual | `grep -n "For /graphify analyze" graphify/skill.md` | ❌ Wave 0 |
| GRAPH_ANALYSIS.md generated in graphify-out/ after tournament | integration | manual end-to-end | manual-only |

### Sampling Rate
- **Per task commit:** `pytest tests/test_analyze.py tests/test_report.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_analyze.py` — add tests for `render_analysis_context()` (new function)
- [ ] `tests/test_report.py` — add tests for `render_analysis()` (new function)
- [ ] Borda count helper — inline Python in skill.md, but unit-testable if extracted to analyze.py

*(Existing test infrastructure covers all other pipeline stages — gaps are specific to new functions only)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Graph context sanitized via `sanitize_label()` before embedding in prompts (existing security.py pattern) |
| V6 Cryptography | no | — |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via node labels in graph context | Tampering | `sanitize_label()` already in security.py — strip control chars, cap length. Apply before `render_analysis_context()` embeds labels in prompt text. |
| LLM output written directly to GRAPH_ANALYSIS.md without sanitization | Tampering | `render_analysis()` wraps LLM output in Python string templates — output is framed by trusted structure. Do not eval() or exec() LLM output. |
| Path traversal in output file write | Elevation of Privilege | Write only to `graphify-out/GRAPH_ANALYSIS.md` — follows existing security.py path confinement pattern |

---

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**: All new code must work on Python 3.10 and 3.12 (CI requirement)
- **No new required dependencies**: Tournament is pure prompt engineering. No new pip installs.
- **No linter/formatter**: Code follows PEP 8 spirit without tooling enforcement
- **Type hints on all functions**: `from __future__ import annotations` on all new modules/functions
- **Pure Python in library**: `analyze.py` additions must be pure Python, no API calls (D-75)
- **Test per module**: New functions in `analyze.py` → tests in `test_analyze.py`. New functions in `report.py` → tests in `test_report.py`.
- **No `**kwargs`**: Use explicit parameters in new functions
- **Error handling**: Raise `ValueError` with clear messages; warnings to stderr with `[graphify]` prefix
- **Output path**: Always write to `graphify-out/` — never to project root or caller's cwd directly
- **skill.md file size**: Already 1345 lines. New tournament section adds ~200-300 lines. Acceptable.
- **No Jinja2**: String f-interpolation and `"\n".join(lines)` only (matches existing patterns)
- **GSD workflow enforcement**: All changes go through GSD commands (per CLAUDE.md enforcement section)

---

## Sources

### Primary (HIGH confidence)
- `graphify/analyze.py` (read in full, 537 lines) — mechanical analysis functions, exact signatures
- `graphify/report.py` (read in full, 175 lines) — rendering pattern for GRAPH_ANALYSIS.md
- `graphify/skill.md` (read in full, 1345 lines) — LLM call pattern, subagent dispatch, tournament integration point
- `.planning/phases/09-multi-perspective-analysis-autoreason-tournament/09-CONTEXT.md` — locked decisions D-75 through D-83
- `tests/test_analyze.py` (read partially) — test patterns for analyze.py functions
- `.planning/config.json` — nyquist_validation: true confirmed

### Secondary (MEDIUM confidence)
- [NousResearch/autoreason GitHub](https://github.com/NousResearch/autoreason) — tournament protocol structure (incumbent/adversary/synthesis/judges, Borda count, "do nothing" as first-class option) [VERIFIED: WebFetch + WebSearch]
- `.planning/notes/agent-memory-research-gap-analysis.md` — confirms autoreason adoption decision and exclusions

### Tertiary (LOW confidence)
- None — all critical claims are verified against codebase or official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all verified in codebase
- Architecture: HIGH — existing skill.md patterns are clear and directly applicable
- Tournament protocol: MEDIUM-HIGH — core structure verified via GitHub/WebSearch; specific prompt wording is Claude's Discretion
- Pitfalls: HIGH — derived from verified code patterns and tournament protocol structure
- Test map: HIGH — existing test structure verified

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable domain — tournament protocol + Python library patterns are not fast-moving)
