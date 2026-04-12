---
phase: 05-integration-cli
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - graphify/__init__.py
  - graphify/export.py
  - graphify/merge.py
  - graphify/profile.py
  - graphify/skill.md
  - graphify/skill-aider.md
  - graphify/skill-claw.md
  - graphify/skill-codex.md
  - graphify/skill-copilot.md
  - graphify/skill-droid.md
  - graphify/skill-opencode.md
  - graphify/skill-trae.md
  - graphify/skill-windows.md
  - tests/test_export.py
  - tests/test_integration.py
  - tests/test_merge.py
  - tests/test_pipeline.py
  - tests/test_profile.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 5 rewires `to_obsidian()` into a profile-driven pipeline composed of the Phase 1-4 public APIs (`load_profile`, `classify`, `render_note`/`render_moc`, `compute_merge_plan`, `apply_merge_plan`). The refactor is tight: the new ~120-line orchestration body delegates almost entirely to well-tested helpers, relies on `_validate_target` for path confinement (defense-in-depth), and honors `dry_run` semantics by returning a `MergePlan` before any `apply_merge_plan` call. New public helpers `format_merge_plan` and `split_rendered_note` in `merge.py` are pure functions with deterministic output and correct handling of the sparse summary dict / empty-frontmatter edge cases. `validate_profile_preflight` + `PreflightResult` is a clean four-layer read-only composite validator with an explicit regression test (`test_validate_profile_preflight_no_side_effects`) asserting zero filesystem mutation. Lazy import map in `__init__.py` adds the Phase 5 symbols without introducing circular imports. Test coverage for `split_rendered_note`, `format_merge_plan`, and `validate_profile_preflight` is thorough (5, 10, and 14 tests respectively), and all new tests stay inside `tmp_path` with no network calls.

The findings below are non-blocking quality concerns — no critical bugs, no security gaps. The two warnings flag silent-error-swallowing in the orchestration loops; the info items capture minor robustness and UX observations.

## Warnings

### WR-01: `to_obsidian` silently drops per-node/per-community rendering failures

**File:** `graphify/export.py:511-518, 539-544`
**Issue:** Both the per-node and per-community render loops wrap `render_note` / `render_moc` / `render_community_overview` in `try: ... except ValueError: continue` with no logging. If a profile's `mapping_rules` produce an unknown `note_type`, or if `classify()` returns a node id that `render_note` considers missing from `G`, every such case is silently discarded. In a pathological but plausible scenario (e.g. misconfigured user rules producing `note_type="articletype"`), `to_obsidian` can return an empty `MergeResult` with zero writes and no diagnostic — the caller cannot tell whether the pipeline succeeded on an empty graph or silently skipped 100% of nodes.

This is inconsistent with the rest of `profile.py` / `load_profile`, which always emit `print(..., file=sys.stderr)` for recoverable errors ("fail loudly with actionable messages, but continue when safe" per CLAUDE.md).

**Fix:**
```python
try:
    filename, rendered_text = render_note(
        node_id, G, profile, note_type, ctx, vault_dir=out,
    )
except ValueError as exc:
    print(
        f"[graphify] skipping node {node_id!r} ({note_type}): {exc}",
        file=sys.stderr,
    )
    continue
```
Apply the same pattern to the MOC loop. Optionally track a running counter and print a summary at the end (`[graphify] N nodes skipped during render`) so CI logs capture regressions.

---

### WR-02: `render_note` / `render_moc` can raise `FileNotFoundError` that is NOT caught

**File:** `graphify/export.py:511-518, 539-544`
**Issue:** `render_note` internally calls `load_templates(vault_dir=out)` (via `_render_note_like` / `_render_moc_like`). `load_templates` raises `FileNotFoundError` when `vault_dir` does not exist or is not a directory (`graphify/templates.py:220-230`). `to_obsidian` creates `out` via `out.mkdir(parents=True, exist_ok=True)` on line 479 so the happy path is safe, but:

1. A race where another process unlinks `out` between the `mkdir` call and the first `render_note` invocation is a real (if rare) TOCTOU window.
2. More realistically, if `out` already exists as a regular file (not a directory), `mkdir(..., exist_ok=True)` raises `FileExistsError` with a confusing message — the user will see it, but a clearer preflight check would be kinder.
3. The `except ValueError` clause does not catch `FileNotFoundError` / `OSError`, so any other unexpected OS error propagates out of `to_obsidian` and aborts the entire pipeline partway through — whereas per-node `ValueError` is tolerated.

**Fix:** Broaden the except clause to match `load_profile`'s defensive pattern, and add a single upfront guard:
```python
out = Path(output_dir)
if out.exists() and not out.is_dir():
    raise ValueError(
        f"to_obsidian: output_dir {out} exists but is not a directory"
    )
out.mkdir(parents=True, exist_ok=True)
# ...
except (ValueError, FileNotFoundError) as exc:
    print(f"[graphify] render skipped for {node_id}: {exc}", file=sys.stderr)
    continue
```
This keeps the "validate, report, don't crash" ethos while still propagating genuinely unrecoverable errors (permission denied, disk full, etc.) because `OSError` is broader than `FileNotFoundError`.

---

## Info

### IN-01: `to_obsidian` does not pre-validate folder strings before constructing target paths

**File:** `graphify/export.py:519-520, 545-546`
**Issue:** `folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("default", "Atlas/Dots/")` then `target_path = out / folder / filename`. There is no confinement check at this point — path escapes are caught later inside `compute_merge_plan` via `_validate_target`, which emits `SKIP_CONFLICT(conflict_kind="unmanaged_file")`. This is defense-in-depth-correct, but the user experience is subtle: a profile with `folder_mapping.default: "../../escape"` produces SKIP_CONFLICT actions at plan time rather than a schema-validation error. Plan 05 deliberately delegated to `_validate_target`, so this is noted as informational only — the existing `validate_profile` already rejects `..` and absolute paths in `folder_mapping`, so the only way to hit this is via `ctx.get("folder")` injected by a `mapping_rules` `then.folder` override, and those paths ARE path-safety-warned in `validate_profile_preflight` layer 4.

**Fix:** Consider documenting this delegation contract in the `to_obsidian` docstring so future maintainers don't add a redundant pre-check — or add one defensive `_validate_target(target_path, out)` before calling `split_rendered_note`, which would fail earlier with a clearer `ValueError` than the SKIP_CONFLICT status.

---

### IN-02: `split_rendered_note` re-wraps empty frontmatter into `---\n---` on synthesize

**File:** `graphify/merge.py:1098-1125` (consumed by `_synthesize_file_text` line 914-920)
**Issue:** When `_parse_frontmatter` returns `{}` (the "no frontmatter fence" case), `split_rendered_note` returns `({}, rendered_text)`. If a caller later re-synthesizes via `_synthesize_file_text`, `_dump_frontmatter({})` emits `---\n---` (empty YAML block), producing `---\n---\n<body>` — injecting a frontmatter block that was not originally present. This cannot happen with the real `render_note` pipeline (which always produces non-empty frontmatter), but a user template override lacking frontmatter would trigger the re-wrap. The resulting note still parses correctly in Obsidian; the anomaly is purely cosmetic.

**Fix:** Either (a) document that `_synthesize_file_text` always emits a frontmatter fence, or (b) have `_dump_frontmatter({})` return an empty string so empty-dict input produces no fence. Option (b) is preferable for round-trip fidelity:
```python
def _dump_frontmatter(fields: dict) -> str:
    if not fields:
        return ""
    # ... existing body ...
```
Note this would require auditing all call sites to ensure they don't rely on the `---\n---` prefix being emitted unconditionally. Low priority.

---

### IN-03: `community_labels` injection mutates the `mapping_result` dict in place

**File:** `graphify/export.py:493-498`
**Issue:** The `community_labels` merge loop does `per_community[cid] = ctx`, mutating the dict returned by `classify()`. Because `per_community = mapping_result.get("per_community", {}) or {}` is a reference (not a copy), the mutation reaches back into `mapping_result`. This is harmless in `to_obsidian` (mapping_result is a local variable, never returned), but it is a "spooky action at a distance" that a future caller might trip over — e.g. if someone refactors to pass `mapping_result` to a downstream analyzer after `to_obsidian` runs. The per-ctx `dict(per_community[cid])` copy on the inner line is correct, so only the outer `per_community` mapping is mutated.

**Fix:** Take a shallow copy before the loop to make the intent explicit:
```python
per_community = dict(mapping_result.get("per_community", {}) or {})
```
This is a trivial one-word change with no behavioral impact on current callers.

---

### IN-04: Community-overview notes fall back to `folder_mapping.moc` folder

**File:** `graphify/export.py:545`
**Issue:** When `ctx.get("folder")` is empty and `note_type == "community"` (overview path), the fallback uses `profile.get("folder_mapping", {}).get("moc", "Atlas/Maps/")` — the MOC folder, not a dedicated community-overview folder. In the default profile there is no `folder_mapping.community` entry, so community overviews land in `Atlas/Maps/` alongside MOCs. This may be intentional (overviews and MOCs both live in the Atlas/Maps conceptual space), but it is not obvious from the code alone and the default profile has no override lane for "overview-style" notes.

**Fix:** Either add a `community` key to `_DEFAULT_PROFILE.folder_mapping` in `profile.py`, or add a code comment at the call site documenting why the MOC folder is the correct fallback for community-overview shape. Minor UX / maintainability polish.

---

_Reviewed: 2026-04-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
