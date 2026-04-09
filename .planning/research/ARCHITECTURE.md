# Architecture Patterns: Configurable Vault Adapter

**Domain:** Python CLI library — configurable Obsidian vault export adapter
**Researched:** 2026-04-09
**Confidence:** HIGH (based on direct codebase reading, no external sources needed for architectural decisions)

---

## Recommended Architecture

### Overview

The configurable vault adapter is a **replacement for `to_obsidian()` in `export.py`**, composed of five discrete sub-components that form a sub-pipeline within the existing export stage. The adapter does not touch detect, extract, build, cluster, or analyze — it sits entirely within the export boundary and receives the same inputs `to_obsidian()` already receives.

```
[Existing Pipeline]
detect → extract → build_graph → cluster → analyze → report
                                                         ↓
                                                    [ export() ]
                                                         ↓
                              ┌──────────────────────────────────────────────┐
                              │          Vault Adapter Sub-Pipeline          │
                              │                                              │
                              │  ProfileLoader → MappingEngine              │
                              │       ↓               ↓                     │
                              │  TemplateEngine ← NoteContext               │
                              │       ↓                                     │
                              │  MergeEngine → written .md files            │
                              └──────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | File | Responsibility | Inputs | Outputs |
|-----------|------|---------------|--------|---------|
| **ProfileLoader** | `graphify/obsidian_profile.py` | Find and load `.graphify/profile.yaml` from vault dir; validate schema; inject defaults; merge with built-in default profile | `vault_path: str \| None` | `Profile` (typed dict or dataclass) |
| **MappingEngine** | `graphify/obsidian_mapper.py` | Assign a note type to each node using topology (degree, community role) and content attributes (`file_type`, custom attrs); assign folder and filename per profile rules | `G: nx.Graph`, `communities`, `analysis`, `profile: Profile` | `NodeMap: dict[node_id, NoteSpec]` |
| **TemplateEngine** | `graphify/obsidian_template.py` | Load `.md` templates from profile's `templates/` dir or built-in defaults; render note body and frontmatter by substituting `{{placeholder}}` values; sanitize all user-sourced values before insertion | `template_str: str`, `context: dict` | `rendered: str` |
| **NoteContext builder** | internal to MappingEngine or thin adapter function | Assembles per-node context dict from graph data (label, edges as wikilinks, community, god-node status, etc.) ready for TemplateEngine | `G`, `node_id`, `NoteSpec`, `NodeMap` | `context: dict` |
| **MergeEngine** | `graphify/obsidian_merge.py` | Given a rendered note and the existing file at target path: detect if file exists, parse existing frontmatter, apply merge strategy (update/skip/replace per profile config), write final file | `target_path: Path`, `rendered: str`, `merge_config: MergeConfig` | file written; `MergeResult` (created/updated/skipped) |

The existing `to_obsidian()` function in `export.py` becomes a thin wrapper that:
1. Calls `ProfileLoader` to get a `Profile`
2. Calls `MappingEngine` to get a `NodeMap`
3. For each node: builds context, renders via `TemplateEngine`, writes via `MergeEngine`
4. Writes community notes, `.obsidian/graph.json` — same as today, but driven by profile config

---

## Data Flow

```
vault_path (CLI arg or output_dir)
    │
    ▼
ProfileLoader
    reads:  vault_path/.graphify/profile.yaml  (if exists)
            vault_path/.graphify/templates/     (if exists)
    falls back to: built-in default profile (Ideaverse ACE structure)
    outputs: Profile {
        folders: {moc: "Atlas/Maps", dot: "Atlas/Dots/Things", ...}
        mapping_rules: [{condition: "god_node", note_type: "Dot/Thing"}, ...]
        merge: {strategy: "update", preserve_fields: ["rank", "mapState"]}
        naming: {convention: "label", separator: "-"}
        dataview: {enabled: true}
        graph_colors: {enabled: true}
        community_threshold: 5
    }
    │
    ▼
MappingEngine  ←── G (nx.Graph), communities (dict), analysis (god_nodes, bridges)
    for each node_id:
        - compute topology role: god_node (degree > threshold), community_hub
          (highest degree in community), leaf (degree 1), isolated (degree 0)
        - apply content rules: file_type=="person" → "Dot/Person"
        - apply topology rules: god_node → "Dot/Thing"
        - rules evaluated in declaration order; first match wins
        - assign: note_type, target_folder, filename (per naming convention)
    for each community above threshold:
        - assign: MOC note type, target folder (Maps/)
    outputs: NodeMap {
        node_id: NoteSpec {
            note_type: "Dot/Thing",
            folder: "Atlas/Dots/Things",
            filename: "transformer",         # no extension
            wikilink: "[[Atlas/Dots/Things/transformer]]",
        }
    }
    │
    ▼
NoteContext (per node) ←── G, node_id, NoteSpec, NodeMap, communities, analysis
    builds: {
        "label": "Transformer",
        "up": "[[Atlas/Maps/Core Architecture]]",       # community MOC wikilink
        "related": ["[[Attention]]", "[[LayerNorm]]"],  # same-community neighbors
        "collections": [],
        "tags": ["graphify/code", "community/core-architecture"],
        "source_file": "models/transformer.py",
        "connections": [                                # all neighbors with relation
            {"wikilink": "[[Attention]]", "relation": "contains", "confidence": "EXTRACTED"},
        ],
        "community_name": "Core Architecture",
        "is_god_node": true,
        "dataview_query": "",  # empty for non-MOC notes
        "created": "2026-04-09",
    }
    │
    ▼
TemplateEngine ←── template_str (from profile or built-in), context dict
    - substitutes {{label}}, {{up}}, {{related}}, etc.
    - sanitizes each value via security.sanitize_label() before insertion
    - unknown placeholders left as-is (forward compat)
    - outputs: rendered markdown string (frontmatter + body)
    │
    ▼
MergeEngine ←── target_path, rendered_str, MergeConfig
    if target_path does not exist:
        write rendered_str → MergeResult.CREATED
    else:
        parse existing frontmatter (stdlib re / simple split on "---")
        for each frontmatter field in preserve_fields:
            keep existing value, overwrite rendered value
        if strategy == "update":  replace body + update non-preserved frontmatter
        if strategy == "skip":    leave file untouched → MergeResult.SKIPPED
        if strategy == "replace": overwrite entirely → MergeResult.REPLACED
        write final content → MergeResult.UPDATED
    │
    ▼
Written files in vault directory:
    Atlas/Maps/Core-Architecture.md       (MOC with Dataview query)
    Atlas/Dots/Things/Transformer.md      (god node)
    Atlas/Dots/Things/Attention.md
    Atlas/Sources/Books/Paper-XYZ.md      (source_file origin)
    .obsidian/graph.json                  (community colors, if enabled)
```

---

## Profile Schema Design

The `Profile` is a validated Python dict (no runtime classes needed for Python 3.10 compat). It is loaded from YAML and merged with a hard-coded `DEFAULT_PROFILE` dict — vault overrides win on every present key, absent keys fall back to default.

```yaml
# .graphify/profile.yaml  (vault-owned, checked in with vault)

folders:
  moc: "Atlas/Maps"
  dot_thing: "Atlas/Dots/Things"
  dot_statement: "Atlas/Dots/Statements"
  dot_person: "Atlas/Dots/People"
  source: "Atlas/Sources"
  community_overview: "Atlas/Maps"   # MOC notes land here

mapping_rules:
  # Rules evaluated top-to-bottom; first match wins.
  # topology conditions: god_node, community_hub, leaf, isolated
  # content conditions: file_type, attribute key/value pairs
  - condition: {attribute: "file_type", value: "person"}
    note_type: "dot_person"
  - condition: {topology: "god_node"}
    note_type: "dot_thing"
  - condition: {topology: "community_hub"}
    note_type: "dot_thing"
  - condition: {attribute: "file_type", value: "paper"}
    note_type: "source"
  - condition: {topology: "default"}
    note_type: "dot_thing"            # catch-all

naming:
  convention: "label"                 # "label" | "slug" | "id"
  separator: "-"
  case: "title"                       # "title" | "lower" | "preserve"

merge:
  strategy: "update"                  # "update" | "skip" | "replace"
  preserve_fields: ["rank", "mapState", "created"]   # never overwrite

community_threshold: 5                # min members for community → MOC

features:
  dataview: true
  graph_colors: true
  wayfinder: false
  inline_tags: false

obsidian:
  wikilink_style: "full_path"        # "full_path" | "filename_only"
```

**Inheritance / defaults merge:** `ProfileLoader` starts with `DEFAULT_PROFILE` (module-level dict in `obsidian_profile.py`), recursively updates it with the vault YAML using `dict.update()` at each nesting level. Missing top-level keys in the vault YAML keep their defaults. This is "shallow merge per section" — safe for the depth of this schema without requiring `deepmerge` or similar.

**Validation:** `ProfileLoader` validates the loaded dict against a hand-written set of checks (required keys present, valid enum values for `strategy`, `convention`, `case`, `wikilink_style`). Raises `ValueError` with a clear message on schema violations. No `pydantic` or `jsonschema` dependency — keeps the zero-new-required-dependencies constraint.

---

## Template Engine Design

Templates are plain `.md` files with `{{placeholder}}` substitution. No Jinja2.

```
.graphify/templates/
    dot_thing.md
    dot_person.md
    dot_statement.md
    source.md
    community_moc.md
```

**Substitution rules:**
- `{{label}}` → node label (sanitized)
- `{{up}}` → wikilink to parent MOC
- `{{related}}` → YAML list of wikilinks (`- [[Note]]`)
- `{{tags}}` → YAML list of tags
- `{{connections_body}}` → rendered connections section
- `{{dataview_query}}` → embedded dataview block (empty string if disabled)
- `{{created}}` → ISO date string
- Unknown placeholders → left as literal `{{placeholder}}` text

**Sanitization:** Every value inserted into a template passes through `security.sanitize_label()` (already in `security.py`) to strip HTML-special chars and control chars. This prevents injection via node labels into the rendered markdown.

**Built-in templates:** Module-level string constants in `obsidian_template.py`. Vault templates override built-ins when the profile's template dir contains the matching filename.

**Frontmatter and body are both template-driven.** The entire note content — `---` frontmatter block through body — is the template. This means the profile owner can put any fields they want in frontmatter, any Dataview queries they want in body, without graphify needing to know about them.

---

## Mapping Engine Design

Topology roles are derived from graph data already in memory:

| Role | Detection |
|------|-----------|
| `god_node` | node_id appears in `analysis["god_nodes"]` list |
| `community_hub` | highest degree node within its community (computed locally) |
| `leaf` | `G.degree(node_id) == 1` |
| `isolated` | `G.degree(node_id) == 0` |
| `default` | catch-all, always matches |

Content attribute conditions check `G.nodes[node_id].get(attribute) == value`.

**Rule evaluation:** Rules are tried in order. First matching rule determines `note_type`. This is O(rules × nodes) — acceptable for graphs up to tens of thousands of nodes.

**Community MOC assignment:** Communities with `len(members) >= community_threshold` generate a MOC note. The threshold comes from profile config. Community notes are separate from node notes — they are generated after all node notes.

**NoteSpec output:**

```python
@dataclass  # or TypedDict for Python 3.10 compat
class NoteSpec:
    note_type: str            # "dot_thing", "source", "community_moc", etc.
    folder: str               # resolved from profile folders config
    filename: str             # sanitized, no extension
    wikilink: str             # full [[path/filename]] per wikilink_style
```

---

## Merge Engine Design

The merge engine handles the case where a note already exists in the vault. This is the component most likely to cause data loss if wrong, so it must be conservative.

**Frontmatter parsing:** Split on `---` delimiters using stdlib string ops. No YAML library needed for parsing — only need to extract field values for preservation. Use a simple line-by-line scan: lines matching `key: value` pattern are stored in a dict. This is intentionally minimal — complex YAML structures in frontmatter are preserved by not touching them (they won't match the field-extraction regex and will be left in the preserved block as-is).

**Preservation strategy:**
```
existing frontmatter: {rank: "3", mapState: "architect", created: "2025-01-01"}
preserve_fields: ["rank", "mapState", "created"]
rendered frontmatter: {up: "[[Atlas/Maps/X]]", related: [...], tags: [...], created: "2026-04-09"}

final frontmatter: {
    up: "[[Atlas/Maps/X]]",       ← from rendered (new field)
    related: [...],               ← from rendered (updated)
    tags: [...],                  ← from rendered (updated)
    created: "2025-01-01",        ← PRESERVED from existing
    rank: "3",                    ← PRESERVED from existing
    mapState: "architect",        ← PRESERVED from existing
}
```

**Body handling:** On `update`, the body (everything after the closing `---`) is replaced with the rendered body. The assumption is that graphify owns the body of notes it created. User annotations should go in frontmatter fields that are in `preserve_fields`, or in a separate note that links to the graphify-generated note.

**MergeResult:** A simple enum (`CREATED`, `UPDATED`, `SKIPPED`, `REPLACED`) returned per note. The caller in `to_obsidian()` accumulates counts for a summary report.

---

## Module Structure

**New files to create:**

```
graphify/
    obsidian_profile.py     # ProfileLoader, DEFAULT_PROFILE, schema validation
    obsidian_mapper.py      # MappingEngine, NoteSpec, topology role detection
    obsidian_template.py    # TemplateEngine, built-in template strings
    obsidian_merge.py       # MergeEngine, frontmatter parsing, MergeResult
```

**Modified files:**

```
graphify/export.py          # to_obsidian() refactored to call the four new modules
                            # signature unchanged: G, communities, output_dir,
                            #   community_labels, cohesion
                            # new optional param: vault_profile_dir=None
tests/test_export.py        # existing tests continue passing (backward compat)
tests/test_obsidian_profile.py    # new
tests/test_obsidian_mapper.py     # new
tests/test_obsidian_template.py   # new
tests/test_obsidian_merge.py      # new
```

**Why not extend `export.py` directly:** The current `to_obsidian()` is 240 lines of interleaved logic. Adding profile loading, mapping rules, template rendering, and merge logic into the same function would make it untestable and unreadable. Four focused modules with their own test files follow the existing pattern (one module = one test file, each module under ~200 lines).

**Why `obsidian_` prefix:** There are already `wiki.py` and `export.py` in the package. Prefixing with `obsidian_` groups the new modules visually and avoids name collisions. Alternative (`vault_*.py`) is also acceptable but `obsidian_` is more specific.

---

## Profile Discovery: Default and Override

**Discovery sequence** (executed by `ProfileLoader`):

```
1. vault_profile_dir argument provided?
       YES → look for {vault_profile_dir}/.graphify/profile.yaml
       NO  → look for {output_dir}/.graphify/profile.yaml
             (assumes output_dir IS the target vault, which is the common case)

2. profile.yaml found?
       YES → load YAML, merge over DEFAULT_PROFILE
       NO  → use DEFAULT_PROFILE as-is (Ideaverse ACE structure)

3. templates/ found alongside profile.yaml?
       YES → load .md files from .graphify/templates/
       NO  → use built-in template strings from obsidian_template.py
```

**Built-in default profile** produces:
- Folders: `Atlas/Maps`, `Atlas/Dots/Things`, `Atlas/Dots/Statements`, `Atlas/Sources`
- Mapping: god nodes → `Dot/Thing`, papers → `Source`, everything else → `Dot/Thing`
- Merge: `update` strategy, preserve `["created"]`
- Community threshold: 5 members
- Dataview: enabled, graph colors: enabled

This is close enough to current `to_obsidian()` output that existing users see minimal change.

---

## Scalability Considerations

| Concern | Current (flat vault) | New (profile-driven) |
|---------|---------------------|---------------------|
| Node count | No limit in code; 5K node cap is HTML-only | Same; file I/O is the bottleneck |
| Template rendering | N/A | O(N nodes) string substitution — negligible |
| Merge overhead | N/A (always overwrites) | O(N nodes) file reads for exist check; acceptable |
| Profile loading | N/A | Once per run; O(1) |
| Mapping rules | N/A | O(rules × nodes); rules set is small (<20 typical) |

**Merge at scale:** For vaults with thousands of existing notes, the file-exist check (`Path.exists()`) is the bottleneck. Pre-scanning the vault directory once at MergeEngine initialization (building a `set` of existing filenames) reduces this to O(1) per note.

---

## Component Build Order (Dependency Sequence)

Each component can be built and tested independently. Build order driven by data dependencies:

```
Phase 1: ProfileLoader (obsidian_profile.py)
    - No dependencies on other new modules
    - Depends only on: stdlib pathlib, PyYAML (already in optional deps)
    - Test: unit tests with fixture YAML files in tmp_path
    - Deliverable: Profile dict with validated schema + defaults

Phase 2: TemplateEngine (obsidian_template.py)
    - No dependencies on other new modules
    - Depends only on: stdlib string ops, security.sanitize_label (existing)
    - Test: unit tests with string templates + context dicts
    - Deliverable: Rendered markdown strings with sanitized values

Phase 3: MappingEngine (obsidian_mapper.py)
    - Depends on: ProfileLoader (needs Profile to resolve folders)
    - Depends on: existing analyze.py output structure (god_nodes list)
    - Test: unit tests with small nx.Graph fixtures
    - Deliverable: NodeMap dict with NoteSpec per node

Phase 4: MergeEngine (obsidian_merge.py)
    - No dependencies on other new modules
    - Depends only on: stdlib pathlib, re
    - Test: unit tests with tmp_path, existing .md fixtures
    - Deliverable: File write with preserve-fields merge

Phase 5: Integration in export.py (to_obsidian refactor)
    - Depends on: all four modules above
    - Wires ProfileLoader → MappingEngine → TemplateEngine + MergeEngine per node
    - Existing tests (test_export.py) must pass unchanged
    - Deliverable: Full vault adapter replacing current to_obsidian()
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Embedding profile logic in export.py
**What:** Adding profile loading, rule evaluation, template substitution, and merge logic as nested functions or inline code inside `to_obsidian()`.
**Why bad:** Creates a 600-line function that is impossible to unit-test independently. The existing `to_obsidian()` at 240 lines is already at the boundary of readability.
**Instead:** Four focused modules, each testable in isolation.

### Anti-Pattern 2: Jinja2 or any new templating dependency
**What:** Using Jinja2 for template rendering.
**Why bad:** Adds a required dependency not in the current stack. The constraint is explicit: no new required dependencies.
**Instead:** `str.replace()` or `re.sub()` over `{{placeholder}}` markers. Sufficient for the use case.

### Anti-Pattern 3: Deep YAML merge or pydantic validation
**What:** Using `deepmerge`, `pydantic`, or `jsonschema` to validate/merge the profile.
**Why bad:** All three are new required dependencies. The profile schema is shallow enough that manual validation is straightforward.
**Instead:** Hand-written validation checks in `ProfileLoader._validate()`. Recursive `dict.update()` for merge.

### Anti-Pattern 4: Parsing existing Obsidian YAML with a full YAML parser
**What:** Using PyYAML to parse existing note frontmatter during merge.
**Why bad:** Obsidian frontmatter can contain complex YAML (multi-line strings, nested dicts) that round-trips incorrectly through PyYAML. Also, if vault notes have PyYAML-incompatible syntax, the merge engine would crash on them.
**Instead:** Line-by-line extraction of specific `preserve_fields` keys only. Unknown YAML in the frontmatter is preserved as a verbatim block.

### Anti-Pattern 5: Modifying analyze.py or cluster.py output
**What:** Adding vault-specific data (note types, folder assignments) to the graph itself or to analyze output.
**Why bad:** Violates pipeline isolation. Vault concerns do not belong in the graph data model.
**Instead:** MappingEngine takes the graph + communities + analysis as read-only inputs and produces a separate `NodeMap` dict.

---

## Sources

- Direct reading of `graphify/export.py` lines 440-679 (`to_obsidian()`)
- Direct reading of `graphify/build.py`, `graphify/cluster.py`, `graphify/analyze.py`
- Direct reading of `.planning/PROJECT.md` (milestone requirements and constraints)
- Direct reading of `.planning/codebase/ARCHITECTURE.md` (existing pipeline structure)
- Direct reading of `.planning/codebase/STRUCTURE.md` (module conventions, where to add code)

*All findings HIGH confidence — based on direct codebase analysis, not external sources.*
