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

## Custom templates (files)

Beyond YAML, you can place overrides under `.graphify/templates/` (e.g. `thing.md`, `moc.md`) using `${placeholder}` style substitution. Preflight validation counts and checks these templates when you run `graphify --validate-profile`.

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
