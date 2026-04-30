# Phase 49 — Technical Research

## RESEARCH COMPLETE

**Date:** 2026-04-30  
**Question answered:** What is needed to plan CLI `--version`, success version footer, skill stamp messaging, and a single `package_version()` source?

### Findings

1. **`graphify/__main__.py`** defines `__version__` via `importlib.metadata.version("graphifyy")` at import time; `_check_skill_version` compares `.graphify_version` adjacent to `SKILL.md` to `__version__`. Skill checks run at start of `main()` for every command except `install`, `uninstall`, `-h`/`--help`.
2. **Duplicate readers:** `capability._graphify_version()`, `harness_interchange._package_version()`, `elicit` (inline `pkg_version`) duplicate the same pattern.
3. **`main()` control flow:** Large `if cmd == ... / elif ...` chain; many branches end in `sys.exit(0)`. Top-level `graphify install` calls `install()` then falls through (implicit exit 0). Subcommand `graphify claude install` etc. also return without `sys.exit` in some paths — same fall-through.
4. **Footer strategy:** Introduce `_cli_exit(code: int, *, emit_version_footer: bool = True) -> NoReturn` that prints `[graphify] version {v}` on stderr when `code == 0` and footer enabled; replace `sys.exit(0)` call sites. Suppress footer for `install` / `* install` / `* uninstall` per CONTEXT D-49.03.

### Validation Architecture

- **Dimension 8 (Nyquist):** Automated pytest via `python -m graphify` subprocess (existing `tests/test_main_cli.py` pattern). Wave 0: extend or add `tests/test_main_flags.py` / `test_main_cli.py` for `--version`, `-V`, footer substring on a lightweight success command (`--validate-profile` on empty tmp dir), and stderr wording for mismatched `.graphify_version` fixture under `tmp_path` if feasible without writing under HOME.
