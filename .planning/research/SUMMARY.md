# Project Research Summary

**Project:** graphify v1.8 - Output Taxonomy & Cluster Quality
**Domain:** Obsidian vault export taxonomy, community presentation quality, and safe vault migration
**Researched:** 2026-04-28
**Confidence:** HIGH

## Executive Summary

v1.8 is a presentation-quality and migration-safety milestone for graphify's Obsidian export adapter. The core graph pipeline should remain unchanged: `detect -> extract -> build_graph -> cluster -> analyze -> report -> export`. The work belongs after clustering, where graph communities, node classes, repo identity, and templates are interpreted into vault notes through the existing profile, mapping, template, merge, dry-run, and manifest systems.

The recommended approach is conservative: add no required dependencies, keep `PyYAML` optional, extend `profile.py` as the single schema authority, and implement taxonomy changes inside the existing `to_obsidian()` path. Default exports should move into a Graphify-owned subtree, generate MOC-only community output, separate CODE notes from concept MOCs, use a deterministic cluster-quality floor, and propagate repo identity where it prevents collisions without making concept pages noisy.

The main risks are migration confusion and nondeterminism, not algorithmic difficulty. Moving from legacy Atlas and `_COMMUNITY_*` outputs can create duplicate-looking notes unless dry-run reports old managed paths as orphans or migration candidates. `clustering.min_community_size` must suppress standalone MOCs without dropping nodes from graph/community data. Concept names and repo identity must be resolved once, sanitized per context, cached by stable signatures, and surfaced in dry-run output before touching a real `work-vault` to `ls-vault` flow.

## Key Findings

### Recommended Stack

No new required stack additions are needed. v1.8 should reuse `networkx`, stdlib helpers, the existing profile/merge/template systems, and the optional `PyYAML` Obsidian extra. This is a schema, routing, naming, and documentation release rather than a new infrastructure release.

**Core technologies:**
- `graphify/profile.py`: source of truth for new user-facing config, defaults, validation, and compatibility warnings.
- `graphify/mapping.py`: right place for community routing, MOC qualification, note classes, and folded/bucketed cluster metadata.
- `graphify/templates.py`: right place for frontmatter, repo tags, naming provenance, and CODE/MOC links.
- `graphify/export.py::to_obsidian()`: composition boundary for profile loading, classification, rendering, duplicate target checks, merge planning, dry-run, and writes.
- `networkx`: sufficient for isolates, connected tiny clusters, degree-based naming inputs, and existing community scoring.
- Stdlib `json`, `hashlib`, `pathlib`, `re`, `subprocess`, `collections`, `os.replace`: enough for identity fallback, deterministic naming, and atomic cache writes.

**Non-additions:**
- Do not add `GitPython`, `Jinja2`, `python-slugify`, SQLite, vector storage, a new LLM SDK, a new clustering library, or a new Obsidian writer.
- Keep `PyYAML` optional under the Obsidian/profile extra; profile-free default export must continue to work.

### Expected Features

**Must have (table stakes):**
- Graphify-owned default layout under a generated subtree such as `Graphify/Maps`, `Graphify/Code`, `Graphify/Concepts`, and `Graphify/Sources`.
- MOC-only community output by default; no generated default `_COMMUNITY_*` overview notes.
- Canonical `clustering.min_community_size` profile key, with deterministic routing of isolates and tiny clusters into host or Uncategorized MOCs.
- Compatibility bridge for existing `mapping.moc_threshold`, with documented precedence when both settings exist.
- Stable hybrid concept naming: prefer supplied `community_labels`, otherwise use deterministic graph-derived fallback and stable cache signatures.
- Two-class god-node taxonomy: code-derived hubs become CODE notes; conceptual hubs remain concept/community MOCs.
- Repo identity precedence: CLI flag, profile key, then sanitized fallback from repo/output context.
- A real migration guide for `work-vault` to `ls-vault` covering backup, profile validation, dry-run, write, orphan review, and idempotence.

**Should have (differentiators):**
- Dry-run taxonomy summary showing CODE notes, concept MOCs, skipped/folded tiny clusters, legacy artifacts, and resolved repo identity source.
- Concept MOC naming provenance in frontmatter or metadata: `community_labels`, profile/manual, LLM/cache, or deterministic fallback.
- Identity-aware CODE filenames/tags that prevent cross-repo collisions before merge conflict handling.
- Deprecation warnings for profiles that still opt into legacy community overview output.
- Representative migration command transcript shape, not prose-only docs.

**Defer to later releases:**
- New clustering algorithm research or changes to canonical graph semantics.
- Manual LLM naming approval queues or network-dependent naming as a required path.
- Automatic deletion/relocation of legacy vault files.
- Obsidian plugin behavior or `.obsidian/graph.json` management.

### Architecture Approach

Treat every v1.8 feature as downstream export interpretation. Do not modify `extract.py`, `build.py`, or the canonical `cluster()` contract unless a specific blocker appears. Preserve graph data and derive vault presentation through profile-driven mapping, rendering, and merge planning.

**Major components:**
1. `profile.py` - add and validate v1.8 config sections; preserve custom profile overrides and old threshold readability.
2. `naming.py` - pure deterministic helpers for repo identity normalization and concept/community name resolution.
3. `mapping.py` - apply cluster-quality floor, MOC-only default routing, note classes, folded/bucketed communities, and related context.
4. `templates.py` - render CODE notes, concept MOCs, new frontmatter fields, repo tags, naming provenance, and bidirectional links.
5. `export.py` - thread repo identity and concept-name metadata, detect duplicate target paths, preserve merge safety, and improve dry-run/migration reporting.
6. `__main__.py` and skill files - expose repo identity and keep agent-driven Obsidian export aligned with library behavior.
7. Docs - add `docs/MIGRATING_V1_8.md` or equivalent with the real vault migration path.

### Critical Pitfalls

1. **Taxonomy migration silently strands legacy notes** - load previous manifest paths, surface old Atlas and `_COMMUNITY_*` files as ORPHAN or migration-report entries, and never auto-delete user notes.
2. **MOC-only output still emits legacy community notes** - make MOC-only a default-profile behavior, keep custom legacy support only if intentionally compatible, and test that defaults produce no `type: community` or `_COMMUNITY_*` files.
3. **Cluster-quality floor drops nodes** - interpret the floor as "minimum size for standalone MOC," not "minimum size to exist"; preserve all communities and route tiny ones to host or bucket MOCs.
4. **Concept naming churns** - key caches by stable member/content signatures, not community IDs; always provide deterministic fallback and sanitize model or label output for filenames, tags, wikilinks, Dataview, and frontmatter.
5. **CODE and concept notes collide** - reserve filename namespaces such as `CODE_<repo>_<symbol>` for code-derived notes, generate links from resolved filenames, and detect duplicate target paths before merge planning.
6. **Repo identity drifts or leaks unsafe strings** - resolve identity once, record source, sanitize separately for display/tag/filename/manifest, and ensure CLI overrides profile overrides fallback.

## Implications for Roadmap

### Phase 1: Profile Contract & Defaults

**Rationale:** All later behavior depends on stable config names, defaults, and validation.
**Delivers:** Graphify-owned default folders, `clustering.min_community_size`, concept naming settings, god-node split settings, repo identity profile key, and compatibility behavior for `mapping.moc_threshold`.
**Addresses:** Default output taxonomy, cluster-quality floor contract, custom profile override preservation.
**Avoids:** Profile schema sprawl, non-atomic key additions, bool-as-int validation bugs, and accidental required dependency changes.

### Phase 2: Naming & Repo Identity Helpers

**Rationale:** Names and identity affect filenames, tags, frontmatter, links, manifests, and cache keys; they should be pure and tested before rendering changes.
**Delivers:** `naming.py` or equivalent pure helpers, stable concept signatures, deterministic fallback names, atomic JSON cache support if cache ships, and a single repo identity resolver with source reporting.
**Uses:** Stdlib `hashlib`, `json`, `re`, `subprocess`, `os.replace`, existing `safe_filename`, `safe_tag`, and `sanitize_label`.
**Avoids:** LLM nondeterminism, repo URL leakage, cross-run filename churn, and cache invalidation tied to unstable community IDs.

### Phase 3: Mapping, Cluster Quality & Note Classes

**Rationale:** This is the main behavioral phase, and it should happen before template/export plumbing so contexts are explicit.
**Delivers:** MOC qualification, isolate/tiny-cluster folded or bucketed routing, MOC-only default `note_type`, CODE vs concept note classification, parent/related MOC context, and duplicate namespace metadata.
**Addresses:** MOC-only communities, cluster-quality floor, two-class god-node taxonomy.
**Avoids:** Dropped nodes, broken community tags, default legacy community output, and code/concept classification drift.

### Phase 4: Templates, Export Plumbing & Dry-Run Visibility

**Rationale:** Once classification is stable, rendering and merge planning can safely expose the new taxonomy.
**Delivers:** Graphify-owned paths, CODE note frontmatter/tags, concept MOC naming provenance, bidirectional CODE/MOC links, repo identity in manifests, duplicate target-path detection, and taxonomy-aware dry-run summaries.
**Implements:** Existing `render_note`, `render_moc`, merge plan, manifest, and dry-run paths with new contexts.
**Avoids:** Silent overwrites, stale graphify-owned frontmatter, empty Dataview queries, and dry-run output that understates migration risk.

### Phase 5: Migration Guide, Skill Alignment & Regression Sweep

**Rationale:** The milestone goal includes safe real-vault use, and graphify's skill files may drive the normal pipeline more than the standalone CLI.
**Delivers:** `work-vault` to `ls-vault` migration guide, updated README/config docs, updated platform skill variants if they invoke Obsidian export, and focused regression tests.
**Addresses:** Safe migration, legacy cleanup guidance, dry-run-first workflow, and user-facing command consistency.
**Avoids:** Library/skill drift, destructive cleanup, stale Atlas examples, and confusion when legacy files remain as expected orphans.

### Suggested Requirement Categories

- Default output taxonomy and folder ownership.
- Community output semantics and MOC-only defaults.
- Cluster-quality floor and compatibility with `mapping.moc_threshold`.
- Concept naming determinism, provenance, cache behavior, and sanitization.
- God-node taxonomy, CODE note namespace, and CODE/MOC links.
- Repo identity precedence, propagation, and collision avoidance.
- Migration guide, dry-run reporting, orphan handling, and non-destructive rollout.
- Validation, merge safety, path safety, template safety, and regression coverage.

### Phase Ordering Rationale

- Profile contract first prevents later phases from inventing private config knobs.
- Naming and identity before mapping avoids repeating sanitization and precedence logic across files.
- Mapping before templates keeps behavioral policy separate from Markdown rendering.
- Export/dry-run before docs lets the migration guide describe real output and action names.
- Skill/docs last ensures the library behavior is already tested before agent guidance is updated.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4:** Existing merge manifest/orphan mechanics around old managed paths may need code-level research before designing migration reporting.
- **Phase 5:** Platform skill variants may contain embedded Obsidian export logic and need a drift audit.
- **Any phase that ships LLM naming:** confirm offline behavior, cost ceiling, cache invalidation, and rejection/sanitization rules.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Profile defaults, `_VALID_TOP_LEVEL_KEYS`, validation, and bool-before-int patterns are established.
- **Phase 2:** Deterministic stdlib helpers and atomic JSON cache writes follow existing cache/manifest conventions.
- **Phase 3:** Community routing belongs in existing mapping/classification flow; no new algorithm research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All requested behavior maps to existing stdlib, NetworkX, profile, export, merge, and cache patterns; no required dependency is justified. |
| Features | HIGH | Table stakes and anti-features are well-scoped around the v1.8 goal and existing v1.7 adapter capabilities. |
| Architecture | HIGH | Module boundaries are clear: downstream export interpretation, not extraction/build/cluster changes. Exact folder names remain a product choice. |
| Pitfalls | HIGH | Risks are codebase-specific and include concrete guardrail tests; phase assignment is medium until roadmap is locked. |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact default folder names:** roadmapper should lock the final Graphify-owned layout before requirements are finalized.
- **Config key naming:** research differs between `clustering.min_community_size` and a broader `cluster_quality.min_members` shape; requirements should choose one canonical public key and define compatibility with `mapping.moc_threshold`.
- **Legacy overview policy:** decide whether `community` note type remains custom-profile opt-in indefinitely or receives a deprecation window.
- **LLM concept naming scope:** decide whether v1.8 ships only deterministic fallback or includes cached LLM-provided labels when upstream skill context supplies them.
- **Migration implementation depth:** decide whether v1.8 includes documentation-only guidance or a dry-run migration report that maps old paths to new paths by note identity.
- **Research-file hygiene:** `FEATURES.md` and `PITFALLS.md` were cleaned so the committed research set is v1.8-only.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` - stack decisions, non-additions, integration points, dependency implications.
- `.planning/research/FEATURES.md` - v1.8 table stakes, differentiators, anti-features, requirement groups, MVP recommendation.
- `.planning/research/ARCHITECTURE.md` - export-boundary architecture, profile shape, data flow, build order, invariants, tests.
- `.planning/research/PITFALLS.md` - migration, cluster-quality, naming, taxonomy, repo identity, template, and dry-run guardrails.

### Secondary (MEDIUM confidence)
- Existing codebase conventions summarized in project context: `profile.py`, `mapping.py`, `templates.py`, `merge.py`, `export.py`, `cluster.py`, `analyze.py`, `security.py`.

### Tertiary (needs validation)
- Final product choices: folder names, public config shape, LLM naming inclusion, and migration-report depth.

---
*Research completed: 2026-04-28*
*Ready for roadmap: yes*
