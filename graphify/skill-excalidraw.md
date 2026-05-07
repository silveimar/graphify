---
name: excalidraw-diagram
description: Build an Excalidraw diagram from a graphify diagram seed and write it into the Obsidian vault.
trigger: /excalidraw-diagram
---

# /excalidraw-diagram

Pick a graphify diagram seed, build the Excalidraw scene from it, and write the
result into the vault under `Excalidraw/Diagrams/`. Falls back to a pure-Python
deterministic layout when `mcp_excalidraw` is not configured. Graphify's Python
code never imports `mcp_excalidraw` — the integration lives entirely inside
this skill prompt.

## Required MCP servers

Add this to your `.mcp.json` (do **not** ask me to edit your `.mcp.json` —
copy this block yourself; graphify never touches that file):

```jsonc
{
  "mcpServers": {
    "graphify":   { "command": "graphify", "args": ["serve"] },
    "obsidian":   { "command": "uvx",      "args": ["mcp-obsidian"] },
    "excalidraw": { "command": "npx",      "args": ["-y", "@excalidraw/mcp-server"] }
  }
}
```

## What I do (7 steps)

1. Call MCP `list_diagram_seeds` against the graphify server and surface the
   recommended seeds (recommender output from Phase 21).
2. Show you the seeds and ask which `seed_id` to use. I never auto-pick.
3. Call MCP `get_diagram_seed(seed_id)` to retrieve the full SeedDict
   (main_nodes, supporting_nodes, relations, suggested_layout_type, …).
4. Read the matching template from the vault — `Excalidraw/Templates/{name}.excalidraw.md`
   via `mcp_obsidian`, or a direct file read when running in fallback mode.
5. Build the diagram. **Two paths:**
   - **5a (preferred):** call `mcp_excalidraw` to add elements + export the
     scene. I will tell you when this path is taken.
   - **5b (fallback / pure-Python):** if `mcp_excalidraw` is not registered
     in your `.mcp.json`, I run the deterministic Python fallback
     `graphify.excalidraw.write_diagram(vault, seed, profile)` and report
     "fallback path engaged" so you know the layout is the deterministic
     stand-in, not the polished one.
6. Resolve the output path from `profile.diagram_types[*].output_path`
   (default `Excalidraw/Diagrams/`) and write the file. **Refuse on
   collision** unless you explicitly pass `force: true` when invoking me.
7. Report `seed_id`, `node_count`, `template`, and the absolute `vault_path`
   of the file I wrote.

## Vault conventions

- Templates live at `Excalidraw/Templates/{name}.excalidraw.md`.
- Diagrams write to `Excalidraw/Diagrams/{topic}-{layout_type}.excalidraw.md`.
- Frontmatter MUST contain `excalidraw-plugin: parsed` and `compress: false`.
- The renderer (`graphify.excalidraw._render_excalidraw_md`) owns the
  frontmatter — I never write it directly from this skill.

## Style rules (locked)

- `fontFamily: 5` (Excalifont) on every text element.
- `strokeColor: "#1e1e2e"` everywhere.
- `backgroundColor: "transparent"` on all shapes.
- `compress: false` always — the LZ-String door is permanently closed.

## Do not (guard list)

- Do **not** import or invoke `lzstring` or compress the scene in any form.
- Do **not** derive element IDs from labels — use deterministic counters
  (`elem-0001`, `elem-0002`, …) so re-runs are byte-identical.
- Do **not** write frontmatter directly; route through the renderer.
- Do **not** edit the user's `.mcp.json` on their behalf — show the snippet,
  let them paste it themselves.
- Do **not** combine multiple seeds into one diagram (multi-seed is out of
  scope for v1.5; revisit in v1.6+).

## Collision behavior

If the resolved vault path already exists I exit with a clear message naming
the colliding file and stop. To overwrite, re-invoke me with `force: true`.
There is no graphify CLI flag for this — `force` is a skill-level argument.


<!-- Phase 65 / CCONF prompt-version drift gate (do not remove) -->
### Confidence scoring (Phase 65, prompt_version 1.14.0)
For each concept↔code INFERRED edge, score the relationship 0–1 with ≤280-char evidence,
then write results via `graphify.cache.save_confidence(..., prompt_version="1.14.0", model_id=...)`.
Bumping `PROMPT_VERSION` in `graphify/prompts.py` MUST be matched here (drift gate test enforces).

<!-- BEGIN: phase-72-reas reasoning-relations block -->
### Reasoning relations (documents/papers/rationales only)

When extracting from documents (md/txt/rst), papers (PDF), or rationale notes, also emit reasoning-relation edges using these 5 relation types:

- `supports` — Source asserts evidence in favor of target.
- `contradicts` — Source asserts target is false or incompatible.
- `supersedes` — Source replaces target as canonical. **Orientation: newer -> older. Target is the superseded (deprecated) node.**
- `evolved_into` — Source is an earlier version that became target. Direction: older -> newer.
- `depends_on` — Source's claim relies on target's claim.

**Endpoint constraint:** Both `source` and `target` MUST be document/paper/rationale nodes (or document-derived concept nodes). DO NOT emit reasoning relations on code-typed nodes — they will be rejected by validate.py.

**Confidence rules (CCONF v1.13):** Emit `confidence` (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`). For `INFERRED`, emit `confidence_score` as a float in `[0.0, 1.0]`. EXTRACTED reasoning edges may omit `confidence_score`.

**Worked example 1 — ADR supersession (newer -> older):**
```
Input fragment (in docs/adr/0042-new-auth.md):
  "This ADR supersedes ADR-0028 (token-based auth)."
Emit:
  {"source": "adr_0042", "target": "adr_0028", "relation": "supersedes",
   "confidence": "EXTRACTED", "source_file": "docs/adr/0042-new-auth.md"}
```

**Worked example 2 — ADR contradiction:**
```
Input fragment (in docs/adr/0050-revisit.md):
  "This proposal directly contradicts ADR-0042's claim that JWTs cannot be revoked."
Emit:
  {"source": "adr_0050", "target": "adr_0042", "relation": "contradicts",
   "confidence": "INFERRED", "confidence_score": 0.85,
   "source_file": "docs/adr/0050-revisit.md"}
```

**Resolution note:** If the textual reference (e.g. `ADR-0028`) does not match a node id, the build layer will resolve it by label or substring. Emit the human-readable label or partial id as `target` — do not invent ids.
<!-- END: phase-72-reas reasoning-relations block -->
