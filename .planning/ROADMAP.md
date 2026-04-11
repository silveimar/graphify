# Roadmap: Configurable Obsidian Vault Adapter (Ideaverse Integration)

## Overview

This milestone replaces the existing monolithic `to_obsidian()` function with a four-component configurable vault adapter. Starting from pre-existing bugs and security gaps, the build proceeds through profile loading, template rendering, note classification, and safe merge behavior — culminating in a wired integration that makes graphify vault-agnostic via a declarative `.graphify/profile.yaml`.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Profile loader, filename safety utilities, and security primitives; fixes 5 pre-existing bugs
- [ ] **Phase 2: Template Engine** - Note rendering via `string.Template` with built-in templates for all note types
- [x] **Phase 3: Mapping Engine** - Topology + attribute classification of nodes into note types and folder placements (completed 2026-04-11)
- [ ] **Phase 4: Merge Engine** - Safe frontmatter round-trip with `preserve_fields`, field-order preservation, and merge strategies
- [ ] **Phase 5: Integration & CLI** - Wire all four modules into refactored `to_obsidian()`; add `--dry-run` and `--validate-profile`

## Phase Details

### Phase 1: Foundation
**Goal**: Safe, validated profile loading and filename utilities are available; all pre-existing bugs in the current `to_obsidian()` are patched
**Depends on**: Nothing (first phase)
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, PROF-06, MRG-04, OBS-01, OBS-02, FIX-01, FIX-02, FIX-03, FIX-04, FIX-05
**Success Criteria** (what must be TRUE):
  1. User can place `.graphify/profile.yaml` in a vault and graphify discovers and loads it, merging over built-in defaults
  2. Running graphify against a vault with no profile produces output without errors or behavioral regression
  3. A profile with an invalid schema produces an actionable error message describing the failing field
  4. A profile-derived folder path containing `../` or pointing outside the vault directory is rejected before any file is written
  5. Re-running graphify against an existing vault no longer produces non-deterministic filenames, malformed YAML frontmatter, or wrong `graph.json` `tag:#` syntax
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Create profile.py module with profile loading, validation, deep merge, and safety helpers + tests
- [x] 01-02-PLAN.md — Patch export.py bugs using profile.py helpers, wire module into __init__.py, add obsidian optional dep

### Phase 2: Template Engine
**Goal**: All six built-in note types render correctly from graph data using configurable templates, with proper frontmatter fields and wikilinks
**Depends on**: Nothing (independently buildable)
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07
**Success Criteria** (what must be TRUE):
  1. A generated MOC note contains valid YAML frontmatter with `up:`, `related:`, `collections:`, `tags:`, and `created:` fields using `[[wikilink]]` format
  2. A user-supplied template in `.graphify/templates/` overrides the built-in template for that note type
  3. MOC notes contain an embedded Dataview query that lists community members dynamically
  4. Notes contain wayfinder navigation linking to the parent MOC and related communities
  5. Output filenames follow the convention configured in the profile (title_case, kebab-case, or preserve original label)
**Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md — Package-data + 6 built-in templates + _dump_frontmatter + obsidian profile defaults (BLOCKING foundation)
- [x] 02-02-PLAN.md — templates.py skeleton: resolve_filename + validate_template + load_templates + ClassificationContext + lazy imports
- [x] 02-03-PLAN.md — Section builders + render_note for Thing/Statement/Person/Source
- [x] 02-04-PLAN.md — render_moc + render_community_overview + members/sub-communities/dataview builders + VALIDATION binding

### Phase 3: Mapping Engine
**Goal**: Every graph node is classified into exactly one note type and assigned a folder location, driven by topology and attribute rules from the profile
**Depends on**: Phase 1
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06
**Success Criteria** (what must be TRUE):
  1. God nodes are classified as Things and placed in `Atlas/Dots/Things/` (or profile-equivalent folder)
  2. Communities with member count above the configured threshold become MOC notes; those below collapse into a list in the parent MOC
  3. A node with attribute `file_type: person` is classified as a Person note even when topology alone would classify it differently
  4. Source files route to sub-folders by file type when the profile specifies routing rules (e.g., `.py` files → `Code/`)
  5. Attribute rules take precedence over topology rules, which take precedence over the default classification
**Plans:** 4/4 plans complete

Plans:
- [x] 03-01-PLAN.md — Rule matching core: classify() precedence pipeline, matcher dispatch, per-node classification (MAP-01..MAP-04, MAP-06)
- [x] 03-02-PLAN.md — Community assembly: MOC labels, sibling_labels, nearest-host resolution, bucket MOC, members_by_type (MAP-02, MAP-05)
- [x] 03-03-PLAN.md — Profile validator: _DEFAULT_PROFILE topology+mapping sections, validate_rules, dead-rule detection, path-traversal guards
- [x] 03-04-PLAN.md — Contract tests + __init__ lazy exports: round-trip classify() through render_note/render_moc

### Phase 4: Merge Engine
**Goal**: Re-running graphify on a vault with existing notes updates graphify-owned fields without overwriting user-edited fields, in a deterministic, git-friendly way
**Depends on**: Nothing (independently buildable)
**Requirements**: MRG-01, MRG-02, MRG-06, MRG-07
**Success Criteria** (what must be TRUE):
  1. A user-edited `rank` or `mapState` frontmatter field survives a graphify re-run unchanged
  2. Running graphify with `merge_strategy: skip` leaves existing note files completely untouched
  3. Running graphify with `merge_strategy: replace` overwrites the full note including user-edited fields
  4. Frontmatter field ordering in updated notes matches the original ordering, producing minimal git diff noise
**Plans:** 6 plans

Plans:
- [x] 04-01-PLAN.md — Wrap Phase 2 section builders in sentinel HTML comments so merge can detect graphify-owned body regions (unblocks D-62 fingerprint + D-67/D-68 round-trip)
- [x] 04-02-PLAN.md — Extend _DEFAULT_PROFILE.merge with `created` preserve + `field_policies` default + validate_merge_config schema
- [ ] 04-03-PLAN.md — merge.py dataclasses, hand-rolled YAML reader (inverse of _dump_frontmatter), sentinel parser, _DEFAULT_FIELD_POLICIES table, policy dispatcher
- [ ] 04-04-PLAN.md — compute_merge_plan pure function + 7 vault test fixtures (empty, pristine, user_extended, fingerprint_stripped, malformed_sentinel, preserve_fields_edited, unmanaged_collision)
- [ ] 04-05-PLAN.md — apply_merge_plan atomic writes (.tmp + fsync + os.replace), content-hash skip, stale .tmp cleanup, MergeResult, graphify/__init__.py lazy exports
- [ ] 04-06-PLAN.md — TestPhase4MustHaves: M1..M10 end-to-end tests covering every success criterion + D-63/D-68/D-69/D-72 edge cases + T-04-01 security assertion

### Phase 5: Integration & CLI
**Goal**: All four modules are wired into a refactored `to_obsidian()` that passes existing tests; `--dry-run` and `--validate-profile` are available from the CLI
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4
**Requirements**: PROF-05, MRG-03, MRG-05
**Success Criteria** (what must be TRUE):
  1. Running `graphify --validate-profile <vault-path>` prints pass/fail with actionable messages and exits without writing any files
  2. Running `graphify --obsidian --dry-run` prints the full plan of files to create or update without writing any files
  3. Running `graphify --obsidian` against a vault with no `.graphify/` directory produces output backward-compatible with the pre-existing `to_obsidian()` behavior and all existing tests pass
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

Note: Phases 2 and 4 have no cross-module dependencies; they can be planned and built in parallel with Phase 1 if desired, but Phase 3 requires Phase 1 outputs.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planning complete | - |
| 2. Template Engine | 0/4 | Planning complete | - |
| 3. Mapping Engine | 4/4 | Complete    | 2026-04-11 |
| 4. Merge Engine | 0/6 | Planning complete | - |
| 5. Integration & CLI | 0/TBD | Not started | - |
