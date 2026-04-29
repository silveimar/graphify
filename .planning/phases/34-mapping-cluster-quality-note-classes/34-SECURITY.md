---
phase: 34-mapping-cluster-quality-note-classes
verified: 2026-04-29T06:27:00Z
status: verified
asvs_level: 1
threats_total: 22
threats_closed: 22
threats_open: 0
block_on: open
---

# Phase 34: Mapping, Cluster Quality & Note Classes Security Verification

## Summary

All declared Phase 34 threat mitigations were verified against implementation, tests, transfer documentation, or the accepted risks log below. No `SUMMARY.md` artifact registered new threat flags.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-34-01-01 | Tampering | mitigate | CLOSED | `graphify/profile.py:171-173` accepts `code` and compatibility `community`; `graphify/profile.py:657-660` enforces the allowlist; `tests/test_profile.py:1625-1643` covers `code`. |
| T-34-01-02 | Tampering | mitigate | CLOSED | `graphify/templates.py:1067-1071` accepts `code`; `graphify/templates.py:1111-1147` builds and dumps frontmatter via helpers; `graphify/templates.py:1093-1099` and `graphify/templates.py:654-672` route wikilinks through `_emit_wikilink()` / `_sanitize_wikilink_alias()`. |
| T-34-01-03 | Tampering / Data loss | mitigate | CLOSED | No implementation path scans or deletes legacy `_COMMUNITY_*` vault notes; `tests/test_export.py:393-402` asserts generated create paths do not include `_COMMUNITY_`. |
| T-34-01-04 | Spoofing / Collision | transfer | CLOSED | Transfer target Plan 03 exists in `34-03-PLAN.md`; implemented by `graphify/naming.py:246-282` and covered by `tests/test_naming.py:238-318`. |
| T-34-02-01 | Tampering | mitigate | CLOSED | `graphify/mapping.py:408-414` stores classification context only; filename/path construction occurs downstream in `graphify/export.py:699-743` and `graphify/templates.py:1213-1217`. |
| T-34-02-02 | Spoofing | mitigate | CLOSED | `graphify/mapping.py:226-241` requires god-node membership, `file_type == "code"`, non-empty `source_file`, and excludes concept/file nodes before CODE assignment. |
| T-34-02-03 | Tampering | mitigate | CLOSED | `graphify/mapping.py:644-655` and `graphify/mapping.py:683-695` emit MOC contexts; `graphify/export.py:751-754` avoids per-node MOC/community double rendering. |
| T-34-02-04 | Denial of Service | mitigate | CLOSED | `graphify/mapping.py:487-514` caps structured CODE members through `_MAX_CODE_MEMBERS`; `tests/test_mapping.py:652-685` verifies deterministic top-10 ordering. |
| T-34-02-05 | Tampering / Data loss | mitigate | CLOSED | No mapping/export implementation scans existing vault files for `_COMMUNITY_*`; `tests/test_export.py:393-402` verifies no generated `_COMMUNITY_` output paths. |
| T-34-02-06 | Spoofing / Collision | transfer | CLOSED | Transfer target Plan 03 exists in `34-03-PLAN.md`; collision handling implemented in `graphify/naming.py:246-282` and verified by `tests/test_naming.py:259-318`. |
| T-34-03-01 | Tampering | mitigate | CLOSED | `graphify/naming.py:127-173` resolves normalized repo identity; `graphify/naming.py:235-243` normalizes filename stems before `graphify/naming.py:259` builds CODE stems. |
| T-34-03-02 | Spoofing / Collision | mitigate | CLOSED | `graphify/naming.py:267-281` groups by base stem and suffixes every collision with `sha256(node_id + "\0" + source_file)[:8]`; tests at `tests/test_naming.py:259-318`. |
| T-34-03-03 | Tampering | mitigate | CLOSED | `graphify/export.py:711-743` injects filename stems into contexts only; `graphify/templates.py:1213-1217` applies `safe_filename()` at render time. |
| T-34-03-04 | Tampering | mitigate | CLOSED | `graphify/templates.py:1213-1217` consumes sanitized `filename_stem` for CODE filename rendering; frontmatter/wiki metadata remains in `graphify/templates.py:1111-1147`. |
| T-34-03-05 | Tampering / Data loss | mitigate | CLOSED | Legacy community overview rendering remains compatibility-only in `graphify/templates.py:1491-1515`; export dry-run regression at `tests/test_export.py:393-402` confirms normal generated output avoids `_COMMUNITY_`. |
| T-34-04-01 | Tampering | mitigate | CLOSED | CODE up-links use `_emit_wikilink()` in `graphify/templates.py:1093-1099`; MOC CODE member links use `safe_filename()` plus `_sanitize_wikilink_alias()` in `graphify/templates.py:887-905`; tests at `tests/test_templates.py:48-91` and `tests/test_templates.py:1586-1605`. |
| T-34-04-02 | Tampering | mitigate | CLOSED | Collision metadata is added to the frontmatter fields dict in `graphify/templates.py:1126-1130` and serialized by `_dump_frontmatter()` at `graphify/templates.py:1147`; test at `tests/test_templates.py:1041-1057`. |
| T-34-04-03 | Spoofing | mitigate | CLOSED | Final concept labels propagate into per-node `parent_moc_label` / `community_name` after concept naming in `graphify/export.py:647-697`; export test coverage at `tests/test_export.py:437-457`. |
| T-34-04-04 | Repudiation | mitigate | CLOSED | Focused Phase 34 test gate passed: `486 passed, 1 xfailed, 2 warnings`; full suite passed: `1871 passed, 1 xfailed, 8 warnings`. |
| T-34-04-05 | Tampering / Data loss | mitigate | CLOSED | Implementation changes are limited to generated output behavior; no `_COMMUNITY_*` vault-file scan/edit/delete path was found, and `tests/test_export.py:393-402` asserts no generated `_COMMUNITY_` paths. |
| T-34-05-01 | Tampering | mitigate | CLOSED | `_build_code_member_links()` preserves exact `filename_stem` targets after `safe_filename()` only in `graphify/templates.py:887-905`; regression at `tests/test_templates.py:48-91`. |
| T-34-05-02 | Tampering | mitigate | CLOSED | CODE member aliases are sanitized through `_sanitize_wikilink_alias()` in `graphify/templates.py:901-905`; regression at `tests/test_templates.py:1586-1605`. |
| T-34-05-03 | Spoofing | mitigate | CLOSED | CODE/MOC target identity remains export-provided: `graphify/export.py:711-743` enriches contexts from `build_code_filename_stems()`; templates consume `filename_stem` without deriving new CODE targets at `graphify/templates.py:887-905`. |
| T-34-05-04 | Information Disclosure | accept | CLOSED | Accepted risk logged below; renderer evidence at `graphify/templates.py:1175-1189` and `graphify/builtin_templates/code.md:1-10` shows generated CODE notes use supplied graph/export context and no new data source. |

## Accepted Risks

| Threat ID | Category | Risk | Acceptance Rationale |
|-----------|----------|------|----------------------|
| T-34-05-04 | Information Disclosure | Generated Markdown labels may expose labels already present in graph/export context. | Accepted because Phase 34 renderer emits only labels already present in the graph/export context and introduces no new data source. |

## Unregistered Flags

None. `34-01-SUMMARY.md`, `34-02-SUMMARY.md`, `34-03-SUMMARY.md`, `34-04-SUMMARY.md`, and `34-05-SUMMARY.md` all report `Threat Flags: None.`

## Verification Commands

```bash
pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q
# 486 passed, 1 xfailed, 2 warnings

pytest tests/ -q
# 1871 passed, 1 xfailed, 8 warnings
```
