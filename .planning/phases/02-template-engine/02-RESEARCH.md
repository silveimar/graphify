# Phase 2: Template Engine - Research

**Researched:** 2026-04-11
**Domain:** Python string templating, YAML frontmatter generation, importlib.resources, Obsidian vault note rendering
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-17:** `string.Template.safe_substitute()` with `${var}` syntax. Unknown placeholders left untouched (Templater tokens survive).
- **D-18:** Templates receive pre-rendered sections as scalars. Section vars: `${label}`, `${frontmatter}`, `${wayfinder_callout}`, `${connections_callout}`, `${members_section}`, `${dataview_block}`, `${metadata_callout}`, `${body}`. All empty string when absent.
- **D-19:** `resolve_filename(label, convention)` is the single entry point for both disk filenames and wikilink targets.
- **D-20:** User templates at `.graphify/templates/{type}.md`. Per-type strict filenames. Path resolution via `security.py` confinement.
- **D-21:** Built-in templates as real `.md` files under `graphify/builtin_templates/`, loaded via `importlib.resources`.
- **D-22:** `validate_template(text, required) -> list[str]`. Invalid user template: log to stderr, fall back to built-in.
- **D-23:** Frontmatter built as `dict[str, Any]` with insertion-order, dumped via `_dump_frontmatter()`. No PyYAML on render path. Block-form lists for list fields.
- **D-24:** Field order: `up`, `related`, `collections`, `created`, `tags`, then graphify-owned fields.
- **D-25:** List-valued: `up`, `related`, `collections`, `tags`. Scalar-valued: `type`, `file_type`, `source_file`, `source_location`, `community`, `created`, `cohesion`.
- **D-26:** `up:` always a list, even single item.
- **D-27:** `created:` = ISO date of run (`YYYY-MM-DD`). Phase 4 `preserve_fields` stabilizes across re-runs.
- **D-28:** Dataview query configurable via `obsidian.dataview.moc_query`. Default: `TABLE file.folder as Folder, type, source_file\nFROM #community/${community_tag}\nSORT file.name ASC`. Substitutes `${community_tag}` and `${folder}`.
- **D-29:** Below-threshold communities: `> [!abstract] Sub-communities` callout in parent MOC with nested bullets.
- **D-30:** MOC members grouped by note type using nested callouts: `> [!info] Things`, etc.
- **D-31:** MOC section order: `${frontmatter}` → `# ${label}` → `${wayfinder_callout}` → `${members_section}` → sub-communities callout → `${dataview_block}` → `${metadata_callout}`.
- **D-32:** Non-MOC scaffold: `${frontmatter}` → `# ${label}` → `${wayfinder_callout}` → `${body}` → `${connections_callout}` → `${metadata_callout}`.
- **D-33:** `${connections_callout}`: `> [!info] Connections` with aliased wikilinks and relation/confidence.
- **D-34:** `${metadata_callout}`: `> [!abstract] Metadata` with source_file, source_location, community. No backlinks section.
- **D-35:** Wayfinder: `> [!note] Wayfinder` with `Up:` and `Map:` rows. Derivation rules by note type. Atlas root configurable via `profile.obsidian.atlas_root` (default: `"Atlas"`).
- **D-35a:** Wayfinder derivation also populates `up:` frontmatter list.
- **D-36:** `title_case` → `Title_Case_Underscored.md`. `kebab-case` → `title-case-kebab.md`. `preserve` → `safe_filename(label)`.
- **D-37:** Wikilinks always auto-aliased: `[[Neural_Network_Theory|Neural Network Theory]]`.
- **D-38:** Filename convention applies uniformly to disk, wikilinks, frontmatter `up:`, Dataview expressions.
- **D-39:** Callout palette: `> [!note] Wayfinder`, `> [!info] Connections/Things/etc.`, `> [!abstract] Metadata/Sub-communities`.
- **D-40:** New `graphify/templates.py`. Imports from `graphify.profile` only. Added to `__init__.py` lazy imports.
- **D-41:** Public API: `render_note()`, `render_moc()`, `render_community_overview()`, `resolve_filename()`, `load_templates()`, `validate_template()`.
- **D-42:** `classification_context` typed dict shape defined in Phase 2, populated by Phase 3.

### Claude's Discretion

- Exact wording of built-in template body text (e.g., placeholder body comments).
- Whether `_dump_frontmatter` lives in `templates.py` or extracted to `profile.py`.
- Test fixture design for the 6 built-in templates.
- Exact regex for "unknown `${var}`" detection in `validate_template`.

### Deferred Ideas (OUT OF SCOPE)

- Conditional template blocks (`{{#if_god_node}}...{{/if}}`).
- Connection loop blocks (`{{#connections}}...{{/connections}}`).
- Per-community template overrides.
- Dataview query templates per note type in profile.
- Custom color palettes.
- Type-specific Thing/Statement/Person/Source body sections.
- Markdown-body content generation.
- Akiflow / Google Calendar / Efforts integration.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | Generated notes have YAML frontmatter with configurable fields (default: `up:`, `related:`, `collections:`, `tags:`, `created:`) | `_dump_frontmatter` design verified; block-list format confirmed Obsidian-compatible |
| GEN-02 | All inter-note references use `[[wikilink]]` format with proper deduplication and label sanitization | `resolve_filename()` + auto-alias pattern confirmed; `safe_frontmatter_value()` quotes `[` correctly |
| GEN-03 | User can provide custom markdown templates in `.graphify/templates/` that override built-in templates per note type | `validate_template()` pattern confirmed; fallback-to-builtin strategy confirmed |
| GEN-04 | Built-in templates exist for: MOC, Thing, Statement, Person, Source, Community Overview | `importlib.resources.files()` confirmed for editable + wheel installs on Python 3.10+ |
| GEN-05 | MOC notes include embedded Dataview queries that dynamically list community members | Two-phase substitution design confirmed; single-pass Template prevents collision |
| GEN-06 | Notes include wayfinder navigation elements linking to parent MOC and related communities | Wayfinder callout format confirmed; up: frontmatter coupling designed |
| GEN-07 | File naming follows configurable convention (title_case, kebab-case, preserve original label) | `resolve_filename()` logic verified for all three conventions with edge cases |
</phase_requirements>

---

## Summary

Phase 2 builds `graphify/templates.py` — a pure rendering module that converts graph nodes and communities into Obsidian note strings. Research confirms six critical technical areas: `string.Template.safe_substitute()` is single-pass (no re-parsing of substituted values, confirmed), Templater tokens `<% %>` pass through untouched (confirmed by testing), and `$$` escape sequences are correctly handled by `Template.pattern` so `validate_template` can use it for unknown-var detection without false positives.

The `_dump_frontmatter` helper requires type-dispatch rather than applying `safe_frontmatter_value()` to everything: floats and dates must be emitted unquoted to render as correct YAML types in Obsidian Properties (confirmed by PyYAML parsing tests). The YAML 1.1 boolean trap (`yes/no/on/off` parse as bool) is a real risk for community names but `safe_tag()` slugifies them before they reach frontmatter, neutralizing this. The hand-rolled dumper can stay simple — block list format for list fields, `safe_frontmatter_value()` for strings, `f"{v:.2f}"` for floats.

`importlib.resources.files()` returns a `PosixPath` (which is a Traversable) under editable installs, making `.read_text(encoding='utf-8')` the correct and portable API across editable, wheel, and zip-archive deployments. The `pyproject.toml` package-data entry must be extended to include `"builtin_templates/*.md"` — this is currently absent and will silently break wheel installs.

**Primary recommendation:** Implement `templates.py` as a pure function module with no IO. Test end-to-end with synthetic `classification_context` dicts against real built-in templates loaded via `importlib.resources`. Assert on structural invariants (YAML block lists, wikilink format, callout presence) — not golden output.

---

## Project Constraints (from CLAUDE.md)

- Python 3.10+ minimum; CI tests on 3.10 and 3.12.
- No new required dependencies — `importlib.resources` is stdlib, no PyYAML on render path.
- Backward compatible — `graphify --obsidian` without profile must not regress.
- Pure unit tests only — no network calls, no filesystem side effects outside `tmp_path`.
- `from __future__ import annotations` as first import in every module.
- Single-line module docstring after future import.
- 4-space indentation, type hints on all functions.
- Private helpers prefixed `_`, public API unprefixed.
- Validation returns `list[str]` of errors, never raises (follows `validate.py` pattern).
- Security: all file paths confined via `security.py` / `validate_vault_path()` patterns.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `string.Template` | stdlib | Template substitution | Already decided (D-17); zero deps |
| `importlib.resources` | stdlib 3.9+ | Built-in template loading | Standard Python resource API [VERIFIED: Python 3.10 REPL] |
| `pathlib.Path` | stdlib | File discovery for user overrides | Established project pattern |
| `re` | stdlib | `validate_template` var extraction, `resolve_filename` word-split | Used throughout project |
| `unicodedata` | stdlib | NFC normalization in `resolve_filename` | Already used in `safe_filename` [VERIFIED: profile.py L4] |
| `datetime` | stdlib | `created:` field generation | Stdlib, no dep needed |

### Supporting (import from existing modules)

| From | What | Purpose |
|------|------|---------|
| `graphify.profile` | `safe_frontmatter_value` | YAML scalar quoting |
| `graphify.profile` | `safe_tag` | `${community_tag}` derivation |
| `graphify.profile` | `safe_filename` | Final safety pass in `resolve_filename` |
| `graphify.profile` | `_DEFAULT_PROFILE` | Extend with `obsidian.atlas_root`, `obsidian.dataview.moc_query` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `string.Template` | Jinja2 | Jinja2 is explicit RCE risk via vault-supplied templates; adds dependency. Rejected in REQUIREMENTS.md. |
| Hand-rolled YAML dumper | PyYAML | PyYAML is optional; no dep on render path is required constraint (D-23). |
| `importlib.resources.read_text()` (deprecated 3.11) | `files().read_text()` | `files()` API is the current standard; `read_text()` deprecated in 3.11 [VERIFIED: Python docs]. |

**Installation:** No new packages needed. All stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
graphify/
├── templates.py              # New module: pure rendering functions
├── builtin_templates/
│   ├── moc.md                # Built-in MOC template
│   ├── thing.md              # Built-in Thing template
│   ├── statement.md          # Built-in Statement template
│   ├── person.md             # Built-in Person template
│   ├── source.md             # Built-in Source template
│   └── community.md          # Built-in Community Overview template
└── profile.py                # Extend _DEFAULT_PROFILE (obsidian section)

tests/
└── test_templates.py         # New test file, one per module convention
```

### Pattern 1: Built-in Template Loading via importlib.resources

**What:** Load `.md` files from the `builtin_templates/` subdirectory using the Traversable API.
**When to use:** Always — avoids hardcoded paths, works in editable and wheel installs.
**Confirmed working on Python 3.10:** `files()` returns `PosixPath` (a Traversable) under editable install. `.read_text(encoding='utf-8')` is the portable method. [VERIFIED: Python 3.10.19 REPL]

```python
# Source: Python 3.9+ importlib.resources Traversable API
import importlib.resources as ilr

def _load_builtin_template(note_type: str) -> string.Template:
    ref = ilr.files("graphify") / "builtin_templates" / f"{note_type}.md"
    text = ref.read_text(encoding="utf-8")
    return string.Template(text)
```

**Gotcha — editable installs:** Under `pip install -e .` with `setuptools >= 64`, `files()` returns the actual source directory. Under wheel installs, it returns a `MultiplexedPath` or zip path — both implement the Traversable protocol. Never cast to `Path()` directly; always use `.read_text()`.

**Gotcha — package-data:** `pyproject.toml` currently only lists `skill.md` files. `"builtin_templates/*.md"` is ABSENT. Must be added or wheel installs will fail with `FileNotFoundError`. [VERIFIED: pyproject.toml L62]

```toml
# pyproject.toml addition required
[tool.setuptools.package-data]
graphify = [
    "skill.md", "skill-codex.md", "skill-opencode.md",
    "skill-aider.md", "skill-copilot.md", "skill-claw.md",
    "skill-windows.md", "skill-droid.md", "skill-trae.md",
    "builtin_templates/*.md",   # ADD THIS
]
```

### Pattern 2: validate_template Using Template.pattern

**What:** Extract all substitution variables from a template text using `string.Template.pattern`.
**When to use:** `validate_template()` — catches unknown vars without executing substitution.

```python
# Source: Python stdlib string.Template internals [VERIFIED: Python 3.10.19 REPL]
import string

KNOWN_VARS: frozenset[str] = frozenset({
    "label", "frontmatter", "wayfinder_callout", "connections_callout",
    "members_section", "dataview_block", "metadata_callout", "body",
})

def validate_template(text: str, required: set[str]) -> list[str]:
    """Returns list of error strings — empty means valid."""
    errors: list[str] = []
    found: set[str] = set()
    for m in string.Template.pattern.finditer(text):
        name = m.group("named") or m.group("braced")
        if name:
            found.add(name)
        # m.group("escaped") is "$$" — not a substitution site, correctly ignored
    unknown = found - KNOWN_VARS
    if unknown:
        for var in sorted(unknown):
            errors.append(f"unknown placeholder ${{{{}}}} — not a graphify section var".format(var))
    for req in sorted(required):
        if req not in found:
            errors.append(f"missing required placeholder ${{{req}}}")
    return errors
```

**Key confirmations** [VERIFIED: Python 3.10.19 REPL]:
- `$$` (escaped dollar) matches `m.group("escaped")`, NOT `named`/`braced` — correctly skipped.
- `<% tp.date.now() %>` (Templater syntax) has no `$` prefix — never matched — passes through untouched.
- `${unknown_var}` where var is not in substitution context: `safe_substitute()` leaves it as `${unknown_var}` — intentional (D-17).
- `$$$identifier` = `$$` (escaped `$`) + `$identifier` → renders as `$identifier` — no ambiguity from Template.pattern's perspective.

### Pattern 3: _dump_frontmatter Type Dispatch

**What:** Hand-roll YAML frontmatter from a `dict[str, Any]` maintaining insertion order.
**When to use:** Always in `templates.py`. No PyYAML dependency on render path.

```python
# Source: YAML 1.1 spec + Obsidian Properties behavior [VERIFIED: PyYAML parsing tests]
import datetime
from graphify.profile import safe_frontmatter_value

def _dump_frontmatter(fields: dict) -> str:
    """Emit YAML frontmatter block including --- delimiters."""
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue  # omit None fields
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {safe_frontmatter_value(str(item))}")
        elif isinstance(value, float):
            lines.append(f"{key}: {value:.2f}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, datetime.date):
            lines.append(f"{key}: {value.isoformat()}")
        else:
            lines.append(f"{key}: {safe_frontmatter_value(str(value))}")
    lines.append("---")
    return "\n".join(lines)
```

**Critical YAML 1.1 gotchas** [VERIFIED: PyYAML 6.x parsing]:

| Python value | Unquoted YAML emission | Parses as | Action |
|---|---|---|---|
| `"2026-04-11"` | `created: 2026-04-11` | `datetime.date` | Desired for Obsidian date fields — emit unquoted |
| `"true"` / `"false"` | `type: true` | `bool` | Use `safe_frontmatter_value()` for str fields — but `type: thing` is safe |
| `"null"` | `type: null` | `None` | Would only occur if node label is literally "null" — `safe_frontmatter_value` doesn't quote it |
| `0.85` (float) | `cohesion: 0.85` | `float` | Correct — emit unquoted |
| `"[[link]]"` | `up: [[link]]` | `list` (YAML flow sequence!) | `safe_frontmatter_value` quotes it → `"[[link]]"` → parses as str |
| `"yes"` / `"on"` | `type: yes` | `bool` (YAML 1.1) | Risk only if community name is "yes" — `safe_tag()` slugifies it first |

**YAML block list format** (required by D-24, D-26 for Properties chip rendering and Linter):
```yaml
up:
  - "[[Atlas|Atlas]]"
related:
  - "[[Neural_Network_Theory|Neural Network Theory]]"
tags:
  - community/ml-architecture
  - graphify/code
```
Tags do NOT need quoting since `/` is not in `_YAML_SPECIAL`. [VERIFIED: profile.py + PyYAML test]

### Pattern 4: resolve_filename Convention Logic

**What:** Convert a node label to a disk filename using the profile-configured naming convention.
**When to use:** All wikilink emission, all disk filename generation.

```python
# Source: verified with edge cases in Python 3.10.19 REPL
import re, unicodedata
from graphify.profile import safe_filename

def resolve_filename(label: str, convention: str) -> str:
    """Convert label to filename stem (without .md extension)."""
    if convention == "title_case":
        # Split on spaces AND underscores (both are word separators)
        words = re.split(r"[ \t_]+", label)
        result = "_".join(w.capitalize() for w in words if w)
    elif convention == "kebab-case":
        words = re.split(r"[ \t]+", label.lower())
        result = "-".join(w for w in words if w)
    else:  # "preserve"
        result = label
    # safe_filename: NFC normalization, strip OS-illegal chars, 200-char cap
    return safe_filename(result)
```

**Edge cases confirmed** [VERIFIED: Python 3.10.19 REPL]:

| Label | Convention | Result | Note |
|---|---|---|---|
| `"Neural_Network_Theory"` | title_case | `"Neural_Network_Theory"` | Underscore treated as separator → re-joined |
| `"neural network theory"` | title_case | `"Neural_Network_Theory"` | Spaces → underscores |
| `"Teoría de Redes"` | title_case | `"Teoría_De_Redes"` | Unicode preserved via NFC |
| `"iPhone"` | title_case | `"Iphone"` | `capitalize()` lowercases rest — known limitation, acceptable |
| `"Deep-Learning: Methods"` | title_case | `"Deep-learning_Methods"` | Colon stripped by `safe_filename`; hyphen stays in word |
| `"GPT-4 Turbo"` | title_case | `"Gpt-4_Turbo"` | Hyphen stays in word |
| `"Neural Network Theory"` | kebab-case | `"neural-network-theory"` | Straightforward |
| `"Teoría de Redes"` | kebab-case | `"teoría-de-redes"` | Unicode preserved |

**Wikilink emission always pairs filename with label:**
```python
fname = resolve_filename(label, convention)
wikilink = f"[[{fname}|{label}]]"  # D-37: always aliased
```

### Pattern 5: Two-Phase Dataview Substitution

**What:** Substitute community vars into `moc_query` profile value first, then embed as `${dataview_block}`.
**When to use:** MOC and Community Overview rendering only.
**Key finding:** `string.Template` is SINGLE-PASS — values of substitutions are never re-parsed for further substitutions. [VERIFIED: Python 3.10.19 REPL]

```python
# Source: verified with single-pass test in Python 3.10.19 REPL
import string

def _render_dataview_block(profile: dict, community_tag: str, folder: str) -> str:
    moc_query = (
        profile.get("obsidian", {})
        .get("dataview", {})
        .get("moc_query", _DEFAULT_MOC_QUERY)
    )
    # Phase 1: substitute community-specific vars into the query template
    query = string.Template(moc_query).safe_substitute(
        community_tag=community_tag,
        folder=folder,
    )
    # Phase 2: wrap in dataview fence
    return f"```dataview\n{query}\n```"
    # This string is then passed as dataview_block= to the outer template
    # No collision risk: outer safe_substitute does not re-parse values
```

### Pattern 6: classification_context TypedDict Shape

**What:** Typed dict defining the context Phase 3 will populate and Phase 2 renders with.
**When to use:** Phase 2 defines the shape; tests use synthetic dicts.

```python
# D-42: Phase 2 defines this shape
from typing import TypedDict

class ClassificationContext(TypedDict, total=False):
    note_type: str           # 'thing'|'statement'|'person'|'source'|'moc'|'community'
    folder: str              # profile-derived folder path
    parent_moc_label: str    # label of parent community (for wayfinder Up:)
    community_tag: str       # safe_tag(community_name) for Dataview query
    members_by_type: dict    # {note_type: [node_id, ...]} — MOC/community only
    sub_communities: list    # [{label, members}] — below-threshold, MOC only
```

### Anti-Patterns to Avoid

- **Casting `importlib.resources.files()` to `Path()`:** Works for editable installs but fails for zip-archive or wheel deployments. Always call `.read_text()` via the Traversable protocol.
- **Using `safe_frontmatter_value()` for float/date/bool Python values:** Emits them as strings with potential quoting — loses correct YAML type semantics in Obsidian Properties.
- **Applying `string.Template.substitute()` instead of `safe_substitute()`:** Raises `KeyError` on unknown vars. `safe_substitute()` leaves unknown vars intact (required for Templater coexistence, D-17).
- **Splitting `resolve_filename` title_case on spaces only:** Labels with existing underscores (e.g., `Neural_Network_Theory`) would produce `Neural_network_theory` — wrong. Must split on both `[ \t_]+`.
- **Reading user template files without path confinement:** Must use `validate_vault_path()` from `profile.py` before reading any user template file.
- **Importing from `graphify.export`:** Explicitly forbidden for `templates.py` per D-40. Copy the `_dominant_confidence` pattern, do not import it.
- **Emitting inline YAML list format** `tags: [a, b]`: Obsidian Linter rewrites to block format on save, creating git noise. Always emit block format from the start.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML scalar quoting | Custom quote logic | `safe_frontmatter_value()` from `profile.py` | Already handles all `_YAML_SPECIAL` chars, tested |
| Filename sanitization | Custom strip regex | `safe_filename()` from `profile.py` | NFC, OS-illegal strip, 200-char hash cap all covered |
| Community tag slugification | Custom slugifier | `safe_tag()` from `profile.py` | Handles leading digits, special chars, empty input |
| Template variable extraction | Custom regex | `string.Template.pattern.finditer()` | Handles `$$` escape, braced/unbraced forms correctly |
| Path traversal validation | Custom `..` check | `validate_vault_path()` from `profile.py` | Tested, handles absolute paths outside vault too |

**Key insight:** Phase 1 built exactly the helper surface Phase 2 needs. `templates.py` should import from `graphify.profile` and delegate all sanitization there.

---

## Common Pitfalls

### Pitfall 1: package-data Not Including builtin_templates

**What goes wrong:** `(ilr.files("graphify") / "builtin_templates" / "moc.md").read_text()` raises `FileNotFoundError` when installed from a wheel (not editable).
**Why it happens:** `pyproject.toml` currently only lists `skill.md` files in package-data. The `builtin_templates/` subdirectory is absent. [VERIFIED: pyproject.toml L62]
**How to avoid:** Add `"builtin_templates/*.md"` to `[tool.setuptools.package-data]` in `pyproject.toml` before creating the directory.
**Warning signs:** Tests pass locally (editable install) but fail in CI or after `pip install graphifyy`.

### Pitfall 2: safe_frontmatter_value Does Not Quote YAML Boolean Keywords

**What goes wrong:** A community label like `"True"`, `"false"`, `"yes"`, or `"null"` goes through `safe_frontmatter_value()` unquoted and YAML parsers interpret it as `True`, `False`, `True`, or `None`. [VERIFIED: PyYAML 6.x test]
**Why it happens:** `_YAML_SPECIAL` in `profile.py` only covers `':#[]{}'` — not keyword values.
**How to avoid:** For community names entering frontmatter scalars, they first pass through `safe_tag()` which slugifies them. For `type:` field values, they are controlled graphify constants (`thing`, `statement`, etc.) which are not YAML keywords. The risk is narrow — only if a node `label` attribute is literally `"true"` etc. Document this and add a check in `_dump_frontmatter` for the boolean/null keyword set if paranoia is warranted.
**Warning signs:** Frontmatter field value appears as boolean `true` instead of string `"true"` in Obsidian Properties.

### Pitfall 3: resolve_filename with Existing Underscores in Labels

**What goes wrong:** `resolve_filename("Neural_Network_Theory", "title_case")` with a space-only split → `"Neural_network_theory"` (wrong capitalization after underscore).
**Why it happens:** `"Neural_Network_Theory".split(" ")` returns `["Neural_Network_Theory"]` (single word) → `capitalize()` → `"Neural_network_theory"`.
**How to avoid:** Split on `r"[ \t_]+"` (both spaces and underscores). [VERIFIED: Python 3.10.19 REPL]
**Warning signs:** Labels that already use underscores appear with only the first word capitalized.

### Pitfall 4: Wikilinks in frontmatter Without Quoting

**What goes wrong:** `up: [[Atlas|Atlas]]` without quotes — YAML parses `[[Atlas|Atlas]]` as a list-in-a-list (flow sequence) → `[[['Atlas|Atlas']]]`.
**Why it happens:** `[` is a YAML flow sequence indicator; `[[` is interpreted as nested sequences.
**How to avoid:** `safe_frontmatter_value("[[Atlas|Atlas]]")` returns `'"[[Atlas|Atlas]]"'` because `[` is in `_YAML_SPECIAL`. This happens automatically when wikilinks go through the helper. [VERIFIED: profile.py test + PyYAML parsing]
**Warning signs:** Obsidian Properties shows a list type instead of text for `up:` field.

### Pitfall 5: Two-Phase Substitution Order Confusion

**What goes wrong:** Substituting the outer template vars (including `${label}`) into `moc_query` before wrapping — causes node label to appear in the Dataview query when user accidentally wrote `${label}` in their query.
**Why it happens:** Wrong substitution order: outer vars first, then community vars.
**How to avoid:** Always do community-var substitution into `moc_query` FIRST, then embed as `dataview_block` value in outer context. `string.Template` is single-pass — values of substitutions are never re-parsed. [VERIFIED: Python 3.10.19 REPL]
**Warning signs:** Dataview query in rendered note shows the node label instead of a Dataview expression.

### Pitfall 6: Non-Namespace Package Concern with importlib.resources

**What goes wrong:** Concern about `MultiplexedPath` for namespace packages (no `__init__.py`).
**Why it does NOT apply:** `graphify` has `__init__.py` — it is NOT a namespace package. Under editable install, `files()` returns `PosixPath` directly. The Traversable `.read_text()` API works in all deployment modes. [VERIFIED: Python 3.10.19 REPL]
**Warning signs:** Would only appear with `pip install --editable` and Python < 3.9, or missing `__init__.py`.

---

## Code Examples

### Built-in Template Format (moc.md example)

```markdown
${frontmatter}
# ${label}

${wayfinder_callout}

${members_section}

${dataview_block}

${metadata_callout}
```

Templater tokens users can add in their custom templates:
```markdown
> Created: <% tp.file.creation_date() %>
> Modified: <% tp.file.last_modified_date() %>
```
These survive `safe_substitute()` untouched. [VERIFIED: Python 3.10.19 REPL]

### Frontmatter Block Example (MOC note)

```yaml
---
up:
  - "[[Atlas|Atlas]]"
related:
  - "[[Attention_Mechanism|Attention Mechanism]]"
collections: []
created: 2026-04-11
tags:
  - community/ml-architecture
  - graphify/code
type: moc
community: ML Architecture
cohesion: 0.82
---
```

### Connections Callout Example (non-MOC notes)

```markdown
> [!info] Connections
> - [[MultiHeadAttention|MultiHeadAttention]] — contains [EXTRACTED]
> - [[Attention_Mechanism|attention mechanism]] — implements [INFERRED]
```

### MOC Members Section Example (grouped callouts)

```markdown
> [!info] Things
> - [[Transformer|Transformer]]
> - [[MultiHeadAttention|MultiHeadAttention]]

> [!info] Sources
> - [[Attention_Is_All_You_Need|attention mechanism]]
```

### Sub-communities Callout (D-29)

```markdown
> [!abstract] Sub-communities
> - **Tiny Cluster:** [[Node_A|Node A]], [[Node_B|Node B]]
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Obsidian Linter does not rewrite block-list frontmatter unless user configures YAML Key Sort | Pitfall / YAML design | Field order would change on save, causing git noise — user would need to configure Linter |
| A2 | Obsidian Properties UI renders `created: 2026-04-11` (unquoted) as a date-type chip | _dump_frontmatter design | If Obsidian expects quoted string for date field, `created` shows as text — cosmetic only |
| A3 | `capitalize()` producing `Iphone` from `iPhone` is acceptable for title_case convention | resolve_filename | User may find unexpected casing for brand names — document as known limitation |

**The assumptions table is minimal.** All critical technical claims were verified via Python 3.10.19 REPL and the existing codebase.

---

## Open Questions

1. **Where should `_dump_frontmatter` live — `templates.py` or `profile.py`?**
   - What we know: `profile.py` already hosts `safe_frontmatter_value`; `_dump_frontmatter` is logically the "use site" of that helper.
   - What's unclear: Phase 4 (Merge Engine) will also need to emit frontmatter — if it lives in `templates.py`, Phase 4 would need to import from `templates.py` (or `profile.py`).
   - Recommendation: Place `_dump_frontmatter` in `profile.py` so both Phase 2 and Phase 4 can import it without circular dependencies. Left to Claude's discretion (D-40 says Claude picks).

2. **`_DEFAULT_PROFILE` extension — in-place mutation or separate constant?**
   - What we know: `profile.py` defines `_DEFAULT_PROFILE` as a module-level dict. Phase 2 adds `obsidian.atlas_root` and `obsidian.dataview.moc_query` defaults.
   - What's unclear: Should the extension happen in `profile.py` directly (one source of truth) or in `templates.py` (own your defaults)?
   - Recommendation: Extend in `profile.py` since `_deep_merge` uses it as the base and profile validation tests are there.

---

## Environment Availability

Step 2.6: No external runtime dependencies for Phase 2 — all stdlib. SKIPPED.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | `importlib.resources.files()` | ✓ | 3.10.19 | — |
| PyYAML | Validation tests only | ✓ | Installed (confirmed by test suite) | Not needed on render path |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (implicit) |
| Quick run command | `pytest tests/test_templates.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEN-01 | MOC note has YAML frontmatter with `up:`, `related:`, `collections:`, `tags:`, `created:` in block-list format | unit | `pytest tests/test_templates.py::test_render_moc_frontmatter_fields -x` | ❌ Wave 0 |
| GEN-01 | All list fields (`up`, `related`, `collections`, `tags`) emit as YAML block lists | unit | `pytest tests/test_templates.py::test_frontmatter_block_lists -x` | ❌ Wave 0 |
| GEN-01 | Wikilinks in frontmatter are quoted (`"[[...]]"`) | unit | `pytest tests/test_templates.py::test_frontmatter_wikilinks_quoted -x` | ❌ Wave 0 |
| GEN-02 | Wikilinks are auto-aliased `[[filename\|label]]` | unit | `pytest tests/test_templates.py::test_wikilink_auto_alias -x` | ❌ Wave 0 |
| GEN-02 | `resolve_filename` + `safe_filename` deduplication is stable | unit | `pytest tests/test_templates.py::test_resolve_filename_stable -x` | ❌ Wave 0 |
| GEN-03 | User template in `.graphify/templates/` overrides built-in | unit | `pytest tests/test_templates.py::test_user_template_override -x` | ❌ Wave 0 |
| GEN-03 | Invalid user template falls back to built-in with stderr message | unit | `pytest tests/test_templates.py::test_invalid_user_template_fallback -x` | ❌ Wave 0 |
| GEN-04 | All 6 built-in templates load without error | unit | `pytest tests/test_templates.py::test_all_builtins_load -x` | ❌ Wave 0 |
| GEN-04 | `render_note()` returns `(filename, text)` for each of 5 non-MOC types | unit | `pytest tests/test_templates.py::test_render_note_all_types -x` | ❌ Wave 0 |
| GEN-05 | MOC note contains `dataview` fence with `community_tag` substituted | unit | `pytest tests/test_templates.py::test_render_moc_dataview_block -x` | ❌ Wave 0 |
| GEN-05 | Custom `moc_query` in profile is used instead of default | unit | `pytest tests/test_templates.py::test_custom_moc_query -x` | ❌ Wave 0 |
| GEN-06 | Note contains `> [!note] Wayfinder` callout with `Up:` and `Map:` rows | unit | `pytest tests/test_templates.py::test_wayfinder_callout_present -x` | ❌ Wave 0 |
| GEN-06 | MOC wayfinder `Up:` links to Atlas, non-MOC links to parent MOC | unit | `pytest tests/test_templates.py::test_wayfinder_derivation -x` | ❌ Wave 0 |
| GEN-07 | `resolve_filename("neural network theory", "title_case")` = `"Neural_Network_Theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_title_case -x` | ❌ Wave 0 |
| GEN-07 | `resolve_filename("neural network theory", "kebab-case")` = `"neural-network-theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_kebab -x` | ❌ Wave 0 |
| GEN-07 | `resolve_filename("Neural_Network_Theory", "title_case")` preserves word capitalization | unit | `pytest tests/test_templates.py::test_resolve_filename_existing_underscores -x` | ❌ Wave 0 |

**Additional regression tests (not requirement-mapped but high-value):**
- `validate_template` detects unknown `${foo}` but ignores `$$escaped` and Templater `<% %>` tokens
- `_dump_frontmatter` emits `created: 2026-04-11` (unquoted) and parses as `datetime.date`
- `_dump_frontmatter` emits `cohesion: 0.82` (unquoted float)
- Templater tokens `<% tp.date.now() %>` survive `safe_substitute()` round-trip

### Sampling Rate

- **Per task commit:** `pytest tests/test_templates.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_templates.py` — all tests above; file does not exist yet
- [ ] `graphify/builtin_templates/` directory and 6 `.md` files — do not exist yet
- [ ] `graphify/templates.py` — module does not exist yet

*(No test infrastructure gaps — pytest and the fixture pattern are already established)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (file read) | `validate_vault_path()` from `profile.py` for user template discovery |
| V5 Input Validation | yes | `safe_frontmatter_value()`, `safe_tag()`, `safe_filename()`, `sanitize_label()` from existing modules |
| V6 Cryptography | no | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via user template path | Tampering | `validate_vault_path(vault_dir / ".graphify/templates" / filename, vault_dir)` before open |
| YAML frontmatter injection via node labels | Tampering | `safe_frontmatter_value()` quotes YAML-special chars |
| Template injection via Jinja2-style syntax | Tampering | Not applicable — `string.Template` only, no code execution possible |
| Long label DoS via filename | DoS | `safe_filename()` caps at 200 chars with hash suffix |
| Symlink escape from vault directory | Elevation of Privilege | `Path.resolve()` in `validate_vault_path()` resolves symlinks before checking confinement |

**Note:** Built-in template loading via `importlib.resources` reads from the installed package only — no user-controllable path involved. User template loading must validate the path. [ASSUMED — Jinja2 RCE note is cited from REQUIREMENTS.md Out of Scope table]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `importlib.resources.read_text()` | `importlib.resources.files().read_text()` | Python 3.11 (deprecated `read_text`), removed 3.13 | Use `files()` API for forward compatibility |
| `importlib.resources.path()` (context manager) | `files()` Traversable API | Python 3.9 | No context manager needed; cleaner code |
| Inline YAML list `tags: [a, b]` | Block YAML list `tags:\n  - a\n  - b` | Obsidian Properties UI (2023) | Chip rendering requires block format |

**Deprecated/outdated:**
- `importlib.resources.read_text(package, resource)` — deprecated 3.11, removed 3.13. Do not use. Use `ilr.files("graphify") / "builtin_templates" / "moc.md").read_text()` instead. [CITED: Python 3.11 What's New]

---

## Sources

### Primary (HIGH confidence)

- Python 3.10.19 REPL (local) — verified: `string.Template.safe_substitute()` edge cases, `Template.pattern` for var extraction, `importlib.resources.files()` behavior under editable install, single-pass substitution, Traversable API, `$$` escape behavior
- `graphify/profile.py` (codebase) — `safe_frontmatter_value`, `safe_tag`, `safe_filename`, `_YAML_SPECIAL`, `_DEFAULT_PROFILE`, `validate_vault_path`
- `graphify/__init__.py` (codebase) — lazy import registration pattern to follow
- `graphify/export.py` L440-679 (codebase) — reference for node/community iteration, `_dominant_confidence` pattern
- `graphify/validate.py` (codebase) — `validate_extraction` return-list-of-errors pattern
- `tests/test_profile.py` (codebase) — test patterns: `capsys`, `tmp_path`, `mock.patch.dict`, direct imports
- `pyproject.toml` (codebase) — confirmed missing `builtin_templates/*.md` package-data entry

### Secondary (MEDIUM confidence)

- PyYAML 6.x parsing tests (local) — YAML 1.1 boolean/date/null gotchas for `_dump_frontmatter` design
- `.planning/phases/02-template-engine/02-CONTEXT.md` — all D-17 through D-42 decisions

### Tertiary (LOW confidence / ASSUMED)

- Obsidian Linter behavior on block-list YAML: not directly testable in this session [ASSUMED]
- Obsidian Properties UI date field rendering: based on training knowledge + PyYAML parsing evidence [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, verified against Python 3.10.19
- Architecture: HIGH — all patterns verified via REPL and codebase inspection
- Pitfalls: HIGH — confirmed by direct testing (YAML parsing, Template edge cases, safe_filename)
- Validation architecture: HIGH — test patterns from existing suite, requirements from CONTEXT.md

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stdlib APIs are stable; 30-day window)
