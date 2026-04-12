# Project Research Summary

**Project:** Configurable Obsidian Vault Adapter (Ideaverse Integration)
**Domain:** Knowledge-graph-to-Obsidian-vault injection adapter
**Researched:** 2026-04-09
**Confidence:** HIGH

## Executive Summary

This milestone replaces the existing monolithic `to_obsidian()` function in `export.py` with a four-component configurable vault adapter. The adapter reads a vault-owned `.graphify/profile.yaml` to control folder placement, note-type classification, merge behavior, and template rendering — without introducing any new required dependencies. The recommended build approach decomposes the 240-line existing function into four focused, independently-testable modules (`obsidian_profile.py`, `obsidian_mapper.py`, `obsidian_template.py`, `obsidian_merge.py`) wired together by a refactored thin orchestrator in `export.py`.

The technology stack is entirely stdlib + existing optional dependencies: PyYAML `safe_load` for profile parsing (with graceful ImportError fallback), `string.Template.safe_substitute()` for note rendering, and manual string construction extending the existing `_yaml_str()` helper for YAML frontmatter output. Zero `pyproject.toml` changes required.

The dominant risks are data-correctness bugs in YAML frontmatter generation (six known bugs in current codebase must be fixed first), silent user-data loss from a naive merge strategy, and a path-traversal security hole via `profile.yaml` folder mapping. The single most trust-destroying failure mode is overwriting user-curated frontmatter fields (`rank`, `mapState`) on re-run; the merge engine's `preserve_fields` list must be the earliest design decision.

## Key Findings

### Recommended Stack

The entire feature is buildable on stdlib + PyYAML (already optional). No new `pyproject.toml` entries required.

**Core technologies:**
- `yaml.safe_load` (PyYAML, optional): profile.yaml parsing — safe from YAML injection, graceful ImportError fallback
- `string.Template.safe_substitute()` (stdlib): note template rendering — `$var` syntax avoids Obsidian Templater `{{var}}` collision
- `_yaml_str()` helper (existing, promoted to shared utility): frontmatter serialization — consistent Obsidian-compatible quoting without PyYAML `dump()` artifacts
- Custom ~40-line frontmatter parser: merge-time frontmatter round-trip — line-by-line extraction, not PyYAML (Obsidian YAML doesn't round-trip cleanly)
- `unicodedata.normalize("NFC", ...)` (stdlib): filename normalization — prevents cross-platform duplicate notes

### Expected Features

**Must have (table stakes):**
- Profile discovery (`.graphify/profile.yaml` in target vault) with built-in default fallback
- YAML frontmatter with Ideaverse fields (`up:`, `related:`, `collections:`, `tags:`, `created:`)
- `[[wikilink]]` generation with deduplication and label sanitization
- Folder placement per note type driven by profile `folder_mapping`
- Note-type classification (topology-based: god node, community hub, source file, default)
- Update/merge with `preserve_fields` — re-run must not destroy user edits
- `--dry-run` flag: print plan without writing
- `graph.json` community color generation (configurable on/off)
- Backward compatibility when no profile exists

**Should have (differentiators):**
- Dual mapping rules (topology + attribute conditions in profile)
- Community-to-MOC threshold (configurable member minimum)
- Embedded Dataview queries in MOC notes
- Source-to-Source-note mapping with sub-folder routing
- Wayfinder navigation generation
- Configurable naming conventions

**Defer (post-MVP):**
- Attribute-based mapping rules (adds rule engine complexity)
- Conditional template sections
- Custom color palettes in profile
- Mustache-style loop blocks

### Architecture Approach

The adapter is a pure sub-pipeline within the existing export stage. Four new modules, independently testable, no cross-dependencies at instantiation.

**Major components:**
1. **ProfileLoader** (`obsidian_profile.py`) — load/validate `.graphify/profile.yaml`; merge over defaults; path-traversal validation
2. **MappingEngine** (`obsidian_mapper.py`) — classify nodes by topology + attributes; produce `NoteSpec` per node with folder, filename, wikilink
3. **TemplateEngine** (`obsidian_template.py`) — single-pass `$placeholder` substitution; built-in templates as module constants; vault templates override
4. **MergeEngine** (`obsidian_merge.py`) — read existing note, parse frontmatter line-by-line, apply preserve-fields strategy, write merged content

### Critical Pitfalls

1. **YAML frontmatter injection via f-strings** — node labels containing `:`, `#`, `[`, `]` produce malformed YAML. Pre-existing bug. Fix: proper quoting via `_yaml_str()`.
2. **User-curated frontmatter overwritten on re-run** — permanent data loss unless vault is in git. Fix: `preserve_fields` list in MergeEngine from day one.
3. **Path traversal via profile.yaml folder mapping** — `folder: "../../.ssh"` writes outside vault. Fix: `validate_vault_path()` on every profile-derived path.
4. **graph.json wrong query syntax** — current code writes `tag:#community/...` but Obsidian requires `tag:community/...` (no `#`). Pre-existing bug.
5. **Non-deterministic filename deduplication** — causes stale wikilinks on re-run. Fix: sort nodes before assignment.

## Implications for Roadmap

### Phase 1: Foundation — Profile Loader, Filename Safety, Security
**Rationale:** Everything depends on profile loading and safe file operations. Also fixes 6 pre-existing bugs.
**Delivers:** Validated `Profile` dict; `safe_filename()` / `sanitize_tag()` / `validate_vault_path()` utilities; fixed `graph.json`; deterministic node ordering; NFC normalization.
**Avoids:** P1 (YAML injection), P4 (Unicode dupes), P7 (path traversal), P8 (graph.json syntax), P9 (tag format), P10 (dedup determinism).

### Phase 2: Template Engine and Note Context
**Rationale:** No dependency on MappingEngine or MergeEngine — independently buildable.
**Delivers:** `TemplateEngine` with single-pass substitution; built-in templates for MOC, Dot, Source; `NoteContext` builder from graph data.
**Avoids:** P6 (placeholder collision), P14 (missing placeholder keys).

### Phase 3: Mapping Engine
**Rationale:** Depends on Phase 1 (needs `Profile`) and existing `analyze.py` god-node output.
**Delivers:** Topology-based note-type classification; folder assignment per profile; `NoteSpec` per node; community-to-MOC threshold.

### Phase 4: Merge Engine
**Rationale:** No cross-module dependencies — parallelizable with Phases 2-3 in practice.
**Delivers:** Frontmatter round-trip parser; `preserve_fields` strategy; update/skip/replace modes; field-order preservation.
**Avoids:** P3 (user edits overwritten), P12 (field ordering diff noise).

### Phase 5: Integration and CLI
**Rationale:** Wires all four modules into refactored `to_obsidian()`. Existing tests are backward-compat guard.
**Delivers:** Full configurable vault adapter; `--dry-run` flag; `--validate-profile` subcommand; complete test suite.

### Phase Ordering Rationale

- Phases 1, 2, and 4 have no cross-dependencies but Phase 1 security primitives must exist before any file-writing code
- Phase 3 requires Phase 1's `Profile` output
- Phase 5 integration requires all four modules
- This order ensures no partially-complete implementation writes files with exploitable paths or destructive merge behavior

### Research Flags

Standard patterns (research-phase not needed):
- **Phase 1:** ProfileLoader follows identical guard pattern to `cluster.py`; bugs already diagnosed
- **Phase 2:** `string.Template` is stdlib; substitution logic well-understood
- **Phase 4:** Frontmatter merge is well-defined algorithm

May benefit from design session:
- **Phase 3:** Attribute-based mapping rule priority ordering has edge cases worth designing before coding
- **Phase 5:** Pre-integration backward-compat audit of `test_export.py` fixtures

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All from existing codebase + stdlib docs. No ambiguity given project constraints. |
| Features | MEDIUM-HIGH | Core features from codebase audit (HIGH). Ideaverse frontmatter schema from training data, not live-verified (MEDIUM). |
| Architecture | HIGH | Based entirely on direct codebase reading. Module boundaries fully derivable. |
| Pitfalls | HIGH | YAML behavior and Obsidian format rules well-documented. Pre-existing bugs verified directly. |

**Overall confidence:** HIGH

### Gaps to Address

- **Ideaverse frontmatter field names** (`up:`, `related:`, `collections:`, `rank:`, `mapState:`): training knowledge, not live-verified. Mitigation: profile system makes these fully configurable.
- **Wikilink in YAML lists**: Whether `"[[Note]]"` (PyYAML-quoted) registers backlinks in Obsidian needs a live test.
- **Attribute-based mapping rules**: Deferred or included in MVP? Decision needed before Phase 3.

## Sources

### Primary (HIGH confidence)
- `graphify/export.py` lines 440-679 — current `to_obsidian()`, pre-existing bugs
- `graphify/security.py` — `sanitize_label()`, `validate_graph_path()` APIs
- `graphify/build.py`, `graphify/cluster.py`, `graphify/analyze.py` — pipeline data flow
- `.planning/PROJECT.md` — milestone requirements and constraints
- Python stdlib docs — `string.Template`, `pathlib.Path`, `unicodedata`

### Secondary (MEDIUM confidence)
- Ideaverse Pro 2.5 frontmatter field conventions
- Obsidian Dataview plugin query syntax
- PyYAML `safe_load` / `dump` behavior

### Tertiary (LOW confidence — needs validation)
- Obsidian backlink registration for `"[[Note]]"` double-quoted YAML
- `graph.json` `colorGroups` stability across Obsidian versions

---
*Research completed: 2026-04-09*
*Ready for roadmap: yes*
