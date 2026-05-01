# Phase 51: v1.10-gap-mcp-trace-req-signoff - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-05-01
**Phase:** 51-v1.10-gap-mcp-trace-req-signoff
**Areas discussed:** Verification placement · CCODE-04 REQ mapping (`concept_code_hops` vs `/trace` vs `entity_trace`) · Phase 47 wrap-up vs roadmap-only lock

---

## Session mode

This session applied **roadmap-driven gap closure** analysis without synchronous **AskUserQuestion** turns (Cursor/async). Gray areas were identified from **ROADMAP**, **REQUIREMENTS**, **47-CONTEXT**, **47-01/47-02** plans, and repository grep. Decisions are captured in **`51-CONTEXT.md`**.

---

## Verification artifact placement

| Option | Description | Selected |
|--------|-------------|----------|
| A | Canonical **`47-VERIFICATION.md`** under **`.planning/phases/47-mcp-trace-integration/`** (parity with Phase **45** / **50**) | ✓ |
| B | Verification only under Phase **51** directory | |

**User's choice:** Default **A** (roadmap + hygiene pattern).
**Notes:** Aligns with REQUIREMENTS traceability "**51** (gap closure → **47**)".

---

## CCODE-04 literal vs implemented surfaces

| Option | Description | Selected |
|--------|-------------|----------|
| A | Satisfy CCODE-04 via **`concept_code_hops`** golden-path test; document REQ wording mapping in **`47-VERIFICATION.md`** | ✓ |
| B | Require additional **`/trace`** slash automation tests before tick | |

**User's choice:** Default **A** — REQ allows **`/trace` OR `entity_trace`**; **`entity_trace`** is temporal; typed hops delivered by **`concept_code_hops`** per **47** plans.

---

## Claude's Discretion

- **`server.json`** regeneration and manifest hash validation — executor follows **`CLAUDE.md`** / **`graphify capability`**.
- Ordering of **47-02** grep checks vs full **`pytest tests/`** gate — planner may wave-split; CONTEXT requires no REQ tick without evidence.

---

## Deferred Ideas

- Dedicated slash command invoking **`concept_code_hops`** interactively — out of scope for Phase **51** unless escalated to a new roadmap phase.
