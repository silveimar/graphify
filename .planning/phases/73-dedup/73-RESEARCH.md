# Phase 73: DEDUP — Research

**Researched:** 2026-05-08
**Domain:** Measurement-only spike — content-fingerprint dedup rate vs sem-sim coverage
**Confidence:** HIGH (architecture + schema verified against source); MEDIUM on corpus invocation timing

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Corpus**: Heavy mixed — three distinct external sources (1 code repo, 1 doc-heavy directory, 1 PDF/paper set) drawn from `~/Documents/silogia-repos/engineering-tools/` siblings. Researcher must confirm exact paths.
- **Normalization recipe** (verbatim, locked):
  ```
  norm(s)     = collapse_ws( strip_punct( s.lower() ) )   # strip_punct = regex [^\w\s] -> ""
  fingerprint = sha256( norm(label) + "|" + norm(description[:200]) )
  ```
  - Description truncated to first 200 chars **post-normalization**.
  - Empty/missing description → `sha256(norm(label) + "|")` (degenerate but consistent — must be flagged in artifact methodology).
  - Stemming OFF by default; researcher may report with/without if it materially changes result.
- **Genuine-collision classification**: deterministic cross-check against existing INFERRED `semantically_similar_to` edges.
  - **Raw rate** = nodes-in-any-collision-set / total concept nodes
  - **Residual rate** = nodes-in-collision-sets-with-no-sem-sim-link / total concept nodes
  - **Decision rule**: Ship if `raw > 5% AND residual > 5%`; Defer otherwise.
- **Artifact**: `.planning/phases/73-dedup/73-SPIKE.md` (canonical, phase-scoped).
- **Spike-script location** (default): `scripts/dedup_spike.py` (committed for reproducibility).
- **No production code changes** ship in this phase. `_make_id()`, `build.py`, `cluster.py` stay untouched.

### Claude's Discretion
- Selection of three concrete corpus paths (within constraints above).
- `confidence_score` threshold for counting a `semantically_similar_to` edge as "linking" two nodes (default suggested: any edge counts).
- Whether to run graphify fresh on each corpus or reuse an existing `graph.json` if one is already cached in a sibling.
- Whether NLTK is acceptable as transient spike-script dep (default: no, stemming off).

### Deferred Ideas (OUT OF SCOPE)
- Implementation of fingerprint dedup in `_make_id()` / `build.py` (DEDUP-02..N).
- Manual / LLM-judge collision classification.
- Embedding-based collision detection.
- Multi-recipe comparison (conservative + standard + aggressive).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEDUP-01 | Spike artifact reports near-duplicate concept-node rate from running graphify against a representative multi-source corpus (≥1 code repo + ≥1 doc-heavy dir + ≥1 PDF/paper set) using SHA-256 fingerprinting of normalized labels+descriptions, with a clear ship/defer recommendation tied to the >5%-AND-genuine-collisions threshold. | Standard Stack (stdlib hashlib/re/json + networkx for graph load), Architecture (3-level dedup map + sem-sim cross-check), Concrete corpus paths verified, Spike-script structure, Test plan |
</phase_requirements>

## Summary

Phase 73 is a **measurement-only spike**. No graphify production code changes. The deliverable is a single Python script (`scripts/dedup_spike.py`) plus a markdown artifact (`73-SPIKE.md`) containing a Ship-or-Defer recommendation, derived from running graphify against three real external corpora and computing two numbers: a raw collision rate (concept nodes that share a SHA-256 fingerprint of normalized label+description) and a residual rate (collision-set nodes not already linked by an INFERRED `semantically_similar_to` edge).

The most consequential research finding the planner must absorb: **`description` is not a base node-schema field**. Per `graphify/validate.py`, `REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}`. The free-text `description` (and `enriched_description`) fields appear only after the **enrichment "description" pass** runs (`graphify/enrich.py`). This means the spike either (a) runs `graphify run` *with* enrichment enabled on each corpus so nodes get descriptions before fingerprinting, or (b) defines a deterministic fallback (e.g., `description = label` or `description = ""`) and documents the choice in the artifact's Method section. The CONTEXT recipe already specifies the empty-description fallback (`sha256(norm(label) + "|")`), so option (b) is consistent with locked decisions — but the planner should make the enrichment-vs-no-enrichment choice an explicit task decision.

**Primary recommendation:** Build a single self-contained spike script that takes 1..N pre-built `graph.json` paths as CLI args, computes fingerprints over nodes whose `file_type ∈ {document, paper, image, rationale}` (excluding `code` — those are AST-deduped already and not what the question is about), cross-checks each collision set against the graph's `semantically_similar_to` edges, prints a markdown table, and exits. Run graphify against each of three corpora once (separately, into per-corpus `graphify-out/` directories), then point the spike script at all three `graph.json` files. Aggregate. Decide.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Run graphify against external corpora | graphify CLI (`graphify run`) | — | Existing pipeline, no changes |
| Load `graph.json` for inspection | Spike script (stdlib `json`) | networkx (only if traversal needed) | Plain-JSON read suffices; sem-sim cross-check is just edge filtering |
| Compute SHA-256 fingerprints | Spike script (stdlib `hashlib` + `re`) | — | Pure function, no graphify dep |
| Classify collisions vs sem-sim edges | Spike script | — | Deterministic, no LLM, no embeddings |
| Emit `73-SPIKE.md` artifact | Manual authoring (executor copies script output) OR script-driven | — | Either works; CONTEXT prefers human-curated artifact with Appendix sample, so script likely emits stdout markdown that executor pastes/edits |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `hashlib` | 3.10+ | SHA-256 fingerprinting | [VERIFIED] CONTEXT locks SHA-256; stdlib is the obvious choice |
| Python stdlib `re` | 3.10+ | `[^\w\s]` punctuation strip | [VERIFIED] CONTEXT recipe references this regex |
| Python stdlib `json` | 3.10+ | Read `graph.json` | [VERIFIED] graphify writes plain JSON to `graphify-out/graph.json` |
| `networkx` | already in pyproject | Optional: load as graph for sem-sim edge queries | [VERIFIED via graphify/build.py imports] |
| `pytest` | already in pyproject | Test the spike script's pure functions | [VERIFIED] project test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `argparse` (stdlib) | — | CLI for spike script (`--graph PATH...`) | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain `json.load` | `networkx.readwrite.json_graph.node_link_graph` | networkx is already a dep but adds little for two passes (collect nodes, group by fingerprint, scan edges). Plain `json` keeps the script simpler and faster to test. |
| `hashlib.sha256` | `hashlib.blake2b` | CONTEXT explicitly locks SHA-256. Do not deviate. |
| NLTK Porter stemming | — | OFF by default per CONTEXT. Adding NLTK is a transient spike dep risk; skip unless researcher finds it changes the verdict. |

**Installation:** No new packages required. The spike script uses only stdlib + already-installed `networkx` (optional).

**Version verification:** Spike uses stdlib only — no version pinning concern.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────┐
│ External corpus 1   │ ─┐
│ (code repo)         │  │
└─────────────────────┘  │
┌─────────────────────┐  │   graphify run
│ External corpus 2   │ ─┼──► (per-corpus           ──► per-corpus graphify-out/graph.json
│ (doc-heavy dir)     │  │    `--output <out>`)
└─────────────────────┘  │
┌─────────────────────┐  │
│ External corpus 3   │ ─┘
│ (PDF/paper set)     │
└─────────────────────┘
                              ┌────────────────────────────────┐
                              │ scripts/dedup_spike.py         │
   3× graph.json paths ──────►│  1. load nodes                 │
                              │  2. filter concept_nodes       │
                              │  3. compute fingerprints       │
                              │  4. group by fingerprint       │
                              │  5. cross-check sem-sim edges  │
                              │  6. emit markdown stats        │
                              └──────────────┬─────────────────┘
                                             │ stdout markdown
                                             ▼
                              ┌────────────────────────────────┐
                              │ .planning/phases/73-dedup/     │
                              │ 73-SPIKE.md                    │
                              │ (Summary | Corpus | Method |   │
                              │  Results | Recommendation |    │
                              │  Appendix sample)              │
                              └────────────────────────────────┘
                                             │
                                             ▼
                              .planning/research/questions.md
                              (Q-2026-05-07-01 status flip)
```

### Recommended Project Structure
```
scripts/
└── dedup_spike.py              # NEW — pure-function fingerprint + collision counter + CLI

tests/
└── test_dedup_spike.py         # NEW — unit tests for norm(), fingerprint(), classify_collisions()

.planning/phases/73-dedup/
├── 73-CONTEXT.md               # existing
├── 73-DISCUSSION-LOG.md        # existing
├── 73-RESEARCH.md              # this file
├── 73-PLAN.md                  # planner produces next
└── 73-SPIKE.md                 # NEW (final deliverable)
```

### Pattern 1: Pure-function pipeline with thin CLI shell
**What:** Split the script into pure functions (`normalize`, `fingerprint`, `group_by_fingerprint`, `classify_against_semsim`) and a `main()` that does I/O and stdout emission.
**When to use:** Any spike where reproducibility and unit-testability matter as much as the answer.
**Example:**
```python
# Source: pattern derived from graphify/security.py + graphify/validate.py style
import re
import hashlib

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

def normalize(s: str) -> str:
    return " ".join(_PUNCT.sub("", (s or "").lower()).split())

def fingerprint(label: str, description: str) -> str:
    payload = normalize(label) + "|" + normalize((description or "")[:200])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

### Pattern 2: Concept-node filter
**What:** Define explicitly which `file_type` values count as "concept nodes" for this measurement. CONTEXT lists `{code, document, paper, image, rationale}` as the universe; the dedup question is principally about non-code nodes (code nodes get AST-stable IDs from `_make_id` already).
**Recommendation:** **Default include `{document, paper, image, rationale}` as concept nodes; exclude `code`**. Document this choice in the artifact's Method section with a one-liner rationale ("code nodes are AST-deduped at extraction time and have stable structural IDs; the dedup question targets LLM-extracted concept nodes where label drift is the failure mode"). The planner may also produce a *both-modes* table (with-code vs without-code) — cheap to add, useful for the artifact.

### Anti-Patterns to Avoid
- **Modifying `graphify/extract.py:_make_id()`**: explicitly out of scope; this is DEDUP-02..N.
- **Embedding-based similarity**: out of scope per project-level "Out of Scope" exclusion.
- **LLM-judge collision classification**: explicitly rejected in CONTEXT in favor of deterministic sem-sim cross-check.
- **Inline-in-artifact code**: CONTEXT defaults to a committed `scripts/dedup_spike.py`; do not paste a 100-line block into 73-SPIKE.md instead.
- **Running graphify on test fixtures**: `tests/fixtures/` is too small/contrived per CONTEXT — the spike must use real external corpora.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph traversal | Custom BFS over node+edge dicts | `networkx.Graph` if needed | But for this spike, plain edge-list filtering is sufficient — no traversal required |
| Hashing | Custom hash | `hashlib.sha256` | CONTEXT locks SHA-256 |
| Reading `graph.json` | Custom parser | `json.load` | `graph.json` is plain JSON dict |
| Computing collision groups | Manual loops | `collections.defaultdict(list)` keyed by fingerprint | Idiomatic, fast, testable |

**Key insight:** This phase is small enough that ~150 lines of stdlib Python plus a unit test do the entire job. Avoid over-engineering — no class hierarchies, no plugins, no config files.

## Runtime State Inventory

Not applicable — this phase introduces no rename/refactor/migration. Spike script is new, no existing runtime state references it.

## Common Pitfalls

### Pitfall 1: Description field doesn't exist on base nodes
**What goes wrong:** The CONTEXT-locked recipe references `description[:200]`, but `graphify/validate.py` shows `REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}`. `description` and `enriched_description` are populated only by `graphify/enrich.py`'s "description" pass.
**Why it happens:** Recipe was specified at design time without verifying the live schema.
**How to avoid:**
- **Option A (clean):** Run `graphify run` with the enrichment "description" pass enabled on each corpus before fingerprinting, so each node has `enriched_description`. The spike reads `node.get("enriched_description") or node.get("description") or ""`.
- **Option B (degenerate but consistent):** Skip enrichment; fingerprint becomes effectively `sha256(norm(label) + "|")`. CONTEXT explicitly allows this and tells the researcher to "call it out in artifact methodology". This is cheaper and faster but reduces the spike to a label-only collision rate, which is a weaker signal.
- **Recommended:** Option A on at least one corpus (the smallest one, to keep enrichment cost bounded), Option B on the others, and report both numbers. The planner should make this an explicit decision in PLAN.md.
**Warning signs:** All fingerprints have identical `|` suffix → enrichment was skipped. All fingerprints look identical between rerun → caching may be hiding nondeterminism in description text; check `graphify-out/cache/`.

### Pitfall 2: `semantically_similar_to` edges are produced by the LLM extractor, not by AST passes
**What goes wrong:** Code-only corpora (corpus 1) will have ~zero `semantically_similar_to` edges because those edges are emitted by the LLM semantic-extraction pass on docs/papers/images, not by tree-sitter. So residual rate on a code corpus ≈ raw rate (no sem-sim coverage to subtract).
**Why it happens:** Per skill files (`graphify/skill.md` line ~409), sem-sim edges are emitted only when "two concepts in this chunk solve the same problem... without any structural link" — i.e., during semantic extraction.
**How to avoid:** Report per-corpus numbers, not just an aggregate. Aggregate is still meaningful (the question is about heterogeneous corpora) but the artifact must show the per-corpus breakdown so the reader can see where the residual comes from. Also: aligns with CONTEXT's "Method" required section.
**Warning signs:** Residual ≈ raw across all three corpora → sem-sim edges aren't covering anything → either sem-sim isn't being produced (extraction issue, investigate) or sem-sim genuinely doesn't catch fingerprint collisions (a real Ship signal).

### Pitfall 3: confidence_score threshold ambiguity
**What goes wrong:** CONTEXT marks the threshold as a researcher decision: "any edge counts" vs "score ≥ 0.5" vs "score ≥ 0.7". The number changes the residual rate.
**How to avoid:** Default to **any edge counts** (most permissive — gives sem-sim the most credit, biases the recommendation toward Defer, which is the more conservative null-hypothesis stance). If the residual rate is borderline (4-6%), re-run with score ≥ 0.6 as a sensitivity check and report both. CONTEXT explicitly allows this default.

### Pitfall 4: graphify run cost on real corpora
**What goes wrong:** Running graphify on three external corpora with semantic extraction enabled triggers Claude API calls — non-trivial token cost and minutes-to-hours of wall time. CONTEXT calls out a "~1h timebox" and permits downsampling.
**How to avoid:**
- Use `cache.py`'s SHA256 cache — second runs are nearly free if files unchanged.
- For the PDF/paper set, pick ≤10 PDFs, not the full directory.
- For doc-heavy `claude-cookbooks`, scope to a subdir (e.g., `claude-cookbooks/multimodal/`).
- Document exact `graphify run` invocation including any `--include`/`--exclude` flags so the artifact is reproducible.

### Pitfall 5: `graphify-out/` location
**What goes wrong:** Per CLAUDE.md: "non-vault runs use a single cwd-relative `graphify-out/` via `default_graphify_artifacts_dir()`". If you cd into each corpus and run graphify, output goes to `<corpus>/graphify-out/`. If you run graphify from the graphify repo and pass the corpus as positional arg, output may collide with graphify's own `graphify-out/`.
**How to avoid:** Either (a) `cd` into each corpus and run there, or (b) pass `--output <unique-path>` per corpus run. Document which approach the artifact uses.

## Code Examples

### Compute fingerprint (verified pattern from CONTEXT recipe)
```python
# Source: CONTEXT.md decision block, normalized to Python 3.10
from __future__ import annotations
import re
import hashlib

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

def normalize(s: str) -> str:
    """CONTEXT recipe: lower → strip punct → collapse whitespace."""
    if not s:
        return ""
    lowered = s.lower()
    stripped = _PUNCT_RE.sub("", lowered)
    return " ".join(stripped.split())

def fingerprint(label: str, description: str | None) -> str:
    """sha256(norm(label) + '|' + norm(description[:200]))"""
    desc = (description or "")[:200]
    payload = normalize(label) + "|" + normalize(desc)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

### Group nodes by fingerprint (idiomatic, testable)
```python
# Source: stdlib idiom
from collections import defaultdict

def group_by_fingerprint(nodes: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        fp = fingerprint(n.get("label", ""), n.get("enriched_description") or n.get("description"))
        groups[fp].append(n)
    return {fp: ns for fp, ns in groups.items() if len(ns) > 1}
```

### Sem-sim cross-check (deterministic)
```python
# Source: derived from graphify/analyze.py:239 pattern (relation == "semantically_similar_to")
def semsim_pairs(edges: list[dict], min_score: float = 0.0) -> set[frozenset[str]]:
    """Return undirected pairs of node IDs linked by sem-sim edges above threshold."""
    pairs: set[frozenset[str]] = set()
    for e in edges:
        if e.get("relation") != "semantically_similar_to":
            continue
        score = e.get("confidence_score", 1.0)
        if score < min_score:
            continue
        pairs.add(frozenset((e["source"], e["target"])))
    return pairs

def collision_is_covered(group: list[dict], semsim: set[frozenset[str]]) -> bool:
    """A collision group is 'covered' iff every node is sem-sim-linked to some other in the group."""
    ids = [n["id"] for n in group]
    for nid in ids:
        if not any(frozenset((nid, other)) in semsim for other in ids if other != nid):
            return False
    return True
```

### Loading `graph.json` (verified shape)
```python
# Source: graphify writes graph.json to <corpus>/graphify-out/graph.json
import json
from pathlib import Path

def load_graph_json(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # graph.json is networkx node_link_data shape: {"nodes": [...], "links": [...]} OR {"edges": [...]}
    nodes = data.get("nodes", [])
    edges = data.get("links") or data.get("edges") or []
    return nodes, edges
```
**Note:** Verify the exact key (`links` vs `edges`) by inspecting one real `graph.json` before finalizing. NetworkX's `node_link_data` defaults to `links`; some graphify writers may use `edges`. The script should accept either.

## State of the Art

Not applicable — this is an internal measurement, not a library evaluation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `graph.json` uses node_link_data shape with `links` (or `edges`) keys | Code Examples | Low — script handles both; verify on first real run |
| A2 | Concept nodes ⊇ `{document, paper, image, rationale}` is the right universe | Pattern 2 | MEDIUM — if user expects `code` included, residual numbers change. Planner should confirm. |
| A3 | Default `min_score=0.0` for sem-sim is correct | Pitfall 3 | LOW — sensitivity analysis covers it; CONTEXT marks this as researcher's call. |
| A4 | `claude-code-templates` qualifies as code repo, `claude-cookbooks` as doc-heavy, `claude-cookbooks/misc/data/` PDFs as paper set | Environment Availability | LOW — substitutes are easy; sibling repos are abundant. |
| A5 | Spike script timebox of ~1h includes all three graphify runs (with cache warm or warm-able) | Pitfall 4 | MEDIUM — first cold run on a large doc-heavy corpus may exceed an hour. Plan should include downsampling fallback. |

## Open Questions

1. **Enrichment-on or off for the spike runs?**
   - What we know: `description` is only populated by `enrich.py`'s description pass.
   - What's unclear: Whether the planner wants the spike to invest enrichment cost (more accurate fingerprints) or skip it (faster, but degenerates to label-only).
   - Recommendation: Run enrichment on the smallest corpus (likely PDF/paper set), skip on the other two, report both flavors of fingerprint rate side-by-side.

2. **`graphify run` exact CLI invocation**
   - What we know: `graphify --help` lists `run`, `--obsidian`, `--graph`, `--output`. Output defaults to `graphify-out/`.
   - What's unclear: Whether code-repo runs need any specific include/exclude flags to avoid sweeping in test fixtures or build artifacts.
   - Recommendation: First task in PLAN should be a 5-minute "dry run" against the smallest corpus to capture the canonical CLI command; bake that into 73-SPIKE.md's Corpus section verbatim.

3. **Should the spike script also emit the artifact, or just emit stats?**
   - What we know: CONTEXT specifies six required artifact sections including a 20-row Appendix.
   - What's unclear: Whether the executor hand-writes the artifact (cleaner prose, slower) or the script emits a partial draft.
   - Recommendation: Script emits a markdown-formatted stats block + the 20-row Appendix table. Executor hand-writes Summary, Method prose, and Recommendation rationale. This splits "data" (machine) from "narrative" (human).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Spike script | ✓ (assumed; project requires it) | 3.10/3.12 | — |
| `networkx` | Optional, for graph loading | ✓ (already in pyproject) | — | Plain `json.load` |
| `pytest` | Spike script unit tests | ✓ (already in pyproject) | — | — |
| `graphify` CLI | Producing per-corpus `graph.json` | ✓ (this repo, `pip install -e ".[all]"`) | per `pyproject.toml` | — |
| Claude API key | `graphify run` semantic extraction | likely ✓ (researcher must confirm env) | — | If absent: extraction falls back to AST-only — measurement still works but sem-sim coverage column is ~0 |
| **`~/Documents/silogia-repos/engineering-tools/claude-code-templates`** | Corpus 1 (code) | ✓ verified | — | Any sibling under `companion-util_repos/`, e.g. `oh-my-claudecode` |
| **`~/Documents/silogia-repos/engineering-tools/claude-cookbooks`** | Corpus 2 (doc-heavy) | ✓ verified | — | `awesome-claude` or `awesome-claude-skills` |
| **`~/Documents/silogia-repos/engineering-tools/claude-cookbooks/misc/data/` PDFs** | Corpus 3 (paper set) — has `Constitutional AI.pdf`, `Amazon-com-Inc-2023-Shareholder-Letter.pdf` etc | ✓ verified (3+ PDFs found) | — | `~/Documents/silogia-repos/engineering-tools/claude-howto/slides/` (2 PDFs); `~/Documents/pdfs-sefirot-input-docs/` (~20 PDFs) |

**Note on `companion-util_repos/` path:** CONTEXT references `~/Documents/silogia-repos/engineering-tools/companion-util_repos/`, but **that subdirectory does not exist**. The actual sibling repos live one level up at `~/Documents/silogia-repos/engineering-tools/`. The planner should treat the candidate paths above as the correct locations and update CONTEXT or the artifact to reflect this.

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Claude API key — if unavailable, the spike runs but sem-sim coverage will be near-zero; this would itself be a finding (graphify wasn't producing sem-sim edges anyway, so dedup *must* ship).

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json` — section omitted per spec.

## Security Domain

`security_enforcement` is not explicitly enabled in `.planning/config.json`. Spike script ingests:
- File paths from CLI args (graph.json paths) — must validate they exist and are readable; do not blindly path-traverse. Use `pathlib.Path.resolve()` and refuse paths outside CWD only if conventions demand it (this is a developer-run script, low risk).
- JSON content from `graph.json` — already produced by graphify itself, trusted.
- No external URLs, no LLM calls, no writes outside CWD or `.planning/phases/73-dedup/`.

No new attack surface. Existing `graphify/security.py` patterns are not affected (no changes to graphify proper).

## Project Constraints (from CLAUDE.md)

- **Build/test commands:** `pip install -e ".[all]"`, `pytest tests/ -q` (and `pytest tests/test_dedup_spike.py -q` for the new test file).
- **No linter/formatter configured** — follow PEP 8 spirit, 4-space indent, type hints required, `from __future__ import annotations` first.
- **Test conventions:** One test file per module; pure unit tests; no network/filesystem side effects outside `tmp_path`.
- **GSD Workflow Enforcement:** All file-changing work must go through a GSD command. This phase already is one — proceed normally.
- **Graph rules:** This repo has its own `graphify-out/` — do NOT confuse it with the per-corpus `graphify-out/` directories the spike will create. Per-corpus output should live inside each corpus, not in this repo.
- **`graphify install` skill stamp:** Not affected by this phase (no platform skill changes).

## Sources

### Primary (HIGH confidence)
- `graphify/validate.py` (lines 1-80) — confirmed `REQUIRED_NODE_FIELDS` excludes `description`
- `graphify/build.py` (lines 1-80) — confirmed 3-level dedup is documented in module header
- `graphify/extract.py` (lines 57-66) — confirmed `_make_id()` is slug-based, `re.sub(r"[^a-zA-Z0-9]+", "_", ...)` lowercased
- `graphify/enrich.py` (lines 31, 174, 884) — confirmed `description` is an enrichment-pass output
- `graphify/serve.py` (line 1106) — confirmed runtime fallback `enriched_description` → `description`
- `graphify/__main__.py` (lines 1622-1781) — confirmed CLI surface (`run`, `--output`, `--graph`, `query`, etc.)
- `.planning/phases/73-dedup/73-CONTEXT.md` — locked decisions
- `CLAUDE.md` — project instructions, build/test commands, graph rules
- Filesystem probes confirmed candidate corpus paths exist with appropriate content/PDF counts

### Secondary (MEDIUM confidence)
- Skill files (`graphify/skill*.md`) — confirmed `semantically_similar_to` edge production happens during LLM semantic extraction with confidence_score 0.6-0.95

### Tertiary (LOW confidence)
- None; no WebSearch was needed — entire research is internal.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + networkx, all verified.
- Architecture: HIGH — 3-level dedup documented in source; spike-script structure derived from project conventions.
- Pitfalls: HIGH — schema gap (description not on base nodes) is the load-bearing finding and is verified against `validate.py` and `enrich.py`.
- Corpus selection: MEDIUM — paths verified to exist, but suitability for spike (size, runtime) depends on first dry run.

**Research date:** 2026-05-08
**Valid until:** 2026-06-07 (30 days; stable code surface, no fast-moving deps)

## RESEARCH COMPLETE
