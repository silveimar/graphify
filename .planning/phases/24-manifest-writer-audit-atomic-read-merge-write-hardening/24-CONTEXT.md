# Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make every on-disk manifest writer in graphify survive subpath-scoped runs against a shared vault — no row erasure of siblings — by enforcing uniform **read-merge-write semantics + `.tmp` + `os.replace` atomic commit**, scoped by **row identity** (path / id / tool name), not by run. Producing artifacts: an `AUDIT.md` enumerating every manifest writer with pre-v1.6 vs post-fix policy, code patches against the writers that don't already meet the contract, and a per-writer subpath-isolation regression test suite.

**In scope (writers patched):**
- `routing.json` (`graphify/routing_audit.py:34` — `RoutingAudit.flush`) — switch from blind overwrite to read-merge-write keyed by file path, last-write-wins on conflict.
- `capability.json` (`graphify/capability.py:225` — `write_manifest_atomic`) — switch from blind overwrite to read-merge-write keyed by tool name, last-write-wins on conflict. (This is the file referred to as "the MCP `manifest.json`" in success criterion #2 — it WAS `manifest.json` until the quick-260422-jdj rename.)
- Subpath-isolation regression tests for the three patched-or-locked writers: `vault-manifest.json` (locks existing contract), `routing.json`, `capability.json`.
- `AUDIT.md` — table per writer with policy diff (path / function / line / row identity / pre-fix read+atomic flags / post-fix read+atomic flags / invocation site). Includes `detect.save_manifest` and `seed._save_seeds_manifest` and `vault_promote._save_manifest` and `merge._save_manifest` for completeness, even when no patch is applied.

**Already-compliant writers (locked, not modified):**
- `vault-manifest.json` (`graphify/vault_promote.py:665` and `graphify/merge.py:1085`) — already atomic + read-merge-write keyed by `path`. Phase 24 only adds a regression test that asserts the contract.
- `seeds-manifest.json` (`graphify/seed.py:114`) — already atomic + read-merge-write keyed by `seed_id`. No code change; documented in AUDIT.md.

**Out of scope:**
- `detect.save_manifest` / `graphify-out/manifest.json` — non-atomic AND blind overwrite, but not invoked by any active CLI flow (only callable from `detect_incremental`, which isn't wired up). Documented in AUDIT.md as a known-bad writer; fix deferred to whichever future phase wires up incremental detect. (See D-04.)
- New CLI commands (e.g., `graphify manifest rebuild`) — that would be a new capability and belongs in its own phase.
- Stale-manifest detection / warning heuristics — also new capability; deferred.
- Refactoring writers into a shared helper module — research/planner can decide if a helper falls out naturally, but the success criteria don't require it.

</domain>

<decisions>
## Implementation Decisions

### Q1 — Identity of "the MCP `manifest.json`"
- **D-01:** "The MCP `manifest.json`" referenced in success criterion #2 = `capability.json` (`graphify/capability.py:225`). It was renamed from `manifest.json` in `quick-260422-jdj` to eliminate a path collision with `detect.py`'s `graphify-out/manifest.json` mtime log (collision documented in `capability.py:230-231` docstring). The roadmap's wording "MCP `manifest.json`" is historical — the file ships the MCP tool surface and is the writer that materially needs the read-merge-write upgrade. `detect.py`'s `manifest.json` is explicitly NOT this writer (D-04).

### Q2 — routing.json merge policy
- **D-02:** Switch `RoutingAudit.flush` to read-merge-write keyed by file path with **last-write-wins on conflict**. Read existing `routing.json`; for each path in the new run, replace the entry; preserve all paths from prior runs that this run didn't touch. Mirrors the policy already in `vault-manifest.json` and `seeds-manifest.json` — no new merge semantics. No timestamps, no per-path history list, no preserve-existing branch. Atomic commit (`.tmp` + `os.replace`) is already in place (`routing_audit.py:48-50`); the fix is the read-merge step, not the atomicity step.

### Q3 — Row identity per manifest (locked for AUDIT.md and writer headers)
- **D-03:** Row identity keys, locked:
  - `vault-manifest.json` → `path` (note path) — already de-facto in `vault_promote._save_manifest` and `merge.apply_merge_plan`.
  - `seeds-manifest.json` → `seed_id` — already de-facto in `seed._save_seeds_manifest`.
  - `routing.json` → file path (the dict key in `files: {path: routes}`) — locked as the merge key for the new read-merge-write writer.
  - `capability.json` → tool name — locked as the merge key for the new read-merge-write writer (the existing `build_manifest_dict` already produces a keyed-by-tool-name structure; merge layers new run output on top of disk state).

### Q4 — capability.json merge policy (mirrored from D-02)
- **D-04 (capability.json policy):** Same shape as routing.json — read-merge-write keyed by tool name, last-write-wins on conflict. Atomic commit is already in place (`capability.py:239-240`); the fix is the read-merge step.

### Q5 — detect.py / graphify-out/manifest.json scope
- **D-05:** Document `detect.save_manifest` (`graphify/detect.py:447-457`) in AUDIT.md as a known-bad writer (blind overwrite, non-atomic), but do NOT patch in Phase 24. Rationale: it's only callable via `detect_incremental` (`detect.py:467`), which is not wired up to any active CLI flow. Patching now means writing code + tests for an unreachable surface and risks coupling Phase 24 to whichever future phase wires up incremental detect. AUDIT.md MUST flag this so the future phase can't miss it.

### Q6 — AUDIT.md shape
- **D-06:** AUDIT.md is a **table per writer with a policy diff**, not narrative. Columns: `manifest filename`, `writer (file:function:line)`, `invocation site`, `row identity key`, `pre-fix read?`, `pre-fix atomic?`, `post-fix read?`, `post-fix atomic?`, `Phase 24 action` (PATCHED / LOCKED — already compliant / DEFERRED — known-bad). One table; rows for `vault-manifest.json`, `seeds-manifest.json`, `routing.json`, `capability.json`, `graphify-out/manifest.json` (detect). Compact, anchors future manifest additions. Add a 1-paragraph preamble explaining the row-identity contract and the atomic commit contract. No landmine appendix (the DEFERRED row for detect.py and the PATCHED rows already capture the relevant landmines). Target ~1 page.

### Q7 — Regression test surface
- **D-07:** **One subpath-isolation test per affected writer**, all under existing `tests/` conventions (pure unit, `tmp_path` only, no FS side effects outside it):
  1. `tests/test_vault_promote.py` (or `tests/test_merge.py` — researcher decides based on which module's API best exercises the path) → `test_subpath_isolation_vault_manifest`. Locks the existing contract: two sequential calls writing rows for `sub_a/` then `sub_b/` produce a manifest containing both row sets. Asserts no regression in `vault_promote._save_manifest` or `merge._save_manifest`.
  2. `tests/test_routing_audit.py` → `test_subpath_isolation_routing` — exercises the new read-merge-write writer in `RoutingAudit.flush`. Two sequential flushes covering disjoint path sets; assert union present after the second flush.
  3. `tests/test_capability.py` (or wherever the existing capability tests live; create the file if absent under existing conventions) → `test_subpath_isolation_capability_manifest` — exercises the new read-merge-write writer in `write_manifest_atomic`. Two sequential writes covering disjoint tool-name sets; assert union present after the second write.

  No end-to-end pipeline test (would cross module boundaries, slower, harder to debug); no belt-and-suspenders E2E on top of the unit tests. The three unit tests fully cover success criterion #3.

### Q8 — Migration policy for pre-v1.6 manifests
- **D-08:** No migration. On first read after the upgrade, the new read-merge-write writers treat whatever's on disk as authoritative and merge new run output on top. Users with pre-v1.6 manifests missing sibling rows can re-run on the missing subpaths to re-populate. Zero migration code, zero risk of clobbering hand-edits. AUDIT.md MUST document this behavior in its preamble so users know how to recover stale state. No `graphify manifest rebuild` CLI (new capability, deferred); no auto-detection / stderr warning (also a new capability, deferred).

### Claude's Discretion (for researcher / planner)
- Whether the read-merge step in `routing_audit.py` and `capability.py` lives inline in the writer function or factors out to a tiny module-local `_read_existing(path) -> dict` helper. Default: inline if ≤6 LOC; factored if it would exceed that or if both writers end up with identical shape (then a shared helper in a small new module like `graphify/_manifest_io.py` is acceptable, but NOT required by the success criteria).
- Exact location of the new test file `tests/test_capability.py` if it doesn't already exist (researcher: confirm via `ls tests/test_capability.py`).
- Whether AUDIT.md sits at `.planning/phases/24-manifest-writer-audit-atomic-read-merge-write-hardening/AUDIT.md` (preferred — anchored to the phase) or at the repo root. Default: phase directory, matching success criterion #1's wording.
- Which test in the vault-manifest.json group exercises the contract — researcher picks the most natural module surface based on existing test patterns for `vault_promote` / `merge`.
- One-line code comments at each patched write site referencing MANIFEST-09/10 and Issue context (default: yes, terse, matching the dedup.py:493 anchor-comment style locked in Phase 23).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Manifest Subpath Safety (MANIFEST)" — MANIFEST-09, MANIFEST-10, MANIFEST-11, MANIFEST-12 acceptance text
- `.planning/ROADMAP.md` "Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening" — 4 success criteria
- `.planning/PROJECT.md` "Current Milestone: v1.6 Hardening & Onboarding" — milestone framing

### Code under change (writers patched)
- `graphify/routing_audit.py:34-52` — `RoutingAudit.flush`. Pre-fix: blind overwrite, atomic. Post-fix: read-merge-write keyed by file path, last-write-wins, atomic.
- `graphify/capability.py:225-241` — `write_manifest_atomic`. Pre-fix: blind overwrite, atomic. Post-fix: read-merge-write keyed by tool name, last-write-wins, atomic. Invoked from `capability.write_runtime_manifest` (`capability.py:245`) → `export.to_networkx` (`export.py:585`).

### Code that locks the contract (already compliant — DO NOT modify)
- `graphify/vault_promote.py:650-682` — `_load_manifest` / `_save_manifest`. Reference implementation of read-merge-write + atomic.
- `graphify/merge.py:1085` — `_save_manifest` (sibling of vault_promote). Same pattern; invoked via `apply_merge_plan` at `merge.py:1355`.
- `graphify/seed.py:96-131` — `_load_seeds_manifest` / `_save_seeds_manifest`. Reference implementation keyed by `seed_id`.

### Code documented but NOT patched in Phase 24
- `graphify/detect.py:447-457` — `save_manifest`. Blind overwrite, non-atomic. Only callable from `detect_incremental` (`detect.py:467`), which is not wired up to any active CLI flow. AUDIT.md row marks this DEFERRED with rationale.

### Carry-forward decisions that bind this phase
- Plan 18-01 lock (STATE.md): "single canonical helper, never inline duplication" — applies if a shared `_manifest_io.py` falls out naturally; not required.
- Phase 23 D-01 (atomic helpers live in one canonical place via `analyze._iter_sources`) — sets the precedent for Phase 24's "read-merge-write contract is uniform across all writers".
- quick-260422-jdj — established the `manifest.json` → `capability.json` rename to eliminate path collision with `detect.py`. Phase 24 honors that rename: D-01 anchors to `capability.json`.

### Memory anchors (context only — not code)
- Memory observation 2956 — "manifest.json Overwritten on Subpath Folder Updates" — original symptom that motivated this phase.
- Memory observation 2960 — "manifest.json in graphify-out vs vault-manifest.json — Install Logic in __main__.py" — confirms the historical filename ambiguity that D-01 resolves.
- Memory observation 2976 (Phase 23 trace) — confirms the v1.6 milestone framing of "list-handling + manifest hardening as parallel hardening tracks".

</canonical_refs>

<code_context>
## Reusable Patterns Already in the Codebase

- **Read-merge-write + atomic reference implementation:** `vault_promote._save_manifest` (`graphify/vault_promote.py:665-682`). Pattern:
  1. `existing = _load_manifest(path)` (returns `{}` on missing/corrupt)
  2. Merge new rows into `existing` keyed by row identity
  3. Write to `f"{path}.tmp"` then `os.replace(f"{path}.tmp", path)`
- **`seeds-manifest.json` mirror:** `seed._save_seeds_manifest` (`graphify/seed.py:114`). Same shape, key = `seed_id`.
- **Atomic-only (no merge) writer:** `routing_audit.flush` (`routing_audit.py:34`). Already has `.tmp` + `os.replace`; the patch is the read-merge step before the write.
- **Atomic-only (no merge) writer:** `capability.write_manifest_atomic` (`capability.py:225`). Already has `.tmp` + `os.replace`; patch is the read-merge step.
- **Test conventions for manifest writers:** `tests/test_vault_promote.py` and `tests/test_merge.py` (existing) demonstrate `tmp_path` + write-twice-and-assert-union patterns. New tests should follow that shape, not invent new fixtures.

</code_context>

<deferred>
## Noted for Later

- **Atomic + read-merge-write fix for `detect.save_manifest` / `graphify-out/manifest.json`** — deferred per D-05. The future phase that wires up `detect_incremental` to an active CLI flow (e.g., a `graphify run --update` mode or a watch-mode hookup) MUST include this fix as part of its scope. AUDIT.md will surface this requirement.
- **`graphify manifest rebuild` CLI** — new capability for explicit recovery from stale pre-v1.6 manifests. Useful but genuinely new surface; out of v1.6 hardening scope.
- **Stale-manifest detection + stderr warning** — ergonomic improvement to flag manifests where disk has files not present in manifest entries. Out of v1.6 hardening scope.
- **Shared `graphify/_manifest_io.py` helper module** — only refactor in if the read-merge step ends up identical between `routing_audit.py` and `capability.py` and the planner judges the duplication actively harmful. Otherwise inline.

</deferred>

<spec_lock>
## Locked Acceptance Criteria (from ROADMAP.md success criteria — DO NOT renegotiate)

1. AUDIT.md exists at `.planning/phases/24-manifest-writer-audit-atomic-read-merge-write-hardening/AUDIT.md` enumerating every manifest writer in the codebase, pre-v1.6 policy, post-fix policy. (D-06 locks the table shape.)
2. `vault-manifest.json`, `seeds-manifest.json`, `routing.json`, and the MCP `manifest.json` (= `capability.json` per D-01) all commit via `.tmp` + `os.replace` after read-merge-write keyed by row identity (path/id), not by run.
3. Subpath-isolation regression: two sequential runs against `vault/sub_a/` then `vault/sub_b/` produce a single manifest containing rows from both subpaths. (D-07 locks this as 3 per-writer unit tests.)
4. `pytest tests/ -q` is green; subpath isolation regression test added under existing test conventions.

</spec_lock>
