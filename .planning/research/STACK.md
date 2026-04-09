# Technology Stack

**Project:** Configurable Obsidian Vault Adapter (Ideaverse Integration milestone)
**Researched:** 2026-04-09
**Confidence:** HIGH — all recommendations derived from existing codebase + Python stdlib docs. No new external dependencies introduced.

---

## Recommended Stack

### YAML Profile Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `PyYAML` (`yaml.safe_load`) | >=5.1 (optional dep) | Parse `.graphify/profile.yaml` from vault | Already an optional pattern in the project. `safe_load` prevents arbitrary object construction — mandatory for user-supplied files. Never use `yaml.load()`. |

**Rationale:** The project constraint says "yaml via PyYAML already optional." PyYAML is the de-facto standard for YAML parsing in Python. It is not in `pyproject.toml` as a required dep, which is correct — the profile system is an optional vault-side feature. The loader must be `yaml.safe_load()` because `profile.yaml` comes from user-controlled vault directories.

**Fallback strategy (when PyYAML is not installed):** Provide a graceful ImportError path that falls back to the built-in default profile. This preserves the "no new required dependencies" constraint.

**What NOT to use:**
- `yaml.load()` — unsafe, executes arbitrary Python via YAML tags
- `ruamel.yaml` — not installed, adds complexity, PyYAML is sufficient for read-only config parsing
- `tomllib` (stdlib 3.11+) — TOML not YAML; breaks Python 3.10 compatibility without a backport
- `configparser` — INI format, cannot represent the nested profile schema needed

**Confidence:** HIGH (stdlib + PyYAML well-documented, existing usage pattern in project)

---

### Markdown Template Rendering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `string.Template` (stdlib) | Python 3.10+ | Render per-note-type markdown templates with `$placeholder` substitution | Zero new deps. Explicit `safe_substitute()` prevents KeyError on missing placeholders — safe to use with partially-defined templates. |

**Rationale:** The project constraint explicitly prohibits Jinja2 ("simple placeholder substitution, not Jinja2"). The two stdlib options are:

- `string.Template` — `$var` or `${var}` syntax. `safe_substitute()` leaves unrecognized placeholders intact rather than raising. Good for vault-owner-defined templates that may only use a subset of available variables.
- `str.format_map()` — `{var}` syntax, but raises `KeyError` on missing keys unless wrapped with a `defaultdict`. Also conflicts visually with Python f-strings and JSON objects in templates.

**Choose `string.Template`** because:
1. `safe_substitute()` handles sparse templates without error handling overhead
2. `$var` syntax is distinct from Obsidian's own `{{var}}` Templater syntax — no visual collision
3. Vault owners editing templates see familiar shell-style substitution
4. Security: `string.Template` does not evaluate expressions, purely substitutes named keys from a provided mapping

**Security note:** All values passed into the substitution mapping must be pre-sanitized via `security.sanitize_label()` before substitution. A malicious node label containing `$other_key` could expand unexpectedly — use `safe_substitute()` with a flat dict, not chained template lookups.

**What NOT to use:**
- Jinja2 — new dependency, expressly excluded by project constraint
- `str.format()` / `str.format_map()` — `{` chars in Obsidian wikilinks and Dataview queries would require escaping the entire template body with `{{` — fragile
- Custom regex substitution — reinventing `string.Template` with worse security properties
- Mako, Cheetah, any other template engine — new dependencies

**Confidence:** HIGH (stdlib, no external sources needed)

---

### Frontmatter Generation (YAML in Markdown)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Manual string construction with `_yaml_str()` helper (existing pattern) | — | Emit YAML frontmatter blocks | Consistent with existing `ingest.py` and `export.py` patterns. No new dep. Deterministic output. |

**Rationale:** The current codebase already uses a `_yaml_str()` helper in `ingest.py` that escapes strings for YAML double-quoted scalars. The existing `export.py:to_obsidian()` writes frontmatter as manually constructed string lists.

**Extend, don't replace:** The new vault adapter should extract and formalize `_yaml_str()` into a shared utility (or reuse it from `ingest.py`), then build a `build_frontmatter(fields: dict) -> str` function that:
1. Wraps in `---` delimiters
2. Serializes scalar strings via `_yaml_str()`
3. Serializes list values (tags, wikilinks) as YAML block sequences (`- item`)
4. Never uses `yaml.dump()` for frontmatter — it introduces trailing newlines, Python-specific type tags (`!!python/object`), and inconsistent quoting that breaks Obsidian's YAML parser

**Wikilink frontmatter values** (`up:`, `related:`, `collections:`) require `"[[Note Name]]"` format — a YAML string containing brackets. Double-quote wrapping is already handled by `_yaml_str()`.

**What NOT to use:**
- `yaml.dump()` for frontmatter — unreliable output for Obsidian (adds tags, inconsistent quotes)
- f-strings with raw node labels — injection risk (labels may contain `"` or `:`)
- PyYAML for output — PyYAML's `dump()` doesn't preserve insertion order reliably in 3.10 (dicts are ordered in Python 3.7+ but PyYAML's emitter may reorder)

**Confidence:** HIGH (derived directly from existing codebase patterns)

---

### File Merge/Update Strategy

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pathlib.Path` (stdlib) | Python 3.10+ | Read existing note, parse frontmatter block, merge fields, write back | Already used throughout codebase. |
| Custom frontmatter parser (new, ~40 lines) | — | Split note into (frontmatter_dict, body) | No external dep. Notes have a simple deterministic structure: `---\n{yaml}\n---\n{body}`. |

**Rationale:** The merge strategy must:
1. Read existing note if it exists
2. Parse its frontmatter into a dict
3. Merge graphify-managed fields (overwrite) while preserving user-managed fields (keep)
4. Reconstruct and write

The frontmatter structure in Obsidian notes is deterministic: exactly `---\n...\n---` at the top. A simple parse is:

```python
def split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm_block = text[4:end]
            body = text[end + 5:]
            # parse fm_block as YAML or simple key:value
            return parse_fm(fm_block), body
    return {}, text
```

Profile controls which fields graphify "owns" vs. which the user owns. The `profile.yaml` `merge_behavior` key declares `graphify_fields` (overwritten) and `preserve_fields` (never touched). Default: graphify owns all fields it generates; user content in body is never modified.

**What NOT to use:**
- `python-frontmatter` library — new dependency, not in project, trivial to replace with 40 lines
- Regex to parse YAML frontmatter — fragile for multiline values and nested YAML
- Always-overwrite (current behavior) — breaks user edits, explicitly called out in requirements

**Confidence:** HIGH (stdlib, logic is straightforward)

---

### Obsidian-Specific Conventions

These are format conventions, not library choices. Verified against the existing `export.py` implementation and Obsidian documentation patterns.

#### Wikilinks

Format: `[[Note Name]]` or `[[Note Name|Display Text]]`

- **Filename-based**, not path-based by default in Obsidian (unless vault uses "Shortest path" or "Absolute path" link resolution)
- Safe filename characters: strip `\ / * ? : " < > | # ^ [ ]` — already implemented in `export.py:safe_name()`
- For frontmatter wikilinks (`up:`, `related:`): wrap in quotes: `up: "[[Parent Note]]"`
- For wikilink lists in frontmatter: YAML block sequence format:
  ```yaml
  related:
    - "[[Note A]]"
    - "[[Note B]]"
  ```

**Confidence:** HIGH (verified against existing implementation)

#### Dataview Queries

Format: fenced code block with `dataview` language tag.

```
```dataview
TABLE field1, field2 FROM #tag
WHERE condition
SORT file.name ASC
```
```

- Already used in current `export.py` community notes (line 622-626)
- MOC notes should embed a Dataview query listing members: `FROM [[MOC Note Name]]` (using note backlinks) or `FROM #community/tag`
- The profile should declare whether Dataview queries are embedded (`dataview_queries: true`)

**Confidence:** HIGH (verified against existing implementation + standard Obsidian Dataview convention)

#### graph.json Community Colors

Location: `{vault}/.obsidian/graph.json`

Schema (verified against existing implementation in `export.py` lines 668-677):

```json
{
  "colorGroups": [
    {
      "query": "tag:#community/community_name",
      "color": { "a": 1, "rgb": 5143975 }
    }
  ]
}
```

- `rgb` value is the integer representation of the hex color: `int("4E79A7", 16) = 5143975`
- `a` is opacity (1.0 = fully opaque)
- The vault adapter should only write `.obsidian/graph.json` when the output directory IS the target vault (i.e., writing directly into an existing vault, not to a separate `graphify-out/` dir)
- Profile key: `obsidian_config.write_graph_json: true/false`

**Confidence:** HIGH (verified against existing implementation)

#### Ideaverse ACE Frontmatter Fields

For the default built-in profile (Ideaverse-compatible output):

| Field | Type | Format | Notes |
|-------|------|--------|-------|
| `up` | wikilink string or list | `"[[Parent]]"` | Single parent in hierarchy |
| `related` | wikilink list | `- "[[Note]]"` | Peer connections |
| `collections` | wikilink list | `- "[[MOC]]"` | MOC membership |
| `tags` | list | `- tag/subtag` | No `#` prefix in frontmatter |
| `created` | ISO date | `2026-04-09` | `datetime.date.today().isoformat()` |
| `rank` | int | `1-5` | Maturity/importance score |
| `mapState` | string | `"sprout"/"tree"/"evergreen"` | Garden maturity |

**Confidence:** MEDIUM (based on Ideaverse Pro 2.5 conventions described in PROJECT.md; not directly verified against current Ideaverse docs as web search is unavailable)

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| YAML parsing | `yaml.safe_load` (PyYAML optional) | `ruamel.yaml` | Not installed; PyYAML sufficient for read-only config |
| YAML parsing | `yaml.safe_load` (PyYAML optional) | `tomllib` (stdlib) | TOML not YAML; Python 3.11+ only (breaks 3.10 target) |
| Template rendering | `string.Template.safe_substitute()` | Jinja2 | New dependency; expressly excluded by project constraint |
| Template rendering | `string.Template.safe_substitute()` | `str.format_map()` | `{` chars in Obsidian syntax require double-escaping entire template |
| Frontmatter output | Manual string construction | `yaml.dump()` | Inconsistent quoting, Python type tags break Obsidian |
| Frontmatter merge | Custom 40-line parser | `python-frontmatter` lib | New dependency for trivial logic |
| File write | `pathlib.Path.write_text()` | `open()` + `write()` | `Path` already used everywhere in codebase |

---

## Installation

No new dependencies required for core profile parsing (PyYAML optional path only):

```bash
# If vault profile feature requires PyYAML (optional, for profile.yaml parsing):
pip install PyYAML

# For users who already have graphify installed, no change needed for basic fallback behavior
pip install -e ".[all]"  # already includes no new deps for this feature
```

**Profile-aware Obsidian adapter requires zero new entries in `pyproject.toml` `dependencies`.**

If PyYAML is desired as an optional extra:
```toml
[project.optional-dependencies]
obsidian = ["PyYAML"]
```

But this may be unnecessary if the parser falls back gracefully to the built-in default profile when PyYAML is not available.

---

## Key Implementation Notes

1. **`profile.yaml` loading guard pattern** (follow existing optional-dep pattern from `cluster.py`/`serve.py`):
   ```python
   try:
       import yaml
       _profile = yaml.safe_load(profile_path.read_text())
   except ImportError:
       _profile = None  # fall back to built-in default profile
   ```

2. **Template placeholder naming convention:** Use `snake_case` names matching graph data keys directly: `$node_label`, `$source_file`, `$community_name`, `$created_date`, `$connections_block`. This makes templates self-documenting for vault owners.

3. **Merge field ownership declaration** in `profile.yaml`:
   ```yaml
   merge_behavior:
     strategy: update          # update | skip | replace
     graphify_fields:          # graphify always overwrites these
       - up
       - related
       - collections
       - tags
     preserve_fields:          # user-edited fields, never touched
       - rank
       - mapState
       - aliases
   ```

4. **Security — template injection:** Before passing node data into `string.Template.safe_substitute()`, all string values must pass through `security.sanitize_label()`. A node label containing `$preserve_fields` could theoretically expand to another key's value if the substitution dict contains that key. Use a whitelist-only substitution dict (only expose explicitly named variables, not the full node data dict).

---

## Sources

- Existing `graphify/export.py` — current `to_obsidian()` implementation (lines 440–679): verified wikilink format, frontmatter structure, Dataview query format, graph.json schema
- Existing `graphify/ingest.py` — `_yaml_str()` helper: confirmed existing manual YAML escaping pattern
- Existing `graphify/security.py` — `sanitize_label()`: confirmed label sanitization API
- `pyproject.toml` — confirmed PyYAML is NOT a current dependency
- `.planning/PROJECT.md` — confirmed constraints (no new required deps, stdlib preference, string substitution over Jinja2, Python 3.10+ target)
- Python stdlib docs — `string.Template`, `pathlib.Path` (HIGH confidence, stable APIs)
- PyYAML docs — `safe_load` (HIGH confidence, stable API since 5.1)
