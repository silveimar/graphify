# Phase 27: Vault Detection & Profile-Driven Output Routing - Research

**Researched:** 2026-04-27
**Domain:** CLI configuration plumbing — vault detection, profile schema extension, output destination resolution, CLI flag layering
**Confidence:** HIGH (entire surface is in-tree; no external libraries to discover)

## Summary

Phase 27 is a thin, well-bounded plumbing change with three integration surfaces all already present in the codebase: (1) `graphify/profile.py` for the new `output:` schema, (2) `graphify/__main__.py` for vault-CWD detection + the new `--output` flag, (3) a new `ResolvedOutput` data carrier consumed by Phase 28 (`detect.py`) and Phase 29 (`doctor`). All decisions are locked in CONTEXT.md (D-01 through D-13) — research only resolves *where* the code lives and *which existing patterns* it copies.

There is no library research to do. PyYAML is already an optional dep used by `load_profile`; the YAML schema for `output:` parses with `yaml.safe_load` into the same dict pipeline that handles every other top-level block. Validation extends `validate_profile()`'s accumulator pattern. The `--output` flag follows the manual-loop parser style used at `__main__.py:1304` (`--obsidian-dir`) and `__main__.py:1503` (`--out-dir`). Vault detection is a one-liner (`Path('.obsidian').is_dir()`) per D-04.

The single design judgment call is **where to place `ResolvedOutput` and the resolver function** (`profile.py` vs `detect.py` vs new `output.py`). Recommendation below: **new `graphify/output.py`** — clean dependency layering, no circular import risk, and Phase 28/29 import it without dragging profile or detect logic.

**Primary recommendation:** Add (1) a `output:` block to `_DEFAULT_PROFILE` and `_VALID_TOP_LEVEL_KEYS`; (2) a `validate_output_block()` helper called from `validate_profile()`; (3) a new `graphify/output.py` module exporting `ResolvedOutput` (NamedTuple, mirroring `PreflightResult` in `profile.py:13`), `is_obsidian_vault(path)` and `resolve_output(cwd, profile, cli_output)`; (4) wire one call to `resolve_output()` at the top of the `run` command (`__main__.py:2094`) and another inside `--obsidian` (`__main__.py:1291`); (5) emit the precedence message exactly once per invocation from inside `resolve_output()` itself.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vault detection (`.obsidian/` at CWD) | New `graphify/output.py` | — | One predicate; cleaner than parking it in `detect.py` (read-only this phase) or `profile.py` (which is YAML-focused) |
| `output:` schema validation | `graphify/profile.py` | — | Schema validation already lives there; consistent with `diagram_types`, `tag_taxonomy`, `mapping`, etc. |
| Sibling-of-vault path validator | `graphify/profile.py` | `graphify/security.py` (spirit only) | Sits next to `validate_vault_path()` (profile.py:423). Intentionally relaxes confinement per D-03; do not import from `security.py` |
| `ResolvedOutput` resolution + precedence message | New `graphify/output.py` | — | Single consumer-facing data carrier; imported by `__main__.py`, future `detect.py` (Phase 28), future `doctor.py` (Phase 29) |
| CLI flag parsing (`--output`) | `graphify/__main__.py` | — | Follows existing manual-loop pattern (no argparse for `run`/`--obsidian`) |
| Auto-adopt wiring (default cmd + `--obsidian`) | `graphify/__main__.py` | — | Both branches call `resolve_output()` once and forward `notes_dir` / `artifacts_dir` |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** New top-level `output:` block in profile.yaml: `{ mode: vault-relative | absolute | sibling-of-vault, path: <string> }`. Add to `_VALID_TOP_LEVEL_KEYS` in `graphify/profile.py`.
- **D-02:** No source-path mirroring fallback. Vault detected + `output:` missing → refuse loudly.
- **D-03:** `mode: sibling-of-vault` resolves to `<vault>/../<path>`. New validator authorizes stepping outside vault while still rejecting empty path / filesystem root / above-vault-parent.
- **D-04:** Strict CWD-only detection: `Path('.obsidian').is_dir()`. No parent-walking.
- **D-05:** `.obsidian/` present + `.graphify/profile.yaml` missing → refuse with actionable message.
- **D-06:** Auto-adopt wired into both default `graphify <args>` AND `--obsidian` export.
- **D-07:** Auto-adopt fires → input corpus root forced to CWD.
- **D-08:** New unified `--output <path>` flag. Existing `--out-dir` and `--obsidian-dir` retained for backcompat. `--output` takes precedence over both legacy flags AND profile.
- **D-09:** When CLI `--output` overrides profile `output:`, ALWAYS print one stderr line: `[graphify] --output=<flag-path> overrides profile output (mode=<m>, path=<resolved-p>)`.
- **D-10:** `--output <path>` is a literal CWD-relative or absolute path; no mode inference.
- **D-11:** Auto-adopt → profile `output:` controls ONLY rendered Obsidian markdown notes. Build artifacts (graph.json, extraction.json, cache/, GRAPH_REPORT.md, manifests) auto-route to `<vault>/../graphify-out/`.
- **D-12:** No vault detected (and no `--output`) → preserve v1.0 paths exactly: `graphify-out/` + `graphify-out/obsidian/`.
- **D-13:** Phase ships single `ResolvedOutput` data structure: `{vault_detected: bool, vault_path: Path | None, notes_dir: Path, artifacts_dir: Path, source: Literal["profile", "cli-flag", "default"]}`.

### Claude's Discretion

- Exact Python type / location of `ResolvedOutput` (function in `profile.py` vs new tiny module).
- Exact wording of error messages for D-05 and the sibling-of-vault validator (D-03), beyond suggested shapes.
- Whether vault-detection report (VAULT-08) is a single line or a small block — keep terse.

### Deferred Ideas (OUT OF SCOPE)

- Auto-write a minimal default profile when vault detected but no profile present (rejected for D-05).
- Walking-up parent detection for `.obsidian/` (rejected for D-04).
- `--quiet` flag to suppress precedence stderr line (rejected for D-09).
- Two separate profile fields (`output.notes` and `output.artifacts`) (rejected for D-11).
- Multi-line precedence-resolution trace block (rejected for D-09).
- `graphify init-profile` scaffolding command (Phase 29 stretch / v1.8 candidate).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-08 | graphify detects when CWD is itself an Obsidian vault (presence of `.obsidian/` at CWD) | `is_obsidian_vault(path)` predicate in new `graphify/output.py`; called once at top of `run` and `--obsidian` branches in `__main__.py`. Detection report is the terse stderr line in §"Detection Report" below. |
| VAULT-09 | When CWD is a vault with `.graphify/profile.yaml`, graphify auto-adopts profile-driven placement (Option C) | `resolve_output()` in `graphify/output.py` orchestrates: detect → load profile → validate `output:` block → return `ResolvedOutput`. Forces input corpus = CWD per D-07. |
| VAULT-10 | `.graphify/profile.yaml` declares output destination (vault-rel / absolute / sibling-of-vault); CLI `--output` overrides | Schema extension in `profile.py` (D-01); resolver in `output.py` covers three modes; CLI `--output` flag in `__main__.py` takes precedence per D-08, emits stderr line per D-09. |

## Standard Stack

This is an in-tree refactor. **No new dependencies.**

### Core (already in tree)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` (stdlib) | n/a | Path resolution and existence checks | Used throughout codebase; matches `validate_vault_path` style [VERIFIED: graphify/profile.py:423] |
| `pyyaml` (optional, `obsidian` extra) | already declared | Parse `.graphify/profile.yaml` | Already used by `load_profile()`; ImportError guard already in place [VERIFIED: graphify/profile.py:178] |
| `typing.NamedTuple` (stdlib) | n/a | `ResolvedOutput` data carrier | Same pattern as `PreflightResult` in `profile.py:13` [VERIFIED: graphify/profile.py:13] |

### Supporting

None required. CLAUDE.md constraint "**No new required dependencies**" satisfied trivially.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain `NamedTuple` for `ResolvedOutput` | `dataclass(frozen=True, slots=True)` | NamedTuple wins: matches existing `PreflightResult` pattern in same package, supports tuple unpacking which downstream `doctor` may want. Dataclass would force tooling churn for zero benefit. |
| New `graphify/output.py` | Add to `profile.py` or `detect.py` | Recommendation: new module. Rationale below in §"ResolvedOutput Module Placement". |
| `argparse` for `--output` | Manual flag-loop | Manual loop matches existing `--obsidian` and `--dedup` parsers. CONVENTIONS demand consistency with established patterns; `__main__.py` already uses argparse only for `enrich`/`watch`/`vault-promote`. The `run` command is a flag-free positional, so adding argparse there would be a larger refactor. Stay manual. |

**Installation:** N/A (no new packages).

**Version verification:** N/A — no third-party dependencies introduced.

## Architecture Patterns

### System Architecture Diagram

```
                       graphify <args>            graphify --obsidian
                              │                          │
                              ▼                          ▼
                ┌──────────────────────────────────────────────────┐
                │         resolve_output(cwd, cli_output)           │
                │              [graphify/output.py]                 │
                └─────────┬──────────────────────────────────┬─────┘
                          │                                  │
              ┌───────────▼──────────┐         ┌─────────────▼────────────┐
              │  is_obsidian_vault?  │         │  --output flag present?  │
              │   .obsidian/.is_dir  │         └─────────────┬────────────┘
              └───────────┬──────────┘                       │ yes
                no │      │ yes                              ▼
                   │      ▼                       ┌──────────────────────┐
                   │  load_profile(cwd)           │ ResolvedOutput(      │
                   │      │                       │   source=cli-flag,   │
                   │      ▼                       │   vault_detected=…)  │
                   │  validate_profile             │ + emit precedence   │
                   │  output: present?             │   stderr line       │
                   │   no │       │ yes            └──────────────────────┘
                   │      │       │
                   │      ▼       ▼
                   │  REFUSE   resolve_mode()
                   │  D-05     │  vault-relative → <vault>/<path>
                   │           │  absolute → Path(path)
                   │           │  sibling-of-vault → <vault>/../<path>
                   │           ▼
                   │      validate_sibling_or_vault_path()
                   │           │
                   │           ▼
                   │      ResolvedOutput(source=profile)
                   │
                   ▼
          ResolvedOutput(
            source=default,
            notes_dir=graphify-out/obsidian,
            artifacts_dir=graphify-out)            ← D-12 backcompat
                          │
                          ▼
       ┌──────────────────────────────────────────────┐
       │  run_corpus / to_obsidian consume            │
       │  resolved.notes_dir + resolved.artifacts_dir │
       └──────────────────────────────────────────────┘
                          │
                          ▼
                Phase 28 (detect.py): prune
                Phase 29 (doctor.py): report
```

### Recommended Project Structure

```
graphify/
├── output.py           # NEW: is_obsidian_vault, ResolvedOutput, resolve_output
├── profile.py          # EXTENDED: _DEFAULT_PROFILE['output'], _VALID_TOP_LEVEL_KEYS,
│                       #           validate_profile() (output: branch),
│                       #           validate_sibling_path() helper
├── __main__.py         # EXTENDED: --output flag in `run` and `--obsidian` branches;
│                       #           one call to resolve_output() per branch
├── detect.py           # UNCHANGED this phase (Phase 28 will modify)
└── ...

tests/
├── test_output.py      # NEW: is_obsidian_vault, resolve_output, precedence stderr
├── test_profile.py     # EXTENDED: schema tests for output: block
└── ...
```

### Pattern 1: NamedTuple data carrier

**What:** Use `typing.NamedTuple` for `ResolvedOutput`, mirroring `PreflightResult`.
**When to use:** Multi-field result struct passed across module boundaries; immutable; supports `result.field` and tuple unpacking.
**Example:**
```python
# Source: graphify/profile.py:13 (existing PreflightResult pattern)
from typing import Literal, NamedTuple
from pathlib import Path

class ResolvedOutput(NamedTuple):
    """Single source of truth for vault detection + output destination.

    Consumed by:
      - graphify/__main__.py — `run` and `--obsidian` branches
      - graphify/detect.py (Phase 28) — pruning input scan
      - graphify/doctor.py (Phase 29) — diagnostic report
    """
    vault_detected: bool
    vault_path: Path | None        # None when vault_detected is False
    notes_dir: Path                # rendered Obsidian markdown
    artifacts_dir: Path            # graph.json, cache/, GRAPH_REPORT.md, manifests
    source: Literal["profile", "cli-flag", "default"]
```

### Pattern 2: Validate-first, fail-loudly with `errors: list[str]`

**What:** New `output:` validation extends `validate_profile()` accumulator.
**When to use:** Every profile schema check follows this pattern (see `profile.py:203-416`).
**Example:**
```python
# Source: graphify/profile.py:269 (folder_mapping branch — closest analog)
output = profile.get("output")
if output is not None:
    if not isinstance(output, dict):
        errors.append("'output' must be a mapping (dict)")
    else:
        mode = output.get("mode")
        if mode not in _VALID_OUTPUT_MODES:
            errors.append(
                f"output.mode must be one of {sorted(_VALID_OUTPUT_MODES)} "
                f"(got {mode!r})"
            )
        path_val = output.get("path")
        if not isinstance(path_val, str) or not path_val.strip():
            errors.append("output.path must be a non-empty string")
        elif mode == "vault-relative":
            if Path(path_val).is_absolute() or path_val.startswith("~"):
                errors.append("output.path must be vault-relative (not absolute, no ~)")
            elif ".." in path_val:
                errors.append("output.path contains '..' — not allowed in vault-relative mode")
        elif mode == "absolute":
            if not Path(path_val).is_absolute():
                errors.append("output.path must be an absolute filesystem path when mode=absolute")
        # sibling-of-vault validation deferred to use-time validate_sibling_path()
        # (we don't know vault_dir at schema-validation time)
```

### Pattern 3: Manual-loop CLI flag parser

**What:** Add `--output` and `--output=<path>` to existing `while i < len(args):` loops at `__main__.py:1304` (`--obsidian`) and a parallel one in the `run` branch (line 2094).
**When to use:** Any new flag for `run` / `--obsidian` / `--dedup` (consistent with how those branches already parse).
**Example:**
```python
# Source: graphify/__main__.py:1304 (--obsidian-dir parsing — direct analog)
elif args[i] == "--output" and i + 1 < len(args):
    cli_output = args[i + 1]; i += 2
elif args[i].startswith("--output="):
    cli_output = args[i].split("=", 1)[1]; i += 1
```

The `run` branch (line 2094) currently has no flag-loop — it accepts a single positional path + `--router`. Adding `--output` requires extending that snippet:

```python
# Replace lines ~2094-2105 in __main__.py
elif cmd == "run":
    rest = list(sys.argv[2:])
    use_router = "--router" in rest
    rest = [a for a in rest if a != "--router"]
    cli_output: str | None = None
    # parse --output / --output=<path>
    filtered = []
    i = 0
    while i < len(rest):
        if rest[i] == "--output" and i + 1 < len(rest):
            cli_output = rest[i + 1]; i += 2
        elif rest[i].startswith("--output="):
            cli_output = rest[i].split("=", 1)[1]; i += 1
        else:
            filtered.append(rest[i]); i += 1
    rest = filtered
    raw_target = rest[0] if rest else "."

    from graphify.output import resolve_output
    resolved = resolve_output(Path.cwd(), cli_output=cli_output)
    # auto-adopt → input corpus is CWD (D-07)
    if resolved.vault_detected and resolved.source == "profile":
        target = Path.cwd().resolve()
    else:
        target = Path(raw_target).resolve()
    # ... rest of existing code, but use resolved.artifacts_dir instead of `target / "graphify-out"`
```

### Anti-Patterns to Avoid

- **Importing `output.py` from `profile.py` or `detect.py`** — keep dependency arrow `output.py → profile.py` (output imports profile, never reverse). Avoids circular imports and matches the function-local-import discipline already used in `profile.py:350` and `profile.py:642`.
- **Resolving `--output` and emitting precedence message in two places** — emit it exactly once, inside `resolve_output()`. Both `run` and `--obsidian` branches share this codepath.
- **Re-litigating "should auto-adopt mirror source paths"** — D-02 locked this; the carry-forward note explicitly forbids the fallback. Don't add it back as a "convenience" default.
- **Using `os.getcwd()`** — use `Path.cwd()` (CONVENTIONS prefer pathlib).
- **Mutating `_DEFAULT_PROFILE['output']`** to a non-empty default — leaving it absent (not in `_DEFAULT_PROFILE` at all, or set to `None`) is what makes D-05's "refuse loudly" trigger fire. If we shipped a default `output:` block, the auto-adopt path would silently use it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Profile YAML loading | A custom YAML parser | `load_profile()` (existing) | Already handles ImportError, empty-file, validation roll-up |
| Vault-relative path safety | A new traversal blocker | `validate_vault_path()` (existing) for `mode: vault-relative` only | Reuse for the in-vault mode; sibling-of-vault gets its own validator (D-03) |
| Schema accumulator | Try/except validation | `validate_profile()` extension with `errors: list[str]` | Matches every other schema branch in `profile.py:203-416` |
| Frontmatter sanitization | Custom escaping | `safe_frontmatter_value()` (existing) | Not needed this phase — but Phase 28+ will need it; flagged for awareness |

**Key insight:** This phase is *purely* a schema + flag-wiring change. Every primitive it needs already exists in the codebase. The biggest risk is **adding** code where reuse would suffice.

## Sibling-of-Vault Validator (D-03 concrete sketch)

`validate_vault_path()` rejects anything that escapes vault. `mode: sibling-of-vault` deliberately escapes — but only by exactly one parent level, into a relative path under `<vault>/../`. New helper lives in `profile.py` next to `validate_vault_path`:

```python
def validate_sibling_path(candidate: str, vault_dir: str | Path) -> Path:
    """Resolve <vault>/../<candidate> with sane bounds.

    Authorizes the deliberate one-parent escape for output mode=sibling-of-vault
    while rejecting:
      - empty / whitespace-only candidate
      - candidate that escapes vault parent (no '../..' or absolute paths)
      - resolved path == filesystem root or above vault parent
      - candidate starting with '~' (home expansion)
      - candidate containing '..' (only the implicit parent-of-vault is allowed,
        and that's expressed by the mode itself, not in the candidate string)
    """
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("output.path must be a non-empty string for mode=sibling-of-vault")
    if candidate.startswith("~"):
        raise ValueError("output.path must not start with '~' (home expansion blocked)")
    if Path(candidate).is_absolute():
        raise ValueError(
            "output.path must be relative for mode=sibling-of-vault "
            "(use mode=absolute for absolute paths)"
        )
    if ".." in Path(candidate).parts:
        raise ValueError("output.path must not contain '..' segments for mode=sibling-of-vault")

    vault_base = Path(vault_dir).resolve()
    parent = vault_base.parent
    # Reject filesystem root / above-vault-parent corner cases (containerized envs)
    if parent == vault_base:
        raise ValueError(
            f"vault {vault_base} has no parent directory — "
            "mode=sibling-of-vault is not usable here; switch to mode=absolute"
        )
    resolved = (parent / candidate).resolve()
    # Sanity: resolved must stay under the vault's parent (strict ancestor)
    try:
        resolved.relative_to(parent)
    except ValueError:
        raise ValueError(
            f"output.path {candidate!r} escapes vault parent {parent}"
        )
    return resolved
```

Confidence: **HIGH** — directly mirrors the existing `validate_vault_path` (`profile.py:423`).

## ResolvedOutput Module Placement (D-13 trade-off)

**Recommendation: new `graphify/output.py`.**

| Option | Pro | Con |
|--------|-----|-----|
| `graphify/profile.py` | All profile semantics in one place | profile.py is already 720 lines and on a "schema + safety helpers" mandate; adding CLI-flag-aware resolution mixes concerns. Phase 28 imports detect→output; if `output` lives in profile.py, detect imports profile transitively which it currently doesn't. |
| `graphify/detect.py` | SEED-vault-root-aware-cli's implementation sketch suggested it (`Add _is_obsidian_vault(path: Path) -> bool to detect.py`) | detect.py is read-only this phase per CONTEXT canonical_refs. Phase 28 will modify detect.py — but it will *consume* `ResolvedOutput`, not define it. Co-locating definition + consumer in one phase-mutated module risks merge churn and obscures the integration contract. |
| **NEW `graphify/output.py`** ✅ | Single-purpose module (vault detection + output resolution). Matches one-stage-per-module convention from STRUCTURE.md. Phase 28 (`detect.py` change), Phase 29 (`doctor.py` new), and `__main__.py` all import it without dragging unrelated logic. Tests live in `tests/test_output.py` paired 1:1 per CONVENTIONS. | One more module file. Acceptable cost given clean dependency arrows. |

The SEED's suggestion of putting `_is_obsidian_vault` in `detect.py` was written before Phase 27/28 were split. Splitting them clarifies that detection ≠ scanning; output resolution ≠ file discovery. New module wins.

## Detection Report (VAULT-08 success criterion #1)

The roadmap requires detection be "reported in CLI output". CONTEXT D-09 establishes the `[graphify] ...` stderr convention. Proposed terse single-line format, emitted from `resolve_output()` when `vault_detected=True`:

```
[graphify] vault detected at <vault-path> — output: <notes_dir> (source=<profile|cli-flag>)
```

When no vault is detected, **stay silent** — the v1.0 codepath emits nothing about vault detection today, and silence preserves D-12 backcompat for the no-vault case.

When `cli_output` overrides profile, emit BOTH lines (in order):

```
[graphify] vault detected at <vault-path> — output: <flag-path> (source=cli-flag)
[graphify] --output=<flag-path> overrides profile output (mode=<m>, path=<resolved-p>)
```

The second line is the verbatim D-09 contract. The first line is informational. Confidence: **MEDIUM** — D-09 is locked; the first-line wording is Claude's discretion per CONTEXT but follows the established `[graphify]` convention.

## CLI Wiring (`__main__.py`)

Two call sites, identical pattern:

### Default `run` command (line 2094)

```python
elif cmd == "run":
    # ... parse --router and --output ...
    from graphify.output import resolve_output
    resolved = resolve_output(Path.cwd(), cli_output=cli_output)
    if resolved.vault_detected and resolved.source == "profile":
        target = Path.cwd().resolve()                  # D-07
    else:
        target = Path(raw_target).resolve()
    # ... existing existence check ...
    out_dir = resolved.artifacts_dir                   # was: target / "graphify-out"
    # run_corpus(target, use_router=use_router) — needs out_dir argument
    #   (signature change deferred — see Open Questions)
```

### `--obsidian` command (line 1291)

```python
if cmd == "--obsidian":
    # existing flag loop
    obsidian_dir = "graphify-out/obsidian"             # legacy default
    cli_output = None
    # parse --graph, --obsidian-dir, --output, --dry-run, --force, --obsidian-dedup
    # ...
    from graphify.output import resolve_output
    resolved = resolve_output(Path.cwd(), cli_output=cli_output)
    # Precedence (D-08): --output > --obsidian-dir > profile > legacy default
    if cli_output is not None:
        obsidian_dir = str(resolved.notes_dir)
    elif resolved.vault_detected and resolved.source == "profile":
        obsidian_dir = str(resolved.notes_dir)
    elif user_passed_obsidian_dir:                     # tracked via flag-seen sentinel
        pass                                            # honor explicit --obsidian-dir
    else:
        obsidian_dir = str(resolved.notes_dir)         # falls back to default per D-12
```

The "user_passed_obsidian_dir" tracking is a small sentinel boolean — when the flag-loop sees `--obsidian-dir`, set it `True`. Without this, we can't distinguish "user typed `--obsidian-dir graphify-out/obsidian`" (must honor) from "default value still in place" (allow profile to override). This is the only nuance worth flagging.

Confidence: **HIGH** — pattern matches existing flag-loops verbatim.

## Backward-Compat Verification Recipe (D-12)

Test list to confirm v1.0 paths preserve byte-identical behavior:

1. `test_resolve_output_no_vault_default_paths` — `tmp_path` with no `.obsidian/`, no `--output`. Assert `resolved.notes_dir == Path("graphify-out/obsidian")` and `resolved.artifacts_dir == Path("graphify-out")` and `source == "default"` and `vault_detected is False`.
2. `test_obsidian_explicit_obsidian_dir_honored` — invoke `--obsidian --obsidian-dir mycustom/`. Assert resolver's flag-precedence path leaves `--obsidian-dir` literal value untouched.
3. `test_run_outside_vault_writes_to_graphify_out` — integration: run `graphify run <code-dir>` with no `.obsidian/` anywhere. Assert `graphify-out/` created at the conventional location.
4. `test_no_vault_no_stderr_noise` — capture stderr from no-vault run. Assert no `[graphify] vault detected` line appears (D-12 silent backcompat).
5. `test_obsidian_legacy_invocation_unchanged` — `graphify --obsidian` with no profile.yaml in CWD and no `.obsidian/`. Assert output goes to `graphify-out/obsidian/` exactly as today.

Confidence: **HIGH** — these are direct behavioral assertions on locked-decision invariants.

## Detection Function Placement

Per §"ResolvedOutput Module Placement" — `is_obsidian_vault(path: Path) -> bool` lives in `graphify/output.py`, not `detect.py`. Implementation per D-04:

```python
def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only vault detection (D-04). No parent-walking."""
    obs = path / ".obsidian"
    return obs.is_dir()
```

The `.is_dir()` call (vs `.exists()`) handles the pitfall where a user has a *file* literally named `.obsidian` (gitignore artifact, broken vault, etc.) — `.is_dir()` returns `False` for files. This is the correct behavior; we treat such cases as "not a vault."

Call sites: top of the `run` branch (`__main__.py:2094`) and the `--obsidian` branch (`__main__.py:1291`), both routed through `resolve_output()` so callers never invoke `is_obsidian_vault()` directly.

Confidence: **HIGH** — D-04 locks the predicate.

## Schema Integration Plan (`graphify/profile.py`)

Three concrete changes:

### Change 1: `_DEFAULT_PROFILE`

Do **NOT** add an `output:` key to `_DEFAULT_PROFILE`. The absence of this key in the merged profile is what fires the D-05 refusal. If we set a default, `_deep_merge` would mask the missing-key signal.

Confidence: **HIGH** — direct consequence of D-02 (no fallback) + how `_deep_merge` works (`profile.py:150`).

### Change 2: `_VALID_TOP_LEVEL_KEYS`

```python
# graphify/profile.py:104
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output",   # NEW (Phase 27 D-01)
}
```

Add a sibling constant:

```python
_VALID_OUTPUT_MODES = {"vault-relative", "absolute", "sibling-of-vault"}
```

### Change 3: `validate_profile()` extension

Insert a new branch after the `profile_sync` branch (`profile.py:407`), following the same shape as the `naming` and `mapping` branches:

```python
# output section (Phase 27, D-01, D-03, VAULT-10)
output = profile.get("output")
if output is not None:
    if not isinstance(output, dict):
        errors.append("'output' must be a mapping (dict)")
    else:
        mode = output.get("mode")
        if mode is None:
            errors.append("'output' requires a 'mode' key")
        elif mode not in _VALID_OUTPUT_MODES:
            errors.append(
                f"output.mode {mode!r} invalid — valid modes are: "
                f"{sorted(_VALID_OUTPUT_MODES)}"
            )
        path_val = output.get("path")
        if path_val is None:
            errors.append("'output' requires a 'path' key")
        elif not isinstance(path_val, str) or not path_val.strip():
            errors.append("output.path must be a non-empty string")
        elif mode == "vault-relative":
            if Path(path_val).is_absolute():
                errors.append("output.path must be relative when mode=vault-relative")
            elif path_val.startswith("~"):
                errors.append("output.path must not start with '~' when mode=vault-relative")
            elif ".." in Path(path_val).parts:
                errors.append("output.path must not contain '..' when mode=vault-relative")
        elif mode == "absolute":
            if not Path(path_val).is_absolute():
                errors.append("output.path must be absolute when mode=absolute")
        # mode == "sibling-of-vault": deferred to validate_sibling_path() at use-time
        #   (vault_dir is unknown during static schema validation)
```

### Validator-breakage check

Inspecting `validate_profile()` lines 203-416: every existing branch follows `profile.get(key) → isinstance(...) → leaf checks`. None of them iterate over keys *outside* their target — the unknown-key check at line 211 will not surface false positives once `"output"` is added to the set. **No existing branch breaks.**

Confidence: **HIGH** — read of full `validate_profile()` source.

## Common Pitfalls

### Pitfall 1: Setting `_DEFAULT_PROFILE['output']`

**What goes wrong:** Adding even an empty default `output:` block defeats D-05 — `_deep_merge` produces a non-None `output` for every profile, masking missing-key detection.
**Why it happens:** Reflexive instinct to "make defaults complete."
**How to avoid:** Leave `output` absent from `_DEFAULT_PROFILE`. Detect missingness via `merged.get("output") is None` in `resolve_output()`.
**Warning signs:** A test like `test_load_profile_no_profile_returns_defaults` starts asserting `result["output"] == something`.

### Pitfall 2: `.obsidian` is a file, not a directory

**What goes wrong:** `Path('.obsidian').exists()` returns True for a file too. Predicate becomes false-positive.
**Why it happens:** Some users have a stray `.obsidian` file (broken sync, manual mistake).
**How to avoid:** Use `Path('.obsidian').is_dir()` per D-04 verbatim.
**Warning signs:** Detection report fires on a non-vault directory.

### Pitfall 3: PyYAML import failure under auto-adopt

**What goes wrong:** `load_profile()` already gracefully handles ImportError by returning defaults (`profile.py:179`). But D-05 demands refusal when vault detected and profile missing — and "missing because PyYAML unavailable" looks identical.
**Why it happens:** PyYAML is optional, gated by `obsidian` extra.
**How to avoid:** In `resolve_output()`, when `vault_detected=True` and PyYAML missing, refuse with: `"CWD is an Obsidian vault but PyYAML not installed — install with: pip install graphifyy[obsidian]"`. Distinguish from D-05's missing-profile message.
**Warning signs:** A user installs `graphifyy` (no `[obsidian]`) into a vault and gets a confusing "no profile.yaml" error when the real issue is the parser.

### Pitfall 4: `<vault>/../` resolves to filesystem root in containers

**What goes wrong:** In a Docker container where `/vault/` is the bind-mounted vault, `parent` is `/`. `mode: sibling-of-vault path: graphify-out` resolves to `/graphify-out` — possibly read-only or system-protected.
**Why it happens:** Container layouts where vault is mounted at `/<name>/`.
**How to avoid:** `validate_sibling_path()` rejects when `vault_base.parent == vault_base` (filesystem root case). Error message tells user to switch to `mode=absolute`.
**Warning signs:** "Permission denied" writes from CI runs in containers.

### Pitfall 5: `--output` precedence message printed twice

**What goes wrong:** Both `run` and `--obsidian` branches call `resolve_output()`; if precedence-emit logic is duplicated in callers, message prints twice for combined invocations.
**Why it happens:** Copy-paste of the stderr line from one branch to the other.
**How to avoid:** Emit the precedence line **only inside `resolve_output()`**, never in callers.
**Warning signs:** Test capturing stderr sees the line twice.

### Pitfall 6: Existing `--out-dir` consumers in `--dedup` and `approve` branches

**What goes wrong:** `--out-dir` already appears in `--dedup` (line 1503) and `approve` (line 1759). Phase 27 introduces `--output` only in `run` and `--obsidian` per D-08. If we accidentally widen the new flag to those branches, behavior diverges.
**Why it happens:** Globally adding `--output` "for consistency."
**How to avoid:** Restrict `--output` strictly to `run` and `--obsidian` in this phase. Other branches keep `--out-dir`. Document in the implementation plan.
**Warning signs:** CLI help line for `--dedup` starts mentioning `--output`.

### Pitfall 7: `run_corpus()` signature change

**What goes wrong:** `run_corpus(target, *, use_router)` (`graphify/pipeline.py:7`) currently computes `out_dir` internally as `target/"graphify-out"`. Auto-adopt needs `out_dir` driven by `ResolvedOutput.artifacts_dir`.
**Why it happens:** The pipeline encapsulates output path; phasing the change requires either threading a parameter or making `pipeline` import `output`.
**How to avoid:** Add an optional `out_dir: Path | None = None` parameter to `run_corpus`; when None, preserve current `target / "graphify-out"` behavior (D-12). Auto-adopt callers pass `resolved.artifacts_dir`.
**Warning signs:** Tests need to mock both `target` and "where graph.json was written."

## Code Examples

### `is_obsidian_vault` and `resolve_output` (new module)

```python
# Source: NEW graphify/output.py — Phase 27
"""Vault detection and output destination resolution.

Resolves the (vault, notes_dir, artifacts_dir, source) tuple consumed by
the run/--obsidian commands, Phase 28 self-ingest pruning, and Phase 29
doctor diagnostics.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple


class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]


def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection per D-04."""
    return (path / ".obsidian").is_dir()


def _refuse(msg: str) -> "RuntimeError":
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)


def resolve_output(cwd: Path, *, cli_output: str | None) -> ResolvedOutput:
    """Resolve final output destination per D-06..D-13.

    Precedence: cli_output > profile.output > v1.0 default paths.
    Emits stderr lines per D-09 (precedence) and the detection report.
    """
    cwd_resolved = cwd.resolve()
    is_vault = is_obsidian_vault(cwd_resolved)

    # CLI flag wins everything (D-08, D-10)
    if cli_output is not None:
        flag_path = (cwd_resolved / cli_output).resolve() if not Path(cli_output).is_absolute() else Path(cli_output).resolve()
        if is_vault:
            # Inform + emit precedence message (D-09)
            print(
                f"[graphify] vault detected at {cwd_resolved} — output: {flag_path} (source=cli-flag)",
                file=sys.stderr,
            )
            print(
                f"[graphify] --output={cli_output} overrides profile output "
                f"(mode=cli-literal, path={flag_path})",
                file=sys.stderr,
            )
            return ResolvedOutput(True, cwd_resolved, flag_path, flag_path, "cli-flag")
        return ResolvedOutput(False, None, flag_path, flag_path, "cli-flag")

    # No vault → v1.0 backcompat (D-12)
    if not is_vault:
        return ResolvedOutput(
            vault_detected=False,
            vault_path=None,
            notes_dir=Path("graphify-out/obsidian"),
            artifacts_dir=Path("graphify-out"),
            source="default",
        )

    # Vault detected → require profile (D-05)
    profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
    if not profile_yaml.exists():
        raise _refuse(
            f"CWD is an Obsidian vault ({cwd_resolved}) but no .graphify/profile.yaml found. "
            "Create one (see docs/vault-adapter.md), or pass --output <path> to write outside the vault."
        )

    from graphify.profile import load_profile, validate_sibling_path, validate_vault_path
    profile = load_profile(cwd_resolved)
    output_block = profile.get("output")
    if not output_block or not isinstance(output_block, dict):
        raise _refuse(
            f"CWD is an Obsidian vault but profile.yaml has no 'output:' block. "
            "Declare 'output: {mode: ..., path: ...}' or pass --output <path>."
        )

    mode = output_block.get("mode")
    path_val = output_block.get("path")

    if mode == "vault-relative":
        notes_dir = validate_vault_path(path_val, cwd_resolved)
    elif mode == "absolute":
        notes_dir = Path(path_val).resolve()
    elif mode == "sibling-of-vault":
        notes_dir = validate_sibling_path(path_val, cwd_resolved)
    else:
        raise _refuse(f"profile output.mode {mode!r} invalid")

    # D-11: build artifacts ALWAYS sibling-of-vault as graphify-out
    artifacts_dir = (cwd_resolved.parent / "graphify-out").resolve()

    print(
        f"[graphify] vault detected at {cwd_resolved} — output: {notes_dir} (source=profile)",
        file=sys.stderr,
    )
    return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "profile")
```

Confidence: **HIGH** — every primitive used here is verified in the codebase.

## Test Coverage Plan

New test file: `tests/test_output.py`. Tests for `tests/test_profile.py` extension also listed.

### `tests/test_output.py` (new)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_is_obsidian_vault_true_when_dir_present` | `(tmp_path / ".obsidian").mkdir(); is_obsidian_vault(tmp_path) is True` |
| 2 | `test_is_obsidian_vault_false_when_file_not_dir` | `(tmp_path / ".obsidian").touch(); is_obsidian_vault(tmp_path) is False` (Pitfall 2) |
| 3 | `test_is_obsidian_vault_false_when_absent` | empty tmp_path; predicate False |
| 4 | `test_is_obsidian_vault_no_parent_walk` | nested dir under vault — predicate False at the nested CWD (D-04) |
| 5 | `test_resolve_output_no_vault_default_paths` | source=default, notes_dir=graphify-out/obsidian, artifacts_dir=graphify-out, vault_detected False, no stderr |
| 6 | `test_resolve_output_vault_no_profile_refuses` | `.obsidian/` present, no profile.yaml → SystemExit + actionable stderr (D-05) |
| 7 | `test_resolve_output_vault_profile_no_output_block_refuses` | profile.yaml without `output:` → SystemExit (D-02) |
| 8 | `test_resolve_output_vault_relative_resolves` | `mode: vault-relative path: Knowledge/Graph` → notes_dir=`<vault>/Knowledge/Graph`, source=profile |
| 9 | `test_resolve_output_absolute_mode` | `mode: absolute path: /tmp/notes` → notes_dir=`/tmp/notes`, source=profile |
| 10 | `test_resolve_output_sibling_of_vault_mode` | `mode: sibling-of-vault path: graphify-notes` → notes_dir=`<vault>/../graphify-notes`, source=profile |
| 11 | `test_resolve_output_artifacts_always_sibling_when_vault` | D-11: any profile mode still routes artifacts_dir to `<vault>/../graphify-out` |
| 12 | `test_resolve_output_cli_flag_overrides_profile_emits_stderr` | profile + `cli_output="custom-out"` → source=cli-flag, exact D-09 stderr line present |
| 13 | `test_resolve_output_cli_flag_no_vault` | no `.obsidian/`, cli_output set → source=cli-flag, vault_detected=False, no D-09 line (only fires when overriding profile) |
| 14 | `test_resolve_output_precedence_message_emitted_once` | combined call sites — message appears exactly once (Pitfall 5) |
| 15 | `test_validate_sibling_path_rejects_empty` | `""`, `"   "` → ValueError |
| 16 | `test_validate_sibling_path_rejects_traversal` | `"../foo"`, `"a/../../b"` → ValueError |
| 17 | `test_validate_sibling_path_rejects_absolute` | `"/etc"` → ValueError |
| 18 | `test_validate_sibling_path_rejects_home_expansion` | `"~/notes"` → ValueError |
| 19 | `test_validate_sibling_path_rejects_filesystem_root_parent` | mock `vault_base.parent == vault_base` → ValueError (Pitfall 4) |
| 20 | `test_validate_sibling_path_happy_path` | `"graphify-notes"` with normal vault → resolves under `<vault>/../graphify-notes` |
| 21 | `test_resolve_output_pyyaml_missing_distinct_message` | mock ImportError → distinct error (Pitfall 3) |

### `tests/test_profile.py` (extension)

| # | Test | Asserts |
|---|------|---------|
| 22 | `test_validate_profile_output_block_valid_vault_relative` | empty errors |
| 23 | `test_validate_profile_output_block_valid_absolute` | empty errors |
| 24 | `test_validate_profile_output_block_valid_sibling_of_vault` | empty errors (path safety deferred to use-time) |
| 25 | `test_validate_profile_output_missing_mode` | error mentions "requires a 'mode' key" |
| 26 | `test_validate_profile_output_invalid_mode` | error lists valid modes |
| 27 | `test_validate_profile_output_missing_path` | error mentions "requires a 'path' key" |
| 28 | `test_validate_profile_output_empty_path` | error mentions non-empty |
| 29 | `test_validate_profile_output_vault_relative_rejects_absolute` | error |
| 30 | `test_validate_profile_output_vault_relative_rejects_home` | error |
| 31 | `test_validate_profile_output_vault_relative_rejects_traversal` | error |
| 32 | `test_validate_profile_output_absolute_requires_absolute_path` | error |
| 33 | `test_validate_profile_unknown_top_level_key_still_caught` | regression: existing unknown-key check still works after `output` added |
| 34 | `test_default_profile_has_no_output_key` | `_DEFAULT_PROFILE.get("output") is None` (Pitfall 1 prevention) |

Total: **34 tests**, all pure unit tests, all confined to `tmp_path`, no network.

Confidence: **HIGH** — direct expansion of established `tests/test_profile.py` patterns.

## State of the Art

N/A — no third-party state of the art is relevant. This is in-tree plumbing.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (see `pyproject.toml` test deps) |
| Config file | `pyproject.toml` (no pytest.ini) |
| Quick run command | `pytest tests/test_output.py tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |
| Single test | `pytest tests/test_output.py::test_resolve_output_vault_relative_resolves -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-08 | Detects `.obsidian/` at CWD; reports detection on stderr | unit | `pytest tests/test_output.py::test_is_obsidian_vault_true_when_dir_present -q` | ❌ Wave 0 |
| VAULT-08 | False on file (not dir); false absent; no parent-walk | unit | `pytest tests/test_output.py::test_is_obsidian_vault_false_when_file_not_dir -q` | ❌ Wave 0 |
| VAULT-08 | Detection emits terse `[graphify] vault detected at …` stderr line | unit (capsys) | `pytest tests/test_output.py::test_resolve_output_vault_relative_resolves -q` | ❌ Wave 0 |
| VAULT-09 | Vault + profile.yaml + `output:` → auto-adopt source=profile, input=CWD | unit | `pytest tests/test_output.py::test_resolve_output_vault_relative_resolves -q` | ❌ Wave 0 |
| VAULT-09 | Vault + missing profile → refuse with actionable message | unit | `pytest tests/test_output.py::test_resolve_output_vault_no_profile_refuses -q` | ❌ Wave 0 |
| VAULT-09 | Vault + profile present + `output:` missing → refuse | unit | `pytest tests/test_output.py::test_resolve_output_vault_profile_no_output_block_refuses -q` | ❌ Wave 0 |
| VAULT-10 | Schema accepts vault-relative / absolute / sibling-of-vault | unit | `pytest tests/test_profile.py -k "test_validate_profile_output" -q` | ❌ Wave 0 |
| VAULT-10 | `--output` flag overrides profile + emits D-09 stderr line | unit (capsys) | `pytest tests/test_output.py::test_resolve_output_cli_flag_overrides_profile_emits_stderr -q` | ❌ Wave 0 |
| VAULT-10 | sibling-of-vault validator rejects traversal/empty/root | unit | `pytest tests/test_output.py::test_validate_sibling_path_rejects_traversal -q` | ❌ Wave 0 |
| D-12 backcompat | No vault → v1.0 paths exact | unit | `pytest tests/test_output.py::test_resolve_output_no_vault_default_paths -q` | ❌ Wave 0 |
| D-11 split | Build artifacts always sibling-of-vault when auto-adopt fires | unit | `pytest tests/test_output.py::test_resolve_output_artifacts_always_sibling_when_vault -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_output.py tests/test_profile.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_output.py` — net-new file; 21 tests (covers VAULT-08, VAULT-09, VAULT-10 behavior side)
- [ ] `tests/test_profile.py` — append 13 new tests for `output:` schema branch
- [ ] No new fixtures required — all tests use `tmp_path` and inline YAML strings (matches existing `test_load_profile_with_yaml` pattern at `tests/test_profile.py:62`)
- [ ] No framework install needed — pytest already in dev deps

### Observable Signals (what the planner verifies)

1. **`.obsidian/.is_dir()` returns True** → detection fires (VAULT-08 unit-checkable)
2. **stderr contains `[graphify] vault detected at <path>`** → detection report (VAULT-08 success criterion #1)
3. **`ResolvedOutput.source == "profile"`** → auto-adopt happened (VAULT-09)
4. **SystemExit raised with actionable message** when vault+no-profile or vault+profile-no-output (D-05, D-02)
5. **stderr contains `[graphify] --output=… overrides profile output (mode=…, path=…)`** → flag precedence reported (D-09)
6. **`ResolvedOutput.artifacts_dir == <vault>/../graphify-out`** when auto-adopt fires → D-11 split
7. **`ResolvedOutput == (False, None, Path("graphify-out/obsidian"), Path("graphify-out"), "default")`** when no vault → D-12 byte-identical backcompat

## Sources

### Primary (HIGH confidence)
- [VERIFIED: `graphify/profile.py` lines 1-720] — full module read; `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `validate_profile`, `validate_vault_path`, `PreflightResult` pattern, deep_merge, load_profile (PyYAML guard at 178-185)
- [VERIFIED: `graphify/__main__.py` lines 920-960, 1162-1220, 1264-1382, 1487-1535, 2094-2113] — flag-loop pattern at 1304 / 1503; `run` command at 2094; `--obsidian` at 1291; CLI dispatch
- [VERIFIED: `graphify/detect.py` lines 1-60] — `_MANIFEST_PATH = "graphify-out/manifest.json"` confirms hard-coded default that must stay intact for D-12
- [VERIFIED: `graphify/pipeline.py:7`] — `run_corpus(target: Path, *, use_router: bool) -> dict` signature (Pitfall 7)
- [CITED: `.planning/phases/27-vault-detection-profile-driven-output-routing/27-CONTEXT.md`] — D-01 through D-13 verbatim
- [CITED: `.planning/REQUIREMENTS.md`] — VAULT-08, VAULT-09, VAULT-10
- [CITED: `.planning/ROADMAP.md` lines 156-185] — Phase 27 success criteria + Phase 28/29 dependency declaration
- [CITED: `.planning/seeds/SEED-vault-root-aware-cli.md`] — Option A/B/C; locked to Option C
- [CITED: `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md`] — D-02 origin
- [CITED: `.planning/notes/obsidian-export-self-ingestion-loop.md`] — root cause this milestone fixes
- [CITED: `CLAUDE.md`] — constraints: Python 3.10+, no new required deps, backward compat, pure unit tests, `from __future__ import annotations`, `str | None` not `Optional[str]`
- [CITED: `SECURITY.md`] — vault-confinement model that mode=sibling-of-vault deliberately steps outside (D-03)

### Secondary (MEDIUM confidence)
- [VERIFIED: `tests/test_profile.py` lines 1-80] — testing pattern: `tmp_path`, inline YAML, `_DEFAULT_PROFILE` import, `_deep_merge` import. Direct template for new tests.

### Tertiary (LOW confidence)
- None — every claim verified against codebase.

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** — Use `from __future__ import annotations`, `str | None`, `dict[str, list[str]]`, `Literal[...]` syntax (CONFIRMED — no Python 3.10 incompatibility in proposed code).
- **No new required dependencies** — Satisfied trivially. PyYAML stays optional, only stdlib added.
- **Backward compatibility** — D-12 explicit. Test #5 + integration tests confirm.
- **Pure unit tests, no filesystem side effects outside `tmp_path`** — All proposed tests use `tmp_path` exclusively.
- **No formatter/linter** — Match existing style; 4-space indent; module docstring after `from __future__`.
- **Type hints on all functions** — Confirmed in proposed code.
- **No `**kwargs`** — Proposed `resolve_output(cwd, *, cli_output)` keyword-only single arg, no kwargs explosion.
- **Stderr for warnings/errors** prefixed `[graphify]` — Followed in detection + precedence messages.
- **Validate-first, fail-loudly** — `validate_profile()` accumulator pattern reused.
- **Module-per-stage** convention — New `output.py` follows the convention.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `run` command (`__main__.py:2094`) does not currently parse any flags besides `--router` | CLI Wiring | Low — direct read confirmed only `--router` pattern; if a flag I missed exists, just one extra line in the new flag-loop. Mitigation: planner re-reads lines 2094-2113 before extending. |
| A2 | `run_corpus()` can accept an optional `out_dir` keyword without breaking other callers | Pitfall 7 | Medium — pipeline.py line 7 confirms current signature `run_corpus(target: Path, *, use_router: bool) -> dict`. Adding `out_dir: Path | None = None` is additive. Other callers grep-checked: none in `__main__.py` outside line 2112. Confidence high but flagged. |
| A3 | The vault-detection report wording (first line, before D-09) is acceptable Claude's-discretion content | Detection Report | Low — CONTEXT explicitly cedes wording to Claude's discretion. Planner can iterate. |
| A4 | `--obsidian-dir` "user passed it" detection via sentinel boolean is the right disambiguation strategy | CLI Wiring | Low — same pattern is already used implicitly elsewhere in `__main__.py`. Alternative: track default sentinel value in initial assignment (`obsidian_dir: str | None = None`, set default after flag-loop). Planner picks. |

**If this table is empty:** N/A — assumptions present.

## Open Questions

1. **Should `run_corpus()` gain an `out_dir` parameter, or should `__main__.py` mutate working directory before calling it?**
   - What we know: current signature hard-codes `target / "graphify-out"`; auto-adopt needs sibling-of-vault artifacts placement.
   - What's unclear: planner's preference between API change (cleaner) vs. CWD juggling (smaller diff).
   - Recommendation: API change. Add `out_dir: Path | None = None` keyword. Default preserves v1.0. (See Pitfall 7.)

2. **Where exactly should `validate_sibling_path()` live — `profile.py` or `output.py`?**
   - What we know: it's a path validator (profile.py-style) but used only by `output.py` resolver.
   - What's unclear: which module's tests assert it.
   - Recommendation: `profile.py`, next to `validate_vault_path()` (`profile.py:423`). Tests in `tests/test_profile.py`. Consistency wins.

3. **Should the precedence message also fire when `--output` is set but no profile exists (no-vault case)?**
   - What we know: D-09 phrasing "overrides profile output" implies a profile exists.
   - What's unclear: whether to print *some* line for "explicit override, no profile" cases.
   - Recommendation: silent in no-vault + cli-flag case (only the `--output` literal path applies; no profile to "override"). Test #13 codifies this. Planner can flip if user wants louder UX.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3.10+ | Core | ✓ | 3.10 / 3.12 (CI) | — |
| pytest | Tests | ✓ (already pinned) | matches CI | — |
| pyyaml | profile.yaml parsing | optional (`obsidian` extra) | already declared | Pitfall 3: distinct error message |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** PyYAML covered by Pitfall 3 explicit messaging.

## Metadata

**Confidence breakdown:**
- Schema integration: **HIGH** — full read of `profile.py`; pattern is direct copy of `diagram_types`/`tag_taxonomy` branches.
- ResolvedOutput placement: **HIGH** — explicit trade-off table; D-13 contract clear.
- Sibling-of-vault validator: **HIGH** — direct mirror of `validate_vault_path` with explicit relaxation.
- CLI wiring: **HIGH** — pattern verified at `__main__.py:1304` and `:1503`.
- Backward compat: **HIGH** — D-12 + Pitfall 7 both addressed.
- Test coverage: **HIGH** — 34 tests cover every locked decision and every observable signal.

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days — codebase changes around `profile.py` / `__main__.py` would invalidate specific line numbers but not the structural plan)
