# Architecture Research

**Milestone:** v1.11  
**Researched:** 2026-04-30  
**Confidence:** HIGH for pipeline boundaries

## Executive recommendation

Keep the pipeline:

`detect → extract → build_graph → cluster → analyze → report → export`

- **TMPL/CFG:** Touch **`templates.py`**, **`profile.py`**, **`mapping.py`** (classification context into templates), **`merge.py`** only where rendered output shape changes  
- **CGRAPH:** Touch **`validate.py`**, **`build.py`** (edge merge rules), **`analyze.py`** / **`report.py`** if summaries mention relations; **`serve.py`** for MCP; **`export.py`** only for parity with existing frontmatter links  
- **ELIC/HARN:** **`elicitation` helpers**, **`__main__.py`** CLI, harness writers under existing patterns  
- **VAUX/HYG:** **`__main__.py`**, **`doctor.py`**, **`detect.py`** / output resolution as needed  

Do **not** pushObsidian-only concerns into **`build.py`** unless the graph genuinely carries new facts.

## Suggested build order (roadmap phases)

1. **Schema + build** — new relation types, validation, deterministic merge  
2. **MCP / trace alignment** — tools consume same edges as export  
3. **Templates** — conditionals + loops + profile hooks (depends on stable classification/context)  
4. **Per-community / template overrides** — profile schema + validation  
5. **Elicitation / harness** increments — tests-first  
6. **Vault CLI + hygiene** — doctor parity, registry/quick-task closure  

## Integration diagram

```text
extract (code/docs)
    → validate_extraction
    → build_graph  (+ concept↔code edges)
    → cluster / analyze
    → export (templates consume graph + profile)
    → serve.py MCP (query typed edges)
```
