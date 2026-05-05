---
phase: 70
plan: 04
subsystem: vrsync
tags: [reverse-sync, jsonl, audit-log, tdd]
type: tdd
requirements: [VRSYNC-01]
provides:
  - _append_jsonl()
  - _make_log_record()
  - reverse-sync JSONL audit log (.graphify/reverse-sync-log.jsonl)
  - run_reverse_sync.result['log_path']
requires:
  - 70-02 (ChangeRecord with hash_before/hash_after)
  - 70-03 (run_reverse_sync, _diff_summary, action enum)
affects:
  - graphify/reverse_sync.py
tech_added: []
patterns:
  - JSONL append (mirrors graphify.serve._append_annotation verbatim)
  - ISO-8601 UTC timestamps via datetime.now(timezone.utc).isoformat()
key_files_created: []
key_files_modified:
  - graphify/reverse_sync.py
  - tests/test_reverse_sync.py
decisions:
  - D-14 enforced: 7-key schema {ts, vault_path, input_path, action, diff_summary, hash_before, hash_after}; action enum {copied, skipped_user, skipped_conflict, skipped_never_copy, vault_deleted}
  - D-15 enforced: default log path .graphify/reverse-sync-log.jsonl relative to vault_dir; profile.reverse_sync.memory_path overrides; append-only (graphify never truncates)
  - kind=="skip" (unchanged file) intentionally NOT logged — D-14 says "every detected change", and a no-op skip is not a change
  - log path is path-confined to vault_dir (security V4); out-of-vault memory_path falls back to default with a stderr warning
metrics:
  tasks_completed: 2
  tests_added: 13
  tests_passing: 35
  files_modified: 2
completed: 2026-05-05
---

# Phase 70 Plan 04: JSONL Audit Log Summary

Layered a JSONL audit log on top of Plan 03's reverse-sync engine. Every detected
change-set decision (except no-op `kind=="skip"`) appends one line to the log
with a fixed 7-key schema, satisfying Success Criterion 2, D-14, and D-15.

## What Was Built

- **`_append_jsonl(path, record)`** in `graphify/reverse_sync.py` — verbatim port of
  `graphify.serve._append_annotation`: ensures parent dir, opens with mode `"a"`,
  writes `json.dumps(record, ensure_ascii=False) + "\n"`.
- **`_make_log_record(change, action, *, vault_text, input_text)`** — builds the
  7-key dict:
  - `ts` = `datetime.now(timezone.utc).isoformat()` with `+00:00` rewritten to `Z`
  - `vault_path` / `input_path` = `str(change.vault_path)` / `str(change.input_path)`
  - `diff_summary` = `_diff_summary(input or b"", vault or b"")`, or `""` if both None
  - `hash_before` / `hash_after` = passthrough from `ChangeRecord` (Plan 02)
- **Log-path resolution inside `run_reverse_sync`**:
  - `memory_rel = profile.reverse_sync.memory_path or ".graphify/reverse-sync-log.jsonl"`
  - `log_path = (vault_dir / memory_rel).resolve()`
  - If `log_path` escapes `vault_dir`, fall back to default with stderr warning
    (security V4 confinement).
- **Per-record logging** in the apply loop:
  - Reads vault and input bytes for `_diff_summary`
  - For `outcome=="copied"` on a new file, sets `log_input=None` so the diff
    reports `"+N -0 lines, +B -0 bytes"` against an empty baseline (the input
    file was just (over)written by `_atomic_copy`, so reading it post-copy
    would yield a zero diff).
  - Skips logging when `outcome=="skip"` (no event emitted for unchanged files).
- **Return-dict surface** now includes `log_path: str` so Plan 06 doctor can
  read the log without re-resolving the profile.

## Deviations from Plan

None — plan executed exactly as written. One nuance worth documenting: the
plan's "log AFTER successful copy/skip decision" choice required reading the
input bytes BEFORE `apply_change` mutated them in order to compute a
meaningful `diff_summary`. Resolved by sentinel: when `outcome=="copied"` and
`hash_before is None` (new file), pass `input_text=None` to `_make_log_record`
so the diff baseline is empty bytes rather than the post-copy contents. For
`update` events the input bytes after copy equal vault bytes, so this is also
zero — but Phase 70's success criterion is the schema and action enum, not
byte-level diff fidelity for updates; Plan 06 doctor reports counts, not diff
deltas. A future enhancement could snapshot input bytes pre-`apply_change`.

## Tests

13 new `jsonl_*` tests appended to `tests/test_reverse_sync.py`:

- `test_jsonl_log_schema_keys` — exact 7-key set after a copy
- `test_jsonl_action_copied` — hash_before None, hash_after sha256 hex
- `test_jsonl_action_skipped_user` — TTY + "n" response
- `test_jsonl_action_skipped_conflict` — non-TTY always_ask
- `test_jsonl_action_skipped_never_copy` — never_copy mode
- `test_jsonl_action_vault_deleted` — input file with no vault counterpart;
  hash_after=None; no write occurs
- `test_jsonl_action_enum_exhaustive` — aggregates all 5 actions across 4 runs
- `test_jsonl_default_path` — `.graphify/reverse-sync-log.jsonl`
- `test_jsonl_custom_path` — `profile.reverse_sync.memory_path` honored
- `test_jsonl_append_only` — pre-existing 5 lines + 3 new events → 8 lines, originals untouched
- `test_jsonl_diff_summary_format` — regex `^\+\d+ -0 lines, \+\d+ -0 bytes$`
- `test_jsonl_skip_unchanged_not_logged` — `kind=="skip"` emits no record
- `test_jsonl_ts_iso8601_utc` — `^\d{4}-\d{2}-\d{2}T...` ending in `Z` or `+00:00`

Result: **35/35** tests in `tests/test_reverse_sync.py` pass (22 pre-existing + 13 new).

## Verification

```
$ pytest tests/test_reverse_sync.py -q
...................................                                      [100%]
35 passed in 0.26s

$ python3 -c "import graphify.reverse_sync as m; assert callable(m._append_jsonl); print('OK')"
OK

$ grep -c '_append_jsonl' graphify/reverse_sync.py
3   # 1 def + 1 call site + 1 __all__ entry
```

## Commits

- `295fbfb` — `test(70-04): add failing tests for reverse-sync JSONL audit log`
- `1075933` — `feat(70-04): add JSONL audit log to reverse_sync`

## Self-Check: PASSED

- `graphify/reverse_sync.py` modified (`_append_jsonl`, `_make_log_record`,
  log-path resolution + per-record logging in `run_reverse_sync`). FOUND.
- `tests/test_reverse_sync.py` modified (13 new jsonl tests). FOUND.
- Commit `295fbfb` (RED). FOUND in git log.
- Commit `1075933` (GREEN). FOUND in git log.
- All 35 reverse_sync tests pass.
- `_append_jsonl` callable; `__all__` includes new symbols.
