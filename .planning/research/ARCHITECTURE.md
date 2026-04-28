# Architecture Research: v1.8 Output Taxonomy & Cluster Quality

**Project:** graphify v1.8 Output Taxonomy & Cluster Quality  
**Researched:** 2026-04-28  
**Scope:** Integrate output taxonomy, cluster-quality floor, concept naming, code/concept note split, repo identity, and migration guidance into the existing graphify architecture.  
**Overall confidence:** HIGH for module boundaries and data flow; MEDIUM for exact default folder names, which the roadmap still needs to lock.

## Executive Recommendation

Treat v1.8 as an Obsidian export and presentation-quality milestone, not as a graph-construction milestone. The core `detect -> extract -> build_graph -> cluster -> analyze -> report -> export` pipeline should remain intact. New v1.8 behavior should be derived after clustering and flow through the existing profile-driven Obsidian adapter:

```text
detect -> extract -> build_graph -> cluster -> score_all/analyze
                                      |
                                      v
                          repo identity + concept names
                                      |
                                      v
                 profile -> classify -> render_note/render_moc -> merge
```

Do not add v1.8 concerns to `extract.py` or `build.py`. Output taxonomy, note classes, concept MOC naming, repo identity, and cluster-quality filtering are downstream interpretations of a graph, not new extraction facts. Keep graph data as plain NetworkX node/edge attributes and keep file writes confined to the existing merge/export layer.

## Current Integration Points

`graphify.export.to_obsidian()` is the right composition boundary. It already loads or receives a profile, classifies nodes and communities via `graphify.mapping.classify()`, renders notes via `graphify.templates`, and applies user-safe writes through `graphify.merge`.

Existing flow:

```text
to_obsidian(G, communities, output_dir, profile=None, community_labels=None, cohesion=None)
  -> load_profile(output_dir) when profile is None
  -> classify(G, communities, profile, cohesion=cohesion)
  -> render_note(...) for per-node notes
  -> render_moc(...) or render_community_overview(...) for per-community notes
  -> compute_merge_plan(...)
  -> apply_merge_plan(...)
```

`graphify.cluster.score_all()` already returns cohesion scores, and `mapping.classify()` already accepts `cohesion`. The cluster-quality floor belongs in `mapping._assemble_communities()`, where the system already decides which communities become MOCs, which fold into hosts, and which route to the Uncategorized bucket.

`graphify.analyze._is_concept_node()` and `_is_file_node()` already define concept/file-hub filtering. v1.8 should reuse those helpers instead of creating parallel heuristics.

`graphify.profile._DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, and `validate_profile()` are the profile schema source of truth. Every new profile key should land there atomically with defaults and validation.

`graphify.output.resolve_output()` owns vault detection and output destination precedence. Repo identity should not change path resolution; it should only flow into names, tags, frontmatter, and manifests.

## New vs Modified Files

### New Files

| File | Purpose |
|------|---------|
| `graphify/naming.py` | Pure helpers for deterministic concept/community names, optional LLM naming cache keys, and repo identity normalization. Keeps naming rules out of `mapping.py` and `templates.py`. |
| `docs/MIGRATING_V1_8.md` or `CONFIGURING_V1_8.md` | Step-by-step migration/update guide for the real `work-vault` -> `ls-vault` workflow. |

Avoid a new exporter module unless implementation proves larger than expected. The current `export.py` should remain the Obsidian orchestration boundary.

### Modified Files

| File | Changes |
|------|---------|
| `graphify/profile.py` | Add v1.8 profile sections for output taxonomy, cluster quality, concept naming, god-node split behavior, and repo identity. Validate types, ranges, and path safety. |
| `graphify/mapping.py` | Apply the cluster-quality floor, split code-derived god nodes from concept MOCs, and add context fields like `cluster_quality`, `cluster_floor_reason`, `repo_identity`, and `note_class`. |
| `graphify/templates.py` | Render new note classes, frontmatter fields, repo tags, and bidirectional links. Keep existing placeholder/block safety intact. |
| `graphify/export.py` | Thread optional `repo_identity` and concept-name metadata through `to_obsidian()`. Keep existing per-node/per-community loops and merge plan flow. |
| `graphify/__main__.py` | Add `--repo-identity` to standalone `--obsidian`, pass it to `to_obsidian()`, and update help text. Do not make CLI run the full graph pipeline. |
| `graphify/cache.py` | If LLM naming ships, add a separate concept-name cache namespace/file. Do not reuse or invalidate extraction cache entries. |
| `graphify/output.py` | Only update if output manifest rows need repo identity or taxonomy metadata. Do not change output precedence. |
| `tests/test_profile.py` | Schema/default/validation tests for all new profile keys. |
| `tests/test_export.py` plus mapping/template tests | Regression tests for generated paths, note classes, cluster floor behavior, repo identity propagation, and no default `_COMMUNITY_*` output. |

Avoid changing `extract.py`, `build.py`, and `cluster.py` unless a specific implementation blocker appears. The quality floor is an export policy, not a community detection algorithm change.

## Recommended Profile Shape

Add optional sections with conservative defaults:

```yaml
output_taxonomy:
  graphify_root: "Graphify"
  community_folder: "Graphify/Maps/"
  code_folder: "Graphify/Code/"
  concept_folder: "Graphify/Concepts/"
  source_folder: "Graphify/Sources/"
  legacy_community_overviews: false

cluster_quality:
  min_members: 3
  min_cohesion: 0.0
  isolate_policy: "fold"       # fold | skip | bucket
  tiny_cluster_policy: "fold"  # fold | skip | bucket

concept_naming:
  mode: "hybrid"               # fallback | hybrid
  cache: true
  fallback_pattern: "{top_label} Cluster"

god_nodes:
  split_code_and_concepts: true
  code_prefix: "CODE"

repo_identity:
  name: null
```

Keep these concerns separate:

- `output_taxonomy` controls folders and legacy compatibility.
- `cluster_quality` controls whether a community deserves a generated MOC.
- `concept_naming` controls community/concept labels.
- `god_nodes` controls code-vs-concept note separation.
- `repo_identity` supplies profile-level identity, overridden by CLI.

Do not overload `mapping.moc_threshold` for the full v1.8 quality floor. Preserve it for backward compatibility and layer `cluster_quality` beside it. If `cluster_quality.min_members` is unset, it can default from `mapping.moc_threshold`.

## Data Flow Changes

### Repo Identity

Precedence:

```text
CLI --repo-identity
  > profile.repo_identity.name
  > auto-derived fallback
```

Recommended fallback:

1. Git repository directory name when available.
2. Otherwise current working directory or output source directory name.
3. Sanitize with `safe_tag()` for tags and `safe_filename()` for filenames.

Flow:

```text
__main__.py parses --repo-identity
  -> to_obsidian(..., repo_identity=...)
  -> classify(..., repo_identity=...)
  -> ClassificationContext["repo_identity_label" / "repo_identity_slug"]
  -> render_note/render_moc frontmatter, tags, filename prefix
  -> output manifest metadata
```

Keep display and slug separate. Use `repo_identity_label` for headings/frontmatter and `repo_identity_slug` for tags, filenames, and manifest keys.

### Cluster-Quality Floor

Apply after `cluster()` and `score_all()`, inside `mapping._assemble_communities()`.

Recommended categories:

- `qualified_cids`: communities that get their own MOC.
- `folded_cids`: tiny/low-quality communities rendered as sub-communities inside a host MOC.
- `bucketed_cids`: isolates or hostless communities routed to Uncategorized or a Graphify-owned bucket.
- `skipped_cids`: communities intentionally omitted from MOC output.

Expose the decision in context:

```python
ClassificationContext(
    cluster_quality="qualified" | "folded" | "bucketed" | "skipped",
    cluster_floor_reason="isolate" | "tiny" | "low_cohesion" | "",
)
```

This extends the current `_nearest_host()` and bucket-MOC machinery rather than replacing it.

### Concept Naming

Concept/community naming should happen after cluster scoring and before rendering. Do not mutate extracted node labels. Store names in derived context:

```text
communities + G + profile.concept_naming
  -> naming.resolve_concept_names(...)
  -> {community_id: "Human Readable Name"}
  -> mapping ClassificationContext["community_name"]
  -> render_moc filename/frontmatter/body
```

If LLM naming is included, use a separate cache:

```text
graphify-out/cache/concept-names.json
key = sha256(repo_identity + sorted member ids + sorted member labels + naming config version)
value = {name, source: "llm" | "fallback", created_at}
```

Fallback naming must be deterministic:

1. Highest-degree real node label in the community.
2. First non-file concept label if no real node exists.
3. `Community {cid}` as final fallback.
4. Sanitization happens at render time through existing filename/tag/wikilink helpers.

### Code-Derived God Nodes vs Concept MOCs

Current `god_nodes()` excludes concept nodes and file hubs, and mapping defaults god nodes to `thing`. v1.8 should keep code-derived god nodes as per-node notes and represent concept MOCs as per-community synthetic export artifacts.

Recommended policy:

- Code-derived god nodes get `note_class="code"` or `code_thing`.
- Concept/community MOCs get `note_class="concept_moc"`.
- Code notes link up to their concept MOC via `parent_moc_label`.
- Concept MOCs include code god nodes in members/related links.
- Synthetic IDs like `_moc_{cid}` remain export-only merge identifiers; do not add MOC nodes to the graph.

### Legacy Community Overview Deprecation

Keep `render_community_overview()` available for custom profiles, but stop producing legacy `_COMMUNITY_*` overview notes from built-in/default output.

Implementation:

- Default `output_taxonomy.legacy_community_overviews` to `false`.
- Make `_assemble_communities()` emit `note_type="moc"` by default.
- Keep the `export.to_obsidian()` branch that handles `note_type="community"` for explicit custom profiles.
- Update `__main__.py` install guidance that tells agents to navigate `_COMMUNITY_*.md`.

This gives MOC-only defaults without breaking profile-driven custom behavior.

## Output Taxonomy

Recommended default built-in layout:

```text
Graphify/
  Maps/        # community/concept MOCs
  Code/        # code-derived god nodes and code notes
  Concepts/    # non-code concept notes if surfaced
  Sources/     # source/file notes when enabled
```

Prefer expressing these folders through profile defaults and `folder_mapping`, not hardcoded path logic in `export.py`. Custom vault profiles should be allowed to keep their own folder mapping.

## Manifest and Migration

v1.7 already writes an output manifest after successful export. v1.8 should use that manifest for migration confidence instead of scanning the whole vault.

Recommended manifest metadata:

```json
{
  "repo_identity": "graphify",
  "repo_identity_slug": "graphify",
  "taxonomy_version": "v1.8",
  "note_class": "concept_moc",
  "legacy_path": "Atlas/Maps/Old.md",
  "target_path": "Graphify/Maps/New.md"
}
```

Start with documentation and dry-run visibility. Avoid automatic relocation/deletion of old notes in the first build unless the roadmap explicitly scopes it.

## Risk-Managed Build Order

1. **Profile schema and defaults**  
   Add v1.8 keys in `profile.py`, with validation and default-profile tests. This gives later work a stable contract.

2. **Pure naming and repo identity helpers**  
   Add `naming.py` with deterministic fallback naming and identity normalization. Keep tests network-free.

3. **Mapping/classification changes**  
   Extend `ClassificationContext` and `_assemble_communities()` for quality floor, concept names, note classes, and god-node split metadata. This is the main behavioral phase.

4. **Templates and built-in taxonomy**  
   Update built-in templates/frontmatter/tags and default folders. Assert rendered output, not just file existence.

5. **Export and CLI plumbing**  
   Thread `repo_identity` through `to_obsidian()` and standalone `--obsidian`. Update manifest metadata if needed.

6. **Migration guide and agent guidance**  
   Document the real `work-vault` -> `ls-vault` update path, dry-run workflow, new folders, and handling of old `_COMMUNITY_*` notes. Update stale installed guidance.

7. **Regression sweep**  
   Run focused profile/export/mapping/template/CLI tests, then the broader suite as the final integration gate.

## Invariants to Preserve

- **Pure pipeline:** Stages communicate through plain dicts and NetworkX graphs; no shared mutable state.
- **No graph schema break:** Extraction output remains `{"nodes": [...], "edges": [...]}`.
- **Path confinement:** All vault writes use `validate_vault_path()` or `validate_sibling_path()` patterns. New taxonomy folders reject `..`, absolute paths, and `~`.
- **Template safety:** Block expansion remains before substitution; labels remain sanitized for YAML, filenames, tags, and wikilink aliases.
- **Merge safety:** User sentinel blocks and manifest-based user-modified detection remain authoritative.
- **Determinism:** Fallback concept names, synthetic MOC IDs, member ordering, and folder paths are stable across runs.
- **Backward compatibility:** Existing custom profiles continue to work unless they opt into v1.8 keys. Default output can move to Graphify-owned folders, but migration must be documented.
- **No new required dependencies:** LLM naming, if shipped, is optional and always has deterministic fallback.

## Test Strategy

- `tests/test_profile.py`: schema/default validation for `output_taxonomy`, `cluster_quality`, `concept_naming`, `repo_identity`, and god-node split config.
- `tests/test_mapping.py` or equivalent: qualified/folded/bucketed/skipped communities, isolate policy, cohesion threshold, code god-node context, concept MOC context.
- `tests/test_templates.py`: new frontmatter fields, repo tags, code/MOC bidirectional links, no legacy overview naming by default.
- `tests/test_export.py`: `to_obsidian()` writes under Graphify-owned folders, dry-run paths are correct, and default output does not emit `_COMMUNITY_*` notes.
- CLI tests: `--repo-identity` precedence over profile and fallback, help text, standalone `--obsidian` threading.

Targeted first pass:

```bash
pytest tests/test_profile.py tests/test_export.py -q
```

## Open Questions for Roadmap

- Exact default folder names under the Graphify-owned root.
- Whether legacy community overview rendering remains opt-in indefinitely or is removed after one release.
- Whether LLM concept naming ships in v1.8 or the milestone ships deterministic fallback first.
- Whether migration is documentation-only or includes a dry-run relocation plan.
- Whether repo identity belongs in every note frontmatter, only tags/manifests, or both.
