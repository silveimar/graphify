# Phase 32: Profile Contract & Defaults - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 12
**Analogs found:** 11 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/profile.py` | config/utility | transform + file-I/O preflight | `graphify/profile.py` | exact |
| `graphify/mapping.py` | service/utility | transform | `graphify/mapping.py` | exact |
| `graphify/doctor.py` | service/diagnostic | request-response CLI report | `graphify/doctor.py` | exact |
| `graphify/__main__.py` | CLI route | request-response | `graphify/__main__.py` | exact |
| `graphify/templates.py` | utility | transform | `graphify/templates.py` | role-match |
| `graphify/export.py` | export service | file-I/O | `graphify/export.py` | role-match |
| `tests/test_profile.py` | test | transform + file-I/O fixtures | `tests/test_profile.py` | exact |
| `tests/test_mapping.py` | test | transform | `tests/test_mapping.py` | exact |
| `tests/test_doctor.py` | test | diagnostic request-response | `tests/test_doctor.py` | exact |
| `tests/test_export.py` | test | file-I/O dry-run | `tests/test_export.py` | role-match |
| `.planning/REQUIREMENTS.md` | docs/config | planning traceability | `.planning/REQUIREMENTS.md` | exact |
| `.planning/ROADMAP.md` | docs/config | planning traceability | `.planning/ROADMAP.md` | exact |

## Pattern Assignments

### `graphify/profile.py` (config/utility, transform + file-I/O preflight)

**Analog:** `graphify/profile.py`

**Imports pattern** (lines 1-11):
```python
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
```

**Default contract pattern** (lines 62-97):
```python
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
    ...
    "topology": {"god_node": {"top_n": 10}},
    "mapping": {"moc_threshold": 3},
```

**Top-level key pattern** (lines 136-142):
```python
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output",
    "extends", "includes", "community_templates",  # Phase 30 (CFG-02 / CFG-03)
    "dataview_queries",  # Phase 31 (TMPL-03, D-11)
}
```

**Validation accumulator pattern** (lines 462-472):
```python
def validate_profile(profile: dict) -> list[str]:
    """Validate a profile dict. Returns a list of error strings — empty means valid."""
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]

    errors: list[str] = []

    # Unknown top-level keys
    for key in profile:
        if key not in _VALID_TOP_LEVEL_KEYS:
            errors.append(f"Unknown profile key '{key}' — valid keys are: {sorted(_VALID_TOP_LEVEL_KEYS)}")
```

**Folder safety validation pattern** (lines 631-658):
```python
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
                    errors.append(
                        f"folder_mapping.{name} is an absolute path — "
                        "only relative paths are allowed in folder mappings"
                    )
                elif path_val.startswith("~"):
                    errors.append(
                        f"folder_mapping.{name} starts with '~' — "
                        "home-relative paths are not allowed in folder mappings"
                    )
```

**Preflight shared-surface pattern** (lines 1024-1041):
```python
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
```

**Apply to Phase 32:**
- Add `taxonomy` to `_DEFAULT_PROFILE` and `_VALID_TOP_LEVEL_KEYS` in the same change.
- Replace default `mapping.moc_threshold` with `mapping.min_community_size`.
- Add taxonomy validation next to existing `folder_mapping`, `dataview_queries`, and `output` schema blocks.
- Reject `mapping.moc_threshold` as an error immediately, not as an alias.
- Put warnings that must be shared by CLI and doctor in `validate_profile_preflight()`.

### `graphify/mapping.py` (service/utility, transform)

**Analog:** `graphify/mapping.py`

**Imports and context pattern** (lines 1-17):
```python
"""Mapping engine: pure classification of graph nodes into note types and folders."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

import networkx as nx
...
from graphify.templates import ClassificationContext, _NOTE_TYPES
```

**Folder resolution pattern** (lines 229-237):
```python
def _resolve_folder(
    note_type: str,
    then_folder: str | None,
    folder_mapping: dict,
) -> str:
    """Return the per-rule folder override, falling back to folder_mapping."""
    if isinstance(then_folder, str) and then_folder:
        return then_folder
    return folder_mapping.get(note_type) or folder_mapping.get("default", "Atlas/Dots/")
```

**Classification routing pattern** (lines 270-278):
```python
    folder_mapping = profile.get("folder_mapping") or {}
    top_n = (
        profile.get("topology", {})
        .get("god_node", {})
        .get("top_n", 10)
    )
    raw_rules = profile.get("mapping_rules") or []
    compiled_rules = compile_rules(raw_rules)
```

**Community threshold pattern to replace** (lines 522-540):
```python
    folder_mapping = profile.get("folder_mapping") or {}
    moc_folder = folder_mapping.get("moc") or folder_mapping.get(
        "default", "Atlas/Maps/"
    )

    # Defensive threshold parse — belt-and-suspenders with Plan 03's
    # validate_rules. Explicitly reject bool (bool is a subclass of int).
    raw_threshold = profile.get("mapping", {}).get("moc_threshold", 3)
    if isinstance(raw_threshold, bool) or not isinstance(raw_threshold, int):
        threshold = 3
    else:
        threshold = raw_threshold

    node_to_community = _node_community_map(communities)
    community_sizes = {cid: len(members) for cid, members in communities.items()}

    above_cids = sorted(
        cid for cid, members in communities.items() if len(members) >= threshold
    )
```

**Bucket MOC pattern to update** (lines 588-602):
```python
    bucket_needed = bool(hostless_below) or (not above_cids and bool(below_cids))
    if bucket_needed:
        per_community[-1] = ClassificationContext(
            note_type="moc",
            folder=moc_folder,
            community_name="Uncategorized",
            parent_moc_label="Uncategorized",
            community_tag="uncategorized",
            members_by_type={"thing": [], "statement": [], "person": [], "source": []},
            sub_communities=[],
            sibling_labels=[],
            cohesion=0.0,
        )
```

**Apply to Phase 32:**
- Introduce a single helper or inline step that computes effective taxonomy folders before normal classification.
- Preserve the existing `ClassificationContext.folder` contract so `templates.py` and `export.py` do not need taxonomy-specific branching.
- Replace the threshold read with `profile["mapping"]["min_community_size"]`.
- Change the synthetic bucket display/tag from `Uncategorized`/`uncategorized` to the v1.8 `_Unclassified` semantics decided by the planner.

### `graphify/doctor.py` (service/diagnostic, request-response CLI report)

**Analog:** `graphify/doctor.py`

**Imports pattern** (lines 25-41):
```python
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from graphify.detect import (
    _SELF_OUTPUT_DIRS,
    _is_nested_output,
    _load_graphifyignore,
    _load_output_manifest,
)
from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output
from graphify.profile import load_profile, validate_profile
```

**Fix hint pattern** (lines 67-100):
```python
_FIX_HINTS: list[tuple[str, str]] = [
    (
        "missing .graphify/profile.yaml",
        "[graphify] FIX: Create .graphify/profile.yaml — see docs/vault-adapter.md",
    ),
    ...
    (
        "WOULD_SELF_INGEST",
        "[graphify] FIX: Move existing graphify-out/ outside the input scan, or add 'graphify-out/**' to .graphifyignore",
    ),
]
```

**Report container pattern** (lines 121-142):
```python
@dataclass
class DoctorReport:
    """Structured diagnostic report — fully populated by run_doctor()."""
    vault_detection: bool = False
    vault_path: Optional[Path] = None
    profile_validation_errors: list[str] = field(default_factory=list)
    resolved_output: Optional[ResolvedOutput] = None
    ignore_list: dict[str, list[str]] = field(default_factory=dict)
    manifest_history: Optional[list[dict]] = None
    would_self_ingest: bool = False
    recommended_fixes: list[str] = field(default_factory=list)
    preview: Optional[PreviewSection] = None
```

**Current validation surface to refactor** (lines 312-324):
```python
    # --- Profile validation (D-36) ----------------------------------------
    profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
    if profile_yaml.exists():
        try:
            profile = load_profile(cwd_resolved)
            if isinstance(profile, dict):
                report.profile_validation_errors.extend(validate_profile(profile))
        except Exception as exc:
            report.profile_validation_errors.append(
                f"profile load error: {exc}"
            )
```

**Formatting pattern** (lines 419-440):
```python
def format_report(report: DoctorReport) -> str:
    """Render DoctorReport as sectioned [graphify]-prefixed text (D-34).

    Section order: Vault Detection / Profile Validation / Output Destination /
    Ignore-List / Preview (when present) / Recommended Fixes.
    """
    lines: list[str] = []

    # --- Vault Detection --------------------------------------------------
    lines.append("[graphify] === Vault Detection ===")
    if report.vault_detection:
        lines.append(f"[graphify] vault detected at {report.vault_path}")
    else:
        lines.append("[graphify] no Obsidian vault detected in CWD")

    # --- Profile Validation -----------------------------------------------
    lines.append("[graphify] === Profile Validation ===")
    if report.profile_validation_errors:
        for err in report.profile_validation_errors:
            lines.append(f"[graphify] error: {err}")
```

**Apply to Phase 32:**
- Import and call `validate_profile_preflight()` in doctor so doctor and `--validate-profile` share errors and warnings.
- Either add warning storage to `DoctorReport` or render warnings distinctly in the profile validation section.
- Extend `_FIX_HINTS` for taxonomy errors, `mapping.moc_threshold`, missing `mapping.min_community_size`, and community overview deprecation guidance.

### `graphify/__main__.py` (CLI route, request-response)

**Analog:** `graphify/__main__.py`

**`--validate-profile` thin wrapper pattern** (lines 1265-1279):
```python
    # --validate-profile <vault-path> (D-78, PROF-05)
    # Thin wrapper over graphify.profile.validate_profile_preflight. Read-only.
    # Never writes. Never runs the extract/build/cluster pipeline.
    if cmd == "--validate-profile":
        if len(sys.argv) < 3:
            print("Usage: graphify --validate-profile <vault-path>", file=sys.stderr)
            sys.exit(2)
        from graphify.profile import validate_profile_preflight
        vault_arg = Path(sys.argv[2])
        result = validate_profile_preflight(vault_arg)
        for err in result.errors:
            print(f"error: {err}", file=sys.stderr)
        for warn in result.warnings:
            print(f"warning: {warn}", file=sys.stderr)
```

**CLI success output pattern** (lines 1284-1290):
```python
        if not result.errors:
            # D-77a literal kept verbatim for back-compat:
            print(
                f"profile ok — {result.rule_count} rules, "
                f"{result.template_count} templates validated"
            )
            print()
```

**Obsidian routing precedence pattern** (lines 1393-1404):
```python
        # Phase 27 (VAULT-08, VAULT-09, VAULT-10): resolve vault-aware output destination.
        from graphify.output import resolve_output
        resolved = resolve_output(Path.cwd(), cli_output=cli_output)

        # Precedence (D-08): --output > profile > --obsidian-dir > legacy default
        if cli_output is not None:
            obsidian_dir = str(resolved.notes_dir)
        elif resolved.vault_detected and resolved.source == "profile":
            obsidian_dir = str(resolved.notes_dir)
        elif user_passed_obsidian_dir:
            pass  # honor explicit --obsidian-dir; leave obsidian_dir as-is
        # else: keep legacy default "graphify-out/obsidian" (D-12 backcompat)
```

**Doctor command pattern** (lines 2357-2376):
```python
    elif cmd == "doctor":
        # graphify doctor [--dry-run]
        # D-30: top-level subcommand. D-31: --dry-run lives ONLY here.
        # D-35: exit 1 on invalid profile / unresolvable dest / would_self_ingest.
        import argparse as _ap
        ...
        from graphify.doctor import run_doctor, format_report
        report = run_doctor(Path.cwd(), dry_run=opts.dry_run)
        print(format_report(report))
        sys.exit(1 if report.is_misconfigured() else 0)
```

**Apply to Phase 32:**
- Keep CLI logic thin. Do not duplicate taxonomy validation in `__main__.py`.
- If warning output changes, change the `PreflightResult`/doctor formatting source rather than branching here.
- Preserve the existing exit-code rule: profile validation errors exit 1; warnings do not unless Phase 32 explicitly promotes them to errors.

### `graphify/templates.py` (utility, transform)

**Analog:** `graphify/templates.py`

**Note type vocabulary pattern** (lines 37-52):
```python
KNOWN_VARS: frozenset[str] = frozenset({
    "label",
    "frontmatter",
    "wayfinder_callout",
    "connections_callout",
    "members_section",
    "sub_communities_callout",
    "dataview_block",
    "metadata_callout",
    "body",
})

_NOTE_TYPES: frozenset[str] = frozenset({
    "moc", "community", "thing", "statement", "person", "source",
})
```

**Classification context contract** (lines 86-97):
```python
class ClassificationContext(TypedDict, total=False):
    note_type: str
    folder: str
    parent_moc_label: str
    community_tag: str
    members_by_type: dict
    sub_communities: list
    sibling_labels: list
    community_name: str
```

**Template validation pattern** (lines 370-386):
```python
def validate_template(text: str, required: set[str]) -> list[str]:
    """Validate a template string.

    Returns a list of error strings — empty means valid. Distinguishes:
      - `${var}` → must be in KNOWN_VARS (or `conn.<field>` / `conn_<field>`
        inside a `{{#connections}}` block — Phase 31 TMPL-02)
      ...
    """
    errors: list[str] = []
```

**Community overview render path to warn on, not remove** (lines 1387-1411):
```python
def render_community_overview(
    community_id: int,
    G,
    communities: dict,
    profile: dict,
    classification_context,
    *,
    vault_dir=None,
    created: "datetime.date | None" = None,
) -> tuple[str, str]:
    """Render a Community Overview note. Same signature as render_moc but
    uses the `community.md` built-in template by default.
    ...
    """
    return _render_moc_like(
        community_id, G, communities, profile, classification_context,
        template_key="community", vault_dir=vault_dir, created=created,
        note_type="community",
    )
```

**Apply to Phase 32:**
- Do not delete `community` note type or `render_community_overview()` in this phase.
- Surface deprecation through profile/preflight validation when profiles or templates explicitly request community overview output.
- Keep rendering behavior intact so Phase 32 stays a contract/default phase.

### `graphify/export.py` (export service, file-I/O)

**Analog:** `graphify/export.py`

**Obsidian export pipeline pattern** (lines 518-535):
```python
def to_obsidian(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    *,
    profile: dict | None = None,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    dry_run: bool = False,
    force: bool = False,
    obsidian_dedup: bool = False,
) -> "MergeResult | MergePlan":
    """Export graph as an Obsidian vault using the profile-driven pipeline.

    Runs: load_profile → classify → render_all → compute_merge_plan → apply_merge_plan.
```

**Profile discovery pattern** (lines 581-585):
```python
    # D-74: always run the new pipeline. No `if profile is None` branching.
    if profile is None:
        profile = load_profile(out)

    mapping_result = classify(G, communities, profile, cohesion=cohesion)
```

**Path consumption pattern** (lines 611-628):
```python
        try:
            filename, rendered_text = render_note(
                node_id, G, profile, note_type, ctx, vault_dir=out,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(
                f"[graphify] to_obsidian: skipping node {node_id!r} "
                f"({note_type}): {exc}",
                file=sys.stderr,
            )
            continue
        folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("default", "Atlas/Dots/")
        target_path = out / folder / filename
```

**Community path consumption pattern** (lines 647-665):
```python
        try:
            filename, rendered_text = render_fn(
                cid, G, communities, profile, ctx, vault_dir=out,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(
                f"[graphify] to_obsidian: skipping community {cid} "
                f"({note_type}): {exc}",
                file=sys.stderr,
            )
            continue
        folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("moc", "Atlas/Maps/")
        target_path = out / folder / filename
```

**Apply to Phase 32:**
- Prefer keeping `to_obsidian()` unchanged for path logic if `mapping.classify()` now supplies taxonomy-resolved `ctx["folder"]`.
- Add only narrow tests here for no-profile dry-run paths under the Graphify subtree.
- Do not move taxonomy precedence into final `target_path` construction unless mapping cannot carry the effective folder.

### `tests/test_profile.py` (test, transform + file-I/O fixtures)

**Analog:** `tests/test_profile.py`

**Imports pattern** (lines 1-24):
```python
from __future__ import annotations

"""Unit tests for graphify/profile.py — profile loading, validation, and safety helpers."""

import sys
import unicodedata
from pathlib import Path
from unittest import mock

import pytest
...
from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    ...
    validate_profile,
    validate_vault_path,
)
```

**Default profile assertion pattern to update** (lines 57-72):
```python
def test_load_profile_no_profile_returns_defaults(tmp_path):
    result = load_profile(tmp_path)
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
    assert result["folder_mapping"]["moc"] == "Atlas/Maps/"


def test_load_profile_with_yaml(tmp_path):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text(
        'folder_mapping:\n  moc: "Custom/Maps/"\n', encoding="utf-8"
    )
    result = load_profile(tmp_path)
    assert result["folder_mapping"]["moc"] == "Custom/Maps/"
```

**Validation test style** (lines 137-158):
```python
def test_validate_profile_unknown_key():
    errors = validate_profile({"bad_key": 1})
    assert len(errors) == 1
    assert "Unknown profile key 'bad_key'" in errors[0]


def test_validate_profile_traversal_in_folder_mapping():
    errors = validate_profile({"folder_mapping": {"moc": "../escape"}})
    assert len(errors) == 1
    assert ".." in errors[0]
```

**Atomic profile guard pattern** (lines 1118-1128):
```python
def test_profile_diagram_types_atomicity_guard():
    """PROF-02 atomicity: all four required sites land together.

    Guards against future splits: _VALID_TOP_LEVEL_KEYS, _DEFAULT_PROFILE,
    and validate_profile must agree on diagram_types within the same import.
    """
    from graphify.profile import _VALID_TOP_LEVEL_KEYS, _DEFAULT_PROFILE, validate_profile
    assert "diagram_types" in _VALID_TOP_LEVEL_KEYS
    assert "diagram_types" in _DEFAULT_PROFILE
    assert validate_profile(_DEFAULT_PROFILE) == []
```

**CLI preflight subprocess pattern** (lines 1409-1415):
```python
def _run_validate_profile(vault_path: Path) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify --validate-profile <vault_path>` as subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "graphify", "--validate-profile", str(vault_path)],
        capture_output=True,
        text=True,
    )
```

**Apply to Phase 32:**
- Update existing default assertions from `Atlas/Maps/`, `Atlas/Dots/`, and `moc_threshold`.
- Add taxonomy atomicity guard: `_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`, `validate_profile(_DEFAULT_PROFILE)`, and preflight all agree.
- Add invalid taxonomy key/path tests near existing folder/path tests.
- Add `mapping.moc_threshold` rejection and `mapping.min_community_size` acceptance tests.
- Add `--validate-profile` subprocess coverage for errors and warnings.

### `tests/test_mapping.py` (test, transform)

**Analog:** `tests/test_mapping.py`

**Fixture profile helper to update** (lines 91-110):
```python
def _profile(**overrides) -> dict:
    base = {
        "folder_mapping": {
            "moc": "Atlas/Maps/",
            "thing": "Atlas/Dots/Things/",
            "statement": "Atlas/Dots/Statements/",
            "person": "Atlas/Dots/People/",
            "source": "Atlas/Sources/",
            "default": "Atlas/Dots/",
        },
        "mapping_rules": [],
        "topology": {"god_node": {"top_n": 1}},
        "mapping": {"moc_threshold": 3},
    }
    base.update(overrides)
    return base
```

**Folder behavior assertions to update** (lines 115-147):
```python
def test_classify_default_statement_uses_folder_mapping_default():
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert result["per_node"]["n_softmax"]["note_type"] == "statement"
    assert result["per_node"]["n_softmax"]["folder"] == "Atlas/Dots/Statements/"
...
def test_classify_topology_fallback_god_node_becomes_thing():
    ...
    assert result["per_node"]["n_transformer"]["folder"] == "Atlas/Dots/Things/"
```

**Threshold behavior assertions to update** (lines 424-452):
```python
def test_community_above_threshold_becomes_moc():
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    assert 0 in result["per_community"]
    assert result["per_community"][0]["note_type"] == "moc"
    assert result["per_community"][0]["folder"] == "Atlas/Maps/"
    assert result["per_community"][0]["community_name"] == "Transformer"
```

**Bucket assertions to update** (lines 468-497):
```python
def test_bucket_moc_absorbs_hostless_below_threshold():
    ...
    result = classify(G, communities, _profile())
    # No above-threshold communities → bucket MOC emitted
    assert -1 in result["per_community"]
    assert result["per_community"][-1]["community_name"] == "Uncategorized"
    assert result["per_community"][-1]["community_tag"] == "uncategorized"
    # Both below communities merged into bucket
    assert len(result["per_community"][-1]["sub_communities"]) == 2
```

**Apply to Phase 32:**
- Update `_profile()` to use v1.8 Graphify subtree defaults and `mapping.min_community_size`.
- Add taxonomy-over-`folder_mapping` precedence tests in `classify()`.
- Add `_Unclassified` MOC naming/path tests.
- Keep the existing fixture-based pattern; do not introduce filesystem setup for pure mapping behavior.

### `tests/test_doctor.py` (test, diagnostic request-response)

**Analog:** `tests/test_doctor.py`

**Vault fixture pattern** (lines 22-43):
```python
def _make_vault(tmp_path: Path, *, profile_text: str | None = None) -> Path:
    """Create a synthetic Obsidian vault under tmp_path/vault.

    - .obsidian/  marks it as a vault (D-04)
    - .git/       halts _load_graphifyignore walk-up (RESEARCH §Pitfall 6)
    - .graphify/  for profile.yaml when profile_text is provided
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    (vault / ".graphify").mkdir()
    if profile_text is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_text)
    return vault
```

**Invalid profile diagnostic pattern** (lines 62-75):
```python
def test_run_doctor_invalid_profile(tmp_path):
    pytest.importorskip("yaml")
    # mode is invalid -> resolve_output _refuse() captures into errors
    bad = (
        "output:\n"
        "  mode: not-a-mode\n"
        "  path: Atlas/Generated\n"
    )
    vault = _make_vault(tmp_path, profile_text=bad)
    report = run_doctor(vault)
    assert report.profile_validation_errors, (
        f"expected non-empty errors, got: {report.profile_validation_errors}"
    )
    assert report.is_misconfigured() is True
```

**Formatting section-order pattern** (lines 176-186):
```python
def test_format_report_section_order(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    text = format_report(report)
    i_vault = text.index("Vault Detection")
    i_profile = text.index("Profile Validation")
    i_output = text.index("Output Destination")
    i_ignore = text.index("Ignore-List")
    i_fixes = text.index("Recommended Fixes")
    assert i_vault < i_profile < i_output < i_ignore < i_fixes
```

**Fix-hint coverage pattern** (lines 210-229):
```python
def test_fix_hints_coverage():
    """For each _FIX_HINTS entry, synthesizing the matching error yields the fix line."""
    for pattern, fix_line in _FIX_HINTS:
        if pattern == "WOULD_SELF_INGEST":
            report = DoctorReport(would_self_ingest=True)
        else:
            report = DoctorReport(profile_validation_errors=[pattern])
        from graphify.doctor import _build_recommended_fixes
        fixes = _build_recommended_fixes(
            report.profile_validation_errors, report.would_self_ingest
        )
        assert fix_line in fixes
```

**Apply to Phase 32:**
- Add doctor tests for taxonomy errors and `mapping.moc_threshold` legacy errors.
- Add doctor tests for warning-level community overview deprecation if warnings are represented separately.
- Keep section ordering and `[graphify]` prefix invariants.

### `tests/test_export.py` (test, file-I/O dry-run)

**Analog:** `tests/test_export.py`

**Temporary output test pattern** (lines 14-20):
```python
def test_to_json_creates_file():
    G = make_graph()
    communities = cluster(G)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.json"
        to_json(G, communities, str(out))
        assert out.exists()
```

**Obsidian dry-run pattern** (lines 135-168):
```python
def test_to_obsidian_obsidian_dedup_hydrates_merged_from(tmp_path):
    """--obsidian-dedup populates G.nodes[canonical]['merged_from'] from dedup_report.json."""
    from graphify.export import to_obsidian
    import networkx as nx
    import json

    G = nx.Graph()
    G.add_node("authservice", label="AuthService", file_type="code",
               source_file="a.py", community=0)
    ...
    result = to_obsidian(
        G,
        communities={0: ["authservice"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
        obsidian_dedup=True,
    )
```

**Default obsidian behavior pattern** (lines 173-188):
```python
def test_to_obsidian_default_no_dedup_hydration(tmp_path):
    """Backward compat: default obsidian_dedup=False leaves merged_from untouched."""
    from graphify.export import to_obsidian
    import networkx as nx

    G = nx.Graph()
    G.add_node("foo", label="Foo", file_type="code", source_file="a.py", community=0)
    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()
    to_obsidian(
        G,
        communities={0: ["foo"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
    )
```

**Apply to Phase 32:**
- Add dry-run assertions on returned `MergePlan` action paths for no-profile defaults.
- Assert note paths begin with `Atlas/Sources/Graphify/` and MOC paths with `Atlas/Sources/Graphify/MOCs/`.
- Keep all filesystem writes under `tmp_path`; use `dry_run=True` when possible.

### `.planning/REQUIREMENTS.md` (docs/config, planning traceability)

**Analog:** `.planning/REQUIREMENTS.md`

**Current conflicting requirement wording** (lines 23-29):
```markdown
### Cluster Quality Floor

- [ ] **CLUST-01**: User can set `clustering.min_community_size` in the vault profile to control the minimum size for standalone MOC generation.
- [ ] **CLUST-02**: User sees isolate communities omitted from standalone MOC generation while their nodes remain available in graph data and non-community exports.
- [ ] **CLUST-03**: User sees tiny connected communities below the configured floor routed deterministically into an `_Unclassified` MOC.
- [ ] **CLUST-04**: User receives deterministic behavior when both legacy `mapping.moc_threshold` and new `clustering.min_community_size` are present, with the new key taking precedence.
```

**Traceability table pattern** (lines 102-115):
```markdown
| Requirement | Phase | Status |
|-------------|-------|--------|
| TAX-01 | Phase 32 | Pending |
| TAX-02 | Phase 32 | Pending |
| TAX-03 | Phase 32 | Pending |
| TAX-04 | Phase 32 | Pending |
| COMM-01 | Phase 34 | Pending |
| COMM-02 | Phase 35 | Pending |
| COMM-03 | Phase 32 | Pending |
| CLUST-01 | Phase 32 | Pending |
| CLUST-02 | Phase 34 | Pending |
| CLUST-03 | Phase 34 | Pending |
| CLUST-04 | Phase 32 | Pending |
```

**Apply to Phase 32:**
- Replace `clustering.min_community_size` with `mapping.min_community_size`.
- Replace CLUST-04 precedence wording with immediate invalidation of `mapping.moc_threshold`.
- If TAX-03 remains, align it with the Phase 32 decision that old profiles without `taxonomy` and `mapping.min_community_size` fail validation.

### `.planning/ROADMAP.md` (docs/config, planning traceability)

**Analog:** `.planning/ROADMAP.md`

**Phase 32 roadmap pattern** (lines 263-272):
```markdown
### Phase 32: Profile Contract & Defaults
**Goal:** Users get a stable v1.8 default vault taxonomy and actionable profile validation before downstream export behavior changes.
**Depends on:** Phase 31 (v1.7 template/profile foundation)
**Requirements:** TAX-01, TAX-02, TAX-03, TAX-04, COMM-03, CLUST-01, CLUST-04
**Success Criteria** (what must be TRUE):
  1. User can run graphify with no vault profile and see generated notes routed into a Graphify-owned default subtree, including concept MOCs under `Atlas/Sources/Graphify/MOCs/`
  2. User-authored vault profiles continue to override default folder placement without requiring profile rewrites
  3. User can validate a v1.8 profile and receive actionable errors or warnings for unsupported taxonomy keys, invalid folder mappings, or hard-deprecated community overview output
  4. User can set `clustering.min_community_size` and see it take deterministic precedence over legacy `mapping.moc_threshold` when both are present
```

**Progress table pattern** (lines 362-366):
```markdown
| 32. Profile Contract & Defaults | v1.8 | 0/TBD | Not started | - |
| 33. Naming & Repo Identity Helpers | v1.8 | 0/TBD | Not started | - |
| 34. Mapping, Cluster Quality & Note Classes | v1.8 | 0/TBD | Not started | - |
| 35. Templates, Export Plumbing & Dry-Run/Migration Visibility | v1.8 | 0/TBD | Not started | - |
| 36. Migration Guide, Skill Alignment & Regression Sweep | v1.8 | 0/TBD | Not started | - |
```

**Apply to Phase 32:**
- Update success criterion 2 to reflect strict v1.8 user-profile validation instead of no-rewrite compatibility.
- Update success criterion 4 to `mapping.min_community_size` and `mapping.moc_threshold` invalidation.
- Keep phase status/progress edits scoped to Phase 32 planning/execution state.

## Shared Patterns

### Profile Schema Atomicity
**Source:** `graphify/profile.py`, `tests/test_profile.py`
**Apply to:** `graphify/profile.py`, `tests/test_profile.py`
```python
_DEFAULT_PROFILE: dict = {
    ...
    "mapping": {"moc_threshold": 3},
}

_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", ...
}

def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    ...
    return errors
```

### Path Safety
**Source:** `graphify/profile.py`, `graphify/mapping.py`
**Apply to:** taxonomy folder values, folder mappings, mapping rule folders
```python
elif ".." in path_val:
    errors.append(
        f"folder_mapping.{name} contains '..' — "
        "path traversal sequences are not allowed in folder mappings"
    )
elif Path(path_val).is_absolute():
    errors.append(
        f"folder_mapping.{name} is an absolute path — "
        "only relative paths are allowed in folder mappings"
    )
elif path_val.startswith("~"):
    errors.append(
        f"folder_mapping.{name} starts with '~' — "
        "home-relative paths are not allowed in folder mappings"
    )
```

### Preflight as Shared UX Source
**Source:** `graphify/profile.py`, `graphify/__main__.py`, `graphify/doctor.py`
**Apply to:** `--validate-profile`, `graphify doctor`, tests
```python
result = validate_profile_preflight(vault_arg)
for err in result.errors:
    print(f"error: {err}", file=sys.stderr)
for warn in result.warnings:
    print(f"warning: {warn}", file=sys.stderr)
```

### Mapping Owns Folder Routing
**Source:** `graphify/mapping.py`, `graphify/export.py`
**Apply to:** taxonomy precedence and default folder semantics
```python
mapping_result = classify(G, communities, profile, cohesion=cohesion)
per_node = mapping_result.get("per_node", {}) or {}
per_community = mapping_result.get("per_community", {}) or {}
...
folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("default", "Atlas/Dots/")
target_path = out / folder / filename
```

### Warning-Level Deprecation
**Source:** `graphify/templates.py`, `graphify/profile.py`
**Apply to:** community overview profile/template usage
```python
_NOTE_TYPES: frozenset[str] = frozenset({
    "moc", "community", "thing", "statement", "person", "source",
})
```

Keep `community` render support in place during Phase 32. Emit preflight warnings naming the deprecated profile setting or template rather than removing the renderer.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `/Users/silveimar/Documents/ls-vault/.graphify/profile.yaml` | external config | file-I/O | Folded todo references this personal vault file, but Phase 32 decisions say to fix built-in defaults and validation in repo code rather than edit the external vault directly. |

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/todos/pending/fix-ls-vault-profile-routing.md`
**Files scanned:** 15
**Project rules:** No repo-local `.cursor/rules/`, `.cursor/skills/`, or `.agents/skills/` files found.
**Pattern extraction date:** 2026-04-28
