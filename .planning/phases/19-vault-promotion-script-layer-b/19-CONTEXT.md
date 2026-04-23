# Phase 19: Vault Promotion Script (Layer B) - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

A new standalone module `graphify/vault_promote.py` and CLI subcommand `graphify vault-promote --vault PATH --threshold N` that reads `graphify-out/graph.json` + `GRAPH_REPORT.md`, classifies and degree-gates nodes, and writes promoted Obsidian markdown notes directly into Ideaverse Pro 2.5 destination folders with full frontmatter, wikilinks, and a 4-namespace tag taxonomy. Pure file I/O — no `serve.py` changes, no MCP tools, no merge-with-review flow. Write-only semantics: never overwrite foreign files; overwrite self-created files only when prior-run content hash matches.

**Scope adjustment during discussion:** Scope expanded from VAULT-01..05 to VAULT-01..07 to include profile write-back (VAULT-06) and hybrid 3-layer tag taxonomy (VAULT-07). REQUIREMENTS.md needs VAULT-06 and VAULT-07 rows added during planning.

</domain>

<decisions>
## Implementation Decisions

### Scope
- **D-01:** Phase 19 ships VAULT-01..07 (7 REQ-IDs total). VAULT-06 and VAULT-07 are folded in from the design note in `.planning/notes/layer-b-vault-promotion-design.md` and must be added to `.planning/REQUIREMENTS.md` during planning.
- **D-02:** Tag taxonomy ships 4 namespaces: `garden/*`, `source/*`, `graph/*`, `tech/*`. VAULT-02's mandatory three (`garden/*`, `source/*`, `graph/*`) remain required; `tech/*` is added when `source_file` extensions imply a language/stack.
- **D-03:** Layer 3 (auto-detected tags from `graph.json`) both applies to this run's notes AND writes back to `.graphify/profile.yaml` via union-merge (VAULT-06). Write-back is safe (atomic temp-file + rename), union-only (never removes), deduplicated, sorted.

### Architecture
- **D-04:** `vault_promote.py` is a new standalone module. It does NOT import `graphify.export.to_obsidian` or `graphify.merge.compute_merge_plan`. The write-only contract is strict enough that reusing the merge engine would pay for behavior we do not want (SKIP_CONFLICT, UPDATE, REPLACE, ORPHAN).
- **D-05:** CLI exposed as subcommand `graphify vault-promote --vault PATH --threshold N` (matches the `graphify harness` / `graphify approve` / `graphify install` family, not the `--obsidian` flag family).
- **D-06:** `vault_promote.py` REUSES: `profile.py` loaders (`load_profile`, `validate_profile`), `security.py` guards (`validate_vault_path`, `safe_filename`, `safe_tag`, `safe_frontmatter_value`), `builtin_templates/` (`thing.md`, `moc.md`, `statement.md`, `person.md`, `source.md`, `community.md`, plus new `question.md` and `quote.md`), and `analyze.py` outputs (`god_nodes()`, `knowledge_gaps()`).
- **D-07:** `vault-promote` and the existing `graphify approve` flow coexist independently. Neither supersedes the other; users pick based on whether they want merge-with-review (`approve`) or direct write-only (`vault-promote`).

### Classifier & Scoring
- **D-08:** `--threshold N` gates on **node degree only** (`G.degree(node) >= N`). `graphifyScore` in frontmatter is the degree value.
- **D-09:** `Atlas/Dots/Questions/` is populated from `analyze.py::knowledge_gaps()` output. These nodes are **always promoted regardless of threshold** — knowledge gaps are a separate track.
- **D-10:** `Atlas/Dots/Things/` is populated from `analyze.py::god_nodes()`, filtered to `file_type != "code"`. Code entities (classes, functions, endpoints) are never promoted as their own notes; they appear only as backlink references inside Things notes.
- **D-11:** All 7 folders are supported with heuristic dispatch:
  - **Things** → god_nodes with `file_type != "code"`
  - **Questions** → `knowledge_gaps()` output (isolated, thin-community, high-ambiguity)
  - **Maps** → one MOC per community/cluster (driven by cluster.py output)
  - **Sources** → one note per unique `source_file` (deduped)
  - **People** → labels matching regex `^[A-Z][a-z]+ [A-Z][a-z]+$`
  - **Quotes** → nodes with `file_type='document'` AND label containing quote marks (`"`, `"`, `"`, `«`, `»`)
  - **Statements** → nodes with at least one outgoing edge where `relation='defines'`
- **D-12:** Cluster MOC frontmatter (Maps): `stateMaps: 🟥`, `collections:` union of member Things, `up: [[Atlas]]`. No `related:` key (Maps aggregate, they don't relate).

### Write Semantics & Idempotency
- **D-13:** Re-run strategy: **overwrite self, skip foreign.** A sidecar manifest at `graphify-out/vault-manifest.json` maps `path → last-written-content-hash`. Decision table:
  - Path in manifest AND disk-hash == manifest-hash → overwrite freely
  - Path in manifest AND disk-hash != manifest-hash → skip + log as user-modified
  - Path NOT in manifest AND file exists on disk → skip + log as foreign
  - Path NOT in manifest AND file absent → write
- **D-14:** Collision handling: skip + record in `import-log.md` under `## Skipped` with path and reason. The run proceeds; no stderr warning required (logged to file is sufficient). `import-log.md`'s skipped-count reflects these entries per VAULT-05.
- **D-15:** `import-log.md` format: **append, latest-first.** Each run prepends a `## Run YYYY-MM-DDTHH:MM` block with vault path, threshold, promoted-count by type, skipped-count by reason, and per-skipped-path breakdown.
- **D-16:** All file writes atomic: temp-file + `os.replace` (applies to notes, `vault-manifest.json`, and `profile.yaml` write-back).

### Tag Taxonomy
- **D-17:** `_DEFAULT_PROFILE` baseline is **verbatim from the design note** (VAULT-07 Layer 1):
  - `garden`: `[plant, cultivate, probe, repot, revitalize, revisit, question]`
  - `graph`: `[component, domain, workflow, decision, concept, integration, service, dataset, team, extracted, inferred, ambiguous]`
  - `source`: `[confluence, readme, doc, code, paper, pdf, jira, slack, github, notion, obsidian, web]`
  - `tech`: `[python, typescript, javascript, go, rust, java, sql, graphql, docker, k8s]`
- **D-18:** `_VALID_TOP_LEVEL_KEYS` in `profile.py` gains `tag_taxonomy` and `profile_sync` (the latter for VAULT-06 opt-out flag `profile_sync.auto_update` — default `true`).
- **D-19:** Layer 2 (user overrides from `.graphify/profile.yaml`) is deep-merged over Layer 1. Layer 3 (auto-detected per run) is deep-merged over Layers 1+2 in memory for the current run, and union-merged into `profile.yaml` on write-back.

### Frontmatter Schema
- **D-20:** Every promoted note carries the full Ideaverse frontmatter (VAULT-02): `up`, `related`, `created`, `collections`, `graphifyProject`, `graphifyRun`, `graphifyScore`, `graphifyThreshold`, and at minimum one tag from each of `garden/*`, `source/*`, `graph/*`. `tech/*` is added when applicable.
- **D-21:** `related:` is populated **only from EXTRACTED-confidence edges** (VAULT-04). INFERRED and AMBIGUOUS edges are omitted from wikilinks entirely — they may appear in `graph/inferred` or `graph/ambiguous` tags for audit but never as `[[wikilinks]]`.

### Claude's Discretion
- Exact regex/predicate tuning for People/Quotes/Statements heuristics (e.g., locale handling for `^[A-Z][a-z]+` across accented names) — planner/researcher may propose alternatives; keep the heuristic simple by default.
- Sidecar manifest schema internals (`vault-manifest.json`) — the contract is "path → hash", but exact JSON shape (versioning, timestamp) is Claude's call.
- Whether new templates `question.md` and `quote.md` are added to `builtin_templates/` or inlined as string literals in `vault_promote.py`. Lean toward consistency with existing pattern (separate template files).
- Test file organization — new `tests/test_vault_promote.py` vs. piggyback on `tests/test_export.py`. Recommended: new file per one-test-per-module convention in CLAUDE.md.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope & Requirements
- `.planning/ROADMAP.md` §Phase 19 (lines 211–221) — 5 locked success criteria
- `.planning/REQUIREMENTS.md` — VAULT-01..05 rows. **Planner must add VAULT-06 and VAULT-07 rows** per D-01.
- `.planning/notes/layer-b-vault-promotion-design.md` — richer design doc; source of truth for VAULT-06/07 scope, tag-taxonomy values, and promotion-gate philosophy. Now promoted to canonical.

### Design & Architecture Context
- `.planning/PROJECT.md` §Current Milestone: v1.5 — milestone-level invariants (carried forward from v1.4: D-02 envelope, D-16 alias, D-18 compose don't plumb); note Phase 19 is independent of these (no MCP, no `serve.py`).
- `.planning/notes/folder-architecture-graphify-out-vs-vault.md` — graphify-out vs. vault separation principle.

### Existing Code (reuse surface)
- `graphify/profile.py` — `load_profile()`, `validate_profile()`, `_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`. Needs `tag_taxonomy` and `profile_sync` keys added.
- `graphify/security.py` — `validate_vault_path()`, `safe_filename()`, `safe_tag()`, `safe_frontmatter_value()`.
- `graphify/analyze.py` — `god_nodes()`, `knowledge_gaps()` outputs feed the classifier.
- `graphify/builtin_templates/` — `thing.md`, `moc.md`, `statement.md`, `person.md`, `source.md`, `community.md`. Phase 19 adds `question.md` and `quote.md`.

### Existing Code (non-reuse, documented boundary)
- `graphify/export.py::to_obsidian` — NOT called by `vault_promote.py` (D-04). Documents the merge-with-review flow that vault-promote intentionally does not participate in.
- `graphify/merge.py::compute_merge_plan` — same boundary.
- `graphify/__main__.py::approve` (line 939) — shows how to load `graph.json` from disk without a live pipeline run; pattern can be lifted for `vault_promote.py` but not the merge-plan call.

### CLI Conventions
- `graphify/__main__.py` — `_PLATFORM_CONFIG` and argparse subparser registration. `vault-promote` must be added as a subcommand alongside `harness` / `approve` / `install` (D-05).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/profile.py` — full profile loading + validation stack, already supports layered overrides. Extending `_VALID_TOP_LEVEL_KEYS` for `tag_taxonomy` + `profile_sync` is a small additive change.
- `graphify/security.py` — all path/label/tag sanitization primitives are production-hardened. No new guards needed unless a new input surface is introduced.
- `graphify/analyze.py::god_nodes`, `knowledge_gaps` — ready-to-use primitives; no new detection required.
- `graphify/builtin_templates/` — `${frontmatter}` / `${label}` / `${body}` / `${connections_callout}` / `${metadata_callout}` substitution pattern is already established and reusable.
- `graphify/__main__.py:939-1001` — `_compute_merge_plan_for_approve` and `approve_cli` already demonstrate reading `graph.json` from disk and applying vault writes; pattern can be lifted without the merge-plan dependency.

### Established Patterns
- Write atomicity: `tempfile` + `os.replace()` (see `cache.py` and `enrich.py` for reference).
- Error discipline: warnings/errors to stderr with `[graphify]` prefix; silent graceful fallback where safe.
- File paths from external input always routed through `security.validate_vault_path()` and `safe_filename()`.
- Profile deep-merge pattern already exists for `folder_mapping` — `tag_taxonomy` should follow the same shape.

### Integration Points
- `graphify/__main__.py` argparse subparsers — add `vault-promote` subcommand.
- `graphify/profile.py::_VALID_TOP_LEVEL_KEYS` — add `tag_taxonomy`, `profile_sync`.
- `graphify/profile.py::_DEFAULT_PROFILE` — add baseline `tag_taxonomy` (4 namespaces, verbatim from design note).
- `graphify/profile.py::validate_profile` — add validation for `tag_taxonomy` (nested dict of lists) and `profile_sync` (dict with `auto_update: bool`).
- `graphify/builtin_templates/` — add `question.md` and `quote.md`.
- `graphify-out/` — new sidecar artifact `vault-manifest.json` (self-created path → last-written-content-hash).

</code_context>

<specifics>
## Specific Ideas

- Re-run drift handling: the "overwrite self, skip foreign" strategy via `vault-manifest.json` lets the vault absorb graph drift automatically on every run WITHOUT trampling hand-edited notes. This is stronger than the simple "skip-if-exists" pattern but simpler than v1.1's `GRAPHIFY_USER_START/END` sentinel blocks.
- `import-log.md` is an **append, latest-first** journal — each run is a prepended `## Run YYYY-MM-DDTHH:MM` block. Full example format locked in D-15 and the DISCUSSION-LOG.md preview.
- Map MOC emoji: `stateMaps: 🟥` is the "auto-generated, not yet reviewed" sentinel. When the user reviews a Map manually, they are expected to change the emoji — vault-promote never overwrites a reviewed Map because the content-hash will have changed (D-13).
- All 7 folder types ship with heuristic dispatch even where detectors are imperfect (People regex, Quotes quote-mark search, Statements defines-relation). Users can turn off noisy heuristics later via profile rules if needed, but the default is design-note-faithful.

</specifics>

<deferred>
## Deferred Ideas

- **Sentinel-block preservation (`GRAPHIFY_USER_START/END`)** — v1.1's inviolable-block mechanism inside promoted notes. Not in Phase 19; the content-hash-manifest approach (D-13) is simpler and sufficient for VAULT-01's guarantee. Revisit if users request mid-note edits that survive regeneration.
- **ACE-Aligned Vocabulary candidate phase** (ROADMAP.md §146) — proposes a `vocabulary:` profile section driving note-type enumeration and naming patterns. Phase 19's VAULT-07 pre-empts a slice of this (the tag taxonomy) but NOT the note-type vocabulary or naming conventions. The ACE candidate remains as-is for v1.6+ consideration.
- **Additional `mapRank` / `mapConfidence` / `stateReviewed` frontmatter on Maps** — considered but deferred; `stateMaps: 🟥` + `collections:` union is the locked minimum (D-12).
- **More precise heuristics for People/Quotes/Statements** — e.g., Unicode-aware name regex, structured quote detection via extractor hints. The planner/researcher may propose refinements; the design-note-minimal heuristics are the starting point.

</deferred>

---

*Phase: 19-vault-promotion-script-layer-b*
*Context gathered: 2026-04-22*
