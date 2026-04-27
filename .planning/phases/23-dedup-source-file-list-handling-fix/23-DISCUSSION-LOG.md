# Phase 23: Dedup `source_file` List-Handling Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 23-dedup-source-file-list-handling-fix
**Areas discussed:** Helper choice, Fix surface area, Output shape contract, Regression test shape

---

## Helper Choice

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `_iter_sources` | Import `graphify.analyze._iter_sources` into `dedup.py`. Single source of truth, matches Plan 18-01 carry-forward, satisfies `dedup.py:448`'s own comment. | ✓ |
| Add `_sf_flatten` in `dedup.py` | New module-private helper with identical semantics. Avoids cross-module import but duplicates flattening logic. | |
| Promote `_iter_sources` to a shared spot | Move out of `analyze.py` into a new `graphify/_shape.py` or `graphify/types.py`. Cleanest long-term but expands diff well beyond a bugfix. | |

**User's choice:** Reuse `_iter_sources` (recommended).
**Notes:** Aligns with the locked carry-forward from Plan 18-01 (STATE.md): `source_file: str | list[str]` handling delegates to `analyze._iter_sources`, never inline `isinstance` checks. The `_sf_flatten` name from PROJECT.md was shorthand, not a design directive — REQUIREMENTS.md doesn't mention it.

---

## Fix Surface Area

| Option | Description | Selected |
|--------|-------------|----------|
| Edges path only | Patch only line 493 (the actual crash site). Node path at 445-459 was already hardened in v1.3 (memory obs 918). Pair with idempotency regression test. | ✓ |
| Edges + audit-pass on nodes | Patch line 493 AND refactor node block at 445-459 to also call `_iter_sources` for symmetry, even if not strictly broken. | |
| Sweep every `source_file` consumer in `dedup.py` | Audit all `source_file` references in `dedup.py` (lines 414, 418, 445-459, 493, 526) and route every read through `_iter_sources`. | |

**User's choice:** Edges path only (recommended).
**Notes:** Surgical, minimal diff. The node path was already fixed in v1.3 IN-06; touching it would be re-work. Idempotency test covers the regression vector that caused Issue #4.

---

## Output Shape Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve current contract | Sorted unique `list[str]` when ≥2 contributors, scalar `str` when exactly 1, empty `str` when none. Matches DEDUP-02 verbatim. Zero downstream churn. | ✓ |
| Always emit `list[str]` | Even single-contributor edges get `["file.py"]`. Simpler invariant downstream but violates DEDUP-02's literal wording AND would touch every consumer's scalar fast path. | |
| Always emit scalar (join with separator) | Collapse multi-source to a single string like `"a.py;b.py"`. Loses structured info, breaks `_iter_sources` contract everywhere. Not viable. | |

**User's choice:** Preserve current contract (recommended).
**Notes:** Matches DEDUP-02 literal wording, mirrors the node path at line 459, avoids any downstream churn. A shape change would be a breaking change masquerading as a bugfix.

---

## Regression Test Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Spec-minimum + idempotency | Two cases: (1) DEDUP-03 fixture with pre-merged `list[str]` `source_file` edges, asserts no `TypeError` + correct merge shape; (2) idempotency — run dedup twice, assert no-op + no crash. | ✓ |
| Spec-minimum only | Just the DEDUP-03 fixture. Smallest test diff. Trusts idempotency is implicit. | |
| Spec-minimum + idempotency + export consumer smoke | All of the above PLUS pipe merged extraction through `to_obsidian` / `to_html` / `to_json`. Most thorough but redundant with existing per-module tests. | |
| Spec-minimum + mixed scalar/list inputs | DEDUP-03 fixture PLUS a fixture mixing scalar and list `source_file` in the same edge group. | |

**User's choice:** Spec-minimum + idempotency (recommended).
**Notes:** The idempotency test directly exercises the regression vector — dedup output (`list[str]`) is valid dedup input but the edge path didn't accept it. Mixed scalar/list is implicitly covered if `_iter_sources` flattens both correctly.

---

## Claude's Discretion

- Exact placement of the `_iter_sources` import in `dedup.py` (top-of-file vs lazy import). Default: top-of-file, matches `vault_promote.py` and `serve.py` style.
- Naming/location of the two new test functions in `tests/test_dedup.py`.
- Whether to add a one-line code comment at the patched site referencing Issue #4 / DEDUP-01 (default: yes, brief).

## Deferred Ideas

- Sweep every `source_file` consumer in `dedup.py` and route through `_iter_sources` for symmetry (declined as scope creep beyond DEDUP-01).
- Promote `_iter_sources` to a shared `graphify/_shape.py` or `graphify/types.py` module (declined as larger-than-bugfix; revisit in v1.7+ if needed).
- Always emit `list[str]` for uniform downstream consumption (declined as breaking-change scope creep; not on v1.6 roadmap).
- Export-consumer smoke test piping merged extraction through `to_obsidian` / `to_html` / `to_json` (declined as redundant with existing per-module tests).
