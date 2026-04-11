---
phase: 04-merge-engine
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/profile.py
  - tests/test_profile.py
autonomous: true
requirements:
  - MRG-02
  - MRG-07
tags:
  - profile
  - merge-config
  - validation

must_haves:
  truths:
    - "_DEFAULT_PROFILE.merge.preserve_fields contains 'created' in addition to 'rank', 'mapState', 'tags'"
    - "_DEFAULT_PROFILE.merge has a field_policies key defaulting to an empty dict {}"
    - "A user profile setting merge.field_policies: {tags: replace} deep-merges over the empty default without discarding other merge keys"
    - "validate_profile flags an invalid field_policies value (e.g. 'blah') with mode error and continues validation"
    - "validate_profile flags a non-string field_policies key with a type error"
    - "validate_profile continues to accept all three merge.strategy values: update, skip, replace"
  artifacts:
    - path: "graphify/profile.py"
      provides: "_DEFAULT_PROFILE.merge extended with created + field_policies defaults, validate_profile extended with field_policies validation"
    - path: "tests/test_profile.py"
      provides: "Coverage of new defaults, field_policies validation, and merge-strategy acceptance"
  key_links:
    - from: "_DEFAULT_PROFILE[merge][preserve_fields]"
      to: "Phase 2 created: frontmatter field (D-27)"
      via: "Preserving created across runs"
      pattern: "\"created\""
    - from: "_DEFAULT_PROFILE[merge][field_policies]"
      to: "merge.py _DEFAULT_FIELD_POLICIES table (Plan 03)"
      via: "_deep_merge override path — user overrides user's field_policies over merge.py built-in table"
      pattern: "field_policies"
---

<objective>
Extend `graphify/profile.py` to ship the Phase 4 merge configuration contract: add `"created"` to `_DEFAULT_PROFILE.merge.preserve_fields`, add an empty `"field_policies": {}` default to the same block, and extend `validate_profile` to validate the optional user-supplied `merge.field_policies` map (key-must-be-string, value-must-be-in-{replace,union,preserve}).

Purpose: Satisfies D-65 (policy table lives in merge module + profile override) and D-27 (`created:` preserved forever). Plan 03 depends on the `_DEFAULT_PROFILE` shape emitted here when it deep-merges its `_DEFAULT_FIELD_POLICIES` table with `profile.merge.field_policies`.

Output: `_DEFAULT_PROFILE.merge` has the final shape `{"strategy": "update", "preserve_fields": ["rank", "mapState", "tags", "created"], "field_policies": {}}`. `validate_profile` returns actionable error strings for malformed `field_policies`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-merge-engine/04-CONTEXT.md
@.planning/phases/01-foundation/01-CONTEXT.md
@graphify/profile.py
@graphify/validate.py
@tests/test_profile.py

<interfaces>
<!-- From graphify/profile.py (existing) -->

```python
_DEFAULT_PROFILE: dict = {
    # ... other sections ...
    "merge": {
        "strategy": "update",
        "preserve_fields": ["rank", "mapState", "tags"],
    },
    # ...
}

_VALID_MERGE_STRATEGIES = {"update", "skip", "replace"}  # L49 — already correct

def _deep_merge(base: dict, override: dict) -> dict: ...  # L82 — user-profile overlay engine
def validate_profile(profile: dict) -> list[str]: ...     # L133 — accumulator pattern
```

Existing merge validation (L159-175, the stub we extend):
```python
merge = profile.get("merge")
if merge is not None:
    if not isinstance(merge, dict):
        errors.append("'merge' must be a mapping (dict)")
    else:
        strategy = merge.get("strategy")
        if strategy is not None and strategy not in _VALID_MERGE_STRATEGIES:
            errors.append(...)
        preserve = merge.get("preserve_fields")
        if preserve is not None and not isinstance(preserve, list):
            errors.append("'merge.preserve_fields' must be a list")
```

<!-- Locked field-policy mode vocabulary (from CONTEXT.md D-64, D-65) -->
Valid modes: "replace", "union", "preserve"
Unknown keys default to "preserve" at dispatch time (Plan 03 concern, not validation-time).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend _DEFAULT_PROFILE.merge + add _VALID_FIELD_POLICY_MODES constant</name>
  <files>graphify/profile.py</files>
  <read_first>
    - graphify/profile.py L1-60 (module header + constants block — locate where to add `_VALID_FIELD_POLICY_MODES`)
    - graphify/profile.py L16-40 (_DEFAULT_PROFILE — merge section is what you're modifying)
    - graphify/profile.py L49 (_VALID_MERGE_STRATEGIES — mirror this pattern)
    - graphify/profile.py L359-394 (_dump_frontmatter — DO NOT TOUCH, just confirm field emission semantics for downstream context)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-64, D-65, D-27 (the three locked decisions this implements)
  </read_first>
  <behavior>
    - Test 1: `from graphify.profile import _DEFAULT_PROFILE; assert "created" in _DEFAULT_PROFILE["merge"]["preserve_fields"]`
    - Test 2: `assert _DEFAULT_PROFILE["merge"]["preserve_fields"] == ["rank", "mapState", "tags", "created"]` (exact order, locked)
    - Test 3: `assert _DEFAULT_PROFILE["merge"]["field_policies"] == {}` (empty dict default)
    - Test 4: `from graphify.profile import _VALID_FIELD_POLICY_MODES; assert _VALID_FIELD_POLICY_MODES == {"replace", "union", "preserve"}`
    - Test 5: `load_profile(tmp_vault_no_profile_yaml)` returns a dict whose `["merge"]["field_policies"]` is `{}` (no regression in fallback path)
    - Test 6: A user profile YAML with `merge: {field_policies: {tags: replace}}` produces a merged profile where `["merge"]["field_policies"] == {"tags": "replace"}` AND `["merge"]["preserve_fields"]` is still `["rank", "mapState", "tags", "created"]` (deep-merge preserved other defaults)
  </behavior>
  <action>
Modify `graphify/profile.py` with two exact edits:

**Edit 1 — Add the mode-vocabulary constant next to `_VALID_MERGE_STRATEGIES` (right after line 49):**

```python
_VALID_MERGE_STRATEGIES = {"update", "skip", "replace"}

# Phase 4 D-64: per-key merge policy modes. `replace` overwrites scalar on
# every UPDATE, `union` deduplicates list contributions from both sides,
# `preserve` never touches the key. Unknown keys at dispatch time default to
# `preserve` (conservative) — Plan 03's policy dispatcher enforces that.
_VALID_FIELD_POLICY_MODES: frozenset[str] = frozenset({"replace", "union", "preserve"})
```

**Edit 2 — Replace the `merge` block inside `_DEFAULT_PROFILE` (L26-29) with exactly:**

```python
    "merge": {
        "strategy": "update",
        # D-27 + D-65: `created` must survive re-runs — set ONCE at first
        # CREATE by Phase 2, never rewritten by Phase 4 merge UPDATE path.
        "preserve_fields": ["rank", "mapState", "tags", "created"],
        # D-65: user overrides merge-module's built-in _DEFAULT_FIELD_POLICIES
        # table. Empty default means Plan 03's table wins unchanged.
        "field_policies": {},
    },
```

**DO NOT touch:**
- `validate_profile` (Task 2 handles that)
- `_dump_frontmatter`, `safe_frontmatter_value`, `safe_tag`, `safe_filename` (unrelated)
- `_VALID_TOP_LEVEL_KEYS`, `_VALID_NAMING_CONVENTIONS` (unrelated)
- `_deep_merge` (already handles the new shape correctly — nested dicts deep-merge by default)
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && python -c "from graphify.profile import _DEFAULT_PROFILE, _VALID_FIELD_POLICY_MODES; assert _DEFAULT_PROFILE['merge']['preserve_fields'] == ['rank', 'mapState', 'tags', 'created']; assert _DEFAULT_PROFILE['merge']['field_policies'] == {}; assert _VALID_FIELD_POLICY_MODES == frozenset({'replace', 'union', 'preserve'}); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q '"created"' graphify/profile.py` succeeds and the string appears inside the preserve_fields list
    - `grep -q '_VALID_FIELD_POLICY_MODES' graphify/profile.py` succeeds
    - `grep -q '"field_policies": {}' graphify/profile.py` succeeds (default empty dict present in _DEFAULT_PROFILE)
    - `python -c "from graphify.profile import _DEFAULT_PROFILE; assert _DEFAULT_PROFILE['merge']['preserve_fields'].index('created') == 3"` exits 0 (verifies order: created is LAST in the list, maintaining original order of rank/mapState/tags)
    - `pytest tests/test_profile.py -q` exits 0 (no regression in existing profile tests)
  </acceptance_criteria>
  <done>_DEFAULT_PROFILE.merge has the final shape with `created` added to preserve_fields and `field_policies: {}` default; `_VALID_FIELD_POLICY_MODES` constant declared; all existing profile tests still pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend validate_profile to validate merge.field_policies</name>
  <files>graphify/profile.py, tests/test_profile.py</files>
  <read_first>
    - graphify/profile.py L133-258 (validate_profile — read the entire accumulator pattern so you can extend the merge block in-place)
    - graphify/profile.py L159-173 (existing merge validation stub — your extension slots in immediately below the preserve_fields check)
    - graphify/validate.py (validation returns `list[str]` convention — never raises)
    - tests/test_profile.py (read existing validate_profile test patterns — invalid-strategy, invalid-naming-convention — to mirror style)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-65 (field_policies schema)
  </read_first>
  <behavior>
    - Test `test_validate_profile_accepts_empty_field_policies`: `validate_profile({"merge": {"field_policies": {}}})` returns `[]`.
    - Test `test_validate_profile_accepts_valid_field_policies`: `validate_profile({"merge": {"field_policies": {"tags": "replace", "collections": "union", "rank": "preserve"}}})` returns `[]`.
    - Test `test_validate_profile_rejects_non_dict_field_policies`: `validate_profile({"merge": {"field_policies": ["tags"]}})` returns a non-empty list whose first matching error contains the substring `"merge.field_policies' must be a mapping"`.
    - Test `test_validate_profile_rejects_non_string_field_policy_key`: `validate_profile({"merge": {"field_policies": {42: "replace"}}})` returns a non-empty list whose matching error contains the substring `"merge.field_policies key"` and the substring `"must be a string"`.
    - Test `test_validate_profile_rejects_invalid_field_policy_mode`: `validate_profile({"merge": {"field_policies": {"tags": "nuke"}}})` returns a non-empty list whose matching error contains the substring `"merge.field_policies.tags"` and the substring `"nuke"` and the substring `"valid modes"`.
    - Test `test_validate_profile_accepts_all_three_strategies`: for each `strategy` in `{"update", "skip", "replace"}`, `validate_profile({"merge": {"strategy": strategy}})` returns `[]`.
    - Test `test_validate_profile_does_not_raise_on_field_policies_absent`: `validate_profile({"merge": {"strategy": "update"}})` returns `[]` — the new check is conditional, not a required key.
  </behavior>
  <action>
**Edit 1 — Extend `validate_profile` in `graphify/profile.py`.**

Inside the `merge = profile.get("merge")` block (L159-173), AFTER the existing `preserve_fields` check and BEFORE the block ends, insert:

```python
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
```

The accumulator pattern (error list, never raise) is preserved. The `continue` after the non-string-key error avoids double-reporting on a single bad entry. `_VALID_FIELD_POLICY_MODES` is the constant Task 1 added.

**Edit 2 — Add tests to `tests/test_profile.py`.**

Append a new test group `# --- Phase 4 merge.field_policies validation ---` (or a `TestMergeFieldPoliciesValidation` class). Implement exactly the seven tests from the `<behavior>` block:

```python
def test_validate_profile_accepts_empty_field_policies():
    from graphify.profile import validate_profile
    assert validate_profile({"merge": {"field_policies": {}}}) == []

def test_validate_profile_accepts_valid_field_policies():
    from graphify.profile import validate_profile
    p = {"merge": {"field_policies": {
        "tags": "replace",
        "collections": "union",
        "rank": "preserve",
    }}}
    assert validate_profile(p) == []

def test_validate_profile_rejects_non_dict_field_policies():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": ["tags"]}})
    assert any("merge.field_policies' must be a mapping" in e for e in errors)

def test_validate_profile_rejects_non_string_field_policy_key():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": {42: "replace"}}})
    assert any("merge.field_policies key" in e and "must be a string" in e for e in errors)

def test_validate_profile_rejects_invalid_field_policy_mode():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": {"tags": "nuke"}}})
    matched = [e for e in errors if "merge.field_policies.tags" in e]
    assert matched, f"expected tags policy error, got: {errors}"
    assert "'nuke'" in matched[0]
    assert "valid modes" in matched[0]

def test_validate_profile_accepts_all_three_merge_strategies():
    from graphify.profile import validate_profile
    for strategy in ("update", "skip", "replace"):
        assert validate_profile({"merge": {"strategy": strategy}}) == [], \
            f"strategy {strategy} should be accepted"

def test_validate_profile_omits_field_policies_is_ok():
    from graphify.profile import validate_profile
    assert validate_profile({"merge": {"strategy": "update"}}) == []
```

**DO NOT:**
- Raise exceptions from validate_profile (keep the list[str] return contract)
- Check field_policies semantics against ANY key whitelist — users can name any frontmatter key
- Validate the `type(value)` of policy modes beyond the `_VALID_FIELD_POLICY_MODES` set membership test
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && pytest tests/test_profile.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "field_policies" graphify/profile.py` succeeds and appears inside validate_profile (around L170-190 range)
    - `grep -q "_VALID_FIELD_POLICY_MODES" graphify/profile.py` succeeds in two places (definition + validate_profile use site)
    - `grep -c "def test_validate_profile_.*field_polic" tests/test_profile.py` >= 5
    - `grep -c "def test_validate_profile_accepts_all_three_merge_strategies" tests/test_profile.py` == 1
    - `pytest tests/test_profile.py -k field_polic -q` exits 0 with at least 5 tests passing
    - `pytest tests/test_profile.py -k all_three_merge_strategies -q` exits 0
    - `pytest tests/test_profile.py -q` exits 0 (entire test_profile.py green)
  </acceptance_criteria>
  <done>validate_profile flags malformed field_policies (non-dict, non-string key, invalid mode) via the error-list pattern; all three merge strategies are accepted; seven new unit tests cover every branch; test_profile.py remains green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user-written profile.yaml → `_deep_merge` → runtime profile dict | Untrusted YAML input is parsed by PyYAML (`safe_load`) then handed to validate_profile; any schema bypass here affects all of Phase 4 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-04 | Tampering | `merge.field_policies` with a key that later collides with a graphify-owned frontmatter key | accept | Plan 03's dispatcher treats user-supplied policies as authoritative. A malicious profile setting `{"graphify_managed": "preserve"}` could disable the fingerprint-update path, but this is user-local config — trust level is equivalent to CLI flags. Documented in Plan 03's policy dispatcher. |
| T-04-05 | Elevation of Privilege | Unknown field policy mode silently interpreted as `preserve` | mitigate | Task 2 rejects invalid modes with a clear error via validate_profile. Load_profile falls back to defaults on validation errors (existing L120-124 behavior), so a malformed field_policies cannot degrade merge to an unknown mode. |
| T-04-06 | Information Disclosure | field_policies with non-string key crashes downstream dispatcher | mitigate | Task 2 rejects non-string keys in validate_profile before the profile is returned to callers. |
| T-04-07 | Denial of Service | Enormous field_policies dict (e.g., 10,000 entries) | accept | No cap in v1. Field-policy dispatch in Plan 03 is O(1) hash lookup per frontmatter key. Profile size is bounded by user intent — not a realistic DoS vector. |
</threat_model>

<verification>
- `pytest tests/test_profile.py -q` exits 0
- `python -c "from graphify.profile import load_profile, _DEFAULT_PROFILE; assert 'created' in _DEFAULT_PROFILE['merge']['preserve_fields']"` exits 0
- Manual: read profile.py L16-40 and confirm _DEFAULT_PROFILE.merge has exactly three keys: strategy, preserve_fields, field_policies
</verification>

<success_criteria>
- `_DEFAULT_PROFILE.merge.preserve_fields` is `["rank", "mapState", "tags", "created"]` (exact order)
- `_DEFAULT_PROFILE.merge.field_policies` is `{}` (empty default — Plan 03's built-in table wins by default)
- `_VALID_FIELD_POLICY_MODES` constant declared with value `frozenset({"replace", "union", "preserve"})`
- `validate_profile` flags non-dict, non-string-key, and invalid-mode field_policies entries with actionable error strings
- All existing profile tests pass; seven new validation tests added
</success_criteria>

<output>
After completion, create `.planning/phases/04-merge-engine/04-02-SUMMARY.md` documenting the final `_DEFAULT_PROFILE.merge` shape, the `_VALID_FIELD_POLICY_MODES` constant, and the validate_profile extension.
</output>
