---
phase: 01-foundation
reviewed: 2026-04-09T12:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - graphify/__init__.py
  - graphify/export.py
  - graphify/profile.py
  - pyproject.toml
  - tests/test_export.py
  - tests/test_profile.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-04-09T12:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the new `graphify/profile.py` module, updates to `graphify/__init__.py` and `graphify/export.py` for Obsidian vault profile support, the `pyproject.toml` optional dependency addition, and comprehensive test suites in `tests/test_profile.py` and `tests/test_export.py`.

The new `profile.py` module is well-structured with solid validation, security checks (path traversal prevention, YAML injection mitigation), and proper fallback behavior. The test coverage is thorough. Two bugs were found in `export.py`: a Dataview query tag mismatch that will produce non-functional queries, and a missing `source_location` default that could produce malformed frontmatter. Two minor info items were also noted.

## Warnings

### WR-01: Dataview query tag does not match actual node tags

**File:** `graphify/export.py:622-626`
**Issue:** The Dataview query in community notes uses `community_name.replace(" ", "_")` to build the tag (e.g., `#community/ML_AI_+_Data`), but actual node tags are built with `safe_tag(community_name)` which lowercases and replaces all non-alphanumeric characters with hyphens (e.g., `community/ml-ai-data`). These will never match, making every generated Dataview query return zero results.
**Fix:**
```python
# Line 622 — replace:
comm_tag_name = community_name.replace(" ", "_")
# with:
comm_tag_name = safe_tag(community_name)
```
And update line 626 accordingly:
```python
lines.append(f"TABLE source_file, type FROM #community/{comm_tag_name}")
```

### WR-02: Missing `source_location` default can produce empty frontmatter value

**File:** `graphify/export.py:496-527`
**Issue:** Nodes added to the graph without a `source_location` attribute skip that frontmatter field (line 522 checks `if data.get("source_location")`). However, `_make_small_graph` in tests creates nodes sometimes without `source_location` (line 191-194 in `test_export.py` -- the `_make_small_graph` default nodes have it, but explicit node lists in tests like `test_to_obsidian_dedup_deterministic` at line 189 omit it). This is not a crash bug since the field is simply omitted, but the inconsistency between test fixtures (some with, some without `source_location`) means tests do not exercise the same code paths uniformly. More importantly, if `source_location` is present but is an empty string `""`, the truthiness check passes and an empty `location:` frontmatter line is written, which is not ideal for Obsidian properties.
**Fix:** Make the check explicit:
```python
loc = data.get("source_location")
if loc:
    lines.append(f'location: {safe_frontmatter_value(loc)}')
```
This already works as-is since empty string is falsy. However, ensure test fixtures are consistent -- either always include `source_location` or explicitly test the omission path.

## Info

### IN-01: Duplicated filename dedup logic between `to_obsidian` and `to_canvas`

**File:** `graphify/export.py:464-476` and `graphify/export.py:714-727`
**Issue:** The filename deduplication logic (sort by source_file+label, apply `safe_filename`, append numeric suffix on collision) is duplicated verbatim between `to_obsidian` (lines 464-476) and `to_canvas` (lines 714-727). If one is updated, the other must be manually kept in sync.
**Fix:** Extract into a shared helper function, e.g.:
```python
def _build_node_filenames(G: nx.Graph) -> dict[str, str]:
    node_filename: dict[str, str] = {}
    seen_names: dict[str, int] = {}
    for node_id, data in sorted(
        G.nodes(data=True),
        key=lambda nd: (nd[1].get("source_file", ""), nd[1].get("label", nd[0]))
    ):
        base = safe_filename(data.get("label", node_id))
        if base in seen_names:
            seen_names[base] += 1
            node_filename[node_id] = f"{base}_{seen_names[base]}"
        else:
            seen_names[base] = 0
            node_filename[node_id] = base
    return node_filename
```

### IN-02: `_deep_merge` shallow-copies nested dicts only one level

**File:** `graphify/profile.py:46-54`
**Issue:** `_deep_merge` calls `base.copy()` which is a shallow copy. For the first level of nesting, the recursive call produces a new dict, so mutations are safe. However, if a nested value is a list (e.g., `preserve_fields`), it is shared by reference between the result and the original `base` or `override` dict. In practice this is unlikely to cause bugs since the profile dicts are not mutated after merge, but it is worth noting for defensive correctness.
**Fix:** No immediate action needed. If mutation becomes a concern, use `copy.deepcopy(base)` as the starting point instead of `base.copy()`.

---

_Reviewed: 2026-04-09T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
