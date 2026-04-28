---
title: "Fix self-ingestion: exclude graphify-out/ from detect.py default ignores"
date: 2026-04-27
priority: high
---

# Fix self-ingestion loop in `detect.py`

## Problem

Running `graphify --obsidian` from inside an Obsidian vault root (e.g., `~/Documents/work-vault/`) causes graphify's *prior* output to be re-ingested on subsequent runs, producing nested folders like:

```
~/Documents/work-vault/graphify-out/obsidian/graphify-out/obsidian/Atlas/...
```

## Root cause chain

1. `detect.collect_files()` walks the working directory and treats prior `graphify-out/obsidian/*.md` notes as fresh `document` inputs (no default ignore for graphify's own output dir).
2. `extract.py` produces nodes with `source_file` pointing back into `graphify-out/obsidian/...`.
3. `export.to_obsidian()` mirrors `source_file` paths under the new output dir → doubled `graphify-out/obsidian/graphify-out/obsidian/...` path on every re-run.

This is not an exporter bug — the exporter is doing exactly what it's told. The bug is in detection.

## Fix

In `graphify/detect.py`, add `graphify-out/` (and any `graphify_out/` variant) to the default ignore set, *independent* of `.graphifyignore`. Users overriding via `.graphifyignore` should still be able to opt back in if they really want to (rare), but the default must be safe.

## Acceptance criteria

- [ ] `detect.collect_files()` skips any `graphify-out/` subtree by default
- [ ] Regression test: `tests/test_detect.py` adds a case that creates `tmp_path/graphify-out/obsidian/foo.md`, runs `collect_files(tmp_path)`, and asserts the file is **not** returned
- [ ] Manual verification: re-running `graphify --obsidian` from a vault root no longer produces nested `graphify-out/obsidian/graphify-out/obsidian/` paths
- [ ] Existing tests pass on Python 3.10 and 3.12

## Suggested entry point

`/gsd-quick fix-detect-self-ingestion` — small surface, regression test, atomic commit.

## Cleanup

Delete the orphaned nested tree at `~/Documents/work-vault/graphify-out/obsidian/graphify-out/` after the fix lands (not part of code change — manual user step).
