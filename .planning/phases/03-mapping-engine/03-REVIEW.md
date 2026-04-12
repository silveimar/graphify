---
status: issues_found
phase: 3
slug: 03-mapping-engine
depth: standard
files_reviewed: 6
reviewed_at: 2026-04-11
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
---

# Phase 3: Code Review Report

**Depth:** standard
**Files Reviewed:** 6

- `graphify/__init__.py`
- `graphify/mapping.py`
- `graphify/profile.py`
- `tests/fixtures/template_context.py`
- `tests/test_mapping.py`
- `tests/test_profile.py`

## Summary

Phase 3's mapping engine is implemented carefully and the scrutiny-area checklist in the phase context has been honored:

- All 11 matcher kinds dispatch correctly in `_match_when`, with bool-before-int guards, non-string attribute safety, and ReDoS length caps (`_MAX_PATTERN_LEN=512`, `_MAX_CANDIDATE_LEN=2048`).
- `_detect_dead_rules` is conservative and correctly gated on same matcher kind + same `note_type` (no cross-kind false positives).
- `_nearest_host` tie-break order (count desc → size desc → cid asc) is implemented correctly.
- `_build_sibling_labels` properly filters to god nodes only, and the D-60 regression test `test_sibling_labels_empty_for_non_god_node` pins the contract so removing the gate in `_assemble_communities` would fail the test.
- `_assemble_communities` handles the `-1` bucket MOC sentinel and the tiny-corpus edge case (`not above_cids`) correctly.
- `cohesion` is wrapped with `float()` at every write site per WR-06.
- The `validate_rules` delegation via function-local import in `profile.py` is correct and breaks the `mapping → templates → profile` cycle.
- `graphify/__init__.py` entries for `classify`, `MappingResult`, and `validate_rules` follow the existing lazy-import pattern and are covered by `test_graphify_package_lazy_exports_classify` and `test_graphify_classify_is_graphify_mapping_classify`.
- The Phase 2 ↔ Phase 3 contract round-trip tests exercise the full boundary.

Three warnings worth addressing before merge and a handful of minor info items follow.

## Warnings

### WR-01: `compile_rules` silently clobbers `_compiled_pattern` when a rule contains both `attr+regex` and `source_file_matches`

**File:** `graphify/mapping.py:87-107`

**Issue:** `compile_rules` walks two independent `if` branches that both write to the same `_COMPILED_KEY` on the when-dict:

```python
if "attr" in when and "regex" in when:
    ...
    new_when[_COMPILED_KEY] = re.compile(pat)
if "source_file_matches" in when:
    ...
    new_when[_COMPILED_KEY] = re.compile(pat)
```

If a malformed rule contains both matcher kinds (e.g. `{"attr": "label", "regex": "a", "source_file_matches": "b"}`), the second branch overwrites the first's compiled pattern. `classify()` calls `compile_rules(raw_rules)` directly without first invoking `validate_rules`, so an unvalidated profile can silently produce incorrect matches. `validate_rules` does reject "multiple matcher kinds" — but `classify()` does not depend on that guarantee, and defensive programming in `compile_rules` is cheap.

**Fix:** Short-circuit after compiling one pattern by using `elif`:

```python
if "attr" in when and "regex" in when:
    pat = when["regex"]
    if isinstance(pat, str) and len(pat) <= _MAX_PATTERN_LEN:
        try:
            new_when[_COMPILED_KEY] = re.compile(pat)
        except re.error:
            pass  # validate_rules will surface the error
elif "source_file_matches" in when:  # elif, not if
    ...
```

### WR-02: `_match_when` "in" matcher will crash when a node attribute is unhashable and `choices` is a set

**File:** `graphify/mapping.py:135-137`

**Issue:**
```python
if "in" in when:
    choices = when["in"]
    return isinstance(choices, (list, tuple, set)) and raw in choices
```

`validate_rules` restricts `when.in` to `list | tuple`, but `_match_when` *accepts* `set` in addition. If a caller bypasses validation (e.g. constructs `when` programmatically for a test or direct API usage) and passes a set, and a node attribute happens to be an unhashable value (a list, dict, or tuple containing unhashable items), `raw in choices` will raise `TypeError: unhashable type` — violating the "never raises" contract stated in the docstring.

**Fix:** Narrow the isinstance check to `(list, tuple)` to match `validate_rules`:

```python
if "in" in when:
    choices = when["in"]
    if not isinstance(choices, (list, tuple)):
        return False
    try:
        return raw in choices
    except TypeError:
        return False
```

### WR-03: `_kind_of("attr:?")` for attr rules missing an operator is not documented in the dead-rule skip list

**File:** `graphify/mapping.py:688-699`, `graphify/mapping.py:740-761`

**Issue:** `_kind_of` returns `"attr:?"` for an `attr` matcher with no `equals/in/contains/regex` key. `_is_shadowed("attr:?", ...)` falls through to `return False` — so no dead-rule warnings are produced. This is fine: such rules would be rejected by `validate_rules` and the dead-rule pass is gated on `if not errors:`. But the conservative-skip comment at lines 941–947 only lists `attr:contains`, `attr:regex`, and `source_file_matches` — `attr:?` should be documented too, and ideally an explicit early-return in `_is_shadowed` would make the intent unmistakable.

**Fix:** Add `attr:?` to the comment list and optionally:

```python
if kind == "attr:?":
    return False  # validation rejects attr without op; conservative skip
```

## Info

### IN-01: `god_nodes(top_n=0)` does not produce an empty god-node set as the profile semantics might suggest

**File:** `graphify/analyze.py:39-58` (called from `graphify/mapping.py:284`)

**Issue:** `validate_profile` accepts `top_n: 0`, but `god_nodes()` appends *before* checking `if len(result) >= top_n: break`. With `top_n=0`, the first iteration appends one node, then `1 >= 0` is True and breaks — so `top_n=0` produces *one* god node rather than zero. If a user sets `top_n: 0` intending "disable god-node promotion," they will still see the top-degree real node classified as "thing".

**Fix:** In `validate_profile`, reject `top_n < 1` with a pointed message, or guard the call site:

```python
# in classify()
god_list = god_nodes(G, top_n=top_n) if top_n > 0 else []
```

### IN-02: `classify()` recomputes `_node_community_map` and `community_sizes` inside `_assemble_communities`

**File:** `graphify/mapping.py:282-283` and `graphify/mapping.py:535-536`

**Issue:** `classify()` builds `node_to_community` and `community_sizes`, then `_assemble_communities` rebuilds them. Minor duplication, measurable only for very large graphs.

**Fix:** Pass the cached values via `_MatchCtx` or as additional parameters.

### IN-03: `above_cids` is a list used for O(N) membership checks in `_assemble_communities`

**File:** `graphify/mapping.py:538-540`, `graphify/mapping.py:662`

**Issue:** `above_cids = sorted(...)` is a list. Later `if cid in above_cids:` runs once per node. For large above-threshold community counts this becomes O(N_nodes × N_communities).

**Fix:** Keep `above_cids` as a sorted list for deterministic iteration but also construct `above_cids_set = set(above_cids)` for the membership check.

### IN-04: `_detect_dead_rules` is gated on `if not errors:` which hides shadow warnings behind unrelated shape errors

**File:** `graphify/mapping.py:788-792`

**Issue:** When any earlier rule has a shape error (e.g. a typo in `note_type`), `_detect_dead_rules` is skipped entirely. Users must fix shape errors and re-run validation to discover dead-rule warnings. The rationale is documented; consider a refinement that only skips pairs referencing malformed rules.

**Fix:** Optional refactor — pre-compute `bad_indices = {i for rules with errors}` and skip only pairs where `i` or `j` is in that set.

### IN-05: `test_nearest_host_tiebreak_largest_then_lowest_cid` does not exercise the full three-way tie-break

**File:** `tests/test_mapping.py:352-361`

**Issue:** The test covers tied-edge-count + size-mismatch and tied-edge-count + size-tie paths, but not the case where two hosts are tied on *both* edge count and size (which hits the `host_cid < best_cid` branch).

**Fix:** Add an assertion:

```python
# Three-way tie broken by lowest cid
assert _nearest_host(3, [5, 2, 7], {(3,5):2, (2,3):2, (3,7):2}, {5:5, 2:5, 7:5}) == 2
```

---

_Reviewer: gsd-code-reviewer (standard depth)_
_Findings: 0 critical, 3 warning, 5 info, 8 total_
