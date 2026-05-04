# Phase 60: Milestone-level E2E integration tests — Research

**Researched:** 2026-05-03
**Domain:** subprocess-level integration testing (CLI ↔ pipeline ↔ vault adapter ↔ profile composition ↔ elicitation sidecar)
**Confidence:** HIGH (all claims grounded in codebase reads; no training-data assumptions)

## Summary

Phase 60 adds two `tmp_path`-scoped subprocess tests in a single new file (`tests/test_e2e_integration.py`) closing the v1.11 audit's Flow 2 (composition + override ladder) and Flow 3 (elicit → update-vault sidecar handoff) gaps. Scope, file layout, helper reuse, fixture strategy, and assertion granularity are all locked by `60-CONTEXT.md`. Research focused on the technical-fit gaps a planner needs to write tight, non-flaky TDD tasks: exact CLI surfaces, precondition contracts (vault must contain `.obsidian/` and `.graphify/profile.yaml` with an `output:` block), the precise `artifacts_dir` placement (`<vault>.parent/graphify-out/`) that controls where the sidecar must live for E2E-02's handoff, the override ladder tier order (`mapping_rule_templates` → `community_templates` → `note_type_templates` → base), the frontmatter field set the assertions can target, and the elicitation node shape so substring assertions can hit deterministic content.

**Primary recommendation:** Both tests must (1) build a `tmp_path` vault containing `.obsidian/`, `.graphify/profile.yaml` (with `output:` block), and any referenced template fragments under `.graphify/templates/`; (2) write a small extractable corpus (1–2 `.py` files) to a sibling `--input` directory; (3) for E2E-02, run `elicit` with `--vault <vault>` (or `--output <vault>.parent/graphify-out`) so the sidecar lands at the same `artifacts_dir` that `update-vault` will read; (4) assert the rendered notes under `<vault>/<output.path>` via YAML frontmatter parse + targeted body substring.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Subprocess invocation + env | Test harness (pytest) | — | `_graphify` helper already isolates subprocess + PYTHONPATH |
| CLI parsing / dispatch | `graphify/__main__.py` | — | Tests must hit real `python -m graphify` argv path; locked by CONTEXT |
| Profile load + composition | `graphify/profile.py` | `graphify/templates.py` | Profile loaded inside `run_update_vault`; ladder lives in templates |
| Override ladder resolution | `graphify/templates.py::_resolve_note_template` | profile lists | 4-tier resolution; first-match-wins per tier |
| Block expansion + `${}` substitution | `graphify/templates.py` | — | D-16 ordering invariant: blocks before substitution |
| Elicit sidecar I/O | `graphify/elicit.py` | `output.py` (artifacts_dir) | Sidecar at `<artifacts_dir>/elicitation.json` |
| Pipeline execution | `graphify/migration.py::run_update_vault` → `pipeline.run_corpus` → `build` → `cluster` → `to_obsidian` | — | `update-vault` runs the full chain |
| Note rendering | `graphify/templates.py` + `graphify/export.py::to_obsidian` | merge layer | Frontmatter built by `_build_frontmatter_fields` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| pytest | (project pin in `pyproject.toml [test]`) | Test framework | Already in CI matrix on Py 3.10 + 3.12 |
| stdlib `subprocess` | n/a | CLI invocation | Existing pattern in `tests/test_main_flags.py` |
| stdlib `textwrap.dedent` | n/a | Inline YAML in test source | Locked by CONTEXT (per-test inline fixtures) |
| stdlib `json` | n/a | Sidecar shape, graph fixture | Used by all comparable tests |
| PyYAML | already required by vault path (`output.py:354` raises if missing) | Profile parsing inside graphify; **also needed in tests** to parse rendered note frontmatter | Standard frontmatter parser; install path already gated for vault use |

`[VERIFIED: graphify/output.py:354-360 raises a refusal if PyYAML is not installed when CWD is a vault]` — so the test environment must have PyYAML present anyway. CI `[mcp,pdf,watch]` install path includes it transitively via `graphifyy[obsidian]`.

### Supporting
| Library | Purpose | When to Use |
|---|---|---|
| `networkx` | Already imported by `tests/test_integration.py` for `_make_graph`/`_minimal_graph` | NOT needed by Phase 60 — `update-vault` consumes a corpus directory, not a `nx.Graph` |

**No new dependencies.** Everything needed is already in `pyproject.toml` and present on CI.

### Alternatives Considered (and locked out by CONTEXT)
| Instead of | Could Use | Verdict |
|---|---|---|
| inline YAML | `tests/fixtures/profiles/<new>/` directory | LOCKED OUT — inline preferred per CONTEXT |
| `_run_cli` (no PYTHONPATH) | `_graphify` from `test_main_flags.py` | LOCKED — `_graphify` chosen |
| splitting into two test files | one file, two tests | LOCKED — one file |

## Architecture Patterns

### System Architecture Diagram

```
[ tmp_path / vault ]                       [ tmp_path / corpus ]
  ├── .obsidian/                              └── sample.py  (extractable)
  ├── .graphify/profile.yaml  (inline YAML, dedented)
  └── .graphify/templates/   (referenced by mrt / ntt)
                              │
                              ▼
                   subprocess: python -m graphify [--vault <vault>] elicit       (E2E-02 only)
                              │      writes <vault>.parent/graphify-out/elicitation.json
                              ▼
                   subprocess: python -m graphify update-vault --input <corpus> --vault <vault>
                              │
                              ├─ resolve_output(<vault>) ──► artifacts_dir = <vault>.parent/graphify-out
                              ├─ load_profile(<vault>)
                              ├─ run_corpus(<corpus>) ──► extraction
                              ├─ merge_elicitation_into_build_inputs([extraction], artifacts_dir)
                              │      auto-discovers <artifacts_dir>/elicitation.json IF present
                              ├─ build → nx.Graph
                              ├─ cluster
                              └─ to_obsidian(G, communities, <vault>/<output.path>, profile=profile, dry_run=True, return_render_context=True)
                                       │  rendered_notes returned for migration preview
                                       │  override ladder applied here:
                                       │    1) mapping_rule_templates  (rule_id match)
                                       │    2) community_templates     (label/id match)
                                       │    3) note_type_templates     (note_type match)
                                       │    4) base default
                                       │  block expansion BEFORE ${} substitution (D-16)
                                       ▼
                              writes notes under <vault>/<output.path>/...   ← test parses these
                              writes preview JSON under artifacts_dir/migrations/migration-plan-<id>.json
```

### Recommended Test File Structure

```
tests/test_e2e_integration.py
├── module docstring (Phase 60, E2E-01/E2E-02)
├── _graphify(...)            # subprocess wrapper (copied verbatim from test_main_flags.py:15)
├── _write_vault(tmp_path, profile_yaml, *, templates=None) → Path
│       creates .obsidian/, .graphify/profile.yaml, optional templates/
├── _write_corpus(tmp_path) → Path
│       creates a sibling dir with 1–2 .py files (smallest extractable)
├── _read_frontmatter(note_path) → dict
│       splits "---\n…\n---\n" preamble, yaml.safe_load
├── test_e2e_compose_override_ladder       # E2E-01
└── test_e2e_elicit_then_update_vault      # E2E-02
```

### Pattern 1: Subprocess wrapper (verbatim from `test_main_flags.py:15-34`)
```python
def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    worktree_root = Path(__file__).resolve().parent.parent  # tests/.. → repo root
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd), env=full_env,
        capture_output=True, text=True, timeout=60,
    )
```
`[VERIFIED: tests/test_main_flags.py:15-39]`

**Gotchas the planner must encode:**
- `worktree_root` is `Path(__file__).resolve().parent.parent` — relies on the new test file living in `tests/` (one level deep). Encode as a precondition.
- `timeout=60` is sufficient for a 1–2 file corpus; the full pipeline (extract→build→cluster→render+merge-preview) completes in well under that.
- Use `check=False` (subprocess.run default; `_graphify` does not pass `check=True`). Assert `result.returncode == 0, f"stderr={result.stderr}"` — the f-string surfaces failure context.
- `env` may need `GRAPHIFY_ELICIT_LLM` explicitly **unset** to ensure `maybe_deepen_session` stays a no-op (see `graphify/elicit.py:155-160`). `os.environ.copy()` already inherits whatever the test runner has — safer to defensively pop it: `full_env.pop("GRAPHIFY_ELICIT_LLM", None)`.

### Pattern 2: `update-vault` invocation contract
`[VERIFIED: graphify/__main__.py:3080-3124, graphify/migration.py:166-265]`

```
graphify update-vault --input <corpus_dir> --vault <vault_dir> [--router] [--verbose]
                      [--repo-identity <slug>] [--apply --plan-id <id>]
```

**Required preconditions for the vault** (enforced inside `run_update_vault`):
1. `<vault>/.obsidian/` MUST be a directory (`migration.py:182` raises `ValueError` otherwise; CLI catches and exits 1 with `error: target vault must contain .obsidian: …`).
2. `<vault>/.graphify/profile.yaml` MUST exist AND must contain an `output:` block with both `mode` and `path` (`output.py:325-330` raises `_refuse` → SystemExit(1)). Valid `mode` values: `"vault-relative"`, `"absolute"`, `"sibling-of-vault"`.
3. `<corpus>` directory must exist and ideally contain extractable files (Python `.py`, etc.). `run_corpus` walks via `detect()`; an empty corpus is allowed but yields zero extracted nodes — elicitation contributions still merge in for E2E-02.

**Default invocation behavior:** `update-vault` runs in **preview mode** (no `--apply`). It still calls `to_obsidian(..., dry_run=True, return_render_context=True)` (`migration.py:218-225`). **`dry_run=True` returns a `MergePlan`/`MergeResult` render context tuple BUT the preview path still writes** the migration artifacts (`migration.py:284`) — and crucially, the rendered_notes are computed in-memory but DO NOT touch the vault filesystem.

**THIS IS A CRITICAL FINDING for the planner:** preview-mode `update-vault` does NOT write `.md` files to the vault. The test assertions cannot read rendered notes off disk — they must hit the rendered-notes data via either:
   - **(a)** running `update-vault` with `--apply --plan-id <id>` after first running preview to harvest the plan_id (two subprocess calls), OR
   - **(b)** asserting against the migration preview JSON written under `<artifacts_dir>/migrations/migration-plan-<id>.json` and the markdown report. This file contains `MergeAction` rows but NOT full rendered note bodies — the body content is not persisted in preview.

Verified by reading `migration.py:218-265,283-289`: in preview mode (`apply=False`), `apply_merge_plan` is NEVER called. The function returns the preview dict and writes JSON+markdown artifacts. Rendered note bodies live only in the in-memory `rendered_notes` list returned by `to_obsidian`.

**Implication for the plan:** E2E-01 and E2E-02 must invoke `update-vault` **twice** — once for preview to capture `plan_id`, once with `--apply --plan-id <id>` so notes actually land on disk. The CLI handler exits non-zero on `--apply` without `--plan-id` (`__main__.py:3107-3109`). The plan_id is in the preview JSON at `<artifacts_dir>/migrations/migration-plan-<id>.json` (the path itself encodes the id; also stored under preview key `"plan_id"`).

Alternative path the planner can consider: ask whether `update-vault` should grow a `--apply-immediately` / `--no-preview` flag for one-shot apply, or whether the test should hit `--obsidian` (which DOES write notes directly via `to_obsidian` without dry_run) instead. **`--obsidian` requires a pre-built `graph.json`** (`__main__.py:1731-1840`), so it would require an additional `graphify run` (or in-process) step to produce one. Both paths are viable; the locked-by-CONTEXT command is `update-vault`, so the planner should default to the **two-call preview-then-apply** pattern. Surface this for the discuss-phase to confirm if needed.

`[ASSUMED]` — that two subprocess calls (preview, then apply) is acceptable within the locked scope. CONTEXT.md says "two subprocess calls in sequence" only for E2E-02 (elicit + update-vault), not for E2E-01. **This is a real ambiguity the planner must surface.** The cleanest interpretation: E2E-01 makes two `update-vault` calls (preview, then apply); E2E-02 makes three calls (elicit, update-vault preview, update-vault apply). If user prefers one apply call, they can switch to running `graphify run --vault <vault> --input <corpus>` followed by `graphify --obsidian` — but `run` does not consume the elicitation sidecar in the same way; `update-vault` is the canonical merge path.

### Pattern 3: `elicit` invocation contract
`[VERIFIED: graphify/__main__.py:2523-2611, graphify/elicit.py:215-275]`

```
graphify [--vault <vault>] elicit [--output <PATH>] [--demo] [--force] [--dry-run]
```

- The vault flag may be **global** (before `elicit`) or **local** (after `elicit`); both are accepted. The vault pin sets `artifacts_dir` to `<vault>.parent / graphify-out` (D-11 sibling-of-vault rule, `output.py:392`).
- Without `--demo`, the scripted answers are all empty strings → produces nodes with labels like `(empty: rhythms)`. Use `--demo` to produce nodes with the canned answers (`__main__.py:2563-2570`):
  - `rhythms` → `"Daily standup, weekly retro"`
  - `decisions` → `"Prefer small PRs"`
  - `dependencies` → `"Platform team for deploys"`
  - `knowledge` → `"Internal runbooks are outdated"`
  - `friction` → `"Context switching"`
- Sidecar landing path: `<artifacts_dir>/elicitation.json`. Filename constant: `ELICITATION_SIDECAR_FILENAME = "elicitation.json"`.
- Sidecar JSON shape (`elicit.py:241-267`):
  ```json
  {
    "version": 1,
    "extraction": {"nodes": [...], "edges": [...]},
    "meta": {"updated_at": "<iso>", "mode": "write"}
  }
  ```
- The hub node has `id="elicitation_hub"`, `label="Elicitation session"`, `file_type="rationale"`. Per-dimension nodes: `elicitation_rhythms`, `elicitation_decisions`, `elicitation_dependencies`, `elicitation_knowledge`, `elicitation_friction` — each with edge `(elicitation_hub) --contains--> (elicitation_<dim>)`.

**For E2E-02:** use `--demo` so labels carry deterministic, non-empty strings the assertions can grep for. After elicit, expected sidecar at `<vault>.parent/graphify-out/elicitation.json` (use `--vault <vault>` so `_resolve_cli_paths` yields the same `artifacts_dir` as `update-vault`).

`[VERIFIED: __main__.py:2566-2580]` — elicit's `_resolve_cli_paths(opts.output, global_explicit=g_vault_exp, local_explicit=_lv_e, …)` will return artifacts_dir = `<vault>.parent / graphify-out` when `--vault <vault>` is passed (because `resolve_execution_paths` defers to `resolve_output(vault)` which sets the sibling-of-vault path).

### Anti-Patterns to Avoid

- **DO NOT** rely on the rendered notes being on disk after `update-vault` preview. Only `--apply` materializes notes.
- **DO NOT** put profiles under `tests/fixtures/` — CONTEXT locks inline YAML.
- **DO NOT** import `to_obsidian` directly to bypass subprocess — the whole point is end-to-end coverage. Tests must invoke the real CLI.
- **DO NOT** use `subprocess.run(check=True)` — assertions on `returncode == 0, f"stderr={result.stderr}"` give better failure surface.
- **DO NOT** use `os.urandom`-style randomness in the corpus — clustering must be deterministic; Leiden uses `seed=42` (per `graphify/cluster.py`), and corpus content must be fixed strings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Subprocess invocation | A custom Popen wrapper | `_graphify` from `test_main_flags.py:15` | Already battle-tested on the worktree-PYTHONPATH gotcha |
| Frontmatter parsing | regex-on-text | `yaml.safe_load(content.split('---', 2)[1])` | The `---` delimiter pattern is canonical and `_build_frontmatter_fields` produces YAML-safe output (PyYAML already required) |
| Profile YAML construction | line-by-line concatenation | `textwrap.dedent("""…""")` | Locked by CONTEXT; preserves indentation correctness |
| Graph fixture | a hand-built `nx.Graph` | NONE — `update-vault` does not consume graphs; it consumes a corpus dir | Adapting `_make_graph` is **not applicable** here; the planner needs a tiny `.py` corpus instead |
| Elicit sidecar JSON | hand-construct the dict | run `graphify elicit --demo` and let it write the sidecar | E2E-02 explicitly requires the sidecar to come from real `elicit` invocation |
| `.obsidian/` marker | symlinks / git-tracked dir | `(<vault>/.obsidian).mkdir()` (empty dir is sufficient) | `is_obsidian_vault()` only checks `is_dir()` (`output.py:144`) |

## Runtime State Inventory

> Phase 60 is greenfield test code only. Sub-bullets below confirm "nothing applies" by category to satisfy the rename/refactor checklist defensively.

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | None — Phase 60 is pure new test code; no rename of stored ids/keys. | None |
| Live service config | None — no external services involved. | None |
| OS-registered state | None — no Task Scheduler / launchd / pm2 entries. | None |
| Secrets/env vars | `GRAPHIFY_ELICIT_LLM` — should be defensively unset in test env to keep `maybe_deepen_session` a no-op. | Pop in `_graphify` env or document precondition |
| Build artifacts | None — pytest auto-discovers new test files; no installed-package state to invalidate. | None |

## Common Pitfalls

### Pitfall 1: Vault precondition order
**What goes wrong:** `update-vault` exits 1 with `error: target vault must contain .obsidian` if the vault dir lacks `.obsidian/`.
**Why it happens:** `migration.py:182` enforces this before any other validation.
**How to avoid:** Always `(<vault>/.obsidian).mkdir(parents=True)` BEFORE writing the profile.
**Warning signs:** `result.returncode == 1` with stderr containing `must contain .obsidian`.

### Pitfall 2: Missing `output:` block in profile
**What goes wrong:** `update-vault` exits 1 with `[graphify] CWD is an Obsidian vault (...) but profile.yaml has no 'output:' block.`
**Why it happens:** `output.py:325-330` raises `_refuse(...)` — SystemExit(1).
**How to avoid:** Every inline profile MUST include:
```yaml
output:
  mode: vault-relative
  path: Atlas/Sources/Graphify
```
**Warning signs:** stderr contains `no 'output:' block`.

### Pitfall 3: Sidecar artifacts_dir mismatch (E2E-02 specifically)
**What goes wrong:** `elicit` writes sidecar to a different `artifacts_dir` than `update-vault` reads from → silent no-op merge → assertions fail with no obvious cause.
**Why it happens:** Without `--vault`, `elicit` resolves `artifacts_dir` from CWD (default → `<cwd>/graphify-out`). `update-vault` resolves it from the vault path → `<vault>.parent/graphify-out`. These differ.
**How to avoid:** Pass `--vault <vault>` to `elicit` (either as global `graphify --vault <vault> elicit --demo` or local `graphify elicit --vault <vault> --demo`). Verify between subprocess calls that `<vault>.parent/graphify-out/elicitation.json` exists.
**Warning signs:** `merge_elicitation_into_build_inputs` returns the input list unchanged because `load_elicitation_sidecar` returns None (`elicit.py:294-300`); rendered notes contain no elicitation labels.

### Pitfall 4: Override ladder tier-2 (community_templates) interference
**What goes wrong:** The CONTEXT requires E2E-01 to assert the ordering: block expansion → `${}` → ladder. But the ladder has 4 tiers. If the test profile happens to define a `community_templates` rule that matches by accident, it shadows `note_type_templates` (tier 3) — assertion confusion.
**Why it happens:** Tier 2 (`community_templates`) sits between mrt and ntt (`templates.py:1660-1707`).
**How to avoid:** Inline profile should EITHER:
- (a) define ONLY `mapping_rule_templates` + `note_type_templates` and NO `community_templates`, OR
- (b) explicitly choose community names/ids that never match any community_templates rule.
**Warning signs:** assertion that ntt template was applied fails because community template was applied instead.

### Pitfall 5: Block expansion vs `${}` ordering — what to assert
**What goes wrong:** If the override template is too simple, you can't distinguish "block expansion before substitution" from "no blocks at all."
**Why it happens:** Block expansion is `templates.py:1504,1520,1867,1886` — `_expand_blocks` runs, then `_BlockTemplate.safe_substitute`. To prove the ordering, the override template must contain a block (e.g., `{{#if_note_type_thing}}…{{/if}}`) AND a `${}` placeholder, AND a node label that contains a literal `${`-like character so we can prove substitution doesn't happen on raw label content.
**How to avoid:** Override template contains:
- At least one block: `{{#connections}}- ${conn.label} (${conn.relation})\n{{/connections}}`
- At least one substitution: `${label}`
- A unique sentinel string: `OVERRIDE_NTT_THING_MARKER`
Assert both the sentinel and the expanded block content appear in the rendered note.
**Warning signs:** weak assertion — sentinel appears even if blocks were never expanded.

### Pitfall 6: `to_obsidian` `dry_run=True` does not write notes
**What goes wrong:** Test reads `<vault>/<output.path>/*.md` after preview-mode `update-vault` and finds zero files.
**Why it happens:** Preview path calls `to_obsidian(..., dry_run=True, return_render_context=True)` and never reaches `apply_merge_plan` (`migration.py:218-265`).
**How to avoid:** Run `update-vault` twice — preview to get plan_id, then `--apply --plan-id <id>` to actually write.
**Warning signs:** empty rendered notes; only `<artifacts_dir>/migrations/migration-plan-*.json|md` files exist.

### Pitfall 7: Clustering minimum size
**What goes wrong:** `_DEFAULT_PROFILE` has `mapping.min_community_size: 6` — a tiny synthetic corpus produces communities below threshold and gets bucketed differently.
**Why it happens:** Default profile filter (`graphify/profile.py:124`).
**How to avoid:** Inline profile MUST override: `mapping: {min_community_size: 1}` (or 2). The community_templates fixture under `tests/fixtures/profiles/community_templates/.graphify/profile.yaml` already does this — `min_community_size: 3`.
**Warning signs:** clustering yields no community with members → MOC notes don't render → ntt-targeting assertion fails.

## Code Examples

### Smallest valid profile YAML exercising both ntt and mrt (E2E-01)

```yaml
# Source: synthesized from tests/fixtures/profiles/community_templates/.graphify/profile.yaml
#         + graphify/profile.py::_DEFAULT_PROFILE
#         + Phase 56 validators (profile.py:773-870)
output:
  mode: vault-relative
  path: Atlas/Sources/Graphify
taxonomy:
  version: v1.8
  root: Atlas/Sources/Graphify
  folders:
    moc: MOCs
    thing: Things
    statement: Statements
    person: People
    source: Sources
    default: Things
    unclassified: MOCs
mapping:
  min_community_size: 1
naming:
  convention: kebab-case
mapping_rule_templates:
  - match: rule_id
    pattern: e2e-test-rule
    template: templates/mrt-rule.md
note_type_templates:
  - match: note_type
    pattern: thing
    template: templates/ntt-thing.md
```

Template `templates/ntt-thing.md` (proves block expansion + `${}`):
```
${frontmatter}
# OVERRIDE_NTT_THING_MARKER: ${label}

{{#if_note_type_thing}}NTT_BLOCK_RAN{{/if}}

{{#connections}}
- ${conn.label} via ${conn.relation}
{{/connections}}
```

`[VERIFIED: graphify/templates.py:172-180 (D-16 ordering invariant), 1504/1520/1867/1886 (expand_blocks → safe_substitute call sites), 1689-1707 (note_type_templates tier 3)]`

### Smallest valid corpus

```python
# <corpus_dir>/sample.py
class TransformerLayer:
    def __init__(self, dim):
        self.dim = dim
    def forward(self, x):
        return x

class AttentionHead:
    def attend(self, x):
        return x
```

Two classes + methods → tree-sitter Python extractor produces `defines_class` / `defines_function` / `contains` edges. With `min_community_size: 1`, Leiden produces ≥1 community.

### Frontmatter assertion targets (E2E-01)

`[VERIFIED: graphify/templates.py:803-849 _build_frontmatter_fields]` — emitted field order:
```
up, related, collections, created, tags, type, file_type, source_file, source_location, community, cohesion
```

Distinguishing fields per note-type:
| Field | E2E-01 assertion value |
|---|---|
| `type` | One of `{moc, community, thing, statement, person, source, code}` — assert `== "thing"` for ntt-targeted note |
| `tags` | List containing `community/<slug>` — confirms classification reached |
| `community` | String — confirms a community membership was assigned |
| `cohesion` | Float — present only for `moc`/`community` types (see line 848) — assert ABSENT for `thing` notes |

### Elicitation visibility assertion targets (E2E-02)

The elicit demo answers (locked literals from `__main__.py:2563-2570`) appear as **node labels** in `file_type=rationale` nodes. `to_obsidian` renders rationale-typed nodes (verified by `_KNOWN_NOTE_TYPES` including no `rationale` directly, but the node is still emitted as a member of its community MOC).

For E2E-02 assertions, inspect the rendered MOC for the elicitation hub's community. Substrings to grep in note bodies:
- `"Daily standup, weekly retro"` (rhythms)
- `"Prefer small PRs"` (decisions)
- `"Internal runbooks are outdated"` (knowledge)
- `"Elicitation session"` (hub label)

These reach the rendered output via the members section / wikilinks. Lower-risk assertion: search ALL rendered `*.md` for at least 3 of the 5 demo strings (avoids brittleness to which note carries them).

`[VERIFIED: graphify/elicit.py:113-145, graphify/__main__.py:2563-2570]`

### Frontmatter parser helper (Phase 60–local)

```python
import yaml
def _read_frontmatter(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, fm, _ = text.split("---\n", 2)  # third element is the body
    return yaml.safe_load(fm) or {}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| flat `_COMMUNITY_<n>.md` dump | profile-driven Atlas/-shaped tree | Phase 5 (D-74) | E2E tests must look under `<vault>/<output.path>/MOCs/` etc., not flat root |
| single template per note_type | 4-tier override ladder | Phase 56 (CFG-01, D-56.03) | E2E-01's whole reason for existing |
| `--obsidian` writes notes directly | `update-vault` writes via preview→apply two-step | Phase 12+ migration phases | Plan must call `update-vault` twice for E2E-01/E2E-02 |
| sidecar lived under `graphify-out/cache/` | sidecar at `<artifacts_dir>/elicitation.json` | Phase 39-02 | E2E-02 must compute sibling-of-vault artifacts dir |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The user accepts that E2E-01 and E2E-02 each invoke `update-vault` **twice** (preview, then `--apply --plan-id`) so notes land on disk for assertion. CONTEXT.md says "two subprocess calls in sequence" only for E2E-02; the E2E-01 case is implicit. | Pitfall 6 + Pattern 2 | If user expected one call only, the plan must instead use `--obsidian` (requires a separate `graphify run` to produce `graph.json`) — different test structure, possibly different file invocation count. **Surface to discuss-phase or planner clarification.** |
| A2 | A 2-class Python file is sufficient corpus to produce ≥1 community at `min_community_size: 1`. | Code Examples | If clustering yields 0 communities, MOC rendering does not occur and ntt-targeting assertion fails. Mitigation: bump corpus to 3 classes or pin `min_community_size: 1`. |
| A3 | The community-templates fixture's `min_community_size: 3` is the right reference; reducing to 1 is safe for synthetic two-class corpus. | Pitfall 7 | If fewer-than-3 community filter has subtle interactions with `to_obsidian`, MOC may still be skipped. Verify in TDD RED phase by inspecting render context. |
| A4 | `--demo` elicit answers are locked literals and stable across CI runs. | E2E-02 assertion targets | Verified at `__main__.py:2563-2570` in this session — but if Phase 57 ever rotates wording, tests need updating. |

## Open Questions

1. **One-call vs. two-call `update-vault` for E2E-01.**
   - What we know: `update-vault` preview does NOT write notes; `--apply` requires `--plan-id`.
   - What's unclear: whether the user/planner is OK with two `update-vault` invocations per test (call 1: preview, capture plan_id; call 2: apply).
   - Recommendation: **Default to two-call.** If the planner wants one-call, switch to `graphify run` + `graphify --obsidian` (different LOCKED-DECISION territory; raise to discuss-phase).

2. **Sidecar landing in E2E-02 if elicit is invoked without `--vault`.**
   - What we know: Without `--vault`, elicit writes to `<elicit_cwd>/graphify-out/elicitation.json`.
   - What's unclear: should the test rely on `--vault` propagation OR run elicit with `cwd=<vault>` (which CWD-detects the vault and auto-adopts the profile)?
   - Recommendation: **Use explicit `--vault <vault>`** — most readable, doesn't depend on CWD detection's quirks (`is_obsidian_vault()` is CWD-only, no parent walk per D-04).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.10 | CI matrix | ✓ | 3.10 (CI) | — |
| Python 3.12 | CI matrix | ✓ | 3.12 (CI) | — |
| pytest | test runner | ✓ | per pyproject `[test]` | — |
| PyYAML | profile load + frontmatter parse | ✓ | per pyproject (transitive via `[mcp,pdf,watch]` install per CLAUDE.md) | Test must skip / planner must add to test extras |
| tree-sitter (Python) | corpus extraction | ✓ | per pyproject `[all]` | — |
| graspologic (Leiden) | clustering | optional | per `[leiden]` | Louvain fallback (`cluster.py`); deterministic seed for both |
| Network access | none | n/a | — | n/a (tests are pure tmp_path) |

**No missing dependencies.** All required deps are present in the CI install path graphify uses (`pip install -e ".[mcp,pdf,watch]"` per CLAUDE.md).

## Validation Architecture

> Phase 60 is itself the test infrastructure. Per `workflow.nyquist_validation: true` in `.planning/config.json`, this section sketches how the two added tests collectively validate E2E-01 and E2E-02.

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (CI matrix Python 3.10 + 3.12) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` (per CLAUDE.md "no linter/formatter, but pytest config in pyproject") |
| Quick run command | `pytest tests/test_e2e_integration.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| E2E-01 | profile composition (ntt + mrt) → `update-vault` produces ladder-applied classified notes | subprocess integration | `pytest tests/test_e2e_integration.py::test_e2e_compose_override_ladder -x` | ❌ Wave 0 |
| E2E-02 | `elicit` → sidecar at `artifacts_dir/elicitation.json` → `update-vault` → rendered notes contain elicitation contributions | subprocess integration | `pytest tests/test_e2e_integration.py::test_e2e_elicit_then_update_vault -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_e2e_integration.py -q` (~5–15s expected; full pipeline runs twice per test for preview→apply)
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_e2e_integration.py` — does not exist; covers E2E-01 and E2E-02
- [ ] No new `tests/conftest.py` entry needed (helper LOCKED to file-local per CONTEXT)
- [ ] No new fixture files (CONTEXT locks inline YAML)

### Coverage gaps not addressed by Phase 60 (orthogonal)
- Phase 55 block-expansion ordering is unit-tested (see `templates.py:172` invariant); E2E-01 covers it integratively but only along the `if_note_type_<X>` + `connections` axes. Other predicates (`if_god_node`, `if_isolated`, `if_has_connections`, `if_flag_<X>`) are NOT exercised by E2E-01 — and per CONTEXT this is out of scope.
- Apply-mode failure paths (`SKIP_CONFLICT`, `SKIP_PRESERVE`, `REPLACE`) are covered by `test_integration.py` re-run idempotence tests; Phase 60 does not need to re-cover.
- Multi-community elicitation merge (where elicit hub's community ID collides with corpus community ID) is not exercised — boundary case; flag as future v1.13+ if needed.

## Project Constraints (from CLAUDE.md)

- Python 3.10+ (CI tests on 3.10 + 3.12)
- No new required dependencies (PyYAML already present transitively)
- Backward compatible — Phase 60 adds tests only; no production behavior change
- Pure unit tests: tmp_path only, no network, no filesystem side effects outside tmp_path
- Security: paths confined per `security.py`; no template-injection risk (templates are test-controlled)
- Test naming: `test_<module>.py` — `test_e2e_integration.py` is consistent with existing conventions

## Sources

### Primary (HIGH confidence — verified in codebase this session)
- `graphify/__main__.py:2523-2611` — elicit subcommand handler
- `graphify/__main__.py:3080-3124` — update-vault subcommand handler
- `graphify/migration.py:166-289` — `run_update_vault` orchestration
- `graphify/elicit.py:103-145, 215-300` — elicit extraction shape, sidecar I/O, merge function
- `graphify/output.py:144, 275-402` — vault detection, profile-required preconditions, artifacts_dir derivation
- `graphify/profile.py:69-180, 770-870` — `_DEFAULT_PROFILE`, valid top-level keys, ntt+mrt validators
- `graphify/templates.py:172-203, 803-849, 1504-1520, 1645-1710, 1867-1886` — block expansion ordering, frontmatter builder, override ladder tiers
- `graphify/pipeline.py:11-50` — `run_corpus` (consumed by `update-vault`)
- `tests/test_main_flags.py:15-39` — `_graphify` helper (verbatim source for the new file)
- `tests/test_main_cli.py:29-35, 193-211` — `_run_cli`/`_run_cli_in` patterns (excluded by CONTEXT but documented)
- `tests/test_integration.py:1-225` — `_make_graph`/`_minimal_graph` (NOT applicable to update-vault path; surfaced anyway)
- `tests/test_profile_composition.py:380-615` — community_templates fixture pattern, `_render_moc_with_profile` helper
- `tests/test_profile.py:2154-2280` — well-formed mrt + ntt validator examples (used to derive minimal valid YAML)
- `tests/fixtures/profiles/community_templates/.graphify/profile.yaml` — concrete profile example

### Secondary (HIGH-MEDIUM — corroborating)
- `.planning/REQUIREMENTS.md` E2E-01/E2E-02 entries
- `.planning/ROADMAP.md` Phase 60 row (lines ~454-468)
- `.planning/milestones/v1.11-MILESTONE-AUDIT.md:30-31` — Flow 2/Flow 3 gap rationale
- `.planning/phases/60-milestone-level-e2e-integration-tests/60-CONTEXT.md` — locked decisions
- `.planning/config.json` — confirms `nyquist_validation: true`, `tdd_mode: true`

### Tertiary (LOW — none)
- No external doc lookups required; all answers came from in-repo source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package verified in `pyproject.toml` and `CLAUDE.md`.
- Architecture: HIGH — full call-graph from CLI dispatch through migration.py through templates.py walked.
- Pitfalls: HIGH — preview-vs-apply trap and ntt/mrt ordering are direct reads of `migration.py:218-289` and `templates.py:1645-1710`.
- Open questions: A1 (one-call vs two-call) is the single substantive ambiguity for the planner to resolve.

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days; codebase is stable, but Phase 61 may touch the harness path adjacent to elicit error formatting and Phase 56's ladder is locked).

## RESEARCH COMPLETE

**Phase:** 60 - Milestone-level E2E integration tests
**Confidence:** HIGH

### Key Findings
- **`update-vault` preview does NOT write notes to disk** — `dry_run=True` is hardcoded in `migration.py:218-225`. To produce assertable rendered notes, each test must invoke `update-vault` twice: once for preview (capture plan_id from `<artifacts_dir>/migrations/migration-plan-<id>.json`), once with `--apply --plan-id <id>`. This expands E2E-01 from one subprocess call to two, and E2E-02 from two to three. **This is the largest planner-relevant gap closed.**
- **Vault preconditions are strict and ordered:** `.obsidian/` directory MUST exist before profile load; `.graphify/profile.yaml` MUST contain an `output:` block with `mode` and `path`; failure at either point exits 1 with a specific stderr message the planner can encode.
- **Sidecar handoff for E2E-02 requires `--vault <vault>` on the elicit call** so its `artifacts_dir` resolves to `<vault>.parent/graphify-out/elicitation.json` — the same path `update-vault` reads from. Without `--vault`, elicit writes to `<cwd>/graphify-out/elicitation.json` and the merge silently no-ops.
- **Override ladder has 4 tiers, not 2:** `mapping_rule_templates` → `community_templates` → `note_type_templates` → base. The inline test profile must avoid accidentally matching the tier-2 (community_templates) tier OR explicitly omit it.
- **Block expansion vs `${}` ordering is provable** by combining a block (`{{#if_note_type_thing}}…{{/if}}` or `{{#connections}}…{{/connections}}`) with a `${}` placeholder + a sentinel string in the override template.
- **`min_community_size` default is 6** — too high for a synthetic 2-class corpus. Inline profile must override to `1` (or supply enough corpus to clear the default).

### File Created
`/Users/silveimar/Documents/silogia-repos/graphify/.planning/phases/60-milestone-level-e2e-integration-tests/60-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|---|---|---|
| Subprocess helper contract | HIGH | Verbatim source already exists at `tests/test_main_flags.py:15-39` |
| `update-vault` CLI surface | HIGH | Read both handler (`__main__.py:3080-3124`) and library (`migration.py:166-289`) |
| `elicit` CLI surface + sidecar shape | HIGH | Read handler + `elicit.py:215-300` |
| Profile composition shape | HIGH | Reused validator examples from `test_profile.py:2160-2280` |
| Frontmatter assertion targets | HIGH | Read `_build_frontmatter_fields` (`templates.py:803-849`) directly |
| Elicitation visibility | HIGH | Demo answers are locked literals at `__main__.py:2563-2570` |
| Override ladder tier order | HIGH | Read `_resolve_note_template` (`templates.py:1645-1710`) |
| One-call vs. two-call interpretation | MEDIUM (assumption A1) | CONTEXT is silent on E2E-01's call count; planner should confirm |

### Open Questions / Surprises for the Planner
1. **Surprise (high impact):** preview-mode `update-vault` does not materialize notes. The plan must include both preview AND apply subprocess calls per test, OR the discuss-phase must reopen whether `update-vault` is the right command (alternative: `run` + `--obsidian`, which writes notes directly but loses the elicit-merge integration of `update-vault`). Recommend: stick with `update-vault` + two-call pattern; document in plan's `<acceptance_criteria>`.
2. **Decision needed:** confirm `update-vault` is the right command for E2E-01 specifically (CONTEXT locks it, but the two-call implication may not have been considered when locking).
3. **Minor:** `GRAPHIFY_ELICIT_LLM` env var should be defensively unset in `_graphify`'s env to keep `maybe_deepen_session` deterministic — encode in a small env-hardening helper or document in plan preconditions.

### Ready for Planning
Research complete. Planner can now create PLAN.md files for E2E-01 and E2E-02 using:
- the exact `_graphify` source from `tests/test_main_flags.py:15-39`,
- the inline profile YAML and override-template patterns in §Code Examples,
- the two-call invocation contract for `update-vault`,
- the `--vault` flag passing rule for `elicit`,
- the frontmatter + body assertion targets enumerated in §Code Examples.
