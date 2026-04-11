# Phase 3: Mapping Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 03-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 03-mapping-engine
**Areas discussed:** Mapping rule DSL, God-node threshold, Below-threshold collapse, Community label source

---

## Gray area selection

**Question:** Which gray areas do you want to discuss for Phase 3 (Mapping Engine)?

| Option | Description | Selected |
|--------|-------------|----------|
| Mapping rule DSL | Shape of `mapping_rules` entries, matchers, conflict resolution, rule output | ✓ |
| God-node threshold | Definition of god node for classification + synthetic filter scope | ✓ |
| Below-threshold collapse | Where sub-threshold communities go, isolate handling, empty-graph fallback | ✓ |
| Community label source | MOC display name, tag slug derivation, sibling selection | ✓ |

**User's choice:** All four selected (multiSelect).

---

## Mapping rule DSL

### Rule shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat `when/then` | `{when: {matcher}, then: {note_type, folder}}` per entry | ✓ |
| Boolean tree | `{when: {all_of/any_of/not_of}, then: {...}}` | |
| Single-key shorthand | `{file_type: person, then: person}` compact form | |

**User's choice:** Flat when/then (recommended).
**Notes:** Easy to validate, readable, composes via rule order. Validator can point at `mapping_rules[n].when.<key>` for error messages.

### Matcher operators

| Option | Description | Selected |
|--------|-------------|----------|
| equals / in | Scalar and set membership on node attributes | ✓ |
| topology facts | god_node, community_size_gte/lt, cohesion_gte, is_source_file | ✓ |
| source_file_ext / source_file_matches | Extension and path regex for MAP-06 | ✓ |
| regex / contains | Full regex and substring matchers (initially marked "defer") | ✓ |

**User's choice:** All four selected (multiSelect). User overrode the "defer" recommendation on regex/contains.
**Follow-up confirmation question** asked whether regex/contains should really ship in v1:

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include both with guards | Ship regex + contains, guard with input length caps per security.py | ✓ |
| regex only, skip contains | contains is redundant with regex | |
| Defer both to v2 | Revert to equals/in/topology/source_file_ext only | |

**User's choice:** Yes, include both with guards.
**Notes:** Will use input length caps (pattern ≤512 chars, candidate ≤2048 chars) as the ReDoS mitigation since Python's stdlib `re` has no timeout. Compile at profile load to fail fast.

### Conflict resolution

| Option | Description | Selected |
|--------|-------------|----------|
| First match wins | Rules evaluated top-down, short-circuit on first match | ✓ |
| Last match wins | All evaluated, later matches override earlier | |
| Most-specific wins | Engine ranks rules by matcher-key count | |

**User's choice:** First match wins (recommended).
**Notes:** iptables/nginx mental model. Validator will emit dead-rule warnings for strictly-shadowed rules.

### Rule output

| Option | Description | Selected |
|--------|-------------|----------|
| note_type + optional folder | note_type required, folder defaults to folder_mapping | ✓ |
| note_type + folder + tags + up | Rule can also inject frontmatter | |
| Just note_type | Folder always derived from folder_mapping; no per-rule overrides | |

**User's choice:** note_type + optional folder (recommended).
**Notes:** Keeps classification narrow. Folder override is the mechanism for MAP-06 source-file routing.

---

## God-node threshold

### God node definition

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse analyze.god_nodes | Call the existing function with configurable top_n | ✓ |
| Degree-percentile | Top X% of degree distribution | |
| Absolute min-degree | Degree >= N configurable floor | |

**User's choice:** Reuse analyze.god_nodes (recommended).
**Notes:** Single source of truth between report.py and mapping.py. `_DEFAULT_PROFILE` gains `topology.god_node.top_n: 10`.

### Empty god-node set behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Zero Things is fine | No fallback; real nodes fall through to statement | ✓ |
| Promote highest-degree | Ensure at least one Thing even in tiny graphs | |
| Lower top_n automatically | Adaptive based on graph size | |

**User's choice:** Zero Things is fine (recommended).
**Notes:** Deterministic, no implicit scaling. Tiny vaults are correct.

### Synthetic-node filter scope

| Option | Description | Selected |
|--------|-------------|----------|
| Skip synthetic nodes entirely | Apply _is_file_node/_is_concept_node globally | ✓ |
| Map file hubs to Source notes | Hubs become Source notes via MAP-06 | |
| Profile-configurable flag | topology.exclude_synthetic with default true | |

**User's choice:** Skip synthetic nodes entirely (recommended).
**Notes:** But with an exception — a rule explicitly using `{topology: is_source_file}` can opt hubs back in. Concept nodes unconditionally skipped (defined by absent metadata).

---

## Below-threshold collapse

### Parent MOC resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Nearest-by-edge-count host | Host = community with most inter-community edges to C | ✓ |
| Single 'Uncategorized' bucket | All below-threshold merge into one MOC | |
| Inline at Atlas root | No MOC; members live under Atlas/Dots | |

**User's choice:** Nearest-by-edge-count host (recommended).
**Notes:** Ties broken by largest host, then lowest community_id for determinism. One pass over G.edges() using the community map.

### Isolate handling

| Option | Description | Selected |
|--------|-------------|----------|
| Treat as below-threshold | Size-1 communities use the same nearest-host path | ✓ |
| Classify normally, no MOC | Isolates skip collapse, get default folder, no community_tag | |
| Drop from vault | Record in skipped_node_ids | |

**User's choice:** Treat as below-threshold (recommended).
**Notes:** If an isolate has zero neighbors it falls through to the bucket MOC.

### All-below-threshold edge case

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to bucket MOC | Synthesize 'Uncategorized' MOC only when needed | ✓ |
| Lower threshold automatically | Adaptive MOC threshold for tiny graphs | |
| Emit no MOCs, flat vault | Every node becomes a Statement under Atlas/Dots | |

**User's choice:** Fall back to bucket MOC (recommended).
**Notes:** Synthetic community_id = -1 sentinel, label "Uncategorized", folder from folder_mapping.moc. Only emitted when a below-threshold community has no host.

---

## Community label source

### MOC display label

| Option | Description | Selected |
|--------|-------------|----------|
| Top god node label, fallback "Community N" | Highest-degree real node's label | ✓ |
| Caller-supplied labels | Accept community_labels dict parameter | |
| Literal "Community N" | No heuristic, deterministic | |
| Hybrid: caller, then god node, then "Community N" | Three-tier fallback | |

**User's choice:** Top god node label, fallback "Community N" (recommended).
**Notes:** Deterministic, pure-function derivation. Produces readable vaults (Transformer.md, Auth_Service.md).

### Tag slug derivation

| Option | Description | Selected |
|--------|-------------|----------|
| safe_tag(label) | Reuse Phase 1 slug helper | ✓ |
| Short stable hash | 8-char hash of label | |

**User's choice:** safe_tag(label) (recommended).
**Notes:** Readable tags are non-negotiable for Obsidian tag pane.

### Sibling label population

| Option | Description | Selected |
|--------|-------------|----------|
| Other god nodes in community, capped 5 | Sorted by degree, non-self | ✓ |
| All community members | Every other real node | |
| Claude's discretion | Defer to planner | |

**User's choice:** Other god nodes in same community, capped at 5 (recommended).
**Notes:** Keeps `related:` frontmatter readable. Non-god nodes get empty siblings.

---

## Wrap-up

**Question:** Ready for CONTEXT.md?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Write 03-CONTEXT.md now; remaining micro-decisions become Claude's Discretion | ✓ |
| Explore more gray areas | Surface additional ambiguities | |

**User's choice:** I'm ready for context (recommended).

---

## Claude's Discretion

Deferred to plan-phase — will be resolved when 03-RESEARCH.md is in hand:

- Module name: `graphify/mapping.py` vs `graphify/classify.py`
- Public function shape: single `classify()` returning `MappingResult` dataclass vs paired `classify_nodes()` / `classify_communities()`
- Whether `validate_rules(rules)` lives in `profile.py` or `mapping.py`
- `rule_traces` debug payload scope (v1 or v2)
- Caching strategy for topology matcher evaluations (once per community vs once per node)
- Test fixture strategy — extend Phase 2's `make_min_graph` vs new dedicated classification fixture

## Deferred Ideas

- Boolean-tree matchers (`all_of` / `any_of` / `not_of`) — v2
- Rule output beyond note_type + folder (tags, frontmatter overrides) — v2
- Bridge-node topology matcher — v2
- LLM-generated community names — future enhancement
- Classification result caching — not worth a second cache layer for v1
- `members_by_type` ordering by degree — defer unless users request it
- Hash-based community_tag slugs — rejected, readability wins
- Auto-lowering of thresholds for small graphs — rejected, determinism wins
- Two-pass classification with conflict resolution — rejected, first-match-wins + dead-rule warning is the model
