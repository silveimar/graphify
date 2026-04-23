# Phase 20: Diagram Seed Engine - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

graphify auto-detects diagram-worthy nodes from the analyzed graph and exposes
structured seeds — both on disk (`graphify-out/seeds/{node_id}-seed.json`) and
via MCP tools (`list_diagram_seeds`, `get_diagram_seed`) — so downstream agents
(Phase 22 excalidraw skill) can select and consume them.

Scope is limited to: `analyze.py` extension (auto-tag + `detect_user_seeds`),
new `graphify/seed.py` module (build + dedup + layout heuristic + file output +
CLI flag), and MCP tool exposure (registry + serve wiring).

**Out of scope:** profile `diagram_types:` section (Phase 21), template stubs
(Phase 21), excalidraw skill orchestration and vault bridge (Phase 22), any
`.excalidraw.md` generation.

</domain>

<decisions>
## Implementation Decisions

### Re-run and artifact lifecycle

- **D-01 Atomic write + manifest (Phase-19 parity):** `graphify --diagram-seeds`
  writes seeds using the same pattern as `vault-promote`: tempfile + rename for
  every `*-seed.json`, and a `graphify-out/seeds/seeds-manifest.json` written
  **last** as the final atomic step. No partial runs ever leak visible state.
- **D-02 Manifest is cleanup source-of-truth:** On re-run, read the prior
  `seeds-manifest.json` → delete any `*-seed.json` listed there that is not in
  the new run's decision table → write new seeds atomically → overwrite manifest.
  Stale seeds from prior analyses never surface to `list_diagram_seeds`.
- **D-03 Manifest schema:** One entry per candidate seed (including dropped
  ones) with fields:
  ```
  { "node_id", "seed_file", "trigger" ("auto"|"user"), "layout_type",
    "dedup_merged_from": [node_id, ...],   # union-merge sources
    "dropped_due_to_cap": bool,
    "rank_at_drop": int | null,            # rank in auto ordering if capped
    "written_at": ISO-8601 }
  ```
  This is the audit trail for both dedup merges and `max_seeds=20` drops — no
  separate `seeds-log.md` journal is written.

### Auto + user seed overlap

- **D-04 User trigger wins on overlap:** When a node is BOTH an auto candidate
  (god-node or cross-community bridge) AND carries a `gen-diagram-seed` tag,
  `seed.py` emits exactly one seed with `trigger: "user"`. The user's
  `gen-diagram-seed/<type>` slash-type-hint (if present) is used as
  `layout_hint`. User seeds have no cap (SEED-06), so this seed does NOT count
  against the `max_seeds=20` auto cap — removing it from the auto count can
  free a slot for the next-ranked auto candidate.

### Layout heuristic precedence (auto path)

- **D-05 Specific-first ordering:** When multiple SEED-07 predicates match the
  same subgraph, evaluate in this priority order and return on first hit:
  1. `is_tree` → `cuadro-sinoptico`
  2. DAG with ≥3 topological generations → `workflow`
  3. ≥4 communities → `architecture`
  4. Single community with degree-concentrated hub → `mind-map`
  5. Predominantly code file_type nodes → `repository-components`
  6. Predominantly concept/doc file_type nodes with labeled relations →
     `glossary-graph`

  User slash-type-hint `gen-diagram-seed/<type>` bypasses the heuristic entirely
  and forces the hinted layout.

### Template recommender (bridge to Phase 21)

- **D-06 Built-in fallback keyed by layout_type:** Phase 20 ships before
  `profile.yaml diagram_types:` exists. `suggested_template` is always a
  non-null string, resolved by a hard-coded map from `layout_type` to a
  built-in template filename:
  ```
  cuadro-sinoptico       → "cuadro-sinoptico.excalidraw.md"
  workflow               → "workflow.excalidraw.md"
  architecture           → "architecture.excalidraw.md"
  mind-map               → "mind-map.excalidraw.md"
  repository-components  → "repository-components.excalidraw.md"
  glossary-graph         → "glossary-graph.excalidraw.md"
  ```
  Phase 21 will layer the profile lookup in front of this fallback (precedence:
  profile match → layout-heuristic default → built-in). No downstream consumer
  has to handle null in v1.5.

### max_seeds=20 cap surfacing

- **D-07 Manifest entries + stderr warning:** Dropped auto seeds are recorded
  in `seeds-manifest.json` with `dropped_due_to_cap: true` and their
  `rank_at_drop`. `seed.py` also prints a single `[graphify]` warning to stderr
  when the cap fires:
  ```
  [graphify] Capped at 20 auto seeds; N dropped (see seeds-manifest.json)
  ```
  No separate markdown journal.

### Tag write-back trigger

- **D-08 Opt-in via `--vault`:** `graphify --diagram-seeds` alone is
  vault-side-effect-free — it writes only to `graphify-out/seeds/`.
  `graphify --diagram-seeds --vault /path/to/vault` additionally performs
  the `gen-diagram-seed` tag write-back for auto-detected nodes through
  `vault_adapter.py::compute_merge_plan` with `tags: "union"` policy.
  Mirrors the `vault-promote --vault` contract. Default analyze runs never
  mutate the vault.

### Claude's Discretion

- Empty-state behavior when no auto/user seeds exist: recommend writing an
  empty `seeds/` dir + empty manifest (`[]`) + stderr info line, so MCP
  consumers always find a valid directory.
- `seed_id` string format in MCP envelopes (likely `{node_id}` for singletons
  and `merged-{sha256(sorted_node_ids)[:12]}` for union-merged seeds — planner
  decides).
- Whether subgraph `relations` include AMBIGUOUS-confidence edges (leaning
  yes — diagrams benefit from showing uncertainty; mark with confidence
  attribute in the element data).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 20 scope anchors
- `.planning/ROADMAP.md` §"Phase 20: Diagram Seed Engine" — goal, success
  criteria, 3-plan breakdown, cross-phase rules (D-18, MANIFEST-05, D-02, D-16).
- `.planning/REQUIREMENTS.md` §SEED (SEED-01..SEED-11) — the 11 locked REQ-IDs.
- `.planning/REQUIREMENTS.md` §"Cross-phase rules" — D-02 envelope, D-16 alias
  threading, D-18 analyze-only detection boundary, MANIFEST-05 atomic pair.

### Prior-phase invariants this phase depends on
- `graphify/analyze.py` — `god_nodes()` and `_cross_community_surprises()`
  (Phase 10+ output; seed.py consumes these per D-18; never reimplements).
- `graphify/vault_adapter.py` — `compute_merge_plan` with `tags: "union"`
  policy (Phase 8; SEED-03 and D-08 route through this).
- `graphify/merge.py` line 70 — `tags: "union"` policy implementation.
- `.planning/phases/19-vault-promotion-script-layer-b/19-02-PLAN.md` and
  `19-03-PLAN.md` — reference implementation of the atomic-write + manifest
  pattern reused for `seeds-manifest.json` (D-01, D-02, D-03).
- `graphify/serve.py` and `graphify/mcp_tool_registry.py` — existing D-02
  envelope helpers and `_resolve_alias` (D-16); Plan 20-03 extends both in the
  same commit per MANIFEST-05.

### Excalidraw-format invariants
- Element ID rule: `sha256(node_id)[:16]` (SEED-08). Label-derived IDs are
  forbidden.
- `versionNonce` rule: `int(sha256(node_id + str(x) + str(y))[:8], 16)`
  (SEED-08). Deterministic.

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md` — 7-stage pipeline, module roles.
- `.planning/codebase/CONVENTIONS.md` — `[graphify]` stderr prefix, type-hint
  style, naming, `validate.py` schema enforcement.
- `.planning/codebase/TESTING.md` — unit-only, `tmp_path`, no network.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analyze.py::god_nodes()` — existing degree-ranked god-node detector. Plan
  20-01 adds `possible_diagram_seed: true` node attribute emission here.
- `analyze.py::_cross_community_surprises()` — existing cross-community bridge
  detector. Same treatment in Plan 20-01.
- `vault_adapter.py::compute_merge_plan` — the ONLY legal path for
  `gen-diagram-seed` tag write-back (SEED-03, D-08).
- Phase 19's atomic-write pattern (`graphify/vault_promote.py` + its
  `vault-manifest.json`) — reuse the tempfile+rename + manifest-last sequence
  for seeds.
- `serve.py` D-02 envelope helpers + `_resolve_alias` (D-16) — Plan 20-03
  consumes both for the two new MCP tools.

### Established Patterns
- stdlib-only + optional-dep hygiene: seed.py is pure stdlib + NetworkX (no
  new required deps).
- `[graphify]`-prefixed stderr warnings for operational messages (applied in
  D-07 cap warning).
- Deterministic hashing for stable IDs (sha256 truncation) — already used
  elsewhere; SEED-08 element IDs align with that convention.
- Validation of schemas before writing (`validate.py` pattern) — manifest and
  seed JSON should be validated before the final rename.

### Integration Points
- `__main__.py` — new `--diagram-seeds` CLI flag and optional `--vault` pairing
  (Plan 20-02).
- `mcp_tool_registry.py` + `serve.py` — atomic pair extension per MANIFEST-05
  (Plan 20-03).
- `graphify-out/seeds/` — new canonical artifact directory alongside existing
  `graphify-out/graph.json`, `GRAPH_REPORT.md`, and Phase-19 `vault-manifest.json`.

</code_context>

<specifics>
## Specific Ideas

- Phase 19's `vault-promote --vault` is the UX anchor for `--diagram-seeds --vault`.
  Same mental model: analyze step is pure; `--vault` opts into mutation.
- `seeds-manifest.json` plays the role `vault-manifest.json` plays for Phase 19:
  audit trail + cleanup driver in one file.
- Built-in template filenames match the 6 layout_type names Phase 21 will later
  seed as built-in defaults — keeps a single vocabulary across the pipeline.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-seed diagrams** (combining two seeds into one Excalidraw diagram) —
  explicitly v1.6+ per REQUIREMENTS.md.
- **SEED-001 Tacit Elicitation Engine** — re-evaluate at v1.6 per REQUIREMENTS.md.
- **Empty-state decision** (write empty manifest vs skip dir creation) — left
  as Claude's discretion; planner picks during Plan 20-02.
- **AMBIGUOUS-confidence edges in seed subgraphs** — Claude's discretion during
  planning; surface a flag in the SeedDict if included.

### Reviewed Todos (not folded)
- **Create Graphify master key files in work vault** (`create-master-keys-work-vault.md`)
  — matched on keywords `graphify, vault` but already completed 2026-04-22
  (all 4 master key files written to `~/Documents/work-vault/x/Templates/Master Keys/`).
  Concerns Obsidian tag-suggester UX for the `source/*`, `tech/*`, `graph/*` tag
  taxonomy — unrelated to diagram seed generation. Not folded; leave for manual
  archival.

</deferred>

---

*Phase: 20-diagram-seed-engine*
*Context gathered: 2026-04-23*
