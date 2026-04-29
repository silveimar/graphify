---
phase: 38
slug: with-dormant-seeds-and-pending-quick-task
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
completed: 2026-04-29
---

# Phase 38 Validation - Dormant Seed and Quick Task Reconciliation

## Scope

Phase 38 validates planning/governance artifacts only. It does not change runtime behavior in `graphify/`.

## Deterministic Gate Checks

1. **Plan task contract completeness**
   - `python3 -c "from pathlib import Path; import re, sys; errs=[]; files=[Path('.planning/phases/38-with-dormant-seeds-and-pending-quick-task/38-01-PLAN.md'), Path('.planning/phases/38-with-dormant-seeds-and-pending-quick-task/38-02-PLAN.md')]; 
for p in files:
    t=p.read_text(encoding='utf-8')
    tasks=re.findall(r'<task type=\"auto\">.*?</task>', t, re.S)
    if not tasks: errs.append(f'{p}: no auto tasks found')
    for i,task in enumerate(tasks,1):
        for tag in ['<files>','<action>','<verify>','<acceptance_criteria>','<done>']:
            if tag not in task: errs.append(f'{p}: task {i} missing {tag}')
print('PASS: plan task schema complete' if not errs else 'FAIL:\\n' + '\\n'.join(errs)); sys.exit(1 if errs else 0)"`

2. **Research open questions resolved**
   - `python3 -c "from pathlib import Path; import sys; t=Path('.planning/phases/38-with-dormant-seeds-and-pending-quick-task/38-RESEARCH.md').read_text(encoding='utf-8'); ok='## Open Questions (Resolved)' in t and 'Resolution:' in t; print('PASS: research questions resolved' if ok else 'FAIL: unresolved open questions section'); sys.exit(0 if ok else 1)"`

3. **Phase 38 roadmap wiring is explicit**
   - `python3 -c "from pathlib import Path; import sys; t=Path('.planning/ROADMAP.md').read_text(encoding='utf-8'); errs=[]; 
if '### Phase 38: with dormant seeds and pending quick task' not in t: errs.append('missing phase 38 section')
for token in ['P38-SCOPE-01','P38-SCOPE-02','P38-SCOPE-03','38-01-PLAN.md','38-02-PLAN.md']:
    if token not in t: errs.append(f'missing {token}')
print('PASS: roadmap phase-38 wiring explicit' if not errs else 'FAIL:\\n' + '\\n'.join(errs)); sys.exit(1 if errs else 0)"`

## Wave 0 Checklist

- [x] `38-01-PLAN.md` and `38-02-PLAN.md` include complete auto-task schema.
- [x] `38-RESEARCH.md` open questions are explicitly marked resolved.
- [x] `ROADMAP.md` phase 38 block includes concrete scope/requirements/plan references.

## Validation Sign-Off

- [x] Deterministic gate checks defined and passing.
- [x] Validation remains docs/governance only.
- [x] Approval captured for Nyquist gate readiness.

Approval: Phase 38 planning artifacts satisfy Nyquist validation prerequisites for execution.
