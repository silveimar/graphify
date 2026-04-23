# Phase 8: Obsidian Round-Trip Awareness - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can freely edit graphify-injected vault notes between `--obsidian` runs without losing their changes. Graphify detects user modifications via a content-hash manifest, preserves user-modified notes entirely, and provides explicit user sentinel blocks for permanent preservation zones. `vault-manifest.json` tracks per-note state for accurate change detection. Dry-run output shows modification source per note.

</domain>

<decisions>
## Implementation Decisions

### User Block Sentinels
- **D-01:** User sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) are **separate zones** placed OUTSIDE graphify-managed sections. Graphify-managed sections (`<!-- graphify:name:start/end -->`) and user sentinel blocks have non-overlapping ownership. Graphify sections are managed by graphify; user blocks are never touched.
- **D-02:** Malformed user sentinels (START without END, nested pairs, sentinels placed inside graphify-managed sections) trigger a warning to stderr. The note is treated as if it has no user blocks — graphify proceeds with normal merge. User sees the warning and can fix their sentinels.
- **D-03:** Whether users can place multiple USER_START/END pairs per note or just one is at Claude's discretion. Pick whatever is simpler to implement correctly.

### Change Detection
- **D-04:** `vault-manifest.json` stores a whole-file SHA256 content hash per note, computed at merge time. Uses the same `file_hash()` pattern from `cache.py`. Any file change (whitespace, frontmatter, body) counts as user-modified.
- **D-05:** `vault-manifest.json` is written atomically (via `os.replace()`) after each successful `apply_merge_plan` call.
- **D-06:** Manifest entries include: `content_hash`, `last_merged` (ISO timestamp), `target_path`, `node_id`, `note_type`, `community_id`, and `has_user_blocks` (boolean). This enables richer dry-run output without re-parsing every file.

### Merge Conflict Policy
- **D-07:** When graphify detects a user-modified note (hash mismatch against manifest), it applies `SKIP_PRESERVE` — the entire note is left untouched. User content always wins. This is the default behavior for any modified note on re-run.
- **D-08:** Content inside `<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->` sentinel blocks is never overwritten by any merge action, even `REPLACE` strategy. (Though with D-07, user-modified notes are skipped entirely, sentinels provide an additional guarantee for notes that were NOT modified by the user but contain user blocks.)
- **D-09:** To refresh a user-modified note with new graphify data: delete the note file. The next `--obsidian` run detects the missing file (no manifest match) and creates it fresh as a CREATE action.
- **D-10:** `--obsidian --force` flag overrides D-07 for all notes: user-modified notes are updated/replaced as if they were unmodified. User sentinel blocks (D-08) are still preserved even with `--force`. This lets users opt into a full refresh while keeping their explicit preservation zones.

### Dry-Run Presentation
- **D-11:** Extend the existing `format_merge_plan` table with a `Source` column showing modification source per note: `graphify` (unmodified since last merge), `user` (user-modified), or `both` (has user sentinel blocks AND graphify sections).
- **D-12:** Dry-run output includes a summary line at top: "{N} notes user-modified (will be preserved), {M} notes graphify-only (will update), {K} new notes (will create)".

### Claude's Discretion
- Multiple vs single USER_START/END blocks per note (D-03)
- `vault-manifest.json` file format details (JSON structure, indentation)
- Hash algorithm implementation details (whether to reuse `cache.file_hash()` directly or adapt)
- Error messages for manifest corruption, missing manifest on first run
- How `--force` interacts with `--dry-run` (likely: shows what would happen with force)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Merge Engine
- `graphify/merge.py` — Current merge engine: `compute_merge_plan()`, `apply_merge_plan()`, `format_merge_plan()`, `MergeAction` enum (6 actions: CREATE, UPDATE, REPLACE, SKIP_PRESERVE, SKIP_CONFLICT, ORPHAN), `RenderedNote` TypedDict, dual-signal fingerprint (D-62)
- `graphify/templates.py` — Sentinel block patterns (`<!-- graphify:name:start -->` / `<!-- graphify:name:end -->`), template rendering
- `graphify/export.py` — `to_obsidian()` function that orchestrates note rendering and merge
- `graphify/__main__.py` — `--obsidian` flag handling (lines ~965-1056), `--dry-run` support

### Supporting Modules
- `graphify/cache.py` — `file_hash()` for SHA256, `os.replace()` atomic write pattern to reuse
- `graphify/security.py` — `sanitize_label()` for any user-facing strings, path confinement patterns
- `graphify/profile.py` — `load_profile()`, `validate_vault_path()` for vault operations

### Prior Phase Context
- `.planning/phases/07-mcp-write-back-peer-modeling/07-CONTEXT.md` — Phase 7 decisions: D-10 (proposals through merge engine), D-11 (--vault required)

### Requirements
- `.planning/REQUIREMENTS.md` — TRIP-01 through TRIP-07 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `merge.py::MergeAction` enum — extend or reuse SKIP_PRESERVE for user-modified notes
- `merge.py::compute_merge_plan()` — accepts `previously_managed_paths` for orphan detection; vault-manifest.json provides the same data plus hashes
- `merge.py::format_merge_plan()` — extend with Source column for dry-run
- `cache.py::file_hash()` — SHA256 content hashing, reuse for vault-manifest
- `cache.py` atomic write pattern (`os.replace()`) — reuse for vault-manifest.json

### Established Patterns
- Merge engine is pure reconciliation (`compute_merge_plan`) + side-effectful writes (`apply_merge_plan`) — Phase 8 extends both
- Sentinel blocks are regex-parsed in `merge.py` — add user sentinel regex alongside graphify sentinel regex
- `--dry-run` calls `format_merge_plan()` and prints without writing — extend for round-trip info
- `graphify-out/` as standard output directory for sidecars and manifests

### Integration Points
- **merge.py:** vault-manifest.json written at end of `apply_merge_plan()`, read at start of `compute_merge_plan()`
- **__main__.py:** `--force` flag parsed alongside existing `--dry-run` in `--obsidian` handling
- **export.py:** `to_obsidian()` passes through to merge engine — manifest path flows through here

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-obsidian-round-trip-awareness*
*Context gathered: 2026-04-13*
