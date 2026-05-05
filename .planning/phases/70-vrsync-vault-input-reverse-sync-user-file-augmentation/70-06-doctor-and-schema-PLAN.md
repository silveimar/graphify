---
phase: 70
plan: 06
type: tdd
wave: 3
depends_on: [70-01, 70-02, 70-03, 70-04]
files_modified:
  - graphify/profile.py
  - graphify/doctor.py
  - graphify/vault_promote.py
  - tests/test_profile.py
  - tests/test_doctor.py
  - tests/test_vault_promote.py
autonomous: true
requirements: [VPROF-03, VRSYNC-01]
must_haves:
  truths:
    - "_DEFAULT_PROFILE includes reverse_sync.{mode,memory_path,auto_on_run} and augment.{allow_*} additive defaults (no v2→v2.1 migrator needed per RESEARCH)"
    - "validate_profile rejects invalid mode literals and non-bool augment.allow_* (Pitfall 4)"
    - "Profiles missing the new keys still load via _deep_merge (RESEARCH-confirmed additive)"
    - "Doctor `=== Reverse-Sync ===` section reports pending-conflict count from JSONL log (non-blocking)"
    - "vault_promote routes user-folder writes through augment_user_file_frontmatter at the Phase 69 chokepoint (A4)"
    - "Re-augmenting an already-augmented user file via update-vault produces zero diff (Pitfall 8 idempotence)"
  artifacts:
    - path: "graphify/profile.py"
      provides: "additive _DEFAULT_PROFILE entries + validate_profile rules"
      contains: "reverse_sync"
    - path: "graphify/doctor.py"
      provides: "DoctorReport.reverse_sync_pending_conflicts + format_report section"
      contains: "Reverse-Sync"
    - path: "graphify/vault_promote.py"
      provides: "augmentation routing at user-folder write chokepoint"
      contains: "augment_user_file_frontmatter"
  key_links:
    - from: "graphify/vault_promote.py"
      to: "graphify/augment.py"
      via: "from graphify.augment import augment_user_file_frontmatter"
      pattern: "augment_user_file_frontmatter"
    - from: "graphify/doctor.py"
      to: ".graphify/reverse-sync-log.jsonl"
      via: "tail-read JSONL to count skipped_conflict in last run"
      pattern: "reverse-sync-log\\.jsonl"
---

<objective>
Three glue jobs that close out Phase 70:
1. **Profile schema** — add `reverse_sync` and `augment` defaults to `_DEFAULT_PROFILE`; validate new keys (Pitfall 4 fix).
2. **Doctor section** — non-blocking `=== Reverse-Sync ===` summary that surfaces pending-conflict count from the JSONL log.
3. **Vault-promote integration** — wire `augment_user_file_frontmatter` (Plan 01) into the Phase 69 user-folder write chokepoint so update-vault auto-augments user files (closing the augmentation half of VPROF-03 in real pipeline flow).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-01-augment-PLAN.md
@graphify/profile.py
@graphify/doctor.py
@graphify/vault_promote.py

<interfaces>
- _DEFAULT_PROFILE additions (RESEARCH §"Runtime State Inventory" — pure additive):
  ```python
  "reverse_sync": {
      "mode": "always_ask",
      "memory_path": ".graphify/reverse-sync-log.jsonl",
      "auto_on_run": False,
  },
  "augment": {
      "allow_community": False,  # D-16
  },
  ```
- validate_profile (profile.py:765) — Pitfall 4: must reject `reverse_sync.mode` not in {"always_ask","always_copy","never_copy"}; reject non-bool `auto_on_run`, `augment.allow_community`; reject non-string `memory_path`.
- DoctorReport (doctor.py:147+) — extend dataclass with `reverse_sync_pending_conflicts: int = 0` and `reverse_sync_log_path: Path | None = None`.
- vault_promote.py:959+ — `_preflight_check_user_only_folders()` is the chokepoint (A4). When the gate detects a user-folder target, route to augment_user_file_frontmatter instead of refusing or writing whole file.
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED+GREEN): Profile schema additive defaults + validation</name>
  <files>graphify/profile.py, tests/test_profile.py</files>
  <read_first>
    - graphify/profile.py:69-197 (_DEFAULT_PROFILE, _VALID_TOP_LEVEL_KEYS)
    - graphify/profile.py:765-820 (validate_profile)
    - graphify/profile.py:660-680 (_deep_merge fallback)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pitfall 4)
  </read_first>
  <behavior>
    RED first — add to tests/test_profile.py:
    - test_default_profile_has_reverse_sync_section: load_profile with empty user profile → result.reverse_sync == {"mode":"always_ask","memory_path":".graphify/reverse-sync-log.jsonl","auto_on_run":False}
    - test_default_profile_augment_allow_community_false: result.augment == {"allow_community": False} (D-16, Success Criterion 6)
    - test_user_profile_overrides_merged: user yaml sets reverse_sync.mode=always_copy → effective mode is always_copy; other defaults preserved
    - test_validate_rejects_invalid_mode: profile {"reverse_sync":{"mode":"alway_ask"}} → validate_profile returns list with error mentioning mode (Pitfall 4)
    - test_validate_rejects_non_bool_auto_on_run: auto_on_run="true" (string) → validation error
    - test_validate_rejects_non_bool_allow_community: allow_community=1 → validation error
    - test_validate_rejects_non_string_memory_path: memory_path=42 → validation error
    - test_missing_reverse_sync_key_uses_defaults: user yaml omits reverse_sync entirely → load_profile returns defaults (no migrator needed; pure _deep_merge)
    Then GREEN:
    1. Add the two dict entries to `_DEFAULT_PROFILE` in profile.py.
    2. Confirm `_VALID_TOP_LEVEL_KEYS` already accepts `reverse_sync` and `augment` (RESEARCH says yes — Phase 70 placeholders).
    3. Extend validate_profile() to check the new keys per Pitfall 4 rules; return list[str] of errors (project convention).
  </behavior>
  <action>
    Write the 8 tests. Implement the schema additions and validators. NO migrator function needed (RESEARCH §"Runtime State Inventory" + Pattern 2: `_deep_merge(_DEFAULT_PROFILE, composed)` already supplies missing keys at profile.py:670). Add a one-line code comment near the new defaults: `# Phase 70: reverse_sync + augment are additive; missing keys merge from defaults — no migrator needed.`
  </action>
  <verify>
    <automated>pytest tests/test_profile.py -q</automated>
  </verify>
  <done>8 new tests pass; existing test_profile.py tests still pass; grep "Phase 70" graphify/profile.py shows the comment marker.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (RED+GREEN): Doctor `=== Reverse-Sync ===` section</name>
  <files>graphify/doctor.py, tests/test_doctor.py</files>
  <read_first>
    - graphify/doctor.py:147-628 (DoctorReport, format_report)
    - graphify/doctor.py: search "=== Legacy Artifacts ===" to find the Phase 69-04 section pattern
    - tests/test_doctor.py (existing test patterns)
  </read_first>
  <behavior>
    RED:
    - test_doctor_reverse_sync_section_present: format_report(DoctorReport(...)) output contains "=== Reverse-Sync ==="
    - test_doctor_reverse_sync_pending_count_zero: with no log file → output line "Pending conflicts: 0" and section is non-blocking (does not flip overall status to ERROR)
    - test_doctor_reverse_sync_pending_count_nonzero: with JSONL log containing 3 skipped_conflict entries → output "Pending conflicts: 3 — run `graphify reverse-sync` to resolve"
    - test_doctor_reverse_sync_log_missing: log path absent → output "Log: not yet created"
    - test_doctor_reverse_sync_section_non_blocking: even with 99 pending conflicts, doctor exit-status field is unchanged (non-blocking like legacy_artifact_paths)
    GREEN:
    1. Extend DoctorReport dataclass with `reverse_sync_pending_conflicts: int = 0`, `reverse_sync_log_path: Path | None = None`, `reverse_sync_log_exists: bool = False`.
    2. Populate them inside the `build_doctor_report()` (or whatever the canonical builder is — grep doctor.py for `DoctorReport(`):
       - Resolve `log_path = vault_dir / profile["reverse_sync"]["memory_path"]`.
       - If log_path exists, count lines where `json.loads(line)["action"] == "skipped_conflict"` AND `ts` is within the most recent run window. **Simplification for Phase 70:** count all skipped_conflict lines across the log (RESEARCH "deferred: deeper analytics"); document this in the docstring.
    3. In `format_report`, append section after legacy artifacts:
       ```
       === Reverse-Sync ===
       Log: {path or "not yet created"}
       Pending conflicts: {N}{ — hint if >0}
       ```
    4. Section MUST be non-blocking — do NOT touch any status/exit-code aggregation.
  </behavior>
  <action>
    Write 5 tests, then extend DoctorReport + format_report. Follow Phase 69-04 legacy-artifacts pattern verbatim (mirror the section header style and conditional hint line).
  </action>
  <verify>
    <automated>pytest tests/test_doctor.py -q</automated>
  </verify>
  <done>5 new tests pass; grep "=== Reverse-Sync ===" graphify/doctor.py == 1 hit; non-blocking invariant verified.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 3 (RED+GREEN): Wire augmentation into vault_promote chokepoint</name>
  <files>graphify/vault_promote.py, tests/test_vault_promote.py</files>
  <read_first>
    - graphify/vault_promote.py:959+ (_preflight_check_user_only_folders chokepoint)
    - graphify/vault_promote.py:1091-1092 (write chokepoint per A4)
    - graphify/vault_promote.py:702-732 (manifest-hash overwrite guard, Phase 69 — DO NOT regress)
    - graphify/augment.py (Plan 01 output)
    - tests/test_vault_promote.py (existing patterns)
  </read_first>
  <behavior>
    RED:
    - test_user_folder_write_routed_to_augmentation: target file in user_only_folders → augment_user_file_frontmatter called; full write_note NOT called; body bytes unchanged (D-07 in pipeline)
    - test_non_user_folder_write_unchanged: target in graphify_folder_mapping (not user) → normal write_note path; no augmentation call
    - test_augmentation_passes_only_allowlist_keys: graphify-derived data has random_internal_key="x" → file is NOT modified for that key (allowlist enforcement at integration level)
    - test_user_folder_body_change_still_refused: proposed write to user-folder file would mutate body bytes (not just frontmatter) → REFUSED per Phase 69 VPROF-03 contract; write_note not called; stderr contains [graphify] refusal message; confirms augmentation routing only relaxes frontmatter-allowlist, never body
    - test_augmentation_idempotent_in_pipeline: run update-vault twice on same vault → second run produces zero file changes (Pitfall 8)
    - test_community_added_when_allow_community_true: profile.augment.allow_community=true → community key written to user file
    - test_community_omitted_when_allow_community_false: default profile → community absent (Success Criterion 6)
    GREEN:
    1. Locate the `_preflight_check_user_only_folders` decision branch in vault_promote.py (A4 chokepoint at ~:959 / ~:1091).
    2. Currently Phase 69 makes this branch REFUSE the write. Narrowly relax the refusal: ONLY when the proposed write touches allowlist frontmatter keys (`related_to`, `up`, `tags`, `comments`, `analysis`, `references`, `type`, optionally `community` per D-16) AND would NOT mutate body bytes, route through augmentation. In all other cases (body byte changes, non-allowlist frontmatter keys, full-file rewrites) the Phase 69 refusal MUST still fire — VPROF-03's user-namespace ownership invariant remains intact. Concretely: (a) extract the allowlist subset of the proposed write payload's frontmatter; (b) compute proposed body vs current body byte-equality; (c) if non-allowlist keys are present OR bodies differ, REFUSE with the existing Phase 69 stderr message and skip; (d) otherwise call `augment_user_file_frontmatter(target, allowlist_subset, profile)`. If the result is `(_, [])` no change — that's fine (idempotent re-augment per Pitfall 8). If the file does NOT yet exist in user folder, do NOT create it (augmentation is for existing user files only — preserve user-namespace ownership; emit stderr `[graphify] vault_promote: user file does not exist, skipping augmentation: {rel}`).
    3. Add inline comment referencing this plan: `# Phase 70 / VPROF-03: route user-folder writes to allowlist augmentation (D-04..D-07, D-16).`
    4. Preserve manifest-hash overwrite guard at :702-732 — augmentation does NOT update the manifest (Pitfall 8: graphify must not "own" user files; idempotence via D-04/D-05 ensures next run is also clean).
    5. Import `augment_user_file_frontmatter` lazily inside the function (avoids cycle).
  </action>
  <verify>
    <automated>pytest tests/test_vault_promote.py tests/test_augment.py -q</automated>
  </verify>
  <done>6 new tests pass; existing test_vault_promote.py Phase 69 refusal tests adjusted (refusal → augmentation routing) but DO NOT regress manifest-hash overwrite guard tests; grep -c "augment_user_file_frontmatter" graphify/vault_promote.py >= 1.</done>
</task>

</tasks>

<verification>
- `pytest tests/ -q` full suite green (excluding the known pre-existing test_migration.py::test_preview_expands_risky_action_rows failure documented in RESEARCH §"Sampling Rate")
- grep -n "Phase 70" graphify/profile.py graphify/vault_promote.py — both files have provenance comments
- Manual smoke: create dual-tree vault+input, modify a vault file, run `graphify update-vault`, confirm only allowlist frontmatter keys mutate; body stays byte-identical
</verification>

<success_criteria>
- Profile schema additive defaults present (D-15 default path, D-16 community gate, D-11 warn-and-continue uses auto_on_run default false)
- Doctor section reports pending conflicts non-blockingly
- Augmentation wired into real pipeline at A4 chokepoint
- Re-running update-vault is idempotent (Pitfall 8)
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-06-doctor-and-schema-SUMMARY.md` after completion.

This is the final plan of Phase 70. Once green, run `/gsd-verify-work` to validate against the 6 success criteria in ROADMAP.md.
</output>
