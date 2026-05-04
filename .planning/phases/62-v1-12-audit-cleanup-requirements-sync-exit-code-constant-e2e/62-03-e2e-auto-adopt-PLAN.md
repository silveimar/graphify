---
phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e
plan: 03
type: tdd
wave: 2
depends_on: [01]
files_modified:
  - tests/test_e2e_integration.py
autonomous: true
requirements:
  - E2E-AUTO-ADOPT-01
must_haves:
  truths:
    - "tests/test_e2e_integration.py contains a new test named test_e2e_update_vault_auto_adopts_vault_cwd"
    - "The test runs `python -m graphify update-vault` from cwd=<vault> with no --vault and no --write-into-vault"
    - "Preview run exits 0 and emits the auto-adopt stderr notice exactly once"
    - "A migration plan JSON is produced and contains a plan_id"
    - "A second preview from the same cwd produces an identical plan_id (APPLY-DET-01 determinism preserved under auto-adopt)"
    - "A follow-up `update-vault --apply --plan-id <id>` from cwd=<vault> with no --vault exits 0"
    - "Notes are materialized inside the vault per the resolved profile (auto-adopt routes to the vault's artifacts_dir)"
    - "No new requirement IDs are added to REQUIREMENTS.md (D-16)"
    - "tests/test_vault_cwd.py and tests/test_harness_import.py are not modified"
  artifacts:
    - path: "tests/test_e2e_integration.py"
      provides: "Subprocess E2E test exercising the Phase 59 vault-CWD auto-adopt path through preview→apply"
      contains: "test_e2e_update_vault_auto_adopts_vault_cwd"
  key_links:
    - from: "tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd"
      to: "graphify/__main__.py::_check_vault_cwd_gate (auto-adopt branch)"
      via: "subprocess run from cwd=<vault> with no explicit routing flags"
      pattern: "auto-adopt"
    - from: "tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd"
      to: "Phase 60.1 APPLY-DET-01 determinism contract"
      via: "two consecutive previews must yield the same plan_id"
      pattern: "plan_id"
---

<objective>
Close audit finding E2E-AUTO-ADOPT-01 (audit "WARNING 2"): add ONE subprocess-level E2E test in `tests/test_e2e_integration.py` that exercises the Phase 59 vault-CWD auto-adopt path through the full preview→apply pipeline. Re-uses existing Phase 60 helpers; reuses APPLY-DET-01 determinism contract.

Purpose: The existing E2E suite covers Phase 55+56 and 57+56 composition but never runs `update-vault` from inside a vault CWD without `--vault`. This is the integration gap the audit flagged.
Output: One new test function appended to `tests/test_e2e_integration.py`. No production code changes. No new requirement IDs.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
@$HOME/.claude/get-shit-done/references/tdd.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-CONTEXT.md
@.planning/v1.12-MILESTONE-AUDIT.md
@tests/test_e2e_integration.py
@tests/test_vault_cwd.py

<interfaces>
<!-- Existing helpers in tests/test_e2e_integration.py — REUSE, do not duplicate. -->

```python
# tests/test_e2e_integration.py — module-level helpers already in scope.

_BASE_PROFILE_YAML: str  # minimal profile yaml; reuse for the new test.
_OUTPUT_PATH = "Atlas/Sources/Graphify"

def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess: ...
def _write_vault(tmp_path: Path, profile_yaml: str, *, templates=None) -> Path: ...
def _write_corpus(tmp_path: Path) -> Path: ...
def _read_frontmatter(p: Path) -> dict: ...
```

<!--
Note on _run_update_vault_preview_then_apply: the existing helper passes
`--vault <vault>` explicitly, so it CANNOT be reused unchanged for auto-adopt.
The new test must invoke `_graphify(...)` directly from cwd=<vault> with NO
--vault flag, mirroring the helper's two-call shape (preview, then apply).
Do NOT modify the existing helper — inlining the two subprocess calls keeps
the auto-adopt path explicit at the test site.
-->

<!--
Auto-adopt notice shape (graphify/__main__.py:1551-1554):
  "[graphify] auto-adopted vault at {cwd} (profile: .graphify/profile.yaml)"
The new test asserts this string appears exactly once in preview stderr.
-->

<!--
Artifacts location under auto-adopt: same as `--vault <vault>` because the
gate sets lv_vault = Path.cwd() (CONTEXT D-15 + STATE timeline 5133). So the
migration plan JSON lands at <vault>.parent / graphify-out / migrations / *.json
— matching the existing helper's expectation at tests/test_e2e_integration.py:118.
-->
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — add test_e2e_update_vault_auto_adopts_vault_cwd (D-13, D-14, D-15)</name>
  <files>tests/test_e2e_integration.py</files>
  <behavior>
    - **Setup**: build vault via `_write_vault(tmp_path, _BASE_PROFILE_YAML)` and corpus via `_write_corpus(tmp_path)`. Reuse existing fixtures verbatim — do NOT introduce new helpers.
    - **Preview 1** (auto-adopt): `_graphify(["update-vault", "--input", str(corpus)], cwd=vault)` with NO `--vault` and NO `--write-into-vault`.
      - Assert `returncode == 0`.
      - Assert stderr contains `"auto-adopted vault at"` exactly once (`stderr.count("auto-adopted vault at") == 1`).
      - Locate the single migration plan JSON at `vault.parent / "graphify-out" / "migrations"` and parse `plan_id`.
    - **Preview 2** (determinism check, APPLY-DET-01): repeat the same subprocess from `cwd=vault` with no flags after deleting the migration JSON. Assert `returncode == 0` and the new `plan_id` equals the first one (auto-adopt does not perturb determinism).
    - **Apply**: `_graphify(["update-vault", "--input", str(corpus), "--apply", "--plan-id", plan_id], cwd=vault)`. Assert `returncode == 0`.
    - **Materialization**: assert at least one `.md` file is produced under the vault's resolved output root (`vault.parent / "graphify-out"` per existing helper convention). Glob for `*.md` and assert non-empty list.
    - **Negative guard**: assert NO `[graphify] error:` line appears in any stderr (proves we are on the auto-adopt branch, not the VCWD-03 refusal branch).
  </behavior>
  <action>
Per D-13: add the new test at the bottom of `tests/test_e2e_integration.py` (after the existing `test_e2e_elicit_then_update_vault`). Per D-14: name it exactly `test_e2e_update_vault_auto_adopts_vault_cwd`. Per D-15: implement the preview1 → preview2 → apply → materialization assertion shape described in `<behavior>`.

Implementation guidance:
- Reuse `_write_vault`, `_write_corpus`, `_graphify`, `_BASE_PROFILE_YAML`. Do NOT extract helpers from the existing `_run_update_vault_preview_then_apply` (which passes `--vault` explicitly and is therefore not the auto-adopt path) — inline the two subprocess calls instead.
- For preview 2: delete `vault.parent / "graphify-out" / "migrations" / "migration-plan-*.json"` files between the two previews to force the deterministic regeneration check; confirm the regenerated `plan_id` matches the first.
- For materialization: `list((vault.parent / "graphify-out").rglob("*.md"))` should be non-empty; do not over-specify the path under the resolved profile beyond the convention used by the existing helper at line 119.
- Per D-16: do NOT add any new requirement ID to `.planning/REQUIREMENTS.md`. This test extends coverage of existing requirements (VCWD-02 + APPLY-DET-01); REQUIREMENTS.md is touched only by plan 62-01 in this phase.
- Per D-17: if this RED step exposes a real bug (e.g., auto-adopt path is broken end-to-end, or determinism is not preserved under auto-adopt), STOP. Do NOT patch production code in this phase. Route the bug to `/gsd-debug` or a new sub-phase and reopen the audit. Phase 62 is cleanup, not bug-fixing.

Run the new test in isolation: `pytest tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd -x -q`. Expectation: it should PASS on the currently-shipped Phase 59 + Phase 60.1 implementation (auto-adopt + determinism are already wired). If it passes, the RED→GREEN cycle is satisfied as a single TDD step (test added, behavior already correct, test locks the behavior). Commit with message `test(62-03): add E2E coverage for update-vault auto-adopt from vault CWD`.

If the test FAILS for a non-trivial reason (real bug), STOP per D-17 and escalate.
  </action>
  <verify>
    <automated>pytest tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd -x -q</automated>
  </verify>
  <done>
    - New test exists at the bottom of `tests/test_e2e_integration.py`.
    - Test passes on the currently-shipped main branch (auto-adopt + APPLY-DET-01 + preview→apply already work end-to-end).
    - No production-code changes in this plan.
    - REQUIREMENTS.md is not modified (D-16 enforced).
    - tests/test_vault_cwd.py and tests/test_harness_import.py are not modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Full-suite regression sweep + adjacent E2E parity</name>
  <files>(no edits — verification only)</files>
  <action>Run the full E2E module to confirm no shared-fixture interference: `pytest tests/test_e2e_integration.py -q`. Then run the regression guards: `pytest tests/test_vault_cwd.py tests/test_harness_import.py -q`. Then run the full suite: `pytest tests/ -q`. All must be green. If anything regressed, the new test is contaminating shared state — fix the new test (likely cwd or env hygiene), do NOT modify production code per D-17.</action>
  <verify>
    <automated>pytest tests/ -q</automated>
  </verify>
  <done>Full pytest suite green. The two regression-guard test files (test_vault_cwd.py, test_harness_import.py) remain byte-identical to pre-phase versions and pass.</done>
</task>

</tasks>

<verification>
- `grep -c "def test_e2e_update_vault_auto_adopts_vault_cwd" tests/test_e2e_integration.py` returns exactly `1`.
- The new test is the only diff in `tests/test_e2e_integration.py`; no helper or other test is modified.
- `git diff .planning/REQUIREMENTS.md` is empty for this plan (D-16).
- `git diff tests/test_vault_cwd.py tests/test_harness_import.py` is empty for this plan.
- Full pytest suite green on Python 3.10.
</verification>

<success_criteria>
- New test `test_e2e_update_vault_auto_adopts_vault_cwd` exists and passes.
- Auto-adopt path covered end-to-end through preview→apply.
- APPLY-DET-01 determinism preserved under auto-adopt (two previews → identical plan_id).
- No production code modified.
- No new requirement IDs.
- Full suite green.
</success_criteria>

<risk_and_rollback>
- **Risk class**: medium. Subprocess E2E tests can be flaky around cwd, env, and PYTHONPATH; the existing `_graphify` helper already handles those concerns, so reusing it minimizes risk.
- **Regression guards untouched**: `tests/test_vault_cwd.py` and `tests/test_harness_import.py` are NOT modified by this plan. They will remain green; the new test is additive.
- **D-17 stop-condition**: if the RED step reveals a real bug in the auto-adopt → preview→apply flow, the plan halts. The audit findings flagged ONLY a coverage gap, not a defect; if a defect surfaces, route through `/gsd-debug` and re-open the audit.
- **Rollback**: revert the single test-add commit. The audit's WARNING 2 returns to "uncovered" state but the milestone is otherwise unaffected.
</risk_and_rollback>

<output>
After completion, create `.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-03-SUMMARY.md` listing the new test name, the two preview→apply call signatures, and the SHA of the test-add commit (this SHA feeds plan 62-04).
</output>
