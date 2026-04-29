# Phase 33: Naming & Repo Identity Helpers - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 33 delivers the pre-rendering identity layer for v1.8: stable repo identity resolution and stable human-readable concept MOC names that downstream mapping, templates, manifests, and migration preview code can trust. It does not implement Phase 34's CODE note classes, Phase 35's full export plumbing/migration visibility, or Phase 36's docs and regression sweep.

</domain>

<decisions>
## Implementation Decisions

### Repo Identity Shape and Precedence
- **D-01:** The resolved repo identity should be a short stable slug such as `graphify` or `work-vault`, optimized for readability in filenames, tags, and manifests.
- **D-02:** Source precedence is CLI flag first, profile second, deterministic fallback third. The winning source must be printed to stderr during runs and recorded durably in the manifest.
- **D-03:** Profile-supplied identity belongs in a top-level `repo:` block, with a key such as `repo.identity`. Do not hide repo identity under `naming:`.
- **D-04:** Fallback should derive from the git remote slug first, then the current directory name when no remote-derived identity exists. Offline/local projects must still produce deterministic output.

### Concept Naming Policy
- **D-05:** LLM concept naming should be default-on for the built-in/default v1.8 profile, with deterministic fallback so offline, budget-limited, or no-key runs still produce valid output.
- **D-06:** Vault profiles may control concept naming with enable/disable plus budget/style hints. Avoid exposing full prompt templates in Phase 33.
- **D-07:** Unsafe, empty, duplicate, or overly generic LLM-generated titles must be rejected. Graphify should use the deterministic fallback and record/warn the provenance rather than failing the run.
- **D-08:** Deterministic fallback names should use top meaningful terms plus a community id/hash suffix, e.g. `Auth Session Flow c12`, rather than plain `Community 12` or a single top-node label.

### Naming Cache Stability
- **D-09:** Concept naming cache keys should be based on a community signature from sorted member node IDs plus labels/source files, not the raw community ID alone.
- **D-10:** Cache reuse should tolerate small member changes when the top terms/signature remain close enough, to avoid filename churn from tiny graph drift.
- **D-11:** Concept naming cache/provenance should live in a `graphify-out/` sidecar cache or manifest, matching existing generated-artifact conventions and avoiding writes to vault-owned `.graphify/` configuration.
- **D-12:** Manual concept-name override behavior is not in Phase 33. Design the cache/schema so future profile overrides can win later, but do not add an approval UI or frontmatter round-trip override in this phase.
- **D-13:** Explicit cache refresh UI is deferred. Keep the cache format ready for a future clear/force naming cache command without adding a new Phase 33 CLI flag solely for refresh.

### Claude's Discretion
No selected decision was delegated to Claude. Planner may choose implementation details that preserve the decisions above and the repo's existing helper style.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Contract
- `.planning/ROADMAP.md` — Phase 33 goal, dependencies, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` — NAME-01 through NAME-05 and REPO-01 through REPO-03 traceability.
- `.planning/PROJECT.md` — v1.8 milestone scope and core constraints.
- `.planning/STATE.md` — locked carry-forward decisions and current milestone state.

No external specs were referenced during discussion.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify.profile.safe_filename`, `safe_tag`, and `safe_frontmatter_value` already sanitize filenames, tags, wikilinks, Dataview-adjacent values, and YAML frontmatter.
- `graphify.templates.resolve_filename` centralizes filename convention handling and should remain the place where display labels become note filename stems.
- `graphify.cache` shows the existing generated-artifact cache style: SHA-based keys, `graphify-out/cache/`, JSON payloads, and atomic replace.

### Established Patterns
- `graphify.profile.validate_profile` uses allowlisted top-level keys and accumulated error strings. A new top-level `repo:` block should follow that pattern.
- `graphify.mapping._derive_community_label` currently derives labels from top in-community real nodes. Phase 33 should provide a stronger naming helper that Phase 34 can consume without relying on community IDs alone.
- `graphify.export.to_obsidian` already accepts `community_labels` and injects them into per-community context before rendering. The naming helper can feed this existing integration point before later phases deepen export behavior.

### Integration Points
- `graphify.__main__` is the likely CLI surface for a repo identity flag.
- `graphify.profile.load_profile` and validation are the likely profile integration points for `repo.identity` and concept naming controls.
- `graphify.export.to_obsidian` and downstream merge/manifest code are where resolved identity and concept naming provenance will later need to flow into rendered paths and sidecars.

</code_context>

<specifics>
## Specific Ideas

- Prefer readable generated names over purely technical identifiers, but never at the cost of deterministic offline output.
- Keep Phase 33 helper-focused: build stable inputs and provenance for later rendering/migration phases rather than expanding into manual naming workflows.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 33-Naming & Repo Identity Helpers*
*Context gathered: 2026-04-28*
