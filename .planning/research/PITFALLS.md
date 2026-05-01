# Pitfalls

**Milestone:** v1.11  
**Researched:** 2026-04-30

## Critical

| Pitfall | Prevention |
|---------|------------|
| **Template injection** via profile-controlled blocks | Expand blocks **before** substitution; sanitize labels; reuse **`security.py`** sinks for anything echoed into MD/HTML |
| **Duplicate CFG truth** | Profile overrides must compose with **`extends:`/`includes:`** — single validation path (`validate_profile_preflight`) |
| **Edge semantics drift** | One enum table in **`validate.py`**; MCP + export both derive from graph edges, not parallel heuristics |
| **Harness import** | Treat as **high risk** — quarantine paths, explicit user approval, never silent vault writes |
| **Breaking Obsidian round-trip** | Merge engine + manifest behavior unchanged unless migration guide + tests prove safety |

## Testing

- Regress **`tmp_path`** isolation; no network in CI  
- Property tests for template expansion order (block vs `${}`)  

## Phase ownership hints

- **Schema/build** risks → early phases  
- **Template surface** risks → mid phases after classification context is stable  
- **CLI/doctor** risks → dedicated phase with snapshot tests for help text  
