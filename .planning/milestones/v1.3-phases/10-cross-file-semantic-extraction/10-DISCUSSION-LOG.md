# Phase 10: Cross-File Semantic Extraction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 10-cross-file-semantic-extraction
**Areas discussed:** Similarity stack, Batch clustering heuristic, Canonical label & merge rules, Opt-in vs default-on

---

## Similarity Stack (Dedup Signals)

### Signals to use

| Option | Description | Selected |
|--------|-------------|----------|
| Fuzzy + local embeddings | difflib + sentence-transformers all-MiniLM-L6-v2 as optional `[dedup]` extra; enables GRAPH-04 stretch | ✓ |
| Fuzzy only (stdlib) | difflib.SequenceMatcher alone; drops GRAPH-04 stretch | |
| Fuzzy + rapidfuzz | C-backed fuzzy perf upgrade but same semantic blindspot | |
| Fuzzy + API embeddings | OpenAI/Voyage embeddings; violates "no network in unit tests" convention | |

**User's choice:** Fuzzy + local embeddings
**Notes:** Keeps offline/deterministic property; sentence-transformers transitive deps (torch, scikit-learn, scipy) are acceptable as an opt-in extra.

### Threshold policy

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative / high-precision | fuzzy ≥ 0.90 AND cosine ≥ 0.85; both must agree | ✓ |
| Balanced | fuzzy ≥ 0.82 OR cosine ≥ 0.78 | |
| Aggressive / high-recall | fuzzy ≥ 0.75 OR cosine ≥ 0.70 | |
| You decide | Claude picks conservative and exposes via CLI flags | |

**User's choice:** Conservative
**Notes:** Every merge still recorded in dedup_report even if rejected by safety nets, so recall can be recovered by inspection.

### Pipeline placement

| Option | Description | Selected |
|--------|-------------|----------|
| Blocking stage after extraction | extract → **dedup** → build_graph → cluster → ... | ✓ |
| Post-build, pre-cluster | Run on assembled NetworkX graph | |
| Opt-in staged run | Two-pass: separate `graphify dedup` subcommand | |

**User's choice:** Blocking stage after extraction
**Notes:** Fits existing pure-function pipeline; dedup_report written before graph HTML so auditors see merges first.

### Audit trail format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON + markdown + report section | `dedup_report.json` + `dedup_report.md` + "Entity Dedup" section in `GRAPH_REPORT.md` | ✓ |
| JSON only | Machine-readable only | |
| Report section only | Append to GRAPH_REPORT.md only | |

**User's choice:** All three outputs
**Notes:** Matches existing html+json+report triad; JSON is MCP-queryable.

---

## Batch Clustering Heuristic (Cross-File Extraction)

### File grouping strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: import-components capped by directory | Connected components of import graph, split on top-level directory boundaries | ✓ |
| Directory co-location only | Group by parent directory, no import pre-pass | |
| Import-graph components only | Pure import-adjacency, risk of giant clusters | |
| Content-similarity (embedding-based) | Embed file contents and cluster; flips dependency order | |

**User's choice:** Hybrid
**Notes:** Uses existing `_resolve_cross_file_imports` in extract.py; cheap incremental cost.

### Module location

| Option | Description | Selected |
|--------|-------------|----------|
| New `graphify/batch.py` library module | Sibling of extract.py, consumed by skill | ✓ |
| Skill-only orchestration | Inline in skill.md prose | |
| Inline into extract.py | Add to the already-2817-line extract module | |

**User's choice:** New `graphify/batch.py`
**Notes:** Keeps extract.py pure AST; makes batching unit-testable.

### Cluster size cap

| Option | Description | Selected |
|--------|-------------|----------|
| Token-budgeted soft cap | ~50K tokens default, `--batch-token-budget` flag | ✓ |
| Fixed file count | Hard N-files cap | |
| No cap | Trust natural import components | |

**User's choice:** Token-budgeted soft cap
**Notes:** Adapts to file-size variance; splits at lowest-degree boundary node.

### Ordering within cluster

| Option | Description | Selected |
|--------|-------------|----------|
| Topological order | Imported-first → importer-last; alphabetical on cycles | ✓ |
| Alphabetical / path-sorted | Deterministic but order-agnostic | |
| You decide | Claude picks topological, no CLI flag | |

**User's choice:** Topological order
**Notes:** Helps LLM build on earlier definitions.

---

## Canonical Label & Merge Rules

### Tie-break ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Longest → most-connected → alphabetical | Spec-aligned; excludes mtime for reproducibility | ✓ |
| Longest → most-connected → most-recent → alphabetical | Literal spec including mtime | |
| Most-connected → longest → alphabetical | Centrality-first | |
| File-type priority → longest → alphabetical | Code > document > paper > image | |

**User's choice:** Longest → most-connected → alphabetical
**Notes:** Determinism across machines matters more than freshness; no mtime.

### Edge merge math

| Option | Description | Selected |
|--------|-------------|----------|
| Sum weight, max confidence_score, EXTRACTED wins enum | Spec-aligned, source_file becomes list | ✓ |
| Sum weight, max confidence_score, preserve original enum | Can bury AST ground-truth | |
| Max weight, max confidence_score, EXTRACTED wins enum | Treats parallel edges as votes, not evidence | |

**User's choice:** Sum weight, max confidence_score, EXTRACTED-wins enum
**Notes:** EXTRACTED > INFERRED > AMBIGUOUS precedence prevents INFERRED overwriting AST facts.

### Provenance on canonical nodes

| Option | Description | Selected |
|--------|-------------|----------|
| Full list of source_files + merged_from IDs | Reversible, powers GRAPH-04 stretch | ✓ |
| Winner's source_file only + merged_from IDs | Loses cross-source citation | |
| Winner only, no merged_from | Lightest output, zero reversibility | |

**User's choice:** Full source_file list + merged_from
**Notes:** Required for `auth.py + docs.md + tests/` stretch verification example.

### Structural safety net

| Option | Description | Selected |
|--------|-------------|----------|
| Block merges across file_type by default | Opt-in via `--dedup-cross-type` | ✓ |
| Block merges on relation-set divergence | Heuristic, needs tuning | |
| No structural safety net | Trust thresholds | |
| You decide | Claude implements cross-type blocking default | |

**User's choice:** Block cross-file_type by default
**Notes:** Gateway to GRAPH-04 stretch; when opted in, cross-type uses embeddings only.

---

## Opt-in vs Default-On

### Run-time default

| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in via `--dedup` flag | Off by default, zero-surprise rollout | ✓ |
| On by default, opt-out via `--no-dedup` | Aggressive, breaks pinned node IDs | |
| On for new, opt-out for existing | Split-behavior by project state | |

**User's choice:** Opt-in via `--dedup`
**Notes:** Flip to default-on in a future minor after stability observed.

### Vault interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `--obsidian-dedup` flag + `legacy_aliases` | Vault stays safe; wikilink forward-map | ✓ |
| Always dedup when `--obsidian` is used | Risk of orphaned wikilinks in user notes | |
| Never dedup when `--obsidian` is used | Protects notes; Obsidian users miss the quality win | |

**User's choice:** Separate `--obsidian-dedup` flag with `legacy_aliases`
**Notes:** Obsidian adapter (`merge.py` / `mapping.py`) consumes `legacy_aliases` to update existing notes.

### MCP behavior on merged-away IDs

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to canonical + resolved_from_alias note | Agents don't break; telemetry-visible | ✓ |
| Return 404-like not-found | Strict; forces callers to update | |
| Return both canonical + legacy pseudo-node | Reintroduces the fragmentation we removed | |

**User's choice:** Transparent redirect with annotation
**Notes:** One dict lookup per query; dedup_report loaded alongside graph.json.

### Configuration surface

| Option | Description | Selected |
|--------|-------------|----------|
| CLI flags + `.graphify/dedup.yaml` override | Mirrors Obsidian profile pattern | ✓ |
| CLI flags only | Minimal surface | |
| Env vars + CLI flags | CI-friendly precedence chain | |

**User's choice:** CLI flags + `.graphify/dedup.yaml`
**Notes:** Reuses PyYAML already in `[obsidian]` extra — no new parser.

---

## Claude's Discretion

- `dedup_report.json` schema shape (stable v1 design to be finalized during planning)
- HTML viz tooltip format for merged canonical nodes
- Degree-centrality source (pre-dedup undirected graph degree is acceptable; no PageRank)
- Minimum cluster size below which batching is skipped (likely ≥2 files)

## Deferred Ideas

- LLM-as-judge final confirmation pass (Cognee pattern) — future phase
- Content-similarity clustering for batching — would flip dependency order
- `rapidfuzz` performance swap — only if difflib profiles as bottleneck
- Automatic threshold tuning per corpus — power-user feature
- Ontology-aware alignment rules (snake_case ↔ title case) — post-v1.3 augmentation
- Incremental dedup on Phase 6 delta machinery — optimization for v1.4+
