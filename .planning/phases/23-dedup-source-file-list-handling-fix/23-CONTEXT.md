# Phase 23: Dedup `source_file` List-Handling Fix - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Patch the `TypeError: unhashable type: 'list'` crash in `graphify/dedup.py` (cross-type edge merge) so `graphify --dedup --dedup-cross-type` succeeds on extractions whose edges already carry `list[str]` `source_file` values (Issue #4). Merged edge `source_file` shape stays compatible with existing `export.py` / `report.py` / `serve.py` consumers: sorted unique `list[str]` when ≥2 contributors, scalar `str` when exactly 1, empty `str` when none.

**In scope:** edges-path patch in `dedup.py` only; one regression test fixture + one idempotency test in `tests/test_dedup.py`.
**Out of scope:** node-path refactor (already hardened in v1.3 IN-06); export/report/serve consumer changes; broader sweep of every `source_file` reader; new helpers.

</domain>

<decisions>
## Implementation Decisions

### Helper Choice
- **D-01:** Reuse `graphify.analyze._iter_sources` to flatten `str | list[str] | None` into `list[str]` at the edge-merge site. Do NOT introduce a new `_sf_flatten` helper. This matches Plan 18-01's locked carry-forward ("`source_file: str | list[str]` handling delegates to `analyze._iter_sources` (never inline `isinstance` checks)") and honors the existing recommendation comment at `dedup.py:448`. Single source of truth across `analyze.py`, `vault_promote.py`, `serve.py`, and now `dedup.py`.

### Fix Surface Area
- **D-02:** Patch the edges path only (the set comprehension at `dedup.py:493`). The node merge block at `dedup.py:445-459` was already hardened in v1.3 (memory observation 918, "IN-06 O(n) Set-Based source_file Folding"); leave it untouched. No audit-pass refactor of every `source_file` consumer in `dedup.py` — that would be scope creep beyond DEDUP-01.
- **D-03:** Concrete patch shape: replace `sf_set = {e["source_file"] for e in group if e.get("source_file")}` with a flatten-then-set construction: iterate `group`, feed each `e.get("source_file")` through `_iter_sources`, accumulate into `sf_set` (a `set[str]`). Empty/missing values produce no entries. This is the minimal change that accepts both scalar and list-shaped inputs.

### Output Shape Contract
- **D-04:** Preserve the current contract verbatim — sorted unique `list[str]` for ≥2 contributors, scalar `str` for exactly 1, empty `str` for none. Lines 495-497 stay structurally identical post-fix. This matches DEDUP-02's literal wording, mirrors the node path at `dedup.py:459`, and avoids touching any downstream consumer that relies on the scalar fast path. Do NOT switch to "always emit `list[str]`" — that would be a breaking shape change masquerading as a bugfix.

### Regression Test Shape
- **D-05:** Two test cases in `tests/test_dedup.py`, both pure unit tests under existing conventions (no FS side effects):
  1. **DEDUP-03 spec case** — fixture extraction whose edges already carry `list[str]` `source_file` (e.g., `["a.py", "b.py"]`); run `graphify --dedup --dedup-cross-type` (or its programmatic equivalent); assert no `TypeError` raised AND merged edge `source_file` equals the sorted unique union.
  2. **Idempotency case** — run dedup twice on the same extraction; assert second run is a no-op on `source_file` shape (already-list inputs survive a re-pass) AND no exception. This directly exercises the regression vector that caused Issue #4: dedup output (`list[str]`) being valid dedup input.
- **D-06:** Do NOT add an export-consumer smoke test (`to_obsidian` / `to_html` / `to_json` over merged extraction). Those modules already have their own tests and route through `_iter_sources` — coverage would be redundant.
- **D-07:** Do NOT add a mixed scalar+list-in-the-same-group fixture. The two cases above already cover the pure-list path (D-05.1) and the round-trip path (D-05.2); pure-scalar is the existing baseline. Mixed is implicit if scalar+list both flatten through `_iter_sources` correctly.

### Claude's Discretion
- Exact placement of the `_iter_sources` import in `dedup.py` (top-of-file alongside other `graphify.*` imports vs lazy import inside the merge function). Default: top-of-file, matches existing import style in `vault_promote.py` and `serve.py`.
- Naming/location of the new test functions in `tests/test_dedup.py` (e.g., `test_cross_type_merges_list_shaped_source_file` and `test_dedup_is_idempotent_on_source_file_shape`).
- Whether to add a one-line code comment at the patched site referencing Issue #4 / DEDUP-01 (default: yes, brief, since dedup.py already has anchor comments at lines 87 / 445-449).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Dedup Stability (DEDUP)" — DEDUP-01, DEDUP-02, DEDUP-03 acceptance text
- `.planning/ROADMAP.md` "Phase 23: Dedup `source_file` List-Handling Fix" — 4 success criteria
- `.planning/PROJECT.md` "Current Milestone: v1.6 Hardening & Onboarding" — milestone framing

### Code under change
- `graphify/dedup.py:493` — bug site (edges path, set comprehension)
- `graphify/dedup.py:445-459` — node path (already hardened in v1.3 — DO NOT modify)
- `graphify/dedup.py:87` and `:448` — anchor comments documenting the `str | list[str]` shape contract
- `graphify/analyze.py:11` — `_iter_sources(source_file: "str | list[str] | None") -> list[str]` (the helper to import)

### Carry-forward decisions that bind this phase
- Plan 18-01 lock (STATE.md): "`source_file: str | list[str]` handling delegates to `analyze._iter_sources` (never inline `isinstance` checks)" — applies directly here
- Memory observation 918 (2026-04-16): IN-06 O(n) set-based source_file folding committed for the **node** path; the edge path was missed
- Memory observation 1015 (2026-04-17): `dedup.py` confirmed write site for `source_file: list[str]` production — the same module that produces lists must accept them on re-pass
- Memory observation 1494 (2026-04-20): Focus resolver lock affirming `_iter_sources` as the canonical reader

### Existing tests to extend
- `tests/test_dedup.py` (408 lines) — add the two D-05 cases following existing fixture/assertion style

### External report
- GitHub Issue #4 — `TypeError: unhashable type: 'list'` reproduction (memory obs 2959)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify.analyze._iter_sources` (`analyze.py:11`) — already the canonical `str | list[str] | None → list[str]` flattener; used 8+ times across `analyze.py`, `vault_promote.py`, `serve.py`, and recommended by `dedup.py:448`'s own comment. The fix imports and uses this; no new helper.
- `dedup.py:445-459` (node merge block) — pattern template for the fix. Already builds `sf_set` element-by-element from `existing` and `incoming`, falls back to scalar when `len(sf_set) == 1`. The edges-path fix at line 493 mirrors this pattern.
- `tests/test_dedup.py` (408 lines, existing fixtures and assertion style) — add the two regression cases here without restructuring.

### Established Patterns
- **Shape contract (write side):** dedup produces `list[str]` for multi-source edges/nodes, scalar for single-source. Codified at `dedup.py:459` (nodes) and `dedup.py:495-497` (edges, post-fix).
- **Shape contract (read side):** every reader must route `source_file` through `_iter_sources`. Anything that does inline `isinstance(x, list)` is a latent bug.
- **No new required deps:** v1.6 is a hardening milestone (REQUIREMENTS.md "Out of Scope"). Stdlib + existing intra-package import only.
- **Test conventions (CLAUDE.md):** pure unit tests, no FS side effects outside `tmp_path`, one test file per module.

### Integration Points
- Single edit site: `graphify/dedup.py:493` (the set comprehension) plus a top-of-file `from graphify.analyze import _iter_sources` import.
- Single test file: `tests/test_dedup.py` gains two new test functions.
- No changes to `export.py`, `report.py`, `serve.py`, `analyze.py`, or any `_PLATFORM_CONFIG` skill file. No CLI surface change. No new flags.

</code_context>

<specifics>
## Specific Ideas

- The patch must accept extractions where the SAME edge group contains a mix of scalar and list-shaped `source_file` values across its members — `_iter_sources` flattens both transparently into the accumulator set.
- The fix must be idempotent: a second `--dedup --dedup-cross-type` pass over already-deduped output must succeed and be a no-op on shape (D-05.2).
- The fix must NOT change the merged output shape: scalar-when-1, sorted-list-when-≥2, empty-string-when-0 (D-04).

</specifics>

<deferred>
## Deferred Ideas

- **Sweep every `source_file` consumer in `dedup.py` and route through `_iter_sources` for symmetry** — discussed under "Fix surface area" option 3; declined as scope creep beyond DEDUP-01. If a future phase wants it, file as a refactor task.
- **Promote `_iter_sources` to a shared `graphify/_shape.py` or `graphify/types.py` module** — discussed under "Helper choice" option 3; declined for this phase as larger-than-bugfix. Could be revisited if v1.7+ adds more shape-aware code paths.
- **Always emit `list[str]` for uniform downstream consumption** — discussed under "Output shape contract" option 2; declined as breaking-change scope creep. Would require touching every reader. Not on the v1.6 roadmap.
- **Export-consumer smoke test piping merged extraction through `to_obsidian` / `to_html` / `to_json`** — discussed under "Regression test shape" option 3; declined as redundant with existing per-module tests that already use `_iter_sources`.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-dedup-source-file-list-handling-fix*
*Context gathered: 2026-04-27*
