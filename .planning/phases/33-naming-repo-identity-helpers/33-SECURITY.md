---
phase: 33-naming-repo-identity-helpers
phase_number: 33
status: verified
asvs_level: 1
threats_total: 22
threats_closed: 22
threats_open: 0
unregistered_flags: 0
verified: 2026-04-29
---

# Phase 33 Security Audit: Naming & Repo Identity Helpers

## Summary

Phase 33 declared 22 threats across four implementation plans. All mitigated threats were verified against implementation or test evidence. The four accepted risks are documented below in the accepted risks log. No `## Threat Flags` entries in the phase summaries were unregistered.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-33-01 | Tampering | mitigate | CLOSED | `tests/test_naming.py:146-173` includes unsafe LLM title candidates (`]] | bad`, `{{#connections}}`, `../escape`, empty, generic) and asserts fallback/rejection plus dry-run no sidecar writes. |
| T-33-02 | Tampering | mitigate | CLOSED | `tests/test_profile.py:222-256` asserts invalid `repo.identity` values, including path traversal, slash, backslash, and nested `naming.repo`, are rejected. |
| T-33-03 | Denial of Service | mitigate | CLOSED | `graphify/naming.py:349-373` rejects generic, empty, duplicate, control-character, path-like, template-breaking, wikilink-breaking, and over-80-character candidates; `tests/test_naming.py:125-143` verifies generic title fallback. |
| T-33-04 | Repudiation | mitigate | CLOSED | `graphify/naming.py:25-31` exposes `ConceptName.source`, `signature`, and `reason`; `graphify/naming.py:429-438` persists provenance fields including `top_terms`; `tests/test_naming.py:125-143` asserts provenance is present on fallback/rejection. |
| T-33-05 | Information Disclosure | accept | CLOSED | Accepted risk documented below. Test fixtures are synthetic and use `tmp_path` artifact directories, e.g. `tests/test_naming.py:22-52`, `tests/test_naming.py:64-66`, and `tests/test_naming.py:157-173`. |
| T-33-06 | Tampering | mitigate | CLOSED | `graphify/naming.py:52-64` rejects `/`, `\`, and `..`, normalizes to a short slug, and caps long slugs with a deterministic SHA-256 suffix. |
| T-33-07 | Spoofing | mitigate | CLOSED | `graphify/naming.py:127-173` enforces CLI > profile > git remote > directory precedence and reports the winning source to stderr; `tests/test_naming.py:176-235` covers CLI/profile/fallback source reporting. |
| T-33-08 | Denial of Service | mitigate | CLOSED | `graphify/naming.py:34` sets the 80-character repo identity cap; `graphify/naming.py:61-63` applies hash-suffix truncation; `graphify/naming.py:119-123` rejects empty explicit values with warnings. |
| T-33-09 | Tampering | mitigate | CLOSED | `graphify/naming.py:67-80` extracts only the remote basename slug; `graphify/naming.py:83-102` uses `configparser` and falls back when config is absent or unreadable; `tests/test_naming.py:210-235` covers `.git/config` fallback without shelling out. |
| T-33-10 | Information Disclosure | accept | CLOSED | Accepted risk documented below. Success reporting prints normalized identity plus source only at `graphify/naming.py:139`, `graphify/naming.py:150`, `graphify/naming.py:156-159`, and `graphify/naming.py:169-172`. |
| T-33-11 | Tampering | mitigate | CLOSED | `graphify/naming.py:349-373` rejects unsafe title candidates before cache persistence or export use. |
| T-33-12 | Tampering | mitigate | CLOSED | `graphify/naming.py:182-195` hashes sorted member IDs, labels, and source files into a SHA-256 signature; `graphify/naming.py:400-408` checks exact cache entries by signature before legacy community-id compatibility. |
| T-33-13 | Repudiation | mitigate | CLOSED | `graphify/naming.py:25-31` returns source/signature/reason; `graphify/naming.py:429-438` records source, signature, reason, filename stem, top terms, and community id in cache entries. |
| T-33-14 | Denial of Service | mitigate | CLOSED | `graphify/naming.py:49` sets `_MAX_TITLE_LEN = 80`; `graphify/naming.py:358-359` rejects overlong LLM title candidates before persistence. |
| T-33-15 | Tampering | mitigate | CLOSED | `graphify/naming.py:411-426` requires top-term overlap for tolerant cache reuse; `graphify/naming.py:520-529` marks source as `cache-tolerant` and records previous/current signatures in the reason. |
| T-33-16 | Information Disclosure | accept | CLOSED | Accepted risk documented below. Sidecar data is graph-derived naming provenance written by `graphify/naming.py:429-438` and saved only as `concept-names.json` under the supplied artifacts dir at `graphify/naming.py:326-342`. |
| T-33-17 | Spoofing | mitigate | CLOSED | `graphify/__main__.py:49-71` parses `--repo-identity` and missing-value errors; `graphify/__main__.py:1401-1403` and `graphify/__main__.py:1486-1492` thread it to `to_obsidian`; `graphify/__main__.py:2238-2262` resolves it on `run`. |
| T-33-18 | Tampering | mitigate | CLOSED | `graphify/export.py:629-651` resolves concept names and gives explicit `community_labels` precedence; `graphify/export.py:660-665` injects final labels/tags; `graphify/templates.py:675-686` normalizes generated titles before sinks. |
| T-33-19 | Tampering | mitigate | CLOSED | `graphify/export.py:629-636` passes `dry_run` to concept naming; `graphify/naming.py:582-584` writes `concept-names.json` only when not dry-run; `tests/test_export.py:295-314` asserts dry-run sidecar absence. |
| T-33-20 | Tampering | mitigate | CLOSED | `graphify/templates.py:675-686` sanitizes generated titles; `graphify/profile.py:1133-1164` provides tag/filename safety; `graphify/templates.py:654-660` sanitizes wikilink aliases; `graphify/profile.py:1167-1200` dumps sanitized frontmatter; `tests/test_templates.py:12-45` covers combined sink safety. |
| T-33-21 | Elevation of Privilege | mitigate | CLOSED | `graphify/__main__.py:49-71` removes parsed repo identity flags from argv and exits 2 on missing values; `graphify/__main__.py:2238-2255` strips the flag before `raw_target` selection; `tests/test_main_flags.py:302-313` asserts missing-value exit 2. |
| T-33-22 | Information Disclosure | accept | CLOSED | Accepted risk documented below. `graphify/export.py:26-43` writes `repo-identity.json` with normalized identity/source/raw value/warnings only on non-dry-run paths via `graphify/export.py:622-628`. |

## Accepted Risks Log

| Threat ID | Risk | Acceptance Rationale |
|-----------|------|----------------------|
| T-33-05 | Synthetic test fixtures may include representative unsafe labels. | Accepted because fixtures are local pytest data using `tmp_path` and do not read real vault content or secrets. |
| T-33-10 | Repo identity source reporting appears on stderr. | Accepted because success lines report normalized identity and source only, not raw remote URLs or full filesystem paths. |
| T-33-16 | `concept-names.json` stores graph-derived naming provenance. | Accepted because the sidecar contains graph labels/source-file metadata already present in generated graph outputs and does not introduce new secret sources. |
| T-33-22 | `repo-identity.json` stores repo identity provenance, including raw winning value. | Accepted because Phase 33 intentionally records the resolved identity artifact; broader migration/manifest consistency is outside this phase. |

## Unregistered Flags

None. All four phase summaries reported `## Threat Flags` as `None`; Plan 04 explicitly stated the new CLI argument, generated sidecar write, dry-run filesystem boundary, and generated-title template sinks were covered by the plan threat model.

## Result

`threats_open: 0`

Phase 33 is security-verified for the declared threat model.
