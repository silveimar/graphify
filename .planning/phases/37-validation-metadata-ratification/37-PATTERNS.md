# Phase 37: validation-metadata-ratification - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/phases/32-profile-contract-defaults/32-VALIDATION.md` | config | transform | `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` | exact |
| `.planning/phases/33-naming-repo-identity-helpers/33-VALIDATION.md` | config | transform | `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` | exact |
| `.planning/phases/34-mapping-cluster-quality-note-classes/34-VALIDATION.md` | config | transform | `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` | role-match |
| `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VALIDATION.md` | config | transform | `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` | exact |
| `.planning/v1.8-MILESTONE-AUDIT.md` | config | transform | `.planning/milestones/v1.7-MILESTONE-AUDIT.md` | exact |

## Pattern Assignments

### `.planning/phases/32-profile-contract-defaults/32-VALIDATION.md` (config, transform)

**Analog:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md`

**Frontmatter ratification pattern** (lines 1-9):
```markdown
---
phase: 36
slug: migration-guide-skill-alignment-regression-sweep
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
completed: 2026-04-29
---
```

**Per-task status pattern (all green with evidence-linked commands)** (lines 38-53):
```markdown
| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | MIG-05, VER-01 | T-36-01 / T-36-02 | Archive only after reviewed apply succeeds; no delete path | unit | `pytest tests/test_migration.py -q` | yes | green |
| 36-01-02 | 01 | 1 | MIG-05, VER-01 | T-36-03 | Archive source/destination paths are confined and rollback metadata exists | unit | `pytest tests/test_migration.py -q` | yes | green |
```

**Wave 0 completion pattern** (lines 56-63):
```markdown
## Wave 0 Requirements

- [x] `tests/test_migration.py` — archive helper-level tests for apply archive behavior and archive path confinement.
- [x] `tests/test_main_flags.py` — CLI-level apply archive evidence test for `update-vault --apply --plan-id`.
- [x] `tests/test_skill_files.py` — required v1.8 phrase and forbidden stale `_COMMUNITY_*` generated-output claim tests.
- [x] `tests/test_v18_security_matrix.py` — sanitizer coverage matrix for VER-03.
```

**Sign-off completion pattern** (lines 85-95):
```markdown
## Validation Sign-Off

- [x] All tasks have automated verify commands or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 90s.
- [x] `nyquist_compliant: true` set in frontmatter after execution evidence passes.

**Approval:** Nyquist-compliant after focused and full regression gates passed.
```

**Evidence source to ratify from**: `.planning/phases/32-profile-contract-defaults/32-VERIFICATION.md` lines 1-7, 74-75
```markdown
---
phase: 32-profile-contract-defaults
verified: 2026-04-29T00:40:08Z
status: passed
score: 12/12 must-haves verified
---
...
| Focused Phase 32 test suite | `pytest tests/test_profile.py tests/test_mapping.py tests/test_doctor.py tests/test_export.py -q` | `261 passed, 1 xfailed, 2 warnings` | PASS |
```

---

### `.planning/phases/33-naming-repo-identity-helpers/33-VALIDATION.md` (config, transform)

**Analog:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md`

**Task-row status normalization pattern** (lines 40-53):
```markdown
| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-03-01 | 03 | 2 | VER-02 | T-36-05 | Every shipped skill variant includes required v1.8 phrases | docs contract | `pytest tests/test_skill_files.py -q` | yes | green |
| 36-03-02 | 03 | 2 | VER-02 | T-36-05 | Skill variants omit stale generated `_COMMUNITY_*` overview claims | docs contract | `pytest tests/test_skill_files.py -q` | yes | green |
```

**Final regression evidence section pattern** (lines 65-74):
```markdown
## Final Regression Evidence

| Gate | Command | Result |
|------|---------|--------|
| Task 36-04 matrix/helper gate | `pytest tests/test_v18_security_matrix.py tests/test_profile.py tests/test_templates.py tests/test_naming.py tests/test_migration.py -q` | 435 passed, 1 xfailed, 2 warnings in 8.32s |
| Phase 36 focused gate | `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_docs.py tests/test_v18_security_matrix.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q` | 467 passed, 1 xfailed, 2 warnings in 33.42s |
| Full suite gate | `pytest tests/ -q` | 1896 passed, 1 xfailed, 8 warnings in 71.41s |
```

**Evidence source to ratify from**: `.planning/phases/33-naming-repo-identity-helpers/33-VERIFICATION.md` lines 1-7, 75
```markdown
---
phase: 33-naming-repo-identity-helpers
verified: 2026-04-29T02:51:14Z
status: passed
score: 8/8 must-haves verified
---
...
| Phase 33 helper, profile, export, template, and CLI behavior | `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_export.py tests/test_main_flags.py -q` | `437 passed, 1 xfailed, 2 warnings` | PASS |
```

---

### `.planning/phases/34-mapping-cluster-quality-note-classes/34-VALIDATION.md` (config, transform)

**Analog:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md`

**Missing frontmatter insertion pattern** (copy structure from lines 1-9):
```markdown
---
phase: 34
slug: mapping-cluster-quality-note-classes
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
completed: 2026-04-29
---
```

**Sign-off checkbox contract pattern** (lines 87-94):
```markdown
- [x] All tasks have automated verify commands or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 90s.
- [x] `nyquist_compliant: true` set in frontmatter after execution evidence passes.

**Approval:** Nyquist-compliant after focused and full regression gates passed.
```

**Evidence source to ratify from**: `.planning/phases/34-mapping-cluster-quality-note-classes/34-VERIFICATION.md` lines 1-6, 78-80
```markdown
---
phase: 34-mapping-cluster-quality-note-classes
verified: 2026-04-29T04:31:00Z
status: passed
score: 12/12 must-haves verified
---
...
| Focused Phase 34 test gate | `pytest tests/test_mapping.py tests/test_templates.py tests/test_export.py tests/test_profile.py tests/test_naming.py -q` | `485 passed, 1 xfailed, 2 warnings` | PASS |
| Full suite | `pytest tests/ -q` | `1857 passed, 1 xfailed, 8 warnings` | PASS |
```

---

### `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VALIDATION.md` (config, transform)

**Analog:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md`

**Ratified wave/task/checklist shape** (lines 56-63, 85-94):
```markdown
## Wave 0 Requirements

- [x] `tests/test_migration.py` — archive helper-level tests for apply archive behavior and archive path confinement.
- [x] `tests/test_main_flags.py` — CLI-level apply archive evidence test for `update-vault --apply --plan-id`.
- [x] `tests/test_skill_files.py` — required v1.8 phrase and forbidden stale `_COMMUNITY_*` generated-output claim tests.
- [x] `tests/test_v18_security_matrix.py` — sanitizer coverage matrix for VER-03.

## Validation Sign-Off
...
**Approval:** Nyquist-compliant after focused and full regression gates passed.
```

**Evidence source to ratify from**: `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md` lines 1-7, 80-81
```markdown
---
phase: 35-templates-export-plumbing-dry-run-migration-visibility
verified: 2026-04-29T06:13:23Z
status: passed
score: 12/12 must-haves verified
---
...
| CLI preview/apply gate/repo drift/repo metadata focused behavior | `pytest ... -q` | `7 passed, 2 warnings` | PASS |
| Phase-level regression gate | `pytest tests/ -q` | Orchestrator reported `1871 passed, 1 xfailed, 8 warnings` | PASS |
```

---

### `.planning/v1.8-MILESTONE-AUDIT.md` (config, transform)

**Analog:** `.planning/milestones/v1.7-MILESTONE-AUDIT.md`

**Frontmatter debt/score schema pattern** (lines 1-34):
```markdown
---
milestone: v1.7
milestone_name: Vault Adapter UX & Template Polish
audited: 2026-04-28T14:46:00-06:00
status: passed
scores:
  requirements: 13/13
  phases: 5/5
  integration: deferred
  flows: deferred
  nyquist: 5/5
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - phase: 27-vault-detection-profile-driven-output-routing
    items:
      - "27-VALIDATION.md frontmatter status=draft ... Cosmetic — non-blocking."
...
nyquist:
  compliant_phases: ["27", "28", "29", "30", "31"]
  partial_phases: []
  missing_phases: []
---
```

**Verdict section pattern** (lines 36-56):
```markdown
# v1.7 Milestone Audit (passed) — Vault Adapter UX & Template Polish
...
**Verdict: `passed`** — 13/13 requirements satisfied, 5/5 phases verified, 5/5 Nyquist ratified, no documentation drift, no blockers.
...
- Status: tech_debt → **passed**
```

**Current v1.8 debt rows to reconcile/close**: `.planning/v1.8-MILESTONE-AUDIT.md` lines 16-27, 112-118
```markdown
tech_debt:
  - phase: 32-profile-contract-defaults
    items:
      - "VALIDATION.md remains draft metadata with nyquist_compliant: false even though phase verification passed."
...
## Tech Debt

- Normalize Phase 32, 33, 34, and 35 `*-VALIDATION.md` metadata so `nyquist_compliant` and task rows reflect the already-passed verification evidence.
```

## Shared Patterns

### Nyquist Frontmatter Contract
**Source:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` (lines 1-9)  
**Apply to:** `32-VALIDATION.md`, `33-VALIDATION.md`, `34-VALIDATION.md`, `35-VALIDATION.md`
```markdown
---
phase: <phase number>
slug: <phase slug>
status: draft
nyquist_compliant: true
wave_0_complete: true
created: <existing date>
completed: <ratification date>
---
```

### Evidence-First Status Ratification
**Source:** `32-VERIFICATION.md`, `33-VERIFICATION.md`, `34-VERIFICATION.md`, `35-VERIFICATION.md`  
**Apply to:** All `32-35` validation per-task rows and sign-off checklists
```markdown
| ... | Automated Command | ... | Status |
| ... | `pytest ... -q` | ... | green |
...
- [x] All tasks have automated verify commands or Wave 0 dependencies.
...
**Approval:** Nyquist-compliant after focused and full regression gates passed.
```

### Milestone Audit Closure Shape
**Source:** `.planning/milestones/v1.7-MILESTONE-AUDIT.md` (lines 1-34, 50-56)  
**Apply to:** `.planning/v1.8-MILESTONE-AUDIT.md`
```markdown
status: passed
...
tech_debt: []
...
nyquist:
  partial_phases: []
...
**Verdict: `passed`**
```

## No Analog Found

None. All expected Phase 37 touch points have direct analogs in existing v1.7/v1.8 planning artifacts.

## Metadata

**Analog search scope:** `.planning/phases/32-*` through `.planning/phases/36-*`, `.planning/v1.8-MILESTONE-AUDIT.md`, `.planning/milestones/v1.7-MILESTONE-AUDIT.md`  
**Files scanned:** 12  
**Pattern extraction date:** 2026-04-29
