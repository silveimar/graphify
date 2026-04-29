# Phase 36: Migration Guide, Skill Alignment & Regression Sweep - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29T06:36:00Z
**Phase:** 36-Migration Guide, Skill Alignment & Regression Sweep
**Areas discussed:** Migration guide shape, Skill alignment strategy, Regression gate scope, Security and sanitization proof

---

## Migration Guide Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Real workflow first | Lead with `work-vault/raw` as source and `ls-vault` as fixed Obsidian vault; generalize only in notes. | |
| Generic first | Document any `--input`/`--vault` pair, with `work-vault/raw` -> `ls-vault` as one example. | ✓ |
| Two-track | Quickstart for `work-vault/raw` -> `ls-vault`, then reusable reference for other vaults. | |
| You decide | Keep it practical and hard to misuse. | |

**User's choice:** Generic first.
**Notes:** The guide should be reusable, with the real `work-vault/raw` -> `ls-vault` flow as the canonical example.

| Option | Description | Selected |
|--------|-------------|----------|
| Manual review only | Graphify never deletes legacy notes; users inspect ORPHAN rows and decide outside graphify. | |
| Guided archive | Recommend moving legacy notes to an archive folder after review, with no automated deletion. | |
| Future cleanup command | Document current manual review and note automated cleanup is out of scope. | |
| Automatic archive | Implement automatic archive behavior in Phase 36. | ✓ |

**User's choice:** Implement automatic archiving in Phase 36.
**Notes:** This expands cleanup from guide-only behavior to apply-time archive behavior. It remains non-destructive: archive, never delete.

| Option | Description | Selected |
|--------|-------------|----------|
| Reviewed plan-id required | Archive only rows from a matching migration preview artifact. | |
| Separate archive flag | Require explicit archive flag tied to preview/apply safety checks. | |
| Own dry-run first | Require archive preview before archive apply. | |
| Archive by default on apply | Applying a reviewed migration archives legacy notes by default. | ✓ |

**User's choice:** Archive by default when using apply.
**Notes:** Planner must keep this reviewed/reversible because users may not expect moves during apply unless clearly documented.

| Option | Description | Selected |
|--------|-------------|----------|
| Vault Graphify archive | `Atlas/Sources/Graphify/Archive/Legacy/`. | |
| Root archive | `_graphify-archive/legacy/`. | |
| Artifacts archive | `graphify-out/migrations/archive/`, preserving relative paths. | ✓ |
| You decide | Preserve original relative paths and make rollback straightforward. | |

**User's choice:** Artifacts archive.
**Notes:** Archive should live outside the vault note tree.

---

## Skill Alignment Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| All variants direct | Update all shipped variants directly and add tests for shared v1.8 wording. | ✓ |
| Main then generated | Treat `skill.md` as source of truth and copy/regenerate sections into variants. | |
| Minimal drift patch | Patch only stale Obsidian output lines. | |
| You decide | All installed platforms must stop saying `_COMMUNITY_*` overview notes are generated. | |

**User's choice:** Update all variants directly.
**Notes:** Phase 36 should not leave any shipped platform with stale Obsidian export behavior.

| Option | Description | Selected |
|--------|-------------|----------|
| `update-vault` primary | Make `update-vault` primary for migration/update; keep `--obsidian` lower-level. | |
| `--obsidian` primary | Keep `/graphify --obsidian` primary and mention `update-vault` only in guide. | |
| Both by intent | `update-vault` for existing vault migration/update; `--obsidian` for generic export. | |
| You decide | Avoid confusing users about when writes happen. | ✓ |

**User's choice:** Claude/planner discretion.
**Notes:** Command framing can be chosen during planning, but write safety must be clear.

| Option | Description | Selected |
|--------|-------------|----------|
| Exact shared phrases | Every variant contains required v1.8 terms and omits `_COMMUNITY_*` generated-output claims. | ✓ |
| Section snapshot | Extract Obsidian sections from every variant and compare to a canonical block. | |
| Behavioral terms | Check command names, safety semantics, and deprecated wording without byte-for-byte matching. | |
| You decide | Catch future behavior drift without excessive brittleness. | |

**User's choice:** Exact shared phrases.
**Notes:** Tests should be direct enough to catch drift in every platform variant.

| Option | Description | Selected |
|--------|-------------|----------|
| English only | Update `README.md` and core skill files; leave localized READMEs for later. | ✓ |
| Minimal localized terms | Remove stale dangerous terms but do not fully translate the guide. | |
| Full localized sync | Update migration guidance in every localized README. | |
| You decide | Choose based on risk and effort. | |

**User's choice:** English docs only.
**Notes:** Localized docs become deferred work.

---

## Regression Gate Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Focused plus full | Focused v1.8 suites per task, then full `pytest tests/ -q` at phase verification. | |
| Focused only | Avoid full-suite cost unless verifier asks. | |
| Full each plan | Full suite after every plan touching docs/skills/tests. | |
| You decide | Evidence must be strong enough for milestone audit. | ✓ |

**User's choice:** Claude/planner discretion.
**Notes:** Planner chooses cadence, but milestone audit strength is the bar.

| Option | Description | Selected |
|--------|-------------|----------|
| Docs/skills/security | Required phrases, forbidden legacy claims, and sanitizer coverage matrix. | ✓ |
| CLI examples only | Verify documented commands and help text stay in sync. | |
| Full v1.8 matrix | Map every v1.8 requirement to a focused test or artifact. | |
| You decide | Keep tests useful rather than overfitted to wording. | |

**User's choice:** Docs/skills/security contract tests.
**Notes:** Meta-tests should prove the final contract, not just implementation helpers.

| Option | Description | Selected |
|--------|-------------|----------|
| Helper-level archive | `tests/test_migration.py` covers apply archive helpers. | |
| CLI archive | `tests/test_main_flags.py` covers `update-vault --apply --plan-id` archive behavior. | |
| Both | Helper-level and CLI-level coverage using `tmp_path`. | ✓ |
| You decide | Rollback/review story must be testable. | |

**User's choice:** Both.
**Notes:** Archive-by-default is important enough to test at both levels.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep deferred | Do not fix known baseline failures in Phase 36. | |
| Fix if blocks full | Fix only if they block the full verification gate. | ✓ |
| Include now | Include and fix them as part of the regression sweep. | |
| You decide | Based on current suite behavior. | |

**User's choice:** Fix if blocks full.
**Notes:** Do not pull unrelated baseline cleanup into Phase 36 unless it blocks verification.

---

## Security And Sanitization Proof

| Option | Description | Selected |
|--------|-------------|----------|
| Matrix in tests and verification | Each input class maps to helper plus test. | ✓ |
| Verification only | Document existing coverage without adding a matrix test. | |
| Docs table | Public-facing safety table in guide backed by tests. | |
| You decide | Maintainers should not infer sanitizer coverage from scattered tests. | |

**User's choice:** Matrix in tests and verification.
**Notes:** VER-03 should be explicit and auditable.

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve relative under artifacts | Preserve relative vault paths under `graphify-out/migrations/archive/`, validate confinement, reject traversal/symlink escapes. | |
| Flatten names | Flatten archived names into one folder with collision hashes. | |
| Manifest only | Do not move files physically; write archive manifest only. | |
| You decide | Rollback is clear and vault files are not deleted. | ✓ |

**User's choice:** Claude/planner discretion.
**Notes:** Constraints are clear rollback and no deletion; implementation can choose the safest archive layout.

| Option | Description | Selected |
|--------|-------------|----------|
| Hard prerequisite | Backup before apply/archive is required; rollback steps immediately after apply. | ✓ |
| Strong recommendation | Backup emphasized but not mandatory. | |
| Concise warning | Keep guide short and rely on preview/apply safety. | |
| You decide | Keep guide practical. | |

**User's choice:** Hard prerequisite.
**Notes:** Guide should not bury backup/rollback.

| Option | Description | Selected |
|--------|-------------|----------|
| Fully mitigated | Review-plan-driven, reversible, confined to artifacts, and covered by tests. | ✓ |
| Accepted risk | Moving legacy files during apply is intentional but a user-visible risk. | |
| Conditional | Accepted risk only if implementation cannot make it reversible/confinement-safe. | |
| You decide | Based on implementation quality. | |

**User's choice:** Fully mitigated.
**Notes:** Security artifact should not list archive-by-default as accepted risk if implementation meets the constraints.

---

## Claude's Discretion

- Exact skill command framing: planner decides how to distinguish `update-vault` and `--obsidian` while preserving write-safety clarity.
- Exact test cadence: planner decides focused/full suite cadence as long as milestone audit evidence is strong.
- Exact archive path layout under `graphify-out/migrations/archive/`: planner decides the safest layout with clear rollback and no deletion.

## Deferred Ideas

- Localized README translation/synchronization for v1.8 migration guidance.
- Any destructive cleanup or deletion workflow for legacy notes.
- Broader multi-vault selector or explicit vault-selection UX beyond the current `--vault` flag.
