# Vault profile configuration guide

This guide explains how to configure graphify’s Obsidian vault adapter using `.graphify/profile.yaml`. It complements the canonical example file [`profile-example.yaml`](../profile-example.yaml) at the repository root, which mirrors the built-in defaults from `graphify/profile.py` (`_DEFAULT_PROFILE`).

## Where the profile lives

- **Path:** `<your-vault>/.graphify/profile.yaml`
- **Dependencies:** PyYAML (install graphify with the `obsidian` extra, e.g. `pip install "graphifyy[obsidian]"` or `pip install -e ".[mcp,pdf,watch]"` as in `CLAUDE.md`).

If that file is missing, graphify uses the **built-in default profile** only (no user file to validate). If `profile.yaml` **exists** but fails validation or resolution, graphify prints errors to stderr and **falls back** to the same built-in defaults.

## Quick start

1. Copy [`profile-example.yaml`](../profile-example.yaml) to your vault as `.graphify/profile.yaml`.
2. Edit `taxonomy`, `folder_mapping`, and any other sections you need (see below).
3. Validate:

   ```bash
   graphify --validate-profile /path/to/your/vault
   ```

4. Preview an export (no writes, or merge-plan only, depending on your workflow):

   ```bash
   graphify --obsidian --obsidian-dir /path/to/your/vault --dry-run
   ```

For v1.8 migration workflows, see [`MIGRATION_V1_8.md`](MIGRATION_V1_8.md). For Excalidraw diagram seeds, templates, and MCP tools, see [`CONFIGURING_V1_5.md`](CONFIGURING_V1_5.md).

## How profiles are loaded and merged

1. **Composition (optional):** If your `profile.yaml` uses `extends:` or `includes:`, graphify resolves a **chain** of YAML fragments under `.graphify/` (sibling-relative paths, max depth 8, no cycles). Order per file: `extends` parent → `includes` (left to right) → **this file’s keys win**.
2. **Merge with defaults:** The composed user profile is **deep-merged** over graphify’s built-in `_DEFAULT_PROFILE`. User keys override at the leaf level.
3. **Taxonomy → folders:** If `taxonomy` is present, graphify recomputes `folder_mapping` entries from `taxonomy.root` + `taxonomy.folders` (see [Taxonomy](#taxonomy)). Explicit `folder_mapping` in the merged profile can still set final paths; the example file sets both for clarity.
4. **v1.8 user file requirements:** When a user authorship chain is successfully loaded, the **composed** profile (before default merge) must include:
   - top-level `taxonomy`
   - `mapping.min_community_size`

The repository [`profile-example.yaml`](../profile-example.yaml) satisfies these requirements.

## Top-level keys (reference)

Allowed top-level keys are enforced by schema validation. Unknown keys cause validation errors.

| Key | Purpose |
|-----|--------|
| `taxonomy` | v1.8 namespace: version, root path, and per–note-type folder names (drives `folder_mapping` when applied). |
| `folder_mapping` | Vault-relative **directories** (trailing `/` recommended) for each note role: `moc`, `thing`, `statement`, `person`, `source`, `default`. |
| `repo` | Optional monorepo identity: `identity` string (no path segments or `..`). |
| `naming` | Filename and label conventions; optional `concept_names` for concept nodes. |
| `merge` | How exported notes merge with existing files: strategy, preserved frontmatter fields, per-field policies. |
| `mapping_rules` | Ordered list of `when` / `then` rules to assign `note_type` and optional `folder` overrides. |
| `obsidian` | Obsidian-specific settings (e.g. `atlas_root`, embedded Dataview for MOCs). |
| `dataview_queries` | Per–note-type Dataview query strings (overrides / extends template behavior). |
| `topology` | Graph metrics (e.g. god-node `top_n`). |
| `mapping` | Community gating: `min_community_size` (required in v1.8 user files; replaces legacy `moc_threshold`). |
| `tag_taxonomy` | Namespaces of tags used for generated metadata (e.g. `garden`, `graph`, `source`, `tech`). |
| `profile_sync` | e.g. `auto_update` for profile-related sync behavior. |
| `diagram_types` | Excalidraw / diagram seed configuration (see `CONFIGURING_V1_5.md`). |
| `output` | Optional redirect of export output: `mode` + `path`, optional `exclude` globs. |
| `extends` | Single string: path to another fragment under `.graphify/` (parent profile). |
| `includes` | List of strings: additional fragments merged left-to-right before own keys. |
| `community_templates` | Rules matching communities by `label` or `id` to pick a custom template file under `.graphify/`. |
| `mapping_rule_templates` | Rules matching `mapping_rules[].id` to pick a custom template file under `.graphify/` (Phase 56). |
| `note_type_templates` | Rules matching a known `note_type` to pick a custom template file under `.graphify/` (Phase 56). |

---

## Taxonomy

The `taxonomy` block groups all generated notes under a logical tree.

From [`profile-example.yaml`](../profile-example.yaml):

```yaml
taxonomy:
  version: v1.8
  root: Atlas/Sources/Graphify
  folders:
    moc: MOCs
    thing: Things
    statement: Statements
    person: People
    source: Sources
    default: Things
    unclassified: MOCs
```

| Field | Meaning |
|-------|--------|
| `version` | Must be `v1.8` when present (schema validation). |
| `root` | Vault-relative base path; must not be absolute, use `..`, or start with `~`. |
| `folders` | Short names joined with `root` to build full folder paths. Keys: `moc`, `thing`, `statement`, `person`, `source`, `default`, `unclassified`. Each folder value must be a safe relative path segment (same rules as `root`). |

The `unclassified` folder key participates in taxonomy metadata; the primary export folders are the others.

---

## `folder_mapping`

Maps **note roles** to vault-relative directories where notes are written.

Example (from [`profile-example.yaml`](../profile-example.yaml)):

```yaml
folder_mapping:
  moc: Atlas/Sources/Graphify/MOCs/
  thing: Atlas/Sources/Graphify/Things/
  statement: Atlas/Sources/Graphify/Statements/
  person: Atlas/Sources/Graphify/People/
  source: Atlas/Sources/Graphify/Sources/
  default: Atlas/Sources/Graphify/Things/
```

Rules enforced by validation:

- Paths must be **relative** to the vault (no absolute paths, no `~`, no `..` in components).

If both `taxonomy` and explicit `folder_mapping` are set, resolve overlaps by remembering that taxonomy application runs in the loader and may rewrite `folder_mapping` from `taxonomy.folders`.

---

## `repo`

Optional stable identity for the analyzed repository in monorepo or multi-root setups:

```yaml
repo:
  identity: my-repo-slug
```

Only `identity` is allowed under `repo`. It must be a non-empty string without `/`, `\`, or `..` (normalized via `normalize_repo_identity`).

---

## `naming`

Controls how file names are derived from labels.

| Field | Values / notes |
|-------|----------------|
| `convention` | `title_case`, `kebab-case`, or `preserve`. |
| `concept_names` | Optional object: `enabled` (bool), `budget` (non-negative number), `style` (short string, e.g. `readable`). |

Do **not** put repository identity under `naming`; use `repo.identity`.

---

## `merge`

Controls how graphify updates notes that already exist in the vault.

| Field | Meaning |
|-------|--------|
| `strategy` | `update` (merge/preserve user fields where configured), `skip` (do not overwrite existing), or `replace` (overwrite). |
| `preserve_fields` | List of frontmatter field names graphify should not clobber on update (e.g. `rank`, `mapState`, `tags`, `created`). |
| `field_policies` | Map of field name → `replace`, `union`, or `preserve` for finer-grained list/scalar merge behavior. |

---

## `mapping_rules`

A **list** of rules evaluated in order. Each rule has:

- `when`: exactly **one** matcher kind among:
  - **`attr`**: match a graph node attribute with **one** of `equals`, `in`, `contains`, `regex` (regex uses full match; patterns length-capped for safety).
  - **`topology`**: `god_node`, `is_source_file`, `community_size_gte`, `community_size_lt`, or `cohesion_gte` (with `value` as required).
  - **`source_file_ext`**: string like `.py` or list of extensions.
  - **`source_file_matches`**: regex matched against the node’s `source_file`.
- `then`:
  - **`note_type`** (required): one of `moc`, `community`, `thing`, `statement`, `person`, `source`, `code`.
  - **`folder`** (optional): vault-relative folder override; same path safety as `folder_mapping`.

Only `note_type` and `folder` are allowed under `then`. Earlier rules can shadow later ones; validation may emit **warnings** for structurally dead rules.

Example (illustrative only):

```yaml
mapping_rules:
  - when:
      attr: file_type
      equals: person
    then:
      note_type: person
      folder: Atlas/Dots/People/
  - when:
      topology: god_node
    then:
      note_type: thing
```

---

## `obsidian`

Obsidian- and Atlas-oriented settings.

From the example file:

```yaml
obsidian:
  atlas_root: Atlas
  dataview:
    moc_query: |-
      TABLE file.folder as Folder, type, source_file
      FROM #community/${community_tag}
      SORT file.name ASC
```

- **`atlas_root`:** Prefix for Atlas-style layouts.
- **`dataview.moc_query`:** Dataview snippet embedded in MOC/community notes. Supports placeholders such as `${community_tag}` (expanded at render time).

---

## `dataview_queries`

Overrides Dataview blocks **per note type** without changing the whole `moc_query`. Keys must be one of: `moc`, `community`, `thing`, `statement`, `person`, `source`, `code`. Values are non-empty strings (the query text).

Example:

```yaml
dataview_queries:
  moc: "TABLE file.name, type FROM #community/${community_tag}"
  thing: "LIST FROM #community/${community_tag} WHERE type = 'thing'"
```

---

## `topology`

```yaml
topology:
  god_node:
    top_n: 10
```

`topology.god_node.top_n` is a non-negative integer controlling how many top hub nodes are treated as god nodes for analysis/export signals.

---

## `mapping`

```yaml
mapping:
  min_community_size: 6
```

- **`min_community_size`:** Integer ≥ 1. Communities smaller than this threshold are handled according to the mapping engine (reduces noise from tiny clusters). **Required** in v1.8 **user-authored** profiles.
- **`moc_threshold`** is **not** supported; use `min_community_size` only.

---

## `tag_taxonomy`

Namespaces mapping to lists of allowed tag suffixes (or tag components) for structured tagging in generated notes. The example file defines `garden`, `graph`, `source`, and `tech` lists—customize to match your vault’s tagging scheme.

---

## `profile_sync`

```yaml
profile_sync:
  auto_update: true
```

Optional automation preferences (e.g. whether graphify may refresh profile-derived artifacts). `auto_update` must be a boolean when present.

---

## `diagram_types`

Each entry describes a **diagram type** for seeds / Excalidraw (template path, triggers, naming, layout, output folder). See [`profile-example.yaml`](../profile-example.yaml) for six built-in types (`architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`) and [`CONFIGURING_V1_5.md`](CONFIGURING_V1_5.md) for the full pipeline.

Per-entry keys validated include: `name`, `template_path`, `trigger_node_types`, `trigger_tags`, `min_main_nodes`, `naming_pattern`, `layout_type`, `output_path`.

---

## `output` (optional)

Redirects where structured export writes relative to the vault or filesystem:

- **`mode`:** `vault-relative`, `absolute`, or `sibling-of-vault` (the latter is further validated at runtime).
- **`path`:** Must match the mode (e.g. relative for `vault-relative`, absolute for `absolute`).
- **`exclude`:** Optional list of vault-relative path patterns to exclude; each entry must be a non-empty relative string without `..` or absolute roots.

---

## Composition: `extends` and `includes`

- **`extends`:** A single string path (relative to the current file’s directory) to a **parent** fragment. Loaded first; then `includes`; then the current file’s keys override.
- **`includes`:** A list of paths (same resolution rules), merged in order; later fragments override earlier ones; the hosting file overrides all.

All paths must stay inside `.graphify/` after resolution. Depth and cycles are limited so broken configs fail fast with clear errors.

---

## `community_templates`

A list of rules to pick **custom markdown templates** for specific communities:

| Field | Meaning |
|-------|--------|
| `match` | `label` or `id`. |
| `pattern` | If `match` is `label`, a string pattern; if `id`, an integer community id. |
| `template` | Path **relative to `.graphify/`** (non-empty, no `..`, not absolute). |

---

## `mapping_rules[].id` (optional)

Phase 56 adds an optional `id:` field to each entry in `mapping_rules:`. The `id:` makes the rule **referenceable** from `mapping_rule_templates:` (below). Rules without `id:` continue to work exactly as before — they just cannot be targeted by a per-rule template override.

Validation rules (enforced at `graphify --validate-profile`):

| Constraint | Rule |
|------------|------|
| Type | string (when present). |
| Slug pattern | `^[a-z][a-z0-9_-]*$` — lowercase ASCII, digits, `_`, `-`; first char must be a letter. |
| Length | ≤ 80 characters. |
| Uniqueness | The `id:` value must be unique across the entire `mapping_rules:` list. Duplicate ids are a preflight error citing both colliding indices. |
| Backward compatibility | Optional. Existing profiles without any `id:` fields remain valid; opt in only when you intend to override that rule's template. |

Example:

```yaml
mapping_rules:
  - id: person-from-attr
    when:
      attr: file_type
      equals: person
    then:
      note_type: person
      folder: Atlas/Dots/People/
  - id: god-node-thing
    when:
      topology: god_node
    then:
      note_type: thing
  # Rules without id: still valid — just un-targetable from mapping_rule_templates:
  - when:
      source_file_ext: .py
    then:
      note_type: code
```

---

## `mapping_rule_templates`

A list of rules selecting a custom template **per matching `mapping_rules[].id`**. Each entry is a `{match, pattern, template}` mapping mirroring `community_templates:`:

| Field | Meaning |
|-------|--------|
| `match` | Must be the literal string `rule_id` (the only allowed match kind in v1.11). |
| `pattern` | The slug of a `mapping_rules[].id` declared elsewhere in the profile. Must match the slug regex `^[a-z][a-z0-9_-]*$`. |
| `template` | Path **relative to `.graphify/`** (non-empty, no `..`, not absolute, no leading `~`). |

Path-confinement is enforced at preflight (substring `..`, absolute paths, and `~` prefixes are rejected). At render time, a missing or unreadable override file falls back to the base note-type template and emits a single stderr warning (Phase 55 D-55.14 contract).

Example:

```yaml
mapping_rules:
  - id: service-class
    when:
      attr: kind
      equals: service_class
    then:
      note_type: thing

mapping_rule_templates:
  - match: rule_id
    pattern: service-class
    template: templates/service-class.md
```

---

## `note_type_templates`

A list of rules selecting a custom template **per matching `note_type`**. Each entry is a `{match, pattern, template}` mapping with the same shape as the two sibling lists:

| Field | Meaning |
|-------|--------|
| `match` | Must be the literal string `note_type`. |
| `pattern` | One of the known note types: `code`, `community`, `moc`, `person`, `source`, `statement`, `thing`. |
| `template` | Path **relative to `.graphify/`** (non-empty, no `..`, not absolute, no leading `~`). |

Same path-confinement rules apply at preflight, and the same warn-and-fall-back contract applies at render time.

Example:

```yaml
note_type_templates:
  - match: note_type
    pattern: code
    template: templates/code-rich.md
  - match: note_type
    pattern: person
    template: templates/person-card.md
```

---

## How overrides resolve (precedence ladder)

When more than one override list could supply a template for the same node, graphify picks the **most specific** scope using this strict precedence ladder (Phase 56 D-56.05). Selection happens at render time inside `_resolve_note_template`:

1. **`mapping_rule_templates`** — wins if the node was classified by a `mapping_rules[]` entry that carries an `id:`, **and** a `mapping_rule_templates:` entry has `pattern:` equal to that id.
2. **`community_templates`** — wins if the node's community matches a `community_templates:` entry (by `label` or `id`).
3. **`note_type_templates`** — wins if the node's resolved `note_type` matches a `note_type_templates:` entry's `pattern`.
4. **Base profile template** for the note type (built-in or `.graphify/templates/<note_type>.md`).

Most-specific scope wins. **Cross-scope overlaps resolve silently** via this ladder — for example, a node that matches both a `mapping_rule_templates:` entry and a `note_type_templates:` entry simply uses the mapping-rule template; no warning is emitted, no error is raised. This is intentional design: authors edit the most-specific override knowing it always wins, and broad defaults stay safe.

**Within a single list,** first-matching-rule wins. This only matters when patterns overlap inside one list (intra-list pattern overlap is **not** detected at preflight — see the next subsection).

---

## Override collision validation

Phase 56 adds **schema-only collision detection** at `validate_profile_preflight` time (D-56.06). Four collision classes raise deterministic preflight errors that cite the offending indices and contributing source paths:

| Class | Where | Detected by | Error shape |
|-------|-------|-------------|-------------|
| 1. Duplicate `pattern` (rule_id) within `mapping_rule_templates` | `_detect_mapping_rule_template_collisions` | Two entries with the same `pattern` slug. | `mapping_rule_templates[<idx>]: duplicate pattern '<id>' — also defined at mapping_rule_templates[<other_idx>]` |
| 2. Duplicate exact `pattern` within a sibling list | `_detect_sibling_list_pattern_collisions` (per-list independent) | Same `pattern` string repeated within `community_templates`, `mapping_rule_templates`, or `note_type_templates`. | `<list>[<idx>]: duplicate pattern <p!r> — also defined at <list>[<other_idx>]` |
| 3. Duplicate `pattern` (= note_type) within `note_type_templates` | `_detect_note_type_template_collisions` | Two entries targeting the same `_KNOWN_NOTE_TYPES` value. | `note_type_templates[<idx>]: duplicate pattern '<note_type>' — also defined at note_type_templates[<other_idx>]` |
| 4. Cross-chain duplicate `dataview_queries.<note_type>` | Provenance-aware composition chain check | Composing `extends:`/`includes:` produces conflicting values for the same `dataview_queries.<note_type>` key from different source files. | Error enumerates **all** contributing source paths via the `_deep_merge_with_provenance` map. |

> **Pattern overlap is intentionally NOT detected.** Detecting that two patterns *could* match the same node (e.g., `Auth*` vs `AuthService` in `community_templates:`, or two regex-style patterns covering overlapping label sets) is undecidable in the general case. Render-time list-order resolution applies — first matching rule in list order wins. If you need deterministic ordering, structure your patterns from most-specific to least-specific.

---

## Worked example: all three override lists for one note

Consider a single conceptual note for a class named `AuthService` that:

- is classified by a mapping rule with `id: service-class` (because its `kind` attribute equals `service_class`),
- belongs to community `Authentication`,
- has resolved `note_type: thing`.

The profile below registers an override at every scope:

```yaml
mapping_rules:
  - id: service-class
    when:
      attr: kind
      equals: service_class
    then:
      note_type: thing

community_templates:
  - match: label
    pattern: Authentication
    template: templates/community-authentication.md

note_type_templates:
  - match: note_type
    pattern: thing
    template: templates/thing-rich.md

mapping_rule_templates:
  - match: rule_id
    pattern: service-class
    template: templates/service-class.md
```

Render-time resolution walks the ladder top-down:

| Step | List checked | Match? | Outcome |
|------|--------------|--------|---------|
| 1 | `mapping_rule_templates` | Yes — node classified by `service-class`. | **Wins:** loads `.graphify/templates/service-class.md`. |
| 2 | `community_templates` | (Skipped — already resolved.) | — |
| 3 | `note_type_templates` | (Skipped — already resolved.) | — |
| 4 | Base `thing` template | (Skipped — already resolved.) | — |

Resolved template path: `.graphify/templates/service-class.md`.

If you delete the `mapping_rule_templates:` entry, step 1 misses and the ladder advances to step 2; `community_templates` matches `Authentication`, so the resolved template becomes `.graphify/templates/community-authentication.md`. Delete that too and step 3 wins (`templates/thing-rich.md`). Delete that and step 4 wins (the built-in `thing` template, or any file at `.graphify/templates/thing.md`).

If any selected override file is missing or unreadable at render time, graphify emits a single stderr warning and falls back to the base note-type template (D-56.13).

---

## Custom templates (files)

Beyond YAML, you can place overrides under `.graphify/templates/` (e.g. `thing.md`, `moc.md`) using `${placeholder}` style substitution. Preflight validation counts and checks these templates when you run `graphify --validate-profile`.

For conditional blocks (`{{#if_…}}`) and connection loops (`{{#connections}}`), see [`docs/TEMPLATES.md`](TEMPLATES.md).

---

## Validation and troubleshooting

1. Run **`graphify --validate-profile <vault>`** — exercises schema, template, and path-safety layers.
2. Watch **stderr** when running exports: profile resolution errors cause an automatic fallback to built-in defaults, which can **look** like “graphify ignored my profile”—fix validation errors until the command is clean.
3. Ensure **`taxonomy`** and **`mapping.min_community_size`** exist in the **composed** user profile for v1.8 (see [`profile-example.yaml`](../profile-example.yaml)).

---

## Related files

| File | Role |
|------|------|
| [`profile-example.yaml`](../profile-example.yaml) | Copy-paste baseline aligned with `_DEFAULT_PROFILE`. |
| [`MIGRATION_V1_8.md`](MIGRATION_V1_8.md) | Reviewed vault updates and apply flow. |
| [`CONFIGURING_V1_5.md`](CONFIGURING_V1_5.md) | Diagram seeds, Excalidraw templates, MCP. |
| `graphify/profile.py` | Defaults, merge, validation, safety helpers. |
| `graphify/mapping.py` | `mapping_rules` matchers and `validate_rules`. |
