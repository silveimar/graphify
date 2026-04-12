---
phase: 02
slug: template-engine
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Built from `02-RESEARCH.md` STRIDE patterns, `02-REVIEW.md` + `02-REVIEW-FIX.md` findings,
> and the `02-UAT.md` Test 5 follow-up, then verified against HEAD on 2026-04-11.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Python process ↔ filesystem (vault dir) | `load_templates()` reads user override templates from `<vault>/.graphify/templates/<type>.md` | User-supplied template bytes (UTF-8 markdown) |
| Python process ↔ filesystem (package data) | `_load_builtin_template()` reads wheel-shipped built-in templates via `importlib.resources` | Package-owned bytes — no user control |
| Extractor (untrusted labels) ↔ Template engine | Node labels, relations, community tags flow from LLM/AST extractors into frontmatter, wikilinks, callouts, tags, dataview blocks | Arbitrary UTF-8 strings including control chars |
| Profile loader ↔ Template engine | `validate_profile()` passes `folder_mapping` values into downstream path resolution | Vault-relative path strings |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | `load_templates()` | mitigate | `validate_vault_path()` resolves candidate against `vault_dir` and rejects paths that escape confinement (`graphify/profile.py:209-222`); called from `graphify/templates.py:211` before any `read_text()` | closed |
| T-02-02 | Tampering | `_dump_frontmatter()` | mitigate | `safe_frontmatter_value()` quotes YAML-special chars, leading indicators, reserved words (yes/null/true/false/on/off), numeric-looking strings, commas; strips C0/DEL/NEL/LS/PS control chars (`graphify/profile.py:230-266`). Applied to every string scalar in `_dump_frontmatter` (`graphify/profile.py:325, 336`) | closed |
| T-02-03 | Tampering | Template rendering | mitigate | `string.Template.safe_substitute` only — no `eval`/`exec`, no Jinja2/Mako/Cheetah imports. `string.Template` has no expression or code-execution surface by design. Verified: `grep -nE "eval\(\|exec\(" graphify/templates.py` returns 0 matches | closed |
| T-02-04 | DoS | `safe_filename()` | mitigate | `max_len=200` cap with SHA256 suffix for collision resistance (`graphify/profile.py:283-300`). Prevents unbounded filename growth from pathological labels | closed |
| T-02-05 | Elevation of Privilege | `validate_vault_path()` | mitigate | `Path.resolve()` applied to BOTH `vault_base` and the candidate path before the `is_relative_to` check (`graphify/profile.py:214-215`). Symlinks are resolved before confinement is verified, preventing symlink escape from the vault directory | closed |
| T-02-06 | Tampering | `_emit_wikilink()` — alias side | mitigate | `_sanitize_wikilink_alias()` replaces `]]` → `] ]`, `|` → `-`, `\n`/`\r` → space (`graphify/templates.py:240-263`) plus `_WIKILINK_ALIAS_CONTROL_RE` second pass strips tab + C0/DEL/NEL/LS/PS controls to single space. Prevents premature wikilink close, alias corruption, callout line break, invisible control embedding (CR-01 + UAT-05) | closed |
| T-02-07 | Tampering | `_emit_wikilink()` — filename target side | mitigate | `safe_filename()` regex now strips OS-illegal chars AND `\x00-\x1f`, `\x7f`, `\u0085`, `\u2028`, `\u2029` (`graphify/profile.py:290-296`). A label like `line1\nline2` resolves to filename `line1line2`, not a literal-newline target that breaks Obsidian's wikilink parser (UAT-05 follow-up) | closed |
| T-02-08 | Tampering | `_build_connections_callout()` | mitigate | `relation` and `confidence` are coerced to `str` and stripped of `\n`, `\r`, and `]` before interpolation into the `> - {link} — {relation} [{confidence}]` bullet (`graphify/templates.py:377-378`). Prevents callout line break and early bracket close (WR-02) | closed |
| T-02-09 | Tampering | `render_note()` tag list | mitigate | Both `community_tag` and `file_type` are wrapped in `safe_tag()` before being interpolated into the `graphify/{tag}` and `community/{tag}` entries (`graphify/templates.py:598-599`). Prevents extractor-supplied values with spaces, uppercase, or special chars from producing malformed Obsidian tags (WR-04) | closed |
| T-02-10 | Tampering | `_build_dataview_block()` | mitigate | `community_tag` and `folder` are stripped of backticks, `\n`, `\r` before `safe_substitute()`. Post-substitution, any remaining ` ``` ` sequence is stripped from the resolved query to prevent premature dataview fence closure (`graphify/templates.py:516-528`). Two-phase substitution pattern isolates user query tokens from outer template (WR-05) | closed |
| T-02-11 | EoP | `validate_profile()` folder_mapping | mitigate | After the `".." in path_val` literal check, `validate_profile` also rejects `Path(path_val).is_absolute()` paths and `path_val.startswith("~")` home-expansion paths (`graphify/profile.py:182-198`). Catches escape attempts at profile load time rather than deferring to `validate_vault_path` at use time (WR-07) | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks — all identified threats mitigated in code.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 11 | 11 | 0 | Claude (/gsd-secure-phase) |

**Audit scope:**
- STRIDE patterns from `02-RESEARCH.md` Known Threat Patterns table (5 threats: T-02-01..05)
- Critical + Warning findings from `02-REVIEW.md` (all 8 closed by iteration-1 code review fix: commits 426328c, 13ec26b, 4ab72d8, f68bd4a, 5f09561, 56c9bc9, da06a84, b4ade72 — covering T-02-02, T-02-06 (alias side), T-02-08, T-02-09, T-02-10, T-02-11 plus two already in STRIDE set)
- UAT Test 5 follow-up gap fixed inline in commit 7b5c228 — covering T-02-07 (filename-target side) and extending T-02-06 (alias control-char coverage)

**Verification method:**
All mitigations verified via targeted `grep`/`sed` against HEAD source files. See commit history for fix provenance:

| Threat | Fix commit(s) |
|--------|---------------|
| T-02-01..05 | Original plans 02-01..04 (pre-review baseline) |
| T-02-02 (YAML hardening) | `13ec26b` (WR-01) |
| T-02-06 (alias) | `426328c` (CR-01) + `7b5c228` (UAT-05 tab/C0 coverage) |
| T-02-07 (filename) | `7b5c228` (UAT-05) |
| T-02-08 | `4ab72d8` (WR-02) |
| T-02-09 | `5f09561` (WR-04) |
| T-02-10 | `56c9bc9` (WR-05) |
| T-02-11 | `b4ade72` (WR-07) |

**Test coverage:** 658 passing tests in `pytest tests/ -q`, including 41 new regression tests from the code-review fix pass and 11 additional from the UAT follow-up — every threat has at least one dedicated regression test.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (none)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
