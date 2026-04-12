# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 01-foundation
**Areas discussed:** Profile schema design, Filename safety strategy, Bug fix approach, Module organization

---

## Profile Schema Design

### Schema structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat sections | Top-level keys: folder_mapping, naming, merge, mapping_rules, obsidian. Simple, easy to partially override | ✓ |
| Nested by note type | Group config per note type (moc.folder, moc.template). More structured but deeper nesting | |
| Minimal top-level | Only essential keys at top, everything else in 'advanced' section | |

**User's choice:** Flat sections
**Notes:** None

### Merge behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Deep merge | Recursively merge user profile over defaults. Partial overrides work at any depth | ✓ |
| Section replace | Top-level section replaces entirely if user specifies it | |

**User's choice:** Deep merge
**Notes:** None

### Validation reporting

| Option | Description | Selected |
|--------|-------------|----------|
| All errors at once | Collect all validation errors and report together. Follows validate.py pattern | ✓ |
| Fail on first error | Stop at first invalid field | |

**User's choice:** All errors at once
**Notes:** None

### PyYAML dependency

| Option | Description | Selected |
|--------|-------------|----------|
| Optional with graceful error | Stay in optional deps, clear error if profile exists but PyYAML missing | ✓ |
| Make it required | Add to core dependencies | |

**User's choice:** Optional with graceful error
**Notes:** None

---

## Filename Safety Strategy

### Deduplication

| Option | Description | Selected |
|--------|-------------|----------|
| Sorted suffix | Sort by (source_file, label), duplicates get _2, _3 suffixes. Deterministic | ✓ |
| Source-qualified names | Append source file: Transformer (model).md | |
| You decide | Claude picks | |

**User's choice:** Sorted suffix
**Notes:** None

### Length cap truncation

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate + hash suffix | Truncate to 192 chars, append 8-char hash of full name | ✓ |
| Simple truncate | Cut at 200 chars | |
| You decide | Claude picks | |

**User's choice:** Truncate + hash suffix
**Notes:** None

### Unicode normalization

| Option | Description | Selected |
|--------|-------------|----------|
| NFC normalize only | NFC normalization, preserves international chars | ✓ |
| ASCII-safe transliteration | NFC + transliterate non-ASCII to ASCII | |
| You decide | Claude picks | |

**User's choice:** NFC normalize only
**Notes:** None

---

## Bug Fix Approach

### Fix location

| Option | Description | Selected |
|--------|-------------|----------|
| Extract helpers | Patch in to_obsidian(), extract reusable helpers to profile.py | ✓ |
| Inline in export.py | Keep fixes self-contained | |
| You decide | Claude picks | |

**User's choice:** Extract helpers
**Notes:** None

### YAML frontmatter injection (FIX-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Quote wrapping | Wrap values in double quotes when containing YAML-special chars | ✓ |
| Strip special chars | Remove YAML-special characters entirely | |
| You decide | Claude picks | |

**User's choice:** Quote wrapping
**Notes:** None

### Tag sanitization (FIX-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Slugify to safe tag | Lowercase, hyphens, strip special chars, prefix digits | ✓ |
| Preserve with escaping | Keep original casing and spaces | |
| You decide | Claude picks | |

**User's choice:** Slugify to safe tag
**Notes:** None

### graph.json handling (OBS-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Read-merge-write | Read existing, merge graphify's groups, preserve user settings | ✓ |
| Overwrite with backup | Save .bak, write fresh | |

**User's choice:** Read-merge-write
**Notes:** None

### Additional bug: to_canvas() path prefix (FIX-06)

**User's input:** "The to_canvas() function in the graphify library generates paths using graphify/ as the prefix instead of the actual output directory name. That causes the obsidian graph canvas fail due to files not found."
**Notes:** User-reported bug added to scope. Line 809 in export.py hardcodes `graphify/obsidian/{fname}.md` instead of using the output path parameter.

---

## Module Organization

### New module location

| Option | Description | Selected |
|--------|-------------|----------|
| New graphify/profile.py | Dedicated module for profile loading, validation, defaults, helpers | ✓ |
| Expand security.py | Add to existing security module | |
| Split: profile.py + obsidian_utils.py | Two new files | |

**User's choice:** New graphify/profile.py
**Notes:** None

### Default profile storage

| Option | Description | Selected |
|--------|-------------|----------|
| Python dict constant | _DEFAULT_PROFILE as dict literal in profile.py | ✓ |
| Embedded YAML string | YAML string parsed at load time | |
| External YAML file | Ship default_profile.yaml alongside module | |

**User's choice:** Python dict constant
**Notes:** None

### Pipeline integration

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone + lazy import | profile.py standalone, export.py imports helpers, Phase 5 wires load_profile() | ✓ |
| Don't wire until Phase 5 | Profile exists but export.py doesn't use it yet | |

**User's choice:** Standalone + lazy import
**Notes:** None

---

## Claude's Discretion

- Path traversal validation approach for profile-derived paths
- Test file organization for profile.py

## Deferred Ideas

None — discussion stayed within phase scope
