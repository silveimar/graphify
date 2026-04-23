# Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `13-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 13 — Agent Capability Manifest (+ SEED-002 Harness Memory Export)
**Areas discussed:** Wave A machine-readable surface, CI validate output, MANIFEST-07 meta hash behavior

---

## Wave A: incomplete tool surface

| Option | Description | Selected |
|--------|-------------|----------|
| Live-only truth | JSON lists only tools in `serve.py::list_tools()` at generation time; roadmap stays human docs only | ✓ |
| Schema version / wave field | Add `manifest_schema_version` or `capability_wave` without fake tool entries | |
| Other | User describes in chat | |

**User's choice:** Live-only truth — introspected tools only; no speculative entries.

**Notes:** Aligns with MANIFEST-05 introspection and honest agent contracts.

---

## CI: `graphify capability --validate`

| Option | Description | Selected |
|--------|-------------|----------|
| Hash + command | Non-zero exit; expected/actual hash, paths, exact regenerate command; no huge diffs by default | ✓ |
| Hash + jsonschema path / snippet | Above plus first mismatch path or short diff | |
| Other | User describes in chat | |

**User's choice:** Hash + command (minimal, copy-paste friendly).

---

## MANIFEST-07: manifest hash in `meta`

| Option | Description | Selected |
|--------|-------------|----------|
| Invalidate on reload | Recompute when manifest-relevant state changes; align with `serve.py` reload hooks / narrowed file set | ✓ |
| Every response | Fresh hash every RPC | |
| Startup only | Hash fixed at process start | |
| Other | User describes in chat | |

**User's choice:** Invalidate on reload — consistent merged state per response batch after reload triggers.

---

## Claude's Discretion

_No “you decide” on the three areas — all three were explicitly selected from structured options._

## Deferred Ideas

_None recorded._
