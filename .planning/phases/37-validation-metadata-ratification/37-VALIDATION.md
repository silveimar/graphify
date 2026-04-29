---
phase: 37
slug: validation-metadata-ratification
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
completed: 2026-04-29
---

# Phase 37 Validation - Metadata Ratification

## Scope

Phase 37 validates planning and audit artifacts only. It does not change runtime behavior in `graphify/`.

## Deterministic Gate Checks

1. **Task schema completeness in plans**
   - `python3 -c "from pathlib import Path; import re, sys; errs=[]; files=[Path('.planning/phases/37-validation-metadata-ratification/37.1-PLAN.md'), Path('.planning/phases/37-validation-metadata-ratification/37.2-PLAN.md')]; 
for p in files:
    t=p.read_text(encoding='utf-8')
    tasks=re.findall(r'<task type=\"auto\">.*?</task>', t, re.S)
    if not tasks: errs.append(f'{p}: no auto tasks found')
    for i,task in enumerate(tasks,1):
        for tag in ['<files>','<action>','<verify>','<done>']:
            if tag not in task: errs.append(f'{p}: task {i} missing {tag}')
print('PASS: plan task schema complete' if not errs else 'FAIL:\\n' + '\\n'.join(errs)); sys.exit(1 if errs else 0)"`

2. **No remaining v1.8 validation-metadata debt**
   - `python3 -c "from pathlib import Path; import re, sys; t=Path('.planning/v1.8-MILESTONE-AUDIT.md').read_text(encoding='utf-8'); errs=[]; 
if re.search(r'^status:\\s*tech_debt\\b', t, re.M): errs.append('frontmatter status still tech_debt')
if re.search(r'^\\s*partial_phases:\\s*\\n(?:\\s*-\\s*.+\\n)+', t, re.M): errs.append('nyquist.partial_phases not empty')
if re.search(r'^\\s*overall:\\s*partial\\b', t, re.M): errs.append('nyquist.overall still partial')
debt_patterns=[r'32-profile-contract-defaults.*nyquist_compliant:\\s*false', r'33-naming-repo-identity-helpers.*nyquist_compliant:\\s*false', r'34-mapping-cluster-quality-note-classes.*no Nyquist frontmatter', r'35-templates-export-plumbing-dry-run-migration-visibility.*nyquist_compliant:\\s*false']
for pat in debt_patterns:
    if re.search(pat, t, re.S): errs.append('remaining debt pattern: ' + pat)
print('PASS: no v1.8 validation-metadata debt remains' if not errs else 'FAIL:\\n' + '\\n'.join(errs)); sys.exit(1 if errs else 0)"`

3. **Phase 37 roadmap and artifact wiring**
   - `python3 -c "from pathlib import Path; import sys; r=Path('.planning/ROADMAP.md').read_text(encoding='utf-8'); v=Path('.planning/phases/37-validation-metadata-ratification/37-VALIDATION.md').read_text(encoding='utf-8'); errs=[]; 
if '**Plans:** 2 plans' not in r: errs.append('ROADMAP Phase 37 plan count not set to 2')
for token in ['37.1-PLAN.md','37.2-PLAN.md']:
    if token not in r: errs.append(f'ROADMAP missing {token}')
for token in ['phase: 37', 'slug: validation-metadata-ratification', '## Validation Sign-Off']:
    if token not in v: errs.append(f'37-VALIDATION missing {token}')
print('PASS: roadmap and validation artifact wiring is complete' if not errs else 'FAIL:\\n' + '\\n'.join(errs)); sys.exit(1 if errs else 0)"`

## Wave 0 Checklist

- [x] 37.1 plan includes explicit `<files>` and `<done>` in all auto tasks.
- [x] 37.2 plan includes explicit `<files>` and `<done>` in all auto tasks.
- [x] 37.2 includes deterministic verification proving no v1.8 validation-metadata debt remains.
- [x] ROADMAP Phase 37 plan inventory is explicit (count and two plan entries).

## Validation Sign-Off

- [x] Deterministic gate checks executed and passing.
- [x] Ratification remains documentation-only with no runtime behavior edits.
- [x] Approval captured after Nyquist gate review.

Approval: Phase 37 metadata ratification approved after passing deterministic gate checks.
