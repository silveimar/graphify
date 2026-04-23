---
phase: quick-260422-jdj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/capability.py
  - graphify/export.py
  - graphify/skill.md
  - graphify/skill-codex.md
  - tests/test_capability.py
autonomous: true
requirements:
  - BUGFIX-MANIFEST-COLLISION
must_haves:
  truths:
    - "capability.py writes to graphify-out/capability.json (not manifest.json)"
    - "detect.py's _MANIFEST_PATH remains graphify-out/manifest.json (unchanged)"
    - "A regression test fails if capability writer ever targets basename 'manifest.json' again"
    - "export.py error message references capability.json"
    - "Docs in skill.md / skill-codex.md reference capability.json for the agent capability manifest"
    - "Existing capability tests pass against the new filename"
    - "Incremental detect round-trip (save_manifest/load_manifest) still works end-to-end"
  artifacts:
    - path: "graphify/capability.py"
      provides: "_write_manifest targeting out_dir / 'capability.json'"
      contains: "capability.json"
    - path: "graphify/export.py"
      provides: "Error message referencing capability.json"
      contains: "capability.json"
    - path: "tests/test_capability.py"
      provides: "Regression test asserting capability writer basename is not 'manifest.json'"
      contains: "capability.json"
  key_links:
    - from: "graphify/export.py"
      to: "graphify/capability.py"
      via: "capability writer call in to_json"
      pattern: "capability"
---

<objective>
Fix the `graphify-out/manifest.json` path collision between `detect.py` (incremental mtime manifest, original owner) and `capability.py` (Phase 13 agent capability manifest, new entrant). Rename the capability manifest to `graphify-out/capability.json` so that incremental re-runs stop getting their mtime dict clobbered by the capability JSON.

Purpose: Restore the incremental skip-unchanged-files behavior for users whose `graphify-out/manifest.json` was overwritten by the Phase 13 capability writer.

Output: Updated `capability.py` + `export.py` + docs + regression test; `detect.py` untouched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@graphify/capability.py
@graphify/export.py
@graphify/detect.py
@tests/test_capability.py

<interfaces>
<!-- Extracted from codebase. Executor should use these directly. -->

From graphify/capability.py (lines ~228-240):
```python
def _write_manifest(out_dir: Path, manifest: dict) -> Path:
    """Write graphify-out/manifest.json via .tmp + os.replace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "manifest.json"
    tmp = target.with_suffix(".json.tmp")
    # ... atomic write via os.replace ...
    return target
```

From graphify/export.py (line 309 — inside exception / error message):
```python
"graphify-out/manifest.json could not be written; install graphify with [mcp] extras "
```

From graphify/detect.py line 19 (DO NOT TOUCH):
```python
_MANIFEST_PATH = "graphify-out/manifest.json"
```

From graphify/skill.md line 5 and graphify/skill-codex.md line 5:
```
capability_manifest: graphify-out/manifest.json
```

From tests/test_capability.py lines 57-65:
```python
def test_pipeline_writes_manifest_json(tmp_path: Path) -> None:
    """MANIFEST-02: export.to_json triggers manifest.json (uses same deps as CI [mcp])."""
    ...
    man = tmp_path / "manifest.json"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rename capability manifest path and add regression test</name>
  <files>
    graphify/capability.py,
    graphify/export.py,
    graphify/skill.md,
    graphify/skill-codex.md,
    tests/test_capability.py
  </files>
  <behavior>
    - Regression test: calling `_write_manifest(tmp_path, {...})` produces a file whose `.name` is `"capability.json"`, NOT `"manifest.json"`. Assert both: positive (capability.json exists) and negative (manifest.json does NOT exist in tmp_path after the call).
    - Existing `test_pipeline_writes_manifest_json` is renamed to `test_pipeline_writes_capability_json` and asserts `tmp_path / "capability.json"` exists (and `tmp_path / "manifest.json"` does not).
    - After the fix, a fresh pytest run of `tests/test_capability.py` passes.
    - `detect.py` is NOT modified; its `_MANIFEST_PATH = "graphify-out/manifest.json"` is preserved.
  </behavior>
  <action>
    1. **capability.py** — In `_write_manifest` (~line 230), change `target = out_dir / "manifest.json"` to `target = out_dir / "capability.json"`. Update the docstring on line 228 from "Write graphify-out/manifest.json via .tmp + os.replace." to "Write graphify-out/capability.json via .tmp + os.replace." Update the `_build_and_write_manifest` docstring (~line 239) similarly. Preserve all atomic-write semantics (`.tmp` suffix + `os.replace`) and schema shape unchanged.

    2. **export.py line 309** — Update error message string from `"graphify-out/manifest.json could not be written; ..."` to `"graphify-out/capability.json could not be written; ..."`.

    3. **graphify/skill.md line 5** — Change `capability_manifest: graphify-out/manifest.json` to `capability_manifest: graphify-out/capability.json`. Also grep the rest of `skill.md` for any further `manifest.json` references that refer to the CAPABILITY manifest (not the detect incremental one) and update them. Leave references that clearly concern the incremental/detect manifest alone.

    4. **graphify/skill-codex.md line 5** — Same treatment as skill.md.

    5. **tests/test_capability.py**:
       - Rename `test_pipeline_writes_manifest_json` to `test_pipeline_writes_capability_json`. Update the docstring and the assertion target to `tmp_path / "capability.json"`. Add a negative assertion: `assert not (tmp_path / "manifest.json").exists()` so the collision cannot regress silently.
       - Add a new dedicated regression test:
         ```python
         def test_capability_writer_basename_is_not_manifest_json(tmp_path: Path) -> None:
             """Regression: capability writer MUST NOT target 'manifest.json' (collides with detect incremental manifest)."""
             from graphify.capability import _write_manifest
             target = _write_manifest(tmp_path, {"CAPABILITY_TOOLS": []})
             assert target.name == "capability.json"
             assert target.name != "manifest.json"
             assert not (tmp_path / "manifest.json").exists()
         ```
       - Update any other references in this test file from `"manifest.json"` to `"capability.json"` where they refer to the capability manifest.

    6. **Do NOT modify** `graphify/detect.py`, `graphify/manifest.py`, `graphify/merge.py`, or `graphify/__main__.py`. The incremental mtime manifest at `graphify-out/manifest.json` stays exactly as-is — this is load-bearing for users with existing on-disk mtime files.

    7. Grep-sweep check — run `grep -rn "manifest.json" graphify/ tests/ | grep -v vault-manifest | grep -v file-manifest` and confirm all remaining hits fall into one of: (a) `detect.py` line 19 (correct — detect owns this), (b) `capability_manifest.schema.json` `$id` URL (cosmetic/identifier, leave alone), (c) legitimate capability paths now pointing at `capability.json`. No stray `manifest.json` should remain in capability.py, export.py, skill.md, skill-codex.md, or tests/test_capability.py.
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify &amp;&amp; pytest tests/test_capability.py -q &amp;&amp; pytest tests/test_detect.py -q 2>/dev/null || pytest tests/ -q -k "manifest or capability or detect"</automated>
  </verify>
  <done>
    - `graphify/capability.py` writes to `graphify-out/capability.json`.
    - `graphify/detect.py` line 19 unchanged (`graphify-out/manifest.json`).
    - `grep -rn "manifest.json" graphify/capability.py graphify/export.py graphify/skill.md graphify/skill-codex.md tests/test_capability.py` returns ONLY occurrences that are (i) intentional references to the detect incremental manifest with accompanying context, or (ii) have been replaced with `capability.json`. No stray collisions.
    - `pytest tests/test_capability.py -q` passes, including the new `test_capability_writer_basename_is_not_manifest_json` regression test.
    - Full `pytest tests/ -q` green (or at minimum: capability + detect + manifest test files green, no new failures introduced).
  </done>
</task>

</tasks>

<verification>
Run the full test suite and confirm:
- `pytest tests/ -q` passes
- `grep -rn "manifest.json" graphify/ | grep -v vault-manifest | grep -v file-manifest | grep -v capability_manifest.schema.json` returns ONLY `graphify/detect.py:19:_MANIFEST_PATH = "graphify-out/manifest.json"` (the single legitimate remaining reference).
- Smoke: instantiate `_write_manifest(tmp_path, {"CAPABILITY_TOOLS": []})` and confirm the return path ends with `capability.json`.
</verification>

<success_criteria>
1. Capability manifest and detect incremental manifest no longer share a filename.
2. Regression test asserts the filename divergence and will fail if anyone re-collides the paths in the future.
3. Docs (skill.md, skill-codex.md) and export.py error message reference the new `capability.json` name.
4. Zero changes to `detect.py`, `manifest.py`, `merge.py`, `__main__.py`.
5. All existing tests pass; the renamed `test_pipeline_writes_capability_json` passes against `capability.json`.
</success_criteria>

<output>
After completion, create `.planning/quick/260422-jdj-fix-manifest-json-path-collision-between/260422-jdj-SUMMARY.md` documenting:
- Files changed with line-level diff summary
- Confirmation that `detect.py` was not modified
- Test results (pytest output excerpt for test_capability.py)
- Grep confirmation showing the single remaining `manifest.json` reference is detect.py line 19
</output>
