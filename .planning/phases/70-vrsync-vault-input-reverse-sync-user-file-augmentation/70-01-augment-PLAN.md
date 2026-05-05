---
phase: 70
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - graphify/augment.py
  - tests/test_augment.py
  - tests/conftest.py
autonomous: true
requirements: [VPROF-03]
must_haves:
  truths:
    - "Augmentation merges only allowlist frontmatter keys into user files (D-04, D-05)"
    - "Body content is byte-identical before vs after augmentation (D-07, Success Criterion 5)"
    - "community key only written when profile.augment.allow_community is true (D-16, Success Criterion 6)"
    - "Re-augmenting an already-augmented file produces zero diff (D-04/D-05 idempotence)"
  artifacts:
    - path: "graphify/augment.py"
      provides: "augment_user_file_frontmatter() helper"
      exports: ["augment_user_file_frontmatter"]
    - path: "tests/test_augment.py"
      provides: "Allowlist merge + body-byte-identical property test"
  key_links:
    - from: "graphify/augment.py"
      to: "graphify/merge.py"
      via: "_parse_frontmatter / _find_body_start imports"
      pattern: "from graphify.merge import _parse_frontmatter"
    - from: "graphify/augment.py"
      to: "graphify/profile.py"
      via: "_dump_frontmatter import"
      pattern: "from graphify.profile import _dump_frontmatter"
---

<objective>
Implement allowlist frontmatter merge for user files. Lists union with user order preserved; scalars only-if-absent; body bytes identical; community key gated. This is the augmentation half of VPROF-03 (success criteria 5 and 6).

Purpose: Enforce the contract "graphify may only ADD specified frontmatter keys to user-authored vault files; never touch the body".
Output: `graphify/augment.py` with `augment_user_file_frontmatter()`, plus full unit + property tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-VALIDATION.md
@graphify/merge.py
@graphify/profile.py

<interfaces>
Reuse (do NOT re-implement):
- `graphify.merge._parse_frontmatter(text: str) -> dict | None` (merge.py:198)
- `graphify.merge._find_body_start(text: str) -> int` (merge.py:614-628)
- `graphify.profile._dump_frontmatter(fm: dict) -> str` (profile.py:1753) — does NOT emit trailing newline
- Allowlist (D-04 lists): {"tags", "related_to", "up", "references"}
- Allowlist (D-05 scalars): {"comments", "analysis", "type"} (+ "community" iff augment.allow_community)
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Write failing tests for augment_user_file_frontmatter</name>
  <files>tests/test_augment.py, tests/conftest.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pattern 3, Pitfalls 2/3/7)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md (D-04..D-07, D-16)
    - graphify/merge.py (lines 130-280, 600-660 for _parse_frontmatter / _find_body_start)
    - graphify/profile.py (lines 1745-1800 for _dump_frontmatter)
    - tests/test_merge.py (existing patterns)
  </read_first>
  <behavior>
    - test_list_keys_union_preserve_order: existing tags=[a,b]; augment with [b,c]; result tags=[a,b,c] (D-04)
    - test_scalar_keys_only_if_absent: existing type="note"; augment with type="ml"; result still "note" (D-05)
    - test_scalar_added_when_absent: no type; augment type="ml"; result type="ml"
    - test_community_gate_default_false: augment community="x" with profile augment={}; community NOT in result (D-16)
    - test_community_gate_enabled: augment with augment={"allow_community": True}; community present
    - test_non_allowlist_keys_ignored: augment with random_key="x"; not in result
    - test_body_byte_identical_property: 50 randomized markdown bodies (LF/CRLF mix, BOM, embedded ---, empty body, trailing-newline variants); for each, body bytes after _find_body_start must equal original body (D-07)
    - test_idempotent_reaugment: augment twice with same data; second call returns ([], no changed_keys)
    - test_d06_stateless_readd: augment with tags=["a"]; manually strip tags from file frontmatter (simulating user delete); augment again with tags=["a"]; assert tags=["a"] is present in result (graphify re-adds the deleted key — stateless merge per D-06)
    - test_returns_changed_keys_list: returned tuple second element lists which keys were modified
    - test_atomic_write: writes via .tmp + os.replace; mid-failure leaves original intact
    - conftest.py: add `make_user_file(tmp_path, frontmatter, body)` factory + `random_markdown_body(seed)` generator
  </behavior>
  <action>
    Create tests/test_augment.py with all 10 test functions above. Use stdlib `random` (no Hypothesis — per A1 in RESEARCH). Property test loops 50 iterations with `random.Random(seed)`. Each test imports `from graphify.augment import augment_user_file_frontmatter`. Run pytest — ALL must FAIL because graphify/augment.py does not exist yet.
  </action>
  <verify>
    <automated>pytest tests/test_augment.py -q 2>&1 | grep -E "(error|ModuleNotFoundError|failed)" </automated>
  </verify>
  <done>tests/test_augment.py exists with 10+ tests; all fail with ModuleNotFoundError or AssertionError; tests/conftest.py exports make_user_file fixture</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Implement graphify/augment.py to pass all tests</name>
  <files>graphify/augment.py</files>
  <read_first>
    - tests/test_augment.py (just written)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pattern 3 reference implementation)
    - graphify/merge.py:198, :614 (imports)
    - graphify/profile.py:1753 (_dump_frontmatter contract)
  </read_first>
  <action>
    Create graphify/augment.py with module docstring and:
    ```python
    from __future__ import annotations
    """Allowlist frontmatter augmentation for user files (Phase 70 / VPROF-03 augmentation half).

    Body bytes are guaranteed byte-identical (D-07). DO NOT use cache.file_hash here
    (it strips frontmatter). DO NOT introduce PyYAML on the write path.
    """
    import os
    from pathlib import Path
    from graphify.merge import _parse_frontmatter, _find_body_start
    from graphify.profile import _dump_frontmatter

    _ALLOWLIST_LISTS = frozenset({"tags", "related_to", "up", "references"})  # D-04
    _ALLOWLIST_SCALARS = frozenset({"comments", "analysis", "type"})           # D-05

    def augment_user_file_frontmatter(
        target: Path,
        augmentations: dict,
        profile: dict,
    ) -> tuple[Path, list[str]]:
        ...
    ```
    Implementation rules:
    1. Read with `target.read_text(encoding="utf-8")`; strip leading BOM if present (Pitfall 3).
    2. `body_start = _find_body_start(text); body = text[body_start:]` — capture before mutation.
    3. `existing_fm = _parse_frontmatter(text) or {}`.
    4. Compute scalar allowlist: include "community" iff `profile.get("augment", {}).get("allow_community", False)`.
    5. Loop augmentations: list keys → union preserving user order, append new items at end (D-04). Scalar keys → write only if absent (D-05).
    6. If no changes, return `(target, [])` without rewriting.
    7. Re-emit: `new_fm = _dump_frontmatter(merged)` then concat with body. Pitfall 2: `_dump_frontmatter` has NO trailing newline; insert `"\n"` between fm and body unless body already starts with `\n`.
    8. Pitfall 7: Preserve original file's trailing-newline state — if original text ended with `\n`, ensure output does too.
    9. Atomic write via `tmp = target.with_suffix(target.suffix + ".tmp"); tmp.write_text(...); os.replace(tmp, target)`.
    10. Return `(target, sorted(changed_keys))` for deterministic output.
  </action>
  <verify>
    <automated>pytest tests/test_augment.py -q</automated>
  </verify>
  <done>All tests in test_augment.py pass; module exports `augment_user_file_frontmatter`; grep -c '_ALLOWLIST_LISTS' graphify/augment.py == 1; grep 'allow_community' graphify/augment.py shows D-16 gate.</done>
</task>

<task type="execute">
  <name>Task 3 (REFACTOR): Lint pass + integrate import path</name>
  <files>graphify/augment.py</files>
  <read_first>
    - graphify/augment.py (just written)
    - graphify/__init__.py (lazy-load convention)
  </read_first>
  <action>
    Review augment.py for:
    1. `from __future__ import annotations` is the first import (project convention).
    2. All public functions have type hints using `dict[K,V]` and `str | None` style (not `Dict`/`Optional`).
    3. Module docstring present.
    4. No `print()` calls (this module is library code; warnings belong upstream).
    5. No new top-level dependencies imported (stdlib only + intra-package).
    Do NOT add to graphify/__init__.py — call sites import directly per project convention (e.g. `from graphify.augment import augment_user_file_frontmatter`).
  </action>
  <verify>
    <automated>pytest tests/test_augment.py -q && python3 -c "from graphify.augment import augment_user_file_frontmatter; print('ok')"</automated>
  </verify>
  <done>All tests pass; import works; no lint regressions in CI matrix.</done>
</task>

</tasks>

<verification>
- `pytest tests/test_augment.py -q` all green (10+ tests including property test)
- `pytest tests/ -q` no regressions in test_merge.py / test_profile.py
- grep -c "PyYAML\|yaml.safe_load" graphify/augment.py == 0 (anti-pattern check)
</verification>

<success_criteria>
- augment_user_file_frontmatter writes only allowlist keys
- Property test passes 50 random body bytes round-trip byte-identical
- community key gated by profile.augment.allow_community
- Idempotent re-augment produces zero changes
</success_criteria>

<output>
After completion, create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-01-augment-SUMMARY.md` summarizing: files created, tests added, decisions confirmed (D-04..D-07, D-16), and any deviations.
</output>
