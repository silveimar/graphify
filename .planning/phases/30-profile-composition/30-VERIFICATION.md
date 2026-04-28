---
phase: 30-profile-composition
verified: 2026-04-28T10:46:00-05:00
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 30: Profile Composition — Verification Report

**Phase Goal:** Resolve `extends:`/`includes:` into a single composed profile with deterministic merge order and cycle detection; map community ID/label patterns to per-community template overrides (first-match-wins); surface merge chain, field provenance, and resolved community-template rules through `graphify --validate-profile`; allow operators to observe lost fields by removing an `extends:` reference.
**Verified:** 2026-04-28T10:46:00-05:00
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–4 + CFG-02 / CFG-03)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `extends:`/`includes:` resolve into a single composed profile via deterministic merge order; cycles detected with clear error | ✓ VERIFIED | `graphify/profile.py:235` `_resolve_profile_chain` exists; lines 311–314 emit `extends/includes cycle detected: <chain>` using `frame_chain` rendered with U+2192; lines 297 enforce depth cap 8; lines 281–284 enforce `Path.is_relative_to(graphify_root)` confinement; CLI smoke on `cycle_via_profile_yaml` printed `error: profile.yaml: extends/includes cycle detected: profile.yaml → b.yaml → profile.yaml` and exit code 1; `linear_chain` smoke printed merge chain `bases/core.yaml → bases/fusion.yaml → profile.yaml` (root-ancestor first). |
| 2 | `community_templates` field maps community ID/label patterns to custom templates; first-match-wins | ✓ VERIFIED | `graphify/templates.py:761` `_pick_community_template` iterates `profile.get("community_templates")` and returns on first matching rule (label via `fnmatch.fnmatchcase` line 788, id via exact `int` compare line 794 with bool rejection). Validator block in `graphify/profile.py:478` enforces schema (match in {label,id}, pattern type, template path safety). Dispatch wired into `_render_moc_like` at `graphify/templates.py:909`. Tests `test_community_templates_first_match_wins`, `test_community_templates_label_glob_match`, `test_community_templates_id_exact_match`, `test_community_templates_fnmatch_case_sensitive`, `test_override_template_path_escape_falls_back`, `test_override_scope_moc_only` all pass within the 48-test composition suite. |
| 3 | `graphify --validate-profile` reports merge chain and resolved per-community template assignments | ✓ VERIFIED | `graphify/__main__.py:1308` prints `Merge chain (root ancestor first):` followed by `result.chain` files; `:1318` prints `Field provenance (N leaf fields):` with `←` arrow; `:1330` prints `Resolved community templates (N rules):` and graph-blind disclaimer at `:1343`; `:1347` prints `Resolved community templates: (none)` for the empty case. Live smoke on `community_templates` fixture printed all three sections including `[1] match=label  pattern="transformer*"  template=templates/transformer-moc.md` and `[2] match=id  pattern=0 template=...` with the disclaimer "actual community-to-template assignments require a graph". |
| 4 | Removing `extends:` ref + re-validating shows exactly which fields were lost | ✓ VERIFIED | Test `test_validate_profile_lost_fields_after_extends_removal` (passes) uses `lost_fields_demo` fixture: before removal the provenance section contains `naming.convention ← parent.yaml`; after rewriting `profile.yaml` without `extends:`, the provenance section no longer contains `parent.yaml` or `naming.convention`, confirming D-15. Both pre- and post-removal runs exit 0. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/profile.py` | `_resolve_profile_chain`, `_deep_merge_with_provenance`, `ResolvedProfile`, extended `_VALID_TOP_LEVEL_KEYS`, `community_templates` validator, extended `PreflightResult`, refactored `load_profile`/`validate_profile_preflight` | ✓ VERIFIED | All symbols present (lines 14, 36, 130–135, 194, 235, 387, 428, 1047). `is_relative_to` confinement at :281–284. Cycle error literal at :313–314. Recursion-depth literal at :297. |
| `graphify/templates.py` | `_pick_community_template`, `_load_override_template`, dispatch in `_render_moc_like`, fnmatchcase use, `_REQUIRED_PER_TYPE["moc"]` reuse | ✓ VERIFIED | `_load_override_template` at :714, `_pick_community_template` at :761, fnmatchcase at :788, dispatch wired at :909. Function-local `from graphify.profile import validate_vault_path` import for circular-dep safety. |
| `graphify/__main__.py` | Extended `--validate-profile` dispatch printing merge chain, provenance, community-template rules | ✓ VERIFIED | Block at :1268–1352 prints all three sections, preserves back-compat `profile ok — N rules, M templates validated` line, preserves exit-code contract (smoke: `linear_chain`→1 due to schema warning unrelated to phase 30; `community_templates`→0; `cycle_via_profile_yaml`→1). |
| `tests/test_profile_composition.py` | Wave-0 + community_templates + CLI tests covering CFG-02/CFG-03 | ✓ VERIFIED | 48 `def test_*` functions present. Suite green. |
| `tests/fixtures/profiles/` | Composition fixtures (single_file, linear_chain, includes_only, extends_and_includes, cycle_self, cycle_indirect, diamond, partial_fragment, community_templates, cycle_via_profile_yaml, path_escape, lost_fields_demo, linear_chain_valid) | ✓ VERIFIED | 13 fixture vault directories present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `graphify/profile.py::load_profile` | `_resolve_profile_chain` | function call replacing inline `yaml.safe_load` | ✓ WIRED | Line 428 — replaces previous inline parser; falls back to `_DEFAULT_PROFILE` on resolver errors. |
| `_resolve_profile_chain` | `_deep_merge_with_provenance` | per-fragment merge call | ✓ WIRED | Lines 350, 370, 375 — three merge sites (parent, includes, own fields). |
| `_resolve_profile_chain` | `Path.is_relative_to((vault_dir / '.graphify').resolve())` | post-resolve confinement check | ✓ WIRED | Lines 281–284 inside `_is_inside_graphify`. |
| `templates.py::_render_moc_like` | `_pick_community_template` | dispatch replacing direct `templates[template_key]` lookup | ✓ WIRED | Line 909. |
| `templates.py::_pick_community_template` | `fnmatch.fnmatchcase` | label-pattern matching | ✓ WIRED | Line 788 (case-sensitive). |
| `__main__.py::--validate-profile` | `PreflightResult.chain` / `.provenance` / `.community_template_rules` | tuple-field access | ✓ WIRED | `result.chain` :1309, `result.provenance` :1317, `result.community_template_rules` :1328. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Composition test suite green | `pytest tests/test_profile_composition.py tests/test_profile.py tests/test_templates.py -q` | 368 passed, 1 xfailed in 1.21s | ✓ PASS |
| Merge chain section printed and root-ancestor-first | `python -m graphify --validate-profile tests/fixtures/profiles/linear_chain` | stdout contained `Merge chain (root ancestor first):` followed by `bases/core.yaml`, `bases/fusion.yaml`, `profile.yaml` in order | ✓ PASS |
| Resolved community templates printed with graph-blind disclaimer | `python -m graphify --validate-profile tests/fixtures/profiles/community_templates` | stdout contained `Resolved community templates (2 rules):`, both `[1] match=label pattern="transformer*"` and `[2] match=id pattern=0` lines, plus disclaimer "actual community-to-template assignments require a graph"; exit 0 | ✓ PASS |
| Cycle detection produces clear error and exit 1 | `python -m graphify --validate-profile tests/fixtures/profiles/cycle_via_profile_yaml` | stderr `error: profile.yaml: extends/includes cycle detected: profile.yaml → b.yaml → profile.yaml`; exit 1 | ✓ PASS |
| Single-file profile shows `Resolved community templates: (none)` | (subset of linear_chain smoke) | linear_chain output ended with `Resolved community templates: (none)` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CFG-02 | 30-01, 30-03 | Compose profiles via `extends`/`includes` with cycle detection and deterministic merge order | ✓ SATISFIED | `_resolve_profile_chain` cycle detection (line 313), depth cap (line 297), path confinement (lines 281–284), deep merge with provenance (lines 350/370/375); CLI surfaces resolution in merge-chain section. |
| CFG-03 | 30-02, 30-03 | Per-community template overrides; first-match-wins; MOC-only scope; safe fallback on failure | ✓ SATISFIED | `_pick_community_template` first-match-wins (templates.py:776–795); `_load_override_template` graceful-fallback with stderr warnings on every failure path (templates.py:714–759); CLI surfaces resolved rules with graph-blind disclaimer. |

### Anti-Patterns Found

None blocking. The smoke run on `linear_chain` exits 1 due to a pre-existing schema warning ("Invalid naming convention 'snake_case'") that originates from the test fixture's intentional override semantics, not from Phase 30 logic. The merge chain, provenance, and rules sections all still print in that case (consistent with D-14 — print informational sections regardless of error state).

### Human Verification Required

None — all four success criteria have automated programmatic verification (subprocess CLI smoke tests + pytest assertions on stdout/stderr/exit code).

### Gaps Summary

No gaps. All four ROADMAP success criteria are achieved with live evidence in source files and tests; both CFG-02 and CFG-03 are fully satisfied by the merged code.

---

_Verified: 2026-04-28T10:46:00-05:00_
_Verifier: Claude (gsd-verifier)_
