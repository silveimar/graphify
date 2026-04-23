---
phase: 10-cross-file-semantic-extraction
reviewed: 2026-04-16T20:25:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - graphify/__main__.py
  - graphify/batch.py
  - graphify/dedup.py
  - graphify/export.py
  - graphify/report.py
  - graphify/serve.py
  - graphify/templates.py
  - graphify/validate.py
  - graphify/skill.md
  - graphify/skill-aider.md
  - graphify/skill-claw.md
  - graphify/skill-codex.md
  - graphify/skill-copilot.md
  - graphify/skill-droid.md
  - graphify/skill-opencode.md
  - graphify/skill-trae.md
  - graphify/skill-windows.md
  - pyproject.toml
  - tests/conftest.py
  - tests/fixtures/multi_file_extraction.json
  - tests/test_batch.py
  - tests/test_dedup.py
  - tests/test_export.py
  - tests/test_main_cli.py
  - tests/test_pyproject.py
  - tests/test_report.py
  - tests/test_serve.py
  - tests/test_templates.py
  - tests/test_validate.py
findings:
  critical: 0
  warning: 3
  info: 7
  total: 10
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-16T20:25:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Phase 10 introduces `graphify/batch.py` (file-cluster detection, ~213 LoC) and `graphify/dedup.py` (entity merge pipeline, ~590 LoC), plus an integration surface: `--dedup` CLI branch in `__main__.py`, MCP alias redirect in `serve.py`, `aliases:` frontmatter in `templates.py`, `_hydrate_merged_from` in `export.py`, a dedup section in `report.py`, and schema extensions in `validate.py` for `source_file: list[str]` and `merged_from: list[str]`.

Overall the phase follows the locked decisions (D-01..D-17) faithfully. Security threat mitigations (T-10-01 path confinement, T-10-02 label sanitization, T-10-04 yaml.safe_load, T-10-05 wikilink alias sanitization, T-10-06 defensive MCP alias loading) are all present and covered by unit tests. The Pitfall 1 guidance ("never use `nx.relabel_nodes` — operate on extraction dicts") is respected throughout `dedup.py`. Test coverage is solid: 408 lines of dedup tests, 162 lines of batch tests, plus cross-file coverage in `test_main_cli`, `test_serve`, `test_export`, `test_templates`, `test_report`, and `test_validate`.

No critical issues found. Three warnings concern a real user-facing defect in the `--dedup --graph` CLI flow, an un-mutated-arguments contract in MCP dispatch, and an alias-overwrite that loses provenance when multiple aliases resolve to the same canonical. Seven info items cover dead code, inconsistent sanitization between `dedup.py` and `report.py`, a noisy warning path, and a stale 9-skill divergence. Cross-skill divergence for the Phase 10 surface looks mechanically similar (no substantive drift in the dedup/batch content).

Nine skill `.md` variants are intentional platform duplicates per phase context — spot-checked for substantive Phase 10 divergence, none found beyond the existing mechanical wrapper differences (python invocation, heredoc styles).

## Warnings

### WR-01: `graphify --dedup --graph graph.json` hard-rejects node-link format

**File:** `graphify/__main__.py:1199-1205`
**Issue:** The `--dedup` help text (line 1339) advertises `--graph <path> source extraction.json or graph.json (default graphify-out/extraction.json)`, but the shape validation after load only accepts extraction dicts that contain both `"nodes"` and `"edges"` at the top level. `graphify-out/graph.json` is written in NetworkX node-link format, which uses `"links"` as the edge key (see `graphify/validate.py:58` where `validate_extraction` already accepts `"links"` as a fallback). The CLI explicitly excludes that path:

```python
if "nodes" not in extraction or "edges" not in extraction:
    print(f"error: {source_path!s} does not contain 'nodes' and 'edges' keys", ...)
    sys.exit(1)
```

Users following the help text and passing `--graph graphify-out/graph.json` will hit a confusing error.

**Fix:** Either (a) normalize `"links"` → `"edges"` before the shape check, mirroring `validate.py`, or (b) drop `or graph.json` from the help text so the contract matches the implementation. Suggested (a):
```python
if "links" in extraction and "edges" not in extraction:
    extraction = {**extraction, "edges": extraction.pop("links")}
if "nodes" not in extraction or "edges" not in extraction:
    ...
```

---

### WR-02: `_resolved_aliases[canonical] = node_id` loses original alias when multiple aliases redirect to the same canonical

**File:** `graphify/serve.py:791-796`
**Issue:** The alias-resolution recorder keys by canonical ID, so when two different merged-away IDs (e.g. `auth`, `auth_svc`) both resolve to the same canonical (`authentication_service`), only the *last* alias written wins. The response meta `resolved_from_alias` therefore surfaces incomplete provenance and breaks the D-16 contract ("every node redirected" is annotated). Tests in `test_serve.py` only cover the single-alias case, so this is unlikely to be caught by the existing suite.

```python
_resolved_aliases: dict[str, str] = {}  # {canonical_id: original_alias}

def _resolve_alias(node_id: str) -> str:
    canonical = _effective_alias_map.get(node_id)
    if canonical and canonical != node_id:
        _resolved_aliases[canonical] = node_id  # <-- overwrites on second hit
        return canonical
    return node_id
```

**Fix:** Record a list of aliases per canonical, or key by alias instead of canonical:
```python
_resolved_aliases: dict[str, list[str]] = {}  # {canonical_id: [original_aliases]}
...
_resolved_aliases.setdefault(canonical, []).append(node_id)
```
Then `meta["resolved_from_alias"]` holds `{canonical_id: [alias1, alias2, ...]}`. Document the shape change in the D-16 schema.

---

### WR-03: `_run_query_graph` mutates the caller's `arguments` dict in place

**File:** `graphify/serve.py:803-810`
**Issue:** `_run_query_graph` rewrites `arguments[_alias_field]` and `arguments["seed_nodes"]` in place during alias resolution. MCP dispatch passes `arguments` from `_tool_query_graph` (line ~1202) — the caller's dict. A subsequent invocation reusing the same dict (or any future debug/logging code that inspects `arguments`) will see already-resolved IDs, which is confusing and a latent source of bugs if a retry logic or instrumentation ever reads the argument dict after dispatch. Also makes the function harder to test in isolation (the test already only checks meta, not argument state).

```python
for _alias_field in ("node_id", "source", "target", "seed", "start"):
    if _alias_field in arguments and isinstance(arguments[_alias_field], str):
        arguments[_alias_field] = _resolve_alias(arguments[_alias_field])
```

**Fix:** Shallow-copy `arguments` at the function head or build a separate `resolved_args` dict:
```python
arguments = dict(arguments)  # shallow copy — preserve caller's input
for _alias_field in ...:
    ...
```

## Info

### IN-01: Dead/redundant assignment in `_split_by_top_dir`

**File:** `graphify/batch.py:117-120`
**Issue:** The first assignment to `common` is immediately overwritten on the next line:
```python
common = Path(*[p.parent for p in paths]) if len(paths) == 1 else paths[0].parent
# Use os.path.commonpath for multi-path common ancestor
import os
common = Path(os.path.commonpath([str(p) for p in paths]))
```
Since `len(paths) > 1` is guaranteed by the early-return at line 114 (`if len(component) <= 1`), the `if len(paths) == 1 else ...` branch is unreachable. The whole first assignment is dead code.
**Fix:** Remove the first assignment; move `import os` to the module top:
```python
common = Path(os.path.commonpath([str(p) for p in paths]))
```

---

### IN-02: Inline `import os` in `_split_by_top_dir`

**File:** `graphify/batch.py:119`
**Issue:** `import os` is placed inside the function body rather than at the top of the module. Minor style inconsistency with the rest of the file (all other imports are at module top). PEP 8 convention and the project's import-organization style (per CLAUDE.md) keep imports at the top.
**Fix:** Move `import os` to the top of `batch.py` next to `from pathlib import Path`.

---

### IN-03: `_load_dedup_report` silently swallows OS errors (no warning)

**File:** `graphify/serve.py:99-103`
**Issue:** `_load_dedup_report` prints a stderr warning for `json.JSONDecodeError` but not for `OSError` (permission denied, device error, etc.) — OSError is caught by the combined `except (json.JSONDecodeError, OSError)` clause and silently returns `{}`. An unreadable `dedup_report.json` disables alias-redirection without any feedback, which is harder to diagnose than the JSON parse case.
**Fix:** Split the except clauses or always warn:
```python
except json.JSONDecodeError:
    print("[graphify] warning: dedup_report.json could not be parsed ...", file=sys.stderr)
    return {}
except OSError as e:
    print(f"[graphify] warning: could not read dedup_report.json: {e}", file=sys.stderr)
    return {}
```

---

### IN-04: Inconsistent label sanitization between `dedup_report.md` and `GRAPH_REPORT.md`

**File:** `graphify/dedup.py:579-581` vs `graphify/report.py:264-267`
**Issue:** `_render_dedup_md` uses `html.escape(sanitize_label(...))` which leaves backticks untouched. When a canonical label contains backticks (e.g. a raw LLM label like `` `rm -rf` ``), the surrounding `` `{canon_label}` `` inline-code wrapping produces broken markdown. By contrast, `report.py:_sanitize_md` explicitly replaces backticks with apostrophes. Not a security risk (html.escape handles `<`/`>`), but a fidelity/consistency bug between the two report surfaces for the same dedup_report payload.
**Fix:** Apply `_sanitize_md` (or an equivalent) in `_render_dedup_md`:
```python
def _sanitize_md(text: str) -> str:
    return text.replace("`", "'")
canon_label = html.escape(sanitize_label(_sanitize_md(merge.get("canonical_label", ""))))
```
Or centralize the helper in `graphify/security.py` so both reports share it.

---

### IN-05: `<-` arrow in `dedup_report.md` becomes `&lt;-` after `html.escape`

**File:** `graphify/dedup.py:584`
**Issue:** The line `f"- \`{canon_label}\` <- {eliminated_labels}  ..."` contains a literal `<-`. Since the loop runs `html.escape(sanitize_label(...))` on labels (not the surrounding template), the arrow itself escapes correctly in renderers, but the inconsistency with `report.py:272` which uses `←` (unicode U+2190) produces mismatched output between `GRAPH_REPORT.md` and `dedup_report.md`. Minor aesthetic inconsistency.
**Fix:** Use the same arrow glyph in both files:
```python
f"- `{canon_label}` ← {eliminated_labels}  ..."
```

---

### IN-06: `_merge_extraction` uses O(n²) `not in` check when folding `source_file`

**File:** `graphify/dedup.py:466-471`
**Issue:** Inside the per-eliminated loop, `if s and s not in sf_list:` is O(n) on a list. Across n merges with m source files each, this becomes O(n·m²). For real-world corpora this is negligible (merge groups are small), but worth noting for large-merge cases (performance, out of v1 scope but flagged for awareness). Not a correctness bug.
**Fix (optional):** Accumulate into a set, sort at the end:
```python
sf_set = set(existing if isinstance(existing, list) else [existing] if existing else [])
if isinstance(incoming, list):
    sf_set.update(s for s in incoming if s)
elif incoming:
    sf_set.add(incoming)
canon["source_file"] = sorted(sf_set) if len(sf_set) > 1 else (next(iter(sf_set)) if sf_set else "")
```

---

### IN-07: Docstring for `_load_dedup_report` lists three fallback candidate paths, but `_hydrate_merged_from` uses a different search order

**File:** `graphify/export.py:454-462`
**Issue:** `_hydrate_merged_from` searches three candidate locations for `dedup_report.json`:
1. `output_dir.parent / "dedup_report.json"`
2. `output_dir / ".." / "dedup_report.json"` (same as 1 after resolve)
3. `Path("graphify-out") / "dedup_report.json"` (cwd-relative)

Candidates 1 and 2 are equivalent after `.resolve()` — the second is redundant. Candidate 3 depends on cwd, which can surprise users when they invoke the CLI from a parent directory. Not a bug but a clarity/maintainability concern: the search order is under-documented and contains a duplicate.
**Fix:** Remove the duplicate candidate and document the precedence:
```python
# Search order:
# 1. alongside the vault dir (typical graphify-out/obsidian layout)
# 2. graphify-out/ relative to cwd (fallback for unusual layouts)
candidates = [
    output_dir.parent / "dedup_report.json",
    Path("graphify-out") / "dedup_report.json",
]
```

---

_Reviewed: 2026-04-16T20:25:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
