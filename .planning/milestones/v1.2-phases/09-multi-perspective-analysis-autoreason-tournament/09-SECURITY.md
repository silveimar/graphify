---
phase: "09"
phase_name: "multi-perspective-analysis-autoreason-tournament"
asvs_level: 1
audit_date: "2026-04-14"
threats_total: 7
threats_closed: 7
threats_open: 0
result: SECURED
---

# Security Audit — Phase 09: Multi-Perspective Analysis / Autoreason Tournament

**ASVS Level:** 1
**Threats Closed:** 7/7
**Threats Open:** 0/7

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-09-01 | Tampering | mitigate | CLOSED | `graphify/report.py:178–182` — `_sanitize_md()` strips backticks (replaced with `'`) and escapes `<`/`>` as HTML entities. Applied to `findings_text`, `voting_rationale`, `top_finding`, `incumbent_summary`, `adversary_summary`, `synthesis_summary` at lines 221–226. |
| T-09-02 | Info Disclosure | accept | CLOSED | Accepted: `render_analysis_context()` serializes graph structure for LLM prompts intentionally. No secrets or credentials flow into graph data — graph is built from source code AST and LLM semantic extraction only. Declared in 09-01-SUMMARY.md Threat Flags section. |
| T-09-03 | Tampering | mitigate | CLOSED | `graphify/analyze.py` — `render_analysis_context()` and all helper functions use `.get()` with defaults throughout (verified at lines 20, 24, 51, 53, 81–83, 103, 145–146, 164–165, 171, 180–181, 205, 213–214, 220–235, 271–279, 288–289, 295, 299–311, 351–354, 371–376, 393–395, 398, 402–409, 422, 434, 471–473, 479–483, 490–492). No direct attribute access on untrusted node/edge dicts. |
| T-09-04 | Tampering | mitigate | CLOSED | `graphify/skill.md:1445` — "Parse each judge's response. Validate it matches the format '1st: Analysis-N / 2nd: Analysis-N / 3rd: Analysis-N'. If malformed, skip that judge and degrade gracefully to 2 judges." Format validation with explicit skip-and-degrade behavior. |
| T-09-05 | Spoofing | mitigate | CLOSED | `graphify/skill.md:1288–1290` — Three `ANTI-PATTERN` HTML comments enforce: (1) no conversation history between rounds — only TEXT output flows; (2) blind judge labels using Analysis-1/2/3, not incumbent/adversary/synthesis; (3) module placement guard (render_analysis stays in report.py). |
| T-09-06 | Tampering | accept | CLOSED | Accepted: Node labels originate from graphify's own extraction pipeline. `graphify/security.py` sanitizes all external input (HTML-escape, control char strip, 256-char length cap) before labels enter the graph. No external untrusted source injects labels directly into tournament prompts. Declared in 09-02-SUMMARY.md Threat Flags section. |
| T-09-07 | Denial of Service | accept | CLOSED | Accepted: Tournament is opt-in via explicit `/graphify analyze` command. Token cost of 4 lenses x 6 LLM calls is user-initiated and bounded by lens selection subset support (D-78). Declared in threat register. |

---

## Unregistered Threat Flags

Both 09-01-SUMMARY.md and 09-02-SUMMARY.md report "No new network endpoints, auth paths, file access patterns, or schema changes introduced."

No unregistered flags to record.

---

## Accepted Risks Log

| Threat ID | Category | Rationale |
|-----------|----------|-----------|
| T-09-02 | Info Disclosure | Graph context serialized into LLM prompts is intentional design. Graph data contains code structure only — no credentials, PII, or secrets. Extraction pipeline blocks sensitive files via `detect.py` sensitivity checks before they enter the graph. |
| T-09-06 | Tampering | Node labels pass through `graphify/security.py` sanitization (HTML-escape, control char strip, 256-char cap) before entering the graph. Labels in tournament prompts are therefore pre-sanitized at ingestion time. Risk accepted at ASVS Level 1. |
| T-09-07 | Denial of Service | Tournament is explicitly opt-in. Users control lens selection and can run a subset. No automatic or background invocation. Token cost is bounded and visible in Step A6 user report. |
