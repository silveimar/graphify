---
phase: 72
slug: reas
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-07
---

# Phase 72 — Security (reasoning relations)

> Per-phase security contract: threat register, accepted risks, and audit trail.
> All 13 plan-time threats verified CLOSED via gsd-security-auditor on 2026-05-07.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| extractor (LLM) → validate.py | Untrusted reasoning edges with arbitrary `relation`, `confidence`, `confidence_score`, endpoint ids | extraction dicts |
| skill prompt → LLM extractor | Prompt body shapes LLM emission; drift between platforms causes silent extraction divergence | prompt strings |
| extraction dict → build.py | Untrusted target strings; possible adversarial id collisions in substring fallback | extraction edges |
| analyze/report/wiki/export → rendered output | LLM-derived neighbor labels and target strings reach markdown / YAML / HTML output | rendered artifacts |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-72-01 | Tampering | validate.py per-edge loop | mitigate | Read-only endpoint type lookup; rejects `file_type=='code'`; appends to errors (no raise). graphify/validate.py:237-244 | closed |
| T-72-02 | Tampering | validate.py confidence_score parse | mitigate | `float()` in try/except; non-numeric drops to error path. graphify/validate.py:248-251 | closed |
| T-72-03 | Information disclosure | docs/RELATIONS.md orientation | mitigate | Direction explicitly documented "newer → older"; downstream tested by Plan 03 outbound-stamp tests | closed |
| T-72-04 | Tampering / Repudiation | skill*.md drift | mitigate | BEGIN/END markers in all 10 skill files; tests/test_skill_prompt_drift.py:64 `test_reasoning_relations_block_parity` | closed |
| T-72-05 | Information disclosure (stale cache) | confidence cache | mitigate | PROMPT_VERSION bumped 1.13.0 → 1.14.0 invalidates `sha256(PROMPT_VERSION‖model_id‖file_hash)` key. graphify/prompts.py:10 | closed |
| T-72-06 | Tampering | _resolve_reasoning_targets substring fallback | mitigate | Lex-sorted deterministic selection; literal `in` test only — no regex/eval. graphify/build.py:67 | closed |
| T-72-07 | Information disclosure (orientation flip) | _stamp_supersession_outbound | mitigate | Direction explicitly tested (target = superseded). graphify/build.py:94-107; tests/test_build.py:538 | closed |
| T-72-08 | DoS (cycle in supersedes chain) | outbound stamp | accept | Single-pass O(E); no recursion; cycles tolerated as no-ops. graphify/build.py:101-107 | closed |
| T-72-09 | Tampering (double-stamp w/ Phase 71) | outbound stamp | mitigate | `if e.get("valid_until") is None` idempotency guard. graphify/build.py:106; tests/test_build.py:575 | closed |
| T-72-10 | DoS | analyze.py contradictions_and_chains | mitigate | Per-path cycle guard `if s in path: continue` + single stderr "supersession cycle detected" warning. graphify/analyze.py:822-850; tests/test_analyze.py:920 | closed |
| T-72-11 | Tampering | wiki.py reasoning subsection | mitigate | `html.escape(neighbor_label)[:64]`. graphify/wiki.py:102 | closed |
| T-72-12 | Tampering (YAML object injection) | export.py / templates.py frontmatter | mitigate | JSON-encoded scalar strings inside flat YAML list (plan deviation, equivalent safety); values pre-coerced to `str`/`float`. graphify/templates.py:1411-1424; graphify/export.py:820 | closed |
| T-72-13 | Information disclosure | report.py source_file path leakage | accept | Project-relative paths intentional; existing Temporal Health pattern | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-72-01 | T-72-08 | Single-pass O(E) outbound stamp has no recursion; cycles tolerated as no-ops. No DoS surface. | gsd-security-auditor | 2026-05-07 |
| AR-72-02 | T-72-13 | source_file paths are project-relative and intentional, matching the existing Temporal Health section pattern. | gsd-security-auditor | 2026-05-07 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-07 | 13 | 13 | 0 | gsd-security-auditor |

### Notes

- T-72-12 deviation from plan (JSON-encoded scalars in flat YAML list vs. `yaml.safe_dump`) verified safe: only `str`/`float` reach the YAML emitter; each list item is a single-line JSON scalar that cannot inject YAML structure.
- All implementation files left unmodified during audit (read-only verification).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
