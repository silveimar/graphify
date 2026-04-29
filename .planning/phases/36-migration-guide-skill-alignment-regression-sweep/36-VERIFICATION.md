---
phase: 36-migration-guide-skill-alignment-regression-sweep
verified: 2026-04-29T08:46:06Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: not_passed
  previous_score: 8/9
  issues_closed:
    - "Maintainer can confirm skill files and CLI/install docs use the same v1.8 Obsidian export behavior, with stale generated `_COMMUNITY_*` claims gone."
  issues_remaining: []
  regressions: []
---

# Phase 36: Migration Guide, Skill Alignment & Regression Sweep Verification Report

**Phase Goal:** Users and maintainers can trust the v1.8 behavior because docs, skill files, tests, and security checks all describe and verify the same export contract.
**Verified:** 2026-04-29T08:46:06Z
**Status:** passed
**Re-verification:** Yes - after gap closure plan 36-05

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User receives a Markdown migration guide covering backup, validation, dry-run, migration command, review, cleanup/archive, rollback, and rerun steps. | VERIFIED | Prior passed truth regression-checked against Phase 36 artifacts: `MIGRATION_V1_8.md`, README/CLI docs contract tests, and Phase 36 validation/security evidence remain present. |
| 2 | Reviewed `graphify update-vault --apply --plan-id <id>` archives legacy notes by default after successful apply. | VERIFIED | Prior passed truth regression-checked via `tests/test_main_flags.py`; focused re-run passed and includes `test_update_vault_apply_archives_legacy_notes_by_default`. |
| 3 | Legacy notes are archived outside the vault notes tree under `graphify-out/migrations/archive/` with rollback metadata. | VERIFIED | Prior passed truth unchanged; `tests/test_main_flags.py` still asserts the archive path appears in apply output. |
| 4 | Archive movement is plan-driven, reversible, path-confined, content-hash-bound, and covered by `tmp_path` tests. | VERIFIED | Prior passed truth unchanged; `36-SECURITY.md` and `36-REVIEW-FIX.md` record hash binding, collision preflight, path confinement, and helper-level coverage. |
| 5 | Skill files and CLI/install docs use the same v1.8 Obsidian export behavior; stale generated `_COMMUNITY_*` claims are gone. | VERIFIED | Gap closure confirmed: `_CLAUDE_MD_SECTION` and `_AGENTS_MD_SECTION` now direct agents to `GRAPH_REPORT.md`, Obsidian MOC notes with `[[wikilinks]]`, and `wiki/index.md` fallback. `tests/test_skill_files.py` imports both constants, checks required install phrases, and applies forbidden stale `_COMMUNITY_*` phrase/pattern guards to them. |
| 6 | Maintainer can verify v1.8 behavior with pure unit/CLI/docs tests using `tmp_path` and no network. | VERIFIED | Focused re-verification run: `pytest tests/test_skill_files.py tests/test_main_flags.py -q` -> 30 passed. Provided post-gap full-suite evidence: `pytest tests/ -q` -> 1901 passed, 1 xfailed, 8 warnings. |
| 7 | Sanitizer coverage matrix maps new path, template, profile, LLM-label, repo-identity, archive, tag, wikilink, Dataview, frontmatter, and CODE filename inputs to helpers and executable tests. | VERIFIED | Prior passed truth unchanged; `tests/test_v18_security_matrix.py` and `36-SECURITY.md` map each locked VER-03 input class to executable helper assertions. |
| 8 | Locked context decisions D-01 through D-16 are honored. | VERIFIED | Prior passed truth unchanged; gap closure additionally satisfies D-06/D-07 by covering installed Claude/AGENTS guidance, not only packaged skill variants. |
| 9 | Review findings BL-01, BL-02, HI-01, MD-01, and the Phase 36 install-guidance gap are fixed. | VERIFIED | `36-REVIEW-FIX.md` records earlier review fixes; `36-05-SUMMARY.md` records commits `d2025bc` and `129d572` for install guidance alignment and drift tests. Scoped post-gap review is clean. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `MIGRATION_V1_8.md` | Generic-first migration guide | VERIFIED | Prior passed artifact unchanged; guide contract covered by Phase 36 docs tests and validation evidence. |
| `README.md` | English docs pointer and v1.8 migration summary | VERIFIED | Prior passed artifact unchanged; README/guide alignment remains within Phase 36 validation scope. |
| `graphify/migration.py` | Archive helper, metadata, and apply orchestration | VERIFIED | Prior passed artifact unchanged; earlier review/fix artifacts show apply, hash, and archive safety fixes. |
| `graphify/__main__.py` | CLI help and install-time guidance aligned to v1.8 | VERIFIED | `_CLAUDE_MD_SECTION` and `_AGENTS_MD_SECTION` contain `GRAPH_REPORT.md`, MOC navigation, `[[wikilinks]]`, and `wiki/index.md`; stale `_COMMUNITY_* overview notes` guidance is absent. |
| `graphify/skill*.md` | Platform skill v1.8 wording | VERIFIED | Packaged variants remain covered by required phrase and forbidden stale-claim tests. |
| `tests/test_migration.py` | Archive helper/apply tests | VERIFIED | Prior passed artifact unchanged; covered by prior Phase 36 validation and full-suite evidence. |
| `tests/test_main_flags.py` | CLI archive/help tests | VERIFIED | Focused re-run passed; includes update-vault archive/default and help-text coverage. |
| `tests/test_docs.py` | Docs contract tests | VERIFIED | Prior passed artifact unchanged; documented in validation/security evidence. |
| `tests/test_skill_files.py` | Skill and install-guidance drift tests | VERIFIED | Imports `graphify.__main__`, defines `INSTALL_GUIDANCE_SECTIONS`, checks install-specific required phrases, and reuses stale generated-output guards. |
| `tests/test_v18_security_matrix.py` | Executable sanitizer matrix | VERIFIED | Prior passed artifact unchanged; matrix remains security evidence for VER-03. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graphify/__main__.py` | `graphify.migration.run_update_vault` | `update-vault` command branch | WIRED | Prior passed link unchanged; CLI tests still pass. |
| `graphify/migration.py` | `graphify.merge.apply_merge_plan` | reviewed apply branch | WIRED | Prior passed link unchanged; archive runs after successful apply. |
| `graphify/migration.py` | `graphify.profile.validate_vault_path` | archive source and action path validation | WIRED | Prior passed link unchanged; security artifact records mitigation. |
| `tests/test_skill_files.py` | `graphify/skill*.md` | `PRIMARY_SKILL` and `PLATFORM_VARIANTS` loop | WIRED | All packaged skill variants remain covered by phrase contract tests. |
| `tests/test_skill_files.py` | `graphify/__main__.py` install-time sections | imported install guidance section constants | WIRED | Closed gap: `INSTALL_GUIDANCE_SECTIONS` includes `graphify_main._CLAUDE_MD_SECTION` and `graphify_main._AGENTS_MD_SECTION`; tests assert required install phrases and reject stale generated `_COMMUNITY_*` claims. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `graphify/migration.py` | `archived_legacy_notes` | `archive_legacy_notes()` after validated apply | Yes | FLOWING |
| `graphify/migration.py` | `legacy_mappings[].old_content_hash` and action `content_hash` | `scan_legacy_notes()` and preview construction | Yes | FLOWING |
| `tests/test_v18_security_matrix.py` | `SANITIZER_COVERAGE_MATRIX` | parametrized pytest dispatch | Yes | FLOWING |
| `tests/test_skill_files.py` | `INSTALL_GUIDANCE_SECTIONS` | `graphify.__main__` embedded install constants | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gap closure focused gate | `pytest tests/test_skill_files.py tests/test_main_flags.py -q` | 30 passed in 24.60s | PASS |
| Full suite gate after gap closure | `pytest tests/ -q` | Provided evidence: 1901 passed, 1 xfailed, 8 warnings | PASS |
| Scoped post-gap code review | `36-REVIEW.md` | status clean, 0 findings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MIG-05 | 36-01, 36-02 | Markdown migration guide with backup, validation, dry-run, migration command, review, cleanup, rollback, and rerun steps. | SATISFIED | Prior passed guide and docs contract evidence remains valid. |
| VER-01 | 36-01, 36-04 | Pure unit/CLI/docs tests using `tmp_path` and no network calls. | SATISFIED | Focused tests passed locally; full-suite post-gap evidence is green. |
| VER-02 | 36-02, 36-03, 36-05 | Skill files, CLI docs, and install-time Claude/AGENTS guidance use the same v1.8 Obsidian export behavior. | SATISFIED | Gap closure adds install guidance alignment plus regression tests for `_CLAUDE_MD_SECTION` and `_AGENTS_MD_SECTION`; focused gate passes. |
| VER-03 | 36-04 | New path/template/profile/LLM-label/repo-identity inputs pass through sanitization helpers. | SATISFIED | Prior passed sanitizer matrix evidence remains valid. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | N/A | N/A | N/A | No blocker anti-patterns remain in the gap-closure scope. |

### Human Verification Required

None. Phase 36 behavior is docs, CLI help, install guidance strings, local migration behavior, and regression/security tests; all remaining checks are automatable.

### Gaps Summary

No gaps remain. The previous VER-02 blocker is closed because installed Claude/AGENTS guidance now matches the v1.8 MOC/wiki/GRAPH_REPORT navigation contract and `tests/test_skill_files.py` covers those embedded install-time sections against stale generated `_COMMUNITY_*` claims. Automated focused re-verification passed, and provided full-suite evidence is green.

---

_Verified: 2026-04-29T08:46:06Z_
_Verifier: Claude (gsd-verifier)_
