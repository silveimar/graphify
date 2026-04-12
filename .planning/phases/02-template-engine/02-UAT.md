---
status: complete
phase: 02-template-engine
source:
  - 02-01-SUMMARY.md
  - 02-02-SUMMARY.md
  - 02-03-SUMMARY.md
  - 02-04-SUMMARY.md
started: 2026-04-11T00:00:00Z
updated: 2026-04-11T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Package import smoke test
expected: From a Python shell, `from graphify import render_note, render_moc, render_community_overview, load_templates, validate_template, resolve_filename` succeeds with no ImportError. Lazy map resolves all six names.
result: pass

### 2. render_note() produces a complete non-MOC note
expected: Calling `render_note("n_transformer", G, profile, "thing", ctx)` on a 3-node graph returns `(filename, text)` where text has proper YAML frontmatter, H1, Wayfinder/Connections/Metadata callouts, no unsubstituted `${...}` tokens.
result: pass

### 3. render_moc() groups members by locked order
expected: render_moc output has `> [!info] Things` callout before `> [!info] Sources` callout, empty Statements/People groups omitted entirely.
result: pass

### 4. Dataview block uses two-phase substitution
expected: render_moc output contains ` ```dataview ` fence with `${community_tag}` and `${folder}` substituted, no residual tokens, user `${label}` preserved.
result: pass

### 5. Wikilink label injection is defused (CR-01 + UAT-05 follow-up)
expected: Alias portion sanitizes `]]` → `] ]`, `|` → `-`, `\n`/`\r`/`\t`/C0 controls → space. Filename target portion strips `\n`/`\r`/`\t`/C0 controls so Obsidian's wikilink target parser never sees a literal control character.
result: pass
resolution: "Initial run found the alias side already safe (CR-01 iteration-1 fix) but the filename side leaked \\n/\\r/\\t via safe_filename(). Fixed inline in commit 7b5c228 by (1) extending safe_filename()'s illegal-char regex to strip \\x00-\\x1f, \\x7f, \\u0085, \\u2028, \\u2029, and (2) adding _WIKILINK_ALIAS_CONTROL_RE as a second pass in _sanitize_wikilink_alias for tab and other controls missed by the replace-dict. 11 new regression tests confirm both sides clean across all control-char classes."

### 6. YAML frontmatter quotes reserved words, numerics, leading indicators (WR-01)
expected: Reserved words (yes/null/true), numeric strings (42, 0.1), leading-indicator chars (-, ?, !, &, *, |, >, `, @), comma-containing strings all get quoted. Control chars stripped.
result: pass

### 7. community_name ctx field wins over parent_moc_label (WR-03)
expected: `community:` frontmatter field and metadata callout community field use `ctx["community_name"]` when present, fall back to `parent_moc_label` when absent. (Note: `up:` link legitimately stays on parent_moc_label — that's correct semantics, not a bug.)
result: pass

### 8. load_templates() override + fallback with stderr warning
expected: Valid user override wins for its note type. Malformed user template logs `[graphify] template error:` to stderr and falls back to built-in. Valid overrides for sibling types still win.
result: pass

### 9. load_templates() raises on missing vault_dir (IN-09)
expected: `load_templates("/nonexistent")` raises FileNotFoundError. Path-is-file also raises FileNotFoundError (not silent built-in fallback).
result: pass

### 10. validate_template() surfaces malformed placeholders (IN-08)
expected: `validate_template("${frontmatter}\n${bad name}", ...)` returns error containing "malformed" for the `${bad name}` token. Valid template returns empty list. Unknown but well-formed placeholder returns distinct "unknown placeholder" error.
result: pass

### 11. resolve_filename() locked GEN-07 behavior
expected: `resolve_filename("ML Architecture", "title_case")` → `"Ml_Architecture"` (locked .capitalize() behavior). Kebab-case → `"ml-architecture"`. Splits on both underscore and space.
result: pass

### 12. render_note() accepts created kwarg for determinism (IN-05)
expected: `render_note(..., created=datetime.date(2025,1,1))` produces `created: 2025-01-01` in frontmatter. Same for render_moc and render_community_overview. Without kwarg, uses today's date.
result: pass

### 13. Full test suite passes
expected: `pytest tests/ -q` → 647+ passed, 0 failed.
result: pass
note: "Post-fix baseline is 658 passed (647 before UAT + 11 new regression tests for control-char sanitization added by commit 7b5c228)."

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0

## Gaps

[all gaps closed — see Test 5 resolution]
