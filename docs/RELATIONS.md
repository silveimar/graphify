# Graphify relation vocabulary

Authoritative registry for **`edge.relation`** strings (extract JSON) and **`hyperedges[].relation`** (group edges). **`validate.py`** warns once per unknown value on stderr; update this doc when adding emitters.

## Concept ↔ code (Phase 46)

| Relation | Direction | Notes |
|----------|-----------|--------|
| `implements` | **code → concept** | Canonical after `build()` normalization. |
| `implemented_by` | concept → code | Accepted from extractors; normalized to `implements` with endpoints swapped before graph assembly. |

Non-code endpoints (both ends non-`code` `file_type`): orientation is left as emitted after `implemented_by` removal.

## Structural / extractor edges

Includes **imports**, **imports_from**, **contains**, **method**, **inherits**, **defines**, **calls**, **includes**, **uses_component**, **binds_method**, **uses**, **rationale_for**.

## Semantic / narrative edges

Includes **references**, **cites**, **conceptually_related_to**, **shares_data_with**, **semantically_similar_to**, **related**, **related_to**.

## Tooling / harness

**derived_shortcut** — MCP-derived shortcut edges.

## Hyperedges

| Relation | Purpose |
|----------|---------|
| `participate_in` | Multi-node participation |
| `implement` | Legacy singular verb (skills); prefer aligning new payloads with `implements` where practical |
| `implements` | Allowed synonym on hyperedges |
| `form` | Group formation |

---

Implementation: `KNOWN_EDGE_RELATIONS` / `KNOWN_HYPEREDGE_RELATIONS` in `graphify/validate.py`.
