# Phase 55: Template Conditionals & Connection Loops — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 7
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/templates.py` | utility (predicate engine) | transform | `graphify/templates.py` itself — extend `_IF_ATTR_RE` branch + `BlockContext` dataclass | exact (self-extension) |
| `graphify/profile.py` | utility (validation) | transform | `graphify/profile.py` `dataview_queries` validation block (L648–674) + `validate_profile_preflight` Layer 2 (L1430–1465) | exact (self-extension) |
| `tests/test_templates.py` | test | transform | `tests/test_templates.py` L2613–2670 — `test_if_attr_*` block, L3219–3265 — byte-identical gate | exact (self-extension) |
| `tests/test_profile.py` | test | transform | `tests/test_profile.py` L1631–1695 — `test_dataview_queries_*` block | exact (self-extension) |
| `tests/test_docs_templates_examples.py` | test | transform | `tests/test_docs.py` — phrase-check-doc pattern (closest; no exec-fixture pattern exists yet) | role-match |
| `docs/TEMPLATES.md` | documentation | n/a | `docs/RELATIONS.md` — terse reference format: what/when/example/pitfall | style-match |
| `docs/PROFILE-CONFIGURATION.md` | documentation | n/a | `docs/PROFILE-CONFIGURATION.md` itself — 1-line pointer addition | exact (self-extension) |

---

## Pattern Assignments

### `graphify/templates.py` (extend — two new predicate branches)

**Analog:** `graphify/templates.py:196–272` (self, `_IF_ATTR_RE` branch + `_eval_predicate`)

**Pattern 1 — `_IF_ATTR_RE` regex constant (line 196); copy structure for two new constants:**
```python
# templates.py:196
_IF_ATTR_RE = re.compile(r"^if_attr_([a-z_][a-z0-9_]*)$")
```
Apply this pattern by adding these two constants directly below `_IF_ATTR_RE`:
```python
_IF_NOTE_TYPE_RE = re.compile(r"^if_note_type_([a-z]+)$")
_IF_FLAG_RE = re.compile(r"^if_flag_([a-z][a-z0-9_]*)$")
```

**Pattern 2 — `BlockContext` frozen dataclass (lines 206–219); add two defaulted fields:**
```python
# templates.py:206-219
@dataclasses.dataclass(frozen=True)
class BlockContext:
    graph: "object"
    node_id: str
    edges: list[dict]
    dataview_nonempty: bool
```
Apply this pattern by appending two fields with defaults (frozen dataclasses support defaults in Python 3.10+):
```python
    note_type: str | None = None
    flag_predicates: dict = dataclasses.field(default_factory=dict)
```
Critical: defaults make all existing `BlockContext(graph=G, node_id=..., edges=..., dataview_nonempty=False)` call sites backward-compatible without modification. Verify with `grep -n "BlockContext(" graphify/templates.py tests/` — confirms exactly 2 production call sites (L1408, L1669) and ~30+ test call sites, all safe to leave unchanged.

**Pattern 3 — `_eval_predicate` dispatch (lines 264–272); add two new regex branches:**
```python
# templates.py:264-272  — EXISTING, do not modify
def _eval_predicate(name: str, ctx: BlockContext) -> bool:
    if name in _PREDICATE_CATALOG:
        return _PREDICATE_CATALOG[name](ctx)
    m = _IF_ATTR_RE.match(name)
    if m:
        attr = m.group(1)
        node = ctx.graph.nodes.get(ctx.node_id, {})
        return bool(node.get(attr))
    raise KeyError(name)
```
Apply this pattern by inserting two new branches before the final `raise KeyError(name)`:
```python
    m = _IF_NOTE_TYPE_RE.match(name)
    if m:
        return ctx.note_type == m.group(1)
    m = _IF_FLAG_RE.match(name)
    if m:
        flag_name = m.group(1)
        handler = ctx.flag_predicates.get(flag_name)
        if handler is not None:
            return handler(ctx)
    raise KeyError(name)
```

**Pattern 4 — `validate_template` predicate name validation (lines 513–521); extend with two new guards:**
```python
# templates.py:513-521  — EXISTING, do not modify
if opener in _PREDICATE_CATALOG:
    pass
elif _IF_ATTR_RE.match(opener):
    pass
else:
    block_errors.append(
        f"validate_template: unknown predicate '{{{{#{opener}}}}}' "
        f"— known: {sorted(_PREDICATE_CATALOG)} "
        "(or use {{#if_attr_<name>}} for raw node attributes)"
    )
```
Apply this pattern by inserting two elif branches:
```python
elif _IF_NOTE_TYPE_RE.match(opener):
    note_type_suffix = _IF_NOTE_TYPE_RE.match(opener).group(1)
    if note_type_suffix not in _KNOWN_NOTE_TYPES:
        block_errors.append(
            f"validate_template: unknown note type suffix '{note_type_suffix}' "
            f"in '{{{{#{opener}}}}}' — known: {sorted(_KNOWN_NOTE_TYPES)}"
        )
elif _IF_FLAG_RE.match(opener):
    flag_name = _IF_NOTE_TYPE_RE.match(opener) and ... # accept syntactically
    # validate_template accepts if_flag_* syntactically (same as if_attr_*);
    # validate_profile_preflight checks flag names against profile's predicate_flags
    pass
```
Note: `validate_template` also receives a new optional keyword `known_flag_predicates: frozenset[str] = frozenset()` to support the preflight cross-check described in RESEARCH.md Risk 2.

**Pattern 5 — `BlockContext` plumbing at production call sites (lines 1408, 1669):**

At `templates.py:1408` (`render_note`): `note_type` is the 4th positional parameter of `render_note` (confirmed at L1235). Pass it through:
```python
block_ctx = BlockContext(
    graph=G, node_id=node_id,
    edges=_build_edge_records(G, node_id),
    dataview_nonempty=bool(dataview_block.strip()),
    note_type=note_type,                          # NEW
    flag_predicates=_compile_flag_predicates(profile),  # NEW
)
```
At `templates.py:1669` (`_render_moc_like`): pass `note_type=None` (MOC context; `if_note_type_*` blocks always evaluate False here, which is safe and documented):
```python
block_ctx = BlockContext(
    graph=G, node_id=node_id,
    edges=_build_edge_records(G, node_id),
    dataview_nonempty=...,
    note_type=None,                               # NEW — MOC has no TMPL-01 note_type
    flag_predicates=_compile_flag_predicates(profile),  # NEW
)
```

---

### `graphify/profile.py` (extend — `predicate_flags` validation)

**Analog 1:** `graphify/profile.py:648–674` — `dataview_queries` validation block (self-extension)

**Analog 2:** `graphify/profile.py:1430–1465` — `validate_profile_preflight` Layer 2 template validation (self-extension)

**Pattern 1 — `dataview_queries` validation block (lines 648–674); copy structure for `_validate_predicate_flags`:**
```python
# profile.py:648-674  — EXISTING dataview_queries block; model the new one on this
dvq = profile.get("dataview_queries")
if dvq is not None:
    if not isinstance(dvq, dict):
        errors.append(
            f"dataview_queries must be a dict, got {type(dvq).__name__}"
        )
    else:
        for key, value in dvq.items():
            if not isinstance(key, str):
                errors.append(
                    f"dataview_queries: key {key!r} must be a string "
                    f"(got {type(key).__name__})"
                )
                continue
            if key not in _KNOWN_NOTE_TYPES:
                errors.append(
                    f"dataview_queries: unknown note_type {key!r} — "
                    f"valid types are: {sorted(_KNOWN_NOTE_TYPES)}"
                )
                continue
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"dataview_queries.{key}: query must be a non-empty string"
                )
```
Apply this pattern by adding an analogous `predicate_flags` block in `validate_profile` (same function, after the `dataview_queries` block). Key differences: the per-entry check validates `{attr, equals}` rule shape rather than string values.

**Pattern 2 — `validate_profile_preflight` Layer 2 local import (lines 1430–1435):**
```python
# profile.py:1430-1435  — function-local import pattern to avoid import cycle
        from graphify.templates import (
            validate_template as _validate_template,
            _REQUIRED_PER_TYPE,
        )
```
Apply this pattern by adding `_PREDICATE_CATALOG` and the new `_IF_FLAG_RE` to the same local import block when calling `_validate_predicate_flags`. This avoids the `templates.py ↔ profile.py` import cycle (confirmed precedent at L1447).

**Pattern 3 — `_VALID_TOP_LEVEL_KEYS` addition (line 168):**
```python
# profile.py:168-177  — EXISTING
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output", "taxonomy", "repo", "corpus",
    "extends", "includes", "community_templates",  # Phase 30 (CFG-02 / CFG-03)
    "dataview_queries",  # Phase 31 (TMPL-03, D-11)
}
```
Apply this pattern by adding `"predicate_flags"` to this set with a Phase 55 comment.

**Pattern 4 — `mapping.py:129–135` attr-matcher dispatch; model for the `predicate_flags` rule evaluator:**
```python
# mapping.py:129-135  — model for _compile_flag_predicates / flag evaluator
if "attr" in when:
    key = when["attr"]
    if key not in attrs:
        return False
    raw = attrs[key]
    if "equals" in when:
        return raw == when["equals"]
    # no equals → truthy check
    return bool(raw)
```
Apply this pattern in the `_compile_flag_predicates` helper in `templates.py` (or `profile.py`). Two-shape schema per D-55.07: `{attr: <name>}` → truthy; `{attr: <name>, equals: <value>}` → equality. The inner keys `attr` and `equals` mirror existing mapping-rules vocabulary exactly — no new vocabulary.

---

### `tests/test_templates.py` (extend — new predicate cases + `BlockContext` update)

**Analog:** `tests/test_templates.py:2613–2670` — `test_if_attr_*` block (self-extension)

**Pattern 1 — `test_if_attr_*` structure (lines 2613–2670); copy for `if_note_type_*` cases:**
```python
# test_templates.py:2613-2625  — EXACT model for if_note_type_* true/false cases
def test_if_attr_escape_hatch_reads_node_attribute():
    from graphify.templates import BlockContext

    G = nx.Graph()
    G.add_node("p", label="P", is_published=True)
    ctx = BlockContext(graph=G, node_id="p", edges=[], dataview_nonempty=False)
    out = _expand("X{{#if_attr_is_published}}PUB{{/if}}Y", ctx)
    assert out == "XPUBY"


def test_if_attr_falsy_value_omits():
    from graphify.templates import BlockContext

    G = nx.Graph()
    G.add_node("p_false", label="P", is_published=False)
    G.add_node("p_missing", label="P")
    ctx_false = BlockContext(graph=G, node_id="p_false", edges=[], dataview_nonempty=False)
    ctx_missing = BlockContext(graph=G, node_id="p_missing", edges=[], dataview_nonempty=False)
    template = "X{{#if_attr_is_published}}PUB{{/if}}Y"
    assert _expand(template, ctx_false) == "XY"
    assert _expand(template, ctx_missing) == "XY"
```
Apply this pattern for `if_note_type_*` tests: one true case per note type (6 cases), one false case (wrong type), one missing-note_type case (note_type=None). For `if_flag_*` tests: truthy rule case, equality rule case, false/absent attr case.

**Pattern 2 — byte-identical gate `BlockContext` constructor (lines 3249–3254); must be updated:**
```python
# test_templates.py:3249-3254  — MUST UPDATE to pass new default fields explicitly
block_ctx = BlockContext(
    graph=G,
    node_id="n",
    edges=_build_edge_records(G, "n"),
    dataview_nonempty=False,
)
```
Apply this pattern by adding `note_type=None, flag_predicates={}` — Wave 0 task. Confirm this is the only direct `BlockContext(...)` constructor in the test file that needs updating (grep all call sites first; most pass keyword args and will be auto-compatible via the new defaults).

---

### `tests/test_profile.py` (extend — `predicate_flags` validation tests)

**Analog:** `tests/test_profile.py:1631–1695` — `test_dataview_queries_*` block (self-extension)

**Pattern — `test_dataview_queries_*` structure; copy for `predicate_flags` validation tests:**
```python
# test_profile.py:1631-1641
def test_dataview_queries_top_level_key_accepted():
    """Valid dataview_queries dict produces no validation errors."""
    profile = {
        "dataview_queries": {
            "moc": "TABLE x FROM y",
            "community": "TABLE z FROM w",
        }
    }
    assert validate_profile(profile) == []


def test_dataview_queries_unknown_key_rejected():
    """Typo `mocs:` produces a validate_profile error citing the typo."""
    profile = {"dataview_queries": {"mocs": "TABLE x"}}
    errors = validate_profile(profile)
    assert any("unknown note_type 'mocs'" in e for e in errors), errors


def test_dataview_queries_non_dict_rejected():
    profile = {"dataview_queries": "not a dict"}
    errors = validate_profile(profile)
    assert any("must be a dict" in e for e in errors), errors
```
Apply this pattern for the 4 rejection rules from D-55.08:
1. `test_predicate_flags_valid_truthy_rule` — `{is_published: {attr: is_published}}` → no errors
2. `test_predicate_flags_valid_equality_rule` — `{is_reviewed: {attr: status, equals: done}}` → no errors
3. `test_predicate_flags_non_dict_rejected` — scalar value rejected
4. `test_predicate_flags_catalog_collision_rejected` — name `god_node` collides with `if_god_node` in `_PREDICATE_CATALOG`
5. `test_predicate_flags_attr_prefix_rejected` — name `attr_foo` starts with `attr_`
6. `test_predicate_flags_missing_attr_key_rejected` — rule `{}` missing required `attr` key
7. `test_predicate_flags_extra_keys_rejected` — rule `{attr: x, op: y}` has unknown key
8. `test_predicate_flags_top_level_key_accepted` — key present in `_VALID_TOP_LEVEL_KEYS`

---

### `tests/test_docs_templates_examples.py` (CREATE NEW — doc-fence-as-fixture)

**Analog:** No exact analog. Closest: `tests/test_docs.py` — phrase-check pattern (role-match).

**Pattern — `tests/test_docs.py` phrase-check approach; extend with engine execution:**
```python
# tests/test_docs.py — existing phrase-check pattern (no direct read needed;
# the pattern is: read doc file, assert phrase appears verbatim)
```
Apply this pattern as the base, then extend each check to also run the extracted template text through `_expand_blocks`. RESEARCH.md Q6 recommends the annotation approach for executable examples:

```python
# Recommended idiom for new test file
import re
from pathlib import Path
import networkx as nx

TEMPLATES_MD = Path(__file__).resolve().parent.parent / "docs" / "TEMPLATES.md"

def _extract_fence(label: str) -> str:
    """Extract a ```template fence annotated with <!-- test:<label> -->."""
    text = TEMPLATES_MD.read_text(encoding="utf-8")
    pattern = rf"```template <!-- test:{re.escape(label)} -->\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    assert m, f"No annotated fence with label {label!r} found in TEMPLATES.md"
    return m.group(1)
```
Each test: (1) assert the fence exists in TEMPLATES.md, (2) build a minimal `BlockContext`, (3) call `_expand_blocks`, (4) assert expected output. One test per section of `docs/TEMPLATES.md` (8 sections = 8 tests minimum per D-55.12).

---

### `docs/TEMPLATES.md` (CREATE NEW — 8-section reference doc)

**Analog:** `docs/RELATIONS.md` — terse reference format (style-match)

**Pattern — RELATIONS.md opening style (lines 1–12):**
```markdown
# Graphify relation vocabulary

Authoritative registry for **`edge.relation`** strings (extract JSON) and
**`hyperedges[].relation`** (group edges). **`validate.py`** warns once per
unknown value on stderr; update this doc when adding emitters.

## Concept ↔ code (Phase 46)

| Relation | Direction | Notes |
|----------|-----------|--------|
| `implements` | **code → concept** | Canonical after `build()` normalization. |
```
Apply this pattern: terse, no tutorial prose, tables for catalogs, code fences for YAML/template examples, one "Pitfall" note per section where a misuse is likely. Section structure per D-55.11 (8 locked sections):

1. **Conditional blocks** — predicate catalog table + `if_attr_*` escape hatch + new `if_note_type_*` + new `if_flag_*`
2. **Connection loops** — `{{#connections}}…{{/connections}}` + `${conn.<field>}` / `${conn_<field>}` field table + sort key
3. **Ordering invariant** — D-16: blocks expand BEFORE `${}` substitution
4. **Sanitization** — label/HTML sinks, T-31-01 contract, why new predicates need no new sink (boolean output)
5. **Predicate catalog table** — name → semantics → typical use (all built-ins + note-type family + flag family)
6. **Authoring `predicate_flags:`** — profile.yaml example with `{attr}` and `{attr, equals}` shapes
7. **Validation behavior** — preflight flow, `--validate-profile` flag, fallback contract (warn + builtin, no abort)
8. **Backward compatibility** — block-free templates remain byte-identical (ROADMAP criterion 4 citation)

Each section with an executable example gets a `<!-- test:<id> -->` annotation on its fence.

---

### `docs/PROFILE-CONFIGURATION.md` (modify — 1-line pointer)

**Analog:** `docs/PROFILE-CONFIGURATION.md` itself (self-extension)

**Pattern:** Find the existing template-related section in `docs/PROFILE-CONFIGURATION.md` and add one line:
```
For block syntax (`{{#if_*}}`, `{{#connections}}`, predicates), see [docs/TEMPLATES.md](TEMPLATES.md).
```
Per D-55.13: nothing more. No migration doc, no cross-link to older config refs.

---

## Shared Patterns

### `BlockContext` construction (all call sites)
**Source:** `graphify/templates.py:206–219` (dataclass definition) and `tests/test_templates.py:3249–3254` (byte-identical gate)
**Apply to:** `graphify/templates.py:1408` (`render_note`), `graphify/templates.py:1669` (`_render_moc_like`), and every `BlockContext(...)` in `tests/test_templates.py`
```python
# Safe default values mean all existing call sites compile unchanged.
# Only the two production sites (L1408, L1669) need explicit new kwargs.
# The byte-identical gate test at L3249 must be updated as Wave 0.
note_type: str | None = None
flag_predicates: dict = dataclasses.field(default_factory=dict)
```

### Function-local import to avoid import cycle
**Source:** `graphify/profile.py:1430–1435`
**Apply to:** Any new `_validate_predicate_flags` helper in `profile.py` that needs `_PREDICATE_CATALOG` from `templates.py`
```python
from graphify.templates import (
    validate_template as _validate_template,
    _REQUIRED_PER_TYPE,
    # add: _PREDICATE_CATALOG, _IF_FLAG_RE
)
```

### Error-list return convention
**Source:** `graphify/profile.py:562–565` (`validate_profile`)
**Apply to:** `_validate_predicate_flags` helper
```python
def validate_profile(profile: dict) -> list[str]:
    """Validate a profile dict. Returns a list of error strings — empty means valid."""
    ...
    errors: list[str] = []
```
Return `list[str]`, empty = valid, non-empty = errors found. Caller extends its own error list: `errors.extend(_validate_predicate_flags(...))`.

### `{attr, equals}` rule shape
**Source:** `graphify/mapping.py:129–135`
**Apply to:** `_compile_flag_predicates` / flag evaluator in `templates.py`, and `_validate_predicate_flag_rule` in `profile.py`
```python
if "attr" in when:
    key = when["attr"]
    if key not in attrs:
        return False
    raw = attrs[key]
    if "equals" in when:
        return raw == when["equals"]
    return bool(raw)
```
Reuse `attr` / `equals` vocabulary exactly — vault authors who know mapping-rules already know this schema.

---

## No Analog Found

None. All 7 files have viable analogs in the codebase. `tests/test_docs_templates_examples.py` is the weakest match (no exec-fixture pattern exists), but `tests/test_docs.py` provides sufficient structural guidance.

---

## Metadata

**Analog search scope:** `graphify/templates.py`, `graphify/profile.py`, `graphify/mapping.py`, `tests/test_templates.py`, `tests/test_profile.py`, `tests/test_docs.py`, `docs/RELATIONS.md`
**Files scanned:** 7 primary + 2 supporting (`mapping.py`, `test_docs.py`)
**Pattern extraction date:** 2026-05-02
