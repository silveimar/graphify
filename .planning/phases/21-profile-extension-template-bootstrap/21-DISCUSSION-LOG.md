# Phase 21: Profile Extension & Template Bootstrap - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 21-profile-extension-template-bootstrap
**Areas discussed:** Stub content shape, Tag write-back trigger, Trigger-match + recommender order, --force + partial-state behavior

---

## Stub Content Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal empty scene | Frontmatter + empty elements + empty Text Elements block | ✓ |
| Skeleton placeholders | 2-4 placeholder shapes per type implying the layout | |
| Styled style-guides | Full 8-10 element scenes with colors/fonts/spacing | (deferred) |

**User's choice:** Minimal empty scene; defer styled style-guides to a later phase.
**Notes:** User explicitly said "Do 1 and defer 3 Styled style-guides for a future phase." Captured as deferred idea.

---

## Tag Write-Back Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| During --diagram-seeds | Write-back piggybacks on Phase 20 seed-build flow | ✓ |
| During --init-diagram-templates | Init writes stubs AND tags seeds in one command | |
| Separate --write-seed-tags CLI | Dedicated flag | |

**User's choice:** During --diagram-seeds.
**Notes:** Colocates tagging with the pipeline that decides what to tag; --init-diagram-templates performs zero vault note writes.

---

## Trigger-Match Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| AND (both must match) | Strict, fewer false matches | |
| OR (either matches) | Permissive, more suggestions surface | ✓ |
| Per-entry trigger_mode override | Optional and/or per diagram_type | |

**User's choice:** OR (either matches).
**Notes:** Defaults bias toward surfacing diagram suggestions in real user vaults where trigger lists are rarely tuned.

---

## Tiebreak (Multiple Matching Types)

| Option | Description | Selected |
|--------|-------------|----------|
| Highest min_main_nodes wins | Most-specific-wins | ✓ |
| Profile declaration order | First declared wins | |
| Most trigger matches (score) | Highest score wins | |

**User's choice:** Highest min_main_nodes.
**Notes:** Semantically meaningful, stable across profile rewrites.

---

## Partial-State Behavior (--init-diagram-templates without --force)

| Option | Description | Selected |
|--------|-------------|----------|
| Idempotent fill-in | Write missing, skip existing, report counts | ✓ |
| Refuse until --force | Abort if any stub exists | |

**User's choice:** Idempotent fill-in.
**Notes:** Matches user expectation for `init` commands; counts report clarifies state.

---

## Template Path Default

| Option | Description | Selected |
|--------|-------------|----------|
| Excalidraw/Templates/{name}.excalidraw.md | Plugin convention | ✓ |
| folder_mapping['default'] fallback | Reuse Ideaverse Atlas/Dots/ path | |
| New profile key obsidian.excalidraw_templates_dir | Explicit, expands ATOMIC scope | |

**User's choice:** Excalidraw/Templates/{name}.excalidraw.md.
**Notes:** Matches the Obsidian Excalidraw plugin's own convention. Can be promoted to a profile key later if needed.

---

## Claude's Discretion

- Exact tag-merge call shape into compute_merge_plan (union vs append)
- Reported counts formatting and argparse wiring
- Whether to cache profile-to-recommender resolution per build
- Whether to include `trigger_mode: and|or` optional override if it comes for free

## Deferred Ideas

- Styled style-guide templates (full 8-10 element scenes) — future phase
- Per-entry `trigger_mode` override — declined for v1
- `obsidian.excalidraw_templates_dir` profile key — declined for v1
- "Most trigger matches wins" scoring tiebreak — declined
