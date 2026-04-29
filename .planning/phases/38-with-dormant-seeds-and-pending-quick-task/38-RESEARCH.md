# Phase 38: with-dormant-seeds-and-pending-quick-task - Research

**Researched:** 2026-04-29  
**Domain:** GSD planning hygiene (seed triage + quick-task closure)  
**Confidence:** HIGH

## User Constraints

### Locked Decisions
- No phase-specific `CONTEXT.md` exists for Phase 38, so there are no additional locked discuss decisions to inherit. [VERIFIED: `gsd-sdk query init.phase-op "38"` returned `"has_context": false`]

### Claude's Discretion
- Phase 38 is intentionally open (`Goal: [To be planned]`, `Requirements: TBD`, `Plans: 0`), so scope definition is the primary responsibility of this research. [VERIFIED: `.planning/ROADMAP.md`]

### Deferred Ideas (OUT OF SCOPE)
- Deferred seeds already tracked at project state level are `SEED-001` and `SEED-002`; these remain deferred unless Phase 38 explicitly promotes them. [VERIFIED: `.planning/STATE.md` Deferred Items]

## Summary

Phase 38 should be a **planning-state reconciliation phase**, not a feature build. The concrete need is to convert currently scattered context about dormant seeds and quick-task history into one consistent, auditable planning posture before milestone rollover. [VERIFIED: `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md`]

The immediate signals are: (1) deferred seed backlog is partially represented in `STATE.md`, (2) additional seed files exist in `.planning/seeds/` with differing status/fit metadata, and (3) a completed quick task exists in `.planning/quick/260427-rc7-fix-detect-self-ingestion/` but is not surfaced as an active or pending todo item. [VERIFIED: `.planning/STATE.md`, `.planning/seeds/*.md`, `.planning/quick/260427-rc7-fix-detect-self-ingestion/*`]

Phase 38 should therefore define and execute a safe closure sequence: **inventory -> classify -> decide disposition -> synchronize docs -> verify consistency**. This keeps v1.8 shipped behavior untouched while preparing clean inputs for next-milestone planning. [VERIFIED: `.planning/v1.8-MILESTONE-AUDIT.md` indicates v1.8 behavior is complete and passed]

**Primary recommendation:** Use Phase 38 as a docs-only governance pass to ratify dormant seed policy and quick-task lifecycle state, with explicit no-runtime-code-change boundaries. [VERIFIED: current Phase 38 has no implementation requirements in `.planning/ROADMAP.md`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dormant seed inventory and classification | Planning docs (`.planning/seeds`, `STATE.md`) | Roadmap metadata | Seed status is planning-state, not runtime behavior. [VERIFIED: seed files + `STATE.md`] |
| Pending/complete quick-task disposition | Quick artifacts (`.planning/quick`) | `STATE.md` continuity | Quick items are tracked as planning execution artifacts and should be reflected in state docs. [VERIFIED: `.planning/quick/260427-rc7-fix-detect-self-ingestion/*`] |
| Cross-document consistency enforcement | `ROADMAP.md`, `STATE.md`, optional milestone docs | Phase directory artifacts | These docs are canonical for next-step orchestration and planning integrity. [VERIFIED: `STATE.md` + `ROADMAP.md`] |
| Verification/sign-off evidence for planning closeout | Phase 38 docs (`38-PLAN.md`, `38-VERIFICATION.md`, `38-SUMMARY.md`) | Existing audit docs | Nyquist/process gates require explicit verification artifacts even for docs-heavy phases. [VERIFIED: workflow settings in `.planning/config.json` with `"nyquist_validation": true`] |

## Project Constraints (from .cursor/rules/)

- No `.cursor/rules/` directory exists in this repository; no extra project-local rule files were discoverable for this phase. [VERIFIED: glob search under `.cursor/rules/**/*.md` returned none]

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| Python | 3.10.19 | Execute repo tooling and verification commands | Matches supported runtime floor (3.10+) for project workflows. [VERIFIED: `python3 --version`; CITED: `CLAUDE.md`] |
| pytest | 9.0.3 | Validation command surface for non-regression checks | Canonical test runner in project commands. [VERIFIED: `pytest --version`; CITED: `CLAUDE.md`] |
| gsd-sdk CLI | available (version not exposed) | GSD phase context/bootstrap operations | Required to resolve phase metadata and workflow actions. [VERIFIED: `command -v gsd-sdk`; ASSUMED: exact semantic version unavailable] |

### Supporting
| Library/Tool | Version | Purpose | When to Use |
|--------------|---------|---------|-------------|
| Markdown planning artifacts | N/A | Canonical project state and traceability | For all scope/decision synchronization work in this phase. [VERIFIED: `.planning/*.md`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Docs-only reconciliation | Runtime/code changes | High risk of unnecessary behavior churn in already-passed v1.8 scope. [VERIFIED: `.planning/v1.8-MILESTONE-AUDIT.md`] |
| Phase-structured closure | Ad-hoc note edits | Weak traceability and harder milestone handoff. [ASSUMED] |

**Installation:**
```bash
pip install -e ".[mcp,pdf,watch]"
```
[CITED: `CLAUDE.md`]

## Architecture Patterns

### System Architecture Diagram

```text
Input signals
  (STATE deferred table, seed docs, quick summaries, roadmap phase entry)
      |
      v
Inventory pass
  (collect all dormant/pending items + current statuses)
      |
      v
Classification decision point
  - keep dormant
  - promote to future requirement/seed trigger
  - mark closed/archived
      |
      v
Planning doc synchronization
  (ROADMAP + STATE + phase artifacts + optional milestones note)
      |
      v
Verification gate
  (consistency checklist + command evidence + sign-off artifacts)
      |
      v
Output
  Clean Phase 38 planning state for next planning command
```

### Recommended Project Structure

```text
.planning/
├── phases/38-with-dormant-seeds-and-pending-quick-task/
│   ├── 38-RESEARCH.md
│   ├── 38-PLAN.md
│   ├── 38-VERIFICATION.md
│   └── 38-SUMMARY.md
├── STATE.md                  # canonical continuity + deferred table
├── ROADMAP.md                # phase goal/dependencies/plans status
├── seeds/                    # source of dormant seed intent
└── quick/                    # source of quick-task lifecycle evidence
```

### Pattern 1: Reconcile-Then-Route
**What:** Consolidate all dormant/pending artifacts first, then route each item to explicit disposition buckets (`dormant`, `future phase candidate`, `closed`).  
**When to use:** Any phase with planning debt but no required runtime behavior changes.  
**Example:** Build a table in `38-PLAN.md` mapping each seed/quick artifact to owner and next action. [VERIFIED: artifacts exist in `.planning/seeds/` and `.planning/quick/`]

### Pattern 2: Docs-Only Safety Boundary
**What:** Freeze runtime modules; limit edits to planning artifacts unless a blocker proves a code change is required.  
**When to use:** Post-milestone cleanup phases after a passed audit.  
**Example:** Do not touch `graphify/*.py` while reconciling dormant seeds and quick-task status. [VERIFIED: v1.8 audit passed; no unmet requirements in scope]

### Anti-Patterns to Avoid
- **Silent carry-forward drift:** leaving seeds/quick outcomes in only one document creates contradictory future planning context.
- **Scope resurrection by accident:** promoting deferred seeds into active work without explicit requirement IDs.
- **Runtime churn during governance phase:** changing shipped behavior while phase goal is documentation/state reconciliation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Planning continuity tracking | Custom trackers/scripts for Phase 38 | Existing `.planning` conventions and phase artifacts | Current workflow already defines canonical state surfaces and verification flow. [CITED: `CLAUDE.md`, `.planning/config.json`] |
| Dependency/status verification | New ad-hoc framework | Existing command checks (`python3 --version`, `pytest --version`, `gsd-sdk query init.phase-op`) | Faster and consistent with current operator workflow. [VERIFIED: command outputs in this research session] |

**Key insight:** The safest implementation is governance alignment, not new mechanics.

## Common Pitfalls

### Pitfall 1: Partial Seed Visibility
**What goes wrong:** Only `STATE.md` deferred rows are reviewed, while additional seed files with meaningful triggers remain unaccounted for.  
**Why it happens:** Multiple seed files exist with different lifecycles/status metadata.  
**How to avoid:** Build a full inventory from `.planning/seeds/` before any decisions.  
**Warning signs:** Phase output references only `SEED-001`/`SEED-002` and ignores other dormant seeds. [VERIFIED: additional seed files exist]

### Pitfall 2: Quick Task Lifecycle Ambiguity
**What goes wrong:** A quick fix appears complete in quick artifacts but not clearly reconciled in canonical state docs.  
**Why it happens:** Quick workflows produce local plan/summary files that can drift from roadmap/state narratives.  
**How to avoid:** Add explicit disposition row in Phase 38 outputs and synchronize `STATE.md`/`ROADMAP.md`.  
**Warning signs:** "pending quick task" remains in phase naming after closure evidence exists. [VERIFIED: quick summary indicates completion]

### Pitfall 3: Over-scoping into New Features
**What goes wrong:** Dormant seeds get transformed into implementation work inside this phase.  
**Why it happens:** Seed docs include implementation sketches that look immediately actionable.  
**How to avoid:** Require requirement IDs + explicit future-phase mapping before activation.  
**Warning signs:** Phase 38 starts changing runtime modules unrelated to planning state.

## Code Examples

Verified operational patterns from current workflow:

### Resolve phase context safely
```bash
INIT=$(gsd-sdk query init.phase-op "38")
if [[ "$INIT" == @file:* ]]; then INIT=$(python3 - <<'PY'
import os
p=os.environ["INIT"][6:]
print(open(p).read())
PY
); fi
printf "%s\n" "$INIT"
```
[VERIFIED: executed successfully in this research session]

### Confirm core validation tooling
```bash
python3 --version
pytest --version
command -v gsd-sdk
```
[VERIFIED: executed successfully in this research session]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Feature build immediately after milestone close | Explicit metadata ratification (Phase 37) then targeted follow-up phase | 2026-04-29 | Safer closure with less hidden planning debt. [VERIFIED: `.planning/ROADMAP.md`, `.planning/STATE.md`] |
| Ad-hoc quick-fix context | Dedicated quick artifact folder with plan/summary | 2026-04-27 | Better evidence, but requires explicit synchronization to canonical docs. [VERIFIED: `.planning/quick/260427-rc7-fix-detect-self-ingestion/*`] |

**Deprecated/outdated:**
- Treating `_COMMUNITY_*` output semantics as active v1.8 behavior is outdated; v1.8 is MOC-only by default. [VERIFIED: `REQUIREMENTS.md` COMM-01/COMM-02 and v1.8 audit]

## Open Questions

1. **Should Phase 38 formally archive or merely annotate the completed quick task?**
   - What we know: quick task artifacts show completion and passing verification. [VERIFIED: `260427-rc7-SUMMARY.md`]
   - What's unclear: desired end-state convention for quick artifacts after closure.
   - Recommendation: choose one explicit lifecycle rule in `38-PLAN.md` and apply consistently.

2. **Which dormant seeds remain intentionally deferred vs candidate for next milestone intake?**
   - What we know: `STATE.md` explicitly lists `SEED-001`/`SEED-002` as deferred; other seed docs exist with status metadata. [VERIFIED]
   - What's unclear: whether non-listed seed files should be represented in canonical deferred table.
   - Recommendation: Phase 38 should produce a single normalized dormant-seed register.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | GSD workflow + command checks | ✓ | 3.10.19 | — |
| pytest | verification architecture commands | ✓ | 9.0.3 | — |
| gsd-sdk | phase context bootstrap | ✓ | — (not reported) | Use existing phase file paths manually if command unavailable |

**Missing dependencies with no fallback:**
- None identified.

**Missing dependencies with fallback:**
- `gsd-sdk` version introspection flag is unavailable; command itself is available and sufficient for phase init. [VERIFIED]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none detected in this research pass |
| Quick run command | `pytest tests/test_detect.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P38-SCOPE-01 | Dormant seed inventory is fully enumerated and dispositioned | docs verification | `python3 -m pytest tests/ -q` (non-regression guard) + manual doc checklist | ❌ Wave 0 |
| P38-SCOPE-02 | Pending/complete quick task disposition is explicit and synchronized | docs verification | manual consistency pass across `ROADMAP.md`, `STATE.md`, `38-SUMMARY.md` | ❌ Wave 0 |
| P38-SCOPE-03 | No runtime behavior changes occur in governance phase | regression guard | `pytest tests/ -q` | ✅ existing |

### Sampling Rate
- **Per task commit:** run focused guard if any runtime file is touched; otherwise run doc consistency checklist.
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** `pytest tests/ -q` green + planning-doc cross-check complete before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `38-PLAN.md` must define explicit doc-consistency checklist and required target files.
- [ ] `38-VERIFICATION.md` must include executed command evidence + state/roadmap reconciliation checklist.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (docs-only phase) |
| V3 Session Management | no | N/A (docs-only phase) |
| V4 Access Control | no | N/A (docs-only phase) |
| V5 Input Validation | yes | Keep existing `graphify/security.py` as unchanged boundary for future runtime work |
| V6 Cryptography | no | N/A (docs-only phase) |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Planning-state drift leading to unsafe future execution | Tampering | Single-source reconciliation in `STATE.md` + phase artifacts with verification checklist |
| Accidental scope escalation into runtime code | Elevation of Privilege (process) | Explicit docs-only boundary and regression-gate requirement |

## Sources

### Primary (HIGH confidence)
- Repository planning docs:
  - `.planning/ROADMAP.md` (Phase 38 placeholder details; v1.8 phase outcomes)
  - `.planning/REQUIREMENTS.md` (v1.8 requirement closure and deferred items)
  - `.planning/STATE.md` (deferred seeds, pending todos, next action context)
  - `.planning/v1.8-MILESTONE-AUDIT.md` (milestone passed + no functional debt)
  - `.planning/seeds/*.md` (dormant-seed metadata and triggers)
  - `.planning/quick/260427-rc7-fix-detect-self-ingestion/*` (quick-task completion evidence)
- Workflow/config:
  - `.planning/config.json` (`nyquist_validation: true`)
  - `CLAUDE.md` (commands, constraints, testing/security conventions)

### Secondary (MEDIUM confidence)
- None required; all key findings were repository-verified.

### Tertiary (LOW confidence)
- None.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ad-hoc phase edits are less reliable than explicit phase artifacts for continuity | Standard Stack / Alternatives | Could over-constrain a workflow the team intentionally keeps flexible |
| A2 | Non-listed seed docs should be normalized into canonical deferred tracking | Open Questions | Might create unnecessary documentation churn if intentionally excluded |

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from local runtime/tool outputs and `CLAUDE.md`
- Architecture: HIGH - based on current planning artifact structure and phase definitions
- Pitfalls: HIGH - directly observed mismatch risk between seed/quick artifacts and canonical state docs

**Research date:** 2026-04-29  
**Valid until:** 2026-05-29

