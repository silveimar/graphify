# v1.5 pipeline runbook (checklist)

Use this page as an ordered checklist. Full prose, YAML reference, and MCP tool details live in [`CONFIGURING_V1_5.md`](CONFIGURING_V1_5.md).

## Goal

Run the **v1.5 pipeline** end-to-end:

`vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → `/excalidraw-diagram` (with MCP servers configured).

---

## Before you start

1. **Python:** 3.10+
2. **graphify:** editable install from repo root with extras (PyYAML included):

   ```bash
   cd /path/to/graphify
   pip install -e ".[all]"
   ```

3. **Inputs:**
   - A writable **Obsidian vault** path (below: `$VAULT`)
   - **`graphify-out/graph.json`** from a completed graphify run on your corpus (same project where you run the commands)

Set a shell variable so the steps are copy-paste safe:

```bash
export VAULT="$HOME/vaults/myproject"   # change to your vault
```

Optional: confirm the vault has `.graphify/profile.yaml` with a `diagram_types:` block if you want custom diagram types; otherwise init-templates uses the six built-ins. See the [profile reference](CONFIGURING_V1_5.md#the-graphifyprofileyaml-reference) in the main guide.

---

## Step 0 — Produce `graphify-out/graph.json`

If you do not already have a graph:

```bash
cd /path/to/your-corpus-root
graphify .
```

(or your assistant’s `/graphify .` equivalent)

Confirm:

```bash
test -f graphify-out/graph.json && echo "ok"
```

---

## Step 1 — Promote nodes into the vault

Writes promoted notes under your vault from the current graph; respects `vault-manifest` semantics (does not clobber foreign notes).

```bash
graphify vault-promote --vault "$VAULT" --threshold 3
```

**Expect:** stderr line like `[graphify] vault-promote complete: promoted=...; skipped=...`

**Tune:** raise or lower `--threshold` to change minimum node degree for promotion.

---

## Step 2 — Generate diagram seeds

Emits `graphify-out/seeds/<seed_id>-seed.json` and `graphify-out/seeds/seeds-manifest.json`.

```bash
graphify --diagram-seeds --vault "$VAULT"
```

**Expect:** `[graphify] diagram-seeds complete: {...}`

**Note:** `--vault` is optional; if set, tag write-back goes through the merge planner (union-friendly).

**Verify:**

```bash
ls graphify-out/seeds/seeds-manifest.json
```

---

## Step 3 — Initialize Excalidraw template stubs

**Requires** `--vault`.

```bash
graphify --init-diagram-templates --vault "$VAULT"
```

**Expect:** `[graphify] init-diagram-templates complete: wrote <N> stub(s) (force=False)`

**Verify:** under `$VAULT`, one stub per `diagram_types` entry (or six defaults if the block is empty).

---

## Step 4 — Install the Excalidraw skill (Claude Code path)

Copies packaged `skill-excalidraw.md` into `.claude/skills/excalidraw-diagram/SKILL.md` (no CLAUDE.md anchor).

```bash
graphify install --platform excalidraw
```

Run from a directory where you want client config written (typically your project root), or understand where your platform expects skills to live.

---

## Step 5 — Configure MCP and invoke the skill

1. Merge this block into your client’s MCP config (graphify does **not** edit it for you). Adjust `command` paths if `graphify` / `uvx` / `npx` are not on your default `PATH`:

   ```jsonc
   {
     "mcpServers": {
       "graphify":   { "command": "graphify", "args": ["serve"] },
       "obsidian":   { "command": "uvx",      "args": ["mcp-obsidian"] },
       "excalidraw": { "command": "npx",      "args": ["-y", "@excalidraw/mcp-server"] }
     }
   }
   ```

2. Restart the client so MCP servers load.

3. In the client, run:

   ```
   /excalidraw-diagram
   ```

**Runtime contract:** the skill uses **graphify** for seeds, **obsidian** for note placement, **excalidraw** for canvas generation.

---

## Quick verification matrix

| Artifact / behavior | Check |
|---------------------|--------|
| Graph input | `graphify-out/graph.json` exists |
| Promotion | Vault has new/updated promoted notes; stderr shows completion |
| Seeds | `graphify-out/seeds/*.json` + `seeds-manifest.json` |
| Stubs | Vault has `.excalidraw.md` stubs under paths from `diagram_types` |
| Skill | `.claude/skills/excalidraw-diagram/SKILL.md` present (after step 4) |
| MCP | Three servers respond; `/excalidraw-diagram` can list/open seeds |

---

## If something fails

| Symptom | What to check |
|---------|----------------|
| `vault-promote` no-ops | Threshold too high; graph too small; manifest / foreign-note rules — see main guide Step 1 |
| No seeds | Empty or weak graph; re-run corpus with more structure; inspect `graphify-out/seeds/` |
| `init-diagram-templates` errors on missing `--vault` | Pass `--vault "$VAULT"` (required) |
| Skill cannot see seeds | `graphify serve` MCP must see the same `graphify-out/` (cwd / project root) |
| obsidian/excalidraw MCP errors | `uvx`, `npx`, and network available; Node installed for `npx` |

---

## Deep dive

- **Profile YAML** (`diagram_types`, merges, triggers): [`CONFIGURING_V1_5.md` § The `.graphify/profile.yaml` reference](CONFIGURING_V1_5.md#the-graphifyprofileyaml-reference)
- **MCP tools** `list_diagram_seeds` / `get_diagram_seed` and alias behavior: [`CONFIGURING_V1_5.md` § MCP Tool Integration](CONFIGURING_V1_5.md#mcp-tool-integration)
- **Vault profile schema** (shared concepts): [`PROFILE-CONFIGURATION.md`](PROFILE-CONFIGURATION.md)
