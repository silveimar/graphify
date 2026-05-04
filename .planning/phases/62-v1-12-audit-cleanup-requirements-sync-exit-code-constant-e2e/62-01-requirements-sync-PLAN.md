---
phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/REQUIREMENTS.md
autonomous: true
requirements:
  - REQUIREMENTS-SYNC-01
must_haves:
  truths:
    - "REQUIREMENTS.md line 20 (E2E-01) is checked: `- [x] **E2E-01**`"
    - "REQUIREMENTS.md line 21 (E2E-02) is checked: `- [x] **E2E-02**`"
    - "No other lines in REQUIREMENTS.md are modified"
    - "Phase 60 VERIFICATION.md remains unchanged"
  artifacts:
    - path: ".planning/REQUIREMENTS.md"
      provides: "Up-to-date checkbox state for v1.12 requirements"
      contains: "- [x] **E2E-01**"
    - path: ".planning/REQUIREMENTS.md"
      provides: "Up-to-date checkbox state for E2E-02"
      contains: "- [x] **E2E-02**"
  key_links:
    - from: ".planning/REQUIREMENTS.md (E2E-01/E2E-02 rows)"
      to: ".planning/phases/60-update-vault-pipeline-integration-e2e/60-VERIFICATION.md"
      via: "audit-trail consistency (status: passed already certifies these)"
      pattern: "\\[x\\] \\*\\*E2E-0[12]\\*\\*"
---

<objective>
Close audit finding REQUIREMENTS-SYNC-01: flip E2E-01 and E2E-02 checkboxes in `.planning/REQUIREMENTS.md` from `[ ]` to `[x]`. Pure documentation drift correction — Phase 60 VERIFICATION.md `status: passed` already certifies satisfaction.

Purpose: Eliminate the audit-identified sync drift between REQUIREMENTS.md and Phase 60's VERIFICATION.md so `/gsd-complete-milestone v1.12` sees a consistent state.
Output: One commit on `.planning/REQUIREMENTS.md` modifying exactly two lines.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/v1.12-MILESTONE-AUDIT.md
@.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-CONTEXT.md
@.planning/REQUIREMENTS.md

<interfaces>
<!-- The two lines to flip are stable references in REQUIREMENTS.md -->
<!-- Current shape (lines 20-21): -->
<!-- - [ ] **E2E-01**: Subprocess-level integration test asserts ... -->
<!-- - [ ] **E2E-02**: Subprocess-level integration test asserts ... -->
<!-- Target shape: -->
<!-- - [x] **E2E-01**: Subprocess-level integration test asserts ... -->
<!-- - [x] **E2E-02**: Subprocess-level integration test asserts ... -->
<!-- Only the box character changes; the body of each line is preserved verbatim. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Flip E2E-01/E2E-02 checkboxes in REQUIREMENTS.md (D-01, D-02)</name>
  <files>.planning/REQUIREMENTS.md</files>
  <action>Per D-01: edit `.planning/REQUIREMENTS.md` and change the leading `- [ ]` token on the E2E-01 and E2E-02 rows (currently lines 20 and 21) to `- [x]`. Use Edit, not sed, and match the full prefix `- [ ] **E2E-01**` → `- [x] **E2E-01**` and `- [ ] **E2E-02**` → `- [x] **E2E-02**`. Do NOT modify any other line in the file. Do NOT renumber requirements. Do NOT touch the body text after the bold ID. Per D-02: this is a pure documentation edit; no code changes accompany it. Commit message body should cite Phase 60 VERIFICATION.md status as the justification (already certifies passed).</action>
  <verify>
    <automated>grep -c "^- \[x\] \*\*E2E-0[12]\*\*" .planning/REQUIREMENTS.md | grep -q "^2$" &amp;&amp; grep -c "^- \[ \] \*\*E2E-0[12]\*\*" .planning/REQUIREMENTS.md | grep -q "^0$"</automated>
  </verify>
  <done>Exactly two lines in REQUIREMENTS.md match `^- \[x\] \*\*E2E-0[12]\*\*` and zero lines match `^- \[ \] \*\*E2E-0[12]\*\*`. No other diff vs the prior commit.</done>
</task>

</tasks>

<verification>
- `git diff --stat .planning/REQUIREMENTS.md` shows 2 insertions, 2 deletions, single file modified.
- `pytest tests/ -q` (sanity check, should remain green; this plan touches no code).
- `.planning/v1.12-MILESTONE-AUDIT.md` is NOT modified by this plan (D-18 closure happens in plan 62-04).
</verification>

<success_criteria>
- E2E-01 and E2E-02 are checked in REQUIREMENTS.md.
- No other REQUIREMENTS.md row, requirement ID, or section ordering changes.
- pytest still green (no code touched).
- Phase 60 VERIFICATION.md untouched.
</success_criteria>

<risk_and_rollback>
- **Risk**: trivial — single-character edits in two lines.
- **Regression guards untouched**: this plan does not modify `tests/test_vault_cwd.py` or `tests/test_harness_import.py`. They will remain green.
- **Rollback**: `git revert` the single commit; the file returns to the pre-edit unchecked state and the audit finding re-opens.
</risk_and_rollback>

<output>
After completion, create `.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-01-SUMMARY.md` documenting the two-line edit and citing Phase 60 VERIFICATION.md as the justification.
</output>
