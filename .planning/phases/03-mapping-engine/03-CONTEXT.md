# Phase 3: Mapping Engine - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A **pure classification layer** that consumes a NetworkX graph + a community partition + a profile, and produces per-node and per-community `ClassificationContext` dicts matching the TypedDict shape already locked in `graphify/templates.py` (D-42). The engine decides:

- Which of the six note types each real node belongs to (`thing | statement | person | source | moc | community`).
- Which folder it lives in, via `folder_mapping` plus optional `then.folder` rule overrides.
- Which community is rendered as a full MOC vs absorbed into another MOC's `sub_communities` list.
- The MOC-level bag of `members_by_type`, `community_tag`, `community_name`, `parent_moc_label`, and `sibling_labels` that Phase 2's `render_note` / `render_moc` already consume.

The engine does NOT render markdown (Phase 2), merge with existing notes (Phase 4), or write files (Phase 5). It produces pure data structures over pure inputs — no filesystem, no network, no global state.

</domain>

<decisions>
## Implementation Decisions

### Mapping rule DSL (D-43..D-47)

- **D-43:** `profile.yaml:mapping_rules` is a **list of flat `{when, then}` entries**. No boolean trees, no shorthand. Example:
  ```yaml
  mapping_rules:
    - when: {attr: file_type, equals: person}
      then: {note_type: person}
    - when: {topology: god_node}
      then: {note_type: thing, folder: Atlas/Dots/Things/}
    - when: {source_file_ext: .py}
      then: {note_type: source, folder: Atlas/Sources/Code/}
  ```
  Flat shape is easy for the validator to emit pointed error messages (`mapping_rules[2].when.source_file_ext: invalid ext ...`), easy for users to read, and composes via rule order.

- **D-44:** Matchers supported in v1 (inside `when:`):
  - `{attr: <key>, equals: <scalar>}` — exact scalar match on a node attribute.
  - `{attr: <key>, in: [<v1>, <v2>, ...]}` — set membership.
  - `{attr: <key>, contains: <substring>}` — case-sensitive substring match on a string attribute. Rejected if attr value is non-string.
  - `{attr: <key>, regex: <python-regex>}` — `re.fullmatch` against the attribute value. **Guarded:** pattern length capped at 512 chars; candidate string length capped at 2048 chars; any `re.error` becomes a validation error; uses the `security.py` input-cap mindset (we are not adding timeouts since Python `re` has no native timeout — the length caps are the mitigation). Pattern is compiled at profile-load time, not at classification time, so malformed patterns fail fast.
  - `{topology: god_node}` — true iff the node is in `analyze.god_nodes(G, top_n)` output for this run.
  - `{topology: community_size_gte, value: N}` — true iff the node's community has ≥ N members.
  - `{topology: community_size_lt, value: N}` — true iff the node's community has < N members.
  - `{topology: cohesion_gte, value: 0.7}` — true iff the node's community cohesion (from `cluster.score_all`) ≥ value.
  - `{topology: is_source_file}` — true iff the node is the file-level hub (label == basename(source_file)). **Note:** these nodes are SKIPPED by default (D-51) unless a rule explicitly maps them.
  - `{source_file_ext: .py}` / `{source_file_ext: [.py, .pyi]}` — matches on the file extension of the node's `source_file` attribute (lowercase comparison, leading `.` normalized). Required for MAP-06.
  - `{source_file_matches: "<regex>"}` — `re.fullmatch` against the full `source_file` path, with the same guards as the top-level regex matcher.

- **D-45:** **First-match-wins.** Rules are evaluated in profile order; the first rule whose `when:` clause is true for a node locks the outcome, short-circuiting the rest. This is the iptables/nginx mental model — users control precedence by ordering rules in `profile.yaml`. The validator warns (not errors) when a rule is provably dead (e.g. a less-specific rule precedes a strictly more-specific one for the same `note_type`).

- **D-46:** **Rule output (`then:`):** `note_type` is required; `folder` is optional and defaults to `folder_mapping[note_type]` when omitted. **Nothing else.** No tags, no `up:` injection, no custom frontmatter. Classification stays narrow; frontmatter/rendering remains Phase 2's job. This also means per-rule folder overrides are how MAP-06 (source files → sub-folders by file type) is expressed — exactly the mechanism the `source_file_ext` matcher was built for.

- **D-47:** **Precedence pipeline (MAP-04):**
  1. **Explicit `mapping_rules` (attribute + topology)** — first-match-wins.
  2. **Built-in topology classification** — if no rule matched: god node → `thing`, community above threshold → the community's node becomes a `moc` (one per community, see D-55), source-file hub → `source`.
  3. **Default** — `folder_mapping.default` with `note_type: statement`.
  Note that `mapping_rules` can express ALL of step 2's logic as explicit rules if users want to override; step 2 is the implicit fallback only when `mapping_rules` is empty or no rule matched.

### God-node threshold & synthetic-node filtering (D-48..D-51)

- **D-48:** `profile.topology.god_node.top_n` (default: **10**). Phase 3 invokes `analyze.god_nodes(G, top_n=top_n)` — the existing function is the single source of truth. No duplicate "what is a god node" logic between `report.py` and `mapping.py`. `_DEFAULT_PROFILE` gets a new `topology` section with this default.

- **D-49:** **Zero god nodes is valid state.** If `analyze.god_nodes()` returns `[]` (tiny graph, or every high-degree node is a file hub), the classification pass produces zero `thing` notes. No fallback promotion, no auto-lowering of `top_n`. Real nodes fall through the precedence chain to `statement`. MOC threshold still fires independently.

- **D-50:** **Synthetic-node filter is applied globally, not just to god-node selection.** Phase 3 imports `_is_file_node` and `_is_concept_node` from `analyze.py` (or re-implements them in `mapping.py` if import pollution is a concern — Claude's Discretion at planning time). Any node for which either returns `True` is added to a `skipped_node_ids: set[str]` in the engine's return value and **produces no ClassificationContext**. This keeps the vault free of `.auth_flow()` method stubs and empty-`source_file` concept nodes.

- **D-51:** **Exception:** a user rule in `mapping_rules` with `{topology: is_source_file}` can **explicitly opt in** a file-hub node to a note type (typically `source`). Concept nodes remain unconditionally skipped — there is no matcher for them because they are defined by absent metadata, not present metadata. This gives MAP-06 users a way to surface per-file source notes without polluting the default vault.

### Community-to-MOC routing & below-threshold collapse (D-52..D-57)

- **D-52:** `profile.mapping.moc_threshold` (default: **3**) — unchanged from MAP-05. Communities with `len(members) >= threshold` become full MOC notes; communities below threshold collapse.

- **D-53:** **Nearest-by-edge-count host resolution.** For each below-threshold community `C`, count inter-community edges from `C` to every above-threshold community; host is the `arg max`. Ties broken by largest host (`len(members)` descending), then by lowest community_id for determinism. Computed once per run using a single pass over `G.edges()` filtered through the community map.

- **D-54:** **`sub_communities` payload shape** (consumed by Phase 2's `_build_sub_communities_callout` at `templates.py:458`):
  ```python
  [
      {
          "label": "Community 7",  # per D-56 naming
          "members": [
              {"label": "node_a_label", "note_type": "thing"},
              {"label": "node_b_label", "note_type": "statement"},
          ],
      },
      ...
  ]
  ```
  Members inside a collapsed community still get their note_type classified normally — they just don't get their own MOC. They DO get individual note files (so `[[wikilinks]]` from the parent MOC resolve), placed in the folder Phase 3 assigns them, with `parent_moc_label = host_MOC_label`.

- **D-55:** **Size-1 isolates are treated as below-threshold.** `cluster.py` returns singletons as their own community when the isolate fallback fires (`cluster.py:87`). These hit the same nearest-host path as any other small community, which usually lands them in the MOC of whichever neighbor they're connected to. If an isolate has zero neighbors at all, it hits the fallback bucket MOC (D-56).

- **D-56:** **Fallback bucket MOC.** When every community in the graph is below threshold (tiny corpus edge case), OR a below-threshold community has NO inter-community edges to resolve a host, Phase 3 synthesizes a single MOC with:
  ```
  community_id: -1  (sentinel)
  label: "Uncategorized"
  folder: folder_mapping.moc
  ```
  All host-less below-threshold communities merge into this bucket's `sub_communities` list. Only emitted when needed — no empty Uncategorized in well-connected graphs.

- **D-57:** **`members_by_type` composition for a MOC** (consumed by `_build_members_section` at `templates.py:421`): populated from the classified non-MOC nodes whose community_id matches. Keys are note types (`thing`, `statement`, `person`, `source`), values are `list[dict]` with at minimum `{"label": <display>}`. A node can only appear in exactly one group — its final classified `note_type`. Classification happens before MOC assembly, so there is no deduplication ambiguity.

### Community labels & tags (D-58..D-60)

- **D-58:** **Community display label = top-god-node-inside-community, fallback to `"Community N"`.** For each community, rank its members by `G.degree()` (the same metric `analyze.god_nodes` uses), skipping nodes that `_is_file_node` or `_is_concept_node` would filter. The label of the highest-degree real node becomes the community's `community_name` → MOC filename → wayfinder `Up:` → `community_tag` input. If all members are synthetic (rare — would mean an all-file-hub community), fall back to `f"Community {cid}"`. This is a pure-function derivation — no LLM, no caller input.

- **D-59:** **`community_tag` = `safe_tag(community_name)`.** Reuses `profile.safe_tag()` (Phase 1, `profile.py:204`). Output is the tag's path component — Phase 2 wraps it as `community/<slug>` when emitting frontmatter/Dataview (`templates.py:598`). No separate hash slugs; readable tags win.

- **D-60:** **`sibling_labels` = up to 5 other god-node labels in the same community**, sorted by `G.degree()` descending. Capped at 5 to keep `related:` readable in Obsidian's Properties UI. Non-god nodes get `sibling_labels: []`. God nodes in singleton communities get `sibling_labels: []`. For a community whose top god node IS the current node, siblings are the next 5 god nodes in the ranking (so the current node never links to itself).

### Engine API & module boundary (Claude's Discretion)

The following are **Claude's Discretion at plan-phase**, to be decided when `03-RESEARCH.md` lands and the planner has concrete test cases in hand:

- Module name: `graphify/mapping.py` (most likely) vs `graphify/classify.py`. The public verb is "classify" but the domain noun is "mapping" — go with whichever feels more natural when Phase 5's refactor wires it in.
- Public function shape. Two likely surfaces:
  1. Single entry: `classify(G, communities, profile, *, cohesion=None) -> MappingResult` where `MappingResult` is a dataclass or TypedDict with `.per_node: dict[str, ClassificationContext]`, `.per_community: dict[int, ClassificationContext]`, `.skipped_node_ids: set[str]`, `.rule_traces: list[RuleTrace]` (which rule matched which node — debugging gold).
  2. Paired entries: `classify_nodes(...)` + `classify_communities(...)` with independent signatures, composed by Phase 5. Simpler per-function but leaks the precedence pipeline across two call sites.
  Recommendation: single `classify()` entry with a `MappingResult` dataclass — the precedence pipeline is one algorithm, keep it one function.
- Validator extension point: `validate_profile` in `profile.py` currently checks only `mapping_rules is a list`. Phase 3 extends it to walk each rule, check `when`/`then` shape, compile any regexes, and verify referenced `note_type` values are in `_NOTE_TYPES`. Whether this logic lives in `profile.py` or in `mapping.py::validate_rules(rules) -> list[str]` called from `profile.py` is Claude's pick — lean toward the latter to keep the DSL grammar and its validator co-located.
- `rule_traces` payload and whether it ships in v1 or is a debug-only kwarg. Worth it for test assertions (`assert result.rule_traces[node_id].rule_index == 2`) but can be stubbed.
- Whether `topology` matcher values like `community_size_gte` are evaluated once per community (cached) or once per node (re-evaluated). Cached is obviously right; call it out in planning.
- Test fixture strategy — minimal graph with 2 communities + 1 isolate vs reusing Phase 2's `make_min_graph`. Lean toward extending `tests/fixtures/template_context.py` with a `make_classification_fixture()` helper so Phase 2 and Phase 3 share a corpus.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 foundations (MUST produce data that matches these consumers)
- `graphify/templates.py:57-67` — `ClassificationContext` TypedDict. This is the contract. Every field Phase 3 populates must match these names and types.
- `graphify/templates.py:421-451` — `_build_members_section` — consumes `ctx["members_by_type"]`. Determines the shape of each member dict (`{"label": str}` at minimum; non-dict entries silently dropped per IN-06).
- `graphify/templates.py:458-477` — `_build_sub_communities_callout` — consumes `ctx["sub_communities"]`. Shape is `[{"label": str, "members": [{"label": str}, ...]}, ...]`.
- `graphify/templates.py:536-653` — `render_note` — reads `parent_moc_label`, `community_tag`, `community_name`, `sibling_labels` from the classification context. These names are load-bearing.
- `graphify/templates.py:660-820` — `_render_moc_like` / `render_moc` — reads `members_by_type`, `sub_communities`, `community_tag`, `parent_moc_label`. Unused fields (`G`, `communities`) stay in signature per IN-02.

### Phase 1 foundations (MUST import, MUST extend)
- `graphify/profile.py:16-37` — `_DEFAULT_PROFILE`. Phase 3 **extends it** with a new `topology.god_node.top_n` entry (default 10) and `mapping.moc_threshold` entry (default 3). Existing sections (folder_mapping, naming, merge, mapping_rules, obsidian) stay intact.
- `graphify/profile.py:197-200` — current `mapping_rules` validation (only checks it's a list). Phase 3 **replaces this stub** with full per-rule validation (shape, matchers, regex compile, `then.note_type` whitelist).
- `graphify/profile.py:204` — `safe_tag(name)` — used to slug `community_name` into `community_tag`.
- `graphify/validate.py` — Validation contract: return `list[str]`, never raise. Phase 3's rule validator follows the same shape.

### Graph-layer inputs (READ ONLY — do not modify)
- `graphify/analyze.py:11-36` — `_is_file_node` — Phase 3 reuses this filter (D-50) to skip file-level hub nodes globally.
- `graphify/analyze.py:39-58` — `god_nodes(G, top_n)` — Phase 3's single source of truth for god-node identification (D-48).
- `graphify/analyze.py:93-109` — `_is_concept_node` — Phase 3 reuses this filter (D-50) to skip empty-source_file concept nodes globally.
- `graphify/analyze.py:6-8` — `_node_community_map(communities)` — utility Phase 3 will call repeatedly for O(1) community lookups.
- `graphify/cluster.py:59-104` — `cluster(G)` — shape of the `communities: dict[int, list[str]]` input. Community 0 is always largest after splitting; IDs are stable across runs.
- `graphify/cluster.py:125-137` — `cohesion_score` / `score_all` — Phase 3 calls `score_all` to feed the `cohesion_gte` topology matcher.

### Existing Obsidian export (REFERENCE ONLY — Phase 5 will rewire)
- `graphify/export.py:444-679` — current `to_obsidian()`. Phase 3 reads this to understand the legacy flat-classification behavior we're replacing, not to modify it. Phase 5 does the wiring.
- `graphify/export.py:492-498` — `_FTYPE_TAG` dict — reference for how legacy code mapped file_type to tag namespaces; Phase 3's `file_type`-keyed rules should cover the same taxonomy.

### Prior phase context (MUST read — decisions cascade)
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-01 through D-16: profile schema, `_DEFAULT_PROFILE`, safety helpers, validation pattern.
- `.planning/phases/02-template-engine/02-CONTEXT.md` — D-17 through D-42: the TypedDict contract (D-42) and the render-time field consumers Phase 3 is feeding.
- `.planning/phases/02-template-engine/02-RESEARCH.md` — research patterns that informed Phase 2 (reusable as background for Phase 3 tests).
- `.planning/phases/02-template-engine/02-SECURITY.md` — security threat model; Phase 3's regex matchers MUST be consistent with the input-cap philosophy there.

### Requirements
- `.planning/REQUIREMENTS.md` — MAP-01 through MAP-06 (folder placement, topology classification, attribute override, rule precedence, below-threshold collapse, source-file sub-folder routing).
- `.planning/REQUIREMENTS.md` — MRG-05 (no-profile backward compat) — Phase 3 must still produce *something* that Phase 5 can feed to a fallback-mode `to_obsidian()` when mapping_rules is empty.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analyze.py:god_nodes()` — Phase 3's god-node authority (D-48). Import directly; no re-implementation.
- `analyze.py:_is_file_node` / `_is_concept_node` — synthetic-node filters (D-50). Import or mirror; either is acceptable at plan time.
- `analyze.py:_node_community_map` — O(1) inverted community lookup; will be hot-called in the classification loop.
- `cluster.py:score_all` — cohesion dict keyed by community_id; backs the `cohesion_gte` topology matcher.
- `profile.py:safe_tag` — community_name → community_tag slug (D-59). Already handles FIX-03 edge cases.
- `profile.py:validate_vault_path` — path-confinement check; any `then.folder` override must pass through this OR equivalent before Phase 5 writes files.
- `profile.py:_deep_merge` — `_DEFAULT_PROFILE` gains new `topology` and `mapping` sections; user profiles still deep-merge cleanly.

### Established Patterns
- **Pure functions over dicts / NetworkX graphs** — classification engine keeps this shape. No shared state, no filesystem, no side effects outside `tmp_path` in tests.
- **Validation returns error list** — `validate_rules(rules) -> list[str]` follows `validate_extraction` / `validate_profile` shape. Never raises.
- **Lazy imports** — new public `classify` / `MappingResult` export added to `graphify/__init__.py` lazy map.
- **`from __future__ import annotations`** + single-line module docstring on the first line after it.
- **TypedDict for structured dicts** — Phase 2 uses `ClassificationContext(TypedDict)`. Phase 3's `RuleTrace` / `MappingResult` follow the same convention (or use a `@dataclass(frozen=True)` if mutation is obviously a non-goal — Claude picks at plan time).

### Integration Points
- `profile.py::_DEFAULT_PROFILE` — extended in-place with `topology.god_node.top_n: 10` and `mapping.moc_threshold: 3`. `_VALID_TOP_LEVEL_KEYS` also gains `topology` and `mapping`.
- `profile.py::validate_profile` — imports `validate_rules` from the new `mapping.py` (or wherever the rule grammar lives), invokes it as part of the existing validation pass. Error list aggregates both profile-schema and mapping-rules errors.
- `__init__.py` lazy map — new entries: `classify`, `MappingResult`, `validate_rules`.
- Phase 5 callsite — `to_obsidian()` will pull `MappingResult` from `classify(G, communities, profile, cohesion=score_all(G, communities))` and feed per-node + per-community entries to `templates.render_note` / `templates.render_moc`.

### Creative Options the Architecture Enables
- **Rule traces as first-class output.** `MappingResult.rule_traces` records which rule (index + `when` expression) matched which node — trivial to surface in `GRAPH_REPORT.md` as an "explain classification" section, invaluable for users debugging why a node landed in the wrong folder.
- **Pure-function testability.** `classify(G, communities, profile)` is a pure function of its inputs; test fixtures are minimal NetworkX graphs + dict profiles. No tmp_path needed for classification tests — only Phase 5 integration tests need filesystem.
- **Profile dry-run affinity.** MRG-03 (`--dry-run`) and PROF-05 (`--validate-profile`) land in Phase 5, but Phase 3's `validate_rules()` + `classify()` already expose the internals those CLI flags need — Phase 5 mostly glues them to argparse.
- **Future extensibility without DSL churn.** Adding a matcher (e.g. `{topology: bridge_node}` in v2) is a single dispatch entry + a single validator entry. The `{when, then}` wrapper doesn't move.

</code_context>

<specifics>
## Specific Ideas

- **Rule grammar is load-bearing for UX.** The profile.yaml example in D-43 is what users will paste into their vaults. Built-in docs (README or a new `docs/mapping-rules.md`) should use that exact example.
- **`topology: god_node` unifies MAP-02 and the `mapping_rules` DSL.** Users who want to keep the default god-node-as-Thing behavior get it for free when `mapping_rules` is empty. Users who want *custom* thresholds (e.g. "also promote high-betweenness nodes") write an explicit rule.
- **`source_file_ext` is how MAP-06 is expressed.** There is no hardcoded extension routing in Phase 3; it all flows through rules. Users who don't want sub-folder routing just don't write those rules, and all source files fall into `folder_mapping.source` (default `Atlas/Sources/`).
- **Community labels driven by top god node make the vault read like a textbook.** `Transformer.md`, `Auth_Service.md`, `Payment_Gateway.md` — not `Community 0.md`, `Community 1.md`. This is the single decision that turns graphify's output from "technical dump" into "readable knowledge map".
- **`first-match-wins` means rule order is part of the user's spec.** Docs must call this out explicitly. The validator's dead-rule warning (D-45) is the guardrail — users will absolutely write rules in the wrong order on their first try.
- **Regex guards via length caps, not timeouts.** Python's stdlib `re` has no timeout. The mitigation is: cap pattern length (512 chars), cap candidate string length (2048 chars), compile at profile load (fail-fast on `re.error`). Consistent with how `security.py` handles validator inputs.
- **Skipped-node set is an audit artifact.** `MappingResult.skipped_node_ids` should surface in `GRAPH_REPORT.md` during Phase 5 wiring — users need to know graphify dropped their `.auth_flow()` method stubs, even though it's the right call.
- **Size-1 isolates pathway.** `cluster.py:87` explicitly carves isolates into their own communities. Phase 3 must test this — a single isolated node with zero neighbors is a real edge case in small corpora.
- **`analyze.py` is the single source of truth for topology filters.** Importing `_is_file_node` and `_is_concept_node` across module boundaries (leading underscore) is a stylistic trade-off — acceptable for v1, consider promoting to public `is_file_node` / `is_concept_node` in a future cleanup pass.

</specifics>

<deferred>
## Deferred Ideas

- **Boolean-tree matchers** (`all_of` / `any_of` / `not_of`) — v2 extension. Flat `when:` entries compose via rule order for v1. Rejected for v1 in D-43 after considering the validator burden.
- **Rule output beyond `note_type` + `folder`** (tags, up injection, frontmatter overrides) — rejected in D-46 to keep classification narrow. If users need per-rule frontmatter customization, custom templates in `.graphify/templates/` are the escape hatch.
- **Bridge-node topology matcher** (`{topology: bridge_node}`) — interesting v2 extension using betweenness centrality. Not required for MAP-02..MAP-06.
- **Per-community template overrides** (v2 CFG-03) — not a Phase 3 concern. Community identity is here; template selection by community is a Phase 2 v2 extension.
- **LLM-generated community names** — deferred to future work. D-58's top-god-node heuristic is deterministic, free, and produces readable names. If a user wants richer names they can pass a `community_labels` dict from Phase 5 in a future enhancement.
- **Classification result caching** — `MappingResult` is cheap to recompute and depends on the graph structure, which the existing semantic cache (`cache.py`) doesn't cover. Not worth a second cache layer for v1.
- **`members_by_type` ordering by degree** — for now members are grouped by type, and within a group ordered alphabetically by label (Phase 2's current behavior). Sorting by degree inside each group would better surface importance; defer unless users request it.
- **Hash-based community_tag slugs** — rejected in D-59 because readable tags are non-negotiable for Obsidian tag pane usability.
- **Auto-lowering of `top_n` or MOC threshold for small graphs** — rejected in D-49 and D-52 in favor of deterministic, predictable behavior. Tiny corpora just get tiny vaults; that's correct.
- **Two-pass classification with conflict resolution** — rejected in D-45 in favor of first-match-wins. Users who want conflict detection get it via the dead-rule validator warning.

</deferred>

---

*Phase: 03-mapping-engine*
*Context gathered: 2026-04-11*
