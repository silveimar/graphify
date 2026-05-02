# Phase 56: Dataview templates & profile overrides - Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 8 (3 source, 3 test, 2 docs)
**Analogs found:** 7 / 8 (docs/TEMPLATES.md is forward-pointer only — no analog needed)

> Phase 56 is overwhelmingly a "port and parameterize" exercise. Every new validator and every new resolver has a near-byte-for-byte analog already in the codebase. This file pins each new addition to its analog with concrete excerpts so the planner can write actions like "port lines X-Y from `<analog>` to `<new>` swapping `<thing>`".

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/profile.py` (modify — new validators + collision detectors + provenance shape) | config / schema validator | request-response (validation pipeline) | `graphify/profile.py:682-735` (community_templates: validator) | exact (self-analog) |
| `graphify/mapping.py` (modify — optional `id:` field) | config / schema validator | request-response | `graphify/mapping.py:910-913` (then.folder optional-field check) + `graphify/naming.py:34,53-64` (slug pattern) | exact |
| `graphify/templates.py` (modify — `_resolve_note_template` + extend `_load_override_template`) | service / runtime resolver | request-response | `graphify/templates.py:1521-1568` (`_load_override_template`) + `graphify/templates.py:1572-1610` (`_pick_community_template`) | exact (self-analog) |
| `tests/test_profile.py` (modify — add validator + collision tests) | test (unit) | CRUD on dict fixtures | `tests/test_profile.py:1612-1740` (existing `dataview_queries:` validator tests) | exact |
| `tests/test_mapping.py` (modify — `id:` field tests) | test (unit) | CRUD on dict fixtures | `tests/test_mapping.py` (existing `validate_rules` tests) | exact |
| `tests/test_template_overrides.py` (NEW — collision matrix + ladder) | test (unit + integration) | request-response (render) | `tests/test_profile_composition.py:385-590` (community_templates: render-time tests) | exact |
| `docs/PROFILE-CONFIGURATION.md` (modify — major update) | documentation | static | existing `community_templates:` and `dataview_queries:` sections in same doc | exact |
| `docs/TEMPLATES.md` (modify — one-paragraph forward-pointer) | documentation | static | n/a — pure forward link | no analog needed |

## Pattern Assignments

### `graphify/profile.py` — `mapping_rule_templates:` validator (NEW block in `validate_profile`, after line 735)

**Analog:** `graphify/profile.py:682-735` (`community_templates:` validator) — port byte-for-byte, swap allowlists.

**Canonical excerpt to mirror** (`profile.py:682-735`):
```python
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
                errors.append(...)
            elif match == "id" and (isinstance(pattern, bool) or not isinstance(pattern, int)):
                errors.append(...)
            template = rule.get("template")
            if not isinstance(template, str) or not template:
                errors.append(f"{prefix}.template must be a non-empty string")
            elif ".." in template:
                errors.append(f"{prefix}.template contains '..' — fragment paths must stay inside .graphify/")
            elif Path(template).is_absolute():
                errors.append(f"{prefix}.template is an absolute path — must be relative to .graphify/")
            elif template.startswith("~"):
                errors.append(f"{prefix}.template starts with '~' — must be relative to .graphify/")
            extra = set(rule) - {"match", "pattern", "template"}
            if extra:
                errors.append(f"{prefix}: unknown keys {sorted(extra)} — only 'match', 'pattern', 'template' are supported")
```

**Phase 56 swaps for `mapping_rule_templates:`:**
- Variable name: `ct` → `mrt`
- Top-level key: `"community_templates"` → `"mapping_rule_templates"`
- Prefix string: `"community_templates[{idx}]"` → `"mapping_rule_templates[{idx}]"`
- `match` allowlist: `{"label", "id"}` → `{"rule_id"}` (single value in v1.11)
- `pattern` type rule: must be `str` matching slug regex `^[a-z][a-z0-9_-]*$` (mirrors mapping_rules.id slug — D-56.04). Drop the `match == "id"` int-pattern branch entirely.
- Path-confinement (`..`, absolute, `~`) and unknown-keys: **port verbatim including error wording** (per D-56.13).

**Phase 56 swaps for `note_type_templates:`:**
- Variable name: `ct` → `ntt`
- Top-level key → `"note_type_templates"`
- Prefix → `"note_type_templates[{idx}]"`
- `match` allowlist → `{"note_type"}` (single value)
- `pattern` type rule: must be `str` AND in `_KNOWN_NOTE_TYPES` (mirrors `dataview_queries:` validator at `profile.py:752-758`)
- Same path-confinement + unknown-keys block.

**CRITICAL — path-confinement style** (per RESEARCH.md Pitfall §"Path-confinement port"):
- Use **substring** check `".." in template` (NOT `Path.parts`-based check from `_taxonomy_path_errors` at `profile.py:277-296`).
- Order matters: `..` → absolute → `~`. First match per rule wins (`elif` chain).
- Error wording uses `.graphify/` with trailing slash. Mirror exactly.

---

### `graphify/profile.py` — `dataview_queries:` validator extension (modify `profile.py:737-763`)

**Analog (existing implementation to extend):** `graphify/profile.py:737-763`:
```python
dvq = profile.get("dataview_queries")
if dvq is not None:
    if not isinstance(dvq, dict):
        errors.append(f"dataview_queries must be a dict, got {type(dvq).__name__}")
    else:
        for key, value in dvq.items():
            if not isinstance(key, str): ...
            if key not in _KNOWN_NOTE_TYPES: ...
            if not isinstance(value, str) or not value.strip():
                errors.append(f"dataview_queries.{key}: query must be a non-empty string")
```

**Phase 56 four dead-rule additions inside the per-key loop (D-56.02):**

**§1 — Unknown `${var}` references.** Allowlist is **exactly** `{"community_tag", "folder"}` (per RESEARCH.md "Allowlist" section, exhaustive enumeration of `_build_dataview_block` callsites at `templates.py:1290-1293`, `1439-1444`, `1707-1710`). NOT `note_type`, NOT `vault_root` — those are speculative.

```python
import string  # already imported in profile.py
_DATAVIEW_QUERY_VARS = frozenset({"community_tag", "folder"})

# Inside the per-key loop, after the empty-string check:
for match in string.Template.pattern.finditer(value):
    name = match.group("named") or match.group("braced")
    if name and name not in _DATAVIEW_QUERY_VARS:
        errors.append(
            f"dataview_queries.{key}: unknown ${{{name}}} — "
            f"valid vars are: {sorted(_DATAVIEW_QUERY_VARS)}"
        )
```

**§2 — Unreachable note_type.** Reject `dataview_queries.<note_type>` only when fully provable (be conservative — see RESEARCH.md Pitfall 4):
```python
def _reachable_note_types(profile: dict) -> set[str]:
    # mapping.py:397-406 built-in topology fallback path
    reachable = {"moc", "community", "thing", "statement", "code"}
    for rule in profile.get("mapping_rules") or []:
        if not isinstance(rule, dict):
            continue
        then = rule.get("then")
        if isinstance(then, dict) and isinstance(then.get("note_type"), str):
            reachable.add(then["note_type"])
    return reachable
# Only `person` and `source` are ever potentially unreachable.
```

**§3 — Empty after substitution.** Extend the existing `not value.strip()` check:
- (a) reject pure whitespace once stripped (already covered by `.strip()` — verify wording).
- (b) reject queries that render empty when every `${var}` expands to empty (`string.Template(value).safe_substitute(community_tag="", folder="")` then `.strip()`).

**§4 — Cross-chain duplicate `dataview_queries.<note_type>`.** This is the cross-cutting collision class — implementation is in the new collision detector, not in `validate_profile`. See "Cross-Cutting Patterns" below.

---

### `graphify/profile.py` — `_VALID_TOP_LEVEL_KEYS` extension (modify `profile.py:172-179`)

**Analog (existing):**
```python
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output", "taxonomy", "repo", "corpus",
    "extends", "includes", "community_templates",  # Phase 30 (CFG-02 / CFG-03)
    "dataview_queries",  # Phase 31 (TMPL-03, D-11)
    "predicate_flags",  # Phase 55 (TMPL-01, D-55.08)
}
```

**Phase 56 addition (mirror Phase 31/55 comment style):**
```python
"mapping_rule_templates",  # Phase 56 (CFG-01, D-56.03)
"note_type_templates",     # Phase 56 (CFG-01, D-56.03)
```

---

### `graphify/profile.py` — provenance shape extension (modify lines 35, 56, 247-274)

**Analog (current implementation):** `profile.py:247-274`:
```python
def _deep_merge_with_provenance(
    base: dict,
    override: dict,
    source_path: Path,
    provenance: dict[str, Path],     # ← shape change here
    _prefix: str = "",
) -> dict:
    result = base.copy()
    for key, value in override.items():
        dotted = f"{_prefix}{key}" if _prefix else key
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_with_provenance(
                result[key], value, source_path, provenance, _prefix=f"{dotted}."
            )
        else:
            result[key] = value
            provenance[dotted] = source_path     # ← write change here
    return result
```

**Phase 56 changes (verbatim diff):**
1. Type alias at `profile.py:35` (PreflightResult.provenance): `dict[str, Path]` → `dict[str, list[Path]]`
2. Type alias at `profile.py:56` (ResolvedProfile.provenance): `dict[str, Path]` → `dict[str, list[Path]]`
3. Function signature at `profile.py:250`: `provenance: dict[str, Path]` → `provenance: dict[str, list[Path]]`
4. Leaf write at `profile.py:274`: `provenance[dotted] = source_path` → `provenance.setdefault(dotted, []).append(source_path)`
5. Audit existing readers at `profile.py:1481, 1503` (`validate_profile_preflight`) and `report_validate_profile_text` for `dict[str, Path]` assumptions; update to handle list shape (typically: take last element via `[-1]` for "current writer" semantics).

**Test that must be amended:** `tests/test_profile.py:1711+` (`test_dataview_queries_provenance_in_validate_profile_output`) — currently asserts scalar shape.

**Merge order** (`profile.py:464-491`, no change): extends-parents → includes → own. Lists naturally end up in this order, which conveniently matches D-56.05 priority.

---

### `graphify/profile.py` — Four collision detectors (NEW, called from `validate_profile_preflight`)

**Analog:** No exact prior analog — these are new schema-only detectors. Pattern mirrors the **append-to-errors-list** style of every existing validator. Place them as module-level helpers `_detect_*_collisions(profile_or_provenance) -> list[str]`.

**§1 — Duplicate id in `mapping_rule_templates`** (two entries with same `pattern` value targeting same rule_id):
```python
def _detect_mapping_rule_template_collisions(profile: dict) -> list[str]:
    errors: list[str] = []
    rules = profile.get("mapping_rule_templates") or []
    seen: dict[str, int] = {}
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        pattern = rule.get("pattern")
        if not isinstance(pattern, str):
            continue
        if pattern in seen:
            errors.append(
                f"mapping_rule_templates[{idx}]: duplicate pattern {pattern!r} — "
                f"also defined at mapping_rule_templates[{seen[pattern]}]"
            )
        else:
            seen[pattern] = idx
    return errors
```

**§2 — Duplicate exact pattern within same list** — same shape, applied to `community_templates` and `note_type_templates`. (NB: extends Phase 30 `community_templates:` validator — currently no duplicate-pattern check exists there; this is additive.)

**§3 — Duplicate note_type in `note_type_templates`** — same shape with `pattern` keyed against `_KNOWN_NOTE_TYPES`.

**§4 — Cross-chain `dataview_queries.<note_type>` duplicate** (consumes the new list-shape provenance):
```python
def _detect_dataview_collisions(provenance: dict[str, list[Path]]) -> list[str]:
    errors: list[str] = []
    for dotted, sources in provenance.items():
        if not dotted.startswith("dataview_queries."):
            continue
        if len(sources) > 1:
            note_type = dotted.split(".", 1)[1]
            paths = ", ".join(str(p) for p in sources)
            errors.append(
                f"dataview_queries.{note_type}: collision across composition chain — "
                f"defined in: {paths}"
            )
    return errors
```

**Wiring point:** `validate_profile_preflight` (`profile.py:1426+`) — append all four to its aggregated errors list after Layer 1 schema validation completes. Per Open Question 2 in RESEARCH.md, surface as **errors** (not warnings) per D-56.06 wording.

---

### `graphify/mapping.py` — Optional `id:` field on mapping rules (modify `validate_rules` at lines 841-925)

**Analog (existing optional-field pattern in same function — `mapping.py:910-913`):**
```python
# --- then.folder (optional, path-safety) -----------------------
folder = then.get("folder")
if folder is not None:
    errors.extend(_validate_folder(folder, f"{prefix}.then.folder"))
```

**Slug constants analog (`naming.py:34, 53-64`):**
```python
_REPO_IDENTITY_MAX_LEN = 80

def normalize_repo_identity(value: str) -> str:
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError(...)
    raw = value.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
```

**Phase 56 addition (suggested injection between line 871 and the matcher logic at line 873):**
```python
# Module-level constants (top of mapping.py, near _MAX_PATTERN_LEN at line 26):
_RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_RULE_ID_MAX_LEN = 80  # mirror naming._REPO_IDENTITY_MAX_LEN

# Inside validate_rules per-rule loop, before matcher dispatch:
rule_id = rule.get("id")
if rule_id is not None:
    if not isinstance(rule_id, str):
        errors.append(f"{prefix}.id: must be a string (got {type(rule_id).__name__})")
    elif len(rule_id) > _RULE_ID_MAX_LEN:
        errors.append(f"{prefix}.id: length {len(rule_id)} exceeds cap {_RULE_ID_MAX_LEN}")
    elif not _RULE_ID_PATTERN.fullmatch(rule_id):
        errors.append(
            f"{prefix}.id: must match pattern '^[a-z][a-z0-9_-]*$' (got {rule_id!r})"
        )
```

**Uniqueness pass (single post-loop iteration, before line 924's `_detect_dead_rules` call):**
```python
seen_ids: dict[str, int] = {}
for idx, rule in enumerate(rules):
    if not isinstance(rule, dict):
        continue
    rid = rule.get("id")
    if isinstance(rid, str) and rid in seen_ids:
        errors.append(
            f"mapping_rules[{idx}].id: duplicate id {rid!r} — also defined at "
            f"mapping_rules[{seen_ids[rid]}]"
        )
    elif isinstance(rid, str):
        seen_ids[rid] = idx
```

**NOTE:** RESEARCH.md observed there is currently **no top-level unknown-keys check** in `validate_rules` (only `then:` has one at lines 916-921). Phase 56 may add a top-level rejection for keys outside `{"when", "then", "id"}` — planner discretion (CONTEXT.md Claude's Discretion list does not mandate this).

---

### `graphify/mapping.py` — `ClassificationContext` extension for rule_id

**Analog:** `graphify/templates.py:109-126` (the actual definition — note RESEARCH.md was slightly wrong: it's a `TypedDict`, **not** a frozen dataclass).

**Existing definition** (`templates.py:109-126`):
```python
class ClassificationContext(TypedDict, total=False):
    note_type: str
    folder: str
    filename_stem: str
    filename_collision: bool
    ...
    community_name: str
```

**Phase 56 addition (one new optional field — `total=False` keeps it backward compatible):**
```python
class ClassificationContext(TypedDict, total=False):
    ...
    community_name: str
    rule_id: str  # Phase 56 (CFG-01, D-56.04) — populated by classify() when matched rule has id:
```

**Population point:** `mapping.py:408` (`per_node[node_id] = ClassificationContext(...)`). When the matched rule has an `id:` field, include `rule_id=rule["id"]` in the dict literal.

---

### `graphify/templates.py` — `_resolve_note_template` (NEW, refactor of `_pick_community_template`)

**Analog 1 — load helper to extend** (`templates.py:1521-1568`, `_load_override_template`):
```python
def _load_override_template(rel_path: str, vault_dir, default_template):
    from graphify.profile import validate_vault_path
    if vault_dir is None:
        return default_template
    try:
        graphify_dir = Path(vault_dir) / ".graphify"
        canonical = validate_vault_path(rel_path, graphify_dir)
    except (ValueError, OSError) as exc:
        print(
            f"[graphify] community_templates override path rejected ({rel_path}): {exc} — using default",
            file=sys.stderr,
        )
        return default_template
    if not canonical.exists():
        print(
            f"[graphify] community_templates override missing ({rel_path}) — using default",
            file=sys.stderr,
        )
        return default_template
    try:
        text = canonical.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"[graphify] community_templates override unreadable ({rel_path}): {exc} — using default",
            file=sys.stderr,
        )
        return default_template
    errors = validate_template(text, _REQUIRED_PER_TYPE["moc"])
    if errors:
        for err in errors:
            print(
                f"[graphify] community_templates override invalid ({rel_path}): {err} — using default",
                file=sys.stderr,
            )
        return default_template
    return _BlockTemplate(text)
```

**Phase 56 extension (per RESEARCH.md "anti-patterns: do not duplicate fall-back logic three times"):**
- Add a `list_name: str = "community_templates"` keyword argument so warn messages identify which list's override failed.
- Replace every hardcoded `"community_templates"` literal in stderr lines with `{list_name}`.
- Backward compatible (default keeps existing wording for community_templates calls).

**Analog 2 — picker to refactor** (`templates.py:1572-1610`, `_pick_community_template`):
```python
def _pick_community_template(community_id, community_name, profile, vault_dir, default_template):
    rules = profile.get("community_templates") or []
    if not isinstance(rules, list):
        return default_template
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = rule.get("match")
        pattern = rule.get("pattern")
        template_path = rule.get("template")
        if not isinstance(template_path, str) or not template_path:
            continue
        if match == "label":
            if not isinstance(pattern, str) or not isinstance(community_name, str):
                continue
            if fnmatch.fnmatchcase(community_name, pattern):
                return _load_override_template(template_path, vault_dir, default_template)
        elif match == "id":
            if isinstance(pattern, bool) or not isinstance(pattern, int):
                continue
            if pattern == community_id:
                return _load_override_template(template_path, vault_dir, default_template)
    return default_template
```

**Phase 56 single-resolver design** (per RESEARCH.md recommendation — eliminates duplicate fall-back logic):
```python
def _resolve_note_template(
    *,
    rule_id: str | None,
    community_id: int | None,
    community_name: str | None,
    note_type: str,
    profile: dict,
    vault_dir,
    default_template: "string.Template",
) -> "string.Template":
    """D-56.05 ladder: mapping_rule > community > note_type > base."""
    # 1. mapping_rule_templates (NEW)
    if rule_id is not None:
        for rule in profile.get("mapping_rule_templates") or []:
            if not isinstance(rule, dict):
                continue
            if rule.get("match") == "rule_id" and rule.get("pattern") == rule_id:
                return _load_override_template(
                    rule.get("template"), vault_dir, default_template,
                    list_name="mapping_rule_templates",
                )
    # 2. community_templates (existing — delegate to current picker)
    if community_id is not None and community_name is not None:
        result = _pick_community_template(
            community_id, community_name, profile, vault_dir, default_template,
        )
        if result is not default_template:
            return result
    # 3. note_type_templates (NEW)
    for rule in profile.get("note_type_templates") or []:
        if not isinstance(rule, dict):
            continue
        if rule.get("match") == "note_type" and rule.get("pattern") == note_type:
            return _load_override_template(
                rule.get("template"), vault_dir, default_template,
                list_name="note_type_templates",
            )
    # 4. base
    return default_template
```

**Insertion points** (call sites that must switch from direct lookup / `_pick_community_template` to `_resolve_note_template`):
- `templates.py:1487-1494` — inside `render_note`: currently `templates[note_type]` direct lookup. Wrap with `_resolve_note_template(rule_id=ctx.get("rule_id"), community_id=None, community_name=None, note_type=note_type, default_template=templates[note_type], ...)`.
- `templates.py:1748-1750` — inside `_render_moc_like`: currently `_pick_community_template(...)`. Replace with `_resolve_note_template(rule_id=None, community_id=community_id, community_name=community_name, note_type=template_key, ...)`.

---

### `tests/test_profile.py` — schema validator + collision tests (extend existing file)

**Analog:** `tests/test_profile.py:1612-1740` (existing `dataview_queries:` validator tests).

**Pattern observed:**
- One assertion per test function (existing style; `pytest.mark.parametrize` is not yet used in this file).
- Direct `validate_profile(dict)` calls — no fixture vault required for schema-only checks.
- Provenance test at `:1711+` uses `tmp_path` to construct a real extends/includes chain, then reads `provenance` directly.

**Phase 56 test layout per requirements table in RESEARCH.md §"Phase Requirements → Test Map":**
- `dataview_queries_unknown_var` — TMPL-03 §1
- `dataview_queries_unreachable_note_type` — TMPL-03 §2
- `dataview_queries_empty_after_substitution` — TMPL-03 §3
- `dataview_queries_collision_across_chain` — TMPL-03 §4 (also CFG-02 §4)
- `mapping_rule_templates_validates` — CFG-01a (positive + each rejection class)
- `note_type_templates_validates` — CFG-01b
- `collision_duplicate_rule_id` — CFG-02 §1
- `collision_duplicate_pattern` — CFG-02 §2
- `collision_duplicate_note_type` — CFG-02 §3
- `collision_duplicate_dv_across_chain` — CFG-02 §4

Each collision-class test gets ≥1 positive (collision detected) and ≥1 negative (similar-but-non-colliding) per D-56.07.

**MUST AMEND:** `test_dataview_queries_provenance_in_validate_profile_output` at `:1711+` — currently asserts scalar `dict[str, Path]` shape; update to assert `dict[str, list[Path]]`.

---

### `tests/test_mapping.py` — `id:` field validation tests (extend existing file)

**Analog:** Existing tests of `validate_rules` in `tests/test_mapping.py` (one test per assertion style).

**Phase 56 tests required (per RESEARCH.md §"`mapping_rules.id:` rejection rules"):**
- `validate_rules_id_field_accepted` — string slug accepted, optional absence accepted (backward compat).
- `validate_rules_id_field_rejects_non_string` — int/list/None-typed `id:` rejected with type error.
- `validate_rules_id_field_rejects_too_long` — > 80 chars rejected.
- `validate_rules_id_field_rejects_bad_pattern` — leading digit, uppercase, `..`, `/` all rejected.
- `validate_rules_id_field_rejects_duplicate` — two rules with same `id:` rejected with citation of both indices.

---

### `tests/test_template_overrides.py` — NEW file (collision matrix + ladder + warn-fallback)

**Analog:** `tests/test_profile_composition.py:385-590` (existing `community_templates:` runtime tests).

**Pattern observed (`tests/test_profile_composition.py:385-540`):**
- Fixture vault copied via `_copy_fixture("community_templates", tmp_path)` at line 391.
- Helper `_render_moc_with_profile(vault, profile_overrides, community_id, community_name)` at line 414 — loads profile, applies overrides, builds 1-node `nx.Graph`, calls `_render_moc_like` directly.
- Override-marker assertion: `assert "OVERRIDE_TEMPLATE_MARKER" in text`.
- Warn-and-fall-back tests use `capsys` (`test_override_template_path_escape_falls_back` at line 540): asserts `OVERRIDE_TEMPLATE_MARKER not in text` AND `"[graphify] community_templates override" in captured.err`.

**Phase 56 tests for new file:**
- **Ladder precedence** (per D-56.05): given a node with `rule_id=X`, community membership, and note_type — assert mapping_rule_templates wins; remove the mapping_rule_templates entry → community_templates wins; remove that → note_type_templates wins; remove that → base default.
- **Warn-fallback for `mapping_rule_templates`** — missing override file → stderr contains `"[graphify] mapping_rule_templates override missing"` and base template renders.
- **Warn-fallback for `note_type_templates`** — same shape.
- **Collision matrix** (4 classes × 2 cases per D-56.07): can be parametric (`pytest.mark.parametrize`) for compactness, or one function per case to match house style. Planner discretion.

**Test layout decision (D-56.07 / D-56-discretion):**
- Schema-only validator tests → `tests/test_profile.py` (matches `dataview_queries:` precedent).
- Render-time ladder + warn-fallback → `tests/test_template_overrides.py` (NEW) OR `tests/test_profile_composition.py` (matches `community_templates:` precedent). The NEW file is justified by D-56.07 explicitly authorizing it; sticking to `test_profile_composition.py` is also correct. Recommend: NEW file for cohesion (Phase 56 is a discrete surface, deserves its own test file), and the precedent `tests/test_profile_composition.py` exists as a sibling-of-`test_profile.py` showing this split is accepted.

---

### `docs/PROFILE-CONFIGURATION.md` — major update (D-56.10)

**Analog:** Existing `community_templates:` and `dataview_queries:` sections in the same document.

**Phase 56 additions (per D-56.10):**
- Subsection per new key: `mapping_rule_templates:`, `note_type_templates:`, `mapping_rules.id:`.
- "How overrides resolve" subsection with the precedence ladder as a numbered list (D-56.05).
- "Override collision validation" subsection cross-referencing the four CFG-02 classes (D-56.06).
- One worked example showing all three override types resolving for a single note.

---

### `docs/TEMPLATES.md` — one-paragraph forward-pointer (D-56.11)

**No analog needed.** Add a single paragraph after the existing block-engine intro:
> Profile-level template overrides (per-mapping-rule, per-community, per-note-type) and the precedence ladder are documented in `docs/PROFILE-CONFIGURATION.md` (Phase 56 additions). This document scopes to the block engine; override resolution lives in the profile composition layer.

No duplication of override semantics into TEMPLATES.md.

## Cross-Cutting Patterns (Shared)

### Path-confinement at validators (V12 — File and Resources)
**Source:** `graphify/profile.py:716-728` (community_templates: validator).
**Apply to:** Both new `mapping_rule_templates:` and `note_type_templates:` validators.

```python
elif ".." in template:
    errors.append(f"{prefix}.template contains '..' — fragment paths must stay inside .graphify/")
elif Path(template).is_absolute():
    errors.append(f"{prefix}.template is an absolute path — must be relative to .graphify/")
elif template.startswith("~"):
    errors.append(f"{prefix}.template starts with '~' — must be relative to .graphify/")
```

**CRITICAL:** Use this **substring** style (`".." in template`), NOT the `Path.parts` style from `_taxonomy_path_errors` (`profile.py:277-296`). The Phase 30 `community_templates:` validator chose substring intentionally — port verbatim for parity.

### Validator return contract (`list[str]` of error strings, never raise)
**Source:** Every existing validator in `profile.py` and `mapping.py` (e.g., `validate_rules` docstring at `mapping.py:841-855`: "Returns a list of error strings — empty means valid. Never raises.").
**Apply to:** All four new collision detectors and both new validator blocks.

### Deterministic error wording (index/key + bad value + rule)
**Source:** Phase 30/31 validators throughout `profile.py:682-763`.
**Apply to:** All new error messages. Format: `"<scope>[<idx>].<field>: <description> (got <value>)"` or `"<scope>.<key>: <rule violated>"`.

### Warn-and-fall-back at render time (D-56.13 + Phase 55 D-55.14)
**Source:** `_load_override_template` at `templates.py:1521-1568`.
**Apply to:** Both new override-list resolvers. Achieved by extending `_load_override_template` with a `list_name:` parameter rather than duplicating.

### Stderr warning format
**Source:** `templates.py:1541-1564`.
**Apply to:** All new render-time warnings.

```python
print(f"[graphify] {list_name} override missing ({rel_path}) — using default", file=sys.stderr)
```

### Provenance threading for cross-chain collision detection
**Source:** `profile.py:247-274` (`_deep_merge_with_provenance`).
**Apply to:** `_detect_dataview_collisions` (Phase 56 §4) — consumes the new `dict[str, list[Path]]` shape to enumerate all contributing files.

### Constant-style convention
**Source:** `naming.py:34` (`_REPO_IDENTITY_MAX_LEN = 80`), `mapping.py:26` (`_MAX_PATTERN_LEN = 512`).
**Apply to:** New constants `_RULE_ID_MAX_LEN = 80`, `_RULE_ID_PATTERN`, `_DATAVIEW_QUERY_VARS`. Module-private (leading underscore), uppercase.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/TEMPLATES.md` (forward-pointer paragraph) | documentation | static | Pure cross-link to PROFILE-CONFIGURATION.md; no implementation pattern needed. |

(All other files have strong analogs — Phase 56 is overwhelmingly "port and parameterize.")

## Metadata

**Analog search scope:**
- `graphify/profile.py` (validators, provenance, top-level keys)
- `graphify/templates.py` (override resolver chain, dataview block builder, ClassificationContext)
- `graphify/mapping.py` (validate_rules, ClassificationContext population)
- `graphify/naming.py` (slug pattern reference)
- `tests/test_profile.py`, `tests/test_profile_composition.py`, `tests/test_mapping.py`

**Files scanned:** 6 source + 3 test
**Pattern extraction date:** 2026-05-02

**Verified excerpts:** Every code excerpt above was read directly from the cited file at the cited line range; no excerpts are paraphrased or speculative.
