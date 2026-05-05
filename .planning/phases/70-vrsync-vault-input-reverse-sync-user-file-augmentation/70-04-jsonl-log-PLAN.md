---
phase: 70
plan: 04
type: tdd
wave: 2
depends_on: [70-02, 70-03]
files_modified:
  - graphify/reverse_sync.py
  - tests/test_reverse_sync.py
autonomous: true
requirements: [VRSYNC-01]
must_haves:
  truths:
    - "Every detected change appends one JSON line to profile.reverse_sync.memory_path (D-14, Success Criterion 2)"
    - "Each record has exactly the keys: ts, vault_path, input_path, action, diff_summary, hash_before, hash_after"
    - "Action enum is exhaustive: copied | skipped_user | skipped_conflict | skipped_never_copy | vault_deleted (D-14)"
    - "Default log path is .graphify/reverse-sync-log.jsonl when memory_path absent (D-15)"
    - "Log is append-only — never truncated by graphify (D-15)"
  artifacts:
    - path: "graphify/reverse_sync.py"
      provides: "_append_jsonl(), _make_log_record(), wired log calls in run_reverse_sync"
      contains: "_append_jsonl"
  key_links:
    - from: "graphify/reverse_sync.py"
      to: "filesystem .graphify/reverse-sync-log.jsonl"
      via: "open(path, 'a').write(json.dumps(rec)+'\\n')"
      pattern: "json\\.dumps.*ensure_ascii"
---

<objective>
Add JSONL audit log to every change-set decision in run_reverse_sync. One line per ChangeRecord (D-14) regardless of whether a copy occurred. Schema is fixed: 7 keys exactly. Pattern reused from `serve._append_annotation`.

Purpose: Auditable history of vault→input reverse-sync activity. Doctor section (Plan 06) summarizes pending conflicts from this log.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@graphify/serve.py
@graphify/reverse_sync.py

<interfaces>
- Reuse `serve._append_annotation` JSONL pattern verbatim (RESEARCH Code Examples).
- Action enum: `Literal["copied", "skipped_user", "skipped_conflict", "skipped_never_copy", "vault_deleted"]`.
- Record schema (D-14, Success Criterion 2):
  ```
  {
    "ts": ISO-8601 UTC string,
    "vault_path": str (absolute or relative — vault file path),
    "input_path": str (input target path, even if not written),
    "action": str (one of action enum),
    "diff_summary": str ("+N -M lines, +A -B bytes" per D-03; "" if no diff applicable),
    "hash_before": str | None (hex sha256 of input file pre-action; null if file did not exist),
    "hash_after": str | None (hex sha256 of vault file source; null if vault_deleted)
  }
  ```
- Log path resolution: `profile.reverse_sync.memory_path` (default `.graphify/reverse-sync-log.jsonl`, relative to vault_dir per D-15).
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Tests for JSONL log schema + per-action coverage</name>
  <files>tests/test_reverse_sync.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md (D-03, D-14, D-15)
    - graphify/serve.py:36-40 (JSONL append pattern)
  </read_first>
  <behavior>
    - test_jsonl_log_schema_keys: after a copy, log file has exactly one line; json.loads(line) has keys == {ts, vault_path, input_path, action, diff_summary, hash_before, hash_after}
    - test_jsonl_action_copied: mode=always_copy, new file → action == "copied", hash_before is None, hash_after is hex string
    - test_jsonl_action_skipped_user: mode=always_ask, input "n" → action == "skipped_user"
    - test_jsonl_action_skipped_conflict: non-TTY always_ask → action == "skipped_conflict" (D-13 + D-14)
    - test_jsonl_action_skipped_never_copy: mode=never_copy → action == "skipped_never_copy"
    - test_jsonl_action_vault_deleted: input has file, vault does not → action == "vault_deleted", hash_after is None, no write occurred (D-10)
    - test_jsonl_action_enum_exhaustive: parse every action emitted across all tests; assert set ⊆ {copied, skipped_user, skipped_conflict, skipped_never_copy, vault_deleted}
    - test_jsonl_default_path: profile without reverse_sync.memory_path → log lands at vault_dir/.graphify/reverse-sync-log.jsonl (D-15)
    - test_jsonl_custom_path: profile.reverse_sync.memory_path="custom/log.jsonl" → log at vault_dir/custom/log.jsonl
    - test_jsonl_append_only: pre-existing log with 5 lines + run that produces 3 events → final log has 8 lines, original 5 untouched (D-15)
    - test_jsonl_diff_summary_format: copy of new file (no input pre-existing) → diff_summary == "+N -0 lines, +B -0 bytes" matching N,B from content
    - test_jsonl_skip_unchanged_not_logged: kind="skip" records produce no log entry (D-14 says "every detected change" — skip is not a change)
    - test_jsonl_ts_iso8601_utc: parse record["ts"] with datetime.fromisoformat or regex; ends with "Z" or "+00:00"
  </behavior>
  <action>
    Append 13 tests to tests/test_reverse_sync.py. Use `json.loads` per line; assert key sets via `assert set(rec.keys()) == {...}`. For ts validation, regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` plus UTC marker. Run pytest — must FAIL (no JSONL writer wired yet).
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q -k jsonl</automated>
  </verify>
  <done>13 jsonl-prefixed tests added and failing.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Wire JSONL logging into run_reverse_sync</name>
  <files>graphify/reverse_sync.py</files>
  <read_first>
    - tests/test_reverse_sync.py (jsonl tests)
    - graphify/serve.py:36-40 (verbatim pattern)
    - graphify/reverse_sync.py (existing run_reverse_sync from Plan 03)
  </read_first>
  <action>
    Add to graphify/reverse_sync.py:
    1. `def _append_jsonl(path: Path, record: dict) -> None`:
       ```python
       path.parent.mkdir(parents=True, exist_ok=True)
       with open(path, "a", encoding="utf-8") as f:
           f.write(json.dumps(record, ensure_ascii=False) + "\n")
       ```
    2. `def _make_log_record(change: ChangeRecord, action: str, *, vault_text: bytes | None, input_text: bytes | None) -> dict`:
       - ts = `datetime.now(timezone.utc).isoformat()` (replace `+00:00` with `Z`? Either form is acceptable; tests check ISO-8601 + UTC).
       - vault_path = str(change.vault_path), input_path = str(change.input_path).
       - diff_summary = `_diff_summary(input_text or b"", vault_text or b"")` (D-03), empty string if both None.
       - hash_before = change.hash_before, hash_after = change.hash_after (already computed in Plan 02).
    3. Resolve log path inside run_reverse_sync:
       ```python
       memory_rel = profile.get("reverse_sync", {}).get("memory_path") or ".graphify/reverse-sync-log.jsonl"
       log_path = (vault_dir / memory_rel).resolve()
       ```
       Path-confine: ensure log_path is inside vault_dir.resolve() (security).
    4. After every per-file decision in run_reverse_sync's loop (Plan 03), call `_append_jsonl(log_path, _make_log_record(change, action, ...))` — EXCEPT for `kind=="skip"` (no log per D-14 vs Success Criterion 2 — "Each sync event"; skips with no change are not events).
    5. Write the record BEFORE doing `_atomic_copy` for action="copied"? Order chosen: log AFTER successful copy/skip decision so action reflects reality. If copy raises, do NOT log a "copied" entry (catch + re-raise after logging a synthetic skipped_conflict? — for Phase 70, simpler: let the exception propagate; auto_on_run hook in Plan 05 will warn-and-continue at the parent level).
    6. Update return dict to include `log_path`: str so Plan 06 doctor can read it.
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q</automated>
  </verify>
  <done>All 35 reverse_sync tests pass; grep '_append_jsonl' graphify/reverse_sync.py returns ≥3 hits (definition + 1+ call sites); log file format verified by tests.</done>
</task>

</tasks>

<verification>
- `pytest tests/test_reverse_sync.py -q` green (35+ tests)
- `python3 -c "import graphify.reverse_sync as m; assert callable(m._append_jsonl)"` succeeds
- Manual: run reverse-sync, cat .graphify/reverse-sync-log.jsonl, verify 7-key schema
</verification>

<success_criteria>
- Success Criterion 2 fully delivered: 7-key JSONL schema per event
- D-14 action enum exhaustive
- D-15 default path + append-only
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-04-jsonl-log-SUMMARY.md` after completion.
</output>
