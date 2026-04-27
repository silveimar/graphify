# Phase 26: v1.5 Configuration Guide & Walkthrough Docs — Research

**Researched:** 2026-04-27
**Domain:** User-facing documentation authoring (docs-only, no code)
**Confidence:** HIGH (all claims sourced from in-repo files at named line numbers)

## Summary

This phase produces a single Markdown guide, `CONFIGURING_V1_5.md` at the repo
root, plus a one-line cross-link from `README.md`. No code, fixtures, or schema
changes. The guide must accurately describe four pipeline commands, an MCP tool
pair, and a complete annotated `.graphify/profile.yaml` example.

The research below extracts the *factual* shape of each surface (CLI flags,
stdout summary lines, MCP tool input/return schemas, profile schema, gating
logic) so the executor can quote the codebase rather than paraphrase. One
critical finding: **the codebase does not implement "≥3 outbound branches" or
"betweenness centrality" gating**. Those are illustrative *policy values* the
user (D-05/D-06 in CONTEXT.md) chose to teach in the example profile. Real
gating in `seed.py` is `min_main_nodes` based with a stable-max tiebreak. The
guide must annotate the example profile honestly: the policy values are what a
profile author can declare, but the loader's `min_main_nodes` field is the only
threshold actually consumed.

**Primary recommendation:** Single PLAN.md (`26-01-PLAN.md`) with three task
groups — (1) author `CONFIGURING_V1_5.md`, (2) insert README subsection, (3)
update REQUIREMENTS.md REQ→Phase mapping for DOCS-01..04 and overwrite the
stale Phase 26 plan-stub at ROADMAP.md:268. Acceptance is grep-checkable: file
exists, contains the four pipeline command names, contains a `diagram_types:`
YAML block with `decision-tree`, contains both MCP tool names with return
schemas, and `README.md` contains a markdown link to `CONFIGURING_V1_5.md`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Guide at repo root as `CONFIGURING_V1_5.md`. No `docs/` directory introduced this phase.
- **D-02 / D-03:** Inline-described synthetic vault — no in-repo fixture, no executable demo path.
- **D-04:** Custom `diagram_type` example beyond the 6 built-ins is `decision-tree`.
- **D-05:** D-06 gating annotation in the example uses the policy "fire only when source node has ≥3 outbound branches" — illustrative only, see Q3 below.
- **D-06 (CONTEXT):** D-07 tiebreak annotation uses the policy "highest betweenness centrality" — illustrative only, see Q3 below.
- **D-07 (CONTEXT):** Example profile is COMPLETE, not a stub — every key the loader accepts is present, plus the new `decision-tree` entry, with inline `# comments`.
- **D-08:** Dedicated `## MCP Tool Integration` section near the end of the guide, NOT an appendix file, NOT inline per pipeline step.
- **D-09:** Per tool: invocation shape, return schema, `_resolve_alias` traversal-defense subsection citing `serve.py:1234-1250` (and noting repetition at `:1399-1403, 1526, 1815, 1990, 2590, 2686`).
- **D-10:** MCP section must let an agent author integrate the tools without reading source.
- **D-11..D-13:** Insert `### v1.5 Configuration Guide` H3 under existing `## Obsidian vault adapter (Ideaverse integration)` H2, AFTER `### Vault Promotion — graphify vault-promote` (around `README.md:378`). One-line pitch + link, NOT a duplicated abstract.
- **D-14:** Match `INSTALLATION.md` / `ARCHITECTURE.md` tone — direct, command-first, fenced bash, no marketing, no emojis.
- **D-15:** No screenshots.

### Claude's Discretion

- Internal section ordering of the walkthrough.
- Exact wording, headings beyond the major H2s.
- Troubleshooting / FAQ depth (omit rather than pad).
- Whether to include a brief "What's new in v1.5" framing paragraph (recommended, ≤5 lines).

### Deferred Ideas (OUT OF SCOPE)

- Locale README updates (`README.ja-JP.md`, `README.ko-KR.md`, `README.zh-CN.md`).
- Screenshots / animated GIFs.
- `docs/` directory + multi-guide index.
- Executable in-repo sample vault under `examples/v1_5_walkthrough/`.
- Troubleshooting / FAQ depth (Claude's discretion).
- Roadmap-hygiene cleanup beyond Phase 26's own line.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | End-to-end walkthrough of v1.5 pipeline on a sample vault | §1 Ground Truth: Pipeline Commands — exact flags + summary stdout for all four steps + skill invocation in `skill-excalidraw.md` |
| DOCS-02 | Complete example `.graphify/profile.yaml` with `diagram_types:` showing ≥1 custom type beyond the 6 built-ins, plus annotated D-06 / D-07 frontmatter | §3 Ground Truth: Profile Schema (every loader-accepted key) + §4 D-06/D-07 actual gating |
| DOCS-03 | MCP `list_diagram_seeds` + `get_diagram_seed` invocation, return schema, `_resolve_alias` traversal-defense | §2 Ground Truth: MCP Tools — verbatim `inputSchema`, return-meta keys, alias closure |
| DOCS-04 | Guide reachable from `README.md` via a "v1.5 Configuration" link | §5 Style Anchors — README insertion site + existing v1.5-adjacent subsection rhythm |

## Project Constraints (from CLAUDE.md)

- No new required dependencies (PyYAML stays optional). Phase 26 adds zero deps.
- Backward compatible — no behavior change.
- Pure unit tests only, no network/filesystem-outside-`tmp_path` (N/A this phase — docs only).
- Security: any path discussion in the guide must reflect that real CLI paths are confined via `validate_vault_path` (cited in `__main__.py:1444`).
- Style: 4-space indent in any embedded Python; YAML must be valid; CLI sample output should retain the `[graphify]` stderr prefix verbatim.
- Multi-platform: the term "skill" covers 9+ platform variants (`_PLATFORM_CONFIG`); `install excalidraw` is one such platform entry (`__main__.py:140-143`).

---

## 1. Ground Truth: Pipeline Commands

### 1.1 `vault-promote` — `__main__.py:2224-2255`

argparse subcommand. Flags:

| Flag | Type | Default | Required |
|------|------|---------|----------|
| `--vault` | path | — | yes |
| `--threshold` | int | `3` | no |
| `--graph` | path | `graphify-out/graph.json` | no |

Stdout summary (verbatim):

```
[graphify] vault-promote complete: promoted=<k=v, k=v...>; skipped=<reason=N, ...>
```

Source: `__main__.py:2255` — `print(f"[graphify] vault-promote complete: promoted={promoted_str}; skipped={skipped_str}")`.

Implementation: `from graphify.vault_promote import promote(graph_path, vault_path, threshold)`.

### 1.2 `--diagram-seeds` — `__main__.py:1397-1428`

Top-level flag (NOT an argparse subcommand). Flags:

| Flag | Type | Default |
|------|------|---------|
| `--graph` | path | `graphify-out/graph.json` |
| `--vault` | path | optional — if set, routes tag write-back through `compute_merge_plan` (D-08 union policy) |

Stdout summary (verbatim):

```
[graphify] diagram-seeds complete: <summary-dict-repr>
```

Source: `__main__.py:1427` — `print(f"[graphify] diagram-seeds complete: {summary}")` where `summary = build_all_seeds(G, graphify_out=gp.parent, vault=vault_path)`.

Side effects: writes per-seed JSON files + `seeds-manifest.json` under `graphify-out/seeds/` (D-01/D-02 atomic + manifest-last semantics, per `seed.py:429+`).

Help text (`__main__.py:1196-1198`):

```
--diagram-seeds         emit diagram seed JSON + manifest under graphify-out/seeds/ (SEED-01)
  --graph <path>          path to graph.json (default graphify-out/graph.json)
  --vault <path>          opt-in: route gen-diagram-seed tag write-back through compute_merge_plan (D-08)
```

### 1.3 `--init-diagram-templates` — `__main__.py:1432-1478`

Top-level flag. Flags:

| Flag | Type | Default | Required |
|------|------|---------|----------|
| `--vault` | path | — | yes (`error: --vault PATH required` on miss) |
| `--force` | bool | `False` | no |

Stdout summary (verbatim):

```
[graphify] init-diagram-templates complete: wrote <N> stub(s) (force=<bool>)
```

Source: `__main__.py:1474-1477`.

Behavior: loads profile via `load_profile(vault_arg)`; falls back to `_DEFAULT_PROFILE` on error; calls `excalidraw.write_stubs(vault, diagram_types, force)`. Writes one `.excalidraw.md` stub per profile `diagram_types` entry (or 6 built-in defaults) under the vault's `Excalidraw/Templates/`. Stubs hard-code `compress: false` (one-way door, D-TMPL-01).

### 1.4 `install excalidraw` — `__main__.py:1843-1867` + `_PLATFORM_CONFIG["excalidraw"]` at `__main__.py:140-143`

Invocation: `graphify install --platform excalidraw`. The `excalidraw` entry is a platform in `_PLATFORM_CONFIG`:

```python
"excalidraw": {
    "skill_file": "skill-excalidraw.md",
    "skill_dst": Path(".claude") / "skills" / "excalidraw-diagram" / "SKILL.md",
    # ... claude_md=False (no CLAUDE.md anchor)
}
```

So `graphify install --platform excalidraw` copies `skill-excalidraw.md` → `.claude/skills/excalidraw-diagram/SKILL.md`.

### 1.5 Skill invocation — `skill-excalidraw.md:1-5`

```
---
name: excalidraw-diagram
description: Build an Excalidraw diagram from a graphify diagram seed and write it into the Obsidian vault.
trigger: /excalidraw-diagram
---
```

User invokes the slash command **`/excalidraw-diagram`** in their AI client after install.

Required `.mcp.json` block (verbatim, `skill-excalidraw.md:20-27`):

```jsonc
{
  "mcpServers": {
    "graphify":   { "command": "graphify", "args": ["serve"] },
    "obsidian":   { "command": "uvx",      "args": ["mcp-obsidian"] },
    "excalidraw": { "command": "npx",      "args": ["-y", "@excalidraw/mcp-server"] }
  }
}
```

### 1.6 Pipeline order (fixed by codebase)

```
graphify vault-promote --vault <vault>
graphify --diagram-seeds [--vault <vault>]
graphify --init-diagram-templates --vault <vault>
graphify install --platform excalidraw
# In your AI client:
/excalidraw-diagram
```

---

## 2. Ground Truth: MCP Tools

### 2.1 `list_diagram_seeds` — `mcp_tool_registry.py:349-363` + core at `serve.py:2562-2664`

**Tool signature (verbatim from `mcp_tool_registry.py:349`):**

```python
types.Tool(
    name="list_diagram_seeds",
    description=(
        "List all available diagram seeds in graphify-out/seeds/. Returns per-seed: "
        "seed_id, main_node_label, suggested_layout_type, trigger (auto|user), node_count. "
        "D-02 envelope. Alias-resolved per D-16. Returns no_seeds envelope when "
        "directory empty or manifest missing/corrupt."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "budget": {"type": "integer", "default": 500},
        },
    },
)
```

**Arguments:** `budget` (int, default 500) — soft character cap multiplier (cap ≈ `budget * 200`).

**Return shape (text body + meta sentinel):**

The return is a single string: `<text_body>` + `QUERY_GRAPH_META_SENTINEL` + `<json_meta>`.

Text body: tab-separated rows, one per seed. Columns:

```
<seed_id>\t<main_node_label>\t<suggested_layout_type>\t<trigger>\t<node_count>
```

Meta JSON keys:

| Key | Type | Always present |
|-----|------|----------------|
| `status` | `"ok"` \| `"no_seeds"` | yes |
| `seed_count` | int | yes |
| `budget_used` | int | yes |
| `resolved_from_alias` | `dict[str, list[str]]` | only when alias resolution rewrote IDs |

`status="no_seeds"` is returned when `graphify-out/seeds/` is missing, manifest is missing/corrupt, or no eligible seeds exist (`serve.py:2580-2585, 2657-2658`).

### 2.2 `get_diagram_seed` — `mcp_tool_registry.py:364-382` + core at `serve.py:2667-2776`

**Tool signature (verbatim):**

```python
types.Tool(
    name="get_diagram_seed",
    description=(
        "Return the full SeedDict for a specific seed by seed_id. Non-existent seed_id "
        "returns a not_found envelope; corrupt file returns a corrupt envelope; never "
        "crashes. D-02 envelope. Alias-resolved per D-16 on both the seed_id argument "
        "and the node IDs in the returned SeedDict body."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "seed_id": {"type": "string", "description": "Seed identifier from list_diagram_seeds"},
            "budget": {"type": "integer", "default": 2000},
        },
        "required": ["seed_id"],
    },
)
```

**Arguments:**

| Name | Type | Required | Default |
|------|------|----------|---------|
| `seed_id` | str | yes | — |
| `budget` | int | no | 2000 (DoS guard: text_body capped at `budget * 10` chars) |

**Return body:** Pretty-printed JSON of the SeedDict. SeedDict shape from `seed.py:295-307`:

```json
{
  "seed_id": "<canonical_id>",
  "trigger": "auto" | "user",
  "main_node_id": "<id>",
  "main_node_label": "<label>",
  "main_nodes": [{"id":..., "label":..., "file_type":..., "element_id":...}, ...],
  "supporting_nodes": [{"id":..., "label":..., "file_type":..., "element_id":...}, ...],
  "relations": [{"source":..., "target":..., "relation":..., "confidence":...}, ...],
  "suggested_layout_type": "architecture|workflow|repository-components|mind-map|cuadro-sinoptico|glossary-graph",
  "suggested_template": "Excalidraw/Templates/<type>.excalidraw.md",
  "version_nonce_seed": <int>
}
```

**Return meta JSON keys:**

| Key | Type | Always present |
|-----|------|----------------|
| `status` | `"ok"` \| `"truncated"` \| `"not_found"` \| `"corrupt"` | yes |
| `seed_id` | str | yes |
| `node_count` | int | when status is `ok` or `truncated` |
| `budget_used` | int | yes |
| `resolved_from_alias` | `dict[str, list[str]]` | only when alias rewrote IDs |

### 2.3 `_resolve_alias` traversal-defense — canonical at `serve.py:1234-1250`

**Canonical pattern (chat-core, verbatim):**

```python
def _resolve_alias(node_id: str) -> str:
    # WR-03: transitive resolution with cycle guard, in case dedup_report.json
    # ever contains chained entries (e.g. {"a": "b", "b": "c"}).
    seen: set[str] = set()
    current = node_id
    while current in _effective_alias_map and current not in seen:
        seen.add(current)
        nxt = _effective_alias_map[current]
        if nxt == current:
            break
        current = nxt
    if current != node_id:
        aliases = _resolved_aliases.setdefault(current, [])
        if node_id not in aliases:
            aliases.append(node_id)
    return current
```

**What to document:** every MCP tool that accepts a node-id argument re-implements
this closure. It walks chained aliases (`{"a":"b","b":"c"}` → `c`) but exits if
the same node is visited twice (cycle defense). When a rewrite occurs, the
original ID is recorded under the canonical key in `_resolved_aliases`, surfaced
to the agent via the `resolved_from_alias` meta field.

**Where the pattern repeats** (per CONTEXT D-09): `serve.py:1399-1403, 1526, 1815, 1990, 2590, 2686`. The `list_diagram_seeds` and `get_diagram_seed` cores have a *simpler* form (single-step, no transitive walk) at `serve.py:2590-2599` and `2686-2695` — the guide should document both: the canonical transitive-with-cycle-guard form (chat) and note that the seed tools use the single-step variant which is sufficient because seed_id arguments are leaves, not graph nodes.

---

## 3. Ground Truth: Profile Schema (`graphify/profile.py`)

### 3.1 Loader entry point — `profile.py:165`

`load_profile(vault_dir: str | Path | None) -> dict` — discovers
`<vault>/.graphify/profile.yaml`, deep-merges with `_DEFAULT_PROFILE`. Falls
back to `_DEFAULT_PROFILE` (no error) if YAML missing/malformed/PyYAML missing.

### 3.2 Top-level keys accepted — `profile.py:106-108` (`_VALID_TOP_LEVEL_KEYS`)

```
folder_mapping, naming, merge, mapping_rules, obsidian,
topology, mapping, tag_taxonomy, profile_sync, diagram_types
```

Any other top-level key is rejected by `validate_profile()`. The example profile
in the guide MUST use only these 10 keys.

### 3.3 `diagram_types[*]` schema — `profile.py:367-404`

Every entry is a dict. Loader-accepted keys (allowlist enforced at line 403):

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `name` | str | yes | unique per entry |
| `template_path` | str | yes | path under vault, e.g. `Excalidraw/Templates/<name>.excalidraw.md` |
| `trigger_node_types` | list[str] | yes | e.g. `["module", "service"]` |
| `trigger_tags` | list[str] | yes | e.g. `["architecture"]` |
| `min_main_nodes` | int | yes | gating threshold (see §4) |
| `naming_pattern` | str | no | e.g. `"{topic}-architecture"` |
| `layout_type` | str | yes (Phase 22 D-05) | one of the 6 built-in layouts (`architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`) |
| `output_path` | str | yes (Phase 22 D-05) | e.g. `"Excalidraw/Diagrams/"` |

**Any other key in a `diagram_types` entry triggers a validation error.** The
guide's `decision-tree` example must NOT introduce new keys (e.g. no
`branch_threshold`, no `tiebreak_metric`) — those concepts go in `# inline
comments`, not in YAML keys.

### 3.4 The 6 built-in defaults — `profile.py:76-103`

`architecture`, `workflow`, `repository-components`, `mind-map`,
`cuadro-sinoptico`, `glossary-graph`. All carry
`min_main_nodes: 3`, `output_path: "Excalidraw/Diagrams/"`,
`naming_pattern: "{topic}-<name>"`.

### 3.5 README YAML block — `README.md:343-365`

The Phase 26 example profile must be a strict superset of this block (same
keys: `folder_mapping`, `naming`, `merge`, `mapping_rules`) and add
`diagram_types:` plus, optionally, the other valid top-level keys (`obsidian`,
`topology`, `mapping`, `tag_taxonomy`, `profile_sync`).

---

## 4. Ground Truth: D-06 / D-07 in `seed.py:261-291`

**This is the most important honest-reporting moment in this research.**

The CONTEXT.md says the guide should annotate the example profile with
"≥3 outbound branches" (D-05) and "highest betweenness centrality" (D-06).
**Neither phrase appears in `seed.py`.** Here is what the codebase actually
does (verbatim from `seed.py:265-289`):

```python
# Phase 21 PROF-04 + D-06/D-07: profile.diagram_types recommender
# D-06: match iff (trigger_tags ∩ node_tags OR node_type ∈ trigger_node_types)
#       AND len(main_nodes) >= min_main_nodes
# D-07: tiebreak = highest min_main_nodes wins; ties fall back to
#       declaration order (stable max).
suggested_template = _TEMPLATE_MAP[layout_type]
try:
    from graphify.profile import load_profile
    _profile = load_profile(vault_dir=None)
    _node_data = G.nodes[node_id]
    node_tags = set(_node_data.get("tags", []) or [])
    node_type = _node_data.get("file_type") or _node_data.get("node_type")
    candidates = [
        dt for dt in (_profile.get("diagram_types") or [])
        if (
            (set(dt.get("trigger_tags") or []) & node_tags)
            or (node_type is not None and node_type in set(dt.get("trigger_node_types") or []))
        )
        and len(main_nodes) >= int(dt.get("min_main_nodes", 2))
    ]
    if candidates:
        # max() is stable — ties fall back to declaration order (D-07)
        chosen = max(candidates, key=lambda dt: int(dt.get("min_main_nodes", 2)))
        if chosen.get("template_path"):
            suggested_template = chosen["template_path"]
except Exception:
    pass  # Never break seed build on profile errors
```

**What's actually true:**

- **D-06 (real, in code):** A `diagram_type` matches a candidate seed iff
  `(trigger_tags ∩ node_tags) OR (node_type ∈ trigger_node_types)` AND
  `len(main_nodes) >= min_main_nodes`.
- **D-07 (real, in code):** Tiebreak among matching `diagram_types` is
  *highest `min_main_nodes` wins*; ties resolve to *declaration order*
  (Python `max()` is stable on ties).

**What CONTEXT D-05/D-06 prescribe for the guide:**

- The example profile *teaches* a policy of "≥3 outbound branches" and
  "highest betweenness centrality" via the `decision-tree` entry's inline `#`
  comments. These are policy statements the *profile author* documents — they
  are NOT enforced by the loader. The loader only enforces `min_main_nodes`.

**How the guide should write this honestly:** Express the user's policy
choices as inline YAML comments and a paragraph that says (paraphrase):

> The `min_main_nodes` field is the only numeric gate the loader enforces.
> Higher-level policies — "fire only when the source node has ≥3 outbound
> branches" or "tiebreak by highest betweenness centrality" — are policies
> a profile author can declare in comments and enforce in their own
> downstream skill / agent logic. graphify's built-in recommender uses
> `min_main_nodes` for the gate and prefers higher `min_main_nodes` on
> ties (then declaration order).

This both satisfies CONTEXT D-05/D-06 (the *example profile* shows the
policy) and avoids misrepresenting the codebase to the reader.

---

## 5. Style Anchors

### 5.1 `INSTALLATION.md:1-12` — opening rhythm

```
# Installation

How to install graphify **from this repository** (without using the PyPI package) and register it as a skill in your AI coding assistant.

**Requirements:** Python 3.10+ and a supported assistant (...).

## Install from the repo

Clone or copy this repository, then run these commands from the **repository root** (...).
```

Pattern: H1 → 1-paragraph framing → bold "Requirements:" line → H2 procedural section → fenced bash. **Mirror this in `CONFIGURING_V1_5.md`.**

### 5.2 `ARCHITECTURE.md:1-12` — reference table style

```
# Architecture

graphify is a Claude Code skill backed by a Python library. ...

## Pipeline

```
detect()  →  extract()  →  build_graph()  →  cluster()  →  analyze()  →  report()  →  export()
```

| Module | Function | Input → Output |
|--------|----------|----------------|
```

Pattern: ASCII arrow flow + table for module/function/I-O. **Mirror this in
the guide's MCP Tool Integration section: one table per tool listing
arg/type/required/default, plus one table for return-meta keys.**

### 5.3 `README.md:343-365` — annotated YAML style

Example existing inline-comment annotation:

```yaml
naming:
  convention: title_case  # or kebab-case, preserve

merge:
  strategy: update
  preserve_fields: [rank, mapState, tags, created]
  field_policies:
    tags: union  # union, replace, or preserve
```

Pattern: top-of-file comment `# .graphify/profile.yaml (optional — defaults to Ideaverse ACE)`,
then keys with one-line `# comment` per non-obvious field. **The Phase 26
profile example must use this exact comment style.**

### 5.4 `README.md:367-375` — fenced-bash convention

```bash
# validate your profile before exporting
graphify --validate-profile ~/vaults/myproject

# export with dry-run preview
graphify --obsidian --obsidian-dir ~/vaults/myproject --dry-run

# full export
graphify --obsidian --obsidian-dir ~/vaults/myproject
```

Pattern: each command preceded by a `# intent` comment. **Mirror in the guide.**

### 5.5 `README.md:378-398` — existing v1.5-adjacent subsection rhythm

The new `### v1.5 Configuration Guide` lives directly after this block. Its
rhythm: H3 + 1-line description + fenced bash + 1-paragraph notes + final
1-line cross-reference. **The new subsection should be even shorter:
H3 + 1-line description + 1-line markdown link.** Per D-12.

---

## 6. Open Risks / Unknowns

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | The user's CONTEXT D-05/D-06 prescribed policy values (≥3 branches, betweenness) are not enforced by code. Risk: reader thinks they ARE enforced and is confused when their profile doesn't behave that way. | Guide must annotate honestly: D-05/D-06 are *policy values* declared in YAML comments; the loader enforces `min_main_nodes` and stable-max tiebreak only. Wording draft in §4 above. |
| R2 | `decision-tree` is not a value of `_VALID_LAYOUT_TYPES` in `seed.py` (the 6 built-ins). Setting `layout_type: decision-tree` in a profile entry will not error at load time (no enum validation on `layout_type`), but `_select_layout_type` won't *produce* `decision-tree` as a `suggested_layout_type` either — it can only emit the 6 built-ins. | Guide's `decision-tree` example is illustrative for `name` + `template_path` + tag/type triggers. Annotate: "graphify's heuristic returns one of the 6 built-in layouts; custom `name`/`template_path` lets your downstream skill recognize and render the type." Don't pretend `decision-tree` flows through `_select_layout_type`. |
| R3 | `--diagram-seeds` summary stdout is `f"...: {summary}"` where `summary` is a `dict.__repr__()` of the build result — not a stable line format. Quoting it verbatim risks being out-of-date if `build_all_seeds` return shape changes. | Quote the line with a placeholder: `[graphify] diagram-seeds complete: {<summary dict>}`. Note that exact contents may evolve. |
| R4 | ROADMAP.md:268 lists Phase 26 plans with `23-01-PLAN.md — Patch dedup.py edge-merge ...` (copy-paste artifact from Phase 23). Plan must overwrite this line with the real Phase 26 plan name. | Include a step in the plan to fix ROADMAP.md:268 → `26-01-PLAN.md — <name>`. |
| R5 | REQUIREMENTS.md:71-74 marks DOCS-01..04 plan column as `TBD`. Must be updated to point at `26-01-PLAN.md` during execution. | Include in the plan. |
| R6 | The `serve.py:1234-1250` canonical `_resolve_alias` is the *transitive-with-cycle-guard* form; the seed-tool versions at `serve.py:2590-2599` / `2686-2695` are *single-step* (no transitive walk). | Document both honestly in the MCP section. The single-step seed-tool version is sufficient because `seed_id` is a leaf identifier, not a graph node id traversed through chained aliases. |
| R7 | If PyYAML is not installed, the example profile won't be parsed at all (loader returns `_DEFAULT_PROFILE`). Worth a one-line note. | Add a "Prerequisites" line: `pip install -e ".[all]"` (mirrors CLAUDE.md install commands). |

---

## 7. Recommended Plan Skeleton

Single PLAN.md: `26-01-PLAN.md — Author CONFIGURING_V1_5.md + README cross-link + tracker updates (DOCS-01..04)`.

### Task group A — Author `CONFIGURING_V1_5.md` (DOCS-01, DOCS-02, DOCS-03)

**File:** `CONFIGURING_V1_5.md` (new, repo root).

**Required sections (recommended order):**

1. H1 + 1-paragraph framing ("What v1.5 adds; what this guide walks through.")
2. **Prerequisites** — `pip install -e ".[all]"`, an Obsidian vault path, `mcp` extra installed for the MCP section.
3. **Sample vault layout** — inline tree diagram (synthetic Atlas/Maps + Atlas/Dots/Things, 5-10 illustrative notes). Per D-02: described inline, no fixture.
4. **Step 1 — Promote nodes into the vault** (`graphify vault-promote --vault <path> --threshold 3`) + quote the verbatim summary line from §1.1.
5. **Step 2 — Generate diagram seeds** (`graphify --diagram-seeds [--vault <path>]`) + verbatim summary line from §1.2.
6. **Step 3 — Initialize Excalidraw template stubs** (`graphify --init-diagram-templates --vault <path>`) + verbatim summary line from §1.3.
7. **Step 4 — Install the Excalidraw skill** (`graphify install --platform excalidraw`) + note it copies `skill-excalidraw.md` into `.claude/skills/excalidraw-diagram/SKILL.md`.
8. **Step 5 — Invoke the skill** (`/excalidraw-diagram` in the AI client) + the verbatim `.mcp.json` block from §1.5.
9. **`.graphify/profile.yaml` reference** (DOCS-02) — complete annotated YAML with all 6 built-in `diagram_types` + the `decision-tree` custom entry. Inline `# comments` on the custom entry explaining (a) the loader-enforced gate (`min_main_nodes`), (b) the user's *policy* choice of "≥3 outbound branches" (annotation only, not enforced), (c) the user's *policy* choice of "highest betweenness centrality" tiebreak (annotation only). Plus 1-paragraph honesty note from §4 distinguishing loader gates from author-declared policies.
10. **MCP Tool Integration** (DOCS-03) — H2 section. For each tool: invocation example, verbatim `inputSchema` from §2.1/§2.2, return-meta key table, one realistic return example. Then a single `### Alias resolution and traversal defense` subsection citing `serve.py:1234-1250` canonical form (quote the function), noting the seed tools use the single-step variant at `serve.py:2590-2599 / 2686-2695`.

**Acceptance (grep-checkable):**

- `[ -f CONFIGURING_V1_5.md ]`
- `grep -c "vault-promote\|--diagram-seeds\|--init-diagram-templates\|install --platform excalidraw\|/excalidraw-diagram" CONFIGURING_V1_5.md` ≥ 5
- `grep -q "diagram_types:" CONFIGURING_V1_5.md` and contains `decision-tree`
- `grep -q "list_diagram_seeds" CONFIGURING_V1_5.md` and `grep -q "get_diagram_seed"` and `grep -q "_resolve_alias"`
- `grep -q "min_main_nodes" CONFIGURING_V1_5.md` (real gate documented)

### Task group B — Insert README cross-link (DOCS-04)

**File:** `README.md` — edit only.

**Insert after the existing `### Vault Promotion — graphify vault-promote` subsection (around `README.md:398`, before the `## Worked examples` H2):**

```markdown
### v1.5 Configuration Guide

End-to-end walkthrough of the v1.5 pipeline (`vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → skill invocation), the `.graphify/profile.yaml` `diagram_types:` schema, and the `list_diagram_seeds` / `get_diagram_seed` MCP tools. See [CONFIGURING_V1_5.md](CONFIGURING_V1_5.md).
```

Per D-12: one-line pitch + link, no duplicated abstract. Per D-13: insertion location anchored after Vault Promotion, before `## Worked examples`.

**Acceptance:** `grep -q "v1.5 Configuration Guide" README.md` and `grep -q "(CONFIGURING_V1_5.md)" README.md`.

### Task group C — Tracker hygiene

1. **`.planning/REQUIREMENTS.md:71-74`** — replace `TBD` with `26-01-PLAN.md` for DOCS-01..04 rows.
2. **`.planning/ROADMAP.md:268`** — overwrite the stale stub `23-01-PLAN.md — Patch dedup.py edge-merge to flatten source_file via _iter_sources; add 2 regression tests` with the real `26-01-PLAN.md — Author CONFIGURING_V1_5.md + README cross-link + tracker updates (DOCS-01..04)`.

**Acceptance:**

- `grep -q "DOCS-01 | Phase 26 | 26-01-PLAN.md" .planning/REQUIREMENTS.md` (and same for 02/03/04)
- `! grep -q "23-01-PLAN.md — Patch dedup.py" .planning/ROADMAP.md` (the stale line is gone from Phase 26)
- `grep -q "26-01-PLAN.md — Author CONFIGURING_V1_5.md" .planning/ROADMAP.md`

### Why one plan file (not two)

This is a single-document deliverable; splitting groups A/B/C across multiple plans would manufacture coordination overhead without value. Each task group is independently grep-checkable in CI-style verification, which keeps `/gsd-verify-work` honest without requiring multi-plan orchestration.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `decision-tree` custom type, when declared in profile.yaml, will pass `validate_profile()` so long as its keys are restricted to the 8-key allowlist (`name`, `template_path`, `trigger_node_types`, `trigger_tags`, `min_main_nodes`, `naming_pattern`, `layout_type`, `output_path`). The validator does not constrain `layout_type` to the 6-element built-in enum. | §3.3, §6 R2 | If `validate_profile` *does* enum-check `layout_type`, the example profile fails validation. **Quick mitigation:** the executor should run `graphify --validate-profile <vault>` against the example profile before publishing. (Verified by reading `profile.py:399` — only checks `isinstance(str)`, no enum check. So A1 holds.) |
| A2 | The README insertion site (`README.md:398`, after `### Vault Promotion`, before `## Worked examples`) is unchanged at execution time. | §5.5, Task B | Trivial: re-anchor by section header rather than line number when editing. |

All other claims in this research are tagged with file:line citations and were verified during this session.

---

## Sources

### Primary (HIGH confidence — read directly during research)

- `graphify/__main__.py:140-143` — `_PLATFORM_CONFIG["excalidraw"]`
- `graphify/__main__.py:1192-1478` — diagram-seeds + init-diagram-templates dispatch
- `graphify/__main__.py:1843-1867` — `install` command dispatch
- `graphify/__main__.py:2224-2255` — `vault-promote` argparse + summary print
- `graphify/seed.py:139-291` — `_select_layout_type` + `build_seed` + D-06/D-07 actual logic
- `graphify/seed.py:429-500` — `build_all_seeds` summary shape
- `graphify/serve.py:1234-1250` — canonical transitive-with-cycle `_resolve_alias`
- `graphify/serve.py:2553-2776` — `_run_list_diagram_seeds_core` + `_run_get_diagram_seed_core`
- `graphify/serve.py:3316-3357` — tool wrapper registration + `_handlers` dict
- `graphify/mcp_tool_registry.py:349-382` — verbatim Tool() declarations + inputSchema
- `graphify/profile.py:36-108` — `_DEFAULT_PROFILE` + `_VALID_TOP_LEVEL_KEYS`
- `graphify/profile.py:165-196` — `load_profile`
- `graphify/profile.py:367-404` — `diagram_types` schema validation
- `graphify/skill-excalidraw.md:1-30` — slash-command name + required `.mcp.json`
- `INSTALLATION.md:1-30` — style anchor
- `ARCHITECTURE.md:1-20` — style anchor
- `README.md:329-398` — insertion target + existing Obsidian section
- `.planning/REQUIREMENTS.md:33-36, 71-74` — DOCS-01..04 verbatim + tracker
- `.planning/ROADMAP.md:255-268` — Phase 26 entry + stale stub
- `.planning/phases/26-v1-5-configuration-guide-walkthrough-docs/26-CONTEXT.md` — locked decisions

### Secondary

- (none — no web search needed; all facts in repo)

### Tertiary

- (none)

---

## Metadata

**Confidence breakdown:**

- Pipeline command shapes: HIGH — argparse / sys.argv parsing read directly.
- MCP tool schemas: HIGH — `inputSchema` and return-meta keys read verbatim.
- `_resolve_alias` traversal-defense: HIGH — canonical form quoted from `serve.py:1234-1250`.
- Profile schema: HIGH — every accepted key enumerated from `profile.py:367-404`.
- D-06 / D-07 actual gating: HIGH — code at `seed.py:265-289` directly contradicts CONTEXT D-05/D-06 wording; honest annotation guidance provided.
- README insertion site: HIGH — confirmed via `README.md:329-398`.
- Skill invocation slash command: HIGH — `skill-excalidraw.md` frontmatter declares `trigger: /excalidraw-diagram`.

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days; v1.5 surface area is feature-frozen for this milestone)

## RESEARCH COMPLETE
