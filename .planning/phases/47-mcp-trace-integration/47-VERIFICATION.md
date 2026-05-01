---
status: passed
phase: 47
phase_name: MCP & Trace Integration
verified: 2026-05-01
---

# Phase 47 — Verification

> **Phase 51 gap closure:** Evidence for **CCODE-03** / **CCODE-04** via **`concept_code_hops`** and **`tests/test_concept_code_mcp.py`**. REQ wording reconciliation per **D-51.03** (`51-CONTEXT.md`).

## REQ ↔ implementation mapping (**D-51.03**)

| REQ | Audit interpretation | Evidence surface |
|-----|----------------------|------------------|
| **CCODE-03** | MCP tool traverses concept↔implementation via **`implements`** | **`concept_code_hops`** in **`build_mcp_tools()`**, **`capability_tool_meta.yaml`**, **`capability --validate`** parity with committed **`server.json`** |
| **CCODE-04** | REQ text mentions **`/trace` OR `entity_trace`** for “typed hops” — **`entity_trace`** (`_run_entity_trace`) is **temporal snapshot** tracing, **not** typed **`implements`** hops | Typed **`implements`** golden path = **`pytest tests/test_concept_code_mcp.py::test_concept_code_hops_golden_path`** (**`_run_concept_code_hops`**). Slash **`/trace`** + **`entity_trace`** remain **temporal** narrative (**`skill.md`** L122); concept↔code hops documented as **`concept_code_hops`** |

## Must-haves

| Item | Evidence |
|------|----------|
| **CCODE-03** — MCP tool | **`graphify/mcp_tool_registry.py`** — tool name **`concept_code_hops`** (~L290); **`graphify/serve.py`** — **`_run_concept_code_hops`**, **`_tool_concept_code_hops`**, handler map (~L2161, L3354–3367, L3587); **`graphify/capability_tool_meta.yaml`** (~L87) |
| **CCODE-03** — docs | **`docs/RELATIONS.md`** — MCP↔**`implements`** row; **`docs/ARCHITECTURE.md`** — **`_run_concept_code_hops`** paragraph vs **`entity_trace`** |
| **CCODE-03** — manifest | **`python -m graphify capability --validate`** exit **0** (slim **`server.json`** — hash / **`tool_count`**; do not require substring **`concept_code_hops`** inside JSON) |
| **CCODE-04** — automated hops | **`tests/test_concept_code_mcp.py::test_concept_code_hops_golden_path`** |
| **47-02** — skill parity | **`graphify/skill.md`** enumerates **`concept_code_hops`** (L857); **`/trace`** cross-reference (L122). **`graphify/skill-excalidraw.md`** has **no** **`concept_code_hops`** mention — **Gaps** |

## Evidence details (grep anchors)

Sample **`rg`** hits (repo **`8b8f714`** pre–Task 2 transcripts):

- **`graphify/mcp_tool_registry.py:290`** — `name="concept_code_hops"`
- **`graphify/capability_tool_meta.yaml:87`** — `concept_code_hops:` meta block
- **`graphify/serve.py:2161`** — `def _run_concept_code_hops`
- **`docs/RELATIONS.md:18`** — MCP tool table row
- **`docs/ARCHITECTURE.md:32`** — **`concept_code_hops`** vs **`entity_trace`**

## 47-02 deliverables checklist

| Deliverable | Status |
|-------------|--------|
| **`docs/RELATIONS.md`** — **`concept_code_hops`** | Met |
| **`docs/ARCHITECTURE.md`** — narrative | Met |
| **`server.json`** — **`capability --validate`** | Met (exit **0**, 2026-05-01) |
| **Skill variants** — **`concept_code_hops`** in canonical **`skill.md`** | Met |
| **`skill-excalidraw.md`** | Partial — **no** tool substring (documented **Gaps**) |

## Automated

### Focused — `tests/test_concept_code_mcp.py`

```bash
pytest tests/test_concept_code_mcp.py -q
```

```
1 passed in 0.11s
```

### Golden path — CCODE-04

```bash
pytest tests/test_concept_code_mcp.py::test_concept_code_hops_golden_path -q
```

```
1 passed in 0.18s
```

### Full suite

```bash
pytest tests/ -q
```

```
1965 passed, 1 xfailed, 8 warnings in 73.94s (0:01:13)
```

### Manifest validate — CCODE-03 / **D-47.01**

```bash
python -m graphify capability --validate
```

```
  warning: skill stamp ('0.4.7') is older than the installed package; run 'graphify install' to update the skill. (package is '1.0.0').
```
(exit code **0**)

### Tool registration sanity

```bash
python -c "from graphify.mcp_tool_registry import build_mcp_tools; assert any(t.name=='concept_code_hops' for t in build_mcp_tools())"
```
→ *(no output, exit **0**)*

**Commit:** `git rev-parse --short HEAD` → **`8b8f714`**

**Install context:** `pip install -e ".[mcp,pdf,watch]"` from repo root before **`capability --validate`** (per **CLAUDE.md**).

## Gaps

- **`skill-excalidraw.md`** does not enumerate **`concept_code_hops`** — acceptable variant omission for diagram-focused skill unless product mandates parity (**47-02-03** scope); tracked here for audit transparency.

## human_verification

None — evidence is automated + grep + **`capability --validate`**.
