---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 07
type: tdd
wave: 1
depends_on: [70-06]
files_modified:
  - graphify/vault_promote.py
  - tests/test_vault_promote.py
autonomous: true
gap_closure: true
requirements: [VPROF-03]
tags: [vault, augmentation, chokepoint, gap-closure]

must_haves:
  truths:
    - "route_user_folder_to_augmentation has at least one non-test caller inside graphify/vault_promote.py"
    - "Running update-vault against a vault with profile-pinned user_only_folders merges allowlist frontmatter into existing user files without modifying body bytes"
    - "Second update-vault run is byte-idempotent (no churn) for augmented user files"
    - "Non-allowlist frontmatter key change OR body-byte change targeting user_only_folders is still atomically refused (D-09/D-11 preserved)"
    - "Augmented user files do NOT appear in the graphify manifest"
  artifacts:
    - path: "graphify/vault_promote.py"
      provides: "Production call site invoking route_user_folder_to_augmentation at the user_only_folders chokepoint"
      contains: "route_user_folder_to_augmentation("
    - path: "tests/test_vault_promote.py"
      provides: "End-to-end integration test plus negative refusal test for the chokepoint"
      contains: "def test_user_folder_augmentation_chokepoint"
  key_links:
    - from: "graphify/vault_promote.py::_preflight_check_user_only_folders (or its caller in promote_records)"
      to: "graphify/vault_promote.py::route_user_folder_to_augmentation"
      via: "split planned write into (allowlist frontmatter delta) vs (body bytes); on allowlist-only delta, route to augmentation; otherwise refuse"
      pattern: "route_user_folder_to_augmentation\\("
    - from: "tests/test_vault_promote.py"
      to: "graphify.vault_promote.promote_records (or update-vault entrypoint)"
      via: "tmp_path Obsidian-like vault fixture with profile-pinned user_only_folders"
      pattern: "promote_records\\(|update_vault\\("
---

<objective>
Wire `route_user_folder_to_augmentation` into the production vault_promote chokepoint so user_only_folders writes that consist of allowlist-only frontmatter deltas merge into the existing user file instead of being atomically refused. This closes the single gap surfaced by 70-VERIFICATION (score 5/6, human_needed) and unblocks v1.13.

Purpose: Plan 70-06 Task 3 GREEN deferred final pipeline wiring. The helper exists and is unit-tested but has zero non-test callers. Without this, VPROF-03's augmentation half is non-functional in production.

Output: Single call site at the chokepoint plus integration tests proving end-to-end behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/STATE.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-VERIFICATION.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-06-doctor-and-schema-SUMMARY.md
@graphify/vault_promote.py
@graphify/augment.py
@tests/test_vault_promote.py

<interfaces>
Key contracts from prior plans (extract via grep before editing):

From graphify/vault_promote.py:
  - `_preflight_check_user_only_folders(...)` at ~L959 — current atomic refusal gate
  - Chokepoint at L1080–1100 — where planned writes converge before fs commit
  - `route_user_folder_to_augmentation(target_path, planned_frontmatter, planned_body, existing_path) -> bool|dict`
    at L1376 — shipped by 70-06; merges allowlist keys into existing user file, leaves body untouched

From graphify/augment.py:
  - Allowlist key constants (e.g., AUGMENT_ALLOWLIST_KEYS or similar) — the canonical set:
    likely includes `related_to`, `up`, `tags`. Use the module constant; do NOT hardcode.

Use `grep -n "route_user_folder_to_augmentation\|_preflight_check_user_only_folders\|ALLOWLIST" graphify/vault_promote.py graphify/augment.py`
to confirm exact symbols before wiring.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wire route_user_folder_to_augmentation into the user_only_folders chokepoint (RED → GREEN)</name>
  <files>graphify/vault_promote.py, tests/test_vault_promote.py</files>
  <read_first>
    - graphify/vault_promote.py (smart_outline first; then read L950–1100 chokepoint and L1370–1450 helper)
    - graphify/augment.py (find allowlist key constant; confirm name)
    - tests/test_vault_promote.py (existing route_user_folder_to_augmentation unit tests — match style/fixtures)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-VERIFICATION.md (gap.missing list)
  </read_first>
  <behavior>
    RED — write these tests FIRST, run, confirm they fail:

    1. `test_user_folder_augmentation_chokepoint_merges_allowlist_frontmatter`
       - Build tmp_path vault with profile pinning a user_only_folder (e.g., "10 People")
       - Pre-create existing user file with body "user-authored content\n" and frontmatter `{related_to: [foo]}`
       - Call promote_records (or update-vault entrypoint) with a planned write into "10 People/Alice.md"
         carrying ONLY allowlist frontmatter delta (e.g., `related_to: [bar]`, `tags: [x]`) and SAME body bytes
       - Assert: file body bytes unchanged; frontmatter merged (`related_to` contains both `foo` and `bar`,
         `tags` present); no exception raised.
       - Assert: graphify manifest does NOT include this path.

    2. `test_user_folder_augmentation_chokepoint_idempotent`
       - Same fixture; run promote_records twice with identical planned write.
       - Assert: file mtime/bytes stable on second run (or content hash equal); no duplicate list entries.

    3. `test_user_folder_augmentation_chokepoint_refuses_body_change`
       - Same fixture; planned write carries DIFFERENT body bytes.
       - Assert: refusal raised/recorded (per existing D-09/D-11 mechanism); user file untouched.

    4. `test_user_folder_augmentation_chokepoint_refuses_non_allowlist_key`
       - Same fixture; planned write carries non-allowlist frontmatter key (e.g., `community_id: 7`).
       - Assert: refusal raised/recorded; user file untouched.

    GREEN — minimal wiring at the chokepoint (vault_promote.py around L1080–1100 / _preflight_check_user_only_folders):
    - Detect when target path is inside a user_only_folders entry from the active profile
    - Read existing file (if present); split planned write into:
      (a) frontmatter delta keys
      (b) body bytes
    - If body bytes equal existing AND every delta key ∈ augment allowlist (import constant from graphify.augment):
        call `route_user_folder_to_augmentation(...)`; on success, SKIP manifest entry for this path
        (manifest tracks only graphify-owned writes per D-11)
    - Else: preserve existing atomic refusal path (no behavior change for the negative cases)

    Reference D-09 (atomicity) and D-11 (manifest scope) in code comments at the call site.
  </behavior>
  <action>
    1. Run `grep -n "route_user_folder_to_augmentation" graphify/vault_promote.py` — confirm only the
       definition currently appears (count = 1). Add the production caller; final count must be ≥ 2.
    2. Identify the allowlist constant in graphify/augment.py via grep; import it (do NOT hardcode keys).
    3. Write the four tests above in tests/test_vault_promote.py, following existing fixture patterns
       (look for `tmp_path` + profile YAML setup used in current promote_records tests). Run pytest —
       confirm RED (new tests fail; existing tests still pass).
    4. Implement the chokepoint split-and-route logic in vault_promote.py at the user_only_folders
       gate. Keep the diff small: one `if` branch that delegates to `route_user_folder_to_augmentation`
       before the existing refusal path; manifest write is gated to skip augmented paths.
    5. Run pytest; confirm GREEN. All 2235 prior tests must still pass; ≥ 4 new tests added (target ≥ 2239 total).
    6. REFACTOR pass: extract the split helper into a private `_split_planned_write_for_augmentation`
       if the inline logic exceeds ~15 lines; otherwise leave inline. Re-run pytest.
  </action>
  <verify>
    <automated>pytest tests/test_vault_promote.py -q -k "augmentation_chokepoint" && pytest tests/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "route_user_folder_to_augmentation" graphify/vault_promote.py` returns ≥ 2 (definition + call site)
    - `grep -n "augmentation_chokepoint" tests/test_vault_promote.py | wc -l` returns ≥ 4 (four new tests)
    - `pytest tests/test_vault_promote.py -q` exits 0
    - `pytest tests/ -q` exits 0 with passing count ≥ 2239 (was 2235 + 4 new)
    - Code comment at the new call site references D-09 and D-11
    - No graphify manifest entry is written for augmented user files (asserted in test 1)
  </acceptance_criteria>
  <done>
    Production code calls route_user_folder_to_augmentation at the chokepoint; allowlist-only frontmatter
    deltas merge into existing user files with body bytes preserved; non-allowlist or body-changing writes
    still atomically refuse; second run is byte-idempotent; manifest excludes augmented paths; full test
    suite green.
  </done>
</task>

</tasks>

<verification>
- All four new tests pass
- Full suite (`pytest tests/ -q`) green
- `grep -c "route_user_folder_to_augmentation" graphify/vault_promote.py` ≥ 2
- D-09 atomicity preserved for negative cases (verified by refusal tests)
- D-11 manifest scope preserved (asserted in idempotency test)
</verification>

<success_criteria>
70-VERIFICATION.md gap "User-file augmentation routing helper never called from production code" is closed.
v1.13 ships with VPROF-03 augmentation half functional end-to-end.
</success_criteria>

<output>
After completion, create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-07-augmentation-chokepoint-wiring-SUMMARY.md`
</output>
