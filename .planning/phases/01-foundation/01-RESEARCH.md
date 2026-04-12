# Phase 1: Foundation - Research

**Researched:** 2026-04-09
**Domain:** Python module design — profile loading/validation, filename safety helpers, export.py bug fixes
**Confidence:** HIGH

## Summary

Phase 1 is a pure Python, no-new-required-dependencies phase. Every decision has been locked in CONTEXT.md from the prior discussion session. The work splits cleanly into three tracks: (1) create a new `graphify/profile.py` module with profile discovery/loading/deep-merge/validation and filename/frontmatter/tag safety helpers, (2) patch five bugs in `export.py:to_obsidian()` and one in `to_canvas()` by importing the new helpers, and (3) register the new module in `__init__.py` and `pyproject.toml`.

All patterns are directly readable from the existing codebase. `validate.py` is the verbatim template for `validate_profile()`. `security.py:validate_graph_path()` is the verbatim template for the vault path-traversal check (`Path.resolve()` + `relative_to()`). `extract.py:_make_id()` is the reference for the slug core used in `safe_filename()`. No external research is needed — locked decisions plus codebase inspection provide full implementation guidance.

PyYAML is already listed as an optional dependency trigger in project docs but is NOT currently in `pyproject.toml`'s optional-dependencies table. A new `obsidian = ["PyYAML"]` extra must be added. PyYAML's `safe_load()` is the only third-party call needed.

**Primary recommendation:** Implement `profile.py` as a standalone module with zero imports from `export.py`, wire it into `__init__.py` lazy map, patch `export.py` bugs by importing helpers, add `obsidian` extra to `pyproject.toml`, and write `tests/test_profile.py` covering all PROF/MRG-04 requirements.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Profile Schema Design**
- D-01: Profile YAML uses flat top-level sections: `folder_mapping`, `naming`, `merge`, `mapping_rules`, `obsidian`
- D-02: User profiles deep-merge over built-in defaults — specifying `folder_mapping.moc` only overrides that key, all other folder_mapping entries keep their defaults
- D-03: Profile validation collects all errors and reports them together (follows `validate.py` pattern of returning `list[str]`), not fail-on-first
- D-04: PyYAML stays in optional dependencies. If user has a `profile.yaml` but no PyYAML installed, graphify prints a clear install instruction and falls back to built-in defaults

**Filename Safety Strategy**
- D-05: Filename deduplication uses deterministic sorted suffix — sort nodes by `(source_file, label)` before assignment, duplicates get `_2`, `_3` suffixes
- D-06: Filename length cap at 200 characters uses truncate-to-192 + 8-char hash suffix of the full name
- D-07: NFC Unicode normalization only — `unicodedata.normalize("NFC", text)`

**Bug Fix Approach**
- D-08: Bug fixes extract reusable helpers (`safe_filename`, `safe_frontmatter_value`, `safe_tag`) into `profile.py` rather than staying inline in `export.py`
- D-09: FIX-01 (YAML frontmatter injection) uses quote wrapping — values containing YAML-special chars (`:`, `#`, `[`, `]`, `{`, `}`) are wrapped in double quotes
- D-10: FIX-03 (tag sanitization) uses slugification — lowercase, spaces/special chars → hyphens, leading digits prefixed with `x`, `/` and `+` stripped. Format: `community/slugified-name`
- D-11: OBS-02 (graph.json) uses read-merge-write — read existing file, merge graphify's community color groups (keyed by `tag:community/` prefix), preserve all other user settings
- D-12: OBS-01 (graph.json tag syntax) fix: change `tag:#community` to `tag:community/Name` format
- D-13: FIX-06 (NEW): `to_canvas()` L809 hardcodes `graphify/obsidian/{fname}.md` — fix: use real output path parameter

**Module Organization**
- D-14: New `graphify/profile.py` module — profile loading, schema validation, default profile, deep merge, filename/frontmatter/tag helpers
- D-15: Built-in default profile stored as `_DEFAULT_PROFILE` Python dict constant in `profile.py` — no PyYAML needed for defaults
- D-16: `profile.py` is standalone with no imports from `export.py`. Added to `__init__.py` lazy imports. Bug fixes in `export.py` import helpers from `profile.py`

### Claude's Discretion
- Path traversal validation approach for profile-derived paths (MRG-04) — Claude picks the implementation pattern consistent with `security.py`
- Test file organization for `profile.py` — follows existing `test_<module>.py` convention

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROF-01 | User can place `.graphify/profile.yaml` in vault and graphify discovers it | Profile discovery via `Path(vault_dir) / ".graphify" / "profile.yaml"` — simple `exists()` check before `safe_load()` |
| PROF-02 | No vault profile → built-in default produces Ideaverse ACE-compatible output | `_DEFAULT_PROFILE` dict constant returned immediately; no PyYAML needed on this path |
| PROF-03 | Vault profile deep-merges over defaults (partial overrides) | Recursive dict merge: for each key if both values are dicts, recurse; otherwise user value wins |
| PROF-04 | Profile schema validation produces actionable error messages | `validate_profile(profile: dict) -> list[str]` following `validate.py` pattern exactly |
| PROF-06 | Profile YAML schema supports `folder_mapping`, `mapping_rules`, `merge`, `naming`, `obsidian` sections | Defined as `_VALID_TOP_LEVEL_KEYS` set; unknown top-level keys produce an error |
| MRG-04 | Profile-derived paths validated against path-traversal (no writing outside vault) | `Path(vault_dir).resolve()` + `Path(candidate).resolve().relative_to(vault_base)` — mirrors `security.py:validate_graph_path()` |
| OBS-01 | `graph.json` community color groups use `tag:community/Name` syntax (fix `tag:#`) | Current L672: `f"tag:#community/{label}"` → change to `f"tag:community/{safe_tag(label)}"` |
| OBS-02 | `graph.json` read-merge-write to preserve user settings | `json.loads(existing)` → merge graphify's `colorGroups` (filter by `tag:community/` prefix) → `json.dumps()` write-back |
| FIX-01 | Fix YAML frontmatter injection via node labels with special chars | `safe_frontmatter_value(v)`: if contains `:#[]{}'` wrap in `"..."`, escape any `"` inside → call from every `f'field: {value}'` in `to_obsidian()` |
| FIX-02 | Fix non-deterministic filename deduplication | Sort `G.nodes(data=True)` by `(data.get("source_file",""), data.get("label",""))` before the dedup loop in `to_obsidian()` and `to_canvas()` |
| FIX-03 | Fix shallow tag sanitization (handle `/`, `+`, digits-at-start) | `safe_tag(name)`: lowercase → replace `[^a-z0-9]+` with `-` → strip leading digits with `x` prefix → strip leading/trailing `-` |
| FIX-04 | Add NFC Unicode normalization to filenames | `unicodedata.normalize("NFC", text)` at start of `safe_filename()` |
| FIX-05 | Cap filename length at 200 chars | `truncate-to-192 + "_" + hashlib.sha256(full_name.encode()).hexdigest()[:8]` when `len(name) > 200` |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib: `unicodedata` | 3.10+ | NFC normalization for FIX-04 | Zero-dep, `unicodedata.normalize("NFC", text)` [VERIFIED: codebase stdlib] |
| Python stdlib: `hashlib` | 3.10+ | SHA256 hash suffix for FIX-05 length cap | `hashlib.sha256(s.encode()).hexdigest()[:8]` [VERIFIED: codebase stdlib] |
| Python stdlib: `json` | 3.10+ | graph.json read-merge-write for OBS-02 | Already used throughout `export.py` [VERIFIED: codebase] |
| Python stdlib: `pathlib.Path` | 3.10+ | Profile discovery and path-traversal validation | Already project standard [VERIFIED: codebase] |
| `PyYAML` | latest (optional) | Parse `.graphify/profile.yaml` | Only caller needing YAML parsing; stays optional per D-04 [ASSUMED: standard Python YAML library] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib: `re` | 3.10+ | Regex-based slug/tag sanitization | `safe_tag()`, `safe_filename()` slug core [VERIFIED: codebase] |
| Python stdlib: `html` | 3.10+ | HTML-escape for label embedding | Already imported in `export.py` [VERIFIED: codebase grep] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML `safe_load` | `ruamel.yaml` | ruamel preserves comments — not needed here, adds dep |
| `hashlib.sha256` | `zlib.crc32` | crc32 shorter but higher collision risk for 8-char suffix |
| `unicodedata.normalize("NFC")` | NFC + NFKC | NFKC changes width chars — D-07 says NFC only |

**Installation:** No new required dependencies. Optional only:
```bash
# Add to pyproject.toml [project.optional-dependencies]:
# obsidian = ["PyYAML"]
pip install -e ".[obsidian]"
```

**Version verification:** PyYAML not checked against registry — version unpin is consistent with project pattern (no version pins on optional deps). [ASSUMED: latest PyYAML is acceptable]

---

## Architecture Patterns

### New Module: `graphify/profile.py`

```
graphify/
├── profile.py          # NEW: profile loading + safety helpers (standalone)
├── export.py           # MODIFIED: import helpers from profile, patch 6 bugs
├── __init__.py         # MODIFIED: add load_profile, validate_profile to lazy map
└── pyproject.toml      # MODIFIED: add obsidian = ["PyYAML"] optional extra
```

### Pattern 1: Profile Discovery and Loading
**What:** Attempt to load `.graphify/profile.yaml` from the vault root; fall back to `_DEFAULT_PROFILE` dict if absent or PyYAML unavailable.
**When to use:** Called at start of `to_obsidian()` (Phase 5 wires it in; Phase 1 just makes it available as a standalone function).

```python
# Source: [VERIFIED: codebase — mirrors optional dep pattern in extract.py ImportError handling]
from __future__ import annotations
"""Profile loading, validation, deep merge, and safety helpers for Obsidian export."""

import hashlib
import re
import unicodedata
from pathlib import Path

_DEFAULT_PROFILE: dict = {
    "folder_mapping": {
        "moc": "Atlas/Maps/",
        "thing": "Atlas/Dots/Things/",
        "statement": "Atlas/Dots/Statements/",
        "source": "Atlas/Sources/",
        "default": "Atlas/Dots/",
    },
    "naming": {"convention": "title_case"},
    "merge": {"preserve_fields": ["rank", "mapState", "tags"]},
    "mapping_rules": [],
    "obsidian": {},
}


def load_profile(vault_dir: str | Path) -> dict:
    """Discover and load .graphify/profile.yaml, merging over built-in defaults.

    Falls back to _DEFAULT_PROFILE if no profile exists or PyYAML is not installed.
    """
    profile_path = Path(vault_dir) / ".graphify" / "profile.yaml"
    if not profile_path.exists():
        return _deep_merge(_DEFAULT_PROFILE, {})

    try:
        import yaml  # PyYAML optional
    except ImportError:
        print(
            "[graphify] PyYAML not installed — cannot read profile.yaml. "
            "Install with: pip install graphify[obsidian]",
            file=__import__("sys").stderr,
        )
        return _deep_merge(_DEFAULT_PROFILE, {})

    user_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    return _deep_merge(_DEFAULT_PROFILE, user_data)
```

### Pattern 2: Deep Merge
**What:** Recursively merge user dict over defaults — user dict keys win at every level, missing keys inherit defaults.
**When to use:** Always in `load_profile()`; never called externally.

```python
# Source: [ASSUMED — standard recursive dict merge pattern]
def _deep_merge(base: dict, override: dict) -> dict:
    """Return new dict with override recursively merged over base."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result
```

### Pattern 3: Profile Validation (follows `validate.py` exactly)
**What:** Return `list[str]` of all errors; empty list = valid.
**When to use:** After `yaml.safe_load()`, before merge.

```python
# Source: [VERIFIED: codebase — validate.py pattern]
_VALID_TOP_LEVEL_KEYS = {"folder_mapping", "naming", "merge", "mapping_rules", "obsidian"}

def validate_profile(profile: dict) -> list[str]:
    """Validate profile dict. Returns list of error strings; empty = valid."""
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]
    errors: list[str] = []
    for key in profile:
        if key not in _VALID_TOP_LEVEL_KEYS:
            errors.append(
                f"Unknown profile key '{key}' — valid keys: {sorted(_VALID_TOP_LEVEL_KEYS)}"
            )
    # ... per-section validation ...
    return errors
```

### Pattern 4: Path Traversal Guard (MRG-04)
**What:** Raise `ValueError` if a profile-derived path escapes the vault root. Mirrors `security.py:validate_graph_path()` exactly using `Path.resolve()` + `.relative_to()`.
**When to use:** Before writing any file whose folder came from `profile["folder_mapping"]`.

```python
# Source: [VERIFIED: codebase — security.py:validate_graph_path() L144-177]
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    """Raise ValueError if candidate escapes vault_dir."""
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    try:
        resolved.relative_to(vault_base)
    except ValueError:
        raise ValueError(
            f"Profile-derived path {candidate!r} would escape vault directory {vault_base}. "
            "Check folder_mapping values for path traversal sequences."
        )
    return resolved
```

### Pattern 5: Safety Helpers (D-08 through D-10)

```python
# Source: [VERIFIED: codebase — security.py:sanitize_label() as model, D-09/D-10 locked]
_YAML_SPECIAL = set(':#[]{}')

def safe_frontmatter_value(value: str) -> str:
    """Quote YAML frontmatter values containing special characters."""
    if any(c in value for c in _YAML_SPECIAL):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def safe_tag(name: str) -> str:
    """Slugify a community name for use as an Obsidian tag segment.

    Format: lowercase, spaces/specials → hyphens, leading digits → x-prefix.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if slug and slug[0].isdigit():
        slug = "x" + slug
    return slug or "community"


def safe_filename(label: str, max_len: int = 200) -> str:
    """Return a safe filename stem from label.

    Applies NFC normalization, strips OS-illegal chars, deduplication suffix
    handled by caller. Caps at max_len using hash suffix.
    """
    # NFC normalization (FIX-04)
    name = unicodedata.normalize("NFC", label)
    # Strip OS-illegal chars (current safe_name regex)
    name = re.sub(r'[\\/*?:"<>|#^[\]]', "", name).strip() or "unnamed"
    # Length cap (FIX-05)
    if len(name) > max_len:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = name[:max_len - 9] + "_" + suffix
    return name
```

### Pattern 6: Deterministic Dedup Sort (FIX-02)
**What:** Sort graph nodes by `(source_file, label)` before the filename assignment loop so dedup suffixes are stable across re-runs.
**When to use:** In `to_obsidian()` and `to_canvas()` dedup loops.

```python
# Source: [VERIFIED: codebase — existing dedup loop at export.py L466-474, sort is missing]
# Before:
for node_id, data in G.nodes(data=True):
    ...
# After (FIX-02):
for node_id, data in sorted(
    G.nodes(data=True),
    key=lambda nd: (nd[1].get("source_file", ""), nd[1].get("label", nd[0]))
):
    ...
```

### Pattern 7: graph.json Read-Merge-Write (OBS-01 + OBS-02)
**What:** Read existing graph.json → remove only `colorGroups` entries whose query starts with `tag:community/` → insert new community color groups with correct `tag:community/` syntax → write back preserving all other user config.

```python
# Source: [VERIFIED: codebase — current write-only at export.py L666-677; OBS-02 decision]
graph_json_path = obsidian_dir / "graph.json"
existing_config: dict = {}
if graph_json_path.exists():
    try:
        existing_config = json.loads(graph_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        pass  # corrupt file — overwrite cleanly

# Filter out graphify-owned entries, keep user entries
user_color_groups = [
    g for g in existing_config.get("colorGroups", [])
    if not g.get("query", "").startswith("tag:community/")
]
new_color_groups = [
    {
        "query": f"tag:community/{safe_tag(label)}",  # OBS-01 fix
        "color": {"a": 1, "rgb": int(COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)].lstrip("#"), 16)},
    }
    for cid, label in sorted((community_labels or {}).items())
]
existing_config["colorGroups"] = user_color_groups + new_color_groups
graph_json_path.write_text(json.dumps(existing_config, indent=2), encoding="utf-8")
```

### Anti-Patterns to Avoid
- **Importing `export.py` from `profile.py`:** D-16 explicitly prohibits this — would create a circular dependency when Phase 5 wires `load_profile()` into `to_obsidian()`.
- **Raising on first validation error:** D-03 requires collecting all errors — never `raise` inside `validate_profile()`, always append to `errors` list.
- **Calling `yaml.load()` instead of `yaml.safe_load()`:** `yaml.load()` allows arbitrary Python object instantiation — always use `safe_load()` for untrusted vault files.
- **Checking `if not pyyaml:` with `importlib.util.find_spec`:** Project pattern is `try: import yaml except ImportError:` — consistent with graspologic fallback in `cluster.py`.
- **NFC+NFKC normalization:** D-07 says NFC only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML deserialization | Custom YAML parser | `yaml.safe_load()` (PyYAML) | YAML spec edge cases (multiline, anchors, null coercion) |
| Path traversal detection | String-based `../` check | `Path.resolve() + .relative_to()` | Symlinks, `%2e%2e`, encoded forms bypass string checks |
| Unicode filename normalization | Manual code-point table | `unicodedata.normalize("NFC")` | stdlib handles all Unicode blocks |
| 8-char hash suffix | CRC or random | `hashlib.sha256().hexdigest()[:8]` | Deterministic, collision-resistant, stdlib |

**Key insight:** The project already has the patterns — `validate_graph_path()` in `security.py` is the exact path-traversal model. Do not deviate from it.

---

## Common Pitfalls

### Pitfall 1: PyYAML `None` return on empty file
**What goes wrong:** `yaml.safe_load("")` returns `None`, not `{}`. Code does `profile.items()` and crashes.
**Why it happens:** Empty YAML document is a valid null document.
**How to avoid:** `user_data = yaml.safe_load(text) or {}` — the `or {}` guard is required.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'items'` in profile loading.

### Pitfall 2: `relative_to()` raises on pre-Python 3.12 with non-subpath
**What goes wrong:** On Python 3.10/3.11, `Path.relative_to()` raises `ValueError` (correct behavior). On 3.12+ it has a `walk_up` param. Code that catches the wrong exception silently allows traversal.
**Why it happens:** Standard exception handling — both Python 3.10 and 3.12 raise `ValueError` for non-subpaths, which is what we want to catch. No version difference for basic usage.
**How to avoid:** Always `try: resolved.relative_to(base) except ValueError: raise ValueError(...)` — the existing `security.py` pattern is correct for 3.10+.
**Warning signs:** None — the pattern is already proven in `security.py`.

### Pitfall 3: Frontmatter quote wrapping breaks multiline values
**What goes wrong:** A node label like `foo: bar\nbaz` contains a newline. Wrapping in `"..."` with a literal newline produces invalid YAML.
**Why it happens:** YAML double-quoted strings can have escaped newlines (`\n`) but not literal ones.
**How to avoid:** In `safe_frontmatter_value()`, also replace `\n` and `\r` with space before wrapping, or strip them. Single-line check + strip is sufficient since node labels from AST extraction never legitimately span lines.
**Warning signs:** Obsidian shows frontmatter as broken/unreadable properties.

### Pitfall 4: Dedup suffix collision across functions
**What goes wrong:** `to_obsidian()` and `to_canvas()` each have their own independent dedup loops. After FIX-02 both must use the same sort key or canvas wikilinks point at wrong files.
**Why it happens:** Canvas calls `to_obsidian()` separately (or its own dedup) — if sort order differs, `_2` suffix assignments diverge.
**How to avoid:** `to_canvas()` already accepts `node_filenames` parameter — the caller should pass the same `node_filename` dict built by `to_obsidian()`. When building independently, the same sort key must be used.
**Warning signs:** Canvas file cards point to `.md` files that don't exist in the vault.

### Pitfall 5: FIX-06 — `to_canvas()` output path parameter
**What goes wrong:** Line 809 uses `f"graphify/obsidian/{fname}.md"` as the file path embedded in the canvas JSON. This is a hardcoded prefix, not the actual output directory.
**Why it happens:** The `output_path` parameter is the canvas `.canvas` file path, not the vault root. The vault root must be derived from `output_path`'s parent.
**How to avoid:** Derive vault root as `Path(output_path).parent` (or accept vault_dir parameter). Use `str(Path(vault_root) / fname) + ".md"` as the file path value. Verify by checking what `output_path` is when called from the CLI.

### Pitfall 6: `tag:community/Name` vs `community/name` — two different contexts
**What goes wrong:** Confusing the graph.json query syntax (`tag:community/slug`) with the YAML frontmatter tag value (`community/slug`). Using `tag:` prefix in frontmatter produces broken Obsidian tags.
**Why it happens:** Obsidian graph.json `colorGroups[].query` uses Obsidian search query syntax (`tag:X`), but YAML frontmatter `tags:` list uses bare tag paths (`community/slug`).
**How to avoid:** `safe_tag()` returns the bare slug (no `tag:` prefix). Only the graph.json `query` field prepends `tag:`.
**Warning signs:** Tags in notes display as `tag:community/X` literally instead of being recognized as tags.

---

## Code Examples

### Existing: `_make_id()` — slug reference for `safe_filename()` core
```python
# Source: [VERIFIED: graphify/extract.py L14-18]
def _make_id(*parts: str) -> str:
    combined = "_".join(p.strip("_.") for p in parts if p)
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", combined)
    return cleaned.strip("_").lower()
```

### Existing: `validate_extraction()` — exact template for `validate_profile()`
```python
# Source: [VERIFIED: graphify/validate.py L10-63]
def validate_extraction(data: dict) -> list[str]:
    errors: list[str] = []
    # ... append errors, never raise ...
    return errors
```

### Existing: `validate_graph_path()` — exact template for `validate_vault_path()`
```python
# Source: [VERIFIED: graphify/security.py L144-177]
resolved = Path(path).resolve()
try:
    resolved.relative_to(base)
except ValueError:
    raise ValueError(f"Path {path!r} escapes ...")
```

### Existing: `sanitize_label()` — model for safety helper structure
```python
# Source: [VERIFIED: graphify/security.py L188-197]
def sanitize_label(text: str) -> str:
    text = _CONTROL_CHAR_RE.sub("", text)
    if len(text) > _MAX_LABEL_LEN:
        text = text[:_MAX_LABEL_LEN]
    return text
```

### Existing: `__init__.py` lazy import — pattern for adding `load_profile`
```python
# Source: [VERIFIED: graphify/__init__.py L1-28]
_map = {
    "load_profile": ("graphify.profile", "load_profile"),
    "validate_profile": ("graphify.profile", "validate_profile"),
    # ... existing entries ...
}
```

### Existing: Optional dep try/except — pattern for PyYAML
```python
# Source: [VERIFIED: graphify/cluster.py — graspologic optional dep pattern]
try:
    import yaml
except ImportError:
    print("[graphify] PyYAML not installed — ...", file=sys.stderr)
    return _deep_merge(_DEFAULT_PROFILE, {})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline `safe_name()` lambda in `to_obsidian()` | Extracted `safe_filename()` in `profile.py` | Phase 1 (this phase) | Helpers reusable by Phase 2-5 |
| Write-only `graph.json` (overwrites user settings) | Read-merge-write pattern | Phase 1 (this phase) | OBS-02: preserves user's Obsidian config |
| `tag:#community/Name` in graph.json | `tag:community/Name` (Obsidian correct syntax) | Phase 1 (this phase) | OBS-01: fixes non-functional color groups |
| Non-deterministic filename dedup (dict iteration order) | Sorted `(source_file, label)` before dedup | Phase 1 (this phase) | FIX-02: stable re-runs |

**Deprecated/outdated:**
- `safe_name()` inline lambda in `to_obsidian()` and `to_canvas()`: replaced by `safe_filename()` from `profile.py` — both lambdas are removed and callers import the helper instead.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PyYAML `safe_load` is the correct function (not `full_load`) | Standard Stack | Low — `safe_load` is well-established for config files; project docs say "no Jinja2, no RCE risk" |
| A2 | Latest PyYAML version is acceptable (no version pin) | Standard Stack | Low — project has no version pins on optional deps; PyYAML API is stable |
| A3 | `to_canvas()` vault root is `Path(output_path).parent` for FIX-06 | Architecture Patterns (Pitfall 5) | Medium — caller context not fully traced; should verify in `__main__.py` how `to_canvas()` is called |

---

## Open Questions

1. **FIX-06: What is the correct vault root derivation for `to_canvas()`?**
   - What we know: `output_path` is the `.canvas` file path (L836: `Path(output_path).write_text(...)`)
   - What's unclear: Is the `.canvas` file always in the vault root, or in a subdirectory?
   - Recommendation: Check `__main__.py` call site for `to_canvas()` before finalizing FIX-06 to pick the right path derivation. Low risk — the fix is small regardless.

2. **`_DEFAULT_PROFILE` Ideaverse ACE folder structure: exact paths**
   - What we know: CONTEXT.md says "Default profile uses Ideaverse ACE folder structure (`Atlas/Maps/`, `Atlas/Dots/Things/`, etc.) as specified in PROJECT.md"
   - What's unclear: PROJECT.md was referenced but not read — the exact default folder paths for `statement`, `source`, `default` should be confirmed
   - Recommendation: Read `.planning/PROJECT.md` during plan authoring to confirm the full folder_mapping defaults before writing `_DEFAULT_PROFILE`.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 1 is pure Python code/config changes. No external services, CLI tools, or runtimes beyond Python 3.10+ (already confirmed CI target). PyYAML availability is handled by the optional-dep fallback path in the code itself.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version unspecified in pyproject.toml) |
| Config file | none — pytest discovers `tests/` directory |
| Quick run command | `pytest tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-01 | `load_profile()` discovers `.graphify/profile.yaml` from vault dir | unit | `pytest tests/test_profile.py::test_load_profile_discovers_yaml -q` | ❌ Wave 0 |
| PROF-02 | `load_profile()` returns `_DEFAULT_PROFILE` when no yaml present | unit | `pytest tests/test_profile.py::test_load_profile_defaults -q` | ❌ Wave 0 |
| PROF-03 | Deep merge — partial override preserves other keys | unit | `pytest tests/test_profile.py::test_deep_merge_partial -q` | ❌ Wave 0 |
| PROF-04 | `validate_profile()` returns errors for unknown keys | unit | `pytest tests/test_profile.py::test_validate_profile_unknown_key -q` | ❌ Wave 0 |
| PROF-04 | `validate_profile()` collects ALL errors (not fail-on-first) | unit | `pytest tests/test_profile.py::test_validate_profile_collects_all -q` | ❌ Wave 0 |
| PROF-06 | Valid profile with all 5 sections passes validation | unit | `pytest tests/test_profile.py::test_validate_profile_valid -q` | ❌ Wave 0 |
| MRG-04 | `validate_vault_path()` rejects `../` traversal | unit | `pytest tests/test_profile.py::test_validate_vault_path_traversal -q` | ❌ Wave 0 |
| MRG-04 | `validate_vault_path()` accepts valid sub-path | unit | `pytest tests/test_profile.py::test_validate_vault_path_valid -q` | ❌ Wave 0 |
| OBS-01 | `graph.json` color groups use `tag:community/` not `tag:#` | unit | `pytest tests/test_export.py::test_obsidian_graph_json_tag_syntax -q` | ❌ Wave 0 |
| OBS-02 | Re-run preserves user's existing graph.json keys | unit | `pytest tests/test_export.py::test_obsidian_graph_json_merge -q` | ❌ Wave 0 |
| FIX-01 | `safe_frontmatter_value()` wraps colon-containing values | unit | `pytest tests/test_profile.py::test_safe_frontmatter_value_colon -q` | ❌ Wave 0 |
| FIX-02 | `to_obsidian()` filename dedup is stable across two runs | unit | `pytest tests/test_export.py::test_obsidian_deterministic_filenames -q` | ❌ Wave 0 |
| FIX-03 | `safe_tag()` handles `/`, `+`, leading digits | unit | `pytest tests/test_profile.py::test_safe_tag_special_chars -q` | ❌ Wave 0 |
| FIX-04 | `safe_filename()` NFC-normalizes input | unit | `pytest tests/test_profile.py::test_safe_filename_nfc -q` | ❌ Wave 0 |
| FIX-05 | `safe_filename()` caps at 200 chars with hash suffix | unit | `pytest tests/test_profile.py::test_safe_filename_length_cap -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_profile.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_profile.py` — covers PROF-01 through PROF-04, PROF-06, MRG-04, FIX-01, FIX-03, FIX-04, FIX-05 (all profile.py unit tests)
- [ ] `tests/test_export.py` — add test cases for OBS-01, OBS-02, FIX-02 (Obsidian-specific export tests — file exists but has no `to_obsidian` tests yet)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | yes (path traversal) | `Path.resolve() + .relative_to()` — mirrors `security.py:validate_graph_path()` |
| V5 Input Validation | yes | `validate_profile()` returns error list; `safe_frontmatter_value()`, `safe_tag()`, `safe_filename()` sanitize node labels |
| V6 Cryptography | no (hash is for collision resistance, not security) | `hashlib.sha256` for deterministic filename suffix only |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `folder_mapping` in profile | Tampering / EoP | `validate_vault_path()` using `Path.resolve() + relative_to()` |
| YAML frontmatter injection (FIX-01) | Tampering | `safe_frontmatter_value()` quote-wrapping |
| YAML deserialization of vault-supplied profile | Tampering / RCE | `yaml.safe_load()` only — never `yaml.load()` |
| Tag injection via community names (FIX-03) | Tampering | `safe_tag()` slugification — only `[a-z0-9-]` pass through |

---

## Sources

### Primary (HIGH confidence)
- `graphify/export.py` L440-679 — Current `to_obsidian()` implementation; bugs FIX-01 through FIX-05 verified by direct code read
- `graphify/export.py` L682-836 — Current `to_canvas()` implementation; FIX-06 hardcoded path at L809 verified
- `graphify/security.py` L144-177 — `validate_graph_path()` as template for MRG-04
- `graphify/security.py` L188-197 — `sanitize_label()` as model for helper structure
- `graphify/validate.py` L10-63 — `validate_extraction()` as exact template for `validate_profile()`
- `graphify/extract.py` L14-18 — `_make_id()` as reference for slug core
- `graphify/__init__.py` L1-28 — Lazy import pattern for new module registration
- `graphify/tests/test_export.py` — Existing test coverage (no `to_obsidian` tests — all are Wave 0 gaps)
- `pyproject.toml` L43-50 — Optional dep table (confirms `obsidian` extra does not exist yet)

### Secondary (MEDIUM confidence)
- `graphify/tests/test_pipeline.py` L87-91 — Integration smoke test for `to_obsidian()` (confirms function interface)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or PyYAML; patterns verified directly in codebase
- Architecture: HIGH — every pattern mirrors an existing function in the same codebase; no speculation
- Pitfalls: HIGH — six pitfalls derived from direct code reading of `to_obsidian()` / `to_canvas()`; two are MEDIUM (FIX-06 path derivation, frontmatter multiline edge case)

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable Python stdlib domain; PyYAML API has not changed in years)
