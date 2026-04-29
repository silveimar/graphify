# Phase 37: validation-metadata-ratification - Research

**Researched:** 2026-04-29  
**Domain:** GSD Nyquist validation metadata normalization for completed v1.8 phases  
**Confidence:** HIGH

## User Constraints

No `37-CONTEXT.md` exists in this phase directory, so there are no discuss-phase locked decisions to copy verbatim. [VERIFIED: gsd-sdk init.phase-op has_context=false]

## Summary

Phase 37 is an audit-tech-debt cleanup phase, not a behavior-change phase. The roadmap and milestone audit both define the target narrowly: normalize Nyquist metadata in Phase 32-35 validation artifacts so automation can discover them consistently without re-implementing or re-verifying shipped features. [VERIFIED: .planning/ROADMAP.md, .planning/v1.8-MILESTONE-AUDIT.md]

The core implementation surface is under `.planning/phases/*-*/` documentation files (`32-VALIDATION.md` through `35-VALIDATION.md`), with verification evidence already present in corresponding `*-VERIFICATION.md` files and passing test gates. The correct strategy is to ratify metadata and task/status tables to match existing evidence, then re-run milestone audit checks. [VERIFIED: .planning/phases/32-*/32-VALIDATION.md, .planning/phases/32-*/32-VERIFICATION.md, .planning/phases/33-*/33-VALIDATION.md, .planning/phases/33-*/33-VERIFICATION.md, .planning/phases/34-*/34-VALIDATION.md, .planning/phases/34-*/34-VERIFICATION.md, .planning/phases/35-*/35-VALIDATION.md, .planning/phases/35-*/35-VERIFICATION.md]

**Primary recommendation:** Treat Phase 37 as a deterministic metadata reconciliation pass: promote 32/33/35 from draft to ratified Nyquist metadata, add missing Nyquist frontmatter/ratification structure to 34, and ensure all status rows/sign-off checkboxes reflect already-passed evidence before rerunning `/gsd-audit-milestone`. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Normalize phase validation metadata | Planning docs (`.planning/phases`) | GSD audit tooling (`gsd-sdk`, `/gsd-audit-milestone`) | Source-of-truth metadata lives in phase `*-VALIDATION.md`; audit consumes it. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md] |
| Preserve shipped runtime behavior | Verification docs (`*-VERIFICATION.md`) | Test suite (`pytest`) | Behavior is already passed; phase goal is metadata parity with existing evidence. [VERIFIED: .planning/ROADMAP.md, .planning/phases/32-*/32-VERIFICATION.md, .planning/phases/33-*/33-VERIFICATION.md, .planning/phases/34-*/34-VERIFICATION.md, .planning/phases/35-*/35-VERIFICATION.md] |
| Prove debt closure | Milestone audit report | State/roadmap status docs | Success criterion explicitly requires no validation-metadata debt after rerun. [VERIFIED: .planning/ROADMAP.md, .planning/v1.8-MILESTONE-AUDIT.md] |

## Project Constraints (from .cursor/rules/)

No `.cursor/rules/` directory exists in this repository, so no additional project rule directives were discovered for this phase. [VERIFIED: ls .cursor/rules returned no files]

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| Python | 3.10.19 | Runs local tooling and scripts used by GSD flow | Repository baseline is Python 3.10+ and CI validates 3.10/3.12. [VERIFIED: python3 --version, CLAUDE.md] |
| pytest | 9.0.3 | Validation evidence source of already-passed phase gates | Existing validation/verification docs cite pytest gates as evidence backbone. [VERIFIED: pytest --version, 32-36 VERIFICATION/VALIDATION docs] |
| GSD planning artifacts | N/A (repo-local markdown contract) | Machine-readable Nyquist metadata for phase audit automation | Milestone audit tech debt is explicitly metadata inconsistency across these docs. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md] |

### Supporting
| Library/Tool | Version | Purpose | When to Use |
|--------------|---------|---------|-------------|
| `gsd-sdk query init.phase-op` | N/A | Resolve phase paths and workflow flags (`commit_docs`, `nyquist_validation`) | Start-of-phase context hydration. [VERIFIED: command output for phase 37] |
| `/gsd-audit-milestone` | N/A | Validate debt closure after metadata updates | End-of-phase proof for roadmap success criterion #3. [VERIFIED: .planning/ROADMAP.md] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Updating 32-35 validation docs | Re-run implementation waves and regenerate all evidence | Unnecessary scope/behavior risk; phase requirement is metadata ratification only. [VERIFIED: .planning/ROADMAP.md] |
| Manual narrative-only notes | Structured Nyquist frontmatter + status tables | Narrative-only updates do not satisfy automated discovery requirements. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md] |

## Architecture Patterns

### System Architecture Diagram

```text
Inputs (existing evidence)
  ├─ 32-35 VERIFICATION.md (passed truths + test outputs)
  ├─ 32-35 VALIDATION.md (stale/missing nyquist metadata)
  └─ v1.8-MILESTONE-AUDIT.md (tech debt findings)
            |
            v
Phase 37 metadata ratification pass
  ├─ normalize frontmatter fields (status, nyquist_compliant, wave_0_complete, completed)
  ├─ reconcile Per-Task rows to green evidence where already verified
  └─ reconcile Validation Sign-Off checklist to true state
            |
            v
Outputs
  ├─ updated 32-35 VALIDATION.md files
  └─ rerun /gsd-audit-milestone => no v1.8 validation metadata debt
```

### Recommended Project Structure

```text
.planning/
├── phases/
│   ├── 32-profile-contract-defaults/
│   │   ├── 32-VALIDATION.md        # ratify metadata/status
│   │   └── 32-VERIFICATION.md      # evidence source (read-only)
│   ├── 33-naming-repo-identity-helpers/
│   │   ├── 33-VALIDATION.md        # ratify metadata/status
│   │   └── 33-VERIFICATION.md      # evidence source (read-only)
│   ├── 34-mapping-cluster-quality-note-classes/
│   │   ├── 34-VALIDATION.md        # add Nyquist frontmatter + ratify
│   │   └── 34-VERIFICATION.md      # evidence source (read-only)
│   └── 35-templates-export-plumbing-dry-run-migration-visibility/
│       ├── 35-VALIDATION.md        # ratify metadata/status
│       └── 35-VERIFICATION.md      # evidence source (read-only)
└── v1.8-MILESTONE-AUDIT.md         # post-ratification debt check
```

### Pattern 1: Evidence-First Metadata Ratification
**What:** Update `*-VALIDATION.md` metadata only when there is explicit proof in `*-VERIFICATION.md` (passed requirements and commands). [VERIFIED: 32-35 VERIFICATION docs]
**When to use:** Post-verification cleanup phases where behavior is already shipped. [VERIFIED: .planning/ROADMAP.md]
**Example (frontmatter normalization target):**
```markdown
---
phase: 33
slug: naming-repo-identity-helpers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---
```

### Pattern 2: Canonical Shape Alignment with a Known-Good Phase
**What:** Use `36-VALIDATION.md` as structural reference for fields/sections that automation expects. [VERIFIED: .planning/phases/36-*/36-VALIDATION.md]
**When to use:** When one phase is already compliant and sibling phases are partial/non-compliant. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md]
**Example:** Ensure each ratified file includes explicit sign-off status and Nyquist flags in frontmatter. [VERIFIED: .planning/phases/36-*/36-VALIDATION.md]

### Anti-Patterns to Avoid
- **Re-testing instead of ratifying:** Re-running broad implementation work adds scope and can introduce regressions in a docs-only debt phase. [VERIFIED: .planning/ROADMAP.md]
- **Marking green without trace:** `nyquist_compliant: true` without matching task/status/sign-off evidence defeats audit trust. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md]
- **Changing shipped behavior files:** Phase 37 should not touch runtime modules under `graphify/` unless a blocker is discovered. [VERIFIED: .planning/ROADMAP.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nyquist compliance inference | Custom ad-hoc checklist outside phase docs | Existing `*-VALIDATION.md` contract + phase verifier evidence | Existing process already defines expected metadata and evidence path. [VERIFIED: 32-36 VALIDATION/VERIFICATION docs] |
| Debt closure proof | New bespoke scripts for one phase | Existing `/gsd-audit-milestone` workflow | Success criterion already targets this command/output. [VERIFIED: .planning/ROADMAP.md] |

**Key insight:** Phase 37 is a contract reconciliation task; leverage existing GSD artifact conventions rather than inventing a new validation schema. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md, 36-VALIDATION.md]

## Common Pitfalls

### Pitfall 1: Frontmatter-Only Fixes
**What goes wrong:** `nyquist_compliant` is flipped to `true` but per-task rows remain pending and sign-off remains unchecked. [VERIFIED: 32/33/35 VALIDATION current state]
**Why it happens:** Frontmatter is easy to edit; internal tables are longer and often skipped.
**How to avoid:** Reconcile all sections in one pass (frontmatter, per-task status, Wave 0, sign-off, approval line) against verification artifacts.
**Warning signs:** Mixed states like `status: draft` + all verification already passed.

### Pitfall 2: Missing Nyquist Frontmatter in 34
**What goes wrong:** `34-VALIDATION.md` lacks machine-readable Nyquist keys entirely. [VERIFIED: .planning/phases/34-*/34-VALIDATION.md]
**Why it happens:** The file was authored as narrative validation guidance, not ratified metadata.
**How to avoid:** Add the same minimal frontmatter schema used by neighboring compliant phases.
**Warning signs:** Audit keeps reporting “exists but has no Nyquist frontmatter.”

### Pitfall 3: Diverging from Verification Evidence
**What goes wrong:** Validation rows claim pass/fail states that do not match command outputs in `*-VERIFICATION.md`.
**Why it happens:** Manual transcription from memory.
**How to avoid:** Copy exact command/result lines from verification docs when setting green status.
**Warning signs:** Inconsistent pass counts between validation and verification files.

## Likely Touch Points

- `.planning/phases/32-profile-contract-defaults/32-VALIDATION.md` - convert draft metadata/checklists to ratified status based on 12/12 verification. [VERIFIED: 32-VERIFICATION.md]
- `.planning/phases/33-naming-repo-identity-helpers/33-VALIDATION.md` - same ratification pattern based on 8/8 verification. [VERIFIED: 33-VERIFICATION.md]
- `.planning/phases/34-mapping-cluster-quality-note-classes/34-VALIDATION.md` - add Nyquist frontmatter and ratified sign-off structure; align with 12/12 passed evidence. [VERIFIED: 34-VERIFICATION.md]
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VALIDATION.md` - ratify draft metadata/checklists from passed verification. [VERIFIED: 35-VERIFICATION.md]
- `.planning/v1.8-MILESTONE-AUDIT.md` - re-check expected removal of validation-metadata tech debt after updates. [VERIFIED: roadmap phase 37 success criterion #3]

## Code Examples

### Current draft pattern that needs ratification
```markdown
---
phase: 35
slug: templates-export-plumbing-dry-run-migration-visibility
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---
```

### Known-good ratified pattern in v1.8
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

## Sequencing Advice

1. Update Phase 34 first (it is structurally incomplete: no Nyquist frontmatter). [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md, 34-VALIDATION.md]
2. Ratify 32, 33, and 35 in ascending order, using each phase’s own verification report as evidence source. [VERIFIED: 32-35 VERIFICATION docs]
3. Run focused consistency check by scanning these fields across 32-35: `status`, `nyquist_compliant`, `wave_0_complete`, sign-off checkboxes, per-task status markers.
4. Re-run `/gsd-audit-milestone` and ensure v1.8 reports no validation-metadata debt.
5. Only after audit is clean, close the phase and update state artifacts if workflow requires it.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Draft validation metadata in completed phases | Nyquist ratification expected for automation | Identified in v1.8 audit (2026-04-29) | Prevents false partial-compliance signals at milestone close. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md] |
| Narrative-only validation guidance (Phase 34) | Machine-readable Nyquist frontmatter + sign-off contract | Needed for Phase 37 closeout | Enables consistent automated discovery across all v1.8 phases. [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md, 34-VALIDATION.md, 36-VALIDATION.md] |

## Open Questions (Resolved)

1. **Should `status` become `passed` (or stay `draft`) in ratified validation files? — RESOLVED**
   - Resolution: Keep `status` vocabulary consistent with existing v1.8 convention and rely on deterministic Nyquist markers (`nyquist_compliant`, `wave_0_complete`, `completed`) for gate state.
   - Rationale: `36-VALIDATION.md` already demonstrates Nyquist compliance with `status: draft`; checker concerns target deterministic gate assertions, not status vocabulary drift.

2. **Should Phase 37 update old command-result counts verbatim or reference verification docs only? — RESOLVED**
   - Resolution: Use explicit green task/status rows in `*-VALIDATION.md`, and keep command strings/result claims aligned with corresponding `*-VERIFICATION.md` evidence.
   - Rationale: This preserves audit readability while preventing false-pass narrative summaries detached from verification artifacts.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `python3` | GSD/pytest execution and validation checks | ✓ | 3.10.19 | — |
| `pytest` | Reconfirm verification/test evidence references | ✓ | 9.0.3 | — |
| `gsd-sdk` + `/gsd-audit-milestone` workflow | Milestone debt closure proof | ✓ (phase init command works) | — | If command alias unavailable, use equivalent GSD command wrapper in current shell profile. [ASSUMED] |

**Missing dependencies with no fallback:** None identified. [VERIFIED: local command checks]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 [VERIFIED: `pytest --version`] |
| Config file | none (direct pytest invocation) [VERIFIED: CLAUDE.md + existing VALIDATION docs] |
| Quick run command | `pytest tests/test_profile.py tests/test_mapping.py tests/test_naming.py tests/test_templates.py tests/test_export.py tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_v18_security_matrix.py -q` [VERIFIED: .planning/v1.8-MILESTONE-AUDIT.md] |
| Full suite command | `pytest tests/ -q` [VERIFIED: CLAUDE.md] |

### Phase Requirements -> Test Map

Phase 37 has no new product requirement IDs (`Requirements: None — audit tech debt only`), so validation maps to artifact integrity and audit closure checks. [VERIFIED: .planning/ROADMAP.md]

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| META-37-01 | 32/33/34/35 validation docs expose consistent Nyquist metadata | artifact consistency | `python3 - <<'PY'\nfrom pathlib import Path\nfor p in Path('.planning/phases').glob('3[2-5]-*/3[2-5]-VALIDATION.md'):\n    print(p)\nPY` | ✅ |
| META-37-02 | Validation task/sign-off sections align with passed verification evidence | docs parity | `rg \"status:|nyquist_compliant|wave_0_complete|Approval:\" .planning/phases/3[2-5]-*/3[2-5]-VALIDATION.md` | ✅ |
| META-37-03 | v1.8 milestone audit reports no validation-metadata debt | milestone audit | `/gsd-audit-milestone` | ✅ (command available in workflow) [ASSUMED] |

### Sampling Rate
- **Per task commit:** run artifact consistency checks above.
- **Per wave merge:** re-open 32-35 validation + verification docs and verify parity.
- **Phase gate:** rerun milestone audit and confirm debt removal.

### Wave 0 Gaps
- [ ] Add Nyquist frontmatter and completion metadata to `34-VALIDATION.md`.
- [ ] Ratify per-task statuses and sign-off checkboxes in `32-VALIDATION.md`.
- [ ] Ratify per-task statuses and sign-off checkboxes in `33-VALIDATION.md`.
- [ ] Ratify per-task statuses and sign-off checkboxes in `35-VALIDATION.md`.

## Security Domain

This phase is documentation metadata only; no new runtime input surfaces are introduced. [VERIFIED: .planning/ROADMAP.md]

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (no auth changes) |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (artifact integrity checks) | deterministic frontmatter/status schema parity against verification artifacts |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| False-positive compliance metadata | Tampering | Require evidence-first reconciliation from `*-VERIFICATION.md` before setting Nyquist flags. |
| Drift between docs and executable evidence | Repudiation | Keep command outputs and requirement coverage rows synchronized with verification reports. |

## Sources

### Primary (HIGH confidence)
- `.planning/ROADMAP.md` - Phase 37 goal, scope, success criteria. [VERIFIED: repo file]
- `.planning/v1.8-MILESTONE-AUDIT.md` - explicit metadata debt findings and closure target. [VERIFIED: repo file]
- `.planning/phases/32-profile-contract-defaults/32-VALIDATION.md` and `32-VERIFICATION.md` - current mismatch and authoritative evidence. [VERIFIED: repo files]
- `.planning/phases/33-naming-repo-identity-helpers/33-VALIDATION.md` and `33-VERIFICATION.md` - current mismatch and authoritative evidence. [VERIFIED: repo files]
- `.planning/phases/34-mapping-cluster-quality-note-classes/34-VALIDATION.md` and `34-VERIFICATION.md` - missing frontmatter and authoritative evidence. [VERIFIED: repo files]
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VALIDATION.md` and `35-VERIFICATION.md` - current mismatch and authoritative evidence. [VERIFIED: repo files]
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-VALIDATION.md` - compliant reference shape. [VERIFIED: repo file]
- `.planning/config.json` - `workflow.nyquist_validation: true`. [VERIFIED: repo file]
- Local environment checks: `python3 --version`, `pytest --version`, `gsd-sdk query init.phase-op 37`. [VERIFIED: shell outputs]

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - tool versions and workflow flags verified locally/in-repo.
- Architecture: HIGH - phase scope and touch points are explicit in roadmap and audit docs.
- Pitfalls: HIGH - directly derived from mismatches visible in current validation files.

**Research date:** 2026-04-29  
**Valid until:** 2026-05-29 (stable internal documentation workflow)
