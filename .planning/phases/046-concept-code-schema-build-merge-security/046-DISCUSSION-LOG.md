# Phase 46: Concept↔Code Schema, Build Merge & Security - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 46-Concept↔Code Schema, Build Merge & Security
**Areas discussed:** Relation taxonomy, Confidence rules, Merge & duplicate edges, Validation strictness

---

## Relation taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Single directional / pair / symmetric undirected | Schema shape for concept↔code | ✓ Explicit **pair** of inverse relations |
| implements+implemented_by / concept_for_implementation / You decide | Canonical string names | ✓ **You decide** (planner; default `implements` / `implemented_by`) |
| Preserve both / canonical one / You decide | Storage of inverse emitters | ✓ Initially **preserve both**; refined with **dedupe inverse** below |
| Defer hyperedge / document only / unify Phase 46 | Hyperedge `implement` alignment | ✓ **Unify in Phase 46** |

**User's choice:** Directional pair; planner-chosen names; **dedupe redundant inverse pairs** at `build()`; **unify hyperedge vocabulary** with edges.
**Notes:** “Preserve both edges” for distinct semantic cases; **same unordered pair** with both directions → **canonicalize to one edge** (046-CONTEXT **D-46.02**).

---

## Confidence rules

| Option | Description | Selected |
|--------|-------------|----------|
| Structural only / comments OK / never EXTRACTED cross-domain | When **EXTRACTED** | ✓ **Comments/docstrings** OK if parser finds link |
| LLM semantic / cross-file heuristic / mirror existing | When **INFERRED** | ✓ **LLM/semantic** without deterministic anchor |
| Conflicting only / LLM default AMBIGUOUS / rare | When **AMBIGUOUS** | ✓ **Conflicting sources** (or weak/contested) |
| Required / optional / you decide | **confidence_score** for INFERRED | ✓ **You decide** — match existing INFERRED posture |

---

## Merge & duplicate edges

| Option | Description | Selected |
|--------|-------------|----------|
| Last wins / first wins / merge attrs | Duplicate identical triple | ✓ **Merge attributes** |
| Both OK / dedupe inverse / warn keep | Inverse pair for same link | ✓ **Dedupe** — one canonical direction |
| prefer EXTRACTED / highest score / you decide | Same triple, different confidence | ✓ **Highest confidence_score**; tie with EXTRACTED > INFERRED > AMBIGUOUS |
| No MultiGraph / MultiGraph / defer | Parallel edges | ✓ **Stay Graph** — merge evidences into one edge |

---

## Validation strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Strict errors / warn unknown / no enum | Edge `relation` validation | ✓ **Warn unknown** (stderr), allow |
| Same registry / hyperedge subset / edges only | Hyperedge validation | ✓ **Separate hyperedge allowed list** + same warn posture |
| cap stderr / no assert / you decide | Tests for warnings | ✓ **Capture stderr** in tests |
| validate docstring / REQUIREMENTS only / new doc | Registry home | ✓ **`docs/RELATIONS.md`** (new) |

---

## Claude's Discretion

- Relation string final choice if `implements`/`implemented_by` needs adjustment.
- **`confidence_score`** requirement parity with existing INFERRED edges.
- Canonical direction rule for inverse dedupe; edge attribute merge keys; hyperedge allowed list contents.

## Deferred Ideas

- MCP + trace behavior (Phase 47, **CCODE-03** / **CCODE-04**).
