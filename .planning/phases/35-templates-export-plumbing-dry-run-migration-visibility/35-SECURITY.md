---
phase: 35-templates-export-plumbing-dry-run-migration-visibility
secured: 2026-04-29T06:33:00Z
status: verified
asvs_level: 1
threats_total: 16
threats_closed: 16
threats_open: 0
unregistered_flags: 0
---

# Phase 35: Security Audit

**Phase:** 35 - templates-export-plumbing-dry-run-migration-visibility  
**Status:** verified  
**Scope:** Verify declared threat mitigations from `35-01-PLAN.md`, `35-02-PLAN.md`, `35-03-PLAN.md`, and SUMMARY threat flags only.  
**Result:** 16/16 declared threats closed; no unregistered threat flags found.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-35-01 | Tampering | mitigate | CLOSED | `graphify/migration.py:37-56` resolves the vault root, uses `os.walk(..., followlinks=False)`, and validates each candidate with `validate_vault_path()` before reporting it. |
| T-35-02 | Tampering | mitigate | CLOSED | `graphify/migration.py:22`, `graphify/migration.py:333-352`, and `graphify/migration.py:623-631` enforce digest-shaped plan IDs, reject separators/`..`, and recompute the content digest before trusting the artifact. |
| T-35-03 | Tampering | mitigate | CLOSED | `graphify/migration.py:356-375` compares resolved input path, vault path, repo identity, recomputed digest, and current preview plan ID before apply can proceed. |
| T-35-04 | Information Disclosure | mitigate | CLOSED | `graphify/migration.py:144-156`, `graphify/migration.py:452-469`, and `graphify/migration.py:585-594` serialize preview metadata, relative action rows, mappings, and summaries; source/note body contents are not part of the preview digest or action rows. |
| T-35-05 | Repudiation | mitigate | CLOSED | `graphify/migration.py:126-139` marks legacy ORPHAN rows review-only, `graphify/migration.py:378-383` filters apply actions to CREATE/UPDATE/REPLACE, and `tests/test_migration.py:234-277` asserts legacy files still exist after apply. |
| T-35-06 | Tampering | mitigate | CLOSED | `graphify/export.py:617-626` uses `resolve_repo_identity()`, `graphify/export.py:711-721` passes the resolved identity into CODE contexts, and `graphify/templates.py:1108-1125` applies `safe_tag()` plus `safe_frontmatter_value()` before emitting tags/frontmatter. |
| T-35-07 | Tampering | mitigate | CLOSED | `graphify/merge.py:1129-1165` records per-note `repo_identity` from rendered frontmatter and stores run-level metadata under reserved `__graphify_run__`. |
| T-35-08 | Tampering | mitigate | CLOSED | `graphify/merge.py:1068-1089` tolerates old manifests and identifies reserved metadata keys; `graphify/merge.py:1167-1174` skips `__graphify_` keys during path-entry cleanup; `tests/test_merge.py:1540-1569` proves missing repo identity does not create a conflict. |
| T-35-09 | Repudiation | mitigate | CLOSED | `graphify/merge.py:1155-1165` stores per-note and run-level repo identity; `graphify/migration.py:472-502` classifies concrete repo drift as `SKIP_CONFLICT` with `repo_identity_drift` evidence. |
| T-35-10 | Information Disclosure | accept | CLOSED | Accepted risk logged below: normalized repo identity is already present in CODE filenames and preview output; manifest storage adds no source contents or note bodies. |
| T-35-11 | Tampering | mitigate | CLOSED | `graphify/migration.py:171-176` resolves paths, requires existing input, and requires target `.obsidian/`; `graphify/migration.py:189-224` uses `resolve_output(vault)` and passes resolved output roots into preview construction. |
| T-35-12 | Tampering | mitigate | CLOSED | `graphify/migration.py:333-352` delegates `--plan-id` lookup to validated artifact loading; `graphify/migration.py:623-631` rejects empty, malformed, separator-containing, or traversal-shaped IDs. |
| T-35-13 | Tampering | mitigate | CLOSED | `graphify/migration.py:226-246` loads the reviewed artifact, validates it against the current dry-run preview, reconstructs a classified plan from filtered applicable rows, and applies through `apply_merge_plan()`. |
| T-35-14 | Spoofing | mitigate | CLOSED | `graphify/migration.py:191-195` resolves repo identity from input/profile/CLI; `graphify/export.py:711-721` reuses the resolved slug for CODE rows; `graphify/templates.py:1108-1125` sanitizes CODE repo metadata before sink emission. |
| T-35-15 | Tampering | mitigate | CLOSED | `graphify/export.py:828-837` dry-run plans still come from `compute_merge_plan()`; `graphify/merge.py:921-939` preserves user-modified notes as `SKIP_PRESERVE`; `graphify/migration.py:238-246` applies only the validated classified plan through `apply_merge_plan()`. |
| T-35-16 | Repudiation | mitigate | CLOSED | `graphify/migration.py:126-139` keeps legacy `_COMMUNITY_*` files as ORPHAN/review rows, `graphify/migration.py:378-383` excludes ORPHAN rows from applicable actions, and `graphify/merge.py:1320-1322` skips ORPHAN/SKIP actions during apply. |

## Accepted Risks Log

| Threat ID | Risk | Acceptance Rationale | Evidence |
|-----------|------|----------------------|----------|
| T-35-10 | Manifest JSON records normalized repo identity. | The normalized slug is already present in CODE filenames and CLI preview; manifest storage does not include source content or note bodies. | Plan 02 declared `accept`; implementation records only `repo_identity` metadata in `graphify/merge.py:1155-1165`. |

## SUMMARY Threat Flags

No unregistered threat flags were found.

- `35-01-SUMMARY.md`: no `## Threat Flags` section present.
- `35-02-SUMMARY.md`: `## Threat Flags` is `None`.
- `35-03-SUMMARY.md`: `## Threat Flags` is `None`; declared new CLI/apply surfaces are covered by the Plan 03 threat model.

## Review Context

Prior code review blocker CR-01 is included as audit context but not counted as a threat-register item. `35-REVIEW-FIX.md` records fix commit `260f09d`, which changed `build_migration_preview()` and apply reconstruction to honor profile-routed output roots. `35-REVIEW.md` subsequently reports a clean review with no remaining findings.

## Verification Commands

- `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q`

## Security Decision

All declared mitigations are present in implementation and tests. Phase 35 has `threats_open: 0` and is security-verified for the declared threat model.
