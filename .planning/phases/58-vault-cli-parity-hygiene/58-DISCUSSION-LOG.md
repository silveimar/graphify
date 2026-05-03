# Phase 58: Vault CLI parity & hygiene — Discussion Log

**Date:** 2026-05-03
**Mode:** discuss + --chain (auto-advance to plan-phase after CONTEXT.md)
**Areas selected by user:** All 4 — parity assertion shape, actionable-error contract, three failure scenarios, HYG-01 evidence form

---

## Pre-discussion findings (informed gray-area selection)

- HYG-01 quick-task `260427-rc7-fix-detect-self-ingestion` already shipped 2026-04-27 (SUMMARY.md exists). Surfaced as: HYG-01 is a verify-and-cite task, not a re-fix or waiver.
- `_resolve_output_target()` (`__main__.py:1315`) already centralizes resolution for `run`, `--obsidian`, `doctor`, `elicit`, `import-harness` — VAUX-01 parity rides on this hub.
- `tests/test_doctor.py`, `tests/test_vault_cli.py`, `tests/test_vault_promote.py` exist with reusable `_make_vault()` fixture pattern.

---

## Area 1: Parity assertion shape (VAUX-01)

**Q1:** How should `--vault`/discovery vs `graphify doctor` parity be asserted?
- Options presented: Structured parity helper (Recommended) / Golden text snapshots / Field-by-field assertions inline / You decide
- **Selected:** Structured parity helper

**Q2:** What dimensions must agree between the two surfaces? (multi-select)
- Options presented: Resolved vault path / Precedence source label / Profile path & mode / Diagnostic warnings
- **Selected:** All four
- Follow-up note: Selecting "Diagnostic warnings" implies CLI dispatch and `doctor` must share a warning-emission path (today CLI-only at `__main__.py:1299`). Captured as D-03.

---

## Area 2: Actionable-error contract (VAUX-02)

**Q1:** What shape should vault CLI error messages take?
- Options presented: Stderr text + fix hint (Recommended) / Stable error codes + structured stderr / Stderr text only / JSON error mode behind a flag
- **Selected:** Stderr text + fix hint (mirrors `_FIX_HINTS` in `doctor.py`)

**Q2:** How granular should non-zero exit codes be?
- Options presented: Single non-zero (Recommended) / Per-category exit codes / Match existing graphify convention
- **Selected:** Single non-zero

---

## Area 3: Three failure scenarios (VAUX-02)

**Q1:** What counts as 'unknown vault'? (multi-select)
- Options presented: Path doesn't exist / Path exists but no .obsidian/ marker (Recommended) / Path is a file, not a directory
- **Selected:** All three

**Q2:** What counts as 'ambiguous selection'? (multi-select)
- Options presented: --vault-list with multiple valid roots (Recommended) / Global --vault and per-command --vault disagree / GRAPHIFY_VAULT env vs --vault flag conflict
- **Selected:** All three

**Q3:** What counts as 'dry-run mismatch'?
- Options presented: doctor --dry-run vs actual run resolution (Recommended) / Dry-run output vs actual write paths / Concurrent vault state changed
- **Selected:** doctor --dry-run vs actual run resolution

**Clarifier (behavior change check):** For 'global vs per-command' and 'GRAPHIFY_VAULT vs --vault' — what should the new behavior be?
- Options presented: Keep precedence + assert warning is actionable (Recommended) / Hard error / Hard error only when values differ
- **Selected:** Keep precedence + assert warning is actionable
- Rationale: avoids breaking existing scripted users; Phase 58 stays observation-only on precedence (D-09).

---

## Area 4: HYG-01 evidence form

**Q1:** How to record HYG-01 closure in 58-VERIFICATION.md?
- Options presented: Cite SUMMARY + add regression-lock test (Recommended) / Cite SUMMARY only / Formal waiver
- **Selected:** Cite SUMMARY + add regression-lock test (D-10)

---

## Wrap-up

**Q:** Ready to lock context, or any remaining gray areas?
- Options presented: Ready for context (Recommended) / Explore more gray areas
- **Selected:** Ready for context

---

## Deferred ideas (captured in CONTEXT.md `<deferred>`)

- Per-category exit codes
- `--error-format=json` flag
- Hard error on global-vs-per-command --vault conflict
- Hard error on GRAPHIFY_VAULT vs --vault conflict
- Same-path silent / different-path error middle-ground
- Dry-run preview vs actual write-path mismatch tests

---

## Claude's discretion items

- Module location of parity helper (`output.py` vs new `vault_resolution.py`)
- Helper function name and dict schema
- Regression-lock test name in `tests/test_detect.py`
- Test module placement for ambiguity-warning tests (`test_vault_parity.py` vs `test_vault_cli.py`)
