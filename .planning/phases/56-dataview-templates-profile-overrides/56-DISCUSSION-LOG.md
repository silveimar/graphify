# Phase 56: Dataview templates & profile overrides — Discussion Log

**Discussion date:** 2026-05-02
**Mode:** discuss (default), `--chain`
**Phase goal (ROADMAP):** Allow profiles to declare per-note-type Dataview query templates and scoped template overrides (per-community / per-mapping-rule) that compose with v1.7 `extends:` / `includes:` semantics, with deterministic validation when override precedence is ambiguous.
**Requirements covered:** TMPL-03, CFG-01, CFG-02

---

## Gray-area selection

**Question:** Which areas do you want to discuss for Phase 56?
**Options presented:**
- TMPL-03 scope vs Phase 31
- `template_overrides:` shape
- Collision precedence (CFG-02)
- What gets overridden

**User selected:** all four.

---

## Area 1 — TMPL-03 scope

**Question:** What is Phase 56 actually adding for TMPL-03?
**Options presented:**
- Dead-rule preflight only (Recommended)
- Add scoping (per-community / per-rule)
- Promote DV queries to block-engine templates

**User selected:** Dead-rule preflight only → **D-56.01**.

**Question:** Which dead-rule classes should preflight reject for `dataview_queries:` entries?
**Options presented (multiSelect):**
- Unknown `${var}` references
- Note-type with no possible nodes
- Empty / whitespace-only after substitution
- Duplicate keys across `extends:`/`includes:` chain

**User selected:** all four → **D-56.02** (with class 4 folded into CFG-02 collision machinery, D-56.06 §4).

---

## Area 2 — `template_overrides:` shape

**Question:** How should the new override surface be shaped in profile.yaml?
**Options presented:**
- Sibling keys (Recommended) — preview showed `community_templates:` + `mapping_rule_templates:` + `note_type_templates:`
- Unified `template_overrides:` with `scope:` discriminator (with Phase 30 deprecation)
- Extend `community_templates:` with optional `scope:` field

**User selected:** Sibling keys → **D-56.03**.

**Question:** `mapping_rule_templates:` needs to point at a specific mapping rule. Mapping rules currently have no `id` field (positional only). How should rules be referenced?
**Options presented:**
- Add optional `id:` to mapping rules (Recommended)
- Match by `note_type` + matcher signature
- Positional index (1-based)

**User selected:** Add optional `id:` → **D-56.04**.

---

## Area 3 — CFG-02 collision precedence

**Question:** When multiple override lists could match the same note, what is the resolution rule?
**Options presented:**
- Strict precedence ladder (Recommended) — `mapping_rule_templates > community_templates > note_type_templates > base`
- Hard error on any cross-scope overlap
- Author-declared per-rule precedence (`priority:` int)
- Source-path precedence (own > includes > extends)

**User selected:** Strict precedence ladder → **D-56.05**.

**Question:** Where does CFG-02 collision detection run, and how strict?
**Options presented:**
- Schema-only at preflight (Recommended)
- Schema + graph-aware pass
- Schema + render-time warnings only

**User selected:** Schema-only at preflight → **D-56.06** (four collision classes; no glob/regex overlap detection).

---

## Area 4 — Override unit

**Question:** What does an override entry actually replace?
**Options presented:**
- Whole template path (Recommended)
- Whole template OR per-block patch (`blocks:` dict)
- Whole template OR frontmatter-only patch (`frontmatter_extra:` dict)

**User selected:** Whole template path → **D-56.08**.

---

## Closing check

**Question:** Are there gray areas remaining that would block planning?
**Options presented:**
- I'm ready for context
- Explore more gray areas

**User selected:** I'm ready for context. Proceeded to write CONTEXT.md.

---

## Deferred ideas captured

See `<deferred>` section in `56-CONTEXT.md`. Highlights:
- Per-block / per-frontmatter partial overrides
- Unified `template_overrides:` with `scope:` discriminator (long-term cleanup)
- Glob/regex pattern-overlap detection
- Graph-aware collision pass after build
- Author-declared per-rule `priority:`
- Promoting `dataview_queries:` to block-engine templates
- `note_type_templates:` collapsed to dict shape

## Claude's discretion (planner / researcher)

- Test layout (`test_template_overrides.py` vs additions to `test_profile.py`)
- Exact `${var}` allowlist for D-56.02 §1 — enumerate from `_build_dataview_block` callsites
- Validator message wording (mirror Phase 30/31)
- Slug regex for `mapping_rules.id:` (suggested `^[a-z][a-z0-9_-]*$`)
- Whether `mapping_rule_templates:` validation needs a graph-aware "unreachable rule" symmetric to D-56.02 §2 — default no
