# Phase 50: v1.10 gap — Baselines verification — Research

**Researched:** 2026-04-30  
**Domain:** GSD milestone hygiene — Nyquist-style verification artifacts, requirements reconciliation, pytest evidence  
**Confidence:** HIGH for “what is missing and why”; HIGH for code↔test mapping (spot-checked in repo); MEDIUM for final `45-VALIDATION.md` frontmatter edits (orchestrator/process choice)

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|----|-------------|-------------------|
| HYG-01 | Quick-task self-ingestion fix: `corpus_prune`, manifest `prior_files` (default `graphify-out` when `resolved is None`), one-line stderr for manifest skips, `collect_files(..., resolved=)` parity, optional `corpus.dot_graphify`, doctor track flags | Map to `45-01`/`45-02` plans + `graphify/corpus_prune.py`, `detect.py`, `extract.collect_files`, `profile.py`, `doctor`/`__main__`; evidence table in proposed `45-VERIFICATION.md` |
| HYG-02 | `test_detect_skips_dotfiles` passes **or** contract revised with tests/docs | Implemented per `45-03` + D-45.07; test body verified in `tests/test_detect.py` |
| HYG-03 | `test_collect_files_from_dir` passes **or** semantics reconciled + documented | `collect_files` uses shared pruning (`corpus_prune`); targeted tests pass |
</phase_requirements>

## 1. Executive summary — what Phase 50 must prove vs ship

**Ship:** Nothing new in `graphify/` is required for Phase 50 if Phase **45** execution already landed the code (summaries and code inspection indicate **45-01..03** delivered `corpus_prune`, manifest stderr, dot_graphify schema/detect/doctor, and test updates).

**Prove:** Phase 50 is a **documentation and traceability** phase: it must (a) author **`45-VERIFICATION.md`** so the milestone audit’s “verification_status: missing” rows for **HYG-01–03** are closed [CITED: `.planning/v1.10-MILESTONE-AUDIT.md`], (b) flip **HYG-01**, **HYG-02**, **HYG-03** to `[x]` in `.planning/REQUIREMENTS.md` only when each row is backed by cited automated commands and file pointers [VERIFIED: `.planning/REQUIREMENTS.md` traceability table lines 40–42], and (c) optionally align **`45-VALIDATION.md`** frontmatter (`nyquist_compliant`, task status table) so Nyquist “partial” on phase 45 is resolved after sign-off [VERIFIED: `.planning/phases/45-baselines-detect-self-ingestion/45-VALIDATION.md` frontmatter `nyquist_compliant: false`].

**Primary recommendation:** Treat Phase 50 as a **single-wave verification write-up**: create `45-VERIFICATION.md` under the **Phase 45** directory (same convention as `49-VERIFICATION.md` under phase 49’s folder [VERIFIED: `.planning/phases/49-add-version-flag-to-graphify-command-and-also-print-current-/49-VERIFICATION.md`]), paste **executed** pytest outputs (or CI links), then update REQUIREMENTS checkboxes and audit cross-references.

## 2. Source audit — HYG-01/02/03 → Phase 45 plans → code/tests

| REQ | Phase 45 plan | Plan objective (frontmatter) | Concrete code / tests |
|-----|---------------|------------------------------|-------------------------|
| **HYG-01** | **45-01** | D-45.01–03, D-45.08: `corpus_prune`, stderr manifest summary, default-root manifest when `resolved is None`, `collect_files(..., resolved=)` parity | [VERIFIED: repo] `graphify/corpus_prune.py` (`build_prior_files`, manifest load); `graphify/extract.py` imports `build_prior_files`, `dir_prune_reason` and `collect_files(..., resolved=)`; `graphify/detect.py` refactored to use shared helpers (per `45-01-SUMMARY.md`) |
| **HYG-01** (continued) | **45-02** | D-45.04–06: `corpus.dot_graphify`, YAML/profile hard-exclude, doctor / apply track | [VERIFIED: plan frontmatter] `45-02-PLAN.md` lists `profile.py`, `detect.py`, `doctor.py`, `__main__.py`; `tests/test_detect.py` contains `_PHASE45_PROFILE_STUB` and `corpus.dot_graphify` YAML for detect tests |
| **HYG-02** | **45-03** | D-45.07, D-45.09: dual path contracts; mini-vault fixture | [VERIFIED: repo] `tests/test_detect.py::test_detect_skips_dotfiles` — `Path.parts` rule + `_DOTFILE_ALLOWED_PARTS` + posix `"/./"` invariant; `tests/fixtures/phase45-mini-vault/` per `45-03-SUMMARY.md` |
| **HYG-03** | **45-01** + **45-03** | Shared walker / `collect_files` parity; extract tests | [VERIFIED: repo] `tests/test_extract.py::test_collect_files_skips_nested_graphify_out` (D-45.08); `test_collect_files_from_dir` still validates suffix allow-list + non-empty set |

**Inherited decisions (for verification wording, not replanning):** copy from `45-CONTEXT.md` — D-45.01 one-line stderr, D-45.02 default `graphify-out` manifest when `resolved is None`, D-45.03 always skip manifest paths, D-45.07 pathlib + posix string contract, D-45.08 shared primitive [CITED: `.planning/phases/45-baselines-detect-self-ingestion/45-CONTEXT.md`].

## 3. Gap analysis — why `45-VERIFICATION.md` is missing; open REQUIREMENTS ticks

**Why `45-VERIFICATION.md` is missing:** Phase **44** established the pattern that gap closure phases **author** `*-VERIFICATION.md` for the phase that delivered the behavior (e.g. 44 → 39/40/41 verification files) [CITED: `.planning/ROADMAP.md` Phase 44 description]. Phase **45** execution completed plans and summaries but no agent wrote the milestone-facing verification file; the v1.10 audit explicitly records “summaries exist”, “no 45-VERIFICATION.md” [VERIFIED: `.planning/v1.10-MILESTONE-AUDIT.md` YAML `gaps.requirements` for HYG-01..03].

**Why REQUIREMENTS checkboxes stay open:** `.planning/REQUIREMENTS.md` ties **HYG-01..03** sign-off to **Phase 50** with artifact **`45-VERIFICATION.md`** [VERIFIED: REQUIREMENTS.md lines 8–10, 40–42]. Until that file exists and checkboxes are updated, the audit correctly scores those rows as unsatisfied even if code and tests are green.

**CI/tests alignment:** [VERIFIED: local run 2026-04-30] `pytest tests/test_detect.py::test_detect_skips_dotfiles tests/test_extract.py::test_collect_files_from_dir tests/test_extract.py::test_collect_files_skips_nested_graphify_out -q` → **3 passed**. Full suite was cited as green post–Phase 49 work (`1965 passed` in `49-VERIFICATION.md`); Phase 50 gate should re-run `pytest tests/ -q` and paste fresh counts when signing off.

**Note:** `45-VALIDATION.md` task table still shows ⬜ pending rows and `nyquist_compliant: false` — likely stale relative to executed plans. Phase 50 should either update that file on sign-off or document why it remains draft [VERIFIED: `45-VALIDATION.md` lines 39–45, 5–6].

## 4. Recommended outline for `45-VERIFICATION.md` (Nyquist-style)

**Path:** `.planning/phases/45-baselines-detect-self-ingestion/45-VERIFICATION.md` (matches REQUIREMENTS wording “**`45-VERIFICATION.md`**” and phase-49 convention [VERIFIED: REQUIREMENTS traceability; `49-VERIFICATION.md` location]).

Suggested sections (mirror `49-VERIFICATION.md` structure [CITED: `.planning/phases/49-add-version-flag-to-graphify-command-and-also-print-current-/49-VERIFICATION.md`]):

```markdown
---
status: passed | partial
phase: 45
phase_name: Baselines & Detect Self-Ingestion
verified: <ISO date>
---

# Phase 45 — Verification

## Must-haves (from ROADMAP + REQUIREMENTS + plans)

| REQ / decision | Evidence |
|----------------|----------|
| HYG-01 / D-45.01 | grep or pointer: stderr one-line when skipped["manifest"] non-empty — `detect.py` call site |
| HYG-01 / D-45.02 | `corpus_prune.build_prior_files`: resolved artifacts_dir + root/graphify-out branch |
| HYG-01 / D-45.03 | Doc line + test name manifest skip persistence |
| HYG-01 / D-45.04–06 | `profile.py` schema; detect never ingests profile.yaml; doctor flags (names from code) |
| HYG-01 / D-45.08 | `extract.collect_files` + `test_collect_files_skips_nested_graphify_out` |
| HYG-02 / D-45.07 | `tests/test_detect.py::test_detect_skips_dotfiles` |
| HYG-03 | `tests/test_extract.py::test_collect_files_from_dir` (+ nested graphify-out test) |

## Automated

- Quick slice: `pytest tests/test_detect.py tests/test_extract.py -q` — <paste pass summary>
- Focused: `pytest tests/test_profile.py tests/test_profile_composition.py -q` (if dot_graphify schema tests live there)
- Full gate: `pytest tests/ -q` — <paste pass summary; note xfail/skip counts>

## Gaps

- Manual-only items from `45-VALIDATION.md` (e.g. operator manifest clear) — state PASS / N/A

## human_verification

- Optional: one CLI `graphify doctor --dot-graphify-track` on `tests/fixtures/phase45-mini-vault/` if required by stakeholders
```

## 5. Risks / ambiguities

| Topic | Risk | Resolution |
|-------|------|------------|
| **Artifact location** | Duplicating verification under phase **50** vs canonical **45** | **Put `45-VERIFICATION.md` in phase 45 directory**; Phase 50 folder holds `50-RESEARCH.md` / `50-PLAN.md` / `50-SUMMARY.md` only — matches REQUIREMENTS and prior gap phases [VERIFIED: REQUIREMENTS.md; ROADMAP Phase 50 “Artifacts: …50…” is the gap-closure *planning* home, not necessarily the verification file]. |
| **Stale Nyquist metadata** | `45-VALIDATION.md` says pending / `nyquist_compliant: false` after work landed | On Phase 50 completion, either update validation frontmatter + task checkboxes or record in `45-VERIFICATION.md` why validation doc is intentionally frozen. |
| **`test_collect_files_skips_hidden`** | Still asserts “no part.startswith('.')” for `collect_files(FIXTURES)` without allow-list — may diverge from detect if FIXTURES ever gains `.graphify` | [VERIFIED: `tests/test_extract.py` lines 86–89] If FIXTURES stays without dotdirs, no failure; if parity is required, align test with `_DOTFILE_ALLOWED_PARTS` in a follow-up (out of scope unless Phase 50 discovers a failure). |
| **Evidence freshness** | Audit wants proof, not stale counts | Re-run full `pytest tests/ -q` at sign-off; do not copy `49-VERIFICATION` counts as proof for HYG. |

## 6. Validation Architecture

> Nyquist validation is **enabled** in `.planning/config.json` (`workflow.nyquist_validation: true`) [VERIFIED: `.planning/config.json`]. This section supports instantiating **`50-VALIDATION.md`** (or extending `45-VALIDATION.md`).

### Test framework

| Property | Value |
|----------|-------|
| Framework | pytest (stdlib assertions) |
| Config file | none dedicated |
| Quick run command | `pytest tests/test_detect.py tests/test_extract.py -q` |
| Full suite command | `pytest tests/ -q` |
| CI matrix | Python 3.10 and 3.12 per `CLAUDE.md` [CITED: `CLAUDE.md`] |

### Phase requirements → test map

| REQ ID | Behavior | Test type | Automated command | Notes |
|--------|----------|-----------|-------------------|-------|
| HYG-01 | Manifest prior files + stderr summary | unit / integration | `pytest tests/test_detect.py -k manifest -q` *or* narrowest tests touching `skipped["manifest"]` if named; else `tests/test_detect.py` subset | Use `pytest --collect-only -q` to list exact test names after `grep manifest` in `tests/test_detect.py` |
| HYG-01 | `collect_files` vs `detect` pruning | unit | `pytest tests/test_extract.py::test_collect_files_skips_nested_graphify_out -q` | |
| HYG-01 | `corpus.dot_graphify` / profile | unit | `pytest tests/test_detect.py tests/test_profile.py tests/test_profile_composition.py -q` | Trim if slow; keep profile schema tests |
| HYG-02 | Dot-path contract | unit | `pytest tests/test_detect.py::test_detect_skips_dotfiles -q` | |
| HYG-03 | collect_files from fixtures | unit | `pytest tests/test_extract.py::test_collect_files_from_dir -q` | |

### Sampling rate (Phase 50 execution)

- **Per doc edit / checkbox change:** quick slice (`test_detect.py` + `test_extract.py`).
- **Before merging Phase 50 / ticking REQUIREMENTS:** full `pytest tests/ -q` on local; match CI matrix if available.
- **Phase gate:** same full suite; attach stdout snippet to `45-VERIFICATION.md`.

### Wave 0 gaps

None for infrastructure — `tests/test_detect.py`, `tests/test_extract.py`, and `tests/fixtures/phase45-mini-vault/` exist [VERIFIED: glob + reads]. Optional: add explicit test name for manifest stderr if planners want a one-liner grep target (currently may be covered inside broader detect tests).

### Security / ASVS (lightweight)

Phase 50 is non-runtime; implementation already went through plan threat tables (manifest path traversal, YAML writeback) [CITED: `45-01-PLAN.md`, `45-02-PLAN.md` threat_model sections]. Verification doc should **reference** those mitigations; no new ASVS category work.

## Sources

### Primary (HIGH)

- [VERIFIED: workspace] `.planning/ROADMAP.md` — Phases 45, 50, v1.10 gap narrative
- [VERIFIED: workspace] `.planning/REQUIREMENTS.md` — HYG-01..03, traceability table
- [VERIFIED: workspace] `.planning/STATE.md` — milestone position notes
- [VERIFIED: workspace] `.planning/v1.10-MILESTONE-AUDIT.md` — gap evidence
- [VERIFIED: workspace] `.planning/phases/45-baselines-detect-self-ingestion/45-CONTEXT.md`, `45-01..03-PLAN.md`, `45-*-SUMMARY.md`, `45-VALIDATION.md`
- [VERIFIED: workspace] `graphify/corpus_prune.py`, `tests/test_detect.py`, `tests/test_extract.py`
- [VERIFIED: shell] `pytest …::test_detect_skips_dotfiles …::test_collect_files_from_dir …::test_collect_files_skips_nested_graphify_out -q` → 3 passed

### Secondary (MEDIUM)

- [CITED: `CLAUDE.md`] CI Python versions, standard pytest invocations

### Assumptions log

| # | Claim | Risk if wrong |
|---|--------|----------------|
| A1 | Phase 45 code on `main` matches executed plan summaries | Verification would document the wrong SHA; mitigate by citing `git log -1 --oneline` in `45-VERIFICATION.md` |

---

## Metadata

**Research date:** 2026-04-30  
**Valid until:** ~30 days or until Phase 50 PLAN executes (whichever first)

## RESEARCH COMPLETE
