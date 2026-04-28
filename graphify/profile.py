"""Profile loading, validation, deep merge, and safety helpers for Obsidian export."""
from __future__ import annotations

import datetime
import fnmatch  # noqa: F401  # used by Plan 30-02 community-template matcher
import hashlib
import re
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple


class PreflightResult(NamedTuple):
    """Return value for validate_profile_preflight (D-77, D-77a).

    Supports attribute access (result.rule_count) AND tuple unpacking
    (errors, warnings, *_ = result). NamedTuple is immutable and costs
    nothing over a plain tuple at runtime.

    Fields:
      errors:          schema + template errors (layers 1 + 2) — non-empty → skill exits 1
      warnings:        dead-rule + path-safety findings (layers 3 + 4) — non-fatal
      rule_count:      len(merged_profile["mapping_rules"]) at preflight time
      template_count:  number of .graphify/templates/<type>.md overrides that PASSED layer 2 validation
    """
    errors: list[str]
    warnings: list[str]
    rule_count: int
    template_count: int
    chain: list[Path] = []                     # Phase 30, D-14
    provenance: dict[str, Path] = {}           # Phase 30, D-14, D-15
    community_template_rules: list[dict] = []  # Phase 30, D-14, D-17


class ResolvedProfile(NamedTuple):
    """Output of `_resolve_profile_chain` — composed profile + provenance.

    Phase 30 / CFG-02. Distinct from `PreflightResult` because the resolver
    runs BEFORE schema validation and BEFORE merge with `_DEFAULT_PROFILE`;
    its `composed` is the user's intent expressed as a single dict, not yet
    layered onto graphify's defaults.

    Fields:
      composed:                  fully-merged profile dict (NOT yet merged with _DEFAULT_PROFILE)
      chain:                     resolution order, root-ancestor first (post-order append)
      provenance:                dotted-key -> Path of the file that contributed the leaf
      errors:                    cycle/depth/path/parse errors (empty -> success)
      community_template_rules:  echo of composed["community_templates"] or []
    """
    composed: dict
    chain: list[Path]
    provenance: dict[str, Path]
    errors: list[str]
    community_template_rules: list[dict]


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
        # D-27 + D-65: `created` must survive re-runs — set ONCE at first
        # CREATE by Phase 2, never rewritten by Phase 4 merge UPDATE path.
        "preserve_fields": ["rank", "mapState", "tags", "created"],
        # D-65: user overrides merge-module's built-in _DEFAULT_FIELD_POLICIES
        # table. Empty default means Plan 03's table wins unchanged.
        "field_policies": {},
    },
    "mapping_rules": [],
    "obsidian": {
        "atlas_root": "Atlas",
        "dataview": {
            "moc_query": "TABLE file.folder as Folder, type, source_file\nFROM #community/${community_tag}\nSORT file.name ASC",
        },
    },
    # Phase 3 extensions (D-48, D-52)
    "topology": {"god_node": {"top_n": 10}},
    "mapping": {"moc_threshold": 3},
    # Phase 19 extensions (D-17, D-18)
    "tag_taxonomy": {
        "garden": ["plant", "cultivate", "probe", "repot", "revitalize", "revisit", "question"],
        "graph": ["component", "domain", "workflow", "decision", "concept", "integration", "service", "dataset", "team", "extracted", "inferred", "ambiguous"],
        "source": ["confluence", "readme", "doc", "code", "paper", "pdf", "jira", "slack", "github", "notion", "obsidian", "web"],
        "tech": ["python", "typescript", "javascript", "go", "rust", "java", "sql", "graphql", "docker", "k8s"],
    },
    "profile_sync": {"auto_update": True},
    # Phase 21 extensions (PROF-01..PROF-04): 6 built-in diagram type defaults.
    # Phase 22 (D-05): each entry carries layout_type (1:1 with name) and
    # output_path so the Excalidraw skill / pure-Python fallback can dispatch.
    "diagram_types": [
        {"name": "architecture", "template_path": "Excalidraw/Templates/architecture.excalidraw.md",
         "trigger_node_types": ["module", "service"], "trigger_tags": ["architecture"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-architecture",
         "layout_type": "architecture", "output_path": "Excalidraw/Diagrams/"},
        {"name": "workflow", "template_path": "Excalidraw/Templates/workflow.excalidraw.md",
         "trigger_node_types": ["function", "process"], "trigger_tags": ["workflow", "pipeline"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-workflow",
         "layout_type": "workflow", "output_path": "Excalidraw/Diagrams/"},
        {"name": "repository-components", "template_path": "Excalidraw/Templates/repository-components.excalidraw.md",
         "trigger_node_types": ["module", "file"], "trigger_tags": ["repo", "components"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-repository-components",
         "layout_type": "repository-components", "output_path": "Excalidraw/Diagrams/"},
        {"name": "mind-map", "template_path": "Excalidraw/Templates/mind-map.excalidraw.md",
         "trigger_node_types": ["concept"], "trigger_tags": ["mind-map", "brainstorm"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-mind-map",
         "layout_type": "mind-map", "output_path": "Excalidraw/Diagrams/"},
        {"name": "cuadro-sinoptico", "template_path": "Excalidraw/Templates/cuadro-sinoptico.excalidraw.md",
         "trigger_node_types": ["concept", "category"], "trigger_tags": ["synoptic", "cuadro-sinoptico"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-cuadro-sinoptico",
         "layout_type": "cuadro-sinoptico", "output_path": "Excalidraw/Diagrams/"},
        {"name": "glossary-graph", "template_path": "Excalidraw/Templates/glossary-graph.excalidraw.md",
         "trigger_node_types": ["concept", "term"], "trigger_tags": ["glossary", "definitions"],
         "min_main_nodes": 3, "naming_pattern": "{topic}-glossary-graph",
         "layout_type": "glossary-graph", "output_path": "Excalidraw/Diagrams/"},
    ],
}

_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output",
    "extends", "includes", "community_templates",  # Phase 30 (CFG-02 / CFG-03)
}

_VALID_NAMING_CONVENTIONS = {"title_case", "kebab-case", "preserve"}

# Phase 27 (D-01, VAULT-10): valid modes for the output: block. Schema-only
# check; sibling-of-vault paths are further validated at use-time via
# validate_sibling_path() since vault_dir is unknown at static-validation time.
_VALID_OUTPUT_MODES = {"vault-relative", "absolute", "sibling-of-vault"}

_VALID_MERGE_STRATEGIES = {"update", "skip", "replace"}

# Phase 4 D-64: per-key merge policy modes. `replace` overwrites scalar on
# every UPDATE, `union` deduplicates list contributions from both sides,
# `preserve` never touches the key. Unknown keys at dispatch time default to
# `preserve` (conservative) — Plan 03's policy dispatcher enforces that.
_VALID_FIELD_POLICY_MODES: frozenset[str] = frozenset({"replace", "union", "preserve"})

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


def _deep_merge_with_provenance(
    base: dict,
    override: dict,
    source_path: Path,
    provenance: dict[str, Path],
    _prefix: str = "",
) -> dict:
    """Like ``_deep_merge`` but records ``source_path`` for every leaf write.

    Phase 30 (CFG-02). Mirrors the recursion structure of ``_deep_merge``
    line-for-line; the only addition is the ``provenance`` side-effect at
    leaf-level writes. Dict-typed leaves recurse with a dotted prefix; every
    other type (scalar, list, None) records under the dotted key as a single
    leaf — list-typed leaves are NOT indexed (R7).

    Contract: never mutates ``base`` (R3). The ``result = base.copy()``
    first line preserves the same shallow-copy guarantee as ``_deep_merge``.
    """
    result = base.copy()
    for key, value in override.items():
        dotted = f"{_prefix}{key}" if _prefix else key
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_with_provenance(
                result[key], value, source_path, provenance, _prefix=f"{dotted}."
            )
        else:
            result[key] = value
            provenance[dotted] = source_path
    return result


# ---------------------------------------------------------------------------
# Profile composition resolver (Phase 30, CFG-02)
# ---------------------------------------------------------------------------

# Hard cap on extends/includes recursion depth (D-05). 8 layers covers any
# realistic vault-framework fusion (Ideaverse → fusion → mixin × 5) while
# bounding stack growth and keeping cycle-error messages legible.
_MAX_PROFILE_DEPTH = 8


def _resolve_profile_chain(entry_path: Path, vault_dir: Path) -> "ResolvedProfile":
    """Walk an extends/includes chain rooted at *entry_path* and return a composed profile.

    Phase 30 / CFG-02. Resolution order per fragment:
        1. extends parent (single, recursive — root ancestor processed first)
        2. includes list (left-to-right, last-wins)
        3. own fields (override everything above)

    Failure modes (each appends to ``errors`` and aborts that branch — caller
    receives a partial composition + the error list):
        * recursion depth exceeded ``_MAX_PROFILE_DEPTH``
        * fragment path escapes ``vault_dir/.graphify/`` (absolute, ../, symlink)
        * extends/includes cycle (direct or indirect)
        * fragment file missing
        * YAML parse error
        * fragment top-level not a mapping

    Path resolution is sibling-relative (D-06): ``extends: foo.yaml`` from
    ``.graphify/bases/fusion.yaml`` resolves to ``.graphify/bases/foo.yaml``,
    NOT ``.graphify/foo.yaml``.

    Two stack-local structures track the descending path (R8):
        * ``descending`` — set, O(1) cycle membership test
        * ``frame_chain`` — list, ordered names rendered in cycle errors
    Both are populated/cleared at the same site under try/finally.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return ResolvedProfile(
            composed={},
            chain=[],
            provenance={},
            errors=[
                "PyYAML not installed — cannot read profile.yaml. "
                "Install with: pip install graphifyy[obsidian]"
            ],
            community_template_rules=[],
        )

    errors: list[str] = []
    chain: list[Path] = []
    provenance: dict[str, Path] = {}
    graphify_root = (Path(vault_dir) / ".graphify").resolve()

    def _is_inside_graphify(canonical: Path) -> bool:
        # Path.is_relative_to is 3.9+ but raises on some odd inputs in 3.10
        # (non-existent paths handle fine post-resolve, but we wrap defensively).
        try:
            return canonical.is_relative_to(graphify_root)
        except (ValueError, TypeError):
            return False

    def _load_one(
        path: Path,
        depth: int,
        descending: set[Path],
        frame_chain: list[Path],
    ) -> dict | None:
        # 1. Depth check
        if depth > _MAX_PROFILE_DEPTH:
            errors.append(
                f"extends/includes recursion depth exceeded 8 levels at {path.name}"
            )
            return None

        # 2. Path confinement (T-30-01)
        try:
            canonical = path.resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(f"failed to resolve fragment path {path}: {exc}")
            return None
        if not _is_inside_graphify(canonical):
            errors.append(f"fragment path {path} escapes .graphify/")
            return None

        # 3. Cycle check (uses frame_chain for the rendered error chain)
        if canonical in descending:
            chain_arrows = " → ".join(p.name for p in frame_chain + [canonical])
            errors.append(f"extends/includes cycle detected: {chain_arrows}")
            return None

        # 4. Existence
        if not canonical.exists():
            errors.append(f"fragment not found: {canonical.name}")
            return None

        # 5. YAML parse
        try:
            data = yaml.safe_load(canonical.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse error in {canonical.name}: {exc}")
            return None
        if not isinstance(data, dict):
            errors.append(f"{canonical.name}: top-level must be a mapping")
            return None

        composed: dict = {}

        # 6. Push frame BEFORE descending; pop in finally to guarantee cleanup
        descending.add(canonical)
        frame_chain.append(canonical)
        try:
            # 7. extends (single string, recurse)
            ext = data.pop("extends", None)
            if ext is not None:
                if not isinstance(ext, str):
                    errors.append(
                        f"{canonical.name}: 'extends' must be a string "
                        f"(got {type(ext).__name__})"
                    )
                else:
                    parent_path = (canonical.parent / ext).resolve()
                    parent_data = _load_one(parent_path, depth + 1, descending, frame_chain)
                    if parent_data is not None:
                        composed = _deep_merge_with_provenance(
                            composed, parent_data, parent_path, provenance
                        )

            # 8. includes (list of strings, left-to-right)
            incs = data.pop("includes", None)
            if incs is not None:
                if not isinstance(incs, list):
                    errors.append(f"{canonical.name}: 'includes' must be a list")
                else:
                    for entry in incs:
                        if not isinstance(entry, str):
                            errors.append(
                                f"{canonical.name}: 'includes' entry must be a string "
                                f"(got {type(entry).__name__})"
                            )
                            continue
                        inc_path = (canonical.parent / entry).resolve()
                        inc_data = _load_one(inc_path, depth + 1, descending, frame_chain)
                        if inc_data is not None:
                            composed = _deep_merge_with_provenance(
                                composed, inc_data, inc_path, provenance
                            )

            # 9. Apply own fields LAST (own wins over extends + includes)
            composed = _deep_merge_with_provenance(
                composed, data, canonical, provenance
            )
        finally:
            descending.discard(canonical)
            frame_chain.pop()

        # 10. Append to OUTPUT chain (post-order — root ancestor first naturally)
        chain.append(canonical)
        return composed

    composed = _load_one(entry_path, 0, set(), []) or {}
    community_template_rules = composed.get("community_templates") or []
    if not isinstance(community_template_rules, list):
        community_template_rules = []
    return ResolvedProfile(
        composed=composed,
        chain=chain,
        provenance=provenance,
        errors=errors,
        community_template_rules=community_template_rules,
    )


# ---------------------------------------------------------------------------
# Profile loading (PROF-01, PROF-02, D-04)
# ---------------------------------------------------------------------------

def load_profile(vault_dir: str | Path | None) -> dict:
    """Discover and load a vault profile, merging over built-in defaults.

    Returns the merged profile dict. Falls back to defaults when vault_dir is
    None, no profile.yaml exists, or when PyYAML is not installed.
    """
    if vault_dir is None:
        return _deep_merge(_DEFAULT_PROFILE, {})
    profile_path = Path(vault_dir) / ".graphify" / "profile.yaml"
    if not profile_path.exists():
        return _deep_merge(_DEFAULT_PROFILE, {})

    try:
        import yaml  # type: ignore[import-untyped]  # noqa: F401
    except ImportError:
        print(
            "[graphify] PyYAML not installed — cannot read profile.yaml. "
            "Install with: pip install graphifyy[obsidian]",
            file=sys.stderr,
        )
        return _deep_merge(_DEFAULT_PROFILE, {})

    # Phase 30 (CFG-02): walk the extends/includes chain BEFORE schema validation
    # so partial fragments are tolerated (D-08) and only the composed profile
    # must validate. Any resolver error → graceful fallback to _DEFAULT_PROFILE.
    resolved = _resolve_profile_chain(profile_path, Path(vault_dir))
    if resolved.errors:
        for err in resolved.errors:
            print(f"[graphify] profile error: {err}", file=sys.stderr)
        return _deep_merge(_DEFAULT_PROFILE, {})

    errors = validate_profile(resolved.composed)
    if errors:
        for err in errors:
            print(f"[graphify] profile error: {err}", file=sys.stderr)
        return _deep_merge(_DEFAULT_PROFILE, {})

    return _deep_merge(_DEFAULT_PROFILE, resolved.composed)


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

    # Phase 30 (CFG-02): extends/includes/community_templates schema checks.
    # The resolver enforces semantic constraints (cycles, depth, paths); these
    # are pure-typing guards that fire before resolution would even start.
    ext = profile.get("extends")
    if ext is not None and not isinstance(ext, str):
        errors.append(
            "'extends' must be a string (single-parent only — use 'includes' "
            "for multi-base composition)"
        )
    incs = profile.get("includes")
    if incs is not None:
        if not isinstance(incs, list):
            errors.append("'includes' must be a list")
        else:
            for i, item in enumerate(incs):
                if not isinstance(item, str):
                    errors.append(
                        f"includes[{i}] must be a string (got {type(item).__name__})"
                    )
    ct = profile.get("community_templates")
    if ct is not None:
        if not isinstance(ct, list):
            errors.append("'community_templates' must be a list")
        else:
            for idx, rule in enumerate(ct):
                prefix = f"community_templates[{idx}]"
                if not isinstance(rule, dict):
                    errors.append(f"{prefix}: must be a mapping (dict)")
                    continue
                match = rule.get("match")
                if match not in {"label", "id"}:
                    errors.append(
                        f"{prefix}.match must be 'label' or 'id' (got {match!r})"
                    )
                pattern = rule.get("pattern")
                if "pattern" not in rule:
                    errors.append(f"{prefix}.pattern is required")
                elif match == "label" and not isinstance(pattern, str):
                    errors.append(
                        f"{prefix}.pattern must be a string when match='label' "
                        f"(got {type(pattern).__name__})"
                    )
                elif match == "id" and (
                    isinstance(pattern, bool) or not isinstance(pattern, int)
                ):
                    errors.append(
                        f"{prefix}.pattern must be an integer when match='id' "
                        f"(got {type(pattern).__name__})"
                    )
                template = rule.get("template")
                if not isinstance(template, str) or not template:
                    errors.append(f"{prefix}.template must be a non-empty string")
                elif ".." in template:
                    errors.append(
                        f"{prefix}.template contains '..' — fragment paths must "
                        f"stay inside .graphify/"
                    )
                elif Path(template).is_absolute():
                    errors.append(
                        f"{prefix}.template is an absolute path — must be "
                        f"relative to .graphify/"
                    )
                elif template.startswith("~"):
                    errors.append(
                        f"{prefix}.template starts with '~' — must be relative "
                        f"to .graphify/"
                    )
                extra = set(rule) - {"match", "pattern", "template"}
                if extra:
                    errors.append(
                        f"{prefix}: unknown keys {sorted(extra)} — only "
                        f"'match', 'pattern', 'template' are supported"
                    )

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
            # Phase 4 D-65: optional per-key merge policy overrides.
            # Users map frontmatter field name -> one of
            # _VALID_FIELD_POLICY_MODES. Validation keeps the accumulator
            # pattern (error list, never raise).
            field_policies = merge.get("field_policies")
            if field_policies is not None:
                if not isinstance(field_policies, dict):
                    errors.append(
                        "'merge.field_policies' must be a mapping (dict) of "
                        "field-name -> policy-mode"
                    )
                else:
                    for fp_key, fp_value in field_policies.items():
                        if not isinstance(fp_key, str):
                            errors.append(
                                f"merge.field_policies key {fp_key!r} must be a "
                                f"string (got {type(fp_key).__name__})"
                            )
                            continue
                        if fp_value not in _VALID_FIELD_POLICY_MODES:
                            errors.append(
                                f"merge.field_policies.{fp_key} has invalid mode "
                                f"{fp_value!r} — valid modes are: "
                                f"{sorted(_VALID_FIELD_POLICY_MODES)}"
                            )

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

    # topology section (Phase 3, D-48)
    topology = profile.get("topology")
    if topology is not None:
        if not isinstance(topology, dict):
            errors.append("'topology' must be a mapping (dict)")
        else:
            god_node = topology.get("god_node")
            if god_node is not None:
                if not isinstance(god_node, dict):
                    errors.append("'topology.god_node' must be a mapping (dict)")
                else:
                    top_n = god_node.get("top_n")
                    if top_n is not None:
                        # bool-before-int guard (T-3-03) — bool is a subclass
                        # of int in Python; pattern mirrors profile.py:326-329.
                        if isinstance(top_n, bool) or not isinstance(top_n, int):
                            errors.append(
                                f"topology.god_node.top_n must be an integer "
                                f"(got {type(top_n).__name__})"
                            )
                        elif top_n < 0:
                            errors.append(
                                f"topology.god_node.top_n must be ≥ 0 (got {top_n})"
                            )

    # mapping section (Phase 3, D-52)
    mapping = profile.get("mapping")
    if mapping is not None:
        if not isinstance(mapping, dict):
            errors.append("'mapping' must be a mapping (dict)")
        else:
            threshold = mapping.get("moc_threshold")
            if threshold is not None:
                if isinstance(threshold, bool) or not isinstance(threshold, int):
                    errors.append(
                        f"mapping.moc_threshold must be an integer "
                        f"(got {type(threshold).__name__})"
                    )
                elif threshold < 1:
                    errors.append(
                        f"mapping.moc_threshold must be ≥ 1 (got {threshold})"
                    )

    # mapping_rules section — delegate to validate_rules (Phase 3, D-44/D-45)
    mapping_rules = profile.get("mapping_rules")
    if mapping_rules is not None:
        if not isinstance(mapping_rules, list):
            errors.append("'mapping_rules' must be a list")
        else:
            # Function-local import breaks the circular dependency
            # (graphify.mapping imports from graphify.templates which imports
            # from graphify.profile). See plan 03-03 T-3-11.
            from graphify.mapping import validate_rules
            errors.extend(validate_rules(mapping_rules))

    # tag_taxonomy section (Phase 19, D-17, D-18)
    tag_taxonomy = profile.get("tag_taxonomy")
    if tag_taxonomy is not None:
        if not isinstance(tag_taxonomy, dict):
            errors.append("'tag_taxonomy' must be a mapping (dict)")
        else:
            for ns, values in tag_taxonomy.items():
                if not isinstance(ns, str):
                    errors.append(f"tag_taxonomy namespace key must be a string, got {type(ns).__name__}")
                elif not isinstance(values, list):
                    errors.append(f"tag_taxonomy.{ns} must be a list of strings")
                elif not all(isinstance(v, str) for v in values):
                    errors.append(f"tag_taxonomy.{ns} must contain only strings")

    # diagram_types section (Phase 21, PROF-01..PROF-04)
    diagram_types = profile.get("diagram_types")
    if diagram_types is not None:
        if not isinstance(diagram_types, list):
            errors.append("diagram_types must be a list")
        else:
            # Phase 22 (D-05, T-22-V5): added layout_type + output_path
            # for the Excalidraw skill / pure-Python fallback to dispatch on.
            _VALID_DT_KEYS = {"name", "template_path", "trigger_node_types",
                              "trigger_tags", "min_main_nodes", "naming_pattern",
                              "layout_type", "output_path"}
            for i, entry in enumerate(diagram_types):
                if not isinstance(entry, dict):
                    errors.append(f"diagram_types[{i}] must be a dict")
                    continue
                if "name" in entry and not isinstance(entry["name"], str):
                    errors.append(f"diagram_types[{i}].name must be str")
                if "template_path" in entry and not isinstance(entry["template_path"], str):
                    errors.append(f"diagram_types[{i}].template_path must be str")
                if "trigger_node_types" in entry and not isinstance(entry["trigger_node_types"], list):
                    errors.append(f"diagram_types[{i}].trigger_node_types must be list")
                if "trigger_tags" in entry and not isinstance(entry["trigger_tags"], list):
                    errors.append(f"diagram_types[{i}].trigger_tags must be list")
                if "min_main_nodes" in entry and (
                    isinstance(entry["min_main_nodes"], bool)
                    or not isinstance(entry["min_main_nodes"], int)
                ):
                    errors.append(f"diagram_types[{i}].min_main_nodes must be int")
                if "naming_pattern" in entry and not isinstance(entry["naming_pattern"], str):
                    errors.append(f"diagram_types[{i}].naming_pattern must be str")
                # Phase 22 (T-22-V5): per-key validators for new fields.
                if "layout_type" in entry and not isinstance(entry["layout_type"], str):
                    errors.append(f"diagram_types[{i}].layout_type must be str")
                if "output_path" in entry and not isinstance(entry["output_path"], str):
                    errors.append(f"diagram_types[{i}].output_path must be str")
                for key in entry:
                    if key not in _VALID_DT_KEYS:
                        errors.append(f"diagram_types[{i}] unknown key '{key}'")

    # profile_sync section (Phase 19, D-18 — VAULT-06 opt-out)
    profile_sync = profile.get("profile_sync")
    if profile_sync is not None:
        if not isinstance(profile_sync, dict):
            errors.append("'profile_sync' must be a mapping (dict)")
        else:
            auto_update = profile_sync.get("auto_update")
            if auto_update is not None and not isinstance(auto_update, bool):
                errors.append("'profile_sync.auto_update' must be a boolean")

    # output section (Phase 27, D-01, D-03, VAULT-10)
    output = profile.get("output")
    if output is not None:
        if not isinstance(output, dict):
            errors.append("'output' must be a mapping (dict)")
        else:
            mode = output.get("mode")
            if mode is None:
                errors.append("'output' requires a 'mode' key")
            elif mode not in _VALID_OUTPUT_MODES:
                errors.append(
                    f"output.mode {mode!r} invalid — valid modes are: "
                    f"{sorted(_VALID_OUTPUT_MODES)}"
                )
            path_val = output.get("path")
            if path_val is None:
                errors.append("'output' requires a 'path' key")
            elif not isinstance(path_val, str) or not path_val.strip():
                errors.append("output.path must be a non-empty string")
            elif mode == "vault-relative":
                if Path(path_val).is_absolute():
                    errors.append("output.path must be relative when mode=vault-relative")
                elif path_val.startswith("~"):
                    errors.append("output.path must not start with '~' when mode=vault-relative")
                elif ".." in Path(path_val).parts:
                    errors.append("output.path must not contain '..' when mode=vault-relative")
            elif mode == "absolute":
                if not Path(path_val).is_absolute():
                    errors.append("output.path must be absolute when mode=absolute")
            # mode == "sibling-of-vault": deferred to validate_sibling_path() at use-time

            # Phase 28 D-17: validate output.exclude list
            exclude = output.get("exclude")
            if exclude is not None:
                if not isinstance(exclude, list):
                    errors.append("output.exclude must be a list")
                else:
                    for i, item in enumerate(exclude):
                        if not isinstance(item, str):
                            errors.append(
                                f"output.exclude[{i}] must be a string "
                                f"(got {type(item).__name__})"
                            )
                        elif not item.strip():
                            errors.append(
                                f"output.exclude[{i}] must not be empty or whitespace-only"
                            )
                        elif Path(item).is_absolute():
                            errors.append(
                                f"output.exclude[{i}] must not be an absolute path"
                            )
                        elif ".." in Path(item.lstrip("/")).parts:
                            errors.append(
                                f"output.exclude[{i}] must not contain '..' (path traversal)"
                            )

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


def validate_sibling_path(candidate: str, vault_dir: str | Path) -> Path:
    """Resolve <vault>/../<candidate> with sane bounds (Phase 27, D-03).

    Authorizes the deliberate one-parent escape for output mode=sibling-of-vault
    while rejecting:
      - empty / whitespace-only candidate
      - candidate starting with '~' (home expansion)
      - candidate that is absolute
      - candidate containing '..' segments
      - resolved path that escapes vault parent (defense-in-depth)
      - filesystem-root corner case (vault_base.parent == vault_base)
    """
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("output.path must be a non-empty string for mode=sibling-of-vault")
    if candidate.startswith("~"):
        raise ValueError("output.path must not start with '~' (home expansion blocked)")
    if Path(candidate).is_absolute():
        raise ValueError(
            "output.path must be relative for mode=sibling-of-vault "
            "(use mode=absolute for absolute paths)"
        )
    if ".." in Path(candidate).parts:
        raise ValueError("output.path must not contain '..' segments for mode=sibling-of-vault")

    vault_base = Path(vault_dir).resolve()
    parent = vault_base.parent
    if parent == vault_base:
        raise ValueError(
            f"vault {vault_base} has no parent directory — "
            "mode=sibling-of-vault is not usable here; switch to mode=absolute"
        )
    resolved = (parent / candidate).resolve()
    try:
        resolved.relative_to(parent)
    except ValueError:
        raise ValueError(
            f"output.path {candidate!r} escapes vault parent {parent}"
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


# ---------------------------------------------------------------------------
# Preflight composite validator (D-77, D-77a, PROF-05) — read-only four-layer check
# ---------------------------------------------------------------------------

# D-77 path-safety thresholds
_PATH_SAFETY_MAX_LEN = 240           # Windows MAX_PATH 260 with 20-char headroom
_PATH_SAFETY_MAX_SEGMENTS = 4        # UX: Obsidian file tree gets noisy past 4 levels
_PATH_SAFETY_SIM_FILENAME = "X" * 200  # D-06 filename cap, worst-case


def validate_profile_preflight(
    vault_dir: str | Path,
) -> PreflightResult:
    """Four-layer preflight validation of a vault's .graphify/ directory.

    Returns PreflightResult(errors, warnings, rule_count, template_count).
    Never raises on validation problems. Never writes. Never mutates the vault.

    Layers (D-77):
      1. Schema  (errors)   — validate_profile on the merged profile
      2. Templates (errors) — validate_template for each override present
      3. Dead rules (warnings) — mapping._detect_dead_rules
      4. Path safety (warnings) — folder length + nesting thresholds

    Caller contract (D-77a): skill exits 1 if errors non-empty, 0 otherwise.
    On clean validation the skill prints
      `profile ok — {result.rule_count} rules, {result.template_count} templates validated`
    """
    errors: list[str] = []
    warnings: list[str] = []
    rule_count = 0
    template_count = 0

    vault_path = Path(vault_dir)
    if not vault_path.exists():
        return PreflightResult(
            errors=[f"vault_dir does not exist: {vault_path}"],
            warnings=[],
            rule_count=0,
            template_count=0,
        )
    if not vault_path.is_dir():
        return PreflightResult(
            errors=[f"vault_dir is not a directory: {vault_path}"],
            warnings=[],
            rule_count=0,
            template_count=0,
        )

    graphify_dir = vault_path / ".graphify"
    profile_path = graphify_dir / "profile.yaml"

    # No .graphify directory → no user profile at all; all counts are 0 by
    # definition (D-77a: N/M suffix reflects user-authored overrides only).
    if not graphify_dir.exists():
        return PreflightResult(errors=[], warnings=[], rule_count=0, template_count=0)

    # Step A: load user YAML (if any). Mirrors load_profile's PyYAML guard.
    # Phase 30 (CFG-02): resolve the extends/includes chain before validating.
    # The composed dict — not the raw single-file YAML — is what we validate
    # and what feeds the merged profile for layers 3 + 4.
    user_data: dict = {}
    chain: list[Path] = []
    provenance: dict[str, Path] = {}
    community_template_rules: list[dict] = []
    if profile_path.exists():
        try:
            import yaml  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            errors.append(
                "PyYAML not installed — cannot read profile.yaml. "
                "Install with: pip install graphifyy[obsidian]"
            )
            return PreflightResult(
                errors, warnings, rule_count, template_count,
                chain, provenance, community_template_rules,
            )
        resolved = _resolve_profile_chain(profile_path, vault_path)
        # Surface resolver errors with a stable prefix so doctor output is
        # consistent with other layer-1 schema errors.
        for err in resolved.errors:
            errors.append(f"profile.yaml: {err}")
        # Even on partial-failure we still populate downstream context so the
        # rest of preflight (templates / dead-rules / path-safety) keeps
        # producing useful output.
        user_data = resolved.composed
        chain = resolved.chain
        provenance = resolved.provenance
        community_template_rules = resolved.community_template_rules
        if resolved.errors:
            return PreflightResult(
                errors, warnings, rule_count, template_count,
                chain, provenance, community_template_rules,
            )

    # LAYER 1: Schema — validate_profile on the COMPOSED user data (errors only)
    errors.extend(validate_profile(user_data))

    # Build the effective merged profile (for layers 3 + 4).
    merged = _deep_merge(_DEFAULT_PROFILE, user_data)

    # LAYER 2: Templates — check every override present in .graphify/templates/
    templates_dir = graphify_dir / "templates"
    if templates_dir.exists() and templates_dir.is_dir():
        # Function-local import to avoid templates.py → profile.py cycle
        from graphify.templates import (
            validate_template as _validate_template,
            _REQUIRED_PER_TYPE,
        )
        for note_type, required in _REQUIRED_PER_TYPE.items():
            tpl_file = templates_dir / f"{note_type}.md"
            if not tpl_file.exists():
                continue
            # Path-confinement: templates/<type>.md must stay inside vault
            try:
                validate_vault_path(Path(".graphify") / "templates" / f"{note_type}.md", vault_path)
            except ValueError as exc:
                errors.append(f"templates/{note_type}.md: {exc}")
                continue
            try:
                text = tpl_file.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"templates/{note_type}.md: read failed: {exc}")
                continue
            tpl_errors = _validate_template(text, required)
            if tpl_errors:
                for err in tpl_errors:
                    errors.append(f"templates/{note_type}.md: {err}")
            else:
                # Only templates that PASSED validation count toward template_count.
                template_count += 1

    # LAYER 3: Dead mapping rules (warnings only)
    rules = merged.get("mapping_rules") or []
    if isinstance(rules, list):
        rule_count = len(rules)
        if rules:
            # Function-local import — matches validate_profile's existing pattern
            from graphify.mapping import _detect_dead_rules
            warnings.extend(_detect_dead_rules(rules))

    # LAYER 4: Path safety (warnings only)
    folder_candidates: list[tuple[str, str]] = []   # (origin, folder)
    folder_mapping = merged.get("folder_mapping") or {}
    if isinstance(folder_mapping, dict):
        for key, val in folder_mapping.items():
            if isinstance(val, str):
                folder_candidates.append((f"folder_mapping.{key}", val))
    if isinstance(rules, list):
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            then = rule.get("then")
            if not isinstance(then, dict):
                continue
            rule_folder = then.get("folder")
            if isinstance(rule_folder, str):
                folder_candidates.append(
                    (f"mapping_rules[{idx}].then.folder", rule_folder)
                )

    for origin, folder in folder_candidates:
        segments = [s for s in folder.strip("/").split("/") if s]
        if len(segments) > _PATH_SAFETY_MAX_SEGMENTS:
            warnings.append(
                f"{origin}: {len(segments)} path segments exceeds "
                f"{_PATH_SAFETY_MAX_SEGMENTS}-level nesting recommendation "
                f"(Obsidian UX)"
            )
        simulated = str(vault_path / folder / _PATH_SAFETY_SIM_FILENAME)
        if len(simulated) > _PATH_SAFETY_MAX_LEN:
            warnings.append(
                f"{origin}: worst-case path length "
                f"{len(simulated)} exceeds {_PATH_SAFETY_MAX_LEN}-char budget "
                f"(Windows MAX_PATH headroom)"
            )

    return PreflightResult(
        errors=errors,
        warnings=warnings,
        rule_count=rule_count,
        template_count=template_count,
        chain=chain,
        provenance=provenance,
        community_template_rules=community_template_rules,
    )
