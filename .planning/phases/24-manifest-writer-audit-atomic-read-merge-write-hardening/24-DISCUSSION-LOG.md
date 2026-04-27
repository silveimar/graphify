# Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening — Discussion Log

**Date:** 2026-04-27
**Mode:** `/gsd-discuss-phase 24 --chain` (default flow, AskUserQuestion)
**Purpose:** Audit trail of questions presented to the user, options offered, and selections made. For human reference only — downstream agents read CONTEXT.md.

---

## Round 1 — Core Implementation Decisions

### Q1 — MCP manifest identity
**Question:** Success criterion #2 names "the MCP `manifest.json`". The audit shows two candidates after the quick-260422-jdj rename. Which file does Phase 24 actually mean?

| Option | Selected |
|---|---|
| `capability.json` (graphify/capability.py:225 — MCP tool registry, was originally `manifest.json` before the rename) | ✅ |
| `detect.py` mtime log (graphify-out/manifest.json — per-file mtime tracker, blind overwrite + non-atomic) | |
| Both — broaden scope (treat criterion #2 as covering both files) | |

**Notes:** Recommended option taken. Resolves a genuine ambiguity introduced by the `manifest.json` → `capability.json` rename in quick-260422-jdj. Locked as **D-01**.

---

### Q2 — routing.json merge policy
**Question:** routing.json is currently a deterministic dump of in-memory RoutingAudit state (blind overwrite, atomic). To survive subpath runs on a shared vault, it must become read-merge-write — but its `files` dict is keyed by file path. What's the merge policy?

| Option | Selected |
|---|---|
| Last-write-wins by path | ✅ |
| Preserve-existing on conflict (only add new paths; keep old entry on collision) | |
| Append with run timestamp (per-path history list) | |

**Notes:** Recommended option taken. Mirrors policy already in `vault-manifest.json` and `seeds-manifest.json` — no new merge semantics introduced. Locked as **D-02** (and **D-04** for `capability.json`, same policy by mirror).

---

### Q3 — Row identity per manifest
**Question:** Each manifest needs a documented row identity key for merging. Confirm the keys, or flag any to revisit?

| Option | Selected |
|---|---|
| `vault-manifest.json` → `path` (note path) | ✅ |
| `seeds-manifest.json` → `seed_id` | ✅ |
| `routing.json` → file path (dict key) | ✅ |
| MCP manifest → tool name / file path | ✅ |

**Notes:** All four confirmed (multiSelect). Locked as **D-03**. The MCP manifest row identity = `tool name` once Q1 was answered (capability.json keys by tool name, not file path).

---

### Q4 — AUDIT.md shape
**Question:** Success criterion #1 requires an AUDIT.md enumerating every manifest writer with pre-fix and post-fix policy. How exhaustive?

| Option | Selected |
|---|---|
| Table per writer + policy diff (one row per writer, ~1 page) | ✅ |
| Narrative section per writer | |
| Table + landmine appendix (table + appendix listing known subpath-erase incidents) | |

**Notes:** Recommended option taken. Compact, scannable, easy to anchor future manifest additions to. Locked as **D-06**.

---

## Round 2 — Edge Cases and Scope

### Q5 — detect.py / graphify-out/manifest.json scope
**Question:** detect.py's `graphify-out/manifest.json` mtime log isn't covered by success criterion #2 (Q1 picked capability.json, not "both"). But the audit flagged it: blind overwrite AND non-atomic, worst of both worlds. What do we do with it in Phase 24?

| Option | Selected |
|---|---|
| Document in AUDIT.md, defer fix | ✅ |
| Patch it too (atomic + read-merge-write) | |
| Patch atomic only, skip merge | |

**Notes:** Recommended option taken. Rationale: `detect.save_manifest` is only callable from `detect_incremental`, which isn't wired up to any active CLI flow. Patching now would couple Phase 24 to a future "wire up incremental detect" phase. AUDIT.md row will mark this `DEFERRED` with rationale so the future phase can't miss it. Locked as **D-05**.

---

### Q6 — Subpath-isolation regression test surface
**Question:** Success criterion #3 mandates a subpath-isolation regression test (sub_a then sub_b, both row sets present). What's the test surface?

| Option | Selected |
|---|---|
| One test per affected writer (3 unit tests: vault-manifest, routing, capability) | ✅ |
| One end-to-end test on canonical case | |
| Both — unit per writer + one E2E | |

**Notes:** Recommended option taken. Three pure unit tests under existing `tmp_path` conventions: one each for `vault-manifest.json` (locks the existing contract), `routing.json` (exercises the new writer), `capability.json` (exercises the new writer). No E2E — would cross module boundaries, slower, harder to debug, and the unit tests fully cover criterion #3. Locked as **D-07**.

---

### Q7 — Migration policy for pre-v1.6 manifests
**Question:** When a vault has a pre-v1.6 manifest written by the old blind-overwrite code (already missing some sibling rows), the new read-merge-write writer will preserve those incomplete rows on the next run. Migration policy?

| Option | Selected |
|---|---|
| No migration — merge from current state | ✅ |
| Add a `graphify manifest rebuild` CLI | |
| Auto-detect stale manifests and warn | |

**Notes:** Recommended option taken. Treats whatever's on disk as authoritative on first read after upgrade; users re-run on missing subpaths to re-populate. Zero migration code, zero risk of clobbering hand-edits. AUDIT.md preamble will document the recovery path. The CLI and warn-on-stale options are both genuinely new capabilities and belong in their own phase. Locked as **D-08**. Captured in `<deferred>`.

---

## Deferred Ideas (captured, not acted on)

- Atomic + read-merge-write fix for `detect.save_manifest` — deferred to whichever future phase wires up `detect_incremental` to an active CLI flow.
- `graphify manifest rebuild` CLI — new capability for explicit recovery from stale pre-v1.6 manifests.
- Stale-manifest detection with stderr warning — ergonomic improvement; new capability.
- Shared `graphify/_manifest_io.py` helper module — fold in only if read-merge step is identical between `routing_audit.py` and `capability.py` and the planner judges the duplication harmful.

## Claude's Discretion (passed to researcher / planner)

- Inline read-merge step vs factored helper (`_read_existing(path) -> dict`) — default inline if ≤6 LOC.
- Exact location of `tests/test_capability.py` if it doesn't exist.
- Whether AUDIT.md sits at the phase directory (preferred) or repo root.
- Which test in the vault-manifest.json group exercises the contract (`test_vault_promote.py` or `test_merge.py`) — based on existing test patterns.
- One-line code comments at each patched write site referencing MANIFEST-09/10 (default: yes, terse).
