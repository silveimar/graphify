# Phase 34: Mapping, Cluster Quality & Note Classes - Research

**Researched:** 2026-04-28  
**Domain:** Obsidian export mapping, community routing, note-class taxonomy  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Community Output Semantics
- **D-01:** All Obsidian community exports must be MOC-only for default and custom profiles.
- **D-02:** Legacy `_COMMUNITY_*` overview rendering must be disabled in default output, but internal renderer support may remain for explicit legacy/profile migration diagnostics in Phase 35.
- **D-03:** If a profile or mapping path requests `note_type: community`, Phase 34 should coerce it to MOC output with a warning rather than fail or silently render legacy notes.
- **D-04:** Phase 34 must not scan existing vault files for `_COMMUNITY_*`; Phase 35 surfaces existing legacy files as migration candidates or orphans.

### Cluster-Quality Floor Behavior
- **D-05:** Connected below-floor communities should nest under the nearest above-floor host MOC first; only hostless or isolate communities route to `_Unclassified`.
- **D-06:** Isolates below the floor must not get standalone MOCs, but their rendered node notes should point up to `_Unclassified`, and `_Unclassified` should list them as sub-communities.
- **D-07:** Treat accepted `mapping.min_community_size` values literally. If a user configures `1`, single-node communities may become standalone MOCs.
- **D-08:** Change the built-in/default v1.8 `mapping.min_community_size` from `3` to `6`; user profiles can override it.
- **D-09:** Phase 34 should emit enough metadata for MOCs and dry-run plans to show whether a community is standalone, hosted, or bucketed.

### CODE Note Identity
- **D-10:** Add a real `code` note class/type in Phase 34 rather than layering CODE behavior onto `thing`.
- **D-11:** CODE notes are only for god nodes with `file_type: code` and a real `source_file`; concept nodes and file hubs are excluded.
- **D-12:** CODE filenames use `CODE_<repo>_<node>.md`, where repo is the resolved normalized repo identity and node follows safe filename normalization.
- **D-13:** Filename collisions between CODE notes must be resolved with a deterministic short hash derived from node id/source file, and collision provenance should be recorded in metadata/dry-run.

### CODE-Concept Navigation
- **D-14:** CODE and concept MOC navigation should be bidirectional through both frontmatter and body wikilinks.
- **D-15:** CODE notes use `up:` to point to their related concept MOC.
- **D-16:** Concept MOCs list important CODE notes using `related:` or a dedicated code-members field if the implementation needs one.
- **D-17:** Concept MOC CODE listings include only CODE-eligible god-node members of that hosted or standalone community, sorted by degree then label, capped for readability.
- **D-18:** Phase 34 should produce classification context and safe filenames plus minimal default rendering/tests proving CODE<->concept links exist; Phase 35 polishes final templates, dry-run, and migration visibility.

### Claude's Discretion
- Exact warning wording, metadata field names, and cap size for listed CODE members may be chosen during planning, as long as they remain deterministic, testable, and compatible with existing Ideaverse-style frontmatter.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Full legacy `_COMMUNITY_*` vault scan and migration-candidate/orphan reporting — Phase 35.
- Final CODE-specific template polish and broader dry-run/migration presentation — Phase 35.
- Migration guide and skill/documentation alignment — Phase 36.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMM-01 | User receives MOC-only community output by default, with no generated `_COMMUNITY_*` overview notes. | Coerce `community` to `moc` in profile/template/export paths and remove community overview rendering from normal `to_obsidian()` flow. [VERIFIED: `.planning/REQUIREMENTS.md`; `graphify/export.py`] |
| CLUST-02 | User sees isolate communities omitted from standalone MOC generation while their nodes remain available in graph data and non-community exports. | Existing `_assemble_communities()` buckets hostless below-floor communities while preserving per-node contexts; add explicit routing metadata and tests for isolate semantics. [VERIFIED: `graphify/mapping.py`; `tests/test_mapping.py`] |
| CLUST-03 | User sees tiny connected communities below the configured floor routed deterministically into an `_Unclassified` MOC. | User decision supersedes terse requirement: connected below-floor communities host under nearest above-floor MOC first; only hostless/isolate communities route to `_Unclassified`. [VERIFIED: `34-CONTEXT.md`; `graphify/mapping.py`] |
| GOD-01 | User sees code-derived god nodes exported as `CODE_<repo>_<node>` notes rather than generic Things. | Extend note-type whitelist and god-node fallback so eligible code god nodes classify as `code`; compute CODE filenames after repo identity resolution. [VERIFIED: `graphify/mapping.py`; `graphify/templates.py`; `graphify/export.py`; `graphify/naming.py`] |
| GOD-02 | User sees CODE notes linked to their related concept MOC through frontmatter or body wikilinks. | Existing `render_note()` already emits `up:` frontmatter and Wayfinder Up when `parent_moc_label` is present; CODE must reuse this path with CODE filenames. [VERIFIED: `graphify/templates.py`; `tests/test_templates.py`] |
| GOD-03 | User sees concept MOCs list their important CODE member notes, preserving bidirectional navigation. | Extend MOC context with capped CODE member labels and feed them into `related:` and/or members section. [VERIFIED: `graphify/mapping.py`; `graphify/templates.py`] |
| GOD-04 | User is protected from filename collisions between CODE notes and concept MOCs. | Prefix all CODE filenames with normalized `CODE_<repo>_` and hash-suffix duplicate CODE stems deterministically from node id/source file. [VERIFIED: `graphify/naming.py`; `graphify/profile.py`; `graphify/templates.py`] |
</phase_requirements>

## Summary

Phase 34 should be planned as a focused contract update across the existing mapping -> export -> template pipeline, not as a new exporter. `classify()` already centralizes per-node and per-community `ClassificationContext` assembly, including min-community-size routing, nearest-host selection, `_Unclassified` bucket generation, and per-node parent MOC fields. [VERIFIED: `graphify/mapping.py`] `to_obsidian()` already resolves repo identity and concept MOC names before rendering, then routes `per_node` and `per_community` contexts into `render_note()` / `render_moc()`. [VERIFIED: `graphify/export.py`]

The largest planning risk is contract drift between the note-type whitelist surfaces. `templates.py` defines `_NOTE_TYPES`, `_REQUIRED_PER_TYPE`, `load_templates()`, and render-time allowed non-MOC note types; `profile.py` mirrors note-type validation for `dataview_queries`; `mapping.py` validates rule outputs against `_NOTE_TYPES`; tests pin the current six-note-type behavior. [VERIFIED: `graphify/templates.py`; `graphify/profile.py`; `graphify/mapping.py`; `tests/test_templates.py`] Phase 34 must update all of these together for a real `code` class while preserving legacy `community` as a warning/coercion input, not a normal output. [VERIFIED: `34-CONTEXT.md`]

**Primary recommendation:** implement a single `code` note class through existing `ClassificationContext` and template rendering, compute CODE filenames in export after repo identity resolution, and make `community` output a warned MOC coercion in all normal Obsidian paths. [VERIFIED: codebase inspection]

## Project Constraints (from .cursor/rules/)

No `.cursor/rules/` files were present in the repository during research. [VERIFIED: glob search]

Project-level constraints from `CLAUDE.md` still apply: Python 3.10+, no new required dependencies, pure unit tests using `tmp_path`, no filesystem side effects outside temporary/output directories, and security helpers for paths/labels/frontmatter must remain in use. [VERIFIED: `CLAUDE.md`]

No project-defined `.claude/skills/` or `.agents/skills/` existed in the repository. [VERIFIED: glob search]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| MOC-only community semantics | Mapping / Export | Templates | Mapping/export decide which note classes exist; templates only render a selected class. [VERIFIED: `graphify/mapping.py`; `graphify/export.py`; `graphify/templates.py`] |
| Cluster-quality routing | Mapping | Export | `_assemble_communities()` owns community host/bucket routing and per-node parent MOC context; export should consume the result. [VERIFIED: `graphify/mapping.py`] |
| CODE eligibility | Mapping | Analyze | `analyze.god_nodes()` identifies hubs; mapping should filter to code file-backed, non-synthetic nodes and assign `note_type="code"`. [VERIFIED: `graphify/analyze.py`; `graphify/mapping.py`] |
| CODE filename identity | Export | Naming / Templates | Repo identity is resolved in `to_obsidian()` before rendering, so collision-safe CODE filename stems should be computed there and passed through context. [VERIFIED: `graphify/export.py`; `graphify/naming.py`] |
| CODE<->concept links | Mapping / Templates | Export | Mapping knows host MOCs and CODE members; templates emit `up`, `related`, Wayfinder, and members sections. [VERIFIED: `graphify/mapping.py`; `graphify/templates.py`] |
| Profile validation | Profile | Mapping / Templates | `profile.py` validates schema keys and note-type names before rendering; mapping/templates should still coerce legacy `community` safely at runtime. [VERIFIED: `graphify/profile.py`] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10.19 installed; project requires `>=3.10` | Implementation runtime | CI target and project runtime. [VERIFIED: shell; `pyproject.toml`; `CLAUDE.md`] |
| NetworkX | 3.4.2 installed; dependency unpinned | Graph topology, degree, edges, communities | Existing graph abstraction across mapping, export, clustering, and tests. [VERIFIED: shell; `pyproject.toml`; `graphify/mapping.py`] |
| stdlib `hashlib` | Python stdlib | Deterministic CODE collision suffixes | Already used for repo identity length caps and concept-name signatures; no new dependency needed. [VERIFIED: `graphify/naming.py`] |
| stdlib `string.Template` | Python stdlib | Template rendering | Existing template engine intentionally avoids Jinja/new dependencies. [VERIFIED: `graphify/templates.py`; `CLAUDE.md`] |
| pytest | 9.0.3 installed | Unit tests | Existing test suite is pytest-based and pure unit tests. [VERIFIED: shell; `tests/`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 installed; optional `obsidian` extra | User profile parsing | Only for `.graphify/profile.yaml`; built-in defaults still work without it. [VERIFIED: shell; `pyproject.toml`; `graphify/profile.py`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing `ClassificationContext` | Separate CODE export manifest | Adds a parallel source of truth and risks drift from merge/render behavior. [VERIFIED: `graphify/mapping.py`; `graphify/export.py`] |
| Existing `string.Template` templates | Jinja2 | Violates no-new-required-dependency constraint and bypasses Phase 31 block-template validation. [VERIFIED: `CLAUDE.md`; `graphify/templates.py`] |
| Existing NetworkX degree/god-node pipeline | New hub detector | v1.8 explicitly changes output semantics, not graph topology/clustering. [VERIFIED: `.planning/REQUIREMENTS.md`; `graphify/analyze.py`] |

**Installation:** no new required install step. Existing development command remains:

```bash
pip install -e ".[mcp,pdf,watch]"
```

**Version verification:** Python 3.10.19, pytest 9.0.3, NetworkX 3.4.2, tree-sitter 0.25.2, and PyYAML 6.0.3 were installed in the local environment during research. [VERIFIED: shell]

## Architecture Patterns

### System Architecture Diagram

```text
Graph + communities + profile
        |
        v
resolve_repo_identity() + resolve_concept_names()
        |
        v
classify()
  |-- per_node: statement/person/source/code/thing contexts
  |-- per_community: MOC contexts only
  |-- skipped_node_ids: concept/file hubs
  |-- routing metadata: standalone/hosted/bucketed
        |
        v
export pre-render pass
  |-- compute CODE_<repo>_<node> filename stems
  |-- inject collision metadata into code contexts
  |-- ensure community note_type "community" is coerced to "moc"
        |
        v
templates.render_note() / templates.render_moc()
  |-- CODE notes render as real type: code
  |-- concept MOCs include capped CODE links
  |-- all links/frontmatter use existing sanitizers
        |
        v
merge plan / vault writes
```

### Recommended Project Structure

```text
graphify/
├── mapping.py              # classify CODE eligibility, routing metadata, MOC code members
├── export.py               # repo-aware CODE filename pre-pass; MOC-only rendering
├── templates.py            # code note type, built-in code rendering, MOC CODE links
├── profile.py              # note-type validation, default min_community_size=6
├── naming.py               # optional pure filename helper if avoiding template coupling
└── builtin_templates/
    └── code.md             # CODE note default template, likely thing-like initially

tests/
├── test_mapping.py         # routing and CODE classification contracts
├── test_export.py          # dry-run paths, collision-safe CODE filenames
├── test_templates.py       # CODE frontmatter/body links and MOC CODE links
├── test_profile.py         # defaults and profile note-type validation
└── test_naming.py          # helper-level repo/code filename tests if helper added
```

### Pattern 1: Keep Mapping As Source Of Classification Truth

**What:** Extend `classify()` and `_assemble_communities()` to return all note-class and routing data needed by export/templates. [VERIFIED: `graphify/mapping.py`]  
**When to use:** CODE eligibility, standalone/hosted/bucketed routing metadata, `_Unclassified` parent assignment, and MOC member lists. [VERIFIED: `34-CONTEXT.md`]  
**Example:**

```python
# Existing pattern: mapping builds per-node contexts and per-community contexts together.
mapping_result = classify(G, communities, profile, cohesion=cohesion)
per_node = mapping_result.get("per_node", {}) or {}
per_community = mapping_result.get("per_community", {}) or {}
```

### Pattern 2: Compute Repo-Aware CODE Filenames After Repo Resolution

**What:** `to_obsidian()` is the first point where both resolved repo identity and all classified code nodes are available; compute `CODE_<repo>_<node>` filename stems there and inject them into each CODE context before `render_note()`. [VERIFIED: `graphify/export.py`; `graphify/naming.py`]  
**When to use:** CODE filenames, collision suffixes, and collision provenance. [VERIFIED: `34-CONTEXT.md`]  
**Example:**

```python
# Recommended shape, not existing code.
code_stems = build_code_filename_stems(G, per_node, resolved_repo_identity.identity)
for node_id, stem_info in code_stems.items():
    per_node[node_id]["filename_stem"] = stem_info.stem
    per_node[node_id]["filename_collision"] = stem_info.collision
```

### Pattern 3: Coerce `community` At The Boundary, Not By Deleting It

**What:** Keep `community` recognized as an input/profile/template compatibility token, but normalize it to `moc` before normal Obsidian rendering. [VERIFIED: `34-CONTEXT.md`; `graphify/templates.py`; `graphify/export.py`]  
**When to use:** Mapping rules, `dataview_queries`, per-community render dispatch, and user template/profile migration warnings. [VERIFIED: `graphify/profile.py`; `graphify/export.py`]  
**Example:**

```python
# Recommended shape, not existing code.
if note_type == "community":
    print("[graphify] warning: note_type 'community' is deprecated; rendering as 'moc'", file=sys.stderr)
    note_type = "moc"
```

### Pattern 4: Reuse Existing Frontmatter And Wikilink Emitters

**What:** CODE notes should use `render_note()` so `up:`, `related:`, Wayfinder, connections, metadata, frontmatter escaping, and wikilink alias sanitization stay centralized. [VERIFIED: `graphify/templates.py`]  
**When to use:** GOD-02 and GOD-03 rendering. [VERIFIED: `.planning/REQUIREMENTS.md`]  
**Example:**

```python
# Existing behavior: non-MOC notes already get `up` from parent_moc_label.
if parent_moc_label:
    up_list.append(_emit_wikilink(parent_moc_label, convention))
```

### Anti-Patterns To Avoid

- **Parallel CODE exporter:** It would bypass `compute_merge_plan()`, sentinel handling, and profile templates. Use `ClassificationContext` and normal render/merge paths. [VERIFIED: `graphify/export.py`; `graphify/merge.py`]
- **Treating `community` as a normal output type:** It would keep `_COMMUNITY_*` era semantics alive and violate COMM-01. Coerce to MOC with a warning. [VERIFIED: `34-CONTEXT.md`; `.planning/REQUIREMENTS.md`]
- **Hashing every CODE filename unconditionally:** The decision asks for hash suffixes for collisions; prefix-only names should stay readable when unique. [VERIFIED: `34-CONTEXT.md`]
- **Counting file hubs/concept nodes as CODE:** Existing synthetic filters skip concept nodes and file hubs; CODE eligibility must preserve that filter. [VERIFIED: `graphify/mapping.py`; `tests/fixtures/template_context.py`]
- **Changing cluster topology:** v1.8 output taxonomy changes rendering/routing semantics, not Leiden/Louvain clustering. [VERIFIED: `.planning/REQUIREMENTS.md`; `graphify/cluster.py`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| God-node detection | New centrality algorithm | `analyze.god_nodes()` through `classify()` | Existing mapping already computes `god_node_ids` once and tests it. [VERIFIED: `graphify/mapping.py`; `graphify/analyze.py`] |
| Community hosting | New graph traversal | Existing `_nearest_host()` and `_inter_community_edges()` | They already implement deterministic edge-count, size, cid tie-breaks. [VERIFIED: `graphify/mapping.py`; `tests/test_mapping.py`] |
| Filename sanitization | Raw regex in export loops | `safe_filename()` / existing filename normalization patterns | Existing profile/template code already strips unsafe path/wiki chars and caps lengths. [VERIFIED: `graphify/profile.py`; `graphify/templates.py`; `graphify/naming.py`] |
| Frontmatter writing | Manual YAML strings | `_build_frontmatter_fields()` + `_dump_frontmatter()` | Existing helpers preserve field order and quote risky scalars. [VERIFIED: `graphify/templates.py`; `graphify/profile.py`] |
| Template rendering | New templating engine | Existing `string.Template` + block preprocessor | Phase 31 already validates placeholders/blocks and avoids new dependencies. [VERIFIED: `graphify/templates.py`; `CLAUDE.md`] |
| Vault writes | Direct file writes from CODE exporter | Existing merge plan/apply flow | Merge preserves user fields and handles dry-run/update/skip outcomes. [VERIFIED: `graphify/export.py`; `graphify/merge.py`] |

**Key insight:** The hard part is not rendering one more markdown file; it is keeping note identity, community routing, frontmatter, body links, dry-run paths, and merge behavior driven by one classification contract. [VERIFIED: codebase inspection]

## Common Pitfalls

### Pitfall 1: Updating Only One Note-Type Whitelist

**What goes wrong:** `code` validates in one layer but fails in another, or built-in template loading looks for no `code.md`. [VERIFIED: `graphify/templates.py`; `graphify/profile.py`; `graphify/mapping.py`]  
**Why it happens:** Note types are mirrored across `_NOTE_TYPES`, `_KNOWN_NOTE_TYPES`, `_REQUIRED_PER_TYPE`, `render_note()` allowed types, `load_templates()`, and tests. [VERIFIED: codebase inspection]  
**How to avoid:** Plan a single task that updates every note-type surface plus adds `builtin_templates/code.md`. [VERIFIED: `graphify/builtin_templates/`]  
**Warning signs:** `ValueError: render_note: note_type 'code' not in ...`, missing `code.md`, or `dataview_queries: unknown note_type 'code'`.

### Pitfall 2: Concept Names Not Matching Parent Links

**What goes wrong:** Mapping assigns topology-derived community labels, export later replaces MOC names with LLM/cache concept names, but node `parent_moc_label` still points at the old label. [VERIFIED: `graphify/export.py`; `graphify/templates.py`]  
**Why it happens:** `to_obsidian()` currently updates `per_community` labels after `classify()`, but per-node contexts are populated inside mapping before that override. [VERIFIED: `graphify/export.py`; `graphify/mapping.py`]  
**How to avoid:** When applying `merged_labels`, also update every per-node context hosted by that community/bucket so CODE `up:` and Wayfinder target the final rendered concept MOC title. [VERIFIED: codebase inspection]  
**Warning signs:** MOC file is `Authentication_Session_Flow.md` but CODE note links to `[[Auth_Session|Auth Session]]`.

### Pitfall 3: Default Floor Changes Break Existing Tests

**What goes wrong:** Tests expecting `mapping.min_community_size == 3` fail when default changes to 6. [VERIFIED: `tests/test_mapping.py`; `graphify/profile.py`]  
**Why it happens:** Test helper `_profile()` and default profile both currently use `3`. [VERIFIED: `tests/test_mapping.py`; `graphify/profile.py`]  
**How to avoid:** Update default-profile tests to assert `6`, but keep tests that explicitly set `1`, `2`, or `3` to verify literal user override semantics. [VERIFIED: `34-CONTEXT.md`]  
**Warning signs:** Assertions named `test_default_profile_min_community_size_is_3` or comments describing `>=3` behavior.

### Pitfall 4: Host-First Routing Versus Requirement Wording

**What goes wrong:** A planner implements "all tiny connected communities go to `_Unclassified`" because CLUST-03 is terse. [VERIFIED: `.planning/REQUIREMENTS.md`]  
**Why it happens:** The discussion decision D-05 refines the behavior: connected below-floor communities host under nearest above-floor MOC first. [VERIFIED: `34-CONTEXT.md`]  
**How to avoid:** Preserve `_nearest_host()` semantics and add metadata/tests that distinguish hosted from bucketed. [VERIFIED: `graphify/mapping.py`]  
**Warning signs:** Tests asserting a connected below-floor community is in `_Unclassified` despite an inter-community edge to an above-floor MOC.

### Pitfall 5: CODE Collision Handling Depends On Iteration Order

**What goes wrong:** Only the second colliding filename gets a suffix, so output flips when graph insertion order changes. [VERIFIED: NetworkX graph order affects iteration; codebase already sorts in several places]  
**Why it happens:** Sequential "seen count" suffixing is easy but not stable under reordered equivalent input. [VERIFIED: `graphify/export.py` canvas helper uses sequential suffixes; Phase 34 needs stronger determinism]  
**How to avoid:** Group CODE candidates by base stem, and when a group has more than one candidate, suffix every member with `sha256(node_id + "\0" + source_file)[:8]`. [VERIFIED: `34-CONTEXT.md`; `graphify/naming.py` uses SHA-256 patterns]  
**Warning signs:** A test only covers duplicate labels in insertion order and not reversed order.

## Code Examples

### Existing Host Selection Contract

```python
def _nearest_host(
    below_cid: int,
    above_cids: list[int],
    inter_edges: dict[tuple[int, int], int],
    community_sizes: dict[int, int],
) -> int | None:
    """D-53: return the above-threshold cid with the most inter-community
    edges to ``below_cid``.
```

Source: `graphify/mapping.py`. [VERIFIED: codebase]

### Existing Non-MOC `up:` Frontmatter Contract

```python
up_list: list[str] = []
if parent_moc_label:
    up_list.append(_emit_wikilink(parent_moc_label, convention))
```

Source: `graphify/templates.py`. [VERIFIED: codebase]

### Existing Export Ordering: Repo And Concept Names Before Classification Render

```python
resolved_repo_identity = resolve_repo_identity(
    Path.cwd(),
    cli_identity=repo_identity,
    profile=profile,
)
concept_names = resolve_concept_names(
    G,
    communities,
    profile,
    artifacts_dir,
    llm_namer=concept_namer,
    dry_run=dry_run,
)
mapping_result = classify(G, communities, profile, cohesion=cohesion)
```

Source: `graphify/export.py`. [VERIFIED: codebase]

### Recommended CODE Filename Helper Shape

```python
# Proposed pattern for planning; not existing code yet.
def code_filename_stem(repo: str, node_label: str, *, node_id: str, source_file: str, collision: bool) -> str:
    base = f"CODE_{safe_filename(repo)}_{safe_filename(node_label)}"
    if not collision:
        return base
    suffix = hashlib.sha256(f"{node_id}\0{source_file}".encode("utf-8")).hexdigest()[:8]
    return f"{base}_{suffix}"
```

Source rationale: `safe_filename()` in `profile.py`; SHA-256 suffix pattern in `naming.py`; D-12/D-13 in `34-CONTEXT.md`. [VERIFIED: codebase and context]

## State Of The Art

| Old Approach | Current Phase 34 Approach | When Changed | Impact |
|--------------|---------------------------|--------------|--------|
| `_COMMUNITY_*` overview output | MOC-only community output | v1.8 Phase 34 decision | Normal Obsidian export must not create legacy overview notes. [VERIFIED: `34-CONTEXT.md`; `.planning/REQUIREMENTS.md`] |
| God nodes render as generic `thing` notes | Code-derived god nodes render as `code` notes with CODE filenames | v1.8 Phase 34 decision | CODE hubs are visually and path-wise separate from concept MOCs. [VERIFIED: `34-CONTEXT.md`] |
| Default `mapping.min_community_size = 3` | Default `mapping.min_community_size = 6` | v1.8 Phase 34 decision | More small clusters are hosted/bucketed by default; user overrides remain literal. [VERIFIED: `graphify/profile.py`; `34-CONTEXT.md`] |
| Below-floor hostless communities bucketed | Connected below-floor communities host first; hostless/isolate bucket | Already partially implemented before Phase 34 | Plan should preserve host-first and add metadata/tests. [VERIFIED: `graphify/mapping.py`; `34-CONTEXT.md`] |

**Deprecated/outdated:**
- `note_type: community` as normal output is deprecated for Obsidian export; Phase 34 should warn and render MOC output. [VERIFIED: `34-CONTEXT.md`]
- Legacy `_COMMUNITY_*` vault-file scanning is not Phase 34; it is Phase 35. [VERIFIED: `34-CONTEXT.md`; `.planning/ROADMAP.md`]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|

All implementation-relevant claims in this research were verified against planning artifacts, repository code, or local environment probes; no `[ASSUMED]` claims are required. [VERIFIED: research session]

## Open Questions (RESOLVED)

1. **Should concept MOCs use `related:` or a dedicated `code_members:` frontmatter field for CODE links?**
   - Resolution: Use `related:` in Phase 34 for frontmatter compatibility, and add internal `code_members` / `code_member_labels` context fields for deterministic body rendering.
   - Rationale: D-16 explicitly allows either `related:` or a dedicated field; the existing frontmatter builder already supports `related`, so this avoids a new public frontmatter contract while still giving templates structured CODE-member data. [VERIFIED: `34-CONTEXT.md`; `graphify/templates.py`]

2. **What cap should CODE member listings use?**
   - Resolution: Use cap `10`.
   - Rationale: The cap is Claude's discretion; research recommended `10` as large enough for useful hub navigation and small enough for MOC readability. D-17 sorting remains degree descending, then label ascending. [VERIFIED: `34-CONTEXT.md`]

3. **Where should CODE collision provenance appear?**
   - Resolution: Add context fields `filename_stem`, `filename_collision`, and `filename_collision_hash`; render collision status in CODE metadata/frontmatter only when collision occurs.
   - Rationale: D-13 requires metadata/dry-run provenance, while Phase 35 owns broader dry-run and migration presentation. Phase 34 should expose enough structured data for correctness without adding Phase 35 migration-reporting scope. [VERIFIED: `34-CONTEXT.md`; `.planning/ROADMAP.md`]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime/tests | yes | 3.10.19 | CI also targets 3.12. [VERIFIED: shell; `CLAUDE.md`] |
| pytest | Validation | yes | 9.0.3 | None needed. [VERIFIED: shell] |
| NetworkX | Graph fixtures and classification | yes | 3.4.2 | Project dependency. [VERIFIED: shell; `pyproject.toml`] |
| PyYAML | Profile tests and user profile parsing | yes | 6.0.3 | Built-in default profile works without PyYAML; user profile parsing prints warning and falls back. [VERIFIED: shell; `graphify/profile.py`] |

**Missing dependencies with no fallback:** none found. [VERIFIED: shell]

**Missing dependencies with fallback:** none relevant to this phase. [VERIFIED: phase scope]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 [VERIFIED: shell] |
| Config file | none detected in read context; tests run directly via `pytest tests/ -q` per `CLAUDE.md`. [VERIFIED: `CLAUDE.md`] |
| Quick run command | `pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| COMM-01 | Default export creates MOC notes and no `_COMMUNITY_*` paths; `community` note type warns/coerces to MOC | unit/integration | `pytest tests/test_export.py tests/test_templates.py tests/test_profile.py -q` | yes |
| CLUST-02 | Isolate below floor has no standalone MOC, node note remains and points to `_Unclassified` | unit | `pytest tests/test_mapping.py::test_bucket_moc_absorbs_hostless_below_threshold -q` plus new test | yes |
| CLUST-03 | Connected below-floor communities host under nearest above-floor MOC; hostless bucket to `_Unclassified` | unit | `pytest tests/test_mapping.py -q` | yes |
| GOD-01 | Eligible code god node classifies/renders as `code` with `CODE_<repo>_<node>.md` | unit/integration | `pytest tests/test_mapping.py tests/test_export.py -q` | yes |
| GOD-02 | CODE note has `up:` and Wayfinder/body link to concept MOC | unit | `pytest tests/test_templates.py -q` | yes |
| GOD-03 | Concept MOC lists capped CODE members and frontmatter/body links back to CODE notes | unit | `pytest tests/test_mapping.py tests/test_templates.py -q` | yes |
| GOD-04 | CODE filename collisions receive deterministic hash suffixes and do not collide with concept MOCs | unit/integration | `pytest tests/test_naming.py tests/test_export.py -q` | yes |

### Sampling Rate

- **Per task commit:** run the smallest changed surface, usually `pytest tests/test_mapping.py -q`, `pytest tests/test_templates.py -q`, or `pytest tests/test_export.py -q`. [VERIFIED: project test pattern]
- **Per wave merge:** `pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q`. [VERIFIED: relevant files exist]
- **Phase gate:** `pytest tests/ -q` before verification. [VERIFIED: `CLAUDE.md`]

### Wave 0 Gaps

- [ ] `tests/test_mapping.py` — add default floor `6`, literal override `1`, routing metadata, and CODE eligibility tests.
- [ ] `tests/test_templates.py` — add `code` note type rendering, CODE `up:`/Wayfinder/body proof, MOC CODE member list proof, and legacy `community` coercion proof.
- [ ] `tests/test_export.py` — add dry-run path assertions for `CODE_<repo>_<node>.md`, collision hash determinism, and no `_COMMUNITY_*` output.
- [ ] `tests/test_profile.py` — add `_DEFAULT_PROFILE["mapping"]["min_community_size"] == 6`, note-type validation for `code`, and legacy `community` warning/coercion expectations.
- [ ] `tests/test_naming.py` — add helper tests if CODE filename helper lands in `naming.py`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth surface in this phase. [VERIFIED: phase scope] |
| V3 Session Management | no | No session surface in this phase. [VERIFIED: phase scope] |
| V4 Access Control | no | Local vault write paths remain constrained by existing merge/path helpers. [VERIFIED: `graphify/profile.py`; `graphify/merge.py`] |
| V5 Input Validation | yes | Use `safe_filename`, `safe_tag`, `_sanitize_wikilink_alias`, `safe_frontmatter_value`, and `validate_vault_path`. [VERIFIED: `graphify/profile.py`; `graphify/templates.py`] |
| V6 Cryptography | yes, limited | Use SHA-256 only for deterministic collision suffixes; not for security secrets. [VERIFIED: `graphify/naming.py`; `34-CONTEXT.md`] |

### Known Threat Patterns for Obsidian Export

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through CODE filename or taxonomy folder | Tampering | Generate CODE filename stems through existing safe filename logic and join only under validated folders. [VERIFIED: `graphify/profile.py`; `graphify/export.py`] |
| YAML/frontmatter injection through labels/source files | Tampering | Keep `_dump_frontmatter()` and `safe_frontmatter_value()` as the only frontmatter writers. [VERIFIED: `graphify/profile.py`; `graphify/templates.py`] |
| Wikilink breakage through `]]`, `|`, or newlines | Tampering | Use `_emit_wikilink()` / `_sanitize_wikilink_alias()` for all body and frontmatter wikilinks. [VERIFIED: `graphify/templates.py`] |
| Template injection through generated labels | Tampering | Preserve Phase 31 block expansion before `safe_substitute`; do not interpolate raw template syntax from labels. [VERIFIED: `graphify/templates.py`] |
| Accidental destructive migration of legacy `_COMMUNITY_*` files | Tampering / Data loss | Do not scan or delete legacy files in Phase 34; Phase 35 owns migration visibility. [VERIFIED: `34-CONTEXT.md`] |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/34-mapping-cluster-quality-note-classes/34-CONTEXT.md` — locked decisions, phase boundary, deferred scope.
- `.planning/REQUIREMENTS.md` — COMM/CLUST/GOD requirement traceability.
- `.planning/ROADMAP.md` — Phase 34 goal, success criteria, Phase 35/36 boundaries.
- `.planning/STATE.md` — carried-forward Phase 32/33 decisions.
- `CLAUDE.md` — project constraints, architecture, test commands.
- `graphify/mapping.py` — classification, god-node fallback, host/bucket community routing.
- `graphify/export.py` — repo/concept resolution, render loops, merge plan integration.
- `graphify/templates.py` — note-type whitelist, template loading, frontmatter, wikilinks, render functions.
- `graphify/profile.py` — default profile, profile validation, safe filename/tag/frontmatter helpers.
- `graphify/naming.py` — repo identity and deterministic hash/name patterns.
- `tests/test_mapping.py`, `tests/test_export.py`, `tests/test_templates.py`, `tests/test_profile.py`, `tests/test_naming.py` — closest regression homes.

### Secondary (MEDIUM confidence)

- Local environment probes for installed versions: Python, pytest, NetworkX, tree-sitter, PyYAML.
- Stale project graph status: graph exists but is 345 hours old; graph queries for Phase 34 terms returned no nodes, so semantic graph context was not used for decisions. [VERIFIED: graphify status/query]

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — this is an internal codebase phase with no new dependency choice; versions and project dependencies were verified locally and in `pyproject.toml`.
- Architecture: HIGH — implementation boundaries are explicit in `mapping.py`, `export.py`, `templates.py`, `profile.py`, and `naming.py`.
- Pitfalls: HIGH — pitfalls map directly to existing tests, whitelists, and phase decisions.

**Research date:** 2026-04-28  
**Valid until:** 2026-05-28 for internal architecture; re-check environment versions before execution if dependencies are upgraded.
