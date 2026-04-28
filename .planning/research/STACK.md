# Stack Research: v1.8 Output Taxonomy & Cluster Quality

**Project:** graphify v1.8
**Researched:** 2026-04-28
**Focus:** Stack additions or changes for default vault layout, MOC-only communities, cluster-quality floor, concept naming, god-node taxonomy, repo identity, and migration guide.

## Verdict

No new required dependencies are needed. v1.8 should be implemented with existing required dependencies (`networkx`) plus stdlib modules already used throughout the project (`json`, `hashlib`, `os.replace`, `pathlib`, `re`, `subprocess`, `collections`). `PyYAML` remains the existing optional `obsidian` extra for vault profiles; do not promote it to required.

The stack change is mostly schema and routing, not infrastructure: extend `profile.py` defaults/validation, add small export-time helpers around `to_obsidian()`, add a naming cache alongside existing cache/manifest patterns, and thread one new repo identity option through the CLI/skill call path.

## Recommended Additions

### Profile Schema: Existing `dict` + Validation

Use `profile.py` as the only configuration home for new vault-output behavior.

Recommended keys:
- `clustering.min_community_size`: integer, default `2` or `3` depending product choice; validate bool-before-int like existing `topology.god_node.top_n`.
- `repo_identity`: string profile fallback for note naming/tags/manifests.
- `concept_naming`: small mapping for mode/cache controls if needed; keep defaults deterministic and profile-compatible.
- `folder_mapping` updates for Graphify-owned default layout; avoid a second layout config system.

Why: profile composition, provenance, preflight, defaults, and path-safety already exist. A new config loader would duplicate v1.7 work and weaken profile-side control.

### Community Quality: Existing `networkx`

Use `networkx` graph inspection for v1.8 cluster filtering:
- Isolates: `G.degree(node) == 0`; suppress MOC note generation only.
- Tiny connected clusters: `G.subgraph(nodes).number_of_edges() > 0`; merge their MOC representation into a synthetic `_Unclassified` community.
- Graph preservation: keep original node `community` data and JSON/GraphML exports unchanged unless a caller explicitly requests display-quality communities.

Integration point: add a post-processing helper near `cluster.py` or export-specific helper near `to_obsidian()`. Prefer export-time shaping if the requirement is "drop/merge notes, preserve graph data"; changing `cluster()` itself risks altering HTML/JSON/MCP behavior.

### Concept Naming: Existing LLM Path + Stdlib Fallback

Do not add an LLM SDK. Hybrid naming should use the existing skill/agent LLM orchestration to provide `community_labels` when available, with library-level deterministic fallback when labels are absent.

Fallback stack:
- `collections.Counter` for top labels/source terms.
- `re` for token cleanup.
- `hashlib.sha256` for stable cache keys and collision suffixes.
- Existing `safe_filename()`, `safe_tag()`, and `sanitize_label()` before rendering.

Cache stack:
- Add a small JSON sidecar under `graphify-out/cache/` or `graphify-out/concept-names.json`.
- Write atomically with `tmp.write_text(...)` + `os.replace(...)`, matching `cache.py` and manifest patterns.
- Key by graph/community fingerprint, not by community id alone, because ids are size-sorted and can shift after quality-floor changes.

### God-Node Taxonomy: Existing Templates and Export Routing

No new template engine. Split note classes through existing classification/rendering:
- Code-derived god nodes become `CODE_<repo>_<symbol>` notes.
- Concept god nodes/community MOCs remain MOC-shaped notes.
- Bidirectional links are rendered as plain wikilinks in existing templates/render contexts.

Integration point: extend classification context and templates, not `networkx` or graph schema. The graph can keep its current node/edge attributes; the taxonomy is a vault-output concern.

### Repo Identity: Stdlib Only

Use precedence: CLI flag > profile key > git remote/CWD fallback.

Recommended stack:
- CLI parsing in `__main__.py` with a new option such as `--repo-id` on `--obsidian`; mirror the current manual argument parser style.
- `profile.py` validation for `repo_identity`.
- `subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=repo_root, capture_output=True, text=True, timeout=2, check=False)` for fallback discovery.
- `Path.cwd().name` fallback when git is unavailable, remote is absent, or subprocess times out.
- `safe_tag()` / `safe_filename()` for normalized use in tags and filenames.

Do not add `GitPython`; invoking `git config` or falling back to CWD is enough and keeps package weight unchanged.

### Migration Guide: Markdown File Only

The `work-vault` to `ls-vault` guide needs no documentation framework. Write a plain Markdown guide in the repo, cross-link it from `README.md` or existing configuration docs, and include it in package data only if installed users must access it from the wheel.

Recommended content stack:
- Step-by-step commands using existing CLI flags (`--obsidian`, `--dry-run`, `--force`, profile validation/doctor where applicable).
- Before/after layout examples.
- Explicit cleanup/deprecation notes for legacy `_COMMUNITY_*` overview files.
- A dry-run-first real-vault checklist.

## Integration Points

| Area | Primary Files | Stack Impact |
|---|---|---|
| Default layout | `graphify/profile.py`, built-in templates | Config/default changes only |
| MOC-only communities | `graphify/export.py`, templates | Remove legacy community overview routing from default path |
| Cluster-quality floor | `graphify/export.py` or small helper near `cluster.py` | Existing `networkx`; no new algorithms |
| Concept naming | skill pipeline, `graphify/cache.py`, `graphify/export.py` | Stdlib JSON cache; no LLM SDK |
| God-node taxonomy | mapping/classification/templates, `graphify/export.py` | Existing render pipeline |
| Repo identity | `graphify/__main__.py`, `graphify/profile.py`, export context | Stdlib `subprocess` fallback only |
| Migration guide | docs/README/package-data if needed | Markdown only |

## Version and Dependency Implications

- Keep `requires-python = ">=3.10"` unchanged.
- Keep `networkx` unchanged; its current Louvain/graph APIs are already in use.
- Keep `PyYAML` optional under `obsidian`; profile-free default export must still work without it.
- Do not add required extras to `pyproject.toml`.
- Only update `pyproject.toml` package data if a new guide or built-in template must ship inside the wheel.

## Non-Goals

- No new graph clustering library. Leiden/graspologic remains optional and Louvain fallback remains sufficient.
- No `GitPython`, `python-slugify`, `Jinja2`, SQLite, vector database, or LLM client dependency.
- No Obsidian plugin or `.obsidian/graph.json` management.
- No rewrite of shipped v1.7 profile composition, merge engine, doctor, dry-run, or manifest systems.
- No change to canonical graph data just to improve vault note presentation.

## Risks

- **Community id instability:** cache naming by community id will break after sorting or min-size changes. Use member/content fingerprints.
- **Profile schema sprawl:** adding parallel layout/taxonomy config outside `profile.py` will bypass preflight/provenance. Keep all user-facing knobs in the profile schema.
- **Repo identity leakage:** raw remote URLs can include user/org names or credentials. Parse to a safe repo slug and never render the full remote URL into frontmatter by default.
- **Backward-compat confusion:** deprecating `_COMMUNITY_*` notes can leave old files in real vaults. The migration guide and dry-run output should call out orphaned legacy notes clearly.
- **LLM nondeterminism:** concept names must not change on every run. Cache accepted LLM names and require deterministic fallback labels when LLM output is missing or rejected.

## Confidence

**HIGH** for "no new required dependencies": all requested v1.8 features map cleanly onto existing Python, NetworkX, profile, export, merge, and cache patterns.

**MEDIUM** for exact schema key names: the implementation plan should finalize names after choosing whether cluster-quality filtering is global profile config or Obsidian-export-specific config.
