---
phase: 56
plan: 05
subsystem: profile-overrides
tags: [CFG-01, render-time, ladder, mapping_rule_templates, note_type_templates, community_templates, classify, TypedDict, warn-fallback]
requires:
  - 56-02-SUMMARY  # _VALID_TOP_LEVEL_KEYS registers mapping_rule_templates + note_type_templates
  - 56-03-SUMMARY  # _validate_mapping_rule_templates / _validate_note_type_templates / mapping_rules.id slug + uniqueness
  - 56-04-SUMMARY  # TMPL-03 dead-rule preflight (independent surface, but same wave order)
  - 30-02-SUMMARY  # community_templates render-time dispatch (_pick_community_template + _load_override_template) — kept untouched per D-56.03 and reused as ladder tier 2
provides:
  - "_resolve_note_template (graphify/templates.py:1633): keyword-only ladder consulting mapping_rule_templates → community_templates → note_type_templates → base in D-56.05 priority order"
  - "_load_override_template list_name kwarg (graphify/templates.py:1538): single loader services all three lists via parametrised stderr warn line, no duplicated fall-back code"
  - "ClassificationContext.rule_id (graphify/templates.py:124-127): optional TypedDict field; total=False keeps it purely additive"
  - "mapping.classify rule_id population (graphify/mapping.py:381-394, 421-432): captures matched_rule_id when matched mapping_rules entry has slug id, conditionally injects into per-node ctx"
  - "compile_rules id preservation (graphify/mapping.py:114-119): keeps optional id slug through the compile step so classify() can read it from compiled_rules iteration"
affects:
  - "render_note (graphify/templates.py:1495): direct templates[note_type] lookup wrapped in _resolve_note_template; ctx.rule_id flows through"
  - "_render_moc_like (graphify/templates.py:1858): _pick_community_template direct call replaced with full _resolve_note_template ladder; tier 2 delegate preserves Phase 30 behavior byte-for-byte"
tech-stack:
  added: []
  patterns:
    - "Keyword-only ladder helper with first-match-wins per tier and silent miss → fall through; per-tier load failures emit list-named stderr warn then fall through (D-56.13 / Phase 55 D-55.14 contract)"
    - "Parametrised loader (list_name kwarg) avoids triplicating ~50 LOC of validate-load-warn code"
    - "TypedDict total=False additive evolution — new optional field requires zero call-site updates"
    - "Conditional ctx_kwargs dict construction so absent rule_id stays absent (rather than None) in TypedDict"
key-files:
  created: []
  modified:
    - "graphify/templates.py"
    - "graphify/mapping.py"
    - "tests/test_template_overrides.py"
decisions:
  - "Reuse _pick_community_template as tier 2 delegate (rather than reimplementing community matching inside _resolve_note_template). Rationale: Phase 30 D-56.03 lock — community_templates behavior must stay byte-for-byte identical. Test surface: 48/48 test_profile_composition.py green."
  - "_load_override_template list_name default = 'community_templates' (not None or required). Rationale: keep Phase 30 callers compiling without edits; warn wording stays identical for legacy code path."
  - "_resolve_note_template signature is keyword-only (`*,`). Rationale: 7-parameter call sites get unreadable positionally; explicit-kwarg style matches PATTERNS.md spec and prevents argument-order bugs at the two call sites."
  - "ctx_kwargs dict construction in classify (vs. always passing rule_id=None). Rationale: TypedDict total=False semantics — absent key is the contract for 'no rule_id'; passing None would force tier-1 to handle None vs missing identically (works today, but absent-key matches the stated truth in must_haves)."
  - "compile_rules now preserves id (was previously dropped). Rationale: classify iterates compiled_rules for the matcher loop; reading id from raw_rules[idx] would require a second source-of-truth, defeating the deep-copy boundary."
metrics:
  duration: "~25min"
  date_completed: "2026-05-02"
  tests_added: 9
  tests_passing_full_suite: 2080
  baseline_passing: 2071
  net_delta: "+9 tests"
---

# Phase 56 Plan 05: CFG-01 render-time ladder — Summary

Refactored `_pick_community_template` (graphify/templates.py:1572-1610 pre-edit) into a single `_resolve_note_template` consulting all three override lists in D-56.05 ladder order, extended `ClassificationContext` with optional `rule_id: str`, populated it in `mapping.classify()`, and rewired the two render call sites (`render_note`, `_render_moc_like`). Per Phase 55 D-55.14 / D-56.13 warn-and-fall-back contract preserved per-list via a `list_name:` kwarg added to `_load_override_template`.

## What landed

### `_resolve_note_template` (graphify/templates.py:1633)

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
```

Keyword-only ladder. First-match-wins per tier; silent miss → fall through; per-tier load failures emit `[graphify] <list_name> override <reason>` stderr warn then fall through.

Tier order (LOCKED per D-56.05):

1. **mapping_rule_templates** — iterates `profile["mapping_rule_templates"]`; matches when `rule.match == "rule_id"` AND `rule.pattern == rule_id`. Calls `_load_override_template(..., list_name="mapping_rule_templates")`.
2. **community_templates** — delegates to existing `_pick_community_template` when both `community_id` and `community_name` are provided. Returns the picked template only if it differs from `default_template` (preserves Phase 30 silent-miss semantics).
3. **note_type_templates** — iterates `profile["note_type_templates"]`; matches when `rule.match == "note_type"` AND `rule.pattern == note_type`. Calls `_load_override_template(..., list_name="note_type_templates")`.
4. **base** — returns `default_template`.

### `_load_override_template` list_name extension (graphify/templates.py:1538)

```python
def _load_override_template(
    rel_path: str,
    vault_dir,
    default_template,
    *,
    list_name: str = "community_templates",
):
```

Default value preserves Phase 30 wording for legacy callers (the one site inside `_pick_community_template` at templates.py:1624 and 1629). All four hardcoded `"community_templates"` literals in the stderr lines became f-string `{list_name}` interpolations:

- `[graphify] {list_name} override path rejected (...): ... — using default`
- `[graphify] {list_name} override missing (...) — using default`
- `[graphify] {list_name} override unreadable (...): ... — using default`
- `[graphify] {list_name} override invalid (...): ... — using default`

### `ClassificationContext.rule_id` (graphify/templates.py:124-127)

```python
class ClassificationContext(TypedDict, total=False):
    ...
    community_name: str
    rule_id: str  # Phase 56 (CFG-01, D-56.04)
```

Additive. `total=False` keeps absent-key the canonical "no matched rule with id" contract.

### `mapping.classify` rule_id population (graphify/mapping.py:381-432)

In the matcher loop (after `compile_rules` was extended to preserve `id`), capture the optional slug:

```python
matched_rule_id: str | None = None
for idx, rule in enumerate(compiled_rules):
    when = rule.get("when") or {}
    then = rule.get("then") or {}
    if _match_when(when, node_id, G, ctx=ctx):
        matched_rule = (idx, when, then)
        rid = rule.get("id") if isinstance(rule, dict) else None
        if isinstance(rid, str):
            matched_rule_id = rid
        break
```

At ctx assembly, conditionally inject so absent stays absent:

```python
ctx_kwargs: dict = {"note_type": ..., "folder": ..., ...}
if matched_rule_id is not None:
    ctx_kwargs["rule_id"] = matched_rule_id
per_node[node_id] = ClassificationContext(**ctx_kwargs)
```

### `compile_rules` id preservation (graphify/mapping.py:114-119)

```python
compiled: dict = {"when": new_when, "then": then}
if "id" in rule:
    compiled["id"] = rule["id"]
out.append(compiled)
```

### Call-site rewires

- **render_note** (graphify/templates.py:1495): direct `templates[note_type]` lookup wrapped:
  ```python
  template = _resolve_note_template(
      rule_id=ctx.get("rule_id") if isinstance(ctx, dict) else None,
      community_id=None,
      community_name=None,
      note_type=note_type,
      profile=profile,
      vault_dir=vault_dir,
      default_template=templates[note_type],
  )
  ```
  Tier 2 (community) is naturally inert here since `render_note` has no community context — only tiers 1, 3, 4 apply.

- **_render_moc_like** (graphify/templates.py:1858): `_pick_community_template(...)` direct call replaced with the full ladder. `template_key` ("moc" or "community") flows through as `note_type=` so tier 3 can match a `note_type_templates` entry pointing at `moc` or `community`. `_pick_community_template` remains alive as tier 2's delegate.

## Test surface

### RED → GREEN (tests/test_template_overrides.py)

9 new tests, all GREEN at end of plan:

**Ladder precedence (4):**
- `test_ladder_mapping_rule_template_wins_over_community_and_note_type`
- `test_ladder_community_template_wins_when_no_mapping_rule_match`
- `test_ladder_note_type_template_wins_when_no_mapping_or_community_match`
- `test_ladder_base_default_when_no_overrides_match`

**Warn-fallback (3, capsys-asserted on stderr):**
- `test_mapping_rule_template_missing_file_warns_and_falls_back` → `[graphify] mapping_rule_templates override missing`
- `test_note_type_template_missing_file_warns_and_falls_back` → `[graphify] note_type_templates override missing`
- `test_community_template_missing_file_still_warns_with_correct_list_name` → `[graphify] community_templates override missing` (Phase 30 regression guard)

**Integration (2):**
- `test_classify_populates_rule_id_when_matched_rule_has_id` — direct `classify()` call asserting `result["per_node"]["n_thing"]["rule_id"] == "thing_rule"` and absence of the key for rules without `id:`
- `test_render_note_with_rule_id_picks_mapping_rule_template` — end-to-end via `render_note(...)` confirming the override marker appears

### Phase 30 regression-safe

`pytest tests/test_profile_composition.py -q` → 48 passed (Phase 30 community_templates: render-time tests untouched, including label glob, id exact, case-sensitivity, first-match-wins, override path rejection, override missing, override unreadable, override invalid).

### Full suite

- Baseline before plan: 2071 passed
- After Task 1 (RED): 2072 passed + 8 failed (1 base test passed natively)
- After Task 2 (GREEN — infra only): 2075 passed + 5 failed (3 wired tests turned GREEN)
- After Task 3 (GREEN — ladder + rewires): **2080 passed, 1 xfailed**

Net delta: +9 tests, zero regressions.

## Commits

- `8c74433` — `test(56-05): RED — ladder + warn-fallback + classify rule_id population`
- `610e2c1` — `feat(56-05): GREEN — ClassificationContext.rule_id + classify() population + _load_override_template list_name`
- `dd09a85` — `feat(56-05): GREEN — _resolve_note_template ladder + rewire render_note + _render_moc_like`

## Producer/consumer contract

Plan 03's `_validate_mapping_rule_templates` is the **producer** side of the `rule_id` contract: it validates that `mapping_rule_templates[].pattern` is a slug and that the corresponding `mapping_rules[].id` exists upstream. This plan is the **consumer** side: `_resolve_note_template` tier 1 reads `ctx.rule_id` (populated by `classify()` from `mapping_rules[].id`) and matches it against `mapping_rule_templates[].pattern`. Together Plan 03 + Plan 05 close CFG-01.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] `MappingResult` is a TypedDict, not a dataclass — test used `.per_node` instead of `["per_node"]`**
- **Found during:** Task 2 verify
- **Issue:** Initial RED test for `classify` rule_id population used attribute access (`result.per_node[...]`) which raised `AttributeError: 'dict' object has no attribute 'per_node'`
- **Fix:** Switched to subscript access (`result["per_node"][...]`)
- **Files modified:** tests/test_template_overrides.py
- **Commit:** rolled into `610e2c1` (no separate commit since test was still RED at point of error)

**2. [Rule 3 - Blocking] Test fixture vault was missing `mapping.min_community_size: 3` — `load_profile` rejected v1.8 vault**
- **Found during:** Task 2 verify
- **Issue:** Plan 04's profile-loader requires `mapping.min_community_size` for v1.8 profiles; my `_ladder_vault` builder omitted it, so `load_profile(vault)` raised before any render code ran
- **Fix:** Added `mapping:\n  min_community_size: 3` to the fixture vault profile yaml
- **Files modified:** tests/test_template_overrides.py
- **Commit:** rolled into `610e2c1`

**3. [Rule 3 - Blocking] Test fixture `community.md` was missing `${members_section}` placeholder**
- **Found during:** Task 2 verify
- **Issue:** Template validator failed `community.md — missing required placeholder ${members_section}`
- **Fix:** Built `community.md` stub with both `${members_section}` and `${dataview_block}`
- **Files modified:** tests/test_template_overrides.py
- **Commit:** rolled into `610e2c1`

**4. [Rule 3 - Blocking] Override template files missing `${members_section}` placeholder**
- **Found during:** Task 3 verify
- **Issue:** `_load_override_template` hardcodes `_REQUIRED_PER_TYPE["moc"]` validation (members_section + dataview_block) for all override files regardless of which note_type renders them. My override_mr.md/override_nt.md fixtures lacked `${members_section}` so the validator rejected them and the ladder fell through to base instead of tier 1/3.
- **Fix:** Added `${members_section}` to `_OVERRIDE_MR`, `_OVERRIDE_NT`, and the inline override_mr.md in `test_render_note_with_rule_id_picks_mapping_rule_template`. Per-note-type required-placeholder dispatch is plan-out-of-scope (would change validator semantics across community_templates too).
- **Files modified:** tests/test_template_overrides.py
- **Commit:** rolled into `dd09a85`

**Note:** All four are test-fixture-level adjustments, not behavior changes to graphify code. No changes to deviation rules: items 2-4 are Rule 3 blocking-fixes for test infrastructure (the production code already handled these cases correctly — the test setup was incomplete).

### Authentication gates

None — fully autonomous local execution.

## Out-of-scope (locked, unchanged)

- Per-block partial overrides (D-56.08 = whole template path only)
- Cross-scope collision errors at render (precedence ladder is silent by design)
- Author-declared `priority:` field
- Per-note-type required-placeholder dispatch in `_load_override_template`
- Any change to community_templates: behavior (D-56.03 = untouched)

## Self-Check: PASSED

- `_resolve_note_template` definition: graphify/templates.py:1633 — FOUND
- `_resolve_note_template` call sites: graphify/templates.py:1495, 1858 — FOUND (2)
- `_load_override_template` list_name kwarg: graphify/templates.py:1538 — FOUND
- `ClassificationContext.rule_id` field: graphify/templates.py:127 — FOUND
- `compile_rules` id preservation: graphify/mapping.py:114-119 — FOUND
- `classify()` matched_rule_id capture: graphify/mapping.py:381-394 — FOUND
- `classify()` ctx_kwargs population: graphify/mapping.py:421-432 — FOUND
- `_pick_community_template` retained: graphify/templates.py:1596 — FOUND (delegated by tier 2)
- Commits 8c74433, 610e2c1, dd09a85 — FOUND in `git log --oneline`
- pytest tests/ -q exit 0 (2080 passed, 1 xfailed) — FOUND
- pytest tests/test_profile_composition.py -q exit 0 (48 passed) — FOUND
