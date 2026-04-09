# Feature Landscape: Configurable Obsidian Vault Adapter

**Domain:** Knowledge-graph-to-Obsidian-vault injection adapter
**Researched:** 2026-04-09
**Confidence:** MEDIUM — based on deep ecosystem analysis (Ideaverse Pro 2.5, Templater, QuickAdd, Obsidian Linter, Dataview, community patterns) and codebase audit. No live web access; training cutoff August 2025.

---

## Baseline: What graphify Already Produces

The existing `to_obsidian()` in `export.py` (lines 440–679) writes:
- One flat `.md` file per node with YAML frontmatter (`source_file`, `type`, `community`, `tags`)
- Inline `[[wikilinks]]` under a `## Connections` section with relation type + confidence
- One `_COMMUNITY_name.md` per community with members list, inter-community edges, bridge nodes, and a single Dataview query by tag
- `.obsidian/graph.json` colorGroups by community tag

This is the baseline the adapter must match (no-profile fallback) and surpass (with profile).

---

## Table Stakes

Features users expect from any knowledge-to-vault tool. Missing = product feels incomplete or broken compared to tools like Juggl, Smart Connections, Obsidian Importer, or hand-rolled exporters.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| YAML frontmatter with standard Obsidian fields | Every serious vault tool writes frontmatter; Obsidian's Properties panel reads it natively | Low | Must include `tags:` as YAML list. `created:` date is standard. Field names must be configurable (Ideaverse uses `up:`, `related:`, `collections:`; others use `parent:`, `links:`) |
| `[[wikilink]]` generation with deduplication | Obsidian graph is built entirely on wikilinks; without them, vault is just files | Low | Must handle label sanitization (Obsidian forbids `\/*?:"<>|#^[]`). Already exists in `safe_name()` but must be vault-path-aware |
| Folder placement for generated notes | Notes dumped at vault root are disorganized; users expect folder structure matching their framework | Medium | Fixed-path config per note type (MOC → `Atlas/Maps/`, Dot → `Atlas/Dots/Things/`, Source → `Atlas/Sources/`) is the minimum. Dynamic routing is differentiating. |
| Note-type classification | Users need to know what kind of note each generated file is (MOC, atomic note, source, etc.) | Medium | Minimum: topology-based (community overview → MOC, high-degree node → Dot/Thing, origin file → Source). Attribute-based routing is differentiating. |
| Update/merge strategy for existing notes | Re-running graphify must not destroy user edits; overwrite-everything is a dealbreaker | High | Minimum: detect existing file, update frontmatter fields from graphify, preserve body user edits. "Replace" mode also needed for CI/automated use. |
| Naming convention compliance | Notes named `node_42.md` are useless; names must match vault conventions | Low | Strip special chars, handle duplicates with suffix, support configurable casing (title case, kebab-case, snake_case). Already partially done in `safe_name()`. |
| Profile directory convention (`.graphify/`) | Users need a way to declare vault configuration without editing graphify source | Medium | `profile.yaml` at `.graphify/profile.yaml` in the target vault root. Mirrors `.obsidian/`, `.editorconfig` conventions. Absent = built-in default profile (Ideaverse ACE). |
| `profile.yaml` schema with folder mapping | The core configuration primitive: map graphify node types to vault folders and note templates | Medium | Minimum fields: `folder_mapping`, `merge`, `naming`. Must be validated with clear error messages on bad YAML. |
| Built-in default profile (no-config fallback) | If no `.graphify/` exists, output should still be sensible (backwards compat contract) | Low | Default = Ideaverse ACE structure (Atlas/Maps, Atlas/Dots, Atlas/Sources). Identical behavior to current `to_obsidian()` for users with no profile. |
| Template-based note generation | Users must be able to control what ends up in each note section (frontmatter fields, body structure) | High | Templates in `.graphify/templates/` as `.md` files with `{{placeholder}}` syntax. One template per note type (moc.md, dot.md, source.md, community.md). |
| Wikilink format variants | Obsidian supports `[[Note Name]]`, `[[Note Name\|Alias]]`, `[[folder/Note Name]]`; frameworks differ | Low | Configurable in `profile.yaml`: `wikilink_format: bare | aliased | path-qualified`. Ideaverse uses bare by default. |
| Path sanitization and security | Generated file paths must stay inside the vault directory; path traversal via node labels is a real risk | Low | Already flagged as a concern in CONCERNS.md (lines 144–148). Must use `pathlib.Path.resolve()` and reject separators in labels before path construction. |

---

## Differentiators

Features that set this adapter apart from flat exporters and generic vault generators. Not universally expected, but valued by serious framework users.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dual mapping rules (topology + attributes) | Lets profile authors say "if god_node → use Thing template" AND "if file_type==person → use Person template"; covers both structural and semantic classification | High | `mapping_rules:` list in profile.yaml with `if:` conditions and `then:` assignments. Rule priority: attribute rules > topology rules > default. Condition keys: `is_god_node`, `is_bridge`, `file_type`, `community_size_min/max`, custom node attributes. |
| Community-to-MOC mapping with threshold | Communities above a configurable member threshold become MOCs with Dataview queries, smaller ones become atomic notes or are absorbed | Medium | `moc_threshold: 5` in profile. Communities below threshold collapse to a simple list note or are omitted. Prevents MOC explosion on fine-grained graphs. |
| Embedded Dataview queries in MOC notes | MOC notes with live Dataview queries are far more useful than static member lists; they auto-update as vault grows | Medium | Query template is configurable (tag-based or folder-based query). Configurable on/off per profile. Already exists for community notes; needs to work for MOC notes generally. |
| Frontmatter field preservation on update | On re-run, user-added frontmatter fields (e.g., `rank:`, `status:`, `alias:`) are preserved; only graphify-owned fields are refreshed | High | Requires parsing existing YAML frontmatter, merging strategy: graphify fields overwrite, user fields are kept. `merge.preserve_fields:` list in profile.yaml. |
| `graph.json` community color generation | Colors community groups in Obsidian's native graph view; the one feature that makes the graph immediately legible | Low | Already in current `to_obsidian()`. Needs to be profile-configurable: `obsidian_config.community_colors: true/false` and support custom color palettes in profile. |
| Source-to-Source-note mapping | Origin files (code files, papers, documents) become Source notes in a dedicated folder, linking to the concepts they define | Medium | `source_node_type: Source` in mapping rules. Ideaverse's `Atlas/Sources/{Books,Movies,Code,Papers}` folder. Sub-folder routing by `file_type`. |
| Wayfinder note generation | A top-level navigation note (HOME, Dashboard, or per-community wayfinder) that links all MOCs and god nodes; essential for large vaults | Medium | Configurable: `wayfinder: true/false` and `wayfinder_template:`. One wayfinder per community or one global. Ideaverse calls these "wayfinders" linking Maps. |
| Configurable naming conventions | Convert node labels to vault naming conventions: Title Case (Ideaverse), kebab-case (Zettelkasten), snake_case (developer vaults) | Low | `naming.case: title | kebab | snake | preserve` in profile.yaml. |
| Template placeholder sanitization | Placeholders populated from node labels/attributes must be HTML-escaped and length-capped to prevent injection into markdown metadata | Low | Required by security posture. Uses `security.sanitize_label()` before any `{{placeholder}}` substitution. |
| Template loop support for connections | Body templates need a way to render a list of connections (e.g., `{{#connections}}[[{{target}}]] — {{relation}}{{/connections}}`); without it, connection lists can't be templated | High | Minimal Mustache-style block: `{{#key}}...{{/key}}` for list iteration. Only for known list placeholders (connections, members, sources). No full Jinja2 — avoids new dependency. |
| Conditional template sections | Some note types have optional sections (e.g., god node callout box only when `is_god_node=true`); without conditionals, templates produce cluttered output | Medium | `{{#if_god_node}}...{{/if_god_node}}` guards on known boolean flags. Keep whitelist-only: no arbitrary expression evaluation. |
| Obsidian Linter-compatible frontmatter | Generated frontmatter must be sorted and formatted to survive Obsidian Linter's auto-format without diff noise | Low | Follow Linter's default sort order: `aliases`, `tags`, then alphabetical. Emit clean YAML (no trailing spaces, consistent quoting). |
| Profile validation with actionable errors | Bad `profile.yaml` (missing required fields, unknown note types, bad YAML) must fail loudly with line numbers, not silently produce broken vaults | Low | Use PyYAML's `safe_load()` + schema check against a dataclass or TypedDict. Error format: `profile.yaml line N: unknown field 'foldr_mapping'` |
| `--dry-run` mode | Preview what files would be written/updated without touching the vault; essential for first-time users and CI validation | Low | Print a summary: `would create: Atlas/Maps/ML Community.md`, `would update: Atlas/Dots/Things/Transformer.md (2 fields)`. |

---

## Anti-Features

Features to explicitly NOT build in this milestone. These either belong to a different project, create unacceptable complexity, or violate the stated constraints.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Jinja2 / full template engine | Adds a new required dependency; templates become non-readable as plain markdown; most use cases covered by simple `{{placeholder}}` + `{{#block}}` | Keep stdlib string substitution + minimal Mustache-style loops. Re-evaluate if user demand proves overwhelming. |
| Vault framework generation | Designing the ACE/Sefirot/Guitton folder hierarchy is a separate project (explicitly out of scope in PROJECT.md); graphify consumes a profile, doesn't design the vault | Profile declares what already exists; graphify writes into it. |
| Calendar and Efforts population | Time/action data doesn't come from graphify's graph (concepts only); injecting into Daily Notes or Efforts is a different data source problem | Noted explicitly out of scope in PROJECT.md. |
| Real-time sync / watch mode | Batch injection on demand is the right model; watch mode ties graphify's file watcher to Obsidian's sync, creating race conditions | Use existing `watch.py` for code re-extraction; Obsidian injection remains a manual or CI-triggered batch operation. |
| Obsidian plugin development | Graphify produces standard markdown + frontmatter that any Obsidian installation reads without plugins; a plugin creates a maintenance burden | Generate Dataview queries instead of custom plugin views. |
| Two-way sync (read vault edits back into graph) | Would require a parser for arbitrary user-edited markdown, conflict resolution, and domain-specific diff logic; scope explosion | Write-only injection. If users edit generated notes, merge strategy preserves their edits on next run. |
| Arbitrary Python/JS in templates | Template execution with user-supplied code is an RCE vector; the profile is vault-owned and could be adversarially crafted | Whitelist-only placeholder substitution. No `eval()`, no subprocess. |
| Neo4j / other export formats | This milestone is Obsidian-specific; other formats already exist and are out of scope | Existing `to_cypher()` / `push_to_neo4j()` are untouched. |
| Wiki article generation integration | `wiki.py` is a separate system (Wikipedia-style articles per community). It is not being folded into this adapter. | Keep `to_wiki()` and `to_obsidian()` as separate code paths with separate CLI flags. |
| Per-node `--include` / `--exclude` filters | Filtering which nodes to inject is a graph query problem, not a vault adapter problem | Users filter at the `graphify query` stage before passing the graph to export. |

---

## Feature Dependencies

```
profile.yaml parsing → everything else
  └── folder_mapping          → note placement
  └── mapping_rules           → note type classification
       └── topology rules      → requires: god_node data, community data (from analyze())
       └── attribute rules     → requires: node attributes (file_type, custom attrs)
  └── merge strategy           → update/skip/replace logic
       └── frontmatter parsing → requires: reading existing vault notes
       └── field preservation  → requires: knowing which fields are user-owned
  └── naming.case              → note filename generation
  └── wikilink_format          → link rendering in templates
  └── obsidian_config          → graph.json color generation

templates/*.md → note content generation
  └── {{placeholder}} substitution → requires: sanitize_label() from security.py
  └── {{#block}} loops         → requires: connections list, members list
  └── {{#if_*}} conditionals   → requires: classification flags from mapping_rules

moc_threshold                  → community-to-MOC vs. community-to-list decision
  └── dataview query embedding  → only when community becomes MOC
  └── wayfinder generation      → links only MOC-tier communities

graph.json generation          → requires: community labels + color palette
  └── community color config   → requires: profile.yaml obsidian_config section

--dry-run                      → wraps all write calls; no additional data deps
profile validation             → runs before any write; fails fast on bad schema
```

---

## MVP Recommendation

For the initial implementation, prioritize these to reach a usable milestone:

**Must build (MVP):**
1. Profile loader: read `.graphify/profile.yaml`, fall back to built-in default. Fail loudly on bad YAML.
2. `profile.yaml` schema (dataclass or TypedDict): `folder_mapping`, `merge`, `naming`, `wikilink_format`, `obsidian_config`, `moc_threshold`.
3. Topology-only mapping rules: `is_god_node`, `is_community_hub`, `is_source_file` → note type. (Attribute rules are differentiating but add significant complexity.)
4. Template loading from `.graphify/templates/` with simple `{{placeholder}}` substitution + `{{#connections}}` loop.
5. Folder-aware file writing: create intermediate directories, respect `folder_mapping` per note type.
6. Update strategy with field preservation: parse existing YAML frontmatter, merge, rewrite.
7. `--dry-run` flag: print plan without writing.
8. `graph.json` color generation (configurable on/off).

**Defer (post-MVP):**
- Attribute-based mapping rules (increases classification power but requires rule engine)
- Conditional template sections (`{{#if_god_node}}`)
- Wayfinder generation (useful but not blocking)
- Dataview query customization (current hardcoded query works as default)
- Custom color palettes in profile
- `--dry-run` diff output (summary is enough for MVP)

**Minimum viable profile.yaml:**
```yaml
# .graphify/profile.yaml (minimum viable)
folder_mapping:
  moc: "Atlas/Maps"
  dot_thing: "Atlas/Dots/Things"
  dot_person: "Atlas/Dots/People"
  source: "Atlas/Sources"
  community: "Atlas/Maps"

moc_threshold: 5

merge:
  strategy: update        # update | skip | replace
  preserve_fields:
    - rank
    - status
    - aliases

naming:
  case: title             # title | kebab | snake | preserve

wikilink_format: bare     # bare | aliased | path-qualified

obsidian_config:
  community_colors: true
```

---

## Sources

- graphify codebase audit: `graphify/export.py` lines 440–679, `graphify/wiki.py`, `graphify/security.py`
- PROJECT.md (milestone requirements and constraints)
- codebase/CONCERNS.md (path sanitization concern, Obsidian export fragile areas)
- Ecosystem knowledge: Obsidian Templater (uses `<% %>` syntax, TP.* namespace), QuickAdd (uses `{{VALUE}}` prompts), Obsidian Linter (YAML sort order), Dataview plugin (TABLE/LIST queries by tag or folder), Ideaverse Pro 2.5 frontmatter schema (`up:`, `related:`, `collections:`, `rank:`, `mapState:`)
- Confidence for ecosystem patterns: MEDIUM (training data, not live-verified due to tool access restrictions)
