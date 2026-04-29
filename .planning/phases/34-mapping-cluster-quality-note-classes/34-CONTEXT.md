# Phase 34: Mapping, Cluster Quality & Note Classes - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 34 applies MOC-only community semantics, enforces the cluster-quality floor in mapping/render context, and separates code-derived hub notes from concept MOCs. It covers mapping classification, cluster routing, note-class identity, collision-safe CODE filenames, and minimal link rendering needed to prove the contract. Phase 35 owns legacy-file migration visibility, full template/export polish, and broader dry-run migration reporting.

</domain>

<decisions>
## Implementation Decisions

### Community Output Semantics
- **D-01:** All Obsidian community exports must be MOC-only for default and custom profiles.
- **D-02:** Legacy `_COMMUNITY_*` overview rendering must be disabled in default output, but internal renderer support may remain for explicit legacy/profile migration diagnostics in Phase 35.
- **D-03:** If a profile or mapping path requests `note_type: community`, Phase 34 should coerce it to MOC output with a warning rather than fail or silently render legacy notes.
- **D-04:** Phase 34 must not scan existing vault files for `_COMMUNITY_*`; Phase 35 surfaces existing legacy files as migration candidates or orphans.

### Cluster-Quality Floor Behavior
- **D-05:** Connected below-floor communities should nest under the nearest above-floor host MOC first; only hostless or isolate communities route to `_Unclassified`.
- **D-06:** Isolates below the floor must not get standalone MOCs, but their rendered node notes should point up to `_Unclassified`, and `_Unclassified` should list them as sub-communities.
- **D-07:** Treat accepted `mapping.min_community_size` values literally. If a user configures `1`, single-node communities may become standalone MOCs.
- **D-08:** Change the built-in/default v1.8 `mapping.min_community_size` from `3` to `6`; user profiles can override it.
- **D-09:** Phase 34 should emit enough metadata for MOCs and dry-run plans to show whether a community is standalone, hosted, or bucketed.

### CODE Note Identity
- **D-10:** Add a real `code` note class/type in Phase 34 rather than layering CODE behavior onto `thing`.
- **D-11:** CODE notes are only for god nodes with `file_type: code` and a real `source_file`; concept nodes and file hubs are excluded.
- **D-12:** CODE filenames use `CODE_<repo>_<node>.md`, where repo is the resolved normalized repo identity and node follows safe filename normalization.
- **D-13:** Filename collisions between CODE notes must be resolved with a deterministic short hash derived from node id/source file, and collision provenance should be recorded in metadata/dry-run.

### CODE-Concept Navigation
- **D-14:** CODE and concept MOC navigation should be bidirectional through both frontmatter and body wikilinks.
- **D-15:** CODE notes use `up:` to point to their related concept MOC.
- **D-16:** Concept MOCs list important CODE notes using `related:` or a dedicated code-members field if the implementation needs one.
- **D-17:** Concept MOC CODE listings include only CODE-eligible god-node members of that hosted or standalone community, sorted by degree then label, capped for readability.
- **D-18:** Phase 34 should produce classification context and safe filenames plus minimal default rendering/tests proving CODE↔concept links exist; Phase 35 polishes final templates, dry-run, and migration visibility.

### Claude's Discretion
- Exact warning wording, metadata field names, and cap size for listed CODE members may be chosen during planning, as long as they remain deterministic, testable, and compatible with existing Ideaverse-style frontmatter.

</decisions>

<specifics>
## Specific Ideas

- Default cluster quality floor should now be `6`, not the existing profile default of `3`.
- Host-first routing is preferred over strict “everything below floor goes to `_Unclassified`,” despite the terse CLUST-03 requirement wording.
- CODE note filenames must visibly separate code hubs from concept MOCs and prevent collisions by construction.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Definition
- `.planning/ROADMAP.md` — Phase 34 goal, requirements, success criteria, and Phase 35/36 boundaries.
- `.planning/REQUIREMENTS.md` — v1.8 traceability for COMM-01, CLUST-02, CLUST-03, GOD-01, GOD-02, GOD-03, GOD-04.
- `.planning/PROJECT.md` — v1.8 milestone goal, constraints, out-of-scope boundaries, and prior milestone context.
- `.planning/STATE.md` — Carried-forward Phase 32/33 decisions and current progress state.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/mapping.py` already centralizes classification, god-node detection, community assembly, min-community-size routing, host selection, bucket MOC generation, and per-node community context.
- `graphify/export.py` already resolves repo identity and concept names before rendering Obsidian notes, then renders per-node notes and per-community MOCs from `ClassificationContext`.
- `graphify/templates.py` already owns note type validation, frontmatter generation, wikilink emission, `up:` / `related:` behavior, MOC rendering, and block-template rendering.
- `graphify/naming.py` already provides normalized repo identity, concept name resolution, stable cache/fallback behavior, and safe filename stems that Phase 34 can reuse for CODE names.
- `tests/test_mapping.py`, `tests/test_export.py`, `tests/test_templates.py`, and `tests/test_naming.py` are the closest regression homes.

### Established Patterns
- Mapping returns plain dict/TyperDict-like `ClassificationContext` values; downstream rendering consumes those contexts without global state.
- Profile validation should catch schema problems early, while render/export paths warn and continue when safe.
- Existing tests prefer small in-memory NetworkX fixtures and `tmp_path` output assertions.
- No migration deletion belongs in this phase; existing vault file migration behavior is Phase 35.

### Integration Points
- Extend `_NOTE_TYPES`, profile note-type validation, mapping classification, and template rendering to understand a real `code` type.
- Thread resolved repo identity into CODE filename generation so `CODE_<repo>_<node>.md` does not duplicate resolver logic.
- Add routing metadata to community contexts so MOC/dry-run output can distinguish standalone, hosted, and bucketed communities.

</code_context>

<deferred>
## Deferred Ideas

- Full legacy `_COMMUNITY_*` vault scan and migration-candidate/orphan reporting — Phase 35.
- Final CODE-specific template polish and broader dry-run/migration presentation — Phase 35.
- Migration guide and skill/documentation alignment — Phase 36.

</deferred>

---

*Phase: 34-mapping-cluster-quality-note-classes*
*Context gathered: 2026-04-29*
