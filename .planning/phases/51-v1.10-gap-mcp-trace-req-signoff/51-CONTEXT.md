# Phase 51: v1.10-gap-mcp-trace-req-signoff - Context

**Gathered:** 2026-05-01
**Status:** Ready for planning

<domain>
## Phase Boundary

**Roadmap:** Close audit gaps for **CCODE-03**, **CCODE-04** by executing or completing **Phase 47** scope, producing **`47-VERIFICATION.md`**, aligning **manifest / capability / skills** with the shipped MCP surface, and reconciling **REQUIREMENTS.md** wording with the implemented tools (**`concept_code_hops`** vs narrative **`/trace`** vs temporal **`entity_trace`**).

**In scope:** Verification artifact + checkbox sign-off + doc/manifest parity checks tied to **Phase 47** plans (`47-01`, `47-02`). No new relation types or MCP API redesign — Phase **46** + **47** already locked **`implements`** traversal and tool naming.

**Out of scope:** Broad narrative slash-command rework beyond **47-02** skill bullet parity; Neo4j-only exporters; phases **48–52** hygiene items except where ROADMAP explicitly chains.

</domain>

<decisions>
## Implementation Decisions

### Verification & requirements reconciliation

- **D-51.01:** Author canonical **`47-VERIFICATION.md`** under **`.planning/phases/47-mcp-trace-integration/`** (same pattern as **`45-VERIFICATION.md`** / Phase **50**). Evidence must cite **`pytest`** (including **`tests/test_concept_code_mcp.py`**), grep anchors for **`concept_code_hops`** in **`mcp_tool_registry.py`** / **`serve.py`**, and manifest/doc parity checks from **47-02**.
- **D-51.02:** **CCODE-03** sign-off requires **at least one** MCP tool traversing concept↔implementation edges — satisfied by shipped **`concept_code_hops`** + registry/meta rows once verified against **`capability_tool_meta.yaml`** and regenerated **`server.json`** per **D-47.01**.
- **D-51.03:** **CCODE-04** — REQ text allows **`/trace` OR `entity_trace`**. **Locked interpretation for gap closure:** automated golden-path **`implements`** traversal is proven by **`test_concept_code_hops_golden_path`** calling **`_run_concept_code_hops`**. **`entity_trace`** (`_run_entity_trace`) remains **temporal snapshot** tracing — it does **not** satisfy the typed hop requirement alone. **`/trace`** in **`skill.md`** documents **temporal** tracing aligned with **`entity_trace`**; **concept↔code** hops are **`concept_code_hops`** (skill text already cross-references). **`47-VERIFICATION.md`** must state this mapping explicitly so audit reconciles REQ wording without implying **`entity_trace`** was mislabeled as concept hops.
- **D-51.04:** Phase **51** **wraps** Phase **47** execution debt: before ticking CCODE rows, confirm **47-02** deliverables ( **`docs/RELATIONS.md`**, **`docs/ARCHITECTURE.md`** grep targets, **`server.json`** regen + hash, all **`skill*.md`** enumerations) via plan acceptance criteria — partial completion must be recorded under **Gaps** in **`47-VERIFICATION.md`**, not silent drift.

### Claude's Discretion

- Exact **`server.json`** regeneration command and CI vs local **MCP** extra — follow **`CLAUDE.md`** / **`graphify capability`** patterns already used in Phase **24–25** manifest work.
- If **`server.json`** in repo lacks embedded **`concept_code_hops`** string after regen, treat as **blocking** for REQ tick until export pipeline is run and committed (do not fake verification).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning & roadmap

- `.planning/ROADMAP.md` — Phase **51** goal; Phase **47** plans list; Depends on **46**.
- `.planning/REQUIREMENTS.md` — **CCODE-03**, **CCODE-04**; traceability rows (**51** → **47**).
- `.planning/phases/47-mcp-trace-integration/47-CONTEXT.md` — **D-47.01–03**, **`entity_trace`** vs **`concept_code_hops`** distinction.
- `.planning/phases/47-mcp-trace-integration/47-01-PLAN.md` — MCP helper + golden-path test tasks.
- `.planning/phases/47-mcp-trace-integration/47-02-PLAN.md` — docs, **`server.json`**, skill parity.

### Code

- `graphify/serve.py` — **`_run_concept_code_hops`**, **`_tool_concept_code_hops`**, **`_run_entity_trace`** (temporal).
- `graphify/mcp_tool_registry.py` — **`concept_code_hops`** schema.
- `graphify/capability_tool_meta.yaml` — per-tool meta (**D-47.01**).
- `server.json` — regenerated MCP manifest (**47-02**).
- `tests/test_concept_code_mcp.py` — golden path (**CCODE-04** evidence).

### Documentation & skills

- `docs/RELATIONS.md` — MCP ↔ **`implements`** pointer (**D-47.02**).
- `docs/ARCHITECTURE.md` — MCP pipeline paragraph (**D-47.02**).
- `graphify/skill.md` (and platform variants) — **`/trace`** vs **`concept_code_hops`** copy (**D-47.03**).

### Project conventions

- `CLAUDE.md` — pytest, optional **`[mcp]`**, manifest sync notes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`concept_code_hops`** — implemented in **`serve.py`**; registered in **`build_mcp_tools()`**; tests in **`tests/test_concept_code_mcp.py`**.
- **`docs/RELATIONS.md`** — already documents **`concept_code_hops`** ↔ **`implements`** (spot-check **2026-05-01**).

### Gaps to verify during execution

- **`server.json`** — string **`concept_code`** not found in raw grep (**2026-05-01**); likely stale export or tools embedded under **`manifest_content`** — **47-02** regen task must be validated before milestone sign-off.

### Integration points

- **`capability.py`** + **`python -m graphify capability`** — manifest regeneration path for **`server.json`** parity (**47-02-02**).

</code_context>

<specifics>
## Specific Ideas

- Interactive gray-area menu was offered in the discuss-phase session output (verification-only vs full 47-02 checklist ordering); defaults favor **full 47 plan checklist before REQ ticks**.
- No **`51-SPEC.md`** — requirements remain **REQUIREMENTS.md** + Phase **47** plans.

</specifics>

<deferred>
## Deferred Ideas

- **Rename `entity_trace`** or unify slash **`/trace`** UX — explicitly deferred in **47-CONTEXT.md**; not reopened unless product requests a dedicated slash for **`concept_code_hops`**.

</deferred>

---

*Phase: 51-v1.10-gap-mcp-trace-req-signoff*
*Context gathered: 2026-05-01*
