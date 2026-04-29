---
phase: 33
slug: naming-repo-identity-helpers
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
completed: 2026-04-29
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_mapping.py tests/test_export.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run focused `tests/test_naming.py` plus any touched module-paired test file.
- **After every plan wave:** Run `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_mapping.py tests/test_export.py tests/test_output.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green with `python3 -m pytest tests/ -q`
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 0 | NAME-01 | T-33-01 | Cached LLM title is reused when concept naming is enabled | unit | `python3 -m pytest tests/test_naming.py::test_concept_name_uses_cached_llm_title -q` | yes | green |
| 33-01-02 | 01 | 0 | NAME-02 | T-33-02 | Fallback name is deterministic when LLM is disabled, unavailable, or rejected | unit | `python3 -m pytest tests/test_naming.py::test_fallback_name_uses_terms_and_suffix -q` | yes | green |
| 33-01-03 | 01 | 0 | NAME-03 | T-33-03 | Same community signature yields same filename across reruns | unit | `python3 -m pytest tests/test_naming.py::test_same_signature_reuses_filename -q` | yes | green |
| 33-01-04 | 01 | 0 | NAME-04 | T-33-04 | Provenance records source, signature, and rejection/fallback reason | unit | `python3 -m pytest tests/test_naming.py::test_concept_name_provenance_records_source -q` | yes | green |
| 33-01-05 | 01 | 0 | NAME-05 | T-33-05 | Unsafe LLM labels are rejected or sanitized across filename, tag, wikilink, and frontmatter sinks | unit/integration | `python3 -m pytest tests/test_naming.py::test_unsafe_llm_title_rejected tests/test_templates.py -q` | yes | green |
| 33-01-06 | 01 | 0 | REPO-01 | T-33-06 | CLI repo identity wins over profile/fallback and reports source | unit/CLI | `python3 -m pytest tests/test_naming.py::test_repo_identity_cli_wins -q` | yes | green |
| 33-01-07 | 01 | 0 | REPO-02 | T-33-07 | `profile.yaml` `repo.identity` wins when CLI flag is absent | unit | `python3 -m pytest tests/test_profile.py::test_validate_profile_accepts_repo_identity tests/test_naming.py::test_repo_identity_profile_wins -q` | yes | green |
| 33-01-08 | 01 | 0 | REPO-03 | T-33-08 | Git remote slug fallback precedes cwd fallback and both are deterministic | unit | `python3 -m pytest tests/test_naming.py::test_repo_identity_fallback_git_remote_then_cwd -q` | yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `tests/test_naming.py` — new pure unit coverage for repo identity, concept signatures, fallback terms, cache IO, provenance, and LLM rejection.
- [x] `tests/test_profile.py` — extend schema coverage for `repo:` and concept naming controls.
- [x] `tests/test_export.py` — prove `to_obsidian()` receives resolved concept names and keeps MOC filenames stable.
- [x] `tests/test_templates.py` — add explicit unsafe generated community title coverage across filename, tag, wikilink, and frontmatter if existing tests do not cover the combined MOC path.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Nyquist-compliant after 8/8 verification truths passed.
