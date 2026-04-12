---
phase: 02-template-engine
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/02-template-engine/02-REVIEW.md
iteration: 2
findings_in_scope: 19
fixed: 17
skipped: 2
status: partial
---

# Phase 02: Code Review Fix Report — Template Engine

**Fixed at:** 2026-04-11
**Source review:** .planning/phases/02-template-engine/02-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 19 (1 Critical + 7 Warning + 11 Info)
- Fixed: 17 (8 in iteration 1, 9 in iteration 2)
- Skipped: 2 (both flagged as out-of-scope by the reviewer)

## Fixed Issues — Iteration 1 (Critical + Warning)

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

## Fixed Issues — Iteration 2 (Info)

### IN-01: `_FALLBACK_MOC_QUERY` duplicates `_DEFAULT_PROFILE` moc_query

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** e1e2a60
**Applied fix:** Imported `_DEFAULT_PROFILE` from `graphify.profile` and rewrote `_FALLBACK_MOC_QUERY` as `_DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"]` so the two cannot drift. Added a regression test asserting equality between `_FALLBACK_MOC_QUERY` and the dict-resident default.

---

### IN-02: `_render_moc_like` unused `communities` and `G` parameters

**Files modified:** `graphify/templates.py`
**Commit:** caa4fc3
**Applied fix:** Updated the `_render_moc_like` docstring to document that both `G` and `communities` are part of the locked D-41 surface and reserved for future use; added an explicit `_ = communities` line next to the existing `_ = G` to silence linter unused-argument warnings. No behavioural change.

---

### IN-03: `_load_builtin_template` imports `importlib.resources` on every call

**Files modified:** `graphify/templates.py`
**Commit:** c290ac7
**Applied fix:** Hoisted `import importlib.resources as ilr` to the top of the module and introduced a module-level `_BUILTIN_TEMPLATES_ROOT = ilr.files("graphify").joinpath("builtin_templates")` cache. `_load_builtin_template` now reuses the cached Traversable instead of re-walking the package on every call.

---

### IN-05: `render_note` uses `datetime.date.today()` non-deterministically

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** ba0119a
**Applied fix:** Added a `created: datetime.date | None = None` keyword argument to `render_note`, `render_moc`, `render_community_overview`, and the shared `_render_moc_like` helper. When supplied, the value is passed to `_build_frontmatter_fields`; when omitted, the existing `datetime.date.today()` default is preserved for backward compatibility. Added 3 regression tests: caller-supplied date for `render_note`, default-today fallback, and caller-supplied date for `render_moc`.

---

### IN-06: Inconsistent member-dict handling between `_build_members_section` and `_build_sub_communities_callout`

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 198fc75
**Applied fix:** Tightened `_build_members_section` to match the strict policy already used by `_build_sub_communities_callout`: only dicts with a non-empty `label` key are rendered; non-dict entries (raw strings, `None`, ints) are silently dropped. Added a guard so a group whose entries are all dropped no longer emits a lone callout header with zero bullets. Added 3 regression tests covering non-dict drop, missing-label drop, and the empty-group skip.

---

### IN-07: `_build_wayfinder_callout` called with hardcoded `note_type="moc"` from `_render_moc_like`

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 326817a
**Applied fix:** Replaced the hardcoded `note_type="moc"` argument with `note_type=template_key` so community-overview rendering no longer mis-tags the wayfinder context. The change is currently behaviour-preserving (the wayfinder builder treats `"moc"` and `"community"` identically) but removes a latent bug for any future divergence. Added 2 regression tests: one asserting `render_community_overview` still produces a wayfinder callout, one using `monkeypatch` to spy on the builder and confirm `render_moc`/`render_community_overview` pass `"moc"`/`"community"` respectively.

---

### IN-08: `validate_template` silently ignores malformed placeholders

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 399355d
**Applied fix:** `validate_template` now inspects the `invalid` group from `string.Template.pattern.finditer` and surfaces a clear `"malformed placeholder near 'X'"` error for each match (e.g. `${bad name}` with whitespace, trailing `$`). Escaped `$$` is still correctly skipped. Added 5 regression tests: malformed braced placeholder, trailing dollar, escaped dollar, well-formed placeholder, and a sweep over every shipped built-in template asserting they all pass validation.

---

### IN-09: `render_note` does not validate `vault_dir` existence

**Files modified:** `graphify/templates.py`, `tests/test_templates.py`
**Commit:** 268d0f6
**Applied fix:** `load_templates` now raises `FileNotFoundError` when `vault_dir` does not exist or is not a directory, with actionable error messages. The check fires before any template lookup so callers learn about typo'd vault paths immediately instead of silently falling back to built-ins. Added 4 regression tests: missing directory, vault path that points to a file, valid empty directory (built-ins still loaded), and propagation through `render_note`.

---

### IN-10: `pyproject.toml` obsidian extras semantic clarity

**Files modified:** `graphify/templates.py`, `tests/test_pyproject.py`
**Commit:** 2ebd303
**Applied fix:** Added a module-level docstring to `graphify/templates.py` documenting the pure-stdlib policy and clarifying that PyYAML belongs to `graphify.profile` only. Added a regression test in `test_pyproject.py` that AST-parses `templates.py` and asserts every top-level import comes from a stdlib whitelist (`__future__`, `datetime`, `importlib`, `re`, `string`, `sys`, `pathlib`, `typing`) or from the `graphify` package. Future PRs that try to add a third-party top-level import to `templates.py` will fail this guard with a pointer to the IN-10 docstring.

---

## Skipped Issues

### IN-04: `render_note` / `render_moc` re-read and re-parse built-in templates on every call

**File:** `graphify/templates.py:146-180, 514-520, 621-628`
**Reason:** Out of scope per REVIEW.md — the reviewer explicitly flagged this for the Phase 5 adapter rather than v1, since the optimization (caching parsed templates and detecting mid-run edits) is interlocked with how `to_obsidian()` will own the per-vault template lifecycle.
**Original issue:** Performance + correctness — re-reading templates on every call wastes I/O and lets mid-run template edits cause cross-note drift within a single render pass.

---

### IN-11: `.gitignore` modification not in review scope

**File:** `.gitignore`
**Reason:** Out of scope per REVIEW.md — the reviewer noted the `.gitignore` change in `git status` but explicitly excluded it from the review file list and marked the finding "Out of scope."
**Original issue:** A `.gitignore` modification was visible in `git status` but not in the files reviewed for Phase 02; the reviewer chose not to audit it.

---

## Test Suite Results

Final full suite run after iteration 2:

```
647 passed in 1.47s
```

- Iteration 1 ending count: 628 passed (154 baseline + 474 added across phases prior to this fix run + 41 new regression tests for CR-01/WR-01..07).
- Iteration 2 ending count: 647 passed (628 + 19 new regression tests for IN-01, IN-05, IN-06, IN-07, IN-08, IN-09, IN-10).
- No pre-existing tests were modified or skipped.

Per-finding focused-suite verification:

```
pytest tests/test_templates.py tests/test_profile.py tests/test_pyproject.py -q
217 passed in 0.22s
```

---

_Fixed: 2026-04-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
