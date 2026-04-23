---
phase: 10
slug: cross-file-semantic-extraction
status: verified
threats_open: 0
threats_total: 12
threats_closed: 12
asvs_level: 1
created: 2026-04-16
verified: 2026-04-16
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Cross-file semantic extraction with entity deduplication — new surfaces: LLM-generated
> labels crossing into markdown/HTML reports, YAML-sourced dedup config, MCP alias-map
> disclosure, Obsidian frontmatter alias emission.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| LLM extraction output → dedup.py / report.py / export.py | Upstream `extract()` output contains LLM-generated labels (untrusted). These are rendered into `dedup_report.md`, `GRAPH_REPORT.md`, and Obsidian notes. | Arbitrary strings (label, description) |
| dedup.py → graphify-out/ filesystem | `write_dedup_reports` writes JSON + MD. Path traversal via misconfigured `out_dir` could escape project root. | Output file paths |
| `.graphify/dedup.yaml` → `yaml.safe_load` | Corpus-root config file (under version control / shared). YAML tag-injection is the EoP vector if default loader were used. | Config values (thresholds, strategy names) |
| `dedup_report.json` → serve.py (MCP) | Sidecar file consumed by `_load_dedup_report`. Malformed contents could crash the MCP loop (availability). | alias_map dict |
| `merged_from` IDs → Obsidian `aliases:` frontmatter | Alias IDs embedded into YAML parsed by Obsidian. Malformed chars could break wikilinks or inject YAML. | Slugified node IDs (no PII) |
| installer → pyproject `[dedup]` extra | User-controlled install command chooses optional deps; no untrusted input. | Install graph |
| ast_results → batch.py | Batch token-budget estimates from already-validated upstream dicts. `batch.py` only reads `Path.stat().st_size`, never opens files. | Integer byte counts |

---

## Threat Register

Threat IDs are qualified with the source plan (`T-10-{plan}/{orig_id}`) because several plans independently assigned overlapping IDs.

| Qualified ID | Category | Component | Disposition | Mitigation | Status |
|---|---|---|---|---|---|
| T-10-01/T-10-02 | Tampering | `validate.py` schema for dedup provenance (`source_file`, `merged_from`) | mitigate | isinstance list-of-str checks reject malformed fields before graph construction. `graphify/validate.py:38-56`. Test: `tests/test_validate.py`. | closed |
| T-10-01/T-10-03 | Denial-of-Service | `pyproject [dedup]` extra pulls `sentence-transformers` (~1GB w/ torch) | accept | Opt-in optional extra (`pyproject.toml:51`), precedent `[leiden]`/`graspologic`. Core install unaffected. | closed |
| T-10-02/T-10-02 | Tampering | `batch.py` token estimate from untrusted file content | accept | Only `Path.stat().st_size` used (`graphify/batch.py:209`); grep confirms no `open()`/`read_bytes`/`read_text`. File bytes never read. | closed |
| T-10-03/T-10-01 | Tampering | `dedup.py write_dedup_reports` `out_dir` path traversal | mitigate | `out_dir.resolve().relative_to(Path.cwd().resolve())` raises on escape. `graphify/dedup.py:168-177`. Test: `tests/test_dedup.py:318 test_report_path_confined`. | closed |
| T-10-03/T-10-02 | Tampering | `dedup_report.md` rendering of LLM-generated labels | mitigate | `sanitize_label_md(sanitize_label(...))` applied in `_render_dedup_md` (`graphify/dedup.py:35, 579-581`); helper impl `graphify/security.py:188-207` (HTML-escape `<>`, backtick→apostrophe, control-char strip). Test: `tests/test_dedup.py:335 test_canonical_label_sanitized`. | closed |
| T-10-03/T-10-03 | Denial-of-Service | Large embedding tensor on hostile corpus | accept | Blocking strategy + length-ratio guard (`graphify/dedup.py:100, 268, 286-290`) bounds candidate pairs pre-embedding; CLI `--batch-token-budget` caps upstream; labels <100 chars bound memory. | closed |
| T-10-04/T-10-04 | Elevation of Privilege | `.graphify/dedup.yaml` parsing with PyYAML | mitigate | `_load_dedup_yaml_config` uses `yaml.safe_load` only (`graphify/__main__.py:884-904`). Two CI-enforced regex scans: `tests/test_main_cli.py:300 test_dedup_yaml_safe_load_only` and `:314 test_no_unsafe_yaml_load_in_any_module` (scans both `__main__.py` and `dedup.py` for `\byaml\.load\(`). | closed |
| T-10-05/T-10-02 | Tampering | `report.py` rendering of dedup labels in `GRAPH_REPORT.md` | mitigate | Defense-in-depth: `sanitize_label` (security.py) wrapped by local `_sanitize_md` (ticks/angle-brackets). `graphify/report.py:7, 248-276, 281`. Test: `tests/test_report.py:537 test_generate_dedup_section_sanitizes_labels`. | closed |
| T-10-06/T-10-06 | Information Disclosure | `resolved_from_alias` exposing internal node IDs to MCP caller | accept | Intentional per decision D-16 — agent must see alias→canonical redirect to interpret results. Node IDs are slug(code-entity-name), no PII. `graphify/serve.py:929`. Test: `tests/test_serve.py:1361 test_run_query_graph_resolves_alias`. | closed |
| T-10-06/extra | Availability (defense-in-depth) | `_load_dedup_report` robustness to malformed `dedup_report.json` | mitigate | `graphify/serve.py:91-112` catches `json.JSONDecodeError` (line 102) and `OSError` (line 105) separately (post IN-03 split), returns `{}`. Type-checks reject non-dict wrapper and non-str keys/values. Docstring: "Never raises — broken dedup report must not crash MCP serve." | closed |
| T-10-07/T-10-05 | Tampering | `merged_from` IDs embedded as Obsidian YAML `aliases:` | mitigate | `_sanitize_wikilink_alias` strips `]`, `|`, newlines, tabs, C0 controls. Control lives in `graphify/templates.py:283-289`, invoked at `:300` (wikilink display alias) and `:652-654` (aliases frontmatter loop). Test: `tests/test_templates.py:2306 test_render_note_aliases_sanitized_for_wikilinks`. See note in Audit Trail re: control location. | closed |
| T-10-07/extra | Availability (defense-in-depth) | `_hydrate_merged_from` robustness to missing/corrupt `dedup_report.json` | mitigate | `graphify/export.py:453-487` — "Silently returns when the report is missing. Never raises." Catches `(json.JSONDecodeError, OSError)`. Missing-file path warns and returns. | closed |

*Status: `open` · `closed`*
*Disposition: `mitigate` (implementation required) · `accept` (documented risk) · `transfer` (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-01/T-10-03 | `[dedup]` extra is opt-in; users installing core graphify pay no install-size cost. Matches `[leiden]`/`graspologic` precedent. Install size is disclosed in README / pyproject extras. | Phase 10 plan (10-01) | 2026-04-16 |
| AR-10-02 | T-10-02/T-10-02 | `batch.py` is pure computation on already-trusted stat metadata; no file-content read path exists. Re-verified by auditor (no `open()`/`read_bytes`/`read_text` in module). | Phase 10 plan (10-02) | 2026-04-16 |
| AR-10-03 | T-10-03/T-10-03 | Memory bound by blocking + length-ratio candidate filter and CLI `--batch-token-budget`. Labels are <100 chars. Hostile-corpus DoS is bounded to known-small vectors. | Phase 10 plan (10-03) | 2026-04-16 |
| AR-10-04 | T-10-06/T-10-06 | `resolved_from_alias` is an intentional agent-affordance per decision **D-16**: the caller must see the redirect to interpret query results correctly. Node IDs are slugs of code entity names (no PII, no secrets). | Decision D-16 / Phase 10 plan (10-06) | 2026-04-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-16 | 12 | 12 | 0 | gsd-security-auditor (auto, sonnet) |

### Audit 2026-04-16 — notes

- **Register-vs-code location drift (documentation only):** T-10-07/T-10-05 mitigation was planned in `export.py` but the `_sanitize_wikilink_alias` helper and its applications live in `graphify/templates.py` (the Obsidian note renderer module). Control is present, applied at both wikilink display and YAML frontmatter sites, and covered by `tests/test_templates.py:2306`. No security impact; noted here so future auditors search the right module.
- **IN-03 fix confirmed effective:** `_load_dedup_report` now distinguishes `json.JSONDecodeError` from `OSError` with distinct warnings (commit `38792d9`), strengthening the T-10-06/extra availability mitigation.
- **Yaml-load CI guard is belt-and-suspenders:** two independent regex scans in `tests/test_main_cli.py` (lines 300 and 314) cover both `__main__.py` and `dedup.py`. Any future `yaml.load(` introduction breaks CI.
- **Summary threat-flag scan:** all 7 SUMMARY.md files report `None` for new threat flags and `Self-Check: PASSED`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (AR-10-01 through AR-10-04)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-16
