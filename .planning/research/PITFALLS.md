# Domain Pitfalls: Configurable Obsidian Vault Adapter

**Domain:** Obsidian vault generation / knowledge graph injection into existing vaults
**Researched:** 2026-04-09
**Confidence:** HIGH (based on YAML spec, Obsidian docs behavior, and analysis of existing export.py)

---

## Critical Pitfalls

These mistakes cause data loss, vault corruption, or silent breakage that is hard to detect.

---

### Pitfall 1: YAML Frontmatter — Unquoted Special Characters Break the Vault Note

**What goes wrong:**
Node labels containing `:`, `#`, `[`, `]`, `{`, `}`, `>`, `|`, `*`, `&`, or `!` are written directly into YAML frontmatter values without quoting, producing malformed YAML. Obsidian silently drops the entire frontmatter block for that note. The note renders without properties; Dataview queries return nothing; the graph view loses color groupings.

**Why it happens:**
The existing `export.py` writes frontmatter lines as bare f-strings:
```python
f'source_file: "{data.get("source_file", "")}"'
```
This double-quotes source_file but the value itself can still contain `"` characters, causing YAML parse failure. Labels used in tag values (e.g., `community/{name}`) are not quoted and not sanitized for YAML-invalid chars.

**Consequences:**
- Obsidian Properties panel shows "Invalid YAML" warning
- All Dataview queries referencing `FROM #community/...` return 0 results
- `graph.json` color groups silently apply to no nodes
- User sees blank notes, blames graphify, loses trust

**Prevention:**
Use PyYAML's `yaml.dump()` exclusively for ALL frontmatter serialization — never hand-craft YAML strings. PyYAML correctly quotes values that need it and handles all edge cases. Specifically:
```python
import yaml
frontmatter = yaml.dump({"source_file": label, "tags": tag_list}, allow_unicode=True, default_flow_style=False)
```
Never interpolate node labels, community names, or any graph-derived string directly into a YAML line with an f-string.

**Detection (warning signs):**
- Node labels containing `:` (e.g., `http://example.com`, `key: value`) — very common in code graphs
- Community names with spaces that get used as raw tag values
- Source file paths containing `#` (common in URLs stored as source_file)

**Phase:** Implement PyYAML-based serialization from day one in the profile loader and template renderer. Do not defer.

---

### Pitfall 2: YAML Frontmatter — Wikilinks Inside List Fields Break Obsidian's Backlink Index

**What goes wrong:**
Obsidian's parser treats `[[Note Name]]` inside a YAML list field (e.g., `up:`, `related:`) as a resolved wikilink only if the field uses the bare wikilink syntax, not the quoted string form. If the value is `"[[Note Name]]"` (double-quoted YAML string), Obsidian does not register a backlink from `Note Name` to the current note. The link appears to work visually but the backlink panel and graph view miss the edge.

**Why it happens:**
PyYAML will quote `[[Note Name]]` as a string because `[` is a special YAML character, producing `"[[Note Name]]"`. This is valid YAML but defeats Obsidian's backlink resolution.

**Consequences:**
- `up:` and `related:` fields appear correct in the Properties panel
- Graph view is missing edges (MOC → Dot connections vanish)
- Dataview queries using `FROM [[MOC Name]]` return 0 results
- Extremely hard to debug because the notes look correct on inspection

**Prevention:**
For wikilink list fields (`up:`, `related:`, `collections:`), do not use PyYAML for those specific keys. Instead write the YAML block manually using a known-safe pattern:
```python
def _wikilink_yaml_list(field: str, targets: list[str]) -> list[str]:
    lines = [f"{field}:"]
    for t in targets:
        # Sanitize the target name itself, then write bare [[]] syntax
        safe = sanitize_label(t)  # strips control chars, caps length
        lines.append(f"  - \"[[{safe}]]\"")
    return lines
```
Note that Obsidian parses `"[[Note]]"` (quoted) correctly for backlinks in YAML list items — the double-quote wrapping is required by YAML spec when the value starts with `[`, and Obsidian's parser handles this case. Verify this behavior against the Obsidian release notes for the target minimum version.

**Detection (warning signs):**
- Any frontmatter field that is supposed to carry wikilinks
- Profile YAML declares `format: wikilink` for a field mapping
- Running Dataview `FROM [[SomeNote]]` returns 0 when notes exist with `related: [[SomeNote]]`

**Phase:** Phase 1 (frontmatter generation). Write a test that parses the output YAML and verifies backlinks are registered (check `.obsidian/cache` or parse output and assert the `[[]]` syntax is present).

---

### Pitfall 3: Merge Strategy — Overwriting User-Edited Frontmatter Fields

**What goes wrong:**
The adapter re-runs and writes a fresh note, replacing the user's hand-edited `rank:`, `mapState:`, or custom fields with the default values from the template. The user's curation work is silently destroyed. This is the single most trust-destroying failure mode for an injection tool operating on an existing vault.

**Why it happens:**
Naive implementation reads the template, fills placeholders, and writes the file. No round-trip parse of the existing note's frontmatter before writing.

**Consequences:**
- Permanent data loss (unless the vault is in git)
- User cannot trust graphify to run on a live vault
- Adoption blocker — the tool is too dangerous to use on real vaults

**Prevention:**
Implement a frontmatter merge with a field preservation list. On update:
1. Parse the existing note's frontmatter into a dict (handle missing/malformed frontmatter gracefully)
2. Apply the template-generated frontmatter as the base
3. For each field in `profile.yaml`'s `preserve_fields` list, restore the value from the existing note (if present)
4. Write the merged result

Default `preserve_fields` should include at minimum: `rank`, `mapState`, `created`, and any field the profile does not generate.

```python
def merge_frontmatter(existing: dict, generated: dict, preserve: list[str]) -> dict:
    merged = {**generated}
    for field in preserve:
        if field in existing:
            merged[field] = existing[field]
    return merged
```

**Detection (warning signs):**
- Profile defines fields the user might also manually set (`rank`, `mapState`, custom fields)
- Any re-run of graphify on a vault that has been open for editing

**Phase:** Phase 1 (merge strategy design). Must be implemented before any real vault is tested. Cannot be added as a later enhancement — the schema must account for it from the start.

---

### Pitfall 4: File Naming — Unicode Normalization Causes Duplicate or Phantom Notes

**What goes wrong:**
A node label `"café"` stored as NFC (U+00E9 `é`) produces filename `café.md`. On macOS (HFS+/APFS, NFD normalization) the filesystem stores it as `cafe\u0301.md`. When graphify re-runs and generates the NFC form again, Python's `Path.exists()` says the file does not exist (NFC ≠ NFD at the bytes level on Linux/ext4), so a new file is created. The vault now has two notes for the same node. On macOS they appear as one file; on Linux sync targets they appear as two.

**Why it happens:**
macOS normalizes filenames to NFD internally. Python's `pathlib` on macOS will transparently handle this for local operations, but string comparison of filenames across platforms breaks when NFC vs NFD differ.

**Consequences:**
- Duplicate notes appear in vault after cross-platform sync (Obsidian Sync, iCloud, git)
- Wikilinks to the NFC form resolve on macOS but break on Linux/Windows
- Phantom backlinks in graph view

**Prevention:**
Normalize all filenames to NFC before use:
```python
import unicodedata
def normalize_filename(name: str) -> str:
    return unicodedata.normalize("NFC", name)
```
Apply this normalization at the point of filename generation, not display. Store the normalized form in the `node_filename` mapping and use it consistently for both file writes and wikilink generation.

**Detection (warning signs):**
- Any node labels sourced from document text (very common — paper titles, person names)
- Vault is synced across macOS and Linux/Windows

**Phase:** Phase 1 (filename generation). One-line fix, but must be in from the start.

---

### Pitfall 5: OS Path Limits and Folder Nesting Cause Silent Write Failures

**What goes wrong:**
The profile maps nodes to nested folders like `Atlas/Dots/Things/`. Long node labels (256 chars, already the current `sanitize_label` cap) plus deep folder nesting exceed the 255-byte limit on Linux/ext4 for filename components and the ~260-char limit on Windows for full paths. `Path.write_text()` raises `OSError: File name too long` or `FileNotFoundError` (Windows path limit). The error may be swallowed by a broad except clause, silently skipping note generation.

**Why it happens:**
`sanitize_label` caps at 256 characters — which is already at the filesystem limit for the filename component alone, before adding `.md` (3 bytes). With folder prefix, it easily exceeds limits.

**Consequences:**
- Silent note generation failures (nodes skipped without warning)
- Inconsistent vault — some nodes have notes, others don't
- Wikilinks to missing notes appear as unresolved in Obsidian

**Prevention:**
Cap filenames at 200 characters (leaves room for folder depth, `.md` extension, and deduplication suffixes like `_2`). Emit a warning log for every truncation. For Windows compatibility, also strip trailing dots and spaces (Windows disallows them):
```python
_WINDOWS_RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', re.IGNORECASE)

def safe_filename(label: str, max_len: int = 200) -> str:
    name = unicodedata.normalize("NFC", label)
    name = re.sub(r'[\\/*?:"<>|#^\[\]]', "", name).strip(" .")
    if _WINDOWS_RESERVED.match(name):
        name = f"_{name}"
    return name[:max_len] or "unnamed"
```

**Detection (warning signs):**
- Profile folder mapping places notes 3+ levels deep (`Atlas/Dots/Things/`)
- Graph contains nodes from codebases with long fully-qualified class names

**Phase:** Phase 1. Tighten the filename cap in `safe_name()` before folder-mapping is added.

---

### Pitfall 6: Template Rendering — Placeholder Collision with User Content

**What goes wrong:**
A template uses `{{label}}` as a placeholder. A node's label contains `{{` or `}}` literally (e.g., a code symbol like `{{MyComponent}}` in a React codebase, or a Jinja2/Handlebars template fragment extracted from docs). The simple string substitution replaces the placeholder, but the label value itself contains the delimiter, creating malformed output or injecting false placeholders that get substituted in a second pass.

**Why it happens:**
Simple `str.replace("{{label}}", value)` is safe for single-pass substitution IF the replacement value cannot contain the delimiter. But node labels from code graphs routinely contain `{`, `}`, `{{`, `}}`.

**Consequences:**
- Malformed note body (missing text, corrupted structure)
- If a multi-pass substitution is ever added, arbitrary content injection from label into template
- Template fields like `{{created}}` appear literally in notes if the node label replaces `{{label}}` with a value that consumed part of the template

**Prevention:**
Use a single-pass substitution with non-colliding delimiters and escape the replacement value before substitution. The safest approach: replace all occurrences of each placeholder exactly once, and sanitize the replacement value by escaping `{` and `}` before insertion:
```python
def render_template(template: str, context: dict[str, str]) -> str:
    result = template
    for key, value in context.items():
        # Escape braces in value to prevent collision
        safe_value = str(value).replace("{", "&#123;").replace("}", "&#125;")
        result = result.replace(f"{{{{{key}}}}}", safe_value)
    return result
```
Alternatively, use `string.Template` with `$label` syntax — `$` is extremely rare in node labels. Document the chosen delimiter in the profile schema so users writing custom templates know the syntax.

**Detection (warning signs):**
- Nodes extracted from JavaScript/TypeScript, JSX, Jinja2, Go templates, or Helm charts
- Any node label containing `{` or `}`
- Template placeholders that overlap with Obsidian Templater plugin syntax (`{{` is Templater syntax too)

**Phase:** Phase 1 (template renderer). Test with node labels containing `{{`, `}}`, `$`, and backticks.

---

### Pitfall 7: Security — Path Traversal via profile.yaml Folder Mapping

**What goes wrong:**
A profile.yaml `folder_mapping` entry specifies `folder: "../../.ssh"` or `folder: "/etc/passwd"`. The adapter resolves the output path as the vault root joined with the configured folder, and writes note files outside the vault directory. This is a directory traversal vulnerability via configuration file.

**Why it happens:**
Folder values from `profile.yaml` are used as path components without validation. The profile could be from an untrusted source (auto-downloaded, committed by a collaborator, or crafted by a malicious vault template).

**Consequences:**
- Arbitrary file write to any path writable by the graphify process
- Potential overwrite of SSH keys, shell configs, or other critical files
- On systems where graphify runs with elevated privileges, severe

**Prevention:**
Apply the same `validate_graph_path()` pattern from `security.py` to all profile-configured output paths. Resolve the final path and assert it is inside the configured vault output directory:
```python
def validate_vault_path(path: Path, vault_root: Path) -> Path:
    resolved = (vault_root / path).resolve()
    try:
        resolved.relative_to(vault_root.resolve())
    except ValueError:
        raise ValueError(
            f"Profile folder mapping {path!r} escapes vault root {vault_root}. "
            "Only paths inside the vault directory are permitted."
        )
    return resolved
```
Validate every path-producing profile field: `folder_mapping`, `template_dir`, `output_dir` override.

**Detection (warning signs):**
- Any profile field that is used to construct a file path
- Profile loaded from `.graphify/profile.yaml` inside an untrusted vault
- `folder_mapping` entries that contain `..`, absolute paths, or drive letters

**Phase:** Phase 1 (profile loader). Security check must be in the loader, not deferred to write time.

---

### Pitfall 8: graph.json — Incorrect Format Breaks Obsidian Graph View Silently

**What goes wrong:**
The current `export.py` writes `.obsidian/graph.json` with `colorGroups[].query` as `"tag:#community/..."`. Obsidian's graph view query syntax does not use `tag:#` — it uses `tag:#tagname` only in search, not in graph filter queries. In the graph view, the filter syntax is `tag:tagname` (no `#`). The color groups are written but never applied because the query syntax is wrong.

**Why it happens:**
Obsidian has two subtly different query syntaxes: the search bar (`tag:#foo`) and the graph view filter (`tag:foo`). They look similar but the `#` prefix is only for search.

**Consequences:**
- Graph view shows all nodes in the default color (gray)
- Community color coding appears to be working (the JSON is written) but has zero visual effect
- Very hard to debug because the file is syntactically valid JSON

**Prevention:**
In `graph.json` `colorGroups`, use `tag:community/name` without the `#`:
```json
{
  "colorGroups": [
    {
      "query": "tag:community/Machine_Learning",
      "color": {"a": 1, "rgb": 16711680}
    }
  ]
}
```
Additionally, Obsidian's `graph.json` schema has evolved across versions. Validate against a known working vault's `graph.json` rather than relying on documentation. The `colorGroups` format was introduced in Obsidian 0.12 and has been stable, but `hideAttachments`, `showTags`, and other fields change between versions — only write fields that are explicitly needed.

**Detection (warning signs):**
- Graph view shows no community colors despite `graph.json` being present
- Obsidian console (Ctrl+Shift+I) shows JSON parse errors or unknown fields

**Phase:** Phase 1 (graph.json generation). Fix the `#` prefix bug immediately — it exists in the current codebase.

---

### Pitfall 9: Dataview Query — Tag Format Restrictions Break Queries

**What goes wrong:**
Obsidian tags (and therefore Dataview `FROM #tag` queries) have strict format rules: tags cannot contain spaces, cannot start with a number, and cannot contain most special characters except `/` (for nested tags) and `-` (hyphen). A community name like `"Machine Learning 2024"` maps to tag `community/Machine_Learning_2024` only if spaces are replaced. But community names like `"C++ Core"`, `"2D Rendering"`, or `"async/await"` produce tags that are either invalid or collide after sanitization.

**Why it happens:**
The current `export.py` does `.replace(' ', '_')` on community names for tag generation, which handles spaces but not digits-at-start, slashes (produces nested tag `community/async/await` which Obsidian treats as three-level nesting), or special chars like `+`, `.`, `(`, `)`.

**Consequences:**
- Invalid tags are silently ignored by Dataview
- `FROM #community/C++_Core` matches nothing
- Slashes in community names create unintended tag nesting (`community/async/await` is tag `community` > `async` > `await`)
- Dataview queries on community overview notes return 0 results

**Prevention:**
Apply comprehensive tag sanitization:
```python
import re

def sanitize_tag(name: str) -> str:
    """Produce a valid Obsidian tag segment from an arbitrary string."""
    # Replace spaces and special chars with hyphens
    tag = re.sub(r'[^a-zA-Z0-9\-_]', '-', name)
    # Collapse multiple hyphens
    tag = re.sub(r'-+', '-', tag).strip('-')
    # Tags cannot start with a digit
    if tag and tag[0].isdigit():
        tag = f"g-{tag}"
    return tag or "unnamed"
```
Apply this to every tag segment individually, including community name segments used in nested tags.

**Detection (warning signs):**
- Community names from LLM-generated labels (highly variable, often contain special chars)
- Node labels sourced from code (frequently contain `+`, `*`, `<`, `>`, `::`, `/`)
- Any Dataview query returning 0 results when matching notes exist

**Phase:** Phase 1. Fix `safe_name()` usage in tag generation. Add a test asserting that a community named `"C++ Core/2D"` produces a valid Obsidian tag.

---

### Pitfall 10: Wikilink Generation — Duplicate Display Names Across Different Nodes

**What goes wrong:**
Two nodes with different IDs but the same label (e.g., two `__init__` functions from different Python modules) both produce the same base filename. The current `export.py` deduplicates by appending `_1`, `_2`, etc. But a wikilink `[[__init__]]` in one note resolves to whichever note Obsidian finds first — the numeric suffix must appear in the wikilink too. If the wikilink omits the suffix, Obsidian resolves it to the wrong note, and the graph view shows a collapsed node.

**Why it happens:**
The deduplication logic tracks `node_filename[node_id]` correctly, but the ORDER in which `G.nodes(data=True)` iterates is not deterministic across Python versions or graph mutations. Node `__init__` from `module_a` might get suffix `_1` on one run and `_2` on the next run, making wikilinks in previously generated notes stale.

**Consequences:**
- Wikilinks point to wrong notes after re-run
- Obsidian shows unresolved links (red in graph view) when notes do exist
- Community member lists in overview notes link to wrong nodes

**Prevention:**
Sort nodes deterministically before assigning filenames — sort by `source_file` + `label` to produce a stable ordering:
```python
sorted_nodes = sorted(G.nodes(data=True), key=lambda nd: (nd[1].get("source_file",""), nd[1].get("label", nd[0])))
```
Also generate aliases in the frontmatter for deduplicated nodes so Obsidian can find them by either name:
```yaml
aliases:
  - __init__
```

**Detection (warning signs):**
- Any codebase with common function/class names (`__init__`, `main`, `index`, `handler`)
- Re-running graphify on the same project and seeing different deduplication suffixes

**Phase:** Phase 1 (filename generation). Add a test with two nodes that have identical labels and assert deterministic suffix assignment across multiple runs.

---

## Moderate Pitfalls

---

### Pitfall 11: YAML Multiline Strings — Folded/Literal Block Scalars in Frontmatter

**What goes wrong:**
PyYAML, when serializing a string containing newlines, produces a literal block scalar (`|`) or folded scalar (`>`). Obsidian's Properties panel does not render multi-line YAML string values correctly — it shows the raw `|` or `>` character followed by the content as a single broken line. This affects `description:` or `summary:` fields populated from graph analysis data.

**Prevention:**
For frontmatter fields, strip newlines from all string values before YAML serialization. If a description field needs multiple sentences, join them with a space or use a YAML list instead of a multiline string. Pass `width=float('inf')` to `yaml.dump()` to prevent PyYAML from line-wrapping long strings (which also triggers block scalar output).

**Phase:** Phase 1. Add sanitization in the frontmatter builder for any field sourced from analysis text.

---

### Pitfall 12: Merge — Frontmatter Field Ordering Changes Trigger False Diffs

**What goes wrong:**
The existing note has frontmatter in user-authored order (`up:`, `related:`, `tags:`, `created:`). The adapter writes the merged frontmatter in template-defined order (`created:`, `tags:`, `up:`, `related:`). Git (if the vault is versioned) shows the entire frontmatter block as changed on every run, even when no values changed. This noise pollutes git history and causes confusion.

**Prevention:**
After merging frontmatter dicts, write fields in the order they appear in the existing note first, then append any new fields. Implement a key-ordered merge:
```python
def ordered_merge(existing_keys: list[str], merged: dict) -> dict:
    result = {}
    for k in existing_keys:
        if k in merged:
            result[k] = merged[k]
    for k, v in merged.items():
        if k not in result:
            result[k] = v
    return result
```

**Phase:** Phase 2 (merge strategy refinement). Acceptable to defer until after initial merge is working, but must be addressed before production use.

---

### Pitfall 13: Profile YAML — Missing Fields Cause Silent Fallback to Wrong Defaults

**What goes wrong:**
A profile.yaml is partially defined (user configured `folder_mapping` but omitted `merge_strategy`). The adapter uses a hardcoded default for `merge_strategy` that differs from what the user expects. Since no error is raised, the user does not know the profile is incomplete, and notes are silently overwritten.

**Prevention:**
Implement strict schema validation for profile.yaml using a schema dict (no Pydantic, to avoid new dependencies). Log a warning for every missing optional field, listing the default being applied. For required fields, raise `ValueError` with a clear message pointing to the profile key. Provide a `graphify --validate-profile` command that reports missing/invalid fields.

**Phase:** Phase 1 (profile loader). Schema validation must be in the loader.

---

### Pitfall 14: Template — Missing Placeholder Context Keys Produce Literal Placeholder Text in Notes

**What goes wrong:**
A template contains `{{community_label}}` but the template renderer is called for a node type that does not have community data (e.g., an orphan node). The renderer finds no value for `community_label` in the context dict and leaves `{{community_label}}` literally in the note body. Obsidian renders this as text. Dataview queries that filter on empty fields return unexpected results.

**Prevention:**
The renderer must require that all placeholders in a template be present in the context. On missing key: either raise `KeyError` with the template name and missing key, or substitute a configurable empty string and emit a warning. Never silently leave placeholder text in output. Implement a `validate_template(template_str, context_keys)` function that extracts all `{{...}}` tokens and checks them against available keys before rendering.

**Phase:** Phase 1 (template renderer).

---

### Pitfall 15: Obsidian Alias Resolution — Spaces in Filenames vs. Underscores in Wikilinks

**What goes wrong:**
Obsidian resolves `[[Machine Learning]]` to a file named `Machine Learning.md`. But `[[Machine_Learning]]` does NOT resolve to `Machine Learning.md` — underscores are not treated as spaces in wikilinks. The existing `safe_name()` strips only the listed forbidden characters but preserves spaces. If any code path normalizes spaces to underscores for tag generation but reuses the same string for wikilink generation, links break.

**Prevention:**
Maintain strict separation between filename strings (spaces allowed, used for wikilinks) and tag strings (spaces replaced with hyphens/underscores). Never share the same sanitized string between both use cases. Define explicit functions: `to_filename(label)` and `to_tag(label)`, and use them consistently.

**Phase:** Phase 1. The existing code already separates `safe_name` from tag generation mostly correctly, but the new profile system must enforce this distinction explicitly.

---

## Minor Pitfalls

---

### Pitfall 16: graph.json — Writing to Existing Vault Overwrites User's Graph Settings

**What goes wrong:**
The adapter writes `.obsidian/graph.json` with only community color groups, overwriting the user's existing graph view settings (display depth, filters, show tags toggle, show orphans setting, link strength).

**Prevention:**
Read the existing `graph.json` if present, merge only the `colorGroups` array, and write back. Do not overwrite other keys. If `.obsidian/graph.json` does not exist, write only the `colorGroups` key with a minimal valid structure.

**Phase:** Phase 1 (graph.json generation). The current export.py already has this bug — it overwrites unconditionally.

---

### Pitfall 17: Unicode in Tag Values — Emoji and Non-Latin Scripts

**What goes wrong:**
Community names with emoji (`"🧠 AI Core"`) or non-Latin scripts (`"机器学习"`) produce tags that are technically valid in Obsidian (which supports Unicode tags) but may break Dataview's `FROM #tag` query parser in older plugin versions. The `#` character in the middle of a tag segment (e.g., from a label containing `#`) silently terminates the tag.

**Prevention:**
The `sanitize_tag()` function (see Pitfall 9) should strip emoji and non-ASCII characters from tag segments if the profile targets maximum compatibility. Offer a profile setting `tag_charset: ascii|unicode` with `ascii` as the safe default for compatibility.

**Phase:** Phase 2. Low priority unless vault targets older Dataview versions.

---

### Pitfall 18: Wikilink Aliases — Display Text Containing `|` Breaks the Link

**What goes wrong:**
Obsidian wikilink syntax for aliases is `[[Target|Display Text]]`. If the display text itself contains `|`, the link is malformed. Node labels from code graphs (e.g., `A|B` as a type union in TypeScript) can contain `|`.

**Prevention:**
When generating wikilinks with display text, strip or replace `|` in the display portion: `display.replace("|", "or")` or `display.replace("|", " | ")` (the space-padded version is not interpreted as alias separator by Obsidian).

**Phase:** Phase 1 (wikilink builder). Small guard, easy to miss.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Profile loader (YAML parsing) | Missing fields silently using wrong defaults (P13) | Strict schema validation with explicit warnings for every defaulted field |
| Frontmatter generation | Unquoted special chars breaking YAML (P1), wikilinks not registering backlinks (P2) | Use PyYAML for all non-wikilink fields; manual wikilink list rendering with tested pattern |
| Filename generation | Unicode normalization duplicates (P4), OS path limits (P5), determinism (P10) | NFC normalization + 200-char cap + sort-stable deduplication, all in Phase 1 |
| Template renderer | Placeholder collision from node labels (P6), missing keys (P14) | Single-pass substitution with brace-escaped values; pre-render validation of all placeholders |
| Merge strategy | User edits overwritten (P3), field ordering diffs (P12) | Preserve list from profile; ordered merge respecting existing field sequence |
| Security (path traversal) | profile.yaml folder mapping escaping vault root (P7) | `validate_vault_path()` in profile loader before any path is used |
| graph.json generation | Wrong query syntax (P8), overwriting user settings (P16) | Fix `tag:#` → `tag:` immediately; read-merge-write instead of overwrite |
| Tag generation | Invalid Dataview tag format (P9), emoji/Unicode compat (P17) | `sanitize_tag()` applied to every segment; profile setting for charset |
| Wikilink generation | Alias `|` in display text (P18), space vs underscore confusion (P15) | Separate `to_filename()` / `to_tag()` / `to_wikilink()` functions; strip `|` from display text |

---

## Existing Code Baseline Issues (Pre-existing Bugs in export.py)

The following bugs exist in the current `to_obsidian()` implementation and should be fixed as part of this milestone:

1. **graph.json query uses `tag:#community/...`** — should be `tag:community/...` (no `#`) for graph view filter syntax (P8)
2. **graph.json overwrites unconditionally** — no read-merge (P16)
3. **Frontmatter hand-crafted with f-strings** — no PyYAML, no protection against `:`, `"`, `#` in values (P1)
4. **Node iteration order not sorted** — deduplication suffix assignment is non-deterministic (P10)
5. **Tag generation uses only `.replace(' ', '_')`** — does not handle `/`, `+`, digits-at-start, etc. (P9)
6. **`sanitize_label` cap is 256 chars** — too long when combined with folder nesting (P5)
