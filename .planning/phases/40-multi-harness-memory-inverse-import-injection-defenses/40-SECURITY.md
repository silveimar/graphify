---
phase: 40
slug: multi-harness-memory-inverse-import-injection-defenses
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-29
---

# Phase 40 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Graph snapshot → interchange file | User-controlled labels in graph; export validates before write | JSON / extraction dict |
| Imported harness file | Untrusted filesystem content → build inputs | Markdown / JSON bytes |
| MCP / CLI argv | Hostile path strings | Paths resolved under `graphify-out` |
| Tool responses | Agent-consumed text | JSON of validated extraction / interchange envelope |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-40-01 | T | interchange write | mitigate | Path confined under artifacts base; atomic `.tmp` + `os.replace` (`harness_interchange`, `harness_export`) | closed |
| T-40-02 | I | provenance in file | accept | Provenance is attest metadata; `validate_extraction` on inner payload | closed |
| T-40-03 | I | harness markdown / JSON bodies | mitigate | `sanitize_label`, `sanitize_harness_text`, `guard_harness_injection_patterns`; optional `strict` | closed |
| T-40-04 | E | oversized file DoS | mitigate | `MAX_HARNESS_IMPORT_BYTES`; capped read before decode | closed |
| T-40-05 | T | path traversal | mitigate | `validate_graph_path` relative to artifacts root | closed |
| T-40-06 | T | import-harness CLI path | mitigate | Delegates to `import_harness_path` + same path policy | closed |
| T-40-07 | I | echoed file content | accept | CLI prints destination path; writes `harness_import.json` (validated JSON), not raw harness dump | closed |
| T-40-08 | T | MCP import path | mitigate | `validate_graph_path` before read; `import_harness_path` only | closed |
| T-40-09 | I | MCP tool return text | mitigate | Returns JSON of validated extraction / interchange only | closed |
| T-40-10 | E | large MCP payloads | mitigate | Same byte caps and library path as CLI | closed |
| T-40-RT | — | fixture tests | accept | Test-only scope; no production surface | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-40-01 | T-40-02 | Spoofed provenance fields do not bypass `validate_extraction` on graph content | Phase 40 secure-phase | 2026-04-29 |
| AR-40-02 | T-40-07 | Operators see output path; extraction body written to confined JSON file | Phase 40 secure-phase | 2026-04-29 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-29 | 11 | 11 | 0 | gsd-secure-phase (automated verification) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-29
