# Phase 41 — Technical Research

## RESEARCH COMPLETE

### Goal recap

Pin Obsidian vault root via **`--vault`**, optional **`GRAPHIFY_VAULT`** / **`--vault-list`**, keep **CI deterministic**, align **`doctor`** and **dry-run** with **`ResolvedOutput`** (`graphify/output.py`).

### Current architecture

- **`resolve_output(cwd, cli_output=None)`** returns **`ResolvedOutput`**: `vault_detected`, `vault_path`, `notes_dir`, `artifacts_dir`, `source`, `exclude_globs`.
- **Vault detection** is **CWD-only** (`is_obsidian_vault`) — no `--vault` today for the main `run` pipeline.
- **`tests/test_output.py`** already regression-tests refusal modes, profile modes, CLI `--output` override stderr — extend here for `--vault` / env / list semantics.

### Recommended extension (single resolver)

Add a **facade** used by CLI (avoid splintering):

```text
resolve_execution_paths(
    cwd: Path,
    *,
    cli_output: str | None = None,
    explicit_vault: Path | None = None,   # from --vault
    env_vault: str | None = None,          # os.environ.get("GRAPHIFY_VAULT")
    vault_list_file: Path | None = None, # from --vault-list
) -> ResolvedOutput
```

**Precedence (41-CONTEXT D-01):** resolved `explicit_vault` > env (`GRAPHIFY_VAULT`) > first valid entry from list file (if provided) > existing **`resolve_output(cwd, cli_output)`** behavior using **effective working directory** = vault root when a vault pin applies (so profile loads from pinned vault, not accidental CWD).

**Multi-match / discovery:** When multiple candidates exist and no pin (D-03): **TTY** → short interactive choice listing paths; **non-TTY** → exit 2 with candidate list (no prompt).

### CLI integration notes

- **`graphify/__main__.py`** uses manual `sys.argv` dispatch. Prefer **`parse_known_args`** or a **pre-scan** for `--vault` / `--vault-list` **before** subcommand dispatch so subcommands (`run`, `doctor`, `elicit`, `--obsidian`) share one resolution path.
- Subcommands that already take **`--vault`** (`init-diagram-templates`, `approve`, …) must stay consistent with global semantics — document whether global `--vault` stacks or whether local wins (planner: recommend **local subcommand flag overrides global** when both present, with stderr note).

### Doctor / dry-run

- Locate **`doctor`** implementation branch in **`__main__.py`** (diagnostics module may live under **`graphify/`**). Thread **`ResolvedOutput`** fields into stdout/stderr banners per **D-05/D-06**.

### Security

- Reuse **`validate_graph_path`** / **`validate_vault_path`** from **`graphify.profile`** for any user-supplied `--vault` or list file paths — reject `..` escapes consistent with **SECURITY.md**.

### Testing strategy

- **`tmp_path`** vault fixtures: `.obsidian/` dir + minimal `.graphify/profile.yaml` with `output:` block (copy patterns from **`tests/test_output.py`**).
- Matrix: `--vault` only, env only, list file only, precedence conflicts, non-TTY multi-candidate error.

---

## Validation Architecture

Phase 41 verification is **pytest-first**:

| Dimension | Approach |
|-----------|----------|
| Correctness | `tests/test_output.py` extensions + new `tests/test_vault_cli.py` (or split) for argv/integration |
| Security | Tests assert traversal rejection on `--vault` outside allowed roots |
| Doctor parity | Golden stderr/stdout fragments or structured sections containing `vault_path=` / `source=` |

Nyquist Wave 0: extend **`tests/test_output.py`** with failing stubs for new resolver API before implementation (red-green optional per planner).
