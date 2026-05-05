# Domain Pitfalls — graphify v1.13 Concept Intelligence & Audit Closure

**Domain:** Code knowledge graphs with typed edges, file-hash LLM caching, Leiden communities, multi-platform skill distribution
**Researched:** 2026-05-05
**Scope:** Pitfalls specific to ADDING cross-repo entity resolution, per-edge LLM confidence scoring, drift detection, query DSL, vault reroute, and audit closure to graphify's existing v1.10–v1.12 pipeline.

---

## Critical Pitfalls

These cause rewrites, silent data corruption, or break v1.10–v1.12 graph artifacts.

---

### Pitfall 1: False-Positive Concept Merges in Cross-Repo Federation
**Domain:** Cross-repo entity resolution
**What goes wrong:** Two repos each define `class User`, `def authenticate`, or a "Pipeline" concept — graphify federation merges them by name (or normalised id `user`) into a single node. The merged graph now claims the auth-service `User` calls billing-service `User.charge()`, which is a phantom edge.
**Why it happens:** graphify's `_make_id()` is a deterministic slug of the label. When two corpora are unioned without namespace prefixing, identical slugs collide. Leiden then happily clusters the phantom-merged node based on the union of both repos' edges.
**Consequences:**
- God-node analysis lies (the merged `User` looks like a hub spanning two domains).
- Drift detection (Phase 6X) flags massive "drift" the moment a second repo is added.
- Wikilinks in `obsidian/` vault point to a single note that conflates two real classes — users edit it and lose context for one or both.
**Prevention:**
- **Namespace by repo origin, merge only by explicit signal.** Default to `repo:<name>/<id>` for federated nodes. Promote to a merged canonical node ONLY when (a) labels match AND (b) at least one shared structural neighbour exists (shared import, shared concept edge with confidence ≥ EXTRACTED) AND (c) embedding/lexical similarity of source-context > threshold. This is the pattern Sourcegraph SCIP uses (symbol roles + monikers per package) and what GraphRAG's "entity disambiguation" stage adds on top of name match.
- **Record merge provenance on the node:** `merged_from: ["repo_a:user", "repo_b:user"]`, `merge_reason: "shared_neighbour+lexical_0.92"`. Without provenance, users cannot audit or unmerge.
- **Provide an unmerge escape hatch** — a CLI flag or profile rule that splits a merged node back into namespaced children. Cognee's failure mode: silent merges with no rollback path.
**Detection:** Sudden god-node degree spike when adding a repo; communities merging that previously had zero cross-edges; user reports of "wrong" wikilinks.
**Phase that must address:** Federation phase. Required: namespace-by-default + multi-signal merge + provenance fields in `validate.py` schema + unmerge CLI.

---

### Pitfall 2: Per-Edge LLM Confidence Cache Explosion / Invalidation Cascade
**Domain:** Per-edge confidence scoring
**What goes wrong:** v1.12's cache is keyed on file hash. Adding per-edge LLM confidence means the cache must also key on (a) the prompt template version, (b) the model name/version, (c) the edge endpoints, and (d) the file hashes of BOTH endpoint files. A tweak to the scoring prompt invalidates the entire cache; one file edit invalidates every edge touching it (potentially 100s of edges per file).
**Why it happens:** Naive implementations attach confidence to the edge dict and rely on the existing file-hash cache. But the existing cache stores `extraction-by-file`, not `score-by-edge` — so a prompt-only change cannot be detected, and stale scores persist silently.
**Consequences:**
- Token-cost blow-up: a prompt iteration during development re-scores every edge in every fixture corpus on every test run if mocking is incomplete.
- Stale scores: changing the prompt to fix a known bug leaves old scores cached for users who don't bust the cache.
- Test flakiness: any test depending on confidence values breaks when the prompt is touched.
**Prevention:**
- **Two-tier cache:** keep the existing file-hash cache for extraction; add a SEPARATE `scores/` cache keyed on `sha256(prompt_template + model_id + edge_signature + endpoint_file_hashes)`. Both endpoint hashes must appear — invalidate when EITHER endpoint changes.
- **Pin a `prompt_version` constant** in source and include it in the cache key. Bumping it is an explicit, reviewable act.
- **Batch-score per file pair**, not per edge — one LLM call returns N scores. Reduces cost ~10–50× on dense graphs (this is the pattern LangChain's `RAGAS` and DSPy use for per-claim scoring).
- **Test rule:** all confidence-scoring tests must use a `mock_score()` fixture that returns deterministic floats keyed on edge_signature. Never call the real LLM in tests.
**Detection:** CI runtime jumps after a prompt change; `graphify-out/cache/scores/` size grows faster than `extraction/`; nondeterministic test failures.
**Phase that must address:** Confidence scoring phase. Required: schema field for `prompt_version`, separate cache directory, mock-score fixture in `conftest.py`, batched scoring API.

---

### Pitfall 3: Backward-Compat Break in `validate.py` for v1.10–v1.12 Graphs
**Domain:** Schema evolution
**What goes wrong:** v1.13 adds `confidence_score` requirement on INFERRED edges, or makes `prompt_version` mandatory, or adds a new required field — and `validate.py` rejects every existing v1.10–v1.12 graph artifact on load. Users who run `graphify query` against a saved graph from a week ago get a hard validation error.
**Why it happens:** validate.py uses frozensets of allowed values (per the May 3 observation: "Concept↔Code Relation Values Confirmed in Both Frozensets"). Adding values is safe; tightening required-field rules is not.
**Consequences:**
- Cached graphs in user vaults become unreadable mid-milestone.
- Tests pass (fixtures regenerated) but real users hit errors.
- Obsidian vault re-runs explode because the loader rejects last week's graph before the adapter can refresh it.
**Prevention:**
- **All new fields are OPTIONAL on read, REQUIRED on write.** Loader fills defaults (`confidence_score: None`, `prompt_version: "legacy"`); writer enforces the new shape.
- **Add a `schema_version` field** to the graph metadata; loader switches behaviour on version. v1.13 reads v1 (legacy), v2 (v1.10), v3 (v1.13) and writes v3.
- **Test matrix must include a v1.10 fixture and a v1.12 fixture** loaded by v1.13 code — assert no errors.
- **Never remove a value from a frozenset** without a deprecation cycle; only add.
**Detection:** Tests against committed legacy fixtures fail; Obsidian reruns error on existing vaults.
**Phase that must address:** Every phase touching `validate.py` schema. Add a "legacy fixture load" test as a phase-success criterion.

---

## Moderate Pitfalls

### Pitfall 4: Drift Detection Confused by Community Renames
**Domain:** Drift detection
**What goes wrong:** Leiden community membership is stable (seed=42 per CLAUDE.md), but community NAMES are LLM-generated from member labels. A single new member node can shift the LLM-chosen name from "Auth Service" to "Authentication & Sessions" — drift detection flags this as concept drift when nothing has actually drifted.
**Prevention:**
- **Anchor drift on membership Jaccard, not name string.** Compute `J = |members_t ∩ members_t-1| / |members_t ∪ members_t-1|`; drift only when `J < 0.5` AND god-node has changed. Names are display only.
- **Snapshot only community membership + god-node + edge-confidence histogram** — not full graphs. ~5KB per snapshot; 100 snapshots = 500KB, acceptable. Storing full graphs blows out `graphify-out/` size.
- **Whitelist "stable" relations** (EXTRACTED `defines_class`, `defines_function`, `imports`) from drift entirely — these only change when code changes, and code-change drift is already visible in git.
**Detection:** Drift report flags >30% of communities every run; users disable the feature.
**Phase:** Drift detection phase. Required: membership-Jaccard metric, snapshot schema doc, exclude-list for stable relations.

### Pitfall 5: Query DSL Overdesign (Mini-Cypher Trap) or Underdesign
**Domain:** Parameterized query DSL
**What goes wrong:** Either (a) the DSL grows toward Cypher (`MATCH (a)-[r:CALLS*1..3]->(b) WHERE …`) — a 6-month rabbit hole with parser bugs and security holes; or (b) the DSL is two flags (`--relation`, `--min-confidence`) and users immediately need a third (`--exclude-community`) which forces a breaking change.
**Prevention:**
- **Pick a fixed, finite parameter set up front:** `relation`, `min_confidence`, `confidence_class` (EXTRACTED/INFERRED/AMBIGUOUS), `community`, `node_type`, `depth`. Six parameters. Document that this is the surface; no string DSL.
- **Expose the same six parameters identically in CLI flags AND the MCP tool schema.** No parameter that exists only in one surface.
- **Reject string-DSL requests in v1.13.** If users want Cypher, the existing `--neo4j-push` exporter is the answer; graphify's role is curation, not query language.
- **MCP surface bloat:** add ONE new tool (`query_graph`) with the parameter object, not six tools.
**Phase:** Query DSL phase. Required: explicit parameter list in CONTEXT.md; NO string parser.

### Pitfall 6: Silent Vault Reroute Violates Principle of Least Surprise
**Domain:** Vault Option B reroute
**What goes wrong:** User runs `graphify` from inside a vault subdirectory; output silently reroutes to a vault-relative path instead of `./graphify-out/`. User goes looking for output in cwd, can't find it, files a bug, or worse — re-runs with `--force` thinking the previous run failed.
**Prevention:**
- **Always emit a single stderr line on reroute:** `[graphify] vault detected at <path>; writing to <vault>/graphify-out/ (use --no-vault-reroute to disable)`. One line, every run, no `--quiet` suppression for this specific message.
- **Add `--explain-paths` flag** that prints the resolved output dir, profile path, and reroute decision tree, then exits. Cheap to implement, kills 80% of "where did my output go" bugs.
- **Never reroute on first run if `graphify-out/` already exists in cwd** — that's user intent. Reroute only when cwd has no prior output.
- **Test:** assert the stderr line appears on every reroute path.
**Phase:** Vault reroute phase. Required: stderr line + `--explain-paths` + cwd-priority rule.

### Pitfall 7: Audit Closure Rubber-Stamping
**Domain:** Retroactive VALIDATION.md gap-fill
**What goes wrong:** "Closing" Nyquist VALIDATION.md gaps for already-shipped phases becomes a checkbox exercise — author adds boilerplate "validated ✓" entries without re-running validation, or worse, copies entries between phases and the entries no longer correspond to the actual delivered code.
**Prevention:**
- **Each retroactive VALIDATION.md entry must cite a SHA** (the commit that delivered the validated behaviour) AND a test file/path that proves it. No SHA → not closed.
- **Run the cited test before stamping.** Closure phase must execute `pytest <cited_test>` per entry and store the result. The May 3 observation pattern (cite Phase 62 SHAs in v1.12 audit) is the model.
- **Do NOT add new behaviour during closure.** If a gap reveals missing code, that's a new phase, not a closure entry.
- **Diff-style review:** closure PR shows VALIDATION.md before/after side-by-side; reviewer checks every SHA link resolves.
**Phase:** Audit closure phase. Required: SHA + test path per entry; closure runs the cited tests.

### Pitfall 8: Stderr Format Sweep Breaks Downstream Parsers
**Domain:** Stderr format normalisation
**What goes wrong:** v1.13 normalises `[graphify] ...` stderr formatting (consistent prefix, structured fields). Skill files for 7 platforms parse stderr with regex — Codex skill greps for `warning`, OpenCode greps for `error:`. A format sweep breaks one or more of these silently because skill files are markdown, not test-covered.
**Prevention:**
- **Audit all 7 platform skill files for stderr parsing BEFORE the sweep.** Grep skills/ for `stderr`, `warning`, `error`, regex patterns over `[graphify]`.
- **Keep the legacy substring** (`warning`, `error`) as part of the new format (`[graphify] error: <msg>` not `[graphify] [ERR] <msg>`). Substring-grep callers keep working.
- **Add an integration test** that runs the CLI with known-failure inputs and asserts stderr matches BOTH the new structured format and a legacy-substring regex.
- **Bump skill `.graphify_version` stamp** so users running `graphify install` get refreshed skills — but this only helps users who reinstall. The substring-compat strategy protects users who don't.
**Phase:** Stderr sweep phase. Required: skill-file audit + substring-compat + dual-assertion test.

---

## Minor Pitfalls

### Pitfall 9: Confidence Score Clustering at 0.85
**What:** LLMs asked for a 0.0–1.0 score concentrate output in [0.7, 0.9] — the histogram is useless for ranking.
**Prevention:** Ask for a discrete bucket (`HIGH`/`MEDIUM`/`LOW`) and map to numeric, OR ask for pairwise comparison ("which is more confident, A or B?") and derive scores via Bradley–Terry. Both are documented patterns in DSPy/RAGAS literature. Do not ask for raw 0–1 floats.

### Pitfall 10: Cache Directory Path Confinement
**What:** New `scores/` cache directory must live inside `graphify-out/` per `security.py` path-confinement rules. Easy to accidentally write to `~/.cache/graphify` for "user-global" reuse and bypass confinement.
**Prevention:** Reuse `default_graphify_artifacts_dir()` for the new cache root; reject any code path that constructs cache paths from `os.path.expanduser`.

### Pitfall 11: Federation Determinism
**What:** Cross-repo merges may depend on iteration order of input repos — merge `A∪B` produces a different graph than `B∪A` if tie-breakers aren't deterministic.
**Prevention:** Sort input repos lexicographically by name before federation; sort merge candidates by (label, repo_name) before applying merge rules.

### Pitfall 12: Drift Snapshot Storage in Vaults
**What:** If snapshots land in `graphify-out/obsidian/` they pollute the vault and Obsidian indexes them as notes.
**Prevention:** Snapshots go to `graphify-out/drift/` (non-vault subtree); the Obsidian adapter's profile filter must exclude this directory.

### Pitfall 13: MCP Tool Description Drift
**What:** Adding `query_graph` to MCP without updating `server.json` manifest hash leaves the tool registered but unannounced; agents don't discover it.
**Prevention:** Run `python scripts/sync_mcp_server_json.py` as part of phase success criteria; version bump rule already documented in CLAUDE.md.

---

## Phase-Specific Warning Matrix

| Phase Topic | Critical Pitfalls | Moderate | Minor |
|-------------|-------------------|----------|-------|
| Cross-repo federation | #1 (false merges), #3 (schema compat) | — | #11 (determinism) |
| Per-edge confidence scoring | #2 (cache cascade), #3 (schema) | — | #9 (0.85 clustering), #10 (path confinement) |
| Drift detection | #3 (schema) | #4 (rename noise) | #12 (vault pollution) |
| Query DSL / MCP surface | — | #5 (over/under design) | #13 (manifest sync) |
| Vault Option B reroute | — | #6 (silent reroute) | — |
| Audit closure (Nyquist) | — | #7 (rubber-stamp) | — |
| Stderr format sweep | — | #8 (parser break) | — |

---

## Cross-Cutting Test/Cache Implications

1. **Every phase touching schema** must add a load-legacy-fixture test (Pitfall #3).
2. **Every phase calling LLMs** must use mocked scoring, never real network (CLAUDE.md test convention + Pitfall #2).
3. **Every phase adding a cache subdirectory** must respect `default_graphify_artifacts_dir()` and stay inside `graphify-out/` (Pitfall #10).
4. **Every phase touching CLI surface or stderr** must audit the 7 platform skill files (Pitfall #8).

---

## Sources

Confidence levels:
- HIGH: graphify codebase observations (CLAUDE.md, validate.py frozenset behaviour, cache.py file-hash design, May 3 SHA-citing audit pattern, _PLATFORM_CONFIG 7-platform list, default_graphify_artifacts_dir).
- MEDIUM (production-pattern parallels, training-data based, not freshly verified):
  - Sourcegraph SCIP symbol roles & monikers as namespace-by-package pattern (sourcegraph.com/docs/code-search/types/scip)
  - Microsoft GraphRAG entity disambiguation pipeline (github.com/microsoft/graphrag)
  - DSPy / RAGAS pairwise scoring vs raw float patterns
  - Cognee's known weakness: silent merges without provenance (community discussion)
- LOW: specific token-cost numbers — flagged as "potentially 10–50×" rather than precise.

WebSearch was not run for this synthesis (analysis grounded in graphify's existing pipeline + well-known production patterns from training data); recommend the federation-phase author re-verify Sourcegraph SCIP and GraphRAG disambiguation links at phase-research time, since those projects iterate quickly.
