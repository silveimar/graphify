# Phase 61: Harness vault-write error format normalization - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate the one-line `[graphify] refusing to write harness import under vault root <path>; pass --allow-vault-write to override` stderr emission at `graphify/__main__.py:2727` (the `import-harness` subcommand's vault-write guard) to the two-line `[graphify] error: <msg>` + `  hint: <fix>` format established in Phase 58 (VAUX-02). The migration uses the existing `_emit_vault_error()` helper at `graphify/output.py:80`. This is the last surviving one-line vault-error outlier from v1.11. Tests asserting the harness refusal stderr are updated to lock the new two-line shape and reject regression to the old one-line form.

</domain>

<decisions>
## Implementation Decisions

### Helper & Call Site
- **D-01:** Call `_emit_vault_error(msg, hint, code=1)` from `graphify/output.py:80` — do not inline a new two-line print. Use `raise _emit_vault_error(...)` so SystemExit propagates the same way `_ensure_vault_root` does (`output.py:95-100`), rather than `print(...); sys.exit(...)`.
- **D-02:** Migrate **only** the refusal at `graphify/__main__.py:2727`. The adjacent `print(f"[graphify] {exc}", file=sys.stderr)` at ~line 2745 (the `ValueError`/`FileNotFoundError` handler in the same `import-harness` block) is **out of scope** — different error class (input validation, not vault-policy refusal) and not covered by HARN-FMT-01.

### Exit Code
- **D-03:** Use `code=1` (the `_emit_vault_error` default) instead of preserving the current `sys.exit(2)`. Rationale: aligns with every other vault-policy refusal normalized in Phase 58 (`_ensure_vault_root` and siblings all use code=1). This is a deliberate behavior change — the refusal is reclassified from an argv-level error (2) to a vault-policy error (1), matching the rest of the family. Phase 58 already established this convention; Phase 61 closes the last outlier on **both** axes (format and exit code).

### Error Text
- **D-04:** `msg` line: `Refusing to write harness import under vault root <artifacts>` (preserves the existing semantic content, dropping the trailing `; pass --allow-vault-write to override` since that becomes the hint).
- **D-05:** `hint` line: `Pass --allow-vault-write to override.` (verbatim from current text, capitalized as a sentence to match the `_ensure_vault_root` hint style at `output.py:97-99`).

### Test Tightening
- **D-06:** Tighten the existing harness tests in `tests/test_harness_import.py` (the test asserting `--allow-vault-write` in stderr around line 144) with **three** assertions:
  1. **Positive:** `"[graphify] error:" in rc.stderr` — locks the new error-line marker.
  2. **Positive:** `"hint:" in rc.stderr` — locks the new hint-line marker.
  3. **Negative:** `"refusing to write harness import" not in rc.stderr` — guarantees the old one-line substring cannot regress.
- **D-07:** Keep the existing `"--allow-vault-write" in rc.stderr` assertion as-is (it is correct under both the old and new shapes — its purpose is to verify the actionable flag name appears, independent of format).
- **D-08:** Test-tightening lives in the same plan as the source migration (TDD: tighten test → red → migrate → green). No separate plan needed for the test side.

### Claude's Discretion
- The **exact label/grouping** of the test changes within `test_harness_import.py` (e.g., whether D-06's three assertions extend the existing `test_import_refuses_vault_without_flag` test or live in a new dedicated test) is left to the planner. Either is acceptable as long as the three assertions exist and run.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement
- `.planning/REQUIREMENTS.md` §HARN-FMT-01 (line 25, mapping at line 68) — the locked requirement for this phase.
- `.planning/ROADMAP.md` §"Phase 61" (lines 505-517) — phase boundary, depends-on, success criteria.

### Format Contract (Phase 58)
- `graphify/output.py:80-89` — `_emit_vault_error(msg, hint, *, code=1)` — the helper to call. Two-line contract: `[graphify] error: {msg}` then `  hint: {hint}`.
- `graphify/output.py:91-104` — `_ensure_vault_root` — the canonical sibling call site. Use as the style model: `raise _emit_vault_error(<msg>, <hint>)`.

### Migration Target
- `graphify/__main__.py:2718-2731` — the `import-harness` vault-write guard block containing the one-line refusal that must be replaced.

### Test Site
- `tests/test_harness_import.py` (the `test_import_refuses_vault_without_flag`-style test around lines 130-145, plus `test_import_accepts_vault_with_explicit_flag` at lines 147+) — assertions to tighten.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_emit_vault_error()`** at `graphify/output.py:80` — already exists, already imported into `__main__.py` indirectly via the `output` module. Returns `SystemExit(code)` so callers `raise` it. No new helper needed.
- **`_ensure_vault_root()`** at `graphify/output.py:91` — exact pattern template: two `raise _emit_vault_error(...)` call sites with msg + hint. Phase 61's call site mirrors this shape line-for-line.

### Established Patterns
- **Two-line vault-error format (Phase 58, VAUX-02):** `[graphify] error: <msg>\n  hint: <fix>` — already the contract for every vault error except the harness refusal. Phase 61 closes the last outlier.
- **`raise SystemExit` over `print + sys.exit`:** `output.py` and `_ensure_vault_root` use the `raise _emit_vault_error(...)` form. Phase 61 should match — the current `print(...); sys.exit(2)` shape is the legacy pattern being retired.
- **Subprocess-stderr testing pattern:** `tests/test_harness_import.py` runs `subprocess.run([sys.executable, "-m", "graphify", "import-harness", ...], capture_output=True, text=True)` and asserts on `rc.stderr` substrings. Phase 61's tightened test follows this exact pattern.

### Integration Points
- The migration is contained: one source-side change at `__main__.py:2727`, one test-side change in `test_harness_import.py`. No public-API surface changes, no skill files affected, no docs touched.

</code_context>

<specifics>
## Specific Ideas

- The `<artifacts>` value in D-04's msg is the resolved vault path computed at `__main__.py:2718` (`artifacts = resolved.artifacts_dir`). It must be interpolated as a string, not the `Path` repr — match the existing f-string style of the one-line version (`f"...vault root {artifacts}..."`).
- HARN-FMT-01 explicitly requires the old one-line variant be **removed entirely from production code**, not just complemented by the new form. D-08's TDD ordering (tighten test first, watch it fail on the old shape, then migrate) operationalizes this guarantee.

</specifics>

<deferred>
## Deferred Ideas

- **Normalizing the adjacent `print(f"[graphify] {exc}", ...)` at __main__.py:~2745** — captured as a candidate follow-up phase. It is a different error class (input validation around `import_harness_path`), not a vault-policy refusal, so it does not belong under HARN-FMT-01. If a future audit identifies more one-line stderr emissions outside the vault-error family, group them into a dedicated "non-vault CLI error format normalization" phase rather than extending Phase 61.

</deferred>

---

*Phase: 61-Harness vault-write error format normalization*
*Context gathered: 2026-05-04*
