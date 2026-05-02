---
phase: 53
slug: concept-code-schema-build-merge
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
reconstructed_from: [53-01-PLAN.md, 53-02-PLAN.md, 53-03-PLAN.md, 53-04-PLAN.md, 53-VERIFICATION.md, 53-RESEARCH.md]
---

# Phase 53 — Validation Strategy

> Per-phase validation contract. Reconstructed retroactively from completed phase artifacts (Plans 01–04 + VERIFICATION). All requirements have automated coverage; phase is Nyquist-compliant.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in `pyproject.toml`; `[all]` extras include test deps) |
| **Config file** | `pyproject.toml` (no separate `pytest.ini`) |
| **Quick run command** | `pytest tests/test_concept_code_edges.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~0.2s quick / ~30s full (1979 passed at phase close) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_concept_code_edges.py -q`
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~0.2s (single-file) / ~30s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | CGRAPH-01, CGRAPH-02 | — | Round-trip fixture + 14 RED tests in place | unit | `pytest tests/test_concept_code_edges.py -q` | ✅ | ✅ green |
| 53-02-01 | 02 | 2 | CGRAPH-01 | — | `validate_extraction` accepts 4 new relations with confidence/evidence rules | unit | `pytest tests/test_concept_code_edges.py -k "new_relation or evidence or inferred_score or ambiguous or implements_unchanged" -q` | ✅ | ✅ green |
| 53-03-01 | 03 | 2 | CGRAPH-02 | — | `_merge_edge_fields` deterministic dedupe + canonical sort + W2 NetworkX iteration fix | unit | `pytest tests/test_concept_code_edges.py -k "merge or canonical_sort or direction_normalize or round_trip" -q` | ✅ | ✅ green |
| 53-04-01 | 04 | 3 | CGRAPH-01, CGRAPH-02 | — | `docs/RELATIONS.md` documents 4 new relations + 5 evidence values + merge invariants | doc-spot-check | `grep -E "Phase 53 additions\|annotation\|jsdoc\|docstring\|test_docstring\|inheritance\|max\\(\\)\|base-wins\|canonical sort" docs/RELATIONS.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Test → Requirement Index

**CGRAPH-01 — `validate_extraction` accepts new typed concept↔code relations**

| Test | Behavior |
|------|----------|
| `test_new_relations_validate_clean_with_inferred_score` | 4 new relations accepted with `INFERRED + confidence_score` |
| `test_extracted_new_relation_without_evidence_rejected` | EXTRACTED + new relation requires `evidence` |
| `test_extracted_new_relation_unknown_evidence_rejected` | `evidence` must be in `KNOWN_EVIDENCE_VALUES` |
| `test_extracted_new_relation_with_valid_evidence_accepted` | Valid evidence accepted |
| `test_inferred_new_relation_missing_score_rejected` | INFERRED + new relation requires `confidence_score ∈ [0,1]` |
| `test_ambiguous_new_relation_no_evidence_accepted` | AMBIGUOUS branch falls through (D-53.09) |
| `test_implements_unchanged_extracted_no_evidence_accepted` | `implements` retains Phase 46 semantics (D-53.10) |
| `test_unknown_edge_relation_warns_stderr` | Unknown relations warn on stderr |

**CGRAPH-02 — `build`/merge preserves concept↔code edges deterministically**

| Test | Behavior |
|------|----------|
| `test_mergeable_duplicates_canonical_source_files` | Sorted, deduplicated `source_file` joined `"; "` |
| `test_mergeable_duplicates_max_confidence_score` | `max()` of `confidence_score` |
| `test_canonical_sort_across_all_relations` | Final `(source, target, relation)` ascending sort |
| `test_direction_normalize_realizes_reverse` | Reverse-direction edge oriented code→concept |
| `test_direction_normalize_all_concept_code_relations` | All 5 relations oriented code→concept |
| `test_documents_relation_no_orient_when_neither_endpoint_code` | Concept↔concept `documents` left untouched |
| `test_round_trip_list_equality_across_reruns` | NetworkX iteration matches sorted edge list (W2 fix) |

**Phase 46 backward-compat (sentinel tests included in same file):**

`test_implemented_by_normalizes_to_implements_orient_code_to_concept`,
`test_duplicate_implements_merges_source_files`,
`test_graph_json_round_trip_implements`.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Plan 01 (Wave 1) seeded the fixture + RED test scaffold; no separate Wave 0 install was needed because pytest + tree-sitter + NetworkX were already configured for v1.10 phases.

- ✅ `tests/fixtures/concept_code/round_trip.json` — deterministic test corpus (Plan 01)
- ✅ `tests/test_concept_code_edges.py` — 14 new tests + 4 Phase 46 backward-compat (Plan 01)

---

## Manual-Only Verifications

All phase behaviors have automated verification. This phase is schema- and merge-logic-only — every truth is observable via deterministic code inspection plus pytest, which is fully GREEN at phase close (1979 passed, 1 xfailed, matches plan baseline).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — fixture seeded in Wave 1)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full) / < 1s (quick)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-02 (retroactive — phase shipped 2026-04-30 via `/gsd-next --chain`, `83aabf2` close-out).

## Validation Audit 2026-05-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Truths verified (from 53-VERIFICATION.md) | 21/21 |
| Tests in `tests/test_concept_code_edges.py` | 18 (4 Phase 46 + 14 Phase 53) |
| Full suite at phase close | 1979 passed, 1 xfailed |
