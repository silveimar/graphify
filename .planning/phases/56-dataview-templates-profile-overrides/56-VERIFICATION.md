---
phase: 56-dataview-templates-profile-overrides
verified: 2026-05-02T19:20:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 56: Dataview templates & profile overrides — Verification Report

**Phase Goal:** Allow profiles to declare per-note-type Dataview query templates and scoped template overrides (per-community / per-mapping-rule) that compose with v1.7 `extends:` / `includes:` semantics, with deterministic validation when override precedence is ambiguous.

**Verified:** 2026-05-02T19:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP §Phase 56 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Profile schema supports per-note-type Dataview templates validated at `validate_profile_preflight` (schema + dead-rule checks) — TMPL-03 | VERIFIED | `graphify/profile.py:196` (`_DATAVIEW_QUERY_VARS`), `:199` (`_reachable_note_types`), `:918-953` (4 dead-rule blocks: §1 unknown var, §2 unreachable note_type, §3 empty-after-substitution, §4 cross-chain delegation); 19 dvq tests pass |
| 2 | Composed profiles support scoped template overrides without breaking `extends:`/`includes:` merge semantics; documented in profile schema — CFG-01 | VERIFIED | `_VALID_TOP_LEVEL_KEYS` extended with `mapping_rule_templates` + `note_type_templates`; validators in `profile.py` (Plan 03); render-time ladder `_resolve_note_template` at `templates.py:1633`; `mapping_rules[].id` validation at `mapping.py:892-905`; documented in `docs/PROFILE-CONFIGURATION.md` (511 lines, +178); Phase 30 composition tests still 48/48 |
| 3 | Override-precedence collisions raise deterministic validation errors; collision matrix encoded in tests — CFG-02 | VERIFIED | 4 detectors `_detect_mapping_rule_template_collisions/_detect_pattern_duplicate_collisions/_detect_note_type_template_collisions/_detect_dataview_collisions` at `profile.py:1383-1454`; wired at `:1369-1371` (validate_profile) + `:1816` (validate_profile_preflight); 8 parametric matrix tests in `tests/test_template_overrides.py` (4 classes × pos/neg) |

**Score:** 3/3 roadmap truths verified

### Must-Have Spot-Checks (12 specified items)

| # | Must-have | Status | Evidence |
|---|-----------|--------|----------|
| 1 | D-56.05 ladder order in `_resolve_note_template`: mapping_rule_templates > community_templates > note_type_templates > base | VERIFIED | `templates.py:1660-1710` — Tier 1 mapping_rule_templates (1660-1678), Tier 2 community_templates delegate (1681-1690), Tier 3 note_type_templates (1693-1707), Tier 4 base default (1710) — exact priority order |
| 2 | `${var}` allowlist for dataview_queries dead-rule check is exactly `{community_tag, folder}` (NOT note_type, NOT vault_root) | VERIFIED | `profile.py:196`: `_DATAVIEW_QUERY_VARS: frozenset[str] = frozenset({"community_tag", "folder"})` — comment block at :190-195 explicitly cites callsite walk and rules out note_type/vault_root |
| 3 | Provenance map shape is `dict[str, list[Path]]` | VERIFIED | `profile.py:39, 60, 285, 428, 1454, 1776` — all annotated as `dict[str, list[Path]]`; setdefault().append() write pattern; `paths[-1]` reader convention in `__main__.py` |
| 4 | 4 CFG-02 collision detector functions exist and are wired into `validate_profile_preflight` | VERIFIED | `profile.py:1383, 1406, 1431, 1454` defines 4 `_detect_*` helpers; §1-3 wired in `validate_profile` (`:1369-1371`); §4 wired in `validate_profile_preflight` (`:1816`) |
| 5 | `mapping_rules.id:` is OPTIONAL (rules without id remain valid; backward-compat preserved) | VERIFIED | `mapping.py:892-905`: `rule_id = rule.get("id")` followed by `if rule_id is not None:` guard — all checks gated, absent id is valid |
| 6 | Path-confinement uses substring style (`".." in template`) not Path.parts | VERIFIED | `profile.py:751, 810, 866` — three `elif ".." in template:` substring checks (community_templates + mapping_rule_templates + note_type_templates) — verbatim port |
| 7 | `community_templates:` is UNCHANGED (not deprecated, not modified except validator extension) | VERIFIED | `_pick_community_template` retained at `templates.py:1596`; tier-2 ladder delegates to it; Phase 30 regression suite `tests/test_profile_composition.py` 48/48 green |
| 8 | 8 parametric collision-matrix tests exist in `tests/test_template_overrides.py` (4 classes × positive/negative) | VERIFIED | `grep ^def test_collision_` returns exactly 8 tests covering §1, §2, §3, §4 each with positive + negative case; file contains 17 tests total (8 collision matrix + 4 ladder + 3 warn-fallback + 2 integration) |
| 9 | `docs/PROFILE-CONFIGURATION.md` documents new keys + ladder + collision classes + worked example | VERIFIED | File grew to 511 lines (+178); contains `mapping_rule_templates` (12x), `note_type_templates` (9x), `precedence ladder` (2x), `collision`/`composition chain` (6x), `worked example` (1x), `match: note_type` (3x) |
| 10 | `docs/TEMPLATES.md` has a one-paragraph forward-pointer (NOT duplicated content) | VERIFIED | Line 7 of TEMPLATES.md: single paragraph pointing to PROFILE-CONFIGURATION.md; `grep -c "mapping_rule_templates\|note_type_templates" docs/TEMPLATES.md` = 0 (no duplication) |
| 11 | `docs/MIGRATION_V1_11.md` does NOT exist | VERIFIED | `test -f` returns non-zero — file absent |
| 12 | No `community_templates:` deprecation language anywhere in docs | VERIFIED | `grep -ci "deprecat"` returns 0 in both PROFILE-CONFIGURATION.md and TEMPLATES.md |

**Score:** 12/12 must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/profile.py` | 4 collision detectors + DV dead-rule extensions + new validators + provenance shape | VERIFIED | All present at documented line numbers |
| `graphify/templates.py` | `_resolve_note_template` ladder + `_load_override_template` list_name kwarg + ClassificationContext.rule_id | VERIFIED | Lines 127, 1538, 1633 |
| `graphify/mapping.py` | `mapping_rules.id` validation + classify rule_id population + compile_rules id preservation | VERIFIED | Lines 29 (`_RULE_ID_PATTERN`), 114-119 (compile preserve), 378-388 (capture), 425-436 (ctx_kwargs), 892-905 (id validation) |
| `tests/test_template_overrides.py` | 8 collision tests + ladder + warn-fallback + integration | VERIFIED | 17 tests total, 8 collision_*, 4 ladder_*, 3 warn-fallback, 2 integration |
| `docs/PROFILE-CONFIGURATION.md` | New override-surface sections + ladder + collision matrix + worked example | VERIFIED | 511 lines, all required sections present |
| `docs/TEMPLATES.md` | Single forward-pointer paragraph | VERIFIED | Line 7, no duplication |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `validate_profile_preflight` | `_detect_dataview_collisions` | `errors.extend(...)` at line 1816 | WIRED | grep confirms call exists |
| `validate_profile` | 3 schema-only collision detectors | `errors.extend(...)` at lines 1369-1371 | WIRED | grep confirms 3 calls |
| `render_note` | `_resolve_note_template` | call at templates.py:1495 | WIRED | with `rule_id=ctx.get("rule_id")` plumbing |
| `_render_moc_like` | `_resolve_note_template` | call at templates.py:1858 | WIRED | passes template_key as note_type |
| `_resolve_note_template` tier 1 | `_load_override_template(list_name="mapping_rule_templates")` | direct call | WIRED | line 1674 |
| `_resolve_note_template` tier 2 | `_pick_community_template` | delegate | WIRED | line 1683 (Phase 30 surface preserved) |
| `_resolve_note_template` tier 3 | `_load_override_template(list_name="note_type_templates")` | direct call | WIRED | line 1702 |
| `mapping.classify` | `ClassificationContext.rule_id` | conditional `ctx_kwargs["rule_id"]` | WIRED | mapping.py:435-436; absent-key contract preserved when no id |
| `compile_rules` | id-preserving compile | `if "id" in rule: compiled["id"] = rule["id"]` | WIRED | mapping.py:114-119 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite green | `pytest tests/ -q` | `2080 passed, 1 xfailed, 8 warnings in 70.88s` | PASS |
| Phase 30 regression-safe | `pytest tests/test_profile_composition.py -q` | `48 passed in 1.56s` | PASS |
| No new required deps | `grep dependencies pyproject.toml` | base deps unchanged (networkx, tree-sitter, tree-sitter-python — no PyYAML, no jinja2 added to required) | PASS |
| MIGRATION doc absent | `test -f docs/MIGRATION_V1_11.md` | non-zero exit | PASS |
| No deprecation language in docs | `grep -ci "deprecat" docs/PROFILE-CONFIGURATION.md docs/TEMPLATES.md` | both 0 | PASS |
| Substring path-confinement | `grep -n '".." in template' graphify/profile.py` | 3 hits (lines 751, 810, 866) | PASS |
| 8 collision matrix tests | `grep -c "^def test_collision_" tests/test_template_overrides.py` | 8 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TMPL-03 | 56-04 | Per-note-type Dataview templates (schema + dead-rule preflight) | SATISFIED | 4 dead-rule classes implemented at `profile.py:918-953`; 9 new tests; allowlist locked to `{community_tag, folder}` |
| CFG-01 | 56-03, 56-05 | Scoped template overrides composing with extends:/includes: | SATISFIED | New keys registered + validated; render-time ladder honoring composition; `mapping_rules.id` opt-in slug; documented in PROFILE-CONFIGURATION.md |
| CFG-02 | 56-01, 56-02 | Deterministic validation errors on collision; matrix in tests | SATISFIED | 4 detectors covering all D-56.06 classes; provenance-aware §4 reuses `dict[str, list[Path]]`; 8 parametric matrix tests |

**Note:** REQUIREMENTS.md still lists the three IDs as `- [ ]` (unchecked) — the Phase 56 close-out plan should flip them to `- [x]`. This is a docs-bookkeeping observation, not a goal-blocking gap (REQUIREMENTS.md uses Phase 56 → ID mapping table that already maps the IDs to phase 56).

### Anti-Patterns Found

None of consequence. No TODO/FIXME/PLACEHOLDER added by Phase 56. Validators return `list[str]` and never raise (idiomatic Phase 30/31 pattern preserved). No new required dependencies. Provenance shape change correctly threaded through all 5 producer/consumer sites with `paths[-1]` reader convention preserving CLI output.

### Human Verification Required

None. All claims verifiable via grep + pytest. Documentation content additive and follows existing section style; render-time semantics covered by the 9 new render/integration tests in `tests/test_template_overrides.py` plus full Phase 30 regression suite.

### Gaps Summary

No gaps found. Every must-have was independently verified against the live codebase:

- Ladder order matches D-56.05 exactly (4 tiers in correct priority).
- Allowlist locked to `{community_tag, folder}` per RESEARCH §1 callsite walk; comment block in source explicitly bans drift.
- Provenance shape changed to `dict[str, list[Path]]` at all 5 producer/consumer sites; CLI output preserved via `paths[-1]`.
- All 4 collision detectors exist, wired into the correct entry point (§1-3 in `validate_profile`, §4 in `validate_profile_preflight` because it needs the resolved provenance map).
- `mapping_rules.id:` is purely additive — `if rule_id is not None:` gates all validation; profiles without it remain valid.
- Substring `".." in template` style ported verbatim 3 times (community + 2 new validators).
- `community_templates:` validator + `_pick_community_template` runtime helper untouched; tier-2 ladder delegates to it byte-for-byte.
- 8 parametric collision-matrix tests confirmed by name-grep (4 classes × pos/neg).
- `docs/PROFILE-CONFIGURATION.md` grew by 178 lines covering all six required subsections; `docs/TEMPLATES.md` got a single forward-pointer paragraph; no override semantics duplicated.
- `docs/MIGRATION_V1_11.md` confirmed absent; zero deprecation language anywhere.

Quality gates green: `pytest tests/ -q` reports **2080 passed, 1 xfailed** (matches Plan 05 baseline exactly); `tests/test_profile_composition.py` 48/48 (Phase 30 regression-safe); no new required dependencies in `pyproject.toml`.

---

*Verified: 2026-05-02T19:20:00Z*
*Verifier: Claude (gsd-verifier)*
