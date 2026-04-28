# Phase 30: Profile Composition — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 5 (3 modify, 2 create)
**Analogs found:** 5 / 5 (all in-repo, exact-role matches)

---

## File Classification

| New/Modified File | Action | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `graphify/profile.py` | EXTEND | config / validator / loader | request-response (file -> dict; errors-as-list) | self (lines 156-202, 209-478, 668-822) + `graphify/mapping.py::validate_rules` (lines 707-790) | exact |
| `graphify/templates.py` | EXTEND | renderer / dispatcher | transform (profile + ctx -> string.Template) | self `_render_moc_like` (lines 709-823) + `load_templates` (lines 206-260) | exact |
| `graphify/__main__.py` | EXTEND | CLI dispatcher | request-response (argv -> stdout/stderr + exit) | self `--validate-profile` block (lines 1265-1290) | exact |
| `tests/test_profile_composition.py` | CREATE | unit tests (pytest) | filesystem-backed unit tests under `tmp_path` | `tests/test_profile.py` (1389 lines, 60+ tests) | exact |
| `tests/fixtures/profiles/` | CREATE | YAML fixture vaults | static data | `tests/fixtures/` (existing convention) | role-match |

---

## Pattern Assignments

### `graphify/profile.py` (config / validator / loader, EXTEND)

**Primary analog:** `graphify/profile.py` (self) — extending an existing module. New code MUST mirror the existing function-shape, error accumulator, and graceful-fallback contracts.

**Secondary analog (for `community_templates` validator):** `graphify/mapping.py::validate_rules` (lines 707-790) — the canonical "iterate-over-list-of-dicts, accumulate `mapping_rules[i].field: error` strings" pattern.

#### Excerpt 1 — `_deep_merge` (lines 156-164) — the shape `_deep_merge_with_provenance` MUST mirror

```python
def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*. Override wins at leaf level."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

**Copy-rule for the provenance variant (R3):** The new `_deep_merge_with_provenance` MUST also start with `result = base.copy()` so it preserves the "does not mutate base" contract that `tests/test_profile.py::test_deep_merge_does_not_mutate_base` (line 46) asserts. Add provenance-write `provenance[dotted] = source_path` only on the leaf-write branch (the `else:` arm).

#### Excerpt 2 — `load_profile` graceful-fallback contract (lines 167-202)

```python
def load_profile(vault_dir: str | Path | None) -> dict:
    if vault_dir is None:
        return _deep_merge(_DEFAULT_PROFILE, {})
    profile_path = Path(vault_dir) / ".graphify" / "profile.yaml"
    if not profile_path.exists():
        return _deep_merge(_DEFAULT_PROFILE, {})
    try:
        import yaml
    except ImportError:
        print("[graphify] PyYAML not installed ...", file=sys.stderr)
        return _deep_merge(_DEFAULT_PROFILE, {})
    user_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    errors = validate_profile(user_data)
    if errors:
        for err in errors:
            print(f"[graphify] profile error: {err}", file=sys.stderr)
        return _deep_merge(_DEFAULT_PROFILE, {})
    return _deep_merge(_DEFAULT_PROFILE, user_data)
```

**Copy-rule:** The refactored `load_profile` MUST keep ALL four early-return-with-defaults arms (None vault_dir, missing file, ImportError, validation errors) and ALSO add a fifth arm: resolver returned errors -> stderr loop with `[graphify] profile error: {err}` prefix -> return `_deep_merge(_DEFAULT_PROFILE, {})`. Never raise. Never crash. The `or {}` empty-YAML guard (line 194) MUST be replicated inside the resolver's `_load_one`.

#### Excerpt 3 — `_VALID_TOP_LEVEL_KEYS` whitelist (lines 104-108)

```python
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output",
}
```

**Copy-rule:** Add three keys to this set: `"extends"`, `"includes"`, `"community_templates"`. The unknown-key validator at lines 218-221 then accepts them automatically:
```python
for key in profile:
    if key not in _VALID_TOP_LEVEL_KEYS:
        errors.append(f"Unknown profile key '{key}' — valid keys are: {sorted(_VALID_TOP_LEVEL_KEYS)}")
```

#### Excerpt 4 — `validate_rules` shape for the `community_templates` validator (graphify/mapping.py:707-790)

```python
def validate_rules(rules: list) -> list[str]:
    errors: list[str] = []
    if rules is None:
        return errors
    if not isinstance(rules, list):
        errors.append("'mapping_rules' must be a list")
        return errors
    for idx, rule in enumerate(rules):
        prefix = f"mapping_rules[{idx}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: must be a mapping (dict)")
            continue
        # ... field-by-field accumulation ...
        extra_keys = set(then) - {"note_type", "folder"}
        if extra_keys:
            errors.append(
                f"{prefix}.then: unknown keys {sorted(extra_keys)} — "
                "only 'note_type' and 'folder' are supported (D-46)"
            )
    return errors
```

**Copy-rule for `community_templates` validator (D-09, D-10, R5):**
- Iterate with `for idx, rule in enumerate(rules):` and prefix every error with `f"community_templates[{idx}]"` for grep-ability.
- Reject non-dict entries with `continue` so later rules still validate.
- Required keys `match`, `pattern`, `template`; `match in {"label", "id"}`; per-entry unknown-key rejection mirroring lines 786-790.
- **bool-before-int guard (R5):** when `match == "id"`, validate `if isinstance(pattern, bool) or not isinstance(pattern, int):` — the existing precedent is `profile.py:319` (`top_n` validator) and `profile.py:337` (`moc_threshold` validator). Pattern from `topology.god_node.top_n`:
  ```python
  if isinstance(top_n, bool) or not isinstance(top_n, int):
      errors.append(f"topology.god_node.top_n must be an integer (got {type(top_n).__name__})")
  ```
- **template-path safety:** mirror `folder_mapping` checks at lines 281-296 — reject `..`, absolute, and `~`-prefix:
  ```python
  elif ".." in path_val:
      errors.append(f"folder_mapping.{name} contains '..' — ...")
  elif Path(path_val).is_absolute():
      errors.append(f"folder_mapping.{name} is an absolute path — ...")
  elif path_val.startswith("~"):
      errors.append(f"folder_mapping.{name} starts with '~' — ...")
  ```

#### Excerpt 5 — `validate_vault_path` reuse (profile.py lines 485-499)

```python
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    try:
        resolved.relative_to(vault_base)
    except ValueError:
        raise ValueError(
            f"Profile-derived path {candidate!r} would escape vault directory {vault_base}. ..."
        )
    return resolved
```

**Copy-rule for fragment-path resolution (D-07, R9):** Use Approach A from RESEARCH.md — compute `canonical = (referencing_file.parent / ext).resolve()` then assert `canonical.is_relative_to((vault_dir / ".graphify").resolve())`. `Path.resolve()` follows symlinks; the post-resolve `is_relative_to` check rejects symlink targets outside `.graphify/`. Reject with an error string matching the existing voice (`"fragment {path} escapes .graphify/"`), never raise — feed into the resolver's `errors: list[str]` accumulator.

#### Excerpt 6 — `validate_profile_preflight` PyYAML + parse-error guard (profile.py lines 738-755)

```python
if profile_path.exists():
    try:
        import yaml
    except ImportError:
        errors.append("PyYAML not installed — cannot read profile.yaml. ...")
        return PreflightResult(errors, warnings, rule_count, template_count)
    try:
        user_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        errors.append(f".graphify/profile.yaml parse error: {exc}")
        return PreflightResult(errors, warnings, rule_count, template_count)
    if not isinstance(user_data, dict):
        errors.append(".graphify/profile.yaml top-level must be a mapping (dict)")
        return PreflightResult(errors, warnings, rule_count, template_count)
```

**Copy-rule for `_resolve_profile_chain._load_one`:** Replicate the three-tier guard — ImportError, YAMLError, non-dict top-level — in the resolver's per-fragment loader. Each maps to one error string appended to `errors` and `return None` from `_load_one`.

#### Excerpt 7 — `PreflightResult` NamedTuple extension (profile.py lines 13-29)

```python
class PreflightResult(NamedTuple):
    errors: list[str]
    warnings: list[str]
    rule_count: int
    template_count: int
```

**Copy-rule (R1 — backward compatibility):** Append new fields **at the end**:
```python
class PreflightResult(NamedTuple):
    errors: list[str]
    warnings: list[str]
    rule_count: int
    template_count: int
    chain: list[Path] = []                     # NEW (Phase 30, D-14)
    provenance: dict[str, Path] = {}           # NEW (Phase 30, D-14, D-15)
    community_template_rules: list[dict] = []  # NEW (Phase 30, D-14, D-17)
```
Existing callers using `errors, warnings, *_ = result` continue to unpack unchanged. Default values keep `PreflightResult(errors, warnings, 0, 0)` constructor calls valid for the existing return-early paths in lines 711-718.

---

### `graphify/templates.py` (renderer / dispatcher, EXTEND)

**Analog:** `graphify/templates.py::_render_moc_like` (lines 709-823, the dispatch surface) + `graphify/templates.py::load_templates` (lines 206-260, the validate-then-fallback pattern).

#### Excerpt 1 — `_render_moc_like` dispatch site (lines 810-820)

```python
templates = (
    load_templates(vault_dir)
    if vault_dir is not None
    else {
        nt: _load_builtin_template(nt)
        for nt in ("thing", "statement", "person", "source", "moc", "community")
    }
)
template = templates[template_key]                 # ← INJECTION POINT
text = template.safe_substitute(substitution_ctx)
```

**Copy-rule for `_pick_community_template` (D-12, D-13):** Replace the `template = templates[template_key]` line with:
```python
default_template = templates[template_key]
template = _pick_community_template(
    community_id=community_id,
    community_name=community_name,
    profile=profile,
    vault_dir=vault_dir,
    default_template=default_template,
)
```
The override applies ONLY here — `render_note()` at lines 691-698 stays untouched (D-12 MOC-only scope is enforced structurally by call-site, not by config).

#### Excerpt 2 — `load_templates` validate-then-fallback (lines 232-253)

```python
if user_text is not None:
    errors = validate_template(user_text, required)
    if errors:
        for err in errors:
            print(
                f"[graphify] template error: {note_type}.md — {err}",
                file=sys.stderr,
            )
        templates[note_type] = _load_builtin_template(note_type)
    else:
        templates[note_type] = string.Template(user_text)
else:
    templates[note_type] = _load_builtin_template(note_type)
```

**Copy-rule for `_load_override_template` (CFG-03 fallback chain):** Replicate the validate-then-stderr-then-fallback chain exactly:
1. `validate_vault_path(rule["template"], vault_dir)` — on `ValueError` → stderr `[graphify] community_template error: {exc}` → return `default_template`.
2. `Path.read_text(encoding="utf-8")` — on `OSError` → stderr same prefix → return `default_template`.
3. `validate_template(text, _REQUIRED_PER_TYPE["moc"])` — on non-empty errors → stderr loop → return `default_template`.
4. Otherwise return `string.Template(user_text)`.

The stderr prefix MUST match `[graphify] ...` voice (see graceful-fallback in load_profile excerpt 2).

#### Excerpt 3 — fnmatch dispatch (NEW pattern, no in-repo analog)

```python
import fnmatch  # stdlib

def _pick_community_template(community_id, community_name, profile, vault_dir, default_template):
    rules = profile.get("community_templates") or []
    for rule in rules:                                # first-match-wins (D-13)
        match = rule.get("match")
        pattern = rule.get("pattern")
        if match == "label" and isinstance(pattern, str) and isinstance(community_name, str):
            if fnmatch.fnmatchcase(community_name, pattern):     # case-sensitive (R6)
                return _load_override_template(rule["template"], vault_dir, default_template)
        elif match == "id" and isinstance(pattern, int) and not isinstance(pattern, bool):
            if pattern == community_id:
                return _load_override_template(rule["template"], vault_dir, default_template)
    return default_template
```

**Copy-rule (R6 — `fnmatchcase` not `fnmatch`):** Use `fnmatch.fnmatchcase` for portable case-sensitive matching. `fnmatch.fnmatch` does platform-dependent case-folding (POSIX vs Windows) and would silently break cross-platform fixtures.

---

### `graphify/__main__.py` (CLI dispatcher, EXTEND)

**Analog:** `graphify/__main__.py:1265-1290` — the existing `--validate-profile` dispatch block.

#### Excerpt 1 — current dispatch (lines 1265-1284)

```python
if cmd == "--validate-profile":
    if len(sys.argv) < 3:
        print("Usage: graphify --validate-profile <vault-path>", file=sys.stderr)
        sys.exit(2)
    from graphify.profile import validate_profile_preflight
    result = validate_profile_preflight(Path(sys.argv[2]))
    for err in result.errors:
        print(f"error: {err}", file=sys.stderr)
    for warn in result.warnings:
        print(f"warning: {warn}", file=sys.stderr)
    if result.errors:
        sys.exit(1)
    print(
        f"profile ok — {result.rule_count} rules, "
        f"{result.template_count} templates validated"
    )
    sys.exit(0)
```

**Copy-rule for Phase 30 extensions (D-14, D-16):**
- Keep error/warning loop AND `sys.exit(1)` arm UNCHANGED — exit-code contract preserved (D-14 final paragraph).
- Insert THREE new sections to **stdout** AFTER the success line `profile ok — N rules, M templates validated`, regardless of whether the profile uses `extends:`/`includes:`. Single-file profile MUST still print `Merge chain (root ancestor first):` followed by one line.
- Use the U+2014 em-dash (`—`) already present at line 1283 — match existing visual style.
- Use U+2190 left-arrow (`←`) for provenance arrows and U+2192 right-arrow (`→`) for chain arrows (matches CONTEXT.md examples and existing cycle-error voice).
- Iterate `result.chain`, `result.provenance`, `result.community_template_rules` — preflight is the single source of truth; `__main__.py` does pure formatting.

Render shape (verbatim from RESEARCH.md §--validate-profile Output Extension):

```
profile ok — 3 rules, 2 templates validated

Merge chain (root ancestor first):
  bases/core.yaml
  bases/fusion.yaml
  profile.yaml

Field provenance (15 leaf fields):
  folder_mapping.thing                   ← bases/core.yaml
  folder_mapping.statement               ← bases/core.yaml
  ...

Resolved community templates (2 rules):
  [1] match=label  pattern="transformer*"     template=templates/transformer-moc.md
  [2] match=id     pattern=0                  template=templates/big-community-moc.md
  (note: actual community-to-template assignments require a graph — run after `graphify`)
```

For `community_template_rules == []`, print `Resolved community templates: (none)` (single line, parenthesized empty marker matches RESEARCH.md example).

---

### `tests/test_profile_composition.py` (unit tests, CREATE)

**Analog:** `tests/test_profile.py` (1389 lines, 60+ tests) — exact role match (one test file per module).

#### Excerpt 1 — header + imports (test_profile.py lines 1-24)

```python
from __future__ import annotations

"""Unit tests for graphify/profile.py — profile loading, validation, and safety helpers."""

import sys
import unicodedata
from pathlib import Path
from unittest import mock

import pytest

import datetime

from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    _dump_frontmatter,
    load_profile,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_profile,
    validate_vault_path,
)
```

**Copy-rule:** Mirror header verbatim. Module docstring: `"""Unit tests for graphify/profile.py composition + community_templates (Phase 30)."""`. Imports add `_resolve_profile_chain`, `_deep_merge_with_provenance`, `validate_profile_preflight` from `graphify.profile`.

#### Excerpt 2 — `tmp_path` fixture pattern (test_profile.py lines 63-83)

```python
def test_load_profile_with_yaml(tmp_path):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text(
        'folder_mapping:\n  moc: "Custom/Maps/"\n', encoding="utf-8"
    )
    result = load_profile(tmp_path)
    assert result["folder_mapping"]["moc"] == "Custom/Maps/"
    assert result["folder_mapping"]["thing"] == "Atlas/Dots/Things/"


def test_load_profile_empty_yaml_returns_defaults(tmp_path):
    """Empty YAML returns None from safe_load — guarded by `or {}` (Pitfall 1)."""
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("", encoding="utf-8")
    result = load_profile(tmp_path)
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
```

**Copy-rule (R10 — fixture isolation):** Every test constructs its vault under `tmp_path / ".graphify"` (or copies a fixture vault via `shutil.copytree` per RESEARCH.md R10). NEVER reference `tests/fixtures/profiles/` directly — `Path.resolve()` is sensitive to vault location, so symlink and path-confinement tests would behave inconsistently.

#### Excerpt 3 — capsys + stderr-fallback assertion (test_profile.py lines 84-94)

```python
def test_load_profile_invalid_yaml_prints_errors(tmp_path, capsys):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("unknown_key: 1\n", encoding="utf-8")
    result = load_profile(tmp_path)
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err
    assert "Unknown profile key 'unknown_key'" in captured.err
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
```

**Copy-rule for cycle/depth/path-escape tests:** Use `capsys` to capture stderr; assert the `[graphify] profile error:` prefix; assert specific substrings of the error message; assert the result equals `_deep_merge(_DEFAULT_PROFILE, {})` (graceful-fallback contract).

#### Excerpt 4 — depth-chain helper (NEW, RESEARCH.md §Test Fixture Layout)

```python
def _make_chain(tmp_path: Path, depth: int) -> Path:
    """Programmatically create lvl0.yaml..lvl{depth}.yaml under tmp_path/.graphify/."""
    graphify_dir = tmp_path / ".graphify"
    graphify_dir.mkdir(parents=True, exist_ok=True)
    for i in range(depth):
        (graphify_dir / f"lvl{i}.yaml").write_text(f"extends: lvl{i + 1}.yaml\n", encoding="utf-8")
    (graphify_dir / f"lvl{depth}.yaml").write_text("folder_mapping:\n  moc: Atlas/Maps/\n", encoding="utf-8")
    return graphify_dir / "lvl0.yaml"
```

**Copy-rule:** Use this helper for `test_depth_cap_8` (depth=8, success boundary) and `test_depth_cap_8` (depth=9, failure). Cleaner than committing 9 nearly-identical fixture files.

#### Excerpt 5 — symlink test pattern (NEW, R9)

```python
def test_extends_symlink_escape_rejected(tmp_path):
    if not hasattr(Path, "symlink_to"):
        pytest.skip("symlinks unavailable on this platform")
    outside = tmp_path / "outside.yaml"
    outside.write_text("folder_mapping:\n  moc: Evil/\n", encoding="utf-8")
    graphify_dir = tmp_path / "vault" / ".graphify"
    graphify_dir.mkdir(parents=True)
    (graphify_dir / "evil.yaml").symlink_to(outside)
    (graphify_dir / "profile.yaml").write_text("extends: evil.yaml\n", encoding="utf-8")
    # Assert resolver rejects + load_profile falls back
```

**Copy-rule (R9):** symlinks created at runtime in `tmp_path` (cannot live in git). Use `pytest.mark.skipif` or `pytest.skip` if symlink privileges are missing on Windows CI runners. CI is Linux-only per CLAUDE.md, so the skip path is mostly defensive.

---

### `tests/fixtures/profiles/` (YAML fixture vaults, CREATE)

**Analog:** `tests/fixtures/` (existing root used elsewhere in test suite for static data).

**Convention (RESEARCH.md §Test Fixture Layout):** One sub-directory per scenario, each containing a complete `.graphify/` tree mimicking a real vault. Recommended scenarios: `single_file/`, `linear_chain/`, `includes_only/`, `extends_and_includes/`, `cycle_self/`, `cycle_indirect/`, `diamond/`, `path_escape/`, `absolute_path/`, `community_templates/`, `partial_fragment/`.

**Copy-rule:** Static fixtures (`linear_chain`, `diamond`, `community_templates`, `partial_fragment`) live under `tests/fixtures/profiles/` and are copied into `tmp_path` per test via `shutil.copytree`. Programmatic-only fixtures (depth chains, symlinks) live in test code, not on disk.

---

## Shared Patterns

### Errors-as-list-of-strings (CFG-02 + CFG-03)

**Source:** `graphify/profile.py::validate_profile` (lines 209-478) + `graphify/mapping.py::validate_rules` (lines 707-790)
**Apply to:** `_resolve_profile_chain`, the `community_templates` validator block in `validate_profile`, the new `_deep_merge_with_provenance` (no errors but follows the no-raise contract).

```python
errors: list[str] = []
# ... accumulate ...
errors.append(f"{prefix}.{field}: {reason} (got {type(value).__name__})")
return errors  # empty == valid
```

**Rule:** NEVER raise on validation failure. Always accumulate. Caller decides exit code.

### Graceful-fallback contract (`load_profile`)

**Source:** `graphify/profile.py::load_profile` (lines 167-202) + `graphify/templates.py::load_templates` (lines 232-253)
**Apply to:** Every new resolver/loader/dispatcher: `_resolve_profile_chain` (when called from `load_profile`), `_pick_community_template`, `_load_override_template`.

**Pattern:**
1. Try the user-authored thing.
2. On any error → print to stderr with `[graphify] {category} error: {message}` prefix.
3. Return the safe default (`_deep_merge(_DEFAULT_PROFILE, {})` for profile, built-in template for templates).
4. Never let an error propagate to the caller's caller. graphify NEVER crashes from a bad vault.

### Bool-before-int guard (R5)

**Source:** `profile.py:319` (top_n) + `profile.py:337` (moc_threshold) + `profile.py:387` (min_main_nodes)
**Apply to:** `community_templates[i].pattern` validator when `match == "id"`.

```python
if isinstance(value, bool) or not isinstance(value, int):
    errors.append(f"{prefix}.{field} must be an integer (got {type(value).__name__})")
```

**Rule:** Python's `bool` is a subclass of `int`; `isinstance(True, int) is True`. Always guard first.

### Function-local imports for circular-dep avoidance

**Source:** `profile.py:355` (`from graphify.mapping import validate_rules` inside `validate_profile`)
**Apply to:** Any place templates.py needs to call into profile.py during runtime dispatch (e.g., `_pick_community_template` calling `validate_vault_path` from profile.py).

```python
def some_function(...):
    # Function-local import breaks the circular dependency
    # (graphify.mapping imports from graphify.templates which imports
    # from graphify.profile).
    from graphify.X import Y
    ...
```

**Rule:** When a downstream module needs an upstream symbol AND adding a module-level import would cycle, use a function-local import inside the calling function. Pattern is documented in profile.py:355-358.

### Path-confinement via `Path.resolve()` + `is_relative_to()`

**Source:** `profile.py::validate_vault_path` (lines 485-499) + `profile.py::validate_sibling_path` (lines 502-543)
**Apply to:** Fragment-path resolution in `_resolve_profile_chain._load_one`; community-template-path validation in `_load_override_template`.

```python
canonical = (referencing_file.parent / fragment_string).resolve()
if not canonical.is_relative_to((vault_dir / ".graphify").resolve()):
    errors.append(f"fragment {fragment_string!r} escapes .graphify/")
    return None
```

**Rule:** Always `.resolve()` before checking confinement. `resolve()` follows symlinks; the post-resolve `is_relative_to` is the security boundary against outward-pointing symlinks (D-07). Python 3.10+ floor guarantees `is_relative_to` availability.

---

## No Analog Found

| File / Capability | Reason | Fallback Strategy |
|-------------------|--------|-------------------|
| `_resolve_profile_chain` (the chain walker itself) | No existing chain-resolver in graphify; this is a new architectural primitive. | Use the algorithm sketch in RESEARCH.md §Resolver Design (lines 100-194). Cycle detection uses a stack-local `currently_descending: set[Path]` (R8). Depth cap uses an int parameter incremented on each recursive call. |
| Field provenance tracking | No existing per-key source-attribution code. | RESEARCH.md §`_deep_merge_with_provenance` provides the algorithm — flat `dict[dotted_key, Path]`, recorded only on the leaf-write branch. |
| `--validate-profile` 3-section output rendering | Existing dispatch only prints error/warning lines + the success line. | RESEARCH.md §--validate-profile Output Extension specifies the visual contract (em-dash, `←`, `→`, single-file degenerate case). |

These three are net-new; planner should reference RESEARCH.md sections directly for the algorithm and CONTEXT.md decisions (D-04, D-05, D-14, D-15) for the contract.

---

## Metadata

**Analog search scope:** `graphify/profile.py`, `graphify/templates.py`, `graphify/mapping.py`, `graphify/__main__.py`, `graphify/security.py`, `tests/test_profile.py`, `tests/test_templates.py`.
**Files scanned:** 7
**Pattern extraction date:** 2026-04-28

---

## PATTERN MAPPING COMPLETE

**Phase:** 30 - profile-composition
**Files classified:** 5
**Analogs found:** 5 / 5

### Coverage
- Files with exact analog: 4 (profile.py, templates.py, __main__.py, tests/test_profile_composition.py)
- Files with role-match analog: 1 (tests/fixtures/profiles/)
- Files with no analog: 0 (resolver/provenance/output-rendering are net-new but specified end-to-end in RESEARCH.md)

### Key Patterns Identified
- All validators use the errors-as-list-of-strings accumulator (`validate_profile`, `validate_rules`); resolver and `community_templates` validator MUST follow suit (no raises on validation problems).
- `load_profile` graceful-fallback contract is non-negotiable: every error path returns `_deep_merge(_DEFAULT_PROFILE, {})` after a `[graphify] profile error: ...` stderr line. The new resolver plugs into the same contract.
- `PreflightResult` is extended at the END (default-valued NamedTuple fields) so existing `errors, warnings, *_ = result` callers continue to work — backward-compat is verified by the existing 60+ test_profile.py suite.
- `_pick_community_template` is the SINGLE injection point for CFG-03 (D-12 MOC-only); enforce structurally by call-site, not by config.
- Bool-before-int guard, `validate_vault_path` reuse, function-local imports, and `Path.resolve() + is_relative_to()` are all established patterns; new code copies them verbatim.

### File Created
`.planning/phases/30-profile-composition/30-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference per-file analog excerpts and shared cross-cutting patterns directly when authoring the 3 plans (resolver+schema, runtime dispatch, CLI output) identified in RESEARCH.md §Implementation Surface Estimate.
