# Phase 34: Mapping, Cluster Quality & Note Classes - Validation

**Created:** 2026-04-29  
**Source:** `34-RESEARCH.md` Validation Architecture  
**Status:** Ready for execution

## Validation Goal

Phase 34 is valid when automated tests prove MOC-only community output, cluster-quality floor routing, CODE note classification, CODE filename collision safety, and CODE↔concept navigation without scanning legacy vault files or expanding Phase 35/36 scope.

## Requirement Coverage

| Req ID | Behavior To Prove | Primary Tests | Automated Command |
|--------|-------------------|---------------|-------------------|
| COMM-01 | Default Obsidian export creates MOC notes only and no generated `_COMMUNITY_*` paths; legacy `community` note type warns/coerces to MOC. | `tests/test_export.py`, `tests/test_templates.py`, `tests/test_profile.py` | `pytest tests/test_export.py tests/test_templates.py tests/test_profile.py -q` |
| CLUST-02 | Isolate below-floor communities do not receive standalone MOCs, while their nodes remain renderable and point to `_Unclassified`. | `tests/test_mapping.py`, `tests/test_export.py` | `pytest tests/test_mapping.py tests/test_export.py -q` |
| CLUST-03 | Connected below-floor communities host under the nearest above-floor MOC first; hostless or isolate communities route to `_Unclassified`. | `tests/test_mapping.py` | `pytest tests/test_mapping.py -q` |
| GOD-01 | Eligible code-backed god nodes classify/render as `code` notes with `CODE_<repo>_<node>.md` paths. | `tests/test_mapping.py`, `tests/test_export.py`, `tests/test_templates.py` | `pytest tests/test_mapping.py tests/test_export.py tests/test_templates.py -q` |
| GOD-02 | CODE notes link upward to their related concept MOC through frontmatter and body/Wayfinder wikilinks. | `tests/test_templates.py`, `tests/test_export.py` | `pytest tests/test_templates.py tests/test_export.py -q` |
| GOD-03 | Concept MOCs list capped important CODE member notes, preserving bidirectional navigation. | `tests/test_mapping.py`, `tests/test_templates.py` | `pytest tests/test_mapping.py tests/test_templates.py -q` |
| GOD-04 | CODE filename collisions receive deterministic hash suffixes and cannot collide with concept MOCs. | `tests/test_naming.py`, `tests/test_export.py` | `pytest tests/test_naming.py tests/test_export.py -q` |

## Wave 0 Test Expectations

Plans should create or update tests before production code for these behaviors:

- `tests/test_profile.py`: default `mapping.min_community_size == 6`, `code` note-type validation, and legacy `community` compatibility warnings.
- `tests/test_mapping.py`: literal floor overrides, standalone/hosted/bucketed routing metadata, isolate `_Unclassified` behavior, CODE eligibility, and capped CODE member context.
- `tests/test_naming.py`: CODE filename helper, order-independent collision suffixes, unsafe-label normalization, and collision provenance.
- `tests/test_export.py`: dry-run CODE paths, no generated `_COMMUNITY_*` paths, collision-stable path sets, and final concept-label propagation.
- `tests/test_templates.py`: CODE `up:` links, MOC CODE-member links, `filename_stem` consumption, and sanitizer-backed wikilinks.

## Sampling Plan

| Stage | Command | Required Result |
|-------|---------|-----------------|
| Plan 34-01 | `pytest tests/test_profile.py tests/test_templates.py -q` | Profile/template contract passes. |
| Plan 34-02 | `pytest tests/test_mapping.py -q` | Routing metadata and CODE eligibility pass. |
| Plan 34-03 | `pytest tests/test_naming.py tests/test_export.py tests/test_templates.py -q` | CODE filename helper, export injection, filename-stem rendering, and MOC-only dispatch pass. |
| Plan 34-04 | `pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q` | Focused Phase 34 gate passes. |
| Phase gate | `pytest tests/ -q` | Full suite is run; only documented pre-existing baseline failures may remain. |

## Known Baseline Failures

`.planning/STATE.md` lists deferred baseline failures outside Phase 34:

- `tests/test_detect.py::test_detect_skips_dotfiles`
- `tests/test_extract.py::test_collect_files_from_dir`

Executors must not fix these in Phase 34 unless Phase 34 changes introduce or alter the failure. If the full suite still reports them after the focused gate passes, record them in the relevant plan summary as pre-existing deferred baseline failures.

## Out-Of-Scope Validation

The following are explicitly not Phase 34 validation targets:

- Scanning existing vault files for legacy `_COMMUNITY_*` notes.
- Producing migration candidates, orphan reports, or migration dry-run outcome classes.
- Writing the Phase 36 migration guide or sweeping skill/docs references.
- Deleting, replacing, or otherwise mutating legacy vault notes.

## Nyquist Gate

Phase 34 passes the validation architecture when every requirement row above has at least one automated test assertion in the named test files and the focused Phase 34 gate passes:

```bash
pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q
```
