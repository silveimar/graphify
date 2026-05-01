# Stack Research

**Domain:** graphify v1.11 — vault templates, graph semantics, elicitation/harness, CLI  
**Researched:** 2026-04-30  
**Confidence:** HIGH

## Verdict

No new **required** dependencies. Stay on **stdlib + NetworkX + optional PyYAML** (`obsidian` extra), consistent with `CLAUDE.md`.

| Area | Approach |
|------|----------|
| Template conditionals / loops | Extend existing `templates.py` with a **small custom scanner** (or layered expansion before `string.Template`) — stdlib only; avoid Jinja2 |
| Profile composition | **`extends:` / `includes:`** already validated in v1.7 — v1.11 adds **per-community template overrides** and TMPL features without a second config system |
| Concept↔code edges | **`validate.py`** allows new `relation` enum values; **`build.py`** merges/dedupes like today; optional **confidence_score** on INFERRED edges |
| Elicitation / harness | Reuse existing JSON/session paths; no new pip packages for core flows |

### Optional (feature-flagged only)

- **sentence-transformers** / embedding stacks remain optional (dedup path), not pulled in for TMPL/CGRAPH.

## What NOT to add

- Jinja2 or full templating languages as required deps  
- New required YAML features beyond existing PyYAML optional extra  
- Separate graph DB — NetworkX remains canonical

## Installation / CI

- Continue **Python 3.10 + 3.12** pytest gates; pure unit tests under `tmp_path`.
