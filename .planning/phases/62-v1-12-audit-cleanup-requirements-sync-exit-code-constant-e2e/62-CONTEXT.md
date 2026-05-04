# Phase 62: v1.12 audit cleanup — REQUIREMENTS sync + exit-code constant + E2E auto-adopt — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/v1.12-MILESTONE-AUDIT.md`)

<domain>
## Phase Boundary

Close the three actionable findings surfaced by the v1.12 milestone audit (`.planning/v1.12-MILESTONE-AUDIT.md`, status `tech_debt`) so the milestone can transition to `/gsd-complete-milestone v1.12`:

1. **REQUIREMENTS-SYNC-01** — Flip the E2E-01 / E2E-02 checkboxes in `.planning/REQUIREMENTS.md` from `[ ]` to `[x]`. Phase 60 VERIFICATION.md status is `passed`; the unchecked rows are documentation drift, not functional gaps. (Audit "Required" item.)
2. **EXIT-CODE-CONST-01** — Resolve the `_emit_vault_error` exit-code divergence between `__main__.py:1557` (VCWD-03 gate refusal, `code=2`) and `__main__.py:2906` (HARN-FMT-01 vault-policy refusal, default `code=1`) by introducing **named exit-code constants** in `graphify/output.py` and replacing the magic numbers at both call sites. Behavior must not change — both sites keep their current exit codes; only legibility improves. (Audit "WARNING 1".)
3. **E2E-AUTO-ADOPT-01** — Add **one** subprocess E2E test that runs `graphify update-vault` from inside a vault CWD without `--vault` and locks the auto-adopt path through preview→apply. This closes the audit's WARNING 2 — the existing E2E suite covers Phases 55+56 and 57+56 but does not exercise the Phase 59 vault-CWD gate via the milestone E2E harness. (Audit "WARNING 2", optional-but-in-scope.)

**Explicitly out of scope** (deferred per audit, not blocking milestone closure):

- Nyquist VALIDATION.md gap-fill for Phases 59 / 59.1 / 60 / 60.1 / 61. The audit defers this to standalone `/gsd-validate-phase` runs; the audit calls these "Optional" and they do not block `/gsd-complete-milestone`.
- SEED-001 / SEED-002 traceability rows (pre-existing from earlier milestones, not introduced by v1.12).
- Any change to vault-error message strings, harness format, or update-vault determinism — those are locked by Phases 58, 60.1, and 61.

</domain>

<decisions>
## Implementation Decisions

### REQUIREMENTS-SYNC-01 (audit "Required")

- **D-01:** Edit `.planning/REQUIREMENTS.md` lines 20-21 only. Change `- [ ] **E2E-01**` → `- [x] **E2E-01**` and `- [ ] **E2E-02**` → `- [x] **E2E-02**`. No other edits to REQUIREMENTS.md in this phase.
- **D-02:** No code changes accompany this edit — it is pure documentation drift correction. Rationale (logged in commit body): Phase 60 VERIFICATION.md `status: passed` already certifies E2E-01/E2E-02 are satisfied; the audit caught the unchecked rows as a sync bug.

### EXIT-CODE-CONST-01 (audit "WARNING 1")

- **D-03:** **Named constants in `graphify/output.py`**, not docstring-only documentation. The audit offered both options ("define a named constant in `graphify/output.py` or document the policy in the helper docstring"); we choose the constant route because (a) it removes the literal `2` at `__main__.py:1557` which is currently un-grepable, (b) it gives downstream exit-code parsers a stable symbol to import, and (c) the docstring on `_emit_vault_error` will reference the constants by name as a side effect.
- **D-04:** Constant names: `EXIT_VAULT_REFUSAL = 1` and `EXIT_VAULT_GATE = 2`, defined as module-level integers in `graphify/output.py` directly above the existing `_emit_vault_error` definition (`output.py:80`). Names chosen to mirror the audit language: "vault refused" (vault-policy, code 1) vs "gate refusal" (argparse-style usage error from the CWD gate, code 2).
- **D-05:** Replace the literal `2` at `__main__.py:1560` (the VCWD-03 gate-refusal site, `_check_vault_cwd_gate`) with `code=EXIT_VAULT_GATE`. The site's existing `from graphify.output import is_obsidian_vault, _emit_vault_error` import (currently at `__main__.py:1535`) extends to add the constant.
- **D-06:** Replace the implicit default at `__main__.py:2906` (HARN-FMT-01 site) by adding an explicit `code=EXIT_VAULT_REFUSAL` argument. Rationale: even though `_emit_vault_error`'s default is `1`, naming the constant at the call site makes the divergence between the two sites obvious to readers. The local import at `__main__.py:2904` extends to add the constant.
- **D-07:** Update `_ensure_vault_root` at `output.py:91` to use `code=EXIT_VAULT_REFUSAL` for both of its `raise _emit_vault_error(...)` calls (`output.py:95` and `output.py:100`). Currently they rely on the implicit default; making them explicit at the same time keeps the policy uniform across all call sites in the family.
- **D-08:** Update `_emit_vault_error`'s default value: change `code: int = 1` → `code: int = EXIT_VAULT_REFUSAL`. The default still equals `1`; this is a presentation change that anchors the default to the constant name.
- **D-09:** Update the `_emit_vault_error` docstring at `output.py:80-89` to reference the two constants by name and explain the policy (vault-policy refusal vs gate refusal). Keep it short — two or three lines added max.
- **D-10:** Update the comment at `__main__.py:1525-1529` (the `_check_vault_cwd_gate` docstring that says "raises SystemExit(2) via _emit_vault_error") to use the constant name.

### EXIT-CODE-CONST-01 — Test strategy

- **D-11:** Add **one** new test in `tests/test_output.py` (or extend an existing helper test there) that imports `EXIT_VAULT_REFUSAL` and `EXIT_VAULT_GATE` from `graphify.output` and asserts their integer values (`1` and `2` respectively). This locks the symbol existence and the wire values so future refactors cannot silently change the exit-code contract.
- **D-12:** **Do not** add new behavioral tests asserting subprocess exit codes — `tests/test_vault_cwd.py` already locks `code=2` for VCWD-03, and `tests/test_harness_import.py` already locks `code=1` for HARN-FMT-01 (via the Phase 61 D-03 contract). Both should keep passing unchanged after this phase. If either suite breaks, the constant wiring is wrong.

### E2E-AUTO-ADOPT-01 (audit "WARNING 2")

- **D-13:** Add the new E2E test in `tests/test_e2e_integration.py` (the existing milestone-level E2E module from Phase 60), not in `tests/test_vault_cwd.py`. Rationale: the audit's WARNING 2 frames this as an *E2E suite scope* gap, and the new test must exercise the full preview→apply pipeline, which is what `test_e2e_integration.py` is structured for.
- **D-14:** Test name: `test_e2e_update_vault_auto_adopts_vault_cwd`.
- **D-15:** Test shape:
  1. Build a tiny corpus + temp vault directory with `.obsidian/` marker (reuse the helpers `tests/test_e2e_integration.py` already uses for vault setup; no new fixtures needed).
  2. `subprocess.run([sys.executable, "-m", "graphify", "update-vault", "--from", <corpus>, ...])` from `cwd=<vault>` with **no** `--vault` flag and **no** `--write-into-vault` flag.
  3. Assert: preview run exits 0, emits the auto-adopt notice once, and produces a `plan_id`.
  4. Assert: a follow-up `update-vault --apply --plan-id <id>` (also from `cwd=<vault>`, also no `--vault`) exits 0 and writes notes under `<vault>/.graphify/...` per the resolved profile.
  5. Assert: the `plan_id` is identical across two consecutive previews (re-uses the APPLY-DET-01 determinism contract — auto-adopt must not break determinism).
- **D-16:** **Do not** add a new requirement ID to `.planning/REQUIREMENTS.md` for this E2E test. The audit calls it a follow-up to Phase 60's E2E-01/E2E-02; we extend coverage of the existing requirement family (auto-adopt is already required by VCWD-02, and APPLY-DET-01 is already required for determinism). The new test merely closes the audit-identified coverage gap inside the existing requirement set.
- **D-17:** If the new E2E test exposes a real bug in the auto-adopt → preview→apply path, **stop the phase** and route the bug fix through `/gsd-debug` or a new sub-phase. Phase 62 is cleanup, not bug-fixing — a real bug in a previously-shipped feature is out of scope and must be tracked separately so the audit signal stays clean.

### Audit document update

- **D-18:** After all three items land, append a "Closure" section at the bottom of `.planning/v1.12-MILESTONE-AUDIT.md` listing the Phase 62 commit SHAs that closed each tech-debt item. Do **not** modify the original audit body or the YAML frontmatter — append-only, so the audit remains a faithful snapshot of the moment it was taken.

### Claude's Discretion

- Whether D-11's symbol-existence test extends an existing test in `tests/test_output.py` or lives as a new top-level test (e.g., `test_emit_vault_error_exit_code_constants`) — planner's call. Either is acceptable as long as both constant values are asserted.
- The exact phrasing of the docstring update at D-09 (one sentence vs two, prose vs bullet list). Keep it under ~4 lines.
- Whether D-15's vault setup helper is extracted into a shared fixture or inlined in the new test — depends on what already exists in `tests/test_e2e_integration.py`. Don't refactor existing tests just to share a fixture; add what's needed and stop.
- Plan splitting: REQUIREMENTS-SYNC-01 is trivial (one edit, no tests) and could ride alongside EXIT-CODE-CONST-01 in a single plan, or stand alone. E2E-AUTO-ADOPT-01 is heavier and likely warrants its own plan. Final partitioning is the planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit (the PRD)
- `.planning/v1.12-MILESTONE-AUDIT.md` — the audit document this phase closes. Status `tech_debt`, lists 3 actionable items + deferred Nyquist gap-fill. Phase 62 must reference audit findings by line number when commit messages cite them.

### Requirement source
- `.planning/REQUIREMENTS.md` lines 20-21 — the E2E-01 / E2E-02 rows to flip from `[ ]` to `[x]` (REQUIREMENTS-SYNC-01).

### Exit-code constant work
- `graphify/output.py:80-89` — `_emit_vault_error(msg, hint, *, code: int = 1)`. Add module-level constants `EXIT_VAULT_REFUSAL` / `EXIT_VAULT_GATE` directly above this function.
- `graphify/output.py:91-104` — `_ensure_vault_root` — both `raise _emit_vault_error(...)` sites. Update to pass `code=EXIT_VAULT_REFUSAL` explicitly.
- `graphify/__main__.py:1525-1560` — `_check_vault_cwd_gate` (VCWD-03 site). Update `code=2` → `code=EXIT_VAULT_GATE` and refresh the docstring at lines 1525-1529.
- `graphify/__main__.py:2900-2910` — harness `import-harness` vault-write guard (HARN-FMT-01 site). Add explicit `code=EXIT_VAULT_REFUSAL`.

### E2E test home
- `tests/test_e2e_integration.py` — Phase 60's milestone E2E module. New test `test_e2e_update_vault_auto_adopts_vault_cwd` lands here, reusing existing vault-setup helpers if any.
- `tests/test_vault_cwd.py` — existing dedicated subprocess test for VCWD gate behavior. **Do not** modify; the new E2E test complements it, does not replace it.
- `tests/test_harness_import.py` — existing dedicated subprocess test for HARN-FMT-01. **Do not** modify; the explicit `code=EXIT_VAULT_REFUSAL` change is behavior-preserving.

### Prior-phase contracts that must not regress
- Phase 59 VERIFICATION.md (`.planning/phases/59-vault-cwd-aware-cli-default/59-VERIFICATION.md`) — VCWD-01..05 must remain `passed`.
- Phase 60 VERIFICATION.md — E2E-01 / E2E-02 must remain `passed`.
- Phase 61 D-03 (in `.planning/phases/61-harness-vault-write-error-format-normalization/61-CONTEXT.md`) — locks the harness-side exit-code = 1 decision. Phase 62 preserves it; constants name the policy, they do not change it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_emit_vault_error()` — already takes a `code` keyword argument. No signature change beyond switching the default literal `1` to the constant `EXIT_VAULT_REFUSAL`.
- `tests/test_e2e_integration.py` — already has subprocess-based preview→apply scaffolding from Phase 60 / 60.1. The new auto-adopt E2E test follows the same shape.

### Established Patterns
- **`raise _emit_vault_error(...)`** — every vault-error call site uses this form. Phase 62 does not introduce new call sites; it only retro-fits constants to the four existing ones.
- **Two consecutive previews must produce identical `plan_id`** — APPLY-DET-01's determinism contract from Phase 60.1. The new E2E test asserts this property under auto-adopt as well, locking that auto-adopt does not perturb the determinism guarantee.
- **TDD where it pays** — D-11 (constant-existence test) and D-15 (E2E auto-adopt test) are RED-first candidates. D-01 (REQUIREMENTS.md checkbox) is a doc edit and does not need a test; D-03..D-10 (exit-code wiring) are mechanical refactors guarded by the already-passing VCWD/HARN test suites.

### Integration Points
- **No public API change.** `_emit_vault_error`'s signature is preserved; the new constants are additive exports from `graphify.output`. Skill files, MCP server, and CLI surface are all unaffected.
- **No skill-version bump.** Phase 62 is internal cleanup — `pyproject.toml` version, MCP `server.json`, and `.graphify_version` stamps are untouched.

</code_context>

<specifics>
## Specific Ideas

- **Commit granularity:** REQUIREMENTS-SYNC-01 should be a single small commit at the start of the phase (`docs(62): sync REQUIREMENTS.md E2E-01/E2E-02 checkboxes`) so the audit-identified drift gets closed before any code changes ship. This matches the audit's "Required" framing.
- **Audit-trail update (D-18)** lands as the final commit of the phase, after all three items are merged, so the closure section can cite real SHAs.
- **Plan ordering recommendation (planner's call):**
  1. Plan 62-01: REQUIREMENTS-SYNC-01 (one-line edit + commit).
  2. Plan 62-02: EXIT-CODE-CONST-01 (constants + 4 call-site updates + 1 unit test).
  3. Plan 62-03: E2E-AUTO-ADOPT-01 (one new E2E test).
  4. Plan 62-04: Audit closure section (single doc edit citing prior 3 commit SHAs).
  Could also be 3 plans if 62-01 is folded into 62-02. Planner decides.

</specifics>

<deferred>
## Deferred Ideas

- **Nyquist VALIDATION.md gap-fill** for Phases 59 / 59.1 / 60 / 60.1 / 61. The audit lists these as "Optional" and explicitly does not require them for milestone closure. They are tracked under the audit's deferred list and remain available via standalone `/gsd-validate-phase <N>` runs.
- **SEED-001 / SEED-002 traceability rows.** Pre-existing audit signal from earlier milestones; not introduced by v1.12; not in scope here.
- **Adjacent `print(f"[graphify] {exc}", ...)` at `__main__.py:~2745`.** Already deferred by Phase 61 (different error class — input validation, not vault-policy refusal). Re-deferred here.
- **A second E2E flow for the harness vault-write refusal (HARN-FMT-01)** — the audit lists this as a possible extension, but only the auto-adopt path is explicitly scoped. If a follow-up E2E expansion is desired, route through a new phase.

</deferred>

---

*Phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e*
*Context gathered: 2026-05-04 via PRD Express Path (`.planning/v1.12-MILESTONE-AUDIT.md`)*
