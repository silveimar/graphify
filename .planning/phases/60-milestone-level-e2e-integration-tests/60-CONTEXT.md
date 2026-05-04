---
phase: 60
phase_name: Milestone-level E2E integration tests
milestone: v1.12
date: 2026-05-03
status: context-gathered
---

# Phase 60 Context — Milestone-level E2E integration tests

## Domain

Two `tmp_path`-scoped subprocess integration tests that close the v1.11 audit gaps for Flow 2 (Phase 55+56 — composition of `note_type_templates` block expansion plus `mapping_rule_templates` override ladder) and Flow 3 (Phase 57+56 — `graphify elicit` sidecar → `graphify update-vault` merge). Pure test infrastructure — no user-facing surface, no production code changes expected (except possibly a shared subprocess helper).

## Requirements (locked by ROADMAP.md / REQUIREMENTS.md)

- **E2E-01** — Subprocess test: profile containing both `note_type_templates` and `mapping_rule_templates` → `graphify update-vault` → notes correctly classified with override ladder applied (block expansion before `${}` substitution, then template ladder resolution). Closes audit Flow 2 gap.
- **E2E-02** — Subprocess test: `graphify elicit` produces sidecar at `artifacts_dir/elicitation.json`, then `graphify update-vault` produces a merged graph whose rendered notes contain visible elicitation contributions. Closes audit Flow 3 gap.
- Both tests must pass on the CI Python 3.10 / 3.12 matrix, run against `tmp_path`, no network calls.

## Decisions

### Test file layout
**One new file: `tests/test_e2e_integration.py` containing both tests.**
- `test_e2e_compose_override_ladder` (E2E-01)
- `test_e2e_elicit_then_update_vault` (E2E-02)
- **Why:** Keeps E2E discoverable as a category; low file count; parallels existing `tests/test_integration.py` naming. Two tests don't justify two files of boilerplate, and folding into `test_integration.py` would conflate Phase 5 in-process pipeline tests with subprocess-level E2E.

### Subprocess helper
**Reuse the `_graphify` pattern from `tests/test_main_flags.py:15`.**
- Returns `subprocess.CompletedProcess`, accepts `cwd` and optional `env`, prepends the worktree root to `PYTHONPATH` so subprocesses pick up local `__main__.py` changes (critical because graphify is also developed in worktrees on this repo).
- **Locally redefine** the helper inside `tests/test_e2e_integration.py` for Phase 60 — do NOT promote to `tests/conftest.py` yet (that's a separate hygiene concern, out of scope).
- **Why:** `_run_cli` from `test_main_cli.py` lacks the PYTHONPATH wiring; on a worktree-based dev workflow it could silently exercise the *installed* graphify instead of the local edits, masking regressions.

### Vault profile fixture strategy
**Inline YAML in the test file (per-test).**
- Each test writes its own `<vault>/.graphify/profile.yaml` to `tmp_path` via a `textwrap.dedent`'d string.
- A small `_write_vault(tmp_path, profile_yaml: str) -> Path` helper local to the file may consolidate the boilerplate.
- **Why:** Two tests with diverging profile shapes (composition+override vs. elicit-aware). Inline keeps the test self-contained and readable top-to-bottom; avoids fixture drift from production default profile semantics; no second-source-of-truth to maintain.

### Assertion granularity
**Structured frontmatter parse + targeted body substrings.**
- Parse YAML frontmatter of rendered notes; assert on specific fields (`type`, `tags`, dataview keys, classified note-type label).
- Use targeted substring checks for body content where required (E2E-02 explicitly needs visible elicitation contributions in note bodies).
- **Avoid** full snapshot files (high churn, every legitimate template tweak forces multi-snapshot updates) and **avoid** substring-only checks (weak signal — wrong template selection can pass if substring happens to appear elsewhere).
- **Why:** Tightest fit between regression-catch strength and maintenance overhead. Frontmatter is the contract surface for ladder resolution; bodies carry the elicitation-visibility signal.

## Implementation notes for downstream agents

- E2E-01 must exercise both `note_type_templates` (block expansion / Phase 55) AND `mapping_rule_templates` (override ladder / Phase 56) in a single profile, then assert that the override ladder runs in the right order: block expansion BEFORE `${}` substitution, then template ladder resolution.
- E2E-02 must invoke two subprocess calls in sequence: `graphify elicit` first (which produces `<artifacts_dir>/elicitation.json`), then `graphify update-vault` (which merges that sidecar). Assert sidecar exists between calls AND that elicitation contributions are visible in the rendered notes after the second call.
- A small synthetic graph (a few code/document nodes, 1–2 communities) is sufficient — these tests are about pipeline plumbing, not graph richness.
- Use `subprocess.run(..., check=False)` and assert `returncode == 0` explicitly so failure messages include captured stderr.

## Canonical refs

Every downstream agent (researcher / planner / executor) MUST read:

- `.planning/ROADMAP.md` — Phase 60 row at line 460 (goal, dependencies, success criteria).
- `.planning/REQUIREMENTS.md` — E2E-01 and E2E-02 entries (locked acceptance criteria).
- `.planning/milestones/v1.11-MILESTONE-AUDIT.md` — lines 30–31 (Flow 2 / Flow 3 audit-gap descriptions, the "why this phase exists" source).
- `tests/test_main_flags.py` — `_graphify` helper pattern (lines 8–35) to mirror in the new E2E file.
- `tests/test_main_cli.py` — `_run_cli` pattern (lines 17–35) for comparison and worktree-PYTHONPATH gotcha.
- `tests/test_integration.py` — Phase-5 in-process integration tests, naming/structure parallel for the new file.
- `graphify/__main__.py` — `update-vault` and `elicit` subcommand handlers (entry points the subprocess tests will hit).

## Code context (reusable assets)

- **Subprocess CLI helpers:** `_graphify` (`tests/test_main_flags.py:15`), `_run_cli` (`tests/test_main_cli.py:29`), `_run_cli_in` (`tests/test_main_cli.py:193`).
- **Graph fixture builders:** `_make_graph` and `_minimal_graph` in `tests/test_integration.py` — adapt for synthetic input feeding `update-vault`.
- **Profile YAML samples:** existing profiles under `graphify/templates/` and tests under `tests/test_profile_composition.py` show valid `note_type_templates` + `mapping_rule_templates` shapes to use as a starting point.
- **Default profile reference:** `graphify/profile.py` `_DEFAULT_PROFILE` for Atlas/-shaped layout expectations.

## Deferred ideas (out of scope for Phase 60)

- Promoting `_graphify` to `tests/conftest.py` as a project-wide fixture so all subprocess tests converge on a single helper. Worth doing later as a hygiene phase.
- Additional E2E flows beyond the two audit gaps (e.g., delta + write-back round-trip subprocess test). v1.13+.
- Snapshot-based regression suite for rendered-note shape — orthogonal investment, not needed for closing Flow 2/3 gaps.
