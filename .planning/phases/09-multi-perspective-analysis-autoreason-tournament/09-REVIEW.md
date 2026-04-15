---
phase: "09"
status: issues_found
depth: standard
reviewed: 2026-04-14
files_reviewed: 5
blockers: 0
warnings: 3
info: 4
---

# Phase 09: Code Review

## Summary

Phase 09 added `render_analysis_context()` to `analyze.py`, `render_analysis()` to `report.py`, a tournament orchestration section in `skill.md`, and 23 new tests. The Python implementations are well-structured and follow project conventions. One confirmed logic bug exists (field-name mismatch), two additional warnings cover dead code and edge case handling.

## Warnings

### WR-01: Field mismatch — "note" vs "why" in surprise connection dicts
**File:** graphify/analyze.py:279,315 vs graphify/analyze.py:483
`_cross_community_surprises()` builds dicts with `"note"` key; `render_analysis_context()` reads `"why"`. Multi-file corpora unaffected (uses `_cross_file_surprises()` which sets `"why"`). Single-file graphs silently lose surprise explanations.

### WR-02: Dead code branch in convergences section
**File:** graphify/report.py:268-273
`elif len(clean) == len(lens_results)` is unreachable for N>=3 lenses because `len(clean) >= 3` fires first.

### WR-03: Zero-judge fallback can produce Clean verdict with 0 confidence
**File:** graphify/skill.md:1447-1491
If all 3 judges return malformed responses, Borda produces all-zero scores, `max()` returns 'A', and if incumbent said "no issues found" the verdict is Clean with confidence 0.0.

## Info

### IN-01: DOC_EXTENSIONS imported but unused in analyze.py
### IN-02: render_analysis_context() no "None detected" message for empty god nodes
### IN-03: lens name in heading not sanitized (future-proofing)
### IN-04: Fragile line-parsing in test_render_analysis_context_top_n_limits

---

*Reviewed: 2026-04-14 | Depth: standard | Reviewer: Claude (gsd-code-reviewer)*
