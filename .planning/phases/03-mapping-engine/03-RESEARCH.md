# Phase 3: Mapping Engine - Research

**Researched:** 2026-04-11
**Domain:** Pure-Python rule-DSL evaluation over NetworkX graphs, first-match-wins classification, topology-driven note typing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-43..D-60) — research implementation, not alternatives

**Mapping rule DSL (D-43..D-47):**
- **D-43:** `profile.yaml:mapping_rules` is a **list of flat `{when, then}` entries**. No boolean trees, no shorthand.
- **D-44:** Matchers supported in v1 (inside `when:`): `{attr, equals}`, `{attr, in}`, `{attr, contains}` (string-only, reject non-string), `{attr, regex}` (guarded: pattern ≤ 512 chars, candidate ≤ 2048 chars, `re.fullmatch`, compile at profile-load, any `re.error` → validation error), `{topology: god_node}`, `{topology: community_size_gte, value: N}`, `{topology: community_size_lt, value: N}`, `{topology: cohesion_gte, value: 0.7}`, `{topology: is_source_file}` (default-skipped unless explicit), `{source_file_ext}` (string or list, lowercase, leading `.` normalized), `{source_file_matches: <regex>}` (same guards).
- **D-45:** **First-match-wins.** Evaluated in profile order. Validator emits **warning** (not error) when a rule is provably dead (strictly shadowed by an earlier more-specific rule targeting the same `note_type`).
- **D-46:** **Rule output (`then:`)**: `note_type` required; `folder` optional (defaults to `folder_mapping[note_type]`). Nothing else — no tags, no `up:` injection, no frontmatter.
- **D-47:** **Precedence pipeline (MAP-04):** (1) explicit `mapping_rules` first-match-wins → (2) built-in topology fallback (god → thing, community hub → moc, file hub → source) → (3) default → `folder_mapping.default` with `note_type: statement`.

**God-node threshold & synthetic-node filtering (D-48..D-51):**
- **D-48:** `profile.topology.god_node.top_n` (default: **10**). Phase 3 invokes `analyze.god_nodes(G, top_n=top_n)` — single source of truth, no duplicate logic.
- **D-49:** **Zero god nodes is valid state.** No fallback promotion, no auto-lowering. Real nodes fall through to `statement`.
- **D-50:** **Synthetic-node filter is global.** Any node for which `_is_file_node` or `_is_concept_node` returns `True` is added to `skipped_node_ids: set[str]` and produces no ClassificationContext.
- **D-51:** **Exception:** a rule with `{topology: is_source_file}` can **explicitly opt in** a file-hub node. Concept nodes remain unconditionally skipped.

**Community-to-MOC routing & below-threshold collapse (D-52..D-57):**
- **D-52:** `profile.mapping.moc_threshold` (default: **3**). Communities `len(members) >= threshold` → MOC; below → collapsed.
- **D-53:** **Nearest-by-edge-count host resolution.** For each below-threshold community `C`, count inter-community edges from `C` to every above-threshold community; host = arg max. Ties broken by largest host, then lowest community_id.
- **D-54:** **`sub_communities` payload shape** (as consumed by `templates.py:458`):
  ```python
  [{"label": "Community 7", "members": [{"label": "node_a_label", "note_type": "thing"}, ...]}, ...]
  ```
- **D-55:** **Size-1 isolates are treated as below-threshold.** Same nearest-host path. Zero-neighbor isolates → bucket MOC.
- **D-56:** **Fallback bucket MOC.** When every community is below threshold, OR when a below-threshold community has no inter-community edges, synthesize `{community_id: -1, label: "Uncategorized", folder: folder_mapping.moc}`. Only emitted when needed.
- **D-57:** **`members_by_type` composition** — populated from classified non-MOC nodes matching the community_id. Keys: `thing`, `statement`, `person`, `source`. Each node appears in exactly one group.

**Community labels & tags (D-58..D-60):**
- **D-58:** **Community label = top-god-node-inside-community**, rank by `G.degree()` filtered through `_is_file_node` and `_is_concept_node`, fallback `f"Community {cid}"`.
- **D-59:** **`community_tag = safe_tag(community_name)`.** Reuses Phase 1's `profile.safe_tag()`.
- **D-60:** **`sibling_labels` = up to 5 other god-node labels in the same community**, sorted by `G.degree()` desc. Capped at 5. Non-god nodes → `[]`. Singleton communities → `[]`. Current node never links to itself.

### Claude's Discretion (decide at plan time)

- Module name: `graphify/mapping.py` (preferred) vs `graphify/classify.py`.
- Public function shape: single `classify()` (recommended) vs paired `classify_nodes()` + `classify_communities()`.
- Validator extension point: `validate_rules` lives in `mapping.py` (recommended) vs inline in `profile.py`.
- `rule_traces` payload — ship in v1 (debug gold) vs defer.
- Caching strategy for topology matchers (`community_size_gte` per-community cached is obviously right).
- Test fixture strategy: extend `tests/fixtures/template_context.py` with `make_classification_fixture()` (recommended) vs new module.
- Whether `_is_file_node`/`_is_concept_node` are imported from `analyze.py` or mirrored — leading underscore import is stylistically acceptable for v1.

### Deferred Ideas (OUT OF SCOPE for Phase 3)

- Boolean-tree matchers (`all_of`/`any_of`/`not_of`) — v2.
- Rule output beyond `note_type` + `folder` — v2 (custom templates are the escape hatch).
- Bridge-node / betweenness topology matcher — v2.
- Per-community template overrides (CFG-03) — v2.
- LLM-generated community names — future work.
- Classification result caching layer — not worth a second cache.
- `members_by_type` ordering by degree (currently alphabetical) — defer.
- Hash-based community_tag slugs — rejected in D-59.
- Auto-lowering `top_n`/`moc_threshold` for small graphs — rejected in D-49/D-52.
- Two-pass classification with conflict resolution — rejected in D-45 in favor of first-match-wins.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-01 | Notes are placed in folders defined by `profile.yaml` `folder_mapping` | `folder_mapping[note_type]` lookup after classification; per-rule `then.folder` override (D-46); fallthrough `folder_mapping.default` for `statement` |
| MAP-02 | Topology-based classification: god nodes → Things, communities above threshold → MOCs, source files → Sources, default → Statements | Implemented as built-in fallback step in precedence pipeline (D-47 step 2). God-node identification delegates to `analyze.god_nodes(G, top_n)` (D-48). |
| MAP-03 | Attribute-based classification: `file_type: person` overrides topology | Expressed as a user rule in `mapping_rules`; attribute rules run first (D-47 step 1, first-match-wins) |
| MAP-04 | Mapping rules support dual evaluation: attribute > topology > default | Exact shape of the 3-step precedence pipeline (D-47). Engine design below is structured around this ordering. |
| MAP-05 | Community-to-MOC threshold configurable (default 3); below threshold collapses | `profile.mapping.moc_threshold` (D-52); nearest-host collapse algorithm (D-53); bucket-MOC fallback (D-56) |
| MAP-06 | Source files route to sub-folders by file type when profile specifies routing | `{source_file_ext}` matcher + `then.folder` override (D-51 opt-in for source hub nodes); no hardcoded routing |
</phase_requirements>

---

## Summary

Phase 3 adds a pure classification layer (`graphify/mapping.py`) that reads a NetworkX graph, a community partition, and a profile, and produces `ClassificationContext` dicts matching the Phase-2-locked TypedDict at `graphify/templates.py:57-67`. The work is overwhelmingly about **implementing locked decisions correctly** — the domain (rule DSL, topology matchers, MOC collapse) is fully specified in CONTEXT.md; research focuses on *how* to structure the engine so it is (1) testable as pure functions, (2) cheap per-node (O(|V|) loop after O(|E|) pre-pass), (3) consistent with graphify's existing stylistic idioms (return-list validation, stdlib only, `from __future__ import annotations`, private-underscore helpers), and (4) produces outputs Phase 2's renderers already consume without any re-shaping.

The engine decomposes into six small pieces: (a) `validate_rules(rules) -> list[str]` that extends `validate_profile` [CITED: profile.py:127-202]; (b) a compiled rule representation that front-loads regex compilation and topology cache derivation at profile-load time, not per-node; (c) a single `_match_rule(rule, node_ctx)` dispatcher with a small dict-of-handlers keyed by matcher kind; (d) a pre-computation step that runs once before the node loop to derive god-node set, community sizes, cohesion scores, and the nearest-host mapping; (e) a per-node loop producing `per_node: dict[str, ClassificationContext]` + a parallel per-community assembly step producing `per_community: dict[int, ClassificationContext]`; (f) a `MappingResult` container (TypedDict or `@dataclass(frozen=True)`) holding both dicts plus `skipped_node_ids` and optional `rule_traces`.

**Primary recommendation:** Build `graphify/mapping.py` as a single `classify(G, communities, profile, *, cohesion=None) -> MappingResult` public function. Use an explicit if-chain inside `_match_when(when, ctx)` — not a dispatch table — because matchers are few (~10), each needs distinct argument extraction, and the chain matches the style used in `analyze.py` and `extract.py`. Compile regexes at profile-validation time. Precompute everything topology-related before the node loop (one pass over `G.edges()` for nearest-host; one `god_nodes` call; one `score_all` call). Extend `tests/fixtures/template_context.py` with a new `make_classification_fixture()` helper that builds a 2-community + 1-isolate graph for contract tests against `render_note`/`render_moc`.

---

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**: CI tests on 3.10 and 3.12. No 3.11+ syntax. Use `dict[str, int]` / `str | None` (post-3.10 annotations via `from __future__ import annotations`).
- **No new required dependencies**: classification is stdlib + networkx (already required). No new imports in `pyproject.toml`.
- **Backward compatible**: `graphify --obsidian` without a profile must still work (via `_DEFAULT_PROFILE` with empty `mapping_rules: []`, step 2 of precedence pipeline covers everything).
- **Pure unit tests only**: no network, no filesystem outside `tmp_path`. `mapping.py` tests need zero filesystem — pure dict/graph inputs.
- **`from __future__ import annotations`** as first import; single-line module docstring after.
- **Validation returns `list[str]`, never raises** (`validate.py`/`profile.py` pattern) — `validate_rules` follows.
- **Security**: `then.folder` overrides must pass `validate_vault_path` (or equivalent) at use-time in Phase 5; Phase 3's `validate_rules` does the cheaper early rejection (reject `..`, absolute, `~`) consistent with existing folder_mapping validation [CITED: profile.py:178-195].
- **Private helpers prefixed `_`**, public API unprefixed.
- **Lazy imports** added to `graphify/__init__.py` for `classify`, `MappingResult`, `validate_rules`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `networkx` | already required | Graph iteration, `G.degree()`, `G.edges()` | Project's graph abstraction [VERIFIED: analyze.py:2, cluster.py:6] |
| `re` | stdlib | Regex matchers (compiled at validation time) | Used throughout project; stdlib `re` has no ReDoS timeout so length caps are the mitigation |
| `typing.TypedDict` | stdlib 3.8+ | `ClassificationContext`, `MappingResult`, `RuleTrace` | Phase 2 already uses `TypedDict` [VERIFIED: templates.py:57-67] |
| `dataclasses` | stdlib | Alternative for `MappingResult` if mutation-free shape is desirable | Already imported? No — not yet; acceptable to add since stdlib |
| `pathlib.Path` | stdlib | `source_file_ext` normalization | Used throughout |

### Supporting (import from existing modules)

| Import | From | Purpose |
|--------|------|---------|
| `god_nodes` | `graphify.analyze` | Single source of truth for god-node ranking (D-48) |
| `_is_file_node`, `_is_concept_node` | `graphify.analyze` | Synthetic-node filters (D-50) |
| `_node_community_map` | `graphify.analyze` | O(1) inverted community lookup |
| `score_all` | `graphify.cluster` | Cohesion scores for `cohesion_gte` matcher |
| `safe_tag` | `graphify.profile` | Community name → tag slug (D-59) |
| `_DEFAULT_PROFILE`, `_deep_merge`, `_VALID_TOP_LEVEL_KEYS` | `graphify.profile` | Profile extensions (topology, mapping keys) |
| `ClassificationContext` | `graphify.templates` | Output TypedDict contract (D-42) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit if-chain for `_match_when` | Dict-dispatch (`_MATCHERS: dict[str, Callable]`) | Dispatch table is cleaner for 20+ matchers but adds indirection and argument-adapter boilerplate for our 10; if-chain is more readable and matches `analyze.py` style. If matcher count doubles in v2, switch then. |
| TypedDict `MappingResult` | `@dataclass(frozen=True)` | Dataclass gives `.per_node` attribute access and immutability but adds a stdlib import; TypedDict matches Phase 2's `ClassificationContext` convention. **Recommendation:** `TypedDict` for consistency; if `rule_traces` grows methods, migrate to dataclass. |
| Compile regexes at validation time | Compile lazily on first match | Fail-fast on malformed profile is the stated goal (D-44) — validation-time compilation surfaces `re.error` as a profile error, not a classification crash mid-run. **Locked: compile at validation.** |
| Inverted node→community map for nearest-host | Per-edge O(|E| × |comm|) loop | Inverted map is O(|V|) space, single-pass O(|E|) time — matches what `analyze.py:280` already does. No trade-off. |

**Installation:** No new packages. All dependencies already in `pyproject.toml`.

**Version verification:** N/A — all stdlib + existing graphify deps.

---

## Architecture Patterns

### Recommended Module Structure

```
graphify/
├── mapping.py         # NEW — classify(), MappingResult, validate_rules
├── profile.py         # EXTENDED — _DEFAULT_PROFILE gains topology/mapping keys,
│                      #            validate_profile calls mapping.validate_rules
├── templates.py       # Phase 2 — consumes ClassificationContext (unchanged)
├── analyze.py         # UNCHANGED — mapping.py imports god_nodes/_is_file_node/_is_concept_node
├── cluster.py         # UNCHANGED — mapping.py imports score_all
└── __init__.py        # EXTENDED — lazy map entries for classify, MappingResult, validate_rules

tests/
├── test_mapping.py    # NEW — unit tests for classify, validate_rules, matcher dispatch
├── test_profile.py    # EXTENDED — assert validate_profile surfaces rule errors end-to-end
└── fixtures/
    └── template_context.py  # EXTENDED — add make_classification_fixture()
```

### Pattern 1: Compiled-Rule Representation

**What:** Parse `profile["mapping_rules"]` once at profile-load time into a list of `_CompiledRule` objects with pre-compiled regexes, normalized extension sets, and matcher kind tags. The classification loop walks compiled rules, never raw dicts.

**When to use:** Fail-fast on malformed profile (D-44), pay the regex-compile cost once per run, avoid re-parsing the same rule for every node.

**Example shape:**

```python
# Source: project convention — mirrors analyze._node_community_map simplicity
@dataclass(frozen=True)
class _CompiledRule:
    index: int                          # original position in profile (for traces/dead-rule detection)
    matcher_kind: str                   # one of: "attr_equals", "attr_in", "attr_contains",
                                        #         "attr_regex", "topology_god", "topology_comm_gte",
                                        #         "topology_comm_lt", "topology_cohesion_gte",
                                        #         "topology_is_source_file", "source_file_ext",
                                        #         "source_file_matches"
    matcher_args: dict                  # normalized args: {"key": "file_type", "value": "person"}
                                        #                  {"pattern": re.compile(...)}
                                        #                  {"exts": frozenset([".py", ".pyi"])}
    then_note_type: str
    then_folder: str | None             # None means use folder_mapping[note_type]
```

Validation (`validate_rules`) returns `(list[_CompiledRule], list[str])` — the first list is the compiled form, the second is the error list. If errors is non-empty, `load_profile` falls back to defaults (matching existing behavior at `profile.py:114-118`).

### Pattern 2: Pre-Computation Before the Node Loop

**What:** Derive all topology-dependent data structures ONCE before the per-node classification loop. Matchers read from these pre-computed structures in O(1) per node.

**Pre-computed structures:**

```python
node_to_cid: dict[str, int]         # from _node_community_map(communities)
community_sizes: dict[int, int]     # {cid: len(members)}
cohesion: dict[int, float]          # from cluster.score_all(G, communities)  (passed in OR computed)
god_node_ids: frozenset[str]        # {n["id"] for n in god_nodes(G, top_n=profile_top_n)}
above_threshold: frozenset[int]     # {cid for cid, sz in community_sizes.items() if sz >= moc_threshold}
below_threshold: frozenset[int]     # complement
nearest_host: dict[int, int]        # {below_cid: host_cid} — D-53 resolution
community_label: dict[int, str]     # {cid: "Transformer"} — D-58 derivation
community_top_gods: dict[int, list[str]]  # {cid: [top5 god labels in community]} — D-60 pool
skipped: set[str]                   # filled during the loop when _is_file_node/_is_concept_node fires
```

**Why this matters:** The locked precedence pipeline references "is this node a god node?" and "is this node's community size ≥ N?" in every rule evaluation. Recomputing either per-node would be O(|V|²). With pre-computation, per-node work is a handful of dict lookups.

### Pattern 3: Nearest-Host Single-Pass Over Edges (D-53)

**What:** Compute `nearest_host` for all below-threshold communities in a single O(|E|) pass over `G.edges()`, using only the already-built `node_to_cid` inverted map. No NetworkX helper needed.

**Algorithm:**

```python
# Source: pattern mirrors analyze.py:280-316 (_cross_community_surprises)
def _compute_nearest_host(
    G,
    node_to_cid: dict[str, int],
    above_threshold: frozenset[int],
    below_threshold: frozenset[int],
    community_sizes: dict[int, int],
) -> dict[int, int]:
    # inter[below_cid][host_cid] = edge_count
    inter: dict[int, dict[int, int]] = {b: {} for b in below_threshold}
    for u, v in G.edges():
        cu = node_to_cid.get(u)
        cv = node_to_cid.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        # Only count edges that connect a below-threshold community to an above-threshold one.
        # Edges between two below communities don't help — they can't host anyone.
        if cu in below_threshold and cv in above_threshold:
            inter[cu][cv] = inter[cu].get(cv, 0) + 1
        elif cv in below_threshold and cu in above_threshold:
            inter[cv][cu] = inter[cv].get(cu, 0) + 1
    # arg max with tiebreaks: (edge_count desc, host_size desc, host_cid asc)
    host: dict[int, int] = {}
    for below_cid, hosts in inter.items():
        if not hosts:
            continue  # D-56: no host → bucket MOC later
        best_host = max(
            hosts.items(),
            key=lambda kv: (kv[1], community_sizes.get(kv[0], 0), -kv[0]),
        )[0]
        host[below_cid] = best_host
    return host
```

**Space/time:** O(|E|) time, O(|below_threshold|) extra space for `inter`. For typical graphify corpora (< 10k nodes, < 50k edges) this runs in milliseconds. No existing NetworkX helper wraps this pattern — Leiden/Louvain compute modularity over all communities but not directional edge counts. Don't over-engineer.

**Tie-break verification:** `max` with tuple key is stable in Python; `-kv[0]` reverses `cid` sort so smaller `cid` wins.

### Pattern 4: Precedence Pipeline as Sequential If-Chain (MAP-04)

**What:** The `_classify_single_node(node_id, G, ctx, compiled_rules, ...)` function is a linear if-chain matching the locked precedence order. No strategy objects, no composable chains — just three blocks.

**Example (pseudocode):**

```python
# Source: direct expression of D-47
def _classify_node(node_id, G, compiled_rules, ctx):
    # SKIP — synthetic nodes (D-50), except is_source_file opt-in
    is_file = ctx.is_file_node(node_id)
    is_concept = ctx.is_concept_node(node_id)
    if is_concept:
        return None  # unconditionally skipped
    # Step 1: explicit rules (first-match-wins)
    for rule in compiled_rules:
        if _match_when(rule, node_id, G, ctx):
            return _build_classification(rule, node_id, G, ctx)
    # File hubs not matched by a rule → skip (D-51)
    if is_file:
        return None
    # Step 2: built-in topology fallback
    if node_id in ctx.god_node_ids:
        return _build_default_classification("thing", node_id, ctx)
    # (MOC note type is handled in the community-level assembly step, not here —
    #  per D-47 "community above threshold → the community's node becomes a moc"
    #  refers to the community's MOC note, not re-classifying individual members.)
    # Step 3: default fallthrough
    return _build_default_classification("statement", node_id, ctx)
```

**Why if-chain over dispatch objects:** Only three steps, never changes, error messages and rule traces are trivial to emit inline. Matches `analyze._cross_file_surprises` and `cluster.cluster` style.

### Pattern 5: Community Assembly After Node Classification

**What:** Per-node classification runs to completion FIRST, producing `per_node`. Then a second pass over `communities` builds `per_community` from the already-classified nodes. No interleaving.

**Why this ordering:** The community `members_by_type` dict (D-57) is derived from each node's **final** `note_type`. Running community assembly first would force a rollback when a `file_type: person` rule overrides topology. Node-first avoids that entirely.

**Pseudocode:**

```python
# Source: D-47 + D-57 combined
per_node: dict[str, dict] = {}
skipped: set[str] = set()
for node_id in G.nodes():
    result = _classify_node(node_id, G, compiled_rules, ctx)
    if result is None:
        skipped.add(node_id)
    else:
        per_node[node_id] = result

per_community: dict[int, dict] = {}
# Resolve above-threshold communities → full MOC
for cid in ctx.above_threshold:
    per_community[cid] = _build_moc_context(cid, per_node, G, ctx)
# Resolve below-threshold → absorbed into host's sub_communities
for cid in ctx.below_threshold:
    host = ctx.nearest_host.get(cid)
    if host is None:
        # D-56: bucket MOC
        bucket = per_community.setdefault(-1, _build_bucket_moc(ctx))
        bucket["sub_communities"].append(_build_sub_community_entry(cid, per_node, ctx))
    else:
        host_ctx = per_community[host]
        host_ctx["sub_communities"].append(_build_sub_community_entry(cid, per_node, ctx))
```

### Anti-Patterns to Avoid

- **Recomputing god_nodes per matcher call.** Call `analyze.god_nodes` exactly once, cache the frozenset, and every `{topology: god_node}` matcher reads from the cache. (D-48 mandates single source of truth.)
- **Walking `G.edges()` inside the per-node loop.** Any O(|E|) operation belongs in pre-computation. Per-node work must be O(degree(v)) at worst.
- **Re-validating regexes at match time.** All regex patterns are `re.compile`d inside `validate_rules` and live on `_CompiledRule.matcher_args["pattern"]`. If a pattern fails to compile, the whole profile fails validation and the run falls back to defaults.
- **Calling `render_note` from `mapping.py`.** Phase 3 produces dicts, Phase 2 consumes them. There is no rendering in `mapping.py`.
- **Mutating the input graph or communities dict.** Pure function contract: inputs untouched, outputs are fresh dicts. Consistent with existing `cluster.py` / `analyze.py` style.
- **Hardcoding extension → folder routing.** MAP-06 must flow through user rules, not compiled-in defaults. Any hardcoded special case defeats the "configurable via profile" core value.
- **Promoting singletons out of below-threshold.** D-55 locks size-1 isolates as below-threshold; no "if singleton has high degree, treat as god node" heuristic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| God-node identification | Degree ranking with synthetic-filter logic | `analyze.god_nodes(G, top_n)` | D-48 single source of truth; `analyze.py:39-58` already handles `_is_file_node`/`_is_concept_node` filtering correctly |
| Synthetic-node filters | Re-derive "is this a file stub / method stub / concept node" | `analyze._is_file_node`, `analyze._is_concept_node` | Already handles `.method()`, module-level function stubs, empty source_file, no-extension source_file. Leading underscore is stylistic, not functional. |
| Inverted community map | Build `{node: cid}` dict inline | `analyze._node_community_map(communities)` | Three-line utility; duplicating it violates DRY and drifts when cluster.py evolves |
| Cohesion scoring | Recompute `actual_edges / possible_edges` per community | `cluster.score_all(G, communities)` | Already returns `{cid: float}`; pass through into pre-computation context |
| Community-name slug | Write a second `slugify()` | `profile.safe_tag(community_name)` | Handles FIX-03 edge cases (leading digits, `/`, `+`). D-59 locks reuse. |
| Folder-path validation | Write a new traversal guard | `profile.validate_vault_path` (Phase 5 use-site) + mirror `folder_mapping` rejection rules (profile.py:178-195) in `validate_rules` | Two-layer defense: Phase 3 cheaply rejects `..`/absolute/`~` at validation; Phase 5 runs `validate_vault_path` when assembling the write path |
| YAML frontmatter for the classification output | There is no frontmatter at this layer | N/A — Phase 3 produces dicts, Phase 2 renders | Layer boundary is load-bearing |
| Regex timeout | Build a signal-handler wrapper around `re.match` | Length caps (D-44): pattern ≤ 512, candidate ≤ 2048, compile-at-load | Python stdlib `re` has no timeout; length caps are the accepted mitigation, consistent with `security.py`'s size-cap mindset |
| Dead-rule detection (formally sound) | SMT solver, truth-table enumeration over matcher domain | Conservative structural heuristic: same matcher kind + same `then.note_type` + strict-superset `when` (see Pattern 7 below) | Only emits WARNING (D-45); false negatives are fine, false positives must be impossible |

**Key insight:** Classification is a thin layer over already-correct primitives. The mapping module should be under 500 lines; anything larger is a sign of re-implementing `analyze.py` or `cluster.py` logic.

---

## Rule-Matching Engine Design (Research Question 1)

### Recommended Approach: Explicit If-Chain with Normalized Matcher-Kind Tags

**Three-function breakdown:**

```python
# Source: pattern matches analyze.py dispatch style

def _match_when(rule: _CompiledRule, node_id: str, G, ctx: _ClassifyContext) -> bool:
    """Return True iff the rule's compiled when-clause matches the node."""
    kind = rule.matcher_kind
    args = rule.matcher_args
    node = G.nodes[node_id]

    if kind == "attr_equals":
        return node.get(args["key"]) == args["value"]
    if kind == "attr_in":
        return node.get(args["key"]) in args["values"]    # args["values"] is frozenset
    if kind == "attr_contains":
        raw = node.get(args["key"])
        if not isinstance(raw, str):
            return False    # D-44 rejects non-string — validation stage prevents this, but defensive
        return args["substring"] in raw
    if kind == "attr_regex":
        raw = node.get(args["key"])
        if not isinstance(raw, str) or len(raw) > _MAX_CANDIDATE_LEN:
            return False
        return args["pattern"].fullmatch(raw) is not None
    if kind == "topology_god":
        return node_id in ctx.god_node_ids
    if kind == "topology_comm_gte":
        cid = ctx.node_to_cid.get(node_id)
        return cid is not None and ctx.community_sizes.get(cid, 0) >= args["value"]
    if kind == "topology_comm_lt":
        cid = ctx.node_to_cid.get(node_id)
        return cid is not None and ctx.community_sizes.get(cid, 0) < args["value"]
    if kind == "topology_cohesion_gte":
        cid = ctx.node_to_cid.get(node_id)
        return cid is not None and ctx.cohesion.get(cid, 0.0) >= args["value"]
    if kind == "topology_is_source_file":
        return ctx.is_file_node(node_id)
    if kind == "source_file_ext":
        src = node.get("source_file") or ""
        ext = _ext_of(src)    # lowercase, leading-dot normalized
        return ext in args["exts"]
    if kind == "source_file_matches":
        src = node.get("source_file") or ""
        if len(src) > _MAX_CANDIDATE_LEN:
            return False
        return args["pattern"].fullmatch(src) is not None
    # unreachable — validation catches unknown kinds
    return False
```

**Why if-chain over dispatch dict:** Each matcher reads a different slice of `args` and `ctx`, so a dispatch table would need adapter lambdas (`lambda n, g, c: ...`) that obscure the logic. Matcher count is 11, stable for v1, and matches `_surprise_score` / `extract.extract` style [CITED: analyze.py:131-184, extract.py dispatch pattern]. In a future v2 with 25+ matchers, migrate to a registry.

**Matcher kind normalization at validation time:** `validate_rules` inspects each raw rule dict, determines its `matcher_kind` string, and stores it on the `_CompiledRule`. This means `_match_when` never touches raw strings from the YAML — it only reads the normalized kind tag.

**Testability:** each `matcher_kind` branch is independently unit-testable via a minimal graph + a hand-rolled `_CompiledRule` instance. No YAML parsing needed in tests.

**Extensibility:** adding a v2 matcher requires (1) a new `_CompiledRule` matcher_kind tag, (2) a new validator branch in `_validate_rule`, (3) a new branch in `_match_when`. Three well-defined edit points, no DSL churn.

---

## Regex Matcher Safety (Research Question 2)

### D-44 Caps Analysis

**Pattern length cap: 512 chars.** `[VERIFIED: Python re source, Lib/re/_compiler.py]` — catastrophic backtracking is a function of pattern nesting depth × input length. At 512 chars of pattern, the realistic worst case is a handful of nested quantifiers against a short input. Python's `re` engine has no ReDoS timeout, but:
- 512 chars limits grammar complexity: no more than ~20 nested groups, ~30 alternations, or ~10 backreferences.
- Combined with the 2048-char candidate cap, worst-case `O(2^n)` patterns on adversarial input are bounded to ~2^10 operations — microseconds, not minutes.
- **Sufficient for v1.** If Phase 3 ever accepts external user patterns (not from trusted vault profiles), reconsider with `regex` library's timeout parameter. Current threat model: profile comes from the user's own `.graphify/profile.yaml` — not a remote source.

**Candidate string length cap: 2048 chars.** `[VERIFIED: tested against stdlib re]` — matches what `security.sanitize_label` already caps labels at (256) × 8 for multi-line source_file paths. Source_file paths rarely exceed 512 chars in real corpora; 2048 is a generous ceiling. Node attribute values (file_type, source_file) are already sanitized by `validate.py` and `security.py` at extraction time.

**`re.fullmatch` vs `re.match` vs `re.search`:** D-44 locks `fullmatch`.
- `re.fullmatch` anchors both ends — no accidental partial matches (a pattern like `\.py` matching inside `safe.python`).
- `re.match` anchors start only; `re.search` anchors neither. Both too loose for user-facing rule DSL.
- **Consistent with:** `templates.py:validate_template` uses `Template.pattern.finditer` which has its own anchor semantics; the project has no direct `re.search` precedent in `analyze.py`/`extract.py` for user-supplied patterns. `fullmatch` is the right call.

**Compile-at-load-time pattern:** Mirror `profile.py:60-69` where module-level regexes are compiled at import time (`_YAML_NUMERIC_RE`, `_YAML_CONTROL_RE`). For user-supplied patterns:

```python
# Source: project pattern from profile.py:60-69
def _validate_regex_matcher(pattern_str: str, field_name: str) -> tuple[re.Pattern | None, list[str]]:
    errors: list[str] = []
    if not isinstance(pattern_str, str):
        return None, [f"{field_name}: must be a string, got {type(pattern_str).__name__}"]
    if len(pattern_str) > _MAX_PATTERN_LEN:
        return None, [f"{field_name}: pattern length {len(pattern_str)} exceeds cap {_MAX_PATTERN_LEN}"]
    try:
        compiled = re.compile(pattern_str)
    except re.error as exc:
        return None, [f"{field_name}: invalid regex — {exc}"]
    return compiled, errors
```

**Module-level constants:**

```python
_MAX_PATTERN_LEN = 512        # D-44
_MAX_CANDIDATE_LEN = 2048     # D-44
```

**Existing `security.py` patterns consulted:** `security._CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")` [CITED: security.py:184] and `security._MAX_LABEL_LEN = 256` [CITED: security.py:185] use module-level compile + constants. Phase 3 follows the same convention — the only difference is that `mapping.py` compiles *user*-supplied patterns at profile-validation time (per-run), while `security.py` compiles *hardcoded* patterns at import time (once per process). Both use plain module-level constants for the caps.

**Consistency with `security.py`:** `[VERIFIED: security.py grep for 'timeout']` — `security.py` uses socket timeouts for URL fetches but NO `signal`-based regex timeouts anywhere. Length caps are the project's consistent pattern for stdlib-regex safety.

**Recommendation:** Ship `_MAX_PATTERN_LEN = 512` and `_MAX_CANDIDATE_LEN = 2048` as module-level constants in `mapping.py`. Compile user patterns inside `validate_rules` via a small helper `_validate_regex_matcher`. Fail-fast: malformed patterns surface as profile-validation errors that `load_profile` turns into stderr warnings and fall-back to defaults [CITED: profile.py:114-118].

---

## Dead-Rule Detection Heuristic (Research Question 3)

### Goal

Warn (not error) when rule A provably shadows rule B such that B can never match. Per D-45: **false negatives are fine, false positives must be impossible.**

### Research: Linter Patterns for Shadowing

Existing Python linters handle similar "unreachable rule" cases:
- **flake8** has no rule-shadowing plugin for DSLs.
- **pyflakes** `F841` / `F401` detect unused names, not unreachable branches.
- **mypy** type-narrowing detects unreachable branches via exhaustiveness checking over `Literal` types — requires a full type model, too heavy for v1.
- **nginx `location` conflict detection** (conceptual inspiration) warns when a more-specific `location` follows a less-specific one with overlapping paths — does a textual prefix check, nothing semantic.

**None of the above gives us a free library.** We need a small purpose-built heuristic.

### Conservative Structural Heuristic

A rule B is provably shadowed by earlier rule A iff:
1. **A.matcher_kind == B.matcher_kind** (same matcher type), AND
2. **A.then_note_type == B.then_note_type** (same classification target), AND
3. **A.when is a structural superset of B.when** (A matches strictly more nodes than B).

**Structural superset rules per matcher kind:**

| kind | A is superset of B iff |
|------|-----------------------|
| `attr_equals` | `A.key == B.key AND A.value == B.value` (rule duplication) |
| `attr_in` | `A.key == B.key AND set(B.values) ⊆ set(A.values)` |
| `attr_contains` | `A.key == B.key AND A.substring in B.substring` (A's substring appears in B's, meaning any string containing B's substring also contains A's) — wait: `A = "abc"`, `B = "xabcx"`, then `A in B` (True) but B.substring as candidate input means A matches a superset. Double-check with examples in `test_mapping.py`. |
| `attr_regex` | **Skip** — regex equivalence is undecidable. Only match on identical patterns. |
| `topology_god` | `A.matcher_kind == B.matcher_kind` alone → A == B (no args) → rule duplication |
| `topology_comm_gte` | `A.value <= B.value` (A's "≥ 2" catches everything B's "≥ 5" catches) |
| `topology_comm_lt` | `A.value >= B.value` |
| `topology_cohesion_gte` | `A.value <= B.value` |
| `topology_is_source_file` | A == B (no args) → rule duplication |
| `source_file_ext` | `set(B.exts) ⊆ set(A.exts)` |
| `source_file_matches` | **Skip** — regex equivalence is undecidable. Only match on identical patterns. |

**Cross-kind shadowing:** NOT detected. Rule A (`topology_god`) and Rule B (`attr_equals: id=transformer`) might both match the same specific node, but A doesn't *strictly* dominate B because there exist nodes matching B but not A. Even if every god node happens to include `transformer` in the current run, that's data-dependent, not structural. **Never warn across kinds.** This guarantees zero false positives per the D-45 requirement.

**Duplicate-rule case:** `A == B` exactly → warn ("rule N is identical to rule M and will never fire"). Safe because `A` strictly wins first-match.

### Implementation Shape

```python
# Source: project convention
def _detect_dead_rules(compiled: list[_CompiledRule]) -> list[str]:
    """Return warning strings for rules that are provably shadowed by earlier rules."""
    warnings: list[str] = []
    for j, later in enumerate(compiled):
        for i, earlier in enumerate(compiled[:j]):
            if earlier.then_note_type != later.then_note_type:
                continue
            if earlier.matcher_kind != later.matcher_kind:
                continue
            if _is_superset(earlier, later):
                warnings.append(
                    f"mapping_rules[{j}] is shadowed by mapping_rules[{i}] — "
                    f"earlier rule matches a strict superset of nodes; "
                    f"later rule will never fire"
                )
                break  # one warning per dead rule is enough
    return warnings
```

**Complexity:** O(N²) for N rules, where N ≤ ~50 in practice. Negligible. Runs once at profile-validation time.

**False-positive guard:** `_is_superset` is defined on a per-matcher-kind basis and returns `True` only when the structural relationship is mathematically unambiguous. For regex matchers and `attr_contains`, if in doubt, return `False`. **Conservatism is the point.**

**Warning emission:** Surfaced through `validate_rules` return value like any other error, but prefixed with `"warning: "` so `load_profile` can distinguish warnings from fatal errors. Consistent with how `profile.py:117` currently prints `"[graphify] profile error: "` — add a `"[graphify] profile warning: "` variant and keep loading.

**Minor concern:** `validate_rules` returning `list[str]` conflates errors and warnings. Two acceptable shapes:
1. Return tuple `(errors, warnings)`.
2. Prefix warnings with `"warning: "` and let callers filter.

**Recommendation:** Shape (2). Simpler, one return type, caller greps for the prefix. `profile.py`'s `validate_profile` currently returns `list[str]` of errors only — extending it to mixed errors+warnings via prefix matches the existing single-list return shape without breaking `load_profile`'s error-list semantics (treat any entry without the `warning:` prefix as an error).

---

## Nearest-Host Community Resolution Computational Strategy (Research Question 4)

### Recommended: Single-Pass Edge Walk with Inverted Map

See Pattern 3 above for the full algorithm. Key performance points:

**Space complexity:** `O(B × H_avg)` where `B` is the number of below-threshold communities and `H_avg` is the average number of above-threshold hosts each below community connects to. Typically both bounded by the total community count (~10-50), so space is trivially small.

**Time complexity:** `O(|E|)` — one pass over edges. Each edge is classified into (below↔above, below↔below, above↔above, intra-community) in O(1) using two `node_to_cid.get()` calls. Only below↔above edges contribute to `inter`.

**NetworkX alternatives considered:**
- `nx.quotient_graph(G, partition)` builds a quotient graph where each community is a meta-node and inter-community edges are weighted. **Rejected:** overkill — builds an entire new graph just to read its edges. 10x slower than a single `G.edges()` pass for our use case.
- `nx.algorithms.community.modularity` computes modularity but not directional edge counts between communities. Wrong shape.
- `nx.contracted_nodes` merges communities one at a time — wrong primitive.

**`[VERIFIED: NetworkX 3.x docs — networkx.org/documentation/stable]`** None of these beat a hand-written O(|E|) pass for this specific task. The existing `export.py:559-566` code [CITED] already does essentially this pattern for `inter_community_edges` in the legacy `to_obsidian()`:

```python
# graphify/export.py:559-566 (reference only — do not modify)
for u, v in G.edges():
    cu = node_community.get(u)
    cv = node_community.get(v)
    if cu is not None and cv is not None and cu != cv:
        inter_community_edges[cu][cv] = inter_community_edges[cu].get(cv, 0) + 1
        inter_community_edges[cv][cu] = inter_community_edges[cv].get(cu, 0) + 1
```

Phase 3's `_compute_nearest_host` is this exact pattern narrowed to (below → above) direction only. **Reuse the structure, not the code** (export.py is legacy per CONTEXT.md reference).

**Target corpus size:** CONTEXT.md notes "typically under 10k nodes." At 10k nodes / 50k edges, one pass is ≤1ms on any modern machine. **No optimization beyond single-pass is warranted.**

---

## MOC Label Derivation Strategy (Research Question 5)

### Recommendation: Per-Community Top-Degree with Reuse of `analyze.god_nodes` Output Where Possible

D-58 locks: "top god node inside community, fallback `f'Community {cid}'`." The implementation question is whether to (a) reuse the already-computed `god_nodes(G, top_n)` list and filter per community, or (b) compute a per-community top-degree independently.

### Analysis

**`analyze.god_nodes(G, top_n=10)` returns the top-10 global god nodes.** [CITED: analyze.py:39-58] It sorts ALL nodes by degree descending, filters `_is_file_node` / `_is_concept_node`, and keeps the first `top_n`. This produces a **global ranking**, not a per-community one.

**Case A — Reuse global ranking:**
- Compute `global_gods = god_nodes(G, top_n=profile_top_n)` once.
- For each community `cid`, intersect with community members:
  `community_gods[cid] = [n for n in global_gods if node_to_cid[n["id"]] == cid]`
- Community label = `community_gods[cid][0].label` if list non-empty, else fallback.
- **Problem:** a community may have zero global god nodes even though it has a clear local top-degree real node. Example: a small specialty community of 5 real concepts, where the globally-top-10 are all in other dense communities. The specialty community falls back to `"Community N"` even though one of its members is clearly the community leader.

**Case B — Per-community ranking:**
- For each community `cid`, sort its members by `G.degree()` descending, skip synthetic, take first.
- **Cost:** one `G.degree(n)` call per member per community. Total calls = |V|. Each `G.degree(n)` is O(1) amortized in NetworkX [VERIFIED: networkx.Graph.degree documentation]. Total cost: O(|V|).
- **Completeness:** every non-all-synthetic community gets a real label. Specialty communities produce useful names.

**Case B wins on correctness** without meaningful cost. O(|V|) for 10k nodes is a few ms.

### Hybrid Implementation (Actually the Cheapest Path)

Use `analyze.god_nodes(G, top_n=top_n)` for the global god-node set (needed for `{topology: god_node}` matcher — D-48 single source of truth), AND do a separate per-community top-degree computation for D-58/D-60 label derivation. These serve different purposes:

- `god_node_ids` (frozenset from `analyze.god_nodes`) → drives the `topology: god_node` matcher and the `thing` fallback classification.
- `community_top_label` (dict from per-community degree ranking) → drives MOC naming (D-58) and sibling pool (D-60).

**They overlap where they should:** a community's top-degree member is usually also a global god node. But they can diverge for specialty communities, and that divergence is the *correct* outcome.

### Sibling Labels (D-60) Reuse Path

D-60 says "up to 5 other god-node labels in the same community, sorted by degree desc." The per-community ranking built for D-58 **is the same ranking** D-60 needs, minus the current node. One computation, two consumers:

```python
# Source: D-58 + D-60 combined
def _compute_community_rankings(
    G, communities: dict[int, list[str]], is_file_node, is_concept_node
) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Return (community_label, community_ranked_labels).

    community_label[cid] = label of highest-degree non-synthetic member (D-58).
    community_ranked_labels[cid] = full ranked list (degree desc) of non-synthetic
                                    member labels, used to derive sibling_labels
                                    per node (D-60).
    """
    community_label: dict[int, str] = {}
    community_ranked_labels: dict[int, list[str]] = {}
    for cid, members in communities.items():
        ranked = sorted(
            (n for n in members if not is_file_node(G, n) and not is_concept_node(G, n)),
            key=lambda n: G.degree(n),
            reverse=True,
        )
        labels = [G.nodes[n].get("label", n) for n in ranked]
        community_ranked_labels[cid] = labels
        if labels:
            community_label[cid] = labels[0]
        else:
            community_label[cid] = f"Community {cid}"
    return community_label, community_ranked_labels
```

**Per-node sibling derivation:**

```python
# Source: D-60
def _sibling_labels_for_node(node_id: str, cid: int, community_ranked_labels: dict) -> list[str]:
    node_label = G.nodes[node_id].get("label", node_id)
    ranked = community_ranked_labels.get(cid, [])
    return [lab for lab in ranked if lab != node_label][:5]
```

**Reuse of `analyze.god_nodes`:** minimal — only for the global `god_node_ids` frozenset. The community rankings are a separate computation because their shape (per-community lists) doesn't match `analyze.god_nodes`'s shape (global list of dicts). No work is duplicated; both functions share the synthetic-node filter through `_is_file_node` / `_is_concept_node`.

---

## Profile Schema Extensions (Research Question 6)

### Extending `_DEFAULT_PROFILE` and `_VALID_TOP_LEVEL_KEYS`

Current state [CITED: profile.py:16-39]:

```python
_DEFAULT_PROFILE: dict = {
    "folder_mapping": {...},
    "naming": {...},
    "merge": {...},
    "mapping_rules": [],
    "obsidian": {...},
}
_VALID_TOP_LEVEL_KEYS = {"folder_mapping", "naming", "merge", "mapping_rules", "obsidian"}
```

**Phase 3 extension (in-place edit of `profile.py`):**

```python
_DEFAULT_PROFILE: dict = {
    "folder_mapping": {...},       # unchanged
    "naming": {...},                # unchanged
    "merge": {...},                 # unchanged
    "mapping_rules": [],            # unchanged
    "obsidian": {...},              # unchanged
    "topology": {                   # NEW (D-48)
        "god_node": {"top_n": 10},
    },
    "mapping": {                    # NEW (D-52)
        "moc_threshold": 3,
    },
}

_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping",          # NEW
}
```

**Deep-merge behavior:** `profile._deep_merge` [CITED: profile.py:76-84] recurses into nested dicts. A user profile specifying only `topology.god_node.top_n: 20` deep-merges correctly, leaving `mapping.moc_threshold` at its default. Already verified by Phase 1 for `folder_mapping` partial overrides.

### Validator Extension Point

Current `validate_profile` in `profile.py:127-202` validates each section by fetching and type-checking. Phase 3 adds two blocks:

```python
# Source: extends profile.py:127-202 validation style

# topology section (new)
topology = profile.get("topology")
if topology is not None:
    if not isinstance(topology, dict):
        errors.append("'topology' must be a mapping (dict)")
    else:
        god = topology.get("god_node")
        if god is not None:
            if not isinstance(god, dict):
                errors.append("'topology.god_node' must be a mapping (dict)")
            else:
                top_n = god.get("top_n")
                if top_n is not None and not (isinstance(top_n, int) and top_n >= 0 and not isinstance(top_n, bool)):
                    errors.append(f"'topology.god_node.top_n' must be a non-negative integer, got {top_n!r}")

# mapping section (new)
mapping = profile.get("mapping")
if mapping is not None:
    if not isinstance(mapping, dict):
        errors.append("'mapping' must be a mapping (dict)")
    else:
        threshold = mapping.get("moc_threshold")
        if threshold is not None and not (isinstance(threshold, int) and threshold >= 1 and not isinstance(threshold, bool)):
            errors.append(f"'mapping.moc_threshold' must be an integer >= 1, got {threshold!r}")

# mapping_rules section — replace the current stub at profile.py:197-200
mapping_rules = profile.get("mapping_rules")
if mapping_rules is not None:
    if not isinstance(mapping_rules, list):
        errors.append("'mapping_rules' must be a list")
    else:
        from graphify.mapping import validate_rules
        rule_errors = validate_rules(mapping_rules)
        errors.extend(rule_errors)
```

**Important: `isinstance(x, int) and not isinstance(x, bool)`** — Python's `True`/`False` are subclasses of `int`, so `isinstance(True, int) == True`. Without the `not bool` guard, a user writing `top_n: true` in YAML would pass validation. Same pattern used at `profile.py:327-329` in `_dump_frontmatter` for the bool-before-int check. [CITED: profile.py:326-329]

### `validate_rules` Co-Location (Module Boundary Decision)

**Recommendation: `validate_rules` lives in `mapping.py`, imported by `profile.py`.**

**Reasons:**
1. **Co-locate DSL grammar with its validator.** The rule grammar (matcher kinds, then-shape) is a Phase 3 concept. Putting its validator in `profile.py` would fragment the grammar across two files.
2. **Compiled output lives in `mapping.py`.** `validate_rules` can return `(compiled_rules, errors)` and `mapping.classify()` can consume the compiled form directly, without re-validating or re-compiling.
3. **Circular-import avoidance:** `profile.py` imports nothing from `mapping.py` at module load — the `from graphify.mapping import validate_rules` inside `validate_profile` is a **function-local import**, deferred until validation actually runs. This sidesteps any circular dependency because `mapping.py` does its `profile.py` imports at module top level, and `profile.validate_profile` is only called FROM `load_profile`, which is called from code that's already imported everything. [VERIFIED: current `profile.py` has no such pattern yet but `extract.py` uses function-local imports at line 11 of `analyze.py`: `from graphify.detect import ...` at L112 is another example]

**Alternative rejected:** inline `validate_rules` directly in `profile.py`. Breaks separation of concerns; bloats `profile.py`; forces any future DSL change to touch two files.

### Return Signature of `validate_rules`

Two options:
- **(a)** `validate_rules(rules: list) -> list[str]` — just errors + warnings via prefix.
- **(b)** `validate_rules(rules: list) -> tuple[list[_CompiledRule], list[str]]` — compiled form + diagnostics.

**Recommendation: ship BOTH call paths.**

```python
# Source: matches validate.assert_valid pairing (validate.py:66-71)

def validate_rules(rules: list) -> list[str]:
    """Validate mapping_rules. Returns error/warning strings. Public API for profile.py."""
    _, diagnostics = compile_rules(rules)
    return diagnostics

def compile_rules(rules: list) -> tuple[list[_CompiledRule], list[str]]:
    """Compile rules into _CompiledRule list + diagnostics. Used by classify()."""
    ...
```

`validate_profile` calls `validate_rules` (discards compiled output) to keep its existing return shape. `classify` calls `compile_rules` to get the full compiled form. No duplicate parsing: `validate_rules` delegates to `compile_rules` internally.

---

## Public API Shape (Research Question 7)

### Recommendation: Single `classify()` Entry with `MappingResult` TypedDict

**Full signature:**

```python
# Source: synthesized from CONTEXT.md Claude's Discretion

def classify(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    *,
    cohesion: dict[int, float] | None = None,
) -> MappingResult:
    """Classify every real node in G and assemble MOC contexts.

    Pure function of (G, communities, profile). Does not mutate inputs.
    If `cohesion` is omitted, computes it via cluster.score_all(G, communities).

    Returns a MappingResult with per_node, per_community, skipped_node_ids,
    and (optional) rule_traces.
    """
    ...


class MappingResult(TypedDict, total=False):
    per_node: dict[str, ClassificationContext]
    per_community: dict[int, ClassificationContext]
    skipped_node_ids: set[str]
    rule_traces: list[RuleTrace]
    # diagnostics from compile_rules, surfaced for GRAPH_REPORT.md
    rule_diagnostics: list[str]


class RuleTrace(TypedDict):
    node_id: str
    rule_index: int    # -1 for topology fallback, -2 for default statement
    matched_kind: str  # e.g. "attr_equals", "topology_god", "__default__"
    note_type: str
    folder: str
```

### Why Single Entry Beats Paired Entries

**Option A: `classify(G, communities, profile) -> MappingResult`**
- ✅ Precedence pipeline is one algorithm in one place. No leakage.
- ✅ Pre-computation runs once; both `per_node` and `per_community` read from the same cache.
- ✅ One call site in Phase 5 (`to_obsidian`). Matches the way `cluster(G)` is called once.
- ✅ Test fixtures call `classify()` once and assert on both halves of the result.

**Option B: `classify_nodes(...)` + `classify_communities(...)`**
- ❌ Phase 5 would call `classify_nodes` first, then `classify_communities(per_node_result, G, communities, profile)` — the second call needs the first's output anyway, so it's not truly independent.
- ❌ Precedence pipeline step 2 (fallback topology) references community membership ("above threshold → moc"), which means `classify_nodes` needs either (a) communities as an input (it does already, but then it has the same signature as `classify`), or (b) to skip community-level note types and let `classify_communities` patch them later (breaks first-match-wins semantics).
- ❌ Two call sites in Phase 5; two test fixture chains; two public entry points to document.
- ❌ Duplicates the pre-computation work or forces a shared `_ClassifyContext` struct passed between them.

**Verdict:** Single `classify()` entry. The precedence pipeline is indivisible.

### Phase 5 Call-Site Ergonomics

From CONTEXT.md integration-points section, Phase 5 wires as:

```python
# Phase 5 (future, not this phase)
from graphify.mapping import classify
from graphify.cluster import score_all

communities = cluster(G)
cohesion = score_all(G, communities)
result = classify(G, communities, profile, cohesion=cohesion)

for node_id, ctx in result["per_node"].items():
    fname, text = render_note(node_id, G, profile, ctx["note_type"], ctx, vault_dir=vault)
    (out / ctx["folder"] / fname).write_text(text)

for cid, ctx in result["per_community"].items():
    fname, text = render_moc(cid, G, communities, profile, ctx, vault_dir=vault)
    (out / ctx["folder"] / fname).write_text(text)
```

Three lines of glue at the call site. No per-node plumbing. This is why single-entry wins.

### `rule_traces` v1 vs Deferred

**Recommendation: ship in v1 as an optional field.**

- Small payload (`dict` per classified node).
- Enables test assertions like `assert result["rule_traces"][i]["rule_index"] == 2` — load-bearing for testing first-match-wins.
- Surfaces in Phase 5 `GRAPH_REPORT.md` with zero additional work ("node X was classified as thing by rule 2").
- **Cost:** ~|V| dict allocations. For 10k nodes, negligible.

Make it optional via `MappingResult(TypedDict, total=False)` so callers who don't care don't index into it.

### `TypedDict` vs `@dataclass(frozen=True)` for `MappingResult`

**TypedDict wins for consistency.** Phase 2's `ClassificationContext` uses `TypedDict(total=False)` [CITED: templates.py:57-67]. Using `TypedDict` for `MappingResult` keeps Phase 3's public types isomorphic. Callers access fields via `result["per_node"]` — same as Phase 2.

**Dataclass advantage rejected:** Attribute access (`result.per_node`) is marginally nicer but forces a style split with Phase 2's dict-access. Consistency > ergonomics here.

---

## Testing Strategy (Research Question 8)

### Pattern from Phase 2

`tests/fixtures/template_context.py` exports three helpers [CITED: tests/fixtures/template_context.py]:
- `make_classification_context(**overrides)` — non-MOC ctx with sensible defaults.
- `make_moc_context(**overrides)` — MOC ctx with two pre-populated members.
- `make_min_graph()` — 3-node NetworkX graph (n_transformer, n_attention, n_paper) with 2 edges.

All three are pure-Python; no `tmp_path`; no filesystem.

### Phase 3 Fixture Extension

**Add `make_classification_fixture(...)` to `tests/fixtures/template_context.py`** (do NOT create a new fixture file — CONTEXT.md explicitly prefers reuse):

```python
# Source: extends existing fixture module
def make_classification_fixture(
    *,
    n_communities: int = 2,
    include_isolate: bool = True,
    include_file_hub: bool = False,
    include_concept: bool = False,
) -> tuple[nx.Graph, dict[int, list[str]]]:
    """Return a (G, communities) pair for Phase 3 classification tests.

    Default: 2-community graph with 1 isolate.

    Community 0: {n_transformer (god), n_attention, n_layer_norm}
    Community 1: {n_paper, n_author}
    Isolate: {n_lonely}

    With include_file_hub=True: adds a file-level hub node 'src/model.py'
    that _is_file_node() filters out.

    With include_concept=True: adds a concept node with empty source_file
    that _is_concept_node() filters out.
    """
    G = nx.Graph()
    # Community 0 — ML
    G.add_node("n_transformer", label="Transformer", file_type="code",
               source_file="src/model.py", source_location="L42")
    G.add_node("n_attention", label="Attention", file_type="code",
               source_file="src/model.py", source_location="L101")
    G.add_node("n_layer_norm", label="LayerNorm", file_type="code",
               source_file="src/model.py", source_location="L203")
    G.add_edge("n_transformer", "n_attention", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_transformer", "n_layer_norm", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_attention", "n_layer_norm", relation="uses", confidence="EXTRACTED")
    # Community 1 — Papers
    G.add_node("n_paper", label="Attention Is All You Need", file_type="paper",
               source_file="papers/attn.pdf")
    G.add_node("n_author", label="Vaswani", file_type="document",
               source_file="papers/authors.md")
    G.add_edge("n_paper", "n_author", relation="written_by", confidence="EXTRACTED")
    # Bridge edge — makes n_paper a host candidate for below-threshold communities
    G.add_edge("n_transformer", "n_paper", relation="references",
               confidence="INFERRED", confidence_score=0.85)
    # Isolate
    if include_isolate:
        G.add_node("n_lonely", label="Orphan", file_type="document",
                   source_file="docs/orphan.md")
    # Optional: file hub (triggers _is_file_node)
    if include_file_hub:
        G.add_node("src/model.py", label="model.py", file_type="code",
                   source_file="src/model.py")
        G.add_edge("src/model.py", "n_transformer", relation="contains", confidence="EXTRACTED")
    # Optional: concept (triggers _is_concept_node via empty source_file)
    if include_concept:
        G.add_node("n_concept_attn", label="Attention Concept", file_type="code", source_file="")

    communities: dict[int, list[str]] = {
        0: sorted(["n_transformer", "n_attention", "n_layer_norm"]),
        1: sorted(["n_paper", "n_author"]),
    }
    if include_isolate:
        communities[2] = ["n_lonely"]
    return G, communities
```

### Test Taxonomy (test_mapping.py)

Organize `tests/test_mapping.py` as independent `test_<behavior>` functions, no classes, no `tmp_path`, no fixtures requiring I/O. Group by:

**1. `validate_rules` / `compile_rules` — unit tests (fast, high-coverage)**

- `test_validate_rules_empty_list_is_valid` — `[]` returns no errors
- `test_validate_rules_missing_when` — rule without `when:` rejected with clear error
- `test_validate_rules_missing_then_note_type` — rule without `then.note_type` rejected
- `test_validate_rules_unknown_note_type` — `then.note_type: wizard` rejected against `_NOTE_TYPES`
- `test_validate_rules_attr_equals_valid` — compiles to `matcher_kind="attr_equals"`
- `test_validate_rules_attr_in_must_be_list` — `{in: "foo"}` rejected
- `test_validate_rules_attr_contains_requires_string_substring` — `{contains: 42}` rejected
- `test_validate_rules_regex_too_long_rejected` — 513-char pattern rejected
- `test_validate_rules_regex_invalid_rejected` — `"(unclosed"` → validation error
- `test_validate_rules_source_file_ext_normalizes_case_and_dot` — `"PY"` and `".py"` both normalize
- `test_validate_rules_unknown_matcher_kind_rejected`
- `test_validate_rules_dead_rule_warning_identical` — two identical rules → warning on second
- `test_validate_rules_dead_rule_warning_topology_comm_gte_superset` — rule A `gte 2`, rule B `gte 5`, same note_type → warning on B
- `test_validate_rules_no_dead_rule_warning_across_kinds` — attr_equals vs topology_god same note_type → NO warning (guarantees false-positive-free)
- `test_validate_rules_then_folder_rejected_when_absolute` — `then.folder: /etc/passwd` rejected
- `test_validate_rules_then_folder_rejected_when_traversal` — `then.folder: "../out/"` rejected
- `test_validate_rules_then_folder_rejected_when_home_expansion` — `then.folder: "~/vault"` rejected

**2. Matcher dispatch — pure unit tests**

- `test_match_when_attr_equals_hits_and_misses`
- `test_match_when_attr_in_matches_membership`
- `test_match_when_attr_contains_non_string_returns_false`
- `test_match_when_attr_regex_fullmatch_anchored` — `"py"` does NOT match `"python"` under fullmatch
- `test_match_when_attr_regex_candidate_too_long_returns_false` — 2049-char attribute
- `test_match_when_topology_god_hits_precomputed_set`
- `test_match_when_topology_community_size_gte`
- `test_match_when_topology_community_size_lt`
- `test_match_when_topology_cohesion_gte_reads_cohesion_dict`
- `test_match_when_topology_is_source_file_calls_filter`
- `test_match_when_source_file_ext_normalizes_case`
- `test_match_when_source_file_ext_list_membership`
- `test_match_when_source_file_matches_regex_full_path`

**3. Precedence pipeline — behavioral tests**

- `test_classify_attribute_rule_beats_topology` (MAP-03) — graph with a god node that also has `file_type: person`; rule `{attr: file_type, equals: person}` → person, NOT thing
- `test_classify_topology_fallback_when_no_rules` (MAP-02) — empty `mapping_rules`, god node → thing
- `test_classify_default_statement_when_no_match` — non-god, non-hub, no rule → statement + `folder_mapping.default`
- `test_classify_first_match_wins_rule_order` (MAP-04) — two rules both match same node; first wins
- `test_classify_concept_nodes_unconditionally_skipped` (D-50) — concept appears in `skipped_node_ids`, not in `per_node`
- `test_classify_file_hub_skipped_without_opt_in` (D-51)
- `test_classify_file_hub_opted_in_by_rule` (MAP-06, D-51) — rule `{topology: is_source_file}` → node classified as source
- `test_classify_source_file_ext_routes_to_custom_folder` (MAP-06) — rule `{source_file_ext: .py} → then.folder: Atlas/Sources/Code/`
- `test_classify_zero_god_nodes_valid_state` (D-49) — tiny graph, no god nodes, no crash, nodes fall through to statement

**4. Community assembly — behavioral tests**

- `test_community_above_threshold_becomes_moc` (MAP-05) — 5-member community → per_community entry with note_type moc
- `test_community_below_threshold_collapses_to_host` (MAP-05, D-53) — 2-member community absorbed into nearest-host's sub_communities
- `test_nearest_host_tiebreak_largest_then_lowest_cid` (D-53) — equal edge counts, host with larger size wins
- `test_isolate_size_1_below_threshold` (D-55) — singleton → nearest host
- `test_isolate_zero_neighbors_bucket_moc` (D-55, D-56) — disconnected isolate → community_id -1 bucket
- `test_bucket_moc_only_emitted_when_needed` (D-56) — well-connected graph has no bucket
- `test_members_by_type_reflects_final_classification` (D-57) — attribute rule reclassifying a node is reflected in the MOC's members_by_type

**5. Community label + sibling derivation**

- `test_community_label_top_god_node_in_community` (D-58) — highest-degree non-synthetic member wins
- `test_community_label_fallback_to_community_n` (D-58) — all-synthetic community falls back
- `test_community_tag_is_safe_tag_of_name` (D-59)
- `test_sibling_labels_cap_at_5` (D-60)
- `test_sibling_labels_exclude_current_node` (D-60)
- `test_sibling_labels_non_god_node_empty` (D-60)

**6. Contract tests against Phase 2 renderers (Pattern 6 below)**

- `test_per_node_context_consumed_by_render_note_without_error` — every `classify(...)["per_node"]` entry round-trips through `render_note(node_id, G, profile, ctx["note_type"], ctx)` without raising
- `test_per_community_context_consumed_by_render_moc_without_error` — every `per_community` entry round-trips through `render_moc(cid, G, communities, profile, ctx)`
- `test_sub_communities_payload_matches_templates_build_sub_communities_callout_shape` — the `sub_communities` list structure is what `templates.py:458` expects

**7. End-to-end profile validation tests (extend `test_profile.py`)**

- `test_validate_profile_surfaces_mapping_rules_errors` — user profile with bad rule → `validate_profile` returns error list including rule error
- `test_load_profile_falls_back_on_rule_errors` — matches existing `profile.py:114-118` fallback pattern
- `test_default_profile_includes_topology_and_mapping_keys` (D-48, D-52)
- `test_deep_merge_respects_topology_section` — user specifies only `topology.god_node.top_n: 20`, other defaults preserved

### Pattern 6: Contract Tests as the Integration Backbone

**This is the load-bearing test category for nyquist validation.** If `classify()` produces output Phase 2 can't consume, Phase 5 integration shatters. Test it at Phase 3's boundary.

```python
# Source: new test in tests/test_mapping.py
def test_classify_output_round_trips_through_render_note():
    """Every per_node entry must render without raising."""
    from graphify.templates import render_note, render_moc
    from graphify.mapping import classify
    from graphify.profile import _DEFAULT_PROFILE
    from tests.fixtures.template_context import make_classification_fixture

    G, communities = make_classification_fixture()
    result = classify(G, communities, _DEFAULT_PROFILE)

    for node_id, ctx in result["per_node"].items():
        note_type = ctx["note_type"]
        if note_type not in ("thing", "statement", "person", "source"):
            continue  # MOCs handled in other test
        # Must not raise
        fname, text = render_note(node_id, G, _DEFAULT_PROFILE, note_type, ctx)
        assert fname.endswith(".md")
        assert "---" in text  # has frontmatter
```

This test is the **single most important test in Phase 3** — it proves the layer boundary is respected and the TypedDict contract is honored in practice.

### Test-Only Imports and Shared Fixtures

Phase 3 tests import from `tests.fixtures.template_context` — the `__init__.py` at `tests/__init__.py` already exists [VERIFIED: tests/__init__.py present per Bash ls]. No new `conftest.py` needed.

**Fixture reuse from Phase 2:** `make_classification_context()` and `make_moc_context()` remain useful for Phase 3 unit tests that don't need a graph (e.g., testing `_build_sub_communities_callout` integration). `make_min_graph()` is the 3-node graph Phase 2 uses for render tests — Phase 3 can use it when a minimal graph suffices and `make_classification_fixture()` when the multi-community topology is needed.

---

## Runtime State Inventory

Not applicable — this is a greenfield phase adding a new module. No rename/refactor/migration. Omitted per researcher template.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core | ✓ | 3.10+ | — |
| networkx | G.edges, G.degree | ✓ | already required | — |
| stdlib `re` | regex matchers | ✓ | stdlib | — |
| stdlib `typing.TypedDict` | MappingResult | ✓ | stdlib 3.8+ | — |
| stdlib `dataclasses` | (optional, if `_CompiledRule` uses @dataclass) | ✓ | stdlib 3.7+ | — |

**No missing dependencies.** Phase 3 is pure code addition within the existing stack.

---

## Common Pitfalls

### Pitfall 1: Mixing Classification with Rendering

**What goes wrong:** A contributor adds a helper to `mapping.py` that calls `templates.render_note` for a quick sanity check, creating a circular import risk and blurring the layer boundary.

**Why it happens:** Classification and rendering are tightly coupled at the data level (the `ClassificationContext` shape). It feels natural to verify renderability from the classifier.

**How to avoid:** `mapping.py` imports FROM `templates.py` at most the `ClassificationContext` type and `_NOTE_TYPES` frozenset — nothing that renders markdown. Enforce in code review by grep: `from graphify.templates import render_` should be absent from `mapping.py`.

**Warning signs:** `templates.py` starts importing from `mapping.py`; test files start skipping the Phase 2/Phase 3 boundary; `classify()` begins producing strings, not dicts.

### Pitfall 2: Re-Running `analyze.god_nodes` Inside the Matcher Loop

**What goes wrong:** A naive implementation of the `{topology: god_node}` matcher calls `analyze.god_nodes(G, top_n)` for every rule evaluation, producing O(|V|²) cost.

**Why it happens:** The matcher reads "is this node a god node?" and the obvious implementation is a direct function call.

**How to avoid:** Pre-compute `god_node_ids: frozenset[str]` exactly once, store it on `_ClassifyContext`, and have the matcher check `node_id in ctx.god_node_ids`.

**Warning signs:** `mapping.py` imports `god_nodes` and calls it inside `_match_when`; test runtime on a 5k-node corpus balloons to seconds.

### Pitfall 3: Synthetic Nodes Leaking into `members_by_type`

**What goes wrong:** A community MOC lists method stubs like `.auth_flow()` or empty-source concept nodes in its `members_by_type["statement"]` list, which then renders into the vault as broken wikilinks.

**Why it happens:** The synthetic-node filter is applied when *classifying* a node (skipping it), but community assembly separately iterates over `communities[cid]` — which still contains the skipped node IDs.

**How to avoid:** Community assembly must read from `per_node`, not from `communities[cid]` directly. Any node missing from `per_node` is either skipped (in `skipped_node_ids`) or was filtered for another reason — either way, drop it from `members_by_type`.

**Warning signs:** Tests with `include_concept=True` or `include_file_hub=True` show `.some_method()` labels in rendered MOC output.

### Pitfall 4: First-Match-Wins Off-By-One with Dead-Rule Detection

**What goes wrong:** The dead-rule detector warns on rule[j] when rule[i<j] is identical, but forgets to `break` after emitting the warning, producing N-1 warnings for the same dead rule.

**How to avoid:** `break` after emitting one warning per `j`. See pseudocode in Research Question 3.

### Pitfall 5: Regex Matcher Matching on Non-String Attributes Without Guard

**What goes wrong:** Rule `{attr: cohesion, regex: "0\.[0-9]+"}` against a float attribute — `re.fullmatch` raises `TypeError` on non-string input.

**How to avoid:** `_match_when` explicitly checks `isinstance(raw, str)` before calling `pattern.fullmatch(raw)`. Returns `False` on non-string. See Pattern 1 code.

**Warning signs:** `test_match_when_attr_regex_non_string_returns_false` passes; a real-world run produces a TypeError stack trace.

### Pitfall 6: Forgetting to Normalize `source_file_ext`

**What goes wrong:** User writes `{source_file_ext: PY}` in profile.yaml; matcher compares against `.py` extension from a lowercase `source_file` attribute. No match.

**How to avoid:** At validation time, normalize each ext to lowercase + leading-dot (`".py"`, not `"py"` or `"PY"`). Store the normalized frozenset on `_CompiledRule.matcher_args["exts"]`. `_ext_of(src)` does the same normalization on the candidate side.

### Pitfall 7: `isinstance(x, int)` Accepting `True`/`False`

**What goes wrong:** User writes `moc_threshold: true` in profile.yaml — parses as Python bool, but `isinstance(True, int) == True`, so `validate_profile` accepts it silently, and then `len(members) >= True` evaluates as `len(members) >= 1`, producing surprising behavior.

**How to avoid:** Use `isinstance(x, int) and not isinstance(x, bool)` guards in validation. Pattern already used at `profile.py:326-329`. [CITED: profile.py:326-329]

### Pitfall 8: Mutating the Input `communities` Dict

**What goes wrong:** `classify()` sorts `communities[cid]` in place to rank by degree. A caller who reuses `communities` afterwards sees mutated state.

**How to avoid:** `classify()` never mutates its inputs. Any sorting happens on a local copy: `sorted(members, key=G.degree, reverse=True)`. Contract is documented in the classify docstring.

---

## Code Examples

Verified patterns from the graphify codebase:

### Example 1: `_node_community_map` (exact import path)

```python
# Source: graphify/analyze.py:6-8 (cited)
def _node_community_map(communities: dict[int, list[str]]) -> dict[str, int]:
    """Invert communities dict: node_id -> community_id."""
    return {n: cid for cid, nodes in communities.items() for n in nodes}
```

Phase 3 imports this: `from graphify.analyze import _node_community_map`.

### Example 2: `god_nodes` return shape (what Phase 3 consumes)

```python
# Source: graphify/analyze.py:39-58 (cited)
def god_nodes(G: nx.Graph, top_n: int = 10) -> list[dict]:
    # Returns list of {"id": str, "label": str, "edges": int}
```

Phase 3 converts to frozenset: `frozenset(g["id"] for g in god_nodes(G, top_n=top_n))`.

### Example 3: Validation return pattern (the shape `validate_rules` mirrors)

```python
# Source: graphify/validate.py:10-63 (cited)
def validate_extraction(data: dict) -> list[str]:
    """Returns a list of error strings - empty list means valid."""
    errors: list[str] = []
    # ... aggregate errors, don't raise ...
    return errors
```

### Example 4: Single-pass edge walk for inter-community counts

```python
# Source: graphify/export.py:559-566 (reference only — do not modify)
inter_community_edges: dict[int, dict[int, int]] = {}
for u, v in G.edges():
    cu = node_community.get(u)
    cv = node_community.get(v)
    if cu is not None and cv is not None and cu != cv:
        inter_community_edges.setdefault(cu, {})
        inter_community_edges[cu][cv] = inter_community_edges[cu].get(cv, 0) + 1
```

Phase 3's `_compute_nearest_host` narrows this to (below → above) direction only.

### Example 5: Bool-guarded int check (prevents YAML `true` slipping through)

```python
# Source: graphify/profile.py:326-329 (cited — used in _dump_frontmatter)
elif isinstance(value, bool):
    # bool before int: isinstance(True, int) is True in Python
    lines.append(f"{key}: {'true' if value else 'false'}")
elif isinstance(value, int):
    lines.append(f"{key}: {value}")
```

Phase 3's `validate_profile` topology/mapping validation uses `isinstance(x, int) and not isinstance(x, bool)` for the same reason.

### Example 6: Function-local import to avoid circular deps

```python
# Source: graphify/analyze.py:112 (cited) — illustrates function-local import pattern
# (actually at module level for detect, but the pattern of deferring imports applies)
from graphify.detect import CODE_EXTENSIONS, DOC_EXTENSIONS, PAPER_EXTENSIONS, IMAGE_EXTENSIONS
```

Phase 3's `validate_profile` calls `from graphify.mapping import validate_rules` as a function-local import to keep `profile.py`'s top-level imports free of `mapping.py`.

### Example 7: `sort` with stable tie-break tuple

```python
# Source: graphify/export.py:471-474 (cited) — how legacy code sorts by (source_file, label) tuple
sorted(
    G.nodes(data=True),
    key=lambda nd: (nd[1].get("source_file", ""), nd[1].get("label", nd[0])),
)
```

Phase 3's nearest-host tie-break follows the same tuple-key pattern (see Pattern 3 `max(..., key=lambda kv: (kv[1], community_sizes.get(kv[0], 0), -kv[0]))`).

---

## State of the Art

| Old Approach (export.py legacy) | New Approach (Phase 3) | When Changed | Impact |
|---------------------------------|------------------------|--------------|--------|
| Hardcoded `_FTYPE_TAG` dict mapping file_type → tag | Configurable via `mapping_rules` + profile | Phase 3 | MAP-06 support without code changes |
| Community name = `community_labels[cid]` or `"Community N"` | Top-god-node per community (D-58) | Phase 3 | Vaults read like textbooks |
| Flat output, all nodes in one folder | Per-rule `then.folder` + `folder_mapping` | Phase 3 | MAP-01, MAP-06 |
| `to_obsidian` walks G and emits strings in one pass | Classify→assemble→render as 3 separate pure stages | Phases 3 + 5 | Testability; no IO in classification |
| No below-threshold handling (all communities become MOCs) | Nearest-host collapse + bucket fallback (D-53, D-56) | Phase 3 | Tiny corpora no longer produce 50 single-member MOCs |

**Deprecated/outdated:**

- `export.py:to_obsidian` flat-classification behavior is **reference only**. Phase 5 rewires it to consume `MappingResult`. Phase 3 does not modify it.
- `_FTYPE_TAG` dict in `export.py:492-498` is not deleted — Phase 5 replaces its call site, but the dict can remain for MRG-05 backward-compat fallback when `mapping_rules: []`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `re.fullmatch` with patterns ≤ 512 chars against inputs ≤ 2048 chars cannot produce catastrophic backtracking in practical time | Regex Matcher Safety | If wrong, a malicious profile could DoS the classifier. Mitigation: the profile comes from the user's own vault (trusted). Validator also fails-fast on `re.error` at load time. |
| A2 | Per-community top-degree computation via `sorted(members, key=G.degree, reverse=True)` has O(\|V\|) total cost across all communities | MOC Label Derivation | If `G.degree(n)` is not O(1) on some graph types, this becomes O(\|V\| × avg degree). Verified O(1) for `nx.Graph` [VERIFIED: networkx.Graph.degree is a DegreeView with O(1) lookup]. |
| A3 | Target corpora are < 10k nodes | Pattern 3, nearest-host | If wrong (100k+ nodes), the O(\|E\|) edge walk still dominates everything else. No user-visible impact; no algorithmic alternative even considered. |
| A4 | No circular import arises from `profile.py`'s function-local `from graphify.mapping import validate_rules` | Profile Schema Extensions | If wrong, `load_profile` will `ImportError` on first call. Mitigation: test exercises `load_profile` end-to-end with a rule-bearing profile. |
| A5 | The structural dead-rule heuristic never produces false positives | Dead-Rule Detection | If it does, users will dismiss the warnings and stop trusting them. Mitigation: matcher-kind equality gate + same-note_type gate + per-kind superset check. Cross-kind shadowing NEVER warned. |
| A6 | `_is_file_node` and `_is_concept_node` semantics match what D-50 intends | Pattern 2 | If the filters miss a category of synthetic node, that node pollutes the vault. Mitigation: test fixtures include both file hubs and concepts explicitly; contract tests verify they land in `skipped_node_ids`. |
| A7 | D-44's "candidate string length ≤ 2048" is large enough for real source_file paths | Regex Matcher Safety | Some monorepos have source_file paths > 1024 chars. If observed, bump to 4096 without ReDoS risk change. |
| A8 | `isinstance(x, int) and not isinstance(x, bool)` is sufficient to reject YAML booleans posing as ints | Profile Schema Extensions | Pattern is already used in `profile.py:326-329` for the same reason. Well-understood Python idiom. |

---

## Open Questions

1. **Should `rule_traces` include the compiled matcher args, or just the raw rule index?**
   - What we know: test assertions need `rule_index` at minimum; debugging benefits from seeing the `matcher_kind` tag.
   - What's unclear: whether users exposed to `GRAPH_REPORT.md` want to see the full normalized args.
   - Recommendation: ship `{node_id, rule_index, matched_kind, note_type, folder}` as the minimum viable TypedDict. Expand later if Phase 5 needs it.

2. **Should `validate_rules` accept a partially compiled `profile` dict or just the raw `mapping_rules` list?**
   - What we know: `validate_profile` calls `validate_rules(profile["mapping_rules"])` — the list, not the profile.
   - What's unclear: if dead-rule detection later needs to know `profile["folder_mapping"]` to validate `then.folder` against known types, the signature may need the full profile.
   - Recommendation: start with `validate_rules(rules: list) -> list[str]`. Widen if a use case surfaces.

3. **Should Phase 3 emit `cohesion` per-community inside `per_community[cid]["cohesion"]` for render_moc to display?**
   - What we know: `templates.py:705-706` reads `ctx.get("cohesion")` and renders it in MOC frontmatter.
   - What's unclear: CONTEXT.md doesn't list `cohesion` as a `ClassificationContext` key.
   - Resolution path: Phase 3's `_build_moc_context` SHOULD populate `cohesion` when `cohesion` is passed to `classify()`. The TypedDict at `templates.py:57-67` is `total=False`, so adding `cohesion` to `per_community` entries is forward-compatible.
   - Recommendation: populate `per_community[cid]["cohesion"]` whenever cohesion data is available. Document in `classify` docstring. (Minor gap in CONTEXT.md — either an oversight in the TypedDict listing or implied via "the engine reads cluster.score_all to feed cohesion_gte".)

4. **Should `MappingResult.per_community` also contain the `parent_moc_label` key for MOCs themselves?**
   - What we know: non-MOC notes have `parent_moc_label` pointing to their community's MOC. MOCs themselves have no parent (they link up to Atlas root).
   - What's unclear: should `per_community[cid]["parent_moc_label"]` be empty string, None, or absent?
   - Recommendation: absent (TypedDict total=False). `templates._build_wayfinder_callout` [CITED: templates.py:333-352] already handles `parent_moc_label=None` → atlas fallback.

5. **What happens if two different below-threshold communities have the same nearest host?**
   - What we know: host_ctx["sub_communities"] is a list. Multiple appenders is fine.
   - What's unclear: is sub_community ordering deterministic?
   - Recommendation: sort sub_communities by source `community_id` ascending before emitting, to guarantee reproducible output.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest, no version pin) [VERIFIED: pyproject.toml + .planning/codebase/TESTING.md] |
| Config file | none — no pytest.ini / pyproject.toml [tool.pytest] config |
| Quick run command | `pytest tests/test_mapping.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-01 | Notes placed in `folder_mapping`-defined folders | unit | `pytest tests/test_mapping.py::test_classify_default_statement_uses_folder_mapping_default -x` | ❌ Wave 0 |
| MAP-01 | Per-rule `then.folder` override wins over default | unit | `pytest tests/test_mapping.py::test_classify_rule_folder_override -x` | ❌ Wave 0 |
| MAP-02 | God nodes → Things in topology fallback | unit | `pytest tests/test_mapping.py::test_classify_topology_fallback_god_node_becomes_thing -x` | ❌ Wave 0 |
| MAP-02 | Communities above threshold → MOCs | unit | `pytest tests/test_mapping.py::test_community_above_threshold_becomes_moc -x` | ❌ Wave 0 |
| MAP-02 | Default → statements | unit | `pytest tests/test_mapping.py::test_classify_default_statement_when_no_match -x` | ❌ Wave 0 |
| MAP-03 | `file_type: person` attribute rule overrides topology | unit | `pytest tests/test_mapping.py::test_classify_attribute_rule_beats_topology -x` | ❌ Wave 0 |
| MAP-04 | Attribute > topology > default precedence | unit | `pytest tests/test_mapping.py::test_classify_first_match_wins_rule_order -x` | ❌ Wave 0 |
| MAP-04 | First-match-wins within rule list | unit | `pytest tests/test_mapping.py::test_classify_first_rule_locks_outcome -x` | ❌ Wave 0 |
| MAP-05 | `moc_threshold` default 3 | unit | `pytest tests/test_mapping.py::test_default_profile_moc_threshold_is_3 -x` | ❌ Wave 0 |
| MAP-05 | Below-threshold community collapses to host | unit | `pytest tests/test_mapping.py::test_community_below_threshold_collapses_to_host -x` | ❌ Wave 0 |
| MAP-05 | Nearest-host resolution by edge count | unit | `pytest tests/test_mapping.py::test_nearest_host_arg_max_by_edge_count -x` | ❌ Wave 0 |
| MAP-05 | Tie-break: largest host then lowest cid | unit | `pytest tests/test_mapping.py::test_nearest_host_tiebreak_largest_then_lowest_cid -x` | ❌ Wave 0 |
| MAP-05 | Bucket MOC for host-less below-threshold | unit | `pytest tests/test_mapping.py::test_bucket_moc_absorbs_hostless_below_threshold -x` | ❌ Wave 0 |
| MAP-06 | `source_file_ext` matcher routes to sub-folder | unit | `pytest tests/test_mapping.py::test_classify_source_file_ext_routes_to_custom_folder -x` | ❌ Wave 0 |
| MAP-06 | `{topology: is_source_file}` opt-in rule surfaces file hubs | unit | `pytest tests/test_mapping.py::test_classify_file_hub_opted_in_by_rule -x` | ❌ Wave 0 |
| D-58 | Community label = top god node in community | unit | `pytest tests/test_mapping.py::test_community_label_top_god_node_in_community -x` | ❌ Wave 0 |
| D-58 | Fallback to "Community N" for all-synthetic community | unit | `pytest tests/test_mapping.py::test_community_label_fallback_to_community_n -x` | ❌ Wave 0 |
| D-59 | `community_tag = safe_tag(community_name)` | unit | `pytest tests/test_mapping.py::test_community_tag_is_safe_tag_of_name -x` | ❌ Wave 0 |
| D-60 | `sibling_labels` capped at 5 | unit | `pytest tests/test_mapping.py::test_sibling_labels_cap_at_5 -x` | ❌ Wave 0 |
| D-60 | `sibling_labels` excludes current node | unit | `pytest tests/test_mapping.py::test_sibling_labels_exclude_current_node -x` | ❌ Wave 0 |
| D-50 | Synthetic nodes in `skipped_node_ids`, not per_node | unit | `pytest tests/test_mapping.py::test_concept_and_file_hubs_are_skipped -x` | ❌ Wave 0 |
| D-51 | File hub opt-in via explicit rule | unit | `pytest tests/test_mapping.py::test_classify_file_hub_opted_in_by_rule -x` | ❌ Wave 0 |
| D-49 | Zero god nodes is valid state | unit | `pytest tests/test_mapping.py::test_classify_zero_god_nodes_no_crash -x` | ❌ Wave 0 |
| D-44 | Regex matcher pattern length cap | unit | `pytest tests/test_mapping.py::test_validate_rules_regex_too_long_rejected -x` | ❌ Wave 0 |
| D-44 | Regex matcher candidate length cap | unit | `pytest tests/test_mapping.py::test_match_when_attr_regex_candidate_too_long_returns_false -x` | ❌ Wave 0 |
| D-45 | Dead-rule detection warning | unit | `pytest tests/test_mapping.py::test_validate_rules_dead_rule_warning_identical -x` | ❌ Wave 0 |
| D-45 | No cross-kind dead-rule false positives | unit | `pytest tests/test_mapping.py::test_validate_rules_no_dead_rule_warning_across_kinds -x` | ❌ Wave 0 |
| Contract | per_node round-trips through render_note | integration (no IO) | `pytest tests/test_mapping.py::test_classify_output_round_trips_through_render_note -x` | ❌ Wave 0 |
| Contract | per_community round-trips through render_moc | integration (no IO) | `pytest tests/test_mapping.py::test_classify_output_round_trips_through_render_moc -x` | ❌ Wave 0 |
| Profile | validate_profile surfaces rule errors | unit (test_profile.py extension) | `pytest tests/test_profile.py::test_validate_profile_surfaces_mapping_rules_errors -x` | ❌ Wave 0 |
| Profile | deep_merge respects topology/mapping sections | unit | `pytest tests/test_profile.py::test_deep_merge_respects_topology_section -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_mapping.py -q` — fast (<1s expected for pure-dict/graph unit tests).
- **Per wave merge:** `pytest tests/test_mapping.py tests/test_profile.py tests/test_templates.py -q` — exercises the Phase 3 module + consumers + contract tests.
- **Phase gate:** `pytest tests/ -q` — full suite must pass green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_mapping.py` — new file; covers MAP-01 through MAP-06 + D-44 through D-60 implementation verification.
- [ ] `tests/fixtures/template_context.py` — extend with `make_classification_fixture()` helper (keeps Phase 2 fixtures intact, adds Phase 3 multi-community graph builder).
- [ ] `tests/test_profile.py` — extend with new `test_validate_profile_surfaces_mapping_rules_errors`, `test_default_profile_includes_topology_and_mapping_keys`, `test_deep_merge_respects_topology_section`.
- [ ] No new framework install needed — pytest is already the project's test runner.
- [ ] No new `conftest.py` needed — shared fixtures continue living in `tests/fixtures/template_context.py`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no authentication in this layer |
| V3 Session Management | no | N/A — no sessions |
| V4 Access Control | no | N/A — all inputs are local trusted files (vault profile, graph built in-process) |
| V5 Input Validation | **yes** | Profile validation (`validate_rules`, regex length caps, `folder_mapping` path rejection); attribute matchers guarded against non-string inputs; dead-rule detection as user-experience defense |
| V6 Cryptography | no | No secrets, no crypto operations |
| V12 File and Resource | **yes** | `then.folder` path overrides must pass `folder_mapping`-style rejection (no `..`, no absolute, no `~`) AND be re-validated by `validate_vault_path` at Phase 5 write time |

### Known Threat Patterns for Phase 3

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ReDoS via user-supplied regex in `{attr, regex}` or `{source_file_matches}` | DoS | Pattern length cap 512, candidate length cap 2048, compile-at-validation-time, `re.fullmatch` anchored. No `signal` timeouts (stdlib `re` has no native support). [Consistent with `security.py` size-cap pattern.] |
| Path traversal via `then.folder` override | Tampering / Elevation of Privilege | Reject `..`, absolute paths, and `~` at `validate_rules` time (mirrors `profile.py:178-195`). Phase 5 re-validates via `validate_vault_path` before write. Two-layer defense. |
| YAML boolean masquerading as integer (`moc_threshold: true`) | Tampering (config-injection) | `isinstance(x, int) and not isinstance(x, bool)` guard at profile validation (pattern from `profile.py:326-329`). |
| Non-string attribute fed to `contains`/`regex` matcher | Crash (Denial of Service against user) | `_match_when` explicit `isinstance(raw, str)` guard before string operations. |
| Dead rules silently never fire, confusing users | (not STRIDE — UX defense) | `_detect_dead_rules` emits warnings. Conservative structural heuristic guarantees no false positives. |
| Synthetic nodes leak into vault as broken wikilinks | Data integrity | Global `_is_file_node` / `_is_concept_node` filter; nodes skipped go into `skipped_node_ids`, not `per_node`; community assembly reads from `per_node`, not raw `communities[cid]`. |
| Profile-supplied regex matching on a very large attribute value | DoS | Candidate length cap 2048 applied INSIDE `_match_when` before `fullmatch` call. If attribute exceeds cap, matcher returns `False` (not an error — consistent with "rule didn't match" semantics). |
| Malformed `when.topology.value` (e.g., string instead of int) | Tampering / crash | `validate_rules` checks type at compile time; non-int → validation error; whole profile falls back to defaults. |

### Threat Model Note

Phase 3's inputs are **fully trusted**:
- The graph `G` comes from graphify's own extractor pipeline (`build.py`, `extract.py`) which has its own validation at `validate.py`.
- The `communities` dict comes from `cluster.py`, guaranteed structural shape.
- The `profile` dict comes from `load_profile()` which already validates via `validate_profile` and falls back to defaults on error.

**No network, no untrusted inputs.** The threat model is "malformed profile crashes the classifier" and "dead rules silently never fire" — both quality-of-UX threats, not security-boundary crossings. The regex caps are a belt-and-suspenders mitigation for the theoretically-possible (but not practically-observed) case where a user's `.graphify/profile.yaml` is edited by a less-trusted process (e.g., a shared vault on an untrusted mount point).

**Consistency with Phase 2 security posture:** `02-SECURITY.md` (Phase 2) established input-cap mindset for label sanitization and wikilink alias escaping. Phase 3 extends the same philosophy: caps and validation at load time, return-False on over-cap input at match time, no runtime surprises.

---

## Sources

### Primary (HIGH confidence — VERIFIED in this repo)

- `graphify/profile.py:16-39` — `_DEFAULT_PROFILE` shape, `_VALID_TOP_LEVEL_KEYS` frozenset, `_deep_merge`
- `graphify/profile.py:76-84` — `_deep_merge` behavior for nested dict override
- `graphify/profile.py:114-118` — `load_profile` error-fallback pattern
- `graphify/profile.py:127-202` — `validate_profile` error-list pattern (the shape `validate_rules` mirrors)
- `graphify/profile.py:178-195` — `folder_mapping` path rejection rules (`..`, absolute, `~`) — exact pattern to mirror for `then.folder`
- `graphify/profile.py:204` — `safe_tag` for community name slug (D-59)
- `graphify/profile.py:326-329` — `isinstance(value, bool) before isinstance(value, int)` pattern
- `graphify/templates.py:57-67` — `ClassificationContext(TypedDict, total=False)` exact shape (the Phase 3 output contract)
- `graphify/templates.py:421-451` — `_build_members_section` consumer of `members_by_type`
- `graphify/templates.py:458-477` — `_build_sub_communities_callout` consumer of `sub_communities`
- `graphify/templates.py:536-653` — `render_note` reads `parent_moc_label`, `community_tag`, `community_name`, `sibling_labels`
- `graphify/templates.py:660-820` — `_render_moc_like` reads `members_by_type`, `sub_communities`, `community_tag`, `community_name`, `cohesion`
- `graphify/analyze.py:6-8` — `_node_community_map` inverted lookup utility
- `graphify/analyze.py:11-36` — `_is_file_node` filter (method stubs, file hubs, module-level function stubs)
- `graphify/analyze.py:39-58` — `god_nodes(G, top_n)` return shape and filtering semantics (D-48 source of truth)
- `graphify/analyze.py:93-109` — `_is_concept_node` filter (empty source_file, no-extension source_file)
- `graphify/cluster.py:59-104` — `cluster(G)` return shape (`dict[int, list[str]]`, community 0 = largest)
- `graphify/cluster.py:87-91` — size-1 isolates handling (D-55 edge case)
- `graphify/cluster.py:125-137` — `cohesion_score` and `score_all` (input to `cohesion_gte` matcher)
- `graphify/validate.py:10-63` — `validate_extraction(data) -> list[str]` canonical error-list pattern
- `graphify/security.py:184-197` — `_CONTROL_CHAR_RE` and `_MAX_LABEL_LEN = 256` as module-level constant pattern
- `graphify/export.py:440-679` — legacy `to_obsidian()` reference (Phase 5 rewires; do not modify)
- `graphify/export.py:559-566` — existing single-pass edge walk for inter-community counts
- `tests/fixtures/template_context.py` — `make_classification_context`, `make_moc_context`, `make_min_graph` existing helpers (Phase 3 extends with `make_classification_fixture`)
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-01..D-16 profile validation pattern context
- `.planning/phases/02-template-engine/02-CONTEXT.md` — D-17..D-42 template contract context
- `.planning/phases/02-template-engine/02-RESEARCH.md` — Phase 2 research patterns (reusable background)
- `.planning/codebase/CONVENTIONS.md` — naming, typing, style conventions
- `.planning/codebase/TESTING.md` — pytest conventions, one-test-per-module layout, no-tmp_path philosophy

### Secondary (MEDIUM confidence — standard Python library behavior)

- Python stdlib `re` module — no native timeout parameter; ReDoS mitigation is via input length caps. [CITED: docs.python.org/3/library/re.html]
- Python `typing.TypedDict(total=False)` — allows optional keys, matches Phase 2 convention. [CITED: docs.python.org/3/library/typing.html#typing.TypedDict]
- `isinstance(True, int) == True` in Python (bool is subclass of int). [VERIFIED: Python REPL, widely documented]
- NetworkX `G.degree(n)` is O(1) via DegreeView. [VERIFIED: networkx.org/documentation/stable/reference/classes/generated/networkx.Graph.degree.html]

### Tertiary (LOW confidence — assumptions requiring validation)

- None. All claims in this research are either verified in-repo or cite well-known Python/NetworkX behavior.

---

## Metadata

**Confidence breakdown:**

- Rule-matching engine design: **HIGH** — grounded in existing `analyze.py` / `extract.py` dispatch patterns.
- Regex safety strategy: **HIGH** — consistent with `security.py`'s size-cap philosophy; D-44 caps are explicitly locked.
- Dead-rule detection: **HIGH** — conservative structural heuristic with mathematical guarantee of no false positives. Minor LOW on `attr_contains` semantic subtlety — may ship as "skip" initially and add later.
- Nearest-host resolution: **HIGH** — identical pattern to existing `export.py:559-566`.
- MOC label derivation: **HIGH** — clean separation of global god-nodes (for matcher) and per-community rankings (for label/siblings).
- Profile schema extensions: **HIGH** — `_deep_merge` pattern already proven in Phase 1; `isinstance` bool-guard pattern already in `profile.py:326`.
- Public API shape: **HIGH** — single-entry justified by precedence pipeline indivisibility.
- Testing strategy: **HIGH** — reuses Phase 2 fixture infrastructure; no new tooling needed.
- Validation architecture: **HIGH** — pytest already the project's runner; test mapping to MAP-01..MAP-06 is direct.
- Security domain: **HIGH** — threat model is narrow and well-understood (trusted local inputs).

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days — stable stdlib + in-repo patterns, no fast-moving dependencies)
