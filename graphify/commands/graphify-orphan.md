---
name: graphify-orphan
description: List nodes orphaned from the graph — isolated (no community) and stale/ghost (enrichment staleness=GHOST) — so the user can decide whether to re-cluster, revisit, or prune.
argument-hint:
disable-model-invocation: true
target: obsidian
---

This command takes no arguments. It produces a read-only report; it does NOT write to the vault.

**Step 1 — load isolated nodes from `graphify-out/graph.json`:**

Call the graphify MCP tool `graph_summary` (or whichever tool in this build exposes community-less node ids — the skill's host agent will resolve). From the response, take the list of nodes where `community` is `null`, `-1`, or the field is missing entirely (defensive union — all three encodings must be treated as isolated). Capture their `id`, `label`, and `source_file` fields.

**Step 2 — load ghost nodes from `graphify-out/enrichment.json` if present:**

Check whether `graphify-out/enrichment.json` exists. It is optional — Phase 15 runs asynchronously, so the file may not yet be generated.

- **If `enrichment.json` is present:** call the MCP tool that surfaces the staleness overlay (or read the file via the host agent). Collect every node id whose `staleness` value equals `"GHOST"`.
- **If `enrichment.json` is absent or unavailable:** skip Step 2 and emit the banner in Step 3.

**Step 3 — render the two distinct sections (do NOT merge them):**

## Isolated Nodes

Bulleted list of `[[<label>]]  —  <source_file>` for every isolated node. If there are no isolated nodes, render `_No isolated nodes — every node belongs to a community._`.

## Stale/Ghost Nodes

- If `enrichment.json` is present and there are ghost nodes: bulleted list of `[[<label>]]  —  <source_file>  —  staleness: GHOST` for each.
- If `enrichment.json` is present and there are no ghost nodes: render `_No stale or ghost nodes — enrichment is up to date._`.
- If `enrichment.json` is absent: render this banner verbatim:
  > _Ghost detection unavailable — enrichment.json not yet generated. Run `graphify enrich` to populate staleness data, then re-invoke `/graphify-orphan`._

Do NOT conflate the two sections. Do NOT write to the vault. This command is strictly read-only — no vault-write primitives, no note-proposal tool calls.
