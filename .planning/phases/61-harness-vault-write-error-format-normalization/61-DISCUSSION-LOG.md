# Phase 61: Harness vault-write error format normalization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 61-Harness vault-write error format normalization
**Areas discussed:** Exit code, Hint text, Test rigor, Other guards (scope)

---

## Exit code

| Option | Description | Selected |
|--------|-------------|----------|
| code=1 (align w/ Phase 58) | Pass code=1 (the _emit_vault_error default), matching all other vault errors normalized in Phase 58. Treats the refusal as a vault-policy error, not an argv error. Slight behavior change: anyone parsing exit code 2 from this specific path will see 1 instead. | ✓ |
| code=2 (preserve current) | Pass code=2 explicitly to preserve the current exit semantics (originally chosen because --allow-vault-write is an argv-level toggle). Strictly format-only migration — zero behavior change beyond stderr text. | |
| You decide | Defer to Claude's judgment based on the codebase pattern — likely code=1 for consistency unless tests pin code=2. | |

**User's choice:** code=1 (align w/ Phase 58)
**Notes:** Closes the last vault-error outlier on both axes — format AND exit code. Existing harness tests assert `rc.returncode != 0`, not a specific value, so the change is safe.

---

## Hint text

| Option | Description | Selected |
|--------|-------------|----------|
| Pass --allow-vault-write to override | Keep the existing hint verbatim. msg=`Refusing to write harness import under vault root <path>`, hint=`Pass --allow-vault-write to override.` | ✓ |
| Pass --allow-vault-write to confirm | Replace 'override' with 'confirm' — slightly softer phrasing matching how Phase 57's vault-write flag is documented elsewhere. Otherwise identical. | |
| You decide | Pick whichever phrasing best matches the surrounding _emit_vault_error call sites in output.py (e.g., _ensure_vault_root style). | |

**User's choice:** Pass --allow-vault-write to override
**Notes:** Preserves user-facing copy verbatim; only the surrounding format and exit code change.

---

## Test rigor

| Option | Description | Selected |
|--------|-------------|----------|
| Tight: pin both lines | Add explicit assertions: `"[graphify] error:" in stderr` AND `"hint:" in stderr` AND the old substring `"refusing to write harness import"` is NOT in stderr. Locks the contract end-to-end and prevents regression to the one-line form. | ✓ |
| Medium: positive only | Assert the new two-line markers (`[graphify] error:` and `hint:`) are present, but skip the negative assertion that the old string is absent. Simpler test, slightly weaker regression guard. | |
| Loose: keep current | Leave existing assertions untouched (they still pass). Risk: a future regression to the old one-line shape would not be caught by these tests. | |

**User's choice:** Tight: pin both lines
**Notes:** Three-assertion lock (positive on `error:`, positive on `hint:`, negative on the old `refusing to write harness import` substring) operationalizes HARN-FMT-01's "removed entirely from production code" clause.

---

## Other guards (scope)

| Option | Description | Selected |
|--------|-------------|----------|
| Strict scope: only :2727 | Only migrate the vault-write refusal as HARN-FMT-01 specifies. Leave the ValueError/FileNotFoundError print untouched — it's a different error class (input validation, not a vault-policy refusal) and not in REQUIREMENTS.md. Recommended for clean phase boundaries. | ✓ |
| Bundle the sibling print too | Also migrate the adjacent `print(f"[graphify] {exc}", ...)` to the two-line format while we're here. Risk: scope creep beyond HARN-FMT-01; would need a new requirement ID. Better as a follow-up phase. | |

**User's choice:** Strict scope: only :2727
**Notes:** Adjacent ValueError/FileNotFoundError print noted as a deferred idea for a possible future "non-vault CLI error format normalization" phase.

---

## Claude's Discretion

- Exact placement of the three new test assertions inside `tests/test_harness_import.py` (extend the existing `test_import_refuses_vault_without_flag` test vs. add a dedicated test method) is left to the planner.

## Deferred Ideas

- **Normalize the `print(f"[graphify] {exc}", ...)` at `graphify/__main__.py:~2745`** — adjacent ValueError/FileNotFoundError handler in the same `import-harness` block. Different error class (input validation, not vault-policy refusal). Belongs in a future "non-vault CLI error format normalization" phase, not Phase 61.
