---
phase: 59-vault-cwd-aware-cli-default
checker: gsd-plan-checker
date: 2026-05-04
status: issues_found
blockers: 2
warnings: 4
---

# Phase 59 Plan Verification — PLAN-CHECK

**Phase:** 59 — Vault-CWD-aware CLI default
**Plans checked:** 5 (59-01 through 59-05)
**Result:** CHECK FAILED — 2 blockers, 4 warnings

---

## Dimensions Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| 1. Requirement Coverage | PASS | VCWD-01..05 each in exactly one plan's `requirements` |
| 2. Task Completeness | PASS | All tasks have files, action, verify (automated), done |
| 3. Dependency Correctness | PASS | Wave 1→2→3 chain valid; no cycles |
| 4. Key Links Planned | PASS | gate→output.py, gate→branches, doctor→classifier all wired |
| 5. Scope Sanity | PASS | Max 3 tasks/plan; max 2 files/plan |
| 6. Verification Derivation | PASS | must_haves are user-observable truths; artifacts concrete |
| 7. Context Compliance | PASS | D-1..D-5 honored; deferred items absent from plans |
| 7b. Scope Reduction | PASS | No v1/static/stub language for locked decisions |
| 7c. Architectural Tier | SKIP | No Architectural Responsibility Map in RESEARCH.md |
| 8. Nyquist Compliance | PASS with concern | VALIDATION.md exists; all tasks have `<automated>`; feedback < 30s |
| 9. Cross-Plan Data Contracts | WARNING | Wave 2 plans share files; sequential ordering not enforced |
| 10. CLAUDE.md Compliance | PASS | Python 3.10+, from __future__ annotations, pure unit tests |
| 11. Research Resolution | BLOCKER | RESEARCH.md Open Questions lacks `(RESOLVED)` suffix |
| 12. Pattern Compliance | SKIP | No PATTERNS.md for this phase |

---

## BLOCKERS (must fix before execution)

### BLOCKER 1 — [research_resolution] RESEARCH.md Open Questions not marked resolved

**Plan:** (phase-level)
**Dimension:** research_resolution

The RESEARCH.md file has a `## Open Questions` section at line 396 that is NOT suffixed with `(RESOLVED)`. Per Dimension 11, this is a blocking condition. The three questions are:

1. Is `--write-into-vault` a boolean or value flag?
2. Does doctor `[vault-cwd]` sit inside existing section or as its own `=== Vault-CWD Default ===` header?
3. Does `--obsidian-dir` count as explicit routing for VCWD-02/03?

All three questions have "Recommendation:" answers in RESEARCH.md and the plans implement those recommendations consistently. However, the section heading does not carry the `(RESOLVED)` marker required by the gate.

**Fix:** Rename `## Open Questions` to `## Open Questions (RESOLVED)` in 59-RESEARCH.md and confirm each question has a final answer inline. No plan changes needed.

---

### BLOCKER 2 — [task_completeness / pitfall_violation] Module-level `pytest.importorskip("yaml")` in Plan 02 Task 1 code

**Plan:** 59-02
**Task:** Task 1 (RED)
**Dimension:** task_completeness / pitfall_violation

Plan 02's Task 1 action appends the following to `tests/test_vault_cwd.py` at module level:

```python
yaml_required = pytest.importorskip("yaml")  # noqa: F841 — only the with-profile tests need YAML
```

This is a **module-level** `importorskip` call. When PyYAML is absent from the environment, pytest will **skip the entire `tests/test_vault_cwd.py` module**, including:
- `test_gate_runs_for_each_gated_cmd` (Plan 01, no YAML needed)
- `test_gate_skipped_for_readonly_cmds` (Plan 01, no YAML needed)
- `test_refusal_exit_code_and_format` (Plan 03, no YAML needed)
- `test_refusal_message_text` (Plan 03, no YAML needed)

VALIDATION.md Wave 0 requirements explicitly state:
> `pytest.importorskip("yaml")` only in tests that actually load profiles (VCWD-02 with-profile cases)

The comment on the line itself (`— only the with-profile tests need YAML`) contradicts its module-level placement.

Per-test `pytest.importorskip("yaml")` calls already appear correctly inside the individual test functions in Plan 02's action (lines 110, 139, 153), making the module-level call doubly wrong.

**Fix:** Remove the module-level `yaml_required = pytest.importorskip("yaml")` line from Plan 02 Task 1's append code. The per-function `pytest.importorskip("yaml")` calls inside `test_auto_adopt_matches_explicit_vault`, `test_auto_adopt_notice_emitted_once`, and `test_explicit_vault_no_auto_adopt_notice` are the correct pattern and should be retained.

---

## WARNINGS (fix recommended; execution can proceed after blockers are resolved)

### WARNING 1 — [key_links_planned] test_auto_adopt_matches_explicit_vault uses non-gated `doctor` command as routing proxy

**Plan:** 59-02, Task 1 (RED)
**Dimension:** key_links_planned

`test_auto_adopt_matches_explicit_vault` invokes `graphify doctor` (a read-only, non-gated command) to compare resolved output paths between the auto-adopt path and the explicit `--vault $CWD` path. Doctor does not run through `_check_vault_cwd_gate`; the auto-adopt injection (setting `lv_vault = Path.cwd()`) only fires on the 14 gated commands. Running `doctor` from a vault CWD without flags will NOT trigger auto-adopt routing injection, so `auto_path` and `explicit_path` will likely both be `None` or diverge in a way that does not test VCWD-02.

The plan acknowledges this: "CONCRETE TACTIC: Use the run_corpus path with an empty corpus. If executor finds a cleaner harness during GREEN, refactor." The Green task explicitly defers the fix to the executor. However, if the executor does not recognize this as broken, the GREEN test could pass via a false positive (both paths returning `None` or both returning the same default resolution for reasons unrelated to auto-adopt routing).

**Fix:** Replace `graphify("doctor", ...)` with a gated command that terminates quickly without side effects. Options: `graphify("save-result", "--help")` (if the gate runs before argparse), or add a dedicated `--dry-run` introspection flag. Alternatively, assert that `proc_auto.stderr` contains the auto-adopt notice AND that a gated command run returns the same output directory as `--vault $CWD`, using a separate output-dir assertion approach. The note in Plan 02 Task 1 already recommends refactoring during GREEN — this warning flags it as higher-risk than the plan implies.

---

### WARNING 2 — [dependency_correctness / cross_plan_data_contracts] Plans 02, 03, 04 all modify the same two files with no explicit sequencing

**Plans:** 59-02, 59-03, 59-04 (all Wave 2)
**Dimension:** dependency_correctness

All three Wave 2 plans share `files_modified: [tests/test_vault_cwd.py, graphify/__main__.py]` and `depends_on: [59-01]` with no inter-Wave-2 ordering. An executor that runs Wave 2 plans in parallel would produce merge conflicts in both files.

The modifications are additive and at different code sites:
- Plan 02: adds `gate == "auto-adopt"` branch logic + 3 tests
- Plan 03: adds sanitization in refusal branch + 2 tests
- Plan 04: adds `_pop_global_write_into_vault` helper + `_strip_write_into_vault_from_tokens` + 4 tests

Sequential execution within Wave 2 is the only safe path. The GSD executor does not currently guarantee serial execution within a wave when depends_on lists are identical.

**Fix:** Add explicit Wave 2 sub-ordering by updating depends_on:
- Plan 03: `depends_on: [59-01, 59-02]` (or just ensure serial scheduling)
- Plan 04: `depends_on: [59-01, 59-02, 59-03]`

Alternatively, document in each plan's frontmatter that Wave 2 plans MUST execute serially and confirm the executor implements serial-within-wave for shared-file cases.

---

### WARNING 3 — [verification_derivation] test_vault_list_disables_gate does not verify doctor parity for --vault-list

**Plan:** 59-05, Task 1 (RED)
**Dimension:** verification_derivation

Plan 05's `must_haves.truths` states:
> "`--vault-list` argument is treated as explicit routing by both runtime gate and doctor (cross-cutting)."

The test `test_vault_list_disables_gate` only verifies the runtime side:
```python
proc = _graphify("--vault-list", list_file, "run", "--help", cwd=str(bare))
assert "refusing to write" not in proc.stderr
```

There is no assertion that `graphify doctor` invoked with `--vault-list` also reports `[vault-cwd] n/a`. By contrast, `test_env_pin_disables_gate` correctly tests BOTH runtime and doctor parity for `GRAPHIFY_VAULT`.

The `_classify_vault_cwd` implementation in Plan 05 GREEN Step 1 does include `vault_list_file` in the explicit_route boolean, but without a test, this path is untested.

**Fix:** Append to `test_vault_list_disables_gate` a second assertion block:
```python
proc_doc = _graphify("--vault-list", str(list_file), "doctor", cwd=str(bare))
section = " ".join(_doctor_section_lines(proc_doc.stdout))
assert "n/a" in section, f"doctor parity broken with --vault-list: {section!r}"
```

---

### WARNING 4 — [task_completeness] `--help` short-circuit risk leaves gate-coverage tests fragile

**Plans:** 59-01 Task 0, 59-02 Tasks 1 and 2
**Dimension:** task_completeness

Multiple tests use `graphify <cmd> --help` to exercise the dispatch gate. If argparse processes `--help` before the subcommand dispatch ladder (which is common in the `_pop_global_*` → `sys.argv` → argparse flow), the gate call at the top of each `elif cmd ==` branch will never execute. This would cause:
- `test_gate_runs_for_each_gated_cmd` to PASS GREEN falsely (help exits 0 without hitting the gate, but test expects exit 2 — so it would actually still FAIL; however the executor may "fix" it by using a different flag)
- `test_auto_adopt_notice_emitted_once` to find 0 occurrences of the notice on `run --help`

All three plans acknowledge this risk via "Note on `--help` short-circuit" comments and instruct the executor to validate and swap the invocation. The concern is that the fix is left to executor judgment rather than specified in the plan's `<action>` with concrete alternative invocations.

**Fix (advisory):** In Plan 01 Task 0, replace `cmd, "--help"` with an explicit test-safe invocation that is known to reach the dispatch ladder — for example, a vault-pinned no-side-effect flag, or use a test monkeypatch on the gate itself. Alternatively, keep `--help` but add an `if proc.returncode == 0` guard that re-invokes without `--help` to confirm the gate fires.

---

## Coverage Matrix

| Requirement | Plan | Tasks | Status |
|-------------|------|-------|--------|
| VCWD-01 | 59-01 | T0 (infra), T1 (RED), T2 (GREEN) | COVERED |
| VCWD-02 | 59-02 | T1 (RED), T2 (GREEN) | COVERED (with Warning 1) |
| VCWD-03 | 59-03 | T1 (RED), T2 (GREEN) | COVERED |
| VCWD-04 | 59-04 | T1 (RED), T2 (GREEN) | COVERED |
| VCWD-05 | 59-05 | T1 (RED), T2 (GREEN), T3 (REFACTOR) | COVERED (with Warning 3) |

## Wave Structure

| Plan | Wave | Depends On | Files Modified | Status |
|------|------|------------|----------------|--------|
| 59-01 | 1 | [] | tests/test_vault_cwd.py, graphify/__main__.py | Valid |
| 59-02 | 2 | [59-01] | tests/test_vault_cwd.py, graphify/__main__.py | Shared-file conflict (Warning 2) |
| 59-03 | 2 | [59-01] | tests/test_vault_cwd.py, graphify/__main__.py | Shared-file conflict (Warning 2) |
| 59-04 | 2 | [59-01] | tests/test_vault_cwd.py, graphify/__main__.py | Shared-file conflict (Warning 2) |
| 59-05 | 3 | [59-01,59-02,59-03,59-04] | tests/test_vault_cwd.py, graphify/doctor.py | Valid |

## Decision Compliance

| Decision | Verified In | Status |
|----------|-------------|--------|
| D-1: 14 gated + 8 read-only | Plan 01 must_haves, T2 acceptance criteria | PASS |
| D-2: Exact notice text `[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)` | Plan 01 GREEN action line 321 | PASS |
| D-3: `--write-into-vault` global+per-command; silent precedence; suppresses VCWD-03 only | Plan 04 must_haves and T2 action | PASS |
| D-4: Verbatim em-dash refusal text; exit 2; sanitized cwd | Plan 03 T2 action; em-dash verified present | PASS |
| D-5: NEW `[vault-cwd]` section; three outcomes; always shown | Plan 05 must_haves and T2 action | PASS |

## VALIDATION.md Row Coverage

| Row | Test Name | Plan | Covered |
|-----|-----------|------|---------|
| 59-01-W0 | collect-only | 59-01 T0 | YES |
| 59-01-01 | test_gate_runs_for_each_gated_cmd | 59-01 T1/T2 | YES |
| 59-01-02 | test_gate_skipped_for_readonly_cmds | 59-01 T1/T2 | YES |
| 59-02-01 | test_auto_adopt_matches_explicit_vault | 59-02 T1/T2 | YES (Warning 1) |
| 59-02-02 | test_auto_adopt_notice_emitted_once | 59-02 T1/T2 | YES |
| 59-02-03 | test_explicit_vault_no_auto_adopt_notice | 59-02 T1/T2 | YES |
| 59-03-01 | test_refusal_exit_code_and_format | 59-03 T1/T2 | YES |
| 59-03-02 | test_refusal_message_text | 59-03 T1/T2 | YES |
| 59-04-01 | test_write_into_vault_suppresses_refusal | 59-04 T1/T2 | YES |
| 59-04-02 | test_global_write_into_vault_suppresses_refusal | 59-04 T1/T2 | YES |
| 59-04-03 | test_write_into_vault_silent_precedence | 59-04 T1/T2 | YES |
| 59-04-04 | test_write_into_vault_yields_to_profile | 59-04 T1/T2 | YES |
| 59-05-01 | test_doctor_vault_cwd_section_always_shown | 59-05 T1/T2 | YES |
| 59-05-02 | test_doctor_runtime_parity | 59-05 T1/T2 | YES |
| 59-05-03 | test_doctor_three_outcomes | 59-05 T1/T2 | YES |
| 59-X-01 | test_env_pin_disables_gate | 59-05 T1/T2 | YES |
| 59-X-02 | test_vault_list_disables_gate | 59-05 T1/T2 | YES (Warning 3) |
| 59-R-01 | pytest tests/test_vault_cli.py | 59-02, 59-04 verify | YES |
| 59-R-02 | pytest tests/test_e2e_integration.py | 59-05 T3 (full suite) | YES (implicit) |
| 59-R-03 | pytest tests/ full suite | 59-05 T3 | YES |

## Structured Issues (YAML)

```yaml
issues:
  - plan: null
    dimension: research_resolution
    severity: blocker
    description: "RESEARCH.md has '## Open Questions' without '(RESOLVED)' suffix; 3 questions answered in body but not marked resolved"
    file: ".planning/phases/59-vault-cwd-aware-cli-default/59-RESEARCH.md"
    fix_hint: "Rename section to '## Open Questions (RESOLVED)' and verify each question has an inline RESOLVED marker"

  - plan: "59-02"
    dimension: task_completeness
    severity: blocker
    task: 1
    description: "Module-level 'yaml_required = pytest.importorskip(\"yaml\")' in append code will cause entire test_vault_cwd.py module to skip if PyYAML absent, violating VALIDATION.md Wave 0 rule"
    fix_hint: "Remove the module-level yaml_required line from Plan 02 Task 1 append code; per-function pytest.importorskip calls are already present and correct"

  - plan: "59-02"
    dimension: key_links_planned
    severity: warning
    task: 1
    description: "test_auto_adopt_matches_explicit_vault uses 'graphify doctor' (non-gated, no auto-adopt injection) to test routing parity; will likely produce false results"
    fix_hint: "Replace 'graphify doctor' with a gated command (e.g. a gated command with minimal side effects, or monkeypatch the gate); executor must validate during GREEN"

  - plans: ["59-02", "59-03", "59-04"]
    dimension: dependency_correctness
    severity: warning
    description: "Wave 2 plans 02, 03, 04 all share files_modified [tests/test_vault_cwd.py, graphify/__main__.py] with no intra-wave sequencing; parallel execution would produce merge conflicts"
    fix_hint: "Add depends_on: [59-02] to Plan 03 and depends_on: [59-02, 59-03] to Plan 04, OR confirm executor runs Wave 2 serially when file sets overlap"

  - plan: "59-05"
    dimension: verification_derivation
    severity: warning
    task: 1
    description: "test_vault_list_disables_gate only tests runtime gate; must_haves truth claims doctor ALSO treats --vault-list as explicit routing, but no doctor parity assertion is present"
    fix_hint: "Add doctor parity assertion to test_vault_list_disables_gate mirroring the pattern in test_env_pin_disables_gate"

  - plans: ["59-01", "59-02"]
    dimension: task_completeness
    severity: warning
    description: "Multiple tests use 'cmd --help' invocation; if argparse processes --help before dispatch gate, tests may not exercise the gate path at all"
    fix_hint: "Verify gate wiring point vs argparse help processing during Plan 01 GREEN; if help short-circuits, use alternative safe invocation (documented in plan action as deferred to executor judgment)"
```

---

## Recommendation

**2 blockers require revision before execution.**

### Blocker 1 fix (minimal, no plan rewrite needed):
Edit `59-RESEARCH.md` line 396: change `## Open Questions` to `## Open Questions (RESOLVED)` and confirm each question body shows the final answer.

### Blocker 2 fix (plan edit):
Edit `59-02-auto-adopt-PLAN.md` Task 1 action: remove the line `yaml_required = pytest.importorskip("yaml")  # noqa: F841 — only the with-profile tests need YAML` from the append code block. The three per-function `pytest.importorskip("yaml")` calls inside the test functions are correct and should stay.

Both fixes are narrow (single-line edits) and do not require restructuring any plan's logic, tests, or acceptance criteria. After applying these two fixes, re-run this checker before executing.

The 4 warnings are advisory. Warning 2 (Wave 2 shared files) is the highest-risk advisory and is recommended to fix before execution to avoid merge conflicts during parallel wave execution.

---

## RE-CHECK — 2026-05-04 (after commit 8e1b744)

**Three fixes applied and verified:**

### Fix 1 — RESEARCH.md Open Questions heading

Verified: `59-RESEARCH.md` line ~403 now reads `## Open Questions (RESOLVED)`.
Each of the three questions retains its inline answer body.
**BLOCKER 1: CLEARED.**

### Fix 2 — Module-level `yaml_required = pytest.importorskip("yaml")` removed

Verified: `grep -n "yaml_required"` returns no output in `59-02-auto-adopt-PLAN.md`.
The replacement NOTE comment at the insertion point explicitly explains the per-function pattern is correct and warns against module-level placement.
Per-function `pytest.importorskip("yaml")` calls inside the three with-profile tests remain untouched.
**BLOCKER 2: CLEARED.**

### Fix 3 — Wave 2 intra-plan sequencing

Verified:
- `59-03-refusal-PLAN.md` frontmatter: `depends_on: [59-01, 59-02]`
- `59-04-write-into-vault-flag-PLAN.md` frontmatter: `depends_on: [59-01, 59-02, 59-03]`

This enforces a strict serial execution order for the three Wave 2 plans that share `tests/test_vault_cwd.py` and `graphify/__main__.py`, eliminating the merge-conflict risk identified in Warning 2.
**WARNING 2: RESOLVED (promoted from advisory to fixed).**

### Remaining advisories (unchanged from original report)

The following three warnings were not addressed by the fixes and remain advisory. They do not block execution:

- **Warning 1** (59-02 T1): `test_auto_adopt_matches_explicit_vault` uses `graphify doctor` as routing proxy — non-gated command; executor must validate during GREEN and refactor if false-positive risk materialises.
- **Warning 3** (59-05 T1): `test_vault_list_disables_gate` has no doctor-parity assertion for `--vault-list`; the runtime side is tested but the doctor side is not.
- **Warning 4** (59-01/02): `cmd --help` short-circuit risk; gate coverage deferred to executor judgment during GREEN.

None of these introduce a correctness gap that is undetected — each is either annotated in the plan action or covered by the GREEN refactor step.

---

## CHECK PASSED WITH CONCERNS

Both blockers from the original report are cleared. Warning 2 (shared-file merge conflict risk) is also resolved by the dependency serialisation. Three advisory warnings remain; all are scoped to executor judgment during GREEN tasks and carry no phase-level risk.

**Plans are approved for execution. Run `/gsd-execute-phase 59` to proceed.**
