# Phase 30: Profile Composition - Research

**Researched:** 2026-04-28
**Domain:** Profile composition (extends/includes), per-community template overrides, --validate-profile output extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Profiles support BOTH `extends:` (single-parent string) AND `includes:` (ordered list of mixin fragments) with distinct semantics. Familiar mental model from ESLint/Spectral/TS configs.
- **D-02:** Merge order when both are present: parent chain via `extends:` resolved first (depth-first, post-order — root ancestor's fields are the foundation), then `includes:` layered in declared order (sequential `_deep_merge`, last wins), then this profile's own fields applied last as the most-specific override.
- **D-03:** `extends:` MUST be a string (single parent only). Multi-base composition is expressed exclusively via `includes:`.
- **D-04:** Cycle detection: `[graphify] profile error: extends/includes cycle detected: a.yaml → b.yaml → c.yaml → a.yaml` to stderr, non-zero exit from `--validate-profile`. From `load_profile()`: print error and fall back to `_DEFAULT_PROFILE` (graceful-fallback contract preserved).
- **D-05:** Hard recursion-depth cap of 8 levels (belt-and-suspenders against pathological YAML).
- **D-06:** Paths in `extends:`/`includes:` resolve **relative to the file containing the directive** (sibling-relative).
- **D-07:** Strict in-vault confinement — every resolved path MUST stay inside `.graphify/`. Absolute paths, `../` escapes, and outward-pointing symlinks rejected. Reuses v1.0 `validate_vault_path()`.
- **D-08:** Fragments may be **partial profiles** — only the fully-composed profile is required to pass `validate_profile()`.
- **D-09:** New top-level key: `community_templates: [...]`. Adds one entry to `_VALID_TOP_LEVEL_KEYS`. Stays at top level (not nested under `obsidian:`).
- **D-10:** Each rule has explicit field selector: `{match: 'label' | 'id', pattern: <str|int>, template: <relative-path>}`.
- **D-11:** Pattern syntax = stdlib `fnmatch` globs.
- **D-12:** Override scope is **MOC-only** — applies to community's MOC note; member nodes keep their type-based templates.
- **D-13:** First-match-wins precedence (consistent with v1.0 `mapping_rules`).
- **D-14:** Every `--validate-profile` run prints three new sections in plain text: (1) Merge chain, (2) Field provenance, (3) Resolved community templates rule list.
- **D-15:** "Lost fields" success criterion satisfied by the field-provenance table — no separate diff engine.
- **D-16:** Plain text output. No `--json`, no tree rendering. Both deferred.
- **D-17:** `--validate-profile` stays **graph-blind** — does not auto-load `graphify-out/graph.json`. Rule list dumped as-written.

### Claude's Discretion

- File-format details (delimiters, whitespace, ordering) within `--validate-profile` output — match existing visual style.
- Internal API: how `load_profile()` is split between resolution and merge. Resolver MUST be the single source of truth used by both `load_profile()` and `--validate-profile`.
- Cycle/depth check ordering and exact error wording.
- Test fixture layout under `tests/fixtures/profiles/`.

### Deferred Ideas (OUT OF SCOPE)

- `--validate-profile --json` output.
- `--explain-removal <fragment>` flag.
- Tree-style provenance rendering.
- Auto-resolving community-to-template assignments via `graphify-out/graph.json`.
- Org-wide / user-global fragments (absolute paths, `~/.graphify/`).
- Per-community templates beyond MOC (Things/Statements/etc.).
- Multi-parent `extends:` (string-or-list).
- Regex pattern syntax for `community_templates`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID      | Description (from REQUIREMENTS.md) | Research Support |
|---------|-----------------------------------|------------------|
| CFG-02  | Profile includes/extends mechanism — compose profiles from fragments via `extends:` or `includes:`; deterministic merge order; cycle detection | §Resolver Design (chain walk + visited-set + depth cap) + §Path Resolution & Security + §--validate-profile Output Extension |
| CFG-03  | Per-community template overrides — profile field mapping community ID/label patterns to custom templates; first-match-wins precedence consistent with v1.0 mapping engine | §Community Template Matching (fnmatch first-match dispatch in `templates.py::_render_moc_like`) |
</phase_requirements>

## Summary

Phase 30 closes CFG-02 and CFG-03 by extending the existing `graphify/profile.py` module with two orthogonal features: (a) a fragment **composition resolver** that walks `extends:` (single-parent chain) and `includes:` (ordered mixin list), detects cycles via canonical-path visited-set, enforces an 8-level recursion cap, and produces a single composed dict via the existing `_deep_merge`; and (b) a new `community_templates: [{match, pattern, template}]` top-level rule list evaluated first-match-wins (`fnmatch.fnmatchcase` for `match='label'`, exact int compare for `match='id'`) at MOC render time. Both features hook into the existing graceful-fallback contract — no profile error ever crashes graphify.

The critical architectural constraint: the new `_resolve_profile_chain()` function MUST be the **single source of truth** consumed by both `load_profile()` (production path, falls back to defaults on error) and `validate_profile_preflight()` (CLI path, returns errors + provenance + chain). They cannot diverge or success criterion 4 ("removing extends shows lost fields") becomes unreliable.

**Primary recommendation:** Add `_resolve_profile_chain(profile_path, vault_dir) -> ResolvedProfile` (NamedTuple with `composed`, `chain`, `provenance`, `errors`) returning the composed dict plus accounting metadata. `load_profile()` calls it and discards metadata; `validate_profile_preflight()` calls it and renders metadata into three new plain-text sections. Community-template dispatch lives in `templates.py::_render_moc_like` immediately before `template = templates[template_key]` — a small (~15 line) lookup that picks an override template path when a rule matches, validates it via `validate_vault_path` + `validate_template`, and falls back to the existing `templates[template_key]` on any failure.

## Architectural Responsibility Map

| Capability | Primary Module | Secondary Module | Rationale |
|------------|---------------|------------------|-----------|
| Fragment YAML loading + path resolution | `graphify/profile.py` (new `_resolve_profile_chain`) | `graphify/security.py::validate_vault_path` (path-traversal guard) | Profile module already owns YAML load + `_deep_merge` + validation; resolver is a thin orchestrator atop them. |
| Cycle / depth detection | `graphify/profile.py` (new helper inside resolver) | — | Pure algorithm; visited-set keyed by canonical absolute path. |
| Per-key field provenance tracking | `graphify/profile.py` (new `_deep_merge_with_provenance`) | — | Provenance is merge-time-only metadata; staying co-located with `_deep_merge` keeps the contract testable. |
| `community_templates` schema validation | `graphify/profile.py::validate_profile()` | — | Mirrors existing `mapping_rules` validation pattern (lines 348-357). |
| `community_templates` runtime dispatch | `graphify/templates.py::_render_moc_like` | `graphify/profile.py` (helper to pick rule) | Render-time pick is where the override actually applies; helper keeps fnmatch logic out of the render hot path. |
| `--validate-profile` output (3 new sections) | `graphify/profile.py::validate_profile_preflight` | `graphify/__main__.py` (calls preflight, prints output) | Preflight already returns a NamedTuple; extend with `chain`, `provenance`, `community_template_rules`. The `__main__.py` dispatch (lines 1265-1290) just iterates and prints. |

## Existing Profile System (current API surface)

**Public API in `graphify/profile.py`:**

| Symbol | Lines | Role | Phase 30 touch |
|--------|-------|------|----------------|
| `_DEFAULT_PROFILE` | 36-102 | Built-in defaults dict (Ideaverse ACE structure) | No change — defaults DO NOT carry `extends`/`includes`/`community_templates`. |
| `_VALID_TOP_LEVEL_KEYS` | 104-108 | Whitelist for unknown-key validation | **MUST add** `extends`, `includes`, `community_templates`. |
| `_deep_merge(base, override)` | 156-164 | Recursive merge, override wins at leaf, returns new dict (does NOT mutate `base` — verified at line 158 `base.copy()`) | Provenance variant added; original kept verbatim for back-compat. |
| `load_profile(vault_dir)` | 171-202 | Discover → load → validate → merge with defaults; graceful fallback on every error | **Refactor to call `_resolve_profile_chain`**, then `_deep_merge(_DEFAULT_PROFILE, composed)`. Falls back to defaults if chain returns errors. |
| `validate_profile(profile)` | 209-478 | Schema validator returning `list[str]` of error strings | **Add `community_templates` validator block** (mirrors `mapping_rules`). |
| `validate_vault_path(candidate, vault_dir)` | 485-499 | Path-traversal guard — resolves `vault_base / candidate` and asserts `relative_to(vault_base)` | **Reused for fragment paths** (callsite passes `.graphify/<rest>` as candidate). |
| `validate_profile_preflight(vault_dir)` | 668-822 | Four-layer preflight returning `PreflightResult(errors, warnings, rule_count, template_count)` | **Extend NamedTuple** with `chain`, `provenance`, `community_template_rules`. Call resolver instead of inline `yaml.safe_load`. |
| `PreflightResult` | 13-29 | Tuple-unpackable result struct | **Add 3 fields** at end (back-compat: `*_ = result` unpacks unchanged for existing callers). |

**Backward-compat constraints (verified by reading existing tests):**
- All 60+ existing `test_profile.py` tests pass with current `load_profile()` / `validate_profile()` semantics. New code MUST NOT change behaviour for profiles lacking `extends`/`includes`/`community_templates`.
- `_DEFAULT_PROFILE` is imported by external test fixtures (line 14 of `test_profile.py`); shape MUST stay stable.
- `PreflightResult` tuple unpacking pattern (`errors, warnings, *_ = result`) documented in its docstring — adding fields at the end preserves it.
- `validate_profile()` accepts non-dict input and returns `["Profile must be a YAML mapping (dict)"]` — fragments getting None/list need same treatment.

## Resolver Design (algorithm + provenance tracking)

### `_resolve_profile_chain(entry_path, vault_dir)`

```python
class ResolvedProfile(NamedTuple):
    composed: dict                     # final merged profile (NOT _deep_merged with _DEFAULT_PROFILE yet)
    chain: list[Path]                  # files in resolution order, root ancestor first
    provenance: dict[str, Path]        # dotted-key -> file that contributed leaf value
    errors: list[str]                  # cycle / depth / path / parse errors
    community_template_rules: list[dict]  # the resolved community_templates list (echo)


def _resolve_profile_chain(entry_path: Path, vault_dir: Path) -> ResolvedProfile:
    chain: list[Path] = []
    provenance: dict[str, Path] = {}
    errors: list[str] = []
    visited: set[Path] = set()           # canonical absolute paths seen on current path
    cycle_path: list[Path] = []          # for cycle error message

    def _load_one(path: Path, depth: int) -> dict | None:
        # 1. Depth check (D-05)
        if depth > 8:
            errors.append(f"extends/includes recursion depth exceeded 8 levels at {path}")
            return None
        # 2. Confine to .graphify/ (D-07): resolve & assert under vault_dir/.graphify
        try:
            canonical = validate_vault_path(path.relative_to(vault_dir), vault_dir)
        except ValueError as exc:
            errors.append(f"fragment path escapes .graphify/: {exc}")
            return None
        if not str(canonical).startswith(str((vault_dir / ".graphify").resolve())):
            errors.append(f"fragment {canonical} not inside .graphify/")
            return None
        # 3. Cycle check (D-04)
        if canonical in visited:
            cycle_path.append(canonical)
            errors.append(
                "extends/includes cycle detected: " +
                " → ".join(p.name for p in cycle_path)
            )
            return None
        # 4. Read + parse (PyYAML guard, empty-file guard)
        if not canonical.exists():
            errors.append(f"fragment not found: {canonical}")
            return None
        try:
            data = yaml.safe_load(canonical.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse error in {canonical.name}: {exc}")
            return None
        if not isinstance(data, dict):
            errors.append(f"{canonical.name}: top-level must be a mapping")
            return None

        visited.add(canonical)
        cycle_path.append(canonical)

        # 5. Resolve extends (single parent, post-order — D-02, D-03)
        composed: dict = {}
        ext = data.pop("extends", None)
        if ext is not None:
            if not isinstance(ext, str):
                errors.append(f"{canonical.name}: 'extends' must be a string (got {type(ext).__name__})")
            else:
                parent_path = (canonical.parent / ext).resolve()
                parent_data = _load_one(parent_path, depth + 1)
                if parent_data is not None:
                    composed = _deep_merge_with_provenance(composed, parent_data, parent_path, provenance)

        # 6. Resolve includes (ordered list — D-02)
        incs = data.pop("includes", None)
        if incs is not None:
            if not isinstance(incs, list):
                errors.append(f"{canonical.name}: 'includes' must be a list")
            else:
                for inc in incs:
                    if not isinstance(inc, str):
                        errors.append(f"{canonical.name}: 'includes' entries must be strings")
                        continue
                    inc_path = (canonical.parent / inc).resolve()
                    inc_data = _load_one(inc_path, depth + 1)
                    if inc_data is not None:
                        composed = _deep_merge_with_provenance(composed, inc_data, inc_path, provenance)

        # 7. Apply own fields last (D-02)
        composed = _deep_merge_with_provenance(composed, data, canonical, provenance)
        chain.append(canonical)
        cycle_path.pop()
        # Note: do NOT visited.discard(canonical) — diamond inheritance is allowed,
        # but cycle = same node revisited on the same descent path. We use a
        # frame-local "currently descending" set, not a permanent one. See variant below.
        return composed
    ...
```

**Cycle-detection refinement:** the visited-set must be **path-local** (set on entry to a frame, cleared on exit) NOT global, otherwise legitimate diamond `A extends B; A includes C; C extends B` flags B as a cycle. Use a stack-based `currently_descending` set instead of `visited`. Implementation: pass `descending: set[Path]` as a parameter, add on entry, remove on return.

### `_deep_merge_with_provenance(base, override, source_path, provenance)`

A new function. Mirrors `_deep_merge` line-for-line but additionally records the source path for every leaf write:

```python
def _deep_merge_with_provenance(base, override, source_path, provenance, _prefix=""):
    result = base.copy()
    for key, value in override.items():
        dotted = f"{_prefix}{key}" if _prefix else key
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_with_provenance(
                result[key], value, source_path, provenance, _prefix=f"{dotted}.")
        else:
            result[key] = value
            provenance[dotted] = source_path   # last writer wins → matches override semantics
    return result
```

**Provenance contract:** `provenance` is a flat `dict[dotted_key, Path]`. List-typed leaves (`mapping_rules`, `community_templates`, `tag_taxonomy.garden`, etc.) record at the **list level** — i.e. `mapping_rules ← fusion-base.yaml` rather than per-entry, because `_deep_merge`'s replace-on-non-dict semantics treat the entire list as one leaf. This is consistent with how the existing merge behaves and is what users see when they remove an `extends:` (the whole list disappears).

### Why the resolver returns the composed profile WITHOUT pre-merging defaults

`load_profile()` does `_deep_merge(_DEFAULT_PROFILE, user_data)` as its last step. Keeping the defaults-merge **outside** the resolver means:
1. Provenance only tracks user-authored fields (defaults are not interesting for the "lost fields" use case).
2. `--validate-profile` can show users which fields they actually contributed vs. inherited from defaults.
3. The chain output is meaningful: `chain = [base.yaml, fusion-base.yaml, profile.yaml]` — defaults are not part of the user-authored chain.

## Path Resolution & Security

### Resolution algorithm (D-06, D-07)

For each `extends`/`includes` string:

1. **Sibling-relative resolve**: `(referencing_file.parent / fragment_string).resolve()` — uses `pathlib.Path.resolve()` which canonicalizes symlinks and `..` segments.
2. **Vault confinement**: assert resolved path is under `(vault_dir / ".graphify").resolve()`. Use `Path.is_relative_to()` (Python 3.9+, available on the 3.10+ floor).
3. **Existence check**: `if not canonical.exists(): error`.
4. **File-type check**: implicit via `read_text()` raising `IsADirectoryError`.

### Reuse of `validate_vault_path()`

The existing helper takes `(candidate, vault_dir)` where `candidate` is **vault-relative**. For fragment resolution, the candidate is `extends_string` joined with the referencing file's vault-relative parent. Two viable approaches:

- **Approach A** (preferred): compute `canonical = (referencing_file.parent / ext).resolve()`, then assert `canonical.is_relative_to((vault_dir / ".graphify").resolve())`. Bypasses `validate_vault_path` because the function expects vault-relative input, not pre-resolved absolute paths.
- **Approach B**: derive vault-relative form by `canonical.relative_to(vault_dir)` and pass to `validate_vault_path`. More indirection but reuses the exact contract.

Recommend **Approach A** with a tight `is_relative_to` check; document that fragments are confined to `.graphify/` (stricter than `validate_vault_path`'s vault-wide confinement) and that the symlink-resolution behaviour of `Path.resolve()` is the security boundary against outward symlinks (D-07).

### Symlink handling

`Path.resolve()` follows symlinks by default. After resolution, `is_relative_to((vault_dir / ".graphify").resolve())` rejects any symlink target outside `.graphify/`. This satisfies "symlinks pointing outside are rejected" from D-07 without needing a separate symlink check.

### Extension policy

YAML allows both `.yaml` and `.yml`. The current vault contract (`profile.yaml`) uses `.yaml`. Recommend: **require the user to include the extension** in their `extends:`/`includes:` strings (no auto-`.yaml` suffix). Rejecting extension-less strings keeps error messages clear and avoids ambiguity. Test fixtures use `.yaml` consistently.

## Community Template Matching

### Schema (validate_profile additions, D-09 / D-10)

```yaml
community_templates:
  - match: label                          # 'label' | 'id'
    pattern: "transformer*"               # str for label, int for id
    template: templates/transformer-moc.md
  - match: id
    pattern: 0
    template: templates/big-community-moc.md
```

Validation (mirrors existing `mapping_rules`/`diagram_types` patterns in profile.py:348-410):

- `community_templates` must be `list`; each entry must be `dict`.
- `match` ∈ `{"label", "id"}` (required).
- `pattern` required: `str` if `match=="label"`, `int` (and not `bool`) if `match=="id"`.
- `template` required: non-empty `str`, no `..`, not absolute, not `~`-prefixed (mirror folder_mapping checks).
- Unknown keys per entry → error.

### Runtime dispatch (D-12, D-13)

The override applies to **community MOC notes only**. The dispatch site is `graphify/templates.py::_render_moc_like` (lines 709-823), specifically the block at lines 810-819:

```python
templates = (
    load_templates(vault_dir)
    if vault_dir is not None
    else { nt: _load_builtin_template(nt) for nt in (...) }
)
template = templates[template_key]   # ← inject override here
text = template.safe_substitute(substitution_ctx)
```

Replace with a small helper:

```python
def _pick_community_template(
    community_id: int,
    community_name: str,
    profile: dict,
    vault_dir: Path | None,
    default_template: string.Template,
) -> string.Template:
    rules = profile.get("community_templates") or []
    for rule in rules:
        match = rule.get("match")
        pattern = rule.get("pattern")
        candidate = community_id if match == "id" else community_name
        if match == "label" and isinstance(pattern, str) and isinstance(candidate, str):
            if fnmatch.fnmatchcase(candidate, pattern):  # case-sensitive (D-11)
                return _load_override_template(rule["template"], vault_dir, default_template)
        elif match == "id" and isinstance(pattern, int) and not isinstance(pattern, bool):
            if pattern == candidate:
                return _load_override_template(rule["template"], vault_dir, default_template)
    return default_template
```

Where `_load_override_template`:
1. Calls `validate_vault_path(rule["template"], vault_dir)` → raises ValueError on escape → fall back.
2. Reads the file; on OSError → fall back.
3. Calls `validate_template(text, _REQUIRED_PER_TYPE["moc"])`; on errors → log to stderr (matching D-22 pattern at templates.py:248-252) → fall back.
4. Returns `string.Template(text)`.

`fnmatch.fnmatchcase` (case-sensitive) is the correct choice — the unix-`fnmatch` familiar to users from `.gitignore`/`.graphifyignore`. Plain `fnmatch.fnmatch` does case-folding on POSIX which would surprise Windows users; `fnmatchcase` is portable.

### MOC-only scope enforcement (D-12)

The hook is **only** in `_render_moc_like`. Per-node `render_note()` (templates.py:691-698) is untouched. Members of the community continue to receive their `thing.md` / `statement.md` / etc. templates from `load_templates()`. This is enforced structurally, not by config — there is nowhere else to call `_pick_community_template`.

## --validate-profile Output Extension

### Current dispatch (`graphify/__main__.py:1265-1290`)

Calls `validate_profile_preflight(Path(sys.argv[2]))` → prints `error:`/`warning:` lines → exits 1 if errors → otherwise prints `profile ok — N rules, M templates validated`. Plain text, stderr for errors/warnings, stdout for success.

### Phase 30 extensions (D-14)

Three NEW sections, printed to **stdout** (informational, not error/warning), always — even on a single-file profile with no extends/includes:

```
profile ok — 3 rules, 2 templates validated

Merge chain (root ancestor first):
  bases/core.yaml
  bases/fusion.yaml
  profile.yaml

Field provenance (15 leaf fields):
  folder_mapping.thing                   ← bases/core.yaml
  folder_mapping.statement               ← bases/core.yaml
  naming.convention                      ← bases/fusion.yaml
  merge.preserve_fields                  ← profile.yaml
  community_templates                    ← profile.yaml
  ...

Resolved community templates (2 rules):
  [1] match=label  pattern="transformer*"     template=templates/transformer-moc.md
  [2] match=id     pattern=0                  template=templates/big-community-moc.md
  (note: actual community-to-template assignments require a graph — run after `graphify`)
```

Single-file profile (no extends/includes, no community_templates):
```
Merge chain (root ancestor first):
  profile.yaml

Field provenance (8 leaf fields):
  folder_mapping.thing                   ← profile.yaml
  ...

Resolved community templates: (none)
```

### Output emission

Extend `__main__.py` dispatch to iterate `result.chain`, `result.provenance`, `result.community_template_rules`. The preflight function is the single source of resolver output — `__main__.py` does pure formatting.

Visual style match: keep the em-dash (`—`) used in the existing success line; use `←` (U+2190) for provenance arrows since it's already in CONTEXT.md examples; arrows in the chain use `→` already used in cycle error messages.

### Exit code contract

Unchanged: errors non-empty → exit 1; otherwise exit 0. New sections print on stdout regardless (informational).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.10 + 3.12 on CI) |
| Config file | `pyproject.toml` (no separate pytest.ini) — `pytest tests/ -q` is the canonical command |
| Quick run command | `pytest tests/test_profile_composition.py -x` (new file) |
| Full suite command | `pytest tests/ -q` |

New test file recommended: `tests/test_profile_composition.py` to keep Phase 30 tests grouped and avoid bloating the 1389-line `test_profile.py`. Mirrors the file-per-feature pattern (test_extract.py, test_validate.py, etc.). Existing `test_profile.py` keeps untouched preflight tests.

### Phase Requirements → Test Map

Grouped by success criterion (SC1-SC4) and decision (D-NN). Aim: 28 test cases.

#### Success Criterion 1 — extends/includes resolves to single composed profile, cycles detected (CFG-02)

| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| CFG-02 (D-01) | `extends:` single-parent string composes correctly | unit | `pytest tests/test_profile_composition.py::test_extends_single_parent -x` | ❌ Wave 0 |
| CFG-02 (D-01) | `includes:` ordered list composes correctly, last wins on conflict | unit | `pytest tests/test_profile_composition.py::test_includes_ordered_last_wins -x` | ❌ Wave 0 |
| CFG-02 (D-02) | extends + includes + own fields merge in documented order (parent → includes → own) | unit | `pytest tests/test_profile_composition.py::test_merge_order_extends_then_includes_then_own -x` | ❌ Wave 0 |
| CFG-02 (D-03) | `extends:` as a list raises validation error (string-only) | unit | `pytest tests/test_profile_composition.py::test_extends_as_list_rejected -x` | ❌ Wave 0 |
| CFG-02 (D-04) | direct cycle `a extends a` reports "cycle detected: a → a" | unit | `pytest tests/test_profile_composition.py::test_cycle_self_reference -x` | ❌ Wave 0 |
| CFG-02 (D-04) | indirect cycle `a → b → c → a` reports full chain | unit | `pytest tests/test_profile_composition.py::test_cycle_indirect_chain -x` | ❌ Wave 0 |
| CFG-02 (D-04) | cycle from `--validate-profile` exits non-zero | integration | `pytest tests/test_profile_composition.py::test_cycle_validate_profile_exit_code -x` | ❌ Wave 0 |
| CFG-02 (D-04) | cycle from `load_profile()` falls back to `_DEFAULT_PROFILE` (graceful) | unit | `pytest tests/test_profile_composition.py::test_cycle_load_profile_falls_back -x` | ❌ Wave 0 |
| CFG-02 (D-05) | depth-9 chain raises "recursion depth exceeded 8 levels" error | unit | `pytest tests/test_profile_composition.py::test_depth_cap_8 -x` | ❌ Wave 0 |
| CFG-02 (D-05) | depth-8 chain composes successfully (boundary) | unit | `pytest tests/test_profile_composition.py::test_depth_cap_8_boundary -x` | ❌ Wave 0 |
| CFG-02 (D-08) | partial fragment without `folder_mapping` is acceptable; only composed profile validates | unit | `pytest tests/test_profile_composition.py::test_partial_fragment_allowed -x` | ❌ Wave 0 |
| CFG-02 (diamond) | `A extends B; A includes C; C extends B` is NOT flagged as cycle | unit | `pytest tests/test_profile_composition.py::test_diamond_inheritance_not_cycle -x` | ❌ Wave 0 |

#### Success Criterion 2 — community_templates first-match-wins (CFG-03)

| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| CFG-03 (D-09) | `community_templates` accepted as top-level key | unit | `pytest tests/test_profile_composition.py::test_community_templates_top_level_key -x` | ❌ Wave 0 |
| CFG-03 (D-10) | rule missing `match` rejected | unit | `pytest tests/test_profile_composition.py::test_community_template_rule_requires_match -x` | ❌ Wave 0 |
| CFG-03 (D-10) | `match=label` with int `pattern` rejected | unit | `pytest tests/test_profile_composition.py::test_community_template_label_pattern_must_be_str -x` | ❌ Wave 0 |
| CFG-03 (D-10) | `match=id` with str `pattern` rejected | unit | `pytest tests/test_profile_composition.py::test_community_template_id_pattern_must_be_int -x` | ❌ Wave 0 |
| CFG-03 (D-11) | `pattern="transformer*"` matches community label "Transformer Stack" via fnmatch | unit | `pytest tests/test_profile_composition.py::test_fnmatch_label_glob_match -x` | ❌ Wave 0 |
| CFG-03 (D-11) | `pattern="auth-?"` does not match "auth-stack" (single char wildcard) | unit | `pytest tests/test_profile_composition.py::test_fnmatch_question_mark_no_match -x` | ❌ Wave 0 |
| CFG-03 (D-11) | match is case-sensitive (`Transformer*` does not match `transformer-stack`) | unit | `pytest tests/test_profile_composition.py::test_fnmatch_case_sensitive -x` | ❌ Wave 0 |
| CFG-03 (D-12) | per-community override applies to MOC note only; member nodes use type templates | unit | `pytest tests/test_profile_composition.py::test_override_scope_moc_only -x` | ❌ Wave 0 |
| CFG-03 (D-13) | when two rules match, first one wins | unit | `pytest tests/test_profile_composition.py::test_first_match_wins -x` | ❌ Wave 0 |
| CFG-03 (fallback) | no rule matches → falls back to default community/moc template | unit | `pytest tests/test_profile_composition.py::test_no_match_falls_back_to_default -x` | ❌ Wave 0 |
| CFG-03 (path) | template path escaping `.graphify/` rejected → fallback | unit | `pytest tests/test_profile_composition.py::test_override_template_path_escape_rejected -x` | ❌ Wave 0 |
| CFG-03 (missing) | template file missing → stderr warning + fallback | unit | `pytest tests/test_profile_composition.py::test_override_template_missing_file_falls_back -x` | ❌ Wave 0 |
| CFG-03 (invalid) | template missing required placeholder → fallback | unit | `pytest tests/test_profile_composition.py::test_override_template_invalid_falls_back -x` | ❌ Wave 0 |

#### Success Criterion 3 — `--validate-profile` reports merge chain + community-template assignments (CFG-02 + CFG-03)

| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| CFG-02 (D-14) | output contains "Merge chain" section listing files in resolution order | integration | `pytest tests/test_profile_composition.py::test_validate_profile_prints_merge_chain -x` | ❌ Wave 0 |
| CFG-02 (D-14) | output contains "Field provenance" with correct per-key source files | integration | `pytest tests/test_profile_composition.py::test_validate_profile_prints_provenance -x` | ❌ Wave 0 |
| CFG-03 (D-14) | output contains "Resolved community templates" listing the rule list | integration | `pytest tests/test_profile_composition.py::test_validate_profile_prints_community_template_rules -x` | ❌ Wave 0 |
| CFG-02 (D-16) | output is plain text (no JSON, no tree characters); single-file profile shows `chain: [profile.yaml]` only | integration | `pytest tests/test_profile_composition.py::test_validate_profile_single_file_output_shape -x` | ❌ Wave 0 |
| CFG-03 (D-17) | community-template section dumps rules as written (graph-blind) | integration | `pytest tests/test_profile_composition.py::test_validate_profile_graph_blind -x` | ❌ Wave 0 |

#### Success Criterion 4 — removing `extends:` shows lost fields via provenance (CFG-02)

| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| CFG-02 (D-15) | provenance table changes when `extends:` is removed: fields previously sourced from parent vanish from the table | integration | `pytest tests/test_profile_composition.py::test_lost_fields_visible_after_extends_removal -x` | ❌ Wave 0 |

#### Path Security & Edge Cases

| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| CFG-02 (D-07) | absolute path in `extends:` rejected | unit | `pytest tests/test_profile_composition.py::test_absolute_extends_path_rejected -x` | ❌ Wave 0 |
| CFG-02 (D-07) | `../../etc/passwd` escape rejected | unit | `pytest tests/test_profile_composition.py::test_extends_traversal_rejected -x` | ❌ Wave 0 |
| CFG-02 (D-07) | symlink pointing outside `.graphify/` rejected | unit | `pytest tests/test_profile_composition.py::test_extends_symlink_escape_rejected -x` | ❌ Wave 0 |
| CFG-02 (D-06) | sibling-relative resolution: `extends: ../bases/core.yaml` resolves correctly when staying in `.graphify/` | unit | `pytest tests/test_profile_composition.py::test_sibling_relative_path_resolution -x` | ❌ Wave 0 |
| CFG-02 (D-04) | YAML parse error in fragment surfaces as named error | unit | `pytest tests/test_profile_composition.py::test_malformed_yaml_in_fragment -x` | ❌ Wave 0 |
| CFG-02 (combined) | profile with BOTH extends AND includes resolves all three layers | unit | `pytest tests/test_profile_composition.py::test_extends_and_includes_combined -x` | ❌ Wave 0 |

**Total: ~33 test cases.**

### Sampling Rate

- **Per task commit:** `pytest tests/test_profile_composition.py -x` (~33 tests, < 5s)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_profile_composition.py` — new test file covering CFG-02 + CFG-03
- [ ] `tests/fixtures/profiles/` — fixture directory (see §Test Fixture Layout below)
- [ ] No framework install needed — pytest already in the test toolchain

## Test Fixture Layout

Recommended convention under `tests/fixtures/profiles/`:

```
tests/fixtures/profiles/
├── single_file/
│   └── .graphify/
│       └── profile.yaml                  # no extends/includes
├── linear_chain/
│   └── .graphify/
│       ├── profile.yaml                   # extends: bases/fusion.yaml
│       └── bases/
│           ├── fusion.yaml                # extends: core.yaml
│           └── core.yaml                  # leaf
├── includes_only/
│   └── .graphify/
│       ├── profile.yaml                   # includes: [mixins/team.yaml, mixins/tags.yaml]
│       └── mixins/
│           ├── team.yaml
│           └── tags.yaml
├── extends_and_includes/
│   └── .graphify/
│       ├── profile.yaml                   # extends + includes + own fields
│       ├── bases/fusion.yaml
│       └── mixins/team-tags.yaml
├── cycle_self/
│   └── .graphify/
│       └── profile.yaml                   # extends: profile.yaml (self)
├── cycle_indirect/
│   └── .graphify/
│       ├── a.yaml                          # extends: b.yaml
│       ├── b.yaml                          # extends: c.yaml
│       └── c.yaml                          # extends: a.yaml
├── diamond/
│   └── .graphify/
│       ├── profile.yaml                   # extends: fusion.yaml, includes: [c.yaml]
│       ├── fusion.yaml                    # extends: core.yaml
│       ├── c.yaml                         # extends: core.yaml
│       └── core.yaml                      # leaf
├── depth_8/                                # 8-level chain (boundary success)
│   └── .graphify/
│       └── lvl{0..8}.yaml
├── depth_9/                                # 9-level chain (boundary failure)
│   └── .graphify/
│       └── lvl{0..9}.yaml
├── path_escape/
│   └── .graphify/
│       └── profile.yaml                   # extends: ../../etc/passwd
├── absolute_path/
│   └── .graphify/
│       └── profile.yaml                   # extends: /tmp/evil.yaml
├── community_templates/
│   └── .graphify/
│       ├── profile.yaml                   # community_templates: [...] rules
│       └── templates/
│           ├── transformer-moc.md         # valid override
│           └── invalid-moc.md             # missing required placeholder
└── partial_fragment/
    └── .graphify/
        ├── profile.yaml                   # extends: bases/partial.yaml
        └── bases/
            └── partial.yaml               # missing folder_mapping (partial)
```

**Programmatic alternative for depth tests:** generating `lvl0.yaml..lvl9.yaml` programmatically inside `tmp_path` is cleaner than committing 9 nearly-identical files. Recommended: write a small helper `_make_chain(tmp_path, depth)` in the test module rather than fixture files for depth tests.

**Symlink test:** symlinks must be created at runtime in `tmp_path` (cannot live in git). Use `Path.symlink_to()` inside the test function.

## Risks & Landmines

### R1 — Backward compatibility (HIGH stakes, LOW risk if disciplined)
- All 60+ existing `test_profile.py` tests load profiles WITHOUT `extends`/`includes`/`community_templates`. The resolver MUST treat `entry_path` as a chain of length 1 (own fields only) when no fragments are referenced.
- `_DEFAULT_PROFILE` does NOT contain new keys. Verified via lines 36-102 — adding them would force every existing profile to declare them. Keep defaults clean.
- `PreflightResult` extension: add new fields **at the end** of the NamedTuple. Existing `errors, warnings, *_ = result` patterns continue to unpack. Verified via docstring lines 14-20.

### R2 — Resolver/preflight divergence (the success-criterion-4 trap)
If `load_profile()` and `validate_profile_preflight()` use different resolvers, a user could see "field X provenance: parent.yaml" in `--validate-profile` but get a different value at runtime. The single-source-of-truth resolver is non-negotiable per Claude's-discretion guidance in CONTEXT.md.

### R3 — `_deep_merge` does NOT mutate base (verified, line 158)
Provenance variant must preserve this contract. Tests at `test_profile.py:46 test_deep_merge_does_not_mutate_base` assert it. New variant must ditto — copy on entry.

### R4 — Empty / None YAML files
`load_profile()` line 194 already guards `or {}`. New resolver must do the same in `_load_one`. Empty fragment = empty dict, valid (combines with `extends:` chain above it).

### R5 — Python's bool-is-int subclass for `match=id` patterns
`isinstance(True, int)` is True. The community-template-pattern validator must reject bool values when expecting int (mirror existing pattern at profile.py:319 and 337). Test must include `pattern: true` rejection case.

### R6 — `fnmatch.fnmatch` vs `fnmatchcase`
`fnmatch.fnmatch` does case-folding on POSIX platforms only — its behaviour differs between macOS/Linux and Windows, which would silently break cross-platform fixtures. Use `fnmatchcase` for portable case-sensitive matching. CI runs on Linux only, but real users run on Windows.

### R7 — Provenance dotted-key collision with list types
`mapping_rules` is a list. Provenance records `mapping_rules ← profile.yaml` (one entry, no per-element keys). This matches `_deep_merge`'s replace-on-non-dict behaviour. Document in test fixture: removing extends drops the entire list, not individual entries.

### R8 — Cycle detection vs diamond inheritance
A naïve global `visited: set` flags `A extends B; A includes C; C extends B` as cycle on the second visit to B. Use stack-local `currently_descending: set[Path]` (added on entry, removed on return). Test case: `test_diamond_inheritance_not_cycle`.

### R9 — Symlinks and `Path.resolve()`
`resolve()` follows symlinks; `is_relative_to((vault_dir/".graphify").resolve())` after resolve is the security check. Test must explicitly create a symlink to outside the fixture vault and assert rejection. Skip on Windows if symlink privileges are missing (`pytest.mark.skipif`).

### R10 — Test isolation under `tmp_path`
All fixtures must be copied or constructed inside `tmp_path`, not referenced from `tests/fixtures/` directly, because the resolver writes nothing but the path-confinement check uses `Path.resolve()` which is sensitive to the vault location. Use `shutil.copytree(fixture_src, tmp_path / "vault")` per test.

## Implementation Surface Estimate

| File | Type of change | Approx LOC |
|------|----------------|-----------|
| `graphify/profile.py` | Add `_resolve_profile_chain`, `_deep_merge_with_provenance`, extend `_VALID_TOP_LEVEL_KEYS`, add `community_templates` validator block, refactor `load_profile`, extend `PreflightResult` + `validate_profile_preflight` to populate new fields | +180 / -10 (refactor of `load_profile` lines 171-202) |
| `graphify/templates.py` | Add `_pick_community_template` helper + `_load_override_template` + 1-line dispatch change in `_render_moc_like` | +50 |
| `graphify/__main__.py` | Extend `--validate-profile` dispatch (lines 1265-1290) to print 3 new sections | +30 |
| `graphify/security.py` | No changes — `validate_vault_path` is already in `profile.py`; security.py provides no path helper for `.graphify/`-confined check (we use stdlib `is_relative_to`) | 0 |
| `tests/test_profile_composition.py` | NEW file, ~33 test cases | +650 |
| `tests/fixtures/profiles/` | NEW directory, ~14 fixture vaults | YAML/MD only |
| **Total Python LOC** | | **+910 / -10** |

**Plan sizing:** ~3 plans (resolver+schema, runtime dispatch, CLI output) is the natural decomposition. Each plan ~300 LOC including tests; well within standard plan size.

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**: must use `Path.is_relative_to()` (3.9+) — safe.
- **No new required dependencies**: PyYAML stays optional under `[obsidian]/[all]`. `fnmatch` is stdlib. No new deps.
- **No Jinja2**: not relevant — we use `string.Template` already; community-template overrides plug into the same machinery.
- **Pure unit tests, no network, `tmp_path` only**: all fixtures copied to `tmp_path` per test.
- **Path confinement via `security.py` patterns**: reuse `validate_vault_path` (already in profile.py); use stdlib `Path.is_relative_to` for `.graphify/`-tighter checks.
- **No linter/formatter**: 4-space indent, type hints on all functions, `from __future__ import annotations` first import.
- **Errors-as-list-of-strings**: `validate_profile()` accumulates errors; resolver does the same; never raise on validation problems.
- **Graceful fallback in `load_profile()`**: composition errors → stderr + return `_deep_merge(_DEFAULT_PROFILE, {})`. Never crash on bad vault profile.
- **Function-local imports for circular deps**: profile.py already does this for `graphify.mapping` (line 356); apply same pattern if templates.py needs to import from profile.py.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fnmatch.fnmatchcase` is the right portable case-sensitive matcher (vs `fnmatch.fnmatch`) | Community Template Matching | LOW — D-11 says "fnmatch-style globs"; could swap for `fnmatch.fnmatch` if user prefers POSIX case-folding behaviour. |
| A2 | New `_resolve_profile_chain` should NOT pre-merge `_DEFAULT_PROFILE` (defaults-merge stays in `load_profile`) | Resolver Design | LOW — alternative is to merge defaults in resolver; provenance would then include default-source which isn't useful for "lost fields" UX. |
| A3 | Fragment `extends:`/`includes:` must include `.yaml` extension explicitly (no auto-suffix) | Path Resolution & Security | LOW — could relax later if real fixture pain emerges. |
| A4 | List-typed leaves (mapping_rules, community_templates) record provenance at list level, not per-entry | Resolver Design | LOW — matches `_deep_merge` replace semantics; consistent with how the merge already behaves. |
| A5 | New tests live in `tests/test_profile_composition.py` (separate from `test_profile.py`) | Test Fixture Layout | NONE — file split is ergonomic, not contractual. |

## Open Questions

None blocking. Three `[ASSUMED]` items above are tagged for the planner's awareness; all are reversible implementation details, not architectural commitments.

## Sources

### Primary (HIGH confidence)
- `graphify/profile.py` lines 1-822 (read in full) — current API surface verified.
- `graphify/templates.py` lines 200-260, 600-870 (read in full) — render hot paths verified.
- `graphify/__main__.py` lines 1265-1290 (read in full) — `--validate-profile` dispatch verified.
- `graphify/security.py` lines 1-207 (read in full) — `validate_vault_path` lives in profile.py, not security.py; corrected.
- `graphify/export.py` lines 540-700 (read in full) — MOC render call site verified.
- `tests/test_profile.py` test list (60+ tests grepped) — back-compat surface verified.
- `.planning/phases/30-profile-composition/30-CONTEXT.md` — locked decisions D-01 through D-17.
- `.planning/REQUIREMENTS.md` — CFG-02, CFG-03 definitions.
- `.planning/ROADMAP.md` lines 209-218 — Phase 30 success criteria.
- `.planning/config.json` — `nyquist_validation: true` confirmed.
- `CLAUDE.md` — project constraints.

### Secondary (MEDIUM confidence)
- Python `fnmatch` stdlib behaviour (training knowledge of `fnmatch.fnmatchcase` vs `fnmatch.fnmatch`).
- `Path.is_relative_to()` availability in Python 3.9+ (training knowledge; verified by CLAUDE.md's 3.10+ floor).

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Existing profile system surface: HIGH — entire `profile.py` read.
- Resolver algorithm: HIGH — direct application of well-known DAG-resolution pattern (ESLint/TS-config precedent).
- Path resolution: HIGH — `Path.resolve()` + `is_relative_to()` is the canonical Python pattern.
- Community-template matching: HIGH — `fnmatch.fnmatchcase` is documented stdlib behaviour; render-site dispatch verified by reading templates.py.
- Output extension: HIGH — `__main__.py` and `validate_profile_preflight` read in full.
- Test architecture: HIGH — `test_profile.py` patterns mirrored.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable internal codebase, no fast-moving externals)

## RESEARCH COMPLETE
