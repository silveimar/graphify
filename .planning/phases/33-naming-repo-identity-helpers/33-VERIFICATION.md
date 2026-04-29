---
phase: 33-naming-repo-identity-helpers
verified: 2026-04-29T02:51:14Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 33: Naming & Repo Identity Helpers Verification Report

**Phase Goal:** Users get stable human-readable concept names and deterministic repo identity resolution that downstream note paths can trust.
**Verified:** 2026-04-29T02:51:14Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can provide repo identity through a CLI flag with highest precedence. | VERIFIED | `graphify/__main__.py` parses `--repo-identity` for `run` and `--obsidian`, strips it before positional target selection, and forwards it to `resolve_repo_identity()`/`to_obsidian()`; tests assert CLI source wins exactly once. |
| 2 | User can provide repo identity through `profile.yaml` when no CLI override is supplied. | VERIFIED | `graphify/profile.py` accepts top-level `repo.identity`; `graphify/__main__.py` loads the detected vault profile for standalone `--obsidian`; `graphify/export.py` passes the profile into resolver and writes source `profile` in sidecar. |
| 3 | User gets deterministic fallback repo identity from git remote or current directory. | VERIFIED | `graphify/naming.py` parses `.git/config` with `configparser`, extracts remote slug, then falls back to normalized `cwd.name`; tests cover both fallback sources without shelling out to git. |
| 4 | User receives cached LLM concept MOC titles when concept naming is enabled. | VERIFIED | `resolve_concept_names()` loads `concept-names.json`, validates exact/tolerant cache hits, returns source `llm-cache`/`cache-tolerant`, and avoids a fresh `llm_namer` call on cache hit. |
| 5 | User receives stable deterministic fallback concept names when LLM naming is unavailable, disabled by budget, or rejected. | VERIFIED | `resolve_concept_names()` handles disabled, budget-disabled, missing callable, LLM exceptions, and rejected candidates with `_fallback_name()` based on top graph terms plus a stable signature-derived suffix. |
| 6 | User can rerun graphify on an unchanged community and keep the same concept MOC filename. | VERIFIED | `_community_signature()` hashes sorted member IDs, labels, and source files; fallback and cached names preserve stable `filename_stem`; tests call resolver twice and assert same signature/stem. |
| 7 | User can inspect concept naming provenance. | VERIFIED | `ConceptName` includes `source`, `signature`, and `reason`; sidecar records `signature`, `source`, `reason`, `top_terms`, `filename_stem`, and `community_id`; dry-run returns the same provenance without sidecar writes. |
| 8 | Unsafe generated labels are rejected or sanitized before filename, tag, wikilink, Dataview, and frontmatter sinks. | VERIFIED | LLM candidates with path traversal, wikilink breakers, template braces, control chars, generic/empty/duplicate/too-long titles are rejected; `templates.py` normalizes generated MOC titles and routes filename/tag/frontmatter/Dataview through existing sink helpers. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/naming.py` | Repo identity resolver, concept name resolver, cache/provenance IO, unsafe title validation | VERIFIED | Exports `ResolvedRepoIdentity`, `ConceptName`, `normalize_repo_identity()`, `resolve_repo_identity()`, and `resolve_concept_names()`; substantive implementation uses stdlib parsing, SHA-256 signatures, sidecar JSON, and atomic writes. |
| `graphify/profile.py` | Profile defaults and validation for `repo.identity` and `naming.concept_names` | VERIFIED | `_DEFAULT_PROFILE` contains `repo` and `naming.concept_names`; validation accumulates dotted-path errors for invalid repo identity and concept naming controls. |
| `graphify/__main__.py` | CLI parsing for `--repo-identity` in `run` and `--obsidian` | VERIFIED | Parses both `--repo-identity value` and `--repo-identity=value`; missing values exit 2; `run` resolves identity and `--obsidian` forwards identity/profile to export. |
| `graphify/export.py` | Obsidian export integration and durable repo identity sidecar | VERIFIED | `to_obsidian()` resolves repo identity after profile load, writes `repo-identity.json` on non-dry-run, resolves concept names before rendering, and merges labels with explicit caller override precedence. |
| `graphify/templates.py` | Final sink safety for generated MOC titles | VERIFIED | `_sanitize_generated_title()` normalizes unsafe generated titles before MOC filename/frontmatter/template substitution; existing filename/tag/wikilink/Dataview helpers remain final sinks. |
| `tests/test_naming.py` | Helper behavior coverage | VERIFIED | Covers cached titles, fallback names, filename stability, provenance, unsafe title rejection, and repo identity precedence/fallback. |
| `tests/test_profile.py` | Profile schema coverage | VERIFIED | Covers valid/invalid `repo.identity` and `naming.concept_names`, including collect-all error behavior. |
| `tests/test_export.py` | Export integration coverage | VERIFIED | Covers concept-name MOC paths, dry-run no sidecar, profile repo identity sidecar, and fallback repo identity sidecar. |
| `tests/test_templates.py` | Generated title sink-safety coverage | VERIFIED | Covers unsafe generated MOC title across filename, tag, frontmatter, and raw injection surfaces. |
| `tests/test_main_flags.py` | CLI flag parsing coverage | VERIFIED | Covers `run`, `--obsidian`, profile fallback without flag, CLI override, and missing-value exit 2. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graphify/__main__.py` | `graphify/naming.py` | `run` calls `resolve_repo_identity()` after profile load | WIRED | CLI `run` extracts repo identity, loads profile, and invokes resolver so source reporting happens in normal run wiring. |
| `graphify/__main__.py` | `graphify/export.py` | `--obsidian` passes `repo_identity` and detected vault profile into `to_obsidian()` | WIRED | CR-01 fix ensures standalone `--obsidian` does not lose vault `repo.identity` when output is profile-routed. |
| `graphify/export.py` | `graphify/naming.py` | `resolve_repo_identity()` and `resolve_concept_names()` before MOC rendering | WIRED | Export computes identity/provenance before classification/rendering and propagates dry-run to concept naming. |
| `graphify/export.py` | `graphify-out/repo-identity.json` | `_write_repo_identity_sidecar()` on non-dry-run exports | WIRED | Sidecar contains identity, source, raw value, and warnings; omitted during dry-run. |
| `graphify/export.py` | `graphify/templates.py` | `ctx["community_name"]` and `ctx["community_tag"]` consumed by `render_moc()` | WIRED | Auto-resolved concept names replace mapping fallback labels unless explicit `community_labels` are supplied. |
| `graphify/naming.py` | `graphify-out/concept-names.json` | `artifacts_dir / "concept-names.json"` | WIRED | Cache/provenance sidecar is loaded and atomically saved unless `dry_run=True`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `graphify/__main__.py` | `cli_repo_identity` | `_extract_repo_identity_arg(args)` from actual CLI argv | Yes | FLOWING |
| `graphify/naming.py` | `ResolvedRepoIdentity.identity/source` | CLI value, `profile["repo"]["identity"]`, `.git/config`, or `cwd.name` | Yes | FLOWING |
| `graphify/export.py` | `resolved_repo_identity` | `resolve_repo_identity(Path.cwd(), cli_identity=repo_identity, profile=profile)` | Yes | FLOWING |
| `graphify/export.py` | `repo-identity.json` payload | `ResolvedRepoIdentity` fields | Yes | FLOWING |
| `graphify/naming.py` | `ConceptName` | `concept-names.json`, optional `llm_namer`, graph communities, fallback terms/signature | Yes | FLOWING |
| `graphify/export.py` | `merged_labels` / `per_community[*]["community_name"]` | Resolved `ConceptName.title` with explicit caller override precedence | Yes | FLOWING |
| `graphify/templates.py` | MOC filename/frontmatter/tag/Dataview text | `community_name`/`community_tag` from export context | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 33 helper, profile, export, template, and CLI behavior | `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_export.py tests/test_main_flags.py -q` | `437 passed, 1 xfailed, 2 warnings` | PASS |
| Working tree cleanliness before report | `git status --short` | No output | PASS |
| IDE lints for touched Phase 33 files | `ReadLints` on implementation and test files | No linter errors found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NAME-01 | 33-01, 33-03, 33-04 | Human-readable concept MOC titles from cached LLM naming when enabled | SATISFIED | Cache hit path in `resolve_concept_names()` and `test_concept_name_uses_cached_llm_title`. |
| NAME-02 | 33-01, 33-02, 33-03, 33-04 | Stable deterministic fallback names when LLM unavailable, disabled, budget-blocked, or rejected | SATISFIED | `_fallback_title()`/`_fallback_name()` and tests for disabled/rejected fallback. |
| NAME-03 | 33-01, 33-03, 33-04 | Same unchanged community keeps same concept MOC filename across runs | SATISFIED | `_community_signature()` uses sorted member IDs/labels/source files; test asserts repeated filename stability. |
| NAME-04 | 33-01, 33-03, 33-04 | Concept naming provenance inspectable in generated metadata or dry-run output | SATISFIED | `ConceptName` return data plus `concept-names.json` sidecar records source/signature/reason/top terms; dry-run returns provenance without writing. |
| NAME-05 | 33-01, 33-03, 33-04 | Unsafe LLM-generated labels protected across filenames, tags, wikilinks, Dataview, and frontmatter | SATISFIED | `_validate_title_candidate()` rejects unsafe LLM names; `render_moc()` sanitizes generated titles and uses existing sink helpers; tests cover unsafe title sinks. |
| REPO-01 | 33-01, 33-02, 33-04 | CLI flag repo identity has highest precedence | SATISFIED | `--repo-identity` parsing in both command paths; resolver source `cli-flag`; tests assert CLI wins over profile. |
| REPO-02 | 33-01, 33-02, 33-04 | `profile.yaml` repo identity used when no CLI override supplied | SATISFIED | `profile.py` schema/default support plus `--obsidian` CR-01 fix loading vault profile before export; tests cover `run` and `--obsidian`. |
| REPO-03 | 33-01, 33-02, 33-04 | Deterministic auto-derived repo identity from git remote or current directory | SATISFIED | `.git/config` parser and cwd fallback in `naming.py`; tests cover both fallback sources. |

No orphaned Phase 33 requirement IDs were found. `REPO-04` is explicitly mapped to Phase 35, not Phase 33.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | No blocking TODO/FIXME/placeholders, orphaned helpers, or hardcoded empty data in the Phase 33 path | - | - |

### Human Verification Required

None. Phase 33 is helper/CLI/export plumbing with pure automated coverage; no visual, external-service, or real-time behavior is required for goal achievement.

### Gaps Summary

No gaps found. The codebase satisfies the roadmap success criteria and all eight Phase 33 requirement IDs with implementation, wiring, data flow, and focused automated tests.

---

_Verified: 2026-04-29T02:51:14Z_
_Verifier: Claude (gsd-verifier)_
