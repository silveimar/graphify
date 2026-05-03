# Phase 57: Elicitation & harness increment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 57-elicitation-harness-increment
**Areas discussed:** ELIC-01 scenario pick, ELIC-01 follow-up scope, HARN-01 capability lane, HARN-01 surface follow-up, HARN-02 guard surface, ELIC-02 doc surface, ELIC-02 trust-boundary content

---

## ELIC-01 — Scenario pick

| Option | Description | Selected |
|--------|-------------|----------|
| Sidecar collision | Lock build.py:281-299 invariant; elicitation wins on duplicate id | ✓ |
| --demo offline path | Deterministic --demo sidecar without LLM calls | |
| --force overwrite | --force replaces existing sidecar; refuse without it | |
| Empty-corpus build merge | build() with sidecar only, no file extractions | |

**User's choice:** Sidecar collision (Recommended).
**Notes:** High coverage value, low scope; targets the load-bearing merge invariant.

---

## ELIC-01 — Follow-up: collision scope

| Option | Description | Selected |
|--------|-------------|----------|
| Nodes + edges | Both node-id collision and edge-level merge behavior; ~6-8 cases | ✓ |
| Nodes only | Lock node 'elicitation wins' rule with 2-3 failure modes | |
| Nodes + edges + sidecar shape | Above plus on-disk schema/ordering assertions | |

**User's choice:** Nodes + edges (Recommended).
**Notes:** Sidecar on-disk shape deferred — overlaps validate.py.

---

## HARN-01 — Capability lane

| Option | Description | Selected |
|--------|-------------|----------|
| Inverse-import guards | Keep inverse-import off-default; add explicit guard tests | ✓ |
| New target format on export | Add canonical mapping for an additional harness format | |
| Document + harden existing canonical mapping | Round-trip property tests on existing schema | |

**User's choice:** Inverse-import guards (Recommended).
**Notes:** Pairs naturally with HARN-02 — same surface, different lens.

---

## HARN-01 — Surface follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Existing import-harness surface | Harden existing CLI + MCP path with guard tests; no new code | ✓ |
| New inverse round-trip | Wire export → import → graph equality | |
| Touched but kept dormant | Touch inverse-import code but keep entrypoint off-default | |

**User's choice:** Existing import-harness surface (Recommended).
**Notes:** Doc describes existing canonical mapping (interchange/v1) as-is, in prose.

---

## HARN-02 — Guard surface (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Refuses vault-rooted output | Reject --output inside any vault unless explicit confirm flag | ✓ |
| Never auto-invoked from pipelines | Meta-test: no command transitively calls import_harness_* | ✓ |
| MCP tool requires explicit args | MCP refuses without explicit path; no auto-discovery | ✓ |
| Size + injection caps | Re-test MAX_HARNESS_IMPORT_BYTES + sanitize_harness_text | |

**User's choice:** All three "Recommended" guarantees.
**Notes:** Size + injection caps explicitly out of scope — already covered by Phase 40.

---

## ELIC-02 — Doc surface

| Option | Description | Selected |
|--------|-------------|----------|
| Update ELICITATION.md in place | Add Trust Boundaries + v1.11 Non-Goals sections | ✓ |
| Split out docs/TRUST-BOUNDARIES.md | New dedicated doc with link from ELICITATION.md | |
| Refactor ELICITATION.md into milestone-current overview | Larger restructure; canonical "what we trust" doc | |

**User's choice:** Update ELICITATION.md in place (Recommended).
**Notes:** Smallest blast radius; preserves history.

---

## ELIC-02 — Trust-boundary content (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Where elicitation reads/writes | resolve_output() contract; sidecar location; vault config consent | ✓ |
| What import-harness will and will not do | Off-by-default; vault-rooted refusal; explicit path; no MCP discovery | ✓ |
| LLM trust posture during elicit | --demo / interactive sanitization; label escaping for HTML/Obsidian | ✓ |
| Sidecar merge precedence | Document the build.py 'elicitation wins' invariant in prose | |

**User's choice:** First three (Recommended).
**Notes:** Sidecar merge precedence intentionally NOT in the doc — ELIC-01 tests are the canonical record; doc may reference the test module.

---

## Claude's Discretion

- Test file layout (extend existing modules vs new `test_phase57_guards.py`).
- Exact name of explicit confirmation flag for vault-rooted output.
- Static import-graph analysis vs runtime grep for the "no auto-invocation" guard test.

## Deferred Ideas

- Real inverse round-trip (harness_export → harness_import equality) — future harness phase.
- New harness target format — future "harness expansion" phase when a concrete target appears.
- Sidecar on-disk schema assertions — overlaps validate.py work.
- Re-testing size caps and prompt-injection sanitization — already covered by Phase 40.
- Refactoring docs/ELICITATION.md into a milestone-current overview — future docs-pass phase.
