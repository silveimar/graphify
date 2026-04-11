---
phase: 05-integration-cli
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/05-integration-cli/05-REVIEW.md
fix_scope: critical_warning
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
tests_result: 872 passed in 3.65s
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-04-11T00:00:00Z
**Source review:** `.planning/phases/05-integration-cli/05-REVIEW.md`
**Iteration:** 1
**Scope:** `critical_warning` (Info findings IN-01..IN-04 deferred)

**Summary:**
- Findings in scope: 2 (WR-01, WR-02)
- Fixed: 2
- Skipped: 0
- Test suite: `pytest tests/ -q` -- 872 passed in 3.65s (no regressions)

## Fixed Issues

### WR-01: `to_obsidian` silently drops per-node/per-community rendering failures

**Files modified:** `graphify/export.py`
**Commit:** `39476f3`
**Applied fix:** Added `import sys` to the module imports and replaced both
silent `except ValueError: continue` branches in `to_obsidian`'s per-node and
per-community render loops with stderr-logging versions. Each skip now emits
`[graphify] to_obsidian: skipping node <id> (<note_type>): <exc>` (or
`... skipping community <cid> ...`) via `print(..., file=sys.stderr)`, matching
the stderr logging pattern used across `profile.py`, `validate.py`, and
`security.py`. Captured the exception via `except ValueError as exc` and
included the message text so CI logs can distinguish "ran on empty graph"
from "100% of nodes dropped due to misconfigured rules".

Note on the recommendation's optional counter / end-of-run summary: deferred.
The per-skip log lines already give grep-able signal, and a counter would
require threading state through the loops without changing the observable
correctness. Can be added in a follow-up if the team wants a one-line summary.

### WR-02: `render_note` / `render_moc` can raise `FileNotFoundError` that is NOT caught

**Files modified:** `graphify/export.py`
**Commit:** `606cb81`
**Applied fix:** Two changes to `to_obsidian`:

1. **Upfront non-directory guard** inserted immediately after `out = Path(output_dir)`
   and before `out.mkdir(parents=True, exist_ok=True)`. When the target path
   exists but is not a directory, raises a clear `ValueError` message
   (`"to_obsidian: output_dir <path> exists but is not a directory"`) instead
   of surfacing `FileExistsError` from `mkdir` or `FileNotFoundError` from the
   downstream `load_templates(vault_dir=out)` call.

2. **Broadened except clauses** in both the per-node and per-community render
   loops from `except ValueError as exc` to
   `except (ValueError, FileNotFoundError) as exc`. This catches the real
   FileNotFoundError windows reviewer flagged (TOCTOU races on `out`,
   templates vanishing mid-run) while still letting genuinely unrecoverable
   `OSError` subclasses (PermissionError, OSError on disk-full, etc.)
   propagate out of `to_obsidian` so the caller sees them. Preserved the
   stderr logging added by WR-01 so both exception kinds are diagnosed
   identically.

The combined change keeps the "validate, report, don't crash" ethos for
recoverable errors but stops short of a blanket `except Exception` swallow
that would hide real bugs.

## Skipped Issues

None — all in-scope warnings were fixed cleanly.

The 4 Info findings (IN-01..IN-04) are intentionally out of scope for this
iteration per `fix_scope: critical_warning`. Summary of deferred items:

- **IN-01:** Pre-validate `folder` strings before constructing `target_path`.
  `_validate_target` already catches escapes downstream; purely a UX/error-
  message polish.
- **IN-02:** `split_rendered_note` re-wraps empty frontmatter into `---\n---`.
  Cosmetic, cannot be triggered by real `render_note` pipeline.
- **IN-03:** `community_labels` injection mutates `mapping_result` dict in
  place. Harmless today; one-word copy is the fix if a future caller needs it.
- **IN-04:** Community-overview notes fall back to `folder_mapping.moc`
  folder. Either add a comment or introduce a dedicated `community` key in
  `_DEFAULT_PROFILE.folder_mapping`.

## Verification

- **Tier 1 (re-read modified file):** Confirmed `import sys`, upfront guard,
  broadened exception tuples, and stderr logging all present in
  `graphify/export.py` lines 1-15, 479-489, 521-536, 557-573.
- **Tier 2 (syntax check):** `python -c "import ast; ast.parse(...)"` on
  `graphify/export.py` returned `ok` after each fix.
- **Full test suite:** `pytest tests/ -q` → **872 passed in 3.65s**. No
  regressions introduced; Phase 1-5 coverage intact.

---

_Fixed: 2026-04-11T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
