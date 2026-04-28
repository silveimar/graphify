# Domain Pitfalls: v1.8 Output Taxonomy & Cluster Quality

**Domain:** graphify configurable Obsidian adapter output migration
**Researched:** 2026-04-28
**Overall confidence:** HIGH for codebase-specific risks; MEDIUM for final phase assignment because v1.8 phases are not yet locked.

## Executive Summary

v1.8 changes the identity of generated vault notes: where they are written, which communities become MOCs, how concept MOCs are named, how god nodes are classified, and how repo identity appears in filenames/tags/manifests. The shipped adapter already has good primitives for path confinement, safe filenames, safe frontmatter, template validation, user-modified detection, and sentinel preservation. The main risk is bypassing those primitives while introducing new identity rules.

The most dangerous failure mode is treating a folder/name taxonomy change as a simple re-render. Existing `vault-manifest.json` entries are keyed by vault-relative paths; if v1.8 moves notes from the legacy Atlas layout into Graphify-owned folders, the merge engine may see old files as unrelated and create new files while old user-edited notes remain stranded. That is data-safe but operationally confusing unless migration code and docs explicitly surface the old paths as orphans and explain the expected duplication window.

The second major risk is conflating cluster quality with existing `mapping.moc_threshold`. Today `cluster()` always returns isolates as singleton communities, while `mapping._assemble_communities()` decides which communities get MOCs and where below-threshold nodes are routed. A new `clustering.min_community_size` must not delete communities or remove nodes from `communities`; it should only suppress standalone community/MOC output while still assigning every note to a host or bucket.

The third major risk is adding LLM concept naming in a way that breaks determinism. The output pipeline is intentionally deterministic across dry-runs and re-runs. Concept names must be cached by a stable graph signature and must always have a deterministic fallback that is sanitized before use in filenames, wikilinks, tags, Dataview queries, and frontmatter.

## Phase Names Used Below

Suggested phase ownership for planning:

| Phase | Scope |
|-------|-------|
| Phase A: Default Output Taxonomy | Built-in profile layout, note classes, folder/tag defaults |
| Phase B: Cluster Quality Floor | `clustering.min_community_size`, isolate/tiny-community routing, MOC-only community output |
| Phase C: Concept Naming Cache | Hybrid LLM/fallback concept naming and deterministic cache |
| Phase D: God Nodes + Repo Identity | CODE notes, concept MOCs, bidirectional links, repo identity precedence |
| Phase E: Migration Guide + CLI Docs | Real `work-vault` -> `ls-vault` update path, dry-run checklist, docs/tests |

## Critical Pitfalls

### 1. Taxonomy Migration Creates Duplicate Notes Instead of Updates

**Priority:** P0
**Likely phase:** Phase A, Phase E

**What goes wrong:** Moving the default layout under Graphify-owned folders changes target paths. The merge manifest is keyed by relative path, so existing notes such as `Atlas/Dots/Things/Foo.md` will not match new paths such as `Graphify/Code/Foo.md`. Graphify creates new notes and old notes are not marked user-modified or updated.

**Why it happens:** `to_obsidian()` loads `vault-manifest.json` from `notes_dir.parent`, renders notes to current `target_path`, and calls `compute_merge_plan()` without passing `previously_managed_paths`. The merge engine only detects orphans when callers supply previous paths.

**Warning signs:**
- Dry-run shows many `CREATE` actions and no `ORPHAN` actions after only changing defaults.
- Existing user-edited Atlas notes are left behind with no migration explanation.
- `vault-manifest.json` retains old keys that no longer correspond to rendered paths.

**Prevention:**
- In the migration phase, load old manifest paths and pass them to orphan detection or produce a separate migration report.
- Never auto-delete legacy notes. Use `ORPHAN` reporting plus docs that explain manual review.
- Add an explicit "layout changed" dry-run summary showing old path -> new path where node IDs match.
- Keep `--dry-run` as the required first step in docs for real vault updates.

**Guardrail tests:**
- Seed a vault with an old manifest entry and a user-edited legacy note. Run v1.8 default layout dry-run and assert old path is surfaced as `ORPHAN` or in a migration report, not silently ignored.
- Assert a real run creates the new note but does not delete or modify the old note.
- Assert user-modified detection still protects a note when the path does not change.

### 2. MOC-Only Community Output Leaves Legacy `_COMMUNITY_*` Notes Unaccounted For

**Priority:** P0
**Likely phase:** Phase A, Phase B, Phase E

**What goes wrong:** v1.8 intends to replace `_COMMUNITY_*` overview notes with MOC-only community output, but the current renderer still supports both `moc` and `community` note types. Profiles or mapping changes could continue to produce `type: community`, while legacy community overview files remain in the vault.

**Why it happens:** `to_obsidian()` dispatches `render_moc()` for note_type `moc`; otherwise it falls back to `render_community_overview()`. `templates.py` still has built-in required placeholders and templates for both `moc` and `community`.

**Warning signs:**
- New default output contains both `type: moc` and `type: community` notes.
- Tests pass because `community` remains a known note type, but real vault users see duplicate community pages.
- Legacy `_COMMUNITY_*` notes are neither updated nor called out as legacy artifacts.

**Prevention:**
- Make "MOC-only" a default-profile behavior, not a total deletion of `community` support, unless breaking custom profiles is intentional.
- Keep `community` as a valid legacy/custom note type only if needed for existing profiles; mark it deprecated in docs.
- Ensure default classification never emits `note_type="community"`.
- Migration guide must include a "Legacy community overview notes" section with safe manual cleanup steps.

**Guardrail tests:**
- Default `to_obsidian()` output for a multi-community graph contains no `type: community`.
- No generated default filename starts with `_COMMUNITY_`.
- A custom profile that still maps to `community` either validates with a deprecation warning or is rejected with a targeted error, depending on the chosen compatibility policy.

### 3. `clustering.min_community_size` Accidentally Drops Nodes

**Priority:** P0
**Likely phase:** Phase B

**What goes wrong:** A cluster-quality floor is implemented by filtering entries out of the `communities` dict. Nodes in suppressed communities lose `node_to_community`, do not get `parent_moc_label`/`community_tag`, and may render as orphan statements with broken navigation.

**Why it happens:** `cluster()` is the topology stage and already returns isolates as singleton communities. `mapping._assemble_communities()` is the routing stage that knows how to collapse below-threshold communities into host MOCs or the `Uncategorized` bucket. The new feature belongs in routing/output semantics unless the graph JSON contract is intentionally changed.

**Warning signs:**
- Isolated nodes disappear from Obsidian output.
- Node notes lack `community` frontmatter or `community/*` tags.
- `score_all()` no longer has entries for every original community.
- Graph JSON/HTML communities differ unexpectedly from Obsidian communities.

**Prevention:**
- Treat `clustering.min_community_size` as "minimum size for standalone community MOC", not "minimum size to exist".
- Keep all nodes in `communities`; route tiny communities to nearest host or bucket.
- Define precedence between existing `mapping.moc_threshold` and new `clustering.min_community_size`. Prefer one canonical setting or make one an alias with deprecation.
- Validate bool-before-int and minimum value just like `mapping.moc_threshold`.

**Guardrail tests:**
- Graph with isolates and 2-node clusters: all non-skipped nodes still render notes.
- Only communities meeting the floor get standalone MOCs.
- Tiny connected communities with host edges appear in `sub_communities`; hostless tiny communities appear under `Uncategorized`.
- `clustering.min_community_size: true`, `0`, negative, and string values are rejected.

### 4. Hybrid Concept Naming Breaks Determinism

**Priority:** P0
**Likely phase:** Phase C

**What goes wrong:** Concept MOC names change across runs because LLM naming is nondeterministic, cache keys are unstable, or fallbacks depend on community IDs that are re-indexed by size. This causes file churn, broken wikilinks, stale manifest entries, and duplicated notes.

**Why it happens:** `cluster()` re-indexes communities by size, and current community labels default to the top real node label. Concept naming introduces an external model and a new cache surface. If the cache key is just `community_id`, any reorder invalidates naming.

**Warning signs:**
- Running `--dry-run` twice on the same graph reports CREATE/UPDATE churn.
- Concept MOC filenames change when an unrelated community changes size.
- Cached names survive after member labels or repo identity change.

**Prevention:**
- Cache concept names by a stable signature: sorted member node IDs, sorted sanitized labels, edge fingerprint, repo identity, and naming algorithm version.
- Keep deterministic fallback available and tested with no API/model configured.
- Use `safe_filename`, `safe_tag`, `_sanitize_wikilink_alias`, and `safe_frontmatter_value` on all model output before it reaches disk or Markdown.
- Store naming cache in graphify artifacts, not inside the generated notes folder.

**Guardrail tests:**
- No-LLM run produces the same concept MOC name across two processes.
- Same graph with reordered community dict produces the same concept filenames.
- A concept name containing `]]`, `|`, newlines, backticks, `---`, or `../` cannot break wikilinks, frontmatter, or paths.
- Changing member labels invalidates or version-bumps the cache entry.

### 5. Two-Class God-Node Taxonomy Collides on Filename and Links

**Priority:** P0
**Likely phase:** Phase D

**What goes wrong:** Code-derived god nodes and concept MOCs share labels and resolve to the same filename. One overwrites the other or the merge layer indexes both rendered notes to the same path. Bidirectional links then point to the wrong note class.

**Why it happens:** Current mapping skips concept nodes unconditionally and maps god nodes to `thing` by topology fallback. Filename resolution is label-based. `apply_merge_plan()` indexes rendered notes by resolved path, so duplicate paths can silently select the last rendered note unless collisions are detected earlier.

**Warning signs:**
- A code god node and concept MOC named `Cache` produce one `Cache.md`.
- A dry-run action count is smaller than the number of rendered notes.
- CODE notes link to themselves or to an unrelated concept MOC.

**Prevention:**
- Make note class part of the filename namespace: e.g. `CODE_<repo>_<label>.md` for code-derived notes and concept MOC names without `CODE_`.
- Add duplicate target-path detection before `compute_merge_plan()` and fail as `SKIP_CONFLICT` or raise with actionable details.
- Generate bidirectional links from resolved filenames, not raw labels.
- Keep concept MOCs out of per-node `render_note()` unless concept nodes are intentionally reintroduced to mapping.

**Guardrail tests:**
- Same label code node and concept MOC produce two distinct files.
- CODE note contains a link to concept MOC and concept MOC contains backlink to CODE note.
- Duplicate target paths are detected before writing, with no silent overwrite.

### 6. Repo Identity Precedence Is Ambiguous or Unsanitized

**Priority:** P0
**Likely phase:** Phase D

**What goes wrong:** Repo identity appears inconsistently in code-note names, tags, and manifests, or unsafe repo strings create invalid filenames/tags. CLI flag, profile key, and auto-derived fallback may disagree.

**Why it happens:** The CLI already has one precedence system for output (`--output > profile > defaults`). v1.8 adds another precedence system: CLI repo identity > profile key > auto-derived fallback. If this is implemented in multiple places, code-note filenames, frontmatter, and manifest entries can drift.

**Warning signs:**
- `--repo-id foo` changes filenames but not tags or manifests.
- A GitHub URL or filesystem path leaks into tags.
- Running outside a git repo produces empty or `unknown` filenames that collide across projects.

**Prevention:**
- Resolve repo identity once and pass the resolved value through export/render code.
- Add a profile schema key for repo identity and validate it as a non-empty string with no control characters.
- Sanitize identity separately for display, tag component, and filename component.
- Emit the resolved source in dry-run/summary: `repo_identity=... (source=cli|profile|auto)`.

**Guardrail tests:**
- CLI flag overrides profile; profile overrides git/dirname fallback; fallback is stable when no git remote exists.
- Repo identity with `/`, `:`, spaces, Unicode separators, or shell-looking content cannot escape paths or break tags.
- CODE note filename, frontmatter, tag, and manifest all use the same resolved identity.

## Moderate Pitfalls

### 7. New Frontmatter Keys Become Stale Because Unknown Keys Default to Preserve

**Priority:** P1
**Likely phase:** Phase A, Phase C, Phase D

**What goes wrong:** New graphify-owned fields such as `repo_identity`, `graphify_note_class`, `concept_name`, `concept_signature`, or `graphify_version` are emitted once but never update on rerun.

**Why it happens:** `_resolve_field_policy()` defaults unknown keys to `preserve`. That is right for user fields, but wrong for new graphify-owned identity fields unless they are added to `_DEFAULT_FIELD_POLICIES`.

**Prevention:**
- Add every new graphify-owned scalar to `_DEFAULT_FIELD_POLICIES` as `replace`.
- Add graphify-owned lists to `union` only when user extension is desired; otherwise use `replace`.
- Update `_CANONICAL_KEY_ORDER` so new fields slot consistently.

**Guardrail tests:**
- Existing generated note with old `repo_identity` updates when rerendered with a new resolved identity.
- Field order remains stable and only expected lines change.

### 8. Template Validation Rejects New Placeholders or Lets Unsafe Content Through

**Priority:** P1
**Likely phase:** Phase A, Phase C, Phase D

**What goes wrong:** Built-in or vault templates need `${repo_identity}`, `${concept_name}`, `${code_links}`, or `${concept_links}`, but `KNOWN_VARS` does not include them. User templates fall back to built-ins or fail preflight. The opposite risk is injecting raw LLM/repo values into templates without the existing sanitizers.

**Why it happens:** `templates.py` intentionally uses a locked placeholder vocabulary and validates templates before rendering.

**Prevention:**
- Add new placeholders atomically to `KNOWN_VARS`, required placeholder sets where appropriate, substitution contexts, and tests.
- Keep block expansion before substitution so labels/model output cannot inject template logic.
- Pre-render link lists using sanitized wikilink helpers.

**Guardrail tests:**
- `--validate-profile` accepts valid templates using new placeholders.
- Unknown placeholders are still rejected.
- Concept/repo strings containing `${x}`, `{{#if_god_node}}`, or `{{/if}}` render as text, not template logic.

### 9. Graphify-Owned Layout Breaks Dataview Queries and Tags

**Priority:** P1
**Likely phase:** Phase A, Phase E

**What goes wrong:** MOCs render, but Dataview queries return no results because folders or tags changed. Users see empty MOCs and assume extraction failed.

**Why it happens:** Default MOC query currently filters by `#community/${community_tag}`. New Graphify-owned folders may change folder assumptions but should not change the `community/<slug>` invariant unless all templates and docs change together.

**Prevention:**
- Preserve `community/<slug>` tag behavior unless there is a strong reason to change it.
- If folder filters are added, use `${folder}` through `_build_dataview_block()` and strip fence-breaking characters.
- Migration docs should include "Dataview may need refresh/reindex" and example queries for the new layout.

**Guardrail tests:**
- Generated MOC includes non-empty Dataview block targeting the same tag emitted by member notes.
- Adversarial community names cannot inject into Dataview fences.

### 10. Profile Schema Additions Are Not Atomic

**Priority:** P1
**Likely phase:** Phase B, Phase C, Phase D

**What goes wrong:** New keys such as `clustering`, `concept_naming`, or `repo_identity` are added to defaults but not `_VALID_TOP_LEVEL_KEYS`, or validation accepts them but `load_profile()` does not merge/use them.

**Why it happens:** The profile module requires every new profile surface to land in several places: default profile, valid top-level keys, validation, preflight output if user-visible, and tests.

**Prevention:**
- Add an atomicity test for each new section: present in `_VALID_TOP_LEVEL_KEYS`, validates cleanly in `_DEFAULT_PROFILE`, malformed values rejected.
- Follow existing bool-before-int validation patterns.

**Guardrail tests:**
- `_DEFAULT_PROFILE` validates cleanly after adding v1.8 keys.
- Empty profile still gets defaults.
- Unknown profile keys are still rejected.

### 11. Dry-Run Understates Migration Risk

**Priority:** P1
**Likely phase:** Phase E

**What goes wrong:** `--dry-run` prints ordinary CREATE/UPDATE counts but does not explain that a taxonomy migration is happening, which legacy paths are unmanaged, or which notes require manual review.

**Why it happens:** `format_merge_plan()` is generic and path-action oriented. It has no taxonomy-specific context unless v1.8 supplies it.

**Prevention:**
- Add a migration-specific preamble when old manifest paths or legacy `_COMMUNITY_*` notes are detected.
- Keep the existing six action rows for compatibility, but append a "Migration notes" section.
- Include repo identity source and notes directory source in CLI output.

**Guardrail tests:**
- Dry-run against a legacy fixture mentions old layout, new layout, and legacy community overview files.
- Dry-run remains read-only: no `.tmp`, manifest, or note writes.

### 12. Skill/CLI Drift Leaves the Real Pipeline Behind

**Priority:** P1
**Likely phase:** Phase E

**What goes wrong:** Library tests pass, but the agent skill still calls old pipeline variables or omits new args such as repo identity, concept naming cache location, or min community size.

**Why it happens:** Project decision D-73 says the skill is the full pipeline driver; `graphify --obsidian` is a utility over an existing graph. Changes in `export.py` alone may not affect normal `/graphify` usage.

**Prevention:**
- Update all platform skill variants that invoke Obsidian export.
- Add drift-lock tests similar to prior platform skill tests if new CLI flags or response persistence blocks are added.
- Keep CLI utility and skill pipeline behavior aligned in fixtures.

**Guardrail tests:**
- End-to-end skill-equivalent Python block passes `community_labels`, `cohesion`, resolved repo identity, and min community settings consistently.
- `graphify --help` documents any new flags.

### 13. Concept Naming Cache Is Written Into the Vault and Self-Ingested

**Priority:** P1
**Likely phase:** Phase C, Phase E

**What goes wrong:** Concept naming cache files appear in Obsidian, get indexed by future graphify runs, or show up as user notes.

**Why it happens:** The output resolver separates `notes_dir` and `artifacts_dir`, but feature code may choose the convenient notes path.

**Prevention:**
- Store caches under graphify artifacts, e.g. `graphify-out/cache/` or a dedicated `concept-names.json`.
- Use atomic write patterns for cache updates.
- Ensure output-manifest/exclude logic ignores cache artifacts.

**Guardrail tests:**
- Concept naming cache is not under `notes_dir`.
- Self-ingest dry-run does not include concept naming cache files.

### 14. Filename Collision Detection Remains Implicit

**Priority:** P1
**Likely phase:** Phase A, Phase C, Phase D

**What goes wrong:** Two rendered notes produce the same resolved path. Because merge/apply lookups are path-based at later stages, one rendered note can shadow another.

**Why it happens:** `rendered_notes` is keyed by node ID/synthetic MOC ID, but `apply_merge_plan()` builds `notes_by_path` and later path collisions are ambiguous.

**Prevention:**
- Add a pre-merge duplicate target path check in `to_obsidian()` after all rendered notes are built.
- Collision error should include both note IDs, labels, note classes, and target path.
- CODE/concept taxonomy should reserve distinct filename prefixes.

**Guardrail tests:**
- Two nodes with same label and same note class get deterministic disambiguation or a hard conflict.
- Code and concept same-label case never collides.

## Security Regressions to Guard

| Surface | Regression | Required guard |
|---------|------------|----------------|
| Concept names | LLM output includes path traversal, YAML delimiters, wikilink closers, or template syntax | Sanitize through filename, frontmatter, tag, and wikilink helpers; test adversarial names |
| Repo identity | Git remote/path leaks unsafe characters into filenames or tags | Resolve once; sanitize per context; reject control characters |
| New profile keys | `clustering`, `concept_naming`, or repo keys accept bool-as-int, traversal paths, or arbitrary cache paths | Validate in `profile.py`; no absolute/traversal cache paths unless intentionally artifact-confined |
| Migration writes | Legacy cleanup deletes or overwrites user notes | Never delete; use `ORPHAN`/migration report; preserve user sentinel blocks |
| Duplicate paths | Generated notes shadow each other before merge | Detect duplicate resolved target paths before write |
| Dataview/template content | Generated values break fences or execute template blocks | Keep block expansion before substitution; strip backticks/newlines from query substitutions |

## Migration-Specific Risks

### Risk: Real Vault Users Need a Step-by-Step Update Path

**Phase:** Phase E

The docs must be operational, not just descriptive. The real workflow is `work-vault` -> `ls-vault`; users need to know which directory to run from, which vault contains `.graphify/profile.yaml`, where generated notes will land, and how to inspect changes before writing.

**Required migration guide shape:**
1. Back up or commit the target vault.
2. Run `graphify --validate-profile <vault>`.
3. Run `graphify --obsidian --dry-run` with explicit output arguments matching the real workflow.
4. Review CREATE/UPDATE/SKIP/ORPHAN sections and legacy community overview notes.
5. Run the real export only after dry-run is understood.
6. Review old Atlas/`_COMMUNITY_*` notes manually; do not bulk-delete until links are checked.
7. Re-run dry-run to confirm idempotence.

**Guide tests/quality checks:**
- Commands in docs match actual `graphify --help` flags.
- Docs mention `--force` only as an escape hatch and explicitly state sentinel blocks remain protected.
- Docs explain what old files are left behind and why graphify does not delete them.

## Phase-Specific Warning Matrix

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Phase A: Default Output Taxonomy | New folders create duplicate notes and stale manifest keys | Migration-aware dry-run, orphan surfacing, no deletion |
| Phase A: MOC-only default | `community` overview output continues from default code path | Default classification emits only MOC community notes; tests assert no `type: community` |
| Phase B: Min community size | Filtering communities drops nodes | Suppress standalone MOC only; preserve node routing |
| Phase B: Existing threshold interaction | `mapping.moc_threshold` and `clustering.min_community_size` conflict | Define one precedence rule; validate both; docs explain relationship |
| Phase C: LLM concept naming | Names churn across runs | Stable signature cache plus deterministic fallback |
| Phase C: Naming safety | Model output breaks Markdown/YAML/path syntax | Sanitize every output context; adversarial tests |
| Phase D: God-node taxonomy | CODE and concept notes collide | Distinct note classes, prefixes, duplicate-path detection |
| Phase D: Repo identity | Different parts resolve identity differently | Single resolver with source reporting |
| Phase E: Migration guide | Users misinterpret duplicates as data loss | Explicit dry-run walkthrough and cleanup guidance |

## Concrete Test Suite Additions

- `tests/test_profile.py`: validate new profile sections (`clustering`, concept naming, repo identity), bool-before-int rejection, negative/zero min size rejection, safe default profile validation.
- `tests/test_export.py`: default output uses Graphify-owned folders, no default `community` overview notes, no `_COMMUNITY_*` filenames, duplicate target paths rejected.
- `tests/test_merge.py`: taxonomy migration fixture surfaces old manifest paths as orphans and never deletes legacy notes.
- `tests/test_templates.py` or existing template tests: new placeholders validate, adversarial concept/repo labels do not inject template syntax.
- `tests/test_cluster.py` or mapping tests: isolates and tiny clusters are routed but do not get standalone MOCs below the configured floor.
- CLI tests: `--repo-id` or equivalent flag precedence, `--help` text, dry-run migration preamble, and read-only dry-run behavior.

## What Might Be Missed

- The skill files may contain embedded pipeline code that bypasses new library parameters; those need a separate grep/review during planning.
- Existing docs or examples may still recommend Atlas-default paths; migration docs should update or explicitly mark old paths as legacy.
- If concept naming uses any network/LLM provider, cost ceilings and offline behavior need phase-specific review against existing routing/cache conventions.
