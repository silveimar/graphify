"""Profile loading, validation, deep merge, and safety helpers for Obsidian export."""
from __future__ import annotations

import datetime
import hashlib
import re
import sys
import unicodedata
from pathlib import Path


# ---------------------------------------------------------------------------
# Default profile — Ideaverse ACE folder structure (D-15)
# ---------------------------------------------------------------------------

_DEFAULT_PROFILE: dict = {
    "folder_mapping": {
        "moc": "Atlas/Maps/",
        "thing": "Atlas/Dots/Things/",
        "statement": "Atlas/Dots/Statements/",
        "person": "Atlas/Dots/People/",
        "source": "Atlas/Sources/",
        "default": "Atlas/Dots/",
    },
    "naming": {"convention": "title_case"},
    "merge": {
        "strategy": "update",
        "preserve_fields": ["rank", "mapState", "tags"],
    },
    "mapping_rules": [],
    "obsidian": {
        "atlas_root": "Atlas",
        "dataview": {
            "moc_query": "TABLE file.folder as Folder, type, source_file\nFROM #community/${community_tag}\nSORT file.name ASC",
        },
    },
}

_VALID_TOP_LEVEL_KEYS = {"folder_mapping", "naming", "merge", "mapping_rules", "obsidian"}

_VALID_NAMING_CONVENTIONS = {"title_case", "kebab-case", "preserve"}

_VALID_MERGE_STRATEGIES = {"update", "skip", "replace"}

# Characters that require quoting when present anywhere in a YAML scalar.
# Covers flow-context indicators and structural chars (WR-01).
_YAML_SPECIAL = set(':#[]{},')

# Characters that require quoting when they appear as the FIRST character
# of a YAML scalar — they are interpreted as block/directive/anchor markers.
_YAML_LEADING_INDICATORS = set('-?!&*|>%@`')

# Strings that YAML 1.1 (used by many parsers) interprets as bool/null
# rather than plain strings, regardless of case.
_YAML_RESERVED_WORDS: frozenset[str] = frozenset({
    "yes", "no", "true", "false", "null", "on", "off", "~",
})

# Numeric-looking scalars that YAML parses as int, float, or octal.
_YAML_NUMERIC_RE = re.compile(
    r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$"   # int / float / scientific
    r"|^0x[0-9a-fA-F]+$"                            # hex
    r"|^0o[0-7]+$"                                  # octal (YAML 1.2)
    r"|^0[0-7]+$"                                   # octal (YAML 1.1)
    r"|^\.\w+$"                                     # .inf / .nan
)

# Control characters other than ordinary space that corrupt YAML scalars.
_YAML_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x85\u2028\u2029]")


# ---------------------------------------------------------------------------
# Deep merge (D-02)
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*. Override wins at leaf level."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Profile loading (PROF-01, PROF-02, D-04)
# ---------------------------------------------------------------------------

def load_profile(vault_dir: str | Path) -> dict:
    """Discover and load a vault profile, merging over built-in defaults.

    Returns the merged profile dict. Falls back to defaults when no
    profile.yaml exists or when PyYAML is not installed.
    """
    profile_path = Path(vault_dir) / ".graphify" / "profile.yaml"
    if not profile_path.exists():
        return _deep_merge(_DEFAULT_PROFILE, {})

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print(
            "[graphify] PyYAML not installed — cannot read profile.yaml. "
            "Install with: pip install graphifyy[obsidian]",
            file=sys.stderr,
        )
        return _deep_merge(_DEFAULT_PROFILE, {})

    # Guard against empty YAML returning None (Pitfall 1)
    user_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}

    errors = validate_profile(user_data)
    if errors:
        for err in errors:
            print(f"[graphify] profile error: {err}", file=sys.stderr)
        return _deep_merge(_DEFAULT_PROFILE, {})

    return _deep_merge(_DEFAULT_PROFILE, user_data)


# ---------------------------------------------------------------------------
# Profile validation (PROF-04, D-03)
# ---------------------------------------------------------------------------

def validate_profile(profile: dict) -> list[str]:
    """Validate a profile dict. Returns a list of error strings — empty means valid."""
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]

    errors: list[str] = []

    # Unknown top-level keys
    for key in profile:
        if key not in _VALID_TOP_LEVEL_KEYS:
            errors.append(f"Unknown profile key '{key}' — valid keys are: {sorted(_VALID_TOP_LEVEL_KEYS)}")

    # naming section
    naming = profile.get("naming")
    if naming is not None:
        if not isinstance(naming, dict):
            errors.append("'naming' must be a mapping (dict)")
        else:
            convention = naming.get("convention")
            if convention is not None and convention not in _VALID_NAMING_CONVENTIONS:
                errors.append(
                    f"Invalid naming convention '{convention}' — "
                    f"valid values are: {sorted(_VALID_NAMING_CONVENTIONS)}"
                )

    # merge section
    merge = profile.get("merge")
    if merge is not None:
        if not isinstance(merge, dict):
            errors.append("'merge' must be a mapping (dict)")
        else:
            strategy = merge.get("strategy")
            if strategy is not None and strategy not in _VALID_MERGE_STRATEGIES:
                errors.append(
                    f"Invalid merge strategy '{strategy}' — "
                    f"valid values are: {sorted(_VALID_MERGE_STRATEGIES)}"
                )
            preserve = merge.get("preserve_fields")
            if preserve is not None and not isinstance(preserve, list):
                errors.append("'merge.preserve_fields' must be a list")

    # folder_mapping section
    folder_mapping = profile.get("folder_mapping")
    if folder_mapping is not None:
        if not isinstance(folder_mapping, dict):
            errors.append("'folder_mapping' must be a mapping (dict)")
        else:
            for name, path_val in folder_mapping.items():
                if not isinstance(path_val, str):
                    errors.append(f"folder_mapping.{name} must be a string, got {type(path_val).__name__}")
                elif ".." in path_val:
                    errors.append(
                        f"folder_mapping.{name} contains '..' — "
                        "path traversal sequences are not allowed in folder mappings"
                    )
                elif Path(path_val).is_absolute():
                    # Absolute paths escape the vault entirely (WR-07).
                    # validate_vault_path catches these at use-time, but
                    # rejecting them early gives a clearer error message.
                    errors.append(
                        f"folder_mapping.{name} is an absolute path — "
                        "only relative paths are allowed in folder mappings"
                    )
                elif path_val.startswith("~"):
                    # Home-expansion would also escape the vault (WR-07).
                    errors.append(
                        f"folder_mapping.{name} starts with '~' — "
                        "home-relative paths are not allowed in folder mappings"
                    )

    # mapping_rules section
    mapping_rules = profile.get("mapping_rules")
    if mapping_rules is not None and not isinstance(mapping_rules, list):
        errors.append("'mapping_rules' must be a list")

    return errors


# ---------------------------------------------------------------------------
# Vault path validation (MRG-04)
# ---------------------------------------------------------------------------

def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    """Resolve *candidate* relative to *vault_dir* and verify it stays inside.

    Raises ValueError if the resolved path escapes the vault directory.
    """
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


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def safe_frontmatter_value(value: str) -> str:
    """Sanitize a value for use in YAML frontmatter.

    Wraps in double quotes when the value would be misinterpreted by YAML
    parsers. Covers (WR-01):
      - Structural characters: `:#[]{},`
      - Leading indicator characters: -?!&*|>%@` (backtick)
      - YAML 1.1 reserved words: yes/no/true/false/null/on/off/~
      - Numeric-looking strings parsed as int/float/octal/hex
      - Newlines and other control characters (stripped before quoting check)

    Replaces newlines/CR with spaces and strips other control chars to
    prevent multi-line injection (Pitfall 3).
    """
    # Replace newlines with spaces (Pitfall 3)
    value = value.replace("\n", " ").replace("\r", " ")
    # Strip remaining control characters (tab and others left as-is would
    # corrupt the YAML stream)
    value = _YAML_CONTROL_RE.sub("", value)

    needs_quoting = (
        # Any structural/flow-context character anywhere in the value
        any(ch in _YAML_SPECIAL for ch in value)
        # Leading indicator character at position 0
        or (value and value[0] in _YAML_LEADING_INDICATORS)
        # Reserved word (case-insensitive)
        or value.lower() in _YAML_RESERVED_WORDS
        # Looks like a number, hex, octal, .inf, or .nan
        or bool(_YAML_NUMERIC_RE.match(value))
    )

    if needs_quoting:
        # Escape internal double quotes before wrapping
        value = value.replace('"', '\\"')
        return f'"{value}"'

    return value


def safe_tag(name: str) -> str:
    """Slugify a community name into a valid Obsidian tag component.

    Produces lowercase, hyphen-separated strings. Leading digits get
    an 'x' prefix. Empty input returns 'community'.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if slug and slug[0].isdigit():
        slug = "x" + slug
    return slug or "community"


def safe_filename(label: str, max_len: int = 200) -> str:
    """Sanitize a label for use as a filename.

    Applies NFC Unicode normalization (FIX-04), strips OS-illegal characters,
    and caps length with a hash suffix to avoid collisions (FIX-05, D-06).
    """
    name = unicodedata.normalize("NFC", label)
    # Strip OS-illegal, Obsidian-problematic, and control characters.
    # Control chars (including \n, \r, \t) break wikilink targets — a label
    # like "line1\nline2" would otherwise produce [[line1\nline2|...]] which
    # Obsidian cannot parse (UAT-05 gap adjacent to CR-01 alias fix).
    name = re.sub(
        r'[\\/*?:"<>|#^[\]\x00-\x1f\x7f\u0085\u2028\u2029]', "", name
    ).strip() or "unnamed"
    if len(name) > max_len:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = name[:max_len - 9] + "_" + suffix
    return name


def _dump_frontmatter(fields: dict) -> str:
    """Emit a YAML frontmatter block including --- delimiters.

    Rules:
      - Preserves dict insertion order
      - None values are skipped (not emitted)
      - list → YAML block list (`key:\\n  - item`) with every item passed
        through safe_frontmatter_value(str(item))
      - bool → `true` / `false` (lowercase); checked before int because
        bool is a subclass of int in Python
      - int → unquoted integer literal
      - float → `f"{v:.2f}"` unquoted
      - datetime.date → `v.isoformat()` unquoted (YYYY-MM-DD)
      - str / other → `safe_frontmatter_value(str(value))`
    """
    lines: list[str] = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {safe_frontmatter_value(str(item))}")
        elif isinstance(value, bool):
            # bool before int: isinstance(True, int) is True in Python
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, float):
            lines.append(f"{key}: {value:.2f}")
        elif isinstance(value, datetime.date):
            lines.append(f"{key}: {value.isoformat()}")
        else:
            lines.append(f"{key}: {safe_frontmatter_value(str(value))}")
    lines.append("---")
    return "\n".join(lines)
