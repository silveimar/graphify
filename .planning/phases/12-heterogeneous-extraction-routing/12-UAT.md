---
status: complete
phase: 12-heterogeneous-extraction-routing
source:
  - 12-01-SUMMARY.md
  - 12-02-SUMMARY.md
  - 12-03-SUMMARY.md
  - 12-04-SUMMARY.md
  - 12-05-SUMMARY.md
  - 12-06-SUMMARY.md
started: 2026-04-17T22:37:00Z
updated: 2026-04-17T23:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Help lists run and --router
expected: |
  `graphify --help` includes `run [path] [--router]` (or equivalent) so users can discover the router opt-in.
result: pass

### 2. Run without --router on empty tree
expected: |
  From an empty temporary directory, `python -m graphify run .` exits with code 0 and does not print a line starting with `routing audit ->`.
result: pass

### 3. Run with --router writes routing audit
expected: |
  From an empty temporary directory, `python -m graphify run . --router` exits 0, prints a line like `routing audit -> .../graphify-out/routing.json`, and that path exists.
result: pass

### 4. routing.json has version
expected: |
  `graphify-out/routing.json` from the previous step is valid JSON with top-level `"version"` (integer) and a `"files"` object.
result: pass

### 5. Skill documents router CLI
expected: |
  `graphify/skill.md` mentions the router / `graphify run ... --router` so agent users see parity with the CLI.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
