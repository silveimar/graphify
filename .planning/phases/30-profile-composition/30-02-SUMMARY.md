---
phase: 30-profile-composition
plan: 02
subsystem: template-engine
tags: [cfg-03, community-templates, dispatch, fnmatch, fallback, moc-only]
dependency_graph:
  requires:
    - graphify/profile.py::validate_vault_path
    - graphify/profile.py::validate_profile (community_templates schema, Plan 01)
    - graphify/templates.py::_REQUIRED_PER_TYPE
    - graphify/templates.py::validate_template
    - graphify/templates.py::_render_moc_like
  provides:
    - graphify/templates.py::_pick_community_template
    - graphify/templates.py::_load_override_template
    - tests/fixtures/profiles/community_templates/.graphify/ (fixture vault)
  affects:
    - graphify/templates.py::_render_moc_like (dispatch site rewired to call _pick_community_template)
tech-stack:
  added: []
  patterns:
    - "fnmatch.fnmatchcase for portable, case-sensitive label matching (D-11)"
    - "first-match-wins rule iteration with early return (D-13)"
    - "graceful fallback on every failure path with [graphify] community_templates override … stderr warning"
    - "function-local import of validate_vault_path to avoid circular import"
    - "MOC-only scope — non-MOC render_note path is untouched (D-12)"
key-files:
  created:
    - tests/fixtures/profiles/community_templates/.graphify/profile.yaml
    - tests/fixtures/profiles/community_templates/.graphify/templates/transformer-moc.md
    - tests/fixtures/profiles/community_templates/.graphify/templates/big-community-moc.md
    - tests/fixtures/profiles/community_templates/.graphify/templates/invalid-moc.md
  modified:
    - graphify/templates.py
    - tests/test_profile_composition.py
    - tests/test_pyproject.py
decisions:
  - "Function-local import of validate_vault_path inside _load_override_template to dodge circular dep with graphify.profile"
  - "fnmatch added to test_templates_module_is_pure_stdlib allowlist (stdlib, but the existing whitelist did not yet include it)"
  - "Helpers placed immediately above _render_moc_like (single block of CFG-03 code, easy to find)"
  - "MOC-only scope enforced by call-site placement — only _render_moc_like invokes the dispatch; render_note is untouched"
metrics:
  completed_date: "2026-04-28"
  tasks_total: 2
  tasks_complete: 2
  tests_added: 13
  tests_total_pass: 1734
---

# Phase 30 Plan 02: community_templates Runtime Dispatch Summary

Add the runtime dispatch for `community_templates` rules (CFG-03). When `_render_moc_like` selects a template for a community MOC note, the resolved rule list (already validated and exposed by Plan 01) is evaluated first-match-wins. Label rules match via `fnmatch.fnmatchcase` (portable, case-sensitive); id rules require exact int. Any failure (path-escape, missing file, unreadable, invalid placeholders) falls back to the default with a stderr warning. Member nodes are NOT affected — only the MOC dispatch site changes (D-12).

## What Shipped

- **`_pick_community_template(community_id, community_name, profile, vault_dir, default_template)`** in `graphify/templates.py`. Walks `profile["community_templates"]` first-match-wins (D-13). Skips malformed rules silently (matches the validate_profile contract — bad rules are caught at validation time, runtime is permissive). label-rules require `pattern: str` and use `fnmatch.fnmatchcase`. id-rules reject `bool` (R5) and require `pattern == community_id`. Returns the override template on first match, default otherwise.
- **`_load_override_template(rel_path, vault_dir, default_template)`** — confines the override to `<vault_dir>/.graphify/` via `validate_vault_path` (T-30-01 mitigation), checks file existence, reads UTF-8, then validates the loaded text against `_REQUIRED_PER_TYPE["moc"]` using the existing `validate_template` API. On any failure, prints `[graphify] community_templates override …: … — using default` to stderr and returns `default_template`. `validate_vault_path` is imported function-locally to avoid the circular import with `graphify.profile`.
- **One-line dispatch swap in `_render_moc_like`** — replaced `template = templates[template_key]` with `default_template = templates[template_key]; template = _pick_community_template(...)`. No other change in `_render_moc_like` body.
- **Static fixture vault** at `tests/fixtures/profiles/community_templates/.graphify/` with `profile.yaml` (label-glob + id-exact rules) and three templates: `transformer-moc.md` (`OVERRIDE_TEMPLATE_MARKER`), `big-community-moc.md` (`BIG_OVERRIDE_MARKER`), and `invalid-moc.md` (intentionally missing `${label}` so the placeholder-validation fallback path can be exercised).

## Test Coverage

13 new tests in `tests/test_profile_composition.py` covering all CFG-03 truths:

- **Match semantics:** `test_community_templates_label_glob_match`, `test_community_templates_id_exact_match`, `test_community_templates_first_match_wins`, `test_community_templates_no_match_falls_back_to_default`, `test_community_templates_fnmatch_case_sensitive`, `test_community_templates_question_mark_glob`.
- **Schema rejections (locked-in from Plan 01):** `test_community_templates_id_pattern_bool_rejected`, `test_community_templates_label_pattern_int_rejected`, `test_community_templates_unknown_keys_rejected`.
- **Fallback paths:** `test_override_template_path_escape_falls_back` (asserts stderr `[graphify] community_templates override` warning), `test_override_template_missing_file_falls_back`, `test_override_template_invalid_placeholder_falls_back` (greps stderr for `missing required placeholder ${label}`).
- **Scope guard:** `test_override_scope_moc_only` — `render_note(...)` for a `note_type="thing"` node renders the standard thing template (`type: thing` in frontmatter), with neither override marker present, even when the node belongs to a community whose label matches a `community_templates` rule.

## Verification

- `pytest tests/test_profile_composition.py -k "community_templates or override_template or override_scope" -q` — **13 passed** (GREEN).
- `pytest tests/test_profile_composition.py tests/test_templates.py tests/test_profile.py -q` — **all green** (no regression in existing suites).
- `pytest tests/ -q` — **1734 passed, 1 xfailed** (full suite green; xfailed is pre-existing).
- Acceptance grep checks all pass:
  - `grep -c "^def _pick_community_template" graphify/templates.py` → 1
  - `grep -c "^def _load_override_template" graphify/templates.py` → 1
  - `grep -c "fnmatch.fnmatchcase" graphify/templates.py` → 1
  - `grep -c "_pick_community_template(" graphify/templates.py` → 2 (def + call site)
  - `grep -c "from graphify.profile import validate_vault_path" graphify/templates.py` → 1
  - `grep -cE "^    template = templates\[template_key\]$" graphify/templates.py` → 0 (bare line replaced)
  - `grep -c '_REQUIRED_PER_TYPE\["moc"\]' graphify/templates.py` → 1

## Commits

| Task | Hash      | Message |
|------|-----------|---------|
| 1    | `bf34b24` | test(30-02): add community_templates dispatch RED tests + fixture vault |
| 1    | `6456b9d` | test(30-02): add community_templates fixture vault files (force-add past .gitignore) |
| 2    | `4aded03` | feat(30-02): add community_templates runtime dispatch (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Force-added fixture files past project .gitignore**
- **Found during:** Task 1 commit — only `tests/test_profile_composition.py` landed; the four fixture files under `tests/fixtures/profiles/community_templates/.graphify/` were silently dropped because the project `.gitignore` excludes `.graphify/` (a runtime output directory in graphify itself).
- **Issue:** Without the fixture files committed, the dispatch tests would fail in CI even though they pass locally. Plan 01 hit the same problem and resolved it by force-adding; this plan must mirror that behavior.
- **Fix:** Followup commit `6456b9d` force-adds the four fixture files (`git add -f`).
- **Files modified:** `tests/fixtures/profiles/community_templates/.graphify/{profile.yaml, templates/transformer-moc.md, templates/big-community-moc.md, templates/invalid-moc.md}`.
- **Commit:** `6456b9d`.

**2. [Rule 3 - Blocking] Extended `test_templates_module_is_pure_stdlib` allowlist with `fnmatch`**
- **Found during:** Task 2 — full pytest run failed: `AssertionError: graphify/templates.py imports non-stdlib packages: ['fnmatch']`.
- **Issue:** The existing test's allowlist was a hand-curated set of stdlib roots that did not include `fnmatch`. The Plan 30-02 frontmatter explicitly requires `fnmatch.fnmatchcase` as the matching primitive (D-11), and `fnmatch` IS Python stdlib. The test's allowlist must be extended to reflect the new dependency.
- **Fix:** Added `"fnmatch"` to `allowed_stdlib_roots` in `tests/test_pyproject.py` with a comment pointing to CFG-03.
- **Files modified:** `tests/test_pyproject.py`.
- **Commit:** `4aded03` (folded into the GREEN commit alongside the templates.py change since the test failure was caused by that change).

### Architectural Changes

None — no Rule 4 deviations were necessary.

## Self-Check: PASSED

- File `graphify/templates.py` — FOUND, contains `_pick_community_template`, `_load_override_template`, `fnmatch.fnmatchcase`, function-local `from graphify.profile import validate_vault_path`, and the rewired dispatch site.
- File `tests/test_profile_composition.py` — FOUND, 39 tests collected (13 new CFG-03 + 26 from Plan 01).
- Files `tests/fixtures/profiles/community_templates/.graphify/profile.yaml` and the three template files — FOUND.
- Commit `bf34b24` — FOUND in git log (Task 1 RED tests).
- Commit `6456b9d` — FOUND in git log (Task 1 fixture force-add).
- Commit `4aded03` — FOUND in git log (Task 2 GREEN).
- `pytest tests/ -q` — 1734 passed, 1 xfailed.

## TDD Gate Compliance

The plan declared `tdd="true"` on both tasks. Gate sequence verified in git log:

1. RED gate — `bf34b24` (failing dispatch tests committed first; `_pick_community_template` did not exist yet) and `6456b9d` (fixture files needed by RED tests, force-added past .gitignore).
2. GREEN gate — `4aded03` (helpers added + dispatch rewired; the 13 RED tests turn green).
3. REFACTOR gate — none required (implementation already clean; helpers are isolated above `_render_moc_like` and the call site is one line).

Both required TDD gate commits are present and ordered correctly.
