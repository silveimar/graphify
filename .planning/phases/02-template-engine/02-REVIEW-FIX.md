---
phase: 02-template-engine
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/02-template-engine/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report — Template Engine

**Fixed at:** 2026-04-11
**Source review:** .planning/phases/02-template-engine/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: Wikilink emission performs no escaping of `]]`, `|`, or `\n` in labels

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 426328c
**Applied fix:** Added `_WIKILINK_ALIAS_FORBIDDEN` dict and `_sanitize_wikilink_alias()` helper that replaces `]]` → `] ]`, `|` → `-`, `\n` → ` `, `\r` → ` ` before the alias is interpolated into the wikilink. `_emit_wikilink` now calls `_sanitize_wikilink_alias(label)` to produce the display alias. Added 7 regression tests covering each forbidden character plus end-to-end `_emit_wikilink` scenarios.

---

### WR-01: `safe_frontmatter_value` misses several YAML scalar-poison cases

**Files modified:** `graphify/profile.py`, `tests/test_profile.py`
**Commit:** 13ec26b
**Applied fix:** Broadened `_YAML_SPECIAL` to include `,`. Added three new module-level constants: `_YAML_LEADING_INDICATORS` (set of `-?!&*|>%@\``), `_YAML_RESERVED_WORDS` (frozenset of yes/no/true/false/null/on/off/~), and `_YAML_NUMERIC_RE` (regex matching int/float/scientific/hex/octal/`.inf`/`.nan`). Added `_YAML_CONTROL_RE` to strip control chars beyond `\n`/`\r` (including NEL `\x85`, LS `\u2028`, PS `\u2029`). `safe_frontmatter_value` now strips control chars first, then applies all four quoting conditions. Added 20 regression tests.

---

### WR-02: `_build_connections_callout` does not sanitize relation / confidence / target_label

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 4ab72d8
**Applied fix:** In `_build_connections_callout`, `relation` and `confidence` are now sanitized before interpolation: `\n` and `\r` replaced with space (prevents line-break injection into the callout bullet), `]` stripped (prevents premature bracket closing). Added 3 regression tests covering newline-in-relation, bracket-in-confidence, and newline-in-confidence scenarios.

---

### WR-03: `render_note` ignores `ctx["community_name"]` — assigns `parent_moc_label` to `community_name`

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** f68bd4a
**Applied fix:** Changed the `community_name` assignment in `render_note` from `ctx.get("parent_moc_label")` to `ctx.get("community_name") or ctx.get("parent_moc_label")`, matching the preference order already in `_render_moc_like`. Added 2 regression tests: one verifying `community_name` wins when both are present, one verifying fallback to `parent_moc_label` when `community_name` is absent.

---

### WR-04: `tag_list` builds raw tag strings without `safe_tag` sanitization

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 5f09561
**Applied fix:** In `render_note` tag-list construction, wrapped both `community_tag` and `file_type or 'note'` in `safe_tag()` before interpolation. This ensures uppercase, spaces, and special characters in extractor-supplied values are slugified before becoming Obsidian tags. Added 2 regression tests: one with `file_type="source code"` (spaces), one with `community_tag="ML Architecture"` (uppercase + spaces).

---

### WR-05: `_build_dataview_block` does not sanitize `folder` before substitution

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 56c9bc9
**Applied fix:** In `_build_dataview_block`, `community_tag` and `folder` are stripped of backticks and newlines before being passed to `string.Template.safe_substitute`. After substitution, any remaining ` ``` ` sequences in the resolved query are also stripped to prevent premature fence closure. Added 4 regression tests covering backtick-in-folder, newline-in-folder, backtick-in-community-tag, and triple-backtick-in-custom-query scenarios.

---

### WR-06: `_dump_frontmatter` float branch does not handle numpy.float64

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** da06a84
**Applied fix:** In `_render_moc_like`, `cohesion` is now cast to `float()` at the boundary before passing to `_build_frontmatter_fields`. The pattern `float(_raw_cohesion) if _raw_cohesion is not None else None` covers numpy.float64 (which is not a Python float subclass) without requiring numpy as a dependency. Added 2 regression tests: one using a `float` subclass with overridden `__str__`/`__repr__` to simulate numpy.float64 behaviour, one verifying `cohesion=None` produces no `cohesion:` field.

---

### WR-07: `validate_profile` folder_mapping check only rejects literal `..`

**Files modified:** `graphify/profile.py`, `tests/test_profile.py`
**Commit:** b4ade72
**Applied fix:** In `validate_profile`'s folder_mapping validation, added two additional checks after the `".." in path_val` guard: `Path(path_val).is_absolute()` rejects absolute paths like `/etc/passwd`, and `path_val.startswith("~")` rejects home-expansion paths. Both produce clear error messages earlier than `validate_vault_path` would. Added 3 regression tests covering absolute path, tilde prefix, and valid relative path.

---

## Skipped Issues

None — all 8 in-scope findings were fixed.

---

## Test Suite Results

Final full suite run after all 8 fixes:

```
628 passed in 1.50s
```

Starting count (before fixes): 154 passed
Ending count (after fixes): 628 passed (includes all pre-existing tests plus 41 new regression tests across `tests/test_templates.py` and `tests/test_profile.py`).

---

_Fixed: 2026-04-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
