---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Output Taxonomy & Cluster Quality
status: executing
stopped_at: Completed 34-02-PLAN.md
last_updated: "2026-04-29T03:52:29.363Z"
last_activity: 2026-04-29
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 12
  completed_plans: 10
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28 for v1.8)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile.
**Current focus:** Phase 34 — mapping-cluster-quality-note-classes

## Current Position

Phase: 34 (mapping-cluster-quality-note-classes) — EXECUTING
Plan: 3 of 4
Status: Ready to execute
Last activity: 2026-04-29

Progress: [████████░░] 83%

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

## Accumulated Context

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
| seed | SEED-001 tacit-to-explicit elicitation | Dormant; revisit when onboarding/discovery is milestone theme |
| seed | SEED-002 multi-harness/inverse import | Deferred pending prompt-injection defenses |
| vault-selection | Explicit `--vault` flag and multi-vault selector | Future milestone |
| baseline-test | `test_detect_skips_dotfiles`, `test_collect_files_from_dir` | Separate `/gsd-debug` session |

## Session Continuity

Last session: 2026-04-29T03:52:29.360Z
Stopped at: Completed 34-02-PLAN.md
Next action: `/gsd-discuss-phase 34 --chain`
