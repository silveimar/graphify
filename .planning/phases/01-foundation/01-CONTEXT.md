# Phase 1: Foundation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Safe, validated profile loading and filename utilities are available; all pre-existing bugs in the current `to_obsidian()` and `to_canvas()` are patched. This phase delivers the profile system foundation (discover, load, validate, merge) and extracts reusable safety helpers that Phase 2-5 will consume.

</domain>

<decisions>
## Implementation Decisions

### Profile Schema Design
- **D-01:** Profile YAML uses flat top-level sections: `folder_mapping`, `naming`, `merge`, `mapping_rules`, `obsidian`
- **D-02:** User profiles deep-merge over built-in defaults — specifying `folder_mapping.moc` only overrides that key, all other folder_mapping entries keep their defaults
- **D-03:** Profile validation collects all errors and reports them together (follows `validate.py` pattern of returning `list[str]`), not fail-on-first
- **D-04:** PyYAML stays in optional dependencies. If user has a `profile.yaml` but no PyYAML installed, graphify prints a clear install instruction and falls back to built-in defaults

### Filename Safety Strategy
- **D-05:** Filename deduplication uses deterministic sorted suffix — sort nodes by `(source_file, label)` before assignment, duplicates get `_2`, `_3` suffixes (fixes FIX-02)
- **D-06:** Filename length cap at 200 characters uses truncate-to-192 + 8-char hash suffix of the full name to prevent collisions from long shared prefixes (fixes FIX-05)
- **D-07:** NFC Unicode normalization only — preserves accented characters, CJK, etc. while preventing cross-platform duplicates from macOS NFD vs Windows NFC (fixes FIX-04)

### Bug Fix Approach
- **D-08:** Bug fixes extract reusable helpers (`safe_filename`, `safe_frontmatter_value`, `safe_tag`) into `profile.py` rather than staying inline in `export.py`. Phase 2+ imports these helpers directly
- **D-09:** FIX-01 (YAML frontmatter injection) uses quote wrapping — values containing YAML-special chars (`:`, `#`, `[`, `]`, `{`, `}`) are wrapped in double quotes; clean values stay unquoted
- **D-10:** FIX-03 (tag sanitization) uses slugification — community names become lowercase, spaces/special chars replaced with hyphens, leading digits prefixed with `x`, `/` and `+` stripped. Format: `community/slugified-name`
- **D-11:** OBS-02 (graph.json) uses read-merge-write — read existing file, merge graphify's community color groups (keyed by `tag:community/` prefix), preserve all other user settings, write back
- **D-12:** OBS-01 (graph.json tag syntax) fix: change `tag:#community` to `tag:community/Name` format
- **D-13:** FIX-06 (NEW): `to_canvas()` in `export.py` line 809 hardcodes `graphify/obsidian/{fname}.md` as file paths instead of using the actual output directory. Fix: use the real output path parameter

### Module Organization
- **D-14:** New `graphify/profile.py` module — dedicated module for profile loading, schema validation, default profile, and deep merge. Also hosts extracted filename/frontmatter/tag safety helpers
- **D-15:** Built-in default profile stored as a Python dict constant (`_DEFAULT_PROFILE`) in `profile.py` — no YAML parsing needed for defaults, no PyYAML dependency for fallback path
- **D-16:** `profile.py` is standalone with no imports from `export.py`. Added to `__init__.py` lazy imports. Bug fixes in `export.py` import helpers from `profile.py`. Phase 5 wires `load_profile()` into `to_obsidian()` signature

### Claude's Discretion
- Path traversal validation approach for profile-derived paths (MRG-04) — Claude picks the implementation pattern consistent with `security.py`
- Test file organization for `profile.py` — follows existing `test_<module>.py` convention

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (modify/extend)
- `graphify/export.py` L440-679 — Current `to_obsidian()` function (bugs FIX-01 through FIX-05 live here)
- `graphify/export.py` L682+ — `to_canvas()` function (FIX-06: hardcoded path prefix)
- `graphify/export.py` L809 — Specific line with hardcoded `graphify/obsidian/` path in canvas

### Security Patterns (follow)
- `graphify/security.py` L188+ — `sanitize_label()` as reference for safety helper patterns
- `graphify/validate.py` — Validation pattern (return `list[str]` of errors)

### Architecture References
- `graphify/extract.py` L14 — `_make_id()` as reference for stable ID generation
- `graphify/__init__.py` — Lazy import pattern to follow for `profile.py` registration

### Requirements
- `.planning/REQUIREMENTS.md` — PROF-01 through PROF-04, PROF-06, MRG-04, OBS-01, OBS-02, FIX-01 through FIX-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py:sanitize_label()` — strips control chars, caps length; pattern to follow for `safe_frontmatter_value()`
- `extract.py:_make_id()` — stable slug generation; reference for `safe_filename()` slug logic
- `validate.py:validate_extraction()` — returns `list[str]` of errors; exact pattern for `validate_profile()`

### Established Patterns
- Validation returns error list, not exceptions: `validate_extraction(data) -> list[str]`
- Optional deps use try/except ImportError with clear install message to stderr
- `from __future__ import annotations` as first import in every module
- Module docstring as single-line after future import
- Private helpers prefixed with `_`, public API functions unprefixed

### Integration Points
- `__init__.py` lazy import map — add `load_profile`, `validate_profile` entries
- `export.py:to_obsidian()` — bug fixes import helpers from `profile.py`; Phase 5 adds `profile=None` parameter
- `pyproject.toml` optional-dependencies — add `obsidian = ["PyYAML"]` extra

</code_context>

<specifics>
## Specific Ideas

- The `to_canvas()` path bug (FIX-06) was discovered during this discussion — it's not in REQUIREMENTS.md yet. The fix is straightforward: use the output path parameter instead of hardcoded `graphify/` prefix
- Default profile uses Ideaverse ACE folder structure (`Atlas/Maps/`, `Atlas/Dots/Things/`, etc.) as specified in PROJECT.md
- Tag format `community/slugified-name` (not `#community/name` or `tag:#name`) — the `tag:` prefix is only in graph.json queries, not in frontmatter

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-09*
