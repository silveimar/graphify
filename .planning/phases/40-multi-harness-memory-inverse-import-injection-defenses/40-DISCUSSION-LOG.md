# Phase 40: multi-harness-memory-inverse-import-injection-defenses - Discussion Log

> **Audit trail only.** Decisions live in `40-CONTEXT.md`.

**Date:** 2026-04-29
**Areas discussed:** PORT-01 target, Import CLI, Sanitization, MCP parity, Round-trip, SECURITY.md depth

---

## PORT-01 — second export target

| Option | Selected |
|--------|----------|
| Codex AGENTS bundle | |
| **Canonical JSON manifest interchange** | ✓ |
| Extension point + stub only | |

---

## Import CLI

| Option | Selected |
|--------|----------|
| **Single `import-harness` + `--format`** | ✓ |
| Subcommands per format | |
| File only (stdin deferred) | ✓ (aligned with single_cmd choice) |

---

## SEC-01 — sanitization

| Option | Selected |
|--------|----------|
| **Layered guards + provenance** | ✓ |
| Strict reject file | |
| Normalize only | |

---

## SEC-03 — MCP

| Option | Selected |
|--------|----------|
| **Same milestone — shared code paths** | ✓ |
| CLI first, MCP later | |

---

## PORT-04 — round-trip

| Option | Selected |
|--------|----------|
| **Semantic preservation within documented limits** | ✓ |
| Deterministic bytes | |
| Docs + smoke only | |

---

## SEC-04 — SECURITY.md

| Option | Selected |
|--------|----------|
| **Full subsection** | ✓ |
| Compact bullets | |
| Short pointer | |

---

## Deferred / out of scope

- Phase 41 vault CLI; stdin/URL import; extra markdown emitters until interchange stable (see CONTEXT).
