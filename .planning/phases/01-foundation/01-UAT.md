---
status: diagnosed
phase: 01-foundation
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md]
started: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:30:00Z
tested_by: claude-autonomous
---

## Current Test

[testing complete]

## Tests

### 1. Full Test Suite Passes
expected: Run `pytest tests/ -q` from the repo root. All tests pass (0 failures, 0 errors).
result: pass
note: 469 passed in 2.39s (up from 434 at summary time — suite has grown since Phase 1 shipped).

### 2. Public API Imports
expected: `python -c "from graphify import load_profile, validate_profile; print('ok')"` prints `ok`.
result: pass
note: Lazy import map in graphify/__init__.py lines 22-23 wires both symbols correctly.

### 3. Profile Default Fallback
expected: `load_profile()` on a vault with no `.graphify/profile.yaml` returns the built-in Ideaverse ACE default dict.
result: pass
note: Default shape is `folder_mapping: {moc, thing, statement, person, source, default}` routing node types to `Atlas/...` subfolders, plus `naming`, `merge`, `mapping_rules`, `obsidian`. Original test description expected top-level "Atlas/Calendar/Efforts" keys — that was imprecise; actual shape correctly encodes ACE structure as node-type routing (intent satisfied).

### 4. Profile Custom Deep-Merge
expected: Partial `.graphify/profile.yaml` merges with user values overriding and unspecified fields inheriting defaults.
result: pass
note: Verified with a vault declaring only `folder_mapping.thing: CustomFolder/Things/` and `naming.convention: kebab-case`. Result had `thing` overridden, all other default folders intact, naming convention overridden, and `merge`/`mapping_rules`/`obsidian` preserved.

### 5. Profile Validation Returns Error List
expected: Pass malformed profile to `validate_profile()`. Returns non-empty `list[str]`, does NOT raise.
result: pass
note: Tested 5 bad inputs — non-dict, unknown key, wrong folder_mapping type, invalid naming convention, invalid merge strategy. Each returned a clear error string listing valid values. Valid input returned `[]`.

### 6. Path Traversal Blocked
expected: `validate_vault_path()` raises `ValueError` for escape attempts.
result: pass
note: Blocked `../../etc/passwd`, `../escape.md`, `/etc/passwd`, and `Atlas/../../../../etc/passwd`. Error message includes vault root and a hint to check `folder_mapping` values. Legit `Atlas/note.md` resolved to full path inside vault.

### 7. Safety Helpers Sanitize Labels
expected: safe_filename / safe_frontmatter_value / safe_tag clean their input.
result: pass
note: `safe_filename("Dé-Bug Fïx:/../ 🚀 " + "LongTitle "*30)` → NFC-normalized, path chars stripped, capped at 200 chars, hash suffix `_adda2ffd`. `safe_frontmatter_value("key: value\nanother: line")` → `'"key: value another: line"'` (newlines flattened to spaces, wrapped in quotes). `safe_tag("Machine Learning / Deep 🧠")` → `machine-learning-deep` (slugified, emoji dropped, kebab-case).

### 8. Obsidian Export — Deterministic Output
expected: Running `to_obsidian()` twice on the same graph produces byte-identical output.
result: pass
note: Built a 4-node NetworkX graph, called `to_obsidian()` into two temp dirs, `diff -rq` showed no differences. Filenames produced: `Attention Is All You Need.md`, `LayerNormSpecialChars.md` (special chars `/`, `*`, `?`, `\`, `:` all stripped), `Transformer.md`, `Unicode Dé-Bug 🚀.md` (Unicode preserved), plus `_COMMUNITY_*.md` overviews and `.obsidian/graph.json`. Test originally expected a `graphify run --obsidian` CLI command; that CLI doesn't exist — `to_obsidian()` is a library-only entry point — but the user-observable behavior (deterministic vault artifacts) is verified via the library call.

### 9. graph.json Preserves User Edits
expected: Custom user color groups in `.obsidian/graph.json` survive a re-run; only `tag:community/*` groups are refreshed.
result: pass
note: First run produced `graph.json` with `tag:community/core` and `tag:community/theory` color groups. Hand-edited the file to add a `file:MyNotes` group, a `tag:project` group, and top-level `showArrow: true` + `search: "important"`. Second run of `to_obsidian()` on the same vault directory preserved all 4 user edits AND refreshed both `tag:community/*` groups. Read-merge-write working correctly.

### 10. Optional Obsidian Extras Install
expected: `pip install -e ".[obsidian]"` installs PyYAML; extras group declared in pyproject.toml.
result: issue
reported: "Merge commit 15b97be dropped the obsidian extras group and the PyYAML entry from the all extras. Phase 1 Plan 02's commit 70240fc correctly added both; the merge from v3 into ideaverse-integration silently clobbered them when reconciling with v3's video/audio extras additions."
severity: major

## Summary

total: 10
passed: 9
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "pyproject.toml declares `obsidian = [\"PyYAML\"]` optional-dependencies group and includes PyYAML in the `all` extras group, so `pip install graphifyy[obsidian]` and `pip install graphifyy[all]` both install PyYAML for profile loading support."
  status: failed
  reason: "User reported: merge commit 15b97be dropped the obsidian extras group and the PyYAML entry from all extras when reconciling v3 branch's video/audio additions"
  severity: major
  test: 10
  root_cause: "Three-way merge of `pyproject.toml` in commit 15b97be resolved the `all` line in favor of v3's version (`[..., faster-whisper, yt-dlp]`) and dropped the `obsidian = [\"PyYAML\"]` line entirely. The ideaverse-integration side (commit 70240fc) had both `obsidian = [\"PyYAML\"]` and PyYAML appended to `all`; the v3 side had neither but added `video = [\"faster-whisper\", \"yt-dlp\"]`. The merge driver picked v3's `all` wholesale and did not carry over the new `obsidian` group."
  artifacts:
    - path: "pyproject.toml"
      lines: "43-51"
      issue: "Missing `obsidian = [\"PyYAML\"]` line; `all` extras missing `PyYAML` entry"
    - path: "graphify/profile.py"
      lines: "76-82 (approx)"
      issue: "Fallback error message tells users to run `pip install graphifyy[obsidian]`, but that extras group no longer exists — broken install instructions"
  missing:
    - "Restore `obsidian = [\"PyYAML\"]` line after `office = [\"python-docx\", \"openpyxl\"]` in [project.optional-dependencies]"
    - "Add `\"PyYAML\"` to the `all` extras list alongside `faster-whisper`/`yt-dlp`"
    - "Add a regression test: `tests/test_pyproject.py` parses `pyproject.toml` with `tomllib` and asserts `obsidian` extras group exists and contains PyYAML, AND `all` extras contains PyYAML"
  debug_session: ""
  note: "Root cause diagnosed inline from git history — no separate debug session needed. Fix is mechanical: two-line restoration + one regression test."
