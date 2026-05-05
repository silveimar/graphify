# Research synthesis — Milestone v1.11

**Date:** 2026-04-30  
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md (this cycle)

## One-paragraph summary

v1.11 extends the **vault adapter** (templates + profile overrides without Jinja2), promotes **concept↔implementation** relationships to **validated graph edges** consumed consistently by **export and MCP**, and delivers **incremental elicitation/harness + vault CLI/hygiene** work — all without new required dependencies or breaking the existing pipeline boundaries.

## Stack additions

**None required.** Optional PyYAML unchanged; extend **stdlib-first** template parsing and existing NetworkX graph merge patterns.

## Feature table stakes

- TMPL: conditionals + `#connections` + per-note-type Dataview hooks (profile-driven)  
- CFG: per-community / class template overrides composing with existing profile composition  
- CGRAPH: typed concept↔code edges end-to-end (validate → build → MCP/trace/export parity)  
- ELIC/HARN: observable improvements over v1.9 with documented trust boundaries  
- VAUX/HYG: vault CLI/doctor consistency + hygiene/registry closures in scope  

## Watch out for

- Template block injection / ordering (expand blocks before `${}` substitution)  
- Harness **import** — only with explicit defenses and non-default entrypoints  
- Migration safety when template outputs move paths — orphan/manifest semantics  

## Recommended phase sequencing

1. Graph schema + **build** merge for new relations  
2. **MCP** + reporting alignment  
3. **Templates** + profile overrides  
4. **Elicitation/harness** increments  
5. **Vault CLI + hygiene**  
