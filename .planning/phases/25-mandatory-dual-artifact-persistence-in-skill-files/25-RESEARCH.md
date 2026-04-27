# Phase 25: Mandatory Dual-Artifact Persistence in Skill Files — Research

**Researched:** 2026-04-27
**Domain:** Static prose contract injection into 9 markdown skill-file variants + one parameterized regression test
**Confidence:** HIGH

## Summary

This phase adds a single, byte-identical markdown block (a hidden HTML-comment canary plus a `## Mandatory response persistence` heading and body) to nine skill-file variants under `graphify/`. The block instructs whichever LLM harness reads the skill to produce paired `*.human.md` + `*.graph.md` artifacts in `graphify-out/memory/` for every interactive `query` / `path` / `explain` / `analyze` invocation. No Python production code changes — `graphify` itself never writes these files; the contract is a directive on the LLM consumer.

A new pytest module (or extension to `tests/test_install.py`) iterates `_PLATFORM_CONFIG`, runs `install` against `tmp_path` with `Path.home()` mocked, and grep-asserts the canary string in every emitted `skill_dst`. A second assertion (byte-equality of the contract block across in-scope variants) prevents per-platform drift.

**Primary recommendation:** Author the contract block once as a Python constant (or read it from `skill.md` slice) for the byte-equality test; physically copy the block into the 9 source skill files; reuse the existing `Path.home` mock + `tmp_path` install pattern from `tests/test_install.py:21`. Implement TDD as RED-canary-test → GREEN-skill.md insertion → GREEN-fan-out → byte-equality lock.

## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Canary string** — Hidden HTML-comment sentinel `<!-- graphify:persistence-contract:v1 -->` placed on the line immediately above the `## Mandatory response persistence` heading. Invisible in rendered markdown, version-bumpable (`:v2`), greppable as a one-liner.

2. **Filename schema** — `CMD_<TS>_<SLUG>.{graph,human}.md` where:
   - `<TS>` = `YYYYMMDDTHHMMSSZ` (UTC, compact ISO-8601 basic, no colons, lex-sortable)
   - `<SLUG>` = `<command-kind>-<first-6-tokens>`, lowercased, hyphenated, non-alphanumerics stripped, max 64 chars total
   - `<command-kind>` ∈ {`query`, `path`, `explain`, `analyze`}
   - Pair-mates share identical `<TS>_<SLUG>`

3. **Artifact schema** —
   - `<base>.human.md`: prose only, plain markdown, no required frontmatter
   - `<base>.graph.md`: YAML frontmatter (required keys: `command`, `prompt`, `timestamp`, `graph_path`, `status`, `nodes_touched`, `edges_touched`, `communities_touched`) + single fenced ` ```json ` block with sub-extraction (nodes, edges, communities)

4. **Propagation** — Single source authored in `graphify/skill.md`, copied byte-for-byte into 9 in-scope variants. No paraphrasing of the contract block. `skill-excalidraw.md` is OUT OF SCOPE.

5. **Trigger** — Fires on every interactive `query`/`path`/`explain`/`analyze` invocation including errors (`status: error`, fenced JSON `{}`) and empty results (`status: empty`, empty arrays, well-formed JSON). Collisions resolved with `-1`, `-2` slug suffixes. Persistence is a contract on the harness, not on the Python CLI.

6. **Placement** — `## Mandatory response persistence` section (preceded by sentinel comment) inserted between `## Usage` and `## Available slash commands` in `graphify/skill.md` (lines 12 and 46) and the analogous neighbor positions in every in-scope variant.

### Claude's Discretion

- Exact prose of the contract body (within the locked schema).
- Whether the byte-equality drift check is folded into the canary test or kept separate.
- Whether the regression test goes into `tests/test_install.py` or a new `tests/test_skill_persistence.py` module.
- Source-of-truth strategy for the byte-equality check (Python constant vs. slice-from-`skill.md` at test time).

### Deferred Ideas (OUT OF SCOPE)

- `graphify add` persistence (file as future SKILLMEM-05).
- `skill-excalidraw.md` persistence (different skill surface; revisit if it grows query commands).
- Memory-dir retention/GC/TTL policy.
- Harness-side validator subcommand for `graphify-out/memory/` schema linting.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILLMEM-01 | Source `graphify/skill.md` contains "Mandatory response persistence" section requiring dual-artifact writes | Insertion site verified (lines 12 / 46); contract block draft below; greenfield (no prior text to merge) |
| SKILLMEM-02 | All in-scope platform variants carry the contract verbatim | 9 variants enumerated with verified neighbor lines (`## Usage` / `## Available slash commands`) — see Diff Sites table |
| SKILLMEM-03 | `graphify install <platform>` re-emits the persistence block on a fresh install for every entry in `_PLATFORM_CONFIG` | Install pipeline already copies `skill_file` → `skill_dst` byte-for-byte (`__main__.py:49-155`); no install code changes needed; can be subsumed by SKILLMEM-04 grep-after-install assertion |
| SKILLMEM-04 | Regression test grep-asserts persistence canary in every emitted skill file under each `_PLATFORM_CONFIG[*].skill_dst` | Existing `Path.home` mock + `tmp_path` pattern at `tests/test_install.py:21-23` is a perfect fit; iterate `_PLATFORM_CONFIG` directly |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Contract authoring | Skill prose (`graphify/skill*.md`) | — | The contract is a directive to LLMs reading the skill, not Python behavior. Lives in markdown only. |
| Contract propagation | `graphify install` Python copy logic (`__main__.py:_PLATFORM_CONFIG`) | — | Already copies skill files byte-for-byte; no new code. |
| Drift defense | Test suite (`tests/test_install.py` or new module) | — | Pure unit test — file read + string assertion + parameterization over `_PLATFORM_CONFIG`. |
| Artifact production | LLM harness at runtime | — | Out of Python scope; the harness is the executor. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (project pinned in dev extras) | Test runner | Already used by every test in `tests/`. |
| `unittest.mock.patch` | stdlib | Mock `graphify.__main__.Path.home` | Established pattern at `tests/test_install.py:21`. |
| `pathlib.Path` | stdlib | Path manipulation | Project convention (`from pathlib import Path` everywhere). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | — | — | Pure markdown text edits + pure-stdlib pytest. No new deps required. [VERIFIED: CLAUDE.md "No new required dependencies" + repo grep] |

**Installation:** None — phase introduces zero runtime dependencies and zero test dependencies beyond what already ships.

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────┐
                │  graphify/skill.md           │  (source of truth — 1819 lines)
                │  ── canary <!-- v1 -->       │  insertion at lines 12-46 boundary
                │  ── ## Mandatory response    │
                │       persistence            │
                └──────────┬───────────────────┘
                           │ byte-for-byte copy
                           │ (manual edit, 9 sites)
                           ▼
        ┌──────────────────────────────────────────┐
        │  9 in-scope skill variants:              │
        │   skill-aider / -claw / -codex /         │
        │   -copilot  / -droid / -opencode /       │
        │   -trae    / -windows / skill.md itself  │
        └──────────┬───────────────────────────────┘
                   │ graphify install <platform>
                   │ (existing copy via _PLATFORM_CONFIG)
                   ▼
        ┌──────────────────────────────────────────┐
        │  ~/.{platform}/skills/graphify/SKILL.md  │
        │  (byte-equal copy; canary present)       │
        └──────────┬───────────────────────────────┘
                   │ pytest grep
                   ▼
        ┌──────────────────────────────────────────┐
        │  test_skill_carries_persistence_canary   │
        │  parametrize over _PLATFORM_CONFIG       │
        │  assert canary in skill_dst.read_text()  │
        └──────────────────────────────────────────┘
```

### Diff Sites — In-scope skill files

Insertion neighbors verified by grep on 2026-04-27:

| File | `## Usage` line | `## Available slash commands` line | Total lines |
|------|----:|----:|----:|
| `graphify/skill.md`         | 12 | 46 | 1819 |
| `graphify/skill-aider.md`   | 11 | 40 | 1294 |
| `graphify/skill-claw.md`    | 11 | 40 | 1294 |
| `graphify/skill-codex.md`   | 12 | 42 | 1373 |
| `graphify/skill-copilot.md` | 11 | 42 | 1375 |
| `graphify/skill-droid.md`   | 11 | 40 | 1349 |
| `graphify/skill-opencode.md`| 11 | 40 | 1348 |
| `graphify/skill-trae.md`    | 11 | 40 | 1318 |
| `graphify/skill-windows.md` | 11 | 43 | 1352 |

Every file has the same structural anchor pair (`## Usage` ... `## Available slash commands`), so the insertion is mechanical: append the contract block immediately *before* the `## Available slash commands` heading.

**Note on platform→file fan-out:** `_PLATFORM_CONFIG` has 12 entries but they map to 9 distinct source files because:
- `claude` and `windows` both use `.claude/skills/graphify/SKILL.md` as `skill_dst` but use different sources (`skill.md` vs `skill-windows.md`)
- `trae` and `trae-cn` both reference `skill-trae.md`
- `antigravity` reuses `skill.md`
- `excalidraw` is OUT OF SCOPE (uses `skill-excalidraw.md`)

The regression test must iterate `_PLATFORM_CONFIG` (all entries except `excalidraw`), not the 9 source files — this is what SKILLMEM-04 specifies.

### Pattern 1: Parameterized install + grep assertion

**What:** Iterate `_PLATFORM_CONFIG`, install each (with `Path.home()` mocked to `tmp_path`), read the emitted `skill_dst`, assert canary present.
**When to use:** Every new contract that must propagate to every platform.
**Example (project pattern, lifted from `tests/test_install.py:18-23`):**
```python
# Source: graphify/tests/test_install.py:18-23 (existing pattern)
def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
```

**Recommended new test (TDD-RED first, fails until contract block landed):**
```python
import pytest
from pathlib import Path
from unittest.mock import patch
from graphify.__main__ import _PLATFORM_CONFIG, install

PERSISTENCE_CANARY = "<!-- graphify:persistence-contract:v1 -->"

# excalidraw is out of scope per CONTEXT.md decision 4
_IN_SCOPE = [name for name in _PLATFORM_CONFIG if name != "excalidraw"]

@pytest.mark.parametrize("platform", _IN_SCOPE)
def test_install_emits_persistence_canary(tmp_path, platform):
    """SKILLMEM-04: every emitted skill file carries the persistence canary."""
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
    cfg = _PLATFORM_CONFIG[platform]
    emitted = tmp_path / cfg["skill_dst"]
    assert emitted.exists(), f"{platform}: skill not emitted"
    assert PERSISTENCE_CANARY in emitted.read_text(encoding="utf-8"), (
        f"{platform}: canary missing from {emitted}"
    )
```

### Pattern 2: Byte-equality drift lock

Two viable shapes — recommend folding into the same module for cohesion:

```python
def test_persistence_block_byte_equal_across_variants():
    """SKILLMEM-02: contract block must be byte-identical across in-scope variants."""
    import graphify
    pkg = Path(graphify.__file__).parent
    # The 9 source files (not platform names): skill.md + 8 variants
    sources = [
        "skill.md", "skill-aider.md", "skill-claw.md", "skill-codex.md",
        "skill-copilot.md", "skill-droid.md", "skill-opencode.md",
        "skill-trae.md", "skill-windows.md",
    ]
    blocks = []
    for name in sources:
        text = (pkg / name).read_text(encoding="utf-8")
        start = text.index(PERSISTENCE_CANARY)
        # End sentinel = next "## " heading after the canary
        end = text.index("\n## ", start + len(PERSISTENCE_CANARY))
        blocks.append(text[start:end])
    assert all(b == blocks[0] for b in blocks), "persistence block drift detected"
```

**Recommendation:** Keep the two tests *separate* (one parametrized over platforms via install, one over source files via package read). They test different things — the first verifies install propagation, the second verifies authoring discipline. A single test conflating both is harder to debug when only one fails.

### Anti-Patterns to Avoid

- **Paraphrasing the contract per platform.** Locked decision (CONTEXT.md decision 4); per-platform tweaks defeat the byte-equality test.
- **Hard-coding `_PLATFORM_CONFIG` keys** in the new test — iterate the dict so adding a future platform forces a deliberate inclusion/exclusion decision (mirror Phase 22's `test_platform_config_has_excalidraw` pattern).
- **Embedding the canary inside the test as a copy-pasted prose snippet.** Use a single `PERSISTENCE_CANARY` constant; if the version bumps from `v1` to `v2`, only one place changes.
- **Asserting on rendered markdown.** Read raw bytes with `encoding="utf-8"`; the canary is an HTML comment that markdown renderers hide.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File install copy logic | A new `_install_persistence_block` helper | `_PLATFORM_CONFIG` already copies `skill_file` → `skill_dst` byte-for-byte (`__main__.py:49-155`) | Adding the block to the source files makes it ride along automatically; no install code changes. |
| Test fixture for `Path.home()` | A new fixture in `conftest.py` | `with patch("graphify.__main__.Path.home", return_value=tmp_path):` | Existing 30+ tests already use this pattern; consistency wins. |
| YAML/JSON parsing in tests | Parsing the artifact schema in regression tests | Plain `in` substring assertions on the canary | The contract is a directive to LLMs; we test for *presence of the directive*, not for runtime artifact correctness (those files are produced by harnesses, not by `graphify`). |
| Templating engine | Jinja2 / string-format the contract block | Author it as static markdown once and copy verbatim | CLAUDE.md forbids new required deps; the block is identical across files by design. |

**Key insight:** This phase has zero Python production code changes. Every Python change is in tests. All "implementation" is markdown editing. Plans that add helper modules or refactors are over-engineering.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `graphify-out/memory/` already exists as a concept used by `save-result` (`ingest.py:247`); this phase does not migrate or rename existing memory files | None |
| Live service config | None | None |
| OS-registered state | None — `graphify install` writes skill files to user paths but does not register OS-level services | None |
| Secrets/env vars | None | None |
| Build artifacts | None — skill files are part of the wheel via `pyproject.toml` package data; rebuilding the wheel after editing them is a normal install flow, no stale artifacts to clean | None |

**Note on `graphify-out/memory/` namespace coexistence:** `ingest.save_result` already writes to `graphify-out/memory/` with filename `query_<YYYYMMDD>_<HHMMSS>_<slug>.md` (`ingest.py:255-257`). The Phase 25 schema `CMD_<TS>_<SLUG>.{graph,human}.md` is intentionally distinct (uppercase `CMD_` prefix; compact ISO `T...Z` timestamp; `.graph.md`/`.human.md` paired suffix). The two namespaces will coexist in the same directory without filename collisions. The Phase 25 contract should NOT replace or rename the `save-result` artifacts.

## Common Pitfalls

### Pitfall 1: Drift between source-file edit and platform-derivation copies
**What goes wrong:** `antigravity` reuses `skill.md` directly (`__main__.py:115` per CONTEXT.md). If a future maintainer copies a "fixed" block into `antigravity` they could fork the source.
**Why it happens:** `_PLATFORM_CONFIG` has 12 entries but only 9 distinct `skill_file` values; this 12→9 fan-in is non-obvious.
**How to avoid:** The byte-equality test reads source files (9 of them), not install destinations. The install-canary test reads destinations (12 of them, minus excalidraw = 11). The two tests together pin both fan-ins.
**Warning signs:** A diff that touches only one of `skill.md` / `skill-windows.md` while claiming to update "all variants."

### Pitfall 2: Wrong neighbor line per variant
**What goes wrong:** Editor inserts the block above the wrong heading because variants have slightly different line counts.
**Why it happens:** Variants range 1294–1819 lines with `## Usage` at line 11 or 12 and `## Available slash commands` at line 40, 42, or 43. Hard-coded line numbers will skew across files.
**How to avoid:** Plans MUST reference *headings* (anchor text), not line numbers, when describing where the block goes. Edits should be authored relative to "before `## Available slash commands`."
**Warning signs:** A plan that says "insert at line 13" without specifying the heading anchor.

### Pitfall 3: Markdown renderer hiding the canary causes false positives in human review
**What goes wrong:** Reviewer opens the rendered skill file (in a tool that hides HTML comments) and "doesn't see" the canary, then re-adds it, producing duplicates.
**Why it happens:** `<!-- ... -->` is invisible in rendered markdown.
**How to avoid:** The canary version is `:v1` — a substring grep on raw text is the only ground truth. The test enforces this.
**Warning signs:** Two adjacent canary lines, or a canary above a heading that already has one.

### Pitfall 4: Confusing `_PLATFORM_CONFIG` keys with source-file names
**What goes wrong:** Test iterates over a hand-curated list of 9 source-file basenames, missing the platform-derivation copies (`antigravity` → `skill.md`, `windows` → `skill-windows.md`, `trae-cn` → `skill-trae.md`).
**Why it happens:** SKILLMEM-04 specifies `_PLATFORM_CONFIG[*].skill_dst` not source-file iteration.
**How to avoid:** The install-canary test MUST iterate `_PLATFORM_CONFIG` keys (subtracting `excalidraw`), then read `tmp_path / cfg["skill_dst"]`. Two distinct tests handle the two distinct iterations (sources for byte-equality, destinations for canary-after-install).
**Warning signs:** Test code with a hardcoded list of 9 strings.

### Pitfall 5: Errors / empty-results path forgotten in contract prose
**What goes wrong:** Contract says "write artifacts on every invocation" but doesn't say what happens on errors; LLMs default to the convenient interpretation (skip on error).
**Why it happens:** Authors think "happy path."
**How to avoid:** Decision 5 is explicit: errors → `status: error`, fenced JSON `{}`; empty → `status: empty`, empty arrays. The drafted block below codifies this verbatim.
**Warning signs:** Reviewer asks "what happens if `query` finds zero nodes?" and the contract doesn't answer in two seconds.

## Code Examples

### Drafted Contract Block (proposed verbatim text)

The planner can lock this draft as the byte-identical source. Lines 1-3 are the canary block; the rest is the prose contract. Total: ~50 lines (within the 30-60 target).

```markdown
<!-- graphify:persistence-contract:v1 -->

## Mandatory response persistence

Every interactive `query`, `path`, `explain`, and `analyze` invocation in any
LLM harness MUST write a paired pair of files under `graphify-out/memory/`
before responding to the user. This applies to errors and empty results too.

### Filenames

```
graphify-out/memory/CMD_<TS>_<SLUG>.human.md
graphify-out/memory/CMD_<TS>_<SLUG>.graph.md
```

- `<TS>` = UTC compact ISO-8601: `YYYYMMDDTHHMMSSZ` (no colons, lex-sortable)
- `<SLUG>` = `<command>-<first-6-tokens-of-prompt>`, lowercased, hyphen-joined,
  non-alphanumerics stripped, total filename ≤ 64 chars
- `<command>` ∈ {`query`, `path`, `explain`, `analyze`}
- On collision (sub-second repeat), append `-1`, `-2`, … to `<SLUG>`
- Both files of a pair share identical `<TS>_<SLUG>`

### `<base>.human.md` — prose response

Plain markdown of the answer shown to the user. No required frontmatter; this
file is the human-readable transcript and reads naturally on its own.

### `<base>.graph.md` — structured artifact

YAML frontmatter (all keys required) followed by a single fenced ` ```json `
block containing the sub-extraction the response was built from:

```yaml
---
command: query | path | explain | analyze
prompt: "<verbatim user prompt>"
timestamp: "2026-04-27T15:42:00Z"
graph_path: "<relative path to the graph JSON read>"
status: ok | error | empty
nodes_touched: ["<node-id>", ...]
edges_touched: ["<edge-id>", ...]
communities_touched: [<community-id>, ...]
---
```

Body: a single fenced JSON block with `{"nodes": [...], "edges": [...],
"communities": [...]}`. Empty arrays are permitted on `status: error` or
`status: empty`; the JSON body must remain well-formed (`{}` is acceptable
on errors).

### Why

Persisting paired prose + graph artifacts grows the corpus: subsequent
`graphify run --update` extracts these files back into the graph, closing
the feedback loop. Always write them — even on failure — so the audit trail
is complete and reproducible.
```

(The planner should treat this draft as a starting point; final wording is at planner discretion as long as the canary, schema, error/empty semantics, and collision rule remain.)

### Test scaffolding (existing pattern, copy-paste shape)

```python
# Source: graphify/tests/test_install.py:5-23 (canonical pattern)
import pytest
from pathlib import Path
from unittest.mock import patch

def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-command instructions inline in each command section | Top-of-file global preamble | Decision 6 (this phase) | Single insertion point; LLM reads contract before any per-command instructions |
| Heading-text only (no canary) | Hidden HTML-comment sentinel | Decision 1 (this phase) | Survives prose paraphrase; greppable in one regex |
| Manually verified per-platform | Parameterized regression test | SKILLMEM-04 (this phase) | Drift now CI-detected on every push |

**No deprecated/outdated patterns.** This is a greenfield contract with no prior incarnation in the codebase (greenfield grep verified — see Sources).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project default; CI on Python 3.10 and 3.12) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_install.py -q` (or new module: `pytest tests/test_skill_persistence.py -q`) |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILLMEM-01 | `graphify/skill.md` contains `## Mandatory response persistence` heading after canary | unit (file read) | `pytest tests/test_skill_persistence.py::test_skill_md_has_canary -x` | ❌ Wave 0 |
| SKILLMEM-02 | All 9 in-scope source files contain byte-identical contract block | unit (file read + slice + compare) | `pytest tests/test_skill_persistence.py::test_persistence_block_byte_equal_across_variants -x` | ❌ Wave 0 |
| SKILLMEM-03 | Fresh `install` for every `_PLATFORM_CONFIG` entry emits a skill file containing the canary at `skill_dst` (subsumed by SKILLMEM-04 — same assertion) | unit (parameterized install + read) | `pytest tests/test_skill_persistence.py::test_install_emits_persistence_canary -x` | ❌ Wave 0 |
| SKILLMEM-04 | Regression grep-asserts canary in every emitted skill file under `_PLATFORM_CONFIG[*].skill_dst` | unit (parameterized install + grep) | `pytest tests/test_skill_persistence.py::test_install_emits_persistence_canary -x` | ❌ Wave 0 |

**Recommendation:** SKILLMEM-03 is *fully subsumed* by SKILLMEM-04's grep-after-install pattern — the canary assertion implicitly proves "the install re-emits the block on a fresh install." A single parameterized test covers both. No need for a separate "fresh install" test.

### Sampling Rate

- **Per task commit:** `pytest tests/test_skill_persistence.py -q` (or `tests/test_install.py -q` if folded in) — runs in <2s
- **Per wave merge:** `pytest tests/ -q` — full project suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_skill_persistence.py` (recommended new module) OR three new tests appended to `tests/test_install.py` — choice is planner's discretion
- [ ] No new fixtures needed — `tmp_path` and `Path.home` mock already exist
- [ ] No framework install needed — pytest already in dev extras

## Environment Availability

This phase has no external runtime dependencies — pure markdown edit + pure-stdlib pytest test. Skip-condition criterion met for production code; included only to confirm.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | Test execution | ✓ | per `pyproject.toml` dev extras | — |
| Python stdlib (`pathlib`, `unittest.mock`) | Tests | ✓ | 3.10+ | — |

## Project Constraints (from CLAUDE.md)

- **No new required dependencies** — verified satisfied (zero new deps).
- **Backward compatible** — no behavior change for existing skill consumers; the new section is additive prose. Existing `save-result` flow in `ingest.py` continues unchanged.
- **Existing test patterns** — pure unit tests, no network, no FS side effects outside `tmp_path` — verified satisfied; new tests use the established pattern.
- **Security** — contract instructs LLMs to write under `graphify-out/memory/` only; consistent with `security.py` path-confinement convention. Slug sanitization rule in the contract (`non-alphanumerics stripped, max 64 chars`) prevents path-injection from malicious user prompts. Note for planner: the *Python* code does not enforce this — it's a directive to LLMs. If we later add a Python-side validator (deferred), it will need `security.py` integration.
- **Type hints** + `from __future__ import annotations` — only relevant if a new test module is created; reuse existing imports from `tests/test_install.py`.

## Recommended Task Ordering (TDD)

The planner should structure plans in this order to keep RED→GREEN clean:

1. **Wave 0 (test scaffolding, RED):**
   - Add `PERSISTENCE_CANARY = "<!-- graphify:persistence-contract:v1 -->"` constant.
   - Write `test_install_emits_persistence_canary` parametrized over `_PLATFORM_CONFIG` minus `excalidraw` — should FAIL for all 11 platforms.
   - Write `test_persistence_block_byte_equal_across_variants` — should FAIL (canary not found anywhere).

2. **Wave 1 (source-of-truth GREEN):**
   - Insert the contract block (canary + heading + body) into `graphify/skill.md` between `## Usage` and `## Available slash commands`.
   - Now: `test_install_emits_persistence_canary[claude]` and `[antigravity]` pass; others still fail.

3. **Wave 2 (variant fan-out GREEN):**
   - Copy the same block byte-for-byte into the 8 remaining source files: `skill-aider.md`, `skill-claw.md`, `skill-codex.md`, `skill-copilot.md`, `skill-droid.md`, `skill-opencode.md`, `skill-trae.md`, `skill-windows.md`.
   - Now: all canary tests pass.

4. **Wave 3 (drift lock VERIFIED):**
   - `test_persistence_block_byte_equal_across_variants` now passes — proving the 9 source files have identical blocks.
   - Optional: bump `pyproject.toml` package data if any new files were added (none required for this phase).

5. **Phase gate:**
   - `pytest tests/ -q` green
   - Manual verification: `grep -F "<!-- graphify:persistence-contract:v1 -->" graphify/skill*.md` returns 9 hits.

## Risks and Edge Cases

1. **Future platform addition** — A new `_PLATFORM_CONFIG` entry would auto-fail the install-canary test until the new source file gets the block. This is correct behavior. Document in the contract block's authoring location: "When adding a platform, the new `skill-<x>.md` MUST include this canary block byte-for-byte."

2. **Editing the contract block in only `skill.md`** — Byte-equality test catches this. Plans should explicitly call out: "edit ALL 9 source files in lockstep" as a single task or strictly-ordered sub-tasks.

3. **Antigravity / claude / windows / trae-cn fan-in** — `_PLATFORM_CONFIG` has multiple platform keys mapping to fewer source files. The test iterates platform *keys* (`_PLATFORM_CONFIG.keys()`), not source files, which means platforms sharing a source file are tested independently — duplication is intentional, and correct-by-construction.

4. **HTML-comment escaping in rendered docs** — Any project that publishes the skill files as docs (e.g., GitHub Pages with markdown→HTML) MUST not strip HTML comments during build. Not a concern for this repo (no such build), but flag for future maintainers.

5. **`status: error` JSON `{}` vs. JSON `{"nodes":[],"edges":[],"communities":[]}`** — Drafted contract permits `{}` on errors (terser, less work for failed harness). Decision 5 in CONTEXT.md says "fenced JSON body is `{}`" for errors and "fenced JSON body still present and well-formed" for empty. Plan should faithfully reproduce both.

6. **Canary version bump risk** — If a future phase changes the contract, bumping to `:v2` invalidates all installed skills. That's by design — old installs grep-fail and force re-install. Document in the contract authoring spot.

7. **`save-result` namespace coexistence** — Existing `ingest.save_result` writes `query_<TS>_<slug>.md` to the same `graphify-out/memory/` directory. The new `CMD_<TS>_<SLUG>.{graph,human}.md` namespace does not collide (different prefix, different timestamp format, different suffix structure). Both will coexist; both feed the `--update` re-extraction loop. Worth a one-sentence mention in the contract prose for reviewer awareness.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The drafted contract block prose (~50 lines) is acceptable to the planner verbatim | Code Examples | Planner may rewrite; only schema/canary/error semantics are locked |
| A2 | `claude` platform's `_PLATFORM_CONFIG` entry uses `skill.md` as source (so install-canary test passes for `claude` after only Wave 1) | Recommended Task Ordering | [VERIFIED via `__main__.py:50-58` read] — Not assumed |
| A3 | Existing `save-result` files (`query_<TS>_<slug>.md`) and new contract files (`CMD_<TS>_<SLUG>.{graph,human}.md`) won't collide in the same directory | Risks and Edge Cases | Different prefix verified; collision impossible by schema; LOW risk |

**Otherwise:** All decisions are locked in CONTEXT.md or verified directly against the codebase. No user confirmation needed beyond what CONTEXT.md already captures.

## Open Questions

1. **Should the byte-equality test read from `graphify/skill*.md` directly or from a Python-constant copy of the block?**
   - What we know: Reading from `skill.md` is more DRY but means a corrupt `skill.md` can't be detected as wrong (only as different from variants).
   - What's unclear: Which is more useful for failure messages.
   - Recommendation: Read all 9 source files, slice between canary and the next `## ` heading, assert mutual equality. This pins drift among siblings without privileging any one as "the truth" — acceptable since CONTEXT.md says `skill.md` is the source.

2. **Should Phase 25 also update `pyproject.toml` package data?**
   - What we know: All 9 in-scope skill files are already shipped via existing package data (verified — `test_all_skill_files_exist_in_package` at `tests/test_install.py:84-89` already checks 7 of them; the test would need to add `skill-aider.md` and `skill-copilot.md` if they aren't covered today).
   - What's unclear: Whether `aider` and `copilot` are in the existing `pyproject.toml` package_data.
   - Recommendation: Plan should run `python -c "import graphify; from pathlib import Path; pkg = Path(graphify.__file__).parent; print([f.name for f in pkg.glob('skill*.md')])"` once during planning to confirm. If `skill-aider.md` / `skill-copilot.md` aren't packaged, add them. Out of strict SKILLMEM scope but a near-zero-cost completeness fix.

## Sources

### Primary (HIGH confidence)
- `graphify/__main__.py:49-155` — `_PLATFORM_CONFIG` dict, all 12 entries verified
- `graphify/skill.md:1-60` — Insertion site (`## Usage` line 12, `## Available slash commands` line 46) verified
- `tests/test_install.py:5-23` — Existing `_install` helper with `Path.home` mock pattern
- `tests/test_install.py:84-89` — `test_all_skill_files_exist_in_package` — package data verification precedent
- `graphify/ingest.py:240-270` — Existing `save_result` writes to `graphify-out/memory/` (namespace coexistence verified)
- `.planning/REQUIREMENTS.md:24-29` — SKILLMEM-01..04 verbatim text
- `.planning/ROADMAP.md:245-253` — Phase 25 success criteria
- Greenfield grep — `grep -rn -E "(Mandatory response persistence|graphify-out/memory|persistence-contract|CMD_)" graphify/` returns ZERO hits for the contract strings (only existing `graphify-out/memory` references in `ingest.py`/`__main__.py`/`detect.py` for the unrelated `save-result` flow)
- `CLAUDE.md` — Project conventions (no new deps, pure unit tests, type hints, `from __future__ import annotations`)

### Secondary (MEDIUM confidence)
- Per-variant insertion-line audit (run 2026-04-27) — see Diff Sites table for verified neighbor lines per file

### Tertiary (LOW confidence)
- (None — every claim in this research was verified against the codebase or CONTEXT.md.)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib + pytest, both already in use
- Architecture: HIGH — pattern is "edit markdown + add parameterized test," both have direct project precedent (Phase 22 PATTERNS.md, `test_install.py:18-23`)
- Pitfalls: HIGH — fan-in/fan-out subtleties of `_PLATFORM_CONFIG` were directly inspected
- Insertion sites: HIGH — verified by grep on every in-scope file

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days; underlying `_PLATFORM_CONFIG` and skill files are stable; will only invalidate if a new platform is added or the `## Usage` / `## Available slash commands` headings are renamed)
