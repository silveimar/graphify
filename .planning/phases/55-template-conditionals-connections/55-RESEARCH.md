# Phase 55: Template Conditionals & Connection Loops — Research

**Researched:** 2026-05-02
**Domain:** Python template engine extension (string.Template FSM, predicate dispatch, profile schema)
**Confidence:** HIGH — all findings are from direct codebase reads with file:line citations

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-55.01:** Phase 55 is an EXTEND phase. Add new predicate forms + new profile key + user docs. Engine (FSM, `_expand_blocks`, `validate_template` core, sanitization sinks) remains intact.
- **D-55.02:** ROADMAP Success Criterion 2 ("pytest covers nested + empty-iterable cases") is already satisfied by Phase 31 tests. 55-VERIFICATION.md cites them; planner does not re-add equivalent tests.
- **D-55.03:** ROADMAP Success Criterion 3 ("`validate_profile_preflight` flags malformed blocks") is already satisfied at the wiring level (`profile.py:1453`). Phase 55 confirms via test that `predicate_flags:` and unknown `if_note_type_*` references go through the same path.
- **D-55.04:** Add `if_note_type_<X>` for all 6 known note types: thing, statement, person, source, code, moc.
- **D-55.05:** Unknown note-type suffix rejected at preflight (mirrors unknown-predicate rejection). No silent evaluate-false.
- **D-55.06:** Implementation reads from `note_type` parameter that `render_note` already takes. Add `note_type: str | None` to `BlockContext`. Stays frozen.
- **D-55.07:** Add `predicate_flags:` as top-level profile.yaml key. Schema: `dict[str, dict]`. Key = predicate name suffix. Value = `{attr: <name>}` (truthy) or `{attr: <name>, equals: <value>}`.
- **D-55.08:** `predicate_flags` validation at `validate_profile_preflight`: reject duplicate names, collision with `_PREDICATE_CATALOG`, collision with `if_attr_` prefix, unknown attr refs (best-effort). Errors flow through same channel.
- **D-55.09:** Phase 55 = engine surface. Phase 56 = profile composition surface.
- **D-55.10:** `predicate_flags:` under `extends:` / `includes:` inherits Phase 30 merge semantics. No Phase-55-specific composition rule.
- **D-55.11:** New file `docs/TEMPLATES.md` with 8 locked sections.
- **D-55.12:** Examples in `docs/TEMPLATES.md` are executable fixtures in `tests/test_docs_templates_examples.py`.
- **D-55.13:** PROFILE-CONFIGURATION.md gets a 1-line pointer to TEMPLATES.md. No migration doc.
- **D-55.14:** Keep current preflight UX — warn + fall back. No abort, no exit-code escalation.

### Claude's Discretion

- Test layout: split `predicate_flags` tests into `tests/test_predicate_flags.py` vs append to `tests/test_templates.py`.
- Naming of `predicate_flags` rule schema inner keys (`{attr, equals}` vs other).
- Whether `if_flag_<name>` block rendering supports a parameter vs rule evaluated at render time.
- Doc placement of predicate catalog reference table (inline in TEMPLATES.md vs cross-link to templates.py docstring).

### Deferred Ideas (OUT OF SCOPE)

- Composite predicates (`{{#if_god_node_AND_isolated}}`), `{{#unless_*}}`, partials (`{{> snippet}}`)
- Override precedence + collision matrix for `predicate_flags` under `extends:` chains (Phase 56 / CFG-02)
- `docs/MIGRATION_V1_11.md`
- Loud preflight UX (non-zero exit on block errors)
- Scoped template overrides (`template_overrides:`) — Phase 56 / CFG-01
- Per-note-type Dataview templates — Phase 56 / TMPL-03
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TMPL-01 | Conditional template sections with profile-controlled predicates (note type / god-node / simple flags); expansion before `${}` substitution; outputs pass sanitization sinks | `if_note_type_<X>` evaluator branch in `_eval_predicate`; `predicate_flags:` schema in `validate_profile`; D-16 ordering invariant already enforced at `templates.py:1408` |
| TMPL-02 | `{{#connections}}…{{/connections}}` loop with deterministic ordering and sanitized labels/targets; pytest covers nested + empty-iterable cases | Already satisfied by Phase 31: `test_connections_empty_loop_renders_nothing` (L2767), `test_nested_blocks_rejected_with_specific_error` (L2838); Phase 55 must hold them green |
</phase_requirements>

---

## Summary

Phase 55 is a narrow delta on top of the Phase 31 (v1.7) block engine. The engine itself — `_BlockTemplate`, `_expand_blocks` FSM, `_build_edge_records`, sanitization sinks, and `validate_template` core — is frozen. The two additions are: (1) six `if_note_type_<X>` predicates evaluated via a regex branch in `_eval_predicate` (same pattern as the existing `_IF_ATTR_RE` escape hatch), plumbing `note_type` into `BlockContext` at the two `render_note` / `_render_moc_like` call sites; and (2) a `predicate_flags:` top-level profile key that registers per-vault `if_flag_<name>` predicates, validated at `validate_profile_preflight` time and threaded into `BlockContext` as a `flag_predicates` dict. The third deliverable — `docs/TEMPLATES.md` — fills the v1.7 documentation gap and its examples are tested via a new `tests/test_docs_templates_examples.py` file. All Phase 31 backward-compatibility tests, including the byte-identical gate (`test_block_free_template_renders_byte_identical`, L3219), must remain green.

**Primary recommendation:** Use a regex branch in `_eval_predicate` for both `if_note_type_*` and `if_flag_*` (same dispatch style as `_IF_ATTR_RE`), and add two fields to `BlockContext` (`note_type: str | None` and `flag_predicates: dict[str, Callable[[BlockContext], bool]]`).

---

## Phase Scope Confirmation

This is a delta phase. Phase 31 already ships a fully functional block engine: `_BlockTemplate`, `BlockContext` (4 fields, frozen), `_PREDICATE_CATALOG` (4 entries), `_IF_ATTR_RE` escape hatch, `_expand_blocks` single-pass FSM, `_build_edge_records` with `(relation, label)` sort, `validate_template` with nested-rejection and unknown-predicate rejection, and wiring at `validate_profile_preflight` that calls `validate_template` for every override template. Phase 55 adds predicate names and a profile-side mechanism to register more — nothing else changes in the engine.

---

## Per-Question Findings

### Q1: `if_note_type_<X>` Evaluator Placement

**Finding:** Use a regex evaluator branch in `_eval_predicate`, identical in structure to the existing `_IF_ATTR_RE` branch. Do NOT add 6 separate dict entries to `_PREDICATE_CATALOG`.

**Rationale:** The existing dispatch at `templates.py:264-272` has a clear two-branch structure:

```python
# templates.py:264-272  [VERIFIED: codebase read]
def _eval_predicate(name: str, ctx: BlockContext) -> bool:
    if name in _PREDICATE_CATALOG:
        return _PREDICATE_CATALOG[name](ctx)
    m = _IF_ATTR_RE.match(name)       # regex branch for if_attr_*
    if m:
        attr = m.group(1)
        node = ctx.graph.nodes.get(ctx.node_id, {})
        return bool(node.get(attr))
    raise KeyError(name)
```

Adding a third branch for `^if_note_type_([a-z]+)$` keeps this style exactly:

```python
# Phase 55 addition (third branch)
_IF_NOTE_TYPE_RE = re.compile(r"^if_note_type_([a-z]+)$")

def _eval_predicate(name: str, ctx: BlockContext) -> bool:
    if name in _PREDICATE_CATALOG:
        return _PREDICATE_CATALOG[name](ctx)
    m = _IF_ATTR_RE.match(name)
    if m:
        attr = m.group(1)
        node = ctx.graph.nodes.get(ctx.node_id, {})
        return bool(node.get(attr))
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

Putting all 6 note-type names into `_PREDICATE_CATALOG` would require updating `validate_template`'s known-predicate message and would make the catalog a mix of "callable functions" and "name-keyed data", eroding the catalog's semantic clarity. The regex branch is cleaner and matches the existing precedent exactly.

**`validate_template` implications:** The predicate name validation block at `templates.py:513-521` checks `opener in _PREDICATE_CATALOG` then `_IF_ATTR_RE.match(opener)`. Phase 55 adds a third guard (`_IF_NOTE_TYPE_RE.match(opener)` — must match a known note type from `_KNOWN_NOTE_TYPES`, else error) and a fourth guard (`_IF_FLAG_RE.match(opener)` — accepted only when the `predicate_flags` registry is provided, but at validate_template time the catalog check must accept them). Because `validate_template` is a static text validator (no profile context), the cleanest approach is: accept `if_flag_<name>` syntactically (grammar is valid) and let `validate_profile_preflight` catch unknown flag names against the specific profile's `predicate_flags`. This is consistent with how `if_attr_<name>` works — `validate_template` accepts ANY `if_attr_<name>`, not just attrs that exist on any particular node.

---

### Q2: `note_type` Plumbing into `BlockContext`

**Finding:** `BlockContext` is defined at `templates.py:205` with 4 fields (`graph`, `node_id`, `edges`, `dataview_nonempty`). There are **exactly 2** `BlockContext(...)` constructor call sites:

| Site | File:Line | Function | `note_type` available? |
|------|-----------|----------|------------------------|
| 1 | `templates.py:1408` | `render_note` | YES — `note_type` is the 4th positional parameter at `templates.py:1235` |
| 2 | `templates.py:1669` | `_render_moc_like` | PARTIAL — MOC/community have no "note_type" in the TMPL-01 sense; safe to pass `None` or the `template_key` string |

**`render_note` signature** (confirmed at `templates.py:1231-1240`):

```python
def render_note(
    node_id: str,
    G,
    profile: dict,
    note_type: str,              # <-- already present
    classification_context: ...,
    *,
    vault_dir: ...,
    created: ...,
) -> tuple[str, str]:
```

The `note_type` parameter is validated at `templates.py:1255-1258` against `_KNOWN_NOTE_TYPES = ("thing", "statement", "person", "source", "code")`. Phase 55 must expand this local tuple to include `"moc"` when D-55.04 adds `if_note_type_moc` (or restrict `if_note_type_moc` to MOC context only). The profile-level `_KNOWN_NOTE_TYPES` at `profile.py:180-183` already includes `"moc"` and `"community"`.

**Minimal plumbing path:**
1. Add `note_type: str | None` to `BlockContext` dataclass.
2. At `templates.py:1408`: pass `note_type=note_type`.
3. At `templates.py:1669`: pass `note_type=None` (MOC context; `if_note_type_*` blocks in MOC templates evaluate false, which is safe and documented).
4. In `_eval_predicate`: the `_IF_NOTE_TYPE_RE` branch compares `ctx.note_type == m.group(1)`.

**The byte-identical gate** (`test_block_free_template_renders_byte_identical`, L3219) directly constructs `BlockContext` in the test body at L3249:
```python
block_ctx = BlockContext(
    graph=G, node_id="n", edges=..., dataview_nonempty=False,
)
```
Adding a new field to `BlockContext` (frozen dataclass) will **break this test** unless the test is updated. It must be updated to pass `note_type=None` and `flag_predicates={}`. This is a Wave 0 task.

---

### Q3: `predicate_flags:` Schema Design

**Finding:** Mirror the `mapping_rules` when-clause `{attr, equals}` schema from `mapping.py`. The existing attr-matcher in `mapping.py:129-135` [VERIFIED: codebase read]:

```python
# mapping.py:129-135
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

The `_VALID_ATTR_OPS` frozenset at `mapping.py:27` is `{"equals", "in", "contains", "regex"}`. For `predicate_flags`, the two-shape schema is sufficient (D-55.07 locked this):

```yaml
# predicate_flags schema — two shapes
predicate_flags:
  is_published: { attr: is_published }              # truthy check
  is_reviewed:  { attr: review_status, equals: done }  # equality check
```

The inner keys `attr` and `equals` directly mirror the existing vocabulary from `mapping_rules[N].when`. This is the lowest-friction convention for vault authors who already know the mapping-rules syntax.

**Rule value schema (recommended):**
```python
# Rule validation pseudocode — mirrors _validate_attr_when in mapping.py:960+
def _validate_predicate_flag_rule(name: str, rule: dict, prefix: str) -> list[str]:
    errors = []
    if not isinstance(rule, dict):
        errors.append(f"{prefix}.{name}: rule must be a dict")
        return errors
    attr = rule.get("attr")
    if not isinstance(attr, str) or not attr:
        errors.append(f"{prefix}.{name}.attr: must be a non-empty string")
    allowed_keys = {"attr", "equals"}
    extra = set(rule) - allowed_keys
    if extra:
        errors.append(f"{prefix}.{name}: unknown keys {sorted(extra)} — only 'attr' and 'equals' are supported")
    return errors
```

---

### Q4: `predicate_flags` Registration Timing

**Finding:** Register at render time via a `flag_predicates` dict threaded into `BlockContext`, NOT as a mutation of `_PREDICATE_CATALOG`.

**Rationale:** `_PREDICATE_CATALOG` is a module-level dict (`templates.py:252`). Mutating it at load time would create a global side effect — if two different vaults are processed in the same process (e.g., in tests), vault A's `predicate_flags` would leak into vault B's rendering. The correct approach:

Option (b) from the question: at `load_profile` / `validate_profile_preflight` time, parse `predicate_flags` into a `dict[str, Callable[[BlockContext], bool]]` and thread it into `BlockContext` as a new `flag_predicates` field.

**Concrete mechanism:**
1. `profile.py`: add `_compile_predicate_flags(profile: dict) -> dict[str, Callable[[BlockContext], bool]]` that reads `profile.get("predicate_flags", {})` and returns per-name callables using the `{attr, equals}` rule shape.
2. Thread the compiled dict through to `BlockContext(flag_predicates=compiled)` at both call sites (L1408 and L1669).
3. `_eval_predicate` checks `ctx.flag_predicates.get(flag_name)` for `if_flag_*` predicates.

This keeps `_PREDICATE_CATALOG` immutable, makes the compiled predicates per-render-call, and follows the existing precedent where `dataview_nonempty` is precomputed and passed into `BlockContext` rather than re-evaluated inside the engine.

**`load_profile` already returns a dict** that callers thread into `render_note(profile=...)`. The compiled flag predicates can live in the profile dict under a private key (e.g., `_compiled_flag_predicates`) or be extracted by the caller site separately. The simplest approach: compile at `render_note` entry using a small helper, keeping `load_profile` as a pure YAML-to-dict function.

---

### Q5: `predicate_flags` Validation Rules

**Finding:** All four rejection rules from D-55.08 can be implemented in a new `_validate_predicate_flags` helper called from `validate_profile` (not `validate_profile_preflight` — it should live in the same layer as `dataview_queries` validation at `profile.py:648`).

**Implementation sketch:**

```python
# Lives next to validate_profile at profile.py:562+
_IF_FLAG_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")  # valid flag name

def _validate_predicate_flags(flags: dict, prefix: str = "predicate_flags") -> list[str]:
    from graphify.templates import _PREDICATE_CATALOG  # local import — mirrors L1447 pattern

    errors: list[str] = []
    if not isinstance(flags, dict):
        errors.append(f"{prefix}: must be a dict, got {type(flags).__name__}")
        return errors
    seen_names: set[str] = set()
    for name, rule in flags.items():
        if not isinstance(name, str) or not _IF_FLAG_NAME_RE.match(name):
            errors.append(f"{prefix}: flag name {name!r} must be a lowercase identifier")
            continue
        # Rule 1 — duplicate names (impossible in a YAML dict, but guard anyway for merged profiles)
        if name in seen_names:
            errors.append(f"{prefix}.{name}: duplicate flag name")
        seen_names.add(name)
        # Rule 2 — collision with _PREDICATE_CATALOG (e.g., user names flag "god_node")
        full_name = f"if_flag_{name}"
        # Also check if bare name collides: "if_god_node" is in catalog, not "if_flag_god_node"
        # — but check if user's full block name would shadow a catalog entry
        if f"if_{name}" in _PREDICATE_CATALOG or full_name in _PREDICATE_CATALOG:
            errors.append(
                f"{prefix}.{name}: name collides with built-in predicate 'if_{name}' "
                f"— choose a different name"
            )
        # Rule 3 — collision with if_attr_ prefix
        if name.startswith("attr_"):
            errors.append(
                f"{prefix}.{name}: name starting with 'attr_' collides with the "
                f"{{{{#if_attr_<name>}}}} escape hatch — choose a different name"
            )
        # Rule 4 — validate rule shape (attr key required, equals optional)
        errors.extend(_validate_predicate_flag_rule(name, rule, prefix))
    return errors
```

The local import of `_PREDICATE_CATALOG` mirrors the existing pattern at `profile.py:1447` where `validate_template` and `_REQUIRED_PER_TYPE` are imported locally to avoid the `templates.py ↔ profile.py` cycle.

**Rule 3 nuance:** D-55.08 says "names colliding with `if_attr_` prefix". The rendered block name for a flag is `{{#if_flag_<name>}}`. For a name like `attr_foo`, the rendered block would be `{{#if_flag_attr_foo}}`, which is NOT the same as `{{#if_attr_foo}}` — there is no true ambiguity at the parser level (different prefixes). The real risk is cognitive confusion, not parser collision. The validation rule can either warn or error; erroring on `name.startswith("attr_")` is safe and matches D-55.08 literally.

---

### Q6: `docs/TEMPLATES.md` Example-as-Fixture Pattern

**Finding:** No "doc-fenced examples lifted into tests" pattern currently exists in the codebase. The closest pattern is `tests/test_docs.py` [VERIFIED: codebase read], which tests that specific verbatim phrases appear in `docs/MIGRATION_V1_8.md` and `README.md` — a presence/phrase check, not an execution check.

**Recommended idiom for `tests/test_docs_templates_examples.py`:**

```python
# Lightweight fence-extraction + engine-execution idiom
import re
from pathlib import Path

TEMPLATES_MD = Path(__file__).resolve().parent.parent / "docs" / "TEMPLATES.md"

def _extract_fences(label: str) -> list[str]:
    """Extract ```template ... ``` fences tagged with a label comment."""
    text = TEMPLATES_MD.read_text(encoding="utf-8")
    # Fences marked: ``` template <!-- test:label -->
    pattern = rf"```template <!-- test:{re.escape(label)} -->\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)
```

Each section in `docs/TEMPLATES.md` that has an executable example gets a `<!-- test:<id> -->` annotation in its fence. The test file extracts by ID and runs through `_expand_blocks`. This avoids regex-parsing the entire doc and makes it explicit which examples are contract-tested.

**Token/test cost estimate:** One fence extraction + one `_expand_blocks` call per example. With ~1 example per of the 8 sections (~8 tests), this is negligible. The test file itself will be ~100-150 lines including fixtures.

**Alternative (simpler):** Instead of annotating the doc, just define the example strings as Python constants in the test file and assert they appear verbatim in TEMPLATES.md, then run them through the engine — same as `test_docs.py`'s phrase-check pattern extended with engine execution. This avoids modifying the doc format.

**Recommendation:** Use the annotation approach for the examples section (it documents which examples are tested), and phrase-check for the structural sections (ordering invariant, sanitization contract). D-55.12 says "at least one example per section" — 8 tests is the floor.

---

### Q7: Backward-Compatibility Envelope

**Finding:** The following tests in `tests/test_templates.py` constitute the backward-compatibility envelope that Phase 55 must not break.

**Byte-identical gate (ROADMAP criterion 4):**
- `test_block_free_template_renders_byte_identical` (L3219) — directly constructs `BlockContext`; WILL BREAK if new fields are added to the frozen dataclass without updating the test. This is a **Wave 0 fix** — the test must be updated to include the two new fields (`note_type=None`, `flag_predicates={}`).

**Phase 31 tests that are already GREEN and must remain green (D-55.02):**
- `test_nested_blocks_rejected_with_specific_error` (L2838)
- `test_nested_if_in_if_rejected` (L2852)
- `test_connections_empty_loop_renders_nothing` (L2767)
- `test_if_attr_escape_hatch_reads_node_attribute` (L2613)
- `test_if_attr_falsy_value_omits` (L2623)
- `test_if_attr_disjoint_from_catalog_name` (L2636)

**Additional Phase 31 tests to hold green:**
- `test_block_expansion_runs_before_substitution` (L3184)
- `test_render_does_not_revalidate_blocks` (L3268)
- `test_connections_loop_deterministic_order` (L2780)
- `test_connection_field_sanitization_blocks_label_injection` (L3123)
- All `test_render_note_invokes_block_expansion` / `test_render_moc_like_invokes_block_expansion` (L2913, L2932)

**What Phase 55 must avoid to preserve the byte-identical gate:**
- Do NOT change `_BlockTemplate.idpattern` (templates.py:188) — any change rewrites ALL template rendering.
- Do NOT add block-syntax characters to `_BLOCK_CLOSE_RE` (templates.py:199) — would change what `{{/if}}` matches.
- Do NOT change the `(relation, label)` sort key in `_build_edge_records` (templates.py:301).
- Do NOT change the `_sanitize_wikilink_alias` calls in `_build_edge_records`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (configured in `pyproject.toml`) |
| Config file | `pyproject.toml` (no `pytest.ini`) |
| Quick run command | `pytest tests/test_templates.py tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01 | `{{#if_note_type_thing}}` renders when `note_type=="thing"`, omits otherwise | unit | `pytest tests/test_templates.py -k "if_note_type" -q` | ❌ Wave 0 |
| TMPL-01 | All 6 note types (`thing`, `statement`, `person`, `source`, `code`, `moc`) have coverage | unit | `pytest tests/test_templates.py -k "if_note_type" -q` | ❌ Wave 0 |
| TMPL-01 | Unknown `if_note_type_<X>` rejected at preflight (D-55.05) | unit | `pytest tests/test_templates.py -k "note_type_unknown" -q` | ❌ Wave 0 |
| TMPL-01 | `predicate_flags: {is_published: {attr: is_published}}` — truthy flag renders block | unit | `pytest tests/test_templates.py -k "if_flag" -q` | ❌ Wave 0 |
| TMPL-01 | `predicate_flags: {is_reviewed: {attr: status, equals: done}}` — equality flag | unit | `pytest tests/test_templates.py -k "if_flag" -q` | ❌ Wave 0 |
| TMPL-01 | `predicate_flags` validation rejects: duplicate names, catalog collision, `attr_` prefix, unknown attr (best-effort) | unit | `pytest tests/test_profile.py -k "predicate_flags" -q` | ❌ Wave 0 |
| TMPL-01 | Sanitization regression — new predicates emit boolean only (no new string sinks) | unit | existing injection tests remain green | ✅ exists |
| TMPL-01 | `validate_profile_preflight` surfaces `predicate_flags` errors through same error channel | unit | `pytest tests/test_profile.py -k "preflight.*flag" -q` | ❌ Wave 0 |
| TMPL-01 | `BlockContext` frozen dataclass with `note_type` and `flag_predicates` fields | unit | `pytest tests/test_templates.py -k "block_context" -q` | ❌ Wave 0 |
| TMPL-02 | `test_nested_blocks_rejected_with_specific_error` held green (Phase 31, L2838) | unit | `pytest tests/test_templates.py::test_nested_blocks_rejected_with_specific_error -q` | ✅ exists |
| TMPL-02 | `test_nested_if_in_if_rejected` held green (Phase 31, L2852) | unit | `pytest tests/test_templates.py::test_nested_if_in_if_rejected -q` | ✅ exists |
| TMPL-02 | `test_connections_empty_loop_renders_nothing` held green (Phase 31, L2767) | unit | `pytest tests/test_templates.py::test_connections_empty_loop_renders_nothing -q` | ✅ exists |
| TMPL-01/02 | `test_block_free_template_renders_byte_identical` updated for new `BlockContext` fields | unit | `pytest tests/test_templates.py::test_block_free_template_renders_byte_identical -q` | ✅ exists (needs update) |
| TMPL-01 | `docs/TEMPLATES.md` examples run through `_expand_blocks` without error | integration | `pytest tests/test_docs_templates_examples.py -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_templates.py tests/test_profile.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_templates.py` — update `test_block_free_template_renders_byte_identical` (L3249) and any other direct `BlockContext(...)` constructions to include new fields (`note_type=None`, `flag_predicates={}`)
- [ ] `tests/test_templates.py` — add `if_note_type_*` predicate tests (6 note types × true/false = 12 cases minimum)
- [ ] `tests/test_templates.py` — add `if_flag_*` predicate tests (truthy, equality, false cases)
- [ ] `tests/test_profile.py` — add `predicate_flags` validation tests (4 rejection rules + valid cases)
- [ ] `tests/test_docs_templates_examples.py` — new file; covers ≥1 example per `docs/TEMPLATES.md` section
- [ ] `docs/TEMPLATES.md` — new file (8 locked sections per D-55.11)
- [ ] `docs/PROFILE-CONFIGURATION.md` — 1-line pointer addition (D-55.13)

---

## Risks

### Risk 1: `BlockContext` frozen dataclass breaking every direct constructor call

**Failure mode:** `BlockContext` is `frozen=True` with positional and keyword fields. Adding `note_type: str | None` and `flag_predicates: dict[...]` changes the constructor signature. ANY code that builds `BlockContext(graph=G, node_id=..., edges=..., dataview_nonempty=...)` without the new fields will raise `TypeError` at runtime. The test `test_block_free_template_renders_byte_identical` at L3249 does exactly this.

**Mitigation:** 
1. Use default values: `note_type: str | None = None` and `flag_predicates: dict = dataclasses.field(default_factory=dict)`. Frozen dataclasses support default values — this makes the addition backward-compatible at all existing call sites without changing them.
2. Verify with `grep -n "BlockContext(" graphify/templates.py tests/` before merging Wave 1 — there are exactly 2 production call sites (L1408, L1669) and at least 30+ test call sites throughout `tests/test_templates.py`.
3. Wave 0 task: confirm default-value approach works with `frozen=True` dataclass (it does in Python 3.10+).

### Risk 2: `validate_template` accepting `if_flag_*` predicates that don't exist in the active profile

**Failure mode:** `validate_template` is a static function with no profile context (it only knows `_PREDICATE_CATALOG` and `_IF_ATTR_RE`). If Phase 55 makes `validate_template` accept `if_flag_*` syntactically (because the grammar is valid), then a template referencing `{{#if_flag_nonexistent}}` will pass `validate_template` but fail at render time with a `KeyError` in `_eval_predicate` — unless the defensive `except KeyError: cond = False` fallback is in place (it is, at templates.py:384). However, the D-05 invariant says "validation at preflight, render trusts it." The render's `KeyError` fallback was intended for impossible states, not normal operation.

**Mitigation:**
1. `validate_template` accepts `if_flag_*` syntactically without checking the profile (same as `if_attr_*`).
2. `validate_profile_preflight` Layer 2 (template validation, L1447) must be extended to pass the active profile's `predicate_flags` names as a second allowlist to `validate_template`. This requires a signature change to `validate_template(text, required, *, known_flag_predicates=frozenset())`.
3. With `known_flag_predicates` provided at preflight, unknown `if_flag_*` names are caught then, not at render time.

### Risk 3: `predicate_flags` name `attr_<X>` prefix collision is more subtle than it appears

**Failure mode:** D-55.08 says reject names colliding with `if_attr_` prefix. The rendered block name for a flag `attr_foo` would be `{{#if_flag_attr_foo}}`, which is syntactically different from `{{#if_attr_foo}}`. There is no parser collision. However, `_IF_ATTR_RE = re.compile(r"^if_attr_([a-z_][a-z0-9_]*)$")` and `_IF_FLAG_RE = re.compile(r"^if_flag_([a-z][a-z0-9_]*)$")` are disjoint regex patterns. The actual collision risk is the `validate_template` predicate validation block: if a flag name is `attr_foo`, the full block name `if_flag_attr_foo` would match `_IF_FLAG_RE` but NOT `_IF_ATTR_RE` — no parser ambiguity. The concern in D-55.08 is likely about cognitive confusion in profile YAML (an author writing `attr_foo` might expect `{{#if_attr_foo}}` to work, not `{{#if_flag_attr_foo}}`). Implement the rejection as a warning or as a clear error message, not a silent drop.

---

## Naming Lock-in (Q10)

### `_BLOCK_OPEN_RE` Compatibility

`_BLOCK_OPEN_RE = re.compile(r"\{\{#([a-z_][a-z0-9_]*)\}\}")` at `templates.py:198` [VERIFIED: codebase read].

The pattern `[a-z_][a-z0-9_]*` matches:
- `if_flag_is_published` — YES (starts with `i`, contains `_`, all lowercase)
- `if_note_type_thing` — YES (same character class)

Both new predicate names are accepted by the existing `_BLOCK_OPEN_RE` without modification. No regex change needed.

### Prefix Collision Analysis

| Regex | Pattern | Matches `if_flag_*`? | Matches `if_attr_*`? | Ambiguity? |
|-------|---------|---------------------|---------------------|-----------|
| `_IF_ATTR_RE` | `^if_attr_([a-z_][a-z0-9_]*)$` | No | Yes | None |
| `_IF_NOTE_TYPE_RE` (new) | `^if_note_type_([a-z]+)$` | No | No | None |
| `_IF_FLAG_RE` (new) | `^if_flag_([a-z][a-z0-9_]*)$` | Yes (captures name) | No | None |

The prefixes `if_attr_`, `if_note_type_`, and `if_flag_` share the `if_` prefix but are otherwise disjoint. `_IF_ATTR_RE` would match `if_attr_flag_foo` (if someone named a node attribute `flag_foo`), but `_IF_FLAG_RE` with prefix `if_flag_` would not match `if_attr_flag_foo`. No collision.

**The `if_` shared prefix does NOT cause ambiguity** because all four regex patterns (catalog lookup, `_IF_ATTR_RE`, `_IF_NOTE_TYPE_RE`, `_IF_FLAG_RE`) are evaluated in sequence, and each captures a distinct fixed infix (`attr_`, `note_type_`, `flag_`). The dispatch is unambiguous.

**Confirm `if_flag_<name>` prefix (D-55.11):** The `if_flag_` prefix is well-chosen. It is distinct from `if_attr_` (different fixed infix), visible to authors as "profile-declared", and accepted by `_BLOCK_OPEN_RE` unchanged. No change recommended.

---

## Open Questions (RESOLVED)

> All three questions below were substantively resolved during planning (plan-checker Dimension 11). Resolutions embedded in plan actions: 55-02 Task 2 (`_render_moc_like` passes `note_type=None`), 55-03 Task 1 (both production call sites thread `flag_predicates=_compile_flag_predicates(profile)`), 55-03 Task 2 (`_validate_predicate_flags` uses local-import pattern per profile.py:1447 precedent).

1. **`if_note_type_moc` in `render_note` context** — `render_note` validates `note_type` against `("thing", "statement", "person", "source", "code")` at L1255, excluding `"moc"`. If `if_note_type_moc` is added to the predicate set (D-55.04 says all 6), it can only evaluate `True` at the `_render_moc_like` call site where `note_type=None` is passed (or where `template_key="moc"` is used). The planner must decide: (a) pass `template_key` as `note_type` at the `_render_moc_like` call site, enabling `if_note_type_moc` in MOC templates; or (b) `if_note_type_moc` always evaluates `False` in `render_note` context (since `render_note` rejects `"moc"`) and evaluates `True` only in `_render_moc_like`. This is a **planner decision** — no user input needed, but the test coverage choice depends on it.

2. **`flag_predicates` in `_render_moc_like` / `render_moc` call chain** — The `render_moc` / `render_community_overview` path goes through `_render_moc_like` (L1669 BlockContext). Should MOC templates support `{{#if_flag_<name>}}` blocks? D-55.01 says "add new predicate forms." MOC templates are user templates and could plausibly use flags. The planner should wire `flag_predicates` into the `_render_moc_like` `BlockContext` (L1669) too, not just `render_note` (L1408). This is a **planner decision** with no ambiguity risk — wiring to both call sites is safer.

3. **`_validate_predicate_flags` import cycle** — The function needs to import `_PREDICATE_CATALOG` from `templates.py`. `profile.py` already does this for `validate_template` and `_REQUIRED_PER_TYPE` via function-local imports at `profile.py:1447`. The same pattern applies here. No import cycle concern. Confirm pattern is reused.

---

## Sources

### Primary (HIGH confidence — codebase reads)

- `graphify/templates.py:177-420` — `_BlockTemplate`, `BlockContext`, `_PREDICATE_CATALOG`, `_IF_ATTR_RE`, `_BLOCK_OPEN_RE`, `_eval_predicate`, `_build_edge_records`, `_expand_blocks`, `validate_template` [VERIFIED: direct read]
- `graphify/templates.py:1231-1420` — `render_note` signature, BlockContext construction at L1408 [VERIFIED: direct read]
- `graphify/templates.py:1640-1680` — `_render_moc_like` BlockContext construction at L1669 [VERIFIED: direct read]
- `graphify/profile.py:160-185` — `_VALID_TOP_LEVEL_KEYS`, `_KNOWN_NOTE_TYPES`, `dataview_queries` validation pattern at L648-674 [VERIFIED: direct read]
- `graphify/profile.py:517-560` — `load_profile` function [VERIFIED: direct read]
- `graphify/profile.py:1332-1500` — `validate_profile_preflight` full function [VERIFIED: direct read]
- `graphify/mapping.py:27,80-140,820-950` — `_VALID_ATTR_OPS`, attr-matcher dispatch, `_validate_attr_when` [VERIFIED: direct read]
- `tests/test_templates.py:2510-3280` — Phase 31 test section, key test names and line numbers [VERIFIED: direct read]
- `.planning/phases/55-template-conditionals-connections/55-CONTEXT.md` — All 14 D-55.* decisions [VERIFIED: direct read]

### Secondary (HIGH confidence — confirmed cross-references)

- `.planning/milestones/v1.7-ROADMAP.md:224+` — Phase 31 success criteria (criterion 4 = byte-identical) [VERIFIED: direct read]

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| `_eval_predicate` dispatch style | HIGH | Read actual code at L264-272 |
| `BlockContext` field count and call sites | HIGH | Grep confirmed exactly 2 production call sites at L1408, L1669 |
| `note_type` availability at render_note L1235 | HIGH | Read function signature directly |
| `predicate_flags` schema design (`{attr, equals}`) | HIGH | Read `mapping.py:129-135` and `_VALID_ATTR_OPS` |
| Registration timing (per-render, not global) | HIGH | Confirmed `_PREDICATE_CATALOG` is module-level dict; global mutation is unsafe |
| `validate_template` predicate validation block | HIGH | Read L513-521 directly |
| Backward-compat test names and line numbers | HIGH | Read `tests/test_templates.py` directly |
| `_BLOCK_OPEN_RE` accepts `if_flag_*` | HIGH | Read regex at L198 and verified character class |
| Doc example pattern (none exists) | HIGH | Searched `tests/test_docs.py` and all test files |

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (stable codebase; templates.py API unlikely to change outside Phase 55 scope)
