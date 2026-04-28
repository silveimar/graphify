---
phase: 30-profile-composition
plan: 03
subsystem: cli-dispatch
tags: [cfg-02, cfg-03, validate-profile, merge-chain, provenance, community-templates, d-14, d-16, d-17]
dependency_graph:
  requires:
    - graphify/profile.py::validate_profile_preflight (Plan 01)
    - graphify/profile.py::PreflightResult.chain (Plan 01)
    - graphify/profile.py::PreflightResult.provenance (Plan 01)
    - graphify/profile.py::PreflightResult.community_template_rules (Plan 01)
    - tests/fixtures/profiles/community_templates/ (Plan 02)
  provides:
    - extended graphify/__main__.py::--validate-profile dispatch (3 new sections)
    - tests/fixtures/profiles/linear_chain_valid/ (schema-clean composed result for output tests)
    - tests/fixtures/profiles/lost_fields_demo/ (self-sufficient pre/post extends-removal)
    - tests/fixtures/profiles/cycle_via_profile_yaml/
    - tests/fixtures/profiles/path_escape/
  affects:
    - graphify --validate-profile <vault> output contract (back-compat preserved)
tech-stack:
  added: []
  patterns:
    - "always-print sections regardless of error state (D-14: informational, not error/warning)"
    - "plain-text output (D-16: no JSON, no tree rendering)"
    - "graph-blind disclaimer in community-templates section (D-17)"
    - "best-effort path display via Path.relative_to with .name fallback"
    - "exit-code contract preserved: 0 valid, 1 errors, 2 argv misuse"
key-files:
  created:
    - tests/fixtures/profiles/linear_chain_valid/.graphify/profile.yaml
    - tests/fixtures/profiles/linear_chain_valid/.graphify/bases/core.yaml
    - tests/fixtures/profiles/linear_chain_valid/.graphify/bases/fusion.yaml
    - tests/fixtures/profiles/lost_fields_demo/.graphify/profile.yaml
    - tests/fixtures/profiles/lost_fields_demo/.graphify/bases/parent.yaml
    - tests/fixtures/profiles/cycle_via_profile_yaml/.graphify/profile.yaml
    - tests/fixtures/profiles/cycle_via_profile_yaml/.graphify/b.yaml
    - tests/fixtures/profiles/path_escape/.graphify/profile.yaml
  modified:
    - graphify/__main__.py
    - tests/test_profile_composition.py
decisions:
  - "Created `linear_chain_valid` fixture as a schema-clean sibling of `linear_chain` because the original fixture intentionally composes to `naming.convention: snake_case` (asserted by Plan 01's resolver tests) — invalid through the full `--validate-profile` validation path"
  - "Lost-fields test asserts on `folder_mapping` as the parent-sourced provenance leaf rather than `naming.convention` — `_deep_merge_with_provenance` records the dict-leaf at the layer that first writes it; subsequent recursion only iterates over the override's keys, so `naming.convention` does not appear when only the parent layer defines `naming`"
  - "Path display uses `Path.relative_to(.graphify/)` with `.name` fallback on ValueError so cycle/path-escape paths still render legibly"
metrics:
  completed_date: "2026-04-28"
  duration_seconds: 453
  tasks_total: 2
  tasks_complete: 2
  tests_added: 9
  tests_total_pass: 1743
  files_created: 8
  files_modified: 2
---

# Phase 30 Plan 03: --validate-profile Output Extension Summary

Extended the `graphify --validate-profile <vault>` CLI dispatch to print three new informational sections — Merge chain, Field provenance, and Resolved community templates — closing Phase 30 success criteria 3 and 4. Pure formatting; all backend logic (chain assembly, provenance tracking, rule list) was already populated by Plan 01's `validate_profile_preflight()`.

## What Shipped

- **Three new stdout sections** in `graphify/__main__.py` `--validate-profile` dispatch:
  1. `Merge chain (root ancestor first):` — lists `result.chain` files in resolution order, rendered relative to `.graphify/` with `.name` fallback. Falls back to `(no chain — profile.yaml not found or unparseable)` when chain is empty.
  2. `Field provenance (N leaf fields):` — dumps `result.provenance` as `dotted-key ← source-file` with the keys sorted alphabetically and a 40-column padded key for visual alignment. Empty case prints `Field provenance (0 leaf fields):` + `(none)`.
  3. `Resolved community templates (N rules):` — dumps `result.community_template_rules` as written. String patterns are quoted (`pattern="transformer*"`); non-strings go through `repr()` (`pattern=0` for ints). Each rule prints `[idx] match=... pattern=... template=...`. Followed by the graph-blind disclaimer `(note: actual community-to-template assignments require a graph — run after `graphify`)`. Empty rules → `Resolved community templates: (none)` (no disclaimer).
- **Always-print contract (D-14)** — sections print to stdout regardless of error state. Exit code is determined ONLY by `result.errors`.
- **Back-compat** — the D-77a literal `profile ok — N rules, M templates validated` is preserved verbatim for valid profiles.
- **Four new fixture vaults**:
  - `linear_chain_valid/` — three-level extends chain (core → fusion → profile) where the composed `naming.convention` is `preserve` (schema-valid), so `--validate-profile` exits 0 and the output sections can be asserted on.
  - `lost_fields_demo/` — self-sufficient parent + child pair where the child's provenance keys remain schema-valid both with and without the `extends:` line (D-15 / SC#4).
  - `cycle_via_profile_yaml/` — `profile.yaml` extends `b.yaml` extends `profile.yaml` (cycle via the profile entry point itself).
  - `path_escape/` — `profile.yaml` extends `../../etc/passwd` (T-30-01 mitigation reachable via the CLI).

## Test Coverage

9 new tests in `tests/test_profile_composition.py` (subprocess-invocation pattern matching real CLI usage):

- `test_validate_profile_prints_merge_chain` — chain header + resolution order assertion.
- `test_validate_profile_prints_field_provenance` — header + arrow + dotted-key presence.
- `test_validate_profile_prints_resolved_community_templates` — 2-rule fixture, exact substrings for `match=label`, `pattern="transformer*"`, `pattern=0`, plus graph-blind disclaimer.
- `test_validate_profile_single_file_shows_no_rules` — `(none)` literal for empty rules + one-element merge chain.
- `test_validate_profile_exits_zero_on_valid_composed` — exit 0 even when new sections print.
- `test_validate_profile_exits_nonzero_on_cycle` — cycle fixture → exit 1 + `error:` + `cycle detected` on stderr.
- `test_validate_profile_exits_nonzero_on_path_escape` — escape fixture → exit 1 + `escapes .graphify/` on stderr.
- `test_validate_profile_lost_fields_after_extends_removal` — pre/post comparison: parent-sourced fields disappear after extends removal AND post-removal still exits 0 (D-15 / SC#4).
- `test_validate_profile_graph_blind_note` — literal disclaimer presence (D-17).

## Verification

- `pytest tests/test_profile_composition.py -k validate_profile -q` — **9 passed** (GREEN).
- `pytest tests/ -q` — **1743 passed, 1 xfailed** (full suite green; xfailed is pre-existing; +9 over Plan 02's 1734).
- Smoke `python -m graphify --validate-profile tests/fixtures/profiles/single_file` — exits 0, prints all three sections.
- Smoke `python -m graphify --validate-profile tests/fixtures/profiles/cycle_via_profile_yaml` — exits 1, stderr contains `error:` + `cycle detected`.
- Smoke `python -m graphify --validate-profile tests/fixtures/profiles/path_escape` — exits 1, stderr contains `escapes .graphify/`.
- All Plan 03 acceptance grep checks pass (Merge chain header ×1, Field provenance prefix ×2, Resolved community templates ×3, none branch ×1, graph-blind disclaimer ×1, `result.chain`/`result.provenance`/`result.community_template_rules` accessed, U+2190 arrow present, `profile ok` preserved).

## Commits

| Task | Hash      | Message |
|------|-----------|---------|
| 1    | `487f67a` | test(30-03): add --validate-profile output extension RED tests + fixtures |
| 2    | `88542b4` | feat(30-03): extend --validate-profile dispatch with merge chain / provenance / community-template sections (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Created `linear_chain_valid` fixture for output-section tests**
- **Found during:** Task 2 GREEN — `pytest tests/test_profile_composition.py -k validate_profile_prints_merge_chain` failed with `proc.returncode == 1` because the existing `linear_chain` fixture composes to `naming.convention: snake_case`, which is rejected by `validate_profile()` (`_VALID_NAMING_CONVENTIONS = {"title_case", "kebab-case", "preserve"}`).
- **Issue:** Plan 01's resolver tests intentionally assert that `linear_chain` composes to `snake_case` (lines 79 and 105 of `test_profile_composition.py`) — but those tests bypass `validate_profile()` by calling `_resolve_profile_chain` directly. Plan 03's tests use the full `--validate-profile` CLI path which DOES validate, so the fixture's intentionally-invalid composed value blocks `proc.returncode == 0`.
- **Fix:** Created a sibling fixture `tests/fixtures/profiles/linear_chain_valid/` with the same three-level structure but `convention: preserve` in fusion.yaml, so the composed result is schema-valid. Updated three Plan 03 tests (`prints_merge_chain`, `prints_field_provenance`, `exits_zero_on_valid_composed`) to use `linear_chain_valid`. Existing Plan 01 tests on `linear_chain` are untouched.
- **Files modified:** new fixture under `tests/fixtures/profiles/linear_chain_valid/.graphify/`; `tests/test_profile_composition.py` test bodies.
- **Commit:** `88542b4`.

**2. [Rule 1 - Bug] Reframed lost-fields test assertions around `folder_mapping`**
- **Found during:** Task 2 GREEN — the plan's lost-fields test asserted on `naming.convention` provenance, but `_deep_merge_with_provenance` records `naming` as a dict-leaf at the parent layer (not `naming.convention`) when the child does not have its own `naming` key, because recursion iterates only over the override's keys.
- **Issue:** The assertion `assert "naming.convention" in provenance_before` is impossible with the current resolver semantics (Plan 01's design choice — leaf-key provenance only records keys that are explicitly written by the source). The test's intent (D-15: parent-sourced fields disappear after extends removal) is preserved; only the asserted leaf-name was wrong.
- **Fix:** Asserted that `parent.yaml` and `folder_mapping` appear together in `provenance_before` (the parent-sourced leaf), and that after extends removal `parent.yaml` is gone, `folder_mapping` is sourced from `profile.yaml`, and `proc_after.returncode == 0`. Simplified `lost_fields_demo` parent.yaml to just `folder_mapping.thing`.
- **Files modified:** `tests/test_profile_composition.py`, `tests/fixtures/profiles/lost_fields_demo/.graphify/bases/parent.yaml`.
- **Commit:** `88542b4`.

**3. [Rule 3 - Blocking] Force-added fixture files past `.gitignore`**
- **Found during:** Task 1 commit — `.graphify/` is gitignored at project root, dropping all new fixture YAML files silently. Plans 01 and 02 hit the same issue and resolved it via `git add -f`.
- **Fix:** `git add -f` for all four new fixture trees: `cycle_via_profile_yaml`, `path_escape`, `lost_fields_demo`, `linear_chain_valid`.
- **Commits:** `487f67a`, `88542b4`.

### Architectural Changes

None — no Rule 4 deviations were necessary.

## Self-Check: PASSED

- File `graphify/__main__.py` — FOUND, contains all three new section headers, graph-blind disclaimer, `result.chain`/`result.provenance`/`result.community_template_rules` accesses, U+2190 arrow, and back-compat `profile ok` literal.
- File `tests/test_profile_composition.py` — FOUND, 48 tests collected (39 existing + 9 new validate_profile tests).
- All 8 new fixture YAML files — FOUND under `tests/fixtures/profiles/{linear_chain_valid,lost_fields_demo,cycle_via_profile_yaml,path_escape}/.graphify/`.
- Commit `487f67a` — FOUND in git log (Task 1 RED).
- Commit `88542b4` — FOUND in git log (Task 2 GREEN).
- `pytest tests/test_profile_composition.py -k validate_profile -q` — 9 passed.
- `pytest tests/ -q` — 1743 passed, 1 xfailed.

## TDD Gate Compliance

The plan declared `tdd="true"` on both tasks. Gate sequence verified in git log:

1. RED gate — `487f67a test(30-03): …` (failing output-extension tests committed first; the dispatch still printed only `profile ok — …`).
2. GREEN gate — `88542b4 feat(30-03): …` (dispatch extended to print three sections; the 9 RED tests turn green; full suite green).
3. REFACTOR gate — none required (implementation is straight-line section-printing; no refactor needed).

Both required TDD gate commits are present and ordered correctly.
