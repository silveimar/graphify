---
phase: 02-template-engine
status: issues_found
depth: standard
reviewed: 2026-04-11
files_reviewed: 14
findings:
  critical: 1
  warning: 7
  info: 11
  total: 19
---

# Phase 02: Code Review Report — Template Engine

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the Phase 2 template engine implementation across `graphify/templates.py` (666 lines), `graphify/profile.py` (275 lines), 6 built-in templates, `pyproject.toml` packaging, and 3 test files. The engine correctly implements the two-phase `string.Template` substitution pattern (Pattern 5) and locks the `KNOWN_VARS` vocabulary per D-18. Path confinement via `validate_vault_path` is properly wired into `load_templates`.

**Key concerns:**
- **Security (Critical):** `_emit_wikilink` performs zero escaping of labels — a node label containing `]]`, `|`, or `\n` breaks wikilink syntax and can inject arbitrary markdown/callout content downstream. This is the primary label-injection vector the scope asked to audit.
- **Security (Warning):** `_dump_frontmatter` / `safe_frontmatter_value` miss several YAML scalar-poison cases (leading indicator chars, reserved words `yes`/`no`/`null`/`true`/`false`, control characters other than `\n`/`\r`).
- **Bug (Warning):** `render_note` uses `parent_moc_label` as the `community_name` (line 457), ignoring `ctx["community_name"]` even when Phase 3 populates it.
- **Bug (Warning):** `_build_connections_callout` does not escape `relation`/`confidence`/`target_label` — a relation containing `\n` breaks the callout block.
- **Info-level:** duplicated fallback moc_query, missing folder sanitization in dataview block, tag slug not applied to `file_type`.

No import/dependency issues, no hardcoded secrets, no dangerous function usage. Path confinement works correctly because `validate_vault_path` calls `.resolve()` on both sides.

---

## Critical Issues

### CR-01: Wikilink emission performs no escaping of `]]`, `|`, or `\n` in labels

**File:** `graphify/templates.py:187-190`
**Issue:** `_emit_wikilink` returns `f"[[{fname}|{label}]]"` with the raw `label` passed through unmodified. `fname` has been sanitized by `safe_filename` (which strips `[`, `]`, `|`, `#`, etc.) but the display alias `label` is emitted verbatim. A node label containing `]]` truncates the wikilink early; a label containing `|` creates a malformed alias; a label containing `\n` breaks the containing callout/list/frontmatter block.

This propagates into:
- `_build_connections_callout` (line 290) — breaks the `> - ...` bullet format
- `_build_members_section` (line 349) — breaks the `> [!info]` callout
- `_build_sub_communities_callout` (line 372) — breaks the nested bullets
- `render_note` frontmatter `up:` and `related:` (lines 463, 466) — bypassed by `safe_frontmatter_value` only when YAML-special chars are detected; `]]` is not in `_YAML_SPECIAL`
- `_build_wayfinder_callout` (lines 261, 267)

Example failure case: a node labeled `Array[int]]` would yield `[[Array_int|Array[int]]]` which Obsidian parses as a broken wikilink to `Array_int` followed by literal `]`.

**Fix:**
```python
_WIKILINK_ALIAS_FORBIDDEN = {"\n": " ", "\r": " ", "]]": "] ]", "|": "-"}

def _sanitize_wikilink_alias(label: str) -> str:
    out = label
    for bad, repl in _WIKILINK_ALIAS_FORBIDDEN.items():
        out = out.replace(bad, repl)
    return out

def _emit_wikilink(label: str, convention: str) -> str:
    fname = resolve_filename(label, convention)
    alias = _sanitize_wikilink_alias(label)
    return f"[[{fname}|{alias}]]"
```

---

## Warnings

### WR-01: `safe_frontmatter_value` misses several YAML scalar-poison cases

**File:** `graphify/profile.py:45,192-207`
**Issue:** `_YAML_SPECIAL = set(':#[]{}')` only covers 6 characters. The following unquoted strings parse as non-string YAML or as document structure:

1. **Leading indicator chars:** a label starting with `-`, `?`, `!`, `&`, `*`, `>`, `|`, `%`, `@`, or `` ` `` becomes a sequence/directive/anchor/alias/scalar-block marker.
2. **Reserved words:** `yes`, `no`, `true`, `false`, `null`, `on`, `off`, `~`, `Yes`, `NO`, etc. parse as bool/null, not strings.
3. **Numeric-looking strings:** `"0.1"`, `"42"`, `"1e10"` parse as numbers.
4. **Control characters:** only `\n` and `\r` are replaced — `\t`, `\x00`–`\x1f`, NEL (`\x85`), line/paragraph separators (`\u2028`/`\u2029`) are preserved.
5. **Comma `,`:** flow-context indicator.

**Fix:** broaden `_YAML_SPECIAL`, add `_YAML_LEADING_INDICATORS` and `_YAML_RESERVED_WORDS` sets, add a numeric-string regex, strip/replace all control chars.

---

### WR-02: `_build_connections_callout` does not sanitize relation / confidence / target_label

**File:** `graphify/templates.py:275-294`
**Issue:** Line 291 emits `f"> - {link} — {relation} [{confidence}]"` with no escaping of `relation` or `confidence`. `relation` comes from raw edge data which may include LLM-sourced strings. A relation containing `\n` breaks the callout; a `confidence` containing `]` closes the bracket early.

**Fix:** strip `\n`, `\r`, `]` from `relation`/`confidence` before interpolation.

---

### WR-03: `render_note` ignores `ctx["community_name"]` — assigns `parent_moc_label` to `community_name`

**File:** `graphify/templates.py:457`
**Issue:**
```python
community_name = ctx.get("parent_moc_label") if isinstance(ctx, dict) else None
```
The variable is named `community_name` but reads from `parent_moc_label`. The `ClassificationContext` TypedDict explicitly declares `community_name` as a Phase-3-populated field, and `_render_moc_like` correctly prefers `ctx["community_name"]` over `parent_moc_label`. `render_note` diverges.

**Fix:**
```python
community_name = (
    ctx.get("community_name") or ctx.get("parent_moc_label")
) if isinstance(ctx, dict) else None
```

---

### WR-04: `tag_list` builds raw tag strings without `safe_tag` sanitization

**File:** `graphify/templates.py:469-472`
**Issue:** `file_type` is taken directly from graph node data without running through `safe_tag()`. Extractors may produce values with spaces, uppercase, or special chars. A `file_type` of `"source code"` produces the tag `graphify/source code` — Obsidian treats only the first word as the tag. `community_tag` is also not guaranteed to be slugified in `render_note`.

**Fix:** apply `safe_tag()` to both `community_tag` and `file_type` at tag-list construction time.

---

### WR-05: `_build_dataview_block` does not sanitize `folder` before substitution

**File:** `graphify/templates.py:391-413`
**Issue:** `folder` comes from `ctx.get("folder", "Atlas/Maps/")` and is substituted into `moc_query` without validation. A folder containing a backtick breaks the outer dataview fence.

**Fix:** strip backticks and newlines from `folder` and `community_tag` before substitution; also guard the resolved query against `` ``` ``.

---

### WR-06: `_dump_frontmatter` float branch does not handle numpy.float64

**File:** `graphify/profile.py:262-266`
**Issue:** `isinstance(value, float)` does NOT match `numpy.float64` (not a Python float subclass). If cohesion is passed from a numpy computation in Phase 3, it falls through to `str()` and renders as `numpy.float64(0.82)`.

**Fix:** cast explicitly at the `_build_frontmatter_fields` boundary, e.g. `fields["cohesion"] = float(cohesion)`.

---

### WR-07: `validate_profile` folder_mapping check only rejects literal `..`

**File:** `graphify/profile.py:150-157`
**Issue:** `elif ".." in path_val` catches literal double-dot but not absolute paths (`/etc/passwd`), Windows drive roots, or home-expansion (`~/../`). `validate_vault_path` catches these at use-time, but profile validation should reject them earlier for a clearer error.

**Fix:** also reject `Path(path_val).is_absolute()` and paths starting with `~`.

---

## Info

### IN-01: `_FALLBACK_MOC_QUERY` duplicates `_DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"]`

**File:** `graphify/templates.py:384-388`, `graphify/profile.py:33-35`
Two sources of truth. If one is updated without the other, behavior diverges. Import the default from `profile.py` instead of duplicating the string.

### IN-02: `_render_moc_like` unused `communities` and `G` parameters

**File:** `graphify/templates.py:532-534, 635-665`
Public signature requirement (D-41) — document via `_ = communities  # reserved for future use` to silence linters and clarify intent.

### IN-03: `_load_builtin_template` imports `importlib.resources` on every call

**File:** `graphify/templates.py:134-143`
Move `import importlib.resources as ilr` to the top of the module and cache the `Traversable` root.

### IN-04: `render_note` / `render_moc` re-read and re-parse built-in templates on every call

**File:** `graphify/templates.py:146-180, 514-520, 621-628`
Performance + correctness (mid-run template edits cause cross-note drift). Out of scope for v1 but flag for Phase 5 adapter.

### IN-05: `render_note` uses `datetime.date.today()` non-deterministically

**File:** `graphify/templates.py:484, 588`
Accept `created: datetime.date | None = None` kwarg for test determinism and reproducible vault builds.

### IN-06: Inconsistent member-dict handling between `_build_members_section` and `_build_sub_communities_callout`

**File:** `graphify/templates.py:345-349, 369-376`
One falls through to `str(m)`, the other drops non-dicts silently. Pick one policy.

### IN-07: `_build_wayfinder_callout` called with hardcoded `note_type="moc"` from `_render_moc_like`

**File:** `graphify/templates.py:594-599`
Pass `note_type=template_key` instead.

### IN-08: `validate_template` silently ignores malformed placeholders

**File:** `graphify/templates.py:94-117`
Check for `m.group("invalid")` and surface an error for malformed templates like `${bad name}`.

### IN-09: `render_note` does not validate `vault_dir` existence

**File:** `graphify/templates.py:514-515`
If `vault_dir` points to a non-existent path, templates silently fall back to built-ins instead of raising.

### IN-10: `pyproject.toml` obsidian extras semantic clarity

**File:** `pyproject.toml:50`
`templates.py` is pure stdlib (no PyYAML). Add a module docstring clarifying that PyYAML is profile-loading only.

### IN-11: `.gitignore` modification not in review scope

Noted in `git status` but not in review files list. Out of scope.

---

## Files reviewed

- `graphify/templates.py`
- `graphify/profile.py`
- `graphify/__init__.py`
- `graphify/builtin_templates/{moc,community,thing,statement,person,source}.md`
- `pyproject.toml`
- `tests/test_templates.py`
- `tests/test_profile.py`
- `tests/test_pyproject.py`
- `tests/fixtures/template_context.py`

## Findings summary

| Severity | Count |
|----------|-------|
| Critical | 1     |
| Warning  | 7     |
| Info     | 11    |
| **Total** | **19** |

**Status:** issues_found

The Critical finding (CR-01) should block merge — label injection via unescaped wikilink aliases is the exact vector the phase scope called out, and a two-line fix (`_sanitize_wikilink_alias`) closes it. WR-01 through WR-05 address the YAML injection and downstream markdown injection vectors and should also land before Phase 5 wires this into `to_obsidian()`. The Info items are polish and can be deferred.

_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Reviewed: 2026-04-11_
