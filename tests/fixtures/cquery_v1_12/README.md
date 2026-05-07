# Frozen v1.12 Fixture — CQUERY-02 Byte-Identity Oracle

**DO NOT regenerate.** This fixture is hand-curated and committed verbatim.
It is the byte-identity oracle for `_run_concept_code_hops` under the v1.12
contract: when **all new CQUERY parameters are omitted (None / unset)**, the
function must produce output that is byte-equal to `golden_concept_code_hops.json`.

## Files

- `graph.json` — Tiny v1.12-shaped NetworkX `node_link_data` graph (7 nodes,
  7 edges) covering `implements` / `documents` / `tests` / `imports` / `calls`
  edges with `confidence_score` values across all three bands
  (high `>=0.8`, medium `0.5..0.8`, low `<0.5`). Carries `schema_version: "1.12"`
  and `cache_version: "1.12"` per the Phase 65 cache contract so the fixture
  cannot silently drift.
- `golden_concept_code_hops.json` — Captured output of `_run_concept_code_hops`
  invoked against `graph.json` with **only** `entity` set. Stored as a
  structured envelope:
  - `text_body` — the markdown layer-1 narrative
  - `meta` — the parsed JSON meta envelope
  - `_invocation` — the exact arguments used, plus the sentinel string used
    to splice text and meta into the wire format

## Exact invocation that produced `golden_concept_code_hops.json`

```python
import json
from networkx.readwrite import json_graph
from graphify.serve import _run_concept_code_hops, QUERY_GRAPH_META_SENTINEL

with open("tests/fixtures/cquery_v1_12/graph.json") as f:
    data = json.load(f)
G = json_graph.node_link_graph(data, edges="links")

arguments = {"entity": "Authentication"}   # legacy v1.12 — no relations / max_hops / direction
result_str = _run_concept_code_hops(G, {}, arguments)

text_body, _, meta_json = result_str.partition(QUERY_GRAPH_META_SENTINEL)
meta = json.loads(meta_json)
```

The seed concept resolves to `concept_auth` via case-insensitive label match.

## Wave-2 / Plan 04 contract

`Plan 67-04` will load both files and assert:

```python
assert text_body == golden["text_body"]
assert meta == golden["meta"]
```

If either equality fails, `_run_concept_code_hops` has drifted from the v1.12
legacy path. That is a CQUERY-02 regression unless the change is intentional.

## When (and only when) to regenerate

If the v1.12 legacy path of `_run_concept_code_hops` is **explicitly bumped**
in a future phase (with documented rationale and a contract-version bump),
a human MUST update this fixture in the same commit, with the rationale in
the commit body. Never auto-regenerate.
