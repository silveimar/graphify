# Phase 23: Dedup `source_file` List-Handling Fix - Research

**Researched:** 2026-04-27
**Domain:** Bug fix in `graphify/dedup.py` edge-merge path (cross-type dedup)
**Confidence:** HIGH

## Summary

Single-line bug in `graphify/dedup.py:493` where the edges-merge set comprehension
`{e["source_file"] for e in group if e.get("source_file")}` raises
`TypeError: unhashable type: 'list'` when an input edge already carries a `list[str]`
`source_file` (an idempotency case that arises naturally on a second `--dedup` pass,
or when consumers feed in pre-merged extractions). The node-merge path in the same
file (lines 445-459) already handles both `str` and `list[str]` correctly via a guarded
set fold — it was hardened in v1.3 IN-06 [VERIFIED: dedup.py:447-459]. The edges path
was never updated.

The fix is to route each edge's `source_file` through `graphify.analyze._iter_sources`
(which normalizes `str | list[str] | None` → `list[str]`) before set-based folding,
preserving the existing output-shape contract: scalar `str` for one contributor, sorted
`list[str]` for ≥ 2, empty `str` for none [VERIFIED: dedup.py:497-500, analyze.py:11-29].

**Primary recommendation:** Patch line 493 only. Add `from graphify.analyze import _iter_sources`
to dedup.py imports. Write two tests in `tests/test_dedup.py`: (1) DEDUP-03 spec case (cross-type
dedup on extraction with pre-existing `list[str]` edge `source_file`), (2) idempotency case
(run `dedup()` twice on the same input, second pass must not raise and must produce stable
shape). No other call sites need changing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEDUP-01 | `--dedup --dedup-cross-type` no longer crashes with `TypeError: unhashable type: 'list'` on extractions with list-form edge `source_file` | Root cause confirmed at `dedup.py:493`. Fix routes through `_iter_sources` which accepts `list[str]` [VERIFIED: dedup.py:493, analyze.py:11-29] |
| DEDUP-02 | Merged edge `source_file` is sorted unique union (≥ 2 contributors) or scalar (1 contributor) | Existing output-shape branch at `dedup.py:497-500` is preserved by the patch [VERIFIED: dedup.py:497-500] |
| DEDUP-03 | Regression test in `tests/test_dedup.py` exercises cross-type path on fixture with pre-merged `list[str]` edge `source_file`, asserts no exception + correct shape | Test patterns documented below; fixtures use plain dict literals with `_forced_merge_encoder` and `cross_type=True` [VERIFIED: tests/test_dedup.py:135-150, 286-310] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** (CI runs 3.10 and 3.12). Use `str | None` style hints, `from __future__ import annotations`.
- **No new required dependencies.** Use stdlib only. (Patch needs no new deps — `_iter_sources` is internal.)
- **Backward compatible.** Output shape contract for `source_file` (scalar vs list) must be preserved.
- **Pure unit tests.** No network, no filesystem outside `tmp_path`. Pattern matches existing `tests/test_dedup.py`.
- **No linter/formatter configured.** Match surrounding 4-space indentation and existing import order (stdlib → third-party → local).
- **Security:** No new external input — patch is internal data-shape handling. `security.py` rules unaffected.

## User Constraints (from CONTEXT.md additional_context)

### Locked Decisions

- **D-01:** Reuse `graphify.analyze._iter_sources`. Do NOT add a new `_sf_flatten` helper.
- **D-02:** Patch the edges path only at line 493. Node path at 445-459 is already hardened (v1.3 IN-06).
- **D-03:** Concrete patch shape: replace the `{e["source_file"] for e in group ...}` set comprehension with a flatten-then-set construction routing each edge's `source_file` through `_iter_sources`.
- **D-04:** Preserve current output-shape contract: sorted `list[str]` for ≥ 2 contributors, scalar `str` for exactly 1, empty `str` for 0.
- **D-05:** Two regression tests in `tests/test_dedup.py` — DEDUP-03 spec case + idempotency (run dedup twice).
- **D-06:** Do NOT add export-consumer smoke tests (redundant — export.py already uses `_fmt_source_file` which goes through `_iter_sources`).
- **D-07:** Do NOT add mixed scalar/list fixtures (implicit if `_iter_sources` works — it's already independently tested).

### Claude's Discretion

- Exact wording of test names and docstrings.
- Whether to express the patch as a small inline expression or a tiny local variable for readability — both are acceptable as long as D-03 / D-04 hold.
- Position of the new import within the existing local-import block.

### Deferred Ideas (OUT OF SCOPE)

- Adding a generic `_sf_flatten` helper inside dedup.py (D-01 forbids).
- Refactoring node path at 445-459 to also go through `_iter_sources` (D-02 — already correct, scope creep).
- Export-consumer smoke tests (D-06).
- Mixed-shape fuzz fixtures (D-07).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Edge merge `source_file` shape normalization | `graphify/dedup.py` (Build layer, edges path) | `graphify/analyze.py` (`_iter_sources` reused) | dedup.py owns merge; analyze.py owns the canonical normalizer per Plan 18-01 lock |
| Regression test coverage | `tests/test_dedup.py` | `tests/conftest.py` (`fake_encoder`, `_forced_merge_encoder`) | Existing convention: one test file per module |

## Standard Stack

No new libraries. The patch uses only:

| Symbol | Source | Purpose |
|--------|--------|---------|
| `_iter_sources` | `graphify.analyze` | Normalize `str | list[str] | None` → `list[str]` [VERIFIED: analyze.py:11-29] |
| `sorted`, `set`, `next`, `iter` | stdlib | Existing folding pattern |
| `pytest`, `numpy` | already in `tests/test_dedup.py` | Test infra |
| `_forced_merge_encoder` | `tests/test_dedup.py` (existing) | Force every candidate pair through fuzzy + cosine gates [VERIFIED: tests/test_dedup.py:22-29] |
| `fake_encoder` | `tests/conftest.py` | Deterministic mock encoder for non-forced cases [VERIFIED: conftest.py:12-27] |

## Architecture: Existing Code Block (line 478-500)

The function being patched is `_merge_extraction` in `graphify/dedup.py`. The relevant block (verbatim, line numbers from current file):

```python
# Lines 481-500
merged_edges: list[dict] = []
for _, group in edge_groups.items():
    if len(group) == 1:
        merged_edges.append(group[0])
        continue
    merged = dict(group[0])
    merged["weight"] = sum(e.get("weight", 1.0) for e in group)
    merged["confidence_score"] = max(
        (e.get("confidence_score", 0.0) for e in group), default=0.0
    )
    merged["confidence"] = max(
        group,
        key=lambda e: CONFIDENCE_ORDER.get(e.get("confidence", "AMBIGUOUS"), 0),
    )["confidence"]
    sf_set = {e["source_file"] for e in group if e.get("source_file")}   # ← BUG: line 493
    if len(sf_set) > 1:
        merged["source_file"] = sorted(sf_set)
    elif sf_set:
        merged["source_file"] = next(iter(sf_set))
    merged_edges.append(merged)
```

**The bug:** when any `e["source_file"]` is `list[str]` (legal per the dedup output schema — see node path at 445-459 which produces lists), the set comprehension fails because lists are unhashable.

**The fix shape (D-03 compliant):**

```python
sf_set: set[str] = set()
for e in group:
    sf_set.update(_iter_sources(e.get("source_file")))
if len(sf_set) > 1:
    merged["source_file"] = sorted(sf_set)
elif sf_set:
    merged["source_file"] = next(iter(sf_set))
else:
    merged["source_file"] = ""
```

(The `else` branch makes the empty-case explicit and matches the node-path contract at line 459. The original code left `source_file` whatever `dict(group[0])` carried in the empty case; preserving the empty-string contract per D-04 is safer for downstream consumers. Planner may choose to omit the `else` if strict line-count minimization is preferred — both are valid; current callers tolerate either, but matching the node path is cleaner.)

## Import Layout (graphify/dedup.py)

Existing import order [VERIFIED: dedup.py:11-35]:

```python
from __future__ import annotations

import difflib
import hashlib
# ... stdlib ...
from typing import Any, Callable

import networkx as nx

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

from graphify.security import sanitize_label, sanitize_label_md
```

**Add** the new import next to the existing local import:

```python
from graphify.analyze import _iter_sources
from graphify.security import sanitize_label, sanitize_label_md
```

(Alphabetical order within the local-imports block; analyze < security.)

## `_iter_sources` Signature Confirmation

Verified at `graphify/analyze.py:11-29` [VERIFIED]:

```python
def _iter_sources(source_file: "str | list[str] | None") -> list[str]:
    if not source_file:
        return []
    if isinstance(source_file, str):
        return [source_file]
    if isinstance(source_file, list):
        return [s for s in source_file if isinstance(s, str) and s]
    return []
```

Handles:
- `None` → `[]`
- `""` (empty str) → `[]` (caught by `if not source_file`)
- `"a.py"` → `["a.py"]`
- `["a.py", "b.py"]` → `["a.py", "b.py"]`
- `["", "a.py", None]` → `["a.py"]` (filters non-str and empty)
- Any other type (dict, int, etc.) → `[]` (defensive)

This is exactly the defensive surface needed. No additional helper required.

## `--dedup-cross-type` Code Path

[VERIFIED: dedup.py:53-115] The CLI flag maps to the keyword arg `cross_type: bool = False` of `dedup()`. When `cross_type=True`:

- Cross-`file_type` candidate pairs bypass the fuzzy gate (`_candidate_pairs` at lines 263-310).
- They still go through the cosine gate (`_apply_embedding_gate`).
- Surviving pairs enter union-find → `_merge_extraction` → the buggy edge merge.

**Is the bug also reachable via plain `--dedup` (no cross-type)?** Yes — any time at least two edges with the same `(new_src, new_tgt, relation)` key get grouped, and any of those edges carries a `list[str]` `source_file`, the comprehension crashes. Cross-type just makes it more likely because it produces more cross-source merges. The DEDUP-03 test should still focus on the cross-type path (per requirement wording), but the fix itself benefits both.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Normalize `source_file` shape (str vs list vs None) | Local `_sf_flatten` helper inside dedup.py | `graphify.analyze._iter_sources` | D-01 lock; Plan 18-01 already canonicalized this helper as the single source of truth (per STATE.md 2026-04-20 entry) |
| Test mock encoder | New encoder | `_forced_merge_encoder` (tests/test_dedup.py:22) and `fake_encoder` fixture (conftest.py:12) | Existing patterns proven across 20+ tests |

## Test Conventions (tests/test_dedup.py)

[VERIFIED: tests/test_dedup.py:1-310]

- **Style:** plain pytest functions, no class wrappers, no fixtures beyond `fake_encoder` / `tmp_path`.
- **Fixtures:** in-line dict literals for extractions. `nodes` and `edges` lists with the standard schema.
- **Cross-type invocation:** programmatic via `dedup(extraction, encoder=_forced_merge_encoder, cross_type=True, embed_threshold=0.85)`. Not via CLI subprocess. [VERIFIED: tests/test_dedup.py:145, 296]
- **Existing list-shape coverage:** `test_provenance_fields` (line 266) asserts `isinstance(canon["source_file"], list)` for the **node** path. `test_cross_source_graph04_acceptance` (line 286) asserts a node-side list with `>= 3` entries. **No existing test covers `list[str]` on the edges path** — that is exactly the gap DEDUP-03 fills.
- **Assertion style:** direct dict access (`canon["source_file"]`), `set(...)` comparisons for unordered checks, `sorted(...)` checks where ordering is the contract.

### Test 1 (DEDUP-03 spec case) — sketch

```python
def test_cross_type_merges_edges_with_list_source_file():
    """DEDUP-01/03: edges carrying list[str] source_file (from prior dedup pass)
    must not crash the cross-type merge and must produce sorted unique union."""
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code",   "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "document", "source_file": "b.md"},
            {"id": "h",  "label": "handler",     "file_type": "code",   "source_file": "c.py"},
        ],
        "edges": [
            # NOTE: source_file is already a list[str] — the failure mode from Issue #4
            {"source": "a1", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": ["a.py", "x.py"], "weight": 1.0},
            {"source": "a2", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.md", "weight": 1.0},
        ],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder,
                     cross_type=True, embed_threshold=0.85)
    # Both edges collapse to one after node merge → merged source_file is sorted union
    merged = [e for e in result["edges"] if e["target"] == "h"]
    assert len(merged) == 1
    assert merged[0]["source_file"] == ["a.py", "b.md", "x.py"]
```

### Test 2 (idempotency) — sketch

```python
def test_dedup_is_idempotent_on_list_source_file():
    """DEDUP-01: running dedup twice must not raise; second pass is stable."""
    extraction = {
        "nodes": [
            {"id": "a1", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "a2", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
            {"id": "h",  "label": "handler",     "file_type": "code", "source_file": "c.py"},
        ],
        "edges": [
            {"source": "a1", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py", "weight": 1.0},
            {"source": "a2", "target": "h", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "b.py", "weight": 1.0},
        ],
    }
    pass1, _ = dedup(extraction, encoder=_forced_merge_encoder, embed_threshold=0.85)
    # pass1 now has at least one edge with source_file: list[str]
    pass2, _ = dedup(pass1, encoder=_forced_merge_encoder, embed_threshold=0.85)  # must not raise
    # Shapes preserved
    for e in pass2["edges"]:
        sf = e.get("source_file", "")
        assert isinstance(sf, (str, list))
        if isinstance(sf, list):
            assert sf == sorted(sf)
            assert len(sf) == len(set(sf))
```

## Risk Surface — Downstream Consumers

[VERIFIED via grep] Downstream readers of edge `source_file`:

| Consumer | Read Site | Shape Tolerance | Risk |
|----------|-----------|-----------------|------|
| `graphify/export.py:382` | `_fmt_source_file(data.get("source_file", ""))` | Already handles str/list via `_fmt_source_file` (which uses `_iter_sources`) | None |
| `graphify/export.py:718` | Same `_fmt_source_file` path | Same | None |
| `graphify/serve.py:873` | `_iter_sources(data.get("source_file"))` | Native handling | None |
| `graphify/vault_promote.py` (4 sites) | `_iter_sources(...)` | Native handling | None |
| `graphify/build.py` | Reads edges into NetworkX as opaque attributes | Stores any value; no shape assumption | None |

The fix preserves the existing scalar-fast-path (D-04), so no consumer that depends on `isinstance(sf, str)` will regress.

## Common Pitfalls

### Pitfall 1: Forgetting the empty-set branch
**What goes wrong:** If all edges in a group lack `source_file`, the original code skipped writing the field, so `merged["source_file"]` retained whatever `dict(group[0])` had (likely already missing or `""`). Be explicit in the patch.
**How to avoid:** Either retain the original three-branch structure (`> 1` / `>= 1` / no else) or add the explicit `else: merged["source_file"] = ""` to match the node-path contract at line 459.

### Pitfall 2: Sort ordering surprise
**What goes wrong:** `sorted(sf_set)` is alphabetical, not insertion order. Existing node-path uses the same — preserve it. DEDUP-02 spec says "sorted unique union."
**How to avoid:** Test 1 above asserts the exact sorted order `["a.py", "b.md", "x.py"]`.

### Pitfall 3: Test using non-cross-type encoder
**What goes wrong:** `fake_encoder` (default) returns orthogonal-ish vectors per label — pairs may not pass the cosine gate, so no merge happens, so the bug isn't exercised.
**How to avoid:** Use `_forced_merge_encoder` and `cross_type=True` + `embed_threshold=0.85` (matches existing test pattern at line 145).

## Code Examples

Verified patterns from the existing codebase:

### Cross-type dedup invocation
```python
# Source: tests/test_dedup.py:142-145
result, report = dedup(extraction, encoder=_forced_merge_encoder,
                       cross_type=True, embed_threshold=0.85)
```

### Hardened set fold (node path — model for the edges fix)
```python
# Source: graphify/dedup.py:449-459 (the v1.3 IN-06 hardening)
existing = canon.get("source_file", "")
sf_set: set[str] = set(existing) if isinstance(existing, list) else ({existing} if existing else set())
incoming = node.get("source_file", "")
if isinstance(incoming, list):
    sf_set.update(s for s in incoming if s)
elif incoming:
    sf_set.add(incoming)
canon["source_file"] = sorted(sf_set) if len(sf_set) > 1 else (next(iter(sf_set)) if sf_set else "")
```

The edges-path fix is morally equivalent but uses `_iter_sources` (D-01) for brevity.

## Runtime State Inventory

Not applicable — this is a code bug fix, not a rename/refactor/migration. No stored data, live config, OS state, secrets, or build artifacts are affected.

## Environment Availability

Not applicable — pure code change with no new external dependencies. Existing test infrastructure (`pytest`, `numpy`, `fake_encoder`) is already installed for any contributor running `pip install -e ".[all]"`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in dev dependencies) |
| Config file | none — pytest defaults; tests live under `tests/` |
| Quick run command | `pytest tests/test_dedup.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEDUP-01 | Cross-type dedup does not raise on list-shaped edge source_file | unit | `pytest tests/test_dedup.py::test_cross_type_merges_edges_with_list_source_file -x` | ❌ Wave 0 (new test) |
| DEDUP-01 (idempotency facet) | Second dedup pass on already-dedup'd extraction does not raise | unit | `pytest tests/test_dedup.py::test_dedup_is_idempotent_on_list_source_file -x` | ❌ Wave 0 (new test) |
| DEDUP-02 | Merged edge source_file is sorted unique union (≥2) or scalar (1) | unit | covered by both tests above (assert exact shape) | ❌ Wave 0 |
| DEDUP-03 | Regression coverage for cross-type list-shaped source_file | unit | `pytest tests/test_dedup.py::test_cross_type_merges_edges_with_list_source_file -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_dedup.py -q` (~1-2 s)
- **Per wave merge:** `pytest tests/test_dedup.py tests/test_dedup_pipeline.py tests/test_export.py -q` (sanity for adjacent code)
- **Phase gate:** `pytest tests/ -q` full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dedup.py` — append two new test functions (`test_cross_type_merges_edges_with_list_source_file`, `test_dedup_is_idempotent_on_list_source_file`)
- [ ] No new fixtures needed (`_forced_merge_encoder` and inline dicts cover both cases)
- [ ] No framework install needed — pytest + numpy already in dev dependencies

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal data normalization |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes (defensive) | `_iter_sources` filters non-str list members and empty strings, defending against malformed extraction input |
| V6 Cryptography | no | n/a |

### Threat Patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Malformed `source_file` (non-list, non-str) crashing dedup | Denial of service via crafted input | `_iter_sources` returns `[]` for unknown types — fail-soft, no crash |
| Label injection via list-shaped `source_file` reaching HTML export | Tampering | Already handled downstream by `sanitize_label(_fmt_source_file(...))` in export.py:382 |

No new attack surface introduced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | All claims verified against current source files or cited from CONTEXT.md/REQUIREMENTS.md |

## Open Questions

None blocking. One stylistic choice the planner may resolve:

1. **Explicit empty-`else` branch?** The current buggy code has no `else` — when `sf_set` is empty, `merged["source_file"]` stays as inherited from `dict(group[0])`. The node path (line 459) writes `""` explicitly. Recommendation: add the explicit `else: merged["source_file"] = ""` for symmetry with the node path; the empty case is rare in practice (caught by the `if e.get("source_file")` filter in the original) so this is a clean-up rather than a behavior fix.

## Sources

### Primary (HIGH confidence — verified in this session)
- `graphify/dedup.py` lines 1-40, 50-115, 430-520 — bug location, function signature, surrounding merge logic
- `graphify/analyze.py` lines 1-30 — `_iter_sources` signature and behavior
- `tests/test_dedup.py` lines 1-310 — test patterns, encoders, cross-type invocation conventions
- `tests/conftest.py` lines 1-40 — `fake_encoder` fixture
- `graphify/export.py`, `graphify/serve.py`, `graphify/vault_promote.py` — downstream consumer audit (grep)
- `.planning/REQUIREMENTS.md` lines 13-15, 60-62 — DEDUP-01/02/03 requirement text

### Secondary
- `./CLAUDE.md` — project conventions (Python 3.10+, no formatter, test patterns)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — only stdlib + existing internal helper, all verified by direct read
- Architecture: HIGH — bug location + fix shape + import layout all verified in source
- Pitfalls: HIGH — derived from existing code patterns and the v1.3 IN-06 node-path precedent

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable internal code path; no external dependency churn risk)
