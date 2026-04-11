# Requirements: Configurable Obsidian Vault Adapter

**Defined:** 2026-04-09
**Core Value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Profile System

- [x] **PROF-01**: User can place a `.graphify/profile.yaml` in their vault and graphify discovers it automatically
- [x] **PROF-02**: When no vault profile exists, graphify uses a built-in default profile producing Ideaverse ACE-compatible output
- [x] **PROF-03**: Vault profile merges over defaults (partial overrides work — user only specifies what differs)
- [x] **PROF-04**: Profile schema validation produces actionable error messages on invalid configuration
- [x] **PROF-05**: User can run `graphify --validate-profile <vault-path>` to check profile validity without generating output
- [x] **PROF-06**: Profile YAML schema supports: folder_mapping, mapping_rules, merge behavior, naming conventions, obsidian config sections

### Note Generation

- [ ] **GEN-01**: Generated notes have YAML frontmatter with configurable fields (default: `up:`, `related:`, `collections:`, `tags:`, `created:`)
- [ ] **GEN-02**: All inter-note references use `[[wikilink]]` format with proper deduplication and label sanitization
- [ ] **GEN-03**: User can provide custom markdown templates in `.graphify/templates/` that override built-in templates per note type
- [ ] **GEN-04**: Built-in templates exist for: MOC, Dot/Thing, Dot/Statement, Dot/Person, Source, Community Overview
- [ ] **GEN-05**: MOC notes include embedded Dataview queries that dynamically list community members
- [ ] **GEN-06**: Notes include wayfinder navigation elements linking to parent MOC and related communities
- [ ] **GEN-07**: File naming follows configurable convention (title_case, kebab-case, preserve original label)

### Mapping & Placement

- [ ] **MAP-01**: Notes are placed in folders defined by `profile.yaml` `folder_mapping` (e.g., MOCs → `Atlas/Maps/`, Things → `Atlas/Dots/Things/`)
- [ ] **MAP-02**: Topology-based classification: god nodes → Things, communities above threshold → MOCs, source files → Sources, default → Statements
- [ ] **MAP-03**: Attribute-based classification: node content attributes (e.g., `file_type: person`) override topology classification per profile rules
- [ ] **MAP-04**: Mapping rules support dual evaluation: attribute rules take precedence, then topology rules, then default
- [ ] **MAP-05**: Community-to-MOC threshold is configurable (default: 3 members); below threshold, community collapses to list in parent MOC
- [ ] **MAP-06**: Source files route to sub-folders by file type when profile specifies routing rules (e.g., Books/, Code/, Papers/)

### Merge & Safety

- [x] **MRG-01**: Re-running graphify on a vault with existing notes updates graphify-owned fields while preserving user-edited fields
- [x] **MRG-02**: `preserve_fields` list in profile specifies frontmatter fields that graphify never overwrites (default: `rank`, `mapState`, `tags`)
- [x] **MRG-03**: User can run `graphify --obsidian --dry-run` to preview all changes without writing any files
- [x] **MRG-04**: All profile-derived file paths are validated against path-traversal attacks (no writing outside vault directory)
- [ ] **MRG-05**: When no vault profile exists, output is backward-compatible with current `to_obsidian()` behavior
- [x] **MRG-06**: Frontmatter field ordering is preserved on update to minimize git diff noise
- [x] **MRG-07**: User can configure merge strategy per profile: `update` (default), `skip` (don't touch existing), or `replace` (overwrite entirely)

### Obsidian Config

- [x] **OBS-01**: `.obsidian/graph.json` community color groups use correct `tag:community/Name` syntax (fix existing `tag:#` bug)
- [x] **OBS-02**: `graph.json` generation uses read-merge-write strategy to preserve user's existing color groups and settings

### Pre-existing Bug Fixes

- [x] **FIX-01**: Fix YAML frontmatter injection via node labels containing special characters (`:`, `#`, `[`, `]`)
- [x] **FIX-02**: Fix non-deterministic filename deduplication (sort nodes by `(source_file, label)` before assignment)
- [x] **FIX-03**: Fix shallow tag sanitization (handle `/`, `+`, digits-at-start in community names)
- [x] **FIX-04**: Add NFC Unicode normalization to filenames to prevent cross-platform duplicates
- [x] **FIX-05**: Cap filename length at 200 characters to prevent OS path limit issues

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Templating

- **TMPL-01**: Conditional template sections (`{{#if_god_node}}...{{/if}}` guards)
- **TMPL-02**: Loop blocks for connections (`{{#connections}}...{{/connections}}`)
- **TMPL-03**: Custom Dataview query templates per note type in profile

### Advanced Configuration

- **CFG-01**: Custom color palettes in profile for graph.json
- **CFG-02**: Profile includes/extends mechanism (compose profiles from fragments)
- **CFG-03**: Per-community template overrides (specific communities get custom templates)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vault framework generation (ACE, Sefirot, Guitton, LSA) | Separate project — graphify injects into existing frameworks |
| Wiki article generation integration | Existing separate system (`wiki.py`), not part of this adapter |
| Calendar and Efforts population | graphify produces knowledge (Atlas-equivalent), not time/action data |
| Obsidian plugin development | Output is standard markdown + frontmatter |
| Real-time sync or watch mode | This is a batch injection operation |
| Two-way sync (vault changes → graph) | Unidirectional: graph → vault only |
| Jinja2 template engine | Adds dependency, RCE risk via vault-supplied templates |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROF-01 | Phase 1 | Complete |
| PROF-02 | Phase 1 | Complete |
| PROF-03 | Phase 1 | Complete |
| PROF-04 | Phase 1 | Complete |
| PROF-05 | Phase 5 | Complete |
| PROF-06 | Phase 1 | Complete |
| GEN-01 | Phase 2 | Pending |
| GEN-02 | Phase 2 | Pending |
| GEN-03 | Phase 2 | Pending |
| GEN-04 | Phase 2 | Pending |
| GEN-05 | Phase 2 | Pending |
| GEN-06 | Phase 2 | Pending |
| GEN-07 | Phase 2 | Pending |
| MAP-01 | Phase 3 | Pending |
| MAP-02 | Phase 3 | Pending |
| MAP-03 | Phase 3 | Pending |
| MAP-04 | Phase 3 | Pending |
| MAP-05 | Phase 3 | Pending |
| MAP-06 | Phase 3 | Pending |
| MRG-01 | Phase 4 | Complete |
| MRG-02 | Phase 4 | Complete |
| MRG-03 | Phase 5 | Complete |
| MRG-04 | Phase 1 | Complete |
| MRG-05 | Phase 5 | Pending |
| MRG-06 | Phase 4 | Complete |
| MRG-07 | Phase 4 | Complete |
| OBS-01 | Phase 1 | Complete |
| OBS-02 | Phase 1 | Complete |
| FIX-01 | Phase 1 | Complete |
| FIX-02 | Phase 1 | Complete |
| FIX-03 | Phase 1 | Complete |
| FIX-04 | Phase 1 | Complete |
| FIX-05 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after roadmap confirmation*
