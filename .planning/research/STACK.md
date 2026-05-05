# Technology Stack — graphify v1.13

**Project:** graphify (Concept Intelligence & Audit Closure milestone)
**Researched:** 2026-05-05
**Mode:** Subsequent-milestone increment (not greenfield)
**Overall recommendation:** **Add zero new required dependencies. Add zero new optional extras.** All v1.13 net-new work (C-1..C-4, V-1, A-1..A-3) can be implemented against the existing stack using stdlib + already-installed libraries (NetworkX, PyYAML, the host agent's LLM channel). One *optional, deferred* extra is flagged for future consideration only if C-1 cross-repo dedup later needs semantic similarity beyond string/path heuristics.

---

## Existing stack — reused as-is (NOT re-researched)

Per CLAUDE.md and `pyproject.toml`, v1.13 inherits and reuses:

| Layer | Component | Version | Reused for v1.13 work |
|-------|-----------|---------|------------------------|
| Runtime | Python | 3.10+ (CI: 3.10, 3.12) | All phases |
| Graph core | networkx | unpinned | C-3 drift diff, C-4 hop filter |
| AST | tree-sitter + 16 language parsers | >=0.23.0 | unchanged |
| Clustering | graspologic (`[leiden]`) | optional | C-1 community-aware dedup |
| Routing | PyYAML, radon (`[routing]`) | optional | C-1 profile reads |
| Schema | stdlib `json` + `validate.py` | stdlib | C-2 confidence_score persistence |
| MCP | mcp (`[mcp]`) | optional | unchanged |
| Vault | stdlib only | — | V-1 Option B silent reroute |

LLM call architecture (important constraint for C-2): graphify's CLI library **does not bundle an LLM SDK**. Semantic extraction in `extract.py` is invoked by the host agent (Claude Code / Codex / etc.) via the skill file `skill.md`; the agent calls the model and writes results back through CLI commands. There is no `anthropic` or `openai` import in the package today, and v1.13 must preserve that.

---

## Per-question recommendations

### 1. C-2 Per-edge LLM confidence scoring — **stdlib only, no new dep**

**Recommendation: DO NOT add `instructor`, `pydantic-ai`, `pydantic`, or `jsonschema`.**

**Why:**
- graphify's LLM channel is the host agent, not an SDK. Structured-output libraries like `instructor` (>=1.x) or `pydantic-ai` wrap `openai.ChatCompletion` / `anthropic.messages.create`; they have no surface graphify can call because graphify never opens that client. Adopting them would require *also* adding `anthropic` as a dep — a much larger architectural shift than v1.13 scopes.
- Confidence scoring fits the existing pattern: skill.md prompts the agent to emit JSON conforming to the existing extraction envelope (`{nodes, edges}` with per-edge `confidence_score` already in the schema per validate.py). The agent already returns JSON — graphify already calls `json.loads` and runs `validate_extraction()` on it. Adding a `confidence_score: float ∈ [0.0, 1.0]` validation rule to `validate.py` is one branch.
- Hand-rolled validation is ~20 lines and matches the prevailing `validate.py` style (returns `list[str]` errors, no exceptions).

**What to add (code, not deps):**
- `validate.py`: extend edge-validation to require `confidence_score` is `float | int` in `[0.0, 1.0]` whenever `confidence ∈ {INFERRED, AMBIGUOUS}`.
- `skill.md`: extend the semantic-extraction prompt to require per-edge scoring with a worked example.

**If the team later wants schema enforcement for a public API:** prefer `jsonschema>=4.21` (pure-Python, ~150KB, no compiled deps) over `pydantic` v2 (Rust wheel, ~6MB, transitive `pydantic-core`). Even then, defer until v1.14+.

---

### 2. C-1 Cross-repo concept identity federation — **string/path heuristics first, embeddings deferred**

**Recommendation: DO NOT add `sentence-transformers`, `all-MiniLM`, `faiss`, `chromadb`, or any embedding library in v1.13.**

**Why:**
- `sentence-transformers` pulls `torch` (~800MB CPU wheel, ~2GB CUDA). That would dwarf graphify's entire install footprint and break the "no system dependencies for core" promise in CLAUDE.md.
- Concept nodes already have stable `id`s from `_make_id()` (slugified labels). Cross-repo dedup is fundamentally a *label-space* problem: two `repo_identity` values produce two MOC notes for `transformer` because the namespace differs, not because the labels differ. The fix is namespace-aware: union-find over (label-normalized, file-type=concept) tuples, scoped per the new federation policy. This is pure stdlib.
- graspologic does NOT ship entity-resolution helpers usable here — graspologic.match (graph matching) operates on isomorphism, not label-similarity, and is overkill for MOC dedup.
- For the small fraction of "near-miss" cases (e.g., `attention` vs `attention_mechanism`), `difflib.SequenceMatcher` (stdlib) gives 80% of fuzzy-matching value. `rapidfuzz` (3.x) is a possible *future* optional extra — it's pure-Rust-wheel, ~500KB, no transitive deps — but reject for v1.13 unless the C-1 plan demands it after a heuristic baseline exists.

**Defer-list (only revisit if v1.14+ needs semantic dedup):**
| Candidate | Verdict | Notes |
|-----------|---------|-------|
| `rapidfuzz>=3.6` | Possible future `[fuzzy]` extra | Pure wheel, no torch, well-maintained. Skip until heuristics measurably fall short. |
| `sentence-transformers` | **Reject** | torch dep is incompatible with graphify install profile. |
| `chromadb` / `faiss` | **Reject** | Out of scope; graphify does not store vectors. |

---

### 3. C-3 Edge-level concept drift detection — **NetworkX + stdlib, no new dep**

**Recommendation: DO NOT add `deepdiff`, `dictdiffer`, or any diff library.**

**Why:**
- Drift detection here means: when a community renames (community membership of node X changes between runs), find `implements`-typed edges whose endpoints now span communities they used to share, and surface them as orphaned.
- This is a per-edge set comparison between two graph snapshots: `edges_t1 ∩ edges_t2` with predicate `community(src) == community(dst)`. NetworkX gives `G.edges(data=True)` and node-attribute access. Total: ~30 lines.
- `deepdiff>=8.x` (~700KB with `orderly-set` transitive) is overpowered: it's designed for nested arbitrary-shape diffs, whereas graphify's snapshots are uniform `(src, dst, relation, community_src, community_dst)` tuples. Sets of tuples + `symmetric_difference` is the right primitive.
- For storing prior snapshots: reuse the existing `graphify-out/cache/` directory pattern (SHA256-keyed, JSON files). No new dep.

**What to add (code, not deps):**
- `graphify/drift.py` (new module) producing `{orphaned_edges: [...], renamed_communities: [...]}`.

---

### 4. C-4 Parameterized `concept_code_hops` — **stdlib only**

**Recommendation: No DSL library. Use a small dataclass-based filter.**

**Why:**
- The filter surface is bounded: `relations: set[str] | None`, `min_confidence_score: float`, `confidence_levels: set[Literal["EXTRACTED","INFERRED","AMBIGUOUS"]]`, `max_hops: int`. That's a closed schema, not user-authored expressions.
- Adding a DSL parser (e.g., `lark`, `pyparsing`) would be 10x the implementation cost vs. a `dataclass(frozen=True)` + a single edge-predicate function passed to `nx.bfs_edges` / a custom traversal.
- CLI exposure: argparse already handles comma-separated lists (`--concept-relations implements,documents`). No new dep.

**What to add (code, not deps):**
- `graphify/query.py` (or extend `serve.py`): `HopFilter` dataclass + `traverse_concept_code(graph, start, hop_filter)` helper.

---

### 5. V-1, A-1, A-2, A-3 — **stdlib only**

- V-1 vault Option B silent reroute: `pathlib`, existing `security.py` confinement helpers. No new dep.
- A-1 Nyquist VALIDATION.md gap-fill: docs only.
- A-2 stderr two-line format sweep: `sys.stderr` + existing `[graphify]` prefix convention.
- A-3 retroactive seed traceability: docs only.

---

## Recommended Stack (v1.13 deltas)

### Core / Frameworks / Database — **no changes**

### Supporting Libraries — **no additions**

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none added in v1.13) | — | — | — |

### Optional Extras (`pyproject.toml [project.optional-dependencies]`) — **no additions**

The existing extras (`[mcp]`, `[neo4j]`, `[pdf]`, `[watch]`, `[leiden]`, `[office]`, `[routing]`, `[dedup]`, `[all]`) cover all v1.13 needs. Specifically:
- `[leiden]` already supports C-1's optional community-aware dedup pass.
- `[routing]` already brings PyYAML for any new federation profile reads.
- `[all]` umbrella requires no edit (no new extras to fold in).

### Version bump

`graphify` package version: bump to **`1.13.0`** in `pyproject.toml` per the standard milestone-ship cadence documented in CLAUDE.md (re-run `scripts/bump_version.py` and `scripts/sync_mcp_server_json.py`). This is a normal cadence step, not a stack change.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| C-2 structured output | stdlib `json.loads` + extended `validate.py` | `instructor>=1.6` | Requires bundling `anthropic`/`openai` SDK; graphify's LLM channel is the host agent. |
| C-2 schema validation | extend `validate.py` (returns `list[str]`) | `pydantic>=2.7` | 6MB Rust wheel, breaks pure-wheel install profile, conflict with existing validate-by-return style. |
| C-2 schema validation | extend `validate.py` | `jsonschema>=4.21` | Acceptable but unnecessary; current `validate.py` style is the project convention. Revisit if a public schema is published. |
| C-1 dedup | label-normalize + union-find (stdlib) | `sentence-transformers` + `all-MiniLM-L6-v2` | Pulls torch (~800MB), incompatible with "no system deps" promise. |
| C-1 fuzzy matching | `difflib.SequenceMatcher` | `rapidfuzz>=3.6` | Defer — only worth a `[fuzzy]` extra if heuristics measurably fail. |
| C-1 entity resolution | per-namespace union-find | `graspologic.match` | Designed for graph isomorphism, not label dedup. Wrong tool. |
| C-3 drift | set-of-tuples + `nx` attribute access | `deepdiff>=8.x` | Overpowered; uniform tuple shape doesn't need a generic diff engine. |
| C-3 snapshot store | existing `graphify-out/cache/` JSON | `sqlite3` (stdlib) / `lmdb` | Cache pattern is already established; introducing a second persistence model is unnecessary. |
| C-4 hop filter | `dataclass` + predicate fn | `lark` / `pyparsing` DSL | Closed bounded filter set; DSL is overengineering. |

---

## Installation

No `pip install` changes for contributors. Existing flow stands:

```bash
pip install -e ".[mcp,pdf,watch]"   # CI-matching deps, unchanged
pip install -e ".[all]"             # full optional surface, unchanged
```

---

## Integration with `[all]` umbrella

No edits needed. `[all]` already aggregates `mcp,neo4j,pdf,watch,leiden,office,routing,dedup`. Since v1.13 introduces no new extras, the umbrella stays in sync automatically.

---

## Sources

- `pyproject.toml` (existing extras, observed via priors 860, 4730)
- `graphify/build.py` `_normalize_concept_code_edges` and three-layer dedup (priors 704, 4426)
- `graphify/cluster.py` graspologic ImportError → Louvain fallback (prior 704); deterministic seed=42 (prior 4794)
- `CLAUDE.md` constraints: "No new required dependencies", Python 3.10/3.12 CI matrix, no system deps, label sanitization through `security.py`
- `.planning/research/STACK.md` v1.4 precedent (prior 1251) — same "stdlib-first, optional-extra-only-if-justified" stance
- Phase 53 prior (4107): four concept↔code relations + confidence schema already shipped — confirms `confidence_score` field already exists in the edge schema, so C-2 is field-population work, not field-introduction work
- Prior 5372: SEED-bidirectional-concept-code-links 65% shipped — confirms infrastructure is in place; v1.13 is incremental refinement
- HIGH confidence (architectural constraints are project-internal, verified against current source and CLAUDE.md, not from web search)

**Confidence: HIGH** — All recommendations derive from observable project constraints (no LLM SDK in tree, no system deps allowed, existing extras catalogue) rather than ecosystem speculation. The "don't add" stance is the disciplined call here and is preferred per the quality gate.
