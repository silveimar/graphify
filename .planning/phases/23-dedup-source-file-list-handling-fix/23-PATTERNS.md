# Phase 23: Dedup `source_file` List-Handling Fix - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 2 (1 source, 1 test)
**Analogs found:** 2 / 2 (both exact, in-file analogs)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/dedup.py` (modify ~line 493 + 1 import) | service / pipeline-stage | transform (set-fold over edge groups) | `graphify/dedup.py:445-459` (node merge block) | exact (same file, same operation, opposite path) |
| `tests/test_dedup.py` (add 2 tests) | test | request-response (call `dedup()` → assert) | `tests/test_dedup.py:266-282` (`test_provenance_fields`) and `:286-310` (`test_cross_source_graph04_acceptance`) | exact (same module, same encoder, same cross_type invocation) |

## Pattern Assignments

### `graphify/dedup.py` (service, transform — edges merge fix at line 493)

**Analog:** `graphify/dedup.py:445-459` (node merge block — hardened in v1.3 IN-06, memory observation 918). This is the **canonical in-file template**: same function, same shape contract, same set-fold pattern. The edges path must mirror it — but using `_iter_sources` per locked decision D-01 (Plan 18-01 carry-forward).

**Imports pattern** (verbatim, `dedup.py:10-35`):
```python
from __future__ import annotations

import difflib
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
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

**Insertion slot for new import** — alphabetical within the local-imports block (`analyze` < `security`). Insert immediately above the existing `from graphify.security ...` line (currently `dedup.py:35`):

```python
from graphify.analyze import _iter_sources
from graphify.security import sanitize_label, sanitize_label_md
```

**Cross-module import style for `_iter_sources`** (matches existing usage):
- `graphify/serve.py:19` — `from graphify.analyze import _iter_sources`
- `graphify/vault_promote.py:37` — `from graphify.analyze import god_nodes, knowledge_gaps, _iter_sources`

Both use a top-of-file `from graphify.analyze import _iter_sources`. Match this style — no lazy/inline import.

**Core pattern — node merge block** (verbatim, `dedup.py:445-459`, the v1.3 IN-06 hardened analog):
```python
# Merge source_file (str -> list[str]) using a set for O(1) dedup.
# WRITE SITE: canonical nodes end up with source_file: list[str] when ≥2
# distinct sources contributed. All downstream READ sites in analyze.py,
# report.py, and export.py MUST use graphify.analyze._iter_sources() /
# _fmt_source_file() to handle both str and list[str] shapes correctly.
existing = canon.get("source_file", "")
sf_set: set[str] = set(existing) if isinstance(existing, list) else ({existing} if existing else set())
incoming = node.get("source_file", "")
if isinstance(incoming, list):
    sf_set.update(s for s in incoming if s)
elif incoming:
    sf_set.add(incoming)
# Normalize: single string if only one entry, else sorted list (output is
# sorted regardless of insertion order, so set-based folding is safe)
canon["source_file"] = sorted(sf_set) if len(sf_set) > 1 else (next(iter(sf_set)) if sf_set else "")
```

**Bug site — edges merge block before fix** (verbatim, `dedup.py:481-500`):
```python
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
    sf_set = {e["source_file"] for e in group if e.get("source_file")}   # ← BUG line 493
    if len(sf_set) > 1:
        merged["source_file"] = sorted(sf_set)
    elif sf_set:
        merged["source_file"] = next(iter(sf_set))
    merged_edges.append(merged)
```

**Patch shape (D-03 + D-04 compliant)** — replace line 493's set comprehension with a flatten-then-fold using `_iter_sources`. Lines 494-497 stay structurally identical. Optional explicit `else: merged["source_file"] = ""` mirrors the node-path contract at line 459 (RESEARCH.md "Open Questions" — recommendation: include for symmetry).

**Shape contract (preserve verbatim)** — node-path line 459 is the canonical reference:
- `len(sf_set) > 1` → `sorted(sf_set)` (sorted unique `list[str]`)
- `sf_set` non-empty (exactly 1) → `next(iter(sf_set))` (scalar `str`)
- `sf_set` empty → `""` (empty string, per node-path symmetry)

---

### `tests/test_dedup.py` (test, request-response)

**Analog 1:** `tests/test_dedup.py:266-282` (`test_provenance_fields`) — same encoder, same dict-literal fixture style, same `isinstance(canon["source_file"], list)` assertion idiom.

**Analog 2:** `tests/test_dedup.py:286-310` (`test_cross_source_graph04_acceptance`) — exact `cross_type=True` + `embed_threshold=0.85` + `_forced_merge_encoder` invocation pattern (matches the cross_type call signature researcher noted at line 145).

**Encoder fixture pattern** (verbatim, `tests/test_dedup.py:22-29`):
```python
def _forced_merge_encoder(labels: list[str]) -> np.ndarray:
    """Encoder that returns the SAME vector for every label, forcing cosine=1.0.

    Use in tests that want to isolate the fuzzy gate (all pairs pass cosine).
    """
    vec = np.ones(384, dtype=np.float32)
    vec /= np.linalg.norm(vec)
    return np.array([vec for _ in labels])
```

**Cross-type invocation pattern** (verbatim, `tests/test_dedup.py:144-146`):
```python
result, report = dedup(extraction, encoder=_forced_merge_encoder,
                        cross_type=True, embed_threshold=0.85)
```

**Provenance/shape assertion idiom** (verbatim, `tests/test_dedup.py:266-282`):
```python
def test_provenance_fields():
    """D-11: canonical node has source_file list + merged_from list."""
    extraction = {
        "nodes": [
            {"id": "a", "label": "AuthService", "file_type": "code", "source_file": "a.py"},
            {"id": "b", "label": "auth_service", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [],
    }
    result, _ = dedup(extraction, encoder=_forced_merge_encoder)
    canon = result["nodes"][0]
    assert "merged_from" in canon
    assert isinstance(canon["merged_from"], list)
    assert len(canon["merged_from"]) == 1
    assert isinstance(canon["source_file"], list)
    assert set(canon["source_file"]) == {"a.py", "b.py"}
```

**List-shape multi-source assertion idiom** (verbatim, `tests/test_dedup.py:303-310`):
```python
auth_canonicals = [
    n for n in result["nodes"]
    if isinstance(n.get("source_file"), list) and len(n["source_file"]) >= 3
]
assert len(auth_canonicals) >= 1, (
```

**Test patterns to apply for the two new functions:**
- Plain `def test_*()` functions (no class wrappers, no extra fixtures).
- Inline dict-literal extractions with `nodes` + `edges` keys.
- Edges include `source`, `target`, `relation`, `confidence`, `source_file`, `weight`.
- Call `dedup(extraction, encoder=_forced_merge_encoder, cross_type=True, embed_threshold=0.85)`.
- Tuple unpack `result, _ = dedup(...)` (or `result, report` if asserting on report).
- Assertions: direct `dict` access, `isinstance(..., list)`, `set(...)` for unordered, `sorted(...)` or literal-list for ordered.

## Shared Patterns

### `_iter_sources` import + use (cross-module canonical)
**Source:** `graphify/analyze.py:11-29`
**Apply to:** `graphify/dedup.py` (the only file modified this phase)

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

Existing import sites (style template):
- `graphify/serve.py:19` → `from graphify.analyze import _iter_sources`
- `graphify/vault_promote.py:37` → `from graphify.analyze import god_nodes, knowledge_gaps, _iter_sources`

New site uses the simpler single-symbol form (matches `serve.py`):
```python
from graphify.analyze import _iter_sources
```

### Output-shape contract (write side, dedup.py)
**Source:** `graphify/dedup.py:459` (node path — already correct)
**Apply to:** the new edges-path patch at line 493

```python
# canonical three-branch normalization:
# >1  → sorted(list)
# ==1 → scalar str
# ==0 → empty str
sorted(sf_set) if len(sf_set) > 1 else (next(iter(sf_set)) if sf_set else "")
```

The edges path may keep its existing if/elif structure (lines 494-497) and add an explicit `else: merged["source_file"] = ""`, OR collapse to the one-liner above. Both are D-04 compliant.

### Test conventions (per CLAUDE.md + tests/test_dedup.py existing style)
**Source:** `tests/test_dedup.py` (entire file, 408 lines of consistent style)
**Apply to:** the two new test functions

- Pure unit tests, no FS side effects (no `tmp_path` needed for these two cases).
- Use `_forced_merge_encoder` (already defined in the file at line 22) to bypass cosine gate variance.
- Use `cross_type=True, embed_threshold=0.85` for cross-type invocations.
- Inline dict fixtures (no JSON files).
- One docstring line referencing the requirement ID (DEDUP-01 / DEDUP-03).

## No Analog Found

None. Both files have strong in-codebase analogs (the node-merge block for the fix, and `test_provenance_fields` + `test_cross_source_graph04_acceptance` for the new tests).

## Metadata

**Analog search scope:** `graphify/dedup.py` (lines 1-40, 440-505), `graphify/analyze.py` (line 11), `graphify/serve.py` (line 19), `graphify/vault_promote.py` (line 37), `tests/test_dedup.py` (lines 20-30, 130-160, 260-310).
**Files scanned:** 5 (kept tightly scoped per orchestrator instructions — "tightly scoped bugfix").
**Pattern extraction date:** 2026-04-27
