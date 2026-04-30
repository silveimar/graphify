---
gsd_state_version: 1.0
milestone: v1.10
milestone_name: milestone
status: planning
stopped_at: Phase 45 context gathered
last_updated: "2026-04-30T20:17:16.298Z"
last_activity: 2026-04-30 — Phase 48 added (graphifyignore + canonical graphify-out); v1.10 phases 45–48 in ROADMAP
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (current milestone **v1.10**).

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile.

**Current focus:** Define and execute **v1.10** — baselines + detect self-ingestion + concept↔code MVP per `.planning/REQUIREMENTS.md`.

## Current Position

Phase: **45** — roadmap defined; ready for `/gsd-discuss-phase 45` or `/gsd-plan-phase 45`
Plan: —
Status: Roadmapped (v1.10 Phases 45–48 in `.planning/ROADMAP.md`)
Last activity: 2026-04-30 — Phase 48 added (graphifyignore + canonical graphify-out); v1.10 phases 45–48 in ROADMAP

## Performance Metrics

**Recent milestone baselines:**

| Milestone | Phases | Plans | Result |
|-----------|--------|-------|--------|
| v1.5 | 19-22 | 11 | 34/34 requirements, shipped 2026-04-27 |
| v1.6 | 23-26 | 5 | 15/15 requirements, shipped 2026-04-27 |
| v1.7 | 27-31 | 14 | 13/13 requirements, shipped 2026-04-28 |
| v1.8 | 32-36 | TBD | 33/33 requirements mapped, not started |
| Phase 32 P01 | 4min | 2 tasks | 3 files |
| Phase 32 P02 | 5min | 2 tasks | 3 files |
| Phase 32 P03 | 5min | 2 tasks | 4 files |
| Phase 32 P04 | 6min | 2 tasks | 3 files |
| Phase 33 P01 | 6min | 3 tasks | 5 files |
| Phase 33 P02 | 6min | 3 tasks | 2 files |
| Phase 33 P03 | 5min | 3 tasks | 1 file |
| Phase 33 P04 | 12min | 3 tasks | 5 files |
| Phase 34 P1 | 6min | 2 tasks | 5 files |
| Phase 34 P2 | 8min | 2 tasks | 2 files |
| Phase 34 P03 | 6min | 2 tasks | 6 files |
| Phase 34 P4 | 7min | 3 tasks | 4 files |
| Phase 34 P5 | 4min | 2 tasks | 2 files |
| Phase 35 P01 | 6min | 3 tasks | 2 files |
| Phase 35 P02 | 6min | 3 tasks | 5 files |
| Phase 35 P03 | 9min | 3 tasks | 5 files |
| Phase 36 P01 | 13min | 3 tasks | 4 files |
| Phase 36 P02 | 7min | 2 tasks | 5 files |
| Phase 36 P03 | 6min | 2 tasks | 10 files |
| Phase 36 P04 | 9min | 2 tasks | 3 files |
| Phase 36 P05 | 6min | 2 tasks | 3 files |
| Phase 37 P01 | 6min | 2 tasks | 1 file |
| Phase 37 P02 | 5min | 2 tasks | 3 files |

## Accumulated Context

### Roadmap Evolution

- Phase 38 added: with dormant seeds and pending quick task
- Phase 38 scope ratified as docs-only reconciliation (dormant seeds + quick-task lifecycle) with runtime modules unchanged.
- Phase 48 added: `.graphifyignore` loading / matching fixes for nested `graphify-out` (stop false prompts); consolidate outputs under canonical `graphify-out` instead of nested trees under input (`gsd-add-phase`; numbered **48** after resolving duplicate Phase 46 collision with Concept↔Code roadmap slot).

### Decisions

Locked v1.8 choices:

- MOCs live under `Atlas/Sources/Graphify/MOCs/` by default.
- `_COMMUNITY_*` default output is hard-deprecated; community output is MOC-only by default.
- Cached LLM concept naming is required, with deterministic fallback.
- Migration support includes an automated migration command plus a Markdown guide.
- v1.8 derives phases from current milestone requirements only and continues numbering at Phase 32.
- [Phase 32]: Phase 32 planning contract uses mapping.min_community_size as the canonical cluster floor key.
- [Phase 32]: mapping.moc_threshold is documented as invalid immediately for v1.8 profiles.
- [Phase 32]: v1.8 taxonomy is resolved into folder_mapping at profile load/preflight time. — Keeps downstream mapping/export consumers on the existing folder_mapping contract while centralizing taxonomy truth in profile.py.
- [Phase 32]: mapping.min_community_size is canonical; mapping.moc_threshold is a hard validation error. — Matches the locked v1.8 contract and prevents silent legacy precedence behavior.
- [Phase 32]: Deprecated community overview templates remain renderable but produce MOC-only output migration warnings. — Phase 32 is the contract layer, so warnings guide migration without removing renderer support.
- [Phase 32]: Mapping resolves taxonomy folders into ClassificationContext.folder before Obsidian export rendering.
- [Phase 32]: mapping.min_community_size is the only runtime standalone MOC floor key in mapping.py.
- [Phase 32]: Hostless tiny communities route to the _Unclassified MOC bucket.
- [Phase 32]: Doctor profile diagnostics now use validate_profile_preflight() as the shared source for errors and warnings.
- [Phase 32]: Warning-only doctor profile findings guide migration without making is_misconfigured() true.
- [Phase 32]: Doctor skips output resolution when fatal preflight errors exist to avoid duplicate invalid-profile diagnostics.
- [Phase 33 Plan 01]: Wave 0 tests intentionally define red naming and repo identity contracts before production helpers are implemented.
- [Phase 33 Plan 02]: Repo identity resolution is centralized in graphify.naming with explicit CLI > profile > git remote > directory precedence.
- [Phase 33 Plan 02]: repo.identity is the only profile location for repo identity; naming.repo is rejected with guidance.
- [Phase 33 Plan 02]: naming.concept_names exposes enabled, budget, and style controls only; prompt templates remain out of schema.
- [Phase 33 Plan 03]: Concept naming cache/provenance is sidecar-only under the supplied artifacts directory.
- [Phase 33 Plan 03]: LLM concept title candidates are rejected before persistence when unsafe, generic, duplicate, path-like, template-breaking, wikilink-breaking, control-character-bearing, empty, or too long.
- [Phase 33]: [Phase 33 Plan 04]: Repo identity remains centralized in graphify.naming; CLI parsing only extracts and forwards the optional flag value.
- [Phase 33]: [Phase 33 Plan 04]: to_obsidian() records repo identity as graphify-out/repo-identity.json only on non-dry-run exports.
- [Phase 33]: [Phase 33 Plan 04]: Explicit community_labels remain the highest-precedence override over auto-resolved concept names.
- [Phase 33]: [Phase 33 Plan 04]: Unsafe generated MOC titles are normalized inside templates.py before filename/frontmatter/template sinks consume them.
- [Phase 34]: [Phase 34 Plan 01]: CODE notes are a first-class profile/template note type while legacy community remains a compatibility token. — Phase 34 Plan 01 established the shared profile/template contract needed before mapping and export consume CODE notes.
- [Phase 34]: [Phase 34 Plan 01]: Default mapping.min_community_size is now 6 for built-in v1.8 profiles. — D-08 selected 6 as the default cluster-quality floor while preserving literal user overrides.
- [Phase 34 Plan 02]: Mapping now emits standalone, hosted, and bucketed routing metadata as the source of truth for downstream export/template behavior.
- [Phase 34 Plan 02]: CODE note eligibility is limited to code-backed god nodes with non-empty string source_file values and synthetic-node exclusions.
- [Phase 34 Plan 02]: Concept MOC CODE member context is sorted by degree descending, then label and node id, and capped at 10.
- [Phase 34]: [Phase 34 Plan 03]: CODE filename identity is generated in graphify.naming and injected once in to_obsidian after repo identity resolution. — Keeps repo normalization and filename identity centralized while preserving the existing export/render pipeline.
- [Phase 34]: [Phase 34 Plan 03]: Colliding CODE stems suffix every colliding member with an 8-character SHA-256 hash derived from node id and source file. — Makes collision handling deterministic and independent of graph insertion order.
- [Phase 34]: [Phase 34 Plan 03]: Normal Obsidian export coerces legacy community note requests to MOC rendering instead of calling the community overview renderer. — Satisfies MOC-only community output while retaining migration diagnostics for later phases.
- [Phase 34]: [Phase 34 Plan 04]: Export propagates final concept labels into CODE parent links before rendering. — Keeps CODE up links aligned with explicit community labels and concept naming overrides.
- [Phase 34]: [Phase 34 Plan 04]: Concept MOC CODE links render from ClassificationContext code_members/code_member_labels via _emit_wikilink(). — Preserves context-owned rendering and established wikilink sanitization.
- [Phase 34]: [Phase 34 Plan 04]: CODE collision provenance is emitted only for colliding filename stems through the frontmatter dumper. — Avoids extra metadata for normal CODE notes while keeping collision evidence sanitized.
- [Phase 34 Plan 05]: Structured CODE member links preserve export-provided filename_stem as the wikilink target after safe_filename only. — Closes the verifier gap by preventing title-case target drift while keeping aliases sanitized.
- [Phase 35 Plan 01]: Migration preview plan IDs are SHA-256 digests over normalized non-volatile preview payloads.
- [Phase 35 Plan 01]: Legacy _COMMUNITY_* files are surfaced as review-only ORPHAN rows and never promoted into apply writes.
- [Phase 35 Plan 01]: Migration artifact writes are confined to graphify-out/migrations with tmp+fsync+os.replace.
- [Phase 35]: [Phase 35 Plan 02]: Repo identity for CODE notes is sourced from resolved_repo_identity.identity and propagated through CODE render contexts. — Keeps repo normalization centralized while allowing templates and manifests to expose the same resolved identity.
- [Phase 35]: [Phase 35 Plan 02]: Repo frontmatter is graphify-owned replace metadata while unknown user-added keys remain preserved. — Ensures generated repo metadata updates safely without clobbering arbitrary user-authored frontmatter.
- [Phase 35]: [Phase 35 Plan 02]: Vault manifest run metadata uses reserved __graphify_run__ so path-entry readers can skip it safely. — Separates run-level audit metadata from per-note path entries and preserves old manifest compatibility.
- [Phase 36 Plan 01]: Archive movement stays migration-specific in graphify/migration.py; the generic merge engine continues to skip ORPHAN rows.
- [Phase 36 Plan 01]: Reviewed apply archives legacy notes only after apply_merge_plan reports zero failures.
- [Phase 36 Plan 01]: Rollback evidence is exposed through archived_legacy_notes metadata and CLI wording under graphify-out/migrations/archive/.
- [Phase 36 Plan 02]: The v1.8 guide is generic-first: --input is any raw corpus and --vault is the target Obsidian vault, with work-vault/raw -> ls-vault as the canonical example.
- [Phase 36 Plan 02]: README presents --obsidian as lower-level direct export and update-vault as the reviewed existing-vault migration/update workflow.
- [Phase 36 Plan 02]: CLI help repeats backup-before-apply, reviewed --apply --plan-id, archive path, and non-destructive legacy-note wording.
- [Phase 36]: Skill contract drift is guarded with exact required phrases and targeted forbidden stale-claim phrases rather than full-file snapshots.
- [Phase 36]: The shared skill wording distinguishes lower-level --obsidian export from reviewed preview-first update-vault existing-vault migration/update.
- [Phase 36]: Legacy _COMMUNITY_* wording remains allowed only when describing reviewed legacy archive behavior, not generated v1.8 output.
- [Phase 36]: [Phase 36 Plan 04]: The sanitizer matrix imports private sink helpers intentionally where the private helper is the security boundary under test. — Private sink helpers are the exact security boundaries carrying VER-03 invariants.
- [Phase 36]: [Phase 36 Plan 04]: Phase 36 final validation records actual focused and full pytest outputs; known baseline failures did not reproduce. — Milestone audit needs executed evidence rather than planned command claims.
- [Phase 36]: [Phase 36 Plan 05]: Install-time Claude and AGENTS guidance now uses GRAPH_REPORT.md, Obsidian MOC notes with [[wikilinks]], and wiki/index.md fallback instead of legacy _COMMUNITY_* overview notes. — Closes VER-02 install-time drift identified by phase verification.
- [Phase 36]: [Phase 36 Plan 05]: Embedded install guidance constants are covered by tests/test_skill_files.py so future drift is caught with packaged skill files. — Keeps install-time guidance and packaged skill wording under the same regression test surface.
- [Phase 37]: [Phase 37 Plan 37.1]: Nyquist ratification keeps `status: draft` vocabulary while using `nyquist_compliant` and `wave_0_complete` as deterministic gate truth.
- [Phase 37]: [Phase 37 Plan 37.2]: v1.8 audit debt closure is metadata-only and preserves historical requirement and phase verification facts.

### Pending Todos

None.

### Blockers/Concerns

None. Research flags for planning:

- Phase 35 should research existing merge manifest/orphan mechanics before designing migration reporting.
- Phase 36 should audit platform skill variants for Obsidian export behavior drift.
- Any LLM naming plan must preserve offline behavior, budget gates, cache stability, and sanitization.

## Deferred Items

Items carried forward outside v1.8 scope:

| Category | Item | Status |
|----------|------|--------|
| seed | SEED-001 tacit-to-explicit elicitation | Dormant; activate only for onboarding/discovery milestones or explicit tacit-knowledge-only user demand |
| seed | SEED-002 multi-harness/inverse import | Dormant; activate only on real multi-harness portability demand after prerequisite discovery/context work |
| vault-selection | Explicit `--vault` flag and multi-vault selector | Future milestone |
| baseline-test | `test_detect_skips_dotfiles`, `test_collect_files_from_dir` | **Phase 45** (HYG-02/HYG-03) via roadmap |

### Milestone close acknowledgment (v1.8, 2026-04-29)

Open artifact audit items acknowledged at ship; no runtime blockers:

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260427-rc7-fix-detect-self-ingestion | missing — track via backlog or `/gsd-debug` |
| seed | SEED-001 tacit-knowledge-elicitation-engine | dormant |
| seed | SEED-002 harness-memory-export | dormant |
| seed | SEED-bidirectional-concept-code-links | dormant |
| seed | SEED-vault-root-aware-cli | dormant |

### Milestone close acknowledgment (v1.9, 2026-04-30)

Open artifact audit items carried into next milestone planning:

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260427-rc7-fix-detect-self-ingestion | missing — carry forward as explicit next-milestone candidate |
| seed | SEED-bidirectional-concept-code-links | dormant — carry forward for explicit scope decision |

## Quick Tasks Completed

| Date (UTC) | Slug | Summary |
|------------|------|---------|
| 2026-04-30 | docs-folder-and-guide-refresh | Moved INSTALLATION, MIGRATION_V1_8, PROFILE-CONFIGURATION, CONFIGURING_V1_5, ARCHITECTURE into `docs/`; refreshed README index and cross-links; aligned CONFIGURING with `mcp_tool_registry.py` + alias behavior; `tests/test_docs.py` path updated |

## Session Continuity

Last session: 2026-04-30T20:17:16.288Z
Stopped at: Phase 45 context gathered
Next action: review diff, commit/PR, or `/gsd-ship` / milestone close per project process
