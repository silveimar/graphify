---
status: testing
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

### 5. Wikilink label injection is defused (CR-01)
expected: Alias portion sanitizes `]]` → `] ]`, `|` → `-`, `\n` → space. Filename target portion should not break Obsidian parsing.
result: issue
reported: "Alias sanitization works correctly (CR-01 fix confirmed). However, the filename portion of wikilinks does NOT strip newlines/tabs/CRLF — `safe_filename('line1\\nline2')` returns `'line1\\nline2'` verbatim, producing broken wikilink targets like `[[line1\\nline2|line1 line2]]` that Obsidian cannot parse. This is a gap adjacent to CR-01 but in `graphify/profile.py:safe_filename` rather than `_sanitize_wikilink_alias`. Tab and CRLF exhibit the same issue. Discovered while programmatically verifying Test 5."
severity: major

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

## Summary

total: 13
passed: 12
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Wikilink label injection is fully defused for labels containing `]]`, `|`, `\n`, `\r`, `\t` — the wikilink should parse correctly in Obsidian regardless of which part of the syntax (filename or alias) the bad character lands in."
  status: failed
  reason: "User reported: alias sanitization works (CR-01 fix confirmed), but the filename portion still leaks newlines/tabs/CRLF. safe_filename() in graphify/profile.py does not strip these control chars, producing broken wikilink targets like `[[line1\\nline2|line1 line2]]` that Obsidian cannot parse. This is the filename-side complement to CR-01's alias-side fix."
  severity: major
  test: 5
  artifacts: []
  missing:
    - "Control-char stripping in graphify/profile.py::safe_filename (or a new _sanitize_wikilink_target helper in templates.py called after resolve_filename)"
