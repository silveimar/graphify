---
phase: 32-profile-contract-defaults
phase_number: 32
phase_name: profile-contract-defaults
status: verified
asvs_level: 1
threats_total: 16
threats_closed: 16
threats_open: 0
verified: 2026-04-29
---

# Phase 32 Security Audit

## Scope

Verified the declared threat models from:

- `32-01-PLAN.md`
- `32-02-PLAN.md`
- `32-03-PLAN.md`
- `32-04-PLAN.md`

Implementation files were treated as read-only. This audit verifies declared mitigations and SUMMARY threat flags only; it does not scan for unrelated vulnerabilities.

## Threat Verification

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-32-01 | Tampering | `.planning/REQUIREMENTS.md` | mitigate | CLOSED | `.planning/REQUIREMENTS.md:14`, `.planning/REQUIREMENTS.md:25`, and `.planning/REQUIREMENTS.md:28` use `taxonomy:`, `mapping.min_community_size`, and hard invalidation of `mapping.moc_threshold`; grep found no obsolete `clustering.min_community_size` match in the checked planning docs. |
| T-32-02 | Repudiation | `.planning/ROADMAP.md` | mitigate | CLOSED | `.planning/ROADMAP.md:274` through `.planning/ROADMAP.md:277` list all four Phase 32 plans; `.planning/ROADMAP.md:382` records Phase 32 as `4/4` complete. |
| T-32-03 | Information Disclosure | Planning output paths | accept | CLOSED | Accepted risk logged below. Scope was repo-local planning docs only; no vault-content or generated note path files were modified by Plan 01. |
| T-32-04 | Tampering | `taxonomy.folders.*` | mitigate | CLOSED | `graphify/profile.py:268` through `graphify/profile.py:287` reject non-string, empty, absolute, `~`, and `..` taxonomy path values; `graphify/profile.py:693` through `graphify/profile.py:705` applies that validation to supported taxonomy folders. |
| T-32-05 | Tampering | `taxonomy` schema | mitigate | CLOSED | `graphify/profile.py:177` defines allowed taxonomy keys; `graphify/profile.py:673` through `graphify/profile.py:678` rejects unsupported taxonomy keys. |
| T-32-06 | Repudiation | `mapping.moc_threshold` | mitigate | CLOSED | `graphify/profile.py:877` through `graphify/profile.py:881` emits a hard validation error naming `mapping.moc_threshold` and replacement `mapping.min_community_size`; `tests/test_profile.py:1009` through `tests/test_profile.py:1019` covers the case where both keys exist. |
| T-32-07 | Repudiation | Community overview templates | mitigate | CLOSED | `graphify/profile.py:1320` through `graphify/profile.py:1324` warns on `templates/community.md`; `graphify/profile.py:1344` through `graphify/profile.py:1348` warns on `community_templates` and points users to MOC-only migration guidance. |
| T-32-08 | Denial of Service | `mapping.min_community_size` | mitigate | CLOSED | `graphify/profile.py:882` through `graphify/profile.py:891` rejects bool, non-int, and values below 1; `tests/test_profile.py:754` through `tests/test_profile.py:758` covers bool rejection. |
| T-32-09 | Tampering | `graphify/mapping.py` folder resolution | mitigate | CLOSED | `graphify/mapping.py:269` through `graphify/mapping.py:288` centralizes effective folder resolution from the validated taxonomy contract before classification contexts are created. |
| T-32-10 | Tampering | Taxonomy vs `folder_mapping` precedence | mitigate | CLOSED | `graphify/mapping.py:281` through `graphify/mapping.py:288` overlays taxonomy folders onto `folder_mapping`; `tests/test_mapping.py:542` through `tests/test_mapping.py:573` asserts taxonomy MOC folder placement wins over conflicting `folder_mapping`. |
| T-32-11 | Denial of Service | `mapping.min_community_size` | mitigate | CLOSED | `graphify/mapping.py:613` through `graphify/mapping.py:619` preserves defensive bool/non-int fallback to `3`; strict user-facing errors are present in `graphify/profile.py:882` through `graphify/profile.py:891`. |
| T-32-12 | Repudiation | `_Unclassified` bucket | mitigate | CLOSED | `graphify/mapping.py:682` through `graphify/mapping.py:689` emits `_Unclassified` bucket metadata; `tests/test_mapping.py:593` through `tests/test_mapping.py:609` asserts deterministic bucket naming and routing fields. |
| T-32-13 | Repudiation | `graphify doctor` validation source | mitigate | CLOSED | `graphify/doctor.py:40` imports `validate_profile_preflight`; `graphify/doctor.py:347` through `graphify/doctor.py:351` copies preflight errors and warnings into the doctor report. |
| T-32-14 | Tampering | Unsupported taxonomy keys | mitigate | CLOSED | `graphify/doctor.py:347` through `graphify/doctor.py:351` surfaces preflight errors; `tests/test_doctor.py:96` through `tests/test_doctor.py:117` verifies unsupported taxonomy keys appear as blocking doctor errors. |
| T-32-15 | Repudiation | Deprecated community overview output | mitigate | CLOSED | `graphify/doctor.py:101` through `graphify/doctor.py:102` provides MOC-only fix guidance; `graphify/doctor.py:473` through `graphify/doctor.py:474` renders preflight warnings; `tests/test_doctor.py:134` through `tests/test_doctor.py:150` verifies `MOC-only output` warning behavior. |
| T-32-16 | Denial of Service | Doctor warnings | mitigate | CLOSED | `graphify/doctor.py:159` through `graphify/doctor.py:167` keeps `is_misconfigured()` tied to errors/unresolved output/self-ingestion, not warnings; `tests/test_doctor.py:145` through `tests/test_doctor.py:150` verifies warning-only community guidance is nonfatal. |

## Accepted Risks Log

| Threat ID | Risk | Rationale | Owner | Review Trigger |
|-----------|------|-----------|-------|----------------|
| T-32-03 | Plan 01 edits repo-local planning docs and does not touch vault contents or generated note paths. | The information-disclosure surface is limited to repository planning artifact wording. The phase implementation changed no vault content or generated note paths for this plan. | Phase 32 owner | Revisit if planning-doc edits start emitting vault paths, generated note paths, or user vault content. |

## Summary Threat Flags

No unregistered threat flags were found. `32-04-SUMMARY.md` explicitly reports `None`; `32-01-SUMMARY.md`, `32-02-SUMMARY.md`, and `32-03-SUMMARY.md` do not declare `## Threat Flags` sections.

## Verification Commands

```bash
rg -n "mapping\.min_community_size|32-04-PLAN\.md|mapping\.moc_threshold|validate_profile_preflight|min_community_size|Atlas/Sources/Graphify/MOCs|MOC-only output|_Unclassified|Unknown taxonomy key|path traversal" \
  ".planning/REQUIREMENTS.md" ".planning/ROADMAP.md" \
  "graphify/profile.py" "graphify/mapping.py" "graphify/export.py" "graphify/doctor.py" \
  "tests/test_profile.py" "tests/test_mapping.py" "tests/test_export.py" "tests/test_doctor.py"
```

## Result

All 16 declared Phase 32 threats are closed or documented as an accepted risk. No open threats remain.
