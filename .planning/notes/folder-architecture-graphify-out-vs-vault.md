---
title: "Folder Architecture: graphify-out/ vs --obsidian-dir"
date: 2026-04-16
context: UAT observation during v1.2 raised the question of why `graphify` and `graphify-out` appeared as two separate top-level folders when running `--obsidian --obsidian-dir`. Documents the intentional design separation and the decided lightweight fix.
---

# Folder Architecture: `graphify-out/` vs `--obsidian-dir`

## Observation

When running `graphify --obsidian --obsidian-dir graphify` (or any sibling path of the project root) in dev/test, the user sees **two** top-level output folders:

- `graphify-out/` — created by the build pipeline
- `graphify/` — the Obsidian vault written by `--obsidian-dir`

Question raised: *bug or feature? Should they collapse into one folder?*

## Verdict: Feature, Not Bug

This separation is **deliberate** and rooted in decisions **D-73** (CLI is utilities-only; skill is the pipeline driver) and **D-74** (`to_obsidian()` is a notes pipeline, not a vault-config-file manager).

### The Two Paths Have Different Owners

| Path | Role | Owner | Lifetime |
|------|------|-------|----------|
| `graphify-out/` | Pipeline working dir — `graph.json`, `GRAPH_REPORT.md`, `GRAPH_ANALYSIS.md`, snapshots, cache, telemetry, `agent-edges.json`, `annotations.jsonl`, `vault-manifest.json` | **graphify** (internal) | Regenerated on each run; gitignored in most projects |
| `--obsidian-dir <path>` | Destination Obsidian vault — notes with frontmatter, MOCs, wikilinks, user content | **user** (their vault) | Long-lived; user-edited between runs |

### Why They're Separate

- **Real usage flow**: `--obsidian-dir` typically points to an *existing* user vault (e.g., `~/Documents/MyVault/`), which predates graphify and survives after. It's never a subfolder of the project.
- **Pipeline contract**: The library reads `graphify-out/graph.json` (input) and writes notes to the vault (output). Mixing them would couple pipeline scratch state with user-curated content.
- **Manifest placement**: `vault-manifest.json` intentionally lives in the *parent* of the vault dir — alongside `graph.json` — because it's a graphify sidecar, not vault content. See `export.py:499-501`.

### Default Behavior Is Already One Folder

When `--obsidian` runs *without* an explicit `--obsidian-dir`, the default is `graphify-out/obsidian` — nested inside `graphify-out/`. One top-level folder. The two-folder appearance only emerges when a user explicitly passes `--obsidian-dir` to a sibling path, which in real usage would be an absolute path to their vault — not a sibling of the project root.

Code reference: `graphify/__main__.py:988-1075`:

```python
# --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run]
if cmd == "--obsidian":
    graph_path = "graphify-out/graph.json"
    obsidian_dir = "graphify-out/obsidian"  # ← default nests inside graphify-out/
    ...
```

## Options Considered

| Option | Effort | Verdict |
|--------|--------|---------|
| 1. Doc fix — clearer help text + runtime message on where things landed | ~10 min | **Selected** |
| 2. Add `--out-dir <root>` unifying flag (controls both pipeline root and vault) | ~4 hrs | Rejected for v1.3 — not enough signal it's a real workflow problem |
| 3. Inline vault in `graphify-out/` by default | Already implemented | No-op |

## Selected Fix (Option 1)

### Code changes (small)

1. **Expand `--obsidian` help block** (`__main__.py:910-914`) to state:
   > "Note: `--obsidian-dir` is your existing Obsidian vault (e.g., `~/Documents/MyVault/`). Pipeline artifacts stay in `graphify-out/` — these are two different folders with different owners."

2. **Post-run message** (`__main__.py:1073-1076`):
   > Before: `"wrote obsidian vault at <abs-path> — N actions (...)"`
   > After: `"wrote Obsidian vault at <abs-path> — N actions (...)\n  pipeline artifacts remain in <graphify-out path> (safe to gitignore)"`

3. **CLAUDE.md + skill.md docs** — add a short section explaining the two-folder separation for anyone running `--obsidian` from a dev loop.

### Why Not a Plan Slot

This is < 30 minutes of non-blocking documentation work. It doesn't deserve a plan slot in v1.3. Captured as a pending todo to fold into the next `--obsidian`-touching commit (likely during Phase 10 when cross-file extraction changes how `to_obsidian` receives its inputs).

## When to Revisit

Reopen this decision if any of the following happens:

- Multiple UAT sessions independently flag the two-folder layout as confusing
- A user asks to run graphify against several repos from a single workspace (real multi-project use case for `--out-dir`)
- v1.4 or later introduces a standalone-binary distribution where `graphify-out/` placement becomes less discoverable

## References

- Code: `graphify/__main__.py:988-1075`, `graphify/export.py:449-500`
- Decisions: D-73, D-74 (see `.planning/PROJECT.md` Key Decisions table)
- Related: `vault-manifest.json` placement logic (`export.py:499-501`)

---
*Captured during /gsd-explore session on 2026-04-16 while scoping v1.3. Addresses UAT observation from v1.2 testing.*
