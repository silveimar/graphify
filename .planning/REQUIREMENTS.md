# Requirements — Milestone v2.0 Graph Schema Deepening

**Milestone goal:** Major-version schema upgrade adding temporal edge validity and reasoning-relation edge types, with a measurement-gated dedup spike, a carryover vault-cwd-gate fix, and a coordinated `graphifyy` 2.0.0 package version bump. Backward-compatible read of legacy graph.json fixtures preserved (precedent: CCONF `schema_version`).

**Phase numbering starts at:** Phase 71

**Hard non-goals:** No embeddings; no Postgres backend; no OB1 integration in v2.0 (deferred to seed).

---

## v2.0 Requirements

### Temporal Edge Validity (TEMP)

- [x] **TEMP-01**: Edges produced by `build.py` carry `valid_from` (timestamp of run that observed the edge) and optional `valid_until` (null = currently valid) attributes; emitted by `validate.py` as part of the edge schema and persisted in `graph.json` exports.
- [x] **TEMP-02**: Edges carry a `decay_weight` float in `[0.0, 1.0]` whose default is `1.0` for `EXTRACTED` edges (no decay) and decays per-relation for `INFERRED` edges according to `valid_from` age, configurable per relation type.
- [ ] **TEMP-03**: When `cache.py` re-runs against a corpus and an INFERRED edge from a prior run is no longer produced, the edge's `valid_until` is stamped with the current run timestamp instead of the edge being silently dropped; superseded edges remain in the on-disk graph for history but are excluded from `analyze.py` god-node and surprising-connection scoring by default.
- [ ] **TEMP-04**: `report.py` GRAPH_REPORT.md surfaces a "Temporal Health" sub-section showing counts of currently-valid vs superseded edges and the decay-weight distribution; `wiki.py` per-community articles flag edges with `valid_until` set as historical context rather than current relations.

### Reasoning-Relation Edge Types (REAS)

- [ ] **REAS-01**: `validate.py` accepts five new reasoning relations on document/concept-typed nodes: `supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`; rejects them on code-typed nodes (whose relations remain structural: `calls`/`imports`/`contains`/`defines_*`).
- [ ] **REAS-02**: `extract.py` semantic-extraction prompts for documents (md/txt/rst), papers (PDF), and rationales emit reasoning-relation edges with `confidence` (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`) and per-edge `confidence_score` (continuing the CCONF v1.13 contract); the prompts include explicit examples for ADR supersession and contradiction detection.
- [ ] **REAS-03**: `analyze.py` produces a new "Contradictions and Supersession Chains" analysis section listing detected contradiction pairs and supersession chains (longest first), each with source-node citations and confidence scores; isolated reasoning-edge nodes are NOT misclassified as knowledge gaps.
- [ ] **REAS-04**: `report.py` GRAPH_REPORT.md and `wiki.py` per-community articles render reasoning chains (e.g. "ADR-0042 supersedes ADR-0028 (confidence 0.91)") as first-class relations alongside structural ones; Obsidian export preserves them as typed wikilinks distinguishable from structural relations in the rendered note frontmatter.

### Content-Fingerprint Dedup Spike (DEDUP)

- [ ] **DEDUP-01**: A measurement-only spike resolves `Q-2026-05-07-01` (`.planning/research/questions.md`) by running graphify against a representative multi-source corpus (≥1 code repo + ≥1 doc-heavy directory + ≥1 PDF/paper set), reporting the near-duplicate concept-node rate using SHA-256 fingerprinting of normalized labels/descriptions, and producing a ship/defer recommendation with concrete numbers. Implementation lands ONLY if the spike clears the >5% threshold AND duplicates are confirmed genuine collisions; otherwise the spike artifact is the deliverable and dedup is deferred to a future milestone.

### Vault-CWD Argparse Fix (VBUG)

- [ ] **VBUG-01**: Running `graphify update-vault` (and every other gated command sharing the same defect) from a vault CWD with no `--vault` flag completes successfully — the auto-adopt notice prints AND the command does not exit with code 2. Fix is applied uniformly across every command that registers `--vault required=True` behind `_check_vault_cwd_gate`. Resolves `.planning/debug/vault-cwd-gate-argparse-required.md` (carried over from v1.12).
- [ ] **VBUG-02**: A regression test under `tests/test_vault_cwd_gate.py` exercises every gated subcommand from a fixture vault CWD without `--vault`, asserting non-zero argparse exits do not occur and the auto-adopt stderr breadcrumb is emitted; the debug session's status field flips from `diagnosed-pending-fix-phase` to `resolved` with the fix-phase reference recorded.

### Package Version Bump (PKG)

- [ ] **PKG-01**: `pyproject.toml` `version = "2.0.0"` (PyPI name `graphifyy`); `python scripts/bump_version.py 2.0.0` runs cleanly; `pip install -e ".[mcp,pdf,watch]"` reinstalls without error; `graphify --version` reports `2.0.0`.
- [ ] **PKG-02**: `python scripts/sync_mcp_server_json.py` regenerates `mcp/server.json` with the new manifest hash incorporating `graphify_version = 2.0.0`; `graphify install` writes a fresh `.graphify_version` stamp next to each platform `SKILL.md`; full pytest suite is green on Python 3.10 AND 3.12 post-bump.

---

## Future Requirements (deferred from v2.0)

- **OB1-RECIPE-01..04** — Ship graphify as `recipes/repo-graphify` for OB1 (adapter writes nodes/edges into `graph_nodes`/`graph_edges` or `entities`/`edges`, preserves community + temporal metadata). Tracked: `SEED-ob1-recipe-repo-graphify`.
- **MCP-ALIGN-01..02** — Align `serve.py` MCP tool surface with ob-graph's 10 tools (`get_neighbors`, `multi_hop`, `shortest_path`, etc.) for OB1 interop. Pairs with OB1-RECIPE seed; activate together.
- **DEDUP-02..N** — Implement node-level content-fingerprint dedup if the v2.0 DEDUP-01 spike clears the threshold.

## Out of Scope (explicit exclusions)

- **Embedding-based clustering or similarity search.** Graphify's `cluster.py` is intentionally Leiden topology-only. Adding embeddings would require a separate design decision (`.planning/notes/ob1-comparison-2026-05-07.md` § Hard non-goals).
- **Postgres/Supabase persistence layer.** Filesystem JSON + optional Neo4j export remains the deployment shape. OB1's storage-layer coupling is wrong for graphify (same source).
- **Capture/import recipes** for chat exports, email, social media (Slack/Gmail/X/IG/ChatGPT). Those are OB1's mission, not graphify's.

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| TEMP-01 | Phase 71 | Complete |
| TEMP-02 | Phase 71 | Complete |
| TEMP-03 | Phase 71 | Pending |
| TEMP-04 | Phase 71 | Pending |
| REAS-01 | Phase 72 | Pending |
| REAS-02 | Phase 72 | Pending |
| REAS-03 | Phase 72 | Pending |
| REAS-04 | Phase 72 | Pending |
| DEDUP-01 | Phase 73 | Pending |
| VBUG-01 | Phase 74 | Pending |
| VBUG-02 | Phase 74 | Pending |
| PKG-01 | Phase 75 | Pending |
| PKG-02 | Phase 75 | Pending |
