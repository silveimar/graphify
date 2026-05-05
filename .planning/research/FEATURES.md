# Feature Research — graphify v1.13 Concept Intelligence & Audit Closure

**Domain:** Knowledge-graph / code-intelligence tooling layered on top of an existing concept↔code edge system
**Researched:** 2026-05-05
**Confidence:** MEDIUM-HIGH (cross-checked with Sourcegraph, GitHub stack-graphs, Microsoft GraphRAG, Cognee, Graphiti, Neo4j Cypher docs)

## Scope Reminder

v1.10–v1.11 already shipped: typed concept↔code edges (5 relations), EXTRACTED/INFERRED confidence schema, MCP `concept_code_hops`, `/trace`, node-level drift, `repo_identity` CLI arg + cross-repo helper in `analyze.py:169`, Obsidian bidirectional MOC↔CODE links. This research scopes the v1.13 *delta*: C-1 federation, C-2 per-edge LLM confidence, C-3 edge-level drift, C-4 parameterized queries, V-1 Vault Option B silent reroute, plus audit closure.

The "user" here is dual: (a) human developers reading reports / Obsidian vaults, (b) AI agents calling MCP tools. Feature framing must serve both.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| TS-1 | **Per-repo provenance on every federated node** (C-1) | Sourcegraph and stack-graphs both surface "this symbol resolves to repo X / commit Y." If we merge a `Transformer` concept across repos and the user can't see *which repo* contributed which evidence, federation is worse than no federation — it loses information. | MEDIUM | Add `repos: [{repo_identity, source_files, edge_count}]` aggregate to merged concept nodes. Already have `repo_identity` arg threaded through `analyze.py:169`; need to lift it from analysis-only into the node attribute itself. |
| TS-2 | **Stable identity rule that's documented and deterministic** (C-1) | Stack-graphs' contract is "file-incremental, isolated subgraphs that compose deterministically." Users expect that re-running across the same repos produces the same merged IDs. Anything LLM-driven for identity is a non-starter at this layer. | LOW-MEDIUM | Slug-based `_make_id()` already deterministic per-repo; federation key = normalized label + file_type. Document it explicitly in the report. |
| TS-3 | **Per-edge confidence is *actually* differentiated** (C-2) | The current uniform `1.0` from extract.py is a lie that downstream consumers (filters, agents, reports) silently rely on. GraphRAG, Cognee, and the calibration literature all treat undifferentiated edge scores as a known anti-pattern. If C-2 ships and 90% of edges still come back 0.9, users will stop trusting the field. | HIGH | See PITFALLS — calibration is the load-bearing problem, not prompt engineering. |
| TS-4 | **Confidence threshold filter on `concept_code_hops`** (C-4) | Cypher, GraphQL, and every production graph query language exposes `WHERE r.confidence_score >= $min`. If users can't say "show me only high-confidence implementations," per-edge scores from C-2 are decorative. | LOW | Add `min_confidence: float`, `relations: [str]` (already partially supported per `_parse_relations` at serve.py:2246), `confidence_band: ["EXTRACTED","INFERRED"]` to the existing tool. |
| TS-5 | **Drift surfaces "what changed" not just "things changed"** (C-3) | Graphiti's table-stakes UX: validity windows + reason-for-change ("edge was valid yesterday, the *target community* re-clustered today"). A drift report that just says "drifted" without naming the cause is noise. | MEDIUM | Reuse `_run_drift_nodes` snapshot pattern; add edge-level diff with classification: `{edge_added, edge_removed, target_community_changed, confidence_shifted}`. |
| TS-6 | **Vault writes are reversible / dry-run-able** (V-1) | Any silent file reroute that *can't* be inspected before it happens will get reverted on first user surprise. Obsidian users especially expect this. | LOW | `--dry-run` already a graphify pattern; ensure V-1 Option B reroute respects it and prints destination paths. |
| TS-7 | **Cross-repo identity is opt-in and labeled** (C-1) | Sourcegraph's federation requires explicit indexing; users opt in per-repo. Auto-merging two `User` classes from unrelated repos because the labels match is the #1 federation footgun. | LOW | Federation only triggers when `repo_identity` is set on >1 corpus; emit a warning + provenance trail when merges happen. |

### Differentiators (Competitive Advantage)

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D-1 | **Evidence-bearing INFERRED edges** (C-2) | GraphRAG emits `relationship_description` + `relationship_strength` together. If our INFERRED edge carries `evidence: "L42-58 of foo.py mentions X"` plus a calibrated `confidence_score`, agents can quote the evidence verbatim instead of trusting a number. Most graph systems give the number *or* the description, not both bound. | MEDIUM | Schema already allows `evidence` on EXTRACTED; extend INFERRED to require both `confidence_score` AND `evidence` snippet. |
| D-2 | **Drift classification taxonomy** (C-3) | Graphiti invalidates facts but doesn't categorize *why*. Categories like `community-reshuffle`, `code-deleted`, `concept-renamed`, `confidence-degraded` let users triage drift by cause. This is rare in production graph tools. | MEDIUM | Pure post-processing on two snapshots; no new infra. |
| D-3 | **Coverage lens query** (C-4) | "Show every concept whose `implements` edges sum to <2 — these concepts are under-coded." This is the inverse of god-node ranking and is what doc-quality reviewers actually want. Sourcegraph doesn't expose this; GraphRAG doesn't either. | MEDIUM | Aggregate over typed edges; piggyback on `concept_code_hops` infrastructure with an `aggregate: "coverage"` mode. |
| D-4 | **Calibration self-check report** (C-2) | A built-in section in `GRAPH_REPORT.md`: "INFERRED edge confidence histogram — 0.9 buckets contain 78% of edges; calibration likely degraded." Catches the "always 0.9" failure mode automatically. Almost no LLM-graph product self-audits its own confidence distribution. | LOW-MEDIUM | Pure stats over the graph; no LLM cost. |
| D-5 | **Federated provenance in Obsidian frontmatter** (C-1 × existing MOC↔CODE) | Each merged concept note carries `repos: [...]` frontmatter, queryable via Dataview. Turns federation into a navigable view, not just a graph property. | LOW | Extends existing v1.8 MOC subtree convention. |
| D-6 | **Seed-traceability footer** (audit closure) | Every artifact (drift report, federated node, INFERRED edge) carries `seed: SEED-bidirectional-concept-code-links § C-2` so users can trace any output back to the design decision that authorized it. | LOW | Convention + a small helper; pure metadata. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-merge concepts by string similarity / embeddings across repos** | "It would be smart if `User` and `UserModel` merged automatically." | Stack-graphs and Sourcegraph both refuse to do this — false-merge is unrecoverable, poisons cross-repo navigation, and conflicts with the deterministic identity rule (TS-2). The calibration literature also shows embedding-similarity scores are heavily miscalibrated. | Exact-label + file_type match only for federation. Surface "candidate merges" in a report; require explicit user opt-in via an alias file (out of scope for v1.13). |
| **Free-text Cypher / SPARQL endpoint** | "Just let me write Cypher against the graph." | Drags in Neo4j or graspologic-as-a-server, breaks the "no required deps" constraint, and exposes label-injection vectors that `security.py` would have to re-validate from scratch. Also: 95% of users want 5 query shapes, not arbitrary Cypher. | Parameterized, named query shapes (C-4): `concept_code_hops`, `coverage_lens`, `drift_diff`, each with explicit named parameters. |
| **Per-edge confidence as a single float without a band** | "Just give me 0.0–1.0, I'll threshold it myself." | The EXTRACTED/INFERRED band carries categorical information (AST-derived vs. LLM-inferred) that a single float erases. Calibration research (Mind the Confidence Gap, 2025) shows users systematically misinterpret raw floats without a categorical anchor. | Keep the band, *and* add `confidence_score` for INFERRED. Filters accept both `min_confidence` and `confidence_band`. |
| **LLM rescoring of EXTRACTED edges** | "Why don't we re-confidence-score the AST edges with an LLM too?" | EXTRACTED edges are deterministic and cheap. LLM-scoring them adds cost, non-determinism, and lowers calibration (an LLM doesn't know more than the AST about `class A: contains method_x`). | LLM scoring stays scoped to INFERRED edges where it has signal. |
| **Real-time / streaming drift detection** | "I want a webhook when an edge drifts." | Graphify is a batch tool; the watch-mode rebuild + drift-on-demand pattern matches user mental model. Real-time drift requires temporal-graph infra (Memgraph, Graphiti) we explicitly aren't taking on. | Drift is a `graphify drift` subcommand against two snapshots; users wire it to their CI if they want polling. |
| **Per-edge confidence emitted by a separate LLM call per edge** | "More calls = more accurate." | Cost explodes (N edges × 1 call). GraphRAG batches via "gleanings" — multi-turn extraction over the same chunk — for a reason. | Batch INFERRED edges by source chunk; one LLM call scores all edges from that chunk together. |

---

## Feature Dependencies

```
C-2 (per-edge confidence)
    └──required-by──> C-4 (parameterized confidence-filter queries)
                          └──required-by──> D-3 (coverage lens)
    └──enables──> D-4 (calibration self-check)
    └──enables──> D-1 (evidence-bearing INFERRED)

C-1 (cross-repo identity)
    └──required-by──> D-5 (federated Obsidian provenance)
    └──reuses──> existing repo_identity arg + analyze.py:169 helper

C-3 (edge-level drift)
    └──reuses──> _run_drift_nodes snapshot pattern (serve.py:2513)
    └──enhanced-by──> D-2 (drift taxonomy)

V-1 (Vault Option B silent reroute)
    └──independent──> can ship any time; gated only by TS-6 (dry-run)

Audit closure (Nyquist VALIDATION.md, stderr sweep, seed traceability)
    └──enables──> D-6 (seed-traceability footer)
    └──blocks──> v1.13 ship (must close v1.12 audit gaps before promoting)
```

### Dependency Notes

- **C-4 requires C-2:** Parameterized confidence filters are pointless if every edge is `1.0`. C-4 ships *after* C-2 lands and emits real distributions, or it ships as a no-op stub.
- **D-3 requires C-4:** Coverage lens is implemented as a parameterized query mode; without C-4's query infrastructure it has no surface to live on.
- **D-1 enhances C-2:** C-2 can technically ship score-only, but pairing score with evidence is what makes downstream agents trust it. Treat as same milestone.
- **D-4 catches C-2 regressions:** Calibration self-check is the test harness for C-2 in production. Ship them together or D-4 has nothing to check.
- **C-1 + D-5 are paired:** Federation that doesn't show up in the user-facing vault is invisible. D-5 is the smallest viable surface for C-1.
- **Audit closure blocks v1.13 ship, not feature work:** Phases can develop in parallel; the Nyquist gap-fill, stderr format sweep, and seed-traceability are *release gates*, not blockers for engineering.

---

## MVP Definition for v1.13

### Launch With (v1.13 core)

- [ ] **C-2 per-edge LLM confidence** — load-bearing for everything else; without it, the existing schema stays a uniform `1.0` lie.
- [ ] **D-1 evidence-bearing INFERRED edges** — pairs with C-2; cheap once C-2 is wired.
- [ ] **D-4 calibration self-check report section** — guards C-2 from regressing into "always 0.9".
- [ ] **C-4 parameterized `concept_code_hops`** with `min_confidence`, `relations`, `confidence_band` — turns C-2 into something users can actually filter on.
- [ ] **C-1 cross-repo identity federation** with TS-1 per-repo provenance + TS-7 explicit opt-in — completes the seed's federation arm.
- [ ] **C-3 edge-level drift** with D-2 classification taxonomy — completes the drift arm.
- [ ] **V-1 Vault Option B silent reroute** with TS-6 dry-run — independent but small enough to bundle.
- [ ] **Audit closure**: Nyquist VALIDATION.md gap-fill, stderr format sweep, D-6 seed-traceability footer.

### Add After Validation (v1.14+)

- [ ] **D-3 coverage lens query** — depends on C-4 shipping and being used in anger; defer to see what shapes users actually request.
- [ ] **D-5 federated Obsidian frontmatter** — wait for C-1 to prove federation is trusted before extending it into the vault.
- [ ] **Alias/override file for federation merges** — only if exact-label matching proves too restrictive in practice.

### Future Consideration (v2+)

- [ ] **Real-time drift via watch-mode integration** — only if users hit a clear pain point with batch drift.
- [ ] **Cross-graph query federation** (multiple `graphify-out/` dirs queried as one) — requires identity rules from C-1 to mature first.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| C-2 per-edge LLM confidence | HIGH | HIGH | P1 |
| C-4 parameterized queries | HIGH | LOW | P1 |
| D-1 evidence-bearing INFERRED | HIGH | MEDIUM | P1 |
| D-4 calibration self-check | MEDIUM | LOW | P1 |
| C-1 federation + TS-1 provenance | HIGH | MEDIUM | P1 |
| C-3 edge-level drift + D-2 taxonomy | MEDIUM | MEDIUM | P1 |
| V-1 Vault Option B + TS-6 dry-run | MEDIUM | LOW | P1 |
| Audit closure (Nyquist + stderr + D-6) | MEDIUM | LOW | P1 (release gate) |
| D-3 coverage lens | MEDIUM | MEDIUM | P2 |
| D-5 federated Obsidian frontmatter | MEDIUM | LOW | P2 |
| Auto-merge by similarity | LOW | HIGH | ANTI (do not build) |
| Free-text Cypher endpoint | LOW | HIGH | ANTI (do not build) |

---

## Competitor Feature Analysis

| Capability | Sourcegraph / SCIP | GitHub stack-graphs | Microsoft GraphRAG | Cognee | Graphiti | graphify v1.13 plan |
|---|---|---|---|---|---|---|
| Cross-repo identity | Compiler-accurate, version-aware via SCIP | File-incremental, deterministic path resolution (archived 2025-09) | N/A (text corpus, not multi-repo) | N/A | Per-source provenance | C-1: deterministic label+file_type, opt-in, per-repo provenance |
| Per-edge confidence | N/A (precise = binary) | N/A | `relationship_strength` numeric + description (LLM-emitted) | Confidence-scored eval reports, not per-edge | Score + validity window | C-2: INFERRED-only score + evidence; EXTRACTED stays binary |
| Drift / temporal | Version-aware navigation | N/A | N/A | N/A (rebuild model) | First-class validity windows + invalidation | C-3: snapshot diff with D-2 taxonomy |
| Parameterized query | GraphQL API + MCP server | N/A | Python query API | Vector + graph hybrid query | Cypher (Neo4j-backed) | C-4: named query shapes via MCP, no Cypher surface |
| LLM-as-confidence-source anti-pattern handling | N/A | N/A | Known issue (#1543: invents descriptions) | Eval framework catches it | N/A | D-4 calibration self-check (rare in this market) |

**Takeaway:** No single competitor pairs (per-edge confidence + evidence + calibration self-check + cross-repo provenance + drift taxonomy) in one tool. graphify v1.13's differentiator is the *combination*, not any single feature.

---

## Sources

- [Sourcegraph — Cross-repository code navigation](https://sourcegraph.com/blog/cross-repository-code-navigation) — SCIP-based federation, version-aware resolution
- [Sourcegraph — A New Era / Intelligence Layer](https://sourcegraph.com/blog/a-new-era-for-sourcegraph-the-intelligence-layer-for-ai-coding-agents-and-developers) — MCP server for cross-repo agent queries
- [github/stack-graphs (archived 2025-09)](https://github.com/github/stack-graphs) — file-incremental name resolution; archival itself is a signal
- [Stack Graphs: Name Resolution at Scale (arXiv 2211.01224)](https://arxiv.org/abs/2211.01224) — deterministic identity contract
- [Microsoft GraphRAG — Methods](https://microsoft.github.io/graphrag/index/methods/) — `relationship_strength` schema, gleanings pattern
- [GraphRAG Issue #1543 — LLM invents descriptions](https://github.com/microsoft/graphrag/issues/1543) — confirms anti-pattern is real in production
- [Cognee — GraphRAG building blocks](https://www.cognee.ai/blog/fundamentals/building-blocks-of-knowledge-graphs) — DataPoint model, eval framework
- [Optimizing the Interface Between KGs and LLMs (arXiv 2505.24478)](https://arxiv.org/abs/2505.24478) — confidence-scored eval reports
- [getzep/graphiti](https://github.com/getzep/graphiti) — temporal validity windows, invalidation-not-deletion pattern
- [Mind the Confidence Gap (arXiv 2502.11028)](https://arxiv.org/html/2502.11028v1) — LLM overconfidence calibration, anchors why D-4 matters
- [Calibration of LLMs in Biomedical NLP (PMC12249208)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12249208/) — relation-extraction LLMs are *poorly* calibrated; supports D-4 as table-stakes
- [Neo4j Cypher Parameters](https://neo4j.com/docs/cypher-manual/current/syntax/parameters/) — confirms C-4 named-parameter shape is industry-standard
